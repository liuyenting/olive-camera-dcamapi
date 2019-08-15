from functools import partial
import logging
import re

from olive.devices import Camera, CameraInfo

from . import DCAMAPI
from .dcamapi import DCAM_IDSTR

class GenericCamera(Camera):
    def __init__(self):
        super().__init__()
        self._camera = DCAMAPI()

    # High level functions
    def enumerate_cameras(self):
        cameras = []
        for i in range(self.camera.n_devices):
            try:
                self.camera.open(i)
                self.camera.close()
            except RuntimeError:
                continue
            
            get_info = partial(self.camera.get_string, index=i)

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
    def camera(self):
        return self._camera