import os
import sys

PRGPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bCNC"))
sys.path.append(PRGPATH)
sys.path.append(os.path.join(PRGPATH, "lib"))
sys.path.append(os.path.join(PRGPATH, "plugins"))
sys.path.append(os.path.join(PRGPATH, "controllers"))
