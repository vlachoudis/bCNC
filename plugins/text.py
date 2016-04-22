#!/usr/bin/python
# -*- coding: ascii -*-
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
	__doc__ =  _("Create text using a ttf font")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Text"
		self.icon  = "text"
		self.group = "Generator"

		self.variables = [("name",      "db" ,    "", _("Name")),
				("Text",        "text", "Write this!", _("Text to generate")),
				("Depth",       "mm",    0.0, _("Working Depth")),
				("FontSize",    "mm",   10.0, _("Font size")),
				("FontFile",    "file",   "", _("Font file")),
				("ImageToAscii","file",   "", _("Image to Ascii")),
				("CharsWidth",  "int",    80, _("Image chars width"))]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):

		#Get inputs
		fontSize      = self.fromMm("FontSize")
		depth         = self.fromMm("Depth")
		textToWrite   = self["Text"]
		fontFileName  = self["FontFile"]
		imageFileName = self["ImageToAscii"]
		charsWidth    = self["CharsWidth"]

		#Check parameters!!!
		if fontSize <=0:
			app.setStatus(_("Text abort: please input a Font size > 0"))
			return
		if fontFileName == "":
			app.setStatus(_("Text abort: please select a font file"))
			return
		if imageFileName != "":
			try:
				textToWrite = self.asciiArt(imageFileName,charsWidth)
			except:
				pass
		if textToWrite == "":
			textToWrite = "Nel mezzo del cammin di nostra vita..."
			return

		#Init blocks
		blocks = []
		n = self["name"]
		if not n or n == "default": n = "Text"
		block = Block(n)
		if(u'\n' in  textToWrite):
			block.append("(Text:)")
			for line in textToWrite.splitlines():
				block.append("(%s)" % line)
		else:
			block.append("(Text: %s)" % textToWrite)

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

		xOffset = 0
		yOffset = 0
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

				if glyphIndx < len(adv):
					xOffset += adv[glyphIndx]
				else:
					xOffset += 1
				glyphIndxLast = glyphIndx

		#Remeber to close Font
		font.close()

		#Gcode Zsafe
		block.append(CNC.zsafe())

		blocks.append(block)
		active = app.activeBlock()
		if active==0: active=1
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


	def image_to_ascii(self,image):
		ascii_chars = [ '#', 'A', '@', '%', 'S', '+', '<', '*', ':', ',', '.']
		image_as_ascii = []
		all_pixels = list(image.getdata())
		for pixel_value in all_pixels:
			index = pixel_value / 25 # 0 - 10
			image_as_ascii.append(ascii_chars[index])
		return image_as_ascii

	def asciiArt(self,filePath,new_width = 80):
		from PIL import Image
		img = Image.open(filePath)
		width, heigth = img.size
		new_heigth = int((heigth * new_width) / width)
		new_image = img.resize((new_width, new_heigth))
		new_image = new_image.convert("L") # convert to grayscale

		# now that we have a grayscale image with some fixed width we have to convert every pixel
		# to the appropriate ascii character from "ascii_chars"
		img_as_ascii = self.image_to_ascii(new_image)
		img_as_ascii = ''.join(ch for ch in img_as_ascii)
		output = ""
		for c in range(0, len(img_as_ascii), new_width):
			#print img_as_ascii[c:c+new_width]
			output += img_as_ascii[c:c+new_width] + u'\n'
		return output
