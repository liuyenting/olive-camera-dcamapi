import asyncio
import logging
from pprint import pprint

import coloredlogs

from olive.core.managers import DriverManager
from olive.devices import Camera

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def run(device: Camera):
    try:
        await device.open()

        props = await device.enumerate_properties()
        pprint(props)
    finally:
        await device.close()


async def main():
    driver_mgmt = DriverManager()
    await driver_mgmt.refresh()

    cam_drivers = driver_mgmt.query_drivers(Camera)
    print(cam_drivers)

    cam_driver = cam_drivers[0]
    try:
        await cam_driver.initialize()
        cam_devices = await cam_driver.enumerate_devices()
        print(cam_devices)

        aom_device = cam_devices[0]
        await run(aom_device)
    finally:
        await cam_driver.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
