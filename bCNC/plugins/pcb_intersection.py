#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@mariobasz Mario Basz"
#It is a variation of the difference pluginn of @Harvie
#__email__  = ""

__name__ = _("PCB Intersection")
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
	__doc__ = _("""Intersections by sectors of two shapes""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"PCB Inters")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "intersection"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
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
		self.intersection(app)
		#print("go!")
#	def interesction(self):
	def intersection(self,app):
#		blocks  = []
	
#		paths_base = []
		xbase=0
		xisland=1
		block_number=0

#		print("len", app.gcode[bid].name() ,len(app.editor.getSelectedBlocks()))
		print("----------------------------------")
		elements=len(app.editor.getSelectedBlocks())
		print("elements",elements)
		base_bid=app.editor.getSelectedBlocks()[xbase]
		print("base bid number",base_bid, "base list",xbase)
		island_bid=app.editor.getSelectedBlocks()[xisland]
		print("island bid number",island_bid, "island list",xisland)
#		print("***************************************")

#		for bid in app.editor.getSelectedBlocks():
	#		print("len", app.gcode[bid].name() ,bid)
#			if app.gcode[bid].operationTest('island'):
#		xbase-=1
#		while xbase<elements-2:
#			xbase+=1
#			print("base:", app.gcode[app.editor.getSelectedBlocks()[xbase]].name())
#			print("****************************************************************************")
		for x in range(elements-1): #<< base
			print("======================================================")
			xbase=x
			print("new base:", app.gcode[app.editor.getSelectedBlocks()[xbase]].name())
			print("-----------------------------------------")
	#		print("*****************")
			# entering base
			for x in range (xbase,elements-1):
				paths_isl = []
				xisland=x+1
				subblock_number=0
	#			bid = app.editor.getSelectedBlocks()[xisland]
	#			print("island:", app.gcode[bid].name() ,bid)
	#		print("*****************")
				print("-----------------------------------------")
				bid = app.editor.getSelectedBlocks()[xbase]
				print("base:", app.gcode[bid].name() ,bid)
		#		paths_base.extend(app.gcode.toPath(bid))
				base = app.gcode.toPath(bid)[0]

				bid = app.editor.getSelectedBlocks()[xisland]
				paths_isl.extend(app.gcode.toPath(bid))
				print("island:", app.gcode[bid].name() ,bid)
				print("-----------------------------------------")

				# entering island
				for island in paths_isl:
					paths_newbase = []
#					print(len(paths_newbase))
				#	while len(paths_base) > 0:
				#	base = paths_base.pop()

					base.intersectPath(island)
					island.intersectPath(base)

					newbase = Path("diff")
					control_base=control_isl =0
					#Add segments from outside of islands:
					for i,seg in enumerate(base):
						if island.isInside(seg.midPoint()):
							newbase.append(seg)
#						if island.isInside(seg.midPoint()):
							control_base+=1

					#Add segments from islands to base or external points from islands
					for i,seg in enumerate(island):
						if base.isInside(seg.midPoint()):
							newbase.append(seg)
		#					if base.isInside(seg.midPoint()):
							control_isl+=1
					control=control_base+control_isl
					print"control base",control_base,"control isl",control_isl,"************"
					if control!=1:
						#Eulerize
						#paths_newbase.extend(newbase.eulerize())
						paths_newbase.extend(newbase.split2contours())
						paths_base = paths_newbase

#					if control!=1:
						for base in paths_base:
							blocks  = []
							print "printing base:"
							print base
		#					print "printing paths_newbase:"
		#					print  paths_newbase
							#base = base.eulerize(True)
							block = Block("inters "+str(block_number)+" [("+str(xbase)+","+str(xisland)+" _ "+str(subblock_number)+" ctrol "+str(control)+")]")
							block_number+=1
							subblock_number+=1
							block.extend(app.gcode.fromPath(base))
							blocks.append(block)

							#active = app.activeBlock()
					#		app.gcode.insBlocks(-1, blocks, "Diff") #<<< insert blocks over active block in the editor
#							app.gcode.insBlocks(-1, blocks) #<<< insert blocks over active block in the editor
							app.gcode.insBlocks(-1, blocks) #<<< insert blocks over active block in the editor
							app.refresh()                                                                                           #<<< refresh editor
							app.setStatus(_("Generated: intersections"))                           #<<< feed back result
							#app.gcode.blocks.append(block)
		firstblock=0
		lastblock=firstblock+elements-1
		print("----------------------------------")
		elements=len(app.editor.getSelectedBlocks())
		print("calculated elements",elements, "(The first block is number 0)")
		base_bid=app.editor.getSelectedBlocks()[firstblock]
		print("from block number",base_bid, app.gcode[app.editor.getSelectedBlocks()[firstblock]].name(),"in list number:",firstblock)
		base_bid=app.editor.getSelectedBlocks()[lastblock]
		print("to block number",base_bid, app.gcode[app.editor.getSelectedBlocks()[lastblock]].name(),"in list number:",lastblock)
#		last_bid=app.editor.getSelectedBlocks()[xbase+elements-1]
#		1print("to blockr numer",last_bid, app.gcode[app.editor.getSelectedBlocks()[xbase+elements-1]].name(), "in list number",xbase+elements-1)
#		print("***************************************")

##############################################


