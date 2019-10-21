from functools import partial
import logging
import re

from olive.core import Driver, DeviceInfo
from olive.devices import Camera
from olive.devices.errors import UnsupportedDeviceError

from .wrapper import DCAMAPI as _DCAMAPI
from .wrapper import DCAM, Info

__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)


class HamamatsuCamera(Camera):
    def __init__(self, driver, index):
        super().__init__(driver)
        self._index, self._api = index, None

    ##

    def test_open(self):
        try:
            handle = self.driver.api.open(self._index)
            self._api = DCAM(handle)
            logger.info(f".. {self.info()}")
        except RuntimeError:
            raise UnsupportedDeviceError
        finally:
            self.driver.api.close(self.api)
            self._api = None

    def open(self):
        handle = self.driver.api.open(self._index)
        self._api = DCAM(handle)

    def close(self):
        self.driver.api.close(self.api)
        self._api = None

    ##

    def info(self):
        raw_sn = self.api.get_string(Info.CameraID)
        params = {
            "version": self.api.get_string(Info.APIVersion),
            "vendor": self.api.get_string(Info.Vendor),
            "model": self.api.get_string(Info.Model),
            "serial_number": re.match(r"S/N: (\d+)", raw_sn).group(1),
        }
        return DeviceInfo(**params)

    def enumerate_properties(self):
        pass

    ##

    def snap(self):
        pass

    def configure_grab(self):
        pass

    def grab(self):
        pass

    def sequence(self):
        pass

    ##

    def configure_acquisition(self):
        pass

    def start_acquisition(self):
        pass

    def get_image(self):
        pass

    def stop_acquisition(self):
        pass

    def unconfigure_acquisition(self):
        pass

    ##

    @property
    def api(self):
        return self._api


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
        for i_device in range(self.api.n_devices):
            try:
                device = HamamatsuCamera(self, i_device)
                device.test_open()
                valid_devices.append(device)
            except UnsupportedDeviceError:
                pass
        return tuple(valid_devices)

