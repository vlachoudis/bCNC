# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from bmath import Vector
from CNC import CNC
from GCode import Block
from ToolsPage import Plugin, run_on_selection

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


def cut_path(
    gcode,
    newblock,
    path,
    z,
    depth,
    stepz,
    helix=False,
    helixBottom=True,
    ramp=0,
    islandPaths=[],
    exitpoint=None,
    springPass=False,
):
    closed = path.isClosed()
    zigzag = True  # FIXME: Add UI to set this?
    entry = True
    exit_ = False

    # Calculate ramp
    if ramp > 0:
        ramp = abs(ramp) * CNC.vars["diameter"]  # n times tool diameter
    if ramp < 0:
        ramp = abs(ramp)  # absolute
    if ramp == 0:
        ramp = None  # No ramp

    # Calculate exit point for thread milling
    centr = Vector(path.center())
    if exitpoint == 1:
        exitpoint = centr
    elif exitpoint == -1:
        exitpoint = path[-1].B + (path[-1].B - centr)
    else:
        exitpoint = None

    # Mark in which island we are inside
    if islandPaths:
        for island in reversed(islandPaths):
            path.intersectPath(island)
        for island in reversed(islandPaths):
            path.markInside(island, island._inside)

    # Decide if doing additional "appendix" passes after loop
    # (eg.: spring pass or helixbottom)
    appendix = False
    if (springPass and closed) or (helix and helixBottom):
        appendix = True

    # iterate over depth passes:
    retract = True
    while (z - depth) > 1e-7:
        # Go one step lower
        z = max(z - stepz, depth)

        # Detect last pass of loop
        if abs(z - depth) < 1e-7 and not appendix:
            exit_ = True

        # Flat cuts:
        if not helix:
            newblock.append(f"(pass {z:f})")
            if zigzag:
                gcode.fromPath(
                    path,
                    newblock,
                    z,
                    retract,
                    True,
                    exit_,
                    exitpoint=exitpoint
                )
                if not closed:
                    path.invert()
            else:
                gcode.fromPath(
                    path,
                    newblock,
                    z,
                    True,
                    True,
                    exit_,
                    exitpoint=exitpoint
                )

        # Helical/Ramp cuts:
        else:
            if helixBottom:
                exit_ = False

            if closed:
                newblock.append(
                    f"(pass {z + stepz:f} to {z:f})")
                gcode.fromPath(
                    path,
                    newblock,
                    z,
                    retract,
                    entry,
                    exit_,
                    z + stepz,
                    ramp,
                    exitpoint=exitpoint,
                )
            else:
                # Cut open path back and forth while descending
                newblock.append(
                    f"(pass {z + stepz:f} to {z + stepz / 2:f})")
                gcode.fromPath(
                    path,
                    newblock,
                    z + stepz / 2,
                    retract,
                    entry,
                    False,
                    z + stepz,
                    ramp,
                    exitpoint=exitpoint,
                )
                path.invert()
                newblock.append(f"(pass {z + stepz / 2:f} to {z:f})")
                gcode.fromPath(
                    path,
                    newblock,
                    z,
                    False,
                    False,
                    exit_,
                    z + stepz / 2,
                    ramp,
                    exitpoint=exitpoint,
                )
                path.invert()

        retract = False
        entry = False

    # Do appendix passes like spring pass or helixbottom
    if appendix:
        if springPass and closed:
            ramp = None  # Do not truncate pass when inverting direction
            path.invert()
            if not closed:
                retract = True
                entry = True
            newblock.append(f"(pass {z:f} spring)")
        else:
            newblock.append(f"(pass {z:f} bottom)")

        gcode.fromPath(
            path,
            newblock,
            z,
            retract,
            entry,
            True,
            exitpoint=exitpoint,
            truncate=ramp,
        )

    return newblock


def apply_cut(
    gcode,
    items,
    depth=None,
    stepz=None,
    surface=None,
    feed=None,
    feedz=None,
    cutFromTop=False,
    helix=False,
    helixBottom=True,
    ramp=0,
    islandsLeave=False,
    islandsCut=False,
    islandsSelectedOnly=True,
    exitpoint=None,
    springPass=False,
    islandsCompensate=False,
):
    if surface is None:
        surface = gcode.cnc["surface"]
    if stepz is None:
        stepz = gcode.cnc["stepz"]
    if depth is None:
        depth = surface - gcode.cnc["thickness"]

    # override temporarily the feed if needed
    if feed is not None:  # swap feed with cnc[cutfeed]
        gcode.cnc["cutfeed"], feed = feed, gcode.cnc["cutfeed"]
    if feedz is not None:
        gcode.cnc["cutfeedz"], feedz = feedz, gcode.cnc["cutfeedz"]

    # Test if cutting within stock boundaries
    if surface > gcode.cnc["surface"]:
        return (
            "ERROR: Starting cut height is higher than stock surface. "
            "Please change stock surface in Tools->Stock or cut depth."
        )
    if (
        depth < gcode.cnc["surface"] - gcode.cnc["thickness"]
        or depth > gcode.cnc["surface"]
    ):
        return (
            f"ERROR: Cut depth {depth:g} outside stock surface: "
            f"{gcode.cnc['surface']:g} .. "
            f"{gcode.cnc['surface'] - gcode.cnc['thickness']:g}\n"
            "Please change stock surface in Tools->Stock or cut depth."
        )

    # Determine operation block name
    if abs(depth - (gcode.cnc["surface"] - gcode.cnc["thickness"])) < 1e-7:
        opname = "cut"
        if helix:
            opname = "helicut"
    else:
        opname = f"cut:{depth:g}"
        if helix:
            opname = f"helicut:{depth:g}"

    stepz = abs(stepz)
    undoinfo = []

    # Get list of islands and remove them from items
    islands = []
    islandPaths = []
    if islandsLeave:
        for bid, block in enumerate(gcode.blocks):
            if islandsSelectedOnly and bid not in items:
                continue
            if block.operationTest("island"):
                islands.append(bid)
                # determine island height
                islz = gcode.cnc["safe"]
                if block.operationGet("minz") is not None:
                    islz = float(block.operationGet("minz"))
                # determine if we should offset island
                # (tabs are always offset)
                isloffset = False
                if islandsCompensate or block.operationTest("tab"):
                    isloffset = True
                # load island paths
                for islandPath in gcode.toPath(bid):
                    # compensate for cutter diameter if needed
                    if isloffset:
                        islandPath = islandPath.offsetClean(
                            CNC.vars["diameter"] / 2
                        )[0]
                    islandPath._inside = islz
                    islandPaths.append(islandPath)

    # Remove islands from paths to cut if not requested
    # TODO: maybe also remove all islands with "tab" tag
    if not islandsCut and islands:
        for island in islands:
            if island in items:
                items.remove(island)
    # Check if there are any paths left
    if not items:
        return "You must select toolpaths along with islands!"

    for bid in items:
        block = gcode.blocks[bid]
        if block.name() in ("Header", "Footer"):
            continue
        block.enable = True
        newblock = Block(block.name())

        # Do not apply islands on islands:
        islandPathsClean = islandPaths
        if bid in items and bid in islands:
            islandPathsClean = []

        for path in gcode.toPath(bid):
            z0 = surface + stepz if cutFromTop else surface
            cut_path(
                gcode,
                newblock,
                path,
                z0,
                depth,
                stepz,
                helix,
                helixBottom,
                ramp,
                islandPathsClean,
                exitpoint,
                springPass,
            )
        if newblock:
            undoinfo.append(gcode.addBlockOperationUndo(bid, opname))
            undoinfo.append(gcode.setBlockLinesUndo(bid, newblock))
    gcode.addUndo(undoinfo)

    # restore feed
    if feed is not None:
        gcode.cnc["cutfeed"] = feed
    if feedz is not None:
        gcode.cnc["cutfeedz"] = feedz



# -----------------------------------------------------------------------------
def run_cut(app, *args, **kwargs):
    return run_on_selection(app, apply_cut, *args, **kwargs)


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
        run_cut(app, *p)
        app.setStatus(_("CUT selected paths"))

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

        run_cut(
            app,
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
