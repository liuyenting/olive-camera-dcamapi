import os
from setuptools import Extension, setup

from Cython.Build import build_ext

NAME = "olive-camera-dcamapi"
VERSION = "0.1"
DESCRIPTION = "A small template project that shows how to wrap C/C++ code into python using Cython"
URL = "https://github.com/liuyenting/olive-camera-dcamapi"

# Trove classifiers
#   https://pypi.org/classifiers/
CLASSIFIERS = [
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: Microsoft :: Windows",
]
KEYWORDS = []

AUTHOR = "Liu, Yen-Ting"
EMAIL = "ytliu@gate.sinica.edu.tw"

REQUIRES = []

PACKAGES = ["olive.drivers.dcamapi"]

EXT_DEFS = [
    {
        "name": "olive.drivers.dcamapi.dcamapi",
        "language": "c++",
        "include_dirs": [
            "."  # "Module .pxd file not found next to .pyx file", https://github.com/cython/cython/issues/2452
        ],
        "extra_objects": ["lib/dcamapi.lib"],
    }
]

######################################################################################

cwd = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(cwd, "README.md"), encoding="utf-8") as fd:
    LONG_DESCRIPTION = fd.read()

# - install cython headers so other modules can cimport
# - force sdist to keep the .pyx files
PACKAGE_DATA = {pkg: ["*.pxd", "*.pyx"] for pkg in PACKAGES}

# generate extension constructors
def generate_extension(ext_def):
    assert "name" in ext_def, "invalid extension name"

    ext_path = ext_def["name"].replace(".", os.path.sep) + ".pyx"
    ext_root = os.path.dirname(ext_path)

    ext_def["sources"] = [ext_path]

    # prepend root directory
    arguments = (
        "include_dirs",
        "library_dirs",
        "runtime_library_dirs",
        "extra_objects",
    )
    for argument in arguments:
        try:
            ext_def[argument] = [
                os.path.join(ext_root, path) for path in ext_def[argument]
            ]
        except KeyError:
            # ignore unused argument
            pass

    return Extension(**ext_def)


EXTENSIONS = [generate_extension(ext_def) for ext_def in EXT_DEFS]

setup(
    """ Project Info """
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url=URL,
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    """ Author """
    author=AUTHOR,
    author_email=EMAIL,
    """ Dependencies """
    # use pyproject.toml for setup dependencies instead
    # setup_requires=[],remove
    install_requires=REQUIRES,
    """ Package Structure """
    # package to install
    packages=PACKAGES,
    namespace_packages=["olive", "olive.drivers"],
    package_data=PACKAGE_DATA,
    """ Build Instruction """
    cmdclass={"build_ext": build_ext},
    ext_modules=EXTENSIONS,
    # disable zip_safe
    #   - Cython cannot find .pxd files inside installed .egg
    #   - dynmaic loader may require library unzipped to a temporary directory at import time
    zip_safe=False,
)
