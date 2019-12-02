# SVGcode 0.2
# Converts SVG paths to g-code
# (c) 2018 - Tomas 'Harvie' Mudrunka
# https://github.com/harvie
# License: GPLv2+

# Usage:
# svgcode = SVGcode('./image.svg')
# for path in svgcode.get_gcode():
#	print(path['id'])
#	print(path['path'])

from __future__ import absolute_import

import numpy
import svg.elements


class SVGcode:
	def __init__(self, filepath=None):
		self.svg = svg.elements.SVG(filepath)

	def path2gcode(self, path, subdivratio=1, d=4):
		gcode = ''
		if isinstance(path, str):
			path = svg.elements.Path(path)

		def rv(v):
			return ('%*f'%(d,round(v, d))).rstrip("0").rstrip(".")

		for segment in path:
			subdiv=max(1,round((segment.length())*subdivratio))

			shape = type(segment).__name__
			if shape == 'Move':
				gcode += 'G0 X%s Y%s\n' % (rv(segment.end.x), rv(-segment.end.y))
			elif shape == 'Arc':
				if segment.sweep: garc = "G02"
				else: garc = "G03"
				center = segment.center-segment.start
				#gcode += "(arc %s %s %s %s %s %s)\n"%(segment.center,segment.radius.real,segment.arc,segment.sweep,segment.theta,segment.delta)
				#garc += ' X%s Y%s I%s J%s\n'%(rv(segment.end.real),rv(-segment.end.imag),rv(center.real),rv(-center.imag))
				gcode += '%s X%s Y%s R%s\n'%(garc, rv(segment.end.x),rv(-segment.end.y),rv(segment.rx))
			elif shape in ['QuadraticBezier', 'CubicBezier', 'Arc']:
				subdiv_points = numpy.linspace(0, 1, subdiv, endpoint=False)[1:]
				for point in subdiv_points:
					gcode += 'G1 X%s Y%s\n'%(rv(segment.point(point).x),rv(-segment.point(point).y))
				gcode += 'G1 X%s Y%s\n'%(rv(segment.end.x),rv(-segment.end.y))
			else:
				gcode += 'G1 X%s Y%s\n'%(rv(segment.end.x),rv(-segment.end.y))
		return gcode

	def get_gcode(self, scale=None, subdivratio=1, digits=4):
		gcode = []
		for element in self.svg.elements(ppi=scale):
			if isinstance(element, svg.elements.Shape):
				id = element.id
				gcode.append({
					'id': id,
					'path': self.path2gcode(svg.elements.Path(element), subdivratio, digits)})
		return gcode
