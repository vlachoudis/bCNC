# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018


from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "@harvie Tomas Mudrunka"
# __email__  = ""

__name__ = _("Center")
__version__ = "0.1"


class Tool(Plugin):
    __doc__ = _(
        """Find center of bounding box"""
    )  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        Plugin.__init__(self, master, "Center")
        # Helical_Descent: is the name of the plugin show in the tool ribbon button
        # <<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
        self.icon = "centerpoint"
        self.group = "CAM"  # <<< This is the name of group that plugin belongs
        self.oneshot = True
        # Here we are creating the widgets presented to the user inside the plugin
        # Name, Type , Default value, Description
        self.variables = [  # <<< Define a list of components for the GUI
            (
                "name",
                "db",
                "",
                _("Name"),
            )  # used to store plugin settings in the internal database
        ]
        self.buttons.append(
            "exe"
        )  # <<< This is the button added at bottom to call the execute method below

    # ----------------------------------------------------------------------
    # This method is executed when user presses the plugin execute button
    # ----------------------------------------------------------------------
    def execute(self, app):
        blocks = []
        for bid in app.editor.getSelectedBlocks():
            if len(app.gcode.toPath(bid)) < 1:
                continue
            path = app.gcode.toPath(bid)[0]
            x, y = path.center()
            eblock = Block("center of " + app.gcode[bid].name())
            eblock.append("G0 x"
                          + str(round(x, CNC.digits))
                          + " y"
                          + str(round(y, CNC.digits))
                          )
            eblock.append("G1 Z0 F200")
            eblock.append("G0 Z10")
            blocks.append(eblock)

        active = -1  # add to end
        app.gcode.insBlocks(
            active, blocks, "Center created"
        )  # <<< insert blocks over active block in the editor
        app.refresh()  # <<< refresh editor
        app.setStatus(_("Generated: Center"))  # <<< feed back result
