import os
import sys

# Shared bootstrap for headless unit tests (controllers, cam, cnc, …)
UNITTESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if UNITTESTS_DIR not in sys.path:
    sys.path.insert(0, UNITTESTS_DIR)

PRGPATH = os.path.abspath(os.path.join(UNITTESTS_DIR, "..", "bCNC"))
for path in (
    PRGPATH,
    os.path.join(PRGPATH, "lib"),
    os.path.join(PRGPATH, "plugins"),
    os.path.join(PRGPATH, "controllers"),
):
    if path not in sys.path:
        sys.path.append(path)

import Utils
