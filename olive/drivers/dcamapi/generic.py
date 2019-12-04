import ctypes
from functools import lru_cache
import logging
from multiprocessing.sharedctypes import RawArray
import re

import numpy as np
import trio

from olive.core import Driver, DeviceInfo
from olive.devices import Camera, BufferRetrieveMode
from olive.devices.errors import UnsupportedDeviceError

from .wrapper import DCAMAPI as _DCAMAPI
from .wrapper import Capability, CaptureStatus, CaptureType, DCAM, Event, Info

__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)


class HamamatsuCamera(Camera):
    def __init__(self, driver, index):
        super().__init__(driver)
        self._index, self._api = index, None
        self._properties = dict()

        self._event = None

    ##

    async def test_open(self):
        try:
            await self.open()
            logger.info(f".. {self.info}")
        except RuntimeError as err:
            logger.exception(err)
            raise UnsupportedDeviceError
        finally:
            await self.close()

    async def open(self):
        """
        Note:
            Do not open and close in another thread.
        """
        handle = self.driver.api.open(self._index)
        self._api = DCAM(handle)

        # probe the camera
        await self.enumerate_properties()

        # enable defect correction
        self.set_property("defect_correct_mode", "on")

    async def close(self):
        self.driver.api.close(self.api)
        self._api = None

    ##

    async def enumerate_properties(self):
        properties = dict()

        curr_id, next_id = -1, self.api.get_next_id()
        while curr_id != next_id:
            try:
                curr_id, next_id = next_id, self.api.get_next_id(next_id)
            except RuntimeError:
                # no more supported property id
                break

            name = self.api.get_name(curr_id)
            name = name.lower().replace(" ", "_")
            properties[name] = curr_id

        self._properties = properties
        return tuple(properties.keys())

    def get_property(self, name):
        attributes = self._get_property_attributes(name)
        if not attributes["readable"]:
            raise TypeError(f'property "{name}" is not readable')

        if attributes["is_array"]:
            logger.warning(
                f"an array property with {attributes['n_elements']} element(s), NOT IMPLEMENTED"
            )

        # convert data type
        prop_type, prop_id = attributes["type"], self._get_property_id(name)

        value = self.api.get_value(prop_id)
        if prop_type == "mode":
            # NOTE assuming uniform step
            index = int(value) - int(attributes["min"])
            return attributes["modes"][index]
        elif prop_type == "long":
            return int(value)
        elif prop_type == "real":
            return float(value)

    def set_property(self, name, value):
        attributes = self._get_property_attributes(name)
        if not attributes["writable"]:
            raise TypeError(f'property "{name}" is not writable')

        prop_type, prop_id = attributes["type"], self._get_property_id(name)
        if prop_type == "mode":
            # translate string enum back to index
            # NOTE assuming uniform step
            value = attributes["modes"].index(value) + int(attributes["min"])
        self.api.set_value(prop_id, value)

    def _get_property_id(self, name):
        return self._properties[name]

    @lru_cache(maxsize=16)
    def _get_property_attributes(self, name):
        """
        Attributes indicates the characteristic of the property.

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

    async def configure_ring(self, n_frames):
        """Attach buffer to DCAM-API internals."""
        await super().configure_ring(n_frames)
        self.api.attach(self.buffer.frames)

    def start_acquisition(self):
        mode = CaptureType.Sequence if self.continuous else CaptureType.Snap
        self.api.start(mode)
        logger.debug(f"acquisition STARTED")

    async def _extract_frame(self, mode: BufferRetrieveMode):
        self._event.start(Event.FrameReady)

        while True:
            latest_index, n_frames = self.api.transfer_info()

            """
            # DCAM-API writes directly to the buffer, dummy write
            n_backlog = latest_index - self.buffer._write_index + 1
            for _ in range(n_backlog):
                self.buffer.write()
            """

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

            frame = self.buffer.read()
            if frame is not None:
                return frame
            else:
                await trio.sleep(0)
                logger.debug(f"retry...")

    def stop_acquisition(self):
        self.api.stop()
        self._event.start(Event.Stopped)
        logger.debug("acquisition STOPPED")

    async def unconfigure_acquisition(self):
        # cleanup event handle
        self._event.close()
        self._event = None

        # detach
        self.api.release()

        # free buffer
        await super().unconfigure_acquisition()

    ##

    def get_dtype(self):
        pixel_type = self.get_property("image_pixel_type")
        try:
            return {"mono8": np.uint8, "mono16": np.uint16}[pixel_type]
        except KeyError:
            raise NotImplementedError(f"unknown pixel type {pixel_type.upper()}")

    def get_exposure_time(self):
        # NOTE default return value is in s
        return self.get_property("exposure_time") * 1000

    def set_exposure_time(self, value):
        # NOTE default return value is in s
        self.set_property("exposure_time", value / 1000)

    def get_max_roi_shape(self):
        nx = self.get_property("image_detector_pixel_num_horz")
        ny = self.get_property("image_detector_pixel_num_vert")
        return ny, nx

    def get_roi(self):
        pos0 = (self.get_property("subarray_vpos"), self.get_property("subarray_hpos"))
        shape = (
            self.get_property("subarray_vsize"),
            self.get_property("subarray_hsize"),
        )
        return pos0, shape

    def set_roi(self, pos0=None, shape=None):
        """
        Set region-of-interest.

        Args:
            pos0 (tuple, optional): top-left position
            shape (tuple, optional): shape of the ROI
        """
        # save prior roi
        prev_pos0, prev_shape = self.get_roi()

        # disable subarray mode
        self.set_property("subarray_mode", "off")

        max_shape = self.get_max_roi_shape()

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
                    self.set_property(name, value)
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
                    self.set_property(name, value)
                # re-enable
                self.set_property("subarray_mode", "on")
            except RuntimeError:
                pos1 = tuple(p + (s - 1) for p, s in zip(pos0, shape))
                raise ValueError(
                    f"unable to accommodate the ROI, {pos0[::-1]}->{pos1[::-1]}"
                )
        except ValueError:
            logger.warning("revert back to previous ROI...")
            self.set_roi(pos0=prev_pos0, shape=prev_shape)
            raise

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

    @property
    def info(self):
        raw_sn = self.api.get_string(Info.CameraID)
        params = {
            "version": self.api.get_string(Info.APIVersion),
            "vendor": self.api.get_string(Info.Vendor),
            "model": self.api.get_string(Info.Model),
            "serial_number": re.match(r"S/N: (\d+)", raw_sn).group(1),
        }

        # DEBUG
        for option in (Capability.Region, Capability.FrameOption, Capability.LUT):
            try:
                print(self.api.get_capability(option))
            except RuntimeError as err:
                logger.error(err)

        return DeviceInfo(**params)


class DCAMAPI(Driver):
    api = None

    def __init__(self):
        if self.api is None:
            self.api = _DCAMAPI()

    ##

    async def initialize(self):
        try:
            self.api.init()
        except RuntimeError as err:
            if "No cameras" not in str(err):
                raise

    async def shutdown(self):
        self.api.uninit()

    async def enumerate_devices(self) -> HamamatsuCamera:
        valid_devices = []
        logger.debug(f"max index: {self.api.n_devices}")
        for i_device in range(self.api.n_devices):
            try:
                device = HamamatsuCamera(self, i_device)
                await device.test_open()
                valid_devices.append(device)
            except UnsupportedDeviceError:
                pass
        return tuple(valid_devices)

