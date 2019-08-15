from olive.drivers.dcamapi import GenericCamera

camera = GenericCamera()

from pprint import pprint
pprint(camera.enumerate_cameras())