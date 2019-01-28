#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from __future__ import absolute_import
from __future__ import print_function
__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("Intersection")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from bpath import EPS,eq,Path, Segment
from copy import deepcopy


class Tool(Plugin):
	__doc__ = _("""Intersection of two shapes""")			#<<< This comment will be show as tooltip for the ribbon button

	def __init__(self, master):
		Plugin.__init__(self, master,"Intersection")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "intersection"			#<<< This is the name of png file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "Development"	#<<< This is the name of group that plugin belongs
		self.oneshot = True
		#Here we are creating the widgets presented to the user inside the plugin
		#Name, Type , Default value, Description
		self.variables = [			#<<< Define a list of components for the GUI
			("name"    ,    "db" ,    "", _("Name")),							#used to store plugin settings in the internal database
		]
		self.buttons.append("exe")  #<<< This is the button added at bottom to call the execute method below

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		#print("go!")
		blocks  = []

		bid = app.editor.getSelectedBlocks()[0]
		xbasepath = app.gcode.toPath(bid)[0]

		bid = app.editor.getSelectedBlocks()[1]
		xislandpath = app.gcode.toPath(bid)[0]

		xbasepath.intersectPath(xislandpath)
		xislandpath.intersectPath(xbasepath)

		#xnewisland = self.pathBoolIntersection(xbasepath, xislandpath)
		xnewisland = self.pathBoolIntersection(xislandpath, xbasepath)

		#pth = Path("temp")
		#basepath.invert()
		#pth.extend(basepath)
		#pth.extend(basepath)
		##pth.invert()


		block = Block("intersect")
		block.extend(app.gcode.fromPath(xnewisland))
		blocks.append(block)

		#block = Block("diff")
		#block.extend(app.gcode.fromPath(pth))
		#blocks.append(block)


		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Intersect") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Intersect"))                           #<<< feed back result
		#app.gcode.blocks.append(block)

##############################################


	def pol2car(self, r, phi, a=[0,0]):
		return [round(a[0]+r*cos(phi),4),round(a[1]+r*sin(phi),4)]

	def findSegment(self, path,A,B): #FIXME: not used for now...
		for seg in path:
			if seg.A == A and seg.B == B:
				return seg
			elif seg.A == B and seg.B == A:
				seg.invert()
				return seg
			else: return Segment(1, A, B)

	def findSubpath(self, path,A,B):
		path = deepcopy(path)
		newpath = self._findSubpath(path,A,B)
		if newpath is None:
			path.invert()
			newpath = self._findSubpath(path,A,B)
		return newpath

	def _findSubpath(self, path,A,B):
		print("finding", A, B)

		sub = None
		for i in xrange(0,len(path)*2): #iterate twice with wrap around
			j = i%len(path)
			seg = path[j]

			if eq(seg.A,A): sub = Path("subp")
			print("seg", sub is None, seg)
			if sub is not None: sub.append(seg)
			if eq(seg.B,B): break

		print("found", sub)
		return sub

	def pathBoolIntersection(self, basepath, islandpath):
		#basepath = deepcopy(basepath)
		#islandpath = deepcopy(islandpath)

		#find first intersecting segment
		first = None
		for i,segment in enumerate(islandpath):
			if basepath.isInside(segment.midPoint()): first = i
		if first is None:
			print("not intersecting paths")
			return None

		#generate intersected path
		newisland = Path("new")
		A = None
		for i in xrange(first,2*len(islandpath)+first):
			j = i%len(islandpath)
			segment = islandpath[j]
			if segment.length()<EPS: continue #ignore zero length segments
			if not basepath.isInside(segment.midPoint()):
				if A is None:
					A = segment.A
			else:
				if A is not None:
					newisland.extend(self.findSubpath(basepath,A,segment.A))
					print("new",newisland)
					A = None
				newisland.append(segment)
		#for i,seg in enumerate(newisland):
		#	newisland[i].correct();
		print("new2",newisland)
		return newisland
