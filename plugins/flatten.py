#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date:	2015/10/04

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Flatten")
__version__= "0.0.2"

import math
from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
#Flatten class
#==============================================================================
class Flatten:
	def __init__(self,name="Flatten"):
		self.name = name

	#----------------------------------------------------------------------
	def make(self,app, XStart=0.0, YStart=0.0, FlatWidth=10., FlatHeight=10., \
			FlatDepth=0, BorderPass=False, CutDirection="Climb", PocketType="Raster"):

		#GCode Blocks
		blocks = []

		#Check parameters
		if CutDirection is "":
			app.setStatus(_("Flatten abort: Cut Direction is undefined"))
			return

		if PocketType is "":
			app.setStatus(_("Flatten abort: Pocket Type is undefined"))
			return

		if FlatWidth <= 0 or FlatHeight <= 0 :
			app.setStatus(_("Flatten abort: Flatten Area dimensions must be > 0"))
			return

		if FlatDepth > 0 :
			app.setStatus(_("Flatten abort: Hey this is only for subtractive machine! Check depth!"))
			return

		#Add Region disabled to show worked area
		block = Block(self.name + " Outline")
		block.enable = False
		block.append(CNC.zsafe())
		xR,yR = self.RectPath(XStart,YStart,FlatWidth,FlatHeight)
		for x,y in zip(xR,yR):
			block.append(CNC.gline(x,y))
		blocks.append(block)

		# Load tool and material settings
		toolDiam = CNC.vars['diameter']
		toolRadius = toolDiam / 2.

		#Calc tool diameter with Maximum Step Over allowed
		StepOverInUnitMax = toolDiam * CNC.vars['stepover'] / 100.0

		#Offset for Border Cut
		BorderXStart = XStart + toolRadius
		BorderYStart = YStart + toolRadius
		BorderWidth = FlatWidth - toolDiam
		BorderHeight = FlatHeight - toolDiam
		BorderXEnd = XStart + FlatWidth - toolRadius
		BorderYEnd = YStart + FlatHeight - toolRadius

		PocketXStart = BorderXStart
		PocketYStart = BorderYStart
		PocketXEnd = BorderXEnd
		PocketYEnd = BorderYEnd

		#Calc space to work with/without border cut
		WToWork = FlatWidth - toolDiam
		HToWork = FlatHeight - toolDiam

		if(WToWork < toolRadius or HToWork < toolRadius):
			app.setStatus(_("Flatten abort: Flatten area is too small for this End Mill."))
			return

		#Prepare points for pocketing
		xP=[]
		yP=[]
        #and border
		xB=[]
		yB=[]

        #---------------------------------------------------------------------
        #Raster approach
		if PocketType == "Raster":
			#Correct sizes if border is used
			if(BorderPass):
				PocketXStart += StepOverInUnitMax
				PocketYStart += StepOverInUnitMax
				PocketXEnd -= StepOverInUnitMax
				PocketYEnd -= StepOverInUnitMax
				WToWork -= (StepOverInUnitMax)
				HToWork -= (StepOverInUnitMax)

			#Calc number of pass
			VerticalCount = (int)(HToWork / StepOverInUnitMax)
			#Calc step minor of Max step
			StepOverInUnit = HToWork / (VerticalCount +1)
			flip = False
			ActualY = PocketYStart
			#Zig zag
			if StepOverInUnit==0 : StepOverInUnit=0.001  #avoid infinite while loop
			while (True):
				#Zig
				xP.append(self.ZigZag(flip,PocketXStart,PocketXEnd))
				yP.append(ActualY)
				flip = not flip
				#Zag
				xP.append(self.ZigZag(flip,PocketXStart,PocketXEnd))
				yP.append(ActualY)
				if(ActualY >= PocketYEnd - StepOverInUnitMax + StepOverInUnit):
					break
				#Up
				ActualY += StepOverInUnit
				xP.append(self.ZigZag(flip,PocketXStart,PocketXEnd))
				yP.append(ActualY)

			#Points for border cut depends on Zig/Zag end
			if(BorderPass):
				if flip:
					xB,yB = self.RectPath(BorderXStart,BorderYEnd,BorderWidth,-BorderHeight)
				else:
					xB,yB = self.RectPath(BorderXEnd,BorderYEnd,-BorderWidth,-BorderHeight)

				#Reverse in case of Climb
				if CutDirection == "Climb":
					xB = xB[::-1]
					yB = yB[::-1]

		#---------------------------------------------------------------------
        #Offset approach
		if PocketType == "Offset":
			#Calc number of pass
			VerticalCount = (int)(HToWork / StepOverInUnitMax)
			HorrizontalCount = (int)(WToWork / StepOverInUnitMax)
			#Make them odd
			if VerticalCount%2 == 0 : VerticalCount += 1
			if HorrizontalCount%2 == 0 : HorrizontalCount += 1
			#Calc step minor of Max step
			StepOverInUnitH = HToWork / (VerticalCount)
			StepOverInUnitW = WToWork / (HorrizontalCount)

			#Start from border to center
			xS = PocketXStart
			yS = PocketYStart
			wS = WToWork
			hS = HToWork
			xC = 0
			yC = 0
			while (xC<=HorrizontalCount/2 and yC<=VerticalCount/2):
				#Pocket offset points
				xO,yO = self.RectPath(xS, yS, wS, hS)
				if CutDirection == "Conventional":
					xO = xO[::-1]
					yO = yO[::-1]

				xP = xP + xO
				yP = yP + yO
				xS+=StepOverInUnitH
				yS+=StepOverInUnitW
				hS-=2.0*StepOverInUnitH
				wS-=2.0*StepOverInUnitW
				xC += 1
				yC += 1

			#Reverse point to start from inside (less stres on the tool)
			xP = xP[::-1]
			yP = yP[::-1]

		#Blocks for pocketing
		block = Block(self.name)
		block.append("(Flatten from X=%g Y=%g)"%(XStart,YStart))
		block.append("(W=%g x H=%g x D=%g)"%(FlatWidth,FlatHeight,FlatDepth))
		block.append("(Approach: %s %s)" % (PocketType,CutDirection))
		if BorderPass : block.append("(with border)")

		#Move safe to first point
		block.append(CNC.zsafe())
		block.append(CNC.grapid(xP[0],yP[0]))
		#Init Depth
		currDepth = 0.
		stepz = CNC.vars['stepz']
		if stepz==0 : stepz=0.001  #avoid infinite while loop

		#Create GCode from points
		while True:
			currDepth -= stepz
			if currDepth < FlatDepth : currDepth = FlatDepth
			block.append(CNC.zenter(currDepth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))

			#Pocketing
			for x,y in zip(xP,yP):
				block.append(CNC.gline(x,y))

			#Border cut if request
			for x,y in zip(xB,yB):
				block.append(CNC.gline(x,y))

			#Verify exit condition
			if currDepth <= FlatDepth : break

			#Move to the begin in a safe way
			block.append(CNC.zsafe())
			block.append(CNC.grapid(xP[0],yP[0]))

		#Zsafe
		block.append(CNC.zsafe())
		blocks.append(block)
		return blocks

	#----------------------------------------------------------------------
	def RectPath(self,x,y,w,h):
		xR = []
		yR = []
		xR.append(x)
		yR.append(y)
		xR.append(x + w)
		yR.append(y)
		xR.append(x + w)
		yR.append(y + h)
		xR.append(x)
		yR.append(y + h)
		xR.append(x)
		yR.append(y)
		return (xR,yR)

	#----------------------------------------------------------------------
	def ZigZag(self,flip,zig,zag):
		if flip:
			return zig
		else:
			return zag

#==============================================================================
# Create a flatten surface
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Flatten an area in different ways")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Flatten"
		self.icon  = "flatten"
		self.group = "CAM"
		self.variables = [
			("name",           "db",    "", _("Name")),
			("XStart"  ,       "mm",   0.0, _("X start")),
			("YStart"  ,       "mm",   0.0, _("Y start")),
			("FlatWidth" ,     "mm",   30.0, _("Width to flatten")),
			("FlatHeight"  ,   "mm",   20.0, _("Height to flatten")),
			("FlatDepth"  ,    "mm",    0.0, _("Depth to flatten")),
			("BorderPass"  , "bool",  True , _("Raster border")),
			("CutDirection", "Climb,Conventional","Climb", _("Cut Direction")),
			("PocketType"  , "Raster,Offset" ,"Raster", _("Pocket type"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		n = self["name"]
		if not n or n=="default": n="Flatten"
		flatten = Flatten(n)

		blocks = flatten.make(app,
				self.fromMm("XStart"),
				self.fromMm("YStart"),
				self.fromMm("FlatWidth"),
				self.fromMm("FlatHeight"),
				self.fromMm("FlatDepth"),
				self["BorderPass"],
				self["CutDirection"],
				self["PocketType"]
				)

		if blocks is not None:
			active = app.activeBlock()
			if active==0: active=1
			app.gcode.insBlocks(active, blocks, "Flatten")
			app.refresh()
			app.setStatus(_("Flatten: Generated flatten surface"))
