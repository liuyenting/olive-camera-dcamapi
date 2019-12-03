import logging
from pprint import pprint
import trio

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
            t_exp = 10

            camera.set_exposure_time(t_exp)
            camera.set_roi(shape=(2048, 2048))

            frame = await camera.snap()
            print(f"captured size {frame.shape}, {frame.dtype}")
            imageio.imwrite("debug.tif", frame)
        finally:
            await camera.close()
    finally:
        await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
