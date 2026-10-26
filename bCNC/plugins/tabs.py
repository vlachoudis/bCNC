# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from tkinter import messagebox

import bcam
from GCode import Block
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


def apply_tabs(gcode, items, ntabs, dtabs, dx, dy, z, circ=True):
    """Insert holding-tab island blocks after the last selected path."""
    if ntabs == 0 and dtabs == 0:
        return

    tablocks = []
    for bid in items:
        block = gcode.blocks[bid]
        if block.name() in ("Header", "Footer"):
            continue

        # update minz for selected islands/tabs rather than doing
        # tabs of tabs
        if block.operationTest("island"):
            block._name = f"{block.nameNop()} [island,minz:{z:f}]"
            continue

        tablock = Block(f"{block.nameNop()} [tab,island,minz:{z:f}]")
        # tablock.color = "#FF0000"
        tablock.color = "orange"
        tablock.enable = False  # Prevent tabs from being cut as path

        for path in gcode.toPath(bid):
            length = path.length()
            d = max(length / float(ntabs), dtabs)
            s = d / 2.0  # start from half distance to add first tab

            while s <= length:
                P = path.distPoint(s)
                s += d
                tablock.extend(
                    gcode.fromPath(
                        bcam.tab_path(P[0], P[1], dx, dy, circ),
                        None,
                        None,
                        False,
                        False,
                        False,
                        None,
                        None,
                        False,
                    )
                )
                tablock.append("( ---------- cut-here ---------- )")

        del tablock[-1]  # remove last cut-here
        tablocks.append(tablock)
    gcode.insBlocks(bid + 1, tablocks, "Tabs created")


def run_tabs(app, *args, **kwargs):
    return run_on_selection(app, apply_tabs, *args, **kwargs)


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
        run_tabs(app, i(1, int(self["ntabs"])),
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

        run_tabs(app, ntabs, dtabs, dx, dy, z, True)
        app.setStatus(_("Create tabs on blocks"))
