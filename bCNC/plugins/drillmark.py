# $Id$
#
# Author:  Attila Kolinger
# Date:         26.feb.2018.

import math

# Here import the libraries you need, these are necessary to modify the code
from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "Attila Kolinger"
# <<< here put an email where plugins users can contact you
__email__ = "attila.kolinger@gmail.com"


# =============================================================================
# Manual drillmark plugin
# =============================================================================
class Tool(Plugin):
    __doc__ = _(
        """This plugin is for creating drilling marks with a laser engraver
        for manual drilling"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "Marker for manual drilling")
        self.icon = "crosshair"
        self.group = "Generator"

        # a variable that will be converted in mm/inch based on bCNC setting
        self.variables = [
            (
                "name",
                "db",
                "",
                _("Name"),
            ),  # used to store plugin settings in the internal database
            (
                "Mark size",
                "mm",
                10.0,
                _("Drill mark size"),
            ),
            ("PosX", "mm", 0, _("Mark X center")),  # an integer variable
            ("PosY", "mm", 0, _("Mark Y center")),  # a float value variable
            ("Burn time", "float", 4.0, _("Burn time for drillmark")),
            ("Burn power", "float", 1000.0, _("Burn power for drillmark")),
            ("Mark power", "float", 400.0, _("Mark drawing power")),
            (
                "Mark type",
                "Point,Cross,Cross45,Star,Spikes,Spikes45,SpikesStar,"
                + "SpikesStar45",
                "Cross",
                _("Type of the mark"),
            ),  # a multiple choice combo box
            ("Draw ring", "bool", True, _("Ring mark (d/2)")),
        ]
        self.sin45 = math.sqrt(0.5)

        # <<< This is the button added at bottom to call the execute method below
        self.buttons.append(
            "exe"
        )
        self.help = " ".join([
            "This plugin is for creating drilling marks with a laser",
            "engraver for manual drilling"
        ])

    def appendBurn(self, app, block):
        x0 = self.fromMm("PosX")
        y0 = self.fromMm("PosY")
        burntime = self["Burn time"]
        burnpower = self["Burn power"]
        block.append(CNC.grapid(x=x0, y=y0))
        block.append(f"g1 m3 {CNC.fmt('s', burnpower)}")
        block.append(f"g4 {CNC.fmt('p', burntime)}")
        block.append("m5")

    def getPowerLine(self, app):
        if CNC.laseradaptive:
            pwrcode = "m4"
        else:
            pwrcode = "m3"
        markpower = self["Mark power"]
        return f"{pwrcode} {CNC.fmt('s', markpower)}"

    def appendMark(self, app, block):
        def appendCross(block):
            block.append("m5")
            block.append(CNC.grapid(x=x0, y=y0 + marksizehalf, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(CNC.gline(y=y0 - marksizehalf, f=drawfeed))
            block.append("m5")
            block.append(CNC.grapid(x=x0 + marksizehalf, y=y0, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(CNC.gline(x=x0 - marksizehalf, f=drawfeed))
            block.append("m5")

        def appendCross45(block):
            msh = marksizehalf * self.sin45
            block.append("m5")
            block.append(CNC.grapid(x=x0 - msh, y=y0 + msh, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(CNC.gline(x=x0 + msh, y=y0 - msh, f=drawfeed))
            block.append("m5")
            block.append(CNC.grapid(x=x0 + msh, y=y0 + msh, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(CNC.gline(x=x0 - msh, y=y0 - msh, f=drawfeed))
            block.append("m5")

        def appendCircle(block):
            block.append("m5")
            block.append(CNC.grapid(x=x0, y=y0 + marksizehalf / 2, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(
                CNC.garc(
                    2,
                    x=x0,
                    y=y0 + marksizehalf / 2,
                    j=-marksizehalf / 2,
                    i=0,
                    f=drawfeed,
                )
            )
            block.append("m5")

        def appendSpikes(block):
            sinSpike = math.sin(math.atan(2.0 - math.sqrt(3)))
            cosSpike = math.cos(math.atan(2.0 - math.sqrt(3)))
            block.append("m5")
            block.append(CNC.grapid(x=x0, y=y0, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * sinSpike,
                    y=y0 - marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * sinSpike,
                    y=y0 - marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * sinSpike,
                    y=y0 + marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * sinSpike,
                    y=y0 + marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(CNC.gline(x=x0, y=y0, f=drawfeed))
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * cosSpike,
                    y=y0 + marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * cosSpike,
                    y=y0 - marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * cosSpike,
                    y=y0 + marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * cosSpike,
                    y=y0 - marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(CNC.gline(x=x0, y=y0, f=drawfeed))
            block.append("m5")

        def appendSpikes45(block):
            sinSpike = math.sin(math.atan(1.0 / math.sqrt(3)))
            cosSpike = math.cos(math.atan(1.0 / math.sqrt(3)))
            block.append("m5")
            block.append(CNC.grapid(x=x0, y=y0, f=movefeed))
            block.append(self.getPowerLine(app))
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * sinSpike,
                    y=y0 - marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * cosSpike,
                    y=y0 - marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * cosSpike,
                    y=y0 + marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * sinSpike,
                    y=y0 + marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(CNC.gline(x=x0, y=y0, f=drawfeed))
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * sinSpike,
                    y=y0 - marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 - marksizehalf * cosSpike,
                    y=y0 - marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * cosSpike,
                    y=y0 + marksizehalf * sinSpike,
                    f=drawfeed,
                )
            )
            block.append(
                CNC.gline(
                    x=x0 + marksizehalf * sinSpike,
                    y=y0 + marksizehalf * cosSpike,
                    f=drawfeed,
                )
            )
            block.append(CNC.gline(x=x0, y=y0, f=drawfeed))
            block.append("m5")
            block.append(
                CNC.grapid(x=x0 + marksizehalf / 2,
                           y=y0 + marksizehalf / 2, f=movefeed)
            )
            block.append(self.getPowerLine(app))
            block.append(CNC.gline(x=x0 - marksizehalf / 2, f=drawfeed))
            block.append(CNC.gline(y=y0 - marksizehalf / 2, f=drawfeed))
            block.append(CNC.gline(x=x0 + marksizehalf / 2, f=drawfeed))
            block.append(CNC.gline(y=y0 + marksizehalf / 2, f=drawfeed))
            block.append("m5")

        x0 = self.fromMm("PosX")
        y0 = self.fromMm("PosY")
        movefeed = app.cnc["cutfeed"]
        drawfeed = app.cnc["cutfeedz"]
        marksizehalf = self.fromMm("Mark size") / 2
        marktype = self["Mark type"]
        if "None" == marktype:
            pass
        else:
            block.append("m5")
            if "Star" == marktype:
                appendCross(block)
                appendCross45(block)
            if "Cross" == marktype:
                appendCross(block)
            if "Cross45" == marktype:
                appendCross45(block)
            if "Spikes" == marktype:
                appendSpikes(block)
            if "Spikes45" == marktype:
                appendSpikes45(block)
            if "SpikesStar" == marktype:
                appendSpikes(block)
                appendCross45(block)
            if "SpikesStar45" == marktype:
                appendSpikes45(block)
                appendCross(block)

            if self["Draw ring"]:
                appendCircle(block)
            else:
                block.append("m5")

    def execute(self, app):
        name = self["name"]
        if not name or name == "default":
            name = "Drillmark"
        marksize = self["Mark size"]
        marktype = self["Mark type"]
        block = Block(name + f" {marktype} diameter {CNC.fmt('', marksize)}")
        self.appendBurn(app, block)
        self.appendMark(app, block)
        active = app.activeBlock()
        if active == 0:
            active = 1
        blocks = [block]
        app.gcode.insBlocks(active, blocks, _("Manual drill mark"))
        app.refresh()  # <<< refresh editor
        app.setStatus(_("Generated: Manual drillmark"))
