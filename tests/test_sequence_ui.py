import logging
import os
from pprint import pprint
import trio

import coloredlogs
import numpy as np
from vispy import app, scene

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def acquire(send_channel, camera, n_frames):
    await camera.configure_acquisition(n_frames)

    async with send_channel:
        camera.start_acquisition()
        for i in range(n_frames):
            logger.info(f".. read frame {i:05d}")
            frame = await camera.get_image(copy=False)
            await send_channel.send((i, frame))
        camera.stop_acquisition()

    await camera.unconfigure_acquisition()


async def viewer(receive_channel, shape):
    # init viewer
    canvas = scene.SceneCanvas(keys="interactive")
    canvas.size = 768, 768

    # create view and image
    view = canvas.central_widget.add_view()

    # lock view
    view.camera = scene.PanZoomCamera(aspect=1, interactive=True)
    view.camera.flip = (0, 1, 0)

    image = scene.visuals.Image(
        np.empty(shape, np.uint16), parent=view.scene, cmap="grays"
    )
    view.camera.set_range(margin=0)

    canvas.show()

    async with receive_channel:
        async for i, frame in receive_channel:
            logger.info(f".. show frame {i:05d}")
            frame = (frame - frame.min()) / (frame.max() - frame.min()) * 50000
            frame = frame.astype(np.uint16)
            image.set_data(frame)
            canvas.update()
            app.process_events()


async def main(dst_dir="_debug", t_exp=200, t_total=60, shape=(512, 512)):
    # create destination directory
    try:
        os.makedirs(dst_dir)
    except FileExistsError:
        pass

    # initialize driver
    driver = DCAMAPI()
    await driver.initialize()

    # enumerate cameras and select one
    cameras = await driver.enumerate_devices()
    pprint(cameras)
    camera = cameras[0]

    # open
    await camera.open()

    # pre-configure host-side
    camera.set_max_memory_size(2000 * (2 ** 20))  # 1000 MiB
    await camera.set_exposure_time(t_exp)
    await camera.set_roi(shape=shape)

    # total frames
    n_frames = (t_total * 1000) // t_exp

        # kick-off the acquisition
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(0)
        nursery.start_soon(viewer, receive_channel, shape)
        nursery.start_soon(acquire, send_channel, camera, n_frames)
        # nursery.start_soon(trio.to_thread.run_sync, app.process_events)

    # close and terminate
    await camera.close()
    await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
