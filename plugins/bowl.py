#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	https://github.com/carlosgs
# Date:	14-Sep-2015

__author__ = "Carlos Garcia Saura"
__email__  = ""
__name__   = _("Bowl")

import math
from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
# Bowl class
#==============================================================================
class Bowl:
	def __init__(self, name):
		self.name = name

	#----------------------------------------------------------------------
	# r       = sphere radius
	# res     = pressure angle
	# pocket  = progressive (carves the sphere pocketing each layer)
	#----------------------------------------------------------------------
	def calc(self, D, res, pocket):
		blocks = []
		block = Block(self.name)

		# Load tool and material settings
		toolDiam = CNC.vars['diameter']
		toolRadius = toolDiam/2.
		stepz  = CNC.vars['stepz']
		stepxy = toolDiam*(CNC.vars['stepover']/100.)

		if toolDiam <= 0 or stepxy <= 0 or stepz <= 0 or D <= 0 or res <= 0:
			return blocks

		currDepth = 0.

		def setCutFeedrate():
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))

		def addCircumference(radius):
			block.append(CNC.garc(2,radius, 0., i=-radius))

		# Mills a circle, pocketing it if needed
		def addSingleCircle(radius, depth):
			if pocket:
				block.append(CNC.grapid(0., 0.))
				block.append(CNC.zenter(depth))
				setCutFeedrate()
				currRadius = 0.
				while radius > currRadius+stepxy:
					currRadius += stepxy
					block.append(CNC.gline(currRadius, 0))
					addCircumference(currRadius)
				if radius-currRadius > 0:
					block.append(CNC.gline(radius, 0))
					addCircumference(radius)
			else:
				block.append(CNC.grapid(radius, 0.))
				block.append(CNC.zenter(depth))
				setCutFeedrate()
				addCircumference(radius)

		# Mills a circle in steps of height "stepz"
		def addCircle(radius, depth, currDepth):
			while depth < currDepth-stepz:
				currDepth -= stepz
				addSingleCircle(radius, currDepth)
			if currDepth-depth > 0:
				addSingleCircle(radius, depth)
			return depth

		block.append(CNC.zsafe())
		r = D/2.
		r -= toolRadius # Removes offset of ball-end tool
		angleInc = res
		currAngle = 0.
		angle = math.pi/2. # 90 degrees
		while angle > currAngle+angleInc:
			currAngle += angleInc
			radius = r * math.cos(-currAngle)
			depth  = r * math.sin(-currAngle) - toolRadius # Removes vertical offset (centers the ball tool in Z=0, rather than the tip)
			currDepth = addCircle(radius, depth, currDepth)
		if angle-currAngle > 0:
			radius = r * math.cos(-angle)
			depth  = r * math.sin(-angle) - toolRadius
			currDepth = addCircle(radius, depth, currDepth)

		blocks.append(block)
		return blocks

#==============================================================================
# Create a simple Bowl
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Generate a bowl cavity")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Bowl"
		self.group = "Generator"
		self.icon  = "bowl"
		self.variables = [
			("name",      "db",     "",  _("Name")),
			("D",         "mm",   30.0,  _("Diameter")),
			("res",    "float",   10.0,  _("Resolution (degrees)")),
			("pocket",    "bool",    1,  _("Progressive"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		n = self["name"]
		if not n or n=="default": n="Bowl"
		bowl = Bowl(n)
		blocks = bowl.calc(self.fromMm("D"), math.radians(self["res"]), self["pocket"])
		if len(blocks) > 0:
			active = app.activeBlock()
			if active==0: active=1
			app.gcode.insBlocks(active, blocks, "Create BOWL")
			app.refresh()
			app.setStatus(_("Generated: BOWL"))
		else:
			app.setStatus(_("Error: Check the Bowl and End Mill parameters"))
