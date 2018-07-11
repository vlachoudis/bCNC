#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 11 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("slicemesh")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

#FIXME: not sure how to force bCNC to prefer importing from bCNC/lib to importing from system
#	if having conflicts with system libs, you can try this. It helped for me:
#	pip2 uninstall meshcut stl ply itertools utils

import os
import numpy as np
import itertools
import utils
import ply
import stl
import meshcut


class Tool(Plugin):
	__doc__ = _("""STL/PLY Slicer""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Slice Mesh")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "mesh"			#<<< This is the name of gif file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("file"    ,    "file" ,    "", _(".STL/.PLY file to slice")),
			("flat"    ,    "bool" ,    True, _("Get flat slice")),
			("zstep"    ,    "mm" ,    "0.1", _("layer height (0 = single)")),
			("zmax"    ,    "mm" ,    "1", _("maximum Z height"))
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		file = self["file"]
		zstep = self["zstep"]
		zmax = self["zmax"]
		flat = self["flat"]

		zout = None
		if flat: zout = 0

		blocks = []

		if zstep <= 0:
			#cut only single layer if zstep <= 0
			blocks.append(self.slice(file, zmax))
		else:
			#loop over multiple layers if zstep > 0
			z = 0
			while z <= zmax:
				blocks.append(self.slice(file, z, zout))
				z += zstep

		#Insert blocks to bCNC
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Mesh sliced") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Mesh sliced"))                           #<<< feed back result


	def slice(self, file, z, zout=None):
		block = Block("slice %f"%(float(z)))

		#FIXME: decide if stl or ply and load mesh using proper method
		# STL slicing example: https://github.com/julienr/meshcut/blob/master/examples/1_stl_sphere_cut.py
		with open(file) as f:
			verts, faces, _ = ply.load_ply(f)

		#FIXME: slice along different axes
		plane_orig = (z, 0, 0) #z height to slice
		plane_norm = (1, 0, 0)

		#Crosscut
		contours = meshcut.cross_section(verts, faces, plane_orig, plane_norm)

		#Flatten contours
		if zout is not None:
			for contour in contours:
				for segment in contour:
					segment[0] = zout

		#Contours to G-code
		for contour in contours:
			#print(contour)
			first = contour[0]
			block.append("g0 x%f y%f z%f"%(first[1],first[2],first[0]))
			for segment in contour:
				block.append("g1 x%f y%f z%f"%(segment[1],segment[2],segment[0]))
			block.append("g1 x%f y%f z%f"%(first[1],first[2],segment[0]))
			block.append("( ---------- cut-here ---------- )")
		if block: del block[-1]

		return block
