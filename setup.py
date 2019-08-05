from setuptools import setup, Extension
from Cython.Distutils import build_ext
import numpy as np

NAME = "olive-camera-dcamapi"
VERSION = "0.1"
DESCR = "A small template project that shows how to wrap C/C++ code into python using Cython"
URL = "http://www.google.com"
REQUIRES = ['numpy', 'cython']

AUTHOR = "Liu, Yen-Ting"
EMAIL = "ytliu@gate.sinica.edu.tw"

LICENSE = "Apache 2.0"

SRC_DIR = "olive-camera-dcamapi"
PACKAGES = [SRC_DIR]

ext_1 = Extension(
    "dcamapi",      
    [SRC_DIR + "/dcamapi4.pyx"],
    language='c',
    include_dirs=[np.get_include()],
    extra_objects=[SRC_DIR+'/lib/dcamapi.lib']
)

EXTENSIONS = [ext_1]

if __name__ == "__main__":
    setup(
        install_requires=REQUIRES,
        packages=PACKAGES,
        zip_safe=False,
        name=NAME,
        version=VERSION,
        description=DESCR,
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        license=LICENSE,
        cmdclass={"build_ext": build_ext},
        ext_modules=EXTENSIONS
    )
