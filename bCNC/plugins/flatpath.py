#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from __future__ import absolute_import
from __future__ import print_function
__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("FlatPath")
__version__ = "0.2"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod


class Tool(Plugin):
	__doc__ = _("""Flatten the path""")			#<<< This comment will be show as tooltip for the ribbon button

	def __init__(self, master):
		Plugin.__init__(self, master,"FlatPath")
		self.icon = "flatpath"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		#self.variables = [			#<<< Define a list of components for the GUI
		#	("name"    ,    "db" ,    "", _("Name"))							#used to store plugin settings in the internal database
		#]
		#self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		#print("go!")
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue

			#nblock = Block("flat "+app.gcode[bid].name())
			#for i in app.gcode[bid]:
			#	nblock.append(re.sub(r"\s?z-?[0-9\.]+","",i))
			#blocks.append(nblock)

			eblock = Block("flat "+app.gcode[bid].name())
			eblock = app.gcode.fromPath(app.gcode.toPath(bid)[0],eblock)
			blocks.append(eblock)



		#active = app.activeBlock()
		#if active == 0: active+=1
		active=-1 #add to end
		app.gcode.insBlocks(active, blocks, "Shape flattened") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Flat"))                           #<<< feed back result
		#app.gcode.blocks.append(block)
