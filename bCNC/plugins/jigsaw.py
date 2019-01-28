#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author: Gonzalo Cobos Bergillos
# Date:	15-Nov-2017

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Gonzalo Cobos Bergillos"
__email__  = "gcobos@gmail.com"

import random
import math
import copy
import time
from CNC import CNC, Block, CW, CCW
from ToolsPage import Plugin


class Arc(object):

	_eq_threshold = 2.0     # Difference allowed to consider two arcs equal
	_used_arcs = {}

	def __init__(self, key, x, y, r, direction):
		self.key = key
		if key not in self.__class__._used_arcs:
			self.__class__._used_arcs[key] = []
		self.x = float(x)
		self.y = float(y)
		self.r = float(r)
		self.direction = direction

	@classmethod
	def reset_used_arcs(cls):
		cls._used_arcs = {}

	@classmethod
	def set_diff_threshold(cls, threshold):
		cls._eq_threshold = float(threshold)

	def randomize(self):
		tries = 100
		i = 0
		while self in self._used_arcs[self.key] and i < tries:
			self.x = random.uniform(self.x - self._eq_threshold, self.x + self._eq_threshold)
			self.y = random.uniform(self.y - self._eq_threshold, self.y + self._eq_threshold)
			self.r = random.uniform(self.r - self._eq_threshold/3.0, self.r + self._eq_threshold/3.0)
			i += 1
		Arc._used_arcs[self.key].append(copy.deepcopy(self))

	def __eq__(self, other):
		if 0. in (self.r, other.r):
			return False
		if math.fabs(self.y - other.y) <= self._eq_threshold:
			return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.r - other.r)**2) < self._eq_threshold
		else:
			return False

	def __repr__(self):
		return "Arc(x={}, y={}, r={}, dir={})".format(self.x, self.y, self.r, 'CW' if self.direction==CW else 'CCW')


class Jigsaw(object):

	def __init__(self, name = '', thickness = 0, cut_feed = 100, z_safe = 10.0, step_z = 0.5):
		self.name = name or 'Jigsaw'
		self.thickness = thickness
		self.cut_feed = cut_feed
		self.z_safe = z_safe
		self.step_z = step_z
    
	@staticmethod
	def calculate_piece_size(board_width, board_height, number_of_pieces):

		board_area = float(board_width * board_height)
		board_ratio = board_width / board_height

		vertical_pieces = int(round(math.sqrt(number_of_pieces / board_ratio)))
		horizontal_pieces = int(round(number_of_pieces / vertical_pieces))

		piece_width = float(board_width) / horizontal_pieces
		piece_height = float(board_height) / vertical_pieces

		return piece_width, piece_height, horizontal_pieces, vertical_pieces

	@staticmethod
	def get_new_tap_shape(template_type, inverted=False):

		template_types = {
			'basic': {
				'arcs': [
					Arc('b0', 0, 0, 0, CW),
					Arc('b1', 50, 1, 120, CW),
					Arc('b2', 70, 13, 40, CCW),
					Arc('b3', 63, 37, 26, CW),
					Arc('b4', 107, 37, 25, CW),
					Arc('b5', 100, 13 , 26, CW),    
					Arc('b6', 120, 1, 40, CCW),
					Arc('b7', 170, 0, 120, CW),
				],
				'width': 170.0,
				'height': 170.0
			},
			'heart': {
				'arcs': [
					Arc('h0', 0, 0, 0, CW),
					Arc('h1', 50, 1, 120, CW),
					Arc('h2', 70, 13, 40, CCW),
					Arc('h3', 63, 37, 20, CW),
					Arc('h4', 85, 35, 14, CW),
					Arc('h5', 107, 37, 14, CW),
					Arc('h6', 100, 13 , 20, CW),    
					Arc('h7', 120, 1, 40, CCW),
					Arc('h8', 170, 0, 120, CW),
				],
				'width': 170.0,
				'height': 170.0
			},
			'anchor': {
				'arcs': [
					Arc('a0', 0, 0, 0, CW),
					Arc('a1', 70, 0, 200, CW),
					Arc('a2', 70, 25, 200, CCW),
					Arc('a3', 60, 24, 50, CW),
					Arc('a4', 60, 36, 200, CW),
					Arc('a5', 110, 36, 100, CW),
					Arc('a6', 110, 24, 50, CW),
					Arc('a7', 100, 25 , 200, CW),    
					Arc('a8', 100, 0, 200, CCW),
					Arc('a9', 170, 0, 200, CW),
				],
				'width': 170.0,
				'height': 170.0
			}
		}
		tt = template_types.get(template_type, 'basic')
		new_tap = copy.deepcopy(tt['arcs'])
		if inverted:
			for i, arc in enumerate(new_tap[:-1]):
				arc.r = new_tap[i+1].r
				arc.direction = new_tap[i+1].direction
				arc.direction = CW if arc.direction==CCW else CCW
			new_tap[-1].r = 0
			new_tap[-1].direction = new_tap[-2].direction

		return new_tap, tt['width'], tt['height']


	@classmethod
	def get_piece_tap(cls, x=0, y=0, axis='X', piece_width=100.0, piece_height=100.0, tap_shape = 'basic', inverted=False):
		flipped = random.choice((0, 1))
		new_piece, template_width, template_height = cls.get_new_tap_shape(tap_shape, inverted)
		scale = math.sqrt(piece_width * piece_height) / math.sqrt(template_width * template_height)
		for i, j in reversed(list(enumerate(new_piece))) if inverted else enumerate(new_piece):
			# Ensure every arc is different
			if i > 0 and i < len(new_piece) - 1:
				j.randomize()
			if flipped:
				j.direction = CW if j.direction==CCW else CCW
				j.y =-j.y
			if axis == 'Y':
				tmp = j.x
				j.x = -j.y
				j.y = tmp
			j.x *= piece_width / template_width
			j.y *= piece_height / template_height
			j.r *= scale
			j.x += x
			j.y += y
				
		return new_piece

	@classmethod
	def generate_cut(cls, x, y, axis, piece_count, piece_width, piece_height, tap_shape = 'basic', inverted = False):
		cut = []
		for i in range(piece_count):
			cut.extend(cls.get_piece_tap(x, y, axis, piece_width, piece_height, tap_shape, inverted))
			if axis == 'Y':
				y += piece_height
			else:
				x += piece_width
		if inverted:
			cut = list(reversed(cut))
		
		return cut

	@classmethod
	def make_puzzle_cuts(cls, board_width, board_height, number_of_pieces, tap_shape, threshold):

		cuts = []

		piece_width, piece_height, horizontal_pieces, vertical_pieces = cls.calculate_piece_size(board_width, board_height, number_of_pieces)

		# Vertical cuts
		x = piece_width
		y = 0
		for i in range(horizontal_pieces - 1):
			cuts.append(cls.generate_cut(x, y, 'Y', vertical_pieces, piece_width, piece_height, tap_shape, inverted=i%2))
			x += piece_width

		# Horizontal cuts    
		x = 0
		y = piece_height
		for i in range(vertical_pieces - 1):
			cuts.append(cls.generate_cut(x, y, 'X', horizontal_pieces, piece_width, piece_height, tap_shape, inverted=i%2))
			y += piece_height

		return cuts

	def generate(self, board_width, board_height, number_of_pieces, random_seed = 0, tap_shape = 'basic', threshold = 3.0):
		blocks = []
		block = Block(self.name)
		random.seed(random_seed)
		Arc.reset_used_arcs()
		Arc.set_diff_threshold(threshold)
		puzzle_cuts = self.__class__.make_puzzle_cuts(board_width, board_height, number_of_pieces, tap_shape, threshold)

		
		# Draw puzzle cuts
		x = 0
		y = 0
		for i in range(0, int(self.thickness / self.step_z)):
			for cut in puzzle_cuts:
				block.append(CNC.zsafe())
				block.append(CNC.grapid(x + cut[0].x, y + cut[0].y))
				block.append(CNC.zenter(0.0))
				block.append(CNC.fmt("f", self.cut_feed))
				block.append(CNC.zenter(-(i + 1) * self.step_z))
				for arc in cut:
					if arc.r:
						block.append(CNC.garc(arc.direction, x + arc.x, y + arc.y, r=arc.r))

		blocks.append(block)

		# Draw border
		block = Block(self.name + "_border")

		block.append(CNC.zsafe())
		block.append(CNC.grapid(x, y))

		for i in range(0, int(self.thickness / self.step_z)):
			block.append(CNC.fmt("f",self.cut_feed))
			block.append(CNC.zenter(-(i + 1) * self.step_z))
			block.append(CNC.gline(x + board_width, y))
			block.append(CNC.gline(x + board_width, y + board_height))
			block.append(CNC.gline(x, y + board_height))
			block.append(CNC.gline(x, y))

		block.append(CNC.zsafe())
		blocks.append(block)

		return blocks


#==============================================================================
# Jigsaw puzzle generator
#==============================================================================
class Tool(Plugin):
	__doc__ = _("""Jigsaw puzzle generator""")

	def __init__(self, master):
		Plugin.__init__(self, master, "Jigsaw")
		self.icon = "jigsaw"
		self.group = "Generator"
		self.variables = [
			("name",          "db",      "", _("Name")),
			("width",         "mm",   1000.0, _("Board width")),
			("height",        "mm",    800.0,  _("Board height")),
			("piece_count",  "int",      100, _("Piece count")),
			("random_seed",  "int",       1, _("Random seed")),
			("threshold",  "float",     1.2, _("Difference between pieces")),
			("tap_shape",  'basic,heart,anchor', 'basic', _("Shape of the tap"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		name = self["name"]
		if not name or name == "default":
			name = "Jigsaw"

		jigsaw = Jigsaw(name,
			thickness = app.cnc["thickness"],
			cut_feed  = app.cnc["cutfeed"],
			z_safe  = app.cnc["safe"],
			step_z = app.cnc["stepz"]
		)
		t0 = time.time()
		app.setStatus(_("Generating puzzle..."))
		blocks = jigsaw.generate(self.fromMm("width"), self.fromMm("height"), self["piece_count"], self["random_seed"], self["tap_shape"], self["threshold"])
		duration = int(time.time() - t0)
		if len(blocks) > 0:
			active = app.activeBlock()
			if active==0: active=1
			app.gcode.insBlocks(active, blocks, "Jigsaw puzzle")
			app.refresh()
			app.setStatus(_("Jigsaw puzzle generated in {}s").format(duration))
		else:
			app.setStatus(_("Error: Check the parameters and your endmill config"))


if __name__=='__main__':

	j = Jigsaw(1000, 800)
	j.generate(100, 100, 3)
