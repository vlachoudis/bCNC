# $Id$
#
# Author:    T Marks
# Date:      2020/04/14

import math
import sys  # Trouble Shooting Only!

from tkinter import messagebox

from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "T Marks"
__email__ = "tsmarks@gmail.com"

__name__ = _("Spiral")
__version__ = "0.0.1"


# =============================================================================
# Spiral class
# =============================================================================
class Spiral:
    def __init__(self, name="Spiral"):
        self.name = name

    # ----------------------------------------------------------------------
    def make(
        self,
        app,
        XStart=0.0,
        YStart=0.0,
        ZStart=30.0,
        AlignAxis="Y",
        RotAxis="A",
        StockLeng=20,
        ReduceDepth=-1,
        PassDepth=1,
        Stepover=1,
        ZApproach=35,
        SpiralType="Spiral",
        CutBoth="True",
        LiftPass="False",
    ):

        # GCode Blocks
        blocks = []

        # Load tool and material settings
        toolDiam = CNC.vars["diameter"]
        toolRadius = toolDiam / 2.0

        # Calc tool diameter with Maximum Step Over allowed
        StepOverInUnitMax = toolDiam * CNC.vars["stepover"] / 100.0

        # Check parameters
        if RotAxis == "":
            app.setStatus(_("Spiral abort: Rotary Axis is undefined"))
            return

        if SpiralType == "":
            app.setStatus(_("Spiral abort: Spiral Type is undefined"))
            return

        if ZApproach <= ZStart:
            app.setStatus(
                _("Spiral abort: Approach height must be greater than Z Start")
            )
            return

        if ReduceDepth > 0:
            app.setStatus(_("Spiral abort: Depth Reduction must be negative"))
            return

        if (
            Stepover > StepOverInUnitMax and SpiralType == "Spiral"
        ):  # if Type is Lines then stepover is degrees not mm
            app.setStatus(_("Spiral abort: Step Over exceeds tool limits"))
            return
        elif (
            Stepover > StepOverInUnitMax and SpiralType == "Lines"
        ):  # This could cause a tool crash, but could also be used to make faceted shapes.
            dr = messagebox.askyesno(
                "Crash Risk",
                "WARNING: Using a larger stepover value than tool's "
                + "maximum with lines operation may result in a tool crash. "
                + "Do you want to continue?",
            )
            sys.stdout.write(f"{dr}")
            if dr is True or dr == "yes":
                app.setStatus(
                    _("Risk Accepted")
                )  # Using positive logic, if python returns ANYTHING other than True/yes this will not make g-code.  In case Python uses No instead of False
            else:
                return
        if StockLeng <= 0:
            app.setStatus(
                _("Spiral abort: Stock Length to cut must be positive"))
            return

        # Add Region disabled to show worked area
        block = Block(self.name + " Outline")
        block.enable = False
        block.append(
            CNC.grapid(CNC.vars["wx"], CNC.vars["wy"], ZApproach)
        )  # Cannot trust Safe-Z with 4th axis!!
        if AlignAxis == "X":
            outlineWidth = StockLeng
        else:
            outlineWidth = 0
        if AlignAxis == "Y":
            outlineHeight = StockLeng
        else:
            outlineHeight = 0
        xR, yR = self.RectPath(XStart, YStart, outlineWidth, outlineHeight)
        for x, y in zip(xR, yR):
            block.append(CNC.gline(x, y))
        blocks.append(block)

        if StockLeng < toolDiam:
            app.setStatus(
                _("Spiral abort: Stock Length is too small for this End Mill.")
            )
            return

        # Prepare points for pocketing
        xP = []
        yP = []
        rP = []
        zP = []
        gP = []

        # ---------------------------------------------------------------------
        # Line approach
        if SpiralType == "Lines":
            # Calc number of indexes
            # Using the step over as Degrees

            # Calc number of pass
            VerticalCount = math.ceil(abs(ReduceDepth) / PassDepth)
            # Calc even depths of cut
            EvenCutDepths = ReduceDepth / VerticalCount

            currentR = 0
            currentZ = ZStart - EvenCutDepths
            direction = 1
            if AlignAxis == "X":
                currentX = XStart + toolRadius
                currentY = YStart
            elif AlignAxis == "Y":
                currentX = XStart
                currentY = YStart + toolRadius
            else:
                app.setStatus(_("Spiral abort: Rotary Axis Not Assigned."))
                return

            while currentZ >= (ZStart + ReduceDepth):
                while currentR < 360:

                    # Plunge in
                    gP.append(1)
                    rP.append(currentR)
                    zP.append(currentZ)
                    xP.append(currentX)
                    yP.append(currentY)
                    if direction == 1:
                        if AlignAxis == "X":
                            currentX = StockLeng - toolRadius
                            currentY = YStart
                        elif AlignAxis == "Y":
                            currentX = XStart
                            currentY = StockLeng - toolRadius
                        else:
                            app.setStatus(
                                _("Spiral abort: Rotary Axis Not Assigned."))
                            return
                        if CutBoth == "True":
                            direction = -1
                    else:
                        if AlignAxis == "X":
                            currentX = XStart + toolRadius
                            currentY = YStart
                        elif AlignAxis == "Y":
                            currentX = XStart
                            currentY = YStart + toolRadius
                        else:
                            app.setStatus(
                                _("Spiral abort: Rotary Axis Not Assigned."))
                            return
                        direction = 1
                    gP.append(1)
                    zP.append(currentZ)
                    xP.append(currentX)
                    yP.append(currentY)
                    rP.append(currentR)
                    # Lift before rotating if required, useful to make non-round shape

                    if CutBoth == "False":  # Return to start

                        # Lift Before return
                        gP.append(0)
                        rP.append(currentR)
                        zP.append(ZApproach)
                        xP.append(currentX)
                        yP.append(currentY)

                        # Return to start
                        if AlignAxis == "X":
                            currentX = XStart + toolRadius
                            currentY = YStart
                        elif AlignAxis == "Y":
                            currentX = XStart
                            currentY = YStart + toolRadius
                        else:
                            app.setStatus(
                                _("Spiral abort: Rotary Axis Not Assigned."))
                            return
                        gP.append(0)
                        xP.append(currentX)
                        yP.append(currentY)
                        rP.append(currentR)
                        zP.append(ZApproach)
                        # Rotate
                        currentR += Stepover
                        gP.append(0)
                        xP.append(currentX)
                        yP.append(currentY)
                        rP.append(currentR)
                        zP.append(ZApproach)
                    elif LiftPass == "True" and CutBoth == "True":
                        gP.append(0)
                        rP.append(currentR)
                        zP.append(ZApproach)
                        xP.append(currentX)
                        yP.append(currentY)
                        currentR += Stepover
                        gP.append(0)
                        xP.append(currentX)
                        yP.append(currentY)
                        rP.append(currentR)
                        zP.append(ZApproach)
                    elif LiftPass == "False" and CutBoth == "True":
                        currentR += Stepover
                gP.append(0)
                xP.append(currentX)
                yP.append(currentY)
                rP.append(currentR)
                zP.append(ZApproach)
                currentR = 0
                gP.append(0)
                xP.append(currentX)
                yP.append(currentY)
                rP.append(currentR)
                zP.append(ZApproach)

                # Step Down
                currentZ += EvenCutDepths

        # ---------------------------------------------------------------------
        # Spiral approach
        if SpiralType == "Spiral":
            # Calc number of pass
            StepsPerRot = math.ceil(StockLeng / Stepover)
            TotalRot = 360 * StepsPerRot

            # Calc steps in depth
            VerticalCount = math.ceil(abs(ReduceDepth) / PassDepth)
            # Calc even depths of cut
            EvenCutDepths = ReduceDepth / VerticalCount

            direction = 1
            currentZ = ZStart - EvenCutDepths
            if AlignAxis == "X":
                currentX = XStart + toolRadius
                currentY = YStart
            elif AlignAxis == "Y":
                currentX = XStart
                currentY = YStart + toolRadius
            else:
                app.setStatus(_("Spiral abort: Rotary Axis Not Assigned."))
                return
            currentR = 0
            while currentZ >= (ZStart + ReduceDepth):

                # Plunge to depth
                currentR += 90  # Ramp the Plunge
                gP.append(1)
                rP.append(currentR)
                zP.append(currentZ)
                xP.append(currentX)
                yP.append(currentY)

                # One Full Rotation for a clean shoulder
                currentR += 360
                gP.append(1)
                rP.append(currentR)
                zP.append(currentZ)
                xP.append(currentX)
                yP.append(currentY)

                if AlignAxis == "X":
                    if direction == 1:
                        currentX = StockLeng - toolRadius
                    else:
                        currentX = XStart + toolRadius
                    currentY = YStart
                elif AlignAxis == "Y":
                    currentX = XStart
                    if direction == 1:
                        currentY = StockLeng - toolRadius
                    else:
                        currentY = YStart + toolRadius
                else:
                    app.setStatus(_("Spiral abort: Rotary Axis Not Assigned."))
                    return

                currentR += TotalRot
                gP.append(1)
                rP.append(currentR)
                zP.append(currentZ)
                xP.append(currentX)
                yP.append(currentY)

                # One Full Rotation for a clean shoulder
                currentR += 360
                gP.append(1)
                rP.append(currentR)
                zP.append(currentZ)
                xP.append(currentX)
                yP.append(currentY)

                if CutBoth == "True":
                    direction *= -1
                else:
                    # Retract
                    gP.append(0)
                    rP.append(currentR)
                    zP.append(ZApproach)
                    xP.append(currentX)
                    yP.append(currentY)
                    # Return and Rewind
                    gP.append(0)
                    rP.append(currentR)
                    zP.append(ZApproach)
                    if AlignAxis == "X":
                        currentX = XStart + toolRadius
                        currentY = YStart
                    elif AlignAxis == "Y":
                        currentX = XStart
                        currentY = YStart + toolRadius
                    else:
                        app.setStatus(
                            _("Spiral abort: Rotary Axis Not Assigned."))
                        return
                    xP.append(currentX)
                    yP.append(currentY)

                currentZ += EvenCutDepths

        # Start G-Code Processes
        # Blocks for pocketing
        block = Block(self.name)
        block.append(f"(Reduce Rotary by Y={ReduceDepth:g})")
        block.append(f"(Approach: {SpiralType} )")

        # Move safe to first point
        block.append(
            CNC.grapid(CNC.vars["mx"], CNC.vars["my"], ZApproach)
        )  # Cannot trust Safe-Z with 4th axis!!
        if AlignAxis == "X":
            block.append(CNC.grapid(XStart + toolRadius, YStart))
        elif AlignAxis == "Y":
            block.append(CNC.grapid(XStart, YStart + toolRadius))
        else:
            app.setStatus(_("Spiral abort: Rotary Axis Not Assigned."))
            return

        block.append(CNC.zenter(ZApproach))
        block.append(CNC.gcode(1, [("f", CNC.vars["cutfeed"])]))

        for g, x, y, z, r in zip(gP, xP, yP, zP, rP):
            if RotAxis == "A":
                if g == 0:
                    block.append(
                        CNC.grapidABC(
                            x, y, z, r, CNC.vars["wb"], CNC.vars["wc"])
                    )
                else:
                    block.append(
                        CNC.glineABC(
                            x, y, z, r, CNC.vars["wb"], CNC.vars["wc"])
                    )
            elif RotAxis == "B":
                if g == 0:
                    block.append(
                        CNC.grapidABC(
                            x, y, z, CNC.vars["wa"], r, CNC.vars["wc"])
                    )
                else:
                    block.append(
                        CNC.glineABC(
                            x, y, z, CNC.vars["wa"], r, CNC.vars["wc"])
                    )
            elif RotAxis == "C":
                if g == 0:
                    block.append(
                        CNC.grapidABC(
                            x, y, z, CNC.vars["wa"], CNC.vars["wb"], r)
                    )
                else:
                    block.append(
                        CNC.glineABC(
                            x, y, z, CNC.vars["wa"], CNC.vars["wb"], r)
                    )

        block.append(
            CNC.grapid(CNC.vars["wx"], CNC.vars["wy"], ZApproach)
        )  # Cannot trust Safe-Z with 4th axis!!
        if AlignAxis == "X":
            block.append(CNC.grapid(XStart + toolRadius, YStart))
        elif AlignAxis == "Y":
            block.append(CNC.grapid(XStart, YStart + toolRadius))
        else:
            app.setStatus(_("Spiral abort: Rotary Axis Not Assigned."))
            return
        block.append(CNC.zexit(ZApproach))
        blocks.append(block)
        messagebox.showinfo(
            "Crash Risk",
            "WARNING: Check CAM file Header for Z move. If it exists, "
            + "remove it to prevent tool crash.",
        )

        return blocks

    # ----------------------------------------------------------------------

    def RectPath(self, x, y, w, h):
        xR = []
        yR = []
        xR.append(x)
        yR.append(y)
        xR.append(x + w)
        yR.append(y)
        xR.append(x + w)
        yR.append(y + h)
        xR.append(x)
        yR.append(y + h)
        xR.append(x)
        yR.append(y)
        return (xR, yR)


# =============================================================================
# Spiral Cut on 4th Axis to reduce size
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Reduce Diameter of 4th Axis Stock")

    def __init__(self, master):
        Plugin.__init__(self, master, "Spiral")
        self.icon = "helical"
        self.group = "CAM"
        self.variables = [
            ("name", "db", "", _("Name")),
            ("XStart", "mm", 0.0, _("X start")),
            ("YStart", "mm", 0.0, _("Y start")),
            ("ZStart", "mm", 30.0, _("Z start")),
            ("AlignAxis", "X,Y", "Y", _("Rotary Alignment Axis")),
            ("RotAxis", "A,B,C", "A", _("Rotary Axis")),
            ("StockLeng", "mm", 20.0, _("Length of Stock to Reduce")),
            ("ReduceDepth", "mm", -1.0, _("Depth to Reduce")),
            ("PassDepth", "mm", 1.0, _("Max Depth per Pass")),
            ("Stepover", "mm", 1.0, _("Stepover (spiral=mm, lines=deg)")),
            ("ZApproach", "mm", 35.0, _("Approach Height (Safe Z)")),
            ("SpiralType", "Spiral,Lines", "Spiral", _("Cut Pattern")),
            ("CutBoth", "True,False", "True", _("Cut in Both Directions")),
            ("LiftPass", "True,False", "False", _("Lift before rotate")),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "Spiral"
        spiral = Spiral(n)

        blocks = spiral.make(
            app,
            self.fromMm("XStart"),
            self.fromMm("YStart"),
            self.fromMm("ZStart"),
            self["AlignAxis"],
            self["RotAxis"],
            self.fromMm("StockLeng"),
            self.fromMm("ReduceDepth"),
            self.fromMm("PassDepth"),
            self.fromMm("Stepover"),
            self.fromMm("ZApproach"),
            self["SpiralType"],
            self["CutBoth"],
            self["LiftPass"],
        )

        if blocks is not None:
            active = app.activeBlock()
            if active == 0:
                active = 1
            app.gcode.insBlocks(active, blocks, "Spiral")
            app.refresh()
            app.setStatus(_("Spiral: Reduced 4th Axis Stock"))
