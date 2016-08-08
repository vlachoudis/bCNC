# $Id: bmath.py 3739 2016-03-22 08:14:24Z bnv $
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
# Date:	15-May-2004
from __future__ import generators

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import math
import cmath
from math import *
import rexx
import random

# Accuracy for comparison operators
_accuracy = 1E-15

# Formating
_format = "%12g"

#-------------------------------------------------------------------------------
def Cmp0(x): return abs(x)<_accuracy

#-------------------------------------------------------------------------------
# range of floating point numbers
#-------------------------------------------------------------------------------
def frange(start,stop,step):
	"""range(start,stop,step) for floating point numbers"""
	x = start
	if step<0.0:
		while x>stop:
			yield x
			x += step
	else:
		while x<stop:
			yield x
			x += step

#-------------------------------------------------------------------------------
# limit in number within a range
#-------------------------------------------------------------------------------
def limit(min_, num, max_):
	"""limit a number within a specific range"""
	return max(min(num,max_),min_)

#-------------------------------------------------------------------------------
# dms - degrees from degrees, minutes, seconds
#-------------------------------------------------------------------------------
def dms(d,m,s):
	return d + m/60.0 + s/3600.0

#-------------------------------------------------------------------------------
# d2s - degrees to string
# D2S(angle[,"H"|"M"|"D"|"N"])
#-------------------------------------------------------------------------------
def d2s(ang, fmt=""):
	fmt.capitalize()
	if ang<0.0:
		neg = "-"
		ang = -ang
	else:
		neg = ""

	ang = round(ang*360000)/100
	SS  = "%05.2f" % (fmod(ang,60))
	ang = int(ang / 60.0)
	MM  = "%02d" % (ang % 60)
	HH  = neg + str(ang / 60)

	if fmt=="H":
		return HH+"h"+MM+"m"+SS+"s"
	if fmt=="M":
		return HH+"h"+MM+"m"
	if fmt=="D":
		return HH+" "+MM+"'"+SS+'"'
	if fmt=="N":
		return HH+":"+MM
	return HH+":"+MM+":"+SS

#-------------------------------------------------------------------------------
# Format a number to fit in the minimum space
#-------------------------------------------------------------------------------
def format(number, length=10, useExp=False, useD=False):
	"""
	Format a number to fit in the minimum space given by length
	"""

	_MAXLEN=22

	# Convert number to string
	# XXX str cuts at 12 digits, repr shows everything but
	# numbers like e.g 9.2 will be converted to 9.1999999999999
	# What should I do
	# Fields also in the CardWidget are converted with str and
	# are cut at 12 digits!!!!
	if isinstance(number, float) or isinstance(number, int):
		number = repr(number).upper()
	else:
		number = str(number).strip().upper()
		if not rexx.datatype(number, "N"): return number

	if useD:
		number = number.replace("E", "D")
		expE = "D"
	else:
		number = number.replace("D", "E")
		expE = "E"

	if len(number) < length:
		hasExp = (number.find(expE)>=0)
		if useExp:
			if hasExp: return number
		elif number.find(".")>=0 or hasExp:
			return number

	if number=="0":
		if useExp:	return "0.%s0" % (expE)
		else:		return "0.0"

	if length<5 or length>_MAXLEN: raise Exception("Format invalid length")

	# Dissect the number. It is in the normal Rexx format.
	try:
		(mantissa, exponent) = number.split(expE)
		if exponent == '':
			exponent = 0
		else:
			exponent = int(exponent)
	except:
		mantissa = number
		exponent = 0

	if mantissa[0] == '-':
		sgn = True
		mantissa = mantissa[1:]
	elif mantissa[0] == '+':
		sgn = False
		mantissa = mantissa[1:]
	else:
		sgn = False

	try:
		(befo, afte) = mantissa.split(".")
	except:
		befo = mantissa
		afte = ""

	# Count from the left for the decimal point.
	point = len(befo)

	# Make this a number without a point.
	integer = befo + afte

	# Remove leading zeros
	for p in range(len(integer)):
		if integer[p] != '0':
			if p>0:
				integer = integer[p:]
				point  -= p
			break
	else:
		if useExp:	return "0.%s0" % (expE)
		else:		return "0.0"

	# ... and trailing
	for p in range(len(integer)-1,0,-1):
		if integer[p] != '0':
			integer = integer[0:p+1]
			break

	exponent += point

	# Cannot handle more than _MAXLEN digits
	lint = len(integer)
	if lint > _MAXLEN:
		r = integer[_MAXLEN]
		integer = integer[0:_MAXLEN]
		if r>='5':
			integer = str(long(integer)+1)
			if len(integer) > lint:
				exponent += 1
				if len(integer) > _MAXLEN:
					integer = integer[0:_MAXLEN]

	# Now the number is described by:
	#	sgn 0.integer "E" exponent

	# Make space for sign
	if sgn: length -= 1

	while True:
		# Minimum length representation of a number
		# Length = Length of integer
		#	    + 1 for Dot if needed (no exponent)
		#	    + (2-4) for exponent
		#	exponent can be in the following forms
		#		nothing if dot can placed inside integer
		#		E#	2
		#		E##	3
		#		E-#	3
		#		E-##	4
		#	integer is given as  0.integer
		#say("\ninteger=",integer,len(integer),length)
		#say("exponent=",exponent)
		lint = len(integer)
		if useExp:
			mNum = "%s%s%d"%(rexx.insert(".", integer, 1),expE,exponent-1)
		elif exponent==-2:
			mNum = ".00%s"%(integer)
		elif exponent==-1:
			mNum = ".0%s"%(integer)
		elif exponent==0:
			mNum = ".%s"%(integer)
		elif exponent==1:
			mNum = rexx.insert(".", integer, 1)
		elif exponent==length:
			mNum = "%s%s"%(integer,"0"*(length-lint))
		elif exponent>1 and exponent<=lint:
			mNum = rexx.insert(".", integer, exponent)
		elif exponent>1 and exponent<=lint+2:
			if exponent>lint:
				mNum = "%s%s."%(integer, "0"*(exponent-lint))
			else:
				mNum = "%s."%(integer.ljust(exponent))
		elif exponent>lint and exponent+1<length:
			mNum = "%s%s."%(integer, "0"*(exponent-lint))
		else:
			mNum = "%s%s%d"%(rexx.insert(".", integer, 1),expE,exponent-1)

		diff = len(mNum)-length
		if diff<=0:
			break
		elif diff<=2:
			r = integer[-1]
			integer = integer[0:-1]
		else:
			r = integer[-diff]
			integer = integer[0:-diff]

		if r>='5':
			lint = len(integer)
			if lint==0: integer = 0
			integer = str(long(integer)+1)
			if len(integer) > lint:
				exponent += 1

		# Remove trailing zeros
		for p in range(len(integer)-1,-1,-1):
			if integer[p] != '0':
				integer = integer[0:p+1]
				break
		else:
			if useExp:	return "0.%s0"%(expE)
			else:		return "0.0"

	if sgn: mNum = "-%s"%(mNum)
	return mNum

#==============================================================================
# Dangerous dictionary that unknown keys return a user default value
# Use it with care
#==============================================================================
class DefaultDict(dict):
	def __init__(self, default=None):
		self._default = default

	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		return self.get(key,self._default)

#==============================================================================
# Unknown keys will return 0.0
#==============================================================================
class ZeroDict(DefaultDict):
	def __init__(self):
		DefaultDict.__init__(self, 0.0)

#==============================================================================
# Unknown keys will return 0.0
#==============================================================================
class ZeroIntDict(DefaultDict):
	def __init__(self):
		DefaultDict.__init__(self, 0)

#===============================================================================
# Vector class
# Inherits from List
#===============================================================================
class Vector(list):
	"""Vector class"""

	# ----------------------------------------------------------------------
	def __init__(self, x=3, *args):
		"""Create a new vector,
		Vector(size), Vector(list), Vector(x,y,z,...)"""

		if isinstance(x,int) and not args:
			for i in range(x):
				self.append(0.0)
		elif isinstance(x,list) or isinstance(x,tuple):
			for i in x:
				self.append(float(i))
		else:
			self.append(float(x))
			for i in args:
				self.append(float(i))

	# ----------------------------------------------------------------------
	def set(self, x, y, z=None):
		"""Set vector"""
		self[0] = x
		self[1] = y
		if z: self[2] = z

	# ----------------------------------------------------------------------
	def __repr__(self):
		return "[%s]"%(", ".join([(_format%(x)).strip() for x in self]))

	# ----------------------------------------------------------------------
	def eq(self, v, acc=_accuracy):
		"""Test for equality with vector v within accuracy"""
		if len(self) != len(v): return False
		s2 = 0.0
		for i in range(len(self)):
			s2 += (self[i]-v[i])**2
		return s2 <= acc**2
	def __eq__(self, v): return self.eq(v)

	# ----------------------------------------------------------------------
	def __neg__(self):
		"""Negate vector"""
		new = Vector(len(self))
		for i in range(len(self)):
			new[i] = -self[i]
		return new

	# ----------------------------------------------------------------------
	def __add__(self, v):
		"""Add 2 vectors"""
		size = min(len(self),len(v))
		new = Vector(size)
		for i in range(size):
			new[i] = self[i] + v[i]
		return new

	# ----------------------------------------------------------------------
	def __iadd__(self, v):
		"""Add vector v to self"""
		for i in range(min(len(self),len(v))):
			self[i] += v[i]
		return self

	# ----------------------------------------------------------------------
	def __sub__(self, v):
		"""Subtract 2 vectors"""
		size = min(len(self),len(v))
		new = Vector(size)
		for i in range(size):
			new[i] = self[i] - v[i]
		return new

	# ----------------------------------------------------------------------
	def __isub__(self, v):
		"""Subtract vector v from self"""
		for i in range(min(len(self),len(v))):
			self[i] -= v[i]
		return self

	# ----------------------------------------------------------------------
	# Scale or Dot product
	# ----------------------------------------------------------------------
	def __mul__(self, v):
		"""scale*Vector() or Vector()*Vector() - Scale vector or dot product"""
		if isinstance(v,list):
			return self.dot(v)
		else:
			return Vector([x*v for x in self])

	# ----------------------------------------------------------------------
	# Scale or Dot product
	# ----------------------------------------------------------------------
	def __rmul__(self, v):
		"""scale*Vector() or Vector()*Vector() - Scale vector or dot product"""
		if isinstance(v,Vector):
			return self.dot(v)
		else:
			return Vector([x*v for x in self])

	# ----------------------------------------------------------------------
	# Divide by floating point
	# ----------------------------------------------------------------------
	def __div__(self, b):
		return Vector([x/b for x in self])

	# ----------------------------------------------------------------------
	def __xor__(self, v):
		"""Cross product"""
		return self.cross(v)

	# ----------------------------------------------------------------------
	def dot(self, v):
		"""Dot product of 2 vectors"""
		size = min(len(self),len(v))
		s = 0.0
		for i in range(size):
			s += self[i] * v[i]
		return s

	# ----------------------------------------------------------------------
	def cross(self, v):
		"""Cross product of 2 vectors"""
		if len(self)==3:
			return Vector(	self[1]*v[2]-self[2]*v[1],
					self[2]*v[0]-self[0]*v[2],
					self[0]*v[1]-self[1]*v[0])
		elif len(self)==2:
			return self[0]*v[1]-self[1]*v[0]
		else:
			raise Exception("Cross product needs 2d or 3d vectors")

	# ----------------------------------------------------------------------
	def length2(self):
		"""Return length squared of vector"""
		s = 0.0
		for i in range(len(self)):
			s += self[i]**2
		return s

	# ----------------------------------------------------------------------
	def length(self):
		"""Return length of vector"""
		s = 0.0
		for i in range(len(self)):
			s += self[i]**2
		return sqrt(s)
	__abs__ = length

	# ----------------------------------------------------------------------
	def arg(self):
		"""return vector angle"""
		return atan2(self[1], self[0])

	# ----------------------------------------------------------------------
	def norm(self):
		"""Normalize vector and return length"""
		l = self.length()
		if l>0.0:
			invlen = 1.0/l
			for i in range(len(self)):
				self[i] *= invlen
		return l
	normalize = norm

	# ----------------------------------------------------------------------
	def unit(self):
		"""return a unit vector"""
		v = self.clone()
		v.norm()
		return v

	# ----------------------------------------------------------------------
	def clone(self):
		"""Clone vector"""
		return Vector(self)

	# ----------------------------------------------------------------------
	def x(self): return self[0]
	def y(self): return self[1]
	def z(self): return self[2]

	# ----------------------------------------------------------------------
	def orthogonal(self):
		"""return a vector orthogonal to self"""
		xx = abs(self.x())
		yy = abs(self.y())

		if len(self)>=3:
			zz = abs(self.z())
			if xx < yy:
				if xx < zz:
					return Vector(0.0, self.z(), -self.y())
				else:
					return Vector(self.y(), -self.x(), 0.0)
			else:
				if yy < zz:
					return Vector(-self.z(), 0.0, self.x())
				else:
					return Vector(self.y(), -self.x(), 0.0)
		else:
			return Vector(-self.y(), self.x())

	# ----------------------------------------------------------------------
	def direction(self, zero=_accuracy):
		"""return containing the direction if normalized with any of the axis"""

		v = self.clone()
		l = v.norm()
		if abs(l) <= zero: return "O"

		if   abs(v[0]-1.0)<zero:
			return  "X"
		elif abs(v[0]+1.0)<zero:
			return "-X"
		elif abs(v[1]-1.0)<zero:
			return  "Y"
		elif abs(v[1]+1.0)<zero:
			return "-Y"
		elif abs(v[2]-1.0)<zero:
			return  "Z"
		elif abs(v[2]+1.0)<zero:
			return "-Z"
		else:
			#nothing special about the direction, return N
			return "N"

	# ----------------------------------------------------------------------
	# Set the vector directly in polar coordinates
	# @param ma magnitude of vector
	# @param ph azimuthal angle in radians
	# @param th polar angle in radians
	# ----------------------------------------------------------------------
	def setPolar(self, ma, ph, th):
		sf = sin(ph)
		cf = cos(ph)
		st = sin(th)
		ct = cos(th)
		self[0] = ma*st*cf
		self[1] = ma*st*sf
		self[2] = ma*ct

	# ----------------------------------------------------------------------
	# @return the azimuth angle.
	# ----------------------------------------------------------------------
	def phi(self):
		if Cmp0(self.x()) and Cmp0(self.y()):
			return 0.0
		return atan2(self.y(), self.x())

	# ----------------------------------------------------------------------
	# @return the polar angle.
	# ----------------------------------------------------------------------
	def theta(self):
		if Cmp0(self.x()) and Cmp0(self.y()) and Cmp0(self.z()):
			return 0.0
		return atan2(self.perp(),self.z())

	# ----------------------------------------------------------------------
	# @return cosine of the polar angle.
	# ----------------------------------------------------------------------
	def cosTheta(self):
		ptot = length()
		if Cmp0(ptot):
			return 1.0
		else:
			return self.z()/ptot

	# ----------------------------------------------------------------------
	# @return the transverse component squared
	#   (R^2 in cylindrical coordinate system).
	# ----------------------------------------------------------------------
	def perp2(self):
		return self.x() * self.x() + self.y() * self.y();

	# ----------------------------------------------------------------------
	# @return the transverse component
	# (R in cylindrical coordinate system).
	# ----------------------------------------------------------------------
	def perp(self):
		return sqrt(self.perp2())

#-------------------------------------------------------------------------------
# Basic 3D Vectors
#-------------------------------------------------------------------------------
Vector.O = Vector(0.0, 0.0, 0.0)
Vector.X = Vector(1.0, 0.0, 0.0)
Vector.Y = Vector(0.0, 1.0, 0.0)
Vector.Z = Vector(0.0, 0.0, 1.0)

#-------------------------------------------------------------------------------
# Return a random 3D vector
#-------------------------------------------------------------------------------
def random3D():
	cosTheta = 2.0*random.random()-1.0
	sinTheta = sqrt(1.0 - cosTheta**2)
	phi = 2.0*pi*random.random()
	return Vector(cos(phi)*sinTheta, sin(phi)*sinTheta, cosTheta)

# ------------------------------------------------------------------------------
# Return a random nolor
# ------------------------------------------------------------------------------
def rndColor(x):
	def rnd(zw):
		w = zw & 0xffff
		z = (zw >> 16) & 0xffff
		z = 36969 * (z & 0xffff) + (z >> 16)
		w = 18000 * (w & 0xffff) + (w >> 16)
		return (z << 16) + (w & 0xffff)

	x = rnd(x)
	R = (x % 224) + 16
	x = rnd(x)
	G = (x % 224) + 16
	x = rnd(x)
	B = (x % 224) + 16
	return R<<16 | G<<8 | B

#===============================================================================
# Matrix class
# Use 4x4 matrix for vector transformations
#===============================================================================
class Matrix(list):
	"""Matrix 4x4 used for vector transformations"""

	# ----------------------------------------------------------------------
	def __init__(self, rows=4, cols=-1, type=0):
		"""
		Matrix(rows=4, cols=-1, type=0|1)
		if rows is integer then
			Create a matrix rows x cols either
			zero(type=0) or unary(type=1)
		elif rows is a list of lists
			create a matrix from a double-list
		"""
		if isinstance(rows, list):
			lst = rows
			self.rows = len(lst)
			self.extend([[]]*self.rows)
			if isinstance(lst[0], list):
				self.cols = len(lst[0])
				for i in range(self.rows):
					self[i] = lst[i][:]
					if len(self[i]) != self.cols:
						raise Exception("Not a valid double-list for a matrix")
			else:
				self.cols = 1
				for i in range(self.rows):
					self[i] = [lst[i]]
		else:
			if rows<2: raise Exception("Array size too small")
			if cols<0: cols=rows
			self.rows = rows
			self.cols = cols
			self += [[]]*rows
			if type==1:
				self.unary()
			else:
				self.zero()

	# ----------------------------------------------------------------------
	# Create a diagonal square matrix from a list
	# ----------------------------------------------------------------------
	@staticmethod
	def diagonal(lst):
		m = Matrix(len(lst), type=0)
		i = 0
		for item in lst:
			m[i][i] = item
			i += 1
		return m

	# ----------------------------------------------------------------------
	# append row
	# ----------------------------------------------------------------------
	def append(self, col):
		list.append(self, col)
		self.rows += 1

	# ----------------------------------------------------------------------
	@staticmethod
	def translate(x, y=0.0, z=0.0):
		"""m = Matrix.translate(x,y,z|vector)
		@return a translation matrix"""
		m = Matrix(4, type=1)
		if isinstance(x,list) or isinstance(x,tuple):
			m[0][3] = x[0]
			m[1][3] = x[1]
			m[2][3] = x[2]
		else:
			m[0][3] = x
			m[1][3] = y
			m[2][3] = z
		return m

	# ----------------------------------------------------------------------
	@staticmethod
	def scale(sx, sy=None, sz=None):
		"""m = Matrix.scale(scale|vector)
		   @return a scaling matrix"""
		m = Matrix(4, type=1)
		if sy is None: sy = sx
		if sz is None: sz = sx
		if isinstance(sx,list) or isinstance(sx,tuple):
			m[0][0] = sx[0]
			m[1][1] = sx[1]
			m[2][2] = sx[2]
		else:
			m[0][0] = sx
			m[1][1] = sy
			m[2][2] = sz
		return m

	# ----------------------------------------------------------------------
	def zero(self):
		"""Zero matrix"""
		for i in range(self.rows):
			self[i] = [0.0]*self.cols

	# ----------------------------------------------------------------------
	def unary(self):
		"""Unary matrix"""
		self.zero()
		for i in range(min(self.rows, self.cols)):
			self[i][i] = 1.0

	# ----------------------------------------------------------------------
	# Create a transformation matrix from 3 normalized vectors
	# and optionally a translation
	# ----------------------------------------------------------------------
	def make(self,X,Y,Z=None,T=None):
		"""Create a transformation matrix from 3 normalized vectors"""
		self.unary()
		if (self.rows==3 or self.rows==4) and self.cols==self.rows:
			if Z is None:
				Z = X ^ Y
				Z.normalize()
			for i in range(3):
				self[0][i] = X[i]
				self[1][i] = Y[i]
				self[2][i] = Z[i]
				if T is not None and self.rows==4: self[i][3] = T[i]
		else:
			raise Exception("Matrix.make() works only on Matrix(3x3) or Matrix(4x4)")

	# ----------------------------------------------------------------------
	def __str__(self):
		"""Multiline string representation of matrix"""
		s = ""
		for i in range(self.rows):
			if i==0:
				first="/"
				last="\\"
			elif i==self.rows-1:
				first="\\"
				last="/"
			else:
				first=last="|"
			s += first
			for j in range(self.cols):
				s += " " + _format % self[i][j]
			s += " " + last + "\n"
		return s

	# ----------------------------------------------------------------------
	def writeOctave(self, filename, name):
		"""Write an octave matrix file"""
		f = open(filename,"w")
		f.write("# bmath.Matrix\n")
		f.write("# name: %s\n"%(name))
		f.write("# type: matrix\n")
		f.write("# rows: %d\n"%(self.rows))
		f.write("# columns: %d\n"%(self.cols))
		for i in range(self.rows):
			for j in range(self.cols):
				f.write("%s "%(str(self[i][j])))
			f.write("\n")
		f.close()

	# ----------------------------------------------------------------------
	def T(self):
		"""@return transpose matrix"""
		m = Matrix(self.cols, self.rows)
		for i in range(self.rows):
			for j in range(self.cols):
				m[j][i] = self[i][j]
		return m
	transpose=T

	# ----------------------------------------------------------------------
	def trace(self):
		"""Return trace of matrix (sum of diagonal elements)"""
		t = 0.0
		for i in range(min(self.rows,self.cols)):
			t += self[i][i]
		return t

	# ----------------------------------------------------------------------
	def __eq__(self, m):
		"""Test for equality of 2 matrices"""
		if self.rows!=m.rows or self.cols!=m.cols:
			return False
		for i in range(self.rows):
			for j in range(self.cols):
				if abs(self[i][j] - m[i][j]):
					return False
		return True

	# ----------------------------------------------------------------------
	# Create a rotation matrix around one axis
	#	X = 0
	#	Y = 1
	#	Z = 2
	# or an arbitrary vector
	# ----------------------------------------------------------------------
	def rotate(self, angle, axis):
		"""Add rotation elements to the matrix around one axis
		Axis X=0, Y=1, Z=2, or an arbitrary one given by vector axis"""
		self.unary()

		c = cos(angle)
		s = sin(angle)

		if isinstance(axis,int):
			m1 = ((axis+1)%3)+1
			m2 = m1%3
			m1 = m1 - 1

			self[m1][m1] =	c
			self[m2][m2] =	c
			self[m1][m2] = -s
			self[m2][m1] =	s

		elif isinstance(axis,Vector):
			l = axis.length()
			x = axis[0] / l
			y = axis[1] / l
			z = axis[2] / l

			c1 = 1 - c
			self[0][0] = x*x + (1-x*x)*c
			self[0][1] = x*y*c1 - z*s
			self[0][2] = x*z*c1 + y*s

			self[1][0] = x*y*c1 + z*s
			self[1][1] = y*y + (1-y*y)*c
			self[1][2] = y*z*c1 - x*s

			self[2][0] = x*z*c1 - y*s
			self[2][1] = y*z*c1 + x*s
			self[2][2] = z*z + (1-z*z)*c

	# ----------------------------------------------------------------------
	@staticmethod
	def rotX(angle):
		"""m = Matrix.rotX(angle) - Return a rotation matrix around X"""
		m = Matrix(4, type=1)
		m.rotate(angle, 0)
		return m

	# ----------------------------------------------------------------------
	@staticmethod
	def rotY(angle):
		"""m = Matrix.rotY(angle) - Return a rotation matrix arround Y"""
		m = Matrix(4, type=1)
		m.rotate(angle, 1)
		return m

	# ----------------------------------------------------------------------
	@staticmethod
	def rotZ(angle):
		"""m = Matrix.rotZ(angle) - Return a rotation matrix arround Z"""
		m = Matrix(4, type=1)
		m.rotate(angle, 2)
		return m

	# ----------------------------------------------------------------------
	def getEulerRotation(self):
		# ROTX(x) * ROTY(y) * ROTZ(z)
		#  cos(z)*cos(y)
		#			sin(z)*cos(y)
		#						-sin(y)
		# -sin(z)*cos(x)+cos(z)*sin(y)*sin(x)
		#			cos(z)*cos(x)+sin(z)*sin(y)*sin(x)
		#						cos(y)*sin(x)
		#  sin(z)*sin(x)+cos(z)*sin(y)*cos(x)
		#			-cos(z)*sin(x)+sin(z)*sin(y)*cos(x)
		#						cos(y)*cos(x)
		rx =  atan2(self[1][2], self[2][2])
		ry = -asin( self[0][2])
		rz =  atan2(self[0][1], self[0][0])
		return rx,ry,rz

	# ----------------------------------------------------------------------
	@staticmethod
	def eulerRotation(rx, ry, rz):
		# ROTX(x) * ROTY(y) * ROTZ(z)
		m = Matrix(4, type=1)
		cx = cos(rx)
		cy = cos(ry)
		cz = cos(rz)
		sx = sin(rx)
		sy = sin(ry)
		sz = sin(rz)

		row = m[0]
		row[0] =  cz*cy
		row[1] =  sz*cy
		row[2] = -sy

		row = m[1]
		row[0] = -sz*cx+cz*sy*sx
		row[1] =  cz*cx+sz*sy*sx
		row[2] =  cy*sx

		row = m[2]
		row[0] =  sz*sx+cz*sy*cx
		row[1] = -cz*sx+sz*sy*cx
		row[2] =  cy*cx

		return m

	# ----------------------------------------------------------------------
	def __add__(self, B):
		"""Add 2 matrices"""
		if self.rows != B.rows or self.cols != B.cols:
			raise Exception("Matrix.add: matrices same size")
		m = Matrix(self.rows, self.cols)
		for i in range(self.rows):
			mrow = m[i]
			arow = self[i]
			brow = B[i]
			for j in range(self.cols):
				mrow[j] = arow[j] + brow[j]
		return m

	# ----------------------------------------------------------------------
	def __sub__(self, B):
		"""Subtract 2 matrices"""
		if self.rows != B.rows or self.cols != B.cols:
			raise Exception("Matrix.add: matrices same size")
		m = Matrix(self.rows, self.cols)
		for i in range(self.rows):
			mrow = m[i]
			arow = self[i]
			brow = B[i]
			for j in range(self.cols):
				mrow[j] = arow[j] - brow[j]
		return m

	# ----------------------------------------------------------------------
	def __neg__(self):
		"""Negate matrix"""
		m = Matrix(self.rows, self.cols)
		for i in range(self.rows):
			mrow = m[i]
			mold = self[i]
			for j in range(self.cols):
				mrow[j] = -mold[j]
		return m

	# ----------------------------------------------------------------------
	def __mul__(self, B):
		"""Multiply two matrices or vector
		   A.__mul__(B|vec) <==> A*B or A*vec"""
		if isinstance(B, Matrix):	# has to be a matrix of same cxN * Nxr
			if self.cols != B.rows:
				raise Exception("arrays don't have the correct dimensions")
			r = Matrix(self.rows, B.cols)
			for i in range(self.rows):
				for j in range(B.cols):
					s = 0.0
					for k in range(self.cols):
						s += self[i][k]*B[k][j]
					r[i][j] = s
			return r

		elif isinstance(B, list):	# Vector or list
			vecsize = len(B)
			v = Vector(vecsize)
			for i in range(vecsize):
				for j in range(min(self.cols, vecsize)):
					v[i] += self[i][j] * B[j]
				for j in range(vecsize, self.cols):
					v[i] += self[i][j]
			return v

		else:
			for row in self:
				for i in range(self.cols):
					row[i] *= B
			return self

	# -----------------------------------------------------------------------
	# Special function to multiply a transformation matrix with a vector
	# ignoring the translation
	# -----------------------------------------------------------------------
	def multNoTranslation(self, B):
		"""Multiply matrix with a vector ignoring the translation part"""
		if not isinstance(B, list):
			raise Exception("Invalid operation")
		vecsize = len(B)
		v = Vector(vecsize)
		for i in range(vecsize):
			for j in range(min(self.cols, vecsize)):
				v[i] += self[i][j] * B[j]
		return v

	# ----------------------------------------------------------------------
	def inv(self):
		"""Inverse matrix in place"""

		if self.rows != self.cols:
			raise Exception("inverting a non square matrix")
		index = [ 0 ] * self.rows
		self.__ludcmp(index)
		y = Matrix(self.rows)
		for j in range(self.rows):
			col = [ 0.0 ] * self.rows
			col[j] = 1.0
			self.__lubksb(index,col)
			for i in range(self.rows):
				y[i][j] = col[i]
		for j in range(self.rows):
			self[j] = y[j]
	inverse = inv

	# ----------------------------------------------------------------------
	def clone(self):
		"""Clone matrix"""
		m = Matrix(self.rows, self.cols)
		for i in range(self.rows):
			m[i] = self[i][:]
		return m

	# ----------------------------------------------------------------------
	# determinant with Gauss method
	# ----------------------------------------------------------------------
	def det(self, eps=_accuracy):
		"""determinant of square matrix using Gauss method"""
		if self.rows == 2:
			return self[0][0]*self[1][1] - self[1][0]*self[0][1]
		elif self.rows == 3:
			return self[0][0]*(self[1][1]*self[2][2] - self[2][1]*self[1][2]) \
			     - self[0][1]*(self[1][0]*self[2][2] - self[2][0]*self[1][2]) \
			     + self[0][2]*(self[1][0]*self[2][1] - self[2][0]*self[1][1])

		M = self.clone()
		s = 1.0
		n = M.rows
		for i in range(n-1):
			# find the absolute maximum value
			ma = abs(M[i][i])
			k  = i
			for j in range(i+1, n):
				if abs(M[j][i]) > ma:
					ma = abs(M[j][i])
					k  = j
			if ma < eps: return 0.0

			# swap rows i,k
			if i != k:
				s = -s;   # Change sign of determinate
				for j in range(n):
					d = M[i][j]
					M[i][j] = M[k][j]
					M[k][j] = d

			# make all the following rows with zero at the i column
			for j in range(i+1, n):
				if abs(M[j][i]) < _accuracy: continue
				d = - M[i][i] / M[j][i]
				s *= d
				for k in range(i,n):
					M[j][k] = M[i][k] + d * M[j][k]

		d = M[0][0] / s
		for i in range(1,n):
			d *= M[i][i]
		return d

	determinant = det

	# ----------------------------------------------------------------------
	# LU decomposition.
	# Parameters
	#      index[0:size]	row permutation record
	# ----------------------------------------------------------------------
	def __ludcmp(self, index): #procedure expose indx.
		size = self.rows
		vv = [ 0.0 ] * size
		for i in range(size):
			big = 0.0
			for j in range(size):
				big = max(abs(self[i][j]), big)
			if big==0:
				raise Exception("Singular matrix found")
			vv[i] = 1.0/big

		for j in range(size):
			for i in range(j):
				s = self[i][j]
				for k in range(i):
					s -= self[i][k] * self[k][j]
				self[i][j] = s

			big = 0.0
			for i in range(j,size):
				s = self[i][j]
				for k in range(j):
					s -= self[i][k] * self[k][j]

				self[i][j] = s
				dum = vv[i]*abs(s)
				if dum >= big:
					big = dum
					imax = i

			if j != imax:
				for k in range(size):
					dum = self[imax][k]
					self[imax][k] = self[j][k]
					self[j][k] = dum
				vv[imax] = vv[j]

			index[j] = imax
			if self[j][j] == 0.0:
				self[j][j] = 1E-20

			if j != size-1:
				dum = 1.0/self[j][j]
				for i in range(j+1,size):
					self[i][j] *= dum

	# ----------------------------------------------------------------------
	# backward substitution
	#      index[0:size]	  row permutation record
	#      col[0:size]	  right hand vector (?)
	# ----------------------------------------------------------------------
	def __lubksb(self, index, col):
		ii = -1
		size = self.rows
		for i in range(size):
			ip = index[i]
			s = col[ip]
			col[ip] = col[i]
			if ii >= 0:
				for j in range(ii,i):
					s -= self[i][j] * col[j]
			elif s != 0.0:
				ii = i
			col[i] = s

		for i in range(size-1,-1,-1):
			s = col[i]
			for j in range(i+1,size):
				s -= self[i][j] * col[j]
			col[i] = s/self[i][i]

#-------------------------------------------------------------------------------
# Basic Matrices
#-------------------------------------------------------------------------------
Matrix.O = Matrix(4, type=0)
Matrix.U = Matrix(4, type=1)

#-------------------------------------------------------------------------------
# Quaternion
#
# Note: See the following for more information on quaternions:
#
# - Shoemake, K., Animating rotation with quaternion curves, Computer
#   Graphics 19, No 3 (Proc. SIGGRAPH'85), 245-254, 1985.
# - Pletinckx, D., Quaternion calculus as a basic tool in computer
#   graphics, The Visual Computer 5, 2-13, 1989.
#-------------------------------------------------------------------------------
class Quaternion(list):
	def __init__(self, a, b=None, c=None, d=None):
		if isinstance(a, Quaternion):
			self.extend(a)

		elif isinstance(a, Matrix):
			tr = a[0][0] + a[1][1] + a[2][2] + 1.0		# trace of matrix
			if tr > 0:
				S = sqrt(tr) * 2.0			# S=4*qw
				qw = 0.25 * S
				qx = (a[2][1] - a[1][2]) / S
				qy = (a[0][2] - a[2][0]) / S
				qz = (a[1][0] - a[0][1]) / S
			elif a[0][0] > a[1][1] and a[0][0] > a[2][2]:
				S = sqrt(1.0 + a[0][0] - a[1][1] - a[2][2]) * 2.0 # S=4*qx
				qx = 0.25 * S
				qy = (a[0][1] + a[1][0]) / S
				qz = (a[0][2] + a[2][0]) / S
				qw = (a[2][1] - a[1][2]) / S
			elif a[1][1] > a[2][2]:
				S = sqrt(1.0 + a[1][1] - a[0][0] - a[2][2]) * 2.0 # S=4*qy
				qx = (a[0][1] + a[1][0]) / S
				qy = 0.25 * S
				qz = (a[1][2] + a[2][1]) / S
				qw = (a[0][2] - a[2][0]) / S
			else:
				S = sqrt(1.0 + a[2][2] - a[0][0] - a[1][1]) * 2.0 # S=4*qz
				qx = (a[0][2] + a[2][0]) / S
				qy = (a[1][2] + a[2][1]) / S
				qz = 0.25 * S
				qw = (a[1][0] - a[0][1]) / S
			self.extend([qx, qy, qz, qw])

		elif isinstance(a,Vector) and isinstance(b,float):
			s = sin(b/2.0) / a.length()
			self.append(a[0]*s)
			self.append(a[1]*s)
			self.append(a[2]*s)
			self.append(cos(b/2.0))

		else:
			self.extend([a,b,c,d])

	# ----------------------------------------------------------------------
	# Quaternions always obey:  a^2 + b^2 + c^2 + d^2 = 1.0
	# If they don't add up to 1.0, dividing by their magnitued will
	# renormalize them.
	# ----------------------------------------------------------------------
	def norm(self):
		"""normalize quaternion"""
		mag = sqrt(self[0]**2 + self[1]**2 + self[2]**2 + self[3]**2)
		self[0] /= mag
		self[1] /= mag
		self[2] /= mag
		self[3] /= mag
		return mag
	normalize = norm

	# ----------------------------------------------------------------------
	def vector(self):
		"""return vector of quaternion"""
		return Vector(self[0], self[1], self[2])

	# ----------------------------------------------------------------------
	# return rotation matrix
	# ----------------------------------------------------------------------
	def matrix(self):
		"""return rotation matrix"""
		m = Matrix(4, type=1)
		m[0][0] = 1.0 - 2.0 * (self[1] * self[1] + self[2] * self[2])
		m[0][1] = 2.0 * (self[0] * self[1] - self[2] * self[3])
		m[0][2] = 2.0 * (self[2] * self[0] + self[1] * self[3])

		m[1][0] = 2.0 * (self[0] * self[1] + self[2] * self[3])
		m[1][1] = 1.0 - 2.0 * (self[2] * self[2] + self[0] * self[0])
		m[1][2] = 2.0 * (self[1] * self[2] - self[0] * self[3])

		m[2][0] = 2.0 * (self[2] * self[0] - self[1] * self[3])
		m[2][1] = 2.0 * (self[1] * self[2] + self[0] * self[3])
		m[2][2] = 1.0 - 2.0 * (self[1] * self[1] + self[0] * self[0])
		return m

	# ----------------------------------------------------------------------
	# Given two rotations, e1 and e2, expressed as quaternion rotations,
	# figure out the equivalent single rotation and stuff it into dest.
	# This routine also normalizes the result every RENORMCOUNT times it is
	# called, to keep error from creeping in.
	# ----------------------------------------------------------------------
	def __add__(self, b):
		v1 = self.vector()
		v2 = b.vector()
		t1 = v1 * b[3]
		t2 = v2 * self[3]
		t3 = v2.cross(v1)
		tf = t1 + t2 + t3
		q = Quaternion(tf, self[3]*b[3] - v1.dot(v2))
		q.norm()
		return q

	# ----------------------------------------------------------------------
	def __iadd__(self, b):
		v1 = self.vector()
		v2 = b.vector()
		t1 = v1 * b[3]
		t2 = v2 * self[3]
		t3 = v2.cross(v1)

		tf = t1 + t2 + t3

		self[0] = tf[0]
		self[1] = tf[1]
		self[2] = tf[2]
		self[3] = self[3]*b[3] - v1.dot(v2)
		self.norm()
		return self

#-------------------------------------------------------------------------------
def gauss(A, B):
	"""Solve A*X = B using the Gauss elimination method"""

	n = len(A)
	s = [0.0]*n
	X = [0.0]*n

	p = [i for i in range(n)]
	for i in range(n):
		s[i] = max([abs(x) for x in A[i]])

	for k in range(n-1):
		# select j>=k so that
		# |A[p[j]][k]| / s[p[i]] >= |A[p[i]][k]| / s[p[i]] for i = k,k+1,...,n
		j = k
		ap = abs(A[p[j]][k]) / s[p[j]]
		for i in range(k+1, n):
			api = abs(A[p[i]][k]) / s[p[i]]
			if api>ap:
				j  = i
				ap = api

		if j!=k: p[k],p[j] = p[j],p[k]		# Swap values

		for i in range(k+1, n):
			z = A[p[i]][k] / A[p[k]][k]
			A[p[i]][k] = z
			for j in range(k+1, n):
				A[p[i]][j] -= z * A[p[k]][j]

	for k in range(n-1):
		for i in range(k+1,n):
			B[p[i]] -= A[p[i]][k] * B[p[k]]

	for i in range(n-1, -1, -1):
		X[i] = B[p[i]]
		for j in range(i+1, n):
			X[i] -= A[p[i]][j] * X[j]
		X[i] /= A[p[i]][i]

	return X

#-------------------------------------------------------------------------------
def solveOverDetermined(A, B, W=None):
	"""Solve the overdetermined linear system defined by the matrices A,B
		such as A*X = B
	Optionally a weight can be specified"""
	if A.rows < A.cols:
		raise Exception("solveOverDetermined: A matrix has more columns than rows")
	AT  = A.transpose()
	if W:
		Wd = Matrix.diagonal(W)
		ATA = AT * Wd * A
		ATB = AT * Wd * B
	else:
		ATA = AT * A
		ATB = AT * B
	ATA.inv()
	RT = ATA * ATB
	return [RT[i][0] for i in range(len(RT))]

#-------------------------------------------------------------------------------
def linear(X, Y):
	"""
	Solve linear regression y = ax + b
	@return a,b,r
	"""
	Sx = Sy = Sx2 = Sy2 = Sxy = 0.0
	for x,y in zip(X,Y):
		Sx  += x
		Sy  += y
		Sx2 += x*x
		Sy2 += y*y
		Sxy += x*y

	n = float(len(X))
	try:
		b = (Sxy - Sx*Sy/n) / (Sx2 - Sx*Sx/n)
		a = Sy/n - b * Sx/n
		r = (Sxy - Sx*Sy/n) / sqrt(Sx2-Sx*Sx/n) * sqrt(Sy2-Sy*Sy/n)
		return a,b,r

	except ZeroDivisionError:
		return None

#-------------------------------------------------------------------------------
#   Idiotimes pragmatikwv symmetrikwv pivakwv
#
#   O algori8mos poy xrnsimopoieitai stnv roytiva eivai gvwstos sav
#   proseggistikn me8odos Jacobi.
#   O algori8mos ekmetaleyetai tnv idiotnta poy exoyv oi diagwvioi
#   pivakes, dnladn pivakes me mndevika ola ta stoixeia ektos tns
#   kyrias diagwvioy, va exoyv sav idiotimes ta diagwvia stoixeia.
#   Me tov metasxnmatismo.
#	      T			      T
#      A1 = R1 (f) A R1(f),    A2 = R2 (f) A1 R2(f)
#   metaballoyme syvexws tov pivaka A, mexris otoy to a8roisma olwv
#   twv mn diagwviwv stoixeiwv f8asei mia ka8orismevn timn tns eklogns
#   toy xrnstn n givei mndev
#   Ta bnmata tns diadikasias eivai:
#   1. Avazntnsn toy apolytws megistoy mn diagwvioy stoixeioy
#      Divei ta p kai q
#   2. Prosdiorismos tns gwvias peristrofns f. Divei ta sinf kai cosf
#   3. Metasxnmatismos Ai -> Ai+1
#   4. Elegxos av to a8roisma twv mn diagwviwv stoixeiwv exei f8asei tnv
#      epi8ymntn timn. Eav vai tote ta diagwvia stoixeia eivai oi
#      proseggiseis twv idiotimwv, eav oxi tote epistrefoyme sto 1.
#      px.     |  1 -2 -1 |
#	   A = | -2  1 -1 |
#	       | -1 -1 2.5|
#      apolyto megisto A(1,2) = -2
#      Ypologizoyme tnv gwvia f, co=cos(f), si=sin(f) kai kavoyme tov
#      metasxnmatismo
#	   | co -si  0 |   |  1 -2 -1 |   |  co  si  0 |
#      A = | si  co  0 | x | -2  1 -1 | x | -si  co  0 |
#	   |  0   0  1 |   | -1 -1 2.5|   |   0   0  1 |
#
#
#      Oi parametroi tns roytivas eivai oi e3ns:
#	 A     - pivakas tetragwvikos
#	 eps   - akribeia (a8roisma tetragwvwv)
#	 check - av prepei va elejei tnv symmetria toy arxikoy pivaka
#		 n oxi
#-------------------------------------------------------------------------------
def eigenvalues(M, eps=_accuracy, check=False):
	"""Return eigen values and eigen vectors of a symmetric matrix"""
	n = M.rows

	# elegxos av eivai symmetrikos o pivakas
	if check:
		if n != M.cols: return None
		for i in range(n):
			for j in range(i,n):
				if M[i][j] != M[j][i]:
					return None

	# Allocate arrays
	A  = M.clone()
	R  = Matrix(n, type=0)
	RT = Matrix(n, type=0)
	ZW = Matrix(n, type=0)
	V  = None

	# kavovika 8a prepei meta apo merikes prospa8eies va tov aporiptei
	while True:
		# Bnma 1. Avazntnsn toy apolytws megistoy mn diagwvioy stoixeioy
		p=0; q=1; el=abs(A[p][q])
		for i in range(1, n):
			for j in range(i):
				if abs(A[i][j]) > el:
					el = abs(A[i][j])
					p = i; q = j
			if el==0: break

		# Ftiaxvei ta R, RT
		for i in range(n):
			for j in range(n):
				R[i][j] = RT[i][j] = (i==j)

		# Bnma 2. Prosdiorizei tnv gwvia f, cosf kai sinf
		fi = (A[q][q] - A[p][p]) / (2*A[p][q])
		t = 1 / (fi + sqrt(fi*fi+1))
		if fi<0: t = -t
		co = 1 / sqrt(1+t*t)
		si = t / sqrt(1+t*t)

		R[p][p]  = R[q][q]  = co
		RT[p][p] = RT[q][q] = co

		R[p][q]  = si;	   R[q][p] = -si
		RT[p][q] = -si;   RT[q][p] = si

		# Bnma 3. metasxnmatismos Ai+1 = Rt * Ai * R
		#	  ka8os kai to ginomeno Rn*...*R2*R1 that
		#	  gives us the eigenvectors
		if V is None:
			V = R.clone()
		else:
			V = V * R

		for i in range(n):
			for j in range(n):
				if j!=p and j!=q:
					ZW[i][j] = A[i][j]
				else:
					zw1 = 0
					for k in range(n):
						zw1 +=	A[i][k] * R[k][j]
					ZW[i][j] = zw1

		for i in range(n):
			for j in range(n):
				if i!=p and i!=q:
					A[i][j] = ZW[i][j]
				else:
					zw1 = 0
					for k in range(n):
						zw1 += RT[i][k] * ZW[k][j]
					A[i][j] = zw1

		# Bnma 4. Briskoymai to a8roisma kai elegxoyme av teleiwse
		zw1 = 0
		k   = 0
		for i in range(1,n):
			for j in range(i):
				zw1 += A[i][j] * A[i][j]
			k += 1
		zw1 /= n

		# Exit condition
		if zw1 <= eps: break
	return ([A[i][i] for i in range(n)],V.T())

#-------------------------------------------------------------------------------
# Given a function, and given a bracketing triplet of abscissas ax,bx,cx (such
# that bx is between ax and cx, and f(bx) is less than both f(ax) and f(cx),
# this routing performs a golden section search for the minimum, isolating it
# to a fractional precision of about eps. The abscissa of the minimum is
# returned as xmin, and the minimum function value is returned as golden, the
# returned function value.
#
# @param func	function to be evaluated
# @param ax	triplet of abscissas ax,bx,cx
# @param bx	where func(x+bx*d) < min[ func(x+ax*d), func(x+cx*d) ]
# @param cx	...
# @param x	starting vector/value
# @param d	direction vector/value
# @param eps	accuracy of search
#-------------------------------------------------------------------------------
def goldenSectionSearch(func, ax, bx, cx, x, d=1, eps=_accuracy):
	R = 0.61803399		# The golden ratio
	C = (1.0-R)
	x0 = ax			# At any given time we will keep track of four points
	x3 = cx			# x0, x1, x2, x3
	if abs(cx-bx) > abs(bx-ax):
		x1 = bx
		x2 = bx + C*(cx-bx)
	else:
		x2 = bx
		x1 = bx - C*(bx-ax)

	f1 = func(x+x1*d)	# The initial function evaluation
	f2 = func(x+x2*d)
	while abs(x3-x0) > eps*(abs(x1)+abs(x2)):
		if f2 < f1:
			x0 = x1
			x1 = x2
			x2 = R*x1 + C*x3
			f1 = f2
			f2 = func(x+x2*d)
		else:
			x3 = x2
			x2 = x1
			x1 = R*x2 + C*x0
			f2 = f1
			f1 = func(x+x1*d)

	if f1 < f2:
		return x1
	else:
		return x2

#-------------------------------------------------------------------------------
# Generators for calculating a) the permutations of a sequence and
# b) the combinations and selections of a number of elements from a
# sequence. Uses Python 2.2 generators.
# Similar solutions found also in comp.lang.python
# Keywords: generator, combination, permutation, selection
#
# See also: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/105962
# See also: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66463
# See also: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66465
#-------------------------------------------------------------------------------
def xcombinations(items, n):
	if n<=0: yield []
	else:
		for i in range(len(items)):
			for cc in xcombinations(items[:i]+items[i+1:],n-1):
				yield [items[i]]+cc

def xuniqueCombinations(items, n):
	if n<=0: yield []
	else:
		for i in range(len(items)):
			for cc in xuniqueCombinations(items[i+1:],n-1):
				yield [items[i]]+cc

def xselections(items, n):
	if n<=0: yield []
	else:
		for i in range(len(items)):
			for ss in xselections(items, n-1):
				yield [items[i]]+ss

def xpermutations(items):
	return xcombinations(items, len(items))

#-------------------------------------------------------------------------------
# Conversion between rectangular and polar coordinates
# Usage:
#	real, real = rect(real, real [, deg=False])
#	real, real = polar(real, real [, deg=False])
# Normally, rect() and polar() uses radian for angle; but,
# if deg=True specified, degree is used instead.
#-------------------------------------------------------------------------------
# radian if deg=False; degree if deg=True
def rect(r, w, deg=False):
	"""
	Convert from polar (r,w) to rectangular (x,y)
	    x = r cos(w)
	    y = r sin(w)
	"""
	if deg: w = radians(w)
	return r * cos(w), r * sin(w)

#-------------------------------------------------------------------------------
# radian if deg=False; degree if deg=True
#-------------------------------------------------------------------------------
def polar(x, y, deg=False):
	"""
	Convert from rectangular (x,y) to polar (r,w)
	    r = sqrt(x^2 + y^2)
	    w = arctan(y/x) = [-pi,pi] = [-180,180]
	"""
	if deg:
		return hypot(x, y), degrees(atan2(y, x))
	else:
		return hypot(x, y), atan2(y, x)

#-------------------------------------------------------------------------------
# Quadratic equation: x^2 + ax + b = 0 (or ax^2 + bx + c = 0)
#    Solve quadratic equation with real coefficients
#
# Usage
#    number, number = quadratic(real, real [, real])
#
# Normally, x^2 + ax + b = 0 is assumed with the 2 coefficients # as
# arguments; but, if 3 arguments are present, then ax^2 + bx + c = 0 is assumed.
#-------------------------------------------------------------------------------
#def quadratic(a, b, c=None):
#	"""
#	x^2 + ax + b = 0 (or ax^2 + bx + c = 0)
#	By substituting x = y-t and t = a/2,
#	the equation reduces to y^2 + (b-t^2) = 0
#	which has easy solution
#	y = +/- sqrt(t^2-b)
#	"""
#	if c: # (ax^2 + bx + c = 0)
#		a, b = b / float(a), c / float(a)
#	t = a / 2.0
#	r = t**2 - b
#	if r >= 0: # real roots
#		y1 = sqrt(r)
#	else: # complex roots
#		y1 = cmath.sqrt(r)
#	y2 = -y1
#	return y1 - t, y2 - t

def quadratic(b, c, eps=_accuracy):
	D = b*b - 4.0*c
	if D <= 0.0:
		x1 = -0.5*b	# Always return this as a solution!!!
		if D >= -eps*(b*b+abs(c)):
			return x1,x1
		else:
			return None,None
	else:
		if b>0.0:
			bD = -b - sqrt(D)
		else:
			bD = -b + sqrt(D)
		return 0.5 * bD, 2.0 * c / bD

#-------------------------------------------------------------------------------
# Cubic equation: y^3 + a*y^2 + b*y + c = 0 (or ax^3 + bx^2 + cx + d = 0)
#
# Normally, x^3 + ax^2 + bx + c = 0 is assumed with the 3 coefficients as
# arguments; but, if 4 arguments are present, then ax^3 + bx^2 + cx + d = 0 is
# assumed.
#
# Even though both quadratic() and cubic() functions take real arguments, they
# can be modified to accept any real or complex coefficients because the method
# of solution does not make any assumptions.
#-------------------------------------------------------------------------------
def cubic(a, b, c, d=None, eps=_accuracy):
	if d is not None: # (ax^3 + bx^2 + cx + d = 0)
		a, b, c = b/float(a), c/float(a), d/float(a)

	Q = (a*a - 3.0*b) / 9.0
	R = (2.*a**3 - 9.*a*b + 27.*c)/54.

	R2 = R**2
	Q3 = Q**3
	if R2 < Q3:	# the cubic has 3 real solutions
		theta = acos(R/sqrt(Q3))
		sqrt_Q = sqrt(Q)
		x1 = -2. * sqrt_Q * cos(theta/3.) - a/3.
		x2 = -2. * sqrt_Q * cos((theta+2.*pi)/3.) - a/3.
		x3 = -2. * sqrt_Q * cos((theta-2.*pi)/3.) - a/3.
		return x1,x2,x3

	A = -copysign(1.0,R) * (abs(R) + sqrt(R2 - Q3))**(1./3.)
	if abs(A)>eps:
		B = Q / A
	else:
		B = 0.0

	return (A+B) - a/3., None, None

	# imaginary roots
	# x2 = -(A+B)/2 - a/3 + i*sqrt(3)*(A-B)
	# x3 = -(A+B)/2 - a/3 - i*sqrt(3)*(A-B)

#-------------------------------------------------------------------------------
# Fit a plane to a set of points using least square fitting
#-------------------------------------------------------------------------------
def fitPlane(xyz):
	# First do statistics with points
	Sx  = Sy  = Sz  = 0.0
	Sx2 = Sy2 = Sz2 = 0.0
	Sxy = Syz = Sxz = 0.0
	for x,y,z in xyz:
		Sx  += x
		Sy  += y
		Sz  += z

		Sx2 += x**2
		Sy2 += y**2
		Sz2 += z**2

		Sxy += x*y
		Syz += y*z
		Sxz += x*z

	n = float(len(xyz))
	Sx /= n
	Sy /= n
	Sz /= n
	Vx = Sx2/n - Sx**2
	Vy = Sy2/n - Sy**2
	Vz = Sz2/n - Sz**2

	# Count zero variances
	nv = int(abs(Vx)<=_accuracy) + int(abs(Vy)<=_accuracy) + int(abs(Vz)<=_accuracy)
	if nv>1:
		return None
	elif nv==1:
		# Planes parallel to axes
		# Try the solution of x=Xo or y=Yo or z=Zo
		if abs(Vx)<=_accuracy:
			return 1.0, 0.0, 0.0, -Sx
		elif abs(Vy)<=_accuracy:
			return 0.0, 1.0, 0.0, -Sy
		else:
			return 0.0, 0.0, 1.0, -Sz

	# Try a generic solution
	#  z = ax + by + d    <=>  ax + by -z + d = 0
	#  assuming c=-1
	#  it can only fail on ax + by + d = 0
	#
	#  / Sx2    Sxy    Sx \       / Sxz \
	#  | Sxy    Sy2    Sy | * X = | Syz |
	#  \ Sx     Sy     n  /       \ Sz  /
	A = Matrix([[Sx2, Sxy, Sx], [Sxy, Sy2, Sy], [Sx, Sy, n]])
	B = Matrix([[Sxz], [Syz], [Sz]])

	try:
		A.inverse()
		X = A*B
		return X[0][0], X[1][0], -1.0, X[2][0]
	except:
		pass

	# Try a solution where c=0
	# y = ax + d  <=>   ax -y +d = 0
	#.
	#  / Sx2    Sx \       / Sxy \
	#  |           | * X = |     |
	#  \ Sx     n  /       \ Sy  /
	A = Matrix([[Sx2, Sx], [Sx, n]])
	B = Matrix([[Sxy], [Sy]])
	try:
		A.inverse()
		X = A*B
		return X[0][0], -1.0, 0.0, X[1][0]
	except:
		return None

#-------------------------------------------------------------------------------
# Evaluating n'th degree polynomial is simple loop, starting with highest
# coefficient a[n].
#-------------------------------------------------------------------------------
def polyeval(a, x):
	"""
	p(x) = polyeval(a, x)
	     = a[0] + a[1]x + a[2]x^2 +...+ a[n-1]x^{n-1} + a[n]x^n
	     = a[0] + x(a[1] + x(a[2] +...+ x(a[n-1] + a[n]x)...)
	"""
	p = 0
	a.reverse()
	for coef in a:
		p = p*x + coef
	a.reverse()
	return p

#-------------------------------------------------------------------------------
# Find the first derivative of a polynomial
#-------------------------------------------------------------------------------
def polyderiv(a):
	"""
	p'(x) = polyderiv(a)
	      = b[0] + b[1]x + b[2]x^2 +...+ b[n-2]x^{n-2} + b[n-1]x^{n-1}
	where b[i] = (i+1)a[i+1]
	"""
	b = []
	for i in range(1, len(a)):
		b.append(i * a[i])
	return b

#-------------------------------------------------------------------------------
# Factor out a root from n'th degree polynomial, and return the remaining
# (n-1)'th degree polynomial.
# list = polyreduce(list, number)
#-------------------------------------------------------------------------------
def polyreduce(a, root):
	"""
	Given x = r is a root of n'th degree polynomial p(x) = (x-r)q(x),
	divide p(x) by linear factor (x-r) using the same algorithm as
	polynomial evaluation. Then, return the (n-1)'th degree quotient
	q(x) = polyreduce(a, r)
	     = c[0] + c[1]x + c[2]x^2 +...+ c[n-2]x^{n-2} + c[n-1]x^{n-1}
	"""
	c, p = [], 0
	a.reverse()
	for coef in a:
		p = p * root + coef
		c.append(p)
	a.reverse()
	c.reverse()
	return c[1:]

#-------------------------------------------------------------------------------
# Conversion from integer to Roman
#-------------------------------------------------------------------------------
def int2roman(num):
	"""
	Convert an integer to Roman numeral
	"""
	if not isinstance(num,int):
		raise TypeError("expected integer, got %s" % type(input))

	if not 0 < num < 4000:
		raise ValueError("Argument must be between 1 and 3999")

	ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
	nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
	result = ""
	for i in range(len(ints)):
		count = int(num / ints[i])
		result += nums[i] * count
		num -= ints[i] * count
	return result

#-------------------------------------------------------------------------------
# Conversion from Roman to integer
#-------------------------------------------------------------------------------
def roman2int(roman):
	"""
	convert a roman string to integer
	"""
	if not isinstance(roman,str):
		raise TypeError("expected string, got %s"%type(roman))
	roman = roman.upper()
	nums = ('M', 'D', 'C', 'L', 'X', 'V', 'I')
	ints = (1000, 500, 100, 50,  10,  5,   1)
	places = []
	for c in roman:
		if not c in nums:
			raise ValueError("input is not a valid roman numeral: %s"%roman)
	for i in range(len(roman)):
		c = roman[i]
		value = ints[nums.index(c)]
		# If the next place holds a larger number, this value is negative.
		try:
			nextvalue = ints[nums.index(roman[i +1])]
			if nextvalue > value:
				value *= -1
		except IndexError:
			# there is no next place.
			pass
		places.append(value)
	sum = 0
	for n in places: sum += n

	# Easiest test for validity...
	if int2roman(sum) == roman:
		return sum
	else:
		raise ValueError('input is not a valid roman numeral: %s' % roman)

#===============================================================================
if __name__ == "__main__":
	import sys
	import pdb
	from log import say

	for i in range(4,50):
		num = "-1e-%d"%(i)
		say(num, repr(float(num)), format(num,10))

	digits="1234567890123456789012345678"
	for i in range(len(digits)):
		num = digits[:i]
		say("%02d %40s |%10s|"%(i, num, format(num,10)))
	say()
	for i in range(len(digits)):
		num = digits[:i]+".123"
		say("%02d %40s |%10s|"%(i, num, format(num,10)))
	say()
	for i in range(len(digits)):
		num = digits[:i]+".1234567890"
		say("%02d %40s |%10s|"%(i, num, format(num,10)))
	say()
	for i in range(len(digits)):
		num = "-"+digits[:i]
		say("%02d %40s |%10s|"%(i, num, format(num,10)))
	say()
	for i in range(len(digits)):
		num = "-"+digits[:i]+".123"
		say("%02d %40s |%10s|"%(i, num, format(num,10)))
	say()
	for i in range(len(digits)):
		num = "-"+digits[:i]+".1234567890"
		say("%02d %40s |%10s|"%(i, num, format(num,10)))

	say(Vector.O)
	a = 1.2345678901234567890
	w = -1e-05
	say(format(w,22))
	say(format(a,22))
	say(Vector.Y.direction(0.0000001))
	#for i in range(100000):
	#	v = random3D()
	#	d1 = v.direction(0.001)
	#	d2 = v.olddir(0.001)
	#	if d1!="N": say(d1, d2)
	#	#if d1!=d2:
	#	#	say(d1, d2, v)
	#for i in frange(0.0,1.0,0.1):
	#	say(i)
	#say("-------")
	#for i in frange(1.0,0.0,-0.1):
	#	say(i)
	a = Vector(range(5))
	a.norm()
	say("a=",a,"len(a)=",a.length())
	b = Vector(range(5))
	say("b=",b,"length(b)=",b.length(),"len(b)=",len(b))

	say("matO\n",Matrix.O)
	say("matU\n",Matrix.U)

	M = Matrix(4)
	a = Vector(0.1, 0.2, 0.3)
	M.rotate(radians(45.0), a)
	say("M\n",M)
	say("a=",a)
	say("M*a=",M*a)
	say("M*X=",M*Vector.X)

	say(d2s(dms(1,2,3.006)))

	M = Matrix([[ 1.0, -2.0, -3.0,	1.0],
		    [-2.0,  1.0, -2.0, -1.0],
		    [-3.0, -2.0,  2.0,	2.0],
		    [ 1.0, -1.0,  2.0,	3.0]] )
	say("M=\n",M)
	say("det(M)=",M.det())
	v,u = eigenvalues(M)
	say("Eigenvalues=",v)
	say("Eigenvectors=\n",u)
	say("uT * diag(v) * u=\n",u.T()*Matrix.diagonal(v)*u)

	say()
	say("Permutations of 'love'")
	for p in xpermutations(['l','o','v','e']): say(''.join(p))

	say()
	say("Combinations of 2 letters from 'love'")
	for c in xcombinations(['l','o','v','e'],2): say(''.join(c))

	say()
	say("Unique Combinations of 2 letters from 'love'")
	for uc in xuniqueCombinations(['l','o','v','e'],2): say(''.join(uc))

	say()
	say("Selections of 2 letters from 'love'")
	for s in xselections(['l','o','v','e'],2): say(''.join(s))

	say()
	say(map(''.join, list(xpermutations('done'))))

	say()
	say("cubic(x^3-3x^2-10x+24=0)=",cubic(-3.0,-10.0,24.0))

	say()
	for i in range(1,51): say(i, int2roman(i))
