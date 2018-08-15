#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 11 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("slicemesh")
__version__ = "0.0.2"

#import math
import os.path
#import re
from CNC import CNC,Block
from ToolsPage import Plugin
#from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod

#FIXME: not sure how to force bCNC to prefer importing from bCNC/lib to importing from system
#	if having conflicts with system libs, you can try this. It helped for me:
#	pip2 uninstall meshcut stl ply itertools utils python-utils
#	pip2 install scipy numpy

import os
import numpy as np
#import numpy.linalg as la
#import itertools
#import utils
import meshcut
import ply
import stl #FIXME: write smaller STL parser
import scipy.spatial.distance as spdist #stl only, FIXME: can be easily rewritten as internal method


class Tool(Plugin):
	__doc__ = _("""STL/PLY Slicer""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Slice Mesh")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "mesh"			#<<< This is the name of png file used as icon for the ribbon button. It will be search in the "icons" subfolder
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
		self.help = '''This plugin can slice meshes
#mesh

It has following features:

+ file: STL or PLY file
+ flat: Z=0 for all layer
+ zstep: layer height
'''


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

		#Load mesh
		app.setStatus(_("Loading mesh: %s"%(file)), True)
		verts, faces = self.loadMesh(file)

		#Rotate/flip mesh
		#self.transformMesh(verts, 2, 1, 1, -1)

		if zstep <= 0:
			#cut only single layer if zstep <= 0
			blocks.append(self.slice(file, zmax))
		else:
			#loop over multiple layers if zstep > 0
			z = zmax
			while z >= 0:
				#print(_("Slicing %f / %f"%(z,zmax)))
				app.setStatus(_("Slicing %f / %f : %s"%(z,zmax,file)), True)
				block = self.slice(verts, faces, z, zout)
				if block is not None: blocks.append(block)
				z -= zstep

		#Insert blocks to bCNC
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Mesh sliced") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Mesh sliced"))                           #<<< feed back result


	def loadMesh(self, file):
		#Decide on filetype
		fn, fext = os.path.splitext(file)
		fext = fext.upper()

		if fext=='.STL':
			verts, faces = self.load_stl(file)
		elif fext=='.PLY':
			with open(file) as f:
				verts, faces, _ = ply.load_ply(f)
		else:
			print("unknown file extension",fext)
			return None

		return verts, faces


	#Rotate or flip mesh
	def transformMesh(self, verts, a, b=0, ia=1, ib=1):
		for vert in verts:
			vert[a], vert[b] = ia*vert[b], ib*vert[a]


	def slice(self, verts, faces, z, zout=None):
		block = Block("slice %f"%(float(z)))

		#FIXME: slice along different axes
		plane_orig = (0, 0, z) #z height to slice
		plane_norm = (0, 0, 1)

		#Crosscut
		contours = meshcut.cross_section(verts, faces, plane_orig, plane_norm)

		#Flatten contours
		if zout is not None:
			for contour in contours:
				for segment in contour:
					segment[2] = zout

		#Contours to G-code
		for contour in contours:
			#print(contour)
			first = contour[0]
			block.append("g0 x%f y%f z%f"%(first[0],first[1],first[2]))
			for segment in contour:
				block.append("g1 x%f y%f z%f"%(segment[0],segment[1],segment[2]))
			block.append("g1 x%f y%f z%f"%(first[0],first[1],segment[2]))
			block.append("( ---------- cut-here ---------- )")
		if block: del block[-1]

		if not block: block = None
		return block

	def merge_close_vertices(self, verts, faces, close_epsilon=1e-5):
		"""
		Will merge vertices that are closer than close_epsilon.

		Warning, this has a O(n^2) memory usage because we compute the full
		vert-to-vert distance matrix. If you have a large mesh, might want
		to use some kind of spatial search structure like an octree or some fancy
		hashing scheme

		Returns: new_verts, new_faces
		"""
		# Pairwise distance between verts
		D = spdist.cdist(verts, verts)

		# Compute a mapping from old to new : for each input vert, store the index
		# of the new vert it will be merged into
		close_epsilon = 1e-5
		old2new = np.zeros(D.shape[0], dtype=np.int)
		# A mask indicating if a vertex has already been merged into another
		merged_verts = np.zeros(D.shape[0], dtype=np.bool)
		new_verts = []
		for i in range(D.shape[0]):
			if merged_verts[i]:
				continue
			else:
				# The vertices that will be merged into this one
				merged = np.flatnonzero(D[i, :] < close_epsilon)
				old2new[merged] = len(new_verts)
				new_verts.append(verts[i])
				merged_verts[merged] = True

		new_verts = np.array(new_verts)

		# Recompute face indices to index in new_verts
		new_faces = np.zeros((len(faces), 3), dtype=np.int)
		for i, f in enumerate(faces):
			new_faces[i] = (old2new[f[0]], old2new[f[1]], old2new[f[2]])

		# again, plot with utils.trimesh3d(new_verts, new_faces)
		return new_verts, new_faces


	def load_stl(self, stl_fname):
		#import stl
		m = stl.mesh.Mesh.from_file(stl_fname)

		# Flatten our vert array to Nx3 and generate corresponding faces array
		verts = m.vectors.reshape(-1, 3)
		faces = np.arange(len(verts)).reshape(-1, 3)

		verts, faces = self.merge_close_vertices(verts, faces)
		return verts, faces

