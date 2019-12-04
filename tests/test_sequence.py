import logging
import os
from pprint import pprint
import trio

import coloredlogs
import imageio
from numcodecs import Blosc
import zarr

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def acquire(send_channel, camera, n_frames):
    async with send_channel:
        i = 0
        try:
            async for frame in camera.sequence(n_frames):
                await send_channel.send((i, frame))
                i += 1
        except IndexError as err:
            logger.error(str(err))
            return


async def writer(receive_channel, array):
    async with receive_channel:
        async for i, frame in receive_channel:
            logger.info(f".. acquired frame {i:05d}")
            array[i, ...] = frame


async def main(dst_dir="_debug", t_exp=20, t_total=60, shape=(2048, 2048)):
    try:
        # initialize driver
        driver = DCAMAPI()
        await driver.initialize()

        # enumerate cameras and select one
        cameras = await driver.enumerate_devices()
        pprint(cameras)
        assert len(cameras) > 0, "no camera"

        try:
            # open
            camera = cameras[0]
            await camera.open()

            # pre-configure host-side
            logger.debug("> set max memory size")
            camera.set_max_memory_size(2048 * (2 ** 20))  # 1000 MiB
            logger.debug("> set exposure time")
            camera.set_exposure_time(t_exp)
            logger.debug("> set roi")
            camera.set_roi(shape=shape)

            # total frames
            n_frames = (t_total * 1000) // t_exp

            # create storage
            logger.info("creating zarr storage")
            compressor = Blosc(cname="snappy")
            array = zarr.open(
                "_debug.zarr",
                mode="w",
                shape=(n_frames,) + shape,
                dtype=camera.get_dtype(),
                chunks=(1,) + shape,
                compressor=compressor,
            )
            print(array.info)

            # kick-off the acquisition
            async with trio.open_nursery() as nursery:
                send_channel, receive_channel = trio.open_memory_channel(0)
                nursery.start_soon(acquire, send_channel, camera, n_frames)
                nursery.start_soon(writer, receive_channel, array)

            # create destination directory
            try:
                os.makedirs(dst_dir)
            except FileExistsError:
                pass

            # translate
            for i, frame in enumerate(array):
                logger.info(f".. translate frame {i:05d}")
                imageio.imwrite(os.path.join(dst_dir, f"frmae_{i:05d}.tif"), frame)
        finally:
            await camera.close()
    finally:
        await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
