#!/usr/bin/env python3

import sys
from setuptools import find_namespace_packages, setup

if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
    print("ERROR: Python3.8 or newer is required to run bCNC!!")
    sys.exit(1)

print("Running bCNC setup...")

with open("README.md") as fh:
    long_description = fh.read()

setup(
    name="bCNC",
    version="1.0.0",
    license="GPL-2.0-only",
    description="Swiss army knife for all your CNC/g-code needs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(),
    author="Vasilis Vlachoudis",
    author_email="vvlachoudis@gmail.com",
    url="https://github.com/vlachoudis/bCNC",
    include_package_data=True,
    install_requires=[
        "pyobjc ; sys_platform == 'darwin'",
        "pyobjc-core; sys_platform == 'darwin'",
        "pyobjc-framework-Quartz; sys_platform == 'darwin'",
        # Windows XP can't handle pyserial newer than 3.0.1
        #   (it can be installed, but does not work)
        "pyserial>=3.5 ; sys_platform != 'win32'",
        "pyserial<=3.0.1 ; sys_platform == 'win32'",
        "numpy>=1.21",
        "svgelements>=1,<2",
        "shxparser>=0.0.2",
        "Pillow>=4.0",
        # No reliable PyPI wheels on classic 32-bit ARM (Raspberry Pi, etc.);
        # use the distro package there. aarch64 usually has wheels.
        "opencv-python>=4.10,<6 ; "
        + "platform_machine != 'armv6l' and "
        + "platform_machine != 'armv7l'",
        "tkinter-gl>=1.0",
        "PyOpenGL>=3.1",
        #"PyOpenGL_accelerate",
        "pyglm>=2.8.3"
    ],
    entry_points={
        "console_scripts": [
            "bCNC = bCNC.__main__:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",

        "Topic :: Multimedia :: Graphics :: 3D Modeling",
        "Topic :: Multimedia :: Graphics :: Capture",
        "Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Multimedia :: Graphics :: Viewers",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: Terminals :: Serial",
        "Natural Language :: Dutch",
        "Natural Language :: English",
        "Natural Language :: German",
        "Natural Language :: Spanish",
        "Natural Language :: Portuguese",
        "Natural Language :: Portuguese (Brazilian)",
        "Natural Language :: French",
        "Natural Language :: Italian",
        "Natural Language :: Japanese",
        "Natural Language :: Korean",
        "Natural Language :: Russian",
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: Chinese (Traditional)",
    ],
)
