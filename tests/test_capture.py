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
image = scene.visuals.Image(
    np.zeros((2048, 2048), dtype=np.uint16),
    interpolation="nearest",
    parent=view.scene,
    cmap="grays",
)

# lock view
view.camera = scene.PanZoomCamera(aspect=1, interactive=True)
view.camera.flip = (0, 1, 0)

try:
    devices = driver.enumerate_devices()
    pprint(devices)

    camera = devices[0]

    camera.open()
    try:
        t_exp = camera.get_exposure_time()
        print(f'exposure time: {t_exp:04f} ms')

        camera.set_roi(shape=(512, 512))

        frame = camera.snap()
        imageio.imwrite('debug.tif', frame)

        #image.set_data(frame)
        #view.camera.set_range()
        #view.camera.zoom(1)
    finally:
        camera.close()
finally:
    driver.shutdown()

# run loop
#canvas.show()
#app.run()
