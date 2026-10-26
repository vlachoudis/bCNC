# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


class Tool(Plugin):
    __doc__ = _("Toggle island")

    def __init__(self, master):
        Plugin.__init__(self, master, "Island")
        self.icon = "island"
        self.group = "CAM-core"
        self.order = 40
        self.oneshot = True
        self.commands = {"ISLAND": (self.cmdline, 3)}

    def cmdline(self, app, args, oline=None):
        if len(args) > 1:
            isl = args[1].upper() == "1"
        else:
            isl = None
        app.executeOnSelection("ISLAND", True, isl)

    def execute(self, app):
        app.insertCommand("ISLAND", True)
