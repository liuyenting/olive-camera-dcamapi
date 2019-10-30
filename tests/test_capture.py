import errno
import logging
import os
from pprint import pprint
from timeit import timeit

import coloredlogs
import imageio
import numpy as np
from vispy import app, scene

from olive.drivers.dcamapi import DCAMAPI

coloredlogs.install(
    level="DEBUG", fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
)

logger = logging.getLogger(__name__)

# init driver
driver = DCAMAPI()
driver.initialize()

# init viewer
canvas = scene.SceneCanvas(keys="interactive")
canvas.size = 768, 768

# create view and image
view = canvas.central_widget.add_view()

# lock view
view.camera = scene.PanZoomCamera(aspect=1, interactive=True)
view.camera.flip = (0, 1, 0)


def dump_properties(camera):
    # dump properties
    for name in camera.enumerate_properties():
        print(f"{name} ({camera._get_property_id(name)}) = {camera.get_property(name)}")
        pprint(camera._get_property_attributes(name))
        print()


try:
    devices = driver.enumerate_devices()
    pprint(devices)

    camera = devices[0]

    camera.open()
    canvas.title = str(camera.info)

    try:
        t_exp = 15

        camera.set_max_memory_size(1000 * (2 ** 20))  # 1000 MiB

        camera.set_exposure_time(t_exp)
        camera.set_roi(shape=(2048, 2048))

        # dump_properties(camera)

        if False:
            frame = camera.snap()
            print(f"captured size {frame.shape}, {frame.dtype}")
            imageio.imwrite("debug.tif", frame)
        elif True:
            try:
                os.mkdir("E:/_debug")
            except FileExistsError:
                pass

            n_frames = (10 * 1000) // t_exp
            # for i, frame in enumerate(camera.sequence(n_frames)):
            #    imageio.imwrite(os.path.join("E:/_debug", f"frame{i:05d}.tif"), frame)

            import asyncio

            async def grabber(camera, queue, n_frames):
                camera.configure_acquisition(n_frames)
                camera.start_acquisition()
                for i in range(n_frames):
                    await queue.put(camera.get_image(copy=False))
                camera.stop_acquisition()
                camera.unconfigure_acquisition()

            async def writer(queue):
                i = 0
                while True:
                    frame = await queue.get()
                    logger.info(f".. frame {i:05d}")
                    imageio.imwrite(
                        os.path.join("E:/_debug", f"frame{i:05d}.tif"), frame
                    )
                    i += 1
                    queue.task_done()

            async def run(n_frames):
                queue = asyncio.Queue()
                consumer = asyncio.ensure_future(writer(queue))
                await grabber(camera, queue, n_frames)
                await queue.join()
                consumer.cancel()

            loop = asyncio.get_event_loop()
            loop.run_until_complete(run(n_frames))
            loop.close()

        # image = scene.visuals.Image(frame, parent=view.scene, cmap="grays")
        # view.camera.set_range(margin=0)
    finally:
        camera.close()
finally:
    driver.shutdown()

# run loop
# canvas.show()
# app.run()
