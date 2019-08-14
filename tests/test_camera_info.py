from olive.drivers.dcamapi import DCAMAPI
from olive.drivers.dcamapi.dcamapi import DCAM_IDSTR

camera = DCAMAPI()

camera.open(sn='303026')

"""
queries = (
    DCAM_IDSTR.DCAM_IDSTR_MODEL,
    DCAM_IDSTR.DCAM_IDSTR_CAMERAID,
    DCAM_IDSTR.DCAM_IDSTR_BUS
)
for idstr in queries:
    print(camera.get_string(idstr))

camera.close()
"""

camera.uninit()
