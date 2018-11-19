#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 11 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("slicemesh")
__version__ = "0.0.5"

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

#If needed trimesh supports following formats:
#binary/ASCII STL, Wavefront OBJ, ASCII OFF, binary/ASCII PLY, GLTF/GLB 2.0, 3MF, XAML, 3DXML, etc.
#https://github.com/mikedh/trimesh
#but it depends on numpy, scipy and networkx

import os
import numpy as np
#import numpy.linalg as la
#import itertools
#import utils
import meshcut
import ply #FIXME: write PLY parser which supports binary PLY files (currently can only do ASCII PLY)
import stl #FIXME: write smaller STL parser

class Tool(Plugin):
	__doc__ = _("""STL/PLY Slicer""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Slice Mesh")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "mesh"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
			("file"    ,    "file" ,    "", _(".STL/.PLY file to slice"), "What file to slice"),
			("flat"    ,    "bool" ,    True, _("Get flat slice"), "Pack all slices into single Z height?"),
			("cam3d"    ,    "bool" ,    True, _("3D slice (devel)"), "This is just for testing"),
			("faceup"    ,    "Z,-Z,X,-X,Y,-Y" ,    "Z", _("Flip upwards"), "Which face goes up?"),
			("scale"    ,    "float" ,    "1", _("scale factor"), "Size will be multiplied by this factor"),
			("zoff"  ,    "mm" ,    "0", _("z offset"), "This will be added to Z"),
			("zstep"    ,    "mm" ,    "0.1", _("layer height (0 = only single zmin)"), "Distance between layers of slices"),
			("zmin"    ,    "mm" ,    "-1", _("minimum Z height"), "Height to start slicing"),
			("zmax"    ,    "mm" ,    "1", _("maximum Z height"), "Height to stop slicing")
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below
		self.help = '''This plugin can slice meshes
#mesh

Currently it supports following formats:
STL (Binary and ASCII)
PLY (ASCII only)
'''


	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		self.app = app
		file = self["file"]
		zstep = float(self["zstep"])
		zmin = float(self["zmin"])
		zmax = float(self["zmax"])
		flat = self["flat"]
		faceup = self["faceup"]
		scale = float(self["scale"])
		zoff = float(self["zoff"])
		cam3d = self["cam3d"]

		zout = None
		if flat: zout = 0

		blocks = []

		#Load mesh
		self.app.setStatus(_("Loading mesh: %s"%(file)), True)
		verts, faces = self.loadMesh(file)

		#Rotate/flip mesh
		if faceup == 'Z':
			pass
		elif faceup == '-Z':
			self.transformMesh(verts, 2, 2, -1, -1)
		elif faceup == 'X':
			self.transformMesh(verts, 2, 0,  1,  1)
		elif faceup == '-X':
			self.transformMesh(verts, 2, 0,  1, -1)
		elif faceup == 'Y':
			self.transformMesh(verts, 2, 1,  1,  1)
		elif faceup == '-Y':
			self.transformMesh(verts, 2, 1,  1, -1)

		if scale != 1 or zoff != 0:
			#FIXME: maybe use some numpy magic like verts = verts*scale ?
			for vert in verts:
				vert[0], vert[1], vert[2] = vert[0]*scale, vert[1]*scale, (vert[2]*scale)+zoff

		axes = ['z']
		if cam3d: axes = ['x','y','z']

		#Slice
		for axis in axes:
			if zstep <= 0:
				#cut only single layer if zstep <= 0
				zmax = zmin
				zstep = 1
			zmin, zmax = min(zmin,zmax), max(zmin,zmax) #make sure zmin<zmax
			#loop over multiple layers if zstep > 0
			z = zmax
			while z >= zmin:
				#print(_("Slicing %f / %f"%(z,zmax)))
				self.app.setStatus(_("Slicing %s %f in %f -> %f of %s"%(axis,z,zmin,zmax,file)), True)
				block = self.slice(verts, faces, z, zout, axis)
				if block is not None: blocks.append(block)
				z -= abs(zstep)

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
		#FIXME: use numpy vectorization?
		for vert in verts:
			vert[a], vert[b] = ia*vert[b], ib*vert[a]


	def slice(self, verts, faces, z, zout=None, axis='z'):
		tags = '[slice]'
		if axis=='z': tags = '[slice,minz:%f]'%(float(z))
		block = Block("slice %s%f %s"%(axis,float(z),tags))

		#FIXME: slice along different axes
		if axis == 'x':
			plane_orig = (z, 0, 0)
			plane_norm = (1, 0, 0)
		elif axis == 'y':
			plane_orig = (0, z, 0)
			plane_norm = (0, 1, 0)
		else:
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
			gtype = 0
			for segment in contour:
				block.append("g%s x%f y%f z%f"%(gtype, segment[0],segment[1],segment[2]))
				gtype = 1
			block.append("g1 x%f y%f z%f"%(contour[0][0],contour[0][1],contour[0][2])) #Close shape
			block.append("( ---------- cut-here ---------- )")
		if block: del block[-1]

		if not block: block = None
		return block

	def vert_dist(self, A, B):
		#return np.sqrt(np.sum(np.square(B-A)))
		return ((B[0]-A[0])**2+(B[1]-A[1])**2+(B[2]-A[2])**2)**(1.0/2)

	def vert_dist_matrix(self, verts):
		#FIXME: This is VERY SLOW:
		D = np.empty((len(verts), len(verts)), dtype=np.float64)
		for i,v in enumerate(verts):
			self.app.setStatus(_("Calculating distance %d of %d (SciPy not installed => using SLOW fallback method)"%(i,len(verts))), True)
			D[i] = D[:,i] = np.sqrt(np.sum(np.square(verts-verts[i]), axis=1))
			#for j in range(i,len(verts)):
			#	D[j][i] = D[i][j] = self.vert_dist(v,verts[j])
			#	#D[j][i] = D[i][j] = la.norm(verts[j]-v)
		return D

	def pdist_squareformed_numpy(self, a):
		#Thanks to Divakar Roy (@droyed) https://stackoverflow.com/questions/52030458/vectorized-spatial-distance-in-python-using-numpy
		a_sumrows = np.einsum('ij,ij->i',a,a)
		dist = a_sumrows[:,None] + a_sumrows -2*np.dot(a,a.T)
		np.fill_diagonal(dist,0)
		return dist

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
		verts = np.array(verts, dtype=np.float64)
		#Use SciPy, otherwise use slow fallback
		try:
			import scipy.spatial.distance as spdist
			D = spdist.cdist(verts, verts)
		except ImportError:
			D = np.sqrt(np.abs(self.pdist_squareformed_numpy(verts)))

		#Test
		print(len(verts), len(D), len(D[0]))
		#print(D)
		#print(spdist.cdist(verts, verts))

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
