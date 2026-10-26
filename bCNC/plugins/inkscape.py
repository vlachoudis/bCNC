# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014
#
# Inkscape g-code tools on slice/slice it raises the tool to the
# safe height then plunges again.
# Comment out all these patterns
#
# FIXME needs re-working...
#
# Postprocess Inkscape Gcodetools output: comment out needless
# raise-then-plunge pairs (Z up / Z down with no XY move).
#
# 2026-10: moved to separate plugin as this is support for legacy inkscape plugin. is anyone even using this?


import rexx
from CNC import CNC
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Inkscape")
__version__ = "0.1"


def apply_inkscape(gcode, items):
    # Operates on the whole document (legacy behaviour).
    # FIXME needs re-working for real selection scope.
    gcode.initPath()
    newlines = []
    last = -1  # line index of last raise with dx=dy=0.0

    for line in gcode.lines():
        # step id
        # 0 - normal cutting z<0
        # 1 - z>0 raised  with dx=dy=0.0
        # 2 - z<0 plunged with dx=dy=0.0
        cmd = CNC.parseLine(line)
        if cmd is None:
            newlines.append(line)
            continue
        gcode.cnc.motionStart(cmd)
        if gcode.cnc.dx == 0.0 and gcode.cnc.dy == 0.0:
            if gcode.cnc.z > 0.0 and gcode.cnc.dz > 0.0:
                last = len(newlines)
            elif gcode.cnc.z < 0.0 and gcode.cnc.dz < 0.0 and last >= 0:
                for i in range(last, len(newlines)):
                    s = newlines[i]
                    if s and s[0] != "(":
                        newlines[i] = f"({s})"
                last = -1
        else:
            last = -1
        newlines.append(line)
        gcode.cnc.motionEnd()

    gcode.addUndo(gcode.setLinesUndo(newlines))


def run_inkscape(app, select_all=False):
    if select_all or not app.editor.getSelectedBlocks():
        app.editor.selectAll()
    return run_on_selection(app, apply_inkscape)


class Tool(Plugin):
    __doc__ = _("Postprocess Inkscape g-code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Inkscape")
        self.icon = "inkscape"
        self.group = "CAM"
        self.oneshot = True
        self.commands = {"INKSCAPE": (self.cmdline, 3)}

    def cmdline(self, app, args, oline=None):
        select_all = len(args) > 1 and rexx.abbrev("ALL", args[1].upper())
        run_inkscape(app, select_all=select_all)

    def execute(self, app):
        run_inkscape(app)
        app.setStatus(_("Postprocessed: Inkscape"))
