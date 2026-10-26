# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from tkinter import messagebox

from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


class Tool(Plugin):
    __doc__ = _("Insert holding tabs")

    def __init__(self, master):
        Plugin.__init__(self, master, "Tabs")
        self.icon = "tab"
        self.group = "CAM-core"
        self.order = 30
        self.variables = [
            ("name", "db", "", _("Name")),
            ("ntabs", "int", 5, _("Number of tabs")),
            ("dtabs", "mm", 0.0, _("Min. Distance of tabs")),
            ("dx", "mm", 5.0, "Width"),
            ("z", "mm", -3.0, _("Height")),
        ]
        self.buttons.append("exe")
        self.commands = {"TABS": (self.cmdline, 3)}
        self.help = "\n".join([
            "Create tabs, which will be left uncut to hold the part in place "
            + "after cutting.",
            "",
            "Tabs after creation:",
            "#tabs-created",
            "",
            "Tabs after cutting the path they're attached to:",
            "#tabs-cut",
            "",
            "Tab shows the size of material, which will be left in place "
            + "after cutting. It's compensated for endmill diameter during "
            + "cut operation.",
            "",
            "Note that tabs used to be square, but if there was a diagonal "
            + "segment crossing such tab, it resulted in larger tab without "
            + "any reason. If we use circular tabs, the tab size is always "
            + "the same, no matter the angle of segment.",
            "",
            "You can move selected tabs using \"Move\" feature in \"Editor\". "
            + "If you want to modify individual tabs, you have to first use "
            + "\"Split\" feature to break the block into individual tabs. "
            + "After moving them, you can \"Join\" them back together.",
        ])

    # TAB*S [ntabs] [dtabs] [dx] [dy] [z] [circular]
    def cmdline(self, app, args, oline=None):
        def i(n, d):
            try:
                return int(args[n])
            except Exception:
                return d

        def f(n, d):
            try:
                return float(args[n])
            except Exception:
                return d

        dx = f(3, self.fromMm("dx"))
        app.executeOnSelection(
            "TABS",
            True,
            i(1, int(self["ntabs"])),
            f(2, self.fromMm("dtabs")),
            dx,
            f(4, dx),  # dy defaults to dx (same as GUI)
            f(5, self.fromMm("z")),
            bool(args[6]) if len(args) > 6 else True,
        )

    def execute(self, app):
        try:
            ntabs = int(self["ntabs"])
        except Exception:
            ntabs = 0

        dtabs = self.fromMm("dtabs", 0.0)
        dx = self.fromMm("dx", self.master.fromMm(5.0))
        dy = dx
        z = self.fromMm("z", -self.master.fromMm(3.0))

        if ntabs < 0:
            ntabs = 0
        if dtabs < 0.0:
            dtabs = 0

        if ntabs == 0 and dtabs == 0:
            messagebox.showerror(
                _("Tabs error"),
                _("You cannot have both the number of tabs or distance equal "
                  + "to zero"),
            )
            return

        app.executeOnSelection("TABS", True, ntabs, dtabs, dx, dy, z, True)
        app.setStatus(_("Create tabs on blocks"))
