from functools import partial
import logging
import re

from olive.core import Driver
from olive.devices import Camera

from olive.drivers.dcamapi.dcamapi import DCAMAPI as _DCAMAPI
from olive.drivers.dcamapi.dcamapi import DCAM as _DCAM
from olive.drivers.dcamapi.dcamapi import DCAM_IDSTR


__all__ = ["DCAMAPI", "HamamatsuCamera"]

logger = logging.getLogger(__name__)


class DCAMAPI(_DCAMAPI, Driver):
    def __init__(self):
        pass

    ##

    def initialize(self):
        pass

    def shutdown(self):
        pass

    def enumerate_devices(self):
        pass

    ##

    def enumerate_attributes(self):
        pass

    def get_attribute(self, name):
        pass

    def set_attribute(self, name, value):
        pass


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
