# $Id: CNC.py,v 1.8 2014/10/15 15:03:49 bnv Exp $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math
import os
import re
import types

import undo
import Unicode
from bmath import (
    solveOverDetermined,
    sqrt,
    atan2,
    cos,
    sin,
    Matrix,
    Vector,
)
from bpath import Path, Segment
from bstl import Binary_STL_Writer
from dxf import DXF
from svgcode import SVGcode
from Helpers import to_zip

IDPAT = re.compile(r".*\bid:\s*(.*?)\)")
PARENPAT = re.compile(r"(\(.*?\))")
SEMIPAT = re.compile(r"(;.*)")
OPPAT = re.compile(r"(.*)\[(.*)\]")
CMDPAT = re.compile(r"([A-Za-z]+)")
BLOCKPAT = re.compile(r"^\(Block-([A-Za-z]+):\s*(.*)\)")
AUXPAT = re.compile(r"^(%[A-Za-z0-9]+)\b *(.*)$")

STOP = 0
SKIP = 1
ASK = 2
MSG = 3
WAIT = 4
UPDATE = 5

XY = 0
XZ = 1
YZ = 2

CW = 2
CCW = 3

WCS = ["G54", "G55", "G56", "G57", "G58", "G59"]

DISTANCE_MODE = {"G90": "Absolute", "G91": "Incremental"}
FEED_MODE = {"G93": "1/Time", "G94": "unit/min", "G95": "unit/rev"}
UNITS = {"G20": "inch", "G21": "mm"}
PLANE = {"G17": "XY", "G18": "XZ", "G19": "YZ"}

# Modal Mode from $G and variable set
MODAL_MODES = {
    "G0": "motion",
    "G1": "motion",
    "G2": "motion",
    "G3": "motion",
    "G38.2": "motion",
    "G38.3": "motion",
    "G38.4": "motion",
    "G38.5": "motion",
    "G80": "motion",
    "G54": "WCS",
    "G55": "WCS",
    "G56": "WCS",
    "G57": "WCS",
    "G58": "WCS",
    "G59": "WCS",
    "G17": "plane",
    "G18": "plane",
    "G19": "plane",
    "G90": "distance",
    "G91": "distance",
    "G91.1": "arc",
    "G93": "feedmode",
    "G94": "feedmode",
    "G95": "feedmode",
    "G20": "units",
    "G21": "units",
    "G40": "cutter",
    "G43.1": "tlo",
    "G49": "tlo",
    "M0": "program",
    "M1": "program",
    "M2": "program",
    "M30": "program",
    "M3": "spindle",
    "M4": "spindle",
    "M5": "spindle",
    "M7": "coolant",
    "M8": "coolant",
    "M9": "coolant",
}

ERROR_HANDLING = {}
TOLERANCE = 1e-7
MAXINT = 1000000000  # python3 doesn't have maxint


# -----------------------------------------------------------------------------
# Return a value combined from two dictionaries new/old
# -----------------------------------------------------------------------------
def getValue(name, new, old, default=0.0):
    try:
        return new[name]
    except Exception:
        try:
            return old[name]
        except Exception:
            return default


# =============================================================================
# Probing class and linear interpolation
# =============================================================================
class Probe:
    def __init__(self):
        self.init()

    # ----------------------------------------------------------------------
    def init(self):
        self.filename = ""
        self.xmin = 0.0
        self.ymin = 0.0
        self.zmin = -10.0

        self.xmax = 10.0
        self.ymax = 10.0
        self.zmax = 3.0

        self._xstep = 1.0
        self._ystep = 1.0

        self.xn = 5
        self.yn = 5

        self.points = []  # probe points
        self.matrix = []  # 2D matrix with Z coordinates
        self.zeroed = False  # if probe was zeroed at any location
        self.start = False  # start collecting probes
        self.saved = False

    # ----------------------------------------------------------------------
    def clear(self):
        del self.points[:]
        del self.matrix[:]
        self.zeroed = False
        self.start = False
        self.saved = False

    # ----------------------------------------------------------------------
    def isEmpty(self):
        return len(self.matrix) == 0

    # ----------------------------------------------------------------------
    def makeMatrix(self):
        del self.matrix[:]
        for j in range(self.yn):
            self.matrix.append([0.0] * (self.xn))

    # ----------------------------------------------------------------------
    # Load autolevel information from file
    # ----------------------------------------------------------------------
    def load(self, filename=None):
        if filename is not None:
            self.filename = filename
        self.clear()
        self.saved = True

        def read(f):
            while True:
                line = f.readline()
                assert line, "Read an empty line, please check file IO settings"
                line = line.strip()
                if line:
                    return map(float, line.split())

        f = open(self.filename)
        self.xmin, self.xmax, self.xn = read(f)
        self.ymin, self.ymax, self.yn = read(f)
        self.zmin, self.zmax, feed = read(f)
        CNC.vars["prbfeed"] = feed

        self.xn = max(2, int(self.xn))
        self.yn = max(2, int(self.yn))

        self.makeMatrix()
        self.xstep()
        self.ystep()

        self.start = True
        try:
            for j in range(self.yn):
                for i in range(self.xn):
                    self.add(*read(f))
        except Exception:
            raise
        f.close()

    # ----------------------------------------------------------------------
    # Save level information to file
    # ----------------------------------------------------------------------
    def save(self, filename=None):
        if filename is None:
            filename = self.filename

        fn, ext = os.path.splitext(filename)
        ext = ext.lower()

        f = open(filename, "w")
        if ext != ".xyz":
            self.filename = filename
            f.write(f"{self.xmin:g} {self.xmax:g} {int(self.xn)}\n")
            f.write(f"{self.ymin:g} {self.ymax:g} {int(self.yn)}\n")
            f.write(f"{self.zmin:g} {self.zmax:g} {CNC.vars['prbfeed']:g}\n")
            f.write("\n\n")
        for j in range(self.yn):
            y = self.ymin + self._ystep * j
            for i in range(self.xn):
                x = self.xmin + self._xstep * i
                f.write(f"{x:g} {y:g} {self.matrix[j][i]:g}\n")
            f.write("\n")
        f.close()
        self.saved = True

    # ----------------------------------------------------------------------
    # Save level information as STL file
    # ----------------------------------------------------------------------
    def saveAsSTL(self, filename=None):
        if filename is not None:
            self.filename = filename

        with open(self.filename, "wb") as fp:
            writer = Binary_STL_Writer(fp)
            for j in range(self.yn - 1):
                y1 = self.ymin + self._ystep * j
                y2 = self.ymin + self._ystep * (j + 1)
                for i in range(self.xn - 1):
                    x1 = self.xmin + self._xstep * i
                    x2 = self.xmin + self._xstep * (i + 1)
                    v1 = [x1, y1, self.matrix[j][i]]
                    v2 = [x2, y1, self.matrix[j][i + 1]]
                    v3 = [x2, y2, self.matrix[j + 1][i + 1]]
                    v4 = [x1, y2, self.matrix[j + 1][i]]
                    writer.add_face([v1, v2, v3, v4])
            writer.close()

    # ----------------------------------------------------------------------
    # Return step
    # ----------------------------------------------------------------------
    def xstep(self):
        self._xstep = (self.xmax - self.xmin) / float(self.xn - 1)
        return self._xstep

    # ----------------------------------------------------------------------
    def ystep(self):
        self._ystep = (self.ymax - self.ymin) / float(self.yn - 1)
        return self._ystep

    # ----------------------------------------------------------------------
    # Return the code needed to scan margins for autoleveling
    # ----------------------------------------------------------------------
    def scanMargins(self):
        lines = []
        lines.append(f"G0 X{self.xmin:.4f} Y{self.ymin:.4f}")
        lines.append(f"G0 X{self.xmin:.4f} Y{self.ymax:.4f}")
        lines.append(f"G0 X{self.xmax:.4f} Y{self.ymax:.4f}")
        lines.append(f"G0 X{self.xmax:.4f} Y{self.ymin:.4f}")
        lines.append(f"G0 X{self.xmin:.4f} Y{self.ymin:.4f}")
        return lines

    # ----------------------------------------------------------------------
    # Return the code needed to scan for autoleveling
    # ----------------------------------------------------------------------
    def scan(self):
        self.clear()
        self.start = True
        self.makeMatrix()
        x = self.xmin
        xstep = self._xstep
        lines = [
            f"G0Z{CNC.vars['safe']:.4f}",
            f"G0X{self.xmin:.4f}Y{self.ymin:.4f}",
        ]
        for j in range(self.yn):
            y = self.ymin + self._ystep * j
            for i in range(self.xn):
                lines.append(f"G0Z{self.zmax:.4f}")
                lines.append(f"G0X{x:.4f}Y{y:.4f}")
                lines.append("%wait")  # added for smoothie
                lines.append(
                    f"{CNC.vars['prbcmd']}Z{self.zmin:.4f}"
                    f"F{CNC.vars['prbfeed']:g}"
                )
                lines.append("%wait")  # added for smoothie
                x += xstep
            x -= xstep
            xstep = -xstep
        lines.append(f"G0Z{self.zmax:.4f}")
        lines.append(f"G0X{self.xmin:.4f}Y{self.ymin:.4f}")
        return lines

    # ----------------------------------------------------------------------
    # Add a probed point to the list and the 3D matrix
    # ----------------------------------------------------------------------
    def add(self, x, y, z):
        if not self.start:
            return
        i = round((x - self.xmin) / self._xstep)
        if i < 0.0 or i > self.xn:
            return

        j = round((y - self.ymin) / self._ystep)
        if j < 0.0 or j > self.yn:
            return

        rem = abs(x - (i * self._xstep + self.xmin))
        if rem > self._xstep / 10.0:
            return

        rem = abs(y - (j * self._ystep + self.ymin))
        if rem > self._ystep / 10.0:
            return

        try:
            self.matrix[int(j)][int(i)] = z
            self.points.append([x, y, z])
        except IndexError:
            pass

        if len(self.points) >= self.xn * self.yn:
            self.start = False

    # ----------------------------------------------------------------------
    # Make z-level relative to the location of (x,y,0)
    # ----------------------------------------------------------------------
    def setZero(self, x, y):
        del self.points[:]
        if self.isEmpty():
            self.zeroed = False
            return
        zero = self.interpolate(x, y)
        self.xstep()
        self.ystep()
        for j, row in enumerate(self.matrix):
            y = self.ymin + self._ystep * j
            for i in range(len(row)):
                x = self.xmin + self._xstep * i
                row[i] -= zero
                self.points.append([x, y, row[i]])
        self.zeroed = True

    # ----------------------------------------------------------------------
    def interpolate(self, x, y):
        ix = (x - self.xmin) / self._xstep
        jy = (y - self.ymin) / self._ystep
        i = int(math.floor(ix))
        j = int(math.floor(jy))

        if i < 0:
            i = 0
        elif i >= self.xn - 1:
            i = self.xn - 2

        if j < 0:
            j = 0
        elif j >= self.yn - 1:
            j = self.yn - 2

        a = ix - i
        b = jy - j
        a1 = 1.0 - a
        b1 = 1.0 - b

        return (
            a1 * b1 * self.matrix[j][i]
            + a1 * b * self.matrix[j + 1][i]
            + a * b1 * self.matrix[j][i + 1]
            + a * b * self.matrix[j + 1][i + 1]
        )

    # ----------------------------------------------------------------------
    # Split line into multiple segments correcting for Z if needed
    # return only end points
    # ----------------------------------------------------------------------
    def splitLine(self, x1, y1, z1, x2, y2, z2):
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1

        if abs(dx) < 1e-10:
            dx = 0.0
        if abs(dy) < 1e-10:
            dy = 0.0
        if abs(dz) < 1e-10:
            dz = 0.0

        if dx == 0.0 and dy == 0.0:
            return [(x2, y2, z2 + self.interpolate(x2, y2))]

        # Length along projection on X-Y plane
        rxy = math.sqrt(dx * dx + dy * dy)
        dx /= rxy  # direction cosines along XY plane
        dy /= rxy
        dz /= rxy  # add correction for the slope in Z, versus the travel in XY

        i = int(math.floor((x1 - self.xmin) / self._xstep))
        j = int(math.floor((y1 - self.ymin) / self._ystep))
        if dx > 1e-10:
            tx = (
                float(i + 1) * self._xstep + self.xmin - x1
            ) / dx  # distance to next cell
            tdx = self._xstep / dx
        elif dx < -1e-10:
            # distance to next cell
            tx = (float(i) * self._xstep + self.xmin - x1) / dx
            tdx = -self._xstep / dx
        else:
            tx = 1e10
            tdx = 0.0

        if dy > 1e-10:
            ty = (
                float(j + 1) * self._ystep + self.ymin - y1
            ) / dy  # distance to next cell
            tdy = self._ystep / dy
        elif dy < -1e-10:
            # distance to next cell
            ty = (float(j) * self._ystep + self.ymin - y1) / dy
            tdy = -self._ystep / dy
        else:
            ty = 1e10
            tdy = 0.0

        segments = []
        rxy *= 0.999999999  # just reduce a bit to avoid precision errors
        while tx < rxy or ty < rxy:
            if tx == ty:
                t = tx
                tx += tdx
                ty += tdy
            elif tx < ty:
                t = tx
                tx += tdx
            else:
                t = ty
                ty += tdy
            x = x1 + t * dx
            y = y1 + t * dy
            z = z1 + t * dz
            segments.append((x, y, z + self.interpolate(x, y)))

        segments.append((x2, y2, z2 + self.interpolate(x2, y2)))
        return segments


# =============================================================================
# contains a list of machine points vs position in the gcode
# calculates the transformation matrix (rotation + translation) needed
# to adjust the gcode to match the workpiece on the machine
# =============================================================================
class Orient:
    # -----------------------------------------------------------------------
    def __init__(self):
        self.markers = []  # list of points pairs (xm, ym, x, y)
        self.paths = []
        self.errors = []
        self.filename = ""
        self.clear()

    # -----------------------------------------------------------------------
    def clear(self, item=None):
        if item is None:
            self.clearPaths()
            del self.markers[:]
        else:
            del self.paths[item]
            del self.markers[item]

        self.phi = 0.0
        self.xo = 0.0
        self.yo = 0.0
        self.valid = False
        self.saved = False

    # -----------------------------------------------------------------------
    def clearPaths(self):
        del self.paths[:]

    # -----------------------------------------------------------------------
    def add(self, xm, ym, x, y):
        self.markers.append((xm, ym, x, y))
        self.valid = False
        self.saved = False

    # -----------------------------------------------------------------------
    def addPath(self, path):
        self.paths.append(path)

    # -----------------------------------------------------------------------
    def __getitem__(self, i):
        return self.markers[i]

    # -----------------------------------------------------------------------
    def __len__(self):
        return len(self.markers)

    # -----------------------------------------------------------------------
    # Return the rotation angle phi in radians and the offset (xo,yo)
    # or none on failure
    # Transformation equation is the following
    #
    #    Xm = R * X + T
    #
    #    Xm = [xm ym]^t
    #    X  = [x y]^t
    #
    #
    #       / cosf  -sinf \   / c  -s \
    #   R = |             | = |       |
    #       \ sinf   cosf /   \ s   c /
    #
    # Assuming that the machine is squared. We could even solve it for
    # a skewed machine, but then the arcs have to be converted to
    # ellipses...
    #
    #   T = [xo yo]^t
    #
    # The overdetermined system (equations) to solve are the following
    #      c*x + s*(-y) + xo      = xm
    #      s*x + c*y    + yo      = ym
    #  <=> c*y + s*y         + yo = ym
    #
    # We are solving for the unknowns c,s,xo,yo
    #
    #       /  x1  -y1  1 0 \ / c  \    / xm1 \
    #       |  y1   x1  0 1 | | s  |    | ym1 |
    #       |  x2  -y2  1 0 | | xo |    | xm2 |
    #       |  y2   x2  0 1 | \ yo /  = | ym2 |
    #          ...                   ..
    #       |  xn  -yn  1 0 |           | xmn |
    #       \  yn   xn  0 1 /           \ ymn /
    #
    #               A            X    =    B
    #
    # Constraints:
    #   1. orthogonal system   c^2 + s^2 = 1
    #   2. no aspect ratio
    #
    # -----------------------------------------------------------------------
    def solve(self):
        self.valid = False
        if len(self.markers) < 2:
            raise Exception("Too few markers")
        A = []
        B = []
        for xm, ym, x, y in self.markers:
            A.append([x, -y, 1.0, 0.0])
            B.append([xm])
            A.append([y, x, 0.0, 1.0])
            B.append([ym])

        # The solution of the overdetermined system A X = B
        try:
            c, s, self.xo, self.yo = solveOverDetermined(Matrix(A), Matrix(B))
        except Exception:
            raise Exception("Unable to solve system")

        # Normalize the coefficients
        r = sqrt(c * c + s * s)  # length should be 1.0
        if abs(r - 1.0) > 0.1:
            raise Exception("Resulting system is too skew")

        self.phi = atan2(s, c)

        if abs(self.phi) < TOLERANCE:
            self.phi = 0.0  # rotation

        self.valid = True
        return self.phi, self.xo, self.yo

    # -----------------------------------------------------------------------
    # @return minimum, average and maximum error
    # -----------------------------------------------------------------------
    def error(self):
        # Type errors
        minerr = 1e9
        maxerr = 0.0
        sumerr = 0.0

        c = cos(self.phi)
        s = sin(self.phi)

        del self.errors[:]

        for i, (xm, ym, x, y) in enumerate(self.markers):
            dx = c * x - s * y + self.xo - xm
            dy = s * x + c * y + self.yo - ym
            err = sqrt(dx**2 + dy**2)
            self.errors.append(err)

            minerr = min(minerr, err)
            maxerr = max(maxerr, err)
            sumerr += err

        return minerr, sumerr / float(len(self.markers)), maxerr

    # -----------------------------------------------------------------------
    # Convert gcode to machine coordinates
    # -----------------------------------------------------------------------
    def gcode2machine(self, x, y):
        c = cos(self.phi)
        s = sin(self.phi)
        return c * x - s * y + self.xo, s * x + c * y + self.yo

    # -----------------------------------------------------------------------
    # Convert machine to gcode coordinates
    # -----------------------------------------------------------------------
    def machine2gcode(self, x, y):
        c = cos(self.phi)
        s = sin(self.phi)
        x -= self.xo
        y -= self.yo
        return c * x + s * y, -s * x + c * y

    # ----------------------------------------------------------------------
    # Load orient information from file
    # ----------------------------------------------------------------------
    def load(self, filename=None):
        if filename is not None:
            self.filename = filename
        self.clear()
        self.saved = True

        f = open(self.filename)
        for line in f:
            self.add(*map(float, line.split()))
        f.close()

    # ----------------------------------------------------------------------
    # Save orient information to file
    # ----------------------------------------------------------------------
    def save(self, filename=None):
        if filename is not None:
            self.filename = filename
        f = open(self.filename, "w")
        for xm, ym, x, y in self.markers:
            f.write(f"{xm:g} {ym:g} {x:g} {y:g}\n")
        f.close()
        self.saved = True


# =============================================================================
# Command operations on a CNC
# =============================================================================
class CNC:
    inch = False
    lasercutter = False
    laseradaptive = False
    acceleration_x = 25.0  # mm/s^2
    acceleration_y = 25.0  # mm/s^2
    acceleration_z = 25.0  # mm/s^2
    feedmax_x = 3000
    feedmax_y = 3000
    feedmax_z = 2000
    travel_x = 300
    travel_y = 300
    travel_z = 60
    accuracy = 0.01  # sagitta error during arc conversion
    digits = 4
    startup = "G90"
    stdexpr = False  # standard way of defining expressions with []
    comment = ""  # last parsed comment
    developer = False
    drozeropad = 0
    vars = {
        "prbx": 0.0,
        "prby": 0.0,
        "prbz": 0.0,
        "prbcmd": "G38.2",
        "prbfeed": 10.0,
        "errline": "",
        "wx": 0.0,
        "wy": 0.0,
        "wz": 0.0,
        "wa": 0.0,
        "wb": 0.0,
        "wc": 0.0,
        "mx": 0.0,
        "my": 0.0,
        "mz": 0.0,
        "ma": 0.0,
        "mb": 0.0,
        "mc": 0.0,
        "wcox": 0.0,
        "wcoy": 0.0,
        "wcoz": 0.0,
        "wcoa": 0.0,
        "wcob": 0.0,
        "wcoc": 0.0,
        "curfeed": 0.0,
        "curspindle": 0.0,
        "_camwx": 0.0,
        "_camwy": 0.0,
        "G": [],
        "TLO": 0.0,
        "motion": "G0",
        "WCS": "G54",
        "plane": "G17",
        "feedmode": "G94",
        "distance": "G90",
        "arc": "G91.1",
        "units": "G20",
        "cutter": "",
        "tlo": "",
        "program": "M0",
        "spindle": "M5",
        "coolant": "M9",
        "tool": 0,
        "feed": 0.0,
        "rpm": 0.0,
        "planner": 0,
        "rxbytes": 0,
        "OvFeed": 100,  # Override status
        "OvRapid": 100,
        "OvSpindle": 100,
        "_OvChanged": False,
        "_OvFeed": 100,  # Override target values
        "_OvRapid": 100,
        "_OvSpindle": 100,
        "diameter": 3.175,  # Tool diameter
        "cutfeed": 1000.0,  # Material feed for cutting
        "cutfeedz": 500.0,  # Material feed for cutting
        "safe": 3.0,
        "state": "",
        "pins": "",
        "msg": "",
        "stepz": 1.0,
        "surface": 0.0,
        "thickness": 5.0,
        "stepover": 40.0,
        "PRB": None,
        "TLO": 0.0,
        "version": "",
        "controller": "",
        "running": False,
        # "enable6axisopt" : 0,
    }

    drillPolicy = 1  # Expand Canned cycles
    toolPolicy = 1  # Should be in sync with ProbePage
    # 0 - send to grbl
    # 1 - skip those lines
    # 2 - manual tool change (WCS)
    # 3 - manual tool change (TLO)
    # 4 - manual tool change (No Probe)

    toolWaitAfterProbe = True  # wait at tool change position after probing
    appendFeed = False  # append feed on every G1/G2/G3 commands to be used
    # for feed override testing
    # FIXME will not be needed after Grbl v1.0

    # ----------------------------------------------------------------------
    def __init__(self):
        self.initPath()
        self.resetAllMargins()

    # ----------------------------------------------------------------------
    # Update G variables from "G" string
    # ----------------------------------------------------------------------
    @staticmethod
    def updateG():
        for g in CNC.vars["G"]:
            if g[0] == "F":
                CNC.vars["feed"] = float(g[1:])
            elif g[0] == "S":
                CNC.vars["rpm"] = float(g[1:])
            elif g[0] == "T":
                CNC.vars["tool"] = int(g[1:])
            else:
                var = MODAL_MODES.get(g)
                if var is not None:
                    CNC.vars[var] = g

    # ----------------------------------------------------------------------
    def __getitem__(self, name):
        return CNC.vars[name]

    # ----------------------------------------------------------------------
    def __setitem__(self, name, value):
        CNC.vars[name] = value

    # ----------------------------------------------------------------------
    @staticmethod
    def loadConfig(config):
        section = "CNC"
        try:
            CNC.inch = bool(int(config.get(section, "units")))
        except Exception:
            pass
        try:
            CNC.lasercutter = bool(int(config.get(section, "lasercutter")))
        except Exception:
            pass
        try:
            CNC.laseradaptive = bool(int(config.get(section, "laseradaptive")))
        except Exception:
            pass
        try:
            CNC.enable6axisopt = bool(int(
                config.get(section, "enable6axisopt")))
        except Exception:
            pass
        try:
            CNC.doublesizeicon = bool(int(
                config.get(section, "doublesizeicon")))
        except Exception:
            pass
        try:
            CNC.acceleration_x = float(config.get(section, "acceleration_x"))
        except Exception:
            pass
        try:
            CNC.acceleration_y = float(config.get(section, "acceleration_y"))
        except Exception:
            pass
        try:
            CNC.acceleration_z = float(config.get(section, "acceleration_z"))
        except Exception:
            pass
        try:
            CNC.feedmax_x = float(config.get(section, "feedmax_x"))
        except Exception:
            pass
        try:
            CNC.feedmax_y = float(config.get(section, "feedmax_y"))
        except Exception:
            pass
        try:
            CNC.feedmax_z = float(config.get(section, "feedmax_z"))
        except Exception:
            pass
        try:
            CNC.travel_x = float(config.get(section, "travel_x"))
        except Exception:
            pass
        try:
            CNC.travel_y = float(config.get(section, "travel_y"))
        except Exception:
            pass
        try:
            CNC.travel_z = float(config.get(section, "travel_z"))
        except Exception:
            pass
        try:
            CNC.acceleration_a = float(config.get(section, "acceleration_a"))
        except Exception:
            pass
        try:
            CNC.acceleration_b = float(config.get(section, "acceleration_b"))
        except Exception:
            pass
        try:
            CNC.acceleration_c = float(config.get(section, "acceleration_c"))
        except Exception:
            pass
        try:
            CNC.feedmax_a = float(config.get(section, "feedmax_a"))
        except Exception:
            pass
        try:
            CNC.feedmax_b = float(config.get(section, "feedmax_b"))
        except Exception:
            pass
        try:
            CNC.feedmax_c = float(config.get(section, "feedmax_c"))
        except Exception:
            pass
        try:
            CNC.travel_a = float(config.get(section, "travel_a"))
        except Exception:
            pass
        try:
            CNC.travel_b = float(config.get(section, "travel_b"))
        except Exception:
            pass
        try:
            CNC.travel_c = float(config.get(section, "travel_c"))
        except Exception:
            pass
        try:
            CNC.accuracy = float(config.get(section, "accuracy"))
        except Exception:
            pass
        try:
            CNC.digits = int(config.get(section, "round"))
        except Exception:
            pass
        try:
            CNC.drozeropad = int(config.get(section, "drozeropad"))
        except Exception:
            pass

        try:
            CNC.startup = config.get(section, "startup")
        except Exception:
            pass
        try:
            CNC.header = config.get(section, "header")
        except Exception:
            pass
        try:
            CNC.footer = config.get(section, "footer")
        except Exception:
            pass

        if CNC.inch:
            CNC.acceleration_x /= 25.4
            CNC.acceleration_y /= 25.4
            CNC.acceleration_z /= 25.4
            CNC.feedmax_x /= 25.4
            CNC.feedmax_y /= 25.4
            CNC.feedmax_z /= 25.4
            CNC.travel_x /= 25.4
            CNC.travel_y /= 25.4
            CNC.travel_z /= 25.4
            # a,b,c are in degrees no conversion required

        section = "Error"
        if CNC.drillPolicy == 1:
            ERROR_HANDLING["G98"] = 1
            ERROR_HANDLING["G99"] = 1

        for cmd, value in config.items(section):
            try:
                ERROR_HANDLING[cmd.upper()] = int(value)
            except Exception:
                pass

    # ----------------------------------------------------------------------
    @staticmethod
    def saveConfig(config):
        pass

    # ----------------------------------------------------------------------
    def initPath(self, x=None, y=None, z=None, a=None, b=None, c=None):
        if x is None:
            self.x = self.xval = CNC.vars["wx"] or 0
        else:
            self.x = self.xval = x
        if y is None:
            self.y = self.yval = CNC.vars["wy"] or 0
        else:
            self.y = self.yval = y
        if z is None:
            self.z = self.zval = CNC.vars["wz"] or 0
        else:
            self.z = self.zval = z
        if a is None:
            self.a = self.aval = CNC.vars["wa"] or 0
        else:
            self.a = self.aval = a
        if b is None:
            self.b = self.bval = CNC.vars["wb"] or 0
        else:
            self.b = self.bval = b
        if c is None:
            self.c = self.cval = CNC.vars["wc"] or 0
        else:
            self.c = self.cval = c

        self.ival = self.jval = self.kval = 0.0
        self.uval = self.vval = self.wval = 0.0
        self.dx = self.dy = self.dz = 0.0
        self.di = self.dj = self.dk = 0.0
        self.rval = 0.0
        self.pval = 0.0
        self.qval = 0.0
        self.unit = 1.0
        self.mval = 0
        self.lval = 1
        self.tool = 0
        self._lastTool = None

        self.absolute = True  # G90/G91     absolute/relative motion
        self.arcabsolute = False  # G90.1/G91.1 absolute/relative arc
        self.retractz = True  # G98/G99     retract to Z or R
        self.gcode = None
        self.plane = XY
        self.feed = 0  # Actual gcode feed rate (not to confuse with cutfeed
        self.totalLength = 0.0
        self.totalTime = 0.0

    # ----------------------------------------------------------------------
    def resetEnableMargins(self):
        # Selected blocks margin
        CNC.vars["xmin"] = CNC.vars["ymin"] = CNC.vars["zmin"] = 1000000.0
        CNC.vars["xmax"] = CNC.vars["ymax"] = CNC.vars["zmax"] = -1000000.0

    # ----------------------------------------------------------------------
    def resetAllMargins(self):
        self.resetEnableMargins()
        # All blocks margin
        CNC.vars["axmin"] = CNC.vars["aymin"] = CNC.vars["azmin"] = 1000000.0
        CNC.vars["axmax"] = CNC.vars["aymax"] = CNC.vars["azmax"] = -1000000.0

    # ----------------------------------------------------------------------
    @staticmethod
    def isMarginValid():
        return (
            CNC.vars["xmin"] <= CNC.vars["xmax"]
            and CNC.vars["ymin"] <= CNC.vars["ymax"]
            and CNC.vars["zmin"] <= CNC.vars["zmax"]
        )

    # ----------------------------------------------------------------------
    @staticmethod
    def isAllMarginValid():
        return (
            CNC.vars["axmin"] <= CNC.vars["axmax"]
            and CNC.vars["aymin"] <= CNC.vars["aymax"]
            and CNC.vars["azmin"] <= CNC.vars["azmax"]
        )

    # ----------------------------------------------------------------------
    # Number formatting
    # ----------------------------------------------------------------------
    @staticmethod
    def fmt(c, v, d=None):
        if d is None:
            d = CNC.digits
        # Don't know why, but in some cases floats are not truncated by
        # format string unless rounded
        # I guess it's vital idea to round them rather than truncate anyway!
        v = round(v, d)
        return (f"{c}{v:>{d}f}").rstrip("0").rstrip(".")

    # ----------------------------------------------------------------------
    @staticmethod
    def gcode(g, pairs):
        s = f"g{int(g)}"
        for c, v in pairs:
            s += f" {c[0]}{round(v, CNC.digits):g}"
        return s

    # ----------------------------------------------------------------------
    @staticmethod
    def _gcode(g, **args):
        s = f"g{int(g)}"
        for n, v in args.items():
            s += " " + CNC.fmt(n, v)
        return s

    # ----------------------------------------------------------------------
    @staticmethod
    def _gotoABC(g, x=None, y=None, z=None, a=None, b=None, c=None, **args):
        s = f"g{int(g)}"
        if x is not None:
            s += " " + CNC.fmt("x", x)
        if y is not None:
            s += " " + CNC.fmt("y", y)
        if z is not None:
            s += " " + CNC.fmt("z", z)
        if a is not None:
            s += " " + CNC.fmt("a", a)
        if b is not None:
            s += " " + CNC.fmt("b", b)
        if c is not None:
            s += " " + CNC.fmt("c", c)
        for n, v in args.items():
            s += " " + CNC.fmt(n, v)
        return s

    @staticmethod
    def _goto(g, x=None, y=None, z=None, **args):
        s = f"g{int(g)}"
        if x is not None:
            s += " " + CNC.fmt("x", x)
        if y is not None:
            s += " " + CNC.fmt("y", y)
        if z is not None:
            s += " " + CNC.fmt("z", z)
        for n, v in args.items():
            s += " " + CNC.fmt(n, v)
        return s

    # ----------------------------------------------------------------------
    @staticmethod
    def grapidABC(x=None, y=None, z=None, a=None, b=None, c=None, **args):
        return CNC._gotoABC(0, x, y, z, a, b, c, **args)

    @staticmethod
    def grapid(x=None, y=None, z=None, **args):
        return CNC._goto(0, x, y, z, **args)

    # ----------------------------------------------------------------------
    @staticmethod
    def glineABC(x=None, y=None, z=None, a=None, b=None, c=None, **args):
        return CNC._gotoABC(1, x, y, z, a, b, c, **args)

    @staticmethod
    def gline(x=None, y=None, z=None, **args):
        return CNC._goto(1, x, y, z, **args)

    # ----------------------------------------------------------------------
    @staticmethod
    def glinev(g, v, feed=None):
        pairs = to_zip("xyz", v)
        if feed is not None:
            pairs.append(("f", feed))
        return CNC.gcode(g, pairs)

    # ----------------------------------------------------------------------
    @staticmethod
    def garcv(g, v, ijk):
        return CNC.gcode(g, to_zip("xyz", v) + to_zip("ij", ijk[:2]))

    # ----------------------------------------------------------------------
    @staticmethod
    def garc(g, x=None, y=None, z=None, i=None, j=None, k=None, **args):
        s = f"g{int(g)}"
        if x is not None:
            s += " " + CNC.fmt("x", x)
        if y is not None:
            s += " " + CNC.fmt("y", y)
        if z is not None:
            s += " " + CNC.fmt("z", z)
        if i is not None:
            s += " " + CNC.fmt("i", i)
        if j is not None:
            s += " " + CNC.fmt("j", j)
        if k is not None:
            s += " " + CNC.fmt("k", k)
        for n, v in args.items():
            s += " " + CNC.fmt(n, v)
        return s

    # ----------------------------------------------------------------------
    # Enter to material or start the laser
    # ----------------------------------------------------------------------
    @staticmethod
    def zenter(z, d=None):
        if CNC.lasercutter:
            if CNC.laseradaptive:
                return "m4"
            else:
                return "m3"
        else:
            return (f"g1 {CNC.fmt('z', z, d)} "
                    f"{CNC.fmt('f', CNC.vars['cutfeedz'])}")

    # ----------------------------------------------------------------------
    @staticmethod
    def zexit(z, d=None):
        if CNC.lasercutter:
            return "m5"
        else:
            return f"g0 {CNC.fmt('z', z, d)}"

    # ----------------------------------------------------------------------
    # gcode to go to z-safe
    # Exit from material or stop the laser
    # ----------------------------------------------------------------------
    @staticmethod
    def zsafe():
        return CNC.zexit(CNC.vars["safe"])

    # ----------------------------------------------------------------------
    # @return line in broken a list of commands, None if empty or comment
    # ----------------------------------------------------------------------
    @staticmethod
    def parseLine(line):
        # skip empty lines
        if len(line) == 0 or line[0] in ("%", "(", "#", ";"):
            return None

        # remove comments
        line = PARENPAT.sub("", line)
        line = SEMIPAT.sub("", line)

        # process command
        # strip all spaces
        line = line.replace(" ", "")

        # Insert space before each command
        line = CMDPAT.sub(r" \1", line).lstrip()
        return line.split()

    # ----------------------------------------------------------------------
    # @return line,comment
    #   line broken in a list of commands,
    #       None,"" if empty or comment
    #       else compiled expressions,""
    # ----------------------------------------------------------------------
    @staticmethod
    def compileLine(line, space=False):
        line = line.strip()
        if not line:
            return None
        if line[0] == "$":
            return line

        # to accept #nnn variables as _nnn internally
        line = line.replace("#", "_")
        CNC.comment = ""

        # execute literally the line after the first character
        if line[0] == "%":
            # special command
            pat = AUXPAT.match(line.strip())
            if pat:
                cmd = pat.group(1)
                args = pat.group(2)
            else:
                cmd = None
                args = None
            if cmd == "%wait":
                return (WAIT,)
            elif cmd == "%msg":
                if not args:
                    args = None
                return (MSG, args)
            elif cmd == "%update":
                return (UPDATE, args)
            elif line.startswith("%if running") and not CNC.vars["running"]:
                # ignore if running lines when not running
                return None
            else:
                try:
                    return compile(line[1:], "", "exec")
                except Exception as e:
                    print("Compile line error: \n")
                    print(e)
                    return None

        # most probably an assignment like  #nnn = expr
        if line[0] == "_":
            try:
                return compile(line, "", "exec")
            except Exception:
                # FIXME show the error!!!!
                return None

        # commented line
        if line[0] == ";":
            CNC.comment = line[1:].strip()
            return None

        out = []  # output list of commands
        bracket = 0  # bracket count []
        paren = 0  # parenthesis count ()
        expr = ""  # expression string
        cmd = ""  # cmd string
        inComment = False  # inside inComment
        for i, ch in enumerate(line):
            if ch == "(":
                # comment start?
                paren += 1
                inComment = bracket == 0
                if not inComment:
                    expr += ch
            elif ch == ")":
                # comment end?
                paren -= 1
                if not inComment:
                    expr += ch
                if paren == 0 and inComment:
                    inComment = False
            elif ch == "[":
                # expression start?
                if not inComment:
                    if CNC.stdexpr:
                        ch = "("
                    bracket += 1
                    if bracket == 1:
                        if cmd:
                            out.append(cmd)
                            cmd = ""
                    else:
                        expr += ch
                else:
                    CNC.comment += ch
            elif ch == "]":
                # expression end?
                if not inComment:
                    if CNC.stdexpr:
                        ch = ")"
                    bracket -= 1
                    if bracket == 0:
                        try:
                            out.append(compile(expr, "", "eval"))
                        except Exception:
                            # FIXME show the error!!!!
                            pass
                        expr = ""
                    else:
                        expr += ch
                else:
                    CNC.comment += ch
            elif ch == "=":
                # check for assignments (FIXME very bad)
                if not out and bracket == 0 and paren == 0:
                    for i in " ()-+*/^$":
                        if i in cmd:
                            cmd += ch
                            break
                    else:
                        try:
                            return compile(line, "", "exec")
                        except Exception:
                            # FIXME show the error!!!!
                            return None
            elif ch == ";":
                # Skip everything after the semicolon on normal lines
                if not inComment and paren == 0 and bracket == 0:
                    CNC.comment += line[i + 1:]
                    break
                else:
                    expr += ch

            elif bracket > 0:
                expr += ch

            elif not inComment:
                if ch == " ":
                    if space:
                        cmd += ch
                else:
                    cmd += ch

            elif inComment:
                CNC.comment += ch

        if cmd:
            out.append(cmd)

        # return output commands
        if len(out) == 0:
            return None
        if len(out) > 1:
            return out
        return out[0]

    # ----------------------------------------------------------------------
    # Break line into commands
    # ----------------------------------------------------------------------
    @staticmethod
    def breakLine(line):
        if line is None:
            return None
        # Insert space before each command
        line = CMDPAT.sub(r" \1", line).lstrip()
        return line.split()

    # ----------------------------------------------------------------------
    # Create path for one g command
    # ----------------------------------------------------------------------
    def motionStart(self, cmds):
        self.mval = 0  # reset m command
        for cmd in cmds:
            c = cmd[0].upper()
            try:
                value = float(cmd[1:])
            except Exception:
                value = 0

            if c == "X":
                self.xval = value * self.unit
                if not self.absolute:
                    self.xval += self.x
                self.dx = self.xval - self.x

            elif c == "Y":
                self.yval = value * self.unit
                if not self.absolute:
                    self.yval += self.y
                self.dy = self.yval - self.y

            elif c == "Z":
                self.zval = value * self.unit
                if not self.absolute:
                    self.zval += self.z
                self.dz = self.zval - self.z

            elif c == "A":
                self.aval = value * self.unit

            elif c == "F":
                self.feed = value * self.unit

            elif c == "G":
                gcode = int(value)
                decimal = int(round((value - gcode) * 10))

                # Execute immediately
                if gcode in (4, 10, 53):
                    pass  # do nothing but don't record to motion
                elif gcode == 17:
                    self.plane = XY

                elif gcode == 18:
                    self.plane = XZ

                elif gcode == 19:
                    self.plane = YZ

                elif gcode == 20:  # Switch to inches
                    if CNC.inch:
                        self.unit = 1.0
                    else:
                        self.unit = 25.4

                elif gcode == 21:  # Switch to mm
                    if CNC.inch:
                        self.unit = 1.0 / 25.4
                    else:
                        self.unit = 1.0

                elif gcode == 80:
                    # turn off canned cycles
                    self.gcode = None
                    self.dz = 0
                    self.zval = self.z

                elif gcode == 90:
                    if decimal == 0:
                        self.absolute = True
                    elif decimal == 1:
                        self.arcabsolute = True

                elif gcode == 91:
                    if decimal == 0:
                        self.absolute = False
                    elif decimal == 1:
                        self.arcabsolute = False

                elif gcode in (93, 94, 95):
                    CNC.vars["feedmode"] = gcode

                elif gcode == 98:
                    self.retractz = True

                elif gcode == 99:
                    self.retractz = False

                else:
                    self.gcode = gcode

            elif c == "I":
                self.ival = value * self.unit
                if self.arcabsolute:
                    self.ival -= self.x

            elif c == "J":
                self.jval = value * self.unit
                if self.arcabsolute:
                    self.jval -= self.y

            elif c == "K":
                self.kval = value * self.unit
                if self.arcabsolute:
                    self.kval -= self.z

            elif c == "L":
                self.lval = int(value)

            elif c == "M":
                self.mval = int(value)

            elif c == "N":
                pass

            elif c == "P":
                self.pval = value

            elif c == "Q":
                self.qval = value * self.unit

            elif c == "R":
                self.rval = value * self.unit

            elif c == "T":
                self.tool = int(value)

            elif c == "U":
                self.uval = value * self.unit

            elif c == "V":
                self.vval = value * self.unit

            elif c == "W":
                self.wval = value * self.unit

    # ----------------------------------------------------------------------
    # Return center x,y,z,r for arc motions 2,3 and set self.rval
    # ----------------------------------------------------------------------
    def motionCenter(self):
        if self.rval > 0.0:
            if self.plane == XY:
                x = self.x
                y = self.y
                xv = self.xval
                yv = self.yval
            elif self.plane == XZ:
                x = self.x
                y = self.z
                xv = self.xval
                yv = self.zval
            else:
                x = self.y
                y = self.z
                xv = self.yval
                yv = self.zval

            ABx = xv - x
            ABy = yv - y
            Cx = 0.5 * (x + xv)
            Cy = 0.5 * (y + yv)
            AB = math.sqrt(ABx**2 + ABy**2)
            try:
                OC = math.sqrt(self.rval**2 - AB**2 / 4.0)
            except Exception:
                OC = 0.0
            if self.gcode == 2:
                OC = -OC  # CW
            if AB != 0.0:
                return Cx - OC * ABy / AB, Cy + OC * ABx / AB
            else:
                # Error!!!
                return x, y
        else:
            # Center
            xc = self.x + self.ival
            yc = self.y + self.jval
            zc = self.z + self.kval
            self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)

            if self.plane == XY:
                return xc, yc
            elif self.plane == XZ:
                return xc, zc
            else:
                return yc, zc

    # ----------------------------------------------------------------------
    # Create path for one g command
    # ----------------------------------------------------------------------
    def motionPath(self):
        xyz = []

        # Execute g-code
        if self.gcode in (0, 1):  # fast move or line
            if (
                self.xval - self.x != 0.0
                or self.yval - self.y != 0.0
                or self.zval - self.z != 0.0
            ):
                xyz.append((self.x, self.y, self.z))
                xyz.append((self.xval, self.yval, self.zval))

        elif self.gcode in (2, 3):  # CW=2,CCW=3 circle
            xyz.append((self.x, self.y, self.z))
            uc, vc = self.motionCenter()

            gcode = self.gcode
            if self.plane == XY:
                u0 = self.x
                v0 = self.y
                w0 = self.z
                u1 = self.xval
                v1 = self.yval
                w1 = self.zval
            elif self.plane == XZ:
                u0 = self.x
                v0 = self.z
                w0 = self.y
                u1 = self.xval
                v1 = self.zval
                w1 = self.yval
                gcode = 5 - gcode  # flip 2-3 when XZ plane is used
            else:
                u0 = self.y
                v0 = self.z
                w0 = self.x
                u1 = self.yval
                v1 = self.zval
                w1 = self.xval
            phi0 = math.atan2(v0 - vc, u0 - uc)
            phi1 = math.atan2(v1 - vc, u1 - uc)
            try:
                sagitta = 1.0 - CNC.accuracy / self.rval
            except ZeroDivisionError:
                sagitta = 0.0
            if sagitta > 0.0:
                df = 2.0 * math.acos(sagitta)
                df = min(df, math.pi / 4.0)
            else:
                df = math.pi / 4.0

            if gcode == 2:
                if phi1 >= phi0 - 1e-10:
                    phi1 -= 2.0 * math.pi
                ws = (w1 - w0) / (phi1 - phi0)
                phi = phi0 - df
                while phi > phi1:
                    u = uc + self.rval * math.cos(phi)
                    v = vc + self.rval * math.sin(phi)
                    w = w0 + (phi - phi0) * ws
                    phi -= df
                    if self.plane == XY:
                        xyz.append((u, v, w))
                    elif self.plane == XZ:
                        xyz.append((u, w, v))
                    else:
                        xyz.append((w, u, v))
            else:
                if phi1 <= phi0 + 1e-10:
                    phi1 += 2.0 * math.pi
                ws = (w1 - w0) / (phi1 - phi0)
                phi = phi0 + df
                while phi < phi1:
                    u = uc + self.rval * math.cos(phi)
                    v = vc + self.rval * math.sin(phi)
                    w = w0 + (phi - phi0) * ws
                    phi += df
                    if self.plane == XY:
                        xyz.append((u, v, w))
                    elif self.plane == XZ:
                        xyz.append((u, w, v))
                    else:
                        xyz.append((w, u, v))

            xyz.append((self.xval, self.yval, self.zval))

        elif self.gcode == 4:  # Dwell
            self.totalTime = self.pval

        elif self.gcode in (81, 82, 83, 85, 86, 89):  # Canned cycles
            # FIXME Assuming only on plane XY
            if self.absolute:
                # FIXME is it correct?
                self.lval = 1
                if self.retractz:
                    clearz = max(self.rval, self.z)
                else:
                    clearz = self.rval
                drill = self.zval
            else:
                clearz = self.z + self.rval
                drill = clearz + self.dz

            x, y, z = self.x, self.y, self.z
            xyz.append((x, y, z))
            if z != clearz:
                z = clearz
                xyz.append((x, y, z))
            for _line in range(self.lval):
                # Rapid move parallel to XY
                x += self.dx
                y += self.dy
                xyz.append((x, y, z))

                # Rapid move parallel to clearz
                if self.z > clearz:
                    xyz.append((x, y, clearz))

                # Drill to z
                xyz.append((x, y, drill))

                # Move to original position
                z = clearz
                xyz.append((x, y, z))  # ???

        return xyz

    # ----------------------------------------------------------------------
    # move to end position
    # ----------------------------------------------------------------------
    def motionEnd(self):
        if self.gcode in (0, 1, 2, 3):
            self.x = self.xval
            self.y = self.yval
            self.z = self.zval
            self.dx = 0
            self.dy = 0
            self.dz = 0

            if self.gcode >= 2:  # reset at the end
                self.rval = self.ival = self.jval = self.kval = 0.0

        elif self.gcode in (28, 30, 92):
            self.x = 0.0
            self.y = 0.0
            self.z = 0.0
            self.dx = 0
            self.dy = 0
            self.dz = 0

        # FIXME L is not taken into account for repetitions!!!
        elif self.gcode in (81, 82, 83):
            # FIXME Assuming only on plane XY
            if self.absolute:
                self.lval = 1
                if self.retractz:
                    retract = max(self.rval, self.z)
                else:
                    retract = self.rval
                drill = self.zval
            else:
                retract = self.z + self.rval
                drill = retract + self.dz

            self.x += self.dx * self.lval
            self.y += self.dy * self.lval
            self.z = retract

            self.xval = self.x
            self.yval = self.y
            self.dx = 0
            self.dy = 0
            self.dz = drill - retract

    # ----------------------------------------------------------------------
    # Doesn't work correctly for G83 (peck drilling)
    # ----------------------------------------------------------------------
    def pathLength(self, block, xyz):
        # For XY plane
        p = xyz[0]
        length = 0.0
        for i in xyz:
            length += math.sqrt(
                (i[0] - p[0]) ** 2 + (i[1] - p[1]) ** 2 + (i[2] - p[2]) ** 2
            )
            p = i

        if self.gcode == 0:
            # FIXME calculate the correct time with the feed direction
            # and acceleration
            block.time += length / self.feedmax_x
            self.totalTime += length / self.feedmax_x
            block.rapid += length
        elif ((self.gcode == 1 or self.gcode == 2 or self.gcode == 3)
              and self.feed > 0):
            block.time += length / self.feed
            self.totalTime += length / self.feed
        else:
            try:
                if CNC.vars["feedmode"] == 94:
                    # Normal mode
                    t = length / self.feed
                elif CNC.vars["feedmode"] == 93:
                    # Inverse mode
                    t = length * self.feed
                block.time += t
                self.totalTime += t
            except Exception:
                pass
            block.length += length

        self.totalLength += length

    # ----------------------------------------------------------------------
    def pathMargins(self, block):
        if block.enable:
            CNC.vars["xmin"] = min(CNC.vars["xmin"], block.xmin)
            CNC.vars["ymin"] = min(CNC.vars["ymin"], block.ymin)
            CNC.vars["zmin"] = min(CNC.vars["zmin"], block.zmin)
            CNC.vars["xmax"] = max(CNC.vars["xmax"], block.xmax)
            CNC.vars["ymax"] = max(CNC.vars["ymax"], block.ymax)
            CNC.vars["zmax"] = max(CNC.vars["zmax"], block.zmax)

        CNC.vars["axmin"] = min(CNC.vars["axmin"], block.xmin)
        CNC.vars["aymin"] = min(CNC.vars["aymin"], block.ymin)
        CNC.vars["azmin"] = min(CNC.vars["azmin"], block.zmin)
        CNC.vars["axmax"] = max(CNC.vars["axmax"], block.xmax)
        CNC.vars["aymax"] = max(CNC.vars["aymax"], block.ymax)
        CNC.vars["azmax"] = max(CNC.vars["azmax"], block.zmax)

    # ----------------------------------------------------------------------
    # Instead of the current code, override with the custom user lines
    # @param program a list of lines to execute
    # @return the new list of lines
    # ----------------------------------------------------------------------
    @staticmethod
    def compile(program):
        lines = []
        for j, line in enumerate(program):
            newcmd = []
            cmds = CNC.compileLine(line)
            if cmds is None:
                continue
            if isinstance(cmds, str):
                cmds = CNC.breakLine(cmds)
            else:
                # either CodeType or tuple, list[] append it as is
                lines.append(cmds)
                continue

            for cmd in cmds:
                c = cmd[0]
                try:
                    value = float(cmd[1:])
                except Exception:
                    value = 0.0
                if c.upper() in ("F", "X", "Y", "Z", "I", "J", "K", "R", "P"):
                    cmd = CNC.fmt(c, value)
                else:
                    opt = ERROR_HANDLING.get(cmd.upper(), 0)
                    if opt == SKIP:
                        cmd = None

                if cmd is not None:
                    newcmd.append(cmd)
            lines.append("".join(newcmd))
        return lines

    # ----------------------------------------------------------------------
    # code to change manually tool
    # ----------------------------------------------------------------------
    def toolChange(self, tool=None):
        if tool is not None:
            # Force a change
            self.tool = tool
            self._lastTool = None

        # check if it is the same tool
        if self.tool is None or self.tool == self._lastTool:
            return []

        # create the necessary code
        lines = []
        # remember state and populate variables,
        # FIXME: move to ./controllers/_GenericController.py
        lines.append(
            "$g"
        )
        lines.append("m5")  # stop spindle
        lines.append("%wait")
        lines.append("%_x,_y,_z = wx,wy,wz")  # remember position
        lines.append("g53 g0 z[toolchangez]")
        lines.append("g53 g0 x[toolchangex] y[toolchangey]")
        lines.append("%wait")

        if CNC.comment:
            lines.append(
                f"%msg Tool change T{int(self.tool):02} ({CNC.comment})")
        else:
            lines.append(f"%msg Tool change T{int(self.tool):02}")
        lines.append("m0")  # feed hold

        if CNC.toolPolicy < 4:
            lines.append("g53 g0 x[toolprobex] y[toolprobey]")
            lines.append("g53 g0 z[toolprobez]")

            # fixed WCS
            if CNC.vars["fastprbfeed"]:
                prb_reverse = {"2": "4", "3": "5", "4": "2", "5": "3"}
                CNC.vars["prbcmdreverse"] = (
                    CNC.vars["prbcmd"][:-1]
                    + prb_reverse[CNC.vars["prbcmd"][-1]]
                )
                currentFeedrate = CNC.vars["fastprbfeed"]
                while currentFeedrate > CNC.vars["prbfeed"]:
                    lines.append("%wait")
                    lines.append(
                        f"g91 [prbcmd] {CNC.fmt('f', currentFeedrate)} "
                        f"z[toolprobez-mz-tooldistance]"
                    )
                    lines.append("%wait")
                    lines.append(
                        f"[prbcmdreverse] {CNC.fmt('f', currentFeedrate)} "
                        f"z[toolprobez-mz]"
                    )
                    currentFeedrate /= 10
            lines.append("%wait")
            lines.append(
                "g91 [prbcmd] f[prbfeed] z[toolprobez-mz-tooldistance]")

            if CNC.toolPolicy == 2:
                # Adjust the current WCS to fit to the tool
                # FIXME could be done dynamically in the code
                p = WCS.index(CNC.vars["WCS"]) + 1
                lines.append(f"g10l20p{int(p)} z[toolheight]")
                lines.append("%wait")

            elif CNC.toolPolicy == 3:
                # Modify the tool length, update the TLO
                lines.append("g4 p1")  # wait a sec to get the probe info
                lines.append("%wait")
                lines.append("%global TLO; TLO=prbz-toolmz")
                lines.append("g43.1z[TLO]")
                lines.append("%update TLO")

            lines.append("g53 g0 z[toolchangez]")
            lines.append("g53 g0 x[toolchangex] y[toolchangey]")

        if CNC.toolWaitAfterProbe:
            lines.append("%wait")
            lines.append("%msg Restart spindle")
            lines.append("m0")  # feed hold

        # restore state
        lines.append("g90")  # restore mode
        lines.append("g0 x[_x] y[_y]")  # ... x,y position
        lines.append("g0 z[_z]")  # ... z position
        lines.append("f[feed] [spindle]")  # ... feed and spindle
        lines.append("g4 p5")  # wait 5s for spindle to speed up

        # remember present tool
        self._lastTool = self.tool
        return lines

    # ----------------------------------------------------------------------
    # code to expand G80-G89 macro code - canned cycles
    # example:
    # code to expand G83 code - peck drilling cycle
    # format:   (G98 / G99 opt.) G83 X~ Y~ Z~ A~ R~ L~ Q~
    # example:  N150 G98 G83 Z-1.202 R18. Q10. F50.
    #           ...
    #           G80
    # Notes: G98, G99, Z, R, Q, F are unordered parameters
    # ----------------------------------------------------------------------
    def macroGroupG8X(self):
        lines = []
        # FIXME Assuming only on plane XY
        if self.absolute:
            # FIXME is it correct?
            self.lval = 1
            if self.retractz:
                clearz = max(self.rval, self.z)
            else:
                clearz = self.rval
            drill = self.zval
            retract = self.rval
        else:
            clearz = self.z + self.rval
            retract = clearz
            drill = clearz + self.dz

        if self.gcode == 83:  # peck drilling
            peck = self.qval
        else:
            peck = 100000.0  # a large value

        x, y, z = self.x, self.y, self.z
        if z < clearz:
            z = clearz
            lines.append(CNC.grapid(z=z / self.unit))

        for _line in range(self.lval):
            # Rapid move parallel to XY
            x += self.dx
            y += self.dy
            lines.append(CNC.grapid(x / self.unit, y / self.unit))

            # Rapid move parallel to retract
            zstep = max(drill, retract - peck)
            while z > drill:
                if z != retract:
                    z = retract
                    lines.append(CNC.grapid(z=z / self.unit))

                z = max(drill, zstep)
                zstep -= peck

                # Drill to z
                lines.append(
                    CNC.gline(z=z / self.unit, f=self.feed / self.unit))

            # 82=dwell, 86=boring-stop, 89=boring-dwell
            if self.gcode in (82, 86, 89):
                lines.append(CNC._gcode(4, p=self.pval))

                if self.gcode == 86:
                    lines.append("M5")  # stop spindle???

            # Move to original position
            if self.gcode in (85, 89):  # boring cycle
                z = retract
                lines.append(
                    CNC.gline(z=z / self.unit, f=self.feed / self.unit))

            z = clearz
            lines.append(CNC.grapid(z=z / self.unit))

            if self.gcode == 86:
                lines.append("M3")  # restart spindle???
        return lines


# =============================================================================
# Block of g-code commands. A gcode file is represented as a list of blocks
# - Commands are grouped as (non motion commands Mxxx)
# - Basic shape from the first rapid move command to the last rapid z raise
#   above the working surface
#
# Inherits from list and contains:
#   - a list list of gcode lines
#   - (imported shape)
# =============================================================================
class Block(list):
    def __init__(self, name=None):
        # Copy constructor
        if isinstance(name, Block):
            self.copy(name)
            return
        self._name = name
        self.enable = True  # Enabled/Visible in drawing
        self.expand = False  # Expand in editor
        self.color = None  # Custom color for path
        self._path = []  # canvas drawing paths
        self.sx = self.sy = self.sz = 0  # start  coordinates
        # (entry point first non rapid motion)
        self.ex = self.ey = self.ez = 0  # ending coordinates
        self.resetPath()

    # ----------------------------------------------------------------------
    def copy(self, src):
        self._name = src._name
        self.enable = src.enable
        self.expand = src.expand
        self.color = src.color
        self[:] = src[:]
        self._path = []
        self.sx = src.sx
        self.sy = src.sy
        self.sz = src.sz
        self.ex = src.ex
        self.ey = src.ey
        self.ez = src.ez

    # ----------------------------------------------------------------------
    def name(self):
        return self._name is None and "block" or self._name

    # ----------------------------------------------------------------------
    # @return name without the operation
    # ----------------------------------------------------------------------
    def nameNop(self):
        name = self.name()
        pat = OPPAT.match(name)
        if pat is None:
            return name
        else:
            return pat.group(1).strip()

    # ----------------------------------------------------------------------
    # Tests if block contains operation type
    # ----------------------------------------------------------------------
    def operationTest(self, op, name=None):
        if name is None:
            name = self.name()
        pat = OPPAT.match(name)
        if pat is not None:
            ops = pat.group(2)
            ops = re.split(r"\W+", ops)
            if op in ops:
                return True
        return False

    # ----------------------------------------------------------------------
    # Get block operation value
    # ----------------------------------------------------------------------
    def operationGet(self, op, name=None):
        if name is None:
            name = self.name()
        pat = OPPAT.match(name)
        if pat is not None:
            ops = pat.group(2)
            ops = re.split(",", ops)
            for opp in ops:
                t = re.split(":", opp)
                if t[0] == op:
                    return t[1]
        return None

    # ----------------------------------------------------------------------
    # Tests if block contains operation on inside of the part (-1),
    #      outside (1), or can't decide (0)
    # ----------------------------------------------------------------------
    def operationSide(self, name=None):
        if self.operationTest("pocket", name):
            return -1
        if (self.operationTest("in", name)
                and not self.operationTest("out", name)):
            return -1
        if (self.operationTest("out", name)
                and not self.operationTest("in", name)):
            return 1
        return 0

    # ----------------------------------------------------------------------
    # @return the new name with an operation (static)
    # ----------------------------------------------------------------------
    @staticmethod
    def operationName(name, operation, remove=None):
        pat = OPPAT.match(name)
        if pat is None:
            return f"{name} [{operation}]"
        else:
            name = pat.group(1).strip()
            ops = pat.group(2).split(",")
            if ":" in operation:
                oid, opt = operation.split(":")
            else:
                oid = operation
                opt = None

            found = False
            for i, o in enumerate(ops):
                if ":" in o:
                    o, c = o.split(":")
                    try:
                        c = int(c)
                    except Exception:
                        c = 1
                else:
                    c = 1

                if remove and o in remove:
                    ops[i] = ""
                if not found and o == oid:
                    if opt is not None or c is None:
                        ops[i] = operation
                    else:
                        ops[i] = f"{oid}:{int(c + 1)}"
                    found = True

            # remove all empty
            ops = list(filter(lambda x: x != "", ops))

            if not found:
                ops.append(operation)

            return f"{name} [{','.join(ops)}]"

    # ----------------------------------------------------------------------
    # Add a new operation to the block's name
    # ----------------------------------------------------------------------
    def addOperation(self, operation, remove=None):
        self._name = Block.operationName(self.name(), operation, remove)

    # ----------------------------------------------------------------------
    def header(self):
        e = (
            self.expand
            and Unicode.BLACK_DOWN_POINTING_TRIANGLE
            or Unicode.BLACK_RIGHT_POINTING_TRIANGLE
        )
        v = self.enable and Unicode.BALLOT_BOX_WITH_X or Unicode.BALLOT_BOX
        try:
            return f"{e} {v} {self.name()} - [{len(self)}]"
        except UnicodeDecodeError:
            return " ".join([
                f"{e} {v} {self.name().decode('ascii', 'replace')} -",
                f"[{int(len(self))}]"
            ])  # TODO: is this OK?

    # ----------------------------------------------------------------------
    def write_header(self):
        header = ""
        header += f"(Block-name: {self.name()})\n"
        header += f"(Block-expand: {int(self.expand)})\n"
        header += f"(Block-enable: {int(self.enable)})\n"
        if self.color:
            header += f"(Block-color: {self.color})\n"
        return header

    def write(self, f):
        f.write(self.write_header())
        for line in self:
            if self.enable:
                f.write(f"{line}\n")
            else:
                f.write(
                    f"(Block-X: {line.replace('(', '[').replace(')', ']')})\n")

    # ----------------------------------------------------------------------
    # Return a dump object for pickler
    # ----------------------------------------------------------------------
    def dump(self):
        return self.name(), self.enable, self.expand, self.color, self

    # ----------------------------------------------------------------------
    # Create a block from a dump object from unpickler
    # ----------------------------------------------------------------------
    @staticmethod
    def load(obj):
        name, enable, expand, color, code = obj
        block = Block(name)
        block.enable = enable
        block.expand = expand
        block.color = color
        block.extend(code)
        return block

    # ----------------------------------------------------------------------
    def append(self, line):
        if line.startswith("(Block-"):
            pat = BLOCKPAT.match(line)
            if pat:
                name, value = pat.groups()
                value = value.strip()
                if name == "name":
                    self._name = value
                    return
                elif name == "expand":
                    self.expand = bool(int(value))
                    return
                elif name == "enable":
                    self.enable = bool(int(value))
                    return
                elif name == "tab":
                    # Handled elsewhere
                    return
                elif name == "color":
                    self.color = value
                    return
                elif name == "X":  # uncomment
                    list.append(
                        self, value.replace("[", "(").replace("]", ")"))
                    return
        if self._name is None and ("id:" in line) and ("End" not in line):
            pat = IDPAT.match(line)
            if pat:
                self._name = pat.group(1)
        list.append(self, line)

    # ----------------------------------------------------------------------
    def resetPath(self):
        del self._path[:]
        self.xmin = self.ymin = self.zmin = 1000000.0
        self.xmax = self.ymax = self.zmax = -1000000.0
        self.length = 0.0  # cut length
        self.rapid = 0.0  # rapid length
        self.time = 0.0

    # ----------------------------------------------------------------------
    def hasPath(self):
        return bool(self._path)

    # ----------------------------------------------------------------------
    def addPath(self, p):
        self._path.append(p)

    # ----------------------------------------------------------------------
    def path(self, item):
        try:
            return self._path[item]
        except Exception:
            return None

    # ----------------------------------------------------------------------
    def startPath(self, x, y, z):
        self.sx = x
        self.sy = y
        self.sz = z

    # ----------------------------------------------------------------------
    def endPath(self, x, y, z):
        self.ex = x
        self.ey = y
        self.ez = z

    # ----------------------------------------------------------------------
    def pathMargins(self, xyz):
        self.xmin = min(self.xmin, min(i[0] for i in xyz))
        self.ymin = min(self.ymin, min(i[1] for i in xyz))
        self.zmin = min(self.zmin, min(i[2] for i in xyz))
        self.xmax = max(self.xmax, max(i[0] for i in xyz))
        self.ymax = max(self.ymax, max(i[1] for i in xyz))
        self.zmax = max(self.zmax, max(i[2] for i in xyz))


# =============================================================================
# Gcode file
# =============================================================================
class GCode:
    LOOP_MERGE = False

    # ----------------------------------------------------------------------
    def __init__(self):
        self.cnc = CNC()
        self.header = ""
        self.footer = ""
        self.undoredo = undo.UndoRedo()
        self.probe = Probe()
        self.orient = Orient()
        self.vars = {}  # local variables
        self.init()

    # ----------------------------------------------------------------------
    def init(self):
        self.filename = ""
        self.blocks = []  # list of blocks
        self.vars.clear()
        self.undoredo.reset()
        self._lastModified = 0
        self._modified = False

    # ----------------------------------------------------------------------
    # Recalculate enabled path margins
    # ----------------------------------------------------------------------
    def calculateEnableMargins(self):
        self.cnc.resetEnableMargins()
        for block in self.blocks:
            if block.enable:
                CNC.vars["xmin"] = min(CNC.vars["xmin"], block.xmin)
                CNC.vars["ymin"] = min(CNC.vars["ymin"], block.ymin)
                CNC.vars["zmin"] = min(CNC.vars["zmin"], block.zmin)
                CNC.vars["xmax"] = max(CNC.vars["xmax"], block.xmax)
                CNC.vars["ymax"] = max(CNC.vars["ymax"], block.ymax)
                CNC.vars["zmax"] = max(CNC.vars["zmax"], block.zmax)

    # ----------------------------------------------------------------------
    def isModified(self):
        return self._modified

    # ----------------------------------------------------------------------
    def resetModified(self):
        self._modified = False

    # ----------------------------------------------------------------------
    def __getitem__(self, item):
        return self.blocks[item]

    # ----------------------------------------------------------------------
    def __setitem__(self, item, value):
        self.blocks[item] = value

    # ----------------------------------------------------------------------
    # Evaluate code expressions if any and return line
    # ----------------------------------------------------------------------
    def evaluate(self, line, app=None):
        if isinstance(line, int):
            return None

        elif isinstance(line, list):
            for i, expr in enumerate(line):
                if isinstance(expr, types.CodeType):
                    result = eval(expr, CNC.vars, self.vars)
                    if isinstance(result, float):
                        line[i] = str(round(result, CNC.digits))
                    else:
                        line[i] = str(result)
            return "".join(line)

        elif isinstance(line, types.CodeType):
            import traceback  # noqa: F401

            v = self.vars
            v["os"] = os
            v["app"] = app
            return eval(line, CNC.vars, self.vars)

        else:
            return line

    # ----------------------------------------------------------------------
    # add new line to list create block if necessary
    # ----------------------------------------------------------------------
    def _addLine(self, line):
        if line.startswith("(Block-name:"):
            self._blocksExist = True
            pat = BLOCKPAT.match(line)
            if pat:
                value = pat.group(2).strip()
                if not self.blocks or len(self.blocks[-1]):
                    self.blocks.append(Block(value))
                else:
                    self.blocks[-1]._name = value
                return

        # FIXME: Code to import legacy tabs can be probably removed in year
        # 2020 or so:
        if line.startswith("(Block-tab:"):
            pat = BLOCKPAT.match(line)
            if pat:
                value = pat.group(2).strip()
                items = map(float, value.split())
                tablock = Block(f"legacy [tab,island,minz:{items[4]:f}]")
                tablock.color = "orange"
                tablock.extend(self.createTab(*items))
                self.insBlocks(-1, [tablock], "Legacy tab")
                print(
                    "WARNING: Converted legacy tabs loaded from file to new "
                    f"g-code island tabs: {tablock._name}"
                )

        if not self.blocks:
            self.blocks.append(Block("Header"))

        cmds = CNC.parseLine(line)
        if cmds is None:
            self.blocks[-1].append(line)
            return

        self.cnc.motionStart(cmds)

        # rapid move up = end of block
        if self._blocksExist:
            self.blocks[-1].append(line)
        elif self.cnc.gcode == 0 and self.cnc.dz > 0.0:
            self.blocks[-1].append(line)
            self.blocks.append(Block())
        elif self.cnc.gcode == 0 and len(self.blocks) == 1:
            self.blocks.append(Block())
            self.blocks[-1].append(line)
        else:
            self.blocks[-1].append(line)

        self.cnc.motionEnd()

    # ----------------------------------------------------------------------
    # Load a file into editor
    # ----------------------------------------------------------------------
    def load(self, filename=None):
        if filename is None:
            filename = self.filename
        self.init()
        self.filename = filename
        try:
            f = open(self.filename)
        except Exception:
            return False
        self._lastModified = os.stat(self.filename).st_mtime
        self.cnc.initPath()
        self.cnc.resetAllMargins()
        self._blocksExist = False
        for line in f:
            self._addLine(line[:-1].replace("\x0d", ""))
        self._trim()
        f.close()
        return True

    # ----------------------------------------------------------------------
    # Save to a file
    # ----------------------------------------------------------------------
    def save(self, filename=None):
        if filename is not None:
            self.filename = filename
        try:
            f = open(self.filename, "w")
        except Exception:
            return False

        for block in self.blocks:
            block.write(f)
        f.close()
        self._lastModified = os.stat(self.filename).st_mtime
        self._modified = False
        return True

    # ----------------------------------------------------------------------
    # Save in TXT format
    # -Enabled Blocks only
    # -Cleaned from bCNC metadata and comments
    # -Uppercase
    # ----------------------------------------------------------------------
    def saveTXT(self, filename):
        txt = open(filename, "w")
        for block in self.blocks:
            if block.enable:
                for line in block:
                    cmds = CNC.parseLine(line)
                    if cmds is None:
                        continue
                    txt.write(f"{line.upper()}\n")
        txt.close()
        return True

    # ----------------------------------------------------------------------
    def addBlockFromString(self, name, text):
        if not text:
            return
        block = Block(name)
        block.extend(text.splitlines())
        self.blocks.append(block)

    # ----------------------------------------------------------------------
    # If empty insert a header and a footer
    # ----------------------------------------------------------------------
    def headerFooter(self):
        if not self.blocks:
            self.addBlockFromString("Header", self.header)
            self.addBlockFromString("Footer", self.footer)
            return True
        return False

    # ----------------------------------------------------------------------
    # Load DXF file into gcode
    # ----------------------------------------------------------------------
    def importDXF(self, filename):
        try:
            dxf = DXF(filename, "r")
        except Exception:
            return False
        self.filename = ""

        dxf.readFile()
        dxf.close()

        # prepare dxf file
        dxf.sort()
        dxf.convert2Polylines()
        dxf.expandBlocks()

        empty = len(self.blocks) == 0
        if empty:
            self.addBlockFromString("Header", self.header)

        if CNC.inch:
            units = DXF.INCHES
        else:
            units = DXF.MILLIMETERS

        undoinfo = []
        for name, layer in dxf.layers.items():
            enable = not bool(layer.isFrozen())
            entities = dxf.entities(name)
            if not entities:
                continue
            self.importEntityPoints(None, entities, name, enable, layer.color())
            path = Path(name)
            path.fromDxf(dxf, entities, units)
            path.removeZeroLength()
            if path.color is None:
                path.color = layer.color()
            if path.color == "#FFFFFF":
                path.color = None
            opath = path.split2contours(
                0.0001
            )  # Lowered accuracy due to problems interfacing arcs and lines in DXF
            if not opath:
                continue
            while opath:
                li = 0
                llen = 0.0
                for i, p in enumerate(opath):
                    if p.length() > llen:
                        li = i
                        llen = p.length()
                longest = opath.pop(li)
                longest.directionSet(
                    1
                )  # turn path to CW (conventional when milling outside)

                # Can be time consuming
                if GCode.LOOP_MERGE:
                    longest.mergeLoops(opath)

                undoinfo.extend(self.importPath(None, longest, None, enable))

            undoinfo.extend(self.importPath(None, opath, None, enable))

        if empty:
            self.addBlockFromString("Footer", self.footer)
        return True

    # ----------------------------------------------------------------------
    # Save in DXF format
    # ----------------------------------------------------------------------
    def saveDXF(self, filename):
        try:
            dxf = DXF(filename, "w")
        except Exception:
            return False
        if CNC.inch:
            dxf.units = DXF.INCHES
        else:
            dxf.units = DXF.MILLIMETERS
        dxf.writeHeader()
        for block in self.blocks:
            name = block.name()
            if ":" in name:
                name = name.split(":")[0]
            for line in block:
                cmds = CNC.parseLine(line)
                if cmds is None:
                    continue
                self.cnc.motionStart(cmds)
                if self.cnc.gcode == 1:  # line
                    dxf.line(
                        self.cnc.x,
                        self.cnc.y,
                        self.cnc.xval,
                        self.cnc.yval,
                        name
                    )
                elif self.cnc.gcode in (2, 3):  # arc
                    xc, yc = self.cnc.motionCenter()
                    sphi = math.atan2(self.cnc.y - yc, self.cnc.x - xc)
                    ephi = math.atan2(self.cnc.yval - yc, self.cnc.xval - xc)
                    if ephi <= sphi + 1e-10:
                        ephi += 2.0 * math.pi
                    if self.cnc.gcode == 2:
                        dxf.arc(
                            xc,
                            yc,
                            self.cnc.rval,
                            math.degrees(ephi),
                            math.degrees(sphi),
                            name,
                        )
                    else:
                        dxf.arc(
                            xc,
                            yc,
                            self.cnc.rval,
                            math.degrees(sphi),
                            math.degrees(ephi),
                            name,
                        )
                self.cnc.motionEnd()
        dxf.writeEOF()
        dxf.close()
        return True

    # ----------------------------------------------------------------------
    # Get scaling factor for SVG files
    # ----------------------------------------------------------------------
    def SVGscale(self, dpi=96.0):  # same as inkscape 0.9x (according to jscut)
        if CNC.inch:
            return 1.0 / dpi
        return 25.4 / dpi

    # ----------------------------------------------------------------------
    # Load SVG file into gcode
    # ----------------------------------------------------------------------
    def importSVG(self, filename):
        svgcode = SVGcode(filename)

        empty = len(self.blocks) == 0
        if empty:
            self.addBlockFromString("Header", self.header)

        # FIXME: UI to set SVG samples_per_unit
        ppi = 96.0  # 96 pixels per inch.
        scale = self.SVGscale(ppi)
        samples_per_unit = 200.0
        for path in svgcode.get_gcode(scale,
                                      samples_per_unit,
                                      CNC.digits,
                                      ppi=ppi):
            self.addBlockFromString(path["id"], path["path"])

        if empty:
            self.addBlockFromString("Footer", self.footer)
        return True

    # ----------------------------------------------------------------------
    # get document margins
    # ----------------------------------------------------------------------
    def getMargins(self):
        # Get bounding box of document
        minx, miny, maxx, maxy = 0, 0, 0, 0
        for i, block in enumerate(self.blocks):
            paths = self.toPath(i)
            for path in paths:
                minx2, miny2, maxx2, maxy2 = path.bbox()
                minx, miny, maxx, maxy = (
                    min(minx, minx2),
                    min(miny, miny2),
                    max(maxx, maxx2),
                    max(maxy, maxy2),
                )
        return minx, miny, maxx, maxy

    # ----------------------------------------------------------------------
    # Save in SVG format
    # ----------------------------------------------------------------------
    def saveSVG(self, filename):
        try:
            svg = open(filename, "w")
        except Exception:
            return False

        padding = 10
        scale = self.SVGscale()

        # Get bounding box of document
        minx, miny, maxx, maxy = self.getMargins()

        svg.write(
            "<!-- SVG generated by bCNC: "
            "https://github.com/vlachoudis/bCNC -->\n"
        )
        svg.write(
            f"<svg viewBox=\"{(minx * scale) - padding} "
            f"{(-maxy * scale) - padding} "
            f"{((maxx - minx) * scale) + padding * 2} "
            f"{((maxy - miny) * scale) + padding * 2}\">\n"
        )

        def svgLine(scale, px, py, type_="L"):
            return f"\t{type_} {px * scale} {py * scale}\n"

        def svgArc(scale, gcode, r, ax, ay, bx, by, cx, cy):
            sphi = math.atan2(ay - yc, ax - xc)
            ephi = math.atan2(by - yc, bx - xc)
            arcSweep = ephi - sphi
            arcSweep = 0 if arcSweep <= math.radians(180) else 1
            # Arc
            if gcode == 2:
                if ephi <= sphi + 1e-10:
                    ephi += 2.0 * math.pi
                return "\tA {} {} {} {} {} {} {}\n".format(
                    r * scale,
                    r * scale,
                    0,
                    arcSweep,
                    1,
                    bx * scale,
                    by * scale,
                )
            else:
                if ephi <= sphi + 1e-10:
                    ephi += 2.0 * math.pi
                return "\tA {} {} {} {} {} {} {}\n".format(
                    r * scale,
                    r * scale,
                    0,
                    arcSweep,
                    0,
                    bx * scale,
                    by * scale,
                )

        for block in self.blocks:

            name = block.name()
            color = block.color
            if color is None:
                color = "black"
            width = 2
            if ":" in name:
                name = name.split(":")[0]
            svgpath = ""
            lastx, lasty = 0, 0
            firstx, firsty = None, None

            # Write paths
            for line in block:
                cmds = CNC.parseLine(line)
                if cmds is None:
                    continue
                self.cnc.motionStart(cmds)

                if self.cnc.gcode == 0:  # rapid line (move)
                    svgpath += svgLine(
                        scale, self.cnc.xval, -self.cnc.yval, "M")
                else:
                    lastx, lasty = self.cnc.xval, self.cnc.yval
                    if firstx is None:
                        firstx, firsty = self.cnc.x, self.cnc.y

                if self.cnc.gcode == 1:  # line
                    svgpath += svgLine(scale, self.cnc.xval, -self.cnc.yval)

                elif self.cnc.gcode in (2, 3):  # arc
                    xc, yc = self.cnc.motionCenter()

                    # In case of full circle, we need to split circle
                    # in two arcs:
                    midx = self.cnc.x
                    midy = self.cnc.y
                    if (
                        self.cnc.y == self.cnc.yval
                        and self.cnc.x == self.cnc.xval
                    ):  # is full circle?
                        midx = self.cnc.x + (xc - self.cnc.x) * 2
                        midy = self.cnc.y + (yc - self.cnc.y) * 2
                        svgpath += svgArc(
                            scale,
                            self.cnc.gcode,
                            self.cnc.rval,
                            self.cnc.x,
                            -self.cnc.y,
                            midx,
                            -midy,
                            xc,
                            -yc,
                        )
                    # Finish arc
                    svgpath += svgArc(
                        scale,
                        self.cnc.gcode,
                        self.cnc.rval,
                        midx,
                        -midy,
                        self.cnc.xval,
                        -self.cnc.yval,
                        xc,
                        -yc,
                    )
                self.cnc.motionEnd()

            if firstx == lastx and firsty == lasty:
                svgpath += "\tZ\n"

            if len(svgpath) > 0:
                for line in block.write_header().splitlines():
                    svg.write(f"\t<!-- {line} -->\n")
                svg.write(
                    f"\t<path d=\"\n{svgpath}\t\" stroke=\"{color}\" "
                    f"stroke-width=\"{width}\" fill=\"none\" />\n"
                )

        svg.write("</svg>\n")
        svg.close()
        return True

    # ----------------------------------------------------------------------
    # Import POINTS from entities
    # ----------------------------------------------------------------------
    def importEntityPoints(self, pos, entities, name, enable=True, color=None):
        undoinfo = []
        i = 0
        while i < len(entities):
            if entities[i].type != "POINT":
                i += 1
                continue

            block = Block(f"{name} [P]")
            block.enable = enable

            block.color = entities[i].color()
            if block.color is None:
                block.color = color

            x, y = entities[i].start()
            block.append(f"g0 {self.fmt('x', x, 7)} {self.fmt('y', y, 7)}")
            block.append(CNC.zenter(self.cnc["surface"]))
            block.append(CNC.zsafe())
            undoinfo.append(self.addBlockUndo(pos, block))
            if pos is not None:
                pos += 1
            del entities[i]

        return undoinfo

    # ----------------------------------------------------------------------
    # convert a block to path
    # ----------------------------------------------------------------------
    def toPath(self, bid):
        block = self.blocks[bid]
        paths = []
        path = Path(block.name())
        self.initPath(bid)
        start = Vector(self.cnc.x, self.cnc.y)

        # get only first path that enters the surface
        # ignore the deeper ones
        passno = 0
        for line in block:
            # flatten helical paths
            line = re.sub(r"\s?z-?[0-9\.]+", "", line)

            # break after first depth pass
            if line == "( ---------- cut-here ---------- )":
                passno = 0
                if path:
                    paths.append(path)
                    path = Path(block.name())
            if line[:5] == "(pass":
                passno += 1
            if passno > 1:
                continue

            cmds = CNC.parseLine(line)
            if cmds is None:
                continue
            self.cnc.motionStart(cmds)
            end = Vector(self.cnc.xval, self.cnc.yval)
            if self.cnc.gcode == 0:  # rapid move (new block)
                if path:
                    paths.append(path)
                    path = Path(block.name())
            elif self.cnc.gcode == 1:  # line
                if self.cnc.dx != 0.0 or self.cnc.dy != 0.0:
                    path.append(Segment(1, start, end))
            elif self.cnc.gcode in (2, 3):  # arc
                xc, yc = self.cnc.motionCenter()
                center = Vector(xc, yc)
                path.append(Segment(self.cnc.gcode, start, end, center))
            self.cnc.motionEnd()
            start = end
        if path:
            paths.append(path)
        return paths

    # ----------------------------------------------------------------------
    # create a block from Path
    # @param z      I       ending depth
    # @param zstart I       starting depth
    # ----------------------------------------------------------------------
    def fromPath(
        self,
        path,
        block=None,
        z=None,
        retract=True,
        entry=False,
        exit_=True,
        zstart=None,
        ramp=None,
        comments=True,
        exitpoint=None,
        truncate=None,
    ):
        # Recursion for multiple paths
        if not isinstance(path, Path):
            block = Block("new")
            for p in path:
                block.extend(
                    self.fromPath(
                        p,
                        None,
                        z,
                        retract,
                        entry,
                        exit_,
                        zstart,
                        ramp,
                        comments,
                        exitpoint,
                        truncate,
                    )
                )
                block.append("( ---------- cut-here ---------- )")
            del block[-1]  # remove trailing cut-here
            return block

        if z is None:
            z = self.cnc["surface"]
        if zstart is None:
            zstart = z

        # Calculate helix step
        zstep = abs(z - zstart)

        # Preprocess ramp
        if ramp is None:
            ramp = 0
        if ramp == 0:
            ramp = path.length()  # full helix (default)
        ramp = min(ramp, path.length())  # Never ramp longer than single pass!

        # Calculate helical feedrate
        helixfeed = self.cnc["cutfeed"]
        if zstep > 0:
            # Compensate helix feed, so we never plunge too fast on
            # short/steep paths
            # FIXME: Add UI to disable this feature??? Not
            # sure if that's needed.
            rampratio = zstep / min(path.length(), ramp)
            helixfeed2 = round(self.cnc["cutfeedz"] / rampratio)
            helixfeed = min(self.cnc["cutfeed"], helixfeed2)

        #
        if block is None:
            if isinstance(path, Path):
                block = Block(path.name)
            else:
                block = Block(path[0].name)

        # Generate g-code for single path segment
        def addSegment(segment, z=None, cm=""):
            x, y = segment.B

            # Generate LINE
            if segment.type == Segment.LINE:
                x, y = segment.B
                # rounding problem from #903 was manifesting here. Had to lower
                # the decimal precision to CNC.digits
                if z is None:
                    block.append(
                        f"g1 {self.fmt('x', x, 7)} {self.fmt('y', y, 7)}" + cm)
                else:
                    block.append(
                        f"g1 {self.fmt('x', x, 7)} {self.fmt('y', y, 7)} "
                        f"{self.fmt('z', z, 7)}"
                        + cm
                    )

            # Generate ARCS
            elif segment.type in (Segment.CW, Segment.CCW):
                ij = segment.C - segment.A
                if abs(ij[0]) < 1e-5:
                    ij[0] = 0.0
                if abs(ij[1]) < 1e-5:
                    ij[1] = 0.0
                if z is None:
                    block.append(
                        f"g{int(segment.type)} "
                        + f"{self.fmt('x', x, 7)} "
                        + f"{self.fmt('y', y, 7)} "
                        + f"{self.fmt('i', ij[0], 7)} "
                        + f"{self.fmt('j', ij[1], 7)} "
                        + cm
                    )
                else:
                    block.append(
                        f"g{int(segment.type)} "
                        + f"{self.fmt('x', x, 7)} "
                        + f"{self.fmt('y', y, 7)} "
                        + f"{self.fmt('i', ij[0], 7)} "
                        + f"{self.fmt('j', ij[1], 7)} "
                        + f"{self.fmt('z', z, 7)} "
                        + cm
                    )

        # Get island height of segment
        def getSegmentZTab(segment, altz=float("-inf")):
            if segment._inside:
                return max(segment._inside)
            else:
                return altz

        # Generate block from path
        if isinstance(path, Path):
            x, y = path[0].A

            # decide if flat or ramp/helical:
            if z == zstart:
                zh = z
            elif zstart is not None:
                zh = zstart

            # test if not starting in tab/island!
            ztab = getSegmentZTab(path[0], z)

            # Retract to zsafe
            if retract:
                block.append(f"g0 {self.fmt('z', CNC.vars['safe'], 7)}")

            # Rapid to beginning of the path
            block.append(f"g0 {self.fmt('x', x, 7)} {self.fmt('y', y, 7)}")

            # Descend to pass (plunge to the beginning of path)
            if entry:
                # if entry feed to Z
                block.append(CNC.zenter(max(zh, ztab), 7))
            else:
                # without entry just rapid to Z
                block.append(f"g0 {self.fmt('z', max(zh, ztab), 7)}")

            # Begin pass
            if comments:
                block.append("(entered)")

            # Loop over segments
            setfeed = True
            ztabprev = float("-inf")
            ramping = True
            for sid, segment in enumerate(path):
                zhprev = zh

                # Ramp down
                zh -= (segment.length() / ramp) * zstep  # ramp
                zh = max(zh, z)  # Never cut deeper than z!

                # Reset feedrate if not ramping anymore
                if zh == zhprev and ramping:
                    helixfeed = self.cnc["cutfeed"]
                    setfeed = True
                    ramping = False

                # Get tab height
                ztab = getSegmentZTab(segment)

                # Retract over tabs
                # has tab height changed? tab boundary crossed?
                if ztab != ztabprev:
                    # if we need to enter the toolpath after done
                    # clearing the tab
                    if (ztab == float("-inf") or ztab < ztabprev) and (
                        zh < ztabprev or zhprev < ztabprev
                    ):
                        if comments:
                            block.append(
                                "(tab down " + str(max(zhprev, ztab)) + ")")
                        block.append(CNC.zenter(max(zhprev, ztab), 7))
                        setfeed = True
                    elif (
                        zh < ztab or zhprev < ztab
                    ):  # if we need to go higher in order to clear the tab
                        if comments:
                            block.append("(tab up " + str(max(zh, ztab)) + ")")
                        block.append(CNC.zexit(max(zh, ztab), 7))
                        setfeed = True
                ztabprev = ztab

                # Cut next segment of toolpath
                # Never cut deeper than tabs!
                addSegment(segment, max(zh, ztab))

                # Set feed if needed
                if setfeed:
                    block[-1] += f" {self.fmt('f', round(helixfeed))}"
                    setfeed = False

                # Truncate
                if truncate is not None:
                    truncate -= segment.length()
                    if truncate <= -1e-7:
                        break

            # Exit toolpath
            if exit_:
                if comments:
                    block.append("(exiting)")
                if exitpoint is not None:
                    block.append(
                        f"g1 {self.fmt('x', exitpoint[0])} "
                        f"{self.fmt('y', exitpoint[1])}"
                    )
                block.append(CNC.zsafe())

        return block

    # ----------------------------------------------------------------------
    # Import paths as block
    # return ids of blocks added in newblocks list if declared
    # ----------------------------------------------------------------------
    def importPath(
            self, pos, paths, newblocks=None, enable=True, multiblock=True):
        undoinfo = []
        if isinstance(paths, Path):
            block = self.fromPath(paths)
            block.enable = enable
            block.color = paths.color
            undoinfo.append(self.addBlockUndo(pos, block))
            if newblocks is not None:
                newblocks.append(pos)
        else:
            block = None
            for path in paths:
                if block is None:
                    block = Block(path.name)
                block = self.fromPath(path, block)
                if multiblock:
                    block.enable = enable
                    undoinfo.append(self.addBlockUndo(pos, block))
                    if newblocks is not None:
                        newblocks.append(pos)
                    if pos is not None:
                        pos += 1
                    block = None
            if not multiblock:
                block.enable = enable
                undoinfo.append(self.addBlockUndo(pos, block))
                if newblocks is not None:
                    newblocks.append(pos)
        return undoinfo

    # ----------------------------------------------------------------------
    # sync file timestamp
    # ----------------------------------------------------------------------
    def syncFileTime(self):
        try:
            self._lastModified = os.stat(self.filename).st_mtime
        except Exception:
            return False

    # ----------------------------------------------------------------------
    # Check if a new version exists
    # ----------------------------------------------------------------------
    def checkFile(self):
        try:
            return os.stat(self.filename).st_mtime > self._lastModified
        except Exception:
            return False

    # ----------------------------------------------------------------------
    def fmt(self, c, v, d=None):
        return self.cnc.fmt(c, v, d)

    # ----------------------------------------------------------------------
    def _trim(self):
        if not self.blocks:
            return
        # Delete last block if empty
        last = self.blocks[-1]
        if len(last) == 1 and len(last[0]) == 0:
            del last[0]
        if len(self.blocks[-1]) == 0:
            self.blocks.pop()

    # ----------------------------------------------------------------------
    # Undo/Redo operations
    # ----------------------------------------------------------------------
    def undo(self):
        self.undoredo.undo()

    # ----------------------------------------------------------------------
    def redo(self):
        self.undoredo.redo()

    # ----------------------------------------------------------------------
    def addUndo(self, undoinfo, msg=None):
        if not undoinfo:
            return
        self.undoredo.add(undoinfo, msg)
        self._modified = True

    # ----------------------------------------------------------------------
    def canUndo(self):
        return self.undoredo.canUndo()

    # ----------------------------------------------------------------------
    def canRedo(self):
        return self.undoredo.canRedo()

    # ----------------------------------------------------------------------
    # Change all lines in editor
    # ----------------------------------------------------------------------
    def setLinesUndo(self, lines):
        undoinfo = (self.setLinesUndo, list(self.lines()))
        # Delete all blocks and create new ones
        del self.blocks[:]
        self.cnc.initPath()
        self._blocksExist = False
        for line in lines:
            self._addLine(line)
        self._trim()
        return undoinfo

    # ----------------------------------------------------------------------
    def setAllBlocksUndo(self, blocks=[]):
        undoinfo = [self.setAllBlocksUndo, self.blocks]
        self.blocks = blocks
        return undoinfo

    # ----------------------------------------------------------------------
    # Change a single line in a block
    # ----------------------------------------------------------------------
    def setLineUndo(self, bid, lid, line):
        undoinfo = (self.setLineUndo, bid, lid, self.blocks[bid][lid])
        self.blocks[bid][lid] = line
        return undoinfo

    # ----------------------------------------------------------------------
    # Insert a new line into block
    # ----------------------------------------------------------------------
    def insLineUndo(self, bid, lid, line):
        undoinfo = (self.delLineUndo, bid, lid)
        block = self.blocks[bid]
        if lid >= len(block):
            block.append(line)
        else:
            block.insert(lid, line)
        return undoinfo

    # ----------------------------------------------------------------------
    # Clone line inside a block
    # ----------------------------------------------------------------------
    def cloneLineUndo(self, bid, lid):
        return self.insLineUndo(bid, lid, self.blocks[bid][lid])

    # ----------------------------------------------------------------------
    # Delete line from block
    # ----------------------------------------------------------------------
    def delLineUndo(self, bid, lid):
        block = self.blocks[bid]
        undoinfo = (self.insLineUndo, bid, lid, block[lid])
        del block[lid]
        return undoinfo

    # ----------------------------------------------------------------------
    # Add a block
    # ----------------------------------------------------------------------
    def addBlockUndo(self, bid, block):
        if bid is None:
            bid = len(self.blocks)
        if bid >= len(self.blocks):
            undoinfo = (self.delBlockUndo, len(self.blocks))
            self.blocks.append(block)
        else:
            undoinfo = (self.delBlockUndo, bid)
            self.blocks.insert(bid, block)
        return undoinfo

    # ----------------------------------------------------------------------
    # Clone a block
    # ----------------------------------------------------------------------
    def cloneBlockUndo(self, bid, pos=None):
        if pos is None:
            pos = bid
        return self.addBlockUndo(pos, Block(self.blocks[bid]))

    # ----------------------------------------------------------------------
    # Delete a whole block
    # ----------------------------------------------------------------------
    def delBlockUndo(self, bid):
        block = self.blocks.pop(bid)
        undoinfo = (self.addBlockUndo, bid, block)
        return undoinfo

    # ----------------------------------------------------------------------
    # Insert a list of other blocks from another gcode file probably
    # ----------------------------------------------------------------------
    def insBlocksUndo(self, bid, blocks):
        if bid is None or bid >= len(self.blocks):
            bid = len(self.blocks)
        undoinfo = (
            "Insert blocks", self.delBlocksUndo, bid, bid + len(blocks))
        self.blocks[bid:bid] = blocks
        return undoinfo

    # ----------------------------------------------------------------------
    # Delete a range of blocks
    # ----------------------------------------------------------------------
    def delBlocksUndo(self, from_, to_):
        blocks = self.blocks[from_:to_]
        undoinfo = ("Delete blocks", self.insBlocksUndo, from_, blocks)
        del self.blocks[from_:to_]
        return undoinfo

    # ----------------------------------------------------------------------
    # Insert blocks and push the undo info
    # ----------------------------------------------------------------------
    def insBlocks(self, bid, blocks, msg=""):
        if self.headerFooter():  # just in case
            bid = 1
        self.addUndo(self.insBlocksUndo(bid, blocks), msg)

    # ----------------------------------------------------------------------
    # Set block expand
    # ----------------------------------------------------------------------
    def setBlockExpandUndo(self, bid, expand):
        undoinfo = (self.setBlockExpandUndo, bid, self.blocks[bid].expand)
        self.blocks[bid].expand = expand
        return undoinfo

    # ----------------------------------------------------------------------
    # Set block state
    # ----------------------------------------------------------------------
    def setBlockEnableUndo(self, bid, enable):
        undoinfo = (self.setBlockEnableUndo, bid, self.blocks[bid].enable)
        self.blocks[bid].enable = enable
        return undoinfo

    # ----------------------------------------------------------------------
    # Set block color
    # ----------------------------------------------------------------------
    def setBlockColorUndo(self, bid, color):
        undoinfo = (self.setBlockColorUndo, bid, self.blocks[bid].color)
        self.blocks[bid].color = color
        return undoinfo

    # ----------------------------------------------------------------------
    # Swap two blocks
    # ----------------------------------------------------------------------
    def swapBlockUndo(self, a, b):
        undoinfo = (self.swapBlockUndo, a, b)
        tmp = self.blocks[a]
        self.blocks[a] = self.blocks[b]
        self.blocks[b] = tmp
        return undoinfo

    # ----------------------------------------------------------------------
    # Move block from location src to location dst
    # ----------------------------------------------------------------------
    def moveBlockUndo(self, src, dst):
        if src == dst:
            return None
        undoinfo = (self.moveBlockUndo, dst, src)
        if dst > src:
            self.blocks.insert(dst - 1, self.blocks.pop(src))
        else:
            self.blocks.insert(dst, self.blocks.pop(src))
        return undoinfo

    # ----------------------------------------------------------------------
    # Invert selected blocks
    # ----------------------------------------------------------------------
    def invertBlocksUndo(self, blocks):
        undoinfo = []
        first = 0
        last = len(blocks) - 1
        while first < last:
            undoinfo.append(self.swapBlockUndo(blocks[first], blocks[last]))
            first += 1
            last -= 1
        return undoinfo

    # ----------------------------------------------------------------------
    # Move block upwards
    # ----------------------------------------------------------------------
    def orderUpBlockUndo(self, bid):
        if bid == 0:
            return None
        undoinfo = (self.orderDownBlockUndo, bid - 1)
        # swap with the block above
        before = self.blocks[bid - 1]
        self.blocks[bid - 1] = self.blocks[bid]
        self.blocks[bid] = before
        return undoinfo

    # ----------------------------------------------------------------------
    # Move block downwards
    # ----------------------------------------------------------------------
    def orderDownBlockUndo(self, bid):
        if bid >= len(self.blocks) - 1:
            return None
        undoinfo = (self.orderUpBlockUndo, bid + 1)
        # swap with the block below
        after = self[bid + 1]
        self[bid + 1] = self[bid]
        self[bid] = after
        return undoinfo

    # ----------------------------------------------------------------------
    # Insert block lines
    # ----------------------------------------------------------------------
    def insBlockLinesUndo(self, bid, lines):
        undoinfo = (self.delBlockLinesUndo, bid)
        block = Block()
        for line in lines:
            block.append(line)
        self.blocks.insert(bid, block)
        return undoinfo

    # ----------------------------------------------------------------------
    # Delete a whole block lines
    # ----------------------------------------------------------------------
    def delBlockLinesUndo(self, bid):
        lines = [x for x in self.blocks[bid]]
        undoinfo = (self.insBlockLinesUndo, bid, lines)
        del self.blocks[bid]
        return undoinfo

    # ----------------------------------------------------------------------
    # Set Block name
    # ----------------------------------------------------------------------
    def setBlockNameUndo(self, bid, name):
        undoinfo = (self.setBlockNameUndo, bid, self.blocks[bid]._name)
        self.blocks[bid]._name = name
        return undoinfo

    # ----------------------------------------------------------------------
    # Add an operation code in the name as [drill, cut, in/out...]
    # ----------------------------------------------------------------------
    def addBlockOperationUndo(self, bid, operation, remove=None):
        undoinfo = (self.setBlockNameUndo, bid, self.blocks[bid]._name)
        self.blocks[bid].addOperation(operation, remove)
        return undoinfo

    # ----------------------------------------------------------------------
    # Replace the lines of a block
    # ----------------------------------------------------------------------
    def setBlockLinesUndo(self, bid, lines):
        block = self.blocks[bid]
        undoinfo = (self.setBlockLinesUndo, bid, block[:])
        del block[:]
        block.extend(lines)
        return undoinfo

    # ----------------------------------------------------------------------
    # Move line upwards
    # ----------------------------------------------------------------------
    def orderUpLineUndo(self, bid, lid):
        if lid == 0:
            return None
        block = self.blocks[bid]
        undoinfo = (self.orderDownLineUndo, bid, lid - 1)
        block.insert(lid - 1, block.pop(lid))
        return undoinfo

    # ----------------------------------------------------------------------
    # Move line downwards
    # ----------------------------------------------------------------------
    def orderDownLineUndo(self, bid, lid):
        block = self.blocks[bid]
        if lid >= len(block) - 1:
            return None
        undoinfo = (self.orderUpLineUndo, bid, lid + 1)
        block.insert(lid + 1, block.pop(lid))
        return undoinfo

    # ----------------------------------------------------------------------
    # Expand block with autolevel information
    # ----------------------------------------------------------------------
    def autolevelBlock(self, block):
        new = []
        autolevel = not self.probe.isEmpty()
        for line in block:
            cmds = CNC.compileLine(line)
            if cmds is None:
                new.append(line)
                continue
            elif isinstance(cmds, str):
                cmds = CNC.breakLine(cmds)
            else:
                new.append(line)
                continue

            self.cnc.motionStart(cmds)
            if (autolevel and self.cnc.gcode in (0, 1, 2, 3)
                    and self.cnc.mval == 0):
                xyz = self.cnc.motionPath()
                if not xyz:
                    # while auto-levelling, do not ignore non-movement
                    # commands, just append the line as-is
                    new.append(line)
                else:
                    extra = ""
                    for c in cmds:
                        if (c[0].upper() not in
                                ("G", "X", "Y", "Z", "I", "J", "K", "R")):
                            extra += c
                    x1, y1, z1 = xyz[0]
                    if self.cnc.gcode == 0:
                        g = 0
                    else:
                        g = 1
                    for x2, y2, z2 in xyz[1:]:
                        for x, y, z in self.probe.splitLine(x1, y1, z1, x2,
                                                            y2, z2):
                            new.append(
                                "".join([
                                    f"G{int(g)}",
                                    f"{self.fmt('X', x / self.cnc.unit)}",
                                    f"{self.fmt('Y', y / self.cnc.unit)}",
                                    f"{self.fmt('Z', z / self.cnc.unit)}",
                                    extra,
                                ])
                            )
                            extra = ""
                        x1, y1, z1 = x2, y2, z2
                self.cnc.motionEnd()
            else:
                self.cnc.motionEnd()
                new.append(line)
        return new

    # ----------------------------------------------------------------------
    # Execute autolevel on selected blocks
    # ----------------------------------------------------------------------
    def autolevel(self, items):
        undoinfo = []
        operation = "autolevel"
        for bid in items:
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            if not block.enable:
                continue
            lines = self.autolevelBlock(block)
            undoinfo.append(self.addBlockOperationUndo(bid, operation))
            undoinfo.append(self.setBlockLinesUndo(bid, lines))
        if undoinfo:
            self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Return string representation of whole file
    # ----------------------------------------------------------------------
    def __repr__(self):
        return "\n".join(list(self.lines()))

    # ----------------------------------------------------------------------
    # Iterate over the items
    # ----------------------------------------------------------------------
    def iterate(self, items):
        for bid, lid in items:
            if lid is None:
                block = self.blocks[bid]
                for i in range(len(block)):
                    yield bid, i
            else:
                yield bid, lid

    # ----------------------------------------------------------------------
    # Iterate over all lines
    # ----------------------------------------------------------------------
    def lines(self):
        for block in self.blocks:
            yield from block

    # ----------------------------------------------------------------------
    # initialize cnc path based on block bid
    # ----------------------------------------------------------------------
    def initPath(self, bid=0):
        if bid == 0:
            self.cnc.initPath()
        else:
            # Use the ending point of the previous block
            # since the starting (sxyz is after the rapid motion)
            block = self.blocks[bid - 1]
            self.cnc.initPath(block.ex, block.ey, block.ez)

    # ----------------------------------------------------------------------
    # Move blocks/lines up
    # ----------------------------------------------------------------------
    def orderUp(self, items):
        sel = []  # new selection
        undoinfo = []
        for bid, lid in items:
            if isinstance(lid, int):
                undoinfo.append(self.orderUpLineUndo(bid, lid))
                sel.append((bid, lid - 1))
            elif lid is None:
                undoinfo.append(self.orderUpBlockUndo(bid))
                if bid == 0:
                    return items
                else:
                    sel.append((bid - 1, None))
        self.addUndo(undoinfo, "Move Up")
        return sel

    # ----------------------------------------------------------------------
    # Move blocks/lines down
    # ----------------------------------------------------------------------
    def orderDown(self, items):
        sel = []  # new selection
        undoinfo = []
        for bid, lid in reversed(items):
            if isinstance(lid, int):
                undoinfo.append(self.orderDownLineUndo(bid, lid))
                sel.append((bid, lid + 1))
            elif lid is None:
                undoinfo.append(self.orderDownBlockUndo(bid))
                if bid >= len(self.blocks) - 1:
                    return items
                else:
                    sel.append((bid + 1, None))
        self.addUndo(undoinfo, "Move Down")
        sel.reverse()
        return sel

    # ----------------------------------------------------------------------
    # Peck distance
    # Target depth
    # Depth increment
    # Retract height=safe height
    # ----------------------------------------------------------------------
    def drill(
        self,
        items,
        depth=None,
        peck=None,
        dwell=None,
        distance=None,
        number=0,
        center=True,
    ):
        # find the penetration points and drill
        # skip all g1 movements on the horizontal plane
        if depth is None:
            depth = self.cnc["surface"] - self.cnc["thickness"]
        if (
            depth < self.cnc["surface"] - self.cnc["thickness"]
            or depth > self.cnc["surface"]
        ):
            return (
                f"ERROR: Drill depth {depth:g} outside stock surface: "
                f"{self.cnc['surface']:g} .. "
                f"{self.cnc['surface'] - self.cnc['thickness']:g}\n"
                f"Please change stock surface in Tools->Stock or drill depth."
            )
        if abs(depth - (self.cnc["surface"] - self.cnc["thickness"])) < 1e-7:
            opname = "drill"
        else:
            opname = f"drill:{depth:g}"
        # Incorrect peck values can block drilling cycle calculation
        peck = peck or 0.0
        if peck == 0.0:
            peck = None
        if peck is not None:
            if math.copysign(1.0, depth) * math.copysign(1.0, peck) != -1:
                pecksignstr = "less"
                if math.copysign(1.0, peck) < 0:
                    pecksignstr = "greater"
                return (
                    f"Invalid peck depth value of {peck:g}. In this "
                    f"configuration, peck value should be {pecksignstr} than "
                    f"zero."
                )
        # pecking value is well defined.

        undoinfo = []

        def drillHole(lines):
            # drill point
            if peck is None:
                lines.append(CNC.zenter(depth))
                lines.append(CNC.zsafe())
            else:
                z = self.cnc["surface"]
                while z > depth:
                    z = max(z - peck, depth)
                    lines.append(CNC.zenter(z))
                    lines.append(CNC.zsafe())
                    if dwell:
                        lines.append(f"g4 {self.fmt('p', dwell)}")

        for bid in items:
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            block.enable = True

            # construct new name
            undoinfo.append(self.addBlockOperationUndo(bid, opname))

            # 1st detect limits of first pass
            self.initPath(bid)
            self.cnc.z = self.cnc.zval = 1000.0
            lines = []

            if center:
                # Drill in center only
                for path in self.toPath(bid):
                    x, y = path.center()
                    lines.append(f"g0 {self.fmt('x', x)} {self.fmt('y', y)}")
                    drillHole(lines)

            elif distance is None and number == 0:
                # Drill on path beginning only
                for i, line in enumerate(block):
                    cmds = CNC.parseLine(line)
                    if cmds is None:
                        lines.append(line)
                        continue
                    self.cnc.motionStart(cmds)
                    if self.cnc.dz < 0.0:
                        drillHole(lines)
                    elif self.cnc.dz > 0.0:
                        # retract
                        pass
                    elif self.cnc.gcode == 0:
                        # add all rapid movements
                        lines.append(line)
                    elif self.cnc.gcode == 1:
                        # ignore normal movements
                        pass
                    self.cnc.motionEnd()
            else:
                # Drill multiple holes along path
                for path in self.toPath(bid):

                    length = path.length()
                    if number > 0:
                        distance = length / float(number)
                    s = 0.0  # running length

                    while s < length:
                        P = path.distPoint(s)
                        s += distance
                        lines.append(
                            f"g0 {self.fmt('x', P[0])} {self.fmt('y', P[1])}")
                        drillHole(lines)

            undoinfo.append(self.setBlockLinesUndo(bid, lines))
        self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Perform a cut on a path an add it to block
    # @param newblock O block to add the cut paths
    # @param block  I   existing block
    # @param path   I   path to cut
    # @param z      I   starting z surface
    # @param depth  I   ending depth
    # @param stepz  I   stepping in z
    # ----------------------------------------------------------------------
    def cutPath(
        self,
        newblock,
        block,
        path,
        z,
        depth,
        stepz,
        helix=False,
        helixBottom=True,
        ramp=0,
        islandPaths=[],
        exitpoint=None,
        springPass=False,
    ):
        closed = path.isClosed()
        zigzag = True  # FIXME: Add UI to set this?
        entry = True
        exit_ = False

        # Calculate ramp
        if ramp > 0:
            ramp = abs(ramp) * CNC.vars["diameter"]  # n times tool diameter
        if ramp < 0:
            ramp = abs(ramp)  # absolute
        if ramp == 0:
            ramp = None  # No ramp

        # Calculate exit point for thread milling
        centr = Vector(path.center())
        if exitpoint == 1:
            exitpoint = centr
        elif exitpoint == -1:
            exitpoint = path[-1].B + (path[-1].B - centr)
        else:
            exitpoint = None

        # Mark in which island we are inside
        if islandPaths:
            for island in reversed(islandPaths):
                path.intersectPath(island)
            for island in reversed(islandPaths):
                path.markInside(island, island._inside)

        # Decide if doing additional "appendix" passes after loop
        # (eg.: spring pass or helixbottom)
        appendix = False
        if (springPass and closed) or (helix and helixBottom):
            appendix = True

        # iterate over depth passes:
        retract = True
        while (z - depth) > 1e-7:
            # Go one step lower
            z = max(z - stepz, depth)

            # Detect last pass of loop
            if abs(z - depth) < 1e-7 and not appendix:
                exit_ = True

            # Flat cuts:
            if not helix:
                newblock.append(f"(pass {z:f})")
                if zigzag:
                    self.fromPath(
                        path,
                        newblock,
                        z,
                        retract,
                        True,
                        exit_,
                        exitpoint=exitpoint
                    )
                    if not closed:
                        path.invert()
                else:
                    self.fromPath(
                        path,
                        newblock,
                        z,
                        True,
                        True,
                        exit_,
                        exitpoint=exitpoint
                    )

            # Helical/Ramp cuts:
            else:
                if helixBottom:
                    exit_ = False

                if closed:
                    newblock.append(
                        f"(pass {z + stepz:f} to {z:f})")
                    self.fromPath(
                        path,
                        newblock,
                        z,
                        retract,
                        entry,
                        exit_,
                        z + stepz,
                        ramp,
                        exitpoint=exitpoint,
                    )
                else:
                    # Cut open path back and forth while descending
                    newblock.append(
                        f"(pass {z + stepz:f} to {z + stepz / 2:f})")
                    self.fromPath(
                        path,
                        newblock,
                        z + stepz / 2,
                        retract,
                        entry,
                        False,
                        z + stepz,
                        ramp,
                        exitpoint=exitpoint,
                    )
                    path.invert()
                    newblock.append(f"(pass {z + stepz / 2:f} to {z:f})")
                    self.fromPath(
                        path,
                        newblock,
                        z,
                        False,
                        False,
                        exit_,
                        z + stepz / 2,
                        ramp,
                        exitpoint=exitpoint,
                    )
                    path.invert()

            retract = False
            entry = False

        # Do appendix passes like spring pass or helixbottom
        if appendix:
            if springPass and closed:
                ramp = None  # Do not truncate pass when inverting direction
                path.invert()
                if not closed:
                    retract = True
                    entry = True
                newblock.append(f"(pass {z:f} spring)")
            else:
                newblock.append(f"(pass {z:f} bottom)")

            self.fromPath(
                path,
                newblock,
                z,
                retract,
                entry,
                True,
                exitpoint=exitpoint,
                truncate=ramp,
            )

        return newblock

    # ----------------------------------------------------------------------
    # Close paths by joining end with start with a line segment
    # ----------------------------------------------------------------------
    def close(self, items):
        undoinfo = []
        for bid in items:
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            undoinfo.append(
                self.insLineUndo(
                    bid, MAXINT, self.cnc.gline(block.sx, block.sy))
            )
        self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Create a cut my replicating the initial top-only path multiple times
    # until the maximum height
    # ----------------------------------------------------------------------
    def cut(
        self,
        items,
        depth=None,
        stepz=None,
        surface=None,
        feed=None,
        feedz=None,
        cutFromTop=False,
        helix=False,
        helixBottom=True,
        ramp=0,
        islandsLeave=False,
        islandsCut=False,
        islandsSelectedOnly=True,
        exitpoint=None,
        springPass=False,
        islandsCompensate=False,
    ):
        if surface is None:
            surface = self.cnc["surface"]
        if stepz is None:
            stepz = self.cnc["stepz"]
        if depth is None:
            depth = surface - self.cnc["thickness"]

        # override temporarily the feed if needed
        if feed is not None:  # swap feed with cnc[cutfeed]
            self.cnc["cutfeed"], feed = feed, self.cnc["cutfeed"]
        if feedz is not None:
            self.cnc["cutfeedz"], feedz = feedz, self.cnc["cutfeedz"]

        # Test if cutting within stock boundaries
        if surface > self.cnc["surface"]:
            return (
                "ERROR: Starting cut height is higher than stock surface. "
                "Please change stock surface in Tools->Stock or cut depth."
            )
        if (
            depth < self.cnc["surface"] - self.cnc["thickness"]
            or depth > self.cnc["surface"]
        ):
            return (
                f"ERROR: Cut depth {depth:g} outside stock surface: "
                f"{self.cnc['surface']:g} .. "
                f"{self.cnc['surface'] - self.cnc['thickness']:g}\n"
                "Please change stock surface in Tools->Stock or cut depth."
            )

        # Determine operation block name
        if abs(depth - (self.cnc["surface"] - self.cnc["thickness"])) < 1e-7:
            opname = "cut"
            if helix:
                opname = "helicut"
        else:
            opname = f"cut:{depth:g}"
            if helix:
                opname = f"helicut:{depth:g}"

        stepz = abs(stepz)
        undoinfo = []

        # Get list of islands and remove them from items
        islands = []
        islandPaths = []
        if islandsLeave:
            for bid, block in enumerate(self.blocks):
                if islandsSelectedOnly and bid not in items:
                    continue
                if block.operationTest("island"):
                    islands.append(bid)
                    # determine island height
                    islz = self.cnc["safe"]
                    if block.operationGet("minz") is not None:
                        islz = float(block.operationGet("minz"))
                    # determine if we should offset island
                    # (tabs are always offset)
                    isloffset = False
                    if islandsCompensate or block.operationTest("tab"):
                        isloffset = True
                    # load island paths
                    for islandPath in self.toPath(bid):
                        # compensate for cutter diameter if needed
                        if isloffset:
                            islandPath = islandPath.offsetClean(
                                CNC.vars["diameter"] / 2
                            )[0]
                        islandPath._inside = islz
                        islandPaths.append(islandPath)

        # Remove islands from paths to cut if not requested
        # TODO: maybe also remove all islands with "tab" tag
        if not islandsCut and islands:
            for island in islands:
                if island in items:
                    items.remove(island)
        # Check if there are any paths left
        if not items:
            return "You must select toolpaths along with islands!"

        for bid in items:
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            block.enable = True
            newblock = Block(block.name())

            # Do not apply islands on islands:
            islandPathsClean = islandPaths
            if bid in items and bid in islands:
                islandPathsClean = []

            for path in self.toPath(bid):

                if cutFromTop:
                    self.cutPath(
                        newblock,
                        block,
                        path,
                        surface + stepz,
                        depth,
                        stepz,
                        helix,
                        helixBottom,
                        ramp,
                        islandPathsClean,
                        exitpoint,
                        springPass,
                    )
                else:
                    self.cutPath(
                        newblock,
                        block,
                        path,
                        surface,
                        depth,
                        stepz,
                        helix,
                        helixBottom,
                        ramp,
                        islandPathsClean,
                        exitpoint,
                        springPass,
                    )
            if newblock:
                undoinfo.append(self.addBlockOperationUndo(bid, opname))
                undoinfo.append(self.setBlockLinesUndo(bid, newblock))
        self.addUndo(undoinfo)

        # restore feed
        if feed is not None:
            self.cnc["cutfeed"] = feed
        if feedz is not None:
            self.cnc["cutfeedz"] = feedz

    def createTab(self, x=0, y=0, dx=0, dy=0, z=0, circ=True):
        path = Path("tab")

        dx = dx / 2.0
        dy = dy / 2.0

        if not circ:
            # Square tabs (intersect better with trochoids)
            A = A0 = Vector(x - dx, y - dy)
            B = Vector(x + dx, y - dy)
            path.append(Segment(Segment.LINE, A, B))
            A = B
            B = Vector(x + dx, y + dy)
            path.append(Segment(Segment.LINE, A, B))
            A = B
            B = Vector(x - dx, y + dy)
            path.append(Segment(Segment.LINE, A, B))
            A = B
            B = A0
            path.append(Segment(Segment.LINE, A, B))
        else:
            # Circular tabs (intersect better with angled lines)
            A = Vector(x - max(dx, dy), y)
            C = Vector(x, y)
            seg = Segment(Segment.CCW, A, A)
            seg.setCenter(C)
            path.append(seg)

        # compensate for cutter radius
        # update: this is now done right before cutting,
        # so no need to do it here!
        # path = path.offsetClean(CNC.vars["diameter"]/2)[0]

        return self.fromPath(
            path, None, None, False, False, False, None, None, False)

    # ----------------------------------------------------------------------
    # Create tabs to selected blocks
    # @param ntabs  number of tabs
    # @param dtabs  distance between tabs
    # @param dx     width of tabs
    # @param dy     depth of tabs
    # @param z      height of tabs
    # @param isl    create tabs in form of islands?
    # ----------------------------------------------------------------------
    def createTabs(self, items, ntabs, dtabs, dx, dy, z, circ=True):
        msg = None
        undoinfo = []
        if ntabs == 0 and dtabs == 0:
            return

        tablocks = []
        for bid in items:
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue

            # update minz for selected islands/tabs rather than doing
            # tabs of tabs
            if block.operationTest("island"):
                block._name = f"{block.nameNop()} [island,minz:{z:f}]"
                continue

            else:
                tablock = Block(f"{block.nameNop()} [tab,island,minz:{z:f}]")
                # tablock.color = "#FF0000"
                tablock.color = "orange"
                tablock.enable = (
                    False  # Prevent tabs from being accidentally cut as path
                )

                # Add regular tabs
                for path in self.toPath(bid):
                    length = path.length()
                    d = max(length / float(ntabs), dtabs)
                    # running length
                    s = d / 2.0  # start from half distance to add first tab

                    while s <= length:
                        P = path.distPoint(s)
                        s += d
                        # Make island tabs
                        tablock.extend(
                            self.createTab(P[0], P[1], dx, dy, z, circ))
                        tablock.append("( ---------- cut-here ---------- )")

                del tablock[-1]  # remove last cut-here
                tablocks.append(tablock)
        self.insBlocks(bid + 1, tablocks, "Tabs created")
        self.addUndo(undoinfo)

        return msg

    # ----------------------------------------------------------------------
    # Reverse direction of cut
    # ----------------------------------------------------------------------
    def reverse(self, items):
        undoinfo = []
        remove = ["cut", "climb", "conventional", "cw", "ccw", "reverse"]
        for bid in items:
            operation = "reverse"

            if self.blocks[bid].name() in ("Header", "Footer"):
                continue
            newpath = Path(self.blocks[bid].name())

            # Not sure if this is good idea...
            # Might get confusing if something goes wrong,
            # but seems to work fine
            if self.blocks[bid].operationTest("conventional"):
                operation += ",climb"
            if self.blocks[bid].operationTest("climb"):
                operation += ",conventional"
            if self.blocks[bid].operationTest("cw"):
                operation += ",ccw"
            if self.blocks[bid].operationTest("ccw"):
                operation += ",cw"

            for path in self.toPath(bid):
                path.invert()
                newpath.extend(path)
            if newpath:
                block = self.fromPath(newpath)
                undoinfo.append(
                    self.addBlockOperationUndo(bid, operation, remove))
                undoinfo.append(self.setBlockLinesUndo(bid, block))
        self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Change cut direction
    # 1     CW
    # -1    CCW
    # 2     Conventional = CW for inside profiles and pockets,
    #                  CCW for outside profiles
    # -2    Climb = CCW for inside profiles and pockets,
    #               CW for outside profiles
    # ----------------------------------------------------------------------
    def cutDirection(self, items, direction=-1):

        undoinfo = []
        msg = None

        remove = ["cut", "reverse", "climb", "conventional", "cw", "ccw"]
        for bid in items:
            if self.blocks[bid].name() in ("Header", "Footer"):
                continue

            opdir = direction
            operation = ""

            # Decide conventional/climb/error:
            side = self.blocks[bid].operationSide()
            if abs(direction) > 1 and side == 0:
                msg = "Conventional/Climb feature only works for paths with 'in/out/pocket' tags!\n"
                msg += "Some of the selected paths were not tagged (or are both in+out). You can still use CW/CCW for them."
                continue
            if direction == 2:
                operation = "conventional,"
                if side == -1:
                    opdir = 1  # inside CW
                if side == 1:
                    opdir = -1  # outside CCW
            elif direction == -2:
                operation = "climb,"
                if side == -1:
                    opdir = -1  # inside CCW
                if side == 1:
                    opdir = 1  # outside CW

            # Decide CW/CCW tag
            if opdir == 1:
                operation += "cw"
            elif opdir == -1:
                operation += "ccw"

            # Process paths
            for path in self.toPath(bid):
                if not path.directionSet(opdir):
                    msg = "Error determining direction of path!"
                if path:
                    block = self.fromPath(path)
                    undoinfo.append(
                        self.addBlockOperationUndo(bid, operation, remove))
                    undoinfo.append(self.setBlockLinesUndo(bid, block))
        self.addUndo(undoinfo)

        return msg

    # ----------------------------------------------------------------------
    # Toggle or set island tag on block
    # ----------------------------------------------------------------------
    def island(self, items, island=None):

        undoinfo = []
        remove = ["island"]
        for bid in items:
            isl = island

            if self.blocks[bid].name() in ("Header", "Footer"):
                continue

            if isl is None:
                isl = not self.blocks[bid].operationTest("island")
            if isl:
                tag = "island"
                self.blocks[bid].color = "#ff0000"
            else:
                tag = ""
                self.blocks[bid].color = None

            undoinfo.append(self.addBlockOperationUndo(bid, tag, remove))

        self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Return information for a block
    # return XXX
    # ----------------------------------------------------------------------
    def info(self, bid):
        paths = self.toPath(bid)
        if not paths:
            return None, 1
        if len(paths) > 1:
            closed = paths[0].isClosed()
            return len(paths), paths[0]._direction(closed)
        else:
            closed = paths[0].isClosed()
            return int(closed), paths[0]._direction(closed)

    # ----------------------------------------------------------------------
    # make a profile on block
    # offset +/- defines direction = tool/2
    # return new blocks inside the blocks list
    # ----------------------------------------------------------------------
    def profile(self, blocks, offset, overcut=False, name=None, pocket=False):
        undoinfo = []
        msg = ""
        newblocks = []

        remove = [
            "cut",
            "reverse",
            "climb",
            "conventional",
            "cw",
            "ccw",
            "in",
            "out",
        ]

        for bid in reversed(blocks):
            if self.blocks[bid].name() in ("Header", "Footer"):
                continue
            newpath = []
            for path in self.toPath(bid):
                if name is not None:
                    newname = Block.operationName(path.name, name)
                elif offset > 0:
                    newname = Block.operationName(
                        path.name, "out,conventional,ccw", remove
                    )
                    path.directionSet(
                        -1
                    )  # turn path to CCW (conventional when milling outside)
                else:
                    newname = Block.operationName(
                        path.name, "in,conventional,cw", remove
                    )
                    path.directionSet(
                        1
                    )  # turn path to CW (conventional when milling inside)

                if not path.isClosed():
                    m = f"Path: '{path.name}' is OPEN"
                    if m not in msg:
                        if msg:
                            msg += "\n"
                        msg += m

                opath = path.offsetClean(offset, overcut, newname)
                if opath:
                    newpath.extend(opath)
            if newpath:
                # remember length to shift all new blocks the are inserted
                # before
                before = len(newblocks)
                undoinfo.extend(
                    self.importPath(bid + 1, newpath, newblocks, True, False)
                )
                new = len(newblocks) - before
                for i in range(before):
                    newblocks[i] += new
                self.blocks[bid].enable = False
        self.addUndo(undoinfo)

        # return new blocks inside the blocks list
        del blocks[:]
        # TODO: Not sure how to make the pocket block to cut before profile
        # (to reduce machine load when cuting to dimension)
        # Idealy it should be generated as single block containing both pocket
        # and profile
        if pocket:
            msg = msg + self.pocket(
                sorted(newblocks), CNC.vars["diameter"], CNC.vars["stepover"] / 100, name, True, True
            )
            withpocketblocks=sorted(newblocks).copy()
            for i in range(0,len(withpocketblocks)):
                withpocketblocks[i]+=i
                withpocketblocks.append(withpocketblocks[i]+1)
            newblocks = sorted(withpocketblocks,reverse=True)
        blocks.extend(newblocks)
        return msg

    # ----------------------------------------------------------------------
    # Generate a pocket path
    # ----------------------------------------------------------------------
    def _pocket(self, path, diameter, stepover, depth):
        # FIXME: recursions are slow and shall be avoided! Replace recursion
        #        via a loop!

        # python's internal recursion limit hit us before bCNC's
        # limit came to place
        # so i increased python's limit to bCNC's limit + 100
        maxdepth = 10000
        import sys

        sys.setrecursionlimit(max(sys.getrecursionlimit(), maxdepth + 100))

        newpath = []
        if depth > maxdepth:
            return None
        if depth == 0:
            offset = diameter / 2.0
        else:
            offset = diameter * stepover

        opath = path.offset(offset)

        if not opath:
            return None

        opath.intersectSelf()
        opath.removeExcluded(path, offset)
        opath.removeZeroLength(abs(offset) / 100.0)
        opath = opath.split2contours()

#        if not opath:
#            return None
        if opath:
            for pout in opath:
                pin = self._pocket(pout, diameter, stepover, depth + 1)
                if not pin:
                    newpath.append(pout)

                # else: # FIXME
                # 1. Find closest node that we can move with
                #    a straight line without intersecting the path
                # 2. rotate the pout to start from this node
                # 3. join with a normal line
                # else
                # join with a rapid move as a separate path
                elif len(pin) == 1:
                    # FIXME maybe it is dangerous!!
                    # Have to check before making a straight move
                    pin[0].join(pout)
                    newpath.append(pin[0])

                else:
                    # FIXME needs to check if we can go in normal move
                    # needs to find the closest segment and rotate
                    # pin[-1].join(pout)
                    newpath.extend(pin)
                    newpath.append(pout)
        return newpath

    # ----------------------------------------------------------------------
    # make a pocket on block
    # return new blocks inside the blocks list
    # ----------------------------------------------------------------------
    def pocket(self, blocks, diameter, stepover, name, nested=False, updown=False):
        undoinfo = []
        msg = ""
        newblocks = []
        for bid in reversed(blocks):
            if self.blocks[bid].name() in ("Header", "Footer"):
                continue
            newpath = []
            for path in self.toPath(bid):
                if not path.isClosed():
                    m = f"Path: '{path.name}' is OPEN"
                    if m not in msg:
                        if msg:
                            msg += "\n"
                        msg += m
                    path.close()

                # Remove tiny segments
                path.removeZeroLength(abs(diameter) / 100.0)
                # Convert very small arcs to lines
                path.convert2Lines(abs(diameter) / 10.0)

                path.directionSet(
                    1
                )  # turn path to CW (conventional when milling inside)

                D = path.direction()
                if D == 0:
                    D = 1

                remove = [
                    "cut",
                    "reverse",
                    "climb",
                    "conventional",
                    "cw",
                    "ccw",
                    "pocket",
                ]
                if name is None:
                    path.name = Block.operationName(
                        path.name, "pocket,conventional,cw", remove
                    )
                else:
                    path.name = Block.operationName(path.name, name, remove)

                newpath.extend(self._pocket(path, -D * diameter, stepover, 0))

            if newpath:
                # remember length to shift all new blocks
                # the are inserted before
                before = len(newblocks)
                if updown:
                    undoinfo.extend(self.importPath(bid, newpath,
                        newblocks, True, False))
                else:
                    undoinfo.extend(
                        self.importPath(bid + 1, newpath, newblocks, True, False)
                    )
                new = len(newblocks) - before
                for i in range(before):
                    newblocks[i] += new
                if not nested:
                    self.blocks[bid].enable = False
        self.addUndo(undoinfo)

        # return new blocks inside the blocks list
        del blocks[:]
        blocks.extend(newblocks)
        return msg

    # ----------------------------------------------------------------------
    # make a trochoidal profile on block
    # offset +/- defines direction = tool/2
    # return new blocks inside the blocks list
    # ----------------------------------------------------------------------
    def trochprofile_cnc(
        self,
        blocks,
        offset,
        overcut=False,
        adaptative=True,
        adaptedRadius=0.0,
        cutDiam=0.0,
        tooldiameter=0.0,
        targetDepth=0.0,
        depthIncrement=0.0,
        tabsnumber=0.0,
        tabsWidth=0.0,
        tabsHeight=0.0,
    ):
        undoinfo = []
        msg = ""
        newblocks = []
        for bid in reversed(blocks):
            if self.blocks[bid].name() in ("Header", "Footer"):
                continue
            newpath = []
            for path in self.toPath(bid):
                explain = "Tr "
                if offset > 0:
                    explain += "out "
                elif offset < 0:
                    explain += "in "
                explain += str(cutDiam)
                if cutDiam != abs(2 * offset):
                    explain += " offs " + str(abs(offset) - cutDiam / 2.0)
                if offset < 0:
                    if adaptative:
                        explain += " Adapt bit " + str(tooldiameter)
                    if overcut:
                        explain += " overc"
                newname = Block.operationName(path.name, explain)

                if not path.isClosed():
                    m = f"Path: '{path.name}' is OPEN"
                    if m not in msg:
                        if msg:
                            msg += "\n"
                        msg += m

                # Remove tiny segments
                path.removeZeroLength(abs(offset) / 100.0)
                # Convert very small arcs to lines
                path.convert2Lines(abs(offset) / 10.0)
                D = path.direction()
                if D == 0:
                    D = 1
                opath = path.offset(D * offset, newname)
                if opath:
                    opath.intersectSelf()
                    opath.removeExcluded(path, D * offset)
                    opath.removeZeroLength(abs(offset) / 100.0)
                opath = opath.split2contours()
                if opath:
                    if overcut is True or adaptative is True:
                        for p in opath:
                            p.trochovercut(
                                D * offset, overcut, adaptative, adaptedRadius
                            )
                    newpath.extend(opath)
            if newpath:
                # remember length to shift all new blocks the are
                # inserted before
                before = len(newblocks)
                undoinfo.extend(
                    self.importPath(bid + 1, newpath, newblocks, True, False)
                )
                new = len(newblocks) - before
                for i in range(before):
                    newblocks[i] += new
                self.blocks[bid].enable = False
        self.addUndo(undoinfo)

        # return new blocks inside the blocks list
        del blocks[:]
        blocks.extend(newblocks)

        self.cut(
            reversed(blocks),
            targetDepth,
            depthIncrement,
            0,
            900,
            120,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
        )
        return msg

    # ----------------------------------------------------------------------
    def adaptative_clearence(
        self,
        blocks,
        offset,
        overcut=False,
        adaptative=True,
        adaptedRadius=0.0,
        cutDiam=0.0,
        tooldiameter=0.0,
        name=None,
    ):
        undoinfo = []
        msg = ""
        newblocks = []
        for bid in reversed(blocks):
            if self.blocks[bid].name() in ("Header", "Footer"):
                continue
            newpath = []
            for path in self.toPath(bid):
                explain = "Clear "
                if offset > 0:
                    explain += "out "
                elif offset < 0:
                    explain += "in "
                explain += str(cutDiam)
                if cutDiam != abs(2 * offset):
                    explain += " offs " + str(abs(offset) - cutDiam / 2.0)
                if offset < 0:
                    if adaptative:
                        explain += " Adapt bit " + str(tooldiameter)
                    if overcut:
                        explain += " overc"
                newname = Block.operationName(path.name, explain)

                if not path.isClosed():
                    m = f"Path: '{path.name}' is OPEN"
                    if m not in msg:
                        if msg:
                            msg += "\n"
                        msg += m

                # Remove tiny segments
                path.removeZeroLength(abs(offset) / 100.0)
                # Convert very small arcs to lines
                path.convert2Lines(abs(offset) / 10.0)
                D = path.direction()
                if D == 0:
                    D = 1
                opath = path.offset(D * offset, newname)
                if opath:
                    opath.intersectSelf()
                    opath.removeExcluded(path, D * offset)
                    opath.removeZeroLength(abs(offset) / 100.0)
                opath = opath.split2contours()
                if opath:
                    for p in opath:
                        p.two_bit_adaptative_cut(
                            D * offset, overcut, adaptative, adaptedRadius
                        )
                    newpath.extend(opath)
            if newpath:
                # remember length to shift all new blocks the are
                # inserted before
                before = len(newblocks)
                undoinfo.extend(
                    self.importPath(bid + 1, newpath, newblocks, True, False)
                )
                new = len(newblocks) - before
                for i in range(before):
                    newblocks[i] += new
                self.blocks[bid].enable = False
        self.addUndo(undoinfo)

        # return new blocks inside the blocks list
        blocks.extend(newblocks)
        return msg

    # ----------------------------------------------------------------------
    # draw a hole (circle with radius)
    # ----------------------------------------------------------------------
    def hole(self, bid, radius):
        block = self.blocks[bid]

        # Find starting location
        self.initPath(bid)
        for i, line in enumerate(block):
            cmds = CNC.parseLine(line)
            if cmds is None:
                continue
            self.cnc.motionStart(cmds)
            self.cnc.motionEnd()

        # FIXME: doesn't work; lid not defined
        # New lines to append
        pos = 1  # pos = lid + 1
        block.insert(pos, f"g0 {self.fmt('x', self.cnc.x + radius)}")
        pos += 1
        block.insert(pos, f"g1 {self.fmt('z', -0.001)}")
        pos += 1
        block.insert(pos, f"g2 {self.fmt('i', -radius)}")
        pos += 1

    # ----------------------------------------------------------------------
    # Modify the lines according to the supplied function and arguments
    # ----------------------------------------------------------------------
    def modify(self, items, func, tabFunc, *args):
        undoinfo = []
        old = {}  # Motion commands: Last value
        new = {}  # Motion commands: New value
        relative = False

        for bid, lid in self.iterate(items):
            block = self.blocks[bid]

            if isinstance(lid, int):
                cmds = CNC.parseLine(block[lid])
                if cmds is None:
                    continue
                self.cnc.motionStart(cmds)

                # Collect all values
                new.clear()
                for cmd in cmds:
                    if cmd.upper() == "G91":
                        relative = True
                    if cmd.upper() == "G90":
                        relative = False
                    c = cmd[0].upper()
                    # record only coordinates commands
                    if c not in "XYZIJKR":
                        continue
                    try:
                        new[c] = old[c] = float(cmd[1:]) * self.cnc.unit
                    except Exception:
                        new[c] = old[c] = 0.0

                # Modify values with func
                if func(new, old, relative, *args):
                    # Reconstruct new line
                    newcmd = []
                    present = ""
                    for cmd in cmds:
                        c = cmd[0].upper()
                        if c in "XYZIJKR":  # Coordinates
                            newcmd.append(self.fmt(c, new[c] / self.cnc.unit))
                        # Motion
                        elif c == "G" and int(cmd[1:]) in (0, 1, 2, 3):
                            newcmd.append(f"G{int(self.cnc.gcode)}")
                        else:  # the rest leave unchanged
                            newcmd.append(cmd)
                        present += c
                    # Append motion commands if not exist and changed
                    check = "XYZ"
                    if "I" in new or "J" in new or "K" in new:
                        check += "IJK"
                    for c in check:
                        try:
                            if c not in present and new.get(c) != old.get(c):
                                newcmd.append(
                                    self.fmt(c, new[c] / self.cnc.unit))
                        except Exception:
                            pass
                    undoinfo.append(
                        self.setLineUndo(bid, lid, " ".join(newcmd)))
                self.cnc.motionEnd()
                # reset arc offsets
                for i in "IJK":
                    if i in old:
                        old[i] = 0.0

        # FIXME I should add it later, check all functions using it
        self.addUndo(undoinfo)

    # ----------------------------------------------------------------------
    # Move position by dx,dy,dz
    # ----------------------------------------------------------------------
    def moveFunc(self, new, old, relative, dx, dy, dz):
        if relative:
            return False
        changed = False
        if "X" in new:
            changed = True
            new["X"] += dx
        if "Y" in new:
            changed = True
            new["Y"] += dy
        if "Z" in new:
            changed = True
            new["Z"] += dz
        return changed

    # ----------------------------------------------------------------------
    def orderLines(self, items, direction):
        if direction == "UP":
            self.orderUp(items)
        elif direction == "DOWN":
            self.orderDown(items)
        else:
            pass

    # ----------------------------------------------------------------------
    # Move position by dx,dy,dz
    # ----------------------------------------------------------------------
    def moveLines(self, items, dx, dy, dz=0.0):
        return self.modify(items, self.moveFunc, None, dx, dy, dz)

    # ----------------------------------------------------------------------
    # Rotate position by c(osine), s(ine) of an angle around center (x0,y0)
    # ----------------------------------------------------------------------
    def rotateFunc(self, new, old, relative, c, s, x0, y0):
        if "X" not in new and "Y" not in new:
            return False
        x = getValue("X", new, old)
        y = getValue("Y", new, old)
        new["X"] = c * (x - x0) - s * (y - y0) + x0
        new["Y"] = s * (x - x0) + c * (y - y0) + y0

        if "I" in new or "J" in new:
            i = getValue("I", new, old)
            j = getValue("J", new, old)
            if self.cnc.plane in (XY, XZ):
                new["I"] = c * i - s * j
            if self.cnc.plane in (XY, YZ):
                new["J"] = s * i + c * j
        return True

    # ----------------------------------------------------------------------
    # Transform (rototranslate) position with the following function:
    #   xn = c*x - s*y + xo
    #   yn = s*x + c*y + yo
    # it is like the rotate but the rotation center is not defined
    # ----------------------------------------------------------------------
    def transformFunc(self, new, old, relative, c, s, xo, yo):
        if "X" not in new and "Y" not in new:
            return False
        x = getValue("X", new, old)
        y = getValue("Y", new, old)
        new["X"] = c * x - s * y + xo
        new["Y"] = s * x + c * y + yo

        if "I" in new or "J" in new:
            i = getValue("I", new, old)
            j = getValue("J", new, old)
            new["I"] = c * i - s * j
            new["J"] = s * i + c * j
        return True

    # ----------------------------------------------------------------------
    # Rotate items around optional center (on XY plane)
    # ang in degrees (counter-clockwise)
    # ----------------------------------------------------------------------
    def rotateLines(self, items, ang, x0=0.0, y0=0.0):
        a = math.radians(ang)
        c = math.cos(a)
        s = math.sin(a)
        if ang in (0.0, 90.0, 180.0, 270.0, -90.0, -180.0, -270.0):
            c = round(c)  # round numbers to avoid nasty extra digits
            s = round(s)
        return self.modify(items, self.rotateFunc, None, c, s, x0, y0)

    # ----------------------------------------------------------------------
    # Use the orientation information to orient selected code
    # ----------------------------------------------------------------------
    def orientLines(self, items):
        if not self.orient.valid:
            return "ERROR: Orientation information is not valid"
        c = math.cos(self.orient.phi)
        s = math.sin(self.orient.phi)
        return self.modify(
            items,
            self.transformFunc,
            None,
            c,
            s,
            self.orient.xo,
            self.orient.yo
        )

    # ----------------------------------------------------------------------
    # Mirror Horizontal
    # ----------------------------------------------------------------------
    def mirrorHFunc(self, new, old, relative, *kw):
        changed = False
        for axis in "XI":
            if axis in new:
                new[axis] = -new[axis]
                changed = True
        if self.cnc.gcode in (2, 3):  # Change  2<->3
            self.cnc.gcode = 5 - self.cnc.gcode
            changed = True
        return changed

    # ----------------------------------------------------------------------
    # Mirror Vertical
    # ----------------------------------------------------------------------
    def mirrorVFunc(self, new, old, relative, *kw):
        changed = False
        for axis in "YJ":
            if axis in new:
                new[axis] = -new[axis]
                changed = True
        if self.cnc.gcode in (2, 3):  # Change  2<->3
            self.cnc.gcode = 5 - self.cnc.gcode
            changed = True
        return changed

    # ----------------------------------------------------------------------
    # Mirror horizontally/vertically
    # ----------------------------------------------------------------------
    def mirrorHLines(self, items):
        return self.modify(items, self.mirrorHFunc, None)

    # ----------------------------------------------------------------------
    def mirrorVLines(self, items):
        return self.modify(items, self.mirrorVFunc, None)

    # ----------------------------------------------------------------------
    # Round all digits with accuracy
    # ----------------------------------------------------------------------
    def roundFunc(self, new, old, relative):
        for name, value in new.items():
            new[name] = round(value, CNC.digits)
        return bool(new)

    # ----------------------------------------------------------------------
    # Round line by the amount of digits
    # ----------------------------------------------------------------------
    def roundLines(self, items, acc=None):
        if acc is not None:
            CNC.digits = acc
        return self.modify(items, self.roundFunc, None)

    # ----------------------------------------------------------------------
    # Inkscape g-code tools on slice/slice it raises the tool to the
    # safe height then plunges again.
    # Comment out all these patterns
    #
    # FIXME needs re-working...
    # ----------------------------------------------------------------------
    def inkscapeLines(self):

        # Loop over all blocks
        self.initPath()
        newlines = []
        last = -1  # line location when it was last raised with dx=dy=0.0

        for line in self.lines():
            # step id
            # 0 - normal cutting z<0
            # 1 - z>0 raised  with dx=dy=0.0
            # 2 - z<0 plunged with dx=dy=0.0
            cmd = CNC.parseLine(line)
            if cmd is None:
                newlines.append(line)
                continue
            self.cnc.motionStart(cmd)
            if self.cnc.dx == 0.0 and self.cnc.dy == 0.0:
                if self.cnc.z > 0.0 and self.cnc.dz > 0.0:
                    last = len(newlines)
                elif self.cnc.z < 0.0 and self.cnc.dz < 0.0 and last >= 0:
                    for i in range(last, len(newlines)):
                        s = newlines[i]
                        if s and s[0] != "(":
                            newlines[i] = f"({s})"
                    last = -1
            else:
                last = -1
            newlines.append(line)
            self.cnc.motionEnd()

        self.addUndo(self.setLinesUndo(newlines))

    # ----------------------------------------------------------------------
    # Remove the line number for lines
    # ----------------------------------------------------------------------
    def removeNlines(self, items):
        pass

    # ----------------------------------------------------------------------
    # Re-arrange using genetic algorithms a set of blocks to minimize
    # rapid movements.
    # ----------------------------------------------------------------------
    def optimize(self, items):
        n = len(items)

        matrix = []
        for i in range(n):
            matrix.append([0.0] * n)

        # Find distances between blocks (end to start)
        for i in range(n):
            block = self.blocks[items[i]]
            x1 = block.ex
            y1 = block.ey
            for j in range(n):
                if i == j:
                    continue
                block = self.blocks[items[j]]
                x2 = block.sx
                y2 = block.sy
                dx = x1 - x2
                dy = y1 - y2
                # Compensate for machines, which have different
                # speed of X and Y:
                dx /= CNC.feedmax_x
                dy /= CNC.feedmax_y
                matrix[i][j] = sqrt(dx * dx + dy * dy)

        best = [0]
        unvisited = list(range(1, n))
        while unvisited:
            last = best[-1]
            row = matrix[last]
            # from all the unvisited places search the closest one
            mindist = 1e30
            for i, u in enumerate(unvisited):
                d = row[u]
                if d < mindist:
                    mindist = d
                    si = i
            best.append(unvisited.pop(si))

        undoinfo = []
        for i in range(len(best)):
            b = best[i]
            if i == b:
                continue
            ptr = best.index(i)
            undoinfo.append(self.swapBlockUndo(items[i], items[b]))
            best[i], best[ptr] = best[ptr], best[i]
        self.addUndo(undoinfo, "Optimize")

    # ----------------------------------------------------------------------
    # Use probe information to modify the g-code to autolevel
    # ----------------------------------------------------------------------
    def compile(self, queue, stopFunc=None):
        paths = []

        def add(line, path):
            if line is not None:
                if isinstance(line, str):
                    queue.put(line + "\n")
                else:
                    queue.put(line)
            paths.append(path)

        autolevel = not self.probe.isEmpty()
        self.initPath()
        for line in CNC.compile(self.cnc.startup.splitlines()):
            add(line, None)

        every = 1
        for i, block in enumerate(self.blocks):
            if not block.enable:
                continue
            for j, line in enumerate(block):
                every -= 1
                if every <= 0:
                    if stopFunc is not None and stopFunc():
                        return None
                    every = 50

                newcmd = []
                cmds = CNC.compileLine(line)
                if cmds is None:
                    continue
                elif isinstance(cmds, str):
                    cmds = CNC.breakLine(cmds)
                else:
                    # either CodeType or tuple, list[] append at it as is
                    if (isinstance(cmds, types.CodeType)
                            or isinstance(cmds, int)):
                        add(cmds, None)
                    else:
                        add(cmds, (i, j))
                    continue

                skip = False
                expand = None
                self.cnc.motionStart(cmds)

                # FIXME append feed on cut commands. It will be obsolete
                # in grbl v1.0
                if CNC.appendFeed and self.cnc.gcode in (1, 2, 3):
                    # Check is not existing in cmds
                    for c in cmds:
                        if c[0] in ("f", "F"):
                            break
                    else:
                        cmds.append(
                            self.fmt("F", self.cnc.feed / self.cnc.unit))

                if (autolevel and self.cnc.gcode in (0, 1, 2, 3)
                        and self.cnc.mval == 0):
                    xyz = self.cnc.motionPath()
                    if not xyz:
                        # while auto-levelling, do not ignore non-movement
                        # commands, just append the line as-is
                        add(line, None)
                    else:
                        extra = ""
                        for c in cmds:
                            if c[0].upper() not in (
                                "G",
                                "X",
                                "Y",
                                "Z",
                                "I",
                                "J",
                                "K",
                                "R",
                            ):
                                extra += c
                        x1, y1, z1 = xyz[0]
                        if self.cnc.gcode == 0:
                            g = 0
                        else:
                            g = 1
                        for x2, y2, z2 in xyz[1:]:
                            for x, y, z in self.probe.splitLine(x1, y1, z1,
                                                                x2, y2, z2):
                                add(
                                    "".join([
                                        f"G{int(g)}",
                                        f"{self.fmt('X', x / self.cnc.unit)}",
                                        f"{self.fmt('Y', y / self.cnc.unit)}",
                                        f"{self.fmt('Z', z / self.cnc.unit)}",
                                        f"{extra}",
                                    ]),
                                    (i, j),
                                )
                                extra = ""
                            x1, y1, z1 = x2, y2, z2
                    self.cnc.motionEnd()
                    continue
                else:
                    # FIXME expansion policy here variable needed
                    # Canned cycles
                    if CNC.drillPolicy == 1 and self.cnc.gcode in (
                        81,
                        82,
                        83,
                        85,
                        86,
                        89,
                    ):
                        expand = self.cnc.macroGroupG8X()
                    # Tool change
                    elif self.cnc.mval == 6:
                        if CNC.toolPolicy == 0:
                            pass  # send to grbl
                        elif CNC.toolPolicy == 1:
                            skip = True  # skip whole line
                        elif CNC.toolPolicy >= 2:
                            expand = CNC.compile(self.cnc.toolChange())
                    self.cnc.motionEnd()

                if expand is not None:
                    for line in expand:
                        add(line, None)
                    expand = None
                    continue
                elif skip:
                    skip = False
                    continue

                for cmd in cmds:
                    c = cmd[0]
                    try:
                        value = float(cmd[1:])
                    except Exception:
                        value = 0.0
                    if c.upper() in ("F", "X", "Y", "Z",
                                     "I", "J", "K", "R", "P"):
                        cmd = self.fmt(c, value)
                    else:
                        opt = ERROR_HANDLING.get(cmd.upper(), 0)
                        if opt == SKIP:
                            cmd = None
                    if cmd is not None:
                        newcmd.append(cmd)

                add("".join(newcmd), (i, j))

        return paths
