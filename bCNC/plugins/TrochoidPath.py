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

__author__ = "Mario Basz"
__email__  = "mariob_1960@yahoo.com.ar"

__name__ = _("Trochoidal Path")
__version__= "0.0.5"

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
			("name",      "db" ,    "", _("Name")),
	        ("CutDiam" ,"float", 10.0, _("Trochoid Diameter")),
			("Direction","inside,outside,on" , "outside", _("Direction")),
			("Offset",   "float",  0.0, _("Additional offset distance")),
			("endmill",   "db" ,    "", _("End Mill")),
			("Adaptative",  "bool",1,   _("Adaptative")),
			("Overcut",  "bool",     0, _("Overcut")),
			("cornerdiameter",  "float",    10, _("Diameter safe to corner %"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		cornerdiameter = CNC.vars["diameter"]*(1+self["cornerdiameter"]/100.0)
		cornerradius = (self["CutDiam"] - cornerdiameter) /2.0
#		adaptedRadius = (self["CutDiam"] - CNC.vars["diameter"])/2.0

		direction = self["Direction"]
		name = self["name"]
		if name=="default" or name=="": name=None
#		app.trochprofile(direction, self["offset"], self["overcut"], name)
#		app.trochprofile(self["CutDiam"], direction, self["Offset"], self["Overcut"], self["Adaptative"], adaptedRadius, name)
		app.trochprofile(self["CutDiam"], direction, self["Offset"], self["Overcut"], self["Adaptative"], cornerradius, name)
		app.setStatus(_("Generate Trochoidal Profile path"))

#==============================================================================
