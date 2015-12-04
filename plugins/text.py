#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:	Filippo Rivato
# Date: December 2015

__author__ = "Filippo Rivato"
__email__ = "f.rivato@gmail.com"

__name__ = "Text"
__version__ = "0.0.1"

import math
from bmath import Vector
from CNC import CNC,Block
from ToolsPage import Plugin

import tkMessageBox

#==============================================================================
#Text class
#==============================================================================
class Text:
	def __init__(self,name="Text"):
		self.name = name


#==============================================================================
# Create Text
#==============================================================================
class Tool(Plugin):
	"""Create text using a ttf font"""
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name = "Text"
		self.icon = "text"

		self.variables = [("name",      "db" ,    "", "Name"),
			("Text"  ,    "text" ,    "Write this!", "Text to generate"),
			("Depth"  ,   "mm" ,       0.0, "Working Depth"),
			("FontSize"  ,   "mm" ,   100.0, "Font size"),
			("FontFile"  ,   "file" ,       "", "Font file"),]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):

		#Get inputs
		fontSize = self["FontSize"]
		depth = self["Depth"]
		textToWrite = self["Text"]
		fontFileName = self["FontFile"]

		#Check parameters!!!

		#Init blocks
		blocks = []
		n = self["name"]
		if not n or n == "default": n = "Text"
		block = Block(n)
		block.append("(Text: %s)" % textToWrite)

		xOffset = 0
		yOffset = 0

		import ttf
		font = ttf.TruetypeInfo(fontFileName)
		cmap = font.get_character_map()
		kern = font.get_glyph_kernings()
		adv = font.get_glyph_advances()

		glyphIndxLast = cmap[' ']
		#for i,c in enumerate(textToWrite):
		i=0
		while i<len(textToWrite):
			c=textToWrite[i]
			glyphIndx = cmap[c]

			if ((glyphIndx,glyphIndxLast) in kern):
				k = kern[(glyphIndx,glyphIndxLast)]

			#New line
			if c == '\\' and i+1<len(textToWrite) and textToWrite[i + 1] == 'n':
				xOffset = 0.0
				yOffset -= 1#
				i+=2
				continue

			#Get glyph contours as line segmentes and draw them
			gc = font.get_glyph_contours(glyphIndx)
			if(not gc):
				gc = font.get_glyph_contours(0)#standard glyph for missing glyphs (complex glyph)
			if(gc and not c==' '): #for some reason space is not mapped correctly!!!
				self.writeGlyphContour(block, font, gc, fontSize, xOffset, yOffset)
			xOffset += adv[glyphIndx]
			glyphIndxLast = glyphIndx
			i+=1

		#Remeber to close Font
		font.close()

		#Gcode Zsafe
		block.append(CNC.zsafe())

		blocks.append(block)
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Text")
		app.refresh()
		app.setStatus("Generated Text")


	#Write GCode from glyph conrtours
	def writeGlyphContour(self,block,font,contours,fontSize,xO, yO):
		width = font.header.x_max - font.header.x_min
		height = font.header.y_max - font.header.y_min
		scale = fontSize / font.header.units_per_em
		xO = xO * fontSize
		yO = yO * fontSize
		for cont in contours:
			block.append(CNC.zsafe())
			block.append(CNC.grapid(xO + cont[0].x * scale , yO + cont[0].y * scale))
			block.append(CNC.zenter(0))

			for p in cont:
				block.append(CNC.gline(xO + p.x * scale, yO + p.y * scale))




