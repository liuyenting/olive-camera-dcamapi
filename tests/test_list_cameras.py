from pprint import pprint

import coloredlogs

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)


driver = DCAMAPI()

driver.initialize()
try:
    devices = driver.enumerate_devices()
    pprint(devices)

    camera = devices[0]

    camera.open()
    try:
        pprint(camera.enumerate_properties())
    finally:
        camera.close()
finally:
    driver.shutdown()
