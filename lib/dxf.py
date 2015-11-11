#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: dxf.py 3598 2015-10-16 13:07:06Z bnv $
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
import spline
from bmath import Vector

EPS  = 0.0001
EPS2 = EPS**2

# Just to avoid repeating errors
errors = {}

#------------------------------------------------------------------------------
def error(msg):
	global errors
	if msg in errors:
		errors[msg] += 1
	else:
		sys.stderr.write(msg)
		errors[msg] = 1

#==============================================================================
# Entity holder
#==============================================================================
class Entity(dict):
	CLOSED   = 0x01
	PERIODIC = 0x02
	RATIONAL = 0x04
	PLANAR   = 0x08
	LINEAR   = 0x10

	SPLINE_SEGMENTS  = 20
	ELLIPSE_SEGMENTS = 100

	#----------------------------------------------------------------------
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
	def init(self):
		self._start = None
		self._end = None

	#----------------------------------------------------------------------
	def point(self, idx=0):
		return Vector(self.get(10+idx,0), self.get(20+idx,0))
	point2D = point
	center  = point

	#----------------------------------------------------------------------
	def point3D(self, idx=0):
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
	def bulge(self):
		return self.get(42,0)

	#----------------------------------------------------------------------
	def flag(self):
		return self.get(70,0)

	#----------------------------------------------------------------------
	def isClosed(self):
		return bool(self.flag() & Entity.CLOSED)

	#----------------------------------------------------------------------
	# Return start point
	#----------------------------------------------------------------------
	def start(self):
		if self._start is not None:
			return self._start
		elif self.type == "LINE":
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
		elif self.type in ("POLYLINE", "LWPOLYLINE", "SPLINE"):
			self._start = Vector(self[10][0], self[20][0])
		elif self.type in ("POINT", "ELLIPSE"):
			self._start = self.point()
		else:
			#raise Exception("Cannot handle entity type %s"%(self.type))
			error("Cannot handle entity type: %s in layer: %s\n"%(self.type, self.name))
			self._start = self.point()
		return self._start

	#----------------------------------------------------------------------
	# Return end point
	#----------------------------------------------------------------------
	def end(self):
		if self._end is not None:
			return self._end
		elif self.type == "LINE":
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
		elif self.type in ("POLYLINE", "LWPOLYLINE", "SPLINE"):
			if self.isClosed():
				self._end = Vector(self[10][0], self[20][0])
			else:
				self._end = Vector(self[10][-1], self[20][-1])
		elif self.type == "POINT":
			self._end = self.point()
		else:
			#raise Exception("Cannot handle entity type %s"%(self.type))
			error("Cannot handle entity type: %s in layer: %s\n"%(self.type, self.name))
			self._end = self.point()
		return self._end

	#----------------------------------------------------------------------
	# Invert if needed to allow continuity of motion
	#----------------------------------------------------------------------
	def invert(self):
		self._invert = not self._invert
		self._start, self._end = self._end, self._start

	#----------------------------------------------------------------------
	# Convert entity to polyline
	#
	# FIXME needs to be adaptive to the precision requested from the saggita
	#----------------------------------------------------------------------
	def convert2Polyline(self):
		if self.type == "SPLINE":
			# Convert to polyline
			xyz  = zip(self[10], self[20], self[30])
			flag = int(self.get(70,0))
			closed   = bool(flag & Entity.CLOSED)
			periodic = bool(flag & Entity.PERIODIC)
			rational = bool(flag & Entity.RATIONAL)
			planar   = bool(flag & Entity.PLANAR)
			linear   = bool(flag & Entity.LINEAR)
			#for n in sorted(self.keys()): print n,"=",self[n]
			#print "closed=",closed
			#print "periodic=",periodic
			#print "rational=",rational
			#print "planar=",planar
			#print "linear=",linear
			#if closed: xyz.append(xyz[0])
			xx,yy,zz = spline.spline2Polyline(xyz, int(self[71]),
					closed, Entity.SPLINE_SEGMENTS)
			self[10] = xx
			self[20] = yy
			self[30] = zz
			self[42] = 0	# bulge FIXME maybe I should use it
			self.type = "LWPOLYLINE"

		elif self.type == "ELLIPSE":
			center = self.start()
			major  = self.point(1)
			ratio  = self.get(40,1.0)
			sPhi   = self.get(41,0.0)
			ePhi   = self.get(42,2.0*math.pi)

			# minor length
			major_length = major.normalize()
			minor_length = ratio*major_length

			xx = []
			yy = []
			nseg = int((ePhi-sPhi) / math.pi * Entity.ELLIPSE_SEGMENTS)
			dphi = (ePhi-sPhi)/float(nseg)
			phi = sPhi
			for i in range(nseg+1):
				vx = major_length*math.cos(phi)
				vy = minor_length*math.sin(phi)
				xx.append(vx*major[0] - vy*major[1] + center[0])
				yy.append(vx*major[1] + vy*major[0] + center[1])
				phi += dphi
			self[10] = xx
			self[20] = yy
			self[42] = 0	# bulge FIXME maybe I should use it
			self.type = "LWPOLYLINE"
		self.init()

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
	# Default drawing units for AutoCAD DesignCenter blocks:
	UNITLESS           = 0
	INCHES             = 1
	FEET               = 2
	MILES              = 3
	MILLIMETERS        = 4
	CENTIMETERS        = 5
	METERS             = 6
	KILOMETERS         = 7
	MICROINCHES        = 8
	MILS               = 9
	YARDS              = 10
	ANGSTROMS          = 11
	NANOMETERS         = 12
	MICRONS            = 13
	DECIMETERS         = 14
	DECAMETERS         = 15
	HECTOMETERS        = 16
	GIGAMETERS         = 17
	ASTRONOMICAL_UNITS = 18
	LIGHT_YEARS        = 19
	PARSECS            = 20

	# Convert Units to mm
	_TOMM = [    1.0,	# UNITLESS           = 0
		    25.4,	# INCHES             = 1
		 25.4*12,	# FEET               = 2
		1609.34e3,	# MILES              = 3
		     1.0,	# MILLIMETERS        = 4
		    10.0,	# CENTIMETERS        = 5
		  1000.0,	# METERS             = 6
		     1e6,	# KILOMETERS         = 7
		 25.4e-6,	# MICROINCHES        = 8
		 25.4e-3,	# MILS               = 9
		   915.4,	# YARDS              = 10
		    1e-7,	# ANGSTROMS          = 11
		    1e-9,	# NANOMETERS         = 12
		    1e-6,	# MICRONS            = 13
		   100.0,	# DECIMETERS         = 14
		 10000.0,	# DECAMETERS         = 15
		100000.0,	# HECTOMETERS        = 16
		    1e12,	# GIGAMETERS         = 17
		1.496e14,	# ASTRONOMICAL_UNITS = 18
		9.461e18,	# LIGHT_YEARS        = 19
		3.086e19	# PARSECS            = 20
	 ]

	#----------------------------------------------------------------------
	def __init__(self, filename=None, mode="r"):
		self._f = None
		if filename:
			self.open(filename,mode)
		self.title  = "dxf-class"
		self.units  = DXF.UNITLESS
		errors.clear()

	#----------------------------------------------------------------------
	# Convert units to another format
	#----------------------------------------------------------------------
	def convert(self, value, units):
		# Convert to another type of units
		f = self._TOMM[self.units] / DXF._TOMM[units]

		if isinstance(value,float):
			return value * f

		elif isinstance(value,Vector):
			new = Vector(value)
			for i in range(len(value)):
				new[i] *= f
			return new

		elif isinstance(value,list):
			new = []
			for x in value:
				new.append(x*f)
			return new

		else:
			raise Exception("Cannot convert type %s %s"%(type(value),str(value)))

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
			error("Error reading line %s\n"%(line))
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
		var = None
		while True:
			tag,value = self.read()
			if tag is None or (tag == 0 and value=="ENDSEC"):
				return
			elif tag == 9:
				var = value
			elif tag == 70:
				if var == "$MEASUREMENT":
					value = int(value)
					if value == 0:
						self.units = DXF.INCHES
					else:
						self.units = DXF.MILLIMETERS
				elif var == "$INSUNITS":
					self.units = int(value)

	#----------------------------------------------------------------------
	# Read vertex for POLYLINE
	# Very bad!!
	#----------------------------------------------------------------------
	def readVertex(self, entity):
		entity[10] = []
		entity[20] = []
		entity[30] = []
		entity[42] = []

		x = 0.
		y = 0.
		z = 0.
		bulge = None
		while True:
			tag,value = self.read()
			#print tag,value
			if tag is None: return
			if tag==0:
				if bulge is None:
					entity[42].append(0)
				else:
					bulge = None

				if value == "SEQEND":
					# Vertex sequence end
					tag,value = self.read()
					if tag!=8: self.push(tag,value)
					# Correct bulge
					if not entity[42]: entity[42] = 0
					return
				elif value != "VERTEX":
					raise Exception("Entity %s found in wrong context"%(value))

			elif tag in (10,20,30):
				entity[tag].append(value)

			elif tag == 42:
				bulge = value
				entity[tag].append(value)

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
				if entity.type == "POLYLINE":
					self.readVertex(entity)
					return entity
				else:
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
			#for n,v in entity.items(): print n,":",v

			if entity.type in ("ELLIPSE", "SPLINE"):
				entity.convert2Polyline()

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
		self.write( 9, "$MEASUREMENT")
		if self.units == DXF.MILLIMETERS:
			self.write(70, 1)
		else:
			self.write(70, 0)
		self.write( 9, "$INSUNITS")
		self.write(70, self.units)
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
#	from dxfwrite.algebra import CubicSpline, CubicBezierCurve
	dxf = DXF(sys.argv[1],"r")
	dxf.readFile()
	dxf.close()
#	for name,layer in dxf.layers.items():
#		print "#",name
#		for entity in layer.entities:
#			print entity.name, entity.type
#			if entity.type == "SPLINE":
#				xy = zip(entity[10], entity[20])
#				cs = CubicBezierCurve(xy)
#				for x,y in cs.approximate(100):
#					print x,y

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
