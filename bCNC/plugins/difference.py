#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("Difference")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from bpath import EPS,eq,Path, Segment
from bmath import Vector
from copy import deepcopy

class Tool(Plugin):
	__doc__ = _("""Difference of two shapes""")			#<<< This comment will be show as tooltip for the ribbon button
	def __init__(self, master):
		Plugin.__init__(self, master,"Difference")
		#Helical_Descent: is the name of the plugin show in the tool ribbon button
		self.icon = "diff"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
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

		paths_base = []
		paths_isl = []

		for bid in app.editor.getSelectedBlocks():
			if app.gcode[bid].operationTest('island'):
				paths_isl.extend(app.gcode.toPath(bid))
			else:
				paths_base.extend(app.gcode.toPath(bid))

		for island in paths_isl:
			paths_newbase = []
			while len(paths_base) > 0:
				base = paths_base.pop()

				base.intersectPath(island)
				island.intersectPath(base)

				newbase = Path("diff")

				#Add segments from outside of islands:
				for i,seg in enumerate(base):
					if not island.isInside(seg.midPoint()):
						newbase.append(seg)

				#Add segments from islands to base
				for i,seg in enumerate(island):
					if base.isInside(seg.midPoint()): #and base.isInside(seg.A) and base.isInside(seg.B):
						newbase.append(seg)

				#Eulerize
				paths_newbase.extend(newbase.eulerize())
				#paths_newbase.extend(newbase.split2contours())
			paths_base = paths_newbase

		for base in paths_base:
			print base
			#base = base.eulerize(True)
			block = Block("diff")
			block.extend(app.gcode.fromPath(base))
			blocks.append(block)

		#active = app.activeBlock()
		app.gcode.insBlocks(-1, blocks, "Diff") #<<< insert blocks over active block in the editor
		app.refresh()                                                                                           #<<< refresh editor
		app.setStatus(_("Generated: Diff"))                           #<<< feed back result
		#app.gcode.blocks.append(block)

##############################################


	def pol2car(self, r, phi, a=[0,0]):
		return [round(a[0]+r*cos(phi),4),round(a[1]+r*sin(phi),4)]

	#def findSegment(self, path,A,B): #FIXME: not used for now...
	#	for seg in path:
	#		if seg.A == A and seg.B == B:
	#			return seg
	#		elif seg.A == B and seg.B == A:
	#			seg.invert()
	#			return seg
	#		else: return Segment(1, A, B)

	def findSubpath(self, path,A,B ,inside):
		path = deepcopy(path)
		newpath = self._findSubpath(path,A,B,inside)
		if newpath is None:
			path.invert()
			newpath = self._findSubpath(path,A,B,inside)
		return newpath

	def _findSubpath(self, path,A,B, inside):
		print("finding", A, B)

		sub = None
		for i in xrange(0,len(path)*2): #iterate twice with wrap around
			j = i%len(path)
			seg = path[j]
			if inside.isInside(seg.midPoint()):

				if eq(seg.A,A): sub = Path("subp")
				print("seg", sub is None, seg)
				if sub is not None: sub.append(seg)
				if eq(seg.B,B): break

		print("found", sub)
		return sub

	def pathBoolIntersection(self, basepath, islandpath):
		basepath.intersectPath(islandpath)
		islandpath.intersectPath(basepath)
		#basepath = deepcopy(basepath)
		#islandpath = deepcopy(islandpath)

		#find first intersecting segment
		first = None
		for i,segment in enumerate(basepath):
			if islandpath.isInside(segment.midPoint()): first = i
		if first is None:
			print("not intersecting paths")
			return None

		#generate intersected path
		newisland = Path("new")
		A = None
		for i in xrange(first,2*len(basepath)+first):
			j = i%len(basepath)
			segment = basepath[j]
			if segment.length()<EPS: continue #ignore zero length segments
			if not islandpath.isInside(segment.midPoint()):
				if A is None:
					A = segment.A
				newisland.append(segment)
			else:
				if A is not None:
					newisland.extend(self.findSubpath(islandpath,A,segment.A,basepath))
					print("new",newisland)
					A = None
				#newisland.append(segment)
		#for i,seg in enumerate(newisland):
		#	newisland[i].correct();
		print("new2",newisland)
		return newisland
