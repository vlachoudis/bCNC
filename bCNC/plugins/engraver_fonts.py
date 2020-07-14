#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:  Attila Kolinger
# Date:	   26.feb.2018.

__author__ = "Attila Kolinger"
__email__ = "attila.kolinger@gmail.com"  # <<< here put an email where plugins users can contact you

import HersheyFonts

# Here import the libraries you need, these are necessary to modify the code
from CNC import CNC, Block
from ToolsPage import Plugin


# ==============================================================================
# Manual drillmark plugin
# ==============================================================================
class Tool(Plugin):
    __doc__ = _("""This plugin is for creating text optimized for engraving""")  # <<< This comment will be show as tooltip for the ribbon button

    def __init__(self, master):
        self.__editing = None
        Plugin.__init__(self, master, "Text engraver")
        # MYPlugin: is the name of the plugin show in the tool ribbon button
        self.icon = "HersheyIcon"  # <<< This is the name of gif file used as icon for the ribbon button. It will be search in the "icons" subfolder
        self.group = "Generator"  # <<< This is the name of group that plugin belongs
        # Here we are creating the widgets presented to the user inside the plugin
        # Name, Type , Default value, Description
        self.thefont = HersheyFonts.HersheyFonts()
        def_font_name = self.thefont.load_default_font() or 'futural'
        if not def_font_name in self.thefont.default_font_names:
            def_font_name = self.thefont.default_font_names[0]
        self.variables = [
            ("Depth", "mm", -0.20, _("Destination Depth")),
            ("FontSize", "mm", 10.0, _("Font size")),
            ("Spacing", "float", 0.0, _("Extra intercharacter spacing")),
            ("BuiltInFont", ",".join(self.thefont.default_font_names) + ",<file>", def_font_name, _("Builtin fonts")),
            ("FontFile", "file", "", _("Font file")),
            ("Text", "text", "Engrave this!", _("Text"))
        ]
        self.help = '''This plugin generates GCODE from text for engraving. Several fonts are included, but laoding external HersheyFonts (.jhf) is also possible.
If Destination depth is specified rapid moves are executed at zsafe height.
Font size specifies the nominal font height.
Extra intercharacter spacing changes the text density. [Default:0] Negative numbers shortens the text, positive number make it less dense.
The built-in fonts list shows all available fonts. [Default:futural] Selecting '<file>' activates the external file loading option.'''
        self.buttons.append("exe")

    def render_one_pass(self, render_text, working_depth, surface_depth, do_raise, rapid_feed_max, cut_feed):
        block = []
        last_x = last_y = None
        for stroke in self.thefont.strokes_for_text(render_text):
            if len(stroke) > 1:
                start_x, start_y = stroke[0]
                if start_x != last_x or start_y != last_y:
                    if do_raise:
                        block.append(CNC.zsafe())  # <<< Move rapid Z axis to the safe height in Stock Material
                    block.append(CNC.grapid(start_x, start_y, f=rapid_feed_max))  # <<< Move rapid to X and Y start coordinate
                    if do_raise:
                        block.append(CNC.zenter(working_depth))  # <<< Enter in the material with Plunge Feed for current material
                last_x, last_y = stroke[1]
                block.append(CNC.gline(last_x, last_y, f=cut_feed))
                for last_x, last_y in stroke[2:]:
                    block.append(CNC.gline(last_x, last_y))
        return block

    def execute(self, app):
        error = ''
        name = self["name"]
        if not name or name == "default":
            name = "Engraved Hershey Text"

        # Retrive data from user imput
        final_depth = self["Depth"]
        surface_depth = CNC.vars["surface"] or 0.0
        do_raise = type(final_depth) == type(1.0)
        font_size = self["FontSize"] or 0.0
        font_spacing = self["Spacing"] or 0.0
        builtin_font_name = self["BuiltInFont"]
        font_file = self["FontFile"]
        render_text = self["Text"]
        stepdown = abs(CNC.vars["stepz"])
        rapid_feed_max = min(CNC.feedmax_x, CNC.feedmax_y)
        cut_feed = CNC.vars["cutfeed"]  # <<< Get cut feed for the current material

        if render_text:
            blocks = []
            block = Block(name)
            if builtin_font_name == '<file>':
                self.thefont.load_font_file(font_file)
            else:
                self.thefont.load_default_font(builtin_font_name)
            self.thefont.normalize_rendering(font_size)
            self.thefont.render_options.spacing = font_spacing
            first_pass = True

            current_passs_block = self.render_one_pass(render_text=render_text, working_depth=final_depth, surface_depth=surface_depth, do_raise=do_raise, rapid_feed_max=rapid_feed_max, cut_feed=cut_feed)
            if not first_pass:
                block.append('( ---------- cut-here ---------- )')
            block.extend(current_passs_block)
            first_pass = False

            blocks.append(block)
            active = app.activeBlock()
            app.gcode.insBlocks(active, blocks, "Engraved")  # <<< insert blocks over active block in the editor
            app.refresh()  # <<< refresh editor
            app.setStatus(_("Generated: Text for engraving"))  # <<< feed back result
        else:
            app.setStatus(_("Nothing to generate."))  # <<< feed back result

    def update(self):
        editing = self.__editing
        self.__editing = None
        if editing == 'FontFile':
            self['BuiltInFont'] = '<file>'
            return True
        elif editing == 'BuiltInFont':
            self['FontFile'] = ''
            return True
        return Plugin.update(self)

    def edit(self, event=None, rename=False):
        lb = self.master.listbox.listbox(1)
        if event is None or event.type == "2":
            active = lb.index('active')
        else:
            active = lb.nearest(event.y)
        self.__editing, t, d, l = self.variables[active][:4]
        Plugin.edit(self=self, event=event, rename=rename)
