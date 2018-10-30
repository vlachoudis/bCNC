#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 25 sept 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("Linearize")
__version__ = "0.2"

import math
import os.path
import re
from CNC import CNC,Block
from bpath import eq, Path, Segment
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

class Tool(Plugin):
	__doc__ = _("""G-Code linearizer""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Linearize")
		self.icon = "linearize"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("maxseg", "mm", "1", _("segment size"), _("Maximal length of resulting lines, smaller number means more precise output and longer g-code. Length will be automaticaly truncated to be even across whole subdivided segment.")),
			("splitlines", "bool", False, _("subdiv lines"), _("Also subdivide the lines. Otherwise only arcs and splines will be subdivided"))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below
		self.help = """
This plugin will subdivide the toolpath in such way, that all segments are broken to very short lines, which means that there will be no arcs or splines.
This is exact opposite of "arcfit" plugin. This is not very usefull for common CNC operation. However this might be useful when you need to proces arcs in CAD/CAM software which only support straight lines.
It usualy happens that new development features and plugins in bCNC only support straight lines and they add support for arcs later. So if you are early adopter of development features or encounter arc-related bug, you might try to use this plugin to convert your g-code to lines before working using these new features.
Also if you are working with some primitive motion controller, which only supports straight lines (G1). You might use this plugin to preprocess the g-code to get support for arcs (G2 and G3).

If you set the segment size large enough, you can even use this to create inscribed polygons in arcs and circles.
"""


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		maxseg = self.fromMm("maxseg")
		splitlines = self["splitlines"]

		#print("go!")
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue

			#nblock = Block("flat "+app.gcode[bid].name())
			#for i in app.gcode[bid]:
			#	nblock.append(re.sub(r"\s?z-?[0-9\.]+","",i))
			#blocks.append(nblock)

			eblock = Block("lin "+app.gcode[bid].name())
			opath = app.gcode.toPath(bid)[0]
			npath = opath.linearize(maxseg, splitlines)
			eblock = app.gcode.fromPath(npath,eblock)
			blocks.append(eblock)



		#active = app.activeBlock()
		#if active == 0: active+=1
		active=-1 #add to end
		app.gcode.insBlocks(active, blocks, "Linearized") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Linearize"))                           #<<< feed back result
		#app.gcode.blocks.append(block)
