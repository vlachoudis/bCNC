# $Id$
#
# Author:    DodoLaSaumure
# Date:      30-Dec-2019

from tkinter import messagebox

from ToolsPage import Plugin

__author__ = "DodoLaSaumure"
__email__ = ""


# =============================================================================
# Create a simple Translate
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Translates a block to a new position")

    def __init__(self, master):
        Plugin.__init__(self, master, "SimpleTranslate")
        self.icon = "SimpleTranslate"
        self.group = "Generator"
        self.variables = [
            ("xinc", "float", 10.0, _("x increment")),
            ("yinc", "float", 10.0, _("y increment")),
            ("nbrepeat", "int", 2, _("nb repeat including original")),
            ("keep", "bool", True, _("Keep original Yes/No")),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        dx = self["xinc"]
        dy = self["yinc"]
        nbrepeat = self["nbrepeat"]
        if nbrepeat == 1:
            nbrepeat = 2
        keep = self["keep"]
        blocks = app.editor.getSelectedBlocks()
        if not blocks:
            app.editor.selectAll()
            blocks = app.editor.getSelectedBlocks()
        if not blocks:
            messagebox.showerror(_("Tile error"),
                                 _("No g-code blocks selected"))
            return
        pos = blocks[-1]  # insert position
        y = dy
        x = dx
        pos += 1
        for index in range(int(nbrepeat - 1)):
            # clone selected blocks
            undoinfo = []
            newblocks = []
            for bid in blocks:
                undoinfo.append(app.gcode.cloneBlockUndo(bid, pos))
                newblocks.append((pos, None))
                pos += 1
            app.addUndo(undoinfo)
            app.gcode.moveLines(newblocks, x, y)
            x += dx
            y += dy
        if not keep:
            app.editor.deleteBlock()
        app.refresh()
        app.setStatus(_("Moved selected blocks"))


if __name__ == "__main__":
    pass
