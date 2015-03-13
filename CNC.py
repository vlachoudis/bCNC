# -*- coding: latin1 -*-
# $Id: CNC.py,v 1.8 2014/10/15 15:03:49 bnv Exp $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

import os
import re
import sys
import math
from stat import ST_MTIME
import string

import undo
import Macros
import Unicode

from dxf import DXF
from bmath import *

IDPAT    = re.compile(r".*\bid:\s*(.*?)\)")
PARENPAT = re.compile(r"(.*)(\(.*?\))(.*)")
CMDPAT   = re.compile(r"([A-Za-z])")
BLOCKPAT = re.compile(r"^\(Block-([A-Za-z]+): (.*)\)")

FMT = "%.4f"

#------------------------------------------------------------------------------
# Return a value combined from two dictionaries new/old
#------------------------------------------------------------------------------
def getValue(name,new,old,default=0.0):
	try:
		return new[name]
	except:
		try:
			return old[name]
		except:
			return default

#==============================================================================
# Probing class and linear interpolation
#==============================================================================
class Probe:
	def __init__(self):
		self.init()

	#----------------------------------------------------------------------
	def init(self):
		self.filename = ""
		self.xmin =   0.0
		self.ymin =   0.0
		self.zmin = -10.0

		self.xmax =  10.0
		self.ymax =  10.0
		self.zmax =   3.0

		self._xstep = 1.0
		self._ystep = 1.0

		self.xn = 5
		self.yn = 5

		self.feed = 100
		self.points  = []	# probe points
		self.matrix = []	# 2D matrix with Z coordinates
		self.zeroed = False	# if probe was zeroed at any location

	#----------------------------------------------------------------------
	def clear(self):
		del self.points[:]
		del self.matrix[:]
		self.zeroed = False	# if probe was zeroed at any location

	#----------------------------------------------------------------------
	def isEmpty(self): return len(self.matrix)==0

	#----------------------------------------------------------------------
	def makeMatrix(self):
		del self.matrix[:]
		for j in range(self.yn):
			self.matrix.append([0.0]*(self.xn))

	#----------------------------------------------------------------------
	# Load level information from file
	#----------------------------------------------------------------------
	def load(self, filename=None):
		if filename is not None:
			self.filename = filename
		self.clear()

		def read(f):
			while True:
				line = f.readline()
				if len(line)==0: raise
				line = line.strip()
				if line: return map(float, line.split())

		f = open(self.filename,"r")
		self.xmin, self.xmax, self.xn   = read(f)
		self.ymin, self.ymax, self.yn   = read(f)
		self.zmin, self.zmax, self.feed = read(f)

		self.xn = int(self.xn)
		self.yn = int(self.yn)

		self.makeMatrix()
		self.xstep()
		self.ystep()

		try:
			for j in range(self.yn):
				for i in range(self.xn):
					self.add(*read(f))
		except:
			raise
			#print "Error reading probe file",self.filename
		f.close()

	#----------------------------------------------------------------------
	# Save level information to file
	#----------------------------------------------------------------------
	def save(self, filename=None):
		if filename is not None:
			self.filename = filename
		f = open(self.filename,"w")
		f.write("%g %g %d\n"%(self.xmin, self.xmax, self.xn))
		f.write("%g %g %d\n"%(self.ymin, self.ymax, self.yn))
		f.write("%g %g %g\n"%(self.zmin, self.zmax, self.feed))
		f.write("\n\n")
		for j in range(self.yn):
			y = self.ymin + self._ystep*j
			for i in range(self.xn):
				x = self.xmin + self._xstep*i
				f.write("%g %g %g\n"%(x,y,self.matrix[j][i]))
			f.write("\n")
		f.close()

	#----------------------------------------------------------------------
	# Return step
	#----------------------------------------------------------------------
	def xstep(self):
		self._xstep = (self.xmax-self.xmin)/float(self.xn-1)
		return self._xstep

	def ystep(self):
		self._ystep = (self.ymax-self.ymin)/float(self.yn-1)
		return self._ystep

	#----------------------------------------------------------------------
	def scan(self):
		lines = []
		self.makeMatrix()
		for j in range(self.yn):
			y = self.ymin + self._ystep*j
			for i in range(self.xn):
				x = self.xmin + self._xstep*i
				lines.append("G0Z%.4f\n"%(self.zmax))
				lines.append("G0X%.4fY%.4f\n"%(x,y))
				lines.append("G38.2Z%.4fF%g\n"%(self.zmin, self.feed))
		lines.append("G0Z%.4f\n"%(self.zmax))
		lines.append("G0X%.4fY%.4f\n"%(self.xmin,self.ymin))
		return lines

	#----------------------------------------------------------------------
	# Add a probed point to the list and the 3D matrix
	#----------------------------------------------------------------------
	def add(self, x,y,z):
		self.points.append([x,y,z])
		i = round((x-self.xmin) / self._xstep)
		if i<0.0 or i>self.xn: return

		j = round((y-self.ymin) / self._ystep)
		if j<0.0 or j>self.yn: return

		rem = abs(x - (i*self._xstep + self.xmin))
		if rem > self._xstep/10.0: return

		rem = abs(y - (j*self._ystep + self.ymin))
		if rem > self._ystep/10.0: return

		try:
			self.matrix[int(j)][int(i)] = z
		except IndexError:
			pass

	#----------------------------------------------------------------------
	# Make z-level relative to the location of (x,y,0)
	#----------------------------------------------------------------------
	def setZero(self, x, y):
		del self.points[:]
		if self.isEmpty():
			self.zeroed = False
			return
		zero = self.interpolate(x,y)
		self.xstep()
		self.ystep()
		for j,row in enumerate(self.matrix):
			y = self.ymin + self._ystep*j
			for i in range(len(row)):
				x = self.xmin + self._xstep*i
				row[i] -= zero
				self.points.append([x,y,row[i]])
		self.zeroed = True

	#----------------------------------------------------------------------
	def interpolate(self, x, y):
		ix = (x-self.xmin) / self._xstep
		jy = (y-self.ymin) / self._ystep
		i = int(math.floor(ix))
		j = int(math.floor(jy))

		if i<0:
			i = 0
		elif i>=self.xn-1:
			i = self.xn-2

		if j<0:
			j = 0
		elif j>=self.yn-1:
			j = self.yn-2

		a = ix - i
		b = jy - j
		a1 = 1.0 - a
		b1 = 1.0 - b

		return a1*b1 * self.matrix[j][i]   + \
		       a1*b  * self.matrix[j+1][i] + \
		       a *b1 * self.matrix[j][i+1] + \
		       a *b  * self.matrix[j+1][i+1]

	#----------------------------------------------------------------------
	# Split line into multiple segments correcting for Z if needed
	# return only end points
	#----------------------------------------------------------------------
	def splitLine(self, x1, y1, z1, x2, y2, z2):
		#print "splitLine:",x1, y1, z1, x2, y2, z2
		#import pdb
		#pdb.set_trace()
		i1 = int(math.floor((x1-self.xmin) / self._xstep))
		i2 = int(math.floor((x2-self.xmin) / self._xstep))

		j1 = int(math.floor((y1-self.ymin) / self._ystep))
		j2 = int(math.floor((y2-self.ymin) / self._ystep))

		dx = x2-x1
		dy = y2-y1
		dz = z2-z1
		if dx==0.0 and dy==0.0:
			return [(x2,y2,z2+self.interpolate(x2,y2))]

		rxy = math.sqrt(dx*dx+dy*dy)
		r   = math.sqrt(dx*dx + dy*dy + dz*dz)
		dx /= rxy
		dy /= rxy
		# add correction for the slope in Z, versut the travel in XY
		dz  =  dz * rxy/(dx*dx + dy*dy + dz*dz)

		if abs(dx)<1e-10: dx = 0.0
		if abs(dy)<1e-10: dy = 0.0

		# Next intersection
		if dx>0.0:
			i = i1+1
			i2 += 1
		else:
			i = i1

		if dy>0.0:
			j = j1+1
			j2 += 1
		else:
			j = j1

		xn = x = x1
		yn = y = y1
		z  = z1
		tx = ty = 1E10

		segments = []
		endx = False
		endy = False
		while i!=i2 or j!=j2:
			if dx!=0.0:
				xn = self.xmin + i*self._xstep
				tx = (xn - x1) / dx
			if dy!=0.0:
				yn = self.ymin + j*self._ystep
				ty = (yn - y1) / dy

			if tx < ty:
				x = xn
				y = y1 + tx*dy
				z = z1 + tx*dz
				if dx > 0.0:
					i += 1
					endx = i>=i2
				else:
					i -= 1
					endx = i<=i2
			else:
				x = x1 + ty*dx
				y = yn
				z = z1 + ty*dz
				if dy > 0.0:
					j += 1
					endy = j>=j2
				else:
					j -= 1
					endy = j<=j2
			segments.append((x,y,z+self.interpolate(x,y)))
		segments.append((x2,y2,z2+self.interpolate(x2,y2)))
		#print "segments=",segments
		return segments

#==============================================================================
# Command operations on a CNC
#==============================================================================
class CNC:
	inch           = False
	acceleration_x = 25.0	# mm/s^2
	acceleration_y = 25.0	# mm/s^2
	acceleration_z = 25.0	# mm/s^2
	feedmax_x      = 3000
	feedmax_y      = 3000
	feedmax_z      = 2000
	travel_x       = 370
	travel_y       = 205
	travel_z       = 100
	accuracy       = 0.02	# sagitta error during arc conversion
	decimal        = 4
	startup        = "G90"

	_safeZ         = 3.0	# mm (default value to be copied on each project)

	#----------------------------------------------------------------------
	def __init__(self):
		self.accuracy       = 0.02		# sagitta error during arc conversion
		self.safeZ          = CNC._safeZ	# mm
		self.initPath()

	#----------------------------------------------------------------------
	@staticmethod
	def loadConfig(config):
		section = "CNC"
		CNC.inch           = not bool( config.get(section, "units"))
		CNC.acceleration_x = float(config.get(section, "acceleration_x"))
		CNC.acceleration_y = float(config.get(section, "acceleration_y"))
		CNC.acceleration_z = float(config.get(section, "acceleration_z"))
		CNC.feedmax_x      = float(config.get(section, "feedmax_x"))
		CNC.feedmax_y      = float(config.get(section, "feedmax_y"))
		CNC.feedmax_z      = float(config.get(section, "feedmax_z"))
		CNC.travel_x       = float(config.get(section, "travel_x"))
		CNC.travel_y       = float(config.get(section, "travel_y"))
		CNC.travel_z       = float(config.get(section, "travel_z"))
		CNC.travel_z       = float(config.get(section, "travel_z"))
		CNC.accuracy       = float(config.get(section, "accuracy"))
		CNC._safeZ         = float(config.get(section, "safe_z"))
		CNC.decimal        = int(  config.get(section, "round"))
		CNC.startup        =       config.get(section, "startup")
		CNC.header         =       config.get(section, "header")
		CNC.footer         =       config.get(section, "footer")

	#----------------------------------------------------------------------
	@staticmethod
	def saveConfig(config):
		pass

	#----------------------------------------------------------------------
	def initPath(self, x=None, y=None, z=None):
		if x is None:
			self.x = self.xval = 0
		else:
			self.x = self.xval = x
		if y is None:
			self.y = self.yval = 0
		else:
			self.y = self.yval = y
		if z is None:
			self.z = self.zval = 0
		else:
			self.z = self.zval = z
		self.ival = self.jval = self.kval = 0.0
		self.dx   = self.dy   = self.dz   = 0.0
		self.di   = self.dj   = self.dk   = 0.0
		self.rval = 0.0
		self.pval = 0.0
		self.unit = 1.0

		self.xmin = self.ymin = self.zmin =  1000000.0
		self.xmax = self.ymax = self.zmax = -1000000.0

		self.absolute    = True
		self.gcode       = None
		self.feed        = 0
		self.totalLength = 0.0
		self.totalTime   = 0.0

	#----------------------------------------------------------------------
	def isMarginValid(self):
		return	self.xmin < self.xmax and \
			self.ymin < self.ymax and \
			self.zmin < self.zmax

	#----------------------------------------------------------------------
	# Number formating
	#----------------------------------------------------------------------
	def fmt(self, c, v):
		return "%s%g"%(c,round(v,self.decimal))

	#----------------------------------------------------------------------
	# @return line in broken a list of commands, None if empty or comment
	#----------------------------------------------------------------------
	def parseLine(self, line):
		while True:	# repeatedly remove parenthesis
			pat = PARENPAT.match(line)
			if pat:
				line = pat.group(1) + pat.group(3)
			else:
				break

		# skip empty lines
		if len(line)==0 or line[0] in ("%","(","#",";"):
			return None

		# process command
		# strip all spaces
		line = line.replace(" ","")

		# break line into tokens
		#cmd = []
		#for ch in line:
		#

		# Insert space before each command
		line = re.sub(CMDPAT,r" \1",line).lstrip()
		return line.split()

	#----------------------------------------------------------------------
	# Create path for one g command
	#----------------------------------------------------------------------
	def processPath(self, cmds):
		for cmd in cmds:
			c = cmd[0].upper()
			try:
				value = float(cmd[1:])
			except:
				value = 0

			if   c == "X":
				self.xval = value*self.unit
				if not self.absolute:
					self.xval += x

			elif c == "Y":
				self.yval = value*self.unit
				if not self.absolute:
					self.yval += self.y

			elif c == "Z":
				self.zval = value*self.unit
				if not self.absolute:
					self.zval += self.z

			elif c == "I":
				self.ival = value*self.unit

			elif c == "J":
				self.jval = value*self.unit

			elif c == "K":
				self.kval = value*self.unit

			elif c == "R":
				self.rval = value*self.unit

			elif c == "P":
				self.pval = value

			elif c == "F":
				self.feed = value*self.unit

			elif c == "M":
				self.gcode = None

			elif c == "N":
				pass

			elif c == "G":
				self.gcode = int(value)

				# Execute immediately
				if self.gcode==20:	# Switch to inches
					if self.inch:
						self.unit = 1.0
					else:
						self.unit = 25.4

				elif self.gcode==21:	# Switch to mm
					if self.inch:
						self.unit = 1.0/25.4
					else:
						self.unit = 1.0

				elif self.gcode==90:
					self.absolute = True

				elif self.gcode==91:
					self.absolute = False

		self.dx = self.xval - self.x
		self.dy = self.yval - self.y
		self.dz = self.zval - self.z

	#----------------------------------------------------------------------
	# Return center x,y,z,r for arc motions 2,3 and set self.rval
	#----------------------------------------------------------------------
	def motionCenter(self):
		if self.rval>0.0:
			ABx = self.xval-self.x
			ABy = self.yval-self.y
			Cx  = 0.5*(self.x+self.xval)
			Cy  = 0.5*(self.y+self.yval)
			AB  = math.sqrt(ABx**2 + ABy**2)
			try: OC  = math.sqrt(self.rval**2 - AB**2/4.0)
			except: OC = 0.0
			if self.gcode==2: OC = -OC
			if AB != 0.0:
				xc  = Cx - OC*ABy/AB
				yc  = Cy + OC*ABx/AB
			else:
				# Error!!!
				xc = self.x
				yc = self.y
			zc  = self.z
		else:
			# Center
			xc = self.x + self.ival
			yc = self.y + self.jval
			zc = self.z + self.kval
			self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)
			#r2 = math.sqrt((self.xval-xc)**2 + (self.yval-yc)**2 + (self.zval-zc)**2)
			#if abs((self.rval-r2)/self.rval) > 0.01:
			#	print>>sys.stderr, "ERROR arc", r2, self.rval
		return xc,yc,zc

	#----------------------------------------------------------------------
	# Create path for one g command
	#----------------------------------------------------------------------
	def motionPath(self):
		xyz = []

		# Execute g-code
		if self.gcode in (0,1):	# fast move or line
			if self.xval-self.x != 0.0 or \
			   self.yval-self.y != 0.0 or \
			   self.zval-self.z != 0.0:
				xyz.append((self.x,self.y,self.z))
				xyz.append((self.xval,self.yval,self.zval))

		elif self.gcode in (2,3):	# CW=2,CCW=3 circle
			xyz.append((self.x,self.y,self.z))
			xc,yc,zc = self.motionCenter()
#			if self.rval>0.0:
#				ABx = self.xval-self.x
#				ABy = self.yval-self.y
#				Cx  = 0.5*(self.x+self.xval)
#				Cy  = 0.5*(self.y+self.yval)
#				AB  = math.sqrt(ABx**2 + ABy**2)
#				try: OC  = math.sqrt(self.rval**2 - AB**2/4.0)
#				except: OC = 0.0
#				if self.gcode==2: OC = -OC
#				if AB != 0.0:
#					xc  = Cx - OC*ABy/AB
#					yc  = Cy + OC*ABx/AB
#				else:
#					# Error!!!
#					xc = self.x
#					yc = self.y
#				zc  = self.z
#			else:
#				# Center
#				xc = self.x + self.ival
#				yc = self.y + self.jval
#				zc = self.z + self.kval
#				self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)
#				#r2 = math.sqrt((self.xval-xc)**2 + (self.yval-yc)**2 + (self.zval-zc)**2)
#				#if abs((self.rval-r2)/self.rval) > 0.01:
#				#	print>>sys.stderr, "ERROR arc", r2, self.rval

			phi  = math.atan2(self.y-yc, self.x-xc)
			ephi = math.atan2(self.yval-yc, self.xval-xc)
			try:
				sagitta = 1.0-self.accuracy/self.rval
			except ZeroDivisionError:
				sagitta = 0.0
			if sagitta>0.0:
				df = 2.0*math.acos(sagitta)
				df = min(df, math.pi/4.0)
			else:
				df = math.pi/4.0

			if self.gcode==2:
				if ephi>=phi-1e-10: ephi -= 2.0*math.pi
				phi -= df
				while phi>ephi:
					self.x = xc + self.rval*math.cos(phi)
					self.y = yc + self.rval*math.sin(phi)
					phi -= df
					xyz.append((self.x,self.y,self.z))
			else:
				if ephi<=phi+1e-10: ephi += 2.0*math.pi
				phi += df
				while phi<ephi:
					self.x = xc + self.rval*math.cos(phi)
					self.y = yc + self.rval*math.sin(phi)
					phi += df
					xyz.append((self.x,self.y,self.z))

			xyz.append((self.xval,self.yval,self.zval))

		elif self.gcode==4:	# Dwell
			self.totalTime = self.pval

		return xyz

	#----------------------------------------------------------------------
	# move to end position
	#----------------------------------------------------------------------
	def motionPathEnd(self):
		if self.gcode in (0,1,2,3):
			self.x = self.xval
			self.y = self.yval
			self.z = self.zval

			if self.gcode >= 2: # reset at the end
				self.rval = self.ival = self.jval = self.kval = 0.0

		elif self.gcode in (28,30,92):
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0

	#----------------------------------------------------------------------
	def pathLength(self, xyz):
		# For XY plan
		p = xyz[0]
		length = 0.0
		for i in xyz:
			length += math.sqrt((i[0]-p[0])**2 + (i[1]-p[1])**2 + (i[2]-p[2])**2)
			p = i

		self.totalLength += length
		if self.gcode == 0:
			# FIXME calculate the correct time with the feed direction
			self.totalTime += length / self.feedmax_x
		else:
			try:
				self.totalTime += length / self.feed
			except:
				pass
		return length

	#----------------------------------------------------------------------
	def pathMargins(self, xyz):
		if self.gcode in (1,2,3):
			self.xmin = min(self.xmin,min([i[0] for i in xyz]))
			self.ymin = min(self.ymin,min([i[1] for i in xyz]))
			self.zmin = min(self.zmin,min([i[2] for i in xyz]))
			self.xmax = max(self.xmax,max([i[0] for i in xyz]))
			self.ymax = max(self.ymax,max([i[1] for i in xyz]))
			self.zmax = max(self.zmax,max([i[2] for i in xyz]))

#==============================================================================
# Block of g-code commands. A gcode file is represented as a list of blocks
# - Commands are grouped as (non motion commands Mxxx)
# - Basic shape from the first rapid move command to the last rapid z raise
#   above the working surface
#
# Inherits from list and contains:
#	- a list list of gcode lines
#	- (imported shape)
#==============================================================================
class Block(list):
	def __init__(self, name=None):
		self._name   = name
		self.visible = True	# Visible in drawing
		self.expand  = False	# Expand in editor
#		self.start   = None	# starting coordinates
#		self.stop    = None	# exit coordinates

		self._path   = []	# canvas drawing paths
		self.x = self.y = self.z = 0	# ending coordinates

	#----------------------------------------------------------------------
	def name(self):
		return self._name is None and "block" or self._name

	#----------------------------------------------------------------------
	def header(self):
		e = self.expand and Unicode.BLACK_DOWN_POINTING_TRIANGLE \
				or  Unicode.BLACK_RIGHT_POINTING_TRIANGLE
		v = self.visible and Unicode.BALLOT_BOX_WITH_X \
				or   Unicode.BALLOT_BOX
		return "%s %s %s - [%d]"%(e, v, self.name(), len(self))

	#----------------------------------------------------------------------
	def write(self, f):
		f.write("(Block-name: %s)\n"%(self.name()))
		f.write("(Block-expand: %d)\n"%(int(self.expand)))
		f.write("(Block-visible: %d)\n"%(int(self.visible)))
		f.write("%s\n"%("\n".join(self)))

	#----------------------------------------------------------------------
	def append(self, line):
		if line.startswith("(Block-"):
			pat = BLOCKPAT.match(line)
			if pat:
				name, value = pat.groups()
				value = value.strip()
				if name=="name":
					self._name = value
					return
				elif name=="expand":
					self.expand = bool(int(value))
					return
				elif name=="visible":
					self.visible = bool(int(value))
					return
		if self._name is None and ("id:" in line) and ("End" not in line):
			pat = IDPAT.match(line)
			if pat: self._name = pat.group(1)
		list.append(self, line)

	#----------------------------------------------------------------------
	def addPath(self, p):
		self._path.append(p)

	#----------------------------------------------------------------------
	def endPath(self, x, y, z):
		self.x = x
		self.y = y
		self.z = z

	#----------------------------------------------------------------------
	def resetPath(self):
		del self._path[:]

#==============================================================================
# Gcode file
#==============================================================================
class GCode:
	#----------------------------------------------------------------------
	def __init__(self):
		self.filename = ""
		self.probe    = Probe()
		self.blocks   = []	# list of blocks
		self.cnc      = CNC()
		self.undoredo = undo.UndoRedo()

		self._modified = 0
		#self._lastComment = 0

		# Iterator internal variables
		#self._iter = 0
		#self._iter_block = None
		#self._iter_block_i = 0

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename=None):
		if filename is not None: self.filename = filename
		try: f = open(self.filename,"r")
		except: return False

		self._modified = os.stat(self.filename)[ST_MTIME]

		self.probe.init()
		#self.split2blocks(f.read().replace("\x0d","").splitlines())

		self.undoredo.reset()

		self.cnc.initPath()
		del self.blocks[:]
		self._lastComment = 0
		for line in f:
			self._addLine(line[:-1].replace("\x0d",""))
		self._trim()

		f.close()
		return True

	#----------------------------------------------------------------------
	# Save to a file
	#----------------------------------------------------------------------
	def save(self, filename=None):
		if filename is not None: self.filename = filename
		try:
			f = open(self.filename,"w")
		except:
			return False
		for block in self.blocks:
			block.write(f)
		f.close()
		self._modified = os.stat(self.filename)[ST_MTIME]
		return True

	#----------------------------------------------------------------------
	# Load DXF file into gcode
	#----------------------------------------------------------------------
	def loadDXF(self, filename):
		try:
			dxf = DXF(filename,"r")
		except:
			return False
		dxf.readFile()
		dxf.close()

		block = None
		for name in dxf.layers.keys():
			for entity in dxf.sortLayer(name):	# sort and return new layer
				#print ">>>",entity
				if entity.type == "START":
					if block is not None:
						block.append("g0 %s"%((self.fmt("z",self.cnc.safeZ))))

					block = Block(entity.name)
					self.blocks.append(block)
					x,y = entity.start()
					block.append("g0 %s %s"%(self.fmt("x",x), self.fmt("y",y)))
					block.append("g0 %s"%(self.fmt("z",0.0)))

				elif entity.type == "LINE":
					x,y = entity.end()
					block.append("g1 %s %s"%(self.fmt("x",x), self.fmt("y",y)))

				elif entity.type == "CIRCLE":
					x,y = entity.point()
					r     = entity.radius()
					x += r
					block.append("g2 %s %s %s j0"% \
						(self.fmt("x",x), self.fmt("y",y), self.fmt("i",-r)))

				elif entity.type == "ARC":
					gcode = entity._invert and 2 or 3
					xc,yc = entity.point()
					x1,y1 = entity.start()
					x2,y2 = entity.end()
					r  = entity.radius()
					sp = math.radians(entity.startPhi())
					ep = math.radians(entity.endPhi())

					iv = xc - x1
					jv = yc - y1

					block.append("g%d %s %s %s %s"%(gcode,
						self.fmt("x",x2), self.fmt("y",y2),
						self.fmt("i",iv), self.fmt("j",jv)))

				elif entity.type == "LWPOLYLINE":
					xy = zip(entity[10], entity[20])
					if entity._invert: reverse(xy)
					xy.pop(0)

					for x,y in xy:
						block.append("g1 %s %s"%(self.fmt("x",x), self.fmt("y",y)))

		if block:
			block.append("g0 %s"%((self.fmt("z",self.cnc.safeZ))))
		return True

	#----------------------------------------------------------------------
	# Save in DXF format
	#----------------------------------------------------------------------
	def saveDXF(self, filename):
		try:
			dxf = DXF(filename,"w")
		except:
			return False
		dxf.writeHeader()
		for block in self.blocks:
			name = block.name()
			for line in block:
				cmds = self.cnc.parseLine(line)
				if cmds is None: continue
				self.cnc.processPath(cmds)
				if self.cnc.gcode == 1:	# line
					dxf.line(self.cnc.x, self.cnc.y, self.cnc.xval, self.cnc.yval, name)
				if self.cnc.gcode in (2,3):	# arc
					if self.cnc.rval > 0.0:
						pass
					else:
						# Center
						xc = self.cnc.x + self.cnc.ival
						yc = self.cnc.y + self.cnc.jval
						zc = self.cnc.z + self.cnc.kval
						self.cnc.rval = math.sqrt(self.cnc.ival**2 + self.cnc.jval**2 + self.cnc.kval**2)
					phi  = math.atan2(self.cnc.y-yc, self.cnc.x-xc)
					ephi = math.atan2(self.cnc.yval-yc, self.cnc.xval-xc)
					if self.cnc.gcode==2:
						if ephi<=phi+1e-10: ephi += 2.0*math.pi
					else:
						if ephi<=phi+1e-10: ephi += 2.0*math.pi
					dxf.arc(xc,yc,self.cnc.rval, math.degrees(phi), math.degrees(ephi),name)
				self.cnc.motionPathEnd()
		dxf.writeEOF()
		dxf.close()
		return True

	#----------------------------------------------------------------------
	# Check if a new version exists
	#----------------------------------------------------------------------
	def checkFile(self):
		try:
			return os.stat(self.filename)[ST_MTIME] > self._modified
		except:
			return False

	#----------------------------------------------------------------------
	def fmt(self, c, v): return self.cnc.fmt(c,v)

	#----------------------------------------------------------------------
	# add new line to list create block if necessary
	#----------------------------------------------------------------------
	def _addLine(self, line):
		if line.startswith("(Block-name:"):
			pat = BLOCKPAT.match(line)
			if pat:
				value = pat.group(2).strip()
				if not self.blocks or len(self.blocks[-1]):
					self.blocks.append(Block(value))
				else:
					self.blocks[-1]._name = value
				return

		if not self.blocks:
			self.blocks.append(Block("Header"))

		cmds = self.cnc.parseLine(line)
		if cmds is None:
			self.blocks[-1].append(line)
			return

		self.cnc.processPath(cmds)

		# rapid move up = end of block
		if self.cnc.gcode == 0 and self.cnc.dz > 0.0:
			self.blocks[-1].append(line)
			self.blocks.append(Block())
		elif self.cnc.gcode == 0 and len(self.blocks)==1:
			self.blocks.append(Block())
			self.blocks[-1].append(line)
		else:
			#if line and line[0]=="(":
			#	self._lastComment = len(self.blocks[1])
			self.blocks[-1].append(line)

		self.cnc.motionPathEnd()

	#----------------------------------------------------------------------
	def _trim(self):
		# Delete last block if empty
		last = self.blocks[-1]
		if len(last)==1 and len(last[0])==0: del last[0]
		if len(self.blocks[-1])==0:
			self.blocks.pop()

	#----------------------------------------------------------------------
	# Change all lines in editor
	#----------------------------------------------------------------------
	def setLinesUndo(self, lines):
		undoinfo = (self.setLinesUndo, list(self.lines()))
		# Delete all blocks and create new ones
		del self.blocks[:]
		#self._lastComment = 0
		self.cnc.initPath()
		for line in lines: self._addLine(line)
		self._trim()
		return undoinfo

	#----------------------------------------------------------------------
	# Change a single line in a block
	#----------------------------------------------------------------------
	def setLineUndo(self, bid, lid, line):
		undoinfo = (self.setLineUndo, bid, lid, self.blocks[bid][lid])
		self.blocks[bid][lid] = line
		return undoinfo

	#----------------------------------------------------------------------
	# Insert a new line into block
	#----------------------------------------------------------------------
	def insLineUndo(self, bid, lid, line):
		undoinfo = (self.delLineUndo, bid, lid)
		block = self.blocks[bid]
		if lid>=len(block):
			block.append(line)
		else:
			block.insert(lid, line)
		return undoinfo

	#----------------------------------------------------------------------
	# Delete line from block
	#----------------------------------------------------------------------
	def delLineUndo(self, bid, lid):
		block = self.blocks[bid]
		undoinfo = (self.insLineUndo, bid, lid, block[lid])
		del block[lid]
		return undoinfo

	#----------------------------------------------------------------------
	def insBlockUndo(self, bid, lines):
		undoinfo = (self.delBlockUndo, bid)
		block = Block()
		for line in lines:
			block.append(line)
		self.blocks.insert(bid, block)
		return undoinfo

	#----------------------------------------------------------------------
	# Delete a whole block
	#----------------------------------------------------------------------
	def delBlockUndo(self, bid):
		lines = [x for x in self.blocks[bid]]
		undoinfo = (self.insBlockUndo, bid, lines) #list(self.blocks[bid])[:])
		del self.blocks[bid]
		return undoinfo

	#----------------------------------------------------------------------
	def setBlockNameUndo(self, bid, name):
		undoinfo = (self.setBlockNameUndo, bid, self.blocks[bid]._name)
		self.blocks[bid]._name = name
		return undoinfo

	#----------------------------------------------------------------------
	def setBlockLinesUndo(self, bid, lines):
		block = self.blocks[bid]
		undoinfo = (self.setBlockLinesUndo, block[:])
		del block[:]
		block.extend(lines)
		return undoinfo

	#----------------------------------------------------------------------
	# Merge or split blocks depending on motion
	#
	# Each block should start with a rapid move and end with a rapid move
	#----------------------------------------------------------------------
#	def correctBlocks(self):
#		# Working in place tricky
#		bid = 0	# block index
#		while bid < len(self.blocks):
#			block = self.blocks[bid]
#			li = 0	# line index
#			prefix = True
#			suffix = False
#			lastg0 = None
#			while li < len(block):
#				line = block[li]
#				cmds = self.cnc.parseLine(line)
#				if cmds is None:
#					li += 1
#					continue
#
#				self.cnc.processPath(cmds)
#
#				# move
#				if self.gcode in (1,2,3):
#					if prefix is None: prefix = li-1
#
#				# rapid movement
#				elif self.gcode == 0:
#					lastg0 = li
#					if prefix is not None: suffix = li
#
#					# moving up = end of block
#					if self.cnc.dz > 0.0:
#						if suffix:
#							# Move all subsequent lines to a new block
#							#self.blocks.append(Block())
#							pass
#				self.cnc.motionPathEnd()

	#----------------------------------------------------------------------
	def __getitem__(self, item):		return self.blocks[item]
	def __setitem__(self, item, value):	self.blocks[item] = value

	#----------------------------------------------------------------------
	def undo(self):
		self.undoredo.undo()

	def redo(self):
		self.undoredo.redo()

	def addUndo(self, undoinfo):
		if isinstance(undoinfo,list):
			if len(undoinfo)==1:
				self.undoredo.addUndo(undoinfo[0])
			else:
				self.undoredo.addUndo(undo.createListUndo(undoinfo))
		elif undoinfo is not undo.NullUndo:
			self.undoredo.addUndo(undoinfo)

	def canUndo(self):	return self.undoredo.canUndo()
	def canRedo(self):	return self.undoredo.canRedo()

	#----------------------------------------------------------------------
	def setAllBlocksUndo(self, blocks=[]):
		undoinfo = [self.setAllBlocksUndo, self.blocks]
		self.blocks = blocks
		return undoinfo

	#----------------------------------------------------------------------
	# Start a new iterator
	#----------------------------------------------------------------------
#	def __iter__(self):
#		self._iter = 0	#self._iter_start
#		self._iter_block = self.blocks[self._iter]
#		self._iter_block_i = 0
#		self._iter_end   = len(self.blocks)
#		return self
#
#	#----------------------------------------------------------------------
#	# Next iterator item
#	#----------------------------------------------------------------------
#	def next(self):
#		if self._iter >= self._iter_end: raise StopIteration()
#
#		while self._iter_block_i >= len(self._iter_block):
#			self._iter += 1
#			if self._iter >= self._iter_end: raise StopIteration()
#			self._iter_block = self.blocks[self._iter]
#			self._iter_block_i = 0
#
#		item = self._iter_block[self._iter_block_i]
#		self._iter_block_i += 1
#		return item

	#----------------------------------------------------------------------
	# Return string representation of whole file
	#----------------------------------------------------------------------
	def __repr__(self):
		return "\n".join(list(self.lines()))

	#----------------------------------------------------------------------
	# Iterate over a block of lines
	#----------------------------------------------------------------------
	def iterate(self, lines):
		for bid,lid in lines:
			if lid is None:
				for i in range(len(self.blocks[bid])):
					yield bid,i
			else:
				yield bid,lid

	#----------------------------------------------------------------------
	# Iterate over all lines
	#----------------------------------------------------------------------
	def lines(self):
		for block in self.blocks:
			for line in block:
				yield line

	#----------------------------------------------------------------------
	# initialize cnc path based on block bid
	#----------------------------------------------------------------------
	def initPath(self, bid):
		if bid == 0:
			self.cnc.initPath()
		else:
			block = self.blocks[bid-1]
			# Use exiting coords from previous block
			self.cnc.initPath(block.x, block.y, block.z)

	#----------------------------------------------------------------------
	# Move blocks/lines up
	#----------------------------------------------------------------------
	def moveUp(self, lines):
		sel = []	# new selection
		for bid,lid in lines:
			if lid is None:
				# Move up whole block
				if bid==0:
					sel.append((bid,None))
					continue
				# swap with the block above
				before     = self[bid-1]
				self[bid-1] = self[bid]
				self[bid]   = before
				sel.append((bid-1,None))
			else:
				# Move up one line
				pass
		return sel

	#----------------------------------------------------------------------
	def moveDown(self, lines):
		sel = []	# new selection
		for bid,lid in reversed(lines):
			if lid is None:
				# Move down whole block
				if bid>=len(self.blocks)-1:
					sel.insert(0,(bid,None))
					continue
				# swap with the block below
				after      = self[bid+1]
				self[bid+1] = self[bid]
				self[bid]   = after
				sel.insert(0,(bid+1,None))
			else:
				# Move down one line
				pass
		return sel

	#----------------------------------------------------------------------
	# Create a cut my replicating the initial top-only path multiple times
	# until the maximum height
	#----------------------------------------------------------------------
	def cut(self, lines, height, depth_pass, feed):
		for bid,lid in lines:
			# Operate only on blocks
			if lid is not None: continue
			block = self.blocks[bid]

			# 1st detect limits of first pass
			start = None
			end   = None
			exit  = None
			self.initPath(bid)
			self.cnc.z = self.cnc.zval = 1000.0
			for i,line in enumerate(block):
				cmds = self.cnc.parseLine(line)
				if cmds is None: continue
				self.cnc.processPath(cmds)
				#print i,":",self.cnc.dz,self.cnc.z,line
				if self.cnc.dz<0.0:
					if start is None:
						start = i
						#print "START"
					elif end is None:
						end = i
						#print "END"
				elif self.cnc.dz>0.0 and exit is None:
					if end is None: end = i
					exit = i
					#print "EXIT"
					break
				self.cnc.motionPathEnd()
			if start is None: start = 0
			if end   is None: end   = len(block)
			if exit  is None: exit  = len(block)

			#print "len=",len(block)
			#print "start=",start
			#print "end=",end
			#print "exit=",exit
			#print
			#print "start: 0 ..",start
			#print "\n".join(block[:start])
			#print
			#print "path:\n",start,"..",end
			#print "\n".join(block[start:end])
			#print
			#print "exit:\n",exit,"..",len(block)
			#print "\n".join(block[exit:])

			# 2nd copy starting lines
			lines = block[:start]

			# 3rd duplicate passes from [start:end]
			z   = 0.0
			while z > -height:
				z = max(z-depth_pass, -height)

				for i in range(start, end):
					line = block[i]
					cmds = self.cnc.parseLine(line)
					if cmds is not None:
						changed = False
						for j,cmd in enumerate(cmds):
							c = cmd[0].upper()
							if c=="Z":
								changed = True
								cmds[j] = self.fmt(cmd[0],z)
							elif c=="F":
								changed = True
								cmds[j] = self.fmt(cmd[0],feed)
						if changed:
							line = " ".join(cmds)
					lines.append(line)

			# 4th copy remaining lines
			lines.extend(block[exit:])

			self.addUndo(self.setBlockLinesUndo(bid,lines))

	#----------------------------------------------------------------------
	# make a profile on block
	# offset +/- defines direction = tool/2
	#----------------------------------------------------------------------
	def profile(self, bid, offset):
		block = self.blocks[bid]
		self.initPath(bid)

		# path with line segments
		path = []	# (x,y),None|(2|3,xc,yc) arc/center

		new = Block("%s-prof"%(block.name()))
		self.blocks.insert(bid+1, new)
		Dp = None

		# ---------------------------------------
		# FIXME skip the first and last rapid g0
		# ---------------------------------------
		for line in block:
			cmds = self.cnc.parseLine(line)
			if cmds is None:
				new.append(line)
				continue
			self.cnc.processPath(cmds)

			if self.cnc.gcode not in (1,2,3):
				#new.append(line)
				pass
			else:
				xyz = self.cnc.motionPath()
				# Check gcode
				if self.cnc.gcode == 1:
					arc = None
				else:
					xc,yc,zc = self.cnc.motionCenter()
					arc = self.cnc.gcode,xc,yc

				# Offset path
				first = True
				A = Vector(xyz[0][0], xyz[0][1])
				for x2,y2,z2 in xyz[1:]:
					B = Vector(x2,y2)
					D = B-A
					O = D.orthogonal()
					O.norm()		# orthogonal unit vector
					P = O*offset		# perpendicular distance

					if first:
						Ao = A + P
						if Dp is not None:
							cross = D[0]*Dp[1]-D[1]*Dp[0]
							if cross>0:
								# Bo should hold the previous value
								# Center is A = Bo + IJ => IJ = A-Bo
								IJ = A - Bo
								nodearc = (2,A.x(),A.y())
								path.append((Ao, nodearc))
							else:
								path.append((Ao,None))
						else:
							# connect with previous point
							path.append((Ao,None))
						first = False

					# straight line
					Bo = B + P
					path.append((Bo,arc))
					A  = B
					Dp = D
			self.cnc.motionPathEnd()

		# ----------------------------------
		# Mark all intersections in the path
		# ----------------------------------
		A = path[0][0]
		for i,(B,arc) in enumerate(path[1:]):
			C = path[i+1][0]
			min1x = min(A[0],B[0])
			max1x = max(A[0],B[0])
			min1y = min(A[1],B[1])
			max1y = max(A[1],B[1])
			for j,(D,arc2) in enumerate(path[i+2:]):
				# Check if two segments intersect

				# intersect their bounding boxes
				min2 = min(C[0],D[0])
				max2 = max(C[0],D[0])
				lw = max(min1x,min2)
				hg = min(max1x,max2)
				if lw>=hg:
					# move to next segment
					C = D
					continue

				# intersect their bounding boxes
				min2 = min(C[1],D[1])
				max2 = max(C[1],D[1])
				lw = max(min1y,min2)
				hg = min(max1y,max2)
				if lw>=hg:
					# move to next segment
					C = D
					continue

				# check for intersection
				print "***",A,B,"---",C,D
				pass

				# move to next segment
				C = D

			# move to next step
			A = B

		# ----------------------------------
		# Create g code from path
		# ----------------------------------
		p,parc = path[0]
		new.append("g0 x%g y%g"%(p.x(), p.y()))
		new.append("g0 z0")

		pa = p	# starting point of arc (if any)
		ij = None
		for p,arc in path[1:]:
			if arc is None:
				new.append("g1 x%g y%g"%(p.x(), p.y()))
				pa = p	# starting point of arc
			else:
				g,xc,yc = arc
				line = "g%d x%g y%g "%(g, p.x(),p.y())
				if arc is parc:
					# replace the previous entry
					new[-1] = line+ij
				else:
					ij = "i%g j%g"%(xc-pa.x(),yc-pa.y())
					new.append(line+ij)
					pa = p	# starting point of arc
			parc = arc

	#----------------------------------------------------------------------
	# draw a hole (circle with radius)
	#----------------------------------------------------------------------
	def hole(self, bid, radius):
		block = self.blocks[bid]

		# Find starting location
		self.initPath(bid)
		for i,line in enumerate(block):
			cmds = self.cnc.parseLine(line)
			if cmds is None: continue
			self.cnc.processPath(cmds)
			self.cnc.motionPathEnd()

		# FIXME doesn't work

		# New lines to append
		pos = lid+1
		block.insert(pos, "G0 %s"%(self.fmt("X",self.cnc.x+radius)))
		pos += 1
		block.insert(pos, "G1 %s"%(self.fmt("Z",-0.001)))
		pos += 1
		block.insert(pos, "G2 %s"%(self.fmt("I",-radius)))
		pos += 1

	#----------------------------------------------------------------------
	# insert a new box
	#----------------------------------------------------------------------
	def box(self, bid, dx, dy, dz, nx, ny, nz, tool, thick, feed):
		box = Macros.Box(dx,dy,dz)
		box.thick = thick
		box.feed  = feed
		box.safeZ = self.cnc.safeZ
		#box.zfeed = 500
		#box.zstep = 1.5
		box.setNTeeth(nx,ny,nz)
		box.setTool(tool)
	#	box.holes = 'V'
		box.holes = 'D'
		box.cut   = False	# create multiple layers or only one

		blocks = box.make()
		undoinfo = []
		for block in blocks:
			undoinfo.append(self.insBlockUndo(bid,block))
			bid += 1
		self.addUndo(undoinfo)

	#----------------------------------------------------------------------
	# Modify the lines according to the supplied function and arguments
	#----------------------------------------------------------------------
	def process(self, lines, func, *args):
		undoinfo = []
		old = {}	# Last value
		new = {}	# New value

		for bid,lid in self.iterate(lines):
			block = self.blocks[bid]
			cmds = self.cnc.parseLine(block[lid])
			if cmds is None: continue

			# Collect all values
			new.clear()
			for cmd in cmds:
				c = cmd[0].upper()
				try:
					new[c] = float(cmd[1:])
				except:
					new[c] = 0.0

			# Modify values with func
			if func(new, old, *args):
				# Reconstruct new cmd
				newcmd = []
				for cmd in cmds:
					c = cmd[0].upper()
					old[c] = new[c]
					newcmd.append(self.fmt(cmd[0],new[c]))
				undoinfo.append(self.setLineUndo(bid,lid," ".join(newcmd)))

		# XXX should I add it here or return it to be added later?
		self.addUndo(undoinfo)

	#----------------------------------------------------------------------
	# Move position by dx,dy,dz
	#----------------------------------------------------------------------
	def moveFunc(self, new, old, dx, dy, dz):
		changed = False
		if 'X' in new:
			changed = True
			new['X'] += dx
		if 'Y' in new:
			changed = True
			new['Y'] += dy
		if 'Z' in new:
			changed = True
			new['Z'] += dz
		return changed

	#----------------------------------------------------------------------
	# Move position by dx,dy,dz
	#----------------------------------------------------------------------
	def moveLines(self, lines, dx, dy, dz):
		if dx == "UP":
			self.moveUp(lines)
		elif dx == "DOWN":
			self.moveDown(lines)
		else:
			return self.process(lines, self.moveFunc, dx, dy, dz)

	#----------------------------------------------------------------------
	# Rotate position by c(osine), s(ine) of an angle around center (x0,y0)
	#----------------------------------------------------------------------
	def rotateFunc(self, new, old, c, s, x0, y0):
		if 'X' not in new and 'Y' not in new: return False
		x = getValue('X',new,old)
		y = getValue('Y',new,old)
		new['X'] = (x-x0)*c - (y-y0)*s + x0
		new['Y'] = (x-x0)*s + (y-y0)*c + y0

		if 'I' in new or 'J' in new:
			i = getValue('I',new,old)
			j = getValue('J',new,old)
			new['I'] = i*c - j*s
			new['J'] = i*s + j*c
		return True

	#----------------------------------------------------------------------
	# Rotate lines around optional center (on XY plane)
	# ang in degrees (counter-clockwise)
	#----------------------------------------------------------------------
	def rotateLines(self, lines, ang, x0=0.0, y0=0.0):
		a = math.radians(ang)
		c = math.cos(a)
		s = math.sin(a)
		if ang in (0.0,90.0,180.0,270.0,-90.0,-180.0,-270.0):
			c = round(c)	# round numbers to avoid nasty extra digits
			s = round(s)
		return self.process(lines, self.rotateFunc, c, s, x0, y0)

	#----------------------------------------------------------------------
	# Mirror Horizontal
	#----------------------------------------------------------------------
	def mirrorHFunc(self, new, old, *kw):
		changed = False
		for axis in 'XI':
			if axis in new:
				new[axis] = -new[axis]
				changed = True
		g = int(getValue('G',new,old))
		if g==2:
			new['G'] = 3
		elif g==3:
			new['G'] = 2
		return changed

	#----------------------------------------------------------------------
	# Mirror Vertical
	#----------------------------------------------------------------------
	def mirrorVFunc(self, new, old, *kw):
		changed = False
		for axis in 'YJ':
			if axis in new:
				new[axis] = -new[axis]
				changed = True
		g = int(getValue('G',new,old))
		if g==2:
			new['G'] = 3
		elif g==3:
			new['G'] = 2
		return changed

	#----------------------------------------------------------------------
	# Mirror horizontally/vertically
	#----------------------------------------------------------------------
	def mirrorHLines(self, lines):
		return self.process(lines, self.mirrorHFunc)

	def mirrorVLines(self, lines):
		return self.process(lines, self.mirrorVFunc)

	#----------------------------------------------------------------------
	# Round all digits with accuracy
	#----------------------------------------------------------------------
	def roundFunc(self, new, old):
		for name,value in new.items():
			new[name] = round(value,self.decimal)
		return bool(new)

	#----------------------------------------------------------------------
	# Round line by the amount of digits
	#----------------------------------------------------------------------
	def roundLines(self, lines, acc=None):
		if acc is not None: self.decimal = acc
		return self.process(lines, self.roundFunc)

	#----------------------------------------------------------------------
	# Inkscape g-code tools on slice/slice it raises the tool to the
	# safe height then plunges again.
	# Comment out all these patterns
	#----------------------------------------------------------------------
	def inkscapeLines(self):
		undoinfo = []

		# Loop over all blocks
		self.cnc.initPath()
		newlines = []
		#last = None
		last = -1	# line location when it was last raised with dx=dy=0.0

		#for line in self.iterate():
		#for bid,block in enumerate(self.blocks):
		#	for li,line in enumerate(block):
		for line in self.lines():
			# step id
			# 0 - normal cutting z<0
			# 1 - z>0 raised  with dx=dy=0.0
			# 2 - z<0 plunged with dx=dy=0.0
			cmd = self.cnc.parseLine(line)
			if cmd is None:
				newlines.append(line)
				continue
			self.cnc.processPath(cmd)
			xyz = self.cnc.motionPath()
			if self.cnc.dx==0.0 and self.cnc.dy==0.0:
				if self.cnc.z>0.0 and self.cnc.dz>0.0:
					last = len(newlines)
					#last = bid, li

				#elif self.cnc.z<0.0 and self.cnc.dz<0.0 and last is not None:
				elif self.cnc.z<0.0 and self.cnc.dz<0.0 and last>=0:
					# comment out all lines from last
					#lb, ll = last
					#while bid!=lb or li!=ll:
					#	b = self.blocks[lb]
					#	line = b[ll]
					#	if line and line[0] not in ("(","%"):
					#		undoinfo.append(b.setLineUndo(ll,"(%s)"%(line)))
					#	ll += 1
					#	if ll>=len(b):
					#		lb += 1
					#		ll = 0
					# last = None
					for i in range(last,len(newlines)):
						s = newlines[i]
						if s and s[0] != '(':
							newlines[i] = "(%s)"%(s)
					last = -1
			else:
				#last = None
				last = -1
			newlines.append(line)
			self.cnc.motionPathEnd()

		self.addUndo(self.setLinesUndo(newlines))

	#----------------------------------------------------------------------
	# Remove the line number for lines
	#----------------------------------------------------------------------
	def removeNlines(self, lines):
		pass

	#----------------------------------------------------------------------
	# Use probe information to modify the g-code to autolevel
	#----------------------------------------------------------------------
	def prepare2Run(self):
		autolevel = not self.probe.isEmpty()

		lines = []
		paths = []
		for block in self.blocks:
			if not block.visible: continue
			for i,line in enumerate(block):
				newcmd = []
				cmds = self.cnc.parseLine(line)
				if cmds is None: continue

				if autolevel:
					self.cnc.processPath(cmds)
					xyz = self.cnc.motionPath()
					self.cnc.motionPathEnd()
					if not xyz:
						# while auto-levelling, do not ignore non-movement lines
						# so just append the line as-is
						lines.append(line)
						paths.append(None)
						continue

					if self.gcode in (1,2,3):
						for c in cmds:
							if c[0] in ('f','F'):
								feed = c
								break
						else:
							feed = ""

						x1,y1,z1 = xyz[0]
						for x2,y2,z2 in xyz[1:]:
							for x,y,z in self.probe.splitLine(x1,y1,z1,x2,y2,z2):
								lines.append(" G1%s%s%s%s"%\
									(self.fmt("X",x),
									 self.fmt("Y",y),
									 self.fmt("Z",z),
									 feed))
								paths.append(block._path[i])
								feed = ""
							x1,y1,z1 = x2,y2,z2
						lines[-1] = lines[-1].strip()
						continue

				for cmd in cmds:
					c = cmd[0]
					try: value = float(cmd[1:])
					except: value = 0.0
					if c.upper() in ("F","X","Y","Z","I","J","K","R","P",):
						cmd = self.fmt(c,value)
					newcmd.append(cmd)
				lines.append("".join(newcmd))
				paths.append(block._path[i])
		return lines,paths
