#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: Filippo Rivato
# Date:	11 March 2016
# Done in Annonay at Hotel "Du midi" after a business trip and 10 hours of work.

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Hilbert")
__version__= "0.0.1"

from CNC import CNC,Block
from ToolsPage import Plugin


#==============================================================================
#Hilbert class
#==============================================================================
class Hilbert:
	def __init__(self,name="Hilbert"):
		self.name = name

	#----------------------------------------------------------------------
	def hilbert(self,x0, y0, xi, xj, yi, yj, n):
		def x():
			return (x0 + (xi + yi)/2.)
		def y():
			return (y0 + (xj + yj)/2.)

		if n >0:
			for ye in self.hilbert(x0,               y0,               yi/2, yj/2, xi/2, xj/2, n - 1):
				yield ye
			for ye in self.hilbert(x0 + xi/2,        y0 + xj/2,        xi/2, xj/2, yi/2, yj/2, n - 1):
				yield ye
			for ye in self.hilbert(x0 + xi/2 + yi/2, y0 + xj/2 + yj/2, xi/2, xj/2, yi/2, yj/2, n - 1):
				yield ye
			for ye in self.hilbert(x0 + xi/2 + yi,   y0 + xj/2 + yj,  -yi/2,-yj/2,-xi/2,-xj/2, n - 1):
				yield ye
		else:
			yield (x(),y())

	#----------------------------------------------------------------------
	def make(self,n = 2, size = 100, depth = 0):
		self.n = n
		self.size = size
		self.depth = depth

		blocks = []
		block = Block(self.name)

		xi,yi = zip(*(self.hilbert(0.0,0.0,size,0.0,0.0,size,n)))

		block.append(CNC.zsafe())
		block.append(CNC.grapid(xi[0],yi[0]))

		currDepth = 0.
		stepz = CNC.vars['stepz']
		if stepz==0 : stepz=0.001  #avoid infinite while loop

		while True:
			currDepth -= stepz
			if currDepth < self.depth : currDepth = self.depth
			block.append(CNC.zenter(currDepth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
			for x,y in zip(xi,yi):
				block.append(CNC.gline(x,y))
			if currDepth <= self.depth : break

		block.append(CNC.zsafe())
		blocks.append(block)
		return blocks


#==============================================================================
# Create a Hilbert curve
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create a Hilbert path")

	def __init__(self, master):
		Plugin.__init__(self, master, "Hilbert")
		self.icon  = "hilbert"
		self.group = "Artistic"
		self.variables = [
			("name",     "db" ,      "", _("Name")),
			("Size"  ,   "mm" ,    50.0, _("Size")),
			("Order"  , "int" ,       2, _("Order")),
			("Depth"  , "int" ,       0, _("Depth"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		name = self["name"]
		if not name or name=="default": name="Hilbert"
		H = Hilbert(name)

		size = self.fromMm("Size")
		n = self["Order"]
		depth = self["Depth"]

		#Check parameters
		if size <=0:
			app.setStatus(_("Hilbert abort: verify the size"))
			return

		if depth >0:
			app.setStatus(_("Hilbert abort: depth must be minor or equal to zero"))
			return

		blocks = H.make(n,size,depth)

		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Hilbert")
		app.refresh()
		app.setStatus(_("Generated: Hilbert"))

if __name__=="__main__":
	Hilbert = Hilbert()
	Hilbert.make()
