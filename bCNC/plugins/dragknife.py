# Author: @harvie Tomas Mudrunka
# Date: 25 sept 2018
#
# Modified version:
# - adds DragKnife "overcut" setting
# - overcut follows the ORIGINAL closed path by repeating its start
#   for the requested distance before drag-knife compensation is generated.

from math import (
    acos,
    degrees,
    sqrt,
)

from bmath import Vector
from bpath import Path, Segment, eq
from CNC import CNC
from ToolsPage import Plugin

__author__ = "@harvie Tomas Mudrunka"
# __email__ = ""
__name__ = _("DragKnife")
__version__ = "0.3.1-overcut"


class Tool(Plugin):
    __doc__ = _("""Drag knife postprocessor""")

    def __init__(self, master):
        Plugin.__init__(self, master, "DragKnife")
        self.icon = "dragknife"
        self.group = "CAM_Core"

        self.variables = [
            (
                "name",
                "db",
                "",
                _("Name"),
            ),
            (
                "offset",
                "mm",
                3,
                _("dragknife offset"),
                _("distance from dragknife rotation center to the tip of the blade"),
            ),
            (
                "angle",
                "float",
                20,
                _("angle threshold"),
                _("do not perform pivot action for angles smaller than this"),
            ),
            (
                "swivelz",
                "mm",
                0,
                _("swivel height"),
                _(
                    "retract to this height for pivots (useful for thick materials, "
                    "you should enter number slightly lower than material thickness)"
                ),
            ),
            (
                "initdir",
                "X+,Y+,Y-,X-,none",
                "X+",
                _("initial direction"),
                _(
                    "direction that knife blade is facing before and after cut. "
                    "Eg.: if you set this to X+, then the knife's rotation axis should "
                    "be on the right side of the tip. Meaning that the knife is ready "
                    "to cut towards right immediately without pivoting. If you cut "
                    "multiple shapes in single operation, it's important to have this "
                    "set consistently across all of them."
                ),
            ),
            ("feed", "mm", 200, _("feedrate")),
            (
                "overcut",
                "mm",
                0.0,
                _("path overcut"),
                _(
                    "continue cutting along the original closed path for this extra "
                    "distance; useful for closing drag knife cuts"
                ),
            ),
            (
                "simulate",
                "bool",
                False,
                _("simulate"),
                _(
                    "Use this option to simulate cuting of dragknife path. Resulting "
                    "shape will reflect what shape will actually be cut. This should "
                    "reverse the dragknife procedure and give you back the original "
                    "shape from g-code that was previously processed for dragknife."
                ),
            ),
            (
                "simpreci",
                "mm",
                0.5,
                _("simulation precision"),
                _(
                    "Simulation is currently approximated by using lots of short lines. "
                    "This is the length of these lines."
                ),
            ),
            (
                "dwell",
                "s",
                0.0,
                _("pause / dwell"),
                _(
                    "On some machines the solenoid that drops and lifts the knife "
                    "simply isn't fast enough, which leaves uncut segments when the "
                    "knife enters a cut and leaves scratches when the knife exits a "
                    "cut. Use this variable to add delay after the knife is droppend/"
                    "lifted to allow the solenoid to catch up."
                ),
            ),
        ]

        self.buttons.append("exe")
        self.help = """DragKnifes are special kind of razor/blade holders that can be fit into spindle of your CNC (do not turn the spindle on!!!). They are often used to cut soft and thin materials like vinyl stickers, fabric, leather, rubber gaskets, paper, cardboard, etc...

Dragknife blade is located off center to allow for automatic rotation (kinda like rear wheels of car pivot to the direction of front wheels). This fact introduces the need for preprocessing the g-code to account with that offset. Otherwise it wouldn't be able to cut sharp corners. This plugin does this g-code postprocessing.

This modified version also supports path overcut. For closed paths, it repeats the beginning of the original path for the chosen overcut distance before creating the drag-knife compensated toolpath.
"""

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        dragoff = self.fromMm("offset")
        overcut = self.fromMm("overcut")

        angleth = self["angle"]
        swivelz = self.fromMm("swivelz")
        initdir = self["initdir"]
        CNC.vars["cutfeed"] = self.fromMm("feed")
        simulate = self["simulate"]
        simpreci = self["simpreci"]
        dwell = self["dwell"]

        def initPoint(P, direction, offset):
            P = Vector(P[0], P[1])

            if direction == "X+":
                P[0] += offset
            elif direction == "X-":
                P[0] -= offset
            elif direction == "Y+":
                P[1] += offset
            elif direction == "Y-":
                P[1] -= offset

            return P

        def segmentLength(seg):
            return sqrt(
                (seg.B[0] - seg.A[0]) ** 2 +
                (seg.B[1] - seg.A[1]) ** 2
            )

        def addPathOvercut(path, distance, precision):
            """Repeat the beginning of a CLOSED original path.

            This is done before dragknife compensation, so the added overcut
            follows the original geometry. Arcs are approximated using
            path.linearize(precision, True), so curved starts are followed
            using short line segments.
            """
            if distance <= 0:
                return

            if len(path) < 1:
                return

            # Only closed paths can be overcut by repeating their beginning.
            # For open paths there is no meaningful "wrap to start".
            if not eq(path[-1].B, path[0].A):
                return

            # Work from a linearized copy so arcs can be partially repeated.
            lpath = path.linearize(precision, True)
            if len(lpath) < 1:
                return

            remaining = distance
            current = Vector(path[-1].B[0], path[-1].B[1])

            # Repeat the start of the path until requested distance is consumed.
            # This permits overcut longer than the first segment.
            safety = 0
            while remaining > 0 and safety < 10000:
                safety += 1
                consumed_something = False

                for seg in lpath:
                    seglen = segmentLength(seg)
                    if seglen <= 0:
                        continue

                    direction = (seg.B - seg.A).unit()

                    if remaining >= seglen:
                        newB = current + direction * seglen
                        path.append(Segment(Segment.LINE, current, newB))
                        current = newB
                        remaining -= seglen
                        consumed_something = True
                    else:
                        newB = current + direction * remaining
                        path.append(Segment(Segment.LINE, current, newB))
                        remaining = 0
                        consumed_something = True
                        break

                if not consumed_something:
                    break

        blocks = []

        for bid in app.editor.getSelectedBlocks():
            if len(app.gcode.toPath(bid)) < 1:
                continue

            opath = app.gcode.toPath(bid)[0]
            npath = Path(f"dragknife {dragoff}: {app.gcode[bid].name()}")

            if not simulate:
                # Entry vector
                ventry = Segment(
                    Segment.LINE,
                    initPoint(opath[0].A, initdir, -dragoff),
                    opath[0].A
                )

                # Path-following overcut:
                # Repeat the beginning of the original closed path before
                # tangential drag-knife offset is generated.
                addPathOvercut(opath, overcut, simpreci)

                # Exit vector
                vexit = Segment(
                    Segment.LINE,
                    opath[-1].B,
                    initPoint(opath[-1].B, initdir, dragoff)
                )

                opath.append(vexit)
                prevseg = ventry

                # Generate path with tangential lag for dragknife operation
                for i, seg in enumerate(opath):
                    # Get adjacent tangential vectors in this point
                    TA = prevseg.tangentEnd()
                    TB = seg.tangentStart()

                    # Compute difference between tangential vectors of
                    # two neighbor segments
                    angle = degrees(acos(TA.dot(TB)))

                    # Compute swivel direction
                    arcdir = (TA[0] * TB[1]) - (TA[1] * TB[0])
                    if arcdir < 0:
                        arcdir = Segment.CW
                    else:
                        arcdir = Segment.CCW

                    # Append swivel if needed
                    # with an angle threshold of 1 degree on entry/exit segments
                    if abs(angle) > angleth or (
                        abs(angle) > 1 and (i == 0 or i == len(opath) - 1)
                    ):
                        arca = Segment(
                            arcdir,
                            prevseg.tangentialOffset(dragoff).B,
                            seg.tangentialOffset(dragoff).A,
                            prevseg.B,
                        )

                        if swivelz != 0:
                            arca._inside = [swivelz]

                        npath.append(arca)

                    # Append segment with tangential offset
                    if i < len(opath) - 1:
                        newSeg = seg.tangentialOffset(dragoff)

                        # To keep the path connected, we use the end of the
                        # previous segment as the start of this segment.
                        # If there is no previous entry, use the ventry vector.
                        if len(npath) == 0:
                            newSeg.setStart(ventry.B)
                        else:
                            newSeg.setStart(npath[-1].B)

                        npath.append(newSeg)

                    prevseg = seg

            elif simulate:
                # In simulate mode we simulate the path that would be cut.
                # Keep overcut behavior consistent here too.
                addPathOvercut(opath, overcut, simpreci)

                opath = opath.linearize(simpreci, True)
                prevknife = initPoint(opath[0].A, initdir, -dragoff)

                for seg in opath:
                    dist = sqrt(
                        (seg.B[0] - prevknife[0]) ** 2 +
                        (seg.B[1] - prevknife[1]) ** 2
                    )
                    move = (seg.B - prevknife).unit() * (dist - dragoff)
                    newknife = prevknife + move

                    if not eq(newknife, prevknife):
                        npath.append(Segment(Segment.LINE, prevknife, newknife))

                    prevknife = newknife

            eblock = app.gcode.fromPath(path=npath)
            blocks.append(eblock)

        active = -1
        app.gcode.insBlocks(active, blocks, "Dragknife")
        app.refresh()
        app.setStatus(_("Generated: Dragknife"))
