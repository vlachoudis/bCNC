#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: Filippo Rivato
# Date: 9 November 2015
# A special thanks to Vasilis for his patient explanations

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Driller")
__version__= "0.0.7"

import math
from bmath import Vector
from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
#Driller class
#==============================================================================
class Driller:
	def __init__(self,name="Driller"):
		self.name = name

#==============================================================================
# Create holes along selected blocks
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create holes along selected blocks")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Driller"
		self.icon  = "driller"
		self.group = "CAM"

		self.variables = [
			("name",          "db",   "", _("Name")),
			("HolesDistance", "mm", 10.0, _("Distance between holes")),
			("TargetDepth",   "mm",  0.0, _("Target Depth")),
			("Peck",          "mm",  0.0, _("Peck, 0 meas None")),
			("Dwell",      "float",  0.0, _("Dwell time, 0 means None")),
		]
		self.buttons.append("exe")

	# Calc line length -----------------------------------------------------
	def calcSegmentLength(self, xyz):
		if xyz:
			p1 = xyz[0]
			p2 = xyz[1]
			return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
		else:
			return 0

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
						#exclude if fast move or z only movement
						G0 =('g0' in cmd) or ('G0' in cmd)
						Zonly = (xyz[0][0] == xyz[1][0] and xyz[0][1] == xyz[1][1])
						exclude = G0 or Zonly

						#save length for later use
						segLenth = self.calcSegmentLength(xyz)

						if len(xyz) < 3:
							bidSegments.append([xyz[0],xyz[1],exclude,segLenth])
						else:
							for i in range(len(xyz)-1):
								bidSegments.append([xyz[i],xyz[i+1],exclude,segLenth])
			#append bidSegmentes to allSegmentes
			allSegments.append(bidSegments)

		#Disabled used block
		for bid in selectedBlock:
			block = allBlocks[bid]
			if block.name() in ("Header", "Footer"): continue
			block.enable = False

		return allSegments

	# ----------------------------------------------------------------------
	def execute(self, app):
		#Get inputs
		holesDistance = self.fromMm("HolesDistance")
		targetDepth = self.fromMm("TargetDepth")
		peck = self.fromMm("Peck")
		dwell = self["Dwell"]

		zSafe = CNC.vars["safe"]

		#Check inputs
		if holesDistance <=0:
			app.setStatus(_("Driller abort: Distance must be > 0"))
			return

		if peck <0:
			app.setStatus(_("Driller abort: Peck must be >= 0"))
			return

		if dwell <0:
			app.setStatus(_("Driller abort: Dwell time >= 0, here time runs only forward!"))
			return

		# Get selected blocks from editor
		selBlocks = app.editor.getSelectedBlocks()
		if not selBlocks:
			app.editor.selectAll()
			selBlocks = app.editor.getSelectedBlocks()

		if not selBlocks:
			app.setStatus(_("Driller abort: Please select some path"))
			return

		#Get all segments from gcode
		allSegments = self.extractAllSegments(app,selBlocks)

		#Create holes locations
		allHoles=[]
		for bidSegment in allSegments:
			if len(bidSegment)==0:
				continue

			#Summ all path length
			fullPathLength = 0.0
			for s in bidSegment:
				fullPathLength += s[3]

			#Calc rest
			holes = fullPathLength // holesDistance
			rest = fullPathLength - (holesDistance * (holes))
			#Travel along the path
			elapsedLength = rest / 2.0 #equaly distribute rest, as option???
			bidHoles = []
			while elapsedLength <= fullPathLength:
				#Search best segment to apply line interpolation
				bestSegment = bidSegment[0]
				segmentsSum = 0.0
				perc = 0.0
				for s in bidSegment:
					bestSegment = s
					segmentLength = bestSegment[3]
					perc = (elapsedLength-segmentsSum) / segmentLength
					segmentsSum += segmentLength
					if segmentsSum > elapsedLength : break

				#Fist point
				x1 = bestSegment[0][0]
				y1 = bestSegment[0][1]
				z1 = bestSegment[0][2]
				#Last point
				x2 = bestSegment[1][0]
				y2 = bestSegment[1][1]
				z2 = bestSegment[1][2]

				#Check if segment is not excluded
				if not bestSegment[2]:
					newHolePoint = (x1 + perc*(x2-x1) ,
						y1 + perc*(y2-y1),
						z1 + perc*(z2-z1))
					bidHoles.append(newHolePoint)

				#Go to next hole
				elapsedLength += holesDistance

			#Add bidHoles to allHoles
			allHoles.append(bidHoles)

		#Write gcommands from allSegments to the drill block
		n = self["name"]
		if not n or n=="default": n="Driller"
		blocks = []
		block = Block(self.name)

		holesCount = 0
		for bid in allHoles:

			for xH,yH,zH in bid:
				holesCount += 1
				block.append(CNC.grapid(None,None,zH + zSafe))
				block.append(CNC.grapid(xH,yH))
				if (peck != 0) :
					z = 0
					while z > targetDepth:
							z = max(z-peck, targetDepth)
							block.append(CNC.zenter(zH + z))
							block.append(CNC.grapid(None,None,zH + zSafe))
				block.append(CNC.zenter(zH + targetDepth))
				#dwell time only on last pass
				if dwell != 0:
						block.append(CNC.gcode(4, [("P",dwell)]))

		#Gcode Zsafe on finish
		block.append(CNC.zsafe())
		blocks.append(block)

		#Insert created block
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Driller")
		app.refresh()
		app.setStatus(_("Generated Driller: %d holes")%holesCount)
