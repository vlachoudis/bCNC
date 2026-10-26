# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014
"""Portable CAM strategies on bpath geometry.

Pure path in / path out. No GCode, Block, undo, tkinter, or CNC.vars.
Document I/O and UI live in plugins; geometry primitives live in bpath.
"""

import sys

from bmath import Vector
from bpath import Path, Segment


# -----------------------------------------------------------------------------
def tab_path(x=0, y=0, dx=0, dy=0, circ=True):
    """Holding-tab outline as a Path (square or circular)."""
    path = Path("tab")
    dx = dx / 2.0
    dy = dy / 2.0

    if not circ:
        A = A0 = Vector(x - dx, y - dy)
        B = Vector(x + dx, y - dy)
        path.append(Segment(Segment.LINE, A, B))
        A = B
        B = Vector(x + dx, y + dy)
        path.append(Segment(Segment.LINE, A, B))
        A = B
        B = Vector(x - dx, y + dy)
        path.append(Segment(Segment.LINE, A, B))
        A = B
        B = A0
        path.append(Segment(Segment.LINE, A, B))
    else:
        A = Vector(x - max(dx, dy), y)
        C = Vector(x, y)
        seg = Segment(Segment.CCW, A, A)
        seg.setCenter(C)
        path.append(seg)
    return path


# -----------------------------------------------------------------------------
def profile_paths(path, offset, overcut=False, name=None):
    """Offset a path for profiling.

    ``offset`` sign selects side (positive = outside, negative = inside).
    Returns a list of Paths (may be empty). Does not set milling direction;
    caller may call ``path.directionSet`` before this for conventional cuts.
    """
    opath = path.offsetClean(offset, overcut, name)
    if not opath:
        return []
    return list(opath)


# -----------------------------------------------------------------------------
def _pocket_recursive(path, diameter, stepover, depth, maxdepth=10000):
    """Nested pocket offsets. ``diameter`` is signed (negative = inward)."""
    # Recursion is slow; keep parity with historical GCode._pocket behavior.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), maxdepth + 100))

    if depth > maxdepth:
        return None
    if depth == 0:
        offset = diameter / 2.0
    else:
        offset = diameter * stepover

    opath = path.offset(offset)
    if not opath:
        return None

    opath.intersectSelf()
    opath.removeExcluded(path, offset)
    opath.removeZeroLength(abs(offset) / 100.0)
    opath = opath.split2contours()

    newpath = []
    if opath:
        for pout in opath:
            pin = _pocket_recursive(pout, diameter, stepover, depth + 1, maxdepth)
            if not pin:
                newpath.append(pout)
            elif len(pin) == 1:
                # FIXME: verify straight join does not cross material
                pin[0].join(pout)
                newpath.append(pin[0])
            else:
                newpath.extend(pin)
                newpath.append(pout)
    return newpath


# -----------------------------------------------------------------------------
def pocket_paths(path, diameter, stepover):
    """Prepare a closed path and return nested pocket toolpaths.

    Mutates ``path`` (close, cleanup, CW direction). ``diameter`` is the
    absolute tool diameter; inward offset sign is derived from path direction.
    Returns a list of Paths (may be empty).
    """
    if not path.isClosed():
        path.close()

    path.removeZeroLength(abs(diameter) / 100.0)
    path.convert2Lines(abs(diameter) / 10.0)
    path.directionSet(1)  # CW — conventional when milling inside

    D = path.direction()
    if D == 0:
        D = 1

    result = _pocket_recursive(path, -D * diameter, stepover, 0)
    return result if result else []
