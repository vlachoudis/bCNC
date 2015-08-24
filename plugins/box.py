#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	20-Aug-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

__name__ = "Box"

from ToolsPage import DataBase

#==============================================================================
# Create a BOX
#==============================================================================
class Plugin(DataBase):
	"""Generate a finger box"""
	def __init__(self, master):
		""
		DataBase.__init__(self, master)
		self.name = "Box"
		self.icon = "empty"
		self.variables = [
			("name",      "db",    "", "Name"),
			("dx",        "mm", 100.0, "Width Dx"),
			("dy",        "mm",  70.0, "Depth Dy"),
			("dz",        "mm",  50.0, "Height Dz"),
			("nx",       "int",    11, "Fingers Nx"),
			("ny",       "int",     7, "Fingers Ny"),
			("nz",       "int",     5, "Fingers Nz"),
			("profile", "bool",     0, "Profile"),
			("overcut", "bool",     1, "Overcut"),
			("cut",     "bool",     0, "Cut")
		]
		self.buttons  = self.buttons + ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		app.gcode.box(app.gcodelist.activeBlock(),
				self["dx"], self["dy"], self["dz"],
				self["nx"], self["ny"], self["nz"],
				self["profile"], self["cut"], self["overcut"])
		app.gcodelist.fill()
		app.draw()
		app.statusbar["text"] = "BOX with fingers generated"

