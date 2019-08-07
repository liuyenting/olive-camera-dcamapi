from olive.drivers.dcamapi import DCAMAPI as api
from olive.drivers.dcamapi.dcamapi4 import DCAM_IDSTR

camera = api()
camera.get_string(DCAM_IDSTR_MODEL)
