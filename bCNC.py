#!/usr/bin/env python3

# This is loader script for bCNC, which can also be compiled to .exe

import os
import sys
import runpy

if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
    print("ERROR: Python3.8 or newer is required to run bCNC!!")
    exit(1)

print("This is currently broken. Use instead: python -m bCNC")


bcncpath = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "bCNC/__main__.py")

print(f"bCNC runpy loader: {bcncpath}")
runpy.run_path(bcncpath, run_name="__main__")
