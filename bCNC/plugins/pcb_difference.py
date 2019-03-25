#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@mariobasz Mario Basz"
#It is a variation of the difference pluginn of @Harvie
#__email__  = ""

__name__ = _("PCB Difference")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from bpath import EPS,eq,Path, Segment
from bmath import Vector
from copy import deepcopy

class Tool(Plugin):
	__doc__ = _("""Differenece of two shapes""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"PCB diff")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "diff"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		#print("go!")
		blocks  = []

		paths_base = []
		paths_isl = []
#		xisland=0


		for bid in app.editor.getSelectedBlocks():
#			if bid==app.editor.getSelectedBlocks()[xisland]:
			if app.gcode[bid].operationTest('island'):
				paths_isl.extend(app.gcode.toPath(bid))
			else:
				paths_base.extend(app.gcode.toPath(bid))
		print "len paths_base", len(paths_base)
		print "paths_base",paths_base

		for island in paths_isl:
#		for base in paths_base:
			paths_newbase = []
			i=1
			while len(paths_base) > 0:
				print "len",len(paths_base),"********************"
				print "entry",i
#				bid = app.editor.getSelectedBlocks()[i]
#				print "bid",bid
				i+=1
				base = paths_base.pop()
#				base = app.gcode.toPath(bid)[0]

				base.intersectPath(island)
				island.intersectPath(base)

				newbase = Path("diff")
				control_isl=0
				control_base=0
				control =0

				#Add segments from outside of islands:
				for i,seg in enumerate(base):
					if island.isInside(seg.midPoint()):
						control_base+=1
						control+=1
					if not island.isInside(seg.midPoint()):
						newbase.append(seg)
				print"control base",control_base,"======="

				#Add segments from islands to base
				for i,seg in enumerate(island):
					if base.isInside(seg.midPoint()): #and base.isInside(seg.A) and base.isInside(seg.B):
						control_isl+=1
						control+=1
						newbase.append(seg)
				print"control island",control_isl,"======="
				print"********** control",control,"************"

				#Eulerize
				#paths_newbase.extend(newbase.eulerize())
				paths_newbase.extend(newbase.split2contours())
			paths_base = paths_newbase

		for base in paths_base:
#		for island in paths_isl:
			print base
			#base = base.eulerize(True)
			block = Block("diff "+str(control))
			block.extend(app.gcode.fromPath(base))
			blocks.append(block)

		#active = app.activeBlock()
		app.gcode.insBlocks(-1, blocks, "Diff") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Diff"))                           #<<< feed back result
		#app.gcode.blocks.append(block)

