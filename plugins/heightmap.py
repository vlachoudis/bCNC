#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date:     18 November 2015
# Porting of image2gcode and based on dmap2gcode
# Source was used from the following works:
#              image-to-gcode.py   2005 Chris Radek chris@timeguy.com
#              image-to-gcode.py   2006 Jeff Epler
#              Author.py(linuxcnc) 2007 Jeff Epler  jepler@unpythonic.net
#              dmap2gcode G-Code Generator 2015  @schorchworks

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = _("Heightmap")
__version__= "0.0.1"

import math
from CNC import CNC,Block
from ToolsPage import Plugin

from imageToGcode import *

#==============================================================================
#Heightmap class
#==============================================================================
class Heightmap:
	def __init__(self,name="Heightmap"):
		self.name = name

#==============================================================================
# Create heightmap
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Use a brightess map to create a variable Z path")
	def __init__(self, master):
		Plugin.__init__(self, master, "Heightmap")
		self.icon  = "heightmap"
		self.group = "Generator"

		self.variables = [
			("name",      "db" ,     "", _("Name")),
			("Depth",     "mm" ,   -1.0, _("Working Depth")),
			("MaxSize",   "mm" ,  100.0, _("Maximum size")),
			("Scan",      "Columns,Rows,C&R,R&C", "Rows", _("Scan")),
			("ScanDir",   "Alternating,Positive,Negative,Up Mill,Down Mill" ,\
						"Alternating" , _("ScanDir")),
			("CutTop",    "bool",  False, _("Cut Top")),
			("CutBorder", "bool",  False, _("Cut Border")),
			("Invert",    "bool",  False, _("Invert")),
			("SinglePass",    "bool",  False, _("Single pass")),
			("File",      "file" ,	  "", _("Image to process")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		#Try import PIL
		try:
			from PIL import Image
		except:
			app.setStatus(_("Heightmap abort: This plugin requires PIL/Pillow"))
			return

		#Try read image
		fileName = self["File"]
		try:
			img = Image.open(fileName)
			img = img.convert ('L') #Luminance
		except:
			app.setStatus(_("Heightmap abort: Can't read image file"))
			return

		if self.fromMm("Depth")>=0:
			app.setStatus(_("Heightmap abort: depth must be < 0"))
			return

		#Define type of matrix manipulation
		NUMPY = True
		if NUMPY == True:
			try:
				import numpy
			except:
				NUMPY = False

		if NUMPY == True:
			Image_Matrix = Image_Matrix_Numpy
		else:
			Image_Matrix = Image_Matrix_List
			#print "Install NumPy will speed up heightmap creation"

		MAT = Image_Matrix()
		MAT.FromImage(img,True)

		maxSize = self.fromMm("MaxSize")
		w, h = img.size

		if (w > h):
			ratio = float(w) / float(h)
			image_w = maxSize
			image_h = maxSize / ratio
		else:
			ratio = float(h) / float(w)
			image_w = maxSize / ratio
			image_h = maxSize

		#Calc pixel size
		pixel_size = image_h / ( float(MAT.width) - 1.0 )

		tolerance     =  0.1
		safe_z        =  CNC.vars["safe"]
		splitstep     =  0.0	#Offset Stepover
		toptol        = -0.1	#Top Tolerance
		depth         = -self["Depth"]
		Cont_Angle    =  45.0 #Contact angle , only with "Lace Bounding"

		#Cut perimeter/border
		cutperim      = 0
		if (self["CutBorder"]) : cutperim = 1

		######################################################
		tool = app.tools["EndMill"]
		tool_shape = tool["shape"]

		tool_diameter =  CNC.vars['diameter']
		feed_rate     =  CNC.vars["cutfeed"]

		zStep         =  CNC.vars['stepz']
		if self["SinglePass"]:
			zStep     =  0.0
		rough_offset  =  0.0
		rough_feed    =  CNC.vars["cutfeed"]

		plunge_feed   =  CNC.vars["cutfeedz"]
		stepover      =  tool_diameter * CNC.vars['stepover'] / 100.0
		step          =  max(1, int(math.floor( float(stepover) / pixel_size)))

		edge_offset   = 0
		######################################################
		if tool_shape == "Square End" or tool_shape == "Fishtail" or tool_shape == "Radiused":
			TOOL = make_tool_shape(NUMPY,endmill, tool_diameter, pixel_size)
		elif tool_shape== "V-cutting":
			try:
				v_angle = float(tool["angle"])
			except:
				app.setStatus(_("Heightmap abort: angle not defined for selected End Mill"))
				return
			TOOL = make_tool_shape(NUMPY,vee_common(v_angle), tool_diameter, pixel_size)
		else: #"Ball End"
			TOOL = make_tool_shape(NUMPY,ball_tool, tool_diameter, pixel_size)

		######################################################
		rows = 0
		columns = 0
		columns_first = 0
		scanpat = self["Scan"]
		if scanpat!= "Columns":
			rows = 1
		if scanpat!= "Rows":
			columns = 1
		if scanpat == "C&R":
			columns_first = 1

		######################################################
		# Options are "Alternating", "Positive"   , "Negative",  "Up Mill", "Down Mill"
		converter = self["ScanDir"]

		if converter == "Positive":
			conv_index = 0

		elif converter == "Negative":
			conv_index = 1

		elif converter == "Alternating":
			conv_index = 2

		elif converter == "Up Mill":
			conv_index = 3

		elif converter == "Down Mill":
			conv_index = 4
		else:
			conv_index = 2

		######################################################
		convert_makers = [ Convert_Scan_Increasing, Convert_Scan_Decreasing, \
		 Convert_Scan_Alternating, Convert_Scan_Upmill, Convert_Scan_Downmill ]
		if rows:
			convert_rows = convert_makers[conv_index]()
		else:
			convert_rows = None

		if columns:
			convert_cols = convert_makers[conv_index]()
		else:
			convert_cols = None

		######################################################
		lace_bound_val = "None" #"None","Secondary","Full"
		if lace_bound_val != "None" and rows and columns:
			slope = tan( Cont_Angle*pi/180 )
			if columns_first:
				convert_rows = Reduce_Scan_Lace(convert_rows, slope, step+1)
			else:
				convert_cols = Reduce_Scan_Lace(convert_cols, slope, step+1)
			if lace_bound_val == "Full":
				if columns_first:
					convert_cols = Reduce_Scan_Lace(convert_cols, slope, step+1)
				else:
					convert_rows = Reduce_Scan_Lace(convert_rows, slope, step+1)

		######################################################
		###              START COMMON STUFF                ###
		######################################################
##		units = "mm"
##		if units == "in":
##			units = 'G20'
##		else:
##			units = 'G21'
		#Units not used
		units = ""

		######################################################
		cuttop = 1
		if (self["CutTop"]) : cuttop = 0
		if cuttop:
			if rows == 1:
				convert_rows = Reduce_Scan_Lace_new(convert_rows, toptol, 1)
			if columns == 1:
				convert_cols = Reduce_Scan_Lace_new(convert_cols, toptol, 1)

		######################################################
		#Force disable arcs
		disable_arcs = True #grbl doesn't like this, G91.1?
		if (not disable_arcs):
			Entry_cut   = ArcEntryCut(plunge_feed, .125)
		else:
			Entry_cut   = SimpleEntryCut(plunge_feed)

		######################################################
		#Force normalize
		normalize = True
		if normalize:
			pass
			a = MAT.min()
			b = MAT.max()
			if a != b:
				MAT.minus(a)
				MAT.mult(1./(b-a))
		else:
			MAT.mult(1/255.0)

		xoffset = 0
		yoffset = 0
		######################################################
		MAT.mult(depth)

		##########################################
		#         ORIGIN LOCATING STUFF          #
		##########################################
		minx = 0
		maxx = image_w
		miny = 0
		maxy = image_h
		midx = (minx + maxx)/2
		midy = (miny + maxy)/2

		#Force origin, we can move it later
		origin = "Bot-Left"
		CASE = str(origin)
		if     CASE == "Top-Left":
			x_zero = minx
			y_zero = maxy
		elif   CASE == "Top-Center":
			x_zero = midx
			y_zero = maxy
		elif   CASE == "Top-Right":
			x_zero = maxx
			y_zero = maxy
		elif   CASE == "Mid-Left":
			x_zero = minx
			y_zero = midy
		elif   CASE == "Mid-Center":
			x_zero = midx
			y_zero = midy
		elif   CASE == "Mid-Right":
			x_zero = maxx
			y_zero = midy
		elif   CASE == "Bot-Left":
			x_zero = minx
			y_zero = miny
		elif   CASE == "Bot-Center":
			x_zero = midx
			y_zero = miny
		elif   CASE == "Bot-Right":
			x_zero = maxx
			y_zero = miny
		elif   CASE == "Arc-Center":
			x_zero = 0
			y_zero = 0
		else:          #"Default"
			x_zero = 0
			y_zero = 0

		xoffset = xoffset - x_zero
		yoffset = yoffset - y_zero

		######################################################
		invert = self["Invert"]
		if invert:
			MAT.mult(-1.0)
		else:
			MAT.minus(depth)

		######################################################

		gcode = []
		MAT.pad_w_zeros(TOOL)

		header = ""
		postscript = ""
		gcode = convert(self,          \
						 MAT,           \
						 units,         \
						 TOOL,          \
						 pixel_size,    \
						 step,          \
						 safe_z,        \
						 tolerance,     \
						 feed_rate,     \
						 convert_rows,  \
						 convert_cols,  \
						 columns_first, \
						 cutperim,      \
						 Entry_cut,     \
						 zStep,         \
						 rough_feed,    \
						 xoffset,       \
						 yoffset,       \
						 splitstep,     \
						 header,        \
						 postscript,    \
						 edge_offset,   \
						 disable_arcs)

		#Gcode
		n = self["name"]
		if not n or n=="default": n="Heightmap"
		block = Block(n)
		block.append("(Size: %d x %d x %d)"%(image_w,image_h,depth))
		block.append("(Endmill shape: %s , Diameter: %.3f)"%(tool_shape,tool_diameter))
		for line in gcode:
			block.append(line)

		blocks = []
		blocks.append(block)
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, n)
		app.refresh()
		app.setStatus(_("Generated Heightmap %d x %d x %d ")%(image_w,image_h,depth) )
