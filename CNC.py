# -*- coding: latin1 -*-
# $Id: CNC.py,v 1.8 2014/10/15 15:03:49 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import os
import re
import pdb
import sys
import math
import types
import random
import string

import undo
import Unicode

from dxf   import DXF
from bpath import Path, Segment
from bmath import *

IDPAT    = re.compile(r".*\bid:\s*(.*?)\)")
PARENPAT = re.compile(r"(.*)(\(.*?\))(.*)")
OPPAT    = re.compile(r"(.*)\[(.*)\]")
CMDPAT   = re.compile(r"([A-Za-z]+)")
BLOCKPAT = re.compile(r"^\(Block-([A-Za-z]+): (.*)\)")

STOP  = 0
SKIP  = 1
ASK   = 2
PAUSE = 8
WAIT  = 9

XY   = 0
XZ   = 1
YZ   = 2

WCS  = ["G54", "G55", "G56", "G57", "G58", "G59"]

DISTANCE_MODE = { "G90" : "Absolute",
		  "G91" : "Incremental" }
FEED_MODE     = { "G93" : "1/Time",
		  "G94" : "unit/min",
		  "G95" : "unit/rev"}
UNITS         = { "G20" : "inch",
		  "G21" : "mm" }
PLANE         = { "G17" : "XY",
		  "G18" : "ZX",
		  "G19" : "YZ" }

# Modal Mode from $G and variable set 
MODAL_MODES = {
	"G0"	: "motion",
	"G1"	: "motion",
	"G2"	: "motion",
	"G3"	: "motion",
	"G38.2"	: "motion",
	"G38.3"	: "motion",
	"G38.4"	: "motion",
	"G38.5"	: "motion",
	"G80"	: "motion",

	"G54"   : "WCS",
	"G55"   : "WCS",
	"G56"   : "WCS",
	"G57"   : "WCS",
	"G58"   : "WCS",
	"G59"   : "WCS",

	"G17"   : "plane",
	"G18"   : "plane",
	"G19"   : "plane",

	"G90"	: "distance",
	"G91"	: "distance",

	"G91.1" : "arc",

	"G93"   : "feedmode",
	"G94"   : "feedmode",
	"G95"   : "feedmode",

	"G20"	: "units",
	"G21"	: "units",

	"G40"	: "cutter",

	"G43.1" : "tlo",
	"G49"   : "tlo",

	"M0"	: "program",
	"M1"	: "program",
	"M2"	: "program",
	"M30"	: "program",

	"M3"    : "spindle",
	"M4"    : "spindle",
	"M5"    : "spindle",

	"M7"    : "coolant",
	"M8"    : "coolant",
	"M9"    : "coolant",
}


ERROR_HANDLING = {}

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

		self.points = []	# probe points
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
	# Load autolevel information from file
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
		self.xmin, self.xmax, self.xn = read(f)
		self.ymin, self.ymax, self.yn = read(f)
		self.zmin, self.zmax, feed    = read(f)
		CNC.vars["prbfeed"] = feed

		self.xn = max(2,int(self.xn))
		self.yn = max(2,int(self.yn))

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
		f.write("%g %g %g\n"%(self.zmin, self.zmax, CNC.vars["prbfeed"]))
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
		x = self.xmin
		xstep = self._xstep
		for j in range(self.yn):
			y = self.ymin + self._ystep*j
			for i in range(self.xn):
				lines.append("G0Z%.4f"%(self.zmax))
				lines.append("G0X%.4fY%.4f"%(x,y))
				lines.append("%sZ%.4fF%g"%(CNC.vars["prbcmd"], self.zmin, CNC.vars["prbfeed"]))
				x += xstep
			x -= xstep
			xstep = -xstep
		lines.append("G0Z%.4f"%(self.zmax))
		lines.append("G0X%.4fY%.4f"%(self.xmin,self.ymin))
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
	lasercutter    = False
	acceleration_x = 25.0	# mm/s^2
	acceleration_y = 25.0	# mm/s^2
	acceleration_z = 25.0	# mm/s^2
	feedmax_x      = 3000
	feedmax_y      = 3000
	feedmax_z      = 2000
	travel_x       = 300
	travel_y       = 300
	travel_z       = 60
	accuracy       = 0.02	# sagitta error during arc conversion
	digits         = 4
	startup        = "G90"
	stdexpr        = False	# standard way of defining expressions with []

	#----------------------------------------------------------------------
	def __init__(self):
		CNC.vars = {
				"prbx"      : 0.0,
				"prby"      : 0.0,
				"prbz"      : 0.0,
				"prbcmd"    : "G38.2",
				"prbfeed"   : 10.,
				"errline"   : "",
				"wx"        : 0.0,
				"wy"        : 0.0,
				"wz"        : 0.0,
				"mx"        : 0.0,
				"my"        : 0.0,
				"mz"        : 0.0,
				"G"         : ["G20","G54"],
				"motion"    : "G0",
				"WCS"       : "G54",
				"plane"     : "G17",
				"feedmode"  : "G94",
				"distance"  : "G90",
				"arc"       : "G91.1",
				"units"     : "G20",
				"cutter"    : "",
				"tlo"       : "",
				"program"   : "M0",
				"spindle"   : "M5",
				"coolant"   : "M9",

				"tool"      : 0,
				"feed"      : 0.0,
				"rpm"       : 0.0,

				"override"  : 100,
				"diameter"  : 3.175,	# Tool diameter
				"cutfeed"   : 1000.,	# Material feed for cutting
				"cutfeedz"  : 500.,	# Material feed for cutting
				"safe"      : 3.,
				"state"     : "",
				"stepz"     : 1.,
				"surface"   : 0.,
				"thickness" : 5.,
			}
		self.initPath()

	#----------------------------------------------------------------------
	# Update G variables from "G" string
	#----------------------------------------------------------------------
	@staticmethod
	def updateG():
		for g in CNC.vars["G"]:
			if g[0] == "F":
				CNC.vars["feed"] = float(g[1:])
			elif g[0] == "S":
				CNC.vars["rpm"] = float(g[1:])
			elif g[0] == "T":
				CNC.vars["tool"] = int(g[1:])
			else:
				var = MODAL_MODES.get(g)
				if var is not None:
					CNC.vars[var] = g

	#----------------------------------------------------------------------
	def __getitem__(self, name):
		return CNC.vars[name]

	#----------------------------------------------------------------------
	def __setitem__(self, name, value):
		CNC.vars[name] = value

	#----------------------------------------------------------------------
	@staticmethod
	def loadConfig(config):
		section = "CNC"
		CNC.inch           = bool(int(config.get(section, "units")))
		CNC.lasercutter    = bool(int(config.get(section, "lasercutter")))
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
		CNC.digits         = int(  config.get(section, "round"))
		CNC.startup        =       config.get(section, "startup")
		CNC.header         =       config.get(section, "header")
		CNC.footer         =       config.get(section, "footer")

		if CNC.inch:
			CNC.acceleration_x  /= 25.4
			CNC.acceleration_y  /= 25.4
			CNC.acceleration_z  /= 25.4
			CNC.feedmax_x       /= 25.4
			CNC.feedmax_y       /= 25.4
			CNC.feedmax_z       /= 25.4
			CNC.travel_x        /= 25.4
			CNC.travel_y        /= 25.4
			CNC.travel_z        /= 25.4

		section = "Error"
		for cmd,value in config.items(section):
			try:
				ERROR_HANDLING[cmd.upper()] = int(value)
			except:
				pass

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

		CNC.vars["xmin"] = CNC.vars["ymin"] = CNC.vars["zmin"] =  1000000.0
		CNC.vars["xmax"] = CNC.vars["ymax"] = CNC.vars["zmax"] = -1000000.0

		self.absolute    = True
		self.arcabsolute = False
		self.gcode       = None
		self.plane       = XY
		self.feed        = 0		# Actual gcode feed rate (not to confuse with cutfeed
		self.totalLength = 0.0
		self.totalTime   = 0.0

	#----------------------------------------------------------------------
	@staticmethod
	def isMarginValid():
		return	CNC.vars["xmin"] <= CNC.vars["xmax"] and \
			CNC.vars["ymin"] <= CNC.vars["ymax"] and \
			CNC.vars["zmin"] <= CNC.vars["zmax"]

	#----------------------------------------------------------------------
	# Number formating
	#----------------------------------------------------------------------
	@staticmethod
	def fmt(c, v, d=None):
		if d is None: d = CNC.digits
		return ("%s%*f"%(c,d,v)).rstrip("0").rstrip(".")

	#----------------------------------------------------------------------
	@staticmethod
	def gcode(g, pairs):
		s = "g%d"%(g)
		for c,v in pairs:
			s += " %c%g"%(c, round(v,CNC.digits))
		return s

	#----------------------------------------------------------------------
	@staticmethod
	def gline(g, x=None, y=None, z=None):
		s = "g%d"%(g)
		if x is not None: s += ' '+CNC.fmt('x',x)
		if y is not None: s += ' '+CNC.fmt('y',y)
		if z is not None: s += ' '+CNC.fmt('z',z)
		return s

	#----------------------------------------------------------------------
	@staticmethod
	def grapid(x=None, y=None, z=None):
		return CNC.gline(0,x,y,z)

	#----------------------------------------------------------------------
	@staticmethod
	def glinev(g, v, feed=None):
		pairs = zip("xyz",v)
		if feed is not None:
			pairs.append(("f",feed))
		return CNC.gcode(g, pairs)

	#----------------------------------------------------------------------
	@staticmethod
	def garcv(g, v, ijk):
		return CNC.gcode(g, zip("xyz",v) + zip("ij",ijk[:2]))

	#----------------------------------------------------------------------
	@staticmethod
	def garc(g, x=None, y=None, z=None, i=None, j=None, k=None):
		s = "g%d"%(g)
		if x is not None: s += ' '+CNC.fmt('x',x)
		if y is not None: s += ' '+CNC.fmt('y',y)
		if z is not None: s += ' '+CNC.fmt('z',z)
		if i is not None: s += ' '+CNC.fmt('i',i)
		if j is not None: s += ' '+CNC.fmt('j',j)
		if k is not None: s += ' '+CNC.fmt('k',k)
		return s

	#----------------------------------------------------------------------
	# Enter to material or start the laser
	#----------------------------------------------------------------------
	@staticmethod
	def zenter(z):
		if CNC.lasercutter:
			return "m3"
		else:
			return "g1 %s %s"%(CNC.fmt("z",z), CNC.fmt("f",CNC.vars["cutfeedz"]))

	#----------------------------------------------------------------------
	# gcode to go to z-safe
	# Exit from material or stop the laser
	#----------------------------------------------------------------------
	@staticmethod
	def zsafe():
		if CNC.lasercutter:
			return "m5"
		else:
			return "g0 %s"%(CNC.fmt("z",CNC.vars["safe"]))

	#----------------------------------------------------------------------
	# @return line in broken a list of commands, None if empty or comment
	#----------------------------------------------------------------------
	@staticmethod
	def parseLine(line):
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
		line = CMDPAT.sub(r" \1",line).lstrip()
		return line.split()

	# -----------------------------------------------------------------------------
	# @return line in broken a list of commands,
	#         None if empty or comment
	#         else compiled expressions
	#----------------------------------------------------------------------
	@staticmethod
	def parseLine2(line, space=False):
		line = line.strip()
		if not line: return None

		# to accept #nnn variables as _nnn internally
		line = line.replace('#','_')

		# execute literally the line after the first character
		if line[0]=='%':
			# special command
			line = line.strip()
			cmd = line.split()[0]
			if cmd=="%wait":
				return (WAIT,)
			elif cmd=="%pause":
				msg = line[7:].strip()
				if not msg: msg = None
				return (PAUSE, msg)
			try:
				return compile(line[1:],"","exec")
			except:
				# FIXME show the error!!!!
				return None

		# most probably an assignment like  #nnn = expr
		if line[0]=='_':
			try:
				return compile(line,"","exec")
			except:
				# FIXME show the error!!!!
				return None

		# commented line
		if line[0] == ';':
			return None

		out = []	# output list of commands
		braket  = 0	# bracket count []
		paren   = 0	# parenthesis count ()
		comment = False	# inside comment
		expr = ""	# expression string
		cmd  = ""	# cmd string
		for ch in line:
			if ch == '(':
				# comment start?
				paren += 1
				comment = (braket==0)
				if not comment: expr += ch
			elif ch == ')':
				# comment end?
				paren -= 1
				if not comment: expr += ch
				if paren==0 and comment: comment=False
			elif ch == '[':
				# expression start?
				if not comment:
					if CNC.stdexpr: ch='('
					braket += 1
					if braket==1:
						if cmd:
							out.append(cmd)
							cmd = ""
					else:
						expr += ch
			elif ch == ']':
				# expression end?
				if not comment:
					if CNC.stdexpr: ch=')'
					braket -= 1
					if braket==0:
						try:
							out.append(compile(expr,"","eval"))
						except:
							# FIXME show the error!!!!
							pass
						#out.append("<<"+expr+">>")
						expr = ""
					else:
						expr += ch
			elif ch=='=':
				# check for assignments (FIXME very bad)
				if not out and braket==0 and paren==0:
					for i in " ()-+*/^$":
						if i in cmd:
							cmd += ch
							break
					else:
						try:
							return compile(line,"","exec")
						except:
							# FIXME show the error!!!!
							return None
			elif ch == ';':
				# Skip everything after the semicolon on normal lines
				if not comment and paren==0 and braket==0:
					break
				else:
					expr += ch

			elif braket>0:
				expr += ch

			elif not comment:
				if ch == ' ':
					if space:
						cmd += ch
				else:
					cmd += ch

		if cmd: out.append(cmd)

		# return output commands
		if len(out)==0:
			return None
		if len(out)>1:
			return out
		return out[0]

	#----------------------------------------------------------------------
	# Break line into commands
	#----------------------------------------------------------------------
	@staticmethod
	def breakLine(line):
		if line is None: return None
		# Insert space before each command
		line = CMDPAT.sub(r" \1",line).lstrip()
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
					self.xval += self.x

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
				if self.arcabsolute:
					self.ival -= self.x

			elif c == "J":
				self.jval = value*self.unit
				if self.arcabsolute:
					self.jval -= self.y

			elif c == "K":
				self.kval = value*self.unit
				if self.arcabsolute:
					self.kval -= self.z

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
				decimal = int(round((value - self.gcode)*10))

				# Execute immediately
				if self.gcode==17:
					self.plane = XY

				elif self.gcode==18:
					self.plane = XZ

				elif self.gcode==19:
					self.plane = YZ

				elif self.gcode==20:	# Switch to inches
					if CNC.inch:
						self.unit = 1.0
					else:
						self.unit = 25.4

				elif self.gcode==21:	# Switch to mm
					if CNC.inch:
						self.unit = 1.0/25.4
					else:
						self.unit = 1.0

				elif self.gcode==90:
					if decimal == 0:
						self.absolute = True
					elif decimal == 1:
						self.arcabsolute = True

				elif self.gcode==91:
					if decimal == 0:
						self.absolute = False
					elif decimal == 1:
						self.arcabsolute = False

		self.dx = self.xval - self.x
		self.dy = self.yval - self.y
		self.dz = self.zval - self.z

	#----------------------------------------------------------------------
	# Return center x,y,z,r for arc motions 2,3 and set self.rval
	#----------------------------------------------------------------------
	def motionCenter(self):
		if self.rval>0.0:
			if self.plane == XY:
				x  = self.x
				y  = self.y
				xv = self.xval
				yv = self.yval
			elif self.plane == XZ:
				x  = self.x
				y  = self.z
				xv = self.xval
				yv = self.zval
			else:
				x  = self.y
				y  = self.z
				xv = self.yval
				yv = self.zval

			ABx = xv-x
			ABy = yv-y
			Cx  = 0.5*(x+xv)
			Cy  = 0.5*(y+yv)
			AB  = math.sqrt(ABx**2 + ABy**2)
			try: OC  = math.sqrt(self.rval**2 - AB**2/4.0)
			except: OC = 0.0
			if self.gcode==2: OC = -OC
			if AB != 0.0:
				return Cx-OC*ABy/AB, Cy + OC*ABx/AB
			else:
				# Error!!!
				return x,y
		else:
			# Center
			xc = self.x + self.ival
			yc = self.y + self.jval
			zc = self.z + self.kval
			self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)

			if self.plane == XY:
				return xc,yc
			elif self.plane == XZ:
				return xc,zc
			else:
				return yc,zc

		# Error checking
		#err = abs(self.rval - math.sqrt((self.xval-xc)**2 + (self.yval-yc)**2 + (self.zval-zc)**2))
		#if err/self.rval>0.001:
		#	print "Error invalid arc", self.xval, self.yval, self.zval, err
		#return xc,yc,zc

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
			uc,vc = self.motionCenter()
			if self.plane == XY:
				u0 = self.x
				v0 = self.y
				w0 = self.z
				u1 = self.xval
				v1 = self.yval
				w1 = self.zval
			elif self.plane == XZ:
				u0 = self.x
				v0 = self.z
				w0 = self.y
				u1 = self.xval
				v1 = self.zval
				w1 = self.yval
			else:
				u0 = self.y
				v0 = self.z
				w0 = self.x
				u1 = self.yval
				v1 = self.zval
				w1 = self.xval
			phi0 = math.atan2(v0-vc, u0-uc)
			phi1 = math.atan2(v1-vc, u1-uc)
			try:
				sagitta = 1.0-CNC.accuracy/self.rval
			except ZeroDivisionError:
				sagitta = 0.0
			if sagitta>0.0:
				df = 2.0*math.acos(sagitta)
				df = min(df, math.pi/4.0)
			else:
				df = math.pi/4.0

			if self.gcode==2:
				if phi1>=phi0-1e-10: phi1 -= 2.0*math.pi
				ws  = (w1-w0)/(phi1-phi0)
				phi = phi0 - df
				while phi>phi1:
					u = uc + self.rval*math.cos(phi)
					v = vc + self.rval*math.sin(phi)
					w = w0 + (phi-phi0)*ws
					phi -= df
					if self.plane == XY:
						xyz.append((u,v,w))
					elif self.plane == XZ:
						xyz.append((u,w,v))
					else:
						xyz.append((w,u,v))
			else:
				if phi1<=phi0+1e-10: phi1 += 2.0*math.pi
				ws  = (w1-w0)/(phi1-phi0)
				phi = phi0 + df
				while phi<phi1:
					u = uc + self.rval*math.cos(phi)
					v = vc + self.rval*math.sin(phi)
					w = w0 + (phi-phi0)*ws
					phi += df
					if self.plane == XY:
						xyz.append((u,v,w))
					elif self.plane == XZ:
						xyz.append((u,w,v))
					else:
						xyz.append((w,u,v))

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
			# and acceleration
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
			CNC.vars["xmin"] = min(CNC.vars["xmin"], min([i[0] for i in xyz]))
			CNC.vars["ymin"] = min(CNC.vars["ymin"], min([i[1] for i in xyz]))
			CNC.vars["zmin"] = min(CNC.vars["zmin"], min([i[2] for i in xyz]))
			CNC.vars["xmax"] = max(CNC.vars["xmax"], max([i[0] for i in xyz]))
			CNC.vars["ymax"] = max(CNC.vars["ymax"], max([i[1] for i in xyz]))
			CNC.vars["zmax"] = max(CNC.vars["zmax"], max([i[2] for i in xyz]))

	#----------------------------------------------------------------------
	# Instead of the current code, override with the custom user lines
	# @param program a list of lines to execute
	# @return the new list of lines
	#----------------------------------------------------------------------
	@staticmethod
	def compile(program):
		lines = []
		for j,line in enumerate(program):
			newcmd = []
			cmds = CNC.parseLine2(line)
			if cmds is None: continue
			if isinstance(cmds,str):
				cmds = CNC.breakLine(cmds)
			else:
				# either CodeType or list[] append
				lines.append(cmds)
				continue

			for cmd in cmds:
				c = cmd[0]
				try: value = float(cmd[1:])
				except: value = 0.0
				if c.upper() in ("F","X","Y","Z","I","J","K","R","P"):
					cmd = CNC.fmt(c,value)
				else:
					opt = ERROR_HANDLING.get(cmd.upper(),0)
					if opt == SKIP:
						cmd = None

				if cmd is not None:
					newcmd.append(cmd)
			lines.append("".join(newcmd))
		return lines

	#----------------------------------------------------------------------
	@staticmethod
	def initTool():
		CNC._lastTool = None

	#----------------------------------------------------------------------
	# code to change manually tool
	#----------------------------------------------------------------------
	@staticmethod
	def toolChange(cmds):
		# find tool
		tool = CNC._lastTool
		for cmd in cmds:
			cmd = cmd.upper()
			if cmd[0]=="T":
				tool = int(cmd[1:])
				break

		# check if it is the same tool
		if tool == CNC._lastTool: return []
		CNC._lastTool = tool

		# create the necessary code
		lines = []
		lines.append("m5")
		lines.append("g53 g0 z[toolchangez]")
		lines.append("g53 g0 x[toolchangex] y[toolchangey]")

		lines.append("%wait")
		lines.append("%%pause Tool change T%02d"%(tool))

		lines.append("g53 g0 x[toolprobex] y[toolprobey]")
		lines.append("g53 g0 z[toolprobez]")

		# fixed WCS
		lines.append("g91 [prbcmd] f[prbfeed] z[-tooldistance]")
		# FIXME could be done dynamically in the code
		p = WCS.index(CNC.vars["WCS"])+1
		lines.append("G10L20P%d z[toolheight]"%(p))

		lines.append("g53 g0 z[toolchangez]")
		lines.append("g53 g0 x[toolchangex] y[toolchangey]")

		lines.append("g90")
		# FIXME maybe I should remember the last state and restore it m3 or m4
		lines.append("m3")

		return CNC.compile(lines)

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
		# Copy constructor
		if isinstance(name, Block):
			self.copy(name)
			return
		self._name   = name
		self.enable  = True	# Enabled/Visible in drawing
		self.expand  = False	# Expand in editor
		self._path   = []	# canvas drawing paths
		self.sx = self.sy = self.sz = 0	# start  coordinates (entry point first non rapid motion)
		self.ex = self.ey = self.ez = 0	# ending coordinates

	#----------------------------------------------------------------------
	def copy(self, src):
		self._name   = src._name
		self.enable  = src.enable
		self.expand  = src.expand
		self[:]    = src[:]
		self._path = []
		self.sx = src.sx
		self.sy = src.sy
		self.sz = src.sz
		self.ex = src.ex
		self.ey = src.ey
		self.ez = src.ez

	#----------------------------------------------------------------------
	def name(self):
		return self._name is None and "block" or self._name

	#----------------------------------------------------------------------
	# @return the new name with an operation (static)
	#----------------------------------------------------------------------
	@staticmethod
	def operationName(name, operation):
		pat = OPPAT.match(name)
		if pat is None:
			return "%s [%s]"%(name,operation)
		else:
			name = pat.group(1).strip()
			ops = pat.group(2).split(',')
			if ":" in operation:
				oid,opt = operation.split(":")
			else:
				oid = operation
				opt = None
			for i,o in enumerate(ops):
				if ":" in o:
					o,c = o.split(":")
					try:
						c = int(c)
					except:
						c = 1
				else:
					c = 1
				if o==oid:
					if opt is not None or c is None:
						ops[i] = operation
					else:
						ops[i] = "%s:%d"%(oid,c+1)
					break
			else:
				ops.append(operation)
			return "%s [%s]"%(name,','.join(ops))

	#----------------------------------------------------------------------
	# Add a new operation to the block's name
	#----------------------------------------------------------------------
	def addOperation(self, operation):
		n = self.name()
		self._name = Block.operationName(self.name(), operation)

	#----------------------------------------------------------------------
	def header(self):
		e = self.expand and Unicode.BLACK_DOWN_POINTING_TRIANGLE \
				or  Unicode.BLACK_RIGHT_POINTING_TRIANGLE
		v = self.enable and Unicode.BALLOT_BOX_WITH_X \
				or  Unicode.BALLOT_BOX
		return "%s %s %s - [%d]"%(e, v, self.name(), len(self))

	#----------------------------------------------------------------------
	def write(self, f):
		f.write("(Block-name: %s)\n"%(self.name()))
		f.write("(Block-expand: %d)\n"%(int(self.expand)))
		f.write("(Block-enable: %d)\n"%(int(self.enable)))
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
				elif name=="enable":
					self.enable = bool(int(value))
					return
		if self._name is None and ("id:" in line) and ("End" not in line):
			pat = IDPAT.match(line)
			if pat: self._name = pat.group(1)
		list.append(self, line)

	#----------------------------------------------------------------------
	def addPath(self, p):
		self._path.append(p)

	#----------------------------------------------------------------------
	def path(self, i):
		return self._path[i]

	#----------------------------------------------------------------------
	def resetPath(self):
		del self._path[:]

	#----------------------------------------------------------------------
	def startPath(self, x, y, z):
		self.sx = x
		self.sy = y
		self.sz = z

	#----------------------------------------------------------------------
	def endPath(self, x, y, z):
		self.ex = x
		self.ey = y
		self.ez = z

#==============================================================================
# Gcode file
#==============================================================================
class GCode:
	#----------------------------------------------------------------------
	def __init__(self):
		self.cnc = CNC()
		self.header    = ""
		self.footer    = ""
		self.undoredo  = undo.UndoRedo()
		self.probe     = Probe()
		self.vars      = {}		# local variables
		self.init()

	#----------------------------------------------------------------------
	def init(self):
		self.filename = ""
		self.blocks   = []		# list of blocks
		self.vars.clear()
		self.undoredo.reset()
		self.probe.init()

		self._lastModified = 0
		self._modified = False

	#----------------------------------------------------------------------
	def isModified(self): return self._modified

	#----------------------------------------------------------------------
	def resetModified(self): self._modified = False

	#----------------------------------------------------------------------
	# Evaluate code expressions if any and return line
	#----------------------------------------------------------------------
	def evaluate(self, line):
		if isinstance(line,int):
			return None

		elif isinstance(line,list):
			for i,expr in enumerate(line):
				if isinstance(expr, types.CodeType):
					result = eval(expr,CNC.vars,self.vars)
					if isinstance(result,float):
						line[i] = str(round(result,CNC.digits))
					else:
						line[i] = str(result)
			return "".join(line)

		elif isinstance(line, types.CodeType):
			eval(line,CNC.vars,self.vars)
			return None

		else:
			return line

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename=None):
		if filename is None: filename = self.filename
		self.init()
		self.filename = filename
		try: f = open(self.filename,"r")
		except: return False
		self._lastModified = os.stat(self.filename).st_mtime
		self.cnc.initPath()
		self._blocksExist = False
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
		self._lastModified = os.stat(self.filename).st_mtime
		self._modified = False
		return True

	#----------------------------------------------------------------------
	def addBlockFromString(self, name, text):
		if not text: return
		block = Block(name)
		block.extend(text.splitlines())
		self.blocks.append(block)

	#----------------------------------------------------------------------
	# If empty insert a header and a footer
	#----------------------------------------------------------------------
	def headerFooter(self):
		if not self.blocks:
			self.addBlockFromString("Header",self.header)
			self.addBlockFromString("Footer",self.footer)
			return True
		return False

	#----------------------------------------------------------------------
	# Load DXF file into gcode
	#----------------------------------------------------------------------
	def importDXF(self, filename):
		try:
			dxf = DXF(filename,"r")
		except:
			return False
		self.filename = ""

		dxf.readFile()
		dxf.close()

		empty = len(self.blocks)==0
		if empty: self.addBlockFromString("Header",self.header)

		undoinfo = []
		for name,layer in dxf.layers.items():
			enable = not bool(layer.isFrozen())
			entities = dxf.sortLayer(name)
			if not entities: continue
			self.importEntityPoints(None, entities, name, enable)
			path = Path(name)
			path.fromDxfLayer(entities)
			path.removeZeroLength()
			opath = path.split2contours()
			if not opath: continue
			while opath:
				li = 0
				llen = 0.0
				for i,p in enumerate(opath):
					if p.length()>llen:
						li = i
						llen = p.length()
				longest = opath.pop(li)
				longest.mergeLoops(opath)

				undoinfo.extend(self.importPath(None, longest, None, enable))
#				d = longest.direction()
#				bid = len(self.blocks)-1
#				if d==0:
#					undoinfo.extend(self.addBlockOperationUndo(bid,"O"))
#				elif d==1:
#					undoinfo.extend(self.addBlockOperationUndo(bid,"CW"))
#				elif d==-1:
#					undoinfo.extend(self.addBlockOperationUndo(bid,"CCW"))

			undoinfo.extend(self.importPath(None, opath, None, enable))
#			d = opath.direction()
#			bid = len(self.blocks)-1
#			if d==0:
#				undoinfo.extend(self.addBlockOperationUndo(bid,"O"))
#			elif d==1:
#				undoinfo.extend(self.addBlockOperationUndo(bid,"CW"))
#			elif d==-1:
#				undoinfo.extend(self.addBlockOperationUndo(bid,"CCW"))

		if empty: self.addBlockFromString("Footer",self.footer)
		#self.addUndo(undoinfo)
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
			if ":" in name: name = name.split(":")[0]
			for line in block:
				cmds = CNC.parseLine(line)
				if cmds is None: continue
				self.cnc.processPath(cmds)
				if self.cnc.gcode == 1:	# line
					dxf.line(self.cnc.x, self.cnc.y, self.cnc.xval, self.cnc.yval, name)
				elif self.cnc.gcode in (2,3):	# arc
					xc,yc = self.cnc.motionCenter()
					sphi = math.atan2(self.cnc.y-yc,    self.cnc.x-xc)
					ephi = math.atan2(self.cnc.yval-yc, self.cnc.xval-xc)
					if self.cnc.gcode==2:
						if ephi<=sphi+1e-10: ephi += 2.0*math.pi
						dxf.arc(xc,yc,self.cnc.rval, math.degrees(ephi), math.degrees(sphi),name)
					else:
						if ephi<=sphi+1e-10: ephi += 2.0*math.pi
						dxf.arc(xc,yc,self.cnc.rval, math.degrees(sphi), math.degrees(ephi),name)
				self.cnc.motionPathEnd()
		dxf.writeEOF()
		dxf.close()
		return True

	#----------------------------------------------------------------------
	# Import POINTS from entities
	#----------------------------------------------------------------------
	def importEntityPoints(self, pos, entities, name, enable=True):
		undoinfo = []
		i = 0
		while i<len(entities):
			if entities[i].type != "POINT":
				i += 1
				continue

			block = Block("%s [P]"%(name))
			block.enable = enable

			x,y = entities[i].start()
			block.append("g0 %s %s"%(self.fmt("x",x,7),self.fmt("y",y,7)))
			block.append(CNC.zenter(self.cnc["surface"]))
			block.append(CNC.zsafe())
			undoinfo.append(self.addBlockUndo(pos,block))
			if pos is not None: pos += 1

			del entities[i]

		return undoinfo

	#----------------------------------------------------------------------
	# convert a block to path
	#----------------------------------------------------------------------
	def toPath(self, bid):
		block = self.blocks[bid]
		paths = []
		path = Path(block.name())
		self.initPath(bid)
		start = Vector(self.cnc.x, self.cnc.y)

		# get only first path that enters the surface
		# ignore the deeper ones
		z1st = None
		for line in block:
			cmds = CNC.parseLine(line)
			if cmds is None: continue
			self.cnc.processPath(cmds)
			end = Vector(self.cnc.xval, self.cnc.yval)
			if self.cnc.gcode == 0:		# rapid move (new block)
				if path:
					paths.append(path)
					path = Path(block.name())
			elif self.cnc.gcode == 1:	# line
				if z1st is None: z1st = self.cnc.zval
				if (self.cnc.dx != 0.0 or self.cnc.dy != 0.0) and abs(self.cnc.zval-z1st)<0.0001:
					path.append(Segment(1, start, end))
			elif self.cnc.gcode in (2,3):	# arc
				if z1st is None: z1st = self.cnc.zval
				if abs(self.cnc.z-z1st)<0.0001:
					xc,yc = self.cnc.motionCenter()
					center = Vector(xc,yc)
					path.append(Segment(self.cnc.gcode, start,end, center))
			self.cnc.motionPathEnd()
			start = end
		if path: paths.append(path)
		return paths

	#----------------------------------------------------------------------
	# create a block from Path
	#----------------------------------------------------------------------
	def fromPath(self, path, block=None, z=None, entry=True, exit=True):
		if block is None:
			if isinstance(path, Path):
				block = Block(path.name)
			else:
				block = Block(path[0].name)

		if isinstance(path, Path):
			x,y = path[0].start
			if z is None: z = self.cnc["surface"]
			if entry:
				block.append("g0 %s %s"%(self.fmt("x",x,7),self.fmt("y",y,7)))
			block.append(CNC.zenter(z))
			first = True
			for segment in path:
				x,y = segment.end
				if segment.type == 1:
					x,y = segment.end
					block.append("g1 %s %s"%(self.fmt("x",x,7),self.fmt("y",y,7)))
				elif segment.type in (2,3):
					ij = segment.center - segment.start
					if abs(ij[0])<1e-5: ij[0] = 0.
					if abs(ij[1])<1e-5: ij[1] = 0.
					block.append("g%d %s %s %s %s" % \
						(segment.type,
						 self.fmt("x",x,7), self.fmt("y",y,7),
						 self.fmt("i",ij[0],7),self.fmt("j",ij[1],7)))
				if first:
					block[-1] += " %s"%(self.fmt("f",self.cnc["cutfeed"]))
					first = False
			if exit:
				block.append(CNC.zsafe())
		else:
			for p in path:
				self.fromPath(p, block)
		return block

	#----------------------------------------------------------------------
	# Import paths as block
	# return ids of blocks added in newblocks list if declared
	#----------------------------------------------------------------------
	def importPath(self, pos, paths, newblocks=None, enable=True, multiblock=True):
		undoinfo = []
		if isinstance(paths,Path):
			block = self.fromPath(paths)
			block.enable = enable
			undoinfo.append(self.addBlockUndo(pos,block))
			if newblocks is not None: newblocks.append(pos)
		else:
			block = None
			for path in paths:
				if block is None:
					block = Block(path.name)
				block = self.fromPath(path, block)
				if multiblock:
					block.enable = enable
					undoinfo.append(self.addBlockUndo(pos,block))
					if newblocks is not None: newblocks.append(pos)
					if pos is not None: pos += 1
					block = None
			if not multiblock:
				block.enable = enable
				undoinfo.append(self.addBlockUndo(pos,block))
				if newblocks is not None: newblocks.append(pos)
		return undoinfo

	#----------------------------------------------------------------------
	# Check if a new version exists
	#----------------------------------------------------------------------
	def checkFile(self):
		try:
			return os.stat(self.filename).st_mtime > self._lastModified
		except:
			return False

	#----------------------------------------------------------------------
	def fmt(self, c, v, d=None): return self.cnc.fmt(c,v,d)

	#----------------------------------------------------------------------
	# add new line to list create block if necessary
	#----------------------------------------------------------------------
	def _addLine(self, line):
		if line.startswith("(Block-name:"):
			self._blocksExist = True
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

		cmds = CNC.parseLine(line)
		if cmds is None:
			self.blocks[-1].append(line)
			return

		self.cnc.processPath(cmds)

		# rapid move up = end of block
		if self._blocksExist:
			self.blocks[-1].append(line)
		elif self.cnc.gcode == 0 and self.cnc.dz > 0.0:
			self.blocks[-1].append(line)
			self.blocks.append(Block())
		elif self.cnc.gcode == 0 and len(self.blocks)==1:
			self.blocks.append(Block())
			self.blocks[-1].append(line)
		else:
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
		self.cnc.initPath()
		self._blocksExist = False
		for line in lines: self._addLine(line)
		self._trim()
		return undoinfo

	#----------------------------------------------------------------------
	def setAllBlocksUndo(self, blocks=[]):
		undoinfo = [self.setAllBlocksUndo, self.blocks]
		self.blocks = blocks
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
	# Clone line inside a block
	#----------------------------------------------------------------------
	def cloneLineUndo(self, bid, lid):
		return self.insLineUndo(bid, lid, self.blocks[bid][lid])

	#----------------------------------------------------------------------
	# Delete line from block
	#----------------------------------------------------------------------
	def delLineUndo(self, bid, lid):
		block = self.blocks[bid]
		undoinfo = (self.insLineUndo, bid, lid, block[lid])
		del block[lid]
		return undoinfo

	#----------------------------------------------------------------------
	# Add a block
	#----------------------------------------------------------------------
	def addBlockUndo(self, bid, block):
		if bid is None: bid = len(self.blocks)
		undoinfo = (self.delBlockUndo, bid)
		if bid>=len(self.blocks):
			self.blocks.append(block)
		else:
			self.blocks.insert(bid, block)
		return undoinfo

	#----------------------------------------------------------------------
	# Clone a block
	#----------------------------------------------------------------------
	def cloneBlockUndo(self, bid):
		return self.addBlockUndo(bid, Block(self.blocks[bid]))

	#----------------------------------------------------------------------
	# Delete a whole block
	#----------------------------------------------------------------------
	def delBlockUndo(self, bid):
		lines = [x for x in self.blocks[bid]]
		block = self.blocks.pop(bid)
		undoinfo = (self.addBlockUndo, bid, block)
		return undoinfo

	#----------------------------------------------------------------------
	# Insert a list of other blocks from another gcode file probably
	#----------------------------------------------------------------------
	def insBlocksUndo(self, bid, blocks):
		if bid is None or bid >= len(self.blocks):
			bid = len(self.blocks)
		undoinfo = ("Insert blocks", self.delBlocksUndo, bid, bid+len(blocks))
		self.blocks[bid:bid] = blocks
		return undoinfo

	#----------------------------------------------------------------------
	# Delete a range of blocks
	#----------------------------------------------------------------------
	def delBlocksUndo(self, from_, to_):
		blocks = self.blocks[from_:to_]
		undoinfo = ("Delete blocks", self.insBlocksUndo, from_, blocks)
		del self.blocks[from_:to_]
		return undoinfo

	#----------------------------------------------------------------------
	# Insert blocks and push the undo info
	#----------------------------------------------------------------------
	def insBlocks(self, bid, blocks, msg=""):
		if self.headerFooter():	# just in case
			bid = 1
		self.addUndo(self.insBlocksUndo(bid, blocks), msg)

	#----------------------------------------------------------------------
	# Set block expand
	#----------------------------------------------------------------------
	def setBlockExpandUndo(self, bid, expand):
		undoinfo = (self.setBlockExpandUndo, bid, self.blocks[bid].expand)
		self.blocks[bid].expand = expand
		return undoinfo

	#----------------------------------------------------------------------
	# Set block state
	#----------------------------------------------------------------------
	def setBlockEnableUndo(self, bid, enable):
		undoinfo = (self.setBlockEnableUndo, bid, self.blocks[bid].enable)
		self.blocks[bid].enable = enable
		return undoinfo

	#----------------------------------------------------------------------
	# Swap two blocks
	#----------------------------------------------------------------------
	def swapBlockUndo(self, a, b):
		undoinfo = (self.swapBlockUndo, a, b)
		tmp = self.blocks[a]
		self.blocks[a] = self.blocks[b]
		self.blocks[b] = tmp
		return undoinfo

	#----------------------------------------------------------------------
	# Move block from location src to location dst
	#----------------------------------------------------------------------
	def moveBlockUndo(self, src, dst):
		if src == dst: return undo.NullUndo
		undoinfo = (self.moveBlockUndo, dst, src)
		if dst > src:
			self.blocks.insert(dst-1, self.blocks.pop(src))
		else:
			self.blocks.insert(dst, self.blocks.pop(src))
		return undoinfo

	#----------------------------------------------------------------------
	# Invert selected blocks
	#----------------------------------------------------------------------
	def invertBlocksUndo(self, blocks):
		undoinfo = []
		first = 0
		last  = len(blocks)-1
		while first < last:
			undoinfo.append(self.swapBlockUndo(blocks[first],blocks[last]))
			first += 1
			last  -= 1
		return undoinfo

	#----------------------------------------------------------------------
	# Move block upwards
	#----------------------------------------------------------------------
	def orderUpBlockUndo(self, bid):
		if bid==0: return undo.NullUndo
		undoinfo = (self.orderDownBlockUndo, bid-1)
		# swap with the block above
		before      = self.blocks[bid-1]
		self.blocks[bid-1] = self.blocks[bid]
		self.blocks[bid]   = before
		return undoinfo

	#----------------------------------------------------------------------
	# Move block downwards
	#----------------------------------------------------------------------
	def orderDownBlockUndo(self, bid):
		if bid>=len(self.blocks)-1: return undo.NullUndo
		undoinfo = (self.orderUpBlockUndo, bid+1)
		# swap with the block below
		after       = self[bid+1]
		self[bid+1] = self[bid]
		self[bid]   = after
		return undoinfo

	#----------------------------------------------------------------------
	# Insert block lines
	#----------------------------------------------------------------------
	def insBlockLinesUndo(self, bid, lines):
		undoinfo = (self.delBlockLinesUndo, bid)
		block = Block()
		for line in lines:
			block.append(line)
		self.blocks.insert(bid, block)
		return undoinfo

	#----------------------------------------------------------------------
	# Delete a whole block lines
	#----------------------------------------------------------------------
	def delBlockLinesUndo(self, bid):
		lines = [x for x in self.blocks[bid]]
		undoinfo = (self.insBlockLinesUndo, bid, lines) #list(self.blocks[bid])[:])
		del self.blocks[bid]
		return undoinfo

	#----------------------------------------------------------------------
	# Set Block name
	#----------------------------------------------------------------------
	def setBlockNameUndo(self, bid, name):
		undoinfo = (self.setBlockNameUndo, bid, self.blocks[bid]._name)
		self.blocks[bid]._name = name
		return undoinfo

	#----------------------------------------------------------------------
	# Add an operation code in the name as [drill, cut, in/out...]
	#----------------------------------------------------------------------
	def addBlockOperationUndo(self, bid, operation):
		undoinfo = (self.setBlockNameUndo, bid, self.blocks[bid]._name)
		self.blocks[bid].addOperation(operation)
		return undoinfo

	#----------------------------------------------------------------------
	# Replace the lines of a block
	#----------------------------------------------------------------------
	def setBlockLinesUndo(self, bid, lines):
		block = self.blocks[bid]
		undoinfo = (self.setBlockLinesUndo, bid, block[:])
		del block[:]
		block.extend(lines)
		return undoinfo

	#----------------------------------------------------------------------
	# Move line upwards
	#----------------------------------------------------------------------
	def orderUpLineUndo(self, bid, lid):
		if lid==0: return undo.NullUndo
		block = self.blocks[bid]
		undoinfo = (self.orderDownLineUndo, bid, lid-1)
		block.insert(lid-1, block.pop(lid))
		return undoinfo

	#----------------------------------------------------------------------
	# Move line downwards
	#----------------------------------------------------------------------
	def orderDownLineUndo(self, bid, lid):
		block = self.blocks[bid]
		if lid>=len(block)-1: return undo.NullUndo
		undoinfo = (self.orderUpLineUndo, bid, lid+1)
		block.insert(lid+1, block.pop(lid))
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
#				cmds = CNC.parseLine(line)
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
		#print ">u>",self.undoredo.undoText()
		self.undoredo.undo()

	def redo(self):
		#print ">r>",self.undoredo.redoText()
		self.undoredo.redo()

	def addUndo(self, undoinfo, msg=""):
		if isinstance(undoinfo,list):
			if len(undoinfo)==1:
				self.undoredo.addUndo(undoinfo[0])
			else:
				self.undoredo.addUndo(undo.createListUndo(undoinfo,msg))
		elif undoinfo is not undo.NullUndo:
			self.undoredo.addUndo(undoinfo)
		self._modified = True

	def canUndo(self):	return self.undoredo.canUndo()
	def canRedo(self):	return self.undoredo.canRedo()

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
	# Iterate over the items
	#----------------------------------------------------------------------
	def iterate(self, items):
		for bid,lid in items:
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
			# Use the ending point of the previous block
			# since the starting (sxyz is after the rapid motion)
			block = self.blocks[bid-1]
			self.cnc.initPath(block.ex, block.ey, block.ez)

	#----------------------------------------------------------------------
	# Move blocks/lines up
	#----------------------------------------------------------------------
	def orderUp(self, items):
		sel = []	# new selection
		undoinfo = []
		for bid,lid in items:
			if lid is None:
				undoinfo.append(self.orderUpBlockUndo(bid))
				if bid==0:
					return items
				else:
					sel.append((bid-1,None))
			else:
				undoinfo.append(self.orderDownLineUndo(bid,lid))
				sel.append((bid, lid-1))
		self.addUndo(undoinfo,"Move Up")
		return sel

	#----------------------------------------------------------------------
	# Move blocks/lines down
	#----------------------------------------------------------------------
	def orderDown(self, items):
		sel = []	# new selection
		undoinfo = []
		for bid,lid in reversed(items):
			if lid is None:
				undoinfo.append(self.orderDownBlockUndo(bid))
				if bid>=len(self.blocks)-1:
					return items
				else:
					sel.append((bid+1,None))
			else:
				undoinfo.append(self.orderDownLineUndo(bid,lid))
				sel.append((bid,lid+1))
		self.addUndo(undoinfo,"Move Down")
		sel.reverse()
		return sel

	#----------------------------------------------------------------------
	# Peck distance
	# Target depth
	# Depth increment
	# Retract height=safe height
	#----------------------------------------------------------------------
	def drill(self, items, depth=None, peck=None, dwell=None):
		# find the penetration points and drill
		# skip all g1 movements on the horizontal plane
		if depth is None: depth = self.cnc["surface"]-self.cnc["thickness"]
		if depth < self.cnc["surface"]-self.cnc["thickness"] or depth > self.cnc["surface"]:
			return  "ERROR: Drill depth %g outside stock surface: %g .. %g\n" \
				"Please change stock surface in Tools->Stock or drill depth." \
				%(depth, self.cnc["surface"], self.cnc["surface"]-self.cnc["thickness"])
		if abs(depth - (self.cnc["surface"]-self.cnc["thickness"])) < 1e-7:
			opname = "drill"
		else:
			opname = "drill:%g"%(depth)

		undoinfo = []

		for bid in items:
			block = self.blocks[bid]
			if block.name() in ("Header", "Footer"): continue

			# construct new name
			undoinfo.append(self.addBlockOperationUndo(bid, opname))

			# 1st detect limits of first pass
			self.initPath(bid)
			self.cnc.z = self.cnc.zval = 1000.0
			lines = []
			for i,line in enumerate(block):
				cmds = CNC.parseLine(line)
				if cmds is None:
					lines.append(line)
					continue
				self.cnc.processPath(cmds)
				if self.cnc.dz<0.0:
					# drill point
					if peck is None:
						lines.append(CNC.zenter(depth))
						lines.append(CNC.zsafe())
					else:
						z = self.cnc["surface"]
						while z>depth:
							z = max(z-peck, depth)
							lines.append(CNC.zenter(z))
							lines.append(CNC.zsafe())
							if dwell:
								lines.append("g4 %s"%(self.fmt("p",dwell)))

				elif self.cnc.dz>0.0:
					# retract
					pass
				#	drill.append(line)

				elif self.cnc.gcode == 0:
					# add all rapid movements
					lines.append(line)

				elif self.cnc.gcode == 1:
					# ignore normal movements
					pass

				self.cnc.motionPathEnd()

			undoinfo.append(self.setBlockLinesUndo(bid,lines))
		self.addUndo(undoinfo)

	#----------------------------------------------------------------------
	# Perform a cut on a path an add it to block
	# @param block	I/O	block to add the cut paths
	# @param path	I	path to cut
	# @param z	I	starting z surface
	# @param depth	I	ending depth
	# @param stepz	I	stepping in z
	#----------------------------------------------------------------------
	def cutPath(self, block,path, z, depth, stepz):
		closed = path.isClosed()
		entry  = True
		exit   = False
		while z > depth:
			z = max(z-stepz, depth)
			if not closed:
				# on open paths always enter exit
				entry = exit = True
			elif abs(z-depth)<1e-7:
				# last pass
				exit =True
			self.fromPath(path, block, z, entry, exit)
			entry = False
		return block

	#----------------------------------------------------------------------
	# Create a cut my replicating the initial top-only path multiple times
	# until the maximum height
	#----------------------------------------------------------------------
	def cut(self, items, depth=None, stepz=None):
		if stepz is None: stepz = self.cnc["stepz"]
		if depth is None: depth = self.cnc["surface"]-self.cnc["thickness"]

		if depth < self.cnc["surface"]-self.cnc["thickness"] or depth > self.cnc["surface"]:
			return  "ERROR: Cut depth %g outside stock surface: %g .. %g\n" \
				"Please change stock surface in Tools->Stock or cut depth." \
				%(depth, self.cnc["surface"], self.cnc["surface"]-self.cnc["thickness"])
		if abs(depth - (self.cnc["surface"]-self.cnc["thickness"])) < 1e-7:
			opname = "cut"
		else:
			opname = "cut:%g"%(depth)
		stepz = abs(stepz)
		undoinfo = []
		for bid in items:
			block = self.blocks[bid]
			if block.name() in ("Header", "Footer"): continue
			newpath = []
			newblock = Block(block.name())
			for path in self.toPath(bid):
				self.cutPath(newblock, path, self.cnc["surface"], depth, stepz)
			if newblock:
				undoinfo.append(self.addBlockOperationUndo(bid, opname))
				undoinfo.append(self.setBlockLinesUndo(bid, newblock))
		self.addUndo(undoinfo)

	#----------------------------------------------------------------------
	# Reverse direction of cut
	#----------------------------------------------------------------------
	def reverse(self, items):
		undoinfo = []
		for bid in items:
			if self.blocks[bid].name() in ("Header", "Footer"): continue

			newpath = []
			for path in self.toPath(bid):
				path.invert()
				newpath.append(path)
			if newpath:
				block = self.fromPath(newpath)
				undoinfo.append(self.addBlockOperationUndo(bid, "reverse"))
				undoinfo.append(self.setBlockLinesUndo(bid, block))
		self.addUndo(undoinfo)

	#----------------------------------------------------------------------
	# make a profile on block
	# offset +/- defines direction = tool/2
	# return new blocks inside the blocks list
	#----------------------------------------------------------------------
	def profile(self, blocks, offset, cut=False, overcut=False, name=None):
		undoinfo = []
		msg = ""
		newblocks = []
		for bid in reversed(blocks):
			if self.blocks[bid].name() in ("Header", "Footer"): continue
			newpath = []
			for path in self.toPath(bid):
				if not path.isClosed():
					m = "Path: '%s' is OPEN"%(path.name)
					if m not in msg:
						if msg: msg += "\n"
						msg += m
				#print "path=",path
				path.removeZeroLength()
				D = path.direction()
				if D==0: D=1
				if name is not None:
					newname = Block.operationName(path.name, name)
				elif offset>0:
					newname = Block.operationName(path.name, "out")
				else:
					newname = Block.operationName(path.name, "in")

				opath = path.offset(D*offset, newname)
				opath.intersect()
				opath.removeExcluded(path, D*offset)
				opath = opath.split2contours()
				if opath:
					if overcut:
						for p in opath:
							p.overcut(D*offset)
					newpath.extend(opath)
			if newpath:
				# remember length to shift all new blocks the are inserted before
				before = len(newblocks)
				undoinfo.extend(self.importPath(bid+1, newpath, newblocks, True, False))
				new = len(newblocks)-before
				for i in range(before):
					newblocks[i] += new
				self.blocks[bid].enable = False
		self.addUndo(undoinfo)

		# return new blocks inside the blocks list
		del blocks[:]
		blocks.extend(newblocks)
		return msg

	#----------------------------------------------------------------------
	# draw a hole (circle with radius)
	#----------------------------------------------------------------------
	def hole(self, bid, radius):
		block = self.blocks[bid]

		# Find starting location
		self.initPath(bid)
		for i,line in enumerate(block):
			cmds = CNC.parseLine(line)
			if cmds is None: continue
			self.cnc.processPath(cmds)
			self.cnc.motionPathEnd()

		# FIXME doesn't work

		# New lines to append
		pos = lid+1
		block.insert(pos, "g0 %s"%(self.fmt("x",self.cnc.x+radius)))
		pos += 1
		block.insert(pos, "g1 %s"%(self.fmt("z",-0.001)))
		pos += 1
		block.insert(pos, "g2 %s"%(self.fmt("i",-radius)))
		pos += 1

	#----------------------------------------------------------------------
	# Modify the lines according to the supplied function and arguments
	#----------------------------------------------------------------------
	def process(self, items, func, *args):
		undoinfo = []
		old = {}	# Last value
		new = {}	# New value

		for bid,lid in self.iterate(items):
			block = self.blocks[bid]
			cmds = CNC.parseLine(block[lid])
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
	def orderLines(self, items, direction):
		if direction == "UP":
			self.orderUp(items)
		elif direction == "DOWN":
			self.orderDown(items)
		else:
			pass

	#----------------------------------------------------------------------
	# Move position by dx,dy,dz
	#----------------------------------------------------------------------
	def moveLines(self, items, dx, dy, dz):
		return self.process(items, self.moveFunc, dx, dy, dz)

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
	# Rotate items around optional center (on XY plane)
	# ang in degrees (counter-clockwise)
	#----------------------------------------------------------------------
	def rotateLines(self, items, ang, x0=0.0, y0=0.0):
		a = math.radians(ang)
		c = math.cos(a)
		s = math.sin(a)
		if ang in (0.0,90.0,180.0,270.0,-90.0,-180.0,-270.0):
			c = round(c)	# round numbers to avoid nasty extra digits
			s = round(s)
		return self.process(items, self.rotateFunc, c, s, x0, y0)

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
	def mirrorHLines(self, items):
		return self.process(items, self.mirrorHFunc)

	def mirrorVLines(self, items):
		return self.process(items, self.mirrorVFunc)

	#----------------------------------------------------------------------
	# Round all digits with accuracy
	#----------------------------------------------------------------------
	def roundFunc(self, new, old):
		for name,value in new.items():
			new[name] = round(value,CNC.digits)
		return bool(new)

	#----------------------------------------------------------------------
	# Round line by the amount of digits
	#----------------------------------------------------------------------
	def roundLines(self, items, acc=None):
		if acc is not None: CNC.digits = acc
		return self.process(items, self.roundFunc)

	#----------------------------------------------------------------------
	# Inkscape g-code tools on slice/slice it raises the tool to the
	# safe height then plunges again.
	# Comment out all these patterns
	#
	# FIXME needs re-working...
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
			cmd = CNC.parseLine(line)
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
	def removeNlines(self, items):
		pass

	#----------------------------------------------------------------------
	# Re-arrange using genetic algorithms a set of blocks to minimize
	# rapid movements.
	#----------------------------------------------------------------------
	def optimize(self, items):
		n = len(items)

		matrix = []
		for i in range(n):
			matrix.append([0.0] * n)

		# Find distances between blocks (end to start)
		for i in range(n):
			block = self.blocks[items[i]]
			x1 = block.ex
			y1 = block.ey
			for j in range(n):
				if i==j: continue
				block = self.blocks[items[j]]
				x2 = block.sx
				y2 = block.sy
				dx = x1-x2
				dy = y1-y2
				matrix[i][j] = sqrt(dx*dx + dy*dy)
		#from pprint import pprint
		#pprint(matrix)

		best = [0]
		unvisited = range(1,n)
		while unvisited:
			last = best[-1]
			row = matrix[last]
			# from all the unvisited places search the closest one
			mindist = 1e30
			for i,u in enumerate(unvisited):
				d = row[u]
				if d < mindist:
					mindist = d
					si = i
			best.append(unvisited.pop(si))
		#print "best=",best

		undoinfo = []
		for i in range(len(best)):
			b = best[i]
			if i==b: continue
			ptr = best.index(i)
			# swap i,b in items
			undoinfo.append(self.swapBlockUndo(items[i], items[b]))
			# swap i,ptr in best
			best[i], best[ptr] = best[ptr], best[i]
		self.addUndo(undoinfo, "Optimize")

	#----------------------------------------------------------------------
	# Use probe information to modify the g-code to autolevel
	#----------------------------------------------------------------------
	def compile(self):
		CNC.initTool()
		autolevel = not self.probe.isEmpty()
		lines = []
		paths = []
		for i,block in enumerate(self.blocks):
			if not block.enable: continue
			for j,line in enumerate(block):
				newcmd = []
				cmds = CNC.parseLine2(line)
				if cmds is None: continue
				if isinstance(cmds,str):
					cmds = CNC.breakLine(cmds)
				else:
					# either CodeType or list[] append
					lines.append(cmds)
					if isinstance(cmds,types.CodeType) or isinstance(cmds,int):
						paths.append(None)
					else:
						paths.append((i,j))
					continue

				if autolevel:
					self.cnc.processPath(cmds)
					xyz = self.cnc.motionPath()
					self.cnc.motionPathEnd()
					if not xyz:
						# while auto-levelling, do not ignore non-movement
						# commands, just append the line as-is
						lines.append(line)
						paths.append(None)
						continue

					if self.cnc.gcode in (1,2,3):
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
								paths.append((i,j))
								feed = ""
							x1,y1,z1 = x2,y2,z2
						lines[-1] = lines[-1].strip()
						continue

				for cmd in cmds:
					c = cmd[0]
					try: value = float(cmd[1:])
					except: value = 0.0
					if c.upper() in ("F","X","Y","Z","I","J","K","R","P"):
						cmd = self.fmt(c,value)
					else:
						# Tool change
						if cmd[0] in ("m","M") and int(cmd[1:])==6:
							toollines = CNC.toolChange(cmds)
							lines.extend(toollines)
							paths.extend([None]*len(toollines))
							cmd = None
						else:
							opt = ERROR_HANDLING.get(cmd.upper(),0)
							if opt == SKIP:
								cmd = None

					if cmd is not None:
						newcmd.append(cmd)
				lines.append("".join(newcmd))
				paths.append((i,j))
		return lines,paths

#if __name__=="__main__":
#	import pdb; pdb.set_trace()
#	#print Block.operationName("door","in")
#	print Block.operationName("door [in:2,cut:0.1]","cut:0.5")
#	print Block.operationName("door [in:2,cut:0.1]","in")
