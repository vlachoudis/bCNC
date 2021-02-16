#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @DodoLaSaumure Pierre KLein
# Date: 9 feb 2021

from __future__ import print_function
from __future__ import print_function
__author__ = "@DodoLaSaumure  (Pierre Klein)"
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

def pocket(selectedblocks, RecursiveDepth,ProfileDir,CutDir,AdditionalCut,Overcuts, CustomRecursiveDepth,
		ignoreIslands,
		allowG1, diameter, stepover, name,gcode):
	undoinfo = []
	msg = ""
	newblocks = []
	allblocks = gcode.blocks
	islandslist = []
	outpathslist= []
	ignoreIslandschoicedict = {
		"Regard all islands except tabs":0,
		"Ignore all islands":1,
		"Regard only selected islands":2,
		}
	ignoreIslandschoice = ignoreIslandschoicedict.get(ignoreIslands,0)
	for bid,block in enumerate(allblocks):#all blocks
		if block.operationTest('island')and not block.operationTest('tab'):
			if ignoreIslandschoice==0:
				for islandPath in gcode.toPath(bid):
					islandslist.append(islandPath)
	for bid in reversed(selectedblocks):#selected blocks
		if allblocks[bid].name() in ("Header", "Footer"): continue
		newpath = []
		block = allblocks[bid]
		if block.operationTest('island')and not block.operationTest('tab') and ignoreIslandschoice==2:
			for islandPath in gcode.toPath(bid):
				islandslist.append(islandPath)
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
			if not block.operationTest('island'):
				outpathslist.append(path)
		MyPocket = PocketIsland(outpathslist,RecursiveDepth,ProfileDir,CutDir,AdditionalCut,
							Overcuts,CustomRecursiveDepth,
							ignoreIslands,
							allowG1,diameter,stepover,0,islandslist)
		newpathList =  MyPocket.getfullpath()
		#concatenate newpath in a single list and split2contours
		if allowG1 :
			MyFullPath = Path("Pocket")
			for path in newpathList :
				for seg in path:
					MyFullPath.append(seg)
			newpathList = MyFullPath.split2contours()
		if newpathList:
			# remember length to shift all new blocks
			# the are inserted before
			before = len(newblocks)
			undoinfo.extend(gcode.importPath(bid+1, newpathList,
				newblocks, True, False))
			new = len(newblocks)-before
			for i in range(before):
				newblocks[i] += new
			allblocks[bid].enable = False
	gcode.addUndo(undoinfo)

	# return new blocks inside the blocks list
	del selectedblocks[:]
	selectedblocks.extend(newblocks)
	return msg

class PocketIsland:
	def __init__(self,pathlist,RecursiveDepth,ProfileDir,CutDir,AdditionalCut, Overcuts,CustomRecursiveDepth,
				ignoreIslands,
				allowG1,diameter,stepover,depth,islandslist=[]):
		self.outpaths = pathlist
		self.islands = islandslist
		self.diameter = diameter
		self.stepover = stepover
		self.RecursiveDepth=RecursiveDepth
		self.ProfileDir=ProfileDir
		self.CutDir=CutDir
		self.AdditionalCut=float(AdditionalCut)
		self.Overcuts = bool(Overcuts)
		self.CustomRecursiveDepth=CustomRecursiveDepth
		self.childrenIslands = []
		self.childrenOutpath = []
		self.fullpath = []
		self.depth = depth
		self.islandG1SegList = Path("islandG1SegList")
		self.outPathG1SegList = Path("outPathG1SegList")
		self.ignoreIslands = ignoreIslands
		self.allowG1 = allowG1
		maxdepthchoice = {"Single profile":0,
						"Custom recursive depth":int(self.CustomRecursiveDepth-1),
						"Full pocket":100}
		profileDirChoice = {"inside":1.,"outside":-1.}
		cutDirChoice = {"conventional milling":1.,"climbing milling":-1.}
		self.selectCutDir = cutDirChoice.get(self.CutDir,1.)
		self.profiledir = profileDirChoice.get(self.ProfileDir,1.)
		if self.RecursiveDepth=="Full pocket" :
			self.profiledir=1.#to avoid making full pockets, with full recursive depth, outside the path
		maxdepth=maxdepthchoice.get(self.RecursiveDepth,0)
		import sys
		sys.setrecursionlimit(max(sys.getrecursionlimit(),maxdepth+10))
		if depth>maxdepth: return None
		self.eliminateOutsideIslands()
		self.inoutprofile()
		self.removeOutofProfileLinkingSegs()
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
			self.offset = -self.diameter / 2.0 +self.AdditionalCut
		else:
			self.offset = -self.diameter*self.stepover
		self.OutOffsetPathList = []
		for path in self.outpaths :
			p1=p2=None
			if len(path)>0:
				p1 = path[0].A
			if self.depth == 0 :
				path.directionSet(self.selectCutDir*float(self.profiledir))
			direct = path.direction()
			opath = path.offset(self.profiledir*self.offset*float(direct))
			opath.intersectSelf()
			opath.removeExcluded(path, abs(self.offset))
			if self.depth == 0 and self.Overcuts :
				opath.overcut(self.profiledir*self.offset*float(direct))
			if len(opath)>0:
				p2 = opath[0].A
				self.OutOffsetPathList.append(opath)
				if self.depth >0  and p1 is not None:
					self.outPathG1SegList.append(Segment(Segment.LINE,p1,p2))
		self.islandOffPaths = []
		for island in self.insideIslandList :
			p3=p4=None
			if len(island)>0:
				p3 = island[0].A
			if self.depth == 0 :
				island.directionSet(-self.selectCutDir*float(self.profiledir))
			direct = island.direction()
			offIsl = island.offset(-self.profiledir*self.offset*float(direct))
			if len(offIsl)>0:
				p4 = offIsl[0].A
			if self.depth >0 and p3 is not None and p4 is not None :
				self.islandG1SegList.append(Segment(Segment.LINE,p3,p4))
			offIsl.intersectSelf()
			offIsl.removeExcluded(island, abs(self.offset))
			if self.depth == 0 and self.Overcuts :
				offIsl.overcut(-self.profiledir*self.offset*float(direct))
			self.islandOffPaths.append(offIsl)

	def removeOutofProfileLinkingSegs(self):
		self.tmpoutG1 = deepcopy(self.outPathG1SegList)
		self.tmpinG1 = deepcopy(self.islandG1SegList)
		for i,seg in enumerate(self.outPathG1SegList) :
			for path in self.islandOffPaths :
				inside =path.isSegInside(seg)==1#outseg inside offsetislands =>pop
				if  inside and seg in self.tmpoutG1:
					self.tmpoutG1.remove(seg)
		for i,seg in enumerate(self.islandG1SegList):
			for path in self.OutOffsetPathList :
				outside = path.isSegInside(seg)<1#inseg outside offsetOutpaths => pop
				if outside and  seg in self.tmpinG1 : 
						self.tmpinG1.remove(seg)
		self.outPathG1SegList = self.tmpoutG1
		self.islandG1SegList = self.tmpinG1

	def interesect(self):
		self.IntersectedIslands = []
		for island in self.islandOffPaths :
			for path in self.OutOffsetPathList :
				path.intersectPath(island)
				island.intersectPath(path)
			for island2 in self.islandOffPaths :
				island.intersectPath(island2)
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
			if len(self.islandG1SegList) >0 :
				self.outPathG1SegList.extend(self.islandG1SegList)
			if self.allowG1 and len(self.outPathG1SegList)>0:
				for seg in self.outPathG1SegList :
					path = Path("SegPath")
					path.append(seg)
					self.CleanPath.append(path)
			self.fullpath.extend(self.CleanPath)
		return self.CleanPath

	def recurse(self):
		pcket = PocketIsland(self.childrenOutpath,self.RecursiveDepth,self.ProfileDir,
							self.CutDir,self.AdditionalCut,self.Overcuts, self.CustomRecursiveDepth,
							self.ignoreIslands,
							self.allowG1,self.diameter,self.stepover,self.depth+1,self.childrenIslands)
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
			("RecursiveDepth","Single profile,Full pocket,Custom recursive depth", "Single profile",  _("Recursive depth")),
			("CustomRecursiveDepth","int",1,_("Nb of contours (Custom Recursive Depth)")),
			("ProfileDir","inside,outside", "inside",  _("Profile direction if profile option selected")),
			("CutDir","conventional milling,climbing milling", "conventional milling",  _("Cut Direction,default is conventional")),
			("AdditionalCut"  ,         "mm" ,     0., _("Additional cut inside profile")),
			("Overcuts"  ,         "bool" ,     False, _("Overcuts inside corners")),
			("ignoreIslands",
				"Regard all islands except tabs,Ignore all islands,Regard only selected islands",
				"Regard all islands except tabs",_("Ignore islands)")),
			("allowG1",        "bool",    True, _("allow pocket paths linking segments(default yes)")),
		
		]
		self.help="""- Recursive depth : indicates the number of profile passes (single,custom number,full pocket)
- Nb of contours (Custom Recursive Depth) : indicates the number of contours if custom selected
- Profile direction : indicates the direction (inside / outside) for making profiles
- Cut Direction,default is conventional
- Additional cut inside profile : acts like a tool corrector inside the profile
- Overcuts inside corners : Overcuts allow milling in the corners of a box
- Ignore islands : Tabs are always ignored. You can select if all islands are active, none, or only selected
		"""
		self.buttons.append("exe")
	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		RecursiveDepth=self["RecursiveDepth"]
		ProfileDir=self["ProfileDir"]
		CutDir=self["CutDir"]
		AdditionalCut=self["AdditionalCut"]
		Overcuts = self["Overcuts"]
		CustomRecursiveDepth=self["CustomRecursiveDepth"]
		ignoreIslands = self["ignoreIslands"]
		allowG1 = self["allowG1"]
		name = self["name"]
		if name=="default" or name=="": name=None
		tool = app.tools["EndMill"]
		diameter = app.tools.fromMm(tool["diameter"])
		try:
			stepover = tool["stepover"] / 100.0
		except TypeError:
			stepover = 0.

		app.busy()
		selectedblocks = app.editor.getSelectedBlocks()
		msg = pocket(selectedblocks,RecursiveDepth,ProfileDir,CutDir,
					AdditionalCut, Overcuts,CustomRecursiveDepth,
					ignoreIslands,
					bool(allowG1), diameter, stepover,
					name,gcode = app.gcode)
		if msg:
			tkMessageBox.showwarning(_("Open paths"),
					_("WARNING: %s")%(msg),
						parent=app)
		app.editor.fill()
		app.editor.selectBlocks(selectedblocks)
		app.draw()
		app.notBusy()
		app.setStatus(_("Generate pocket path"))

##############################################
