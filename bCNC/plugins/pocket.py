# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from tkinter import messagebox

import bcam
from GCode import Block
from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


# -----------------------------------------------------------------------------
# Apply pocket CAM to selected block indices on a GCode document.
# Mutates blocks list in place to the new block indices (same as old API).
# -----------------------------------------------------------------------------
def apply_pocket(
    gcode, blocks, diameter, stepover, name=None, nested=False, updown=False
):
    undoinfo = []
    msg = ""
    newblocks = []
    for bid in reversed(blocks):
        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue
        newpath = []
        for path in gcode.toPath(bid):
            if not path.isClosed():
                m = f"Path: '{path.name}' is OPEN"
                if m not in msg:
                    if msg:
                        msg += "\n"
                    msg += m

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

            newpath.extend(bcam.pocket_paths(path, diameter, stepover))

        if newpath:
            before = len(newblocks)
            if updown:
                undoinfo.extend(
                    gcode.importPath(bid, newpath, newblocks, True, False)
                )
            else:
                undoinfo.extend(
                    gcode.importPath(bid + 1, newpath, newblocks, True, False)
                )
            new = len(newblocks) - before
            for i in range(before):
                newblocks[i] += new
            if not nested:
                gcode.blocks[bid].enable = False
    gcode.addUndo(undoinfo)

    del blocks[:]
    blocks.extend(newblocks)
    return msg


class Tool(Plugin):
    __doc__ = _("Perform a pocket operation on selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Pocket")
        self.icon = "pocket"
        self.group = "CAM-core"
        self.order = 10
        self.variables = [
            ("name", "db", "", _("Name")),
            ("endmill", "db", "", _("End Mill")),
        ]
        self.buttons.append("exe")
        self.commands = {"POCKET": (self.cmdline, 3)}
        self.help = """Remove all material inside selected shape
"""

    def cmdline(self, app, args, oline=None):
        self.execute(app)

    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])
        name = self["name"]
        if name == "default" or name == "":
            name = None

        tool = app.tools["EndMill"]
        diameter = app.tools.fromMm(tool["diameter"])
        try:
            stepover = tool["stepover"] / 100.0
        except TypeError:
            stepover = 0.0

        app.busy()
        blocks = app.editor.getSelectedBlocks()
        msg = apply_pocket(app.gcode, blocks, diameter, stepover, name)
        if msg:
            messagebox.showwarning(
                _("Open paths"), _("WARNING: {}").format(msg), parent=app
            )
        app.editor.fill()
        app.editor.selectBlocks(blocks)
        app.draw()
        app.notBusy()
        app.setStatus(_("Generate pocket path"))
