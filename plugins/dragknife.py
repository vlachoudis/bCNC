#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 25 sept 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("DragKnife")
__version__ = "0.3.0"

import math
import os.path
import re
from CNC import CNC,Block
from bmath import Vector
from bpath import eq, Path, Segment
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

class Tool(Plugin):
	__doc__ = _("""Drag knife postprocessor""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"DragKnife")
		self.icon = "dragknife"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("offset", "mm", 3, _("dragknife offset"), _("distance from dragknife rotation center to the tip of the blade")),
			("angle", "float", 20, _("angle threshold"), _("do not perform pivot action for angles smaller than this")),
			("swivelz", "mm", 0, _("swivel height"), _("retract to this height for pivots (useful for thick materials, you should enter number slightly lower than material thickness)")),
			("initdir", "X+,Y+,Y-,X-,none", "X+", _("initial direction"), _("direction that knife blade is facing before and after cut. Eg.: if you set this to X+, then the knifes rotation axis should be on the right side of the tip. Meaning that the knife is ready to cut towards right immediately without pivoting. If you cut multiple shapes in single operation, it's important to have this set consistently across all of them.")),
			("feed", "mm", 200, _("feedrate")),
			("simulate", "bool", False, _("simulate"), _("Use this option to simulate cuting of dragknife path. Resulting shape will reflect what shape will actuall be cut. This should reverse the dragknife procedure and give you back the original shape from g-code that was previously processed for dragknife.")),
			("simpreci", "mm", 0.5, _("simulation precision"), _("Simulation is currently approximated by using lots of short lines. This is the length of these lines."))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below

		self.help = """DragKnifes are special kind of razor/blade holders that can be fit into spindle of your CNC (do not turn the spindle on!!!). They are often used to cut soft and thin materials like vinyl stickers, fabric, leather, rubber gaskets, paper, cardboard, etc...

Dragknife blade is located off center to allow for automatic rotation (kinda like rear wheels of car pivot to the direction of front wheels).
This fact introduces the need for preprocessing the g-code to account with that offset. Otherwise it wouldn't be able to cut sharp corners. This plugin does this g-code postprocessing.
"""


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		dragoff = self.fromMm("offset")
		angleth = self["angle"]
		swivelz = self.fromMm("swivelz")
		initdir = self["initdir"]
		CNC.vars["cutfeed"] = self.fromMm("feed")
		simulate = self["simulate"]
		simpreci = self["simpreci"]

		def initPoint(P, dir, offset):
			P = Vector(P[0], P[1])

			if dir == 'X+':
				P[0]+=offset
			elif dir == 'X-':
				P[0]-=offset
			elif dir == 'Y+':
				P[1]+=offset
			elif dir == 'Y-':
				P[1]-=offset
			return P

		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue

			opath = app.gcode.toPath(bid)[0]
			npath = Path("dragknife %s: %s"%(dragoff,app.gcode[bid].name()))

			if not simulate:

				#Entry vector
				ventry = Segment(Segment.LINE, initPoint(opath[0].A, initdir, -dragoff), opath[0].A)

				#Exit vector
				vexit = Segment(Segment.LINE, opath[-1].B, initPoint(opath[-1].B, initdir, dragoff))
				opath.append(vexit)

				prevseg = ventry
				#Generate path with tangential lag for dragknife operation
				for i,seg in enumerate(opath):
					#Get adjacent tangential vectors in this point
					TA = prevseg.tangentEnd()
					TB = seg.tangentStart()

					#Compute difference between tangential vectors of two neighbor segments
					angle = degrees(acos(TA.dot(TB)))

					#Compute swivel direction
					arcdir = ( TA[0] * TB[1] ) - ( TA[1] * TB[0] )
					if arcdir < 0:
						arcdir = Segment.CW
					else:
						arcdir = Segment.CCW

					#Append swivel if needed (also always do entry/exit)
					if abs(angle) > angleth or (abs(angle) > 1 and ( i == 0 or i == len(opath)-1 )):
						arca = Segment(arcdir, prevseg.tangentialOffset(dragoff).B, seg.tangentialOffset(dragoff).A, prevseg.B)

						if swivelz !=0: arca._inside = [swivelz]
						npath.append(arca)

					#Append segment with tangential offset
					if i < len(opath)-1:
						npath.append(seg.tangentialOffset(dragoff))

					prevseg = seg

			elif simulate:

				opath = opath.linearize(simpreci, True)
				prevknife = initPoint(opath[0].A, initdir, -dragoff)
				for seg in opath:
					dist = sqrt((seg.B[0]-prevknife[0])**2+(seg.B[1]-prevknife[1])**2)
					move = ( seg.B - prevknife ).unit() * ( dist - dragoff )
					newknife = prevknife + move
					if not eq(newknife, prevknife):
						npath.append(Segment(Segment.LINE, prevknife, newknife))
					prevknife = newknife


			eblock = app.gcode.fromPath(npath)
			blocks.append(eblock)



		#active = app.activeBlock()
		#if active == 0: active+=1
		active=-1 #add to end
		app.gcode.insBlocks(active, blocks, "Dragknife") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Dragknife"))                           #<<< feed back result
		#app.gcode.blocks.append(block)
