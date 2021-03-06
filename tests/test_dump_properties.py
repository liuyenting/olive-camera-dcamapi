import logging
from pprint import pprint
import trio

import coloredlogs

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def dump_properties(camera):
    for name in await camera.enumerate_properties():
        print(f"{name} ({camera._get_property_id(name)}) = {camera.get_property(name)}")
        pprint(camera._get_property_attributes(name))
        print()


async def main():
    logger.info("starting driver")
    driver = DCAMAPI()

    try:
        logger.info("initializing")
        await driver.initialize()

        devices = await driver.enumerate_devices()
        pprint(devices)

        camera = devices[0]
        logger.info(f'select "{camera}"')
        try:
            await camera.open()
            await dump_properties(camera)
        finally:
            logger.info("closing")
            await camera.close()
    finally:
        logger.info("driver shutdown")
        await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
