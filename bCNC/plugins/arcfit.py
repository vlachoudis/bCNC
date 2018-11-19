#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 25 sept 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("ArcFit")
__version__ = "0.1.1"

import math
import os.path
import re
from CNC import CNC,Block
from bpath import eq, Path, Segment
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

class Tool(Plugin):
	__doc__ = _("""G-Code arc-fit""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"ArcFit")
		self.icon = "arcfit"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("preci", "mm", 0.5, _("arc precision (mm)"), _("how precisely must arc fit. set to 0 to disable arc fitting")),
			("linpreci", "mm", 0.001, _("line precision (mm)"), _("how precisely must line fit. set to 0 to disable line fitting, but at least some line fitting (0.001 to 0.01) might be needed to fix arcs, so they can be fit")),
			("numseg", "int", 3, _("minimal number of segments to create arc"))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below
		self.help = """
This plugin will try to simplify the g-code by replacing amounts of short subsequent lines by one long arc.
There are some precision tunables which will allow you to define how much the resulting arc can differ from orignal lines.
This plugin can reverse the output of "linearize" plugin, which does the opposite.
This is not really meant to fillet sharp corners. But rather to reduce the number of g-code lines while preserving the toolpath shape.
This can be also useful for postprocessing of imported DXF/SVG splines. Splines have to be subdivided to short lines when importing and this can simplify the resulting code.
Another usecase is to postprocess mesh slices as STL/PLY format is based on triangles, it will never perfectly describe circles and arcs. You can use this plugin to simplify/smooth shapes imported from 3D mesh files.
Before this plugin tries to fit arcs it also tries to fit and merge longest possible lines within given precision. Line precision should be set much lower than arc precision, otherwise the line merging algorithm will "eat" lines that belong to arcs. Unless you want to do massive shape simplification and don't mind loosing details.
"""

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		preci = self.fromMm("preci")
		linpreci = self.fromMm("linpreci")
		numseg = self["numseg"]

		#print("go!")
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue

			#nblock = Block("flat "+app.gcode[bid].name())
			#for i in app.gcode[bid]:
			#	nblock.append(re.sub(r"\s?z-?[0-9\.]+","",i))
			#blocks.append(nblock)

			eblock = Block("fit "+app.gcode[bid].name())
			npath = app.gcode.toPath(bid)[0]
			npath = npath.mergeLines(linpreci)
			npath = npath.arcFit(preci, numseg)
			if npath.length() <= 0:
				#FIXME: not sure how this could happen
				print "Warning: ignoring zero length path!"
				continue
			eblock = app.gcode.fromPath(npath,eblock)
			blocks.append(eblock)



		#active = app.activeBlock()
		#if active == 0: active+=1
		active=-1 #add to end
		app.gcode.insBlocks(active, blocks, "Arc fit") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Arc fit"))                           #<<< feed back result
		#app.gcode.blocks.append(block)
