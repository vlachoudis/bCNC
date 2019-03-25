#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from __future__ import print_function
from __future__ import print_function
__author__ = ""
#__email__  = ""

__name__ = _("Intersection2")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block
from CNCList import CNCListbox
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from bpath import EPS,eq,Path, Segment
from bmath import Vector
from copy import deepcopy
from operator import itemgetter


class Tool(Plugin):
	__doc__ = _("""Intersection of pattern and paths""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Intersection2")
		self.icon = "flatten"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "Development"	#<<< This is the name of group that plugin belongs
		#self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [
			("name",         "db" ,    "", _("Name")),
			("ToolSize",     "mm" ,     1, _("Pyrograph tip size")),
			("File",       "file" ,    "", _("File to process")),
			("In-Out",     "In,Out,Solid" ,"In", _(" In or Out")),
			("xAdd",        "mm" ,     1, _("Box X Add")),
			("yAdd",        "mm" ,     1, _("Box Y Add")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):

		n = self["name"]
		if not n or n=="default": n="Pyrograph"

		#Import parameters
		toolSize = self.fromMm("ToolSize")

		if toolSize <=0:
			app.setStatus(_("Pyrograph abort: Tool Size must be > 0"))
			return


		filename = self["File"]

		#Open gcode file
		app.load(filename)
		app.editor.selectAll()

		inOut= self["In-Out"]
		xadd= self["xAdd"]
		yadd= self["yAdd"]
		if xadd=="":xadd=1
		if yadd=="":yadd=1
#---------------------------------------------
		#Create the external box
		if inOut=="Out":
			box=Block("Box")
			external_box=[]

			box.append(CNC.grapid(CNC.vars["xmin"]-xadd,CNC.vars["ymin"]-yadd))
			box.append(CNC.gline(CNC.vars["xmin"]-xadd,CNC.vars["ymax"]+yadd))
			box.append(CNC.gline(CNC.vars["xmax"]+xadd,CNC.vars["ymax"]+yadd))
			box.append(CNC.gline(CNC.vars["xmax"]+xadd,CNC.vars["ymin"]-yadd))
			box.append(CNC.gline(CNC.vars["xmin"]-xadd,CNC.vars["ymin"]-yadd))

			#Insert the external block
			external_box.append(box)
			app.gcode.insBlocks(1, external_box, "External_Box")
			app.refresh()

#---------------------------------------------

		dx = CNC.vars["xmax"]+toolSize

		dy = CNC.vars["ymax"]-CNC.vars["ymin"]+toolSize

		#Number of vertical divisions based on toolsize
		divisions = dy / toolSize
		divisions = int(divisions)+1

		#Distance between horizontal lines
		step_y = dy/divisions
		n_steps_y = divisions+1

		if inOut!="Solid":
			#Create the snake pattern according to the number of divisions
			pattern=Block(self.name)
			pattern_base=[]

			for n in range(n_steps_y+1):
				if n==0:
					pattern.append(CNC.grapid(CNC.vars["xmin"]-1,CNC.vars["ymin"]))
				else:
					y0=step_y*(n-1)+CNC.vars["ymin"]
					y1=step_y*(n)+CNC.vars["ymin"]
					if not(n%2 == 0):
						pattern.append(CNC.glinev(1,[dx,y0]))
						pattern.append(CNC.grapid(dx,y1))
					else:
						pattern.append(CNC.glinev(1,[CNC.vars["xmin"]-1,y0]))
						pattern.append(CNC.grapid(CNC.vars["xmin"]-1,y1))

			#Insert the pattern block
			pattern_base.append(pattern)
			app.gcode.insBlocks(1, pattern_base, "pattern")
			app.refresh()
			
			#Mark pattern as island
			for bid in pattern_base:
				app.gcode.island([1])
		#Select blocks
		app.editor.selectAll()

		paths_base = []
		paths_isl = []

		points=[]

		#Compare blocks to separate island from other blocks
		for bid in app.editor.getSelectedBlocks():
			if app.gcode[bid].operationTest('island'):
				paths_isl.extend(app.gcode.toPath(bid))
				print("island:", app.gcode[bid].name() ,bid)
			else:
				paths_base.extend(app.gcode.toPath(bid))
				print("base:", app.gcode[bid].name() ,bid)
		print ("paths_isl",paths_isl)

		#Make intersection between blocks
		while len(paths_base) > 0:
			base = paths_base.pop()
			for island in paths_isl:
				#points.extend(base.intersectPath(island))
				points.extend(island.intersectPath(base))

		x=[]
		y=[]

		#Get (x,y) intersection points  
		for i in range(len(points)):
			x.append(points[i][2][0])
			y.append(points[i][2][1])

		#Save (x,y) intersection points in a matrix
		matrix=[[0 for i in range(2)] for j in range(len(x))] 

		for i in range(len(x)):
			matrix[i][0]=x[i]
			matrix[i][1]=y[i]

		#print(matrix)

		#Sort points in increasing y coordinate
		matrix.sort(key=itemgetter(1,0))

		# for i in range(len(x)):
		# 	print('puntos',matrix[i][0], matrix[i][1])

		#print(x, y)

		#Generate the gcode from points obtained
		blocks = []
#		block = Block(self.name)
		block = Block(inOut)
	
		for i in range(len(x)):
			if i == 0:
				block.append(CNC.grapid(matrix[0][0],matrix[0][1]))
				inside=0
			else:
				if inside==0:
					block.append(CNC.glinev(1,[matrix[i][0],matrix[i][1]]))
					inside=1
				else:
					block.append(CNC.grapid(matrix[i][0],matrix[i][1]))
					inside=0	


		# for i in range(len(x)):
		# 	print('puntos',x[i], y[i])

		blocks.append(block)
		app.gcode.insBlocks(-1, blocks, "Intersection2")
		app.refresh()
		app.setStatus(_("Generated Intersection2"))

##############################################

