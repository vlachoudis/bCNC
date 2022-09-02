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


from CNC import CNC  # , Block  # << without this error it does not find CNC.vars
from ToolsPage import Plugin

__author__ = "Mario Basz"
__email__ = "mariob_1960@yahoo.com.ar"

__name__ = _("Trochoidal Path")
__version__ = "1.0"
# Date last version: 29-January-2019


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
        app.trochprofile_bcnc(
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
