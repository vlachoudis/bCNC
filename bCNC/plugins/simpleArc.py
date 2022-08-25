# $Id$
#
# Author:    DodoLaSaumure
# Date:      30-Dec-2019

import math

from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "DodoLaSaumure"
__email__ = ""


# =============================================================================
# SimpleArc class
# =============================================================================
class SimpleArc:
    def __init__(self, name):
        self.name = name

    def calc(self, xcenter, ycenter, radius, startangle, endangle):
        self.Points = []
        xcenter, ycenter, radius, startangle, endangle = (
            float(xcenter),
            float(ycenter),
            abs(float(radius)),
            float(startangle),
            float(endangle),
        )
        xstart = xcenter + radius * math.cos(startangle * math.pi / 180.0)
        xend = xcenter + radius * math.cos(endangle * math.pi / 180.0)
        ystart = ycenter + radius * math.sin(startangle * math.pi / 180.0)
        yend = ycenter + radius * math.sin(endangle * math.pi / 180.0)
        i = xcenter - xstart
        j = ycenter - ystart
        blocks = []
        block = Block(self.name)
        block.append(CNC.grapid(x=xstart, y=ystart))
        block.append(CNC.grapid(z=0.0))
        block.append("(entered)")
        if startangle < endangle:
            direction = 3
        else:
            direction = 2
        block.append(CNC.garc(direction, x=xend, y=yend, i=i, j=j))
        block.append("(exiting)")
        block.append(CNC.grapid(z=CNC.vars["safe"]))
        blocks.append(block)
        return blocks


# =============================================================================
# Create a simple Arc
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate a simple Arc")

    def __init__(self, master):
        Plugin.__init__(self, master, "SimpleArc")
        self.icon = "SimpleArc"
        self.group = "Generator"
        self.variables = [
            ("xcenter", "float", 0.0, _("Center X")),
            ("ycenter", "float", 0.0, _("Center Y")),
            ("radius", "float", 0, _("Radius")),
            ("startangle", "float", 0, _("Start Angle in Degrees")),
            ("endangle", "float", 360, _("End Angle in Degrees ")),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "SimpleArc"
        simpleArc = SimpleArc(n)
        blocks = simpleArc.calc(
            self["xcenter"],
            self["ycenter"],
            self["radius"],
            self["startangle"],
            self["endangle"],
        )
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, _("Create Simple Arc"))
        app.refresh()
        app.setStatus(_("Generated: Simple Arc"))


if __name__ == "__main__":
    simpleArc = SimpleArc()
    simpleArc.calc(0, 10, 20, 0, 360)
    simpleArc.calc(10, 10, 20, 0, -360)
