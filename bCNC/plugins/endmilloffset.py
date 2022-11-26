# Author: @DodoLaSaumure Pierre KLein
# Date: 9 feb 2021

import sys
from copy import deepcopy
from tkinter import messagebox

from bpath import Path, Segment
from ToolsPage import Plugin

__author__ = "@DodoLaSaumure  (Pierre Klein)"

__name__ = _("Offset")
__version__ = "0.0.1"


# =============================================================================
def pocket(
    selectedblocks,
    RecursiveDepth,
    ProfileDir,
    CutDir,
    AdditionalCut,
    Overcuts,
    CustomRecursiveDepth,
    ignoreIslands,
    allowG1,
    diameter,
    stepover,
    name,
    gcode,
    app,
):
    undoinfo = []
    msg = ""
    newblocks = []
    allblocks = gcode.blocks
    islandslist = []
    outpathslist = []
    ignoreIslandschoicedict = {
        "Regard all islands except tabs": 0,
        "Ignore all islands": 1,
        "Regard only selected islands": 2,
    }
    ignoreIslandschoice = ignoreIslandschoicedict.get(ignoreIslands, 0)
    for bid, block in enumerate(allblocks):  # all blocks
        if block.operationTest("island") and not block.operationTest("tab"):
            if ignoreIslandschoice == 0:
                for islandPath in gcode.toPath(bid):
                    islandslist.append(islandPath)
    for bid in reversed(selectedblocks):  # selected blocks
        if allblocks[bid].name() in ("Header", "Footer"):
            continue
        block = allblocks[bid]
        if (
            block.operationTest("island")
            and not block.operationTest("tab")
            and ignoreIslandschoice == 2
        ):
            for islandPath in gcode.toPath(bid):
                islandslist.append(islandPath)
        for path in gcode.toPath(bid):
            if not path.isClosed():
                m = f"Path: '{path.name}' is OPEN"
                if m not in msg:
                    if msg:
                        msg += "\n"
                    msg += m
                path.close()
            # Remove tiny segments
            path.removeZeroLength(abs(diameter) / 100.0)
            # Convert very small arcs to lines
            path.convert2Lines(abs(diameter) / 10.0)
            if not block.operationTest("island"):
                outpathslist.append(path)
        MyPocket = PocketIsland(
            outpathslist,
            RecursiveDepth,
            ProfileDir,
            CutDir,
            AdditionalCut,
            Overcuts,
            CustomRecursiveDepth,
            ignoreIslands,
            allowG1,
            diameter,
            stepover,
            0,
            app,
            islandslist,
        )
        newpathList = MyPocket.getfullpath()
        # concatenate newpath in a single list and split2contours
        if allowG1:
            MyFullPath = Path("Pocket")
            for path in newpathList:
                for seg in path:
                    MyFullPath.append(seg)
            newpathList = MyFullPath.split2contours()
        if newpathList:
            # remember length to shift all new blocks
            # the are inserted before
            before = len(newblocks)
            undoinfo.extend(
                gcode.importPath(bid + 1, newpathList, newblocks, True, False)
            )
            new = len(newblocks) - before
            for i in range(before):
                newblocks[i] += new
            allblocks[bid].enable = False
    gcode.addUndo(undoinfo)
    # return new blocks inside the blocks list
    del selectedblocks[:]
    selectedblocks.extend(newblocks)
    return msg


class PocketIsland:
    def __init__(
        self,
        pathlist,
        RecursiveDepth,
        ProfileDir,
        CutDir,
        AdditionalCut,
        Overcuts,
        CustomRecursiveDepth,
        ignoreIslands,
        allowG1,
        diameter,
        stepover,
        depth,
        app,
        islandslist=[],
    ):
        self.outpaths = pathlist
        self.islands = islandslist
        self.diameter = diameter
        self.stepover = stepover
        self.RecursiveDepth = RecursiveDepth
        self.ProfileDir = ProfileDir
        self.CutDir = CutDir
        self.AdditionalCut = float(AdditionalCut)
        self.Overcuts = bool(Overcuts)
        self.CustomRecursiveDepth = CustomRecursiveDepth
        self.childrenIslands = []
        self.childrenOutpath = []
        self.fullpath = []
        self.depth = depth
        self.islandG1SegList = Path("islandG1SegList")
        self.outPathG1SegList = Path("outPathG1SegList")
        self.ignoreIslands = ignoreIslands
        self.allowG1 = allowG1
        self.app = app
        maxdepthchoice = {
            "Single profile": 0,
            "Custom offset count": int(self.CustomRecursiveDepth - 1),
            "Full pocket": 100,
        }
        profileDirChoice = {"inside": 1.0, "outside": -1.0}
        cutDirChoice = {False: 1.0, True: -1.0}
        self.selectCutDir = cutDirChoice.get(self.CutDir, 1.0)
        self.profiledir = profileDirChoice.get(self.ProfileDir, 1.0)
        if self.RecursiveDepth == "Full pocket":
            # to avoid making full pockets, with full recursive depth,
            # outside the path
            self.profiledir = 1.0
        maxdepth = maxdepthchoice.get(self.RecursiveDepth, 0)
        maxdepth = min(maxdepth, 999)
        sys.setrecursionlimit(max(sys.getrecursionlimit(), maxdepth + 1))
        if depth > maxdepth:
            return None
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> eliminateOutsideIslands",
            True,
        )
        self.eliminateOutsideIslands()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> inoutprofile",
            True,
        )
        self.inoutprofile()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> removeOutofProfileLinkingSegs",
            True,
        )
        self.removeOutofProfileLinkingSegs()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> intersect",
            True,
        )
        self.intersect()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> removeOutOfProfile",
            True,
        )
        self.removeOutOfProfile()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> removeInsideIslands",
            True,
        )
        self.removeInsideIslands()
        self.app.setStatus(
            _("Generate pocket path")
            + " - depth:"
            + str(self.depth + 1)
            + " -> getNewPathAndIslands",
            True,
        )
        self.getNewPathAndIslands()
        self.getPaths()
        if len(self.CleanPath) > 0:
            self.recurse()

    def eliminateOutsideIslands(self):
        self.insideIslandList = []
        for island in self.islands:
            for path in self.outpaths:
                if island.isPathInside(path) >= 0:
                    self.insideIslandList.append(island)

    def inoutprofile(self):
        if self.depth == 0:
            self.offset = -self.diameter / 2.0 + self.AdditionalCut
            self.offsetLastPass = self.offset
        else:
            self.offset = -self.diameter * self.stepover
            self.offsetLastPass = -min(
                self.diameter * self.stepover / 2.0, self.diameter * 0.49
            )
        self.OutOffsetPathList = []
        for path in self.outpaths:
            p1 = p2 = None
            if len(path) > 0:
                p1 = path[0].A
            if self.depth == 0:
                path.directionSet(self.selectCutDir * float(self.profiledir))
            direct = path.direction()
            opathCopy = path.offset(self.profiledir
                                    * self.offset
                                    * float(direct))
            opathCopy.removeExcluded(path, abs(self.offset))
            if (
                len(opathCopy) > 0
            ):  # there remains some path after full offset : not the last pass
                opath = path.offset(self.profiledir
                                    * self.offset
                                    * float(direct))
                offset = self.offset
            # nothing remaining after the last pass => apply offsetLastPass
            else:
                opath = path.offset(
                    self.profiledir * self.offsetLastPass * float(direct)
                )
                offset = self.offsetLastPass
            opath.intersectSelf()
            if len(opath) > 0:
                opath.removeExcluded(path, abs(offset))
            opath.removeZeroLength(abs(self.diameter) / 100.0)
            opath.convert2Lines(abs(self.diameter) / 10.0)
            if self.depth == 0 and self.Overcuts:
                opath.overcut(self.profiledir * self.offset * float(direct))
            if len(opath) > 0:
                p2 = opath[0].A
                self.OutOffsetPathList.append(opath)
                if self.depth > 0 and p1 is not None:
                    self.outPathG1SegList.append(Segment(Segment.LINE, p1, p2))
        self.islandOffPaths = []
        for island in self.insideIslandList:
            p3 = p4 = None
            if len(island) > 0:
                p3 = island[0].A
            if self.depth == 0:
                island.directionSet(-self.selectCutDir
                                    * float(self.profiledir))
            direct = island.direction()
            offIsl = island.offset(-self.profiledir
                                   * self.offset
                                   * float(direct))
            offIsl.intersectSelf()
            if len(offIsl) > 0:
                offIsl.removeExcluded(island, abs(self.offset))
            offIsl.removeZeroLength(abs(self.diameter) / 100.0)
            offIsl.convert2Lines(abs(self.diameter) / 10.0)
            if len(offIsl) > 0:
                p4 = offIsl[0].A
            if self.depth > 0 and p3 is not None and p4 is not None:
                self.islandG1SegList.append(Segment(Segment.LINE, p3, p4))
            if self.depth == 0 and self.Overcuts:
                offIsl.overcut(-self.profiledir * self.offset * float(direct))
            self.islandOffPaths.append(offIsl)

    def removeOutofProfileLinkingSegs(self):
        self.tmpoutG1 = deepcopy(self.outPathG1SegList)
        self.tmpinG1 = deepcopy(self.islandG1SegList)
        for i, seg in enumerate(self.outPathG1SegList):
            for path in self.islandOffPaths:
                # outseg inside offsetislands =>pop
                inside = path.isSegInside(seg) == 1
                if inside and seg in self.tmpoutG1:
                    self.tmpoutG1.remove(seg)
        for i, seg in enumerate(self.islandG1SegList):
            for path in self.OutOffsetPathList:
                outside = (
                    path.isSegInside(seg) < 1
                )  # inseg outside offsetOutpaths => pop
                if outside and seg in self.tmpinG1:
                    self.tmpinG1.remove(seg)
        self.outPathG1SegList = self.tmpoutG1
        self.islandG1SegList = self.tmpinG1

    def intersect(self):
        self.IntersectedIslands = []
        for island in self.islandOffPaths:
            for path in self.OutOffsetPathList:
                path.intersectPath(island)
                island.intersectPath(path)
            for island2 in self.islandOffPaths:
                island.intersectPath(island2)
            self.IntersectedIslands.append(island)

    def removeOutOfProfile(self):
        self.NewPaths = []
        newoutpath = Path("path")
        for path in self.OutOffsetPathList:
            for seg in path:
                newoutpath.append(seg)
        for OutoffsetPath in self.OutOffsetPathList:
            for path in self.IntersectedIslands:
                for seg in path:
                    inside = not OutoffsetPath.isSegInside(seg) == -1
                    if inside:
                        newoutpath.append(seg)
        purgednewoutpath = newoutpath.split2contours()  # list of paths
        self.NewPaths.extend(purgednewoutpath)

    def removeInsideIslands(self):
        self.CleanPath = []
        cleanpath = Path("Path")
        for path in self.NewPaths:
            for seg in path:
                inside = False
                for island in self.IntersectedIslands:
                    issegin = island.isSegInside(seg) == 1
                    if issegin:
                        if seg not in island:
                            inside = True
                            break
                if not inside:
                    cleanpath.append(seg)
        cleanpath = cleanpath.split2contours()
        self.CleanPath.extend(cleanpath)

    def getNewPathAndIslands(self):
        if len(self.CleanPath) == 1:
            self.childrenOutpath = self.CleanPath
        else:
            for elt in self.CleanPath:  # List of paths
                for elt2 in self.CleanPath:
                    ins = elt2.isPathInside(elt) == 1
                    ident = elt2.isidentical(elt)
                    addedelt2 = elt2 in self.childrenIslands
                    if ins and not ident and not addedelt2:
                        self.childrenIslands.append(elt2)
            for elt in self.CleanPath:  # List of paths
                for elt2 in self.CleanPath:
                    if (
                        elt2 not in self.childrenIslands
                        and elt2 not in self.childrenOutpath
                    ):
                        self.childrenOutpath.append(elt2)

    def getPaths(self):
        if len(self.CleanPath) > 0:
            if len(self.islandG1SegList) > 0:
                self.outPathG1SegList.extend(self.islandG1SegList)
            if self.allowG1 and len(self.outPathG1SegList) > 0:
                for seg in self.outPathG1SegList:
                    path = Path("SegPath")
                    path.append(seg)
                    self.CleanPath.append(path)
            self.fullpath.extend(self.CleanPath)
        return self.CleanPath

    def recurse(self):
        pcket = PocketIsland(
            self.childrenOutpath,
            self.RecursiveDepth,
            self.ProfileDir,
            self.CutDir,
            self.AdditionalCut,
            self.Overcuts,
            self.CustomRecursiveDepth,
            self.ignoreIslands,
            self.allowG1,
            self.diameter,
            self.stepover,
            self.depth + 1,
            self.app,
            self.childrenIslands,
        )
        self.fullpath.extend(pcket.getfullpath())

    def getfullpath(self):
        return self.fullpath


class Tool(Plugin):
    __doc__ = _("Generate a pocket or profile for selected shape (regarding islands)")

    def __init__(self, master):
        Plugin.__init__(self, master, "Offset")
        self.icon = "offset"
        self.group = "CAM_Core+"
        self.variables = [
            ("name", "db", "", _("Name")),
            ("endmill", "db", "", _("End Mill")),
            (
                "RecursiveDepth",
                "Single profile,Full pocket,Custom offset count",
                "Single profile",
                _("Operation"),
                _(
                    "indicates the number of profile passes (single,custom number,full pocket)"
                ),
            ),
            (
                "CustomRecursiveDepth",
                "int",
                2,
                _("Custom offset count"),
                _(
                    "Number of contours (Custom offset count) : indicates the number of contours if custom selected. MAX:"
                    + str(sys.getrecursionlimit() - 1)
                ),
            ),
            (
                "ProfileDir",
                "inside,outside",
                "inside",
                _("Offset side"),
                _("indicates the direction (inside / outside) for making profiles"),
            ),
            (
                "CutDir",
                "bool",
                False,
                _("Climb milling"),
                _(
                    "This can be used to switch between Conventional and Climb milling. If unsure use Convetional (default)."
                ),
            ),
            (
                "AdditionalCut",
                "mm",
                0.0,
                _("Additional offset (mm)"),
                _("acts like a tool corrector inside the profile"),
            ),
            (
                "Overcuts",
                "bool",
                False,
                _("Overcut corners"),
                _(
                    "Tabs are always ignored. You can select if all islands are active, none, or only selected"
                ),
            ),
            (
                "ignoreIslands",
                "Regard all islands except tabs,Ignore all islands,Regard only selected islands",
                "Regard all islands except tabs",
                _("Island behaviour"),
                _(
                    "Tabs are always ignored. You can select if all islands are active, none, or only selected"
                ),
            ),
            (
                "allowG1",
                "bool",
                True,
                _("Link segments"),
                _(
                    "Currently there is some weird behaviour sometimes when trying to link segments of pocket internally, so it can be disabled using this option. This workaround should be fixed and removed in future."
                ),
            ),
        ]
        self.help = """This plugin offsets shapes to create toolpaths for profiling and pocketing operation.
Shape needs to be offset by the radius of endmill to get cut correctly.

Currently we have two modes.

Without overcut:
#overcut-without

And with overcut:
#overcut-with

Blue is the original shape from CAD
Turquoise is the generated toolpath
Grey is simulation of how part will look after machining
        """
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])
        RecursiveDepth = self["RecursiveDepth"]
        ProfileDir = self["ProfileDir"]
        CutDir = self["CutDir"]
        AdditionalCut = self["AdditionalCut"]
        Overcuts = self["Overcuts"]
        CustomRecursiveDepth = self["CustomRecursiveDepth"]
        ignoreIslands = self["ignoreIslands"]
        allowG1 = self["allowG1"]
        name = self["name"]
        if name == "default" or name == "":
            name = None
        tool = app.tools["EndMill"]
        diameter = app.tools.fromMm(tool["diameter"])
        try:
            stepover = tool["stepover"] / 100.0
        except TypeError:
            stepover = 0.0
        app.busy()
        selectedblocks = app.editor.getSelectedBlocks()
        msg = pocket(
            selectedblocks,
            RecursiveDepth,
            ProfileDir,
            CutDir,
            AdditionalCut,
            Overcuts,
            CustomRecursiveDepth,
            ignoreIslands,
            bool(allowG1),
            diameter,
            stepover,
            name,
            app.gcode,
            app,
        )
        if msg:
            messagebox.showwarning(
                _("Open paths"), _("WARNING: {}").format(msg), parent=app
            )
        app.editor.fill()
        app.editor.selectBlocks(selectedblocks)
        app.draw()
        app.notBusy()
        app.setStatus(_("Generate pocket path") + "..done")


##############################################
