# -*- coding: utf-8 -*-
#
# Copyright European Organization for Nuclear Research (CERN)
# All rights reserved
#
# Author: Vasilis.Vlachoudis@cern.ch
# Contributor: @harvie Tomas Mudrunka (2018)
# Date:   10-Mar-2015

from __future__ import print_function
from __future__ import absolute_import
__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

from operator import itemgetter
from math import atan, atan2, cos, acos, degrees, pi, sin, sqrt, floor, ceil
from bmath import Vector, quadratic

EPS   = 1E-7		# strict tolerances for operations
EPS2  = EPS**2
EPSV  = EPS*10		# relaxed tolerances for vectors
EPSV2 = EPSV**2
PI2   = 2.0*pi


#------------------------------------------------------------------------------
# Compare two Vectors if they are the same
#------------------------------------------------------------------------------
def eq(A,B,acc=EPS):
	d2  = (A[0]-B[0])**2 + (A[1]-B[1])**2
	err = acc*acc * ((abs(A[0])+abs(B[0]))**2 + \
		       (abs(A[1])+abs(B[1]))**2 + 1.0)
	return d2<err


#==============================================================================
# Segment
#==============================================================================
class Segment:
	LINE = 1
	CW   = 2
	CCW  = 3
	_TYPES = ["LINE", "CW  ","CCW "]

	#----------------------------------------------------------------------
	def __init__(self, t, s, e, c=None): #, r=None): #, sPhi=None, ePhi=None):
		self.type = t
		self.A    = s
		self.B    = e
		self.AB   = self.B-self.A	# vector from start to end
		self._cross  = False		# end point is a path crossing point
		self._inside = []		# auxiliary variable for tab and island operations
		if self.type==Segment.LINE:
			self.calcBBox()
		elif c is not None:
			self.setCenter(c)

	#----------------------------------------------------------------------
	def setStart(self, s):
		self.A  = s
		self.AB = self.B-self.A
		if self.type==Segment.LINE:
			self.calcBBox()
		else:
			self.correct()

	#----------------------------------------------------------------------
	def setEnd(self, e):
		self.B  = e
		self.AB = self.B-self.A
		if self.type==Segment.LINE:
			self.calcBBox()
		else:
			self.correct()

	#----------------------------------------------------------------------
	def setCenter(self, c):
		self.C = c
		self.correct()

	#----------------------------------------------------------------------
	# Correct arc so radius, center, start and end point to match
	#----------------------------------------------------------------------
	def correct(self):
		if self.type == Segment.LINE: return #There's no use for this on lines

		if self.AB.length2()>EPS:
			# Correct center by finding the intersection of the
			# orthogonal line from the middle of the start-end segment
			# and the line in the direction start-existing.C

			# First line is   R = M + P*r
			# Mid point
			M = 0.5*(self.A + self.B)
			# perpendicular vector
			P = self.AB.orthogonal()

			# Second line is  R = S + CS*t
			# S=start, C=center
			CS = self.C - self.A

			#    R = S + CS*t = M + P*r
			# =>  CS*t - P*r = M - S = MS
			MS = M - self.A

			# linear system
			#    CSx*t - Px*r = MSx
			#    CSy*t - Py*r = MSy

			#      | CSx  -Px |
			# Dt = |          |
			#      | CSy  -Py |
			D = -CS[0]*P[1] + CS[1]*P[0]
			if abs(D)<EPS2:
				self.change2Line()
				return

			#      | MSx  -Px |
			# Dt = |          |
			#      | MSy  -Py |
			Dt = -MS[0]*P[1] + MS[1]*P[0]

			t = Dt/D

			# C = R(t) = S + CS*t
			#C = self.C
			self.C = self.A + CS*t
			if t < 0.0:
				# change type
				if self.type == Segment.CW:
					self.type = Segment.CCW
				else:
					self.type = Segment.CW
			#if (self.C-C).length()>EPS:
			#	print self
			#	print (self.C-C).length()
			# make a check for both radius
			#r1 = (self.A-self.C).length()
			#r2 = (self.B-self.C).length()
			#if abs(r1-r2)>EPS:
			#	print "ERROR r1=",r1,"r2=",r2
			#	print self

		# -------------------------------------------------------------
		# Check angles in ARC to ensure proper values
		# -------------------------------------------------------------
		self.radius   = (self.A-self.C).length()	# based on starting point
		self.startPhi = atan2(self.A[1]-self.C[1], self.A[0]-self.C[0])
		self.endPhi   = atan2(self.B[1]-self.C[1], self.B[0]-self.C[0])
		if abs(self.startPhi)<EPS: self.startPhi = 0.0
		if abs(self.endPhi)  <EPS: self.endPhi   = 0.0

		if self.type == Segment.CW:
			# CW/Inverted: it must be end < start
			if self.startPhi <= self.endPhi: self.startPhi += PI2
		elif self.type == Segment.CCW:
			# CCW/Normal: it must be start < end
			if self.endPhi <= self.startPhi: self.endPhi += PI2

		self.calcBBox()

	#----------------------------------------------------------------------
	def change2Line(self):
		self.type = Segment.LINE
		self.calcBBox()

	#----------------------------------------------------------------------
	# Invert segment
	#----------------------------------------------------------------------
	def invert(self):
		self.A, self.B = self.B, self.A
		self.AB = -self.AB
		if self.type != Segment.LINE:
			if self.type == Segment.CW:
				self.type = Segment.CCW
			elif self.type == Segment.CCW:
				self.type = Segment.CW
			self.startPhi, self.endPhi = self.endPhi, self.startPhi
			self.correct()

	#----------------------------------------------------------------------
	def calcBBox(self):
		if self.type == Segment.LINE:
			self.minx = min(self.A[0], self.B[0]) - EPSV
			self.maxx = max(self.A[0], self.B[0]) + EPSV
			self.miny = min(self.A[1], self.B[1]) - EPSV
			self.maxy = max(self.A[1], self.B[1]) + EPSV
		else:
			# FIXME very bad
			self.minx = self.C[0] - self.radius - EPSV
			self.maxx = self.C[0] + self.radius + EPSV
			self.miny = self.C[1] - self.radius - EPSV
			self.maxy = self.C[1] + self.radius + EPSV

	#----------------------------------------------------------------------
	def __repr__(self):
		if self._cross:
			c = "x"
		else:
			c = ""
		if self.type == Segment.LINE:
			return "%s %s %s%s L:%g"%(Segment._TYPES[self.type-1],
					repr(self.A), repr(self.B), c, self.length())
		else:
			return "%s %s %s%s C:%s R:%g Phi:[%g..%g] L:%g" % \
				(Segment._TYPES[self.type-1], \
				 repr(self.A), repr(self.B), c, \
				 self.C, self.radius, \
				 degrees(self.startPhi), \
				 degrees(self.endPhi),
				 self.length())

	#----------------------------------------------------------------------
	# Return a point ON the segment (or extrapolated outside of it) at distance traveled from A (or B)
	#----------------------------------------------------------------------
	def extrapolatePoint(self, dist, B=False):
		if self.type == Segment.LINE:
			if not B:
				return self.A+(self.tangentStart()*dist)
			else:
				return self.B+(self.tangentStart()*dist)
		else:
			if self.type == Segment.CW:
				dist = -dist

			raddist = dist/self.radius
			if not B:
				phi = self.startPhi+raddist
			else:
				phi = self.endPhi+raddist
			return Vector(	self.C[0] + self.radius*cos(phi),
					self.C[1] + self.radius*sin(phi))

	#----------------------------------------------------------------------
	# Return a point ON the segment at distance traveled from A to B (or B to A when negative)
	#----------------------------------------------------------------------
	def distPoint(self, dist):
		if dist >= 0:
			return self.extrapolatePoint(dist)
		else:
			return self.extrapolatePoint(abs(dist), True)

	#----------------------------------------------------------------------
	# Return a point ON the segment in the middle (= factor 0.5) or different
	#----------------------------------------------------------------------
	def midPoint(self):
		return self.extrapolatePoint(self.length()/2)

	#----------------------------------------------------------------------
	# Return segment, which naturaly continues this segment
	#----------------------------------------------------------------------
	def suffixSegment(self, dist):
		suffix = Segment(self.type, self.B, self.extrapolatePoint(dist, True))
		if self.type != Segment.LINE:
			suffix.setCenter(self.C)
		return suffix

	#----------------------------------------------------------------------
	# Return segment, which naturaly continues this segment
	#----------------------------------------------------------------------
	def shortenedSegment(self, dist):
		start = self.extrapolatePoint(dist)
		end = self.B
		if dist >= self.length():
			end = start
		shortened = Segment(self.type, start, end)
		if self.type != Segment.LINE:
			shortened.setCenter(self.C)
		return shortened

	#----------------------------------------------------------------------
	# Linearize this segment and return resulted segments
	#----------------------------------------------------------------------
	def linearize(self, maxseg=1, splitlines=False):
		#self.correct()
		#linearized = Path("linearized segment", None)
		linearized = []
		if splitlines or self.type == Segment.CW or self.type == Segment.CCW:
			count = int(ceil(self.length() / maxseg))
			if count == 0: count = 1 #fix for zero length
			step = self.length() / count
			#print "---"
			for i in range(0,count):
				#print i, self.length(), i*step, (i+1)*step
				linearized.append(Segment(Segment.LINE, self.distPoint(i*step), self.distPoint((i+1)*step)))
		else:
			linearized.append(self)
		return linearized

	#----------------------------------------------------------------------
	# Return tangential offset of this segment
	#----------------------------------------------------------------------
	def tangentialOffset(self, distance):
		#self.A = self.A + ( self.tangentStart() * distance )
		#self.B = self.B + ( self.tangentEnd() * distance )
		#self.correct()

		seg = Segment(
			self.type,
			self.A + ( self.tangentStart() * distance ),
			self.B + ( self.tangentEnd() * distance )
			)

		if self.type != Segment.LINE:
			seg.setCenter(self.C)

		return seg

	#----------------------------------------------------------------------
	# return segment length
	#----------------------------------------------------------------------
	def length(self):
		if self.type == Segment.LINE:
			return self.AB.length()

		elif self.type == Segment.CW:
			phi = self.startPhi - self.endPhi

		elif self.type == Segment.CCW:
			phi = self.endPhi - self.startPhi

		if phi < 0.0: phi += PI2
		return self.radius * phi

	#----------------------------------------------------------------------
	# Tangent vector at start
	#----------------------------------------------------------------------
	def tangentStart(self):
		if self.type == Segment.LINE:
			t = self.AB.clone()
			t.norm()
			return t
		else:
			O = self.A - self.C
			O.norm()
			if self.type == Segment.CCW:
				# return cross product -O x z(0,0,1)
				return Vector(-O[1], O[0])
			else:
				# return cross product -O x z(0,0,1)
				return Vector(O[1], -O[0])

	#----------------------------------------------------------------------
	# Tangent vector at end
	#----------------------------------------------------------------------
	def tangentEnd(self):
		if self.type == Segment.LINE:
			t = self.AB.clone()
			t.norm()
			return t
		else:
			O = self.B - self.C
			O.norm()
			if self.type == Segment.CCW:
				# return cross product -O x z(0,0,1)
				return Vector(-O[1], O[0])
			else:
				# return cross product -O x z(0,0,1)
				return Vector(O[1], -O[0])

	#----------------------------------------------------------------------
	# Orthogonal vector at start
	#----------------------------------------------------------------------
	def orthogonalStart(self):
		if self.type == Segment.LINE:
			O = self.AB.orthogonal()
			O.norm()
			return O
		else:
			O = self.A - self.C
			O.norm()
			if self.type == Segment.CCW:
				return -O
			else:
				return O

	#----------------------------------------------------------------------
	# Orthogonal vector at end
	#----------------------------------------------------------------------
	def orthogonalEnd(self):
		if self.type == Segment.LINE:
			O = self.AB.orthogonal()
			O.norm()
			return O
		else:
			O = self.B - self.C
			O.norm()
			if self.type == Segment.CCW:
				return -O
			else:
				return O

	#----------------------------------------------------------------------
	# Check if point P is on segment
	# WARNING: this is not a robust test is used for the intersect
	#----------------------------------------------------------------------
	def _insideArc(self, P):
		phi = atan2(P[1]-self.C[1], P[0]-self.C[0])
		if self.type==Segment.CW:
			if phi < self.endPhi-EPS/self.radius: phi += PI2
			if phi <= self.startPhi + EPS/self.radius:
				return True
		elif self.type==Segment.CCW:
			if phi < self.startPhi-EPS/self.radius: phi += PI2
			if phi <= self.endPhi + EPS/self.radius:
				return True
		if eq(self.A,P,EPS) or eq(self.B,P,EPS):
			return True
		return False

	#----------------------------------------------------------------------
	# Return if P is inside the segment
	#----------------------------------------------------------------------
	def inside(self, P):
		if self.type == Segment.LINE:
			if P[0] <= self.minx or P[0] >= self.maxx: return False
			if P[1] <= self.miny or P[1] >= self.maxy: return False
			return True
		else:
			return self._insideArc(P)

	#----------------------------------------------------------------------
	# return a increasing number LINE:length2 or CW/CCW:angle of point P
	# on the segment wrt to the start point. Useful for sorting points
	# on segments @see Path.intersectSelf()
	#----------------------------------------------------------------------
	def order(self, P):
		if self.type == Segment.LINE:
			return (P-self.A).length2()

		phi = atan2(P[1]-self.C[1], P[0]-self.C[0])
		if self.type==Segment.CW:
			if phi < self.endPhi-EPS/self.radius: phi += PI2
			return self.startPhi - phi
		elif self.type==Segment.CCW:
			if phi < self.startPhi-EPS/self.radius: phi += PI2
			return phi - self.startPhi

	#----------------------------------------------------------------------
	# Intersect a line with line
	#----------------------------------------------------------------------
	def _intersectLineLine(self, other):
		# check for intersection
		DD = -self.AB[0]*other.AB[1] + self.AB[1]*other.AB[0]
		if abs(DD)<EPS2: return None,None

		Dt = -(other.A[0]-self.A[0])*other.AB[1] + \
		      (other.A[1]-self.A[1])*other.AB[0]
		t = Dt/DD
		P = self.AB*t + self.A
		if self.minx<=P[0]<=self.maxx and other.minx<=P[0]<=other.maxx and \
		   self.miny<=P[1]<=self.maxy and other.miny<=P[1]<=other.maxy:
			return P,None
		return None,None

	#----------------------------------------------------------------------
	# Intersect a line segment with an arc
	#----------------------------------------------------------------------
	def _intersectLineArc(self, arc):
		#AB = self.B
		#a  = AB.length2()
		a = self.AB[0]**2 + self.AB[1]**2
		if a<EPS2: return None,None

		#CA = self.A-arc.C
		#b  = 2.0*AB*CA
		#c  = CA.length2() - arc.radius**2
		CAx = self.A[0] - arc.C[0]
		CAy = self.A[1] - arc.C[1]
		b   = 2.0*(self.AB[0]*CAx + self.AB[1]*CAy)

		#c  = CAx**2 + CAy**2 - arc.radius**2
		if abs(CAx) < abs(CAy):
			c = CAy**2 + (CAx+arc.radius)*(CAx-arc.radius)
		else:
			c = CAx**2 + (CAy+arc.radius)*(CAy-arc.radius)

		t1,t2 = quadratic(b/a,c/a)
		if t1 is None: return None,None
		if t1<-EPS or t1>1.0+EPS:
			P1 = None
		elif t1<=EPS:
			P1 = Vector(self.A)
		elif t1>=1.0-EPS:
			P1 = Vector(self.B)
		else:
			#P1 = AB*t1 + self.A
			P1 = Vector(self.AB[0]*t1+self.A[0], self.AB[1]*t1+self.A[1])
		if P1 and not arc._insideArc(P1): P1 = None

		if t2<-EPS or t2>1.0+EPS:
			P2 = None
		elif t2<=EPS:
			P2 = Vector(self.A)
		elif t2>=1.0-EPS:
			P2 = Vector(self.B)
		else:
			#P2 = AB*t2 + self.A
			P2 = Vector(self.AB[0]*t2+self.A[0], self.AB[1]*t2+self.A[1])
		if P2 and not arc._insideArc(P2): P2 = None

		# force P1 to have always the solution if any
		if P1 is None: return P2,None
		return P1,P2

	#----------------------------------------------------------------------
	# Intersect a circle with circle
	#----------------------------------------------------------------------
	def _intersectCircleCircle(self, other):
		# Circle circle intersection
		CC = other.C - self.C
		d = CC.norm()
		if d<=EPS2 or d>=self.radius+other.radius: return None,None
		#x = (d**2 + self.radius**2 - other.radius**2) / (2.*d)
		if abs(d)<abs(self.radius):
			x = (self.radius**2 + \
			    (d+other.radius)*(d-other.radius)) / (2.*d)
		else:
			x = (d**2 + \
			    (self.radius+other.radius)*(self.radius-other.radius)) / (2.*d)

		diff = (self.radius-x)*(self.radius+x)
		if diff<-EPS: return None,None
		elif diff<EPS: diff = 0.0
		y = sqrt(diff)

		O = CC.orthogonal()

		P1 = self.C + x*CC + y*O
		if not self._insideArc(P1) or not other._insideArc(P1):
			P1 = None

		P2 = self.C + x*CC - y*O
		if not self._insideArc(P2) or not other._insideArc(P2):
			P2 = None

		# force P1 to have always the solution if any
		if P1 is None: return P2,None
		return P1,P2

	#----------------------------------------------------------------------
	# Intersect with another segment
	# returns two points
	#----------------------------------------------------------------------
	def intersect(self, other):
		# intersect their bounding boxes
		if max(self.minx,other.minx) > min(self.maxx,other.maxx): return None,None
		if max(self.miny,other.miny) > min(self.maxy,other.maxy): return None,None

		if self.type==Segment.LINE and other.type==Segment.LINE:
			return self._intersectLineLine(other)

		elif self.type==Segment.LINE and other.type!=Segment.LINE:
			return self._intersectLineArc(other)

		elif self.type!=Segment.LINE and other.type==Segment.LINE:
			return other._intersectLineArc(self)

		elif self.type!=Segment.LINE and other.type!=Segment.LINE:
			return self._intersectCircleCircle(other)

	#----------------------------------------------------------------------
	# Return minimum distance of P from segment
	#----------------------------------------------------------------------
	def distance(self, P):
#		if eq(P,Vector(42.0926, 16.8319)) and \
#		   eq(self.A, Vector(48.0042, 15.5539)) and \
#		   eq(self.B, Vector(36.2223, 15.5307)):
#			import pdb; pdb.set_trace()
		if self.type == Segment.LINE:
			AB2  = self.AB[0]**2 + self.AB[1]**2
			APx  = P[0]-self.A[0]
			APy  = P[1]-self.A[1]
			if abs(AB2)<EPS: return sqrt(APx**2+APy**2)
			dot  = APx*self.AB[0] + APy*self.AB[1]
			proj = dot / AB2
			if proj < 0.0:
				return sqrt(APx**2+APy**2)
			elif proj > 1.0:
				return sqrt((P[0]-self.B[0])**2 + (P[1]-self.B[1])**2)
			else:
				d = (APx**2+APy**2) - dot*proj
				if abs(d)<EPS: return 0.0
				return sqrt(d)

		elif self.type == Segment.CW:
			PCx = P[0] - self.C[0]
			PCy = P[1] - self.C[1]
			phi = atan2(PCy, PCx)
			if phi < self.endPhi-EPS/self.radius: phi += PI2
			if phi > self.startPhi+EPS/self.radius:
				return sqrt((P[0]-self.A[0])**2 + (P[1]-self.A[1])**2)
			else:
				return abs(sqrt(PCx**2+PCy**2) - self.radius)

		elif self.type == Segment.CCW:
			PCx = P[0] - self.C[0]
			PCy = P[1] - self.C[1]
			phi = atan2(PCy, PCx)
			if phi < self.startPhi-EPS/self.radius: phi += PI2
			if phi > self.endPhi+EPS/self.radius:
				return sqrt((P[0]-self.B[0])**2 + (P[1]-self.B[1])**2)
			else:
				return abs(sqrt(PCx**2+PCy**2) - self.radius)

	#----------------------------------------------------------------------
	# Split segment at point P and return second part
	#----------------------------------------------------------------------
	def split(self, P):
		if eq(P,self.A,EPS):
			# XXX should flag previous segment as cross
			return -1

		elif eq(P,self.B,EPS):
			self._cross = True
			return 0

		new = Segment(self.type, P, self.B)
		new._cross  = self._cross
		self._cross = False
		self.B    = P
		self.AB     = self.B - self.A
		if self.type>Segment.LINE:
			new.setCenter(self.C) #, self.radius, None, self.endPhi)
			self.setCenter(self.C) #, self.radius, self.startPhi, new.startPhi)
		else:
			self.calcBBox()
		return new


#==============================================================================
# Path: a list of joint segments
# Closed path?
# Path length
# reverse
# ignore zero length segments
#==============================================================================
class Path(list):
	def __init__(self, name, color=None):
		self.name    = name
		self.color   = color
		self._length = None

	#----------------------------------------------------------------------
	def __repr__(self):
		return "%s:\n\t%s"%(self.name, "\n\t".join([
			"%3d: %s"%(i,x) for i,x in enumerate(self)]))

	#----------------------------------------------------------------------
	def calcBBox(self):
		self.minx = self.miny =  1E10
		self.maxx = self.maxy = -1E10
		for segment in self:
			self.minx = min(self.minx, segment.minx)
			self.miny = min(self.miny, segment.miny)
			self.maxx = max(self.maxx, segment.maxx)
			self.maxy = max(self.maxy, segment.maxy)

	#----------------------------------------------------------------------
	# @return true if path is closed
	#----------------------------------------------------------------------
	def isClosed(self):
		return self and eq(self[0].A, self[-1].B)

	#----------------------------------------------------------------------
	# Close path by connecting the with a line segment
	#----------------------------------------------------------------------
	def close(self):
		self._length = None
		self.append(Segment(Segment.LINE, self[-1].B, self[0].A))

	#----------------------------------------------------------------------
	# Join path at the end
	#----------------------------------------------------------------------
	def join(self, path):
		self._length = None
		self.append(Segment(Segment.LINE, self[-1].B, path[0].A))
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
	# Change path direction:
	#	+1 for Segment.CW
	#	-1 for Segment.CCW
	#----------------------------------------------------------------------
	def directionSet(self, opdir):
		curdir = self._direction(self.isClosed())
		if curdir == 0: return False
		if curdir != 0 and curdir != opdir: self.invert()
		return True

	#----------------------------------------------------------------------
	# Return:
	#	-1 for Segment.CCW closed path
	#        0 for open path
	#	+1 for Segment.CW  closed path
	#----------------------------------------------------------------------
	def direction(self):
		if not self.isClosed(): return 0
		return self._direction(True)

	#----------------------------------------------------------------------
	# Return -1/+1 even for open paths (experimental, but seems to work better, than previous version)
	# https://stackoverflow.com/questions/1165647/how-to-determine-if-a-list-of-polygon-points-are-in-clockwise-order
	#----------------------------------------------------------------------
	def _direction(self, closed=True):

		def dircalc(A,B):
			dir = (B[0] - A[0])*(B[1] + A[1])
			#print("point", A[0], A[1], B[0], B[1],"\t",dir)
			#print("g1 x"+str(A[0])+" y"+str(A[1]))
			#print("g1 x"+str(B[0])+" y"+str(B[1]))
			return dir


		sum = 0
		cwarc = 0

		for segment in self:
			if segment.type == Segment.CW: cwarc += segment.length()
			if segment.type == Segment.CCW: cwarc -= segment.length()

			A = segment.A
			B = segment.B
			if A is not None and B is not None:
				sum += dircalc(A,B)

		#Decide direction
		if sum < 0: sum = -1	#CCW
		if sum > 0: sum = 1	#CW

		#Arcs (and therefore circles) are now treated as lines (linear approximation)
		#If we can't decide based on points, we will compare amount of distance traveled in CW and CCW arcs
		#This is kinda heuristic. If we ever need better results, there's way to do it:
		#Just split all arcs into 10 smaller arcs before processing.
		#That will vastly increase the resolution of linear approximation.
		#If you know to split arcs, plese do it. For now we have this heuristic:

		if sum == 0:
			if cwarc < 0: sum = -1	#CCW
			if cwarc > 0: sum = 1	#CW

		#if sum == 0: sum = 1	#CW if still undecided?
		#print("Sum ", sum)
		return sum

	#----------------------------------------------------------------------
	# @return the bounding box of the path (very crude)
	#----------------------------------------------------------------------
	def bbox(self):
		minx = self[0].minx
		miny = self[0].miny
		maxx = self[0].maxx
		maxy = self[0].maxy
		for segment in self[1:]:
			minx = min(minx, segment.minx)
			miny = min(miny, segment.miny)
			maxx = max(maxx, segment.maxx)
			maxy = max(maxy, segment.maxy)
		return minx,miny,maxx,maxy

	#----------------------------------------------------------------------
	# @return the center of the path (based on bbox)
	#----------------------------------------------------------------------
	def center(self):
		minx,miny,maxx,maxy = self.bbox()
		x=(minx+maxx)/2
		y=(miny+maxy)/2
		return x,y

        #----------------------------------------------------------------------
        # Return a point ON the path at distance traveled from A to B (or B to A when negative)
        #----------------------------------------------------------------------
	def distPoint(self, dist):
		if dist < 0:
			dist = self.length() + dist
		for segment in self:
			if dist-segment.length() <= 0:
				return segment.distPoint(dist)
			dist -= segment.length()

        #----------------------------------------------------------------------
        # Return linearized path (arcs are subdivided to lines)
        #----------------------------------------------------------------------
	def linearize(self, maxseg=1, splitlines=False):
		linearized = Path(self.name, self.color)
		for seg in self:
			linearized.extend(seg.linearize(maxseg, splitlines))
		return linearized

        #----------------------------------------------------------------------
        # Return arcfited path
        #----------------------------------------------------------------------
	def arcFit(self, prec=0.5, numseg=10):
		def vecdir(TA,TB):
			if (( TA[0] * TB[1] ) - ( TA[1] * TB[0] )) < 0:
				return 1
			return 0

		def arcsteer(A,B):
			TA = A.tangentEnd()
			TB = B.tangentStart()
			return vecdir(TA,TB)

		def arcdir(seg, C):
			CV = C - seg.midPoint()
			CV.normalize()
			return vecdir(seg.tangentStart(), CV)

		def pdist(A,B):
			return sqrt((B[0]-A[0])**2 + (B[1]-A[1])**2)

		def circle3center(A,B,C):
			try:
				xDelta_a = B[0] - A[0]
				yDelta_a = B[1] - A[1]
				xDelta_b = C[0] - B[0]
				yDelta_b = C[1] - B[1]
				center = Vector(0, 0)

				aSlope = yDelta_a/xDelta_a
				bSlope = yDelta_b/xDelta_b
				center[0] = (aSlope*bSlope*(A[1] - C[1]) + bSlope*(A[0] + B[0]) - aSlope*(B[0]+C[0]) )/(2* (bSlope-aSlope) )
				center[1] = -1*(center[0] - (A[0]+B[0])/2)/aSlope +  (A[1]+B[1])/2

				return center
			except:
				return None

		def arcd2seg(arcd):
			if arcd:
				return Segment.CW
			return Segment.CCW

		def testFit(path, prec, C, r, dir=None):
			if C is None or r is None: return False

			#Small radiuses need more precision
			prec = min(prec, r/4)

			#Check if there are no parts of arc going far away from the original lines
			#FIXME: currently only comparing lenghts and middle points
			if len(path) > 1:
				path._length = None
				arc = Segment(arcd2seg(arcd), path[0].A, path[-1].B, C)
				if abs(path.length() - arc.length()) > prec: return False
				if pdist(path.distPoint(path.length()/2), arc.midPoint()) > prec: return False

			#Check if there are no original lines going far away from arc
			for seg in path:
				if seg.type != Segment.LINE: return False
				if abs(pdist(seg.A, C) - r) > prec: return False
				if abs(pdist(seg.B, C) - r) > prec: return False
				if abs(pdist(seg.midPoint(), C) - r) > prec: return False

				#Test direction
				if arcdir(seg, C) != dir:
					#print "wrong direction"
					return False

			return True

		#Get circle center(s) given radius and two points
		def radius2points(A,B,r, arcd=None):
			q = sqrt((B[0]-A[0])**2 + (B[1]-A[1])**2)
			x3 = (A[0]+B[0])/2
			y3 = (A[1]+B[1])/2

			C = Vector(
				x3 + sqrt(r**2-(q/2)**2)*(A[1]-B[1])/q,
				y3 + sqrt(r**2-(q/2)**2)*(B[0]-A[0])/q
			)

			D = Vector(
				x3 - sqrt(r**2-(q/2)**2)*(A[1]-B[1])/q,
				y3 - sqrt(r**2-(q/2)**2)*(B[0]-A[0])/q
			)

			#There are two solutions (C and D), choose which one we need
			if arcd is not None:
				if arcd == 0:
					return C
				else:
					return D
			else:
				return C, D

		def path2arc(tmpath):
			#Test if all segments are lines
			for seg in tmpath:
				if seg.type != Segment.LINE: return None, None, None

			#Find center
			cnt = 0
			C = Vector(0,0)
			for i in range(1, len(tmpath)):
				Ct = circle3center(tmpath[i-1].A, tmpath[i-1].B, tmpath[i].B)
				#Ct = circle3center(tmpath[0].A, tmpath[i].A, tmpath[-1].B)
				if Ct is not None:
					cnt += 1
					C += Ct
			if cnt < 1:
				return None, None, None
			C /= cnt

			#Find direction
			arcd = arcdir(tmpath[0], C)

			#Find radius
			r = 0
			for seg in tmpath:
				r += pdist(seg.A, C)
				r += pdist(seg.B, C)
			r /= len(tmpath)*2

			#Fix center to match start and end of segment:
			#(Not sure if this needed)
			#print("Center: ", C, radius2points(tmpath[0].A, tmpath[-1].B, r, arcd))
			C = radius2points(tmpath[0].A, tmpath[-1].B, r, arcd)

			return C, r, arcd

		def path2gc(path):
			print("(Block-name: debug)")
			print("g0 x%f y%f"%(path[0].A[0], path[0].A[1]))
			for seg in path:
				print("g1 x%f y%f"%(seg.B[0], seg.B[1]))

		numseg = max(2,numseg)
		npath = Path(self.name, self.color)
		i = 0
		while i < len(self):
			found = False
			#FIXME: allow to merge lines with existing arcs when arc fitting
			if i+numseg <= len(self):
				tmpath = Path('tmp')
				tmpath.extend(self[i:i+numseg])
				C, r, arcd = path2arc(tmpath)
				#FIXME: define arc in way that would enable us to fit arcs without fitting lines first
				if testFit(tmpath, prec, C, r, arcd):
					j = i+numseg
					while j < len(self):
						if not testFit([self[j]], prec, C, r, arcd): break
						tmpath.append(self[j])
						if not testFit(tmpath, prec, C, r, arcd):
							del tmpath[-1]
							break
						Co, ro, ign = path2arc(tmpath)
						if testFit(tmpath, prec, Co, ro, arcd):
							#print "upd", len(tmpath), C, r, Co, ro
							C, r = Co, ro
						j += 1

					if len(tmpath) >= numseg:
						found = True
						#npath.extend(tmpath)
						#npath.append(Segment(Segment.LINE, tmpath[0].A, tmpath[-1].B))
						npath.append(Segment(arcd2seg(arcd), tmpath[0].A, tmpath[-1].B, C))
						#path2gc(tmpath)
						i = j

			if not found:
				npath.append(self[i])
				i+=1

		return npath

        #----------------------------------------------------------------------
        # Return path with merged adjacent lines. It's good to use before arc fiting
        #----------------------------------------------------------------------
	def mergeLines(self, prec=0.5):
		npath = Path(self.name, self.color)
		i = 0
		while i < len(self):
			found = False
			if self[i].type == Segment.LINE:
				tmpath = Path('tmp')
				tmpath.extend([self[i]])
				j = i+1
				while(j < len(self)):
					#Test if next segment is line
					if not self[j].type == Segment.LINE: break

					#Test if there is continuity between lines
					if not eq(tmpath[-1].B, self[j].A): break

					#Test if lines are EXACTLY parallel (not a good idea, we want little bit of give)
					#if not eq(tmpath[0].tangentEnd(), self[j].tangentEnd()): break

					#Test if no point diverts too far from proposed fited line (within specified precision)
					fit = Segment(Segment.LINE, tmpath[0].A, self[j].B)
					toofar = False
					for seg in tmpath:
						if fit.distance(seg.B) > prec: toofar = True
					if toofar: break

					tmpath.append(self[j])
					j += 1

				if len(tmpath) > 1:
					found = True
					npath.append(Segment(Segment.LINE, tmpath[0].A, tmpath[-1].B))
					i = j

			if not found:
				npath.append(self[i])
				i+=1

		return npath



	#----------------------------------------------------------------------
	# Return true if point P(x,y) is inside the path
	# The solution is determined by the number N of crossings of a horizontal
	# line starting from the point P(x,y)
	# If N is odd the point is inside
	# if N is even the point is outside
	# WARNING: the path must be closed otherwise it is meaningless
	#----------------------------------------------------------------------
	def isInside(self, P):
		#print "P=",P
		#minx,miny,maxx,maxy = self.bbox()
		maxx = self.bbox()[2]
		#print "limits:",minx,miny,maxx,maxy
		#FIXME: this is strange. adding +1000 to line endpoint changes the outcome of method
		#	i've found that doing this works around some unknown problem in most cases, but it's not really ideal solution
		line = Segment(Segment.LINE, P, Vector(maxx*1.1, P[1]+1000))
		count = 0
		PP1 = None	# previous points to avoid double counting
		PP2 = None
		#print "Line=",line
		for segment in self:
			P1,P2 = line.intersect(segment)
			#print
			#print i,segment
			if P1 is not None:
				if PP1 is None and PP2 is None:
					count += 1
				elif PP1 is not None and PP2 is not None and \
				     not eq(P1,PP1) and not eq(P1,PP2):
					count += 1
				elif PP1 is not None and not eq(P1,PP1):
					count += 1
				elif PP2 is not None and not eq(P1,PP2):
					count += 1

				if P2 is not None:
					if eq(P1,P2):
						P2 = None
					elif PP1 is None and PP2 is None:
						count += 1
					elif PP1 is not None and PP2 is not None and \
					     not eq(P2,PP1) and not eq(P2,PP2):
						count += 1
					elif PP1 is not None and not eq(P2,PP1):
						count += 1
					elif PP2 is not None and not eq(P2,PP2):
						count += 1
			#print P1,P2,count
			PP1 = P1
			PP2 = P2
		#print "Count=",count
		return bool(count&1)

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
	# This not only SPLITs path to contours,
	# it also takes unsorted segments and JOINs them to closed loops if possible
	# FIXME: If this is true, this should be probably called reconstructContours()
	#----------------------------------------------------------------------
	def split2contours(self, acc=EPSV):
		if not self: return []

		path = Path(self.name, self.color)
		paths = [path]

		# Push first element as start point
		path.append(self.pop(0))

		# Repeat until all segments are used
		while self:
			# End point
			end = path[-1].B

			# Find the segment that starts after the last one
			for i,segment in enumerate(self):
				# Try starting point
				if eq(end, segment.A, acc):
					path.append(segment)
					del self[i]
					break

				# Try ending point (inverse)
				if eq(end, segment.B, acc):
					segment.invert()
					path.append(segment)
					del self[i]
					break

			else:
				# Start point
				start = path[0].A

				# Find the segment that starts after the last one
				for i,segment in enumerate(self):
					# Try starting point
					if eq(start, segment.A, acc):
						segment.invert()
						path.insert(0,segment)
						del self[i]
						break

					# Try ending point (inverse)
					if eq(start, segment.B, acc):
						path.insert(0,segment)
						del self[i]
						break
				else:
					# Not found push a path start point and
					path = Path(self.name, self.color)
					paths.append(path)
					path.append(self.pop(0))

		# Correct ending points of the contours
#		for path in paths:
#			closed = path.isClosed()
#			end = path[0].B
#			for segment in path[1:]:
#				segment.setStart(end)
#				end = segment.B
#			if closed:
#				path[0].setStart(end)

		return paths

	#----------------------------------------------------------------------
	# Return path with offset
	#----------------------------------------------------------------------
	def offset(self, offset, name=None):
		#start = time.time()
		if name is None: name = self.name
		path = Path(name, self.color)

		if self.isClosed():
			prev = self[-1]
			Op = prev.orthogonalEnd()
			Eo = prev.B + Op*offset
		else:
			prev = None
			Op   = None	# previous orthogonal
			Eo   = None
		for segment in self:
			O  = segment.orthogonalStart()
			So = segment.A + O*offset
			# Join with the previous edge
#			inside = False
			if Eo is not None and eq(Eo,So):
				# possibly a full circle
				if segment.type != Segment.LINE and len(self)==1:
					path.append(Segment(segment.type, Eo, So, segment.C))
#					print "*0*",path[-1]

			elif Op is not None:
				# if cross*offset
				cross = O[0]*Op[1]-O[1]*Op[0]
				dot   = O[0]*Op[0]+O[1]*Op[1]
				#if (prev.type!=Segment.LINE and segment.type!=Segment.LINE) or \
				if  (abs(cross)>EPSV or dot<0.0) and cross*offset >= 0:
					# either a circle
					t = Segment.CW if offset> 0 else Segment.CCW
					path.append(Segment(t, Eo, So, segment.A))
#					print "*A*",path[-1]
				else:
					# or a straight line if inside
					path.append(Segment(Segment.LINE, Eo, So))
#					inside = True
#					print "*B*",path[-1]

			# connect with previous point
			O  = segment.orthogonalEnd()
			Eo = segment.B + O*offset
			if (So-Eo).length2() > EPSV2:
				if segment.type == Segment.LINE:
					path.append(Segment(Segment.LINE, So, Eo))
#					print "*C*",path[-1]
				else:
					# FIXME check for radius + offset > 0.0
					path.append(Segment(segment.type, So, Eo, segment.C))
#					print "*D*",path[-1]
#					if abs(abs(segment.radius - path[-1].radius) - abs(offset)) > EPS:
#						print "ERROR", segment.radius - path[-1].radius - abs(offset)
#						import pdb; pdb.set_trace()

				# Internal line segment?
#				if inside and len(path)>2:
#					# Check the distance with the intersection point
#					P1,P2 = path[-3].intersect(path[-1])
#					if P1 or P2:
#						M = path[-2].midPoint()
#						if P1 and (P1-M).length() < abs(offset)/100:
#								#delete segment
#								path[-3].setEnd(P1)
#								path[-1].setStart(P1)
#								del path[-2]
#								print "DELETE SEGMENT"
#						elif P2:
#							pass

			Op = O
			prev = segment
		#print("# path.offset: %g\n"%(time.time()-start))
		return path

	#----------------------------------------------------------------------
	# Return path with offset, overcuts and cleanup
	#----------------------------------------------------------------------
	def offsetClean(self, offset, overcut=False, name=None):
		path = self #deepcopy??
		# Remove tiny segments
		path.removeZeroLength(abs(offset)/100.)
		# Convert very small arcs to lines
		path.convert2Lines(abs(offset)/10.)
		# Determine offset direction
		D = path.direction()
		if D==0: D=1
		# Offset
		opath = path.offset(D*offset, name)
		# Post clean
		if opath:
			opath.intersectSelf()
			opath.removeExcluded(path, D*offset)
			opath.removeZeroLength(abs(offset)/100.)
			opath = opath.split2contours()
			if overcut:
				for p in opath:
					p.overcut(D*offset)

		return opath

	#----------------------------------------------------------------------
	# intersect path with self and mark all intersections
	#----------------------------------------------------------------------
	def intersectSelf(self):
		#FIXME: maybe use intersectPath() to implement this??
		points = []	# list of intersection (segment#, order, point) pair
		def addPoint(i, P):
			# FIXME maybe add sorted and check for duplicates?
			if eq(P,self[i].A,EPS): return
			if eq(P,self[i].B,EPS):   return
			oi = self[i].order(P)
			points.append((i,oi,P))

		# Find all interesection points
		for i,si in enumerate(self[:-2]):
			if si.type==Segment.LINE and self[i+1].type==Segment.LINE:
				j = i+2
			else:
				j = i+1
			while j<len(self):
				P1,P2 = si.intersect(self[j])
				# skip doublet solution
				if P1 is not None and P2 is not None and eq(P1,P2,EPS):
					P2 = None
				if P1:
					addPoint(i,P1)
					addPoint(j,P1)
				if P2:
					addPoint(i,P2)
					addPoint(j,P2)
				j += 1

		# sort accoring to index, and position of point
		points.sort(key=itemgetter(0,1))

		# split paths
		for i,o,P in reversed(points):
			split = self[i].split(P)
			if not isinstance(split,int):
				self.insert(i+1,split)
				self[i]._cross = True
		return points

	#----------------------------------------------------------------------
	# mark all segments of intersected path that lay inside another path
	#----------------------------------------------------------------------
	def markInside(self, path, setinside):
		for i,si in enumerate(self):
			if path.isInside(si.midPoint()): si._inside.append(setinside)

	#----------------------------------------------------------------------
	# intersect path with other path and mark all intersections
	#----------------------------------------------------------------------
	def intersectPath(self, path, setinside=None):
		points = []	# list of intersection (segment#, order, point) pair
		def addPoint(i, P):
			# FIXME maybe add sorted and check for duplicates?
			if eq(P,self[i].A,EPS): return
			if eq(P,self[i].B,EPS):   return
			oi = self[i].order(P)
			points.append((i,oi,P))

		# Find all interesection points
		for i,si in enumerate(self):
			for cut in path:
				P1,P2 = si.intersect(cut)
				# skip doublet solution
				if P1 is not None and P2 is not None and eq(P1,P2,EPS):
					P2 = None
				if P1:
					addPoint(i,P1)
				if P2:
					addPoint(i,P2)

		# sort accoring to index, and position of point
		points.sort(key=itemgetter(0,1))

		# split paths
		for i,o,P in reversed(points):
			split = self[i].split(P)
			if not isinstance(split,int):
				self.insert(i+1,split)
				self[i]._cross = True

		#Mark inside segments
		#FIXME: for some reason this fails if doing multiple intersections
		#	in such case you have to intersect all paths and then mark them using markInside() additionaly
		if setinside is not None:
			self.markInside(path, setinside)

		return points

	#----------------------------------------------------------------------
	# remove the excluded segments from an intersect path
	# @param include defines the first segment if it is to be included
	# or not
	#----------------------------------------------------------------------
	def removeExcluded(self, path, offset):
		chkofs = abs(offset)*(1.0-EPS)

		#--------------------------------------------------------------
		# Search if point P is closer than chkofs or not
		#--------------------------------------------------------------
		def isClose(P, last):
			# search in the close vicinity first
			i0 = last-min(10, len(path))
			if i0<0: i0 += len(path)
			for i in range(i0, len(path)):
				if path[i].distance(P) < chkofs:
					return False, i
			for i in range(i0):
				if path[i].distance(P) < chkofs:
					return False, i
#			for x in path:
#				if x.distance(P) < chkofs:
#					return False
			return True, last

		last = 0
		include, last = isClose(self[0].midPoint(), last)
		i = 0
		while i < len(self):
			cross = self[i]._cross
			if not include:
				del self[i]
				i -= 1
			i += 1
			if cross:	# end of self[i] is a crossing point
				# FIXME Can become more intelligent
				#    check if really it crosses the segment
				#    or it goes back (only touching)
				# Check middle of next path
				include,last = isClose(self[i%len(self)].midPoint(), last)

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
				if prev.type==Segment.LINE \
				   and segment.type==Segment.LINE \
				   and cross*offset < -EPSV:
					# find direction
					D = O+Op
					D.normalize()
					if offset>0.0: D = -D
					costheta = O*Op
					costheta2 = sqrt((1.0+costheta)/2.0)
					distance = abs(offset)*(1.0/costheta2-1.0)
					D *= distance
					self.insert(i,Segment(Segment.LINE, segment.A, segment.A + D))
					self.insert(i+1, Segment(Segment.LINE, segment.A+D, segment.A))
					i += 2
			prev = segment
			Op = prev.orthogonalEnd()
			i += 1

	#----------------------------------------------------------------------
	def trochovercut(self, offset, overcut, adaptative, adaptedRadius):
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
				if prev.type==Segment.LINE and segment.type==Segment.LINE and cross*offset < -EPSV:
					# find direction
					D = O+Op
					D.normalize()
					if offset>0.0: D = -D

					Dpolice = D *0.00001 

					costheta = O*Op
					costheta2 = sqrt((1.0+costheta)/2.0)
					distance = abs(offset)*(1.0/costheta2-1.0)
					if overcut == 1 and adaptative == 0:
						pass
					#	distance =  float(abs(adaptedRadius))
					if overcut == 0 and adaptative == 1:
					#	distance =  abs(adaptedRadius)
						distance = abs(adaptedRadius)*(1.0/costheta2-1.0)
						distance +=  abs(adaptedRadius)
					elif  overcut == 1 and adaptative == 1:
						distance +=  abs(adaptedRadius)
					D *= distance
					if adaptative:
						self.insert(i,Segment(Segment.LINE, segment.A, segment.A + Dpolice))
						self.insert(i+1, Segment(Segment.LINE, segment.A+Dpolice, segment.A))
						self.insert(i+2,Segment(Segment.LINE, segment.A, segment.A + D))
						self.insert(i+3, Segment(Segment.LINE, segment.A+D, segment.A))
						i += 4
					else:
						self.insert(i,Segment(Segment.LINE, segment.A, segment.A + D))
						self.insert(i+1, Segment(Segment.LINE, segment.A+D, segment.A))
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
			if eq(segment.A,P):
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
				k = loop.hasPoint(segment.A)
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
	# return eulerian paths
	# It takes bpath with random segments and tries to order and invert them
	# to create longest possible continuous toolpaths that actually makes sense
	# FIXME: This probably can be replaced with split2contours() and i've just reinvented wheel LOL
	#----------------------------------------------------------------------
	def eulerize(self, single=False):
		#Find eulerian path of graph
		def eulerPath(graph):
			# counting the number of vertices with odd degree
			odd = [ x for x in graph.keys() if len(graph[x])&1 ]
			odd.append( graph.keys()[0] )

			if len(odd)>3:
				#return None
				print("Failed to find eulerian path! Using non-eulerized path instead!")
				#FIXME: Probably we should at least find some non-eulerian paths instead?
				return graph

			stack = [ odd[0] ]
			path = []

			# main algorithm
			while stack:
				v = stack[-1]
				if graph[v]:
					u = graph[v][0]
					stack.append(u)
					# deleting edge u-v
					del graph[u][ graph[u].index(v) ]
					del graph[v][0]
				else:
					path.append( stack.pop() )

			return path

		#Encode bpath to graph
		#	bpath segments	-> graph nodes
		#	bpath points	-> graph edges
		#	(yes it's confusing, but it has to be this way)
		eulg = {}
		for i,segi in enumerate(self):
			eulg[i] = []
		for i,segi in enumerate(self):
			for j,segj in enumerate(self):
				if i == j: continue
				#TODO: some of these are probably redundant, for now i left it here to be safe:
				if eq(segi.B,segj.A) or eq(segi.A,segj.B):
					if j not in eulg[i]: eulg[i].append(j)
				if eq(segi.B,segj.B) or eq(segi.A,segj.A):
					if j not in eulg[i]: eulg[i].append(j)

		#Return first subgraph from graph
		def getFirstSubGraph(graph):
			if len(graph) == 0: return None
			subg = {}
			todo = [graph.keys()[0]]
			while len(todo) > 0:
				if todo[0] in graph.keys():
					subg[todo[0]] = graph[todo[0]]
					todo.extend(graph[todo[0]])
					del graph[todo[0]]
				del todo[0]
			return subg

		#Split to multiple graphs if there are subgraphs without interconnecting edges!
		subgs = []
		subg = getFirstSubGraph(eulg)
		while subg is not None:
			print("subgraph",subg)
			subgs.append(subg)
			subg = getFirstSubGraph(eulg)

		eulpaths = []
		for eulg in subgs:
			#Find eulerian path in graph
			eulp = eulerPath(eulg)
			print("eulerpath",eulp)

			#Reconstruct bpath from eulerian graph
			eulpath = Path("euler")
			lastb = self[eulp[-1]].B
			print("--------")
			for i in eulp:
				seg = self[i]
				if not eq(lastb,seg.A):
					seg.invert()
					#seg._cross=False
				print(seg)
				eulpath.append(seg)
				lastb = seg.B
			del eulpath[0]

			eulpaths.append(eulpath)

		#Return path(s)
		if single:
			return eulpaths[0]
			eulpath = Path("euler")
			for p in eulpaths:
				print("path",p)
				eulpath.extend(p)
			return eulpath
		return eulpaths

	#----------------------------------------------------------------------
	# Remove zero length segments
	# Replace small arcs with lines
	#----------------------------------------------------------------------
	def removeZeroLength(self, eps=EPSV):
		i = 0
		while i<len(self):
			#if eq(self[i].A, [227.286, 151.109]): import pdb; pdb.set_trace()
			if self[i].length() < eps:
				start = self[i].A
				del self[i]
				# Join segments
				if 0<i<len(self):
					self[i].setStart(start)
				continue

			# Convert to line segments ones with small saggita
			if self[i].type != Segment.LINE:
				if self[i].type == Segment.CCW:
					df = self[i].endPhi - self[i].startPhi
				else:
					df = self[i].startPhi - self[i].endPhi
				if df<pi/2.0:
					sagitta = self[i].radius * (1.0 - cos(df/2.0))
					if sagitta < eps*5:
						self[i].change2Line()
			i += 1

		# Join last and first node if closed
		if self and eq(self[0].A, self[-1].B, eps):
			self[-1].setEnd(self[0].A)

	#----------------------------------------------------------------------
	# Convert to LINES small segments
	#----------------------------------------------------------------------
	def convert2Lines(self, minlen):
		for segment in self:
			if segment.type == Segment.LINE: continue
			if segment.length()<=minlen:
				segment.change2Line()

	#----------------------------------------------------------------------
	# Convert a dxf layer to a list of segments
	#----------------------------------------------------------------------
	def fromDxf(self, dxf, layer, units=0):
		for entity in layer:
			self.color = entity.color()
			A = dxf.convert(entity.start(), units)
			B   = dxf.convert(entity.end(), units)
			if entity.type == "LINE":
				if not eq(A,B):
					self.append(Segment(Segment.LINE, A, B))

			elif entity.type == "CIRCLE":
				center = dxf.convert(entity.center(), units)
				self.append(Segment(Segment.CCW, A, B, center))

			elif entity.type == "ARC":
#				t = entity._invert and Segment.CW or Segment.CCW
				t = Segment.CW if entity._invert else Segment.CCW
				center = dxf.convert(entity.center(), units)
				self.append(Segment(t, A, B, center))

			elif entity.type in ("POLYLINE", "LWPOLYLINE", "SPLINE"):
				# split it into multiple line segments
				xy = list(zip(dxf.convert(entity[10],units),
					      dxf.convert(entity[20],units)))
				if entity.isClosed(): xy.append(xy[0])
				bulge = entity.bulge()
				if not isinstance(bulge,list): bulge = [bulge]*len(xy)
				if entity._invert:
					# reverse and negate bulge
					xy.reverse()
					bulge = [-x for x in bulge[::-1]]

				for i,(x,y) in enumerate(xy[1:]):
					b = bulge[i]
					B = Vector(x,y)
					if eq(A,B): continue
					if abs(b)<EPS:
						self.append(Segment(Segment.LINE, A, B))

					elif abs(b-1.0)<EPS:
						# Semicircle
						center = (A+B)/2.0
						if b<0.0:
							t  = Segment.CW
						else:
							t  = Segment.CCW
						self.append(Segment(t, A, B, center))

					else:
						# arc with bulge = b
						# b = tan(theta/4)
						theta = 4.0*atan(abs(b))
						if abs(b)>1.0:
							theta = 2.0*pi - theta
						AB = A-B
						ABlen = AB.length()
						d = ABlen / 2.0
						r = d / sin(theta/2.0)
						C = (A+B)/2.0
						try:
							OC = sqrt((r-d)*(r+d))
							if b<0.0:
								t  = Segment.CW
							else:
								t  = Segment.CCW
								OC = -OC
							if abs(b)>1.0:
								OC = -OC
							center = Vector(C[0] - OC*AB[1]/ABlen,
									C[1] + OC*AB[0]/ABlen)
							self.append(Segment(t, A, B, center))
						except:
							self.append(Segment(Segment.LINE, A, B))
					A = B
