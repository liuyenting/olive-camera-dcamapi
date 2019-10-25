import ctypes
from functools import lru_cache
import logging
from multiprocessing import Array
import re

import numpy as np

from olive.core import Driver, DeviceInfo
from olive.devices import Camera
from olive.devices.errors import UnsupportedDeviceError

from .wrapper import DCAMAPI as _DCAMAPI
from .wrapper import DCAM, Event, Info, Capability, CaptureType, SubArray

__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)


class HamamatsuCamera(Camera):
    def __init__(self, driver, index):
        super().__init__(driver)
        self._index, self._api = index, None
        self._properties = dict()

        self._event = None

    ##

    def test_open(self):
        try:
            handle = self.driver.api.open(self._index)
            self._api = DCAM(handle)
            logger.info(f".. {self.info}")
        except RuntimeError as err:
            logger.exception(err)
            raise UnsupportedDeviceError
        finally:
            self.driver.api.close(self.api)
            self._api = None

    def open(self):
        handle = self.driver.api.open(self._index)
        self._api = DCAM(handle)

        # probe the camera
        self.enumerate_properties()

    def close(self):
        self.driver.api.close(self.api)
        self._api = None

    ##

    @lru_cache(maxsize=1)
    def enumerate_properties(self):
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
        if prop_type == "mode":
            # NOTE assuming uniform step
            index = int(self.api.get_value(prop_id)) - int(attributes["min"])
            return attributes["modes"][index]
        elif prop_type == "long":
            return int(self.api.get_value(prop_id))
        elif prop_type == "real":
            return float(self.api.get_value(prop_id))

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

    def snap(self):
        self.configure_acquisition(1)
        self.start_acquisition()

        frame = self.get_image()
        print(f"retrieved: {frame.shape}, {frame.dtype}")

        self.stop_acquisition()
        self.unconfigure_acquisition()

        return frame

    def configure_grab(self):
        pass

    def grab(self):
        pass

    def sequence(self, n_frames, out=None):
        self.configure_acquisition(n_frames)

    ##

    def configure_acquisition(self, buf_nframes, continuous=False, fallback=False):
        _, (ny, nx) = self.get_roi()
        nbytes = (nx * ny) * 2

        buffer = []
        for _ in range(buf_nframes):
            buffer.append(Array(ctypes.c_uint8, nbytes))

        self.api.attach(buffer)
        self._buffer = buffer
        logger.debug("buffer ALLOCATED")

        self._event = self.api.event
        self._event.open()

    def _attach_external_buffer(self):
        pass

    def _request_internal_buffer(self, buf_nframes):
        self.api.alloc(buf_nframes)

    def start_acquisition(self):
        # TODO setup camera status

        self.api.start(CaptureType.Snap)
        logger.debug("acquisition STARTED")

    def get_image(self):
        self._event.start(Event.FrameReady)
        # return self.api.lock_frame().copy()
        return np.frombuffer(self.buffer[0].get_obj(), dtype=np.uint16).reshape(
            self.get_roi()[1]
        )

    def stop_acquisition(self):
        self._event.start(Event.Stopped)
        logger.debug("acquisition STOPPED")

    def unconfigure_acquisition(self):
        self._event.close()
        self._event = None

        self.api.release()
        logger.debug("buffer RELEASED")

    ##

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
        pos0 = self.get_property("subarray_vpos"), self.get_property("subarray_hpos")
        shape = self.get_property("subarray_vsize"), self.get_property("subarray_hsize")
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
            desc = 'initial position'
            if pos0 is None:
                if shape is None:
                    # full sensor range, disable sub-array mode, nothing to do
                    return
                else:
                    # centered
                    pos0 = [(ms - s) // 2 for ms, s in zip(max_shape, shape)]
                    desc = 'inferred ' + desc
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
            logger.warning('revert back to previous ROI...')
            self.set_roi(pos0=prev_pos0, shape=prev_shape)
            raise

    ##

    @property
    def api(self):
        return self._api

    @property
    def busy(self):
        return False

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

    def initialize(self):
        self.api.init()

    def shutdown(self):
        self.api.uninit()

    def enumerate_devices(self) -> HamamatsuCamera:
        valid_devices = []
        logger.debug(f"max index: {self.api.n_devices}")
        for i_device in range(self.api.n_devices):
            try:
                device = HamamatsuCamera(self, i_device)
                device.test_open()
                valid_devices.append(device)
            except UnsupportedDeviceError:
                pass
        return tuple(valid_devices)

