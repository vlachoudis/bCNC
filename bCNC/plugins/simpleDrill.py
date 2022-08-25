# $Id$
#
# Author:    DodoLaSaumure
# Date:      30-Dec-2019

from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "DodoLaSaumure"
__email__ = ""


# =============================================================================
# SimpleDrill class
# =============================================================================
class SimpleDrill:
    def __init__(self, name):
        self.name = name

    def accelerateIfNeeded(self, ztogo, drillfeed):
        if self.safeZforG0 > 0:
            self.block.append(CNC.grapid(z=ztogo + self.safeZforG0))
            kwargs = {"f": float(drillfeed)}
            self.block.append(CNC.gline(None, None, ztogo, **kwargs))

    def calc(self, x, y, depth, peck, dwell, drillFeed, safeZforG0):
        self.safeZforG0 = float(abs(safeZforG0))
        peck = abs(float(peck))
        currentz = 0.0
        self.blocks = []
        self.block = Block(self.name)
        self.block.append(CNC.grapid(x=x, y=y))
        self.block.append(CNC.grapid(z=CNC.vars["safe"]))
        self.accelerateIfNeeded(0.0, drillFeed)
        self.block.append("(entered)")
        while currentz > depth:
            currentz -= peck
            if currentz < depth:
                currentz = depth
            kwargs = {"f": float(drillFeed)}
            self.block.append(CNC.gline(None, None, float(currentz), **kwargs))
            if self.safeZforG0 > 0:
                self.block.append(CNC.grapid(z=0.0 + self.safeZforG0))
            else:
                self.block.append(CNC.grapid(z=CNC.vars["safe"]))
            self.block.append(f"g4 {CNC.fmt('p', float(dwell))}")
            if currentz > depth:
                self.accelerateIfNeeded(currentz, drillFeed)
        self.block.append("(exiting)")
        self.block.append(CNC.grapid(z=CNC.vars["safe"]))
        self.blocks.append(self.block)
        return self.blocks


# =============================================================================
# Create a simple drill
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate a simple Drill")

    def __init__(self, master):
        Plugin.__init__(self, master, "SimpleDrill")
        self.icon = "SimpleDrill"
        self.group = "Generator"
        self.variables = [
            ("x", "mm", 0, _("X")),
            ("y", "mm", 0, _("Y")),
            ("depth", "mm", "", _("Target z (negative under surface)")),
            ("peck", "mm", "", _("Peck depth (positive)")),
            ("dwell", "float", 0, _("Dwell time (s)")),
            ("drillFeed", "mm/mn", "", _("Z feed for drilling")),
            ("safeZforG0", "mm", -1.0, _("Safe z secu for G0")),
        ]
        self.help = "\n".join([
            "This plugin drills a hole, by going back and forth. when safe "
            + "Z secu for G0 is -1 A drill sequence consists in making a G1 "
            + "to the current depth, then G0 to default zSafe.",
            "The depth is increased progressively by steps of \"peck\" value.",
            "When a value is entered in safe Z secu, the tool will go G0 "
            + "above the current depth, then will drill.",
            "This can accelerate the process ",
        ])
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "SimpleDrill"
        simpleDrill = SimpleDrill(n)
        blocks = simpleDrill.calc(
            self["x"],
            self["y"],
            self["depth"],
            self["peck"],
            self["dwell"],
            self["drillFeed"],
            self["safeZforG0"],
        )
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, _("Create Simple Drill"))
        app.refresh()
        app.setStatus(_("Generated: Simple Drill"))


if __name__ == "__main__":
    simpleDrill = SimpleDrill()
    simpleDrill.calc(10, 10, -20, 1, 0.2, 50)
