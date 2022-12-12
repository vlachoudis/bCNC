# $Id$
#
# Author: Filippo Rivato
# Date: 9 November 2015
# A special thanks to Vasilis for his patient explanations

import math
import os.path
import re
from collections import OrderedDict

import Utils
from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "Filippo Rivato"
__email__ = "f.rivato@gmail.com"

__name__ = _("Driller")
__version__ = "0.0.10"


# =============================================================================
# Driller class
# =============================================================================
class Driller:
    def __init__(self, name="Driller"):
        self.name = name


# =============================================================================
# Create holes along selected blocks
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Create holes along selected blocks")

    def __init__(self, master):
        Plugin.__init__(self, master, "Driller")
        self.icon = "driller"
        self.group = "CAM"

        self.variables = [
            ("name", "db", "", _("Name")),
            ("HolesDistance", "mm", 10.0, _("Distance between holes")),
            ("TargetDepth", "mm", 0.0, _("Target Depth")),
            ("Peck", "mm", 0.0, _("Peck, 0 means None")),
            ("Dwell", "float", 0.0, _("Dwell time, 0 means None")),
            ("useAnchor", "bool", False, _("Use anchor")),
            ("File", "file", "", _("Excellon-File")),
            ("useCustom", "bool", False, _("M3 for laser (settings below)")),
            (
                "rFeed",
                "int",
                "",
                _("Feed rapid G0"),
                "Defaults from config, if blank",
            ),
            (
                "spinMin",
                "int",
                "",
                _("Laser power minimum"),
                "Defaults from config, if blank",
            ),
            (
                "spinMax",
                "int",
                "",
                _("Laser power maximum"),
                "Defaults from config, if blank",
            ),
        ]
        self.buttons.append("exe")

    # Excellon Coordsconvert
    def coord2float(self, text, unitinch, decimals=0.001):
        if "." in text:
            return float(text)
        if unitinch is True:
            return float(text) * 0.0001
        # Unit mm
        # modified to read the number of decimals from file
        return int(text) * decimals

    # Convert to systemsetting
    def convunit(self, value, unitinch):
        if unitinch == CNC.inch:
            return value
        if unitinch is True and CNC.inch is False:
            return value * 25.4
        if unitinch is False and CNC.inch:
            return value / 25.4

    # Excellon Import
    def excellonimport(self, filename, app):
        fo = open(filename)
        header = None
        current_tool = None
        incrementcoord = False
        unitinch = True
        data = {"tools": {}}
        targetDepth = self.fromMm("TargetDepth")
        for row in fo.readlines():
            line = row.strip()
            if len(line) != 0:
                if line[0] != ";":
                    # Read header
                    if line == "M48":
                        header = True
                    if header is True:
                        if (line.startswith("INCH")
                                or line.startswith("METRIC")):
                            unitinch = line.startswith("INCH")
                            decimals = 0.1 ** len(
                                line[line.index("."): -1]
                            )  # calculates the multiplier for decimal places
                        if line == "M95" or line == "%":
                            header = False
                        if line[0] == "T":
                            # Tools
                            m = re.match(r"(T\d+)C(.+)", line)
                            data["tools"][m.group(1)] = {
                                "diameter": float(m.group(2)),
                                "holes": [],
                            }
                        if line == "ICI":
                            incrementcoord = True
                    if header is False:
                        if line[0] == "T":
                            current_tool = line
                        if line[0] == "X":
                            m = re.match(r"X([\d\.-]+)Y([\d\.-]+)", line)
                            # Convert to system
                            x = self.convunit(
                                self.coord2float(m.group(1),
                                                 unitinch, decimals),
                                unitinch,
                            )
                            y = self.convunit(
                                self.coord2float(m.group(2),
                                                 unitinch, decimals),
                                unitinch,
                            )
                            if incrementcoord is True:
                                if len(data["tools"][current_tool]["holes"]) == 0:
                                    prevx = 0
                                    prevy = 0
                                else:
                                    prevx = data["tools"][current_tool]["holes"][-1][0]
                                    prevy = data["tools"][current_tool]["holes"][-1][1]
                                x = x + prevx
                                y = y + prevy
                            data["tools"][current_tool]["holes"].append(
                                (x, y, targetDepth)
                            )

        unittext = "inch" if CNC.inch else "mm"
        n = self["name"]
        if not n or n == "default":
            n = "Driller"
        holesCounter = 0
        blocks = []
        for tool in data["tools"]:
            dia = self.convunit(data["tools"][tool]["diameter"], unitinch)
            # Duplicates shouldn't be in the list - remove unnecessary
            blockholes = [data["tools"][tool]["holes"]]
            block, holesCount = self.create_block(
                blockholes, n + " (" + str(dia) + " " + unittext + ")"
            )
            holesCounter = holesCounter + holesCount
            if not CNC.lasercutter:
                block.insert(
                    0, "M6 T" + str(dia).replace(".", "")
                )  # added a tool change command
            blocks.append(block)

        self.finish_blocks(app, blocks, holesCounter)

    # Calc subsegments -----------------------------------------------------
    # TODO Move to Utils? A few plugins use this
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

    # Extract all segments from commands -----------------------------------
    # TODO Move to Utils? A few plugins use this
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
                except Exception:
                    cmd = None

                if cmd:
                    app.cnc.motionStart(cmd)
                    xyz = app.cnc.motionPath()
                    app.cnc.motionEnd()

                    if xyz:
                        # Exclude if fast move or z only movement
                        G0 = "G0" in cmd[0].upper()
                        Zonly = xyz[0][0] == xyz[1][0] and xyz[0][1] == xyz[1][1]
                        exclude = G0 or Zonly

                        # Save length for later use
                        segLenth = self.calcSegmentLength(xyz)

                        if len(xyz) < 3:
                            bidSegments.append([xyz[0], xyz[1], exclude, segLenth])
                        else:
                            for i in range(len(xyz) - 1):
                                bidSegments.append(
                                    [xyz[i], xyz[i + 1], exclude, segLenth]
                                )
            # Append bidSegments to allSegments
            allSegments.append(bidSegments)

        # Disable used block
        for bid in selectedBlock:
            block = allBlocks[bid]
            if block.name() in ("Header", "Footer"):
                continue
            block.enable = False

        return allSegments

    # ----------------------------------------------------------------------
    def execute(self, app):
        # Get inputs
        holesDistance = self.fromMm("HolesDistance")
        peck = self.fromMm("Peck")
        dwell = self["Dwell"]
        useAnchor = self["useAnchor"]
        excellonFileName = self["File"]

        # ------------------------------------------------------------------
        # Custom for laser in M3 mode
        self.useCustom = self["useCustom"]

        self.rFeed = int(min(CNC.feedmax_x, CNC.feedmax_y))
        if self["rFeed"]:
            self.rFeed = self["rFeed"]

        self.spinMin = Utils.config.get("CNC", "spindlemin")
        if self["spinMin"]:
            self.spinMin = self["spinMin"]

        self.spinMax = Utils.config.get("CNC", "spindlemax")
        if self["spinMax"]:
            self.spinMax = self["spinMax"]
        # ------------------------------------------------------------------

        # Check inputs
        if holesDistance <= 0 and useAnchor is False:
            app.setStatus(_("Driller abort: Distance must be > 0"))
            return

        if peck < 0:
            app.setStatus(_("Driller abort: Peck must be >= 0"))
            return

        if dwell < 0:
            app.setStatus(
                _("Driller abort: Dwell time >= 0, here time runs only forward!")
            )
            return

        if excellonFileName != "":
            if os.path.isfile(excellonFileName):
                self.excellonimport(excellonFileName, app)
            else:
                app.setStatus(_("Driller abort: Excellon-File not a file"))
            return

        # Get selected blocks from editor
        selBlocks = app.editor.getSelectedBlocks()
        if not selBlocks:
            app.editor.selectAll()
            selBlocks = app.editor.getSelectedBlocks()

        if not selBlocks:
            app.setStatus(_("Driller abort: Please select some path"))
            return

        # Get all segments from gcode
        allSegments = self.extractAllSegments(app, selBlocks)

        # Create holes locations
        allHoles = []
        for bidSegment in allSegments:
            if len(bidSegment) == 0:
                continue

            if useAnchor is True:
                bidHoles = []
                for idx, anchor in enumerate(bidSegment):
                    if idx > 0:
                        if self.useCustom:
                            if (
                                anchor[0][0] != anchor[1][0]
                                and anchor[0][1] != anchor[1][1]
                            ):
                                newHolePoint = (
                                    anchor[1][0],
                                    anchor[1][1],
                                    anchor[0][2],
                                )
                                bidHoles.append(newHolePoint)
                        else:
                            newHolePoint = (anchor[0][0], anchor[0][1], anchor[0][2])
                            bidHoles.append(newHolePoint)
            else:
                # Sum all path length
                fullPathLength = 0.0
                for s in bidSegment:
                    fullPathLength += s[3]

                # Calc rest
                holes = fullPathLength // holesDistance
                rest = fullPathLength - (holesDistance * (holes))
                # Travel along the path
                elapsedLength = rest / 2.0  # Equally distribute rest, as option???
                bidHoles = []
                while elapsedLength <= fullPathLength:
                    # Search best segment to apply line interpolation
                    bestSegment = bidSegment[0]
                    segmentsSum = 0.0
                    perc = 0.0
                    for s in bidSegment:
                        bestSegment = s
                        segmentLength = bestSegment[3]
                        perc = (elapsedLength - segmentsSum) / segmentLength
                        segmentsSum += segmentLength
                        if segmentsSum > elapsedLength:
                            break

                    # Fist point
                    x1 = bestSegment[0][0]
                    y1 = bestSegment[0][1]
                    z1 = bestSegment[0][2]
                    # Last point
                    x2 = bestSegment[1][0]
                    y2 = bestSegment[1][1]
                    z2 = bestSegment[1][2]

                    # Check if segment is not excluded
                    if not bestSegment[2]:
                        newHolePoint = (
                            x1 + perc * (x2 - x1),
                            y1 + perc * (y2 - y1),
                            z1 + perc * (z2 - z1),
                        )
                        bidHoles.append(newHolePoint)

                    # Go to next hole
                    elapsedLength += holesDistance
            # Remove duplicates
            bidHoles = list(OrderedDict.fromkeys(bidHoles))
            # Add bidHoles to allHoles
            allHoles.append(bidHoles)

        # Write gcommands from allSegments to the drill block
        blocks = []
        n = self["name"]
        if not n or n == "default":
            n = "Driller"
        if self.useCustom:
            n += "-laser-mode"
        block, holesCount = self.create_block(allHoles, n)
        blocks.append(block)
        self.finish_blocks(app, blocks, holesCount)

    # Write gcommands from allHoles to the drill block
    def create_block(self, holes, name):
        targetDepth = self.fromMm("TargetDepth")
        peck = self.fromMm("Peck")
        dwell = self["Dwell"]
        block = Block(name)
        holesCount = 0

        if self.useCustom:
            block.append("M3 S0")
        else:
            block.append(CNC.zsafe())

        for bid in holes:
            for xH, yH, zH in bid:
                holesCount += 1

                if self.useCustom:
                    block.append(CNC.grapid(x=xH, y=yH) + CNC.fmt(" F", self.rFeed))
                else:
                    block.append(CNC.grapid(xH, yH))

                if peck != 0:
                    z = 0
                    while z > targetDepth:
                        z = max(z - peck, targetDepth)
                        if self.useCustom:
                            block.append(
                                "( --- WARNING! Peck is not setup for laser mode --- )"
                            )
                            break
                        else:
                            block.append(CNC.zenter(zH + z))
                            block.append(CNC.zsafe())

                if self.useCustom:
                    block.append(f"G1 S{self.spinMax}")
                    block.append(CNC.gline(x=xH, y=yH))
                else:
                    block.append(CNC.zenter(targetDepth))

                # Dwell time only on last pass
                if dwell != 0:
                    block.append(CNC.gcode(4, [("P", dwell)]))

                if self.useCustom:
                    block.append(f"G1 S{self.spinMin}")
                else:
                    block.append(CNC.zsafe())

        # Gcode Zsafe on finish
        if self.useCustom:
            block.append("M5")
        else:
            block.append(CNC.zsafe())
        return (block, holesCount)

    # Insert created blocks
    def finish_blocks(self, app, blocks, numberholes):
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, "Driller")
        app.refresh()
        app.setStatus(_("Generated Driller: {} holes").format(numberholes))
