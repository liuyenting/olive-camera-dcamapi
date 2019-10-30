import errno
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
        camera.set_max_memory_size(100 * (2 ** 20))  # 100 MiB

        camera.set_exposure_time(20)
        camera.set_roi(shape=(2048, 2048))

        # dump_properties(camera)

        if False:
            frame = camera.snap()
            print(f"captured size {frame.shape}, {frame.dtype}")
            imageio.imwrite("debug.tif", frame)
        elif True:
            frame = camera.sequence(100)
            print(f"captured size {frame.shape}, {frame.dtype}")
            try:
                os.mkdir("_debug")
            except FileExistsError:
                pass
            for i, _frame in enumerate(frame):
                imageio.imwrite(os.path.join("_debug", f"frame_{i:03d}.tif"), _frame)

        # image = scene.visuals.Image(frame, parent=view.scene, cmap="grays")
        # view.camera.set_range(margin=0)
    finally:
        camera.close()
finally:
    driver.shutdown()

# run loop
# canvas.show()
# app.run()
