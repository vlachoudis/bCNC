#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	20-Aug-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Box")

import math
from bmath import *

from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
# Create a box with finger joints
#==============================================================================
class Box:
	def __init__(self, dx=100., dy=50., dz=25.):
		self.name = "Box"
		self.dx = dx
		self.dy = dy
		self.dz = dz

		self.nx = 3
		self.ny = 3
		self.nz = 3

		self.overcut   = 'D'	# Cut additional holes to compensate
					# round edges from cutter
					# D=diagonal, V=vertical, H=horizontal(doesn't work)
		self.overcutAdd = 0.05	# Add 5% of the tool diameter

		self.surface = 0.	# location of surface
		self.thick   = 5.	# thickness of material (and finger)
		self.tool    = 3.175
		self.safe    = 3.
		self.stepz   = 1.0
		self.feedz   = 500
		self.feed    = 1200
		self.digits  = 4
		self.cut     = True

	#----------------------------------------------------------------------
	def init(self):
		self.r = self.tool/2.0

	#----------------------------------------------------------------------
	def setTool(self, t):
		self.tool = t
		self.init()

	#----------------------------------------------------------------------
	# Set number of tooth's (use odd values)
	#----------------------------------------------------------------------
	def setNTeeth(self, nx, ny, nz):
		if nx > 0:
			self.nx = int(nx)
		else:
			self.nx = int(round(self.dx/nx))

		if ny > 0:
			self.ny = int(ny)
		else:
			self.ny = int(round(self.dy/ny))

		if ny > 0:
			self.nz = int(nz)
		else:
			self.nz = int(round(self.dz/nz))

		if self.nx&1==0: self.nx += 1	# Works only with odd numbers for the moment
		if self.ny&1==0: self.ny += 1
		if self.nz&1==0: self.nz += 1

	#----------------------------------------------------------------------
	# Draw a zig zag line
	# @param pos	starting position
	# @param lstep	longitudinal step
	# @param tstep	transverse step
	# @param n	number of steps
	#----------------------------------------------------------------------
	def zigZagLine(self, block, pos, du, dv, U, V, n, extra=0.):
		sgn = math.copysign(1.0, n)
		n   = abs(n)

		# Make additional overcut/cuts to compensate for the
		# round edges in the inner teeth
		if self.r > 0.0:
			overcut = self.overcut
			#rd = (sqrt(2.)-1.0) * self.r
			rd = (1.0-1.0/sqrt(2.)) * (1.0+self.overcutAdd) * self.r
		else:
			overcut = None

		for i in range(n):
#			if sgn<0.0 and overcut=="U":
#				pos -= self.r*U
#				block.append(CNC.glinev(1, pos, self.feed))
#				pos += self.r*U
#				block.append(CNC.glinev(1, pos))

			x = du
			if sgn<0.0 and n>1:
				if 0 < i < n-1:
					x -= 2*self.r
				else:
					x -= self.r
			if i==0:
				x += extra
			elif i==n-1:
				x += extra

			pos += x*U


			if i==0:
				block.append(CNC.glinev(1, pos, self.feed))
			else:
				block.append(CNC.glinev(1, pos))

#			if sgn<0.0 and overcut=="U":
#				pos += self.r*U
#				block.append(CNC.glinev(1, pos))
#				pos -= self.r*U
#				block.append(CNC.glinev(1, pos))

			if self.r>0.0:
				if sgn<0.0:
					if i<n-1:
						if overcut == "V":
							pos -= sgn*self.r*V
							block.append(CNC.glinev(1, pos))
							pos += sgn*dv*V
						elif overcut == "D":
							pos -= sgn*rd*(U+V)
							block.append(CNC.glinev(1, pos))
							pos += sgn*rd*(U+V)
							block.append(CNC.glinev(1, pos))
							pos += sgn*(dv-self.r)*V
						else:
							pos += sgn*(dv-self.r)*V
						block.append(CNC.glinev(1, pos))
						ijk = self.r*U
						pos += sgn*self.r*V + self.r*U
						block.append(CNC.garcv(3, pos, ijk))
					else:
						# ending
						ijk = self.r*V
						pos += self.r*V + self.r*U
						block.append(CNC.garcv(3, pos, ijk))

				elif sgn>0.0:
					ijk = sgn*self.r*V
					pos += sgn*self.r*V + self.r*U
					block.append(CNC.garcv(3, pos, ijk))
					if i<n-1:
						if overcut == "V":
							pos += sgn*dv*V
							block.append(CNC.glinev(1, pos))
							if self.r > 0.0:
								pos -= sgn*self.r*V
								block.append(CNC.glinev(1, pos))
						elif overcut == "D":
							pos += sgn*(dv-self.r)*V
							block.append(CNC.glinev(1, pos))
							if self.r > 0.0:
								pos -= sgn*rd*(U-V)
								block.append(CNC.glinev(1, pos))
								pos += sgn*rd*(U-V)
								block.append(CNC.glinev(1, pos))
						else:
							pos += sgn*(dv-self.r)*V
							block.append(CNC.glinev(1, pos))

			elif i<n-1:
				pos += sgn*dv*V
				block.append(CNC.glinev(1, pos))
			sgn = -sgn

		return pos

	#----------------------------------------------------------------------
	# @param x0,y0		starting position
	# @param dx,dyz		width/height of box (if negative inside, positive outside)
	# @param nx,ny		number of teeth (negative to start from internal, positive for external)
	# @param ex,ey		additional space for x and y not included in the sx/y calculation
	#----------------------------------------------------------------------
	def _rectangle(self, block, x0, y0, dx, dy, nx, ny, ex=0., ey=0.):
		block.append("(  Location: %g,%g )"%(x0,y0))
		block.append("(  Dimensions: %g,%g )"%(dx,dy))
		block.append("(  Teeth: %d,%d )"%(nx,ny))
		block.append("(  Tool diameter: %g )"%(self.tool))

		# Start with full length
		sx = dx / abs(nx)
		sy = dy / abs(ny)

		# Bottom
		pos = Vector(x0, y0, self.surface)
		pos -= self.r*Vector.Y	# r*V
		block.append(CNC.gcode(0, zip("XY",pos[:2])))

		z = self.surface
		#for z in frange(self.surface-self.stepz, self.surface-self.thick, -self.stepz):
		last = False
		while True:
			if self.cut:
				z -= self.stepz
				if z <= self.surface - self.thick:
					z = self.surface - self.thick
					last = True
			else:
				last = True

			pos[2] = z

			# Penetrate
			block.append(CNC.zenter(pos[2]))

			# Bottom
			pos = self.zigZagLine(block, pos, sx, self.thick, Vector.X, Vector.Y, nx, ex)
			block.append("")

			# Right
			pos = self.zigZagLine(block, pos, sy, self.thick, Vector.Y, -Vector.X, ny, ey)
			block.append("")

			# Top
			pos = self.zigZagLine(block, pos, sx, self.thick, -Vector.X, -Vector.Y, nx, ex)
			block.append("")

			# Right
			pos = self.zigZagLine(block, pos, sy, self.thick, -Vector.Y, Vector.X, ny, ey)
			block.append("")
			if last: break

		# Bring to safe height
		block.append(CNC.zsafe())

	#----------------------------------------------------------------------
	# create all 6 sides of box
	#----------------------------------------------------------------------
	def make(self):
		d = self.thick

		# Convert to external dimensions
		if self.dx<0:
			dx = -self.dx - d*2	# external to internal
		else:
			dx = self.dx

		if self.dy<0:
			dy = -self.dy - d*2	# external to internal
		else:
			dy = self.dy

		if self.dz<0:
			dz = -self.dz - d*2	# external to internal
		else:
			dz = self.dz

		blocks = []
		block = Block("%s-Bottom"%(self.name))
		block.append("(Box: %g x %g x %g)"%(self.dx,self.dy,self.dz))
		block.append("(Fingers: %d x %d x %d)"%(self.nx,self.ny,self.nz))
		self._rectangle(block, 0.,-d, dx,dy, self.nx,-self.ny, 0,d)
		blocks.append(block)

		block = Block("%s-Left"%(self.name))
		self._rectangle(block, -(dz+5*d),-d, dz,dy, self.nz,self.ny, d,d)
		blocks.append(block)

		block = Block("%s-Right"%(self.name))
		self._rectangle(block, dx+3*d,-d, dz,dy, self.nz,self.ny, d,d)
		blocks.append(block)

		block = Block("%s-Front"%(self.name))
		self._rectangle(block, 0,-(dz+4*d), dx,dz, -self.nx,-self.nz, 0,0)
		blocks.append(block)

		block = Block("%s-Back"%(self.name))
		self._rectangle(block, 0,dy+4*d, dx,dz, -self.nx,-self.nz, 0,0)
		blocks.append(block)

		block = Block("%s-Top"%(self.name))
		self._rectangle(block, dx+dz+8*d,-d, dx,dy, self.nx,-self.ny, 0,d)
		blocks.append(block)
		return blocks

#==============================================================================
# Create a BOX
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Generate a finger box")
	def __init__(self, master):
		Plugin.__init__(self, master, "Box")
		self.icon  = "box"
		self.group = "Generator"
		self.variables = [
			("name",      "db",    "", _("Name")),
			("internal","bool",     1, _("Internal Dimensions")),
			("dx",        "mm", 100.0, _("Width Dx")),
			("dy",        "mm",  70.0, _("Depth Dy")),
			("dz",        "mm",  50.0, _("Height Dz")),
			("nx",       "int",    11, _("Fingers Nx")),
			("ny",       "int",     7, _("Fingers Ny")),
			("nz",       "int",     5, _("Fingers Nz")),
			("profile", "bool",     0, _("Profile")),
			("overcut", "bool",     1, _("Overcut")),
			("cut",     "bool",     0, _("Cut"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		dx = self.fromMm("dx")
		dy = self.fromMm("dy")
		dz = self.fromMm("dz")
		if not self["internal"]:
			dx = -dx
			dy = -dy
			dz = -dz
		box = Box(dx,dy,dz)
		box.name  = self["name"]
		if box.name == "default": box.name = "Box"
		box.thick = app.cnc["thickness"]
		box.feed  = app.cnc["cutfeed"]
		box.feedz = app.cnc["cutfeedz"]
		box.safe  = app.cnc["safe"]
		box.stepz = app.cnc["stepz"]
		box.setNTeeth(self["nx"],self["ny"],self["nz"])
		if self["profile"]:
			box.setTool(app.cnc["diameter"])
		else:
			box.setTool(0.0)

		box.cut = self["cut"]	# create multiple layers or only one
		if self["overcut"]:
			box.overcut = 'D'
		else:
			box.overcut = None

		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, box.make(), _("Create finger BOX"))
		app.refresh()
		app.setStatus(_("Generated: BOX with fingers"))

#------------------------------------------------------------------------------
if __name__ == "__main__":
	import sys
#	box = Box(90., 60., 30.)
#	box.thick = 5.0
#	box.stepz = 5
#	box.setTool(0.0)
#	box.setNTeeth(3, 3, 3)
#	box.make()

#	box = Box(120.0, 75.0, 30.0)
	box = Box(71.0, 62.0, 52.0)
	box.thick = 3.0
	box.feed  = 1000
	box.feedz = 500
	box.stepz = 1.5
#	box.setNTeeth(7, 5, 3)
	box.setNTeeth(5, 5, 3)

	box.setTool(3.175)
	box.setTool(0.0)
#	box.overcut = 'V'
	box.overcut = 'D'
	blocks = box.make()
#	d = 0.0; box._rectangle(0.,0.,100., 50., NX, NY)
#	d = 4.0; box._rectangle(0.,0.,100., 50., NX, NY)

	def dump(filename):
		try: f = open(filename,"r")
		except: return
		for line in f:
			sys.stdout.write("%s\n"%(line))
		f.close()
	dump("header")
	for block in blocks:
		for line in block:
			sys.stdout.write("%s\n"%(line))
	dump("footer")
