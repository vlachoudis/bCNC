# $Id$
#
# Author:    Vasilis.Vlachoudis@cern.ch
# Date:      20-Aug-2015

import random

from ToolsPage import Plugin
from tkinter import messagebox

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Random")


# =============================================================================
# Tile replicas of the selected blocks
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate replicas of selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Random")
        self.icon = "randomize"
        self.group = "CAM"
        self.variables = [
            ("name", "db", "", _("Name")),
            ("randx", "mm", 5.0, "Rand x"),
            ("randy", "mm", 5.0, "Rand y"),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        # Get selected blocks from editor
        blocks = app.editor.getSelectedBlocks()
        if not blocks:
            app.editor.selectAll()
            blocks = app.editor.getSelectedBlocks()

        if not blocks:
            messagebox.showerror(_("Tile error"),
                                 _("No g-code blocks selected"))
            return

        try:
            dx = self.fromMm("randx")
        except Exception:
            dx = 0.0

        try:
            dy = self.fromMm("randy")
        except Exception:
            dy = 0.0

        pos = blocks[-1]  # insert position

        pos += 1
        # clone selected blocks
        undoinfo = []  # FIXME it should be only one UNDO

        for bid in blocks:
            undoinfo.append(app.gcode.cloneBlockUndo(bid, pos))
            newblocks = []
            newblocks.append((pos, None))
            pos += 1
            app.addUndo(undoinfo)
            x = random.uniform(-dx, dx)
            y = random.uniform(-dy, dy)
            app.gcode.moveLines(newblocks, x, y)

        allBlocks = app.gcode.blocks
        for bid in blocks:
            block = allBlocks[bid]
            if not block.name() in ("Header", "Footer"):
                block.enable = False
        app.refresh()
        app.setStatus(_("Tiled selected blocks"))
