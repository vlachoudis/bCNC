# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014
"""Document layer: Block, Probe, Orient, and GCode file/CAM operations."""

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

from CNC import CNC, ERROR_HANDLING, SKIP, XY, XZ, YZ

IDPAT = re.compile(r".*\bid:\s*(.*?)\)")
OPPAT = re.compile(r"(.*)\[(.*)\]")
BLOCKPAT = re.compile(r"^\(Block-([A-Za-z]+):\s*(.*)\)")

TOLERANCE = 1e-7
MAXINT = 1000000000  # python3 doesn't have maxint

# Motion words for inferred Header splitting. Canned cycles are the ones
# CNC.motionPath expands; G0 is rapid-only and does not end the pre-cut phase.
_MOTION_G = (0, 1, 2, 3, 81, 82, 83, 85, 86, 89)
_CUTTING_G = (1, 2, 3, 81, 82, 83, 85, 86, 89)
_CANNED_G = (81, 82, 83, 85, 86, 89)


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

    def write_encoded(self, f):
        f.write(self.write_header().encode())
        for line in self:
            if self.enable:
                f.write(f"{line}\n".encode())
            else:
                f.write(
                    f"(Block-X: {line.replace('(', '[').replace(')', ']')})\n".encode())

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
        # Inferred loads stay in the pre-cut phase until a real machining
        # move. load() and setLinesUndo() reset this with _blocksExist.
        self._preCut = True
        self._holdInHeader = False

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
    # Words on this line, plus modal motion, for inferred block boundaries.
    # Inherited G0 must not turn M3/M4, dwell, S/F words, or comments into
    # a rapid. A combined cutting move is never startup-only.
    # ----------------------------------------------------------------------
    @staticmethod
    def _lineWords(cmds):
        g_codes = []
        m_codes = []
        axis = False
        arc = False
        for cmd in cmds:
            if not cmd or not cmd[0].isalpha():
                continue
            letter = cmd[0].upper()
            try:
                value = float(cmd[1:]) if len(cmd) > 1 else 0.0
            except ValueError:
                continue
            if letter == "G":
                g_codes.append(int(value))
            elif letter == "M":
                m_codes.append(int(value))
            elif letter in "XYZABCUVW":
                axis = True
            elif letter in "IJKR":
                arc = True
        return g_codes, m_codes, axis, arc

    @staticmethod
    def _motionWords(g_codes):
        explicit = None
        dwell = False
        for code in g_codes:
            if code == 4:
                dwell = True
            elif code in _MOTION_G:
                explicit = code
        return explicit, dwell

    def _inspectLine(self, cmds):
        g_codes, m_codes, axis, arc = self._lineWords(cmds)
        explicit, dwell = self._motionWords(g_codes)
        spindle = any(code in (3, 4) for code in m_codes)
        # G4 X.. uses X as dwell time; there is no motion word on the line.
        if dwell and explicit is None:
            return "startup", False
        rapid, cutting = self._motionClass(explicit, axis, arc)
        return self._lineKind(cutting, rapid, spindle or dwell), rapid

    def _motionClass(self, explicit, axis, arc):
        motion = explicit if explicit is not None else self.cnc.gcode
        moved = (
            self.cnc.dx != 0.0 or self.cnc.dy != 0.0 or self.cnc.dz != 0.0
        )
        rapid = motion == 0 and (
            explicit == 0 or (explicit is None and axis and moved)
        )
        cutting = motion in _CUTTING_G and (
            motion in _CANNED_G or arc or axis or moved
        )
        return rapid, cutting

    @staticmethod
    def _lineKind(cutting, rapid, startup):
        if cutting:
            return "cut"
        if startup and not rapid:
            return "startup"
        if rapid:
            return "move"
        return "preface"

    # ----------------------------------------------------------------------
    # Fold provisional pre-cut blocks back into Header, keeping line order.
    # ----------------------------------------------------------------------
    def _mergePreCutPrefix(self):
        if len(self.blocks) <= 1:
            return
        header = self.blocks[0]
        for block in self.blocks[1:]:
            header.extend(block)
        del self.blocks[1:]

    # ----------------------------------------------------------------------
    # Explicit (Block-name) files keep authored grouping. Until the first
    # cut, an M3/M4 or dwell extends Header through the provisional
    # rapid prefix. Later spindle changes stay in the block that owns them.
    # Returns True when the line was placed.
    # ----------------------------------------------------------------------
    def _placePreCut(self, kind, line):
        if self._blocksExist or not self._preCut:
            return False
        if kind == "startup":
            self._mergePreCutPrefix()
            self._holdInHeader = True
        elif self._holdInHeader and kind == "cut":
            self._preCut = False
            self._holdInHeader = False
            if len(self.blocks) == 1:
                self.blocks.append(Block())
        elif not (self._holdInHeader and kind == "preface"):
            if kind in ("move", "cut"):
                self._holdInHeader = False
            if kind == "cut":
                self._preCut = False
            return False
        self.blocks[-1].append(line)
        return True

    # ----------------------------------------------------------------------
    # rapid move up = end of block
    # ----------------------------------------------------------------------
    def _placeLine(self, line, rapid):
        if self._blocksExist:
            self.blocks[-1].append(line)
        elif rapid and self.cnc.dz > 0.0:
            self.blocks[-1].append(line)
            self.blocks.append(Block())
        elif rapid and len(self.blocks) == 1:
            self.blocks.append(Block())
            self.blocks[-1].append(line)
        else:
            self.blocks[-1].append(line)

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
        kind, rapid = self._inspectLine(cmds)
        if not self._placePreCut(kind, line):
            self._placeLine(line, rapid)

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
        self._preCut = True
        self._holdInHeader = False
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
        dwell=None
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
                if dwell:
                    block.append(f"g4 {self.fmt('p', float(dwell))}")

            # Rapid to beginning of the path
            block.append(f"g0 {self.fmt('x', x, 7)} {self.fmt('y', y, 7)}")

            # Descend to pass (plunge to the beginning of path)
            if entry:
                # if entry feed to Z
                block.append(CNC.zenter(max(zh, ztab), 7))
            else:
                # without entry just rapid to Z
                block.append(f"g0 {self.fmt('z', max(zh, ztab), 7)}")
                if dwell:
                    block.append(f"g4 {self.fmt('p', float(dwell))}")

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
                if dwell:
                    block.append(f"g4 {self.fmt('p', float(dwell))}")

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
        self._preCut = True
        self._holdInHeader = False
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
    # Extract motion subsegments from selected blocks.
    # Each item is [start, end, exclude, length].
    # ----------------------------------------------------------------------
    def extractSegments(self, bids, exclude_rapid=True, disable=False):
        allSegments = []
        for bid in bids:
            bidSegments = []
            block = self.blocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            self.initPath(bid)
            for line in block:
                try:
                    cmd = self.cnc.breakLine(
                        self.evaluate(self.cnc.compileLine(line))
                    )
                except Exception:
                    cmd = None
                if not cmd:
                    continue

                self.cnc.motionStart(cmd)
                xyz = self.cnc.motionPath()
                self.cnc.motionEnd()
                if not xyz or len(xyz) < 2:
                    continue

                exclude = (
                    xyz[0][0] == xyz[1][0] and xyz[0][1] == xyz[1][1]
                ) or (exclude_rapid and self.cnc.gcode == 0)

                for i in range(len(xyz) - 1):
                    A, B = xyz[i], xyz[i + 1]
                    length = math.sqrt(
                        (B[0] - A[0]) ** 2
                        + (B[1] - A[1]) ** 2
                        + (B[2] - A[2]) ** 2
                    )
                    bidSegments.append([A, B, exclude, length])
            allSegments.append(bidSegments)

            if disable:
                block.enable = False

        return allSegments

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
