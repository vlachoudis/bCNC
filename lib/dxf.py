#!/usr/bin/python
# -*- coding: latin1 -*-
<<<<<<< HEAD
# $Id: dxf.py 3510 2015-05-21 08:40:19Z bnv $
=======
# $Id: dxf.py 3537 2015-08-11 08:56:39Z bnv $
>>>>>>> master
#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# All rights not expressly granted under this license are reserved.
#
# Installation, use, reproduction, display of the
# software ("flair"), in source and binary forms, are
# permitted free of charge on a non-exclusive basis for
# internal scientific, non-commercial and non-weapon-related
# use by non-profit organizations only.
#
# For commercial use of the software, please contact the main
# author Vasilis.Vlachoudis@cern.ch for further information.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH

# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	10-Mar-2015
__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import sys
import math
from bmath import Vector

EPS  = 0.0001
EPS2 = EPS**2

#==============================================================================
# Entity holder
#==============================================================================
class Entity(dict):
	def __init__(self, t, n=None):
		self.type    = t
		self.name    = n
		self._invert = False
		self._start  = None
		self._end    = None

	#----------------------------------------------------------------------
	def __repr__(self):
		out = "%s %s %s %s"%(self.type, self.name, self.start(), self.end())
		if self.type=="ARC":
			out += " R=%g"%(self.radius())
			out += " sPhi=%g"%(self.startPhi())
			out += " ePhi=%g"%(self.endPhi())
		return out

	#----------------------------------------------------------------------
	def point(self,idx=0):
		return Vector(self.get(10+idx,0), self.get(20+idx,0))
	point2D = point
	center  = point

	#----------------------------------------------------------------------
	def point3D(self,idx=0):
		return Vector(self.get(10+idx), self.get(20+idx), self.get(30+idx))

	#----------------------------------------------------------------------
	def radius(self):
		return self.get(40,0)

	#----------------------------------------------------------------------
	def startPhi(self):
		return self.get(50,0)

	#----------------------------------------------------------------------
	def endPhi(self):
		return self.get(51,0)

	#----------------------------------------------------------------------
	# Return start point
	#----------------------------------------------------------------------
	def start(self):
		if self._start is not None: return self._start

		if self.type == "LINE":
			self._start = self.point()
		elif self.type == "CIRCLE":
			x,y = self.point()
			r = self.radius()
			self._start = self._end = Vector(x+r,y)
		elif self.type == "ARC":
			x,y = self.point()
			r = self.radius()
			s = math.radians(self.startPhi())
			self._start = Vector(x+r*math.cos(s), y + r*math.sin(s))
		elif self.type == "LWPOLYLINE":
			self._start = Vector(self[10][0], self[20][0])
		#elif self.type == "ELLIPSE":
		#elif self.type == "SPLINE":
		elif self.type == "POINT":
			self._start = self.point()
		else:
			#raise Exception("Cannot handle entity type %s"%(self.type))
			sys.stderr.write("Cannot handle entity type %s: %s\n"%(self.type, self.name))
			self._start = self.point()

		return self._start

	#----------------------------------------------------------------------
	# Return end point
	#----------------------------------------------------------------------
	def end(self):
		if self._end is not None: return self._end

		if self.type == "LINE":
			self._end = self.point(1)
		elif self.type == "CIRCLE":
			x,y = self.point()
			r = self.radius()
			self._start = self._end = Vector(x+r,y)
		elif self.type == "ARC":
			x,y = self.point()
			r = self.radius()
			s = math.radians(self.endPhi())
			self._end = Vector(x+r*math.cos(s), y + r*math.sin(s))
		elif self.type == "LWPOLYLINE":
			self._end = Vector(self[10][-1], self[20][-1])
		elif self.type == "POINT":
			self._end = self.point()
		else:
			#raise Exception("Cannot handle entity type %s"%(self.type))
			sys.stderr.write("Cannot handle entity type %s: %s\n"%(self.type, self.name))
			self._end = self.point()

		return self._end

	#----------------------------------------------------------------------
	# Invert if needed to allow continuity of motion
	#----------------------------------------------------------------------
	def invert(self):
		self._invert = not self._invert
		self._start, self._end = self._end, self._start

#==============================================================================
# DXF layer
#==============================================================================
class Layer:
	def __init__(self, name, tbl=None):
		self.name  = name
		if tbl is None:
			self.table = {}
		else:
			self.table = tbl
		self.entities = []

	#----------------------------------------------------------------------
	def append(self, item):
		self.entities.append(item)

	#----------------------------------------------------------------------
	def isFrozen(self):
		return self.table.get(70,0) & 1

#==============================================================================
# DXF importer/exporter class
#==============================================================================
class DXF:
	def __init__(self, filename=None, mode="r"):
		self._f = None
		if filename:
			self.open(filename,mode)
		self.title  = "dxf-class"

	#----------------------------------------------------------------------
	def open(self, filename, mode):
		self._f = open(filename, mode)
		self.layers = {}	# entities per layer diction of lists
		self._saved = None

	#----------------------------------------------------------------------
	def close(self):
		self._f.close()

	#----------------------------------------------------------------------
	def read(self):
		if self._saved is not None:
			tv = self._saved
			self._saved = None
			return tv

		line = self._f.readline()
		if not line: return None, None
		try:
			tag = int(line.strip())
		except:
			sys.stderr.write("Error reading line %s\n"%(line))
			return None,None
		value = self._f.readline().strip()
		try:
			value = int(value)
		except:
			try:
				value = float(value)
			except:
				pass
		return tag,value

	#----------------------------------------------------------------------
	def push(self, tag, value):
		self._saved = (tag, value)

	#----------------------------------------------------------------------
	def mustbe(self, t, v=None):
		tag,value = self.read()
		if t!=tag:
			self.push(tag,value)
			return False
		if v is not None and v!=value:
			self.push(tag,value)
			return False
		return True
			#raise Exception("DXF expecting %d,%s found %s,%s"%(t,v,str(tag),str(value)))

	#----------------------------------------------------------------------
	# Skip section
	#----------------------------------------------------------------------
	def skipSection(self):
		while True:
			tag,value = self.read()
			if tag is None or (tag == 0 and value=="ENDSEC"):
				return

	#----------------------------------------------------------------------
	# Read the title as the first item in DXF
	#----------------------------------------------------------------------
	def readTitle(self):
		tag,value = self.read()
		if tag == 999:
			self.title = value
		else:
			self.push(tag,value)

	#----------------------------------------------------------------------
	# Read header section
	#----------------------------------------------------------------------
	def readHeader(self):
		self.skipSection()

	#----------------------------------------------------------------------
	# Read and return one entity
	#----------------------------------------------------------------------
	def readEntity(self):
		tag, value = self.read()
		if value == "ENDSEC":
			return None
		else:
			entity = Entity(value)

		while True:
			tag,value = self.read()
			#print tag,value
			if tag is None: return
			if tag==0:
				self.push(tag,value)
				return entity
			elif tag==8:
				entity.name = str(value)
			else:
				existing = entity.get(tag)
				if existing is None:
					entity[tag] = value
				elif isinstance(existing,list):
					existing.append(value)
				else:
					entity[tag] = [existing, value]

	#----------------------------------------------------------------------
	# Read entities section
	#----------------------------------------------------------------------
	def readEntities(self):
		while True:
			entity = self.readEntity()
			if entity is None: return
			#print ">>>",entity
			if entity.type in ("SPLINE","ELLIPSE"): continue
			try:
				layer = self.layers[entity.name]
			except KeyError:
				layer = Layer(entity.name)
				self.layers[entity.name] = layer
			layer.append(entity)

	#----------------------------------------------------------------------
	# Read one table
	#----------------------------------------------------------------------
	def readTable(self):
		tag, value = self.read()
		if value == "ENDSEC":
			return None
		else:
			table = {}
		table["type"] = value

		while True:
			tag,value = self.read()
			if tag is None: return
			if tag==0:
				self.push(tag,value)
				return table
			elif tag==2:
				table["name"] = str(value)
			else:
				table[tag] = value

	#----------------------------------------------------------------------
	# Read tables section
	#----------------------------------------------------------------------
	def readTables(self):
		while True:
			table = self.readTable()
			if table is None: return
			if table["type"] == "LAYER":
				name = table.get("name")
				if name is not None:
					self.layers[name] = Layer(name, table)

	#----------------------------------------------------------------------
	# Read section based on type
	#----------------------------------------------------------------------
	def readSection(self):
		if not self.mustbe(0,"SECTION"): return None
		tag,value = self.read()
		if tag is None: return None
		if tag != 2:
			self.push()
			return None
		#print "-"*40,value,"-"*40
		if value == "HEADER":
			self.readHeader()

		elif value == "ENTITIES":
			self.readEntities()

		elif value == "TABLES":
			self.readTables()

		else:
			self.skipSection()

		return value

	#----------------------------------------------------------------------
	# Read whole DXF and store it in the self.layers
	#----------------------------------------------------------------------
	def readFile(self):
		self.readTitle()
		while self.readSection() is not None: pass
		self.mustbe(0,"EOF")

	#----------------------------------------------------------------------
	# Sort layer in continuation order of entities
	# where the end of of the previous is the start of the new one
	#
	# Add an new special marker for starting an entity with TYPE="START"
	#----------------------------------------------------------------------
	def sortLayer(self, name):
		entities = self.layers[name].entities
		new   = []

		# Move all points to beginning
		i = 0
		while i < len(entities):
			if entities[i].type == "POINT":
				new.append(entities[i])
				del entities[i]
			else:
				i += 1

		if not entities: return new

		# ---
		def pushStart():
			# Find starting point and add it to the new list
			start = Entity("START",name)
			start._start = start._end = entities[0].start()
			new.append(start)

		# Push first element as start point
		pushStart()

		# Repeat until all entities are used
		while entities:
			# End point
			ex,ey = new[-1].end()
			#print
			#print "*-*",new[-1].start(),new[-1].end()

			# Find the entity that starts after the layer
			for i,entity in enumerate(entities):
				# Try starting point
				sx,sy = entity.start()
				d2 = (sx-ex)**2 + (sy-ey)**2
				err = EPS2 * ((abs(sx)+abs(ex))**2 + (abs(sy)+abs(ey))**2 + 1.0)
				if d2 < err:
					new.append(entity)
					del entities[i]
					break

				# Try ending point (inverse)
				sx,sy = entity.end()
				d2 = (sx-ex)**2 + (sy-ey)**2
				err = EPS2 * ((abs(sx)+abs(ex))**2 + (abs(sy)+abs(ey))**2 + 1.0)
				if d2 < err:
					entity.invert()
					new.append(entity)
					del entities[i]
					break

			else:
				# Not found push a new start point and
				pushStart()

		self.layers[name].entities = new
		return new

	#----------------------------------------------------------------------
	# Write one tag,value pair
	#----------------------------------------------------------------------
	def write(self, tag, value):
		self._f.write("%d\n%s\n"%(tag,str(value)))

	#----------------------------------------------------------------------
	# Write a vector for index idx
	#----------------------------------------------------------------------
	def writeVector(self, idx, x, y, z=None):
		self.write(10+idx, "%g"%(x))
		self.write(20+idx, "%g"%(y))
		if z is not None: self.write(30+idx, "%g"%(z))

	#----------------------------------------------------------------------
	# Write DXF standard header
	#----------------------------------------------------------------------
	def writeHeader(self):
		self.write(999, self.title)
		self.write( 0, "SECTION")
		self.write( 2, "HEADER")
		self.write( 9, "$ACADVER")
		self.write( 1, "AC1009")
		self.write( 9, "$EXTMIN")
		self.writeVector( 0, 0,0,0)
		self.write( 9, "$EXTMAX")
		self.writeVector( 0, 1000,1000,0)
		self.write( 0, "ENDSEC")

		self.write( 0,"SECTION")
		self.write( 2,"ENTITIES")

	#----------------------------------------------------------------------
	# Write End Of File
	#----------------------------------------------------------------------
	def writeEOF(self):
		self.write( 0, "ENDSEC")
		self.write( 0, "EOF")

	#----------------------------------------------------------------------
	def point(self, x, y, name=None):
		self.write( 0, "POINT")
		if name: self.write( 8, name)
		self.writeVector(0, x, y)

	#----------------------------------------------------------------------
	def line(self, x0, y0, x1, y1, name=None):
		self.write( 0, "LINE")
		if name: self.write( 8, name)
		self.writeVector(0, x0, y0)
		self.writeVector(1, x1, y1)

	#----------------------------------------------------------------------
	def circle(self, x, y, r, name=None):
		self.write( 0, "CIRCLE")
		if name: self.write( 8, name)
		self.writeVector(0, x, y)
		self.write(40, r)

	#----------------------------------------------------------------------
	def arc(self, x, y, r, start, end, name=None):
		self.write( 0, "ARC")
		if name: self.write( 8, name)
		self.writeVector(0, x, y)
		self.write(40, r)
		#if start > end: start,end = end,start
		self.write(50, start)
		self.write(51, end)

	#----------------------------------------------------------------------
	def polyline(self, pts, flag=0, name=None):
		self.write( 0, "LWPOLYLINE")
		if name: self.write( 8, name)
		self.write(100,"AcDbEntity")
		self.write(90, len(pts))
		self.write(70, flag)	# bit mask flag? 0=default, 1=closed, 128=plinegen
		self.write(43, 0)	# constant width
		for x,y in pts:
			self.writeVector(0,x,y)

#------------------------------------------------------------------------------
if __name__ == "__main__":
	dxf = DXF(sys.argv[1],"r")
	dxf.readFile()
	dxf.close()
#	for name,layer in dxf.layers.items():
#		#print "Frozen=",not bool(layer.isFrozen())
#		for entity in dxf.sortLayer(name):
#			print entity, entity._invert

#	dxf = DXF("test.dxf","w")
#	dxf.writeHeader()
#	#dxf.line( 0, 0, 20, 0, "line1")
#	#dxf.line(20, 0, 20,10, "line1")
#	#dxf.line(20,10,  0,10, "line1")
#	#dxf.line( 0,10,  0, 0, "line1")
#	#dxf.circle(20,10,5,"circle")
#
#	dxf.arc(0,0,5,30,90,"arc")
#	dxf.arc(0,0,10,90,30,"arc")
#	dxf.line(8.660254037844387, 5, 20,30,"arc")
#	dxf.line(0,5,0,10,"arc")
#	dxf.arc(0,0,20,90,30,"arc")
#
#	#dxf.polyline([(100,0),(200,200),(100,200)],"polyline")
#	dxf.writeEOF()
#	dxf.close()
#
#	dxf.open("test2.dxf","r")
#	dxf.readFile()
#	dxf.close()
#	#print "-"*80
#	#for name in dxf.layers:
#	#	for entity in dxf.sortLayer(name):
#	#		print entity
#	dxf.close()
