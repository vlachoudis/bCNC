#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
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

import math
from bmath import Vector, quadratic

EPS  = 0.0001
EPS2 = EPS**2

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
		      (abs(A[1])+abs(B[1]))**2) + EPS2
	return d2<err

#==============================================================================
# Segment
#==============================================================================
class Segment:
	def __init__(self, t, s, e, c=None, r=None, sPhi=None, ePhi=None):
		self.type  = t
		self.start = s
		self.end   = e
		self.cross = False	# end point is a path cross point
		if self.type>LINE and c is not None:
			self.setArc(c, r, sPhi, ePhi)

	#----------------------------------------------------------------------
	def setArc(self, c=None, r=None, sPhi=None, ePhi=None):
		self.center = c
		if r is not None:
			self.radius = r
		else:
			#self.radius = 0.5*((self.start-self.center).length() + \
			#		   (self.end-self.center).length())
			self.radius = (self.start-self.center).length()
		if sPhi is not None:
			self.startPhi = sPhi
		else:
			self.startPhi = math.atan2(self.start[1]-c[1], self.start[0]-c[0])
		if sPhi is not None:
			self.endPhi = ePhi
		else:
			self.endPhi = math.atan2(self.end[1]-c[1], self.end[0]-c[0])

	#----------------------------------------------------------------------
	def __repr__(self):
		if self.cross:
			c = "x"
		else:
			c = ""
		if self.type == LINE:
			return "%s %s %s%s"%(_TYPES[self.type-1], self.start, self.end, c)
		else:
			return "%s %s %s%s %s %g [%g..%g]"%(_TYPES[self.type-1], self.start, self.end, c, \
						self.center, self.radius, math.degrees(self.startPhi), math.degrees(self.endPhi))

	#----------------------------------------------------------------------
	# Direction vector at start
	#----------------------------------------------------------------------
#	def direction(self):
#		if self.type == LINE:
#			D = self.end - self.start
#			D.norm()
#			return D

		#elif self.type == CW:

	#----------------------------------------------------------------------
	# Orthogonal vector at start
	#----------------------------------------------------------------------
	def orthogonalStart(self):
		if self.type == LINE:
			D = self.end - self.start
			O = D.orthogonal()
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
			D = self.end - self.start
			O = D.orthogonal()
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
	# Invert segment
	#----------------------------------------------------------------------
	def invert(self):
		self.start, self.end = self.end, self.start
		if self.type == CCW:
			self.type = CW
			self.startPhi, self.endPhi = self.endPhi, self.startPhi
		elif self.type == CW:
			self.type = CCW
			self.startPhi, self.endPhi = self.endPhi, self.startPhi

	#----------------------------------------------------------------------
	# Check if point P is on segment
	# WARNING: this is not a robust test is used for the intersect
	#----------------------------------------------------------------------
	def _insideArc(self, P):
		PC = P - self.center
		phi = math.atan2(PC[1], PC[0])
		if self.type==CW:
			if phi >= self.startPhi-EPS or phi <= self.endPhi+EPS:
				return False
		elif self.type==CCW:
			if phi <= self.startPhi+EPS or phi >= self.endPhi-EPS:
				return False
		return True

	#----------------------------------------------------------------------
	# Return if P is inside the segment
	#----------------------------------------------------------------------
	def inside(self, P):
		if self.type == LINE:
			minx = min(self.start[0],self.end[0])-EPS
			maxx = max(self.start[0],self.end[0])+EPS
			if P[0] <= minx or P[0] >= maxx: return False

			miny = min(self.start[1],self.end[1])-EPS
			maxy = max(self.start[1],self.end[1])+EPS
			if P[1] <= miny or P[1] >= maxy: return False
			return True
		else:
			return self._insideArc(P)

	#----------------------------------------------------------------------
	# Intersect a line segment with an arc
	#----------------------------------------------------------------------
	def _intersectLineArc(self, arc):
		AB = self.end - self.start
		a  = AB.length2()
		if a<EPS2: return None,None
		CA = self.start-arc.center
		b  = 2.0*AB*CA
		c  = CA.length2() - arc.radius**2
		t1,t2 = quadratic(b/a,c/a)
		if t1 is None: return None,None
		if t1<=EPS or t1>=1.0-EPS:
			P1 = None
		else:
			P1 = AB*t1 + self.start
			if not arc._insideArc(P1):
				P1 = None

		if t2<=EPS or t2>=1.0-EPS:
			P2 = None
		else:
			P2 = AB*t2 + self.start
			if not arc._insideArc(P2):
				P2 = None
		return P1,P2

	#----------------------------------------------------------------------
	# Intersect with another segment
	# returns two points
	#----------------------------------------------------------------------
	def intersect(self, other):
		if self.type==LINE and other.type==LINE:
			# intersect their bounding boxes
			# first on X
			min1x = min(self.start[0], self.end[0]) - EPS
			max1x = max(self.start[0], self.end[0]) + EPS
			min2x = min(other.start[0], other.end[0]) - EPS
			max2x = max(other.start[0], other.end[0]) + EPS
			if max(min1x,min2x) > min(max1x,max2x): return None,None

			# then on Y
			min1y = min(self.start[1], self.end[1]) - EPS
			max1y = max(self.start[1], self.end[1]) + EPS
			min2y = min(other.start[1], other.end[1]) - EPS
			max2y = max(other.start[1], other.end[1]) + EPS
			if max(min1y,min2y) > min(max1y,max2y): return None,None

			# check for intersection
			AB = self.end  - self.start
			CD = other.end - other.start

			DD = -AB[0]*CD[1] + AB[1]*CD[0]
			#print DD
			if abs(DD)<EPS2: return None,None

			AC = other.start - self.start
			Dt = -AC[0]*CD[1] + AC[1]*CD[0]
			t = Dt/DD
			#print t
			P = AB*t + self.start
			#print P
			if min1x<=P[0]<=max1x and min2x<=P[0]<=max2x and \
			   min1y<=P[1]<=max1y and min2y<=P[1]<=max2y and \
			   (self.start-P).length2()  > EPS and \
			   (self.end-P).length2()    > EPS and \
			   (other.start-P).length2() > EPS and \
			   (other.end-P).length2()   > EPS:
				return P,None
			return None,None

		elif self.type==LINE and other.type!=LINE:
			return self._intersectLineArc(other)

		elif self.type!=LINE and other.type==LINE:
			return other._intersectLineArc(self)

		elif self.type!=LINE and other.type!=LINE:
			# Circle circle intersection
			AB = other.center - self.center
			d = AB.norm()
			if d<=EPS2 or d>=self.radius+other.radius: return None,None
			x = (self.radius**2 - other.radius**2 + d**2) / (2.*d)
			y = math.sqrt(self.radius**2 - x**2)

			O = AB.orthogonal()

			P1 = self.center + x*AB + y*O
			if not self._insideArc(P1) or not other._insideArc(P1):
				P1 = None

			P2 = self.center + x*AB - y*O
			if not self._insideArc(P2) or not other._insideArc(P2):
				P2 = None

			return P1, P2

	#----------------------------------------------------------------------
	# Return minimum distance of P from segment
	#----------------------------------------------------------------------
	def distance(self, P):
		if self.type == LINE:
			AB  = self.end - self.start
			AB2 = AB.length2()
			AP  = P-self.start
			dot = AP*(self.end-self.start)
			proj = dot / AB2
			if proj < 0.0:
				return AP.length()
			elif proj > 1.0:
				return (P-self.end).length()
			else:
				d = AP.length2() - dot*dot/AB2
				if abs(d)<EPS: return 0.0
				return math.sqrt(d)

		elif self.type == CW:
			PC = P - self.center
			phi = math.atan2(PC[1], PC[0])
			if phi > self.startPhi:
				return (P-self.start).length()
			elif phi < self.endPhi:
				return (P-self.end).length()
			else:
				return abs(PC.length() - self.radius)

		elif self.type == CCW:
			PC = P - self.center
			phi = math.atan2(PC[1], PC[0])
			if phi < self.startPhi:
				return (P-self.start).length()
			elif phi > self.endPhi:
				return (P-self.end).length()
			else:
				return abs(PC.length() - self.radius)

	#----------------------------------------------------------------------
	# Split segment at point P and return second part
	#----------------------------------------------------------------------
	def split(self, P):
		new = Segment(self.type, P, self.end)
		new.cross  = self.cross
		self.cross = False 
		self.end   = P
		if self.type>LINE:
			new.setArc(self.center, self.radius, None, self.endPhi)
			self.setArc(self.center, self.radius, self.startPhi, new.startPhi)
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
		return "%s: %s"%(self.name, "\n\t".join(["%3d: %s"%(i,x) for i,x in enumerate(self)]))

	#----------------------------------------------------------------------
	# @return true if path is closed
	#----------------------------------------------------------------------
	def isClosed(self):
		return self and eq(self[0].start, self[-1].end)

	#----------------------------------------------------------------------
	# Find minimum distance of point P wrt to the path
	#----------------------------------------------------------------------
	def distance(self, P):
		mindist = 1e10
		for segment in self:
			mindist = min(mindist, segment.distance(P))
		return mindist

	#----------------------------------------------------------------------
	# Split path into order segments
	#----------------------------------------------------------------------
	def order(self):
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
				# Not found push a path start point and
				path = Path(self.name)
				paths.append(path)
				path.append(self.pop(0))
		return paths

	#----------------------------------------------------------------------
	# Return path with offset
	#----------------------------------------------------------------------
	def offset(self, offset):
		path = Path("%s[%g]"%(self.name,offset))

		if self.isClosed():
			Op = self[-1].orthogonalEnd()
			Eo = self[-1].end + Op*offset
		else:
			Op = None	# previous orthogonal
		for segment in self:
			O  = segment.orthogonalStart()
			So = segment.start + O*offset
			if Op is not None and not eq(Eo,So):
				# if cross*offset
				cross = O[0]*Op[1]-O[1]*Op[0]
				if abs(cross)>EPS and cross*offset > 0:
					t = offset>0 and CW or CCW
					path.append(Segment(t, Eo, So, segment.start))
				else:
					path.append(Segment(LINE, Eo, So))

			# connect with previous point
			O  = segment.orthogonalEnd()
			Eo = segment.end + O*offset
			if segment.type == LINE:
				path.append(Segment(LINE, So, Eo))
			else:
				# FIXME check for radius + offset > 0.0
				path.append(Segment(segment.type, So, Eo, segment.center))
			Op = O
		return path

	#----------------------------------------------------------------------
	# intersect path with self and mark all intersections
	#----------------------------------------------------------------------
	def intersect(self):
		i = 1
		while i<len(self)-2:
			j = i+2
			while j<len(self):
				#if i==17 and j==19:
				#	print self[i]
				#	print self[j]
				#	import pdb; pdb.set_trace()
				P1,P2 = self[i].intersect(self[j])
#				if P1:
#					if self[j].distance(P1)>EPS or \
#					   self[i].distance(P1)>EPS:
#						import pdb; pdb.set_trace()
#				if P2:
#					if self[j].distance(P2)>EPS or \
#					   self[i].distance(P2)>EPS:
#						import pdb; pdb.set_trace()

				if P1 is not None:
					# Split the higher segment
					self.insert(j+1,self[j].split(P1))
					self[j].cross = True

					# Split the lower segment
					self.insert(i+1,self[i].split(P1))
					self[i].cross = True
					j += 1

					# skip doublet solution
					if P2 and (P2-P1).length2()<EPS: P2 = None

				# Check the two high segments where P2 can go
				if P2 is not None:
					if self[j].inside(P2):
						self.insert(j+1, self[j].split(P2))
						self[j].cross = True
					else:
						self.insert(j+2, self[j+1].split(P2))
						self[j+1].cross = True
					j += 1

					if self[i].inside(P2):
						self.insert(i+1, self[i].split(P2))
						self[i].cross = True
					else:
						self.insert(i+2, self[i+1].split(P2))
						self[i+1].cross = True
				# move to next segment
				j += 1
			# move to next step
			i += 1

	#----------------------------------------------------------------------
	# remove the excluded segments from an intersect path
	# @param include defines the first segment if it is to be included or not
	#----------------------------------------------------------------------
	def removeExcluded(self, include):
		i = 0
		while i < len(self):
			segment = self[i]
			if not include:
				del self[i]
				i -= 1
			if segment.cross:	# crossing point
				include = not include
			i += 1

	#----------------------------------------------------------------------
	# Convert a dxf layer to a list of segments
	#----------------------------------------------------------------------
	def fromLayer(self, layer):
		for entity in layer:
			start = entity.start()
			end   = entity.end()
			if entity.type == "LINE":
				if not eq(start,end):
					self.append(Segment(LINE, start, end))

			elif entity.type == "CIRCLE":
				center = entity.center()
				r  = entity.radius()
				self.append(Segment(CCW, start, end, center, r, 0.0, 2.0*math.pi))

			elif entity.type == "ARC":
				t = entity._invert and CW or CCW
				center = entity.center()
				r    = entity.radius()
				sPhi = math.radians(entity.startPhi())
				ePhi = math.radians(entity.endPhi())
				self.append(Segment(t, start, end, center, r, sPhi, ePhi))

			elif entity.type == "LWPOLYLINE":
				# split it into multiple line segments
				xy = zip(entity[10], entity[20])
				if entity._invert: reverse(xy)
				for x,y in xy[1:]:
					end = Vector(x,y)
					if not eq(start,end):
						self.append(Segment(LINE, start, end))
						start = end

