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
__version__= "0.0.10"

import os.path
import re
import math
from collections import OrderedDict
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
		Plugin.__init__(self, master, "Driller")
		self.icon  = "driller"
		self.group = "CAM"

		self.variables = [
			("name",          "db",    "",    _("Name")),
			("HolesDistance", "mm",    10.0,  _("Distance between holes")),
			("TargetDepth",   "mm",    0.0,   _("Target Depth")),
			("Peck",          "mm",    0.0,   _("Peck, 0 meas None")),
			("Dwell",         "float", 0.0,   _("Dwell time, 0 means None")),
			("useAnchor",     "bool",  False, _("Use anchor")),
			("File"  ,        "file" , "",    _("Excellon-File")),
		]
		self.buttons.append("exe")

	# Excellon Coordsconvert
	def coord2float(self, text, unitinch):
		if '.' in text: return float(text)
		if unitinch==True: return float(text)*0.0001
		#unit mm
		if len(text)==(6 if text[0]=='-' else 5): return int(text)*0.01
		if len(text)==(7 if text[0]=='-' else 6): return int(text)*0.001

	#convert to systemsetting
	def convunit(self, value, unitinch):
		if unitinch==CNC.inch: return value
		if unitinch==True and CNC.inch==False: return value*25.4
		if unitinch==False and CNC.inch: return value/25.4

	# Excellon Import
	def excellonimport(self, filename, app):
		fo = open(filename,"r")
		header = None
		current_tool = None
		incrementcoord = False
		unitinch = True
		data = {"tools":{}}
		targetDepth = self.fromMm("TargetDepth")
		for row in fo.readlines():
			line = row.strip()
			if len(line)!=0:
				if line[0]!=";":
					#read header
					if line=="M48": header = True
					if header==True:
						if (line.startswith("INCH") or line.startswith("METRIC")): unitinch = line.startswith("INCH")
						if (line=="M95" or line=="%"): header = False
						if line[0]=="T":
							#tools
							m = re.match('(T\d+)C(.+)',line)
							data["tools"][m.group(1)]={"diameter":float(m.group(2)),"holes":[]}
						if line=="ICI": incrementcoord = True
					if header==False:
						if line[0]=="T": current_tool = line
						if line[0]=="X":
							m = re.match(r'X([\d\.-]+)Y([\d\.-]+)',line)
							# convert to system
							x = self.convunit( self.coord2float(m.group(1), unitinch), unitinch)
							y = self.convunit( self.coord2float(m.group(2), unitinch), unitinch)
							if incrementcoord==True:
								if len(data["tools"][current_tool]["holes"])==0:
									prevx = 0
									prevy = 0
								else:
									prevx = data["tools"][current_tool]["holes"][-1][0]
									prevy = data["tools"][current_tool]["holes"][-1][1]
								x = x + prevx
								y = y + prevy
							data["tools"][current_tool]["holes"].append((x,y,targetDepth))

		unittext = 'inch' if CNC.inch else 'mm'
		n = self["name"]
		if not n or n=="default": n="Driller"
		holesCounter = 0
		blocks = []
		for tool in data["tools"]:
			dia = self.convunit(data["tools"][tool]["diameter"], unitinch)
			#duplicates shouldnt in the list - remove unnessesary
			blockholes = [data["tools"][tool]["holes"]]
			block,holesCount = self.create_block(blockholes ,n+" ("+str(dia)+" "+unittext+")")
			holesCounter = holesCounter+holesCount
			blocks.append(block)

		self.finish_blocks(app, blocks, holesCounter)

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
		peck = self.fromMm("Peck")
		dwell = self["Dwell"]
		useAnchor = self["useAnchor"]
		excellonFileName = self["File"]

		#Check inputs
		if holesDistance <=0 and useAnchor == False:
			app.setStatus(_("Driller abort: Distance must be > 0"))
			return

		if peck <0:
			app.setStatus(_("Driller abort: Peck must be >= 0"))
			return

		if dwell <0:
			app.setStatus(_("Driller abort: Dwell time >= 0, here time runs only forward!"))
			return

		if excellonFileName != "":
			if os.path.isfile(excellonFileName):
				self.excellonimport(excellonFileName, app)
			else:
				app.setStatus(_("Driller abort: Excellon-File not a file"))
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

			if useAnchor == True:
				bidHoles = []
				for idx, anchor in enumerate(bidSegment):
					if idx > 0:
						newHolePoint = (anchor[0][0],anchor[0][1],anchor[0][2])
						bidHoles.append(newHolePoint)
			else:
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
			#remove duplicates
			bidHoles = list(OrderedDict.fromkeys(bidHoles))
			#Add bidHoles to allHoles
			allHoles.append(bidHoles)

		#Write gcommands from allSegments to the drill block
		blocks = []
		n = self["name"]
		if not n or n=="default": n="Driller"
		block,holesCount = self.create_block(allHoles,n)
		blocks.append(block)
		self.finish_blocks(app, blocks, holesCount)

	#Write gcommands from allHoles to the drill block
	def create_block(self, holes, name):
		targetDepth = self.fromMm("TargetDepth")
		peck = self.fromMm("Peck")
		dwell = self["Dwell"]
		block = Block(name)
		holesCount = 0
		for bid in holes:
			for xH,yH,zH in bid:
				holesCount += 1
				block.append(CNC.zsafe())
				block.append(CNC.grapid(xH,yH))
				if (peck != 0) :
					z = 0
					while z > targetDepth:
						z = max(z-peck, targetDepth)
						block.append(CNC.zenter(zH + z))
						block.append(CNC.zsafe())
				block.append(CNC.zenter(zH + targetDepth))
				#dwell time only on last pass
				if dwell != 0:
					block.append(CNC.gcode(4, [("P",dwell)]))
		#Gcode Zsafe on finish
		block.append(CNC.zsafe())
		return (block,holesCount)

	#Insert created blocks
	def finish_blocks(self, app, blocks, numberholes):
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Driller")
		app.refresh()
		app.setStatus(_("Generated Driller: %d holes")%numberholes)
