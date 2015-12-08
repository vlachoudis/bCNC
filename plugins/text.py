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
			("FontSize"  ,   "mm" ,   10.0, "Font size"),
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
		if fontSize <=0:
			app.setStatus(_("Text abort: please input a Font size > 0"))
			return
		if fontFileName == "":
			app.setStatus(_("Text abort: please select a font file"))
			return
		if textToWrite == "":
			textToWrite = "Nel mezzo del cammin di nostra vita..."
			return

		#Init blocks
		blocks = []
		n = self["name"]
		if not n or n == "default": n = "Text"
		block = Block(n)
		block.append("(Text: %s)" % textToWrite)

		xOffset = 0
		yOffset = 0

		try:
			import ttf
			font = ttf.TruetypeInfo(fontFileName)
		except:
			app.setStatus(_("Text abort: That embarrassing, I can't read this font file!"))
			return
		cmap = font.get_character_map()

		kern = None
		try:
			kern = font.get_glyph_kernings()
		except:
			pass
		adv = font.get_glyph_advances()

		glyphIndxLast = cmap[' ']
		for c in textToWrite:
			#New line
			if c == u'\n':
				xOffset = 0.0
				yOffset -= 1#offset for new line
				continue

			if c in cmap:
				glyphIndx = cmap[c]

				if (kern and (glyphIndx,glyphIndxLast) in kern):
					k = kern[(glyphIndx,glyphIndxLast)] #FIXME: use kern for offset??

				#Get glyph contours as line segmentes and draw them
				gc = font.get_glyph_contours(glyphIndx)
				if(not gc):
					gc = font.get_glyph_contours(0)#standard glyph for missing glyphs (complex glyph)
				if(gc and not c==' '): #FIXME: for some reason space is not mapped correctly!!!
					self.writeGlyphContour(block, font, gc, fontSize, depth, xOffset, yOffset)

				xOffset += adv[glyphIndx]
				glyphIndxLast = glyphIndx

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
	def writeGlyphContour(self,block,font,contours,fontSize,depth,xO, yO):
		width = font.header.x_max - font.header.x_min
		height = font.header.y_max - font.header.y_min
		scale = fontSize / font.header.units_per_em
		xO = xO * fontSize
		yO = yO * fontSize
		for cont in contours:
			block.append(CNC.zsafe())
			block.append(CNC.grapid(xO + cont[0].x * scale , yO + cont[0].y * scale))
			block.append(CNC.zenter(depth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
			
			for p in cont:
				block.append(CNC.gline(xO + p.x * scale, yO + p.y * scale))




