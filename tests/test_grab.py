import logging
import os
from pprint import pprint
import trio

import coloredlogs
from skimage import exposure, transform
import numpy as np
from vispy import app, scene

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)


async def acquire(send_channel, camera):
    await camera.configure_grab()
    async with send_channel:
        i = 0
        async for frame in camera.grab():
            logger.info(f".. tx frame {i:05d}")
            await send_channel.send((i, frame))
            i += 1


async def viewer(receive_channel, shape):
    display_shape = (512, 512)

    # init viewer
    canvas = scene.SceneCanvas(keys="interactive")
    canvas.size = display_shape

    # create view and image
    view = canvas.central_widget.add_view()

    # lock view
    view.camera = scene.PanZoomCamera(aspect=1, interactive=False)
    view.camera.flip = (0, 1, 0)

    image = scene.visuals.Image(
        np.empty(display_shape, np.uint16), parent=view.scene, cmap="grays"
    )
    view.camera.set_range(margin=0)

    canvas.show()

    async with receive_channel:
        async for i, frame in receive_channel:
            logger.info(f".. rx frame {i:05d}")

            logger.debug(f".... average {frame.mean():.2f}")

            # resize
            # frame = transform.resize(frame, display_shape)
            # rescale intensity to 8-bit
            # frame = exposure.rescale_intensity(frame, out_range=np.uint8)
            # change dtype
            # frame = frame.astype(np.uint8)

            # image.set_data(frame)


async def ui_event_loop():
    while True:
        await trio.sleep(0)
        app.process_events()


async def main(t_exp=30, shape=(512, 512)):
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
    camera.set_max_memory_size(1000 * (2 ** 20))  # 1000 MiB
    await camera.set_exposure_time(t_exp)
    await camera.set_roi(shape=shape)

    # kick-off the acquisition
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(0)
        nursery.start_soon(acquire, send_channel, camera)
        nursery.start_soon(viewer, receive_channel, shape)
        await ui_event_loop()

    # close and terminate
    await camera.close()
    await driver.shutdown()


if __name__ == "__main__":
    trio.run(main)
