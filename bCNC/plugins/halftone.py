#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date: 14 Febbruary 2016

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Halftone")
__version__= "0.0.1"

import math

from CNC import CW,CNC,Block
from ToolsPage import Plugin
try:
	from PIL import Image, ImageStat
except ImportError:
	Image = None


#==============================================================================
# Create Halftone
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create halftone pattern from a picture")

	def __init__(self, master):
		Plugin.__init__(self, master, "Halftone")
		self.icon  = "halftone"
		self.group = "Artistic"

		self.variables = [
			("name",              "db" ,        "", _("Name")),
			("File"  ,          "file" ,        "", _("Image to process")),
			("Channel","Luminance,Red(sqrt),Green(sqrt),Blue(sqrt)" ,"Luminance", _("Channel to analyze")),
			("Invert"  ,        "bool" ,        "", _("Invert Colors")),
			("DrawSize"  ,         "mm" ,    250.0, _("Max draw size (Width or Height)")),
			("CellSize"  ,        "mm" ,       5.0, _("Cell size")),
			("DiameterMax"  ,     "mm" ,       4.0, _("Max diameter, cap limit")),
			("DiameterMin"  ,     "mm" ,       0.2, _("Min diameter, cut off")),
			("Angle",          "float" ,       0.0, _("Image rotation angle")),
			("DrawBorder",      "bool" ,     False, _("Draw border")),
			("Depth"  ,           "mm" ,       0.0, _("Working Depth")),
			("Conical",         "bool" ,     False, _("Generate for conical end mill")),
		]
		self.buttons.append("exe")

	def rotatePoint(self,centerPoint,point,angle):
		"""Rotates a point around another centerPoint. Angle is in degrees.
		Rotation is clockwise"""
		angle = math.radians(angle)
		resPoint = point[0]-centerPoint[0] , point[1]-centerPoint[1]
		resPoint = ( resPoint[0]*math.cos(angle)-resPoint[1]*math.sin(angle) ,
					 resPoint[0]*math.sin(angle)+resPoint[1]*math.cos(angle))
		resPoint = resPoint[0]+centerPoint[0] , resPoint[1]+centerPoint[1]
		return resPoint

	def halftone(self, im, sample, scale, angle, squareNorm, invert):
		circles = []
		channel = im.rotate(angle, expand=1)
		xx=(channel.size[0]*scale-im.size[0]*scale) / 2
		yy=(channel.size[1]*scale-im.size[1]*scale) / 2

		#Alternate scan
		xscan = range(0, channel.size[0], sample)
		for y in range(0, channel.size[1], sample):
			xscan = xscan[::-1] #reverse scan
			for x in xscan:
				box = channel.crop((x, y, x + sample, y + sample))
				stat = ImageStat.Stat(box)
				diameter = (stat.mean[0] / 255)
				if squareNorm:
					diameter = diameter**0.5
				if not invert:
					diameter = 1 - diameter
				x_pos, y_pos = x*scale, y*scale
				radius = sample * scale * diameter/2.
				x_r,x_y = self.rotatePoint((channel.size[0]*scale/2.,channel.size[1]*scale/2.), (x_pos, y_pos), angle)
				if x_r> xx and x_y> yy and x_r< xx + im.size[0]*scale and x_y< yy + im.size[1]*scale:
					x_r, x_y = x_r - xx, x_y - yy
					circles.append((x_r, x_y, radius))
		return  circles


	# ----------------------------------------------------------------------
	def execute(self, app):
		if Image is None:
			app.setStatus(_("Halftone abort: This plugin requires PIL/Pillow to read image data"))
			return

		n = self["name"]
		if not n or n=="default": n="Halftone"

		#Calc desired size
		channel = self["Channel"]
		invert = self["Invert"]
		drawSize = self["DrawSize"]
		cellSize = self["CellSize"]
		dMax = self["DiameterMax"]
		dMin = self["DiameterMin"]
		angle = self["Angle"]
		drawBorder = self["DrawBorder"]
		depth = self["Depth"]
		conical = self["Conical"]

		#Check parameters
		if drawSize < 1:
			app.setStatus(_("Halftone abort: Size too small to draw anything!"))
			return

		if dMin > dMax:
			app.setStatus(_("Halftone abort: Minimum diameter must be minor then Maximum"))
			return

		if dMax < 1:
			app.setStatus(_("Halftone abort: Maximum diameter too small"))
			return

		if cellSize < 1:
			app.setStatus(_("Halftone abort: Cell size too small"))
			return

		tool = app.tools["EndMill"]
		tool_shape = tool["shape"]
		if conical:
			if tool_shape== "V-cutting":
				try:
					v_angle = float(tool["angle"])
				except:
					app.setStatus(_("Halftone abort: Angle in V-Cutting end mill is missing"))
					return
			else:
				app.setStatus(_("Halftone abort: Conical path need V-Cutting end mill"))
				return

		#Open picture file
		fileName = self["File"]
		try:
			img = Image.open(fileName)
		except:
			app.setStatus(_("Halftone abort: Can't read image file"))
			return

		#Create a scaled image to work faster with big image and better with small ones
		squareNorm = True
		if channel == 'Blue(sqrt)':
			img = img.convert('RGB')
			img = img.split()[0]
		elif channel == 'Green(sqrt)':
			img = img.convert('RGB')
			img = img.split()[1]
		elif channel == 'Red(sqrt)':
			img = img.convert('RGB')
			img = img.split()[2]
		else:
			img = img.convert ('L') #to calculate luminance
			squareNorm = False

		 #flip image to output correct coordinates
		img = img.transpose(Image.FLIP_TOP_BOTTOM)

		#Calc divisions for halftone
		divisions = drawSize / cellSize
		#Get image size
		self.imgWidth, self.imgHeight =  img.size
		if (self.imgWidth > self.imgHeight):
			scale = drawSize / float(self.imgWidth)
			sample = int(self.imgWidth / divisions)
		else:
			scale = drawSize / float(self.imgHeight)
			sample = int(self.imgHeight / divisions)
		self.ratio = scale

		#Halftone
		circles = self.halftone(img, sample, scale, angle, squareNorm, invert)

		#Init blocks
		blocks = []

		#Border block
		if drawBorder:
			block = Block("%s-border"%(self.name))
			block.append(CNC.zsafe())
			block.append(CNC.grapid(0,0))
			block.append(CNC.zenter(depth))
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
			block.append(CNC.gline(self.imgWidth * self.ratio, 0))
			block.append(CNC.gline(self.imgWidth * self.ratio, self.imgHeight*self.ratio))
			block.append(CNC.gline(0, self.imgHeight*self.ratio))
			block.append(CNC.gline(0,0))
			blocks.append(block)

		#Draw block
		block = Block(self.name)

		#Change color
		if channel == 'Blue(sqrt)':
			block.color = "#0000ff"
		elif channel == 'Green(sqrt)':
			block.color = "#00ff00"
		elif channel == 'Red(sqrt)':
			block.color = "#ff0000"

		block.append("(Halftone size W=%d x H=%d x D=%d ,Total points:%i)" %
			 (self.imgWidth * self.ratio, self.imgHeight * self.ratio, depth, len(circles)))
		block.append("(Channel = %s)" % channel)

		for c in circles:
			x,y,r = c
			r = min(dMax/2.0,r)
			if (r >= dMin/2.):
				block.append(CNC.zsafe())
				block.append(CNC.grapid(x+r,y))
				block.append(CNC.zenter(depth))
				block.append(CNC.garc(CW,x+r,y,i=-r,))
		block.append(CNC.zsafe())
		if conical: block.enable = False
		blocks.append(block)

		if conical:
			blockCon = Block("%s-Conical"%(self.name))
			for c in circles:
				x,y,r = c
				blockCon.append(CNC.zsafe())
				blockCon.append(CNC.grapid(x,y))
				dv = r / math.tan(math.radians(v_angle/2.))
				blockCon.append(CNC.zenter(-dv))
			blockCon.append(CNC.zsafe())
			blocks.append(blockCon)

		#Gcode Zsafe
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Halftone")
		app.refresh()
		app.setStatus(_("Generated Halftone size W=%d x H=%d x D=%d ,Total points:%i" %
			 (self.imgWidth * self.ratio, self.imgHeight * self.ratio, depth, len(circles))))
