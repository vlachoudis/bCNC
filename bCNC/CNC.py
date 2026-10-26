# $Id: CNC.py,v 1.8 2014/10/15 15:03:49 bnv Exp $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014
"""Machine layer: G-code protocol constants, config, parse/compile, motion."""

import math
import re

from Helpers import to_zip

PARENPAT = re.compile(r"(\(.*?\))")
SEMIPAT = re.compile(r"(;.*)")
CMDPAT = re.compile(r"([A-Za-z]+)")
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

        def booli(s):
            return bool(int(s))

        for attr, key, cast in (
            ("inch", "units", booli),
            ("lasercutter", "lasercutter", booli),
            ("laseradaptive", "laseradaptive", booli),
            ("enable6axisopt", "enable6axisopt", booli),
            ("doublesizeicon", "doublesizeicon", booli),
            ("acceleration_x", "acceleration_x", float),
            ("acceleration_y", "acceleration_y", float),
            ("acceleration_z", "acceleration_z", float),
            ("feedmax_x", "feedmax_x", float),
            ("feedmax_y", "feedmax_y", float),
            ("feedmax_z", "feedmax_z", float),
            ("travel_x", "travel_x", float),
            ("travel_y", "travel_y", float),
            ("travel_z", "travel_z", float),
            ("acceleration_a", "acceleration_a", float),
            ("acceleration_b", "acceleration_b", float),
            ("acceleration_c", "acceleration_c", float),
            ("feedmax_a", "feedmax_a", float),
            ("feedmax_b", "feedmax_b", float),
            ("feedmax_c", "feedmax_c", float),
            ("travel_a", "travel_a", float),
            ("travel_b", "travel_b", float),
            ("travel_c", "travel_c", float),
            ("accuracy", "accuracy", float),
            ("digits", "round", int),
            ("drozeropad", "drozeropad", int),
            ("startup", "startup", str),
            ("header", "header", str),
            ("footer", "footer", str),
        ):
            try:
                setattr(CNC, attr, cast(config.get(section, key)))
            except Exception:
                continue  # keep existing class default

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
                continue

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
                        # FIXME show the error!!!!
                        try:
                            compiled = compile(expr, "", "eval")
                        except Exception:
                            compiled = None
                        if compiled is not None:
                            out.append(compiled)
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
            t = 0.0
            try:
                if CNC.vars["feedmode"] == 94:
                    # Normal mode
                    t = length / self.feed
                elif CNC.vars["feedmode"] == 93:
                    # Inverse mode
                    t = length * self.feed
            except Exception:
                t = 0.0
            block.time += t
            self.totalTime += t
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


