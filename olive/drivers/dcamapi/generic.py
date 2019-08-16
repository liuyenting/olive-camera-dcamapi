from functools import partial
import logging
import re

from olive.devices import Camera, CameraInfo

from . import DCAMAPI
from .dcamapi import DCAM_IDSTR

class GenericCamera(Camera):
    def __init__(self):
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
                'version': get_info(DCAM_IDSTR.DCAM_IDSTR_DCAMAPIVERSION),
                'vendor': 'Hamamatsu',
                'model': get_info(DCAM_IDSTR.DCAM_IDSTR_MODEL), 
                'serial_number': re.match(r'S/N: (\d+)', raw_sn).group(1) 
            }
            cameras.append(CameraInfo(**params))
        return cameras
            
    # Low level functions

    @property
    def handle(self):
        return self._handle