#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("Trochoidal")

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from numpy import deg2rad

class Tool(Plugin):
	__doc__ = _("""Trochoidal g-code postprocessor""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Trochoidal")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "helical"			#<<< This is the name of gif file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("cw"    ,    "bool" ,    True, _("Clockwise")),
			("rdoc"    ,    "mm" ,    "0.2", _("Radial depth of cut (<= cutter D * 0.4)")),
			("dia"    ,    "mm" ,    "3", _("Trochoid diameter (<= cutter D)"))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button 
	# ----------------------------------------------------------------------
	def execute(self, app):
		rdoc = self["rdoc"]
		radius = self["dia"]/2
		cw = self["cw"]

		#print("go!")
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			#print(blocks[bid])
			path = app.gcode.toPath(bid)[0]
			#print(path)

			block = Block("trochoid")

			for segment in path:
				#print(segment.A)
				#block.append("g0 x0 y0")
				#block.append("g1 x10 y10")
				#block.append("g1 x20 y10")
				#block.append("g0 x0 y0")
				block.extend(self.trochoid(segment, rdoc, radius, cw))

			blocks.append(block)


		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Trochoidal created") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Trochoidal"))                           #<<< feed back result
		#app.gcode.blocks.append(block)


	def pol2car(self, r, phi, a=[0,0]):
		return [round(a[0]+r*cos(phi),4),round(a[1]+r*sin(phi),4)]

	def trochoid(self, segment, step, radius, cw=True):
		#TODO: handle arc segments

		block = []

		if cw:
			u = 1
			arc = "G2"
		else:
			u = -1
			arc = "G3"

		phi = atan2(segment.B[1]-segment.A[1], segment.B[0]-segment.A[0])

		i=0
		while i<(segment.length()+step):
			pos=min(segment.length(), i)

			c = self.pol2car(pos, phi, segment.A)
			d = self.pol2car(radius, phi+deg2rad(90*u), c)
			ij = self.pol2car(radius, phi+deg2rad(-90*u))

			block.append("g1 x"+str(d[0])+" y"+str(d[1]))
			block.append(arc+" x"+str(d[0])+" y"+str(d[1])+" i"+str(ij[0])+" j"+str(ij[1]))

			i+=step
		return block
