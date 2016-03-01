# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

try:
	import cv2 as cv
except ImportError:
	cv = None

try:
	from Tkinter import *
except ImportError:
	from tkinter import *

try:
	from PIL import Image, ImageTk
except ImportError:
	cv = None

import Utils

#-------------------------------------------------------------------------------
def hasOpenCV(): return cv is not None

#===============================================================================
# Camera processing class
# A wrapper to opencv needed functions
#===============================================================================
class Camera:
	#-----------------------------------------------------------------------
	# prefix is the prefix to get configuration parameters from ini
	#-----------------------------------------------------------------------
	def __init__(self, prefix=""):
		if cv is None: return
		self.prefix  = prefix
		self.idx     = Utils.getInt("Camera", prefix)
		self.camera  = None
		self.image   = None
		self.imagetk = None

	#-----------------------------------------------------------------------
	def start(self):
		if cv is None: return
		self.camera = cv.VideoCapture(self.idx)
		self.set()

	#-----------------------------------------------------------------------
	def stop(self):
		if cv is None or self.camera is None: return
		self.camera.release()
#		del self.camera
		self.camera = None

	#-----------------------------------------------------------------------
	def set(self):
		width = Utils.getInt("Camera", self.prefix+"_width",  0)
		if width: self.camera.set(3, width)
		height = Utils.getInt("Camera", self.prefix+"_height",  0)
		if height: self.camera.set(4, height)
		self.angle = Utils.getInt("Camera", self.prefix+"_angle")//90 % 4

	#-----------------------------------------------------------------------
	# Rotate image in steps of 90deg
	#-----------------------------------------------------------------------
	def rotate90(self, image):
		if self.angle == 1:	# 90 deg
			return cv.transpose(image)
		elif self.angle == 2: # 180 deg
			return cv.flip(image,-1)
		elif self.angle == 3: # 270 deg
			return cv.flip(cv.transpose(image), 1)
		else:
			return image

	#-----------------------------------------------------------------------
	# Read one image and rotated if needed
	#-----------------------------------------------------------------------
	def read(self):
		s,self.image = self.camera.read()
		if s: self.image = self.rotate90(self.image)
		return s,self.image

	#-----------------------------------------------------------------------
	# Save image to file
	#-----------------------------------------------------------------------
	def save(self, filename):
		cv.imwrite(filename, self.image)

	#-----------------------------------------------------------------------
	def resize(self, factor):
		self.image = cv.resize(self.image, (0,0), fx=factor, fy=factor)

	#-----------------------------------------------------------------------
	def toTk(self):
		self.imagetk = ImageTk.PhotoImage(
					image=Image.fromarray(
						cv.cvtColor(self.image, cv.COLOR_BGR2RGB), "RGB"))
		return self.imagetk
