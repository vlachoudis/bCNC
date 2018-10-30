#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("ClosePath")
__version__ = "0.1"

import math
import os.path
import re
from CNC import CNC,Block,Segment
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

class Tool(Plugin):
	__doc__ = _("""Close the path""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"ClosePath")
		self.icon = "closepath"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
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
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue

			eblock = Block("closed "+app.gcode[bid].name())
			for path in app.gcode.toPath(bid):
				if not path.isClosed():
					path.append(Segment(Segment.LINE, path[-1].B, path[0].A))
				eblock = app.gcode.fromPath(path,eblock)
			#blocks.append(eblock)
			app.gcode[bid] = eblock

		#active=-1 #add to end
		#app.gcode.insBlocks(active, blocks, "Path closed") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Closepath"))                           #<<< feed back result
		#app.gcode.blocks.append(block)
