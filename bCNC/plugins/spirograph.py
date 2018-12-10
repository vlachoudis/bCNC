#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date:	26 September 2015
# special thanks to my wonderful wife Giulia.

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Spirograph")
__version__= "0.0.1"

import math
from CNC import CNC,Block
from ToolsPage import Plugin
from fractions import gcd


#==============================================================================
#Spirograph class
#==============================================================================
class Spirograph:
	def __init__(self,name="Spirograph"):
		self.name = name

	#----------------------------------------------------------------------
	def lcm(self,x,y):
		return (x*y)/gcd(x,y)

	#----------------------------------------------------------------------
	def calc_dots(self,resolution=2*math.pi/360):
		def x():
			return (self.RExt - self.RInt) * math.cos( self.theta ) +\
         self.ROff * math.cos( (self.RExt - self.RInt) / self.RInt * self.theta )

		def y():
			return (self.RExt - self.RInt) * math.sin( self.theta ) -\
         self.ROff * math.sin( (self.RExt - self.RInt) / self.RInt * self.theta )

		while self.theta < (2*self.PI * self.Spins):
			yield (x(), y())
			self.theta += resolution

	#----------------------------------------------------------------------
	def make(self,RExt=50., RInt=33., ROff=13. , Depth=0):
		self.RExt = RExt
		self.RInt = RInt
		self.ROff = ROff

		if RExt>RInt :
			self.Spins = self.lcm(RExt,RInt) / max(RExt,RInt)
		else:
			self.Spins = self.lcm(RExt,RInt) / min(RExt,RInt)

		self.Depth = Depth
		self.PI = math.pi
		self.theta = 0.0

		blocks = []
		block = Block(self.name)

		block.append("(External Radius = %g)"%(self.RExt))
		block.append("(Internal Radius = %g)"%(self.RInt))
		block.append("(Offset Radius = %g)"%(self.ROff))

		xi,yi = zip(*(self.calc_dots()))

		block.append(CNC.zsafe())
		block.append(CNC.grapid(xi[0],yi[0]))

		currDepth = 0.
		stepz = CNC.vars['stepz']
		if stepz==0 : stepz=0.001  #avoid infinite while loop

		while True:
			currDepth -= stepz
			if currDepth < self.Depth : currDepth = self.Depth
			block.append(CNC.zenter(currDepth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
			for x,y in zip(xi,yi):
				block.append(CNC.gline(x,y))
			block.append(CNC.gline(xi[0],yi[0]))
			if currDepth <= self.Depth : break

		block.append(CNC.zsafe())
		blocks.append(block)
		return blocks


#==============================================================================
# Create a sphirograph plot
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create a spirograph path")

	def __init__(self, master):
		Plugin.__init__(self, master, "Spirograph")
		self.icon  = "spirograph"
		self.group = "Artistic"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("RadiusExternal"  ,   "mm" ,    50.0, _("External Radius")),
			("RadiusInternal"  ,   "mm" ,    33.0, _("Internal Radius")),
			("RadiusOffset"  ,   "mm" ,    13.0, _("Offset radius")),
			("Depth"  ,   "mm" ,    0, _("Target Depth"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		n = self["name"]
		if not n or n=="default": n="Spirograph"
		spirograph = Spirograph(n)

		blocks = spirograph.make(self.fromMm("RadiusExternal"),
				self.fromMm("RadiusInternal"),
				self.fromMm("RadiusOffset"),
				self.fromMm("Depth"))

		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Spirograph")
		app.refresh()
		app.setStatus(_("Generated: Spirograph"))

if __name__=="__main__":
	spirograph = Spirograph()
	spirograph.make()
