import errno
import logging
import os
from pprint import pprint
from timeit import timeit
import trio

import coloredlogs
import imageio
import numpy as np
from vispy import app, scene

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def dump_properties(camera):
    for name in await camera.enumerate_properties():
        print(
            f"{name} ({camera._get_property_id(name)}) = {await camera.get_property(name)}"
        )
        pprint(camera._get_property_attributes(name))
        print()


async def main():
    driver = DCAMAPI()

    try:
        await driver.initialize()

        devices = await driver.enumerate_devices()
        pprint(devices)

        camera = devices[0]
        try:
            await camera.open()
            await dump_properties(camera)
        finally:
            await camera.close()
    finally:
        await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
