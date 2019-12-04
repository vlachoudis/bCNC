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
from svg_elements import SVG, Path, Shape, Move, Arc, QuadraticBezier, CubicBezier


class SVGcode:
	def __init__(self, filepath=None):
		self.svg = SVG(filepath)

	def path2gcode(self, path, subdivratio=1, d=4):
		gcode = []
		if isinstance(path, str):
			path = Path(path)

		def rv(v):
			return ('%*f'%(d,round(v, d))).rstrip("0").rstrip(".")

		for segment in path:
			subdiv=max(1,round(segment.length(error=1e-5)*subdivratio))

			if isinstance(segment, Move):
				gcode.append('G0 X%s Y%s' % (rv(segment.end.x), rv(-segment.end.y)))
			if isinstance(segment, Arc):
				if segment.sweep: garc = "G02"
				else: garc = "G03"
				#center = segment.center-segment.start
				#gcode += "(arc %s %s %s %s %s %s)\n"%(segment.center,segment.radius.real,segment.arc,segment.sweep,segment.theta,segment.delta)
				#garc += ' X%s Y%s I%s J%s\n'%(rv(segment.end.real),rv(-segment.end.imag),rv(center.real),rv(-center.imag))
				gcode.append('%s X%s Y%s R%s'%(garc, rv(segment.end.x),rv(-segment.end.y),rv(segment.rx)))
			elif isinstance(segment, (QuadraticBezier, CubicBezier, Arc)):
				subdiv_points = numpy.linspace(0, 1, subdiv, endpoint=False)[1:]
				for point in subdiv_points:
					sp = segment.point(point)
					gcode.append('G1 X%s Y%s'%(rv(sp.x),rv(-sp.y)))
				gcode.append('G1 X%s Y%s'%(rv(segment.end.x),rv(-segment.end.y)))
			else:
				# Line, Close
				gcode.append('G1 X%s Y%s'%(rv(segment.end.x),rv(-segment.end.y)))
		return '\n'.join(gcode)

	def get_gcode(self, scale=1.0, subdivratio=1, digits=4):
		gcode = []
		for element in self.svg.elements(ppi=96.0 / scale, width=100, height=100):
			if isinstance(element, Path):
				element.reify()
				id = element.id
				gcode.append({'id': id, 'path': self.path2gcode(element, subdivratio, digits)})
			elif isinstance(element, Shape):
				id = element.id
				gcode.append({'id': id, 'path': self.path2gcode(Path(element), subdivratio, digits)})
		return gcode
