# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014
#
# Postprocess Inkscape Gcodetools / SVG-style g-code: comment out needless
# raise-then-plunge pairs (Z up / Z down with no real XY move).
#
# Works for any cutting/plotting plane (not only Z<0). Net Z of a pending
# no-XY sequence must return to the start plane (within tolerance).
#
# 2026-10: more flexible Z-plane handling by @tschundler (PR #1506 / issue #1505)
# 2026-10: moved to separate plugin as this is support for legacy inkscape plugin


import rexx
from CNC import CNC
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Inkscape")
__version__ = "0.2"

# Fuzzy zero for floating-point deltas (mm). Same idea as PR #1506.
_ZERO = 0.001
# Sentinel so header Z setup is not mistaken for a removable raise/plunge.
_HEADER_DZ = 1e6


def _is_zero(value):
    return -_ZERO < value < _ZERO


def _comment_line(line):
    if line[:1] in ("(", "%", "#", ";"):
        return line
    return f"({line})"


def apply_inkscape(gcode, items):
    # Operates on the whole document (legacy behaviour).
    # FIXME needs re-working for real selection scope.
    gcode.initPath()
    newlines = []
    pending = []  # Accumulator for lines we may want to nullify.
    dz = _HEADER_DZ

    for line in gcode.lines():
        cmd = CNC.parseLine(line)
        if cmd is None:
            if pending:
                pending.append(line)
            else:
                newlines.append(line)
            continue

        gcode.cnc.motionStart(cmd)
        # No XY motion, but maybe Z motion.
        if _is_zero(gcode.cnc.dx) and _is_zero(gcode.cnc.dy):
            dz += gcode.cnc.dz
            # Upward (or zero) Z, or continuation of a pending block → candidate.
            if pending or dz >= 0:
                pending.append(line)
                gcode.cnc.motionEnd()
                continue
        gcode.cnc.motionEnd()

        # XY motion has resumed / continues — flush pending.
        if pending:
            if _is_zero(dz):
                pending = [_comment_line(s) for s in pending]
            newlines.extend(pending)
            pending = []

        newlines.append(line)
        dz = 0

    # Footer usually has no XY motion; keep it.
    if pending:
        newlines.extend(pending)

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
