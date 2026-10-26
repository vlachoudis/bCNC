# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math

from CNC import CNC
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


# ----------------------------------------------------------------------
# Peck distance
# Target depth
# Depth increment
# Retract height=safe height
# ----------------------------------------------------------------------
def apply_drill(
    gcode,
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
        depth = gcode.cnc["surface"] - gcode.cnc["thickness"]
    if (
        depth < gcode.cnc["surface"] - gcode.cnc["thickness"]
        or depth > gcode.cnc["surface"]
    ):
        return (
            f"ERROR: Drill depth {depth:g} outside stock surface: "
            f"{gcode.cnc['surface']:g} .. "
            f"{gcode.cnc['surface'] - gcode.cnc['thickness']:g}\n"
            f"Please change stock surface in Tools->Stock or drill depth."
        )
    if abs(depth - (gcode.cnc["surface"] - gcode.cnc["thickness"])) < 1e-7:
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
            z = gcode.cnc["surface"]
            while z > depth:
                z = max(z - peck, depth)
                lines.append(CNC.zenter(z))
                lines.append(CNC.zsafe())
                if dwell:
                    lines.append(f"g4 {gcode.fmt('p', dwell)}")

    for bid in items:
        block = gcode.blocks[bid]
        if block.name() in ("Header", "Footer"):
            continue
        block.enable = True

        # construct new name
        undoinfo.append(gcode.addBlockOperationUndo(bid, opname))

        # 1st detect limits of first pass
        gcode.initPath(bid)
        gcode.cnc.z = gcode.cnc.zval = 1000.0
        lines = []

        if center:
            # Drill in center only
            for path in gcode.toPath(bid):
                x, y = path.center()
                lines.append(f"g0 {gcode.fmt('x', x)} {gcode.fmt('y', y)}")
                drillHole(lines)

        elif distance is None and number == 0:
            # Drill on path beginning only
            for i, line in enumerate(block):
                cmds = CNC.parseLine(line)
                if cmds is None:
                    lines.append(line)
                    continue
                gcode.cnc.motionStart(cmds)
                if gcode.cnc.dz < 0.0:
                    drillHole(lines)
                elif gcode.cnc.dz > 0.0:
                    # retract
                    pass
                elif gcode.cnc.gcode == 0:
                    # add all rapid movements
                    lines.append(line)
                elif gcode.cnc.gcode == 1:
                    # ignore normal movements
                    pass
                gcode.cnc.motionEnd()
        else:
            # Drill multiple holes along path
            for path in gcode.toPath(bid):

                length = path.length()
                if number > 0:
                    distance = length / float(number)
                s = 0.0  # running length

                while s < length:
                    P = path.distPoint(s)
                    s += distance
                    lines.append(
                        f"g0 {gcode.fmt('x', P[0])} {gcode.fmt('y', P[1])}")
                    drillHole(lines)

        undoinfo.append(gcode.setBlockLinesUndo(bid, lines))
    gcode.addUndo(undoinfo)


def run_drill(app, *args, **kwargs):
    return run_on_selection(app, apply_drill, *args, **kwargs)


class Tool(Plugin):
    __doc__ = _("Insert a drill cycle on current objects/location")

    def __init__(self, master):
        Plugin.__init__(self, master, "Drill")
        self.icon = "drill"
        self.group = "CAM-core"
        self.order = 20
        self.variables = [
            ("name", "db", "", _("Name")),
            ("center", "bool", True, _("Drill in center only")),
            ("depth", "mm", "", _("Target Depth")),
            ("peck", "mm", "", _("Peck depth")),
            ("dwell", "float", "", _("Dwell (s)")),
            ("distance", "mm", "", _("Distance (mm)")),
            ("number", "int", "", _("Number")),
        ]
        self.help = "\n".join([
            "Drill a hole in the center of the selected path or drill many "
            + "holes along the selected path.",
            "",
            "MODULE PARAMETERS:",
            "",
            "* center : if checked, there is only one drill in the center of "
            + "the selected path. (Otherwise drill along path)",
            "",
            "* depth : Depth of the drill. If not provided, stock material "
            + "thickness is used. (usually negative value)",
            "",
            "* peck: Peck step depth. If provided, drill with peck depth "
            + "step, raising the drill to z travel value. If not provided, "
            + "one pass drill is generated.",
            "",
            "* dwell: Dwell time at the bottom. If pecking is defined, dwell "
            + "also at lifted height.",
            "",
            "* distance: Distance between drills if drilling along path. "
            + "(Number of drills will superceed this parameter))",
            "",
            "* number: Number of drills if drilling along path. If nonzero, "
            + "Parameter 'distance' has no effect.",
        ])
        self.buttons.append("exe")
        self.commands = {"DRILL": (self.cmdline, 3)}

    # DRI*LL [depth] [peck]
    def cmdline(self, app, args, oline=None):
        p = []
        for i in range(1, 3):
            try:
                p.append(float(args[i]))
            except Exception:
                p.append(None)
        run_drill(app, *p)

    def execute(self, app):
        h = self.fromMm("depth", None)
        p = self.fromMm("peck", None)
        e = self.fromMm("distance", None)
        c = self["center"]
        try:
            d = self["dwell"]
        except Exception:
            d = None
        try:
            n = int(self["number"])
        except Exception:
            n = 0
        run_drill(app, h, p, d, e, n, c)
        app.setStatus(_("DRILL selected points"))
