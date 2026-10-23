# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from ToolsPage import Plugin

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


class Tool(Plugin):
    __doc__ = _("Perform a profile operation on selected code")

    def __init__(self, master):
        Plugin.__init__(self, master, "Profile")
        self.icon = "profile"
        self.group = "CAM-core-big"
        self.order = 30
        self.variables = [
            ("name", "db", "", _("Name")),
            (
                "endmill",
                "db",
                "",
                _("End Mill"),
                _("Size of this endmill will be used as offset distance"),
            ),
            (
                "direction",
                "inside,outside",
                "outside",
                _("Direction"),
                _("Should we machine on inside or outside of the shape?"),
            ),
            ("offset", "float", 0.0, _("Additional offset distance")),
            (
                "overcut",
                "bool",
                1,
                _("Overcut"),
                _("Sets if we want to overcut or not."),
            ),
            (
                "pocket",
                "bool",
                0,
                _("Pocket"),
                _(
                    "Generate pocket after profiling? Useful for making "
                    + "pockets with overcuts."
                ),
            ),
        ]
        self.buttons.append("exe")
        self.help = "\n".join([
            "This plugin offsets shapes to create toolpaths for profiling "
            + "operation.",
            "Shape needs to be offset by the radius of endmill to get cut "
            + "correctly.",
            "",
            "Currently we have two modes.",
            "",
            "Without overcut:",
            "#overcut-without",
            "",
            "And with overcut:",
            "#overcut-with",
            "",
            "Blue is the original shape from CAD",
            "Turquoise is the generated toolpath",
            "Grey is simulation of how part will look after machining",
        ])

    def execute(self, app):
        if self["endmill"]:
            self.master["endmill"].makeCurrent(self["endmill"])
        name = self["name"]
        if name == "default" or name == "":
            name = None
        app.profile(
            self["direction"],
            self["offset"],
            self["overcut"],
            name,
            self["pocket"],
        )
        app.setStatus(_("Generate profile path"))
