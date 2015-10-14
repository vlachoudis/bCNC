#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bpath.py 3575 2015-09-14 07:20:22Z bnv $
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
import time
from math import *
from bmath import Vector, quadratic

EPS0 = 1E-7
EPS  = 0.00001
EPS2 = EPS**2
PI2  = 2.0*pi

LINE = 1
CW   = 2
CCW  = 3
_TYPES = ["LINE","CW  ","CCW "]

#------------------------------------------------------------------------------
# Compare two Vectors if they are the same
#------------------------------------------------------------------------------
def eq(A,B):
	d2  = (A[0]-B[0])**2 + (A[1]-B[1])**2
	err = EPS2 * ((abs(A[0])+abs(B[0]))**2 + \
		      (abs(A[1])+abs(B[1]))**2 + 1.0)
	return d2<err

#------------------------------------------------------------------------------
# Compare two Vectors if they are the same
#------------------------------------------------------------------------------
def eq2(A,B,acc):
	d2  = (A[0]-B[0])**2 + (A[1]-B[1])**2
	err = acc*acc*((abs(A[0])+abs(B[0]))**2 + \
		       (abs(A[1])+abs(B[1]))**2 + 1.0)
	return d2<err

#==============================================================================
# Segment
#==============================================================================
class Segment:
	def __init__(self, t, s, e, c=None): #, r=None): #, sPhi=None, ePhi=None):
		self.type  = t
		self.start = s
		self.end   = e
		self.cross = False	# end point is a path cross point
		self.AB = self.end-self.start
		if self.type==LINE:
			self.calcBBox()
		elif self.type!=LINE and c is not None:
			self.setCenter(c)
			#self.setArc(c, r) #, sPhi, ePhi)

	#----------------------------------------------------------------------
	def setCenter(self, c):
		self.center = c
		self.radius   = (self.start-self.center).length()	# based on starting point
		self.startPhi = atan2(self.start[1]-c[1], self.start[0]-c[0])
		self.endPhi   = atan2(self.end[1]  -c[1], self.end[0]  -c[0])
		if abs(self.startPhi)<EPS0: self.startPhi = 0.0
		if abs(self.endPhi)  <EPS0: self.endPhi   = 0.0
		self._correct()
		self.calcBBox()

	#----------------------------------------------------------------------
	# Check angles in ARC to ensure proper values
	#----------------------------------------------------------------------
	def _correct(self):
		if self.type == CW:	# Inverted: end < start
			if self.startPhi <= self.endPhi: self.startPhi += PI2
		elif self.type == CCW:	# Normal: start < end
			if self.endPhi <= self.startPhi: self.endPhi += PI2
		self._correctEnd()

	#----------------------------------------------------------------------
	def _correctEnd(self):
		# correct exit point to be numerically correct
		self.end[0] = self.center[0] + self.radius*cos(self.endPhi)
		self.end[1] = self.center[1] + self.radius*sin(self.endPhi)
		self.AB = self.end-self.start

	#----------------------------------------------------------------------
	# Invert segment
	#----------------------------------------------------------------------
	def invert(self):
		self.start, self.end = self.end, self.start
		self.AB = -self.AB
		if self.type != LINE:
			if self.type == CW:
				self.type = CCW
			elif self.type == CCW:
				self.type = CW
			self.startPhi, self.endPhi = self.endPhi, self.startPhi
			self._correct()
			self.calcBBox()

	#----------------------------------------------------------------------
	def calcBBox(self):
		if self.type == LINE:
			self.minx = min(self.start[0], self.end[0]) - EPS
			self.maxx = max(self.start[0], self.end[0]) + EPS
			self.miny = min(self.start[1], self.end[1]) - EPS
			self.maxy = max(self.start[1], self.end[1]) + EPS
		else:
			# FIXME very bad
			self.minx = self.center[0] - self.radius - EPS
			self.maxx = self.center[0] + self.radius + EPS
			self.miny = self.center[1] - self.radius - EPS
			self.maxy = self.center[1] + self.radius + EPS

	#----------------------------------------------------------------------
	def __repr__(self):
		if self.cross:
			c = "x"
		else:
			c = ""
		if self.type == LINE:
			return "%s %s %s%s"%(_TYPES[self.type-1], self.start, self.end, c)
		else:
			return "%s %s %s%s %s %g [%g..%g]"%(_TYPES[self.type-1], \
				self.start, self.end, c, \
				self.center, self.radius, \
				degrees(self.startPhi), \
				degrees(self.endPhi))

	#----------------------------------------------------------------------
	# return segment length
	#----------------------------------------------------------------------
	def length(self):
		if self.type == LINE:
			return self.AB.length()
		else:
			if self.type == CW:
				phi = self.startPhi - self.endPhi

			elif self.type == CCW:
				phi = self.endPhi - self.startPhi

			if phi < 0.0: phi += PI2
			return self.radius * phi

	#----------------------------------------------------------------------
	# Orthogonal vector at start
	#----------------------------------------------------------------------
	def orthogonalStart(self):
		if self.type == LINE:
			O = self.AB.orthogonal()
			O.norm()
			return O
		else:
			O = self.start - self.center
			O.norm()
			if self.type == CCW:
				return -O
			else:
				return O

	#----------------------------------------------------------------------
	# Orthogonal vector at end
	#----------------------------------------------------------------------
	def orthogonalEnd(self):
		if self.type == LINE:
			O = self.AB.orthogonal()
			O.norm()
			return O
		else:
			O = self.end - self.center
			O.norm()
			if self.type == CCW:
				return -O
			else:
				return O

	#----------------------------------------------------------------------
	# Check if point P is on segment
	# WARNING: this is not a robust test is used for the intersect
	#----------------------------------------------------------------------
	def _insideArc(self, P):
		phi = atan2(P[1]-self.center[1], P[0]-self.center[0])
		if self.type==CW:
			if phi < self.endPhi-EPS/self.radius: phi += PI2
			if phi <= self.startPhi + EPS/self.radius:
				return True
		elif self.type==CCW:
			if phi < self.startPhi-EPS/self.radius: phi += PI2
			if phi <= self.endPhi + EPS/self.radius:
				return True

		if eq2(self.start,P,EPS0) or eq2(self.end,P,EPS0):
			return True

		return False

	#----------------------------------------------------------------------
	# Return if P is inside the segment
	#----------------------------------------------------------------------
	def inside(self, P):
		if self.type == LINE:
			if P[0] <= self.minx or P[0] >= self.maxx: return False
			if P[1] <= self.miny or P[1] >= self.maxy: return False
			return True
		else:
			return self._insideArc(P)

	#----------------------------------------------------------------------
	# Intersect a line segment with an arc
	#----------------------------------------------------------------------
	def _intersectLineArc(self, arc):
		#AB = self.B
		#a  = AB.length2()
		a = self.AB[0]**2 + self.AB[1]**2
		if a<EPS2: return None,None

		#CA = self.start-arc.center
		#b  = 2.0*AB*CA
		#c  = CA.length2() - arc.radius**2
		CAx = self.start[0] - arc.center[0]
		CAy = self.start[1] - arc.center[1]
		b = 2.0*(self.AB[0]*CAx + self.AB[1]*CAy)
		c  = CAx**2 + CAy**2 - arc.radius**2

		t1,t2 = quadratic(b/a,c/a)
		if t1 is None: return None,None
		if t1<-EPS or t1>1.0+EPS:
			P1 = None
		elif t1<=EPS:
			P1 = Vector(self.start)
		elif t1>=1.0-EPS:
			P1 = Vector(self.end)
		else:
			#P1 = AB*t1 + self.start
			P1 = Vector(self.AB[0]*t1+self.start[0], self.AB[1]*t1+self.start[1])
		if P1 and not arc._insideArc(P1): P1 = None

		if t2<-EPS or t2>1.0+EPS:
			P2 = None
		elif t2<=EPS:
			P2 = Vector(self.start)
		elif t2>=1.0-EPS:
			P2 = Vector(self.end)
		else:
			#P2 = AB*t2 + self.start
			P2 = Vector(self.AB[0]*t2+self.start[0], self.AB[1]*t2+self.start[1])
		if P2 and not arc._insideArc(P2): P2 = None
		return P1,P2

	#----------------------------------------------------------------------
	# Intersect with another segment
	# returns two points
	#----------------------------------------------------------------------
	def intersect(self, other):
		# intersect their bounding boxes
		if max(self.minx,other.minx) > min(self.maxx,other.maxx): return None,None
		if max(self.miny,other.miny) > min(self.maxy,other.maxy): return None,None

		if self.type==LINE and other.type==LINE:
			# check for intersection
			DD = -self.AB[0]*other.AB[1] + self.AB[1]*other.AB[0]
			#print DD
			if abs(DD)<EPS2: return None,None

			Dt = -(other.start[0]-self.start[0])*other.AB[1] + \
			      (other.start[1]-self.start[1])*other.AB[0]
			t = Dt/DD
			#print t
			P = self.AB*t + self.start
			#print P
			if self.minx<=P[0]<=self.maxx and other.minx<=P[0]<=other.maxx and \
			   self.miny<=P[1]<=self.maxy and other.miny<=P[1]<=other.maxy:
				return P,None
			return None,None

		elif self.type==LINE and other.type!=LINE:
			return self._intersectLineArc(other)

		elif self.type!=LINE and other.type==LINE:
			return other._intersectLineArc(self)

		elif self.type!=LINE and other.type!=LINE:
			# Circle circle intersection
			CC = other.center - self.center
			d = CC.norm()
			if d<=EPS2 or d>=self.radius+other.radius: return None,None
			x = (self.radius**2 - other.radius**2 + d**2) / (2.*d)
			diff = (self.radius-x)*(self.radius+x)
			if diff<0.0: return None,None
			y = sqrt(diff)

			O = CC.orthogonal()

			P1 = self.center + x*CC + y*O
			if not self._insideArc(P1) or not other._insideArc(P1):
				P1 = None

			P2 = self.center + x*CC - y*O
			if not self._insideArc(P2) or not other._insideArc(P2):
				P2 = None

			return P1, P2

	#----------------------------------------------------------------------
	# Return minimum distance of P from segment
	#----------------------------------------------------------------------
	def distance(self, P):
		if self.type == LINE:
			AB2  = self.AB[0]**2 + self.AB[1]**2
			APx  = P[0]-self.start[0]
			APy  = P[1]-self.start[1]
			dot  = APx*self.AB[0] + APy*self.AB[1]
			proj = dot / AB2
			if proj < 0.0:
				return sqrt(APx**2+APy**2)
			elif proj > 1.0:
				return sqrt((P[0]-self.end[0])**2 + (P[1]-self.end[1])**2)
			else:
				d = (APx**2+APy**2) - dot*proj
				if abs(d)<EPS: return 0.0
				return sqrt(d)

		elif self.type == CW:
			PCx = P[0] - self.center[0]
			PCy = P[1] - self.center[1]
			phi = atan2(PCy, PCx)
			if phi < self.endPhi-EPS/self.radius: phi += PI2
			if phi > self.startPhi+EPS/self.radius:
				return sqrt((P[0]-self.start[0])**2 + (P[1]-self.start[1])**2)
			else:
				return abs(sqrt(PCx**2+PCy**2) - self.radius)

		elif self.type == CCW:
			PCx = P[0] - self.center[0]
			PCy = P[1] - self.center[1]
			phi = atan2(PCy, PCx)
			if phi < self.startPhi-EPS/self.radius: phi += PI2
			if phi > self.endPhi+EPS/self.radius:
				return sqrt((P[0]-self.end[0])**2 + (P[1]-self.end[1])**2)
			else:
				return abs(sqrt(PCx**2+PCy**2) - self.radius)

	#----------------------------------------------------------------------
	# Split segment at point P and return second part
	#----------------------------------------------------------------------
	def split(self, P):
		if eq2(P,self.start,EPS0):
			# XXX should flag previous segment as cross
			return -1

		elif eq2(P,self.end,EPS0):
			self.cross = True
			return 0

		new = Segment(self.type, P, self.end)
		new.cross  = self.cross
		self.cross = False
		self.end   = P
		self.AB    = self.end - self.start
		self.calcBBox()
		if self.type>LINE:
			new.setCenter(self.center) #, self.radius, None, self.endPhi)
			self.setCenter(self.center) #, self.radius, self.startPhi, new.startPhi)
		return new

#==============================================================================
# Path: a list of joint segments
# Closed path?
# Path length
# reverse
# ignore zero length segments
#==============================================================================
class Path(list):
	def __init__(self, name):
		self.name    = name
		self._length = None

	#----------------------------------------------------------------------
	def __repr__(self):
		return "%s:\n\t%s"%(self.name, "\n\t".join(["%3d: %s"%(i,x) for i,x in enumerate(self)]))

	#----------------------------------------------------------------------
	# @return true if path is closed
	#----------------------------------------------------------------------
	def isClosed(self):
		return self and eq(self[0].start, self[-1].end)

	#----------------------------------------------------------------------
	# Close path by connecting the with a line segment
	#----------------------------------------------------------------------
	def close(self):
		self._length = None
		self.append(Segment(LINE, self[-1].end, self[0].start))

	#----------------------------------------------------------------------
	# Join path at the end
	#----------------------------------------------------------------------
	def join(self, path):
		self._length = None
		self.append(Segment(LINE, self[-1].end, path[0].start))
		self.extend(path)

	#----------------------------------------------------------------------
	# @return total length of path
	#----------------------------------------------------------------------
	def length(self):
		if self._length is not None: return self._length
		self._length = 0.0
		for segment in self:
			self._length += segment.length()
		return self._length

	#----------------------------------------------------------------------
	# Find minimum distance of point P wrt to the path
	#----------------------------------------------------------------------
	def distance(self, P):
		return min([x.distance(P) for x in self])

	#----------------------------------------------------------------------
	# Return:
	#	-1 for CCW closed path
	#        0 for open path
	#	 1 for CW  closed path
	#----------------------------------------------------------------------
	def direction(self):
		if not self.isClosed(): return 0
		phi = 0.0
		P  = self[-1].AB
		PL = P.length()
		for i,N in enumerate(self):
			NL = N.AB.length()
			prod = PL * NL
			if abs(prod)>EPS0:
				cross = (P ^ N.AB) / prod
				if   cross <= -0.9999999999:
					phi -= pi/2.0
				elif cross >=  0.9999999999:
					phi += pi/2.0
				else:
					# WARNING Don't use the angle from the asin(cross)
					# since it can fail when ang > 90deg then it will return
					# the ang-90deg
					#phi += asin(cross)
					dot = (N.AB * P) / prod
					if   dot<-1.0: dot=-1.0
					elif dot> 1.0: dot= 1.0
					phi += copysign(acos(dot), cross)
			else:
				if N.type == CW:
					phi -= PI2
				elif N.type == CCW:
					phi += PI2
			P  = N.AB
			PL = NL
		if phi < 0: return 1
		return -1

	#----------------------------------------------------------------------
	# Invert the whole path
	#----------------------------------------------------------------------
	def invert(self):
		new = []
		for segment in reversed(self):
			segment.invert()
			new.append(segment)
		del self[:]
		self.extend(new)
	reverse = invert

	#----------------------------------------------------------------------
	# Split path into contours
	#----------------------------------------------------------------------
	def split2contours(self):
		if len(self)==0: return []

		path = Path(self.name)
		paths = [path]

		# Push first element as start point
		path.append(self.pop(0))

		# Repeat until all segments are used
		while self:
			# End point
			end = path[-1].end

			# Find the segment that starts after the last one
			for i,segment in enumerate(self):
				# Try starting point
				if eq(end, segment.start):
					path.append(segment)
					del self[i]
					break

				# Try ending point (inverse)
				if eq(end, segment.end):
					segment.invert()
					path.append(segment)
					del self[i]
					break

			else:
				# Start point
				start = path[0].start

				# Find the segment that starts after the last one
				for i,segment in enumerate(self):
					# Try starting point
					if eq(start, segment.start):
						segment.invert()
						path.insert(0,segment)
						del self[i]
						break

					# Try ending point (inverse)
					if eq(start, segment.end):
						path.insert(0,segment)
						del self[i]
						break
				else:
					# Not found push a path start point and
					path = Path(self.name)
					paths.append(path)
					path.append(self.pop(0))

		# Correct ending points of the contours
#		for path in paths:
#			closed = path.isClosed()
#			end = path[0].end
#			for segment in path[1:]:
#				segment.start = Vector(end)	# force points to be the same
#				if segment.type != LINE:
#					segment._correctEnd()
#				end = segment.end
#			if closed:
#				path[0].start = end

		return paths

	#----------------------------------------------------------------------
	# Return path with offset
	#----------------------------------------------------------------------
	def offset(self, offset, name=None):
		start = time.time()
		if name is None: name = self.name
		path = Path(name)

		if self.isClosed():
			prev = self[-1]
			Op = prev.orthogonalEnd()
			Eo = prev.end + Op*offset
		else:
			prev = None
			Op   = None	# previous orthogonal
			Eo   = None
		for segment in self:
			O  = segment.orthogonalStart()
			So = segment.start + O*offset
			# Join with the previous edge
			if Eo is not None and eq(Eo,So):
				# possibly a full circle
				if segment.type != LINE and len(self)==1:
					path.append(Segment(segment.type, Eo, So, segment.center))

			elif Op is not None:
				# if cross*offset
				cross = O[0]*Op[1]-O[1]*Op[0]
				if (prev.type!=LINE and segment.type!=LINE) or \
				   (abs(cross)>EPS and cross*offset > 0):
					# either a circle
					t = offset>0 and CW or CCW
					path.append(Segment(t, Eo, So, segment.start))
				else:
					# or a straight line if inside
					path.append(Segment(LINE, Eo, So))

			# connect with previous point
			O  = segment.orthogonalEnd()
			Eo = segment.end + O*offset
			if (So-Eo).length2() > EPS:
				if segment.type == LINE:
					path.append(Segment(LINE, So, Eo))
				else:
					# FIXME check for radius + offset > 0.0
					path.append(Segment(segment.type, So, Eo, segment.center))
			Op = O
			prev = segment
		#sys.stdout.write("# path.offset: %g\n"%(time.time()-start))
		return path

	#----------------------------------------------------------------------
	# intersect path with self and mark all intersections
	#----------------------------------------------------------------------
	def intersectSelf(self):
		start = time.time()
		i = 0
		while i<len(self)-2:
			j = i+2
			while j<len(self):
				P1,P2 = self[i].intersect(self[j])
				#if P1 is not None or P2 is not None:
				#	print i,j,"P1=",P1,"P2=",P2
				#if i==2 and j==4:
				#	import pdb; pdb.set_trace()
				#	P1,P2 = self[i].intersect(self[j])

				# skip doublet solution
				if P1 is not None and P2 is not None and eq2(P1,P2,EPS0):
					P2 = None

				if P1 is not None:
					# Split the higher segment
					split = self[j].split(P1)
					if isinstance(split,int):
						self[j+split].cross = True
					else:
						self.insert(j+1,split)
						self[j].cross = True
						j += 1

					# Split the lower segment
					split = self[i].split(P1)
					if isinstance(split,int):
						isp = i+split
						if isp<0: isp = len(self)-1
						self[isp].cross = True
					else:
						self.insert(i+1,split)
						self[i].cross = True

				# Check the two high segments where P2 can go
				if P2 is not None:
					if self[j].inside(P2):
						split = self[j].split(P2)
						if isinstance(split,int):
							self[j+split].cross = True
						else:
							self.insert(j+1, split)
							self[j].cross = True
							j += 1
					else:
						split = self[j+1].split(P2)
						if isinstance(split,int):
							self[j+1+split].cross = True
						else:
							self.insert(j+2, split)
							self[j+1].cross = True
							j += 1

					if self[i].inside(P2):
						split = self[i].split(P2)
						if isinstance(split,int):
							isp = i+split
							if isp<0: isp = len(self)-1
							self[isp].cross = True
						else:
							self.insert(i+1, split)
							self[i].cross = True
					else:
						split = self[i+1].split(P2)
						if isinstance(split,int):
							self[i+1+split].cross = True
						else:
							self.insert(i+2, split)
							self[i+1].cross = True
				#if P1 or P2: print ">>>",self
				# move to next segment
				j += 1
			# move to next step
			i += 1
		#sys.stdout.write("# path.intersect: %g\n"%(time.time()-start))

	#----------------------------------------------------------------------
	# remove the excluded segments from an intersect path
	# @param include defines the first segment if it is to be included or not
	#----------------------------------------------------------------------
	def removeExcluded(self, path, offset):
		start = time.time()
		chkofs = abs(offset)*(1.0-EPS)
		include = path.distance(self[0].start) >= chkofs
		i = 0
		while i < len(self):
			segment = self[i]

			if not include:
#				print "remove", self[i]
				del self[i]
				i -= 1

			if segment.cross:	# crossing point
				include = not include
				if include:
					include = path.distance(segment.end) > chkofs
#					print "+++",i, segment.end, path.distance(segment.end), chkofs, include
			i += 1
		self.removeZeroLength()
		#sys.stdout.write("# path.removeExcluded: %g\n"%(time.time()-start))

	#----------------------------------------------------------------------
	# Perform overcut movements on corners, moving at half angle by
	# a certain distance
	#----------------------------------------------------------------------
	def overcut(self, offset):
		if self.isClosed():
			prev = self[-1]
			Op = prev.orthogonalEnd()
		else:
			prev = None
			Op   = None	# previous orthogonal
		i = 0
		while i<len(self):
			segment = self[i]
			O  = segment.orthogonalStart()
			if Op is not None:
				cross = O[0]*Op[1]-O[1]*Op[0]
				if prev.type==LINE and segment.type==LINE and cross*offset < -EPS:
					# find direction
					D = O+Op
					D.normalize()
					if offset>0.0: D = -D

					costheta = O*Op
					costheta2 = sqrt((1.0+costheta)/2.0)
					distance = abs(offset)*(1.0/costheta2-1.0)
					D *= distance

					self.insert(i,Segment(LINE, segment.start, segment.start + D))
					self.insert(i+1, Segment(LINE, segment.start+D, segment.start))
					i += 2
			prev = segment
			Op = prev.orthogonalEnd()
			i += 1

	#----------------------------------------------------------------------
	# @return index of segment that starts with point P
	# else return None
	#----------------------------------------------------------------------
	def hasPoint(self, P):
		for i,segment in enumerate(self):
			if eq(segment.start,P):
				return i
		return None

	#----------------------------------------------------------------------
	# push back cycle/rotate 0..idx segments to the end
	#----------------------------------------------------------------------
	def moveBack(self, idx):
		self.extend(self[:idx])
		del self[:idx]

	#----------------------------------------------------------------------
	# merge loops
	#----------------------------------------------------------------------
	def mergeLoops(self, loops):
		i = 0
		merged = False
		while i < len(loops):
			loop = loops[i]
			if not loop.isClosed():
				i += 1
				continue
			# find if they share a common point
			for j,segment in enumerate(self):
				k = loop.hasPoint(segment.start)
				if k is not None:
					if k>0: loop.moveBack(k)
					self[j:j] = loop
					merged = True
					del loops[i]
					break
			else:
				i += 1
		return merged

	#----------------------------------------------------------------------
	# Remove zero length segments
	# Replace small arcs with lines
	#----------------------------------------------------------------------
	def removeZeroLength(self):
		i = 0
		#ndel = 0
		#nline = 0
		#minlength = 1000.0
		#minsagitta = 1000.0
		while i<len(self):
			#minlength = min(minlength, self[i].length())
			if self[i].length() < EPS:
				del self[i]
				#ndel += 1
				continue

			if self[i].type == CCW:
				df = self[i].endPhi - self[i].startPhi
			elif self[i].type == CW:
				df = self[i].startPhi - self[i].endPhi

			if self[i].type != LINE:
				if df<pi/2.0:
					sagitta = self[i].radius * (1.0 - cos(df/2.0))
					#minsagitta = min(minsagitta, sagitta)
					if sagitta < EPS*10:
						#nline += 1
						self[i].type = LINE

			i += 1

	#----------------------------------------------------------------------
	# Convert a dxf layer to a list of segments
	#----------------------------------------------------------------------
	def fromDxfLayer(self, layer):
		for entity in layer:
			start = entity.start()
			end   = entity.end()
			if entity.type == "LINE":
				if not eq(start,end):
					self.append(Segment(LINE, start, end))

			elif entity.type == "CIRCLE":
				center = entity.center()
				self.append(Segment(CCW, start, end, center))

			elif entity.type == "ARC":
				t = entity._invert and CW or CCW
				center = entity.center()
				self.append(Segment(t, start, end, center))

			elif entity.type == "LWPOLYLINE":
				# split it into multiple line segments
				xy = list(zip(entity[10], entity[20]))
				bulge = entity.bulge()
				if not isinstance(bulge,list): bulge = [bulge]*len(xy)
				if entity._invert:
					xy.reverse()
					# reverse and negate bulge
					bulge = [-x for x in bulge[::-1]]

				for i,(x,y) in enumerate(xy[1:]):
					b = bulge[i]
					end = Vector(x,y)
					if eq(start,end): continue
					if abs(b)<EPS0:
						self.append(Segment(LINE, start, end))
					else:
						# arc with bulge = b
						# b = tan(theta/4)
						theta = 4.0*atan(abs(b))
						AB = start-end
						ABlen = AB.length()
						d = ABlen / 2.0
						r = d / sin(theta/2.0)
						C = (start+end)/2.0
						try:
							OC = sqrt((r-d)*(r+d))
							if b<0.0:
								t  = CW
							else:
								t  = CCW
								OC = -OC
							center = Vector(C[0] - OC*AB[1]/ABlen,
									C[1] + OC*AB[0]/ABlen)
							self.append(Segment(t, start, end, center))
						except:
							self.append(Segment(LINE, start, end))
					start = end
