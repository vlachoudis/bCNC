#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("Trochoidal")
__version__ = "0.0.2"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

class Tool(Plugin):
	__doc__ = _("""Trochoidal g-code postprocessor""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Trochoidal")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "helical"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("cw"    ,    "bool" ,    True, _("Clockwise")),
			("circ"    ,    "bool" ,    False, _("Circular")),
			("evenspacing"    ,    "bool" ,    True, _("Even spacing across segment")),
			("entry"    ,    "bool" ,    False, _("Trochoid entry (prepare for helicut)")),
			("rdoc"    ,    "mm" ,    "0.2", _("Radial depth of cut (<= cutter D * 0.4)")),
			("dia"    ,    "mm" ,    "3", _("Trochoid diameter (<= cutter D)")),
			("feed"    ,    "mm" ,    "2000", _("Feedrate"))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		feed = self["feed"]
		rdoc = self["rdoc"]
		radius = self["dia"]/2
		cw = self["cw"]
		circ = self["circ"]
		evenspacing = self["evenspacing"]

		if cw: cwtext = 'cw'
		else: cwtext = 'ccw'

		if cw: arcg = 'g2'
		else: arcg = 'g3'

		#print("go!")
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			#print(blocks[bid])
			path = app.gcode.toPath(bid)[0]
			#print(path)

			block = Block("trochoid "+cwtext+" "+str(radius*2)+"+"+str(rdoc))
			block.append("F"+str(feed))

			entry = self["entry"]

			A=path[0].A
			block.append("g0 x"+str(A[0])+" y"+str(A[1]))
			block.append("G1 Z0")
			for segment in path:
				#print(segment.A)
				#block.append("g0 x0 y0")
				#block.append("g1 x10 y10")
				#block.append("g1 x20 y10")
				#block.append("g0 x0 y0")
				if entry:
					eblock = Block("trochoid-in")
					eblock.append("G0 Z0")
					eblock.append("G0 x"+str(segment.A[0])+" y"+str(segment.A[1]-radius))
					eblock.append("G2 x"+str(segment.A[0])+" y"+str(segment.A[1]-radius)+" i"+str(0)+" j"+str(radius))
					blocks.append(eblock)
					entry = False

				#Continuity BEGINING
				block.append("g1 x"+str(segment.A[0])+" y"+str(segment.A[1]))
				#block.append(arcg+" x"+str(segment.A[0])+" y"+str(segment.A[1])+" r"+str(radius/2))

				phi = atan2(segment.B[1]-segment.A[1], segment.B[0]-segment.A[0])

				#TODO: handle arc segments
				#if segment.type == Segment.LINE:
				#if segment.type in (Segment.CW, Segment.CCW):

				#Compensate for uneven spacing
				srdoc = rdoc
				if evenspacing:
					subsegs = segment.length()//rdoc
					remainder = segment.length()%rdoc
					if remainder != 0:
						srdoc = segment.length()/(subsegs+1)

				#Loop over subsegmnents of segment
				i=0
				while i<(segment.length()+srdoc):
					pos=min(segment.length(), i)

					B = segment.distPoint(pos)
					block.extend(self.trochoid(A,B,radius,cw,circ))
					A = B

					i+=srdoc

				#Continuity END
				#block.append("g1 x"+str(segment.B[0])+" y"+str(segment.B[1]))
				block.append(arcg+" x"+str(segment.B[0])+" y"+str(segment.B[1])+" r"+str(radius/2))

			blocks.append(block)


		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Trochoidal created") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Trochoidal"))                           #<<< feed back result
		#app.gcode.blocks.append(block)


	#Convert polar to cartesian and add that to existing vector
	def pol2car(self, r, phi, a=[0,0]):
		return [round(a[0]+r*cos(phi),4),round(a[1]+r*sin(phi),4)]

	#Generate single trochoidal element between two points
	def trochoid(self, A, B, radius, cw=True, circular=False):
		block = []

		if cw:
			u = 1
			arc = "G2"
		else:
			u = -1
			arc = "G3"


		phi = atan2(B[1]-A[1], B[0]-A[0])
		step = sqrt((A[0]-B[0])**2+(A[1]-B[1])**2)

		l = self.pol2car(radius, phi+radians(90*u))
		r = self.pol2car(radius, phi+radians(-90*u))
		al = self.pol2car(radius, phi+radians(90*u), A)
		ar = self.pol2car(radius, phi+radians(-90*u), A)
		bl = self.pol2car(radius, phi+radians(90*u), B)
		br = self.pol2car(radius, phi+radians(-90*u), B)

		# This schematic drawing represents naming convention
		# of points and vectors calculated in previous block
		#
		#    <--L---
		#          ---R-->
		#
		#        *   *
		#     *         *
		#    *           *
		#   BL     B     BR
		#    *           *
		#    *     ^     *
		#    *     |     *
		#    *     |     *
		#    *           *
		#   AL     A     AR
		#    *           *
		#     *         *
		#        *   *

		#TODO: improve strategies
		if circular:
			block.append("g1 x"+str(al[0])+" y"+str(al[1]))
			block.append("g1 x"+str(bl[0])+" y"+str(bl[1]))
			block.append(arc+" x"+str(bl[0])+" y"+str(bl[1])+" i"+str(r[0])+" j"+str(r[1]))
		else:
			#block.append(arc+" x"+str(al[0])+" y"+str(al[1])+" r"+str(radius/2))
			block.append("g1 x"+str(al[0])+" y"+str(al[1]))
			block.append("g1 x"+str(bl[0])+" y"+str(bl[1]))
			block.append(arc+" x"+str(br[0])+" y"+str(br[1])+" i"+str(r[0])+" j"+str(r[1]))
			block.append("g1 x"+str(ar[0])+" y"+str(ar[1]))
			block.append(arc+" x"+str(al[0])+" y"+str(al[1])+" i"+str(l[0])+" j"+str(l[1]))
			block.append("g1 x"+str(bl[0])+" y"+str(bl[1]))

		return block
