# $Id$
#
# Author:    DodoLaSaumure
# Date:      30-Dec-2019

from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "DodoLaSaumure"
__email__ = ""


# =============================================================================
# SimpleRectangle class
# =============================================================================
class SimpleRectangle:
    def __init__(self, name):
        self.name = name

    def calc(self, xstart, ystart, xend, yend, radius, cw):
        self.Points = []
        self.corners = [
            min(float(xstart), float(xend)),
            min(float(ystart), float(yend)),
            max(float(xstart), float(xend)),
            max(float(ystart), float(yend)),
        ]

        xmin, ymin, xmax, ymax = (
            self.corners[0],
            self.corners[1],
            self.corners[2],
            self.corners[3],
        )
        r = min(radius, (xmax - xmin) / 2, (ymax - ymin) / 2)
        blocks = []
        block = Block(self.name)
        block.append(CNC.grapid(x=xmin, y=ymin + r))
        block.append(CNC.grapid(z=0.0))
        block.append("(entered)")
        if cw:
            block.append(CNC.gline(x=xmin, y=ymax - r))
            if r > 0:
                block.append(CNC.garc(2, x=xmin + r, y=ymax, i=r, j=0))
            if (xmax - xmin) > 2 * r:
                block.append(CNC.gline(x=xmax - r, y=ymax))
            if r > 0:
                block.append(CNC.garc(2, x=xmax, y=ymax - r, i=0, j=-r))
            if (ymax - ymin) > 2 * r:
                block.append(CNC.gline(x=xmax, y=ymin + r))
            if r > 0:
                block.append(CNC.garc(2, x=xmax - r, y=ymin, i=-r, j=0))
            if (xmax - xmin) > 2 * r:
                block.append(CNC.gline(x=xmin + r, y=ymin))
            if r > 0:
                block.append(CNC.garc(2, x=xmin, y=ymin + r, i=0, j=r))
        else:
            if r > 0:
                block.append(CNC.garc(3, x=xmin + r, y=ymin, i=r, j=0))
            if (xmax - xmin) > 2 * r:
                block.append(CNC.gline(x=xmax - r, y=ymin))
            if r > 0:
                block.append(CNC.garc(3, x=xmax, y=ymin + r, i=0, j=r))
            if (ymax - ymin) > 2 * r:
                block.append(CNC.gline(x=xmax, y=ymax - r))
            if r > 0:
                block.append(CNC.garc(3, x=xmax - r, y=ymax, i=-r, j=0))
            if (xmax - xmin) > 2 * r:
                block.append(CNC.gline(x=xmin + r, y=ymax))
            if r > 0:
                block.append(CNC.garc(3, x=xmin, y=ymax - r, i=0, j=-r))
            if (ymax - ymin) > 2 * r:
                block.append(CNC.gline(x=xmin, y=ymin + r))
        block.append("(exiting)")
        block.append(CNC.grapid(z=CNC.vars["safe"]))
        blocks.append(block)
        return blocks


# =============================================================================
# Create a simple Rectangle
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate a simple rectangle")

    def __init__(self, master):
        Plugin.__init__(self, master, "SimpleRectangle")
        self.icon = "SimpleRectangle"
        self.group = "Generator"
        self.variables = [
            ("xstart", "float", 0, _("xStart")),
            ("xend", "float", 20, _("xEnd")),
            ("ystart", "float", 0, _("yStart")),
            ("yend", "float", 40, _("yEnd")),
            ("radius", "float", 0, _("Corner Radius")),
            ("cw", "bool", True, _("clockwise")),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "SimpleRectangle"
        simpleRectangle = SimpleRectangle(n)
        blocks = simpleRectangle.calc(
            self["xstart"],
            self["ystart"],
            self["xend"],
            self["yend"],
            self["radius"],
            self["cw"],
        )
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, _("Create Simple Rectangle"))
        app.refresh()
        app.setStatus(_("Generated: Simple Rectangle"))


if __name__ == "__main__":
    simpleRectangle = SimpleRectangle()
    simpleRectangle.calc(10, 10, 20, 30, 5, True)
    simpleRectangle.calc(10, 10, 20, 30, 50, False)
