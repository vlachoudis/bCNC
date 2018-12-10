#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date: 16 October 2015

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Pyrograph")
__version__= "0.0.3"

from CNC import CNC,Block
from ToolsPage import Plugin


#==============================================================================
#Pyrograph class
#==============================================================================
class Pyrograph:
	def __init__(self,name="Pyrograph"):
		self.name = name


#==============================================================================
# Create pyrograph
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create a variable feed path based upon image brightness")

	def __init__(self, master):
		Plugin.__init__(self, master, "Pyrograph")
		self.icon  = "pyrograph"
		self.group = "Artistic"

		self.variables = [
			("name",         "db" ,    "", _("Name")),
			("ToolSize",     "mm" ,    0.5, _("Pyrograph tip size")),
			("Depth",        "mm" ,    0.0, _("Working Depth")),
			("MaxSize",      "mm" ,  100.0, _("Maximum size")),
			("FeedMin",     "int" ,    250, _("Minimum feed")),
			("FeedMax",     "int" ,   5000, _("Maximum feed")),
			("Direction", "Horizontal,Vertical,Both", "Horizontal", _("Direction")),
			("DrawBorder",  "bool",  False, _("Draw border")),
			("File",       "file" ,     "", _("Image to process")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		try:
			from PIL import Image
		except:
			app.setStatus(_("Pyrograph abort: This plugin requires PIL/Pillow"))
			return

		n = self["name"]
		if not n or n=="default": n="Pyrograph"

		#Calc desired size
		toolSize = self.fromMm("ToolSize")
		maxSize = self.fromMm("MaxSize")
		feedMin = self["FeedMin"]
		feedMax = self["FeedMax"]
		depth = self.fromMm("Depth")
		direction = self["Direction"]
		drawBorder = self["DrawBorder"]

		#Check parameters
		if direction is "":
			app.setStatus(_("Pyrograph abort: please define a scan Direction"))
			return

		if toolSize <=0:
			app.setStatus(_("Pyrograph abort: Tool Size must be > 0"))
			return

		if feedMin <=0 or feedMax <=0 :
			app.setStatus(_("Pyrograph abort: Please check feed rate parameters"))
			return

		#divisions
		divisions = maxSize / toolSize

		fileName = self["File"]
		try:
			img = Image.open(fileName)
			img = img.convert ('RGB') #be sure to have color to calculate luminance
		except:
			app.setStatus(_("Pyrograph abort: Can't read image file"))
			return

		iWidth,iHeight =  img.size
		newWidth = iWidth
		newHeight = iHeight

		ratio = 1
		if (iWidth > iHeight):
			ratio = float(iWidth) / float(iHeight)
			newWidth = int(divisions)
			newHeight = int(divisions / ratio)
		else:
			ratio = float(iHeight) / float(iWidth)
			newWidth = int(divisions / ratio)
			newHeight = int(divisions)

		#Create a thumbnail image to work faster
		img.thumbnail((newWidth,newHeight), Image.ANTIALIAS)
		newWidth,newHeight =  img.size
		#img.save("thumb.png")
		pixels = list(img.getdata())

		#Extract luminance
		gMap = []
		for x in range(0,newWidth):
			gRow = []
			for y in range(0,newHeight):
				R,G,B = pixels[(y * newWidth) + x ]
				L = (0.299*R + 0.587*G + 0.114*B) #Luminance (Rec. 601 standard)
				gRow.append(L)
			gMap.append(gRow)

		#Init blocks
		blocks = []
		block = Block(self.name)
		block.append("(Pyrograph W=%g x H=%g x D=%g)" %
		(newWidth * toolSize , newHeight * toolSize , depth))

		#Create points for vertical scan
		xH = []
		yH = []
		fH = []
		if (direction=="Vertical" or direction=="Both"):
			r = range(0,newHeight)
			for x in range(0,newWidth):
				r = r[::-1]
				fPrec = -1
				for y in r:
					f = int(feedMin + ((feedMax - feedMin) * gMap[x][y] / 255.0))
					if(f != fPrec or y==0 or  y==newHeight-1):
						xH.append(x * toolSize)
						yH.append((newHeight-y) * toolSize)
						fH.append(f)
					fPrec = f

		#Create points for horizontal scan
		xV = []
		yV = []
		fV = []
		if (direction=="Horizontal" or direction=="Both"):
			r = range(0,newWidth)
			for y in reversed(range(0,newHeight)):
				fPrec = -1
				for x in r:
					f = int(feedMin + ((feedMax - feedMin) * gMap[x][y] / 255.0))
					if(f != fPrec or x==0 or x==newWidth-1):
						xV.append(x * toolSize)
						yV.append((newHeight-y) * toolSize)
						fV.append(f)
					fPrec = f
				r = r[::-1]

		#Gcode Horizontal
		if (len(xH)>1 and len(yH)>1):
			block.append(CNC.zsafe())
			block.append(CNC.grapid(xH[0],yH[0]))
			block.append(CNC.zenter(depth))
			for x,y,f in zip(xH,yH,fH):
					v = (x,y,depth)
					block.append(CNC.glinev(1,v,f))

		#Gcode Vertical
		if (len(xV)>1 and len(yV)>1):
			block.append(CNC.zsafe())
			block.append(CNC.grapid(xV[0],yV[0]))
			block.append(CNC.zenter(depth))
			for x,y,f in zip(xV,yV,fV):
					v = (x,y,depth)
					block.append(CNC.glinev(1,v,f))

		#Draw Border if required
		if drawBorder:
			block.append(CNC.zsafe())
			block.append(CNC.grapid(0,0))
			block.append(CNC.zenter(depth))
			block.append(CNC.gcode(1, [("f",feedMin)]))
			block.append(CNC.gline(newWidth * toolSize - toolSize,0))
			block.append(CNC.gline(newWidth * toolSize - toolSize ,newHeight* toolSize))
			block.append(CNC.gline(0,newHeight* toolSize ))
			block.append(CNC.gline(0,0))

		#Gcode Zsafe
		block.append(CNC.zsafe())

		blocks.append(block)
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Pyrograph")
		app.refresh()
		app.setStatus(_("Generated Pyrograph W=%g x H=%g x D=%g") %
		(newWidth * toolSize , newHeight * toolSize , depth))
