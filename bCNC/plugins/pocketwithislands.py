#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018

from __future__ import print_function
from __future__ import print_function
__author__ = "@Pierre"
#__email__  = ""

__name__ = _("PocketIsland")
__version__ = "0.0.1"

import math
import os.path
import re
from CNC import CNC,Block#,toPath,importPath,addUndo
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
from bpath import EPS,eq,Path, Segment
from bmath import Vector
from copy import deepcopy

try:
	import Tkinter
	from Tkinter import *
	import tkMessageBox
except ImportError:
	import tkinter
	from tkinter import *
	import tkinter.messagebox as tkMessageBox

# =============================================================================
#==============================================================================

def pocket(blocks, diameter, stepover, name,gcode,items):
# 	pocket2(blocks, diameter, stepover, name, nested=False,islandsSelectedOnly=True,islandsLeave=True,items=None)
	undoinfo = []
	msg = ""
	newblocks = []

	islandslist = []

	for bid,block in enumerate(gcode.blocks):
# 				if islandsSelectedOnly and bid not in items: continue
		if block.operationTest('island'):
			for islandPath in gcode.toPath(bid):
				islandslist.append(islandPath)
	for bid in reversed(blocks):
		if gcode.blocks[bid].name() in ("Header", "Footer"): continue
		newpath = []
		for path in gcode.toPath(bid):
			if not path.isClosed():
				m = "Path: '%s' is OPEN"%(path.name)
				if m not in msg:
					if msg: msg += "\n"
					msg += m
				path.close()

			# Remove tiny segments
			path.removeZeroLength(abs(diameter)/100.)
			# Convert very small arcs to lines
			path.convert2Lines(abs(diameter)/10.)

			path.directionSet(1) #turn path to CW (conventional when milling inside)

			D = path.direction()
			if D==0: D=1

			remove = ["cut","reverse","climb","conventional","cw","ccw","pocket"]
			if name is None:
				path.name = Block.operationName(path.name, "pocket,conventional,cw", remove)
			else:
				path.name = Block.operationName(path.name, name, remove)

# 				newpath.extend(self._pocket2(path, -D*diameter, stepover, 0,bid,islands=islands))
			MyPocket = PocketIsland([path],diameter,stepover,0,islandslist)
			newpath =  MyPocket.getfullpath()
# 			newpath=self._pocket2(path, -D*diameter, stepover, 0,islandslist=islandslist)
# 				print ("newPath",newpath)
		if newpath:
			# remember length to shift all new blocks
			# the are inserted before
			before = len(newblocks)
			undoinfo.extend(gcode.importPath(bid+1, newpath,
				newblocks, True, False))
			new = len(newblocks)-before
			for i in range(before):
				newblocks[i] += new
			gcode.blocks[bid].enable = False
	gcode.addUndo(undoinfo)

	# return new blocks inside the blocks list
	del blocks[:]
	blocks.extend(newblocks)
	return msg

class PocketIsland:
	def __init__(self,pathlist,diameter,stepover,depth,islandslist=[]): 
		self.outpaths = pathlist
		self.islands = islandslist
		self.diameter = diameter
		self.stepover = stepover
		self.childrenIslands = []
		self.childrenOutpath = []
		self.children = []
		self.fullpath = []
		self.depth = depth
		maxdepth=100
		import sys
		sys.setrecursionlimit(max(sys.getrecursionlimit(),maxdepth+100))
		if depth>maxdepth: return None
		self.eliminateOutsideIslands()
		self.inoutprofile()
		self.interesect()
		self.removeOutOfProfile()
		self.removeInsideIslands()
		self.getNewPathAndIslands()
		self.getPaths()
		if len (self.CleanPath)>0:
			self.recurse()
		
	def eliminateOutsideIslands(self):
		self.insideIslandList = []
		for island in self.islands:
			for path in self.outpaths :
				if island.isPathInside(path)>=0:
					self.insideIslandList.append(island)

	def inoutprofile(self):
		if self.depth == 0:
			offset = -self.diameter / 2.0
		else:
			offset = -self.diameter*self.stepover
		self.OutOffsetPathList = []
		for path in self.outpaths :
			opath = path.offset(offset)
			opath.intersectSelf()
			opath.removeExcluded(path, offset)
			if len(opath)>0:
				self.OutOffsetPathList.append(opath)
		self.islandOffPaths = []
		for island in self.insideIslandList :
			self.islandOffPaths.append(island.offset(-offset))
	def interesect(self):
		self.IntersectedIslands = []
		self.newbase = [path for path in self.OutOffsetPathList]
		for island in self.islandOffPaths :
			for path in self.OutOffsetPathList :
				path.intersectPath(island)
				island.intersectPath(path)
			for island2 in self.islandOffPaths :
				island.intersectPath(island2)
			self.newbase.append(island)
			self.IntersectedIslands.append(island)

	def removeOutOfProfile(self):
		self.NewPaths = []
		newoutpath = Path("path")
		for path in self.OutOffsetPathList: 
			for seg in path:
				newoutpath.append(seg)
		for OutoffsetPath in self.OutOffsetPathList:
			for path in self.IntersectedIslands :
				for seg in path :
					inside = not OutoffsetPath.isSegInside(seg)==-1
					if inside:
						newoutpath.append(seg)
		purgednewoutpath= newoutpath.split2contours()#list of paths
		self.NewPaths.extend(purgednewoutpath)

	def removeInsideIslands(self):
		self.CleanPath = []
		cleanpath = Path("Path")
		for path in self.NewPaths :
			for seg in path :
				inside = False
				for island in self.IntersectedIslands :
					issegin = island.isSegInside(seg)==1
					if issegin:
						if not seg in island:
							inside = True
							break
				if not inside:
					cleanpath.append(seg)
		cleanpath = cleanpath.split2contours()
		self.CleanPath.extend(cleanpath)

	def getNewPathAndIslands(self):
		if len(self.CleanPath)==1:
			self.childrenOutpath = self.CleanPath
		else :
			for elt in self.CleanPath: #List of paths
				for elt2 in self.CleanPath :
						ins = elt2.isPathInside(elt)==1
						ident = elt2.isidentical(elt)
						addedelt2  = elt2 in self.childrenIslands 
						if ins and not ident and not addedelt2 :
							self.childrenIslands.append(elt2)
			for elt in self.CleanPath: #List of paths
				for elt2 in self.CleanPath:
						if not elt2 in self.childrenIslands and not elt2 in self.childrenOutpath:
							self.childrenOutpath.append(elt2)

	def getPaths(self):
		if len (self.CleanPath)>0:
			self.fullpath.extend(self.CleanPath)
		return self.CleanPath
	def recurse(self):
# 		pcket = self.parent.PocketLayerClass(self.parent,self.childrenOutpath,self.diameter,self.stepover,self.depth+1,self.childrenIslands)
		pcket = PocketIsland(self.childrenOutpath,self.diameter,self.stepover,self.depth+1,self.childrenIslands)
		self.fullpath.extend(pcket.getfullpath())

	def getfullpath(self) :
		return self.fullpath



class Tool(Plugin):
	__doc__ = _("Generate a pocket with Inside Islands")

	def __init__(self, master):
		Plugin.__init__(self, master, "PocketIsland")
		self.icon  = "pocketisland"
		self.group = "Development"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("endmill",   "db" ,    "", _("End Mill")),
		]
		self.buttons.append("exe")
	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		name = self["name"]
		if name=="default" or name=="": name=None
		tool = app.tools["EndMill"]
		diameter = app.tools.fromMm(tool["diameter"])
		try:
			stepover = tool["stepover"] / 100.0
		except TypeError:
			stepover = 0.

		app.busy()
		blocks = app.editor.getSelectedBlocks()
 
# 		app.pocket(name)
		msg = pocket(blocks, diameter, stepover, name,gcode = app.gcode,items=app.editor.getCleanSelection())
		if msg:
			tkMessageBox.showwarning(_("Open paths"),
					_("WARNING: %s")%(msg),
					parent=app)
		app.editor.fill()
		app.editor.selectBlocks(blocks)
		app.draw()
		app.notBusy()
		app.setStatus(_("Generate pocket path"))

##############################################
