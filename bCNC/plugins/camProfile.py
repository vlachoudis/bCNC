# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from tkinter import messagebox

import bcam
import rexx
from GCode import Block
from ToolsPage import Plugin

from pocket import apply_pocket

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


# -----------------------------------------------------------------------------
# Apply profile CAM to selected block indices on a GCode document.
# Mutates blocks list in place to the new block indices (same as old API).
# -----------------------------------------------------------------------------
def apply_profile(
    gcode,
    blocks,
    offset,
    overcut=False,
    name=None,
    pocket=False,
    diameter=None,
    stepover=None,
):
    undoinfo = []
    msg = ""
    newblocks = []

    remove = [
        "cut",
        "reverse",
        "climb",
        "conventional",
        "cw",
        "ccw",
        "in",
        "out",
    ]

    for bid in reversed(blocks):
        if gcode.blocks[bid].name() in ("Header", "Footer"):
            continue
        newpath = []
        for path in gcode.toPath(bid):
            if name is not None:
                newname = Block.operationName(path.name, name)
            elif offset > 0:
                newname = Block.operationName(
                    path.name, "out,conventional,ccw", remove
                )
                path.directionSet(-1)  # CCW — conventional outside
            else:
                newname = Block.operationName(
                    path.name, "in,conventional,cw", remove
                )
                path.directionSet(1)  # CW — conventional inside

            if not path.isClosed():
                m = f"Path: '{path.name}' is OPEN"
                if m not in msg:
                    if msg:
                        msg += "\n"
                    msg += m

            newpath.extend(bcam.profile_paths(path, offset, overcut, newname))

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

    if pocket:
        if diameter is None or stepover is None:
            raise ValueError("pocket=True requires diameter and stepover")
        msg = msg + apply_pocket(
            gcode, sorted(newblocks), diameter, stepover, name, True, True
        )
        withpocketblocks = sorted(newblocks).copy()
        for i in range(0, len(withpocketblocks)):
            withpocketblocks[i] += i
            withpocketblocks.append(withpocketblocks[i] + 1)
        newblocks = sorted(withpocketblocks, reverse=True)

    blocks.extend(newblocks)
    return msg


class Tool(Plugin):
    __doc__ = _("Perform a profile operation on selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Profile")
        self.icon = "profile"
        self.group = "CAM-core-big"
        self.order = 30
        self.variables = [
            ("name", "db", "", _("Name")),
            (
                "endmill",
                "db",
                "",
                _("End Mill"),
                _("Size of this endmill will be used as offset distance"),
            ),
            (
                "direction",
                "inside,outside",
                "outside",
                _("Direction"),
                _("Should we machine on inside or outside of the shape?"),
            ),
            ("offset", "float", 0.0, _("Additional offset distance")),
            (
                "overcut",
                "bool",
                1,
                _("Overcut"),
                _("Sets if we want to overcut or not."),
            ),
            (
                "pocket",
                "bool",
                0,
                _("Pocket"),
                _(
                    "Generate pocket after profiling? Useful for making "
                    + "pockets with overcuts."
                ),
            ),
        ]
        self.buttons.append("exe")
        self.commands = {"PROFILE": (self.cmdline, 3)}
        self.help = "\n".join([
            "This plugin offsets shapes to create toolpaths for profiling "
            + "operation.",
            "Shape needs to be offset by the radius of endmill to get cut "
            + "correctly.",
            "",
            "Currently we have two modes.",
            "",
            "Without overcut:",
            "#overcut-without",
            "",
            "And with overcut:",
            "#overcut-with",
            "",
            "Blue is the original shape from CAD",
            "Turquoise is the generated toolpath",
            "Grey is simulation of how part will look after machining",
        ])

    def cmdline(self, app, args, oline=None):
        self._run(app, args[1] if len(args) > 1 else None)

    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])
        name = self["name"]
        if name == "default" or name == "":
            name = None
        self._run(
            app,
            self["direction"],
            self["offset"],
            self["overcut"],
            name,
            self["pocket"],
        )
        app.setStatus(_("Generate profile path"))

    def _run(
        self,
        app,
        direction=None,
        offset=0.0,
        overcut=False,
        name=None,
        pocket=False,
    ):
        tool = app.tools["EndMill"]
        ofs = app.tools.fromMm(tool["diameter"]) / 2.0
        sign = 1.0

        if direction is None:
            pass
        elif rexx.abbrev("INSIDE", direction.upper()):
            sign = -1.0
        elif rexx.abbrev("OUTSIDE", direction.upper()):
            sign = 1.0
        else:
            try:
                ofs = float(direction) / 2.0
            except Exception:
                pass

        try:
            ofs += float(offset)
        except Exception:
            pass

        diameter = app.tools.fromMm(tool["diameter"])
        try:
            stepover = tool["stepover"] / 100.0
        except TypeError:
            stepover = 0.0

        app.busy()
        blocks = app.editor.getSelectedBlocks()
        msg = apply_profile(
            app.gcode,
            blocks,
            ofs * sign,
            overcut,
            name,
            pocket,
            diameter,
            stepover,
        )
        if msg:
            messagebox.showwarning(
                "Open paths", f"WARNING: {msg}", parent=app
            )
        app.editor.fill()
        app.editor.selectBlocks(blocks)
        app.draw()
        app.notBusy()
        app.setStatus(_("Profile block distance={:g}").format(ofs * sign))
