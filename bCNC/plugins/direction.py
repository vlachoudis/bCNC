# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from tkinter import messagebox

import rexx
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


# ----------------------------------------------------------------------
# Change cut direction
# 1     CW
# -1    CCW
# 2     Conventional = CW for inside profiles and pockets,
#                  CCW for outside profiles
# -2    Climb = CCW for inside profiles and pockets,
#               CW for outside profiles
# ----------------------------------------------------------------------
def apply_direction(gcode, items, direction=-1):
    """Set path winding / climb-conventional tags.

    Returns a warning string if some blocks could not be updated, else None.
    """
    undoinfo = []
    msg = None

    remove = ["cut", "reverse", "climb", "conventional", "cw", "ccw"]
    for bid in items:
        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue

        opdir = direction
        operation = ""

        # Decide conventional/climb/error:
        side = gcode.blocks[bid].operationSide()
        if abs(direction) > 1 and side == 0:
            msg = (
                "Conventional/Climb feature only works for paths with "
                "'in/out/pocket' tags!\n"
                "Some of the selected paths were not tagged (or are both "
                "in+out). You can still use CW/CCW for them."
            )
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
        for path in gcode.toPath(bid):
            if not path.directionSet(opdir):
                msg = "Error determining direction of path!"
            if path:
                block = gcode.fromPath(path)
                undoinfo.append(
                    gcode.addBlockOperationUndo(bid, operation, remove))
                undoinfo.append(gcode.setBlockLinesUndo(bid, block))
    gcode.addUndo(undoinfo)

    return msg


def run_direction(app, direction=-1):
    return run_on_selection(app, apply_direction, direction)


class Tool(Plugin):
    __doc__ = _("Change cut direction")

    def __init__(self, master):
        Plugin.__init__(self, master, "Direction")
        self.icon = "conventional"
        # Editor already has direction buttons; register CLI only
        self.group = "Macros"
        self.oneshot = True
        self.commands = {"DIRECTION": (self.cmdline, 3)}

    def cmdline(self, app, args, oline=None):
        if len(args) < 2:
            messagebox.showerror(
                _("Direction command error"),
                _("Invalid direction {} specified").format(""),
                parent=app,
            )
            return "break"
        if rexx.abbrev("CLIMB", args[1].upper(), 2):
            direction = -2
        elif rexx.abbrev("CONVENTIONAL", args[1].upper(), 2):
            direction = 2
        elif rexx.abbrev("CW", args[1].upper(), 2):
            direction = 1
        elif rexx.abbrev("CCW", args[1].upper(), 2):
            direction = -1
        else:
            messagebox.showerror(
                _("Direction command error"),
                _("Invalid direction {} specified").format(args[1]),
                parent=app,
            )
            return "break"
        run_direction(app, direction)

    def execute(self, app):
        run_direction(app, -1)
