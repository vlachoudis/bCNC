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

    def execute(self, app):
        app.insertCommand("ISLAND", True)
