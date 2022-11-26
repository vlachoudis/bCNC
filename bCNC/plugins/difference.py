# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from copy import deepcopy
from math import (
    cos,
    sin,
)

from bpath import EPS, Path, eq
from CNC import Block
from ToolsPage import Plugin

__author__ = "@harvie Tomas Mudrunka"
# __email__  = ""

__name__ = _("Difference")
__version__ = "0.0.1"


class Tool(Plugin):
    __doc__ = _(
        """Difference of two shapes"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "Difference")
        # Helical_Descent: is the name of the plugin show in the tool ribbon button
        self.icon = "diff"  # <<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
        self.group = "Development"  # <<< This is the name of group that plugin belongs
        self.oneshot = True
        # Here we are creating the widgets presented to the user inside the plugin
        # Name, Type , Default value, Description
        self.variables = [  # <<< Define a list of components for the GUI
            (
                "name",
                "db",
                "",
                _("Name"),
            ),  # used to store plugin settings in the internal database
        ]
        self.buttons.append(
            "exe"
        )  # <<< This is the button added at bottom to call the execute method below

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        blocks = []

        paths_base = []
        paths_isl = []

        for bid in app.editor.getSelectedBlocks():
            if app.gcode[bid].operationTest("island"):
                paths_isl.extend(app.gcode.toPath(bid))
            else:
                paths_base.extend(app.gcode.toPath(bid))

        for island in paths_isl:
            paths_newbase = []
            while len(paths_base) > 0:
                base = paths_base.pop()

                base.intersectPath(island)
                island.intersectPath(base)

                newbase = Path("diff")

                # Add segments from outside of islands:
                for i, seg in enumerate(base):
                    if not island.isInside(seg.midPoint()):
                        newbase.append(seg)

                # Add segments from islands to base
                for i, seg in enumerate(island):
                    if base.isInside(
                        seg.midPoint()
                    ):  # and base.isInside(seg.A) and base.isInside(seg.B):
                        newbase.append(seg)

                # Eulerize
                paths_newbase.extend(newbase.eulerize())
            paths_base = paths_newbase

        for base in paths_base:
            print(base)
            block = Block("diff")
            block.extend(app.gcode.fromPath(base))
            blocks.append(block)

        app.gcode.insBlocks(
            -1, blocks, "Diff"
        )  # <<< insert blocks over active block in the editor
        app.refresh()  # <<< refresh editor
        app.setStatus(_("Generated: Diff"))  # <<< feed back result

    ##############################################

    def pol2car(self, r, phi, a=[0, 0]):
        return [round(a[0] + r * cos(phi), 4), round(a[1] + r * sin(phi), 4)]

    def findSubpath(self, path, A, B, inside):
        path = deepcopy(path)
        newpath = self._findSubpath(path, A, B, inside)
        if newpath is None:
            path.invert()
            newpath = self._findSubpath(path, A, B, inside)
        return newpath

    def _findSubpath(self, path, A, B, inside):
        print("finding", A, B)

        sub = None
        for i in range(0, len(path) * 2):  # iterate twice with wrap around
            j = i % len(path)
            seg = path[j]
            if inside.isInside(seg.midPoint()):

                if eq(seg.A, A):
                    sub = Path("subp")
                print("seg", sub is None, seg)
                if sub is not None:
                    sub.append(seg)
                if eq(seg.B, B):
                    break

        print("found", sub)
        return sub

    def pathBoolIntersection(self, basepath, islandpath):
        basepath.intersectPath(islandpath)
        islandpath.intersectPath(basepath)

        # find first intersecting segment
        first = None
        for i, segment in enumerate(basepath):
            if islandpath.isInside(segment.midPoint()):
                first = i
        if first is None:
            print("not intersecting paths")
            return None

        # generate intersected path
        newisland = Path("new")
        A = None
        for i in range(first, 2 * len(basepath) + first):
            j = i % len(basepath)
            segment = basepath[j]
            if segment.length() < EPS:
                continue  # ignore zero length segments
            if not islandpath.isInside(segment.midPoint()):
                if A is None:
                    A = segment.A
                newisland.append(segment)
            else:
                if A is not None:
                    newisland.extend(
                        self.findSubpath(islandpath, A, segment.A, basepath)
                    )
                    print("new", newisland)
                    A = None
        print("new2", newisland)
        return newisland
