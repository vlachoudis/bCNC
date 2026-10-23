# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


class Tool(Plugin):
    __doc__ = _("Perform a pocket operation on selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Pocket")
        self.icon = "pocket"
        self.group = "CAM-core"
        self.order = 10
        self.variables = [
            ("name", "db", "", _("Name")),
            ("endmill", "db", "", _("End Mill")),
        ]
        self.buttons.append("exe")
        self.help = """Remove all material inside selected shape
"""

    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])
        name = self["name"]
        if name == "default" or name == "":
            name = None
        app.pocket(name)
        app.setStatus(_("Generate pocket path"))
