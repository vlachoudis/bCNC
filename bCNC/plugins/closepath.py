# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from GCode import Block
from bpath import Segment
from ToolsPage import Plugin, run_on_selection

__author__ = "@harvie Tomas Mudrunka"
# __email__  = ""

__name__ = _("ClosePath")
__version__ = "0.1"


def apply_close(gcode, items):
    undoinfo = []
    for bid in items:
        block = gcode.blocks[bid]
        if block.name() in ("Header", "Footer"):
            continue
        paths = gcode.toPath(bid)
        if not paths:
            continue

        eblock = Block("closed " + block.name())
        for path in paths:
            if not path.isClosed():
                path.append(Segment(Segment.LINE, path[-1].B, path[0].A))
            eblock = gcode.fromPath(path, eblock)
        undoinfo.append(gcode.setBlockNameUndo(bid, eblock._name))
        undoinfo.append(gcode.setBlockLinesUndo(bid, eblock))
    gcode.addUndo(undoinfo)


def run_close(app):
    return run_on_selection(app, "CLOSE", apply_close)


class Tool(Plugin):
    __doc__ = _(
        """Close the path"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "ClosePath")
        # <<< This is the name of file used as icon for the ribbon button.
        #       It will be search in the "icons" subfolder
        self.icon = "closepath"
        self.group = "CAM"  # <<< This is the name of group that plugin belongs
        self.oneshot = True
        self.commands = {"CLOSE": (self.cmdline, 4)}

    def cmdline(self, app, args, oline=None):
        run_close(app)

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        run_close(app)
        app.setStatus(_("Generated: Closepath"))  # <<< feed back result
