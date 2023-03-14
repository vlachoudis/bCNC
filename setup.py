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
    version="0.9.15",
    license="GPLv2",
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
        "pyserial ; sys_platform != 'win32'",
        "pyserial<=3.0.1 ; sys_platform == 'win32'",
        "numpy>=1.12",
        "svgelements>=1,<2",
        "shxparser>=0.0.2",
        "Pillow>=4.0",
        # Note there are no PyPI OpenCV packages for ARM
        # (Raspberry PI, Orange PI, etc...)
        "opencv-python==4.5.5.62 ; "
        + "(\"arm\" not in platform_machine) and "
        + "(\"aarch64\" not in platform_machine)"
    ],
    entry_points={
        "console_scripts": [
            "bCNC = bCNC.__main__:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
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
