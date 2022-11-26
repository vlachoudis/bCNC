# $Id$
#
# Author:    DodoLaSaumure
# Date:      30-Dec-2019

from bmath import Vector
from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "DodoLaSaumure"
__email__ = ""


# =============================================================================
# SimpleLine class
# =============================================================================
class SimpleLine:
    def __init__(self, name):
        self.name = name

    def calc(self, xstart, ystart, xend, yend):
        points = []
        points.append(Vector(xstart, ystart))
        points.append(Vector(xend, yend))
        first = points[0]
        last = points[1]
        blocks = []
        block = Block(self.name)
        block.append(CNC.grapid(first.x(), first.y()))
        block.append(CNC.grapid(z=0.0))
        block.append("(entered)")
        block.append(CNC.gline(last.x(), last.y()))
        block.append("(exiting)")
        block.append(CNC.grapid(z=CNC.vars["safe"]))
        blocks.append(block)
        return blocks


# =============================================================================
# Create a simple Line
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate a simple line")

    def __init__(self, master):
        Plugin.__init__(self, master, "SimpleLine")
        self.icon = "SimpleLine"
        self.group = "Generator"
        self.variables = [
            ("xstart", "float", 10, _("xStart")),
            ("xend", "float", 20, _("xEnd")),
            ("ystart", "float", 10, _("yStart")),
            ("yend", "float", 20, _("yEnd")),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "SimpleLine"
        simpleLine = SimpleLine(n)
        blocks = simpleLine.calc(
            self["xstart"],
            self["ystart"],
            self["xend"],
            self["yend"],
        )
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, _("Create Simple Line"))
        app.refresh()
        app.setStatus(_("Generated: Simple Line"))


if __name__ == "__main__":
    simpleLine = SimpleLine()
    simpleLine.calc(10, 10, 20, 20)
