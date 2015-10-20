#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 20-Oct-2015

import sys

SPLINE_SEGMENTS = 20

# -----------------------------------------------------------------------------
# Convert a B-spline to polyline with a fixed number of segments
#
# FIXME to become adaptive
# -----------------------------------------------------------------------------
def spline2Polyline(controlPoints, degree, closed, segments):
	npts = len(controlPoints)

	# order:
	k = degree+1

	# resolution:
	p1 = segments * npts

	# based 1
	b = [0.0]*(npts*3+1)
	h = [1.0]*(npts+1)		# set all homogeneous weighting factors to 1.0
	p = [0.0]*(p1*3+1)

	i = 1
	for pt in controlPoints:
		b[i]   = pt[0]
		b[i+1] = pt[1]
		b[i+2] = 0.0

		#RS_DEBUG->print("RS_Spline::update: b[%d]: %f/%f", i, b[i], b[i+1])
		i +=3

	if closed:
		rbspline(npts,k,p1,b,h,p)
	else:
		rbsplinu(npts,k,p1,b,h,p)

	x = []
	y = []
	for i in range(1,3*p1+1,3):
		x.append(p[i])
		y.append(p[i+1])

	return x,y

# -----------------------------------------------------------------------------
# Generates B-Spline open knot vector with multiplicity
# equal to the order at the ends.
# -----------------------------------------------------------------------------
def knot(num, order, knotVector):
	knotVector[1] = 0
	for i in range(2, num+order+1):
		if i>order and i<num + 2:
			knotVector[i] = knotVector[i-1] + 1
		else:
			knotVector[i] = knotVector[i-1]

# -----------------------------------------------------------------------------
# Generates rational B-spline basis functions for an open knot vector.
def rbasis(c, t, npts, x, h, r):
	nplusc = npts + c
	temp = [0.0]*(nplusc+1)

	# calculate the first order nonrational basis functions n[i]
	for i in range(1, nplusc):
		if t >= x[i] and t < x[i+1]:
			temp[i] = 1.0
		else:
			temp[i] = 0.0

	# calculate the higher order nonrational basis functions

	for k in range(2,c+1):
		for i in range(1,nplusc-k+1):
			# if the lower order basis function is zero skip the calculation
			if temp[i] != 0.0:
				d = ((t-x[i])*temp[i])/(x[i+k-1]-x[i])
			else:
				d = 0.0

			# if the lower order basis function is zero skip the calculation
			if temp[i+1] != 0.0:
				e = ((x[i+k]-t)*temp[i+1])/(x[i+k]-x[i+1])
			else:
				e = 0.0
			temp[i] = d + e

	# pick up last point
	if t == x[nplusc]:
		temp[npts] = 1.0

	# calculate sum for denominator of rational basis functions
	s = 0.0
	for i in range(1,npts+1):
		s += temp[i]*h[i]

	# form rational basis functions and put in r vector
	for i in range(1, npts+1):
		if s != 0.0:
			r[i] = (temp[i]*h[i])/s
		else:
			r[i] = 0

# -----------------------------------------------------------------------------
# Generates a rational B-spline curve using a uniform open knot vector.
#
#	C code for An Introduction to NURBS
#	by David F. Rogers. Copyright (C) 2000 David F. Rogers,
#	All rights reserved.
#
#	Name: rbspline.c
#	Language: C
#	Subroutines called: knot.c, rbasis.c, fmtmul.c
#	Book reference: Chapter 4, Alg. p. 297
#
#    b           = array containing the defining polygon vertices
#                  b[1] contains the x-component of the vertex
#                  b[2] contains the y-component of the vertex
#                  b[3] contains the z-component of the vertex
#    h           = array containing the homogeneous weighting factors
#    k           = order of the B-spline basis function
#    nbasis      = array containing the basis functions for a single value of t
#    nplusc      = number of knot values
#    npts        = number of defining polygon vertices
#    p[,]        = array containing the curve points
#                  p[1] contains the x-component of the point
#                  p[2] contains the y-component of the point
#                  p[3] contains the z-component of the point
#    p1          = number of points to be calculated on the curve
#    t           = parameter value 0 <= t <= npts - k + 1
#    x[]         = array containing the knot vector
# -----------------------------------------------------------------------------
def rbspline(npts, k, p1, b, h, p):
	nplusc = npts + k

	x = [0]*(nplusc+1)
	nbasis = [0.0]*(npts+1)	# zero and redimension the knot vector and the basis array

	# generate the uniform open knot vector
	knot(npts,k,x)

	icount = 0

	# calculate the points on the rational B-spline curve
	t = 0
	step = float(x[nplusc])/float(p1-1)

	for i1 in range(1, p1+1):
		if float(x[nplusc]) - t < 5e-6:
			t = float(x[nplusc])

		# generate the basis function for this value of t
		rbasis(k,t,npts,x,h,nbasis)

		# generate a point on the curve
		for j in range(1, 4):
			jcount = j
			p[icount+j] = 0.0

			# Do local matrix multiplication
			for i in range(1, npts+1):
				p[icount+j] +=  nbasis[i]*b[jcount]
				jcount += 3

		icount += 3
		t += step

# -----------------------------------------------------------------------------
def knotu(num, order, knotVector):
	nplusc = num + order
	knotVector[1] = 0.0
	for i in range(2, nplusc+1):
		knotVector[i] = i-1

# -----------------------------------------------------------------------------
def rbsplinu(npts, k, p1, b, h, p):
	nplusc = npts + k

	x = [0]*(nplusc+1)
	# zero and redimension the knot vector and the basis array
	nbasis = [0.0]*(npts+1)
	# generate the uniform periodic knot vector
	knotu(npts,k,x)
	icount = 0

	# calculate the points on the rational B-spline curve
	t = k-1
	step = (float(npts)-(k-1))/float(p1-1)

	for i1 in range(1, p1+1):
		if float(x[nplusc]) - t < 5e-6:
		    t = float(x[nplusc])

		# generate the basis function for this value of t
		rbasis(k,t,npts,x,h,nbasis)

		# generate a point on the curve
		for j in range(1,4):
			jcount = j
			p[icount+j] = 0.0

			#  Do local matrix multiplication
			for i in range(1,npts+1):
				p[icount+j] += nbasis[i]*b[jcount]
				jcount += 3
		icount += 3
		t += step

# =============================================================================
if __name__ == "__main__":
	from dxf import DXF
#	from dxfwrite.algebra import CubicSpline, CubicBezierCurve
	dxf = DXF(sys.argv[1],"r")
	dxf.readFile()
	dxf.close()
	for name,layer in dxf.layers.items():
		for entity in layer.entities:
			if entity.type == "SPLINE":
				xy = zip(entity[10], entity[20])
				x,y = spline2Polyline(xy, int(entity[71]), True, SPLINE_SEGMENTS)
				for a,b in zip(x,y):
					print a,b
