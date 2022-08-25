#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# Please consult the flair documentation for the license
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH

# Author    :Vasilis.Vlachoudis@cern.ch
# Date:     10-Mar-2015

import math
import sys

import spline
from bmath import Vector
from Helpers import to_zip

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


EPS = 0.000001
EPS2 = EPS**2

# Just to avoid repeating errors
errors = {}


# -----------------------------------------------------------------------------
def error(msg):
    global errors
    if msg in errors:
        errors[msg] += 1
    else:
        sys.stderr.write(msg)
        errors[msg] = 1


# =============================================================================
# Entity holder
# =============================================================================
class Entity(dict):
    CLOSED = 0x01
    PERIODIC = 0x02
    RATIONAL = 0x04
    PLANAR = 0x08
    LINEAR = 0x10

    ELLIPSE_SEGMENTS = 100

    COLORS = [  # Acad colors
        "#000000",
        "#0000FF",
        "#00FFFF",
        "#00FF00",
        "#FFFF00",
        "#FF0000",
        "#FF00FF",
        "#FFFFFF",
        "#414141",
        "#808080",
        "#0000FF",
        "#AAAAFF",
        "#0000BD",
        "#7E7EBD",
        "#000081",
        "#565681",
        "#000068",
        "#454568",
        "#00004F",
        "#35354F",
        "#003FFF",
        "#AABFFF",
        "#002EBD",
        "#7E8DBD",
        "#001F81",
        "#566081",
        "#001968",
        "#454E68",
        "#00134F",
        "#353B4F",
        "#007FFF",
        "#AAD4FF",
        "#005EBD",
        "#7E9DBD",
        "#004081",
        "#566B81",
        "#003468",
        "#455668",
        "#00274F",
        "#35424F",
        "#00BFFF",
        "#AAEAFF",
        "#008DBD",
        "#7EADBD",
        "#006081",
        "#567681",
        "#004E68",
        "#455F68",
        "#003B4F",
        "#35494F",
        "#00FFFF",
        "#AAFFFF",
        "#00BDBD",
        "#7EBDBD",
        "#008181",
        "#568181",
        "#006868",
        "#456868",
        "#004F4F",
        "#354F4F",
        "#00FFBF",
        "#AAFFEA",
        "#00BD8D",
        "#7EBDAD",
        "#008160",
        "#568176",
        "#00684E",
        "#45685F",
        "#004F3B",
        "#354F49",
        "#00FF7F",
        "#AAFFD4",
        "#00BD5E",
        "#7EBD9D",
        "#008140",
        "#56816B",
        "#006834",
        "#456856",
        "#004F27",
        "#354F42",
        "#00FF3F",
        "#AAFFBF",
        "#00BD2E",
        "#7EBD8D",
        "#00811F",
        "#568160",
        "#006819",
        "#45684E",
        "#004F13",
        "#354F3B",
        "#00FF00",
        "#AAFFAA",
        "#00BD00",
        "#7EBD7E",
        "#008100",
        "#568156",
        "#006800",
        "#456845",
        "#004F00",
        "#354F35",
        "#3FFF00",
        "#BFFFAA",
        "#2EBD00",
        "#8DBD7E",
        "#1F8100",
        "#608156",
        "#196800",
        "#4E6845",
        "#134F00",
        "#3B4F35",
        "#7FFF00",
        "#D4FFAA",
        "#5EBD00",
        "#9DBD7E",
        "#408100",
        "#6B8156",
        "#346800",
        "#566845",
        "#274F00",
        "#424F35",
        "#BFFF00",
        "#EAFFAA",
        "#8DBD00",
        "#ADBD7E",
        "#608100",
        "#768156",
        "#4E6800",
        "#5F6845",
        "#3B4F00",
        "#494F35",
        "#FFFF00",
        "#FFFFAA",
        "#BDBD00",
        "#BDBD7E",
        "#818100",
        "#818156",
        "#686800",
        "#686845",
        "#4F4F00",
        "#4F4F35",
        "#FFBF00",
        "#FFEAAA",
        "#BD8D00",
        "#BDAD7E",
        "#816000",
        "#817656",
        "#684E00",
        "#685F45",
        "#4F3B00",
        "#4F4935",
        "#FF7F00",
        "#FFD4AA",
        "#BD5E00",
        "#BD9D7E",
        "#814000",
        "#816B56",
        "#683400",
        "#685645",
        "#4F2700",
        "#4F4235",
        "#FF3F00",
        "#FFBFAA",
        "#BD2E00",
        "#BD8D7E",
        "#811F00",
        "#816056",
        "#681900",
        "#684E45",
        "#4F1300",
        "#4F3B35",
        "#FF0000",
        "#FFAAAA",
        "#BD0000",
        "#BD7E7E",
        "#810000",
        "#815656",
        "#680000",
        "#684545",
        "#4F0000",
        "#4F3535",
        "#FF003F",
        "#FFAABF",
        "#BD002E",
        "#BD7E8D",
        "#81001F",
        "#815660",
        "#680019",
        "#68454E",
        "#4F0013",
        "#4F353B",
        "#FF007F",
        "#FFAAD4",
        "#BD005E",
        "#BD7E9D",
        "#810040",
        "#81566B",
        "#680034",
        "#684556",
        "#4F0027",
        "#4F3542",
        "#FF00BF",
        "#FFAAEA",
        "#BD008D",
        "#BD7EAD",
        "#810060",
        "#815676",
        "#68004E",
        "#68455F",
        "#4F003B",
        "#4F3549",
        "#FF00FF",
        "#FFAAFF",
        "#BD00BD",
        "#BD7EBD",
        "#810081",
        "#815681",
        "#680068",
        "#684568",
        "#4F004F",
        "#4F354F",
        "#BF00FF",
        "#EAAAFF",
        "#8D00BD",
        "#AD7EBD",
        "#600081",
        "#765681",
        "#4E0068",
        "#5F4568",
        "#3B004F",
        "#49354F",
        "#7F00FF",
        "#D4AAFF",
        "#5E00BD",
        "#9D7EBD",
        "#400081",
        "#6B5681",
        "#340068",
        "#564568",
        "#27004F",
        "#42354F",
        "#3F00FF",
        "#BFAAFF",
        "#2E00BD",
        "#8D7EBD",
        "#1F0081",
        "#605681",
        "#190068",
        "#4E4568",
        "#13004F",
        "#3B354F",
        "#333333",
        "#505050",
        "#696969",
        "#828282",
        "#BEBEBE",
        "#FFFFFF",
    ]

    # ----------------------------------------------------------------------
    def __init__(self, t, n=None):
        """Constructor"""
        self.type = t
        self.name = n
        self._invert = False
        self._initCache()

    # ----------------------------------------------------------------------
    def __repr__(self):
        out = f"{self.type} {self.name} {self.start()} {self.end()}"
        if self.type == "ARC":
            out = " ".join([
                out,
                f"R={self.radius():g}",
                f"sPhi={self.startPhi():g}",
                f"ePhi={self.endPhi():g}",
            ])
        return out

    # ----------------------------------------------------------------------
    def _initCache(self, s=None, e=None):
        """Initialize entity"""
        self._start = s
        self._end = e

    # ----------------------------------------------------------------------
    def clone(self):
        """Create a replica of the entity"""
        entity = Entity(self.type, self.name)
        entity.update(self)
        return entity

    # ----------------------------------------------------------------------
    def point(self, idx=0):
        """return 2D point 10+idx,20+idx"""
        return Vector(self.get(10 + idx, 0), self.get(20 + idx, 0))

    point2D = point
    center = point

    # ----------------------------------------------------------------------
    def point3D(self, idx=0):
        """return 3D point 10+idx,20+idx"""
        return Vector(
            self.get(10 + idx), self.get(20 + idx), self.get(30 + idx))

    # ----------------------------------------------------------------------
    def radius(self):
        return self.get(40, 0)

    # ----------------------------------------------------------------------
    def startPhi(self):
        return self.get(50, 0)

    # ----------------------------------------------------------------------
    def endPhi(self):
        return self.get(51, 0)

    # ----------------------------------------------------------------------
    def bulge(self):
        return self.get(42, 0)

    # ----------------------------------------------------------------------
    def flag(self):
        return self.get(70, 0)

    # ----------------------------------------------------------------------
    def color(self):
        try:
            return Entity.COLORS[self.get(62, 0)]
        except Exception:
            return None

    # ----------------------------------------------------------------------
    def isClosed(self):
        return bool(self.flag() & Entity.CLOSED)

    # ----------------------------------------------------------------------
    # Return start point
    # ----------------------------------------------------------------------
    def start(self):
        if self._start is None:
            self._calcEndPoints()
        if self._invert:
            return self._end
        else:
            return self._start

    # ----------------------------------------------------------------------
    # Return end point
    # ----------------------------------------------------------------------
    def end(self):
        if self._end is None:
            self._calcEndPoints()
        if self._invert:
            return self._start
        else:
            return self._end

    # ----------------------------------------------------------------------
    # Calculate start and end points
    # ----------------------------------------------------------------------
    def _calcEndPoints(self):
        if self.type == "LINE":
            self._start = self.point()
            self._end = self.point(1)
        elif self.type == "CIRCLE":
            x, y = self.point()
            r = self.radius()
            self._start = self._end = Vector(x + r, y)
        elif self.type == "ARC":
            x, y = self.point()
            r = self.radius()
            s = math.radians(self.startPhi())
            self._start = Vector(x + r * math.cos(s), y + r * math.sin(s))
            s = math.radians(self.endPhi())
            self._end = Vector(x + r * math.cos(s), y + r * math.sin(s))
        elif self.type in ("POLYLINE", "LWPOLYLINE", "SPLINE"):
            self._start = Vector(self[10][0], self[20][0])
            if self.isClosed():
                self._end = Vector(self[10][0], self[20][0])
            else:
                self._end = Vector(self[10][-1], self[20][-1])
        elif self.type in ("POINT", "ELLIPSE", "DIMENSION", "@START"):
            self._start = self._end = self.point()
        else:
            error("Cannot handle entity type: "
                  + f"{self.type} in layer: {self.name}\n")
            self._start = self._end = self.point()

    # ----------------------------------------------------------------------
    def invert(self):
        """Invert entity if needed to allow continuity of motion"""
        self._invert = not self._invert
        self._start, self._end = self._end, self._start

    # ----------------------------------------------------------------------
    def translate(self, dx, dy=None, dz=None):
        """Translate entity by vector dx or (dx,dy,dz) coordinates"""
        if not isinstance(dx, float):
            dx, dy, dz = dx

        # add d to self[idx]
        def add(from_, to_, d):
            if d is None:
                return
            for idx in range(from_, to_):
                try:
                    value = self[idx]
                    if isinstance(value, list):
                        for i in range(len(value)):
                            value[i] += d
                    else:
                        self[idx] += d
                except KeyError:
                    return

        add(10, 20, dx)
        add(20, 30, dy)
        add(30, 40, dz)
        self._initCache()

    # ----------------------------------------------------------------------
    def scale(self, sx, sy=None, sz=None):
        """Scale entity by vector sx or (sx,sy,sz) coordinates"""
        if not isinstance(sx, float):
            sx, sy, sz = sx

        # multiply by s to self[idx]
        def mult(from_, to_, s):
            if s is None or s == 1.0:
                return
            for idx in range(from_, to_):
                try:
                    value = self[idx]
                    if isinstance(value, list):
                        for i in range(len(value)):
                            value[i] += s
                    else:
                        self[idx] *= s
                except KeyError:
                    return

        mult(10, 20, sx)
        mult(20, 30, sy)
        mult(30, 40, sz)

        if self.type in ("ARC", "CIRCLE"):
            # Convert to Ellpise if sx!=sy
            if abs(sx - sy) > 1e-6:
                error("Non uniform scaling on ARC/CIRCLE is not supported")
            self[40] *= sx

        self._initCache()

    # ----------------------------------------------------------------------
    def rotate(self, r):
        """Rotate entity by angle r"""
        error("Rotation of blocks is not supported for the moment" "")

    # ----------------------------------------------------------------------
    # Convert entity to polyline
    # FIXME needs to be adaptive to the precision requested from the saggita
    # ----------------------------------------------------------------------
    def convert2Polyline(self, splineSegs):
        """Convert complex objects (SPLINE,ELLIPSE) to polylines"""
        if self.type == "SPLINE":
            # Convert to polyline
            xyz = to_zip(self[10], self[20], self[30])
            flag = int(self.get(70, 0))
            closed = bool(flag & Entity.CLOSED)
            knots = self[40]
            xx, yy, zz = spline.spline2Polyline(
                xyz, int(self[71]), closed, splineSegs, knots
            )
            self[10] = xx
            self[20] = yy
            self[30] = zz
            self[42] = 0  # bulge FIXME maybe I should use it
            self.type = "LWPOLYLINE"

        elif self.type == "ELLIPSE":
            center = self.start()
            major = self.point(1)
            ratio = self.get(40, 1.0)
            sPhi = self.get(41, 0.0)
            ePhi = self.get(42, 2.0 * math.pi)

            # minor length
            major_length = major.normalize()
            minor_length = ratio * major_length

            xx = []
            yy = []
            if ePhi < sPhi:
                ePhi += 2.0 * math.pi
            nseg = int((ePhi - sPhi) / math.pi * Entity.ELLIPSE_SEGMENTS)
            dphi = (ePhi - sPhi) / float(nseg)
            phi = sPhi
            for i in range(nseg + 1):
                vx = major_length * math.cos(phi)
                vy = minor_length * math.sin(phi)
                xx.append(vx * major[0] - vy * major[1] + center[0])
                yy.append(vx * major[1] + vy * major[0] + center[1])
                phi += dphi
            self[10] = xx
            self[20] = yy
            self[42] = 0  # bulge FIXME maybe I should use it
            self.type = "LWPOLYLINE"
        self._initCache()

    # ----------------------------------------------------------------------
    # Read vertex for POLYLINE
    # Very bad!!
    # ----------------------------------------------------------------------
    def _readVertex(self, dxf):
        self[10] = [0.0]
        self[20] = [0.0]
        self[30] = [0.0]
        self[42] = [0.0]

        while True:
            tag, value = dxf.read()
            if tag is None:
                return
            if tag == 0:
                if value == "SEQEND":
                    # Vertex sequence end
                    tag, value = dxf.read()
                    if tag != 8:
                        dxf.push(tag, value)
                    return
                elif value == "VERTEX":
                    self[10].append(0.0)
                    self[20].append(0.0)
                    self[30].append(0.0)
                    self[42].append(0.0)
                else:
                    raise Exception(f"Entity {value} found in wrong context")

            elif tag in (10, 20, 30, 42):
                self[tag][-1] = value

    # ----------------------------------------------------------------------
    # Read entity until next block
    # ----------------------------------------------------------------------
    def read(self, dxf):
        """Read entity from a dxf file"""
        while True:
            tag, value = dxf.read()
            if tag is None:
                return
            if tag == 0:
                if self.type == "POLYLINE":
                    self._readVertex(dxf)
                    return self
                else:
                    dxf.push(tag, value)
                    return self
            elif tag == 8:
                self.name = str(value)
            else:
                existing = self.get(tag)

                if tag == 42 and self.type == "LWPOLYLINE":
                    # Replace last value
                    self[42][-1] = value
                elif existing is None:
                    self[tag] = value
                elif isinstance(existing, list):
                    existing.append(value)
                else:
                    self[tag] = [existing, value]
                # Synchronize optional bulge with number of vertices
                if tag == 10 and self.type == "LWPOLYLINE":
                    bulge = self.get(42)
                    if bulge is None:
                        self[42] = [0.0]
                    else:
                        self[42].append(0.0)


# =============================================================================
# DXF layer
# =============================================================================
class Layer:
    # ----------------------------------------------------------------------
    def __init__(self, name, tbl=None):
        self.name = name
        if tbl is None:
            self.table = {}
        else:
            self.table = tbl
        self.entities = []
        self._sorted = False

    # ----------------------------------------------------------------------
    def append(self, item):
        self._sorted = False
        self.entities.append(item)

    # ----------------------------------------------------------------------
    def isFrozen(self):
        return self.table.get(70, 0) & 1

    # ----------------------------------------------------------------------
    def color(self):
        try:
            return Entity.COLORS[self.table.get(62, 0)]
        except Exception:
            return None

    # ----------------------------------------------------------------------
    def __repr__(self):
        return f"Layer: {self.name}"

    # ----------------------------------------------------------------------
    # Sort layer in continuation order of entities
    # where the end of of the previous is the start of the new one
    #
    # Add an new special marker for starting an entity with TYPE="@START"
    # ----------------------------------------------------------------------
    def sort(self):
        if self._sorted:
            return
        self._sorted = True
        new = []

        # Move all points to beginning
        i = 0
        while i < len(self.entities):
            if self.entities[i].type == "POINT":
                new.append(self.entities[i])
                del self.entities[i]
            elif self.entities[i].type == "INSERT":
                new.append(self.entities[i])
                del self.entities[i]
            else:
                i += 1

        if not self.entities:
            self.entities = new
            return

        # ---
        def pushStart():
            # Find starting point and add it to the new list
            start = Entity("@START", self.name)
            s = self.entities[0].start()
            start._initCache(s, s)
            new.append(start)

        # Push first element as start point
        pushStart()

        # Repeat until all entities are used
        while self.entities:
            # End point
            ex, ey = new[-1].end()

            # Find the entity that starts after the last one
            for i, entity in enumerate(self.entities):
                # Try starting point
                sx, sy = entity.start()
                d2 = (sx - ex) ** 2 + (sy - ey) ** 2
                err = EPS2 * ((abs(sx) + abs(ex)) ** 2
                              + (abs(sy) + abs(ey)) ** 2
                              + 1.0)
                if d2 < err:
                    new.append(entity)
                    del self.entities[i]
                    break

                # Try ending point (inverse)
                sx, sy = entity.end()
                d2 = (sx - ex) ** 2 + (sy - ey) ** 2
                err = EPS2 * ((abs(sx) + abs(ex)) ** 2
                              + (abs(sy) + abs(ey)) ** 2
                              + 1.0)
                if d2 < err:
                    entity.invert()
                    new.append(entity)
                    del self.entities[i]
                    break

            else:
                # Not found push a new start point and
                pushStart()

        self.entities = new


# =============================================================================
# DXF Block
# Block-type flags (bit coded values, may be combined):
#   1 = This is an anonymous block generated by hatching, associative
#       dimensioning, other internal operations, or an application.
#   2 = This block has non-constant attribute definitions (this bit is
#       not set if the block has any attribute definitions that are
#       constant, or has no attribute definitions at all).
#   4 = This block is an external reference (xref).
#   8 = This block is an xref overlay.
#  16 = This block is externally dependent.
#  32 = This is a resolved external reference, or dependent of an external
#       reference (ignored on input).
#  64 = This definition is a referenced external reference (ignored on input).
# =============================================================================
class Block(dict):
    # ----------------------------------------------------------------------
    def __init__(self):
        self.name = ""
        self.type = 0
        self.layer = "0"
        self.desc = ""
        self.base = Vector()
        self.layers = {}  # entities per layer diction of lists

    # ----------------------------------------------------------------------
    def __repr__(self):
        return f"Block: {self.name} [{int(self.type)}] Base:{str(self.base)}"

    # ----------------------------------------------------------------------
    def sort(self):
        for layer in self.layers.values():
            layer.sort()

    # ----------------------------------------------------------------------
    # Read block until next block
    # ----------------------------------------------------------------------
    def read(self, dxf):
        while True:
            tag, value = dxf.read()
            if tag is None:
                return
            if tag == 0:
                if value in ("BLOCK", "ENDBLK"):
                    dxf.push(tag, value)
                    return self
                else:
                    entity = Entity(value)
                    entity.read(dxf)
                    if entity.type in ("HATCH",):
                        continue  # ignore
                    try:
                        layer = self.layers[entity.name]
                    except KeyError:
                        layer = Layer(entity.name)
                        self.layers[entity.name] = layer
                    layer.append(entity)
            elif tag == 3:
                self.name = str(value)
            elif tag == 4:
                self.desc = str(value)
            elif tag == 8:
                self.layer = str(value)
            elif tag == 70:
                self.type = int(value)
            elif tag == 10:
                self.base[0] = float(value)
            elif tag == 20:
                self.base[1] = float(value)
            elif tag == 30:
                self.base[2] = float(value)
            else:
                self[tag] = value


# =============================================================================
# DXF importer/exporter class
# =============================================================================
class DXF:
    # Default drawing units for AutoCAD DesignCenter blocks:
    UNITLESS = 0
    INCHES = 1
    FEET = 2
    MILES = 3
    MILLIMETERS = 4
    CENTIMETERS = 5
    METERS = 6
    KILOMETERS = 7
    MICROINCHES = 8
    MILS = 9
    YARDS = 10
    ANGSTROMS = 11
    NANOMETERS = 12
    MICRONS = 13
    DECIMETERS = 14
    DECAMETERS = 15
    HECTOMETERS = 16
    GIGAMETERS = 17
    ASTRONOMICAL_UNITS = 18
    LIGHT_YEARS = 19
    PARSECS = 20

    # Convert Units to mm
    _TOMM = [
        1.0,  # UNITLESS           = 0
        25.4,  # INCHES             = 1
        25.4 * 12,  # FEET               = 2
        1609.34e3,  # MILES              = 3
        1.0,  # MILLIMETERS        = 4
        10.0,  # CENTIMETERS        = 5
        1000.0,  # METERS             = 6
        1e6,  # KILOMETERS         = 7
        25.4e-6,  # MICROINCHES        = 8
        25.4e-3,  # MILS               = 9
        915.4,  # YARDS              = 10
        1e-7,  # ANGSTROMS          = 11
        1e-9,  # NANOMETERS         = 12
        1e-6,  # MICRONS            = 13
        100.0,  # DECIMETERS         = 14
        10000.0,  # DECAMETERS         = 15
        100000.0,  # HECTOMETERS        = 16
        1e12,  # GIGAMETERS         = 17
        1.496e14,  # ASTRONOMICAL_UNITS = 18
        9.461e18,  # LIGHT_YEARS        = 19
        3.086e19,  # PARSECS            = 20
    ]

    # ----------------------------------------------------------------------
    def __init__(self, filename=None, mode="r"):
        self._f = None
        if filename:
            self.open(filename, mode)
        else:
            self.init()

    # ----------------------------------------------------------------------
    def init(self):
        self.title = "dxf-class"
        self.units = DXF.UNITLESS
        self.layers = {}  # entities per layer diction of lists
        self.blocks = {}
        self._saved = None
        self.splineSegs = 8
        self.vars = {}
        errors.clear()

    # ----------------------------------------------------------------------
    def __getitem__(self, var):
        return self.vars[var]

    # ----------------------------------------------------------------------
    def entities(self, name):
        """Return all entries for the layer name"""
        return self.layers[name].entities

    # ----------------------------------------------------------------------
    def convert(self, value, units):
        """Convert units to another format"""
        f = self._TOMM[self.units] / DXF._TOMM[units]

        if isinstance(value, float):
            return value * f

        elif isinstance(value, Vector):
            new = Vector(value)
            for i in range(len(value)):
                new[i] *= f
            return new

        elif isinstance(value, list):
            new = []
            for x in value:
                new.append(x * f)
            return new

        else:
            raise Exception(f"Cannot convert type {type(value)} {str(value)}")

    # ----------------------------------------------------------------------
    def open(self, filename, mode):
        """Open filename for reading or writing"""
        self._f = open(filename, mode)
        self.init()

    # ----------------------------------------------------------------------
    def close(self):
        """Close opened file"""
        self._f.close()

    # ----------------------------------------------------------------------
    # From the DXF reference manual
    # http://www.autodesk.com/techpubs/autocad/acad2000/dxf/
    #   group_code_value_types_dxf_01.htm
    #
    # Code range    python      Group value type
    # 0-9           str         String. (With the introduction of extended
    #                           symbol names
    #           in AutoCAD 2000, the 255 character limit has been lifted.
    #           There is no explicit limit to the number of bytes per line,
    #           although most lines should fall within 2049 bytes.)
    # 10-59         float       Double precision 3D point
    # 60-79         int         16-bit integer value
    # 90-99         int         32-bit integer value
    # 100           str         String (255-character maximum; less for Unicode strings)
    # 102           str         String (255-character maximum; less for Unicode strings)
    # 105           str         String representing hexadecimal (hex) handle value
    # 140-147       float       Double precision scalar floating-point value
    # 170-175       int         16-bit integer value
    # 280-289       int         8-bit integer value
    # 300-309       str         Arbitrary text string
    # 310-319       str         String representing hex value of binary chunk
    # 320-329       str         String representing hex handle value
    # 330-369       str         String representing hex object IDs
    # 370-379       int         8-bit integer value
    # 380-389       int         8-bit integer value
    # 390-399       str         String representing hex handle value
    # 400-409       int         16-bit integer value
    # 410-419       str         String
    # 999           str         Comment (string)
    # 1000-1009     str         String. (Same limits as indicated with 0-9 code range.)
    # 1010-1059     float       Floating-point value
    # 1060-1070     int         16-bit integer value
    # 1071          int         32-bit integer value
    # ----------------------------------------------------------------------
    def read(self):
        """Read one pair tag,value either from file or previously saved"""
        if self._saved is not None:
            tv = self._saved
            self._saved = None
            return tv

        # read the tag
        line = self._f.readline()
        if not line:
            return None, None
        try:
            tag = int(line.strip())
        except Exception:
            error(f"Error reading line {line}, tag was expected\n")
            return None, None

        # and the value
        value = self._f.readline().strip()

        # change the type depending on the tag range
        # float
        if (
            10 <= tag <= 59
            or 140 <= tag <= 147
            or 210 <= tag <= 239
            or 1010 <= tag <= 1059
        ):
            try:
                value = float(value)
            except Exception:
                error(f"Error reading line '{line}', tag={int(tag)}, "
                      + f"floating point expected found \"{value}\"\n")
                return None, None

        # int
        elif (
            60 <= tag <= 79
            or 90 <= tag <= 99
            or 170 <= tag <= 175
            or 280 <= tag <= 289
            or 370 <= tag <= 389
            or 400 <= tag <= 409
            or 1060 <= tag <= 1071
        ):
            try:
                value = int(value)
            except Exception:
                error(f"Error reading line '{line}', tag={int(tag)}, "
                      + f"integer expected found \"{value}\"\n")
                return None, None

        return tag, value

    # ----------------------------------------------------------------------
    def peek(self):
        """peek the next tag,value pair"""
        tag, value = self.read()
        self.push(tag, value)
        return tag, value

    # ----------------------------------------------------------------------
    def push(self, tag, value):
        """save the tag, value for the next read
        WARNING only one depth is supported"""
        self._saved = (tag, value)

    # ----------------------------------------------------------------------
    def mustbe(self, t, v=None):
        """Read next tag, value pair which must be (t,v)
        otherwise report error"""
        tag, value = self.read()
        if t != tag:
            self.push(tag, value)
            return False
        if v is not None and v != value:
            self.push(tag, value)
            return False
        return True

    # ----------------------------------------------------------------------
    def skipBlock(self):
        """Skip everything until next entity/block"""
        while True:
            tag, value = self.read()
            if tag is None or tag == 0:
                self.push(tag, value)
                return

    # ----------------------------------------------------------------------
    def skipSection(self):
        """Skip section"""
        while True:
            tag, value = self.read()
            if tag is None or (tag == 0 and value == "ENDSEC"):
                return

    # ----------------------------------------------------------------------
    def readTitle(self):
        """Read the title as the first item in DXF"""
        tag, value = self.read()
        if tag == 999:
            self.title = value
        else:
            self.push(tag, value)

    # ----------------------------------------------------------------------
    def readHeader(self):
        """Read header section"""
        var = None
        while True:
            tag, value = self.read()
            if tag is None or (tag == 0 and value == "ENDSEC"):
                return
            elif tag == 9:
                var = value
            else:
                self.vars[var] = value
                if tag == 70:
                    if var == "$MEASUREMENT":
                        value = int(value)
                        if value == 0:
                            self.units = DXF.INCHES
                        else:
                            self.units = DXF.MILLIMETERS
                    elif var == "$INSUNITS":
                        self.units = int(value)

                    elif var == "$SPLINESEGS":
                        self.splineSegs = int(value)

    # ----------------------------------------------------------------------
    def addEntity(self, entity):
        """Add entity to the appropriate layer"""
        try:
            layer = self.layers[entity.name]
        except KeyError:
            layer = Layer(entity.name)
            self.layers[entity.name] = layer
        layer.append(entity)

    # ----------------------------------------------------------------------
    def readEntities(self):
        """Read entities section"""
        while True:
            tag, value = self.read()
            if tag is None:
                return
            elif value == "ENDSEC":
                return None
            entity = Entity(value)
            entity.read(self)
            if entity.type in ("HATCH",):
                continue  # ignore
            self.addEntity(entity)

    # ----------------------------------------------------------------------
    def readBlocks(self):
        """Read blocks section"""
        block = None
        while True:
            tag, value = self.read()
            if tag is None:
                return
            elif tag == 0:
                if value == "ENDSEC":
                    return None
                elif value == "BLOCK":
                    block = Block()
                    block.read(self)
                    self.blocks[block.name] = block
                elif value == "ENDBLK":
                    self.skipBlock()
                else:
                    error(f"Unknown {value} section in blocks")

    # ----------------------------------------------------------------------
    def readTable(self):
        """Read one table"""
        tag, value = self.read()
        if value == "ENDSEC":
            return None
        else:
            table = {}
        table["type"] = value

        while True:
            tag, value = self.read()
            if tag is None:
                return
            if tag == 0:
                self.push(tag, value)
                return table
            elif tag == 2:
                table["name"] = str(value)
            else:
                table[tag] = value

    # ----------------------------------------------------------------------
    def readTables(self):
        """Read tables section"""
        while True:
            table = self.readTable()
            if table is None:
                return
            if table["type"] == "LAYER":
                name = table.get("name")
                if name is not None:
                    self.layers[name] = Layer(name, table)

    # ----------------------------------------------------------------------
    def readSection(self):
        """Read section based on type"""
        if not self.mustbe(0, "SECTION"):
            return None
        tag, value = self.read()
        if tag is None:
            return None
        if tag != 2:
            self.push()
            return None
        if value == "HEADER":
            self.readHeader()

        elif value == "ENTITIES":
            self.readEntities()

        elif value == "BLOCKS":
            self.readBlocks()

        elif value == "TABLES":
            self.readTables()

        else:
            self.skipSection()

        return value

    # ----------------------------------------------------------------------
    # Read whole DXF and store it in the self.layers
    # ----------------------------------------------------------------------
    def readFile(self):
        self.readTitle()
        while self.readSection() is not None:
            pass
        self.mustbe(0, "EOF")

    # ----------------------------------------------------------------------
    def write(self, tag, value):
        """Write one tag,value pair"""
        self._f.write(f"{int(tag)}\n{str(value)}\n")

    # ----------------------------------------------------------------------
    def writeVector(self, idx, x, y, z=None):
        """Write a vector for index idx"""
        self.write(10 + idx, f"{x:g}")
        self.write(20 + idx, f"{y:g}")
        if z is not None:
            self.write(30 + idx, f"{z:g}")

    # ----------------------------------------------------------------------
    def writeHeader(self):
        """Write DXF standard header"""
        self.write(999, self.title)
        self.write(0, "SECTION")
        self.write(2, "HEADER")
        self.write(9, "$ACADVER")
        self.write(1, "AC1009")
        self.write(9, "$EXTMIN")
        self.writeVector(0, 0, 0, 0)
        self.write(9, "$EXTMAX")
        self.writeVector(0, 1000, 1000, 0)
        self.write(9, "$MEASUREMENT")
        if self.units == DXF.MILLIMETERS:
            self.write(70, 1)
        else:
            self.write(70, 0)
        self.write(9, "$INSUNITS")
        self.write(70, self.units)
        self.write(0, "ENDSEC")

        self.write(0, "SECTION")
        self.write(2, "ENTITIES")

    # ----------------------------------------------------------------------
    def writeEOF(self):
        """Write End Of File"""
        self.write(0, "ENDSEC")
        self.write(0, "EOF")

    # ----------------------------------------------------------------------
    def point(self, x, y, name=None):
        """Write a point x,y as name"""
        self.write(0, "POINT")
        if name:
            self.write(8, name)
        self.writeVector(0, x, y)

    # ----------------------------------------------------------------------
    def line(self, x0, y0, x1, y1, name=None):
        """Write a line (x0,y0),(x1,y1) as name"""
        self.write(0, "LINE")
        if name:
            self.write(8, name)
        self.writeVector(0, x0, y0)
        self.writeVector(1, x1, y1)

    # ----------------------------------------------------------------------
    def circle(self, x, y, r, name=None):
        """Write a line (x,y),r as name"""
        self.write(0, "CIRCLE")
        if name:
            self.write(8, name)
        self.writeVector(0, x, y)
        self.write(40, r)

    # ----------------------------------------------------------------------
    def arc(self, x, y, r, start, end, name=None):
        """Write an arc (x,y),r as name"""
        self.write(0, "ARC")
        if name:
            self.write(8, name)
        self.writeVector(0, x, y)
        self.write(40, r)
        self.write(50, start)
        self.write(51, end)

    # ----------------------------------------------------------------------
    def polyline(self, pts, flag=0, name=None):
        """Write an polyline from a list of points pts"""
        self.write(0, "LWPOLYLINE")
        if name:
            self.write(8, name)
        self.write(100, "AcDbEntity")
        self.write(90, len(pts))
        self.write(70, flag)  # bit mask flag? 0=default, 1=closed, 128=plinegen
        self.write(43, 0)  # constant width
        for x, y in pts:
            self.writeVector(0, x, y)

    # ----------------------------------------------------------------------
    def sort(self):
        """
        Sort layer in continuation order of entities
        where the end of of the previous is the start of the new one
        Add an new special marker for starting an entity with TYPE="START"
        """
        for block in self.blocks.values():
            block.sort()
        for layer in self.layers.values():
            layer.sort()

    # ----------------------------------------------------------------------
    def convert2Polylines(self):
        """Convert all SPLINES and ELLIPSE to POLYLINEs"""
        for layer in self.layers.values():
            for entity in layer.entities:
                entity.convert2Polyline(self.splineSegs)

    # ----------------------------------------------------------------------
    def expandBlocks(self):
        """Inline BLOCKS as entities in the appropriate layers"""
        for layer in self.layers.values():
            for i, insert in reversed(list(enumerate(layer.entities))):
                if insert.type != "INSERT":
                    continue

                del layer.entities[i]
                block = self.blocks[insert[2]]

                for le in block.layers.values():
                    for e in le.entities:
                        enew = e.clone()

                        # first check for scaling
                        sx = insert.get(41)
                        sy = insert.get(42)
                        sz = insert.get(43)
                        if sx is not None or sy is not None:
                            enew.scale(sx, sy, sz)

                        # followed by the rotation
                        r = insert.get(50, 0)
                        if r != 0.0:
                            enew.rotate(r)

                        # grid placement
                        nc = insert.get(70, 1)  # column count
                        nr = insert.get(71, 1)  # row count
                        cs = insert.get(44, 0.0)  # column spacing
                        rs = insert.get(45, 0.0)  # row spacing

                        # last do the translation
                        enew.translate(insert.point3D())

                        for j in range(nr):
                            for i in range(nc):
                                if i == 0 and j == 0:
                                    self.addEntity(enew)
                                else:
                                    e2 = enew.clone()
                                    e2.translate(i * cs, j * rs)
                                    self.addEntity(e2)


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    dxf = DXF(sys.argv[1], "r")
    dxf.readFile()
    dxf.close()
