from functools import partial
import logging
import re

from olive.core import Driver
from olive.devices import Camera

from .wrapper import DCAMAPI as _DCAMAPI


__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)


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

    def enumerate_devices(self):
        return self.api.n_devices

    ##

    def enumerate_attributes(self):
        pass

    def get_attribute(self, name):
        pass

    def set_attribute(self, name, value):
        pass

"""
class HamamatsuCamera(_DCAM, Camera):
    def __init__(self, driver):
        super().__init__()
        self._handle = DCAMAPI()

    # High level functions
    def enumerate_cameras(self):
        cameras = []
        for i in range(self.handle.n_devices):
            try:
                self.handle.open(i)
                self.handle.close()
            except RuntimeError:
                continue

            get_info = partial(self.handle.get_string, index=i)

            raw_sn = get_info(DCAM_IDSTR.DCAM_IDSTR_CAMERAID)
            params = {
                "version": get_info(DCAM_IDSTR.DCAM_IDSTR_DCAMAPIVERSION),
                "vendor": "Hamamatsu",
                "model": get_info(DCAM_IDSTR.DCAM_IDSTR_MODEL),
                "serial_number": re.match(r"S/N: (\d+)", raw_sn).group(1),
            }
            cameras.append(CameraInfo(**params))
        return cameras

    # Low level functions

    @property
    def handle(self):
        return self._handle
"""
