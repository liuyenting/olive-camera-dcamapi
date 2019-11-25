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


async def acquire(t_exp=50, dst_dir='_debug'):
    try:
        os.mkdir(dst_dir)
    except FileExistsError:
        pass

    driver = DCAMAPI()

    try:
        await driver.initialize()

        devices = await driver.enumerate_devices()
        pprint(devices)

        camera = devices[0]
        await camera.open()

        try:
            camera.set_max_memory_size(2048 * (2 ** 20))  # 1000 MiB

            await camera.set_exposure_time(t_exp)
            await camera.set_roi(shape=(2048, 2048))

            n_frames = (60 * 1000) // t_exp

            async def grabber(camera, queue, n_frames):
                camera.start_acquisition()
                for i in range(n_frames):
                    logger.info(f".. read frame {i:05d}")
                    frame = camera.get_image(copy=False)
                    await queue.put((i, frame))
                    await trio.sleep(0)
                camera.stop_acquisition()

            async def writer(queue):
                while True:
                    i, frame = await queue.get()
                    logger.info(f".. write frame {i:05d}")
                    imageio.imwrite(
                        os.path.join(dst_dir, f"frame{i:05d}.tif"), frame
                    )
                    queue.task_done()
                    await trio.sleep(0)

            async def run(n_frames):
                queue = asyncio.Queue(maxsize=len(camera.buffer.frames) // 2)
                consumer = asyncio.ensure_future(writer(queue))
                await grabber(camera, queue, n_frames)
                await queue.join()
                consumer.cancel()

            camera.configure_acquisition(n_frames)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(run(n_frames))
            loop.close()

            camera.unconfigure_acquisition()

            # image = scene.visuals.Image(frame, parent=view.scene, cmap="grays")
            # view.camera.set_range(margin=0)
        finally:
            await camera.close()
    finally:
        await driver.shutdown()

    # run loop
    # canvas.show()
    # app.run()


async def viewer():
    # init viewer
    canvas = scene.SceneCanvas(keys="interactive")
    canvas.size = 768, 768

    # create view and image
    view = canvas.central_widget.add_view()

    # lock view
    view.camera = scene.PanZoomCamera(aspect=1, interactive=True)
    view.camera.flip = (0, 1, 0)

    canvas.show()


async def main():
    app.run()


if __name__ == "__main__":
    trio.run(main)
