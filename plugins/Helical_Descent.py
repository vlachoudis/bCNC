#!/usr/bin/python
# -*- coding: ascii -*-
#
# Author:  @Mariobasz
# Date:  04-05-2018

__author__ = "@Mariobasz"
__email__  = "my.mail@gmail.com"  #<<< here put an email where plugins users can contact you

#Here import the libraries you need, these are necessary to modify the code
from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
# My plugin
#==============================================================================
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
class Tool(Plugin):
	# WARNING the __doc__ is needed to allow the string to be internationalized
	__doc__ = _("""This is my Helical Descent""")
	def __init__(self, master):
		Plugin.__init__(self, master,"Helical")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "Helical"
		self.group = "CAM"
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [
			("name",	"db",	"",   _("Name")),
			("X",		"mm",	0.00, _("X Initial")),
			("Y",		"mm",	0.00, _("Y Initial")),
			("Z",		"mm",	0.00, _("Z Initial")),
			("CutDiam",	"float",1.50, _("Diameter Cut")),
		#	("RadioHelix",	"mm",	0.80, _("Helicoid Radius")),
			("Pitch",	"mm",	0.10, _("Drop by lap")),			#an integer variable
			("Depth",	"mm",	-3.00, _("Final Depth")),			#a float value variable
			("Mult_Feed_Z",	"float" ,1.0, _("Multiple Z Feed")),
			("HelicalCut",	"Helical Cut,Right Thread,Left Thread", "Helical Cut",_("Helical Type")),
			("ReturnToSafeZ","Not Return,Center,Edge" , "Center", _("Returns to safe Z")),

		#	("Text"    , "text" ,    "Free Text", _("Text description")),		#a text input box
		#	("CheckBox", "bool" ,  False, _("CheckBox description")),			#a true/false check box
		#	("OpenFile", "file" ,     "", _("OpenFile description")),			#a file chooser widget
		#	("ComboBox", "Item1,Item2,Item3" , "Item1", _("ComboBox description"))	#a multiple choice combo box
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		name = self["name"]
		if not name or name=="default": name="Default Name"

		#Radio for Helical retrive data from user imput
		cutDiam       = self["CutDiam"]
		cutRadius     = cutDiam/2.0
		#Radio        = self["RadioHelix"]
		pitch         = self["Pitch"]
		Depth         = self["Depth"]
		Mult_F_Z      = self["Mult_Feed_Z"]
		helicalCut    = self["HelicalCut"]
		returnToSafeZ = self["ReturnToSafeZ"]
		toolDiam      = CNC.vars['diameter']
		toolRadius    = toolDiam/2.0
		Radio = cutRadius - toolRadius
		if Radio < 0:
			Radio = 0
			app.setStatus(_("Error: Cut diameter smaller than tool diameter"))
			return

		if helicalCut == "Helical Cut":
			turn = 2
			p="HelicalCut "
		elif helicalCut == "Right Thread":
			turn = 2
			p= "RightThread "
		elif helicalCut == "Left Thread":
			turn = 3
			p= "LeftThread "

		#Initialize blocks that will contain our gCode
		blocks = []
		#block = Block(name)
#		block = Block("Hole " + str(cutDiam) + " Bit " + str(toolDiam) + " depth " + str(Depth))
		block = Block( p + str(cutDiam) + " Pitch " + str(pitch) + " Bit " + str(toolDiam) + " depth " + str(Depth))

		#use some useful bCNC functions to generate gCode movement, see CNC.py for more
		x = self["X"]
		y = self["Y"]
		z = self["Z"]

		cutFeed   = CNC.vars["cutfeedz"] #<<< Get cut feed Z for the current material
		cutFeedMax = CNC.vars["cutfeed"] #<<< Get cut feed XY for the current material

		if Mult_F_Z == "":
			Mult_F_Z = 1

		if Mult_F_Z == 0:
			Mult_F_Z = 1

		if Mult_F_Z * cutFeed > cutFeedMax:
			cutFeed = cutFeedMax
		else:
			cutFeed = cutFeed*Mult_F_Z

		block.append(CNC.zsafe())			#<<< Move rapid Z axis to the safe height in Stock Material
		block.append(CNC.grapid(x,y))		#<<< Move rapid to X and Y coordinate

		#cutFeed = int(cutFeed)
		block.append(CNC.fmt("f",cutFeed))	#<<< Set cut feed
	#	block.append(CNC.gline(x,y)
	#    while z < 1:
		block.append(CNC.gline(x-Radio,y))
		block.append(CNC.zenter(z))
	#	cutFeed = int((CNC.vars["cutfeed"]	+ CNC.vars["cutfeedz"])/2)	#<<< Get cut feed for the current material

		#cutFeed = int(cutFeed)
		block.append(CNC.fmt("F",cutFeed))	#<<< Set cut feed

	#-----------------------------------------------------------------------------------------------------
	#	Uncomment for first flat pass
	#-----------------------------------------------------------------------------------------------------
		block.append(CNC.gcode(turn, [("X",x-Radio),("Y",y),("Z", z),("I",Radio), ("J",0)]))
		if z < Depth:
			pitch = -pitch
			while (z-pitch) < Depth:
				z = z-pitch
				block.append(CNC.gcode(turn, [("X",x-Radio),("Y",y),("Z", z),("I",Radio), ("J",0)]))

		else:
			while (z-pitch) >= Depth:
				z = z-pitch
				block.append(CNC.gcode(turn, [("X",x-Radio),("Y",y),("Z", z),("I",Radio), ("J",0)]))

		#Target Level
		alpha  = round(Depth / pitch, 4 ) - round(Depth / pitch, 0)
		alpha  = alpha * 2*pi
		Radiox = Radio * cos(alpha)
		Radioy = Radio * sin(alpha)
		z = Depth

		if helicalCut == "Helical Cut":
			block.append(CNC.gcode(turn, [("X",x-Radio),("Y",y),("Z", z),("I",Radio), ("J",0)]))
			#Last flat pass
			block.append(CNC.gcode(turn, [("X",x-Radio),("Y",y),("Z", z),("I",Radio), ("J",0)]))
		elif helicalCut == "Right Thread":
			block.append(CNC.gcode(turn, [("X",x-Radiox),("Y",y-Radioy),("Z", z),("I",Radio), ("J",0)]))
		elif helicalCut == "Left Thread":
			block.append(CNC.gcode(turn, [("X",x-Radiox),("Y",y+Radioy),("Z", z),("I",Radio), ("J",0)]))

		# Return to Z Safe
		if returnToSafeZ == "Center":
			block.append(CNC.gline(x,y))
			block.append(CNC.zsafe())
		elif returnToSafeZ == "Edge":
			block.append(CNC.zsafe())

		blocks.append(block)
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Helical_Descent inserted")	#<<< insert blocks over active block in the editor
		app.refresh()							#<<< refresh editor
		app.setStatus(_("Generated: Helical_Descent Result"))		#<<< feed back result
