#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: Mario Basz
#mariob_1960@yahoo.com.ar
# Date: 20 may 2018
# A special thanks to Vasilis Viachoudis, Filippo Rivato and Buschhardt
#This plugin is based on a variation
# of yours Driller plugin and My_Plugin example.

from __future__ import absolute_import
from __future__ import print_function

__author__ = "Mario S Basz"
__email__  = "mariob_1960@yaho.com.ar"

__name__ = _("Scaling")
__version__= "0.6"

import os.path
import re
import math
from collections import OrderedDict
from CNC import CNC,Block
from ToolsPage import Plugin
from bmath import pi
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod, tan

#==============================================================================
# Scaling selected block
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Scaling the selected block")
	def __init__(self, master):
		Plugin.__init__(self, master, "Scaling")
		self.icon  = "scale"
		self.group = "CAM"

		self.variables = [
			("name"	  ,"db",    "",   _("Name")),
            ("xscale" ,"float", "",   _("X Scale")),
            ("yscale" ,"float", "",   _("Y Scale")),
            ("zscale" ,"float", "",   _("Z Scale")),
            ("centered" ,"bool" , 0,    _("X Y Center")),
			("feed"	  , "int" , 1200, _("Feed")),
			("zfeed"  , "int" ,""   , _("Plunge Feed")),
			("rpm"	  , "int" ,12000, _("RPM"))
		]
		self.buttons.append("exe")
	# -----------------------------------------------------
	def scaling(self,xyz,center,xscale,yscale,zscale):
		safe = CNC.vars["safe"]

		A = xyz[0]
		B = xyz[1]
#		xlength = B[0]-A[0]
#		ylength = B[1]-A[1]
#		zlength = B[2]-A[2]
		xnew=(B[0]-center[0])*xscale+center[0]
		ynew=(B[1]-center[1])*yscale+center[1]
		znew=min(B[2]*zscale,safe)

		dxy=sqrt(((B[0]-A[0])*xscale)**2+((B[1]-A[1])*yscale)**2)
		dz=(B[2]-A[2])*zscale
		return xnew,ynew,znew,dxy,dz

	# Calc subsegments -----------------------------------------------------
	def calcSegmentLength(self, xyz):
		if xyz:
			A = xyz[0]
			B = xyz[1]
			seglength_x = B[0]-A[0]
			seglength_y = B[1]-A[1]
			seglength_z = B[2]-A[2]
			return math.sqrt(seglength_x**2 + seglength_y**2 + seglength_z**2)
		else:
			return 0
	# ----------------------------------------------------------------------

	#Extract all segments from commands ------------ -----------------------
	def extractAllSegments(self, app,selectedBlock):
		allSegments = []
		allBlocks = app.gcode.blocks

		for bid in selectedBlock:
			bidSegments = []
			block = allBlocks[bid]
			if block.name() in ("Header", "Footer"): continue
			#if not block.enable : continue
			app.gcode.initPath(bid)
			for line in block:
				try:
					cmd = app.cnc.breakLine(app.gcode.evaluate(app.cnc.compileLine(line)))
				except:
					cmd = None

				if cmd:
					app.cnc.motionStart(cmd)
					xyz = app.cnc.motionPath()
					app.cnc.motionEnd()
					if xyz:
					#coment its?
#-----------------------------------------------------------------------------------------
						#exclude if fast move or z only movement
						G0 =('g0' in cmd) or ('G0' in cmd)
						Zonly = (xyz[0][0] == xyz[1][0] and xyz[0][1] == xyz[1][1])
						exclude = Zonly
#-----------------------------------------------------------------------------------------

						#save length for later use
						segLength = self.calcSegmentLength(xyz)
						if len(xyz) < 3:
							bidSegments.append([xyz[0],xyz[1],exclude,segLength])
						else:
							for i in range(len(xyz)-1):
								bidSegments.append([xyz[i],xyz[i+1],exclude,segLength])
			#append bidSegmentes to allSegmentes
			allSegments.append(bidSegments)

		#Disabled used block
		for bid in selectedBlock:
			block = allBlocks[bid]
			if block.name() in ("Header", "Footer"): continue
			block.enable = False

		return allSegments,block.name()

	# ----------------------------------------------------------------------
	def execute(self, app):
		# info =xnew,ynew,znew,dxy,dz

		xscale= self["xscale"]
		if xscale=="":xscale=1
		yscale= self["yscale"]
		if yscale=="":yscale=1
		zscale= self["zscale"]
		if zscale=="":zscale=1

		surface = CNC.vars["surface"]
		if zscale>0:
			surface*=zscale

		feed = self["feed"]
		zfeed = CNC.vars["cutfeedz"]
		rpm = self["rpm"]
		if self["zfeed"]:
				zfeed = self["zfeed"]

		#zup = self["zup"]


		centered = self["centered"]

#		zbeforecontact=surface+CNC.vars["zretract"]
#		hardcrust = surface - CNC.vars["hardcrust"]
#		feedbeforecontact = CNC.vars["feedbeforecontact"]/100.0
#		hardcrustfeed = CNC.vars["hardcrustfeed"]/100.0

		# Get selected blocks from editor

		selBlocks = app.editor.getSelectedBlocks()
		if not selBlocks:
			app.setStatus(_("Scaling abort: Please select some path"))
			return 
		elements=len(app.editor.getSelectedBlocks())
		print("elements",elements)
		for bid in app.editor.getSelectedBlocks():
				if len(app.gcode.toPath(bid)) < 1: continue
				path = app.gcode.toPath(bid)[0]
				if centered:
					center = path.center()
				else:
					center=0,0
		print ("center",center[0],center[1])
	#	if elements>=2:
	#		center=0,0


		#Get all segments from gcode
		allSegments = self.extractAllSegments(app,selBlocks)[0]
		name_block = self.extractAllSegments(app,selBlocks)[1]
#		num_block = self.extractAllSegments(app,selBlocks)[2]

		#Create holes locations
		all_blocks=[]
		for bidSegment in allSegments:
			if len(bidSegment)==0:
				continue
	#		all_blocks = []
			n = self["name"]
	#		if not n or n=="default": n="Trochoidal_3D"
			if elements>1:
				n="scale "
			else:
				if centered:
					n="center scale "+str(name_block)
				else:
					n="scale "+str(name_block)
			bid_block = Block(n)

			for idx, segm in enumerate(bidSegment):
	#			if idx >= 0:
	#			bid_block.append("(idx "+str(idx)+" -------------- )")
				info=self.scaling(segm,center,xscale,yscale,zscale)
				if idx == 0:
					bid_block.append("(---- Scale (x "+str(xscale)+" : 1.0),(y "+str(yscale)+" : 1.0),(z "+str(zscale)+" : 1.0) ---- )")
					bid_block.append("(center "+str(center[0])+" ,"+str(center[1])+" )")
					bid_block.append("M03")
					bid_block.append("S "+str(rpm))
					bid_block.append(CNC.zsafe())
					bid_block.append("F "+str(zfeed))
					bid_block.append("g0 x "+str(info[0])+" y "+str(info[1]))
					currentfeed=oldfeed=zfeed
				else:
				#	if B[5]>=0: #<< zsign
				#		currentfeed=feed
				#	else:
					#relationship
					if info[4]>=0:
						currentfeed=feed
					else:
						rel=info[3]/(info[3]+abs(info[4])) 
						currentfeed=int(rel*feed+(1-rel)*zfeed)

					if segm[0][2]> surface and segm[1][2]>=surface:
						bid_block.append("g0 x "+str(info[0])+" y "+str(info[1])+ " z "+str(info[2]))
					else:
						if currentfeed!=oldfeed:
							bid_block.append("F "+str(currentfeed))
						bid_block.append("g1 x "+str(info[0])+" y "+str(info[1])+ " z "+str(info[2]))
					oldfeed=currentfeed

			bid_block.append(CNC.zsafe()) 			#<<< Move rapid Z axis to the safe height in Stock Material
			all_blocks.append(bid_block)
#			print "bid", bid_block.name(), bid_block,"*****************"
		self.finish_blocks(app, all_blocks,elements)
	#--------------------------------------------------------------


	#Insert created blocks
	def finish_blocks(self, app, blocks,elements):
		active = app.activeBlock()
#		if active==0: active=1
		if elements>1:
			active=-2
		app.gcode.insBlocks(active+1, blocks, "scale ")
		app.refresh()
		app.setStatus(_("Scaling Generated"))
