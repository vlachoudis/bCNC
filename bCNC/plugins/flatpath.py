# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018


from CNC import Block
from ToolsPage import Plugin

__author__ = "@harvie Tomas Mudrunka"
# __email__  = ""

__name__ = _("FlatPath")
__version__ = "0.2"


class Tool(Plugin):
    __doc__ = _(
        """Flatten the path"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "FlatPath")
        # <<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
        self.icon = "flatpath"
        self.group = "CAM"  # <<< This is the name of group that plugin belongs
        self.oneshot = True

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        blocks = []
        for bid in app.editor.getSelectedBlocks():
            if len(app.gcode.toPath(bid)) < 1:
                continue

            eblock = Block("flat " + app.gcode[bid].name())
            eblock = app.gcode.fromPath(app.gcode.toPath(bid), eblock)
            blocks.append(eblock)

        active = -1  # add to end
        app.gcode.insBlocks(
            active, blocks, "Shape flattened"
        )  # <<< insert blocks over active block in the editor
        app.refresh()  # <<< refresh editor
        app.setStatus(_("Generated: Flat"))  # <<< feed back result
