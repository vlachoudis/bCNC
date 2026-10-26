# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


class Tool(Plugin):
    __doc__ = _("Cut for the full stock thickness selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Cut")
        self.icon = "cut"
        self.group = "CAM-core-big"
        self.order = 10
        self.variables = [
            ("name", "db", "", _("Name")),
            ("surface", "mm", "", _("Surface Z")),
            ("depth", "mm", "", _("Target Depth")),
            ("stepz", "mm", "", _("Depth Increment")),
            ("feed", "mm", "", _("Feed")),
            ("feedz", "mm", "", _("Plunge Feed")),
            (
                "strategy",
                "flat,helical+bottom,helical,ramp",
                "helical+bottom",
                _("Cutting strategy"),
            ),
            (
                "ramp",
                "int",
                10,
                _("Ramp length"),
                _(
                    "positive value = relative to tool diameter (5 to 10 "
                    + "probably makes sense), negative = absolute ramp "
                    + "distance (you probably don't need this). Also note "
                    + "that ramp can't currently be shorter than affected "
                    + "g-code segment."
                ),
            ),
            ("cutFromTop", "bool", False, _("First cut at surface height")),
            (
                "spring",
                "bool",
                False,
                _("Spring pass"),
                _(
                    "Do the last cut once more in opposite direction. "
                    + "Helix bottom is disabled in such case."
                ),
            ),
            (
                "exitpoint",
                "on path,inside,outside",
                "on path",
                _("Exit strategy (useful for threads)"),
                _(
                    "You should probably always use 'on path', unless "
                    + "you are threadmilling!"
                ),
            ),
            ("islandsLeave", "bool", True, _("Leave islands uncut")),
            (
                "islandsSelectedOnly",
                "bool",
                True,
                _("Only leave selected islands uncut"),
            ),
            (
                "islandsCompensate",
                "bool",
                False,
                _("Compensate islands for cutter radius"),
                _(
                    "Add additional margin/offset around islands to "
                    + "compensate for endmill radius. This is automatically "
                    + "done for all islands if they are marked as tabs."
                ),
            ),
            ("islandsCut", "bool", True, _("Cut contours of selected islands")),
        ]
        self.buttons.append("exe")
        self.commands = {"CUT": self.cmdline}
        self.help = "\n".join([
            "Cut selected toolpath into Z depth of stock material.",
            "",
            "For short paths, you should probably use helical cut with "
            + "bottom.",
            "For long toolpaths and pocketing you should use ramp cut "
            + "(length around 10).",
            "Also there's classic flat cuting strategy, but that will lead to "
            + "plunging straight down to material, which is not really "
            + "desirable (especially when milling harder materials).",
            "",
            "If you have generated tabs and want them to be left uncut, you "
            + "should check \"leave islands\" and uncheck "
            + "\"cut contours of islands\"",
            "If you want islands to get finishing pass, cou can use "
            + "\"cut contours of selected islands\" or cut them "
            + "individually afterwards.",
        ])

    # CUT [depth] [step] [surface] [feed] [feedz]
    def cmdline(self, app, args, oline=None):
        p = []
        for i in range(1, 6):
            try:
                p.append(float(args[i]))
            except Exception:
                p.append(None)
        app.executeOnSelection("CUT", True, *p)

    def execute(self, app):
        surface = self.fromMm("surface", None)
        depth = self.fromMm("depth", None)
        step = self.fromMm("stepz", None)

        try:
            feed = self.fromMm("feed", None)
        except Exception:
            feed = None
        try:
            feedz = self.fromMm("feedz", None)
        except Exception:
            feedz = None

        strategy = self["strategy"]
        cutFromTop = self["cutFromTop"]
        springPass = self["spring"]

        islandsLeave = self["islandsLeave"]
        islandsCut = self["islandsCut"]
        islandsSelectedOnly = self["islandsSelectedOnly"]
        islandsCompensate = self["islandsCompensate"]

        helix = strategy in ["helical+bottom", "helical", "ramp+bottom", "ramp"]

        ramp = 0
        if strategy in ["ramp+bottom", "ramp"]:
            ramp = self["ramp"]
            if ramp < 0:
                ramp = self.master.fromMm(float(ramp))

        helixBottom = strategy in ["helical+bottom", "ramp+bottom", "ramp"]

        exitpoint = self["exitpoint"]
        if exitpoint == "inside":
            exitpoint = 1
        elif exitpoint == "outside":
            exitpoint = -1
        else:
            exitpoint = None

        app.executeOnSelection(
            "CUT",
            True,
            depth,
            step,
            surface,
            feed,
            feedz,
            cutFromTop,
            helix,
            helixBottom,
            ramp,
            islandsLeave,
            islandsCut,
            islandsSelectedOnly,
            exitpoint,
            springPass,
            islandsCompensate,
        )
        app.setStatus(_("CUT selected paths"))
