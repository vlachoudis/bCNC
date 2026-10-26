# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


def apply_island(gcode, items, island=None):
    undoinfo = []
    remove = ["island"]
    for bid in items:
        isl = island

        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue

        if isl is None:
            isl = not gcode.blocks[bid].operationTest("island")
        if isl:
            tag = "island"
            gcode.blocks[bid].color = "#ff0000"
        else:
            tag = ""
            gcode.blocks[bid].color = None

        undoinfo.append(gcode.addBlockOperationUndo(bid, tag, remove))

    gcode.addUndo(undoinfo)


def run_island(app, island=None):
    return run_on_selection(app, "ISLAND", apply_island, island)


class Tool(Plugin):
    __doc__ = _("Toggle island")

    def __init__(self, master):
        Plugin.__init__(self, master, "Island")
        self.icon = "island"
        self.group = "CAM-core"
        self.order = 40
        self.oneshot = True
        self.commands = {"ISLAND": (self.cmdline, 3)}

    def cmdline(self, app, args, oline=None):
        if len(args) > 1:
            isl = args[1].upper() == "1"
        else:
            isl = None
        run_island(app, isl)

    def execute(self, app):
        run_island(app)
