#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	20-Aug-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

__name__ = _("Gear")

import math
from bmath import Vector
from CNC import CW,CCW,CNC,Block
from ToolsPage import Plugin

#==============================================================================
# Gear class
#==============================================================================
class Gear:
	def __init__(self, name): #, R, nteeth):
		self.name = name

	#----------------------------------------------------------------------
	def involute_intersect_angle(self, Rb, R):
		return math.sqrt(R*R - Rb*Rb) / Rb - math.acos(Rb/R)

	#----------------------------------------------------------------------
	def point_on_circle(self, radius, angle):
		return Vector(radius * math.cos(angle), radius * math.sin(angle))

	#----------------------------------------------------------------------
	# N   = no of teeth
	# phi = pressure angle
	# PC  = Circular Pitch
	#----------------------------------------------------------------------
	def calc(self, N, phi, Pc):
		N = abs(N)
		# Pitch Circle
		D = N * Pc / math.pi
		R = D / 2.0

		# Diametrical pitch
		Pd = N / D

		# Base Circle
		Db = D * math.cos(phi)
		Rb = Db / 2.0

		# Addendum
		a = 1.0 / Pd

		# Outside Circle
		Ro = R + a
		Do = 2.0 * Ro

		# Tooth thickness
		T = math.pi*D / (2*N)

		# undercut?
		U = 2.0 / (math.sin(phi) * (math.sin(phi)))
		needs_undercut = N < U
		# sys.stderr.write("N:%s R:%s Rb:%s\n" % (N,R,Rb))

		# Clearance
		c = 0.0
		# Dedendum
		b = a + c

		# Root Circle
		Rr = R - b
		Dr = 2.0*Rr

		two_pi = 2.0*math.pi
		half_thick_angle = two_pi / (4.0*N)
		pitch_to_base_angle = self.involute_intersect_angle(Rb, R)
		pitch_to_outer_angle = self.involute_intersect_angle(Rb, Ro) # pitch_to_base_angle

		points = []
		for x in range(1,N+1):
			c = x * two_pi / N

			# angles
			pitch1 = c - half_thick_angle
			base1  = pitch1 - pitch_to_base_angle
			outer1 = pitch1 + pitch_to_outer_angle

			pitch2 = c + half_thick_angle
			base2  = pitch2 + pitch_to_base_angle
			outer2 = pitch2 - pitch_to_outer_angle

			# points
			b1 = self.point_on_circle(Rb, base1)
			p1 = self.point_on_circle(R,  pitch1)
			o1 = self.point_on_circle(Ro, outer1)
			o2 = self.point_on_circle(Ro, outer2)
			p2 = self.point_on_circle(R,  pitch2)
			b2 = self.point_on_circle(Rb, base2)

			if Rr >= Rb:
				pitch_to_root_angle = pitch_to_base_angle - self.involute_intersect_angle(Rb, Rr)
				root1 = pitch1 - pitch_to_root_angle
				root2 = pitch2 + pitch_to_root_angle
				r1 = self.point_on_circle(Rr, root1)
				r2 = self.point_on_circle(Rr, root2)

				points.append(r1)
				points.append(p1)
				points.append(o1)
				points.append(o2)
				points.append(p2)
				points.append(r2)
			else:
				r1 = self.point_on_circle(Rr, base1)
				r2 = self.point_on_circle(Rr, base2)
				points.append(r1)
				points.append(b1)
				points.append(p1)
				points.append(o1)
				points.append(o2)
				points.append(p2)
				points.append(b2)
				points.append(r2)

		first = points[0]
		del points[0]

		blocks = []
		block = Block(self.name)
		blocks.append(block)

		block.append(CNC.grapid(first.x(), first.y()))
		block.append(CNC.zenter(0.0))
		#print first.x(), first.y()
		for v in points:
			block.append(CNC.gline(v.x(), v.y()))
			#print v.x(), v.y()
		#print first.x(), first.y()
		block.append(CNC.gline(first.x(), first.y()))
		block.append(CNC.zsafe())

		#block = Block("%s-center"%(self.name))
		block = Block("%s-basecircle"%(self.name))
		block.enable = False
		block.append(CNC.grapid(Db/2, 0.))
		block.append(CNC.zenter(0.0))
		block.append(CNC.garc(CW, Db/2, 0., i=-Db/2))
		block.append(CNC.zsafe())
		blocks.append(block)
		return blocks

#==============================================================================
# Create a simple Gear
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Generate a spur gear")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Gear"
		self.icon  = "gear"
		self.group = "Generator"
		self.variables = [
			("name",      "db",    "", _("Name")),
			("n",        "int",    10, _("No of teeth")),
			("phi",    "float",  17.0, _("Pressure angle")),
			("pc",        "mm",   5.0, _("Circular Pitch"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		n = self["name"]
		if not n or n=="default": n="Gear"
		gear = Gear(n)
		blocks = gear.calc(self["n"], math.radians(self["phi"]), self.fromMm("pc"))
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, _("Create Spur GEAR"))
		app.refresh()
		app.setStatus(_("Generated: Spur GEAR"))

if __name__=="__main__":
	gear = Gear()
	gear.calc(12, math.radians(10), math.radians(10))
	gear.calc(36, math.radians(10), math.radians(10))
#	gear.calc(10, math.radians(10), math.radians(10))
	#b:scale(Coord(0,0),Coord(10,10))
