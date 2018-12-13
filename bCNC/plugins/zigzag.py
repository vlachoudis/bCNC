#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: @CarlosGS
# Date:	2-Jan-2017

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Carlos Garcia Saura"
__email__  = "@CarlosGS"

__name__ = _("Zig-Zag")
__version__= "0.0.1"

import math
from CNC import CNC,Block
from ToolsPage import Plugin


#==============================================================================
# ZigZag class
#==============================================================================
class ZigZag:
	def __init__(self,name="ZigZag"):
		self.name = name

	#----------------------------------------------------------------------
	def zigzag(self, Nlines, LineLen, StartEndLen, Step, CornerRes):
		points = []
		x = 0.
		y = -StartEndLen
		points.append((x,y))

		def is_even(num): return (num%2) == 0

		for i in range(Nlines):
			goingUp = is_even(i)
			if i > 0 and CornerRes > 0:
				r = Step/2
				centerX = x + r
				centerY = y
				for j in range(CornerRes):
					y = centerY + r * math.sin(math.pi*(j+1)/CornerRes) * (-1 if goingUp else 1)
					x = centerX - r * math.cos(math.pi*(j+1)/CornerRes)
					points.append((x,y))
			y = LineLen * goingUp
			x = Step * i
			points.append((x,y))

		if goingUp:
			y = LineLen + StartEndLen
		else:
			y = -StartEndLen

		points.append((x,y))
		if is_even(Nlines): points.append((0,-StartEndLen)) # close the path
		return points

	#----------------------------------------------------------------------
	def make(self, Nlines, LineLen, StartEndLen, Step, CornerRes, Depth):
		blocks = []
		block = Block(self.name)

		points = self.zigzag(Nlines, LineLen, StartEndLen, Step, CornerRes)

		block.append(CNC.zsafe())
		block.append(CNC.grapid(points[0][0],points[0][1]))

		currDepth = 0.
		stepz = CNC.vars['stepz']
		if stepz==0 : stepz=0.001  #avoid infinite while loop

		while True:
			currDepth -= stepz
			if currDepth < Depth : currDepth = Depth
			block.append(CNC.zenter(currDepth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
			for (x,y) in points:
				block.append(CNC.gline(x,y))
			if currDepth <= Depth : break

		block.append(CNC.zsafe())
		blocks.append(block)
		return blocks


#==============================================================================
# Create a ZigZag path
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create a Zig-Zag path")

	def __init__(self, master):
		Plugin.__init__(self, master, "Zig-Zag")
		self.icon  = "zigzag"
		self.group = "Artistic"
		self.variables = [
			("name",        "db",  "",   _("Name")),
			("Nlines",      "int", 34,   _("Number of lines")),
			("LineLen",     "mm",  33.,  _("Line length")),
			("StartEndLen", "mm",   5.,  _("Additional length at start/end")),
			("Step",        "mm",   1.,  _("Step distance")),
			("CornerRes",   "int",  5,   _("Corner resolution")),
			("Depth",       "mm",  -0.1, _("Depth"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		name = self["name"]
		if not name or name=="default": name="Zig-Zag"
		Z = ZigZag(name)

		Nlines = self["Nlines"]
		LineLen = self.fromMm("LineLen")
		StartEndLen = self.fromMm("StartEndLen")
		Step = self.fromMm("Step")
		CornerRes = self["CornerRes"]
		Depth = self.fromMm("Depth")

		#Check parameters
		if Nlines <=0:
			app.setStatus(_("Zig-Zag abort: verify Nlines > 0"))
			return

		if LineLen <=0:
			app.setStatus(_("Zig-Zag abort: verify LineLen > 0"))
			return

		if Step <=0:
			app.setStatus(_("Zig-Zag abort: verify Step > 0"))
			return

		if CornerRes <0:
			app.setStatus(_("Zig-Zag abort: verify CornerRes >= 0"))
			return

		if Depth >0:
			app.setStatus(_("Zig-Zag abort: depth must be minor or equal to zero"))
			return

		blocks = Z.make(Nlines, LineLen, StartEndLen, Step, CornerRes, Depth)

		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Zig-Zag")
		app.refresh()
		app.setStatus(_("Generated: Zig-Zag"))
