# SVGcode 0.1
# Converts SVG paths to g-code
# (c) 2018 - Tomas 'Harvie' Mudrunka
# https://github.com/harvie
# License: GPLv2+

# Usage:
# svgcode = SVGcode('./image.svg')
# for path in svgcode.get_gcode():
#	print(path['id'])
#	print(path['path'])

import re
import numpy
import svg.path

class SVGcode:
	paths = []

	rx = {}
	rx['elements'] = re.compile('<path[^>]*>', re.IGNORECASE|re.MULTILINE)

	def __init__(self, filepath=None, string=None):
		if filepath is not None: self.read_file(filepath)
		if string is not None: self.read_string(string)

	def get_attr(self, string, attr='d'):
		if 'attr_'+attr not in self.rx.keys():
			self.rx['attr_'+attr] = re.compile('\s%s="([^">]*)"'%(attr), re.IGNORECASE|re.MULTILINE)
		m = self.rx['attr_'+attr].findall(string) or [None]
		return m[0]

	def read_string(self, data):
		#FIXME: process transform="translate(249.1743,415.5005)"
		self.paths = []
		for element in self.rx['elements'].findall(data):
			path = self.get_attr(element)
			path_id = self.get_attr(element, 'id')
			self.paths.append({'id':path_id, 'path':path})

	def read_file(self, filepath):
		with open(filepath, 'r') as myfile:
			data = myfile.read()
		return self.read_string(data)

	def path2gcode(self, path, scale=None, subdivratio=1):
		gcode = ''
		path = svg.path.parse_path(path)
		if scale is None: scale = 3.7795276 #96/25.4 #Inkscape 0.9x dots per mm

		lastx,lasty = None,None

		for segment in path._segments:
			subdiv=max(1,round((segment.length()/scale)*subdivratio))

			if lastx != segment.start.real or lasty != segment.start.imag:
				gcode += 'G0 X%s Y%s\n'%(segment.start.real/scale,-segment.start.imag/scale)

			shape = type(segment).__name__

			if shape in ['QuadraticBezier', 'CubicBezier', 'Arc']: #FIXME: process arcs as G2/G3
		                subdiv_points = numpy.linspace(0, 1, subdiv, endpoint = False)[1:]
		                for point in subdiv_points:
					gcode += 'G1 X%s Y%s\n'%(segment.point(point).real/scale,-segment.point(point).imag/scale)
				gcode += 'G1 X%s Y%s\n'%(segment.end.real/scale,-segment.end.imag/scale)
			else:
				gcode += 'G1 X%s Y%s\n'%(segment.end.real/scale,-segment.end.imag/scale)

			lastx,lasty = segment.end.real,segment.end.imag
		return gcode

	def get_gcode(self, scale=None, subdivratio=1):
		gcode = []
		for path in self.paths:
			gcode.append({'id':path['id'], 'path':self.path2gcode(path['path'], scale, subdivratio)})
		return gcode
