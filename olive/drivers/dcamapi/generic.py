import asyncio
import ctypes
import logging
import re
from functools import lru_cache, partial
from multiprocessing.sharedctypes import RawArray
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from olive.devices import BufferRetrieveMode, Camera
from olive.devices.base import DeviceInfo
from olive.devices.error import UnsupportedClassError
from olive.drivers.base import Driver
from olive.utils import timeit

from .wrapper import DCAM
from .wrapper import DCAMAPI as _DCAMAPI
from .wrapper import Capability, CaptureStatus, CaptureType, Event, Info

__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=4)


async def sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, partial(func, *args, **kwargs))


class HamamatsuCamera(Camera):
    def __init__(self, driver, index):
        super().__init__(driver)
        self._index, self._api = index, None
        self._properties = dict()

        self._event = None

    ##

    @property
    def api(self):
        return self._api

    @property
    def is_busy(self):
        return self.api.status() != CaptureStatus.Ready

    @property
    def is_opened(self):
        return self._api is not None

    ##

    async def test_open(self):
        try:
            await super().test_open()
        except RuntimeError as err:
            logger.exception(err)
            raise UnsupportedClassError

    async def _open(self):
        handle = self.driver.api.open(self._index)  # cannot wrap in sync
        self._api = DCAM(handle)

        # probe the camera
        await self.enumerate_properties()

        # enable defect correction
        await self.set_property("defect_correct_mode", "on")

    async def _close(self):
        self.driver.api.close(self.api)  # cannot wrap in sync
        self._api = None

    ##

    async def get_device_info(self) -> DeviceInfo:
        params = {
            "version": Info.APIVersion,
            "vendor": Info.Vendor,
            "model": Info.Model,
            "serial_number": Info.CameraID,
        }
        for key, value in params.items():
            params[key] = await sync(self.api.get_string, value)

        # serial number requires further parsing
        parsed_sn = re.match(r"S/N: (\d+)", params["serial_number"]).group(1)
        params["serial_number"] = parsed_sn

        # DEBUG
        for option in (Capability.Region, Capability.FrameOption, Capability.LUT):
            try:
                print(self.api.get_capability(option))
            except RuntimeError as err:
                logger.error(err)

        return DeviceInfo(**params)

    ##

    async def enumerate_properties(self):
        properties = dict()

        curr_id, next_id = -1, self.api.get_next_id()
        while curr_id != next_id:
            try:
                curr_id, next_id = next_id, await sync(self.api.get_next_id, next_id)
            except RuntimeError:
                # no more supported property id
                break

            name = await sync(self.api.get_name, curr_id)
            name = name.lower().replace(" ", "_")
            properties[name] = curr_id

        self._properties = properties
        return tuple(properties.keys())

    async def get_property(self, name):
        attributes = self._get_property_attributes(name)
        if not attributes["readable"]:
            raise TypeError(f'property "{name}" is not readable')

        if attributes["is_array"]:
            logger.warning(
                f"an array property with {attributes['n_elements']} element(s), NOT IMPLEMENTED"
            )

        # convert data type
        prop_type, prop_id = attributes["type"], self._get_property_id(name)

        value = await sync(self.api.get_value, prop_id)
        if prop_type == "mode":
            # NOTE assuming uniform step
            index = int(value) - int(attributes["min"])
            return attributes["modes"][index]
        elif prop_type == "long":
            return int(value)
        elif prop_type == "real":
            return float(value)

    async def set_property(self, name, value):
        attributes = self._get_property_attributes(name)
        if not attributes["writable"]:
            raise TypeError(f'property "{name}" is not writable')

        prop_type, prop_id = attributes["type"], self._get_property_id(name)
        if prop_type == "mode":
            # translate string enum back to index
            # NOTE assuming uniform step
            value = attributes["modes"].index(value) + int(attributes["min"])
        await sync(self.api.set_value, prop_id, value)

    def _get_property_id(self, name):
        return self._properties[name]

    @lru_cache(maxsize=16)
    def _get_property_attributes(self, name):
        """
        Attributes define the characteristic of a property.

        - readable
        - writable
        - auto-rounding:
            value will be adjusted if host software does not set an accurate value
        - stepping inconsistent:
            stepping value is not consistent throughout its range
        - volatile:
            can be changed manually or automatically by the device, e.g. temperature
        - data stream:
            value change will affect the data stream
        - access ready:
            can be changed during READY state
        - access busy:
            can be changed during busy state.

        Args:
            name (str): name of the property
        """
        logger.debug(f"attributes of {name} cache missed")
        prop_id = self._get_property_id(name)
        return self.api.get_attr(prop_id)

    ##

    async def configure_acquisition(self, n_frames, continuous=False):
        # create buffer
        await super().configure_acquisition(n_frames, continuous)

        # create event handle
        self._event = self.api.event
        self._event.open()

    async def _configure_frame_buffer(self, n_frames):
        """Attach buffer to DCAM-API internals."""
        await super()._configure_frame_buffer(n_frames)
        self.api.attach(self.buffer.frames)

    def start_acquisition(self):
        mode = CaptureType.Sequence if self.continuous else CaptureType.Snap
        self.api.start(mode)
        logger.debug(f"acquisition STARTED")

    def _retrieve_frame(self, mode: BufferRetrieveMode):
        self._event.start(Event.FrameReady)

        latest_index, n_frames = self.api.transfer_info

        """
        # DCAM-API writes directly to the buffer, dummy write
        n_backlog = latest_index - self.buffer._write_index + 1
        for _ in range(n_backlog):
            self.buffer.write()
        """

        # TODO should i simplify this?

        if mode == BufferRetrieveMode.Latest:
            # fast forward
            self.buffer._read_index = latest_index
        else:
            wi0, ri0 = self.buffer._write_index, self.buffer._read_index
            if wi0 > ri0 or self.buffer.empty():
                ri0 += self.buffer.capacity()

            wi1 = latest_index + 1
            if wi1 >= ri0:
                self.buffer._is_full = True
                raise IndexError("not enough internal buffer")

            # DCAM-API writes directly to the buffer, update index only
            self.buffer._write_index = wi1 % self.buffer.capacity()

            # ---W--R---
            # ----W-R---
            #
            # ---W--R---
            # ------RW-- (E)
            #
            # ---W--R---
            # ------R---W
            # W-----R--- (E)
            #
            # ---W--R---
            # ------R-------W
            # ----W-R--- (E)
            #
            # ---R--W---
            #   ------W----R
            # ---R----W-
            #   --------W--R
            #
            # ---R--W---
            #   ------W----R
            # ---R-------W
            # -W-R------
            #   ---------W-R
            #
            # ---R--W---
            #   ------W----R
            # ---R----------W
            # ---RW----- (E)
            #   -----------RW
            #
            # ---R--W---
            #   ------W----R
            # ---R-------------W
            # ---R---W-- (E)
            #   -----------R---W

        # since DCAM-API write directly into buffer list, use read to pull it out
        return self.buffer.read()

    def stop_acquisition(self):
        self.api.stop()
        self._event.start(Event.Stopped)
        logger.debug("acquisition STOPPED")

    def unconfigure_acquisition(self):
        # cleanup event handle
        self._event.close()
        self._event = None

        # detach
        self.api.release()

        # free buffer
        super().unconfigure_acquisition()

    ##

    async def get_dtype(self):
        pixel_type = await self.get_property("image_pixel_type")
        try:
            return {"mono8": np.uint8, "mono16": np.uint16}[pixel_type]
        except KeyError:
            raise NotImplementedError(f"unknown pixel type {pixel_type.upper()}")

    async def get_exposure_time(self):
        time = await self.get_property("exposure_time")
        return time * 1000  # default return value is in s

    async def set_exposure_time(self, value):
        # default value is in s
        await self.set_property("exposure_time", value / 1000)

    async def get_max_roi_shape(self):
        nx = await self.get_property("image_detector_pixel_num_horz")
        ny = await self.get_property("image_detector_pixel_num_vert")
        return ny, nx

    async def get_roi(self):
        pos0 = (
            await self.get_property("subarray_vpos"),
            await self.get_property("subarray_hpos"),
        )
        shape = (
            await self.get_property("subarray_vsize"),
            await self.get_property("subarray_hsize"),
        )
        return pos0, shape

    async def set_roi(self, pos0=None, shape=None):
        """
        Set region-of-interest.

        Args:
            pos0 (tuple, optional): top-left position
            shape (tuple, optional): shape of the ROI
        """
        # save prior roi
        prev_pos0, prev_shape = await self.get_roi()

        # disable subarray mode
        await self.set_property("subarray_mode", "off")

        max_shape = await self.get_max_roi_shape()

        try:
            # pos0
            desc = "initial position"
            if pos0 is None:
                if shape is None:
                    # full sensor range, disable sub-array mode, nothing to do
                    return
                else:
                    # centered
                    pos0 = [(ms - s) // 2 for ms, s in zip(max_shape, shape)]
                    desc = "inferred " + desc
            try:
                for name, value in zip(("subarray_vpos", "subarray_hpos"), pos0):
                    await self.set_property(name, value)
            except RuntimeError:
                raise ValueError(f"{desc} {pos0[::-1]} out-of-bound")

            # shape
            if shape is None:
                # extend to boundary
                shape = [ms - p for ms, p in zip(max_shape, pos0)]
            else:
                # manual
                pass
            try:
                for name, value in zip(("subarray_vsize", "subarray_hsize"), shape):
                    await self.set_property(name, value)
                # re-enable
                self.set_property("subarray_mode", "on")
            except RuntimeError:
                pos1 = tuple(p + (s - 1) for p, s in zip(pos0, shape))
                raise ValueError(
                    f"unable to accommodate the ROI, {pos0[::-1]}->{pos1[::-1]}"
                )
        except ValueError:
            logger.warning("revert back to previous ROI...")
            await self.set_roi(pos0=prev_pos0, shape=prev_shape)
            raise


class DCAMAPI(Driver):
    api = None

    def __init__(self):
        # ensure API is only instantiated once
        if self.api is None:
            logger.info(f"loading DCAM-API")
            self.api = _DCAMAPI()
        super().__init__()

    ##

    async def initialize(self):
        try:
            await sync(self.api.init)
        except RuntimeError as err:
            if "No cameras" not in str(err):
                logger.debug(f"no camera found")
                raise

    async def shutdown(self):
        await sync(self.api.uninit)

    def _enumerate_device_candidates(self) -> Iterable[HamamatsuCamera]:
        n_devices = self.api.n_devices
        logger.debug(f"found {n_devices} camera(s)")
        return [HamamatsuCamera(self, i) for i in range(n_devices)]
