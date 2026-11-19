# -*- coding: ascii -*-
"""Color palettes of the application: one for the light and one for the dark
theme. The colors come from the [Color] section of the configuration
(light: "canvas.grid", dark: "dark.canvas.grid"); a missing key falls back to
the built-in value. The UI asks the current theme for a color by name:

    theme.currentTheme.getColor("canvas.grid")
"""

SECTION = "Color"

# key: (light, dark)
DEFAULTS = {
    "canvas.camera": ("Cyan", "Cyan"),
    "canvas.disable": ("LightGray", "LightGray"),
    "canvas.enable": ("Black", "White"),
    "canvas.gantry": ("Red", "Red"),
    "canvas.grid": ("Gray", "#5A5A5A"),
    "canvas.margin": ("Magenta", "Magenta"),
    "canvas.move": ("DarkCyan", "DarkCyan"),
    "canvas.process": ("Green", "Green"),
    "canvas.ruler": ("Green", "Green"),
    "canvas.select": ("Blue", "#5AA9FF"),
    "canvas.select2": ("DarkCyan", "DarkCyan"),
    "canvas.probetext": ("Green", "Green"),
    "canvas.backgroundUp": ("White", "#1E1E1E"),
    "canvas.backgroundDown": ("White", "#1E1E1E"),
    "canvas.axestext": ("Black", "White"),
    "canvas.rapid": ("Gray", "Gray"),
    "canvas.stock": ("BurlyWood", "BurlyWood"),
    "canvas.stockcut": ("BurlyWood4", "BurlyWood4"),
    "ribbon.active": ("LightYellow", "#5A5A3A"),
    "ribbon.select": ("#C0FFC0", "#3A5A3A"),
}

# the colors that may be set to an empty value (feature off)
BLANKABLE = {"canvas.rapid"}


def _flag(value):
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return False


class Theme:
    def __init__(self):
        self.dark = False  # the theme in use, set by tkExtra
        self.followSystem = False  # theme.followsystem
        self.forceDark = False  # theme.forcedark, when not following
        self.palettes = {False: {}, True: {}}
        self.load(lambda section, name, default: default)

    def load(self, getStr):
        """Fill both palettes from the configuration; getStr is
        Utils.getStr like: getStr(section, name, default)"""
        self.followSystem = _flag(getStr(SECTION, "theme.followsystem", "0"))
        self.forceDark = _flag(getStr(SECTION, "theme.forcedark", "0"))
        for dark in (False, True):
            prefix = "dark." if dark else ""
            palette = self.palettes[dark]
            for key, defaults in DEFAULTS.items():
                value = getStr(SECTION, prefix + key, None)
                if value is None:
                    value = defaults[dark]
                value = value.strip()
                if value == "" and key not in BLANKABLE:
                    value = defaults[dark]
                palette[key] = value

    def getColor(self, key, dark=None):
        """Color of the current theme (or of the given one)"""
        return self.palettes[self.dark if dark is None else dark][key]


currentTheme = Theme()
