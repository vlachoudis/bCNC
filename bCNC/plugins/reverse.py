# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from bpath import Path
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


def apply_reverse(gcode, items):
    undoinfo = []
    remove = ["cut", "climb", "conventional", "cw", "ccw", "reverse"]
    for bid in items:
        operation = "reverse"

        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue
        newpath = Path(gcode.blocks[bid].name())

        # Swap conventional/climb and cw/ccw tags when reversing
        if gcode.blocks[bid].operationTest("conventional"):
            operation += ",climb"
        if gcode.blocks[bid].operationTest("climb"):
            operation += ",conventional"
        if gcode.blocks[bid].operationTest("cw"):
            operation += ",ccw"
        if gcode.blocks[bid].operationTest("ccw"):
            operation += ",cw"

        for path in gcode.toPath(bid):
            path.invert()
            newpath.extend(path)
        if newpath:
            block = gcode.fromPath(newpath)
            undoinfo.append(
                gcode.addBlockOperationUndo(bid, operation, remove))
            undoinfo.append(gcode.setBlockLinesUndo(bid, block))
    gcode.addUndo(undoinfo)


def run_reverse(app):
    return run_on_selection(app, apply_reverse)


class Tool(Plugin):
    __doc__ = _("Reverse cut direction")

    def __init__(self, master):
        Plugin.__init__(self, master, "Reverse")
        self.icon = "reverse"
        # Editor already has Reverse button; register CLI only
        self.group = "Macros"
        self.oneshot = True
        self.commands = {"REVERSE": (self.cmdline, 3)}

    def cmdline(self, app, args, oline=None):
        run_reverse(app)

    def execute(self, app):
        run_reverse(app)
