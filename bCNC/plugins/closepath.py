# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from CNC import Block, Segment
from ToolsPage import Plugin

__author__ = "@harvie Tomas Mudrunka"
# __email__  = ""

__name__ = _("ClosePath")
__version__ = "0.1"


class Tool(Plugin):
    __doc__ = _(
        """Close the path"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "ClosePath")
        # <<< This is the name of file used as icon for the ribbon button.
        #       It will be search in the "icons" subfolder
        self.icon = "closepath"
        self.group = "CAM"  # <<< This is the name of group that plugin belongs
        self.oneshot = True

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        for bid in app.editor.getSelectedBlocks():
            if len(app.gcode.toPath(bid)) < 1:
                continue

            eblock = Block("closed " + app.gcode[bid].name())
            for path in app.gcode.toPath(bid):
                if not path.isClosed():
                    path.append(Segment(Segment.LINE, path[-1].B, path[0].A))
                eblock = app.gcode.fromPath(path, eblock)
            app.gcode[bid] = eblock

        app.refresh()  # <<< refresh editor
        app.setStatus(_("Generated: Closepath"))  # <<< feed back result
