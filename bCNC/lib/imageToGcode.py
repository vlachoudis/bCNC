#!/usr/bin/python

## image-to-gcode is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by the
## Free Software Foundation; either version 2 of the License, or (at your
## option) any later version.  image-to-gcode is distributed in the hope
## that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
## warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
## the GNU General Public License for more details.  You should have
## received a copy of the GNU General Public License along with image-to-gcode;
## if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
## Fifth Floor, Boston, MA 02110-1301 USA
##
## image-to-gcode.py is Copyright (C) 2005 Chris Radek
## chris@timeguy.com
## image-to-gcode.py is Copyright (C) 2006 Jeff Epler
## jepler@unpy.net

#################################################################################
#                                 image-to-gcode                                #
#################################################################################
from __future__ import absolute_import
import math
import sys
import operator

epsilon = 1e-5
MAXINT = 1000000000


def ball_tool(r,rad):
	s = -math.sqrt(rad**2-r**2)
	return s


def endmill(r,dia, rough_offset=0.0):
	return 0


def vee_common(angle, rough_offset=0.0):
	slope = math.tan(math.pi/2.0 - (angle / 2.0) * math.pi / 180.0)
	def f(r, dia):
		return r * slope
	return f


def make_tool_shape(NUMPY,f, wdia, resp, rough_offset=0.0):
	# resp is pixel size
	res = 1. / resp
	wrad = wdia/2.0 + rough_offset
	rad = int(math.ceil((wrad-resp/2.0)*res))
	if rad < 1: rad = 1
	dia = 2*rad+1

	hdia = rad
	l = []
	for x in range(dia):
		for y in range(dia):
			r = math.hypot(x-hdia, y-hdia) * resp
			if r < wrad:
				z = f(r, wrad)
				l.append(z)

	if NUMPY == True:
		Image_Matrix = Image_Matrix_Numpy
	else:
		Image_Matrix = Image_Matrix_List
	TOOL = Image_Matrix(dia,dia)
	l = []
	temp = []
	for x in range(dia):
		temp.append([])
		for y in range(dia):
			r = math.hypot(x-hdia, y-hdia) * resp
			if r < wrad:
				z = f(r, wrad)
				l.append(z)
				temp[x].append(float(z))
			else:
				temp[x].append(1e100000)
	TOOL.From_List(temp)
	TOOL.minus(TOOL.min()+rough_offset)
	return TOOL


def amax(seq):
	res = 0
	for i in seq:
		if abs(i) > abs(res): res = i
	return res


def group_by_sign(seq, slop=math.sin(math.pi/18), key=lambda x:x):
	sign = None
	subseq = []
	for i in seq:
		ki = key(i)
		if sign is None:
			subseq.append(i)
			if ki != 0:
				sign = ki / abs(ki)
		else:
			subseq.append(i)
			if sign * ki < -slop:
				sign = ki / abs(ki)
				yield subseq
				subseq = [i]
	if subseq: yield subseq


class Convert_Scan_Alternating:
	def __init__(self):
		self.st = 0

	def __call__(self, primary, items):
		st = self.st = self.st + 1
		if st % 2: items.reverse()
		if st == 1: yield True, items
		else: yield False, items

	def reset(self):
		self.st = 0


class Convert_Scan_Increasing:
	def __call__(self, primary, items):
		yield True, items

	def reset(self):
		pass


class Convert_Scan_Decreasing:
	def __call__(self, primary, items):
		items.reverse()
		yield True, items

	def reset(self):
		pass


class Convert_Scan_Upmill:
	def __init__(self, slop = math.sin(math.pi / 18)):
		self.slop = slop

	def __call__(self, primary, items):
		for span in group_by_sign(items, self.slop, operator.itemgetter(2)):
			if amax([it[2] for it in span]) < 0:
				span.reverse()
			yield True, span

	def reset(self):
		pass


class Convert_Scan_Downmill:
	def __init__(self, slop = math.sin(math.pi / 18)):
		self.slop = slop

	def __call__(self, primary, items):
		for span in group_by_sign(items, self.slop, operator.itemgetter(2)):
			if amax([it[2] for it in span]) > 0:
				span.reverse()
			yield True, span

	def reset(self):
		pass


class Reduce_Scan_Lace:
	def __init__(self, converter, slope, keep):
		self.converter = converter
		self.slope = slope
		self.keep = keep

	def __call__(self, primary, items):
		slope = self.slope
		keep = self.keep
		if primary:
			idx = 3
			test = operator.le
		else:
			idx = 2
			test = operator.ge

		def bos(j):
			return j - j % keep

		def eos(j):
			if j % keep == 0: return j
			return j + keep - j%keep

		for i, (flag, span) in enumerate(self.converter(primary, items)):
			subspan = []
			a = None
			for i, si in enumerate(span):
				ki = si[idx]
				if a is None:
					if test(abs(ki), slope):
						a = b = i
				else:
					if test(abs(ki), slope):
						b = i
					else:
						if i - b < keep: continue
						yield True, span[bos(a):eos(b+1)]
						a = None
			if a is not None:
				yield True, span[a:]

	def reset(self):
		self.converter.reset()


#############
class Reduce_Scan_Lace_new:
	def __init__(self, converter, depth, keep):
		self.converter = converter
		self.depth = depth
		self.keep = keep

	def __call__(self, primary, items):
		keep = self.keep
		max_z_cut = self.depth  # set a max z value to cut

		def bos(j):
			return j - j % keep

		def eos(j):
			if j % keep == 0: return j
			return j + keep - j%keep

		for i, (flag, span) in enumerate(self.converter(primary, items)):
			subspan = []
			a = None
			for i, si in enumerate(span):
				ki = si[1]		 # This is (x,y,z)
				z_value   = ki[2]  # Get the z value from ki
				if a is None:
					if z_value < max_z_cut:
						a = b = i
				else:
					if z_value < max_z_cut:
						b = i
					else:
						if i - b < keep: continue
						yield True, span[bos(a):eos(b+1)]
						a = None
			if a is not None:
				yield True, span[a:]

	def reset(self):
		self.converter.reset()
#############


class Converter:
	def __init__(self, BIG, \
			image, units, tool_shape, pixelsize, pixelstep, safetyheight, tolerance,\
				 feed, convert_rows, convert_cols, cols_first_flag, border, entry_cut,\
				 roughing_delta, roughing_feed, xoffset, yoffset, splitstep, header, \
				 postscript, edge_offset, disable_arcs):

		self.BIG = BIG
		self.image = image
		self.units = units
		self.tool_shape = tool_shape
		self.pixelsize = pixelsize
		self.safetyheight = safetyheight
		self.tolerance = tolerance
		self.base_feed = feed
		self.convert_rows = convert_rows
		self.convert_cols = convert_cols
		self.cols_first_flag = cols_first_flag
		self.entry_cut = entry_cut
		self.roughing_delta = roughing_delta
		self.roughing_feed = roughing_feed
		self.header = header
		self.postscript = postscript
		self.border = border
		self.edge_offset = edge_offset
		self.disable_arcs = disable_arcs

		self.xoffset = xoffset
		self.yoffset = yoffset

		# Split step stuff
		splitpixels = 0
		if splitstep > epsilon:
			pixelstep   = int(math.floor(pixelstep * splitstep * 2))
			splitpixels = int(math.floor(pixelstep * splitstep	))
		self.pixelstep   = pixelstep
		self.splitpixels = splitpixels

		self.cache = {}

		w, h = self.w, self.h = image.shape
		self.h1 = h
		self.w1 = w

		###
		row_cnt=0
		cnt_border = 0
		if self.convert_rows != None:
			row_cnt = math.ceil( self.w1 / pixelstep) + 2
		col_cnt = 0
		if self.convert_cols != None:
			col_cnt = math.ceil( self.h1 / pixelstep) + 2
		if self.roughing_delta != 0:
			cnt_mult = math.ceil(self.image.min() / -self.roughing_delta) + 1
		else:
			cnt_mult = 1
		if self.convert_cols != None or self.convert_rows != None:
			cnt_border = 2
		self.cnt_total = (row_cnt + col_cnt + cnt_border )* cnt_mult
		self.cnt = 0.0

	def one_pass(self):
		g = self.g
		g.set_feed(self.feed)

		if self.convert_cols and self.cols_first_flag:
			self.g.set_plane(19)
			self.mill_cols(self.convert_cols, True)
			if self.convert_rows: g.safety()

		if self.convert_rows:
			self.g.set_plane(18)
			self.mill_rows(self.convert_rows, not self.cols_first_flag)

		if self.convert_cols and not self.cols_first_flag:
			self.g.set_plane(19)
			if self.convert_rows: g.safety()
			self.mill_cols(self.convert_cols, not self.convert_rows)

		g.safety()

		## mill border ##
		if self.convert_cols:
			self.convert_cols.reset()
		if self.convert_rows:
			self.convert_rows.reset()

		step_save = self.pixelstep
		self.pixelstep = max(self.w1, self.h1) + 1
		if self.border == 1 and not self.convert_rows:
			if self.convert_cols:
				self.g.set_plane(18)
				self.mill_rows(self.convert_cols, True)
				g.safety()

		if self.border == 1 and not self.convert_cols:
			if self.convert_rows:
				self.g.set_plane(19)
				self.mill_cols(self.convert_rows, True)
				g.safety()
		self.pixelstep = step_save

		if self.convert_cols:
			self.convert_cols.reset()
		if self.convert_rows:
			self.convert_rows.reset()

		g.safety()

	def convert(self):
		output_gcode = []
		self.g = g = Gcode(safetyheight=self.safetyheight,
						   tolerance=self.tolerance,
						   units=self.units,
						   header=self.header,
						   postscript=self.postscript,
						   target=lambda s: output_gcode.append(s),
						   disable_arcs = self.disable_arcs)
		g.begin()
		#g.continuous(self.tolerance) #commented V0.7
		g.safety()

		if self.roughing_delta:
			##########################################
			self.feed = self.roughing_feed
			r = -self.roughing_delta
			m = self.image.min()
			while r > m:
				self.rd = r
				self.one_pass()
				r = r - self.roughing_delta
			if r < m + epsilon:
				self.rd = m
				self.one_pass()
			##########################################
		else:
			self.feed = self.base_feed
			self.rd = self.image.min()
			self.one_pass()
			##########################################
		g.end()
		return output_gcode

	def get_z(self, x, y):
		try:
			return min(0, max(self.rd, self.cache[x,y]))
		except KeyError:
			self.cache[x,y] = d = self.image.height_calc(x,y,self.tool_shape)
			return min(0.0, max(self.rd, d))

	def get_dz_dy(self, x, y):
		y1 = max(0, y-1)
		y2 = min(self.image.shape[0]-1, y+1)
		dy = self.pixelsize * (y2-y1)
		return (self.get_z(x, y2) - self.get_z(x, y1)) / dy

	def get_dz_dx(self, x, y):
		x1 = max(0, x-1)
		x2 = min(self.image.shape[1]-1, x+1)
		dx = self.pixelsize * (x2-x1)
		return (self.get_z(x2, y) - self.get_z(x1, y)) / dx

	def frange(self,start, stop, step):
		out = []
		i = start
		while i < stop:
			out.append(i)
			i += step
		return out

	def mill_rows(self, convert_scan, primary):
		global STOP_CALC
		w1 = self.w1
		h1 = self.h1
		pixelsize = self.pixelsize
		pixelstep = self.pixelstep
		pixel_offset = int(math.ceil(self.edge_offset / pixelsize))
		jrange = self.frange(self.splitpixels+pixel_offset, w1-pixel_offset, pixelstep)
		if jrange[0] != pixel_offset: jrange.insert(0,pixel_offset)
		if w1-1-pixel_offset not in jrange: jrange.append(w1-1-pixel_offset)

		irange = range(pixel_offset,h1-pixel_offset)

		for j in jrange:
			self.cnt = self.cnt+1
			#progress(self.cnt, self.cnt_total, self.START_TIME, self.BIG )
			y = (w1-j-1) * pixelsize + self.yoffset
			scan = []
			for i in irange:
				self.BIG.update()
				#if STOP_CALC: return
				x = i * pixelsize + self.xoffset
				milldata = (i, (x, y, self.get_z(i, j)),
							self.get_dz_dx(i, j), self.get_dz_dy(i, j))
				scan.append(milldata)
			for flag, points in convert_scan(primary, scan):
				if flag:
					self.entry_cut(self, points[0][0], j, points)
				for p in points:
					self.g.cut(*p[1])
			self.g.flush()



	def mill_cols(self, convert_scan, primary):
		global STOP_CALC
		w1 = self.w1
		h1 = self.h1
		pixelsize = self.pixelsize
		pixelstep = self.pixelstep
		pixel_offset = int(math.ceil(self.edge_offset / pixelsize))
		jrange = self.frange(self.splitpixels+pixel_offset, h1-pixel_offset, pixelstep)
		if jrange[0] != pixel_offset: jrange.insert(0,pixel_offset)
		if h1-1-pixel_offset not in jrange: jrange.append(h1-1-pixel_offset)

		irange = range(pixel_offset,w1-pixel_offset)

		if h1-1-pixel_offset not in jrange: jrange.append(h1-1-pixel_offset)
		jrange.reverse()

		for j in jrange:
			self.cnt = self.cnt+1
			#progress(self.cnt, self.cnt_total, self.START_TIME, self.BIG )
			x = j * pixelsize + self.xoffset
			scan = []
			for i in irange:
				self.BIG.update()
				#if STOP_CALC: return
				y = (w1-i-1) * pixelsize + self.yoffset
				milldata = (i, (x, y, self.get_z(j, i)),
							self.get_dz_dy(j, i), self.get_dz_dx(j, i))
				scan.append(milldata)
			for flag, points in convert_scan(primary, scan):
				if flag:
					self.entry_cut(self, j, points[0][0], points)
				for p in points:
					self.g.cut(*p[1])
			self.g.flush()


def convert(*args, **kw):
	return Converter(*args, **kw).convert()


class SimpleEntryCut:
	def __init__(self, feed):
		self.feed = feed

	def __call__(self, conv, i0, j0, points):
		p = points[0][1]
		if self.feed:
			conv.g.set_feed(self.feed)
		conv.g.safety()
		conv.g.rapid(p[0], p[1])
		if self.feed:
			conv.g.set_feed(conv.feed)


# Calculate the portion of the arc to do so that none is above the
# safety height (that's just silly)
def circ(r,b):
	z = r**2 - (r-b)**2
	if z < 0: z = 0
	return z**.5


class ArcEntryCut:
	def __init__(self, feed, max_radius):
		self.feed = feed
		self.max_radius = max_radius

	def __call__(self, conv, i0, j0, points):
		if len(points) < 2:
			p = points[0][1]
			if self.feed:
				conv.g.set_feed(self.feed)
			conv.g.safety()
			conv.g.rapid(p[0], p[1])
			if self.feed:
				conv.g.set_feed(conv.feed)
			return

		p1 = points[0][1]
		p2 = points[1][1]
		z0 = p1[2]

		lim = int(math.ceil(self.max_radius / conv.pixelsize))
		r = range(1, lim)

		if self.feed:
			conv.g.set_feed(self.feed)
		conv.g.safety()

		x, y, z = p1

		pixelsize = conv.pixelsize

		cx = cmp(p1[0], p2[0])
		cy = cmp(p1[1], p2[1])

		radius = self.max_radius

		if cx != 0:
			h1 = conv.h1
			for di in r:
				dx = di * pixelsize
				i = i0 + cx * di
				if i < 0 or i >= h1: break
				z1 = conv.get_z(i, j0)
				dz = (z1 - z0)
				if dz <= 0: continue
				if dz > dx:
					conv.g.write("(case 1)")
					radius = dx
					break
				rad1 = (dx * dx / dz + dz) / 2
				if rad1 < radius:
					radius = rad1
				if dx > radius:
					break

			z1 = min(p1[2] + radius, conv.safetyheight)

			x1 = p1[0] + cx * circ(radius, z1 - p1[2])
			conv.g.rapid(x1, p1[1])
			conv.g.cut(z=z1)

			I = - cx * circ(radius, z1 - p1[2])
			K = (p1[2] + radius) - z1

			conv.g.flush(); conv.g.lastgcode = None
			if cx > 0:
				#conv.g.write("G3 X%f Z%f R%f" % (p1[0], p1[2], radius)) #G3
				conv.g.write("G3 X%f Z%f I%f K%f" % (p1[0], p1[2], I, K))
			else:
				#conv.g.write("G2 X%f Z%f R%f" % (p1[0], p1[2], radius)) #G2
				conv.g.write("G2 X%f Z%f I%f K%f" % (p1[0], p1[2], I, K))

			conv.g.lastx = p1[0]
			conv.g.lasty = p1[1]
			conv.g.lastz = p1[2]
		else:
			w1 = conv.w1
			for dj in r:
				dy = dj * pixelsize
				j = j0 - cy * dj
				if j < 0 or j >= w1: break
				z1 = conv.get_z(i0, j)
				dz = (z1 - z0)
				if dz <= 0: continue
				if dz > dy:
					radius = dy
					break
				rad1 = (dy * dy / dz + dz) / 2
				if rad1 < radius: radius = rad1
				if dy > radius: break

			z1 = min(p1[2] + radius, conv.safetyheight)
			y1 = p1[1] + cy * circ(radius, z1 - p1[2])
			conv.g.rapid(p1[0], y1)
			conv.g.cut(z=z1)

			J =  -cy * circ(radius, z1 - p1[2])
			K = (p1[2] + radius) - z1

			conv.g.flush(); conv.g.lastgcode = None
			if cy > 0:
				#conv.g.write("G2 Y%f Z%f R%f" % (p1[1], p1[2], radius)) #G2
				conv.g.write("G2 Y%f Z%f J%f K%f" % (p1[1], p1[2], J, K))
			else:
				#conv.g.write("G3 Y%f Z%f R%f" % (p1[1], p1[2], radius)) #G3
				conv.g.write("G3 Y%f Z%f J%f K%f" % (p1[1], p1[2], J, K))
			conv.g.lastx = p1[0]
			conv.g.lasty = p1[1]
			conv.g.lastz = p1[2]
		if self.feed:
			conv.g.set_feed(conv.feed)


class Image_Matrix_List: #Nested list (no Numpy)
	def __init__(self, width=0, height=0):
		self.width  = width
		self.height = height
		self.matrix = []
		self.shape  = [width, height]

	def __call__(self,i,j):
		return self.matrix[i][j]

	def Assign(self,i,j,val):
		self.matrix[i][j] = float(val)

	def From_List(self,input_list):
		s = len(input_list)
		self.width  = s
		self.height = s

		for x in range(s):
			self.api()
			for y in range(s):
				self.apj(x,float(input_list[x][y]))


	def FromImage(self, im, pil_format):
		global STOP_CALC
		self.matrix = []

		if pil_format:
			him,wim = im.size
			for i in range(0,wim):
				self.api()
				for j in range(0,him):
					pix = im.getpixel((j,i))
					self.apj(i,pix)

		else:
			him = im.width()
			wim = im.height()
			for i in range(0,wim):
				self.api()
				for j in range(0,him):
					try:	pix = im.get(j,i).split()
					except: pix = im.get(j,i)
					self.apj(i,pix[0])

		self.width  = wim
		self.height = him
		self.shape  = [wim, him]
		self.t_offset = 0


	def pad_w_zeros(self,tool):
		ts = tool.width
		for i in range(len(self.matrix),self.width+ts):
			self.api()

		for i in range(0,len(self.matrix)):
			for j in range(len(self.matrix[i]),self.height+ts):
				self.apj(i,-1e1000000)

	def height_calc(self,x,y,tool):
		ts = tool.width
		d = -1e1000000
		ilow  = (int)(x-(ts-1)/2)
		ihigh = (int)(x+(ts-1)/2+1)
		jlow  = (int)(y-(ts-1)/2)
		jhigh = (int)(y+(ts-1)/2+1)

		icnt = 0
		for i in range( ilow , ihigh):
			jcnt = 0
			for j in range( jlow , jhigh):
				d = max( d, self(j,i) - tool(jcnt,icnt))
				jcnt = jcnt+1
			icnt = icnt+1
		return d

	def min(self):
		minval = 1e1000000
		for i in range(0,self.width):
			for j in range(0,self.height):
				minval = min(minval,self.matrix[i][j])
		return minval

	def max(self):
		maxval = -1e1000000
		for i in range(0,self.width):
			for j in range(0,self.height):
				maxval = max(maxval,self.matrix[i][j])
		return maxval

	def api(self):
		self.matrix.append([])

	def apj(self,i,val):
		fval = float(val)
		self.matrix[i].append(fval)

	def mult(self,val):
		fval = float(val)
		icnt=0
		for i in self.matrix:
			jcnt = 0
			for j in i:
				self.matrix[icnt][jcnt] = fval * j
				jcnt = jcnt + 1
			icnt=icnt+1

	def minus(self,val):
		fval = float(val)
		icnt=0
		for i in self.matrix:
			jcnt = 0
			for j in i:
				self.matrix[icnt][jcnt] = j - fval
				jcnt = jcnt + 1
			icnt=icnt+1


class Image_Matrix_Numpy:
	def __init__(self, width=2, height=2):
		import numpy
		self.width  = width
		self.height = height
		self.matrix = numpy.zeros((width, height), 'Float32')
		self.shape  = [width, height]
		self.t_offset = 0

	def __call__(self,i,j):
		return self.matrix[i+self.t_offset,j+self.t_offset]

	def Assign(self,i,j,val):
		fval=float(val)
		self.matrix[i+self.t_offset,j+self.t_offset]=fval

	def From_List(self,input_list):
		import numpy
		s = len(input_list)
		self.width  = s
		self.height = s

		self.matrix = numpy.zeros((s, s), 'Float32')
		for x in range(s):
			for y in range(s):
				self.matrix[x,y]=float(input_list[x][y])

	def FromImage(self, im, pil_format):
		import numpy
		global STOP_CALC
		self.matrix = []

		if pil_format:
			him,wim = im.size
			self.matrix = numpy.zeros((wim, him), 'Float32')
			for i in range(0,wim):
				for j in range(0,him):
					pix = im.getpixel((j,i))
					self.matrix[i,j] = float(pix)
		else:
			him = im.width()
			wim = im.height()
			self.matrix = numpy.zeros((wim, him), 'Float32')
			for i in range(0,wim):
				for j in range(0,him):
					try:	pix = im.get(j,i).split()
					except: pix = im.get(j,i)
					self.matrix[i,j] = float(pix[0])

		self.width  = wim
		self.height = him
		self.shape  = [wim, him]
		self.t_offset = 0

	def pad_w_zeros(self,tool):
		import numpy
		ts = tool.width
		self.t_offset = (ts-1)/2
		to = self.t_offset

		w, h = self.shape
		w1 = w + ts-1
		h1 = h + ts-1
		temp = numpy.zeros((w1, h1), 'Float32')
		for j in range(0, w1):
			for i in range(0, h1):
				temp[j,i] = -1e1000000
		temp[to:to+w, to:to+h] = self.matrix
		self.matrix = temp

	def height_calc(self,x,y,tool):
		to = self.t_offset
		ts = tool.width
		d= -1e100000
		m1 = self.matrix[y:y+ts, x:x+ts]
		d = (m1 - tool.matrix).max()
		return d

	def min(self):
		return self.matrix[self.t_offset:self.t_offset+self.width,
							  self.t_offset:self.t_offset+self.height].min()

	def max(self):
		return self.matrix[self.t_offset:self.t_offset+self.width,
							  self.t_offset:self.t_offset+self.height].max()

	def mult(self,val):
		self.matrix = self.matrix * float(val)

	def minus(self,val):
		self.matrix = self.matrix - float(val)


################################################################################
#             Author.py                                                        #
#             A component of emc2                                              #
################################################################################


# Compute the 3D distance from the line segment l1..l2 to the point p.
# (Those are lower case L1 and L2)
def dist_lseg(l1, l2, p):
    x0, y0, z0 = l1
    xa, ya, za = l2
    xi, yi, zi = p

    dx = xa-x0
    dy = ya-y0
    dz = za-z0
    d2 = dx*dx + dy*dy + dz*dz

    if d2 == 0: return 0

    t = (dx * (xi-x0) + dy * (yi-y0) + dz * (zi-z0)) / d2
    if t < 0: t = 0
    if t > 1: t = 1
    dist2 = (xi - x0 - t*dx)**2 + (yi - y0 - t*dy)**2 + (zi - z0 - t*dz)**2

    return dist2 ** .5


def rad1(x1,y1,x2,y2,x3,y3):
    x12 = x1-x2
    y12 = y1-y2
    x23 = x2-x3
    y23 = y2-y3
    x31 = x3-x1
    y31 = y3-y1

    den = abs(x12 * y23 - x23 * y12)
    if abs(den) < 1e-5: return MAXINT
    return math.hypot(float(x12), float(y12)) * math.hypot(float(x23), float(y23)) * math.hypot(float(x31), float(y31)) / 2 / den


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self): return "<%f,%f>" % (self.x, self.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __mul__(self, other):
        return Point(self.x * other, self.y * other)
    __rmul__ = __mul__

    def cross(self, other):
        return self.x * other.y - self.y * other.x

    def dot(self, other):
        return self.x * other.x + self.y * other.y

    def mag(self):
        return math.hypot(self.x, self.y)

    def mag2(self):
        return self.x**2 + self.y**2


def cent1(x1,y1,x2,y2,x3,y3):
    P1 = Point(x1,y1)
    P2 = Point(x2,y2)
    P3 = Point(x3,y3)

    den = abs((P1-P2).cross(P2-P3))
    if abs(den) < 1e-5: return MAXINT, MAXINT

    alpha = (P2-P3).mag2() * (P1-P2).dot(P1-P3) / 2 / den / den
    beta  = (P1-P3).mag2() * (P2-P1).dot(P2-P3) / 2 / den / den
    gamma = (P1-P2).mag2() * (P3-P1).dot(P3-P2) / 2 / den / den

    Pc = alpha * P1 + beta * P2 + gamma * P3
    return Pc.x, Pc.y


def arc_center(plane, p1, p2, p3):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    x3, y3, z3 = p3

    if plane == 17: return cent1(x1,y1,x2,y2,x3,y3)
    if plane == 18: return cent1(x1,z1,x2,z2,x3,z3)
    if plane == 19: return cent1(y1,z1,y2,z2,y3,z3)


def arc_rad(plane, P1, P2, P3):
    if plane is None: return MAXINT

    x1, y1, z1 = P1
    x2, y2, z2 = P2
    x3, y3, z3 = P3

    if plane == 17: return rad1(x1,y1,x2,y2,x3,y3)
    if plane == 18: return rad1(x1,z1,x2,z2,x3,z3)
    if plane == 19: return rad1(y1,z1,y2,z2,y3,z3)
    return None, 0


def get_pts(plane, x,y,z):
    if plane == 17: return x,y
    if plane == 18: return x,z
    if plane == 19: return y,z


def one_quadrant(plane, c, p1, p2, p3):
    xc, yc = c
    x1, y1 = get_pts(plane, p1[0],p1[1],p1[2])
    x2, y2 = get_pts(plane, p2[0],p2[1],p2[2])
    x3, y3 = get_pts(plane, p3[0],p3[1],p3[2])

    def sign(x):
        if abs(x) < 1e-5: return 0
        if x < 0: return -1
        return 1

    signs = set((
        (sign(x1-xc),sign(y1-yc)),
        (sign(x2-xc),sign(y2-yc)),
        (sign(x3-xc),sign(y3-yc))
    ))

    if len(signs) == 1: return True

    if (1,1) in signs:
        signs.discard((1,0))
        signs.discard((0,1))
    if (1,-1) in signs:
        signs.discard((1,0))
        signs.discard((0,-1))
    if (-1,1) in signs:
        signs.discard((-1,0))
        signs.discard((0,1))
    if (-1,-1) in signs:
        signs.discard((-1,0))
        signs.discard((0,-1))

    if len(signs) == 1: return True


def arc_dir(plane, c, p1, p2, p3):
    xc, yc = c
    x1, y1 = get_pts(plane, p1[0],p1[1],p1[2])
    x2, y2 = get_pts(plane, p2[0],p2[1],p2[2])
    x3, y3 = get_pts(plane, p3[0],p3[1],p3[2])

    theta_start = math.atan2(y1-yc, x1-xc)
    theta_mid = math.atan2(y2-yc, x2-xc)
    theta_end = math.atan2(y3-yc, x3-xc)

    if theta_mid < theta_start:
        theta_mid = theta_mid + 2 * math.pi
    while theta_end < theta_mid:
        theta_end = theta_end + 2 * math.pi

    return theta_end < 2 * math.pi


def arc_fmt(plane, c1, c2, p1):
    x, y, z = p1
    if plane == 17: return "I%.4f J%.4f" % (c1-x, c2-y)
    if plane == 18: return "I%.4f K%.4f" % (c1-x, c2-z)
    if plane == 19: return "J%.4f K%.4f" % (c1-y, c2-z)


# Perform Douglas-Peucker simplification on the path 'st' with the specified
# tolerance.  The '_first' argument is for internal use only.
#
# The Douglas-Peucker simplification algorithm finds a subset of the input points
# whose path is never more than 'tolerance' away from the original input path.
#
# If 'plane' is specified as 17, 18, or 19, it may find helical arcs in the given
# plane in addition to lines.  Note that if there is movement in the plane
# perpendicular to the arc, it will be distorted, so 'plane' should usually
# be specified only when there is only movement on 2 axes
def douglas(st, tolerance=.001, plane=None, _first=True):
    if len(st) == 1:
        yield "G1", st[0], None
        return

    l1 = st[0]
    l2 = st[-1]

    worst_dist = 0
    worst = 0
    min_rad = MAXINT
    max_arc = -1

    ps = st[0]
    pe = st[-1]

    for i, p in enumerate(st):
        if p is l1 or p is l2: continue
        dist = dist_lseg(l1, l2, p)
        if dist > worst_dist:
            worst = i
            worst_dist = dist
            rad = arc_rad(plane, ps, p, pe)
            if rad < min_rad:
                max_arc = i
                min_rad = rad

            worst_arc_dist = 0
    if min_rad != MAXINT:
        c1, c2 = arc_center(plane, ps, st[max_arc], pe)
        lx, ly, lz = st[0]
        if one_quadrant(plane, (c1, c2), ps, st[max_arc], pe):
            for i, (x,y,z) in enumerate(st):
                if plane == 17: dist = abs(math.hypot(c1-x, c2-y) - min_rad)
                elif plane == 18: dist = abs(math.hypot(c1-x, c2-z) - min_rad)
                elif plane == 19: dist = abs(math.hypot(c1-y, c2-z) - min_rad)
                else: dist = MAXINT
                if dist > worst_arc_dist: worst_arc_dist = dist

                mx = (x+lx)/2
                my = (y+ly)/2
                mz = (z+lz)/2
                if plane == 17: dist = abs(math.hypot(c1-mx, c2-my) - min_rad)
                elif plane == 18: dist = abs(math.hypot(c1-mx, c2-mz) - min_rad)
                elif plane == 19: dist = abs(math.hypot(c1-my, c2-mz) - min_rad)
                else: dist = MAXINT
                lx, ly, lz = x, y, z
        else:
            worst_arc_dist = MAXINT
    else:
        worst_arc_dist = MAXINT

    if worst_arc_dist < tolerance and worst_arc_dist < worst_dist:
        ccw = arc_dir(plane, (c1, c2), ps, st[max_arc], pe)
        if plane == 18: ccw = not ccw
        yield "G1", ps, None
        if ccw:
            yield "G3", st[-1], arc_fmt(plane, c1, c2, ps)
        else:
            yield "G2", st[-1], arc_fmt(plane, c1, c2, ps)
    elif worst_dist > tolerance:
        if _first: yield "G1", st[0], None
        for i in douglas(st[:worst+1], tolerance, plane, False):
            yield i
        yield "G1", st[worst], None
        for i in douglas(st[worst:], tolerance, plane, False):
            yield i
        if _first: yield "G1", st[-1], None
    else:
        if _first: yield "G1", st[0], None
        if _first: yield "G1", st[-1], None


# For creating rs274ngc files
class Gcode:
	def __init__(self, homeheight = 1.5, safetyheight = 0.04,
				 tolerance=0.001, units="G20", header="", postscript="",
				 target=lambda s: sys.stdout.write(s + "\n"),
				 disable_arcs = False):
		self.lastx = self.lasty = self.lastz = self.lasta = None
		self.lastgcode = self.lastfeed = None
		self.homeheight = homeheight
		self.safetyheight = self.lastz = safetyheight
		self.tolerance = tolerance
		self.units = units
		self.cuts = []
		self.write = target
		self.time = 0
		self.plane = None
		self.header = header
		self.postscript = postscript
		self.disable_arcs = disable_arcs

	def set_plane(self, p):
		if (not self.disable_arcs):
			assert p in (17,18,19)
			if p != self.plane:
				self.plane = p
				self.write("G%d" % p)

	# This function write header and move to safety height
	def begin(self):
		self.write(self.header)
		#self.write(self.units)
		if not self.disable_arcs:
			self.write("G91.1")

		#self.safety()
		#self.rapid(z=self.safetyheight)
		self.write("G0 Z%.4f" % (self.safetyheight))
		#["G17 G40","G80 G90 G94 G91.1"]

	# If any 'cut' moves are stored up, send them to the simplification algorithm
	# and actually output them.
	#
	# This function is usually used internally (e.g., when changing from a cut
	# to a rapid) but can be called manually as well.  For instance, when
	# a contouring program reaches the end of a row, it may be desirable to enforce
	# that the last 'cut' coordinate is actually in the output file, and it may
	# give better performance because this means that the simplification algorithm
	# will examine fewer points per run.
	def flush(self):
		if not self.cuts: return
		for move, (x, y, z), cent in douglas(self.cuts, self.tolerance, self.plane):
			if cent:
				self.write("%s X%.4f Y%.4f Z%.4f %s" % (move, x, y, z, cent))
				self.lastgcode = None
				self.lastx = x
				self.lasty = y
				self.lastz = z
			else:
				self.move_common(x, y, z, gcode="G1")
		self.cuts = []

	def end(self):
		#"""End the program"""
		self.flush()
		self.safety()
		self.write(self.postscript)

	#    """\
	#Set exact path mode.  Note that unless self.tolerance is set to zero,
	#the simplification algorithm may still skip over specified points."""
	#def exactpath(self):
	#    self.write("G61")

	# Set continuous mode.
	#def continuous(self, tolerance=0.0):       #commented V0.7
	#    if tolerance > 0.0:                    #commented V0.7
	#        self.write("G64 P%.4f" % tolerance)#commented V0.7
	#    else:                                  #commented V0.7
	#        self.write("G64")                  #commented V0.7

	def rapid(self, x=None, y=None, z=None, a=None):
		#"Perform a rapid move to the specified coordinates"
		self.flush()
		self.move_common(x, y, z, a, "G0")

	def move_common(self, x=None, y=None, z=None, a=None, gcode="G0"):
		#"An internal function used for G0 and G1 moves"
		gcodestring = xstring = ystring = zstring = astring = ""
		if x == None: x = self.lastx
		if y == None: y = self.lasty
		if z == None: z = self.lastz
		if a == None: a = self.lasta
		if x != self.lastx:
				xstring = " X%.4f" % (x)
				self.lastx = x
		if y != self.lasty:
				ystring = " Y%.4f" % (y)
				self.lasty = y
		if z != self.lastz:
				zstring = " Z%.4f" % (z)
				self.lastz = z
		if a != self.lasta:
				astring = " A%.4f" % (a)
				self.lasta = a
		if xstring == ystring == zstring == astring == "":
			return
		if gcode != self.lastgcode:
				gcodestring = gcode
				self.lastgcode = gcode
		cmd = "".join([gcodestring, xstring, ystring, zstring, astring])
		if cmd:
			self.write(cmd)

	def set_feed(self, feed):
		#"Set the feed rate to the given value"
		self.flush()
		self.write("F%.4f" % feed)

	def cut(self, x=None, y=None, z=None):
		#"Perform a cutting move at the specified feed rate to the specified coordinates"
		if self.cuts:
			lastx, lasty, lastz = self.cuts[-1]
		else:
			lastx, lasty, lastz = self.lastx, self.lasty, self.lastz
		if x is None: x = lastx
		if y is None: y = lasty
		if z is None: z = lastz
		self.cuts.append([x,y,z])

	def home(self):
		#"Go to the 'home' height at rapid speed"
		self.flush()
		self.rapid(z=self.homeheight)

	def safety(self):
		#"Go to the 'safety' height at rapid speed"
		self.flush()
		self.rapid(z=self.safetyheight)
