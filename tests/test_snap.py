import asyncio
import logging
from pprint import pprint

import coloredlogs
import imageio

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def main():
    driver = DCAMAPI()

    try:
        # initialize driver
        await driver.initialize()

        # enumerate and choose device
        devices = await driver.enumerate_devices()
        pprint(devices)

        camera = devices[0]
        await camera.open()

        try:
            # t_exp = 10

            props = await camera.enumerate_properties()

            props = {name: await camera.get_property(name) for name in props}
            pprint(props)

            # camera.set_exposure_time(t_exp)
            # camera.set_roi(shape=(1024, 1024))

            # frame = await camera.snap()
            # print(f"captured size {frame.shape}, {frame.dtype}")
            # imageio.imwrite("_debug.tif", frame)
        finally:
            await camera.close()
    finally:
        await driver.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
