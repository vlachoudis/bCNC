# $Id$
#
# Author: Mario Basz
# mariob_1960@yahoo.com.ar
# Date: 9 November 2017
# Date: 03 may 2018
# A special thanks to Filippo Rivato and Vasilis.
# This plugin is based on a variation
# of yours plugin Driller and My_Plugin example.
# To correct: That's why the first point starts,
#
# Experimental fat plugin: owns trochoidal profile CAM (formerly
# Application.trochprofile_bcnc / GCode.trochprofile_cnc).


from tkinter import messagebox

import rexx
from CNC import CNC
from GCode import Block
from ToolsPage import Plugin
from cut import apply_cut

__author__ = "Mario Basz"
__email__ = "mariob_1960@yahoo.com.ar"

__name__ = _("Trochoidal Path")
__version__ = "1.0"
# Date last version: 29-January-2019


# -----------------------------------------------------------------------------
# Document + path CAM for trochoidal profile (experimental).
# Mutates blocks in place to new block indices; depth via apply_cut.
# -----------------------------------------------------------------------------
def apply_trochprofile(
    gcode,
    blocks,
    offset,
    overcut=False,
    adaptative=True,
    adaptedRadius=0.0,
    cutDiam=0.0,
    tooldiameter=0.0,
    targetDepth=0.0,
    depthIncrement=0.0,
    tabsnumber=0.0,
    tabsWidth=0.0,
    tabsHeight=0.0,
):
    undoinfo = []
    msg = ""
    newblocks = []
    for bid in reversed(blocks):
        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue
        newpath = []
        for path in gcode.toPath(bid):
            explain = "Tr "
            if offset > 0:
                explain += "out "
            elif offset < 0:
                explain += "in "
            explain += str(cutDiam)
            if cutDiam != abs(2 * offset):
                explain += " offs " + str(abs(offset) - cutDiam / 2.0)
            if offset < 0:
                if adaptative:
                    explain += " Adapt bit " + str(tooldiameter)
                if overcut:
                    explain += " overc"
            newname = Block.operationName(path.name, explain)

            if not path.isClosed():
                m = f"Path: '{path.name}' is OPEN"
                if m not in msg:
                    if msg:
                        msg += "\n"
                    msg += m

            path.removeZeroLength(abs(offset) / 100.0)
            path.convert2Lines(abs(offset) / 10.0)
            D = path.direction()
            if D == 0:
                D = 1
            opath = path.offset(D * offset, newname)
            if opath:
                opath.intersectSelf()
                opath.removeExcluded(path, D * offset)
                opath.removeZeroLength(abs(offset) / 100.0)
            opath = opath.split2contours()
            if opath:
                if overcut is True or adaptative is True:
                    for p in opath:
                        p.trochovercut(
                            D * offset, overcut, adaptative, adaptedRadius
                        )
                newpath.extend(opath)
        if newpath:
            before = len(newblocks)
            undoinfo.extend(
                gcode.importPath(bid + 1, newpath, newblocks, True, False)
            )
            new = len(newblocks) - before
            for i in range(before):
                newblocks[i] += new
            gcode.blocks[bid].enable = False
    gcode.addUndo(undoinfo)

    del blocks[:]
    blocks.extend(newblocks)

    apply_cut(
        gcode,
        list(reversed(blocks)),
        depth=targetDepth,
        stepz=depthIncrement,
        surface=0,
        feed=900,
        feedz=120,
        cutFromTop=False,
        helix=False,
        helixBottom=False,
        ramp=0,
        islandsLeave=True,
        islandsCut=False,
        islandsSelectedOnly=False,
        exitpoint=None,
        springPass=False,
        islandsCompensate=False,
    )
    return msg


# -----------------------------------------------------------------------------
# App-facing entry (direction resolve + UI busy/warnings). Used by this plugin
# and by trochoidal_3D.
# -----------------------------------------------------------------------------
def run_trochprofile(
    app,
    cutDiam=0.0,
    direction=None,
    offset=0.0,
    overcut=False,
    adaptative=False,
    adaptedRadius=0.0,
    tooldiameter=0.0,
    targetDepth=0.0,
    depthIncrement=0.0,
    tabsnumber=0.0,
    tabsWidth=0.0,
    tabsHeight=0.0,
):
    adaptedRadius = float(adaptedRadius)
    ofs = float(cutDiam) / 2.0
    sign = 1.0

    if direction is None:
        pass
    elif rexx.abbrev("INSIDE", direction.upper()):
        sign = -1.0
    elif rexx.abbrev("OUTSIDE", direction.upper()):
        sign = 1.0
    elif rexx.abbrev("ON", direction.upper()):
        ofs = 0
    else:
        try:
            ofs = float(direction) / 2.0
        except Exception:
            pass

    try:
        ofs += float(offset)
    except Exception:
        pass

    app.busy()
    blocks = app.editor.getSelectedBlocks()
    msg = apply_trochprofile(
        app.gcode,
        blocks,
        ofs * sign,
        overcut,
        adaptative,
        adaptedRadius,
        cutDiam,
        tooldiameter,
        targetDepth,
        depthIncrement,
        tabsnumber,
        tabsWidth,
        tabsHeight,
    )
    if msg:
        messagebox.showwarning(
            "Open paths", f"WARNING: {msg}", parent=app
        )
    if adaptative:
        messagebox.showwarning(
            "Adaptative",
            "WARNING: Adaptive route generated, but Trocoidal still does "
            + "not implement it. Use will give wrong results in the "
            + "corners!",
            parent=app,
        )

    app.editor.fill()
    app.editor.selectBlocks(blocks)
    app.draw()
    app.notBusy()
    app.setStatus(_("Profile block distance={:g}").format(ofs * sign))
    return msg


# =============================================================================
# Create Trochoidadl route along selected blocks
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Create a trochoid route along selected blocks")

    def __init__(self, master):
        Plugin.__init__(self, master, "Trochoid_Path")  # NAME OF THE PLUGIN
        self.icon = "trochoidal"
        self.group = "Development"

        self.variables = [
            ("name", "db", "", _("Name")),
            ("trochcutdiam", "mm", 6.0, _("Cut Diameter"),
             "Real cutting diameter"),
            ("direction", "inside,outside,on", "inside", _("Direction")),
            ("offset", "float", 0.0, _("Additional offset distance")),
            ("endmill", "db", "",
             _("End Mill"), "If Empty chooses, End Mill loaded"),
            (
                "adaptative",
                "bool",
                1,
                _("Adaptative"),
                "Generate path for adaptative trochoids in the corners "
                + "(Not yet implemented in trochoidal plugin)",
            ),
            ("overcut", "bool", 0, _("Overcut")),
            ("targetDepth", "mm", -1, _("Target Depth")),
            ("depthIncrement", "mm", 1, _("Depth Increment")),
            (
                "tabsnumber",
                "mm",
                1,
                _("Number of Tabs 0 = Not Tabs"),
                "Not available yet",
            ),
            ("tabsWidth", "mm", 1, _("Tabs Diameter"), "Not available yet"),
            ("tabsHeight", "mm", 1, _("Tabs Height"), "Not available yet"),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def update(self):
        self.master.cnc()["trochcutdiam"] = self.fromMm("trochcutdiam")

    # ----------------------------------------------------------------------
    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])

        targetDepth = self["targetDepth"]
        depthIncrement = self["depthIncrement"]
        if depthIncrement == "":
            depthIncrement = 10
        tabsnumber = self["tabsnumber"]
        tabsWidth = self["tabsWidth"]
        tabsHeight = self["tabsHeight"]

        trochcutdiam = self.fromMm("trochcutdiam")
        mintrochdiameter = CNC.vars["diameter"]
        cornerradius = (trochcutdiam - mintrochdiameter) / 2.0
        direction = self["direction"]
        name = self["name"]
        if name == "default" or name == "":
            name = None
        run_trochprofile(
            app,
            trochcutdiam,
            direction,
            self["offset"],
            self["overcut"],
            self["adaptative"],
            cornerradius,
            CNC.vars["diameter"],
            targetDepth,
            depthIncrement,
            tabsnumber,
            tabsWidth,
            tabsHeight,
        )  # << diameter only to information
        app.setStatus(_("Generated path for trochoidal cutting"))


# =============================================================================
