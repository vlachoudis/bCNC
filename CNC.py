# -*- coding: latin1 -*-
# $Id: CNC.py,v 1.8 2014/10/15 15:03:49 bnv Exp $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

import re
import sys
import math
import string

PARENPAT = re.compile(r"(.*)(\(.*?\))(.*)")
CMDPAT   = re.compile(r"([A-Za-z])")

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
			print "Error reading probe file",self.filename
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
# File and command operations on a CNC file
#==============================================================================
class CNC:
	def __init__(self):
		self.filename       = ""
		self.inch           = False
		self.acceleration_x = 25.0	# mm/s^2
		self.acceleration_y = 25.0	# mm/s^2
		self.acceleration_z = 25.0	# mm/s^2
		self.feedmax_x      = 3000
		self.feedmax_y      = 3000
		self.feedmax_z      = 2000
		self.travel_x       = 370
		self.travel_y       = 205
		self.travel_z       = 100
		self.totalLength    = 0.0
		self.totalTime      = 0.0
		self.accuracy       = 0.1	# sagitta error during arc conversion
		self.safeZ          = 3.0	# mm
		self.round          = 4
		self.startup        = "G90"
		self.probe         = Probe()
		self.initPath()

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename=None):
		if filename is not None: self.filename = filename
		try:
			f = open(self.filename,"r")
		except:
			return ""
		self.probe.init()
		lines = f.read().replace("\x0d","")
		f.close()
		return lines

	#----------------------------------------------------------------------
	def loadConfig(self, config):
		section = "CNC"
		self.inch           = not bool( config.get(section, "units"))
		self.acceleration_x = float(config.get(section, "acceleration_x"))
		self.acceleration_y = float(config.get(section, "acceleration_y"))
		self.acceleration_z = float(config.get(section, "acceleration_z"))
		self.feedmax_x      = float(config.get(section, "feedmax_x"))
		self.feedmax_y      = float(config.get(section, "feedmax_y"))
		self.feedmax_z      = float(config.get(section, "feedmax_z"))
		self.travel_x       = float(config.get(section, "travel_x"))
		self.travel_y       = float(config.get(section, "travel_y"))
		self.travel_z       = float(config.get(section, "travel_z"))
		self.travel_z       = float(config.get(section, "travel_z"))
		self.accuracy       = float(config.get(section, "accuracy"))
		self.safeZ          = float(config.get(section, "safe_z"))
		self.round          = int(  config.get(section, "round"))
		self.startup        =       config.get(section, "startup")

	#----------------------------------------------------------------------
	def saveConfig(self, config):
		pass

	#----------------------------------------------------------------------
	def fmt(self, c, v):
		return "%s%g"%(c,round(v,self.round))

	#----------------------------------------------------------------------
	def save(self, lines):
		try:
			f = open(self.filename,"w")
		except:
			return False
		f.write(lines)
		f.close()
		return True

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
	def initPath(self):
		self.x    = self.y    = self.z    = 0.0
		self.xval = self.yval = self.zval = 0.0
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
	# Create path for one g command
	#----------------------------------------------------------------------
	def motionPath(self, autolevel=False):
		xyz = []

		# Execute g-code
		if self.gcode==0:	# fast move
			if self.xval-self.x != 0.0 or \
			   self.yval-self.y != 0.0 or \
			   self.zval-self.z != 0.0:
				xyz.append((self.x,self.y,self.z))
				self.x = self.xval
				self.y = self.yval
				self.z = self.zval
				xyz.append((self.x,self.y,self.z))

		elif self.gcode==1:	# line
			if self.xval-self.x != 0.0 or \
			   self.yval-self.y != 0.0 or \
			   self.zval-self.z != 0.0:
				xyz.append((self.x,self.y,self.z))
				self.x = self.xval
				self.y = self.yval
				self.z = self.zval
				xyz.append((self.x,self.y,self.z))

		elif self.gcode in (2,3):	# CW=2,CCW=3 circle
			xyz.append((self.x,self.y,self.z))
			if self.rval>0.0:
				ABx = self.xval-self.x
				ABy = self.yval-self.y
				Cx  = 0.5*(self.x+self.xval)
				Cy  = 0.5*(self.y+self.yval)
				AB  = math.sqrt(ABx**2 + ABy**2)
				try: OC  = math.sqrt(self.rval**2 - AB**2/4.0)
				except: OC = 0.0
				if self.gcode==2: OC = -OC
				xc  = Cx - OC*ABy/AB
				yc  = Cy + OC*ABx/AB
				zc  = self.z
			else:
				# Center
				xc = self.x + self.ival
				yc = self.y + self.jval
				zc = self.z + self.kval
				self.rval = math.sqrt(self.ival**2 + self.jval**2 + self.kval**2)
				r2 = math.sqrt((self.xval-xc)**2 + (self.yval-yc)**2 + (self.zval-zc)**2)
				#if abs((self.rval-r2)/self.rval) > 0.01:
				#	print>>sys.stderr, "ERROR arc", r2, self.rval

			phi  = math.atan2(self.y-yc, self.x-xc)
			ephi = math.atan2(self.yval-yc, self.xval-xc)
			sagitta = 1.0-self.accuracy/self.rval
			if sagitta>0.0:
				df = 2.0*math.acos(sagitta)
				df = min(df, math.pi/4.0)
			else:
				df = math.pi/4.0

			if self.gcode==2:
				if ephi>phi: ephi -= 2.0*math.pi
				phi -= df
				while phi>ephi:
					self.x = xc + self.rval*math.cos(phi)
					self.y = yc + self.rval*math.sin(phi)
					phi -= df
					xyz.append((self.x,self.y,self.z))
			else:
				if ephi<phi: ephi += 2.0*math.pi
				phi += df
				while phi<ephi:
					self.x = xc + self.rval*math.cos(phi)
					self.y = yc + self.rval*math.sin(phi)
					phi += df
					xyz.append((self.x,self.y,self.z))

			self.x = self.xval
			self.y = self.yval
			self.z = self.zval
			xyz.append((self.x,self.y,self.z))

			# reset at the end
			self.rval = self.ival = self.jval = self.kval = 0.0

		elif self.gcode==4:	# Dwell
			self.totalTime = self.pval

		elif self.gcode==28:
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0

		elif self.gcode==30:
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0

		elif self.gcode==92:
			self.x = 0.0
			self.y = 0.0
			self.z = 0.0

		return xyz

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

	#----------------------------------------------------------------------
	# Modify the lines according to the supplied function and arguments
	#----------------------------------------------------------------------
	def modifyLines(self, lines, func, *args):
		newlines = []

		old = {}	# Last value
		new = {}	# New value

		for line in lines:
			cmds    = self.parseLine(line)
			if cmds is None:
				newlines.append(line)
				continue

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
				newlines.append(string.join(newcmd))
			else:
				newlines.append(line)
		return newlines

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
		return self.modifyLines(lines, self.moveFunc, dx, dy, dz)

	#----------------------------------------------------------------------
	# Rotate position by c(osine), s(ine) of an angle around center (x0,y0)
	#----------------------------------------------------------------------
	def rotateFunc(self, new, old, c, s, x0, y0):
		if 'X' not in new and 'Y' not in new: return False
		x = getValue('X',new,old)
		y = getValue('Y',new,old)
		new['X'] = (x-x0)*c - (y-y0)*s + x0
		new['Y'] = (x-x0)*s + (y-y0)*c + y0
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
		return self.modifyLines(lines, self.rotateFunc, c, s, x0, y0)

	#----------------------------------------------------------------------
	# Round all digits with accuracy
	#----------------------------------------------------------------------
	def roundFunc(self, new, old):
		for name,value in new.items():
			new[name] = round(value,self.round)
		return bool(new)

	#----------------------------------------------------------------------
	# Round line by the amount of digits
	#----------------------------------------------------------------------
	def roundLines(self, lines, acc=None):
		if acc is not None: self.round = acc
		return self.modifyLines(lines, self.roundFunc)

	#----------------------------------------------------------------------
	# Use probe information to modify the g-code to autolevel
	#----------------------------------------------------------------------
	def prepare2Run(self, lines):
		autolevel = not self.probe.isEmpty()

		newlines = []
		for line in lines:
			newcmd = []
			cmds = self.parseLine(line)
			if cmds is None:
				newlines.append(None)
				continue

			if autolevel:
				self.processPath(cmds)
				xyz = self.motionPath(True)
				if not xyz:
					newlines.append(None)
					continue
				if self.gcode in (1,2,3):
					for c in cmds:
						if c[0] in ('f','F'):
							feed = c
							break
					else:
						feed = ""
					#print "LINE=",line
					#print "PATH=",xyz
					x1,y1,z1 = xyz[0]
					for x2,y2,z2 in xyz[1:]:
						for x,y,z in self.probe.splitLine(x1,y1,z1,x2,y2,z2):
							newlines.append(" G1%s%s%s%s"%\
								(self.fmt("X",x),
								 self.fmt("Y",y),
								 self.fmt("Z",z),
								 feed))
							feed = ""
						x1,y1,z1 = x2,y2,z2
					newlines[-1] = newlines[-1].strip()
					continue

			for cmd in cmds:
				c = cmd[0]
				try: value = float(cmd[1:])
				except: value = 0.0
				if c.upper() in ("F","X","Y","Z","I","J","K","R","P",):
					cmd = self.fmt(c,value)
				newcmd.append(cmd)
			newlines.append(string.join(newcmd,""))
		return newlines

	#----------------------------------------------------------------------
	# Inkscape g-code tools on slice/slice it raises the tool to the
	# safe height then plunges again.
	# Comment out all these patterns
	#----------------------------------------------------------------------
	def inkscapeLines(self, lines):
		self.initPath()
		newlines = []

		# step id
		# 0 - normal cutting z<0
		# 1 - z>0 raised with dx=dy=0.0
		# 2 - z<0 plunged with dx=dy=0.0
		last = -1	# line location when it was last raised with dx=dy=0.0
		for line in lines:
			cmd = self.parseLine(line)
			if cmd is None:
				newlines.append(line)
				continue
			self.processPath(cmd)
			xyz = self.motionPath()
			if self.dx==0.0 and self.dy==0.0:
				if self.z>0.0 and self.dz>0.0:
					last = len(newlines)

				elif self.z<0.0 and self.dz<0.0 and last>=0:
					# comment out all lines from last
					for i in range(last,len(newlines)):
						s = newlines[i]
						if s and s[0] != '(':
							newlines[i] = "(%s)"%(s)
					last = -1

			else:
				last = -1
			newlines.append(line)
		return newlines

	#----------------------------------------------------------------------
	# Remove the line number for lines
	#----------------------------------------------------------------------
	def removeNlines(self, lines):
		pass
