from olive.drivers.dcamapi import DCAMAPI

camera = DCAMAPI()

for i, sn in enumerate(camera.list_device_sn()):
    print('[{}] {}'.format(i, sn))

camera.uninit()
