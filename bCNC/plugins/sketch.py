#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date: 	07 January 2016
# Inspired by: "Death to sharpie" a drawbot by Scott Cooper
# see at http://www.dullbits.com/drawbot/drawbot

from __future__ import absolute_import
from __future__ import print_function

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Sketch")
__version__= "0.5.1"

import math
# import time
import random
from array import *

from CNC import CNC,Block
from ToolsPage import Plugin


#==============================================================================
# Create sketch
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Create sketch based on picture brightness")

	def __init__(self, master):
		Plugin.__init__(self, master, "Sketch")
		self.icon  = "sketch"
		self.group = "Artistic"

		self.variables = [
			("name",              "db" ,        "", _("Name")),
			("Grundgy","Low,Medium,High,Very High", "Medium",  _("Grundgy, search radius")),
			("Depth"  ,           "mm" ,       0.0, _("Working Depth")),
			("MaxSize"  ,         "mm" ,     250.0, _("Maximum size")),
			("SquiggleTotal" ,   "int" ,       300, _("Squiggle total count")),
			("SquiggleLength",    "mm" ,     400.0, _("Squiggle Length")),
			("Fading",           "int" ,         4, _("Fading force")),
			("Max_light",        "int" ,         256, _("Maximum light")),
			("DrawBorder",       "bool",     False, _("Draw border")),
			("Casual",           "bool",     True, _("Casual first point")),
			("Repetition",       "bool",     False, _("Repetition of a point")),
			("File"  ,           "file" ,        "", _("Image to process")),
			("Channel","Luminance,Red,Green,Blue" ,"Luminance", _("Channel to analyze")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def findFirst(self, pix, scanAll, casual):
		most = 0
		if casual:
			for e in xrange(1,500):
				x = random.randint(2,self.imgWidth - 3)
				y = random.randint(2,self.imgHeight - 3)
				val = pix[x,y]
				if most == 0:
					most = val
					bestX = x
					bestY = y
				if val < most:
					most = val
					bestX = x
					bestY = y
				if (val <= self.mostest) and not scanAll:
					self.mostest = most
					bestX = x
					bestY = y
		else:
			most = pix[2,2]
			bestX = 2
			bestY = 2
			for x in xrange(2,self.imgWidth - 2):
				for y in xrange(2,self.imgHeight - 2):
					val = pix[x,y]
					if val < most:
						most = val
						bestX = x
						bestY = y
					if (val <= self.mostest) and not scanAll:
						self.mostest = most
		return bestX,bestY

	# ----------------------------------------------------------------------
	def findInRange(self, startX, startY, pix, maxRange):
		xmin = int(max(2, startX - maxRange))
		xmax = int(min(self.imgWidth - 2, startX + maxRange))
		ymin = int(max(2, startY - maxRange))
		ymax = int(min(self.imgHeight - 2, startY + maxRange))

		bestX = startX
		bestY = startY
		distance=1

		most = pix[startX,startY]
		for x in xrange(xmin,xmax):
			for y in xrange(ymin,ymax):
				distance = math.sqrt((startX - x)**2 + (startY -y)**2)
				if(distance > maxRange):
					continue
				val = pix[x,y]
				val += (random.random()*2.)  #avoid ugly straight lines, steal time
				if val < most:
					most = val
					bestX = x
					bestY = y
				if most <= self.mostest:
					self.mostest = most
		return bestX, bestY, distance

	def fadePixel(self, x, y, pix, fad, repetition):
		if (repetition == False):
			pix[x,y] = 256
		pix[x,y] +=10*fad
		pix[x+1,y] +=6*fad
		pix[x-1,y] +=6*fad
		pix[x,y+1] +=6*fad
		pix[x,y-1] +=6*fad
		pix[x+1,y+1] +=5*fad
		pix[x-1,y-1] +=5*fad
		pix[x-1,y+1] +=5*fad
		pix[x+1,y-1] +=5*fad

		pix[x-2,y-2] +=3*fad
		pix[x-2,y-1] +=4*fad
		pix[x-2,y-0] +=4*fad
		pix[x-2,y+1] +=4*fad
		pix[x-2,y+2] +=3*fad

		pix[x+2,y-2] +=3*fad
		pix[x+2,y-1] +=4*fad
		pix[x+2,y-0] +=4*fad
		pix[x+2,y+1] +=4*fad
		pix[x+2,y+2] +=3*fad

		pix[x-2,y-2] +=3*fad
		pix[x-1,y-2] +=4*fad
		pix[x-0,y-2] +=4*fad
		pix[x+1,y-2] +=4*fad
		pix[x+2,y-2] +=3*fad

		pix[x-2,y+2] +=3*fad
		pix[x-1,y+2] +=4*fad
		pix[x-0,y+2] +=4*fad
		pix[x+1,y+2] +=4*fad
		pix[x+2,y+2] +=3*fad

		pix[x-3,y-3] +=1*fad
		pix[x-3,y-2] +=1*fad
		pix[x-3,y-1] +=2*fad
		pix[x-3,y-0] +=2*fad
		pix[x-3,y+1] +=2*fad
		pix[x-3,y+2] +=1*fad
		pix[x-3,y+3] +=1*fad

		pix[x+3,y-3] +=1*fad
		pix[x+3,y-2] +=2*fad
		pix[x+3,y-1] +=2*fad
		pix[x+3,y-0] +=2*fad
		pix[x+3,y+1] +=2*fad
		pix[x+3,y+2] +=2*fad
		pix[x+3,y+3] +=1*fad

		pix[x-3,y-3] +=1*fad
		pix[x-2,y-3] +=2*fad
		pix[x-1,y-3] +=2*fad
		pix[x-0,y-3] +=2*fad
		pix[x+1,y-3] +=2*fad
		pix[x+2,y-3] +=2*fad
		pix[x+3,y-3] +=1*fad

		pix[x-3,y+3] +=1*fad
		pix[x-2,y+3] +=2*fad
		pix[x-1,y+3] +=2*fad
		pix[x-0,y+3] +=2*fad
		pix[x+1,y+3] +=2*fad
		pix[x+2,y+3] +=2*fad
		pix[x+3,y+3] +=1*fad


	# ----------------------------------------------------------------------
	def execute(self, app):
		try:
			from PIL import Image
		except:
			app.setStatus(_("Sketch abort: This plugin requires PIL/Pillow to read image data"))
			return

		n = self["name"]
		if not n or n=="default": n="Sketch"

		#Calc desired size
		grundgy =self["Grundgy"]
		maxSize = self["MaxSize"]
		squiggleTotal  = self["SquiggleTotal"]
		squiggleLength = self["SquiggleLength"]
		depth = self["Depth"]
		drawBorder = self["DrawBorder"]
		channel = self["Channel"]
		casual = self["Casual"]
		fading = self["Fading"]
		max_light = self["Max_light"]
		repetition = self["Repetition"]

		radius = 1
		if grundgy == "Low":
			radius = 2
		elif grundgy == "Medium":
			radius = 3
		elif grundgy == "High":
			radius = 6
		elif grundgy == "Very High":
			radius = 9

		#Check parameters
		if maxSize < 1:
			app.setStatus(_("Sketch abort: Too small to draw anything!"))
			return

		if max_light >256:
			app.setStatus(_("The maximum illumination shouldn't be more than 250!"))
			return

		if squiggleTotal < 1:
			app.setStatus(_("Sketch abort: Please let me draw at least 1 squiggle"))
			return

		if squiggleLength <= 0:
			app.setStatus(_("Sketch abort: Squiggle Length must be > 0"))
			return

		fileName = self["File"]
		try:
			img = Image.open(fileName)
		except:
			app.setStatus(_("Sketch abort: Can't read image file"))
			return

		#Create a scaled image to work faster with big image and better with small ones
		iWidth,iHeight = img.size
		resampleRatio = 800.0 / iHeight
		img = img.resize((int(iWidth *resampleRatio) ,int(iHeight * resampleRatio)), Image.ANTIALIAS)
		if channel == 'Blue':
			img = img.convert('RGB')
			img = img.split()[0]
		elif channel == 'Green':
			img = img.convert('RGB')
			img = img.split()[1]
		elif channel == 'Red':
			img = img.convert('RGB')
			img = img.split()[2]
		else:
			img = img.convert ('L') #to calculate luminance

		img = img.transpose(Image.FLIP_TOP_BOTTOM) #ouput correct image
		pix = img.load()
		#Get image size
		self.imgWidth, self.imgHeight =  img.size
		self.ratio = 1
		if (iWidth > iHeight):
			self.ratio = maxSize / float(self.imgWidth)
		else:
			self.ratio = maxSize / float(self.imgHeight)

		#Init blocks
		blocks = []

		#Info block
		block = Block("Info")
		block.append("(Sketch size W=%d x H=%d x distance=%d)" %
			(self.imgWidth * self.ratio  , self.imgHeight * self.ratio  , depth))
		block.append("(Channel = %s)" %(channel))
		blocks.append(block)

		#Border block
		block = Block("%s-border"%(self.name))
		block.enable = drawBorder
		block.append(CNC.zsafe())
		block.append(CNC.grapid(0,0))
		block.append(CNC.zenter(depth))
		block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))
		block.append(CNC.gline(self.imgWidth * self.ratio, 0))
		block.append(CNC.gline(self.imgWidth * self.ratio, self.imgHeight*self.ratio))
		block.append(CNC.gline(0, self.imgHeight*self.ratio))
		block.append(CNC.gline(0,0))
		blocks.append(block)

		#choose a nice starting point
		x = self.imgWidth / 4.
		y = self.imgHeight / 4.

		#First round search in all image
		self.mostest = 256
		x,y = self.findFirst(pix, True, casual)

		#startAll = time.time()
		total_line=0
		total_length=0
		for c in range(squiggleTotal):
			x,y = self.findFirst(pix, False, casual)
			if pix[x,y]>max_light:
				continue
			block = Block(self.name)
			#print c,x,y
			#start = time.time()

			total_line+=1;
			total_length+=1
			#move there
			block.append(CNC.zsafe())
			block.append(CNC.grapid(x*self.ratio, y*self.ratio))
			#tool down
			block.append(CNC.zenter(depth))
			#restore cut/draw feed
			block.append(CNC.gcode(1, [("f",CNC.vars["cutfeed"])]))

			#start = time.time()
			s = 0
			while (s < squiggleLength):
				x,y,distance = self.findInRange(x, y, pix, radius)
				if pix[x,y]>max_light:
					break
				s+= max(1,distance*self.ratio)  #add traveled distance
				total_length+=1
				#move there
				block.append(CNC.gline(x*self.ratio,y*self.ratio))
				self.fadePixel(x, y, pix, fading, repetition) #adjustbrightness int the bright map
			#tool up
			#print 'Squiggle: %f' % (time.time() - start)
			#Gcode Zsafe
			block.append(CNC.zsafe())
			blocks.append(block)
		active = app.activeBlock()
		app.gcode.insBlocks(active, blocks, "Sketch")
		app.refresh()
		app.setStatus(_("Generated Sketch size W=%d x H=%d x distance=%d, Total line:%i, Total length:%d") %
			(self.imgWidth*self.ratio  , self.imgHeight*self.ratio , depth, total_line, total_length))
		#img.save('test.png')
		#print 'Time: %f' % (time.time() - startAll)
