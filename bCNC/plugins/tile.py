# $Id$
#
# Author:    Vasilis.Vlachoudis@cern.ch
# Date:      20-Aug-2015

from ToolsPage import Plugin
from tkinter import messagebox

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Tile")


# =============================================================================
# Tile replicas of the selected blocks
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate replicas of selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Tile")
        self.icon = "tile"
        self.group = "CAM"
        self.variables = [
            ("name", "db", "", _("Name")),
            ("nx", "int", 3, "Nx"),
            ("ny", "int", 3, "Ny"),
            ("dx", "mm", 50.0, "Dx"),
            ("dy", "mm", 50.0, "Dy"),
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
            messagebox.showerror(_("Tile error"), _("No g-code blocks selected"))
            return

        try:
            dx = self.fromMm("dx")
        except Exception:
            dx = 0.0

        try:
            dy = self.fromMm("dy")
        except Exception:
            dy = 0.0

        pos = blocks[-1]  # insert position

        y = 0.0
        pos += 1
        for j in range(self["ny"]):
            x = 0.0
            for i in range(self["nx"]):
                if i == 0 and j == 0:
                    # skip the first
                    x += dx
                    continue
                # clone selected blocks
                undoinfo = []  # FIXME it should be only one UNDO
                newblocks = []
                for bid in blocks:
                    undoinfo.append(app.gcode.cloneBlockUndo(bid, pos))
                    newblocks.append((pos, None))
                    pos += 1
                app.addUndo(undoinfo)

                # FIXME but the moveLines already does the addUndo
                # I should correct it
                app.gcode.moveLines(newblocks, x, y)
                x += dx
            y += dy

        app.refresh()
        app.setStatus(_("Tiled selected blocks"))
