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

import numpy
from svg_elements import SVG, Path, Move, Shape, Line, Close, Arc


class SVGcode:
	def __init__(self, filepath=None):
		self._filepath = filepath

	def path2gcode(self, path, samples_per_unit=100, d=4):
		gcode = []
		if isinstance(path, str):
			path = Path(path)

		def rv(v):
			return ('%*f' % (d, round(v, d))).rstrip("0").rstrip(".")

		for segment in path:
			subdiv=max(1, round(segment.length(error=1e-5) * samples_per_unit))

			if isinstance(segment, Move):
				gcode.append('G0 X%s Y%s' % (rv(segment.end.x), rv(-segment.end.y)))
			elif isinstance(segment, (Line, Close)):
				gcode.append('G1 X%s Y%s' % (rv(segment.end.x), rv(-segment.end.y)))
			elif isinstance(segment, Arc) and abs(segment.rx - segment.ry) < 1e-9:
				# Strictly speaking, svg arcs can be non circular, whereas gcode only permits circular arcs.
				garc = "G02" if segment.sweep > 0 else "G03"
				gcode.append('%s X%s Y%s R%s' % (garc,
												 rv(segment.end.x),
												 rv(-segment.end.y),
												 rv(segment.rx)))
			else:  # Non-circular arc, Cubic or Quad Bezier Curves.
				subdiv_points = numpy.linspace(0, 1, subdiv, endpoint=True)[1:]
				points = segment.npoint(subdiv_points)  # numpy accelerated point() call
				gcode.extend(['G1 X%s Y%s' % (rv(sp[0]), rv(-sp[1])) for sp in points])

		return '\n'.join(gcode)

	def get_gcode(self, scale=1.0/96.0, samples_per_unit=100, digits=4, ppi=96.0):
		"""
		Parse gcode from an SVG file.

		scale: unit scaling between svg pixels and desired units. 1.0/96.0 is inches.
		subdivratio: How many subdivisions per unit? 1/100th inch steps.
		digits: How many digits of gcode accuracy.
		ppi: pixels per inch of the file being loaded. 96 is standard.
		"""
		gcode = []
		transform = "scale(%g)" % scale if scale != 1.0 else None
		svg = SVG.parse(self._filepath, reify=False, ppi=ppi, transform=transform)
		for element in svg.elements():
			if isinstance(element, Shape):
				if not isinstance(element, Path):
					element = Path(element)
				gcode.append({'id': element.id, 'path': self.path2gcode(element.reify(), samples_per_unit, digits)})
		return gcode
