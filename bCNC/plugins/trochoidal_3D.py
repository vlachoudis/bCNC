# $Id$
#
# Author: Mario Basz
# mariob_1960@yahoo.com.ar
# Date: 20 may 2018
# A special thanks to Vasilis Viachoudis, Filippo Rivato and Buschhardt
# This plugin is based on a variation
# of yours Driller plugin and My_Plugin example.

import math
from math import (
    atan2,
    ceil,
    cos,
    degrees,
    pi,
    radians,
    sin,
    sqrt,
)
from tkinter import EXCEPTION

from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "Mario S Basz"
__email__ = "mariob_1960@yaho.com.ar"

__name__ = _("Trochoidcut")
__version__ = "1.3"


# =============================================================================
# Create trochoids along selected block
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Create trochoids along selected blocks")

    def __init__(self, master):
        Plugin.__init__(self, master, "Trochoidal 3D")
        self.icon = "trochoidal"
        self.group = "CAM"

        self.variables = [
            ("name", "db", "", _("Name")),
            ("diam", "float", "", _("Trochoid Cut Diameter")),
            ("endmill", "db", "", _("End Mill"),
             "If Empty chooses, End Mill loaded"),
            ("ae", "mm", 0.30, _("Trochoids Advance")),
            (
                "TypeSplice",
                "Warpedarc,Splices,Circular one side rectified,Circular both "
                + "sides rectified,Straight,Cut",
                "Warpedarc",
                _("Type of Splice"),
                "Currently Splices works very slow",
            ),
            ("direction", "inside,outside,on (3d Path)", "inside",
             _("Direction")),
            (
                "offset",
                "float",
                0.0,
                _("Additional offset distance"),
                " Only for In or On direction",
            ),
            (
                "adaptative",
                "bool",
                1,
                _("Adaptative"),
                "Generate path for adaptative trochoids in the corners. "
                + "Only for In or On direction",
            ),
            ("overcut", "bool", 0, _("Overcut"),
             " Only for In or On direction"),
            (
                "targetDepth",
                "mm",
                -1,
                _("Target Depth"),
                " Only for In or On direction",
            ),
            (
                "depthIncrement",
                "mm",
                1,
                _("Depth Increment"),
                " Only for In or On direction",
            ),
            ("cw", "bool", True, _("Clockwise")),
            ("rpm", "int", 12000, _("RPM")),
            ("feed", "int", 1200, _("Feed")),
            ("zfeed", "int", "", _("Plunge Feed")),
            (
                "splicesteps",
                "int",
                12,
                _("splice steps every 360 degrees"),
                "Only for Splices Type of Splice",
            ),
        ]
        self.buttons.append("exe")
        self.help = "\n".join([
            "It generates the trochoidal cutting mode on the selected block, "
            + "even at different heights.",
            "Currently, it only works by selecting only one block (a solution "
            + "is to join the blocks).",
            "In or Out generates the route and on it generates trochoids.",
        ])

    # ----------------------------------------------------------------------
    def update(self):
        self.master.cnc()["diam"] = self.fromMm("diam")

    # ----------------------------------------------------------------------
    def came_back(self, current, old):
        B = current[1]
        oldA = old[0]
        if B[0] == oldA[0] and B[1] == oldA[1] and B[2] == oldA[2]:
            control = 1
        else:
            control = 0
        return control

    def center_distance(self, xyz, atot):
        xadd = yadd = zadd = 0
        # xyz:
        A = xyz[0]
        B = xyz[1]
        segmlength = math.sqrt(
            (B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2 + (B[2] - A[2]) ** 2
        )
        segmlength_xy = math.sqrt((B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2)

        xlength = B[0] - A[0]
        ylength = B[1] - A[1]
        zlength = B[2] - A[2]
        # on ascending ramp keep the ae value on xy plane
        if xlength != 0 or ylength != 0 and zlength > 0:
            atot *= segmlength / segmlength_xy

        if segmlength > 0:
            xadd = atot * (xlength / segmlength)
            yadd = atot * (ylength / segmlength)
            zadd = atot * (zlength / segmlength)
            ae = math.sqrt(xadd**2 + yadd**2)

        return xadd, yadd, zadd, atot, ae  #

    # Calc subsegments -----------------------------------------------------
    def calcSegmentLength(self, xyz):
        if xyz:
            A = xyz[0]
            B = xyz[1]
            seglength_x = B[0] - A[0]
            seglength_y = B[1] - A[1]
            seglength_z = B[2] - A[2]
            return math.sqrt(seglength_x**2 + seglength_y**2 + seglength_z**2)
        else:
            return 0

    # ----------------------------------------------------------------------
    # Extract all segments from commands ------------ -----------------------
    def extractAllSegments(self, app, selectedBlock):
        allSegments = []
        allBlocks = app.gcode.blocks

        for bid in selectedBlock:
            bidSegments = []
            block = allBlocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            app.gcode.initPath(bid)
            for line in block:
                try:
                    cmd = app.cnc.breakLine(
                        app.gcode.evaluate(app.cnc.compileLine(line))
                    )
                except EXCEPTION:
                    cmd = None

                if cmd:
                    app.cnc.motionStart(cmd)
                    xyz = app.cnc.motionPath()
                    app.cnc.motionEnd()

                    if xyz:
                        # exclude if fast move or z only movement
                        Zonly = (xyz[0][0] == xyz[1][0]
                                 and xyz[0][1] == xyz[1][1])
                        exclude = Zonly

                        # save length for later use
                        segLength = self.calcSegmentLength(xyz)

                        if len(xyz) < 3:
                            bidSegments.append(
                                [xyz[0], xyz[1], exclude, segLength])
                        else:
                            for i in range(len(xyz) - 1):
                                bidSegments.append(
                                    [xyz[i], xyz[i + 1], exclude, segLength]
                                )
            # append bidSegmentes to allSegmentes
            allSegments.append(bidSegments)

        # Disabled used block
        for bid in selectedBlock:
            block = allBlocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            block.enable = False

        return allSegments

    # ----------------------------------------------------------------------
    def execute(self, app):
        if self["splicesteps"] == "" or self["splicesteps"] < 4:
            steps = 4 / (2 * pi)
        else:
            steps = self["splicesteps"] / (2 * pi)

        manualsetting = 1
        cutradius = self["diam"] / 2.0
        zfeed = CNC.vars["cutfeedz"]
        feed = CNC.vars["cutfeed"]
        minimfeed = CNC.vars["cutfeed"]
        if manualsetting:
            if self["diam"]:
                cutradius = self["diam"] / 2.0

            if self["zfeed"] and self["zfeed"] != "":
                zfeed = self["zfeed"]

            if self["feed"] and self["feed"] != "":
                feed = self["feed"]

            if self["endmill"]:
                self.master["endmill"].makeCurrent(self["endmill"])

        toolRadius = CNC.vars["diameter"] / 2.0
        radius = max(0, cutradius - toolRadius)
        oldradius = radius
        helicalRadius = radius
        helicalPerimeter = pi * 2.0 * helicalRadius

        cw = self["cw"]
        surface = CNC.vars["surface"]

        zbeforecontact = surface
        zbeforecontact = surface
        hardcrust = surface
        feedbeforecontact = zfeed
        hardcrustfeed = feed

        t_splice = self["TypeSplice"]
        dtadaptative = 0.0001
        adaptativepolice = 0
        atot = self.fromMm("ae")
        spiral_twists = (
            ceil(radius - helicalRadius) / atot
        )  # <<spiral ae smaller than ae (aprox 50%)

        rpm = self["rpm"]

        downPecking = helicalPerimeter * zfeed / feed
        helicalangle = degrees(atan2(downPecking, helicalPerimeter))

        direction = self["direction"]
        if direction != "on (3d Path)":
            targetDepth = self["targetDepth"]
            depthIncrement = self["depthIncrement"]
            tabsnumber = tabsWidth = tabsHeight = 0

            app.trochprofile_bcnc(
                2 * cutradius,
                direction,
                self["offset"],
                self["overcut"],
                self["adaptative"],
                radius,
                CNC.vars["diameter"],
                targetDepth,
                depthIncrement,
                tabsnumber,
                tabsWidth,
                tabsHeight,
            )
            app.refresh()

        selBlocks = app.editor.getSelectedBlocks()

        if not selBlocks:
            app.setStatus(_("Trochoid abort: Please select some path"))
            return
        # Check inputs
        if cutradius <= toolRadius:
            app.setStatus(
                _("Trochoid Cut Diameter has to be greater than End mill"))
            return

        if helicalRadius <= 0.0:
            app.setStatus(
                _("Helical Descent Diameter has to be greater than End mill"))
            return

        if feed <= 0:
            app.setStatus(_("Feed has to be greater than 0"))
            return

        if zfeed <= 0:
            app.setStatus(_("Plunge Feed has to be greater than 0"))
            return

        if minimfeed <= 0:
            app.setStatus(
                _("Minimum Adaptative Feed has to be greater than 0"))
            return

        # Get all segments from gcode
        allSegments = self.extractAllSegments(app, selBlocks)

        # Create holes locations
        for bidSegment in allSegments:
            if len(bidSegment) == 0:
                continue
        blocks = []
        n = "Troch3d"
        tr_block = Block(n)
        phi = oldphi = 0
        oldsegm = [[0, 0, 0], [0, 0, 0]]

        # segments ---------------------------------------------
        for idx, segm in enumerate(bidSegment):
            if idx >= 0:
                if cw:
                    u = 1
                else:
                    u = -1
                # ////////////-------------------------------------------------
                # information: ------------------------------------------------
                segLength = self.calcSegmentLength(segm)
                # ////////-----------------------------------------------------
                if idx == 0:
                    tr_block.append(
                        "(Cut diam "
                        + str(cutradius * 2)
                        + " (troch "
                        + str(radius * 2.0)
                        + "+End mill "
                        + str(toolRadius * 2.0)
                        + " ) Advance "
                        + str(atot)
                        + " )"
                    )
                    tr_block.append(
                        "(Feed " + str(feed) + " Plunge feed " + str(zfeed) + " )"
                    )
                    tr_block.append(
                        "(Helical descent angle "
                        + str(round(helicalangle, 2))
                        + " cut diam "
                        + str(round(helicalRadius * 2.0, 3))
                        + "  drop by lap "
                        + str(round(downPecking, 2))
                        + " )"
                    )
                    tr_block.append(
                        "(--------------------------------------------------)"
                    )
                    tr_block.append(
                        "(M06 T0 " + str(toolRadius * 2.0) + " mm)")
                    tr_block.append("M03")
                    tr_block.append("S " + str(rpm))
                    tr_block.append("F " + str(feed))
                    tr_block.append(
                        "( Seg: "
                        + str(idx)
                        + "   length "
                        + str(round(segLength, 4))
                        + "  phi "
                        + str(round(degrees(phi), 2))
                        + " )"
                    )
                    tr_block.append("(Starting point)")
                    if (
                        round(segm[1][1] - segm[0][1], 4) == 0
                        and round(segm[1][0] - segm[0][0], 4) == 0
                    ):
                        phi = 1234567890
                        tr_block.append(
                            "(The original first movement is vertical)")
                    else:
                        tr_block.append(
                            "(The original first movement is not vertical)")
                    tr_block.append(CNC.zsafe())
                    tr_block.append(
                        "(--------------------------------------------------)"
                    )

                # if there is movement in xy plane phi calculate
                if (segm[1][1] - segm[0][1] != 0
                        or segm[1][0] - segm[0][0] != 0):
                    phi = atan2(segm[1][1] - segm[0][1],
                                segm[1][0] - segm[0][0])
                    # On surface
                    if segm[0][2] > surface and segm[1][2] > surface:
                        tr_block.append(
                            "(Seg: "
                            + str(idx)
                            + " length "
                            + str(round(segLength, 4))
                            + " phi "
                            + str(round(degrees(phi), 2))
                            + " On Surface)"
                        )
                        tr_block.append(
                            CNC.grapid(segm[1][0], segm[1][1], segm[1][2]))
                    else:
                        tr_distance = self.center_distance(segm, atot)
                        A = segm[0][0], segm[0][1], segm[0][2]
                        d = segLength
                        ae = tr_distance[4]
                        # ////////////-----------------------------------------
                        # information: ----------------------------------------
                        adv = tr_distance[3]  # <<<
                        ap = tr_distance[2]  # << =zadd
                        # ---------------------------------------------
                        tr_block.append(
                            "(-----------------------------------------)")
                        control_cameback = self.came_back(segm, oldsegm)
                        if control_cameback:
                            tr_block.append(
                                "(-------------> Came back !! <------------- )"
                            )
                        if round(segLength, 5) <= dtadaptative:
                            adaptativepolice += 1.0
                            tr_block.append(
                                "(Seg "
                                + str(idx)
                                + " adaptativepolice "
                                + str(adaptativepolice)
                                + " length "
                                + str(round(segLength, 5))
                                + " )"
                            )
                        # /////////// Trochoid method ///////////////////////
                        if adaptativepolice == 0 or adaptativepolice > 2.5:

                            tr_block.append(
                                "( Seg: "
                                + str(idx)
                                + " phi "
                                + str(round(degrees(phi), 2))
                                + " oldphi "
                                + str(round(degrees(oldphi), 2))
                                + " length "
                                + str(round(segLength, 5))
                                + " )"
                            )
                            tr_block.append(
                                "(ae: "
                                + str(round(ae, 5))
                                + " dz: "
                                + str(round(ap, 4))
                                + "adv: "
                                + str(round(adv, 4))
                                + " )"
                            )
                            # ////////-----------------------------------------
                            if control_cameback:
                                B = segm[1][0], segm[1][1], segm[1][2]
                                t_splice = "came_back"
                                tr_block.extend(
                                    self.trochoid(
                                        t_splice, A, B, 0.0,
                                        radius, oldphi, phi, cw
                                    )
                                )
                                tr_block.append("F " + str(feed))
                                t_splice = self["TypeSplice"]

                            else:
                                # from POINT A -- to ---> POINT B
                                if segLength <= adv:
                                    tr_block.append(
                                        "(Only one trochoid, oldphi "
                                        + str(round(degrees(oldphi), 2))
                                        + " )"
                                    )
                                    tr_block.extend(
                                        self.trochoid(
                                            t_splice,
                                            A,
                                            B,
                                            oldradius,
                                            radius,
                                            oldphi,
                                            phi,
                                            cw,
                                        )
                                    )
                                while d > adv:
                                    B = (
                                        A[0] + tr_distance[0],
                                        A[1] + tr_distance[1],
                                        A[2] + tr_distance[2],
                                    )

                                    tr_block.append(
                                        "(distance to end segment "
                                        + str(round(d, 4))
                                        + " )"
                                    )
                                    tr_block.extend(
                                        self.trochoid(
                                            t_splice,
                                            A,
                                            B,
                                            oldradius,
                                            radius,
                                            oldphi,
                                            phi,
                                            cw,
                                        )
                                    )
                                    A = B
                                    d -= adv
                                    oldphi = phi
                                # last point
                                if (
                                    B[0] != segm[1][0]
                                    or B[1] != segm[1][1]
                                    or B[2] != segm[1][2]
                                ):
                                    B = segm[1][0], segm[1][1], segm[1][2]
                                    tr_block.append(
                                        "(---last trochoid, distance to "
                                        + "end segment "
                                        + str(round(d, 4))
                                        + " ---)"
                                    )
                                    tr_block.extend(
                                        self.trochoid(
                                            t_splice,
                                            A,
                                            B,
                                            oldradius,
                                            radius,
                                            phi,
                                            phi,
                                            cw,
                                        )
                                    )
                            adaptativepolice = 0

                        # /////// Adaptive method //////////////////////////
                        else:
                            if adaptativepolice == 1:
                                # goes to de two warning movements
                                lastphi = oldphi
                                tr_block.append(
                                    "( Alarm "
                                    + str(adaptativepolice)
                                    + "  Seg: "
                                    + str(idx)
                                    + " phi "
                                    + str(round(degrees(phi), 2))
                                    + "oldphi "
                                    + str(round(degrees(oldphi), 2))
                                    + " )"
                                )
                            elif adaptativepolice == 2:
                                phi = lastphi
                                if (
                                    control_cameback
                                ):
                                    tr_block.append(
                                        "(Starts adaptative trochoids"
                                        + " adaptativepolice "
                                        + str(adaptativepolice)
                                    )
                                    adaptativepolice += 0.5
                            elif adaptativepolice == 2.5:
                                tr_block.append(
                                    "(Adaptative Seg: "
                                    + str(idx)
                                    + "   length "
                                    + str(round(segLength, 5))
                                    + "  phi "
                                    + str(round(degrees(phi), 2))
                                    + " oldphi "
                                    + str(round(degrees(oldphi), 2))
                                    + " )"
                                )
                                tr_distance = self.center_distance(
                                    segm, atot / 3.0
                                )  # <<< short advanc distances

                                A = segm[0][0], segm[0][1], segm[0][2]
                                d = segLength
                                ae = tr_distance[4]
                                adv = tr_distance[3]  # <<<
                                d -= adv
                                while d > 0:  # adv:
                                    # first trochoid
                                    if d != segLength - adv:
                                        oldphi = phi
                                    B = (
                                        A[0] + tr_distance[0],
                                        A[1] + tr_distance[1],
                                        A[2] + tr_distance[2],
                                    )
                                    # ------------------------------
                                    a = radius / segLength
                                    adaptradius = self.roundup(a * d, 4)
                                    # ------------------------------
                                    if t_splice != "Splices":
                                        t_splice = "Warpedarc"
                                    tr_block.append(
                                        "(from trochoid distance to "
                                        + "end segment "
                                        + str(round(d, 4))
                                        + " )"
                                    )
                                    tr_block.append(
                                        "(adaptradius "
                                        + str(round(adaptradius, 4))
                                        + " radius "
                                        + str(radius)
                                        + " )"
                                    )
                                    tr_block.append(
                                        "F "
                                        + str(
                                            minimfeed
                                            + (feed - minimfeed)
                                            * adaptradius // radius
                                        )
                                    )
                                    if adaptradius > 0.0:
                                        tr_block.extend(
                                            self.trochoid(
                                                t_splice,
                                                A,
                                                B,
                                                oldradius,
                                                adaptradius,
                                                oldphi,
                                                phi,
                                                cw,
                                            )
                                        )
                                    else:
                                        tr_block.append(
                                            "(R= " + str(adaptradius)
                                            + "not sent )"
                                        )
                                    A = B
                                    d -= adv
                                    oldradius = adaptradius

                                adaptativepolice = 0
                                tr_block.append("(Adaptative Completed)")
                                tr_block.append("F " + str(feed // 3))

                            t_splice = self["TypeSplice"]
                            oldradius = radius
                        oldsegm = segm
                    oldphi = phi
                # /////// Vertical movement /////////////////////////////////
                elif idx != 0:
                    tr_block.append(
                        "(Seg: "
                        + str(idx)
                        + " length "
                        + str(round(segLength, 4))
                        + " phi "
                        + str(round(degrees(phi), 2))
                        + " oldphi "
                        + str(round(degrees(oldphi), 2))
                        + " )"
                    )
                    tr_block.append("(Helical descent")
                    # descent
                    A = segm[0][0], segm[0][1], segm[0][2]
                    if segm[0][2] > segm[1][2]:
                        if segm[0][2] > zbeforecontact:
                            if segm[1][2] <= zbeforecontact:
                                B = (
                                    segm[1][0],
                                    segm[1][1],
                                    max(segm[1][2], zbeforecontact),
                                )
                                tr_block.append(
                                    "(Rapid helical to z before contact "
                                    + "helicalRadius "
                                    + str(helicalRadius)
                                    + " )"
                                )
                                if idx == 1 and oldphi == 1234567890:
                                    tr_block.append(
                                        "g0 x " + str(B[0]) + " y"
                                        + str(B[1]) + " )"
                                    )
                                tr_block.extend(
                                    self.helical(A, B, helicalRadius, phi, u)
                                )

                        # Instead of decreasing the speed, to avoid the jerkl,
                        # decrease the drop by lap
                        if segm[0][2] > surface:
                            if segm[1][2] <= surface:
                                tr_block.append("(Slow helical to surface )")
                                A = A[0], A[1], zbeforecontact
                                d = A[2] - surface
                                adv = downPecking * feedbeforecontact
                                while d > adv:
                                    B = (
                                        segm[1][0],
                                        segm[1][1],
                                        max(segm[1][2], A[2] - adv),
                                    )
                                    tr_block.extend(
                                        self.helical(
                                            A, B, helicalRadius, phi, u)
                                    )
                                    A = A[0], A[1], B[2]
                                    d -= adv
                                B = segm[1][0], segm[1][1], surface
                                tr_block.extend(
                                    self.helical(A, B, helicalRadius, phi, u)
                                )

                        if segm[0][2] > hardcrust:
                            if hardcrust < surface:
                                if segm[1][2] <= hardcrust:
                                    tr_block.append("(Helical in hard crust)")
                                    A = A[0], A[1], surface
                                    d = A[2] - hardcrust
                                    adv = downPecking * hardcrustfeed
                                    while d > adv:
                                        B = (
                                            segm[1][0],
                                            segm[1][1],
                                            max(segm[1][2], A[2] - adv),
                                        )
                                        tr_block.extend(
                                            self.helical(
                                                A, B, helicalRadius, phi, u)
                                        )
                                        A = A[0], A[1], B[2]
                                        d -= adv
                                    B = segm[1][0], segm[1][1], hardcrust
                                    tr_block.extend(
                                        self.helical(
                                            A, B, helicalRadius, phi, u)
                                    )

                        tr_block.append("(Helical to target )")
                        A = A[0], A[1], hardcrust
                        d = A[2] - segm[1][2]
                        adv = downPecking
                        while d > adv:
                            B = segm[1][0], segm[1][1], A[2] - adv
                            tr_block.extend(
                                self.helical(A, B, helicalRadius, phi, u))
                            A = A[0], A[1], B[2]
                            d -= adv
                        B = segm[1][0], segm[1][1], segm[1][2]
                        tr_block.extend(
                            self.helical(A, B, helicalRadius, phi, u))
                        tr_block.append("(Flatten)")
                        tr_block.extend(
                            self.helical(B, B, helicalRadius, phi, u))
                        if round(helicalRadius, 4) != round(radius, 4):
                            tr_block.append("(Spiral adjustment)")
                            tr_block.append(
                                "(Spiral " + str(spiral_twists) + " twists)"
                            )
                            tr_block.extend(
                                self.splice_generator(
                                    B,
                                    B,
                                    helicalRadius,
                                    radius,
                                    phi,
                                    phi - spiral_twists * 2 * pi,
                                    radians(-90),
                                    radians(-90),
                                    u,
                                    1.2 * steps,
                                )
                            )
                            tr_block.append("(Target diameter)")
                            tr_block.extend(
                                self.trochoid(
                                    t_splice, B, B, radius,
                                    radius, phi, phi, cw
                                )
                            )

                    # ascent
                    elif segm[1][2] > segm[0][2]:
                        tr_block.append(
                            "(Helical rapid ascentt "
                            + "helicalRadius "
                            + str(helicalRadius)
                            + " )"
                        )
                        B = segm[1][0], segm[1][1], segm[1][2]
                        tr_block.extend(
                            self.helical(A, B, helicalRadius, phi, u))
        tr_block.append("(-----------------------------------------)")
        tr_block.append(
            CNC.zsafe()
        )  # <<< Move rapid Z axis to the safe height in Stock Material
        blocks.append(tr_block)
        self.finish_blocks(app, blocks)

    # ----------------------------------------------------------
    # Convert polar to cartesian and add that to existing vector
    def pol2car(self, r, phi, a=[0, 0]):
        return [round(a[0] + r * cos(phi), 5), round(a[1] + r * sin(phi), 5)]

    # Generate single trochoidal element between two points
    def trochoid(
            self, typesplice, A, B, oldradius, radius, oldphi, phi, cw=True):

        if self["splicesteps"] == "" or self["splicesteps"] < 4:
            steps = 4 / (2 * pi)
        else:
            steps = self["splicesteps"] / (2 * pi)

        t_splice = typesplice
        block = []

        if cw:
            u = 1
            arc = "G2"
            cut_splice = "G3"
        else:
            u = -1
            arc = "G3"
            cut_splice = "G2"

        al = self.pol2car(oldradius, phi + radians(90 * u), A)
        ar = self.pol2car(oldradius, phi + radians(-90 * u), A)
        bl = self.pol2car(radius, phi + radians(90 * u), B)
        br = self.pol2car(radius, phi + radians(-90 * u), B)

        splice_dist = sqrt((br[0] - al[0]) ** 2 + (br[1] - al[1]) ** 2)
        splice_radius = splice_dist / 2.0

        # This schematic drawing represents naming convention
        # of points and vectors calculated in previous block
        #
        #    <--L---
        #          ---R-->
        #
        #        *   *
        #     *         *
        #    *           *
        #   BL     B     BR
        #    *           *
        #    *     ^     *
        #    *     |     *
        #    *     |     *
        #    *           *
        #   AL     A     AR
        #    *           *
        #     *         *
        #        *   *

        # TODO: improve strategies
        #       block.append("g1 x"+str(al[0])+" y"+str(al[1])+" z"+str(A[2]))
        #       First splice to next trochoid =================================
        #       steps=self["splicesteps"]
        #       steps = max(steps*oldradius,steps*radius)#self["splicesteps"]
        #       steps = int(min(10,steps))#self["splicesteps"]

        block.append(
            "(---------trochoid center x "
            + str(round(B[0], 4))
            + " y "
            + str(round(B[1], 4))
            + " ---------)"
        )
        if t_splice == "came_back":
            block.append(
                CNC.gline(round(B[0], 5), round(B[1], 5), round(B[2], 5)))
            block.append(
                arc
                + " x"
                + str(round(br[0], 4))
                + " y"
                + str(round(br[1], 4))
                + " R"
                + str(self.roundup(radius / 2.0, 3))
                + " z"
                + str(round(B[2], 4))
            )
        else:
            block.append(
                "( phi "
                + str(round(degrees(phi), 2))
                + " oldphi "
                + str(round(degrees(oldphi), 2))
                + " )"
            )
            if oldphi != phi:
                block.append(
                    f"({' Direction changed olldhi ':=^60})"
                )
                block.append("( Splice arch for direction change )")
                block.extend(
                    self.curve_splice_generator(
                        A,
                        A,
                        oldradius,
                        oldradius,
                        oldphi,
                        phi,
                        radians(270),
                        radians(-90),
                        u,
                        4,
                    )
                )  # << steps=4
                block.append(
                    f"({' End Direction changed ':=^60})"
                )

            if t_splice == "Splices":
                block.extend(
                    self.splice_generator(
                        A,
                        B,
                        oldradius,
                        radius,
                        oldphi,
                        phi,
                        radians(-90),
                        radians(90),
                        u,
                        steps,
                    )
                )

            elif t_splice == "Circular one side rectified":
                block.append(
                    arc
                    + " x"
                    + str(round(al[0], 4))
                    + " y"
                    + str(round(al[1], 4))
                    + " R"
                    + str(self.roundup(oldradius, 3))
                    + " z"
                    + str(round(B[2], 5))
                )
                block.append(
                    "g1 x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " z"
                    + str(round(B[2], 4))
                )

            elif t_splice == "Circular both sides rectified":
                block.append(
                    "g1 x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " z"
                    + str(round(B[2], 4))
                )

            elif t_splice == "Straight":
                block.append(
                    "g1 x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " z"
                    + str(round(B[2], 4))
                )

            elif t_splice == "Warpedarc":
                warped_radius = (
                    sqrt((ar[0] - bl[0]) ** 2 + (ar[1] - bl[1]) ** 2)
                ) / 2.0
                block.append("(Warpedarc)")
                block.append(
                    "(control previous position arx "
                    + str(round(ar[0], 4))
                    + " ary "
                    + str(round(ar[1], 4))
                    + " R "
                    + str(warped_radius)
                    + " )"
                )
                block.append(
                    arc
                    + " x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " R"
                    + str(self.roundup(warped_radius, 3))
                    + " z"
                    + str(round(B[2], 5))
                )

            elif t_splice == "Straight on side rectified":
                block.append(
                    "g1 x" + str(round(al[0], 4)) + " y" + str(round(al[1], 4))
                )
                block.append(
                    "g1 x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " z"
                    + str(round(B[2], 4))
                )

            elif t_splice == "Cut":
                block.append(
                    "g1 x" + str(round(ar[0], 4)) + " y" + str(round(ar[1], 4))
                )
                block.append(
                    cut_splice
                    + "x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + "R"
                    + str(self.roundup(splice_radius, 3))
                    + " z"
                    + str(round(B[2], 4))
                )

            # ===========================================================
            #   cut
            block.append("(cuting)")
            block.append(
                arc
                + " x"
                + str(round(br[0], 4))
                + " y"
                + str(round(br[1], 4))
                + " R"
                + str(self.roundup(radius, 3))
                + " z"
                + str(round(B[2], 4))
            )
            # ===============================================================
            if t_splice == "Circular both sides rectified":
                block.append(
                    "g1 x"
                    + str(round(ar[0], 4))
                    + " y"
                    + str(round(ar[1], 4))
                    + " z"
                    + str(round(A[2], 4))
                )
                block.append(
                    arc
                    + " x"
                    + str(round(al[0], 4))
                    + " y"
                    + str(round(al[1], 4))
                    + " R"
                    + str(self.roundup(oldradius, 3))
                    + " z"
                    + str(round(A[2], 4))
                )
                # <<in adaptativee presents problems of location of the
                #   center in change of angle
                block.append(
                    "g1 x"
                    + str(round(bl[0], 4))
                    + " y"
                    + str(round(bl[1], 4))
                    + " z"
                    + str(round(B[2], 4))
                )

        return block

    # --------------------------------------------------------------
    def splice_generator(
            self, C1, C2, r1, r2, phi1, phi2, alpha_1, alpha_2, u, steps):
        block = []

        alpha1 = phi1 + alpha_1 * u
        alpha2 = phi2 + alpha_2 * u
        if u == 1:
            if alpha1 <= alpha2:
                alpha1 += 2 * pi
                if alpha1 <= alpha2:
                    alpha1 += 2 * pi
        elif u == -1:
            if alpha1 >= alpha2:
                alpha1 -= 2 * pi
                if alpha1 >= alpha2:
                    alpha1 -= 2 * pi
        steps = int(abs(steps * (alpha2 - alpha1)))
        if steps == 0:
            steps = 1
        d_r = r2 - r1
        d_r = d_r / steps

        d_a = alpha2 - alpha1
        d_a = d_a / steps

        d_c_x = (C2[0] - C1[0]) / steps
        d_c_y = (C2[1] - C1[1]) / steps
        d_c_z = (C2[2] - C1[2]) / steps
        r = r1
        alpha = alpha1
        C = C1
        i = 0

        a0 = self.pol2car(r1, alpha1, C1)
        block.append(
            "(alpha1 "
            + str(round(degrees(alpha1), 2))
            + " alpha2 "
            + str(round(degrees(alpha2), 2))
            + " first splice point )"
        )
        block.append(
            "(phi-oldphi "
            + str(round(degrees(phi2 - phi1), 2))
            + " steps "
            + str(steps)
            + " )"
        )
        block.append(
            "g1 x" + str(round(a0[0], 4)) + " y" + str(round(a0[1], 4))
        )

        while i < (
            steps
        ):
            r += d_r
            alpha += d_a
            C = C[0] + d_c_x, C[1] + d_c_y, C[2] + d_c_z
            ai = self.pol2car(r, alpha, C)
            block.append("(alpha " + str(round(degrees(alpha), 2)) + " )")
            block.append(
                "g1 x"
                + str(round(ai[0], 4))
                + " y"
                + str(round(ai[1], 4))
                + " z"
                + str(round(C[2], 4))
            )
            i += 1
        return block

    # --------------------------------------------------------------
    def curve_splice_generator(
        self, C1, C2, r1, r2, phi1, phi2, alpha_1, alpha_2, u, steps
    ):
        block = []

        alpha1 = phi1 + alpha_1 * u
        alpha2 = phi2 + alpha_2 * u
        if u == 1:
            arc = "G2"
            if alpha1 <= alpha2:
                alpha1 += 2 * pi
                if alpha1 <= alpha2:
                    alpha1 += 2 * pi
        elif u == -1:
            arc = "G3"
            if alpha1 >= alpha2:
                alpha1 -= 2 * pi
                if alpha1 >= alpha2:
                    alpha1 -= 2 * pi
        if steps == 0:
            steps = 2
        # delta or increase in values radius, anle, center position
        d_r = r2 - r1
        d_r = d_r / steps

        d_a = alpha2 - alpha1
        d_a = d_a / steps

        d_c_x = (C2[0] - C1[0]) / steps
        d_c_y = (C2[1] - C1[1]) / steps
        d_c_z = (C2[2] - C1[2]) / steps
        r = r1
        alpha = alpha1
        C = C1
        i = 0

        a0 = self.pol2car(r1, alpha1, C1)
        block.append(
            "(alpha1 "
            + str(round(degrees(alpha1), 2))
            + " alpha2 "
            + str(round(degrees(alpha2), 2))
            + " first splice point )"
        )
        block.append(
            "(phi-oldphi "
            + str(round(degrees(phi2 - phi1), 2))
            + " steps "
            + str(steps)
            + " )"
        )
        block.append(
            "g1 x" + str(round(a0[0], 4)) + " y" + str(round(a0[1], 4))
        )  # +" z"+str(round(C[1],5)))

        while i < (
            steps
        ):
            r += d_r
            alpha += d_a
            C = C[0] + d_c_x, C[1] + d_c_y, C[2] + d_c_z
            ai = self.pol2car(r, alpha, C)
            block.append("(alpha " + str(round(degrees(alpha), 2)) + " )")
            block.append(
                arc
                + " x"
                + str(round(ai[0], 4))
                + " y"
                + str(round(ai[1], 4))
                + " R "
                + str(self.roundup(r, 3))
                + " z"
                + str(round(C[2], 4))
            )
            i += 1
        return block

    # --------------------------------------------------------------
    def helical(self, A, C, radius, phi, u):
        block = []
        t_splice = self["TypeSplice"]
        if u == 1:
            arc = "G2"
        else:
            u = -1
            arc = "G3"

        l_ = self.pol2car(radius, phi + radians(90 * u))
        r = self.pol2car(radius, phi + radians(-90 * u))
        bl = self.pol2car(radius, phi + radians(90 * u), C)
        br = self.pol2car(radius, phi + radians(-90 * u), C)

        radius = round(radius, 4)
        l_[0] = round(l_[0], 4)
        l_[1] = round(l_[1], 4)
        r[0] = round(r[0], 4)
        r[1] = round(r[1], 4)

        # RESOLVE CONFLICT G2 G3 I J
        obteinedradius = sqrt(l_[0] ** 2 + l_[1] ** 2)
        if obteinedradius > radius:
            block.append(
                "(error G2 G3: radius "
                + str(radius)
                + " radius with sqrt "
                + str(obteinedradius)
                + " )"
            )
            radius = self.roundup(obteinedradius, 3)
            block.append("(new radius " + str(radius) + " )")
        if t_splice == "Circular both sides rectified":
            block.append(
                arc
                + " x"
                + str(round(bl[0], 4))
                + " y"
                + str(round(bl[1], 4))
                + " i"
                + str(-l_[0])
                + " j"
                + str(-l_[1])
                + " z"
                + str(round(C[2], 4))
            )
        else:
            block.append(
                "G1 x" + str(round(br[0], 4)) + " y" + str(round(br[1], 4)))
            z_interm = (A[2] + C[2]) / 2.0
            block.append(
                arc
                + " x"
                + str(round(bl[0], 4))
                + " y"
                + str(round(bl[1], 4))
                + " R"
                + str(self.roundup(radius, 4))
                + " z"
                + str(round(z_interm, 4))
            )
            block.append(
                arc
                + " x"
                + str(round(br[0], 4))
                + " y"
                + str(round(br[1], 4))
                + " R"
                + str(self.roundup(radius, 4))
                + " z"
                + str(round(C[2], 4))
            )

        return block

    # --------------------------------------------------------------
    def roundup(self, number, decimals):
        if number < 0:
            sign = -1
        else:
            sign = 1
        number = round(number, decimals) + 0.1**decimals * sign
        return number

    # Insert created blocks
    def finish_blocks(self, app, blocks):
        active = app.activeBlock()
        app.gcode.insBlocks(active + 1, blocks, "Trochs")
        app.refresh()
        app.setStatus(_("Trochoid Generated"))
