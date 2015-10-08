#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:	Filippo Rivato
# Date:	2015/10/04

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = "Flatten"
__version__= "0.0.1"

from ToolsPage import DataBase

import math
from bmath import Vector
from CNC import CNC,Block
from ToolsPage import Plugin
from fractions import gcd

#==============================================================================
#Spirograph class
#==============================================================================
class Flatten:
	def __init__(self,name="Flatten"):
		self.name = name

	#----------------------------------------------------------------------
	def make(self, XStart=0.0, YStart=0.0, FlatWidth=10., FlatHeight=10., \
			FlatDepth=0,BorderPass=False,CutDirection="Climb",PocketType="Raster"):

		#GCode Blocks
		blocks = []

		#Add Region (disabled?)
		block = Block("Region "+self.name)
		block.enable = False
		block.append(CNC.zsafe())
		xR,yR = self.RectPath(XStart,YStart,FlatWidth,FlatHeight)
		for x,y in zip(xR,yR):
			block.append(CNC.grapid(x,y))

		blocks.append(block)

		# Load tool and material settings
		toolDiam = CNC.vars['diameter']
		toolRadius = toolDiam / 2.

		#Calc tool diameter with Maximum Step Over
		StepOverInUnitMax = toolDiam * CNC.vars['stepover'] / 100.0

		#Offset for Border Cut
		BorderXStart = XStart + toolRadius
		BorderYStart = YStart + toolRadius
		BorderWidth = FlatWidth - toolDiam
		BorderHeight = FlatHeight - toolDiam
		BorderXEnd = XStart + FlatWidth - toolRadius
		BorderYEnd = XStart + FlatHeight - toolRadius

		PocketXStart = BorderXStart
		PocketYStart = BorderYStart
		PocketXEnd = BorderXEnd
		PocketYEnd = BorderYEnd

		#Calc space to work without/with border cut
		WToWork = FlatWidth - toolDiam
		HToWork = FlatHeight - toolDiam

		if(BorderPass and PocketType == "Raster"):
			PocketXStart += StepOverInUnitMax
			PocketYStart += StepOverInUnitMax
			PocketXEnd -= StepOverInUnitMax
			PocketYEnd -= StepOverInUnitMax
			WToWork -= (StepOverInUnitMax)
			HToWork -= (StepOverInUnitMax)

		#Calc points for pocketing
		xP=[]
		yP=[]

		#Raster approach
		if PocketType == "Raster":
			#Calc number of pass
			VerticalCount = (int)(HToWork / StepOverInUnitMax)
			#Calc step minor of Max step
			StepOverInUnit = HToWork / (VerticalCount +1)
			flip = False
			ActualY = PocketXStart
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

		#Offset approach
		if PocketType == "Offset":
			#Calc number of even pass
			VerticalCount = (int)(HToWork / StepOverInUnitMax)
			HorrizontalCount = (int)(WToWork / StepOverInUnitMax)
			#if (VerticalCount % 2 != 0):VerticalCount += 1
			#if (HorrizontalCount % 2 != 0):HorrizontalCount += 1
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
			count = 0
			while (xC<HorrizontalCount/2 and yC<VerticalCount/2):
				xT,yT = self.RectPath(xS, yS, wS, hS)
				if CutDirection == "Conventional":
					xT = xT[::-1]
					yT = yT[::-1]
				xP = xP + xT
				yP = yP + yT
				xS+=StepOverInUnitH
				yS+=StepOverInUnitW
				hS-=2.0*StepOverInUnitH
				wS-=2.0*StepOverInUnitW
				xC += 1
				yC += 1

			#Reverse point to start from internal (less stres tool)
			xP = xP[::-1]
			yP = yP[::-1]


		#Blocks for pocketing
		block = Block(self.name)
		block.append("(Flat Surface from X=%g Y=%g)"%(XStart,YStart))
		block.append("(W=%g x H=%g x D=%g)"%(FlatWidth,FlatHeight,FlatDepth))

		#Move safe to first point
		block.append(CNC.zsafe())
		block.append(CNC.grapid(xP[0],yP[0]))
		#Init Depth
		currDepth = 0.
		stepz = CNC.vars['stepz']
		if stepz==0 : stepz=0.001  #avoid infinite while loop

		while True:
			currDepth -= stepz
			if currDepth < FlatDepth : currDepth = FlatDepth
			block.append(CNC.zenter(currDepth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))

			for x,y in zip(xP,yP):
				block.append(CNC.gline(1,x,y))

			#Border cut if request
			if(BorderPass and PocketType == "Raster"):
				for x,y in zip(xB,yB):
					block.append(CNC.gline(1,x,y))

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
# Create a sphirograph plot
#==============================================================================
class Tool(Plugin):
	"""Create a flattening path"""
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name = "Flatten"
		self.icon = "flatten"
		w = CNC.travel_x
		h = CNC.travel_y
		self.variables = [
			("name",           "db",    "", "Name"),
			("XStart"  ,       "mm",   0.0, "X start"),
			("YStart"  ,       "mm",   0.0, "Y start"),
			("FlatWidth" ,     "mm",   30.0, "Width to flatten"),
			("FlatHeight"  ,   "mm",   25.0, "Height to flatten"),
			("FlatDepth"  ,    "mm",    0.0, "Depth to flatten"),
			("BorderPass"  , "bool",  True , "Raster border"),
			("CutDirection", "Climb,Conventional","Climb", "Cut Direction"),
			("PocketType"  , "Raster,Offset" ,"Raster", "Pocket type")
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		n = self["name"]
		if not n or n=="default": n="Flatten"
		flatten = Flatten(n)

		blocks = flatten.make(self["XStart"],
				self["YStart"],
				self["FlatWidth"],
				self["FlatHeight"],
				self["FlatDepth"],
				self["BorderPass"],
				self["CutDirection"],
				self["PocketType"]
				)

		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Flatten")
		app.refresh()
		app.setStatus("Generated flatten surface")

if __name__=="__main__":
	spirograph = Spirograph()
	spirograph.make()


