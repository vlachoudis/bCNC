#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: Mario Basz
#mariob_1960@yahoo.com.ar
# Date: 9 November 2017
# Date: 03 may 2018
# A special thanks to Filippo Rivato and Vasilis.
#This plugin is based on a variation
# of yours plugin Driller and My_Plugin example.
# To correct: Thats why the first point starts,

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Mario Basz"
__email__  = "mariob_1960@yahoo.com.ar"

__name__ = _("2 bits")
__version__= "0.10"
# Date last version: 29-January-2019

import math
from bmath import Vector
#import CNC					 # <<
from CNC import CNC,Block   #<< without this error it does not find CNC.vars
from ToolsPage import Plugin


#==============================================================================
# Create Trochoidadl rute along selected blocks
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create a adaptative route for 2 bits")

	def __init__(self, master):
		Plugin.__init__(self, master, "Two Bit Clear Path") #NAME OF THE PLUGIN
		self.icon  = "scale"
		self.group = "CAM"

		self.variables = [
			("name",      "db" ,                     "", _("Name")),
			("endmill",   "db" ,                     "", _("Smaller diameter End Mill"), "If Empty chooses, End Mill loaded"),
	        ("larger_endmill" ,"mm",                  6.0, _("Larger diameter End Mill")),
			("direction","inside,outside,on" , "inside", _("Direction")),
			("offset",   "float",                   0.0, _("Additional offset distance")),
#			("adaptative",  "bool",                   1,   _("Adaptative"), "Generate path for adaptative trochoids in the corners (Not yet implemented in trochoidal plugin)"),
#			("overcut",  "bool",                      0, _("Overcut")),
#			("mintrochdiam", "float",                10, _("Minimal trochoid in % tool"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def update(self):
		self.master.cnc()["larger_endmill"] = self.fromMm("larger_endmill")
	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		larger_endmill=self.fromMm("larger_endmill")
#		mintrochdiameter = CNC.vars["diameter"]*(1+self["mintrochdiam"]/100.0)
		mintrochdiameter = CNC.vars["diameter"]
		cornerradius = (larger_endmill - mintrochdiameter) /2.0
		direction = self["direction"]
		name = self["name"]
		if name=="default" or name=="": name=None
#		app.trochprofile_bcnc(trochcutdiam, direction, self["offset"], self["overcut"], self["adaptative"], cornerradius, CNC.vars["diameter"], name) #<< diameter only to information
		app.trochprofile_bcnc(larger_endmill, direction, self["offset"], 0, 1, cornerradius, CNC.vars["diameter"], name) #<< diameter only to information
#		app.adaptative_clearence( CNC.vars["diameter"], direction, self["offset"], 0, 1, cornerradius, larger_endmill, name) #<< diameter only to information
		app.setStatus(_("Generated path for profile clearing two bits"))

