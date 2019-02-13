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

__name__ = _("Trochoidal Path")
__version__= "1.0"
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
	__doc__ = _("Create a trochoid rute along selected blocks")

	def __init__(self, master):
		Plugin.__init__(self, master, "Trochoid_Path") #NAME OF THE PLUGIN
		self.icon  = "trochoidpath"
		self.group = "CAM"

		self.variables = [
			("name",      "db" ,                     "", _("Name")),
	        ("trochcutdiam" ,"mm",                  6.0, _("Cut Diameter"),"Real cutting diameter"),
			("direction","inside,outside,on" , "inside", _("Direction")),
			("offset",   "float",                   0.0, _("Additional offset distance")),
			("endmill",   "db" ,                     "", _("End Mill"), "If Empty chooses, End Mill loaded"),
			("adaptative",  "bool",                   1,   _("Adaptative"), "Generate path for adaptative trochoids in the corners (Not yet implemented in trochoidal plugin)"),
			("overcut",  "bool",                      0, _("Overcut")),
#			("mintrochdiam", "float",                10, _("Minimal trochoid in % tool"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		trochcutdiam=self.fromMm("trochcutdiam")
#		mintrochdiameter = CNC.vars["diameter"]*(1+self["mintrochdiam"]/100.0)
		mintrochdiameter = CNC.vars["diameter"]
		cornerradius = (trochcutdiam - mintrochdiameter) /2.0
		direction = self["direction"]
		name = self["name"]
		if name=="default" or name=="": name=None
		app.trochprofile_bcnc(trochcutdiam, direction, self["offset"], self["overcut"], self["adaptative"], cornerradius, CNC.vars["diameter"], name) #<< diameter only to information
		app.setStatus(_("Generated path for trochoidal cutting"))

#==============================================================================
