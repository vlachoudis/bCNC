# -*- coding: latin1 -*-
# $Id: CNCCanvas.py,v 1.7 2014/10/15 15:04:06 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math
import bmath
try:
	from Tkinter import *
except ImportError:
	from tkinter import *

from CNC import CNC
import tkExtra
import Utils

# Probe mapping we need PIL and numpy
try:
	from PIL import Image, ImageTk
	import numpy

	# Resampling image based on PIL library and converting to RGB.
	# options possible: NEAREST, BILINEAR, BICUBIC, ANTIALIAS
	RESAMPLE = Image.NEAREST	# resize type
except:
	numpy = None
	RESAMPLE = None

VIEW_XY      = 0
VIEW_XZ      = 1
VIEW_YZ      = 2
VIEW_ISO1    = 3
VIEW_ISO2    = 4
VIEW_ISO3    = 5

VIEWS = ["X-Y", "X-Z", "Y-Z", "ISO1", "ISO2", "ISO3"]

INSERT_WIDTH2 = 3
GANTRY_R      = 4
GANTRY_X      = 10
GANTRY_Y      =  5
GANTRY_H      = 20

INSERT_COLOR  = "Blue"
GANTRY_COLOR  = "Red"
MARGIN_COLOR  = "Magenta"
GRID_COLOR    = "Gray"
BOX_SELECT    = "Cyan"

ENABLE_COLOR  = "Black"
DISABLE_COLOR = "LightGray"
SELECT_COLOR  = "Blue"
SELECT2_COLOR = "DarkCyan"
PROCESS_COLOR = "Green"

MOVE_COLOR    = "DarkCyan"
RULER_COLOR   = "Green"

ACTION_SELECT        =  0
ACTION_SELECT_SINGLE =  1
ACTION_SELECT_AREA   =  2
ACTION_SELECT_DOUBLE =  3

ACTION_PAN           = 10
ACTION_ORIGIN        = 11

ACTION_MOVE          = 20
ACTION_ROTATE        = 21
ACTION_GANTRY        = 22

ACTION_RULER         = 30

SHIFT_MASK   = 1
CONTROL_MASK = 4
ALT_MASK     = 8
CONTROLSHIFT_MASK = SHIFT_MASK | CONTROL_MASK
CLOSE_DISTANCE = 5
MAXDIST      = 10000

S60 = math.sin(math.radians(60))
C60 = math.cos(math.radians(60))

DEF_CURSOR = ""
MOUSE_CURSOR = {
	ACTION_SELECT        : DEF_CURSOR,
	ACTION_SELECT_AREA   : "right_ptr",
#	ACTION_ZONE          : "center_ptr",
#	ACTION_ZONEPAINT     : "spraycan",	# "pencil"
#	ACTION_PEN           : "pencil",
#	ACTION_PAINT         : "spraycan",
#	ACTION_INFO          : "tcross",	# "target"

	ACTION_PAN           : "fleur",
	ACTION_ORIGIN        : "cross",
#	ACTION_ORBIT         : "exchange",
#	ACTION_ZOOM_IN       : "sizing",
#	ACTION_ZOOM_OUT      : "sizing",
#	ACTION_ZOOM_ON       : "sizing",

#	ACTION_VIEW_CENTER   : "cross",
#	ACTION_VIEW_MOVE     : "fleur",
#	ACTION_VIEW_ROTATE   : "exchange",

#	ACTION_ADD           : "tcross",
#	ACTION_ADD_NEXT      : "tcross",

	ACTION_MOVE          : "hand1",
	ACTION_ROTATE        : "exchange",
	ACTION_GANTRY        : "target",

	ACTION_RULER         : "tcross",

#	ACTION_EDIT          : "pencil",
}

# ------------------------------------------------------------------------------
def mouseCursor(action):
	return MOUSE_CURSOR.get(action, DEF_CURSOR)

#==============================================================================
# Drawing canvas
#==============================================================================
class CNCCanvas(Canvas):
	def __init__(self, master, app, *kw, **kwargs):
		Canvas.__init__(self, master, *kw, **kwargs)

		# Global variables
		self.view = 0
		self.app = app
		self.cnc = app.cnc
		self.gcode = app.gcode
		self.actionVar = IntVar()

		# Canvas binding
		self.bind('<Motion>',		self.motion)

		self.bind('<Button-1>',		self.click)
		self.bind('<B1-Motion>',	self.buttonMotion)
		self.bind('<ButtonRelease-1>',	self.release)
		self.bind('<Double-1>',		self.double)

		self.bind('<B2-Motion>',	self.pan)
		self.bind('<ButtonRelease-2>',	self.panRelease)
		self.bind("<Button-4>",		self.mouseZoomIn)
		self.bind("<Button-5>",		self.mouseZoomOut)

		self.bind('<Shift-Button-4>',	self.panLeft)
		self.bind('<Shift-Button-5>',	self.panRight)
		self.bind('<Control-Button-4>',	self.panUp)
		self.bind('<Control-Button-5>',	self.panDown)

		self.bind('<Control-Key-Left>',	self.panLeft)
		self.bind('<Control-Key-Right>',self.panRight)
		self.bind('<Control-Key-Up>',	self.panUp)
		self.bind('<Control-Key-Down>',	self.panDown)

		self.bind('<Escape>',		self.actionCancel)
		self.bind('<Key-f>',		self.fit2Screen)
		self.bind('<Key-g>',		self.setActionGantry)
		self.bind('<Key-m>',		self.setActionMove)
		self.bind('<Key-o>',		self.setActionOrigin)
		self.bind('<Key-r>',		self.setActionRuler)
		self.bind('<Key-s>',		self.setActionSelect)

		self.bind('<Control-Key-equal>',self.menuZoomIn)
		self.bind('<Control-Key-minus>',self.menuZoomOut)

#		self.bind('<Control-Key-x>',	self.cut)
#		self.bind('<Control-Key-c>',	self.copy)
#		self.bind('<Control-Key-v>',	self.paste)

#		self.bind('<Key-space>',	self.commandFocus)
#		self.bind('<Control-Key-space>',self.commandFocus)
#		self.bind('<Control-Key-a>',	self.selectAll)

		self.x0     = 0.0
		self.y0     = 0.0
		self.zoom   = 1.0
		self._items = {}

		self.action       = ACTION_SELECT
		self._mouseAction = None
		self._x  = self._y  = 0
		self._xp = self._yp = 0
		self._inDraw      = False		# semaphore for parsing
		self._gantry1     = None
		self._gantry2     = None
		self._select      = None
		self._margin      = None
		self._workarea    = None
		self._vector      = None
		self._lastActive  = None
		self._lastGantry  = None

		self._image       = None
		self._tkimage     = None
		self._probeImage  = None

		self.draw_axes    = True		# Drawing flags
		self.draw_grid    = True
		self.draw_margin  = True
		self.draw_probe   = True
		self.draw_workarea= True
		self.draw_paths   = True
		self.draw_rapid   = True		# draw rapid motions
		self._wx = self._wy = self._wz = 0.	# work position
		self._dx = self._dy = self._dz = 0.	# work-machine position

		self._vx0 = self._vy0 = self._vz0 = 0	# vector move coordinates
		self._vx1 = self._vy1 = self._vz1 = 0	# vector move coordinates
		self._last = (0.,0.,0.)

		self._tzoom  = 1.0
		self._tafter = None

		#self.config(xscrollincrement=1, yscrollincrement=1)
		self.initPosition()

	# ----------------------------------------------------------------------
	# Update scrollbars
	# ----------------------------------------------------------------------
	def _updateScrollBars(self):
		"""Update scroll region for new size"""
		bb = self.bbox('all')
		if bb is None: return
		x1,y1,x2,y2 = bb
		dx = x2-x1
		dy = y2-y1
		# make it 3 times bigger in each dimension
		# so when we zoom in/out we don't touch the borders
		self.configure(scrollregion=(x1-dx,y1-dy,x2+dx,y2+dy))

	# ----------------------------------------------------------------------
	def setAction(self, action):
		self.action = action
		self.actionVar.set(action)
		self._mouseAction = None
		self.config(cursor=mouseCursor(self.action))

	# ----------------------------------------------------------------------
	def actionCancel(self, event=None):
		self.setAction(ACTION_SELECT)
		#self.draw()

	# ----------------------------------------------------------------------
	def setActionSelect(self, event=None):
		self.setAction(ACTION_SELECT)
		self.event_generate("<<Status>>",data="Select objects with mouse")

	# ----------------------------------------------------------------------
	def setActionOrigin(self, event=None):
		self.setAction(ACTION_ORIGIN)
		self.event_generate("<<Status>>",data="Click to set the origin (zero)")

	# ----------------------------------------------------------------------
	def setActionMove(self, event=None):
		self.setAction(ACTION_MOVE)
		self.event_generate("<<Status>>",data="Move graphically objects")

	# ----------------------------------------------------------------------
	def setActionGantry(self, event=None):
		self.setAction(ACTION_GANTRY)
		self.event_generate("<<Status>>",data="Move CNC gantry to mouse location")

	# ----------------------------------------------------------------------
	def setActionRuler(self, event=None):
		self.setAction(ACTION_RULER)
		self.event_generate("<<Status>>",data="Drag a ruler to measure distances")

	# ----------------------------------------------------------------------
	def actionGantry(self, x, y):
		u = self.canvasx(x) / self.zoom
		v = self.canvasy(y) / self.zoom

		if self.view == VIEW_XY:
			self.app.goto(u,-v)

		elif self.view == VIEW_XZ:
			self.app.goto(u,None,-v)

		elif self.view == VIEW_YZ:
			self.app.goto(None,u,-v)

		elif self.view == VIEW_ISO1:
			self.app.goto(0.5*(u/S60+v/C60), 0.5*(u/S60-v/C60))

		elif self.view == VIEW_ISO2:
			self.app.goto(0.5*(u/S60-v/C60), -0.5*(u/S60+v/C60))

		elif self.view == VIEW_ISO3:
			self.app.goto(-0.5*(u/S60+v/C60), -0.5*(u/S60-v/C60))
		self.setAction(ACTION_SELECT)

	# ----------------------------------------------------------------------
	# Find item selected
	# ----------------------------------------------------------------------
	def click(self, event):
		self.focus_set()
		self._x = self._xp = event.x
		self._y = self._yp = event.y

		if event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK:
			self.actionGantry(event.x, event.y)
			return

		elif self.action == ACTION_SELECT:
			#if event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK:
			#self._mouseAction = ACTION_SELECT
			#else:
			self._mouseAction = ACTION_SELECT_SINGLE

		elif self.action in (ACTION_MOVE, ACTION_RULER):
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			if self.action == ACTION_RULER and self._vector is not None:
				# Check if we hit the existing ruler
				coords = self.coords(self._vector)
				if abs(coords[0]-i)<=CLOSE_DISTANCE and abs(coords[1]-j<=CLOSE_DISTANCE):
					# swap coordinates
					coords[0],coords[2] = coords[2], coords[0]
					coords[1],coords[3] = coords[3], coords[1]
					self.coords(self._vector, *coords)
					self._vx0, self._vy0, self._vz0 = self.canvas2xyz(coords[0], coords[1])
					self._mouseAction = self.action
					return
				elif abs(coords[2]-i)<=CLOSE_DISTANCE and abs(coords[3]-j<=CLOSE_DISTANCE):
					self._mouseAction = self.action
					return

			if self._vector: self.delete(self._vector)
			if self.action == ACTION_MOVE:
				# Check if we clicked on a selected item
				try:
					closest = self.gettags(self.find_closest(i,j,CLOSE_DISTANCE))
					if "sel" not in closest and "sel2" not in closest:
						self._mouseAction = ACTION_SELECT_SINGLE
						return
					fill  = MOVE_COLOR
					arrow = LAST
				except:
					self._mouseAction = ACTION_SELECT_SINGLE
					return
			else:
				fill  = RULER_COLOR
				arrow = BOTH
			self._vector = self.create_line((i,j,i,j), fill=fill, arrow=arrow)
			self._vx0, self._vy0, self._vz0 = self.canvas2xyz(i,j)
			self._mouseAction = self.action

		# Move gantry to position
		elif self.action == ACTION_GANTRY:
			self.actionGantry(event.x,event.y)

		# Set coordinate origin
		elif self.action == ACTION_ORIGIN:
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			x,y,z = self.canvas2xyz(i,j)
			self.app.insertCommand("origin %g %g %g"%(x,y,z),True)
			self.setActionSelect()

	# ----------------------------------------------------------------------
	# Canvas motion button 1
	# ----------------------------------------------------------------------
	def buttonMotion(self, event):
		if self._mouseAction == ACTION_SELECT_AREA:
			self.coords(self._select,
				self.canvasx(self._x),
				self.canvasy(self._y),
				self.canvasx(event.x),
				self.canvasy(event.y))

		elif self._mouseAction in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
			if abs(event.x-self._x)>4 or abs(event.y-self._y)>4:
				self._mouseAction = ACTION_SELECT_AREA
				self._select = self.create_rectangle(
						self.canvasx(self._x),
						self.canvasy(self._y),
						self.canvasx(event.x),
						self.canvasy(event.y),
						outline=BOX_SELECT)

		elif self._mouseAction in (ACTION_MOVE, ACTION_RULER):
			coords = self.coords(self._vector)
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			coords[-2] = i
			coords[-1] = j
			self.coords(self._vector, *coords)
			if self._mouseAction == ACTION_MOVE:
				self.move("sel",  event.x-self._xp, event.y-self._yp)
				self.move("sel2", event.x-self._xp, event.y-self._yp)
				self._xp = event.x
				self._yp = event.y

			self._vx1, self._vy1, self._vz1 = self.canvas2xyz(i,j)
			dx=self._vx1-self._vx0
			dy=self._vy1-self._vy0
			dz=self._vz1-self._vz0
			self.event_generate("<<Status>>",
				data="dx=%g  dy=%g  dz=%g  length=%g  angle=%g"\
					% (dx,dy,dz,math.sqrt(dx**2+dy**2+dz**2),
					math.degrees(math.atan2(dy,dx))))

		self.setStatus(event)

	# ----------------------------------------------------------------------
	# Canvas release button1. Select area
	# ----------------------------------------------------------------------
	def release(self, event):
		if self._mouseAction in (ACTION_SELECT_SINGLE,
				ACTION_SELECT_DOUBLE,
				ACTION_SELECT_AREA):
			if self._mouseAction == ACTION_SELECT_AREA:
				#if event.state & SHIFT_MASK == 0:
				if self._x < event.x:	# From left->right enclosed
					closest = self.find_enclosed(
							self.canvasx(self._x),
							self.canvasy(self._y),
							self.canvasx(event.x),
							self.canvasy(event.y))
				else:			# From right->left overlapping
					closest = self.find_overlapping(
							self.canvasx(self._x),
							self.canvasy(self._y),
							self.canvasx(event.x),
							self.canvasy(event.y))

				self.delete(self._select)
				self._select = None

				items = []
				for i in closest:
					try: items.append(self._items[i])
					except: pass

			elif self._mouseAction in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
				closest = self.find_closest(
						self.canvasx(event.x),
						self.canvasy(event.y),
						CLOSE_DISTANCE)

				items = []
				for i in closest:
					try:
						items.append(self._items[i])
						#i = None
					except KeyError:
						#i = self.find_below(i)
						pass
			if not items: return

			self.app.select(items, self._mouseAction==ACTION_SELECT_DOUBLE,
					event.state&CONTROL_MASK==0)
			self._mouseAction = None

		elif self._mouseAction == ACTION_MOVE:
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			self._vx1, self._vy1, self._vz1 = self.canvas2xyz(i,j)
			dx=self._vx1-self._vx0
			dy=self._vy1-self._vy0
			dz=self._vz1-self._vz0
			self.event_generate("<<Status>>", data="Move by %g, %g, %g"%(dx,dy,dz))
			self.app.insertCommand("move %g %g %g"%(dx,dy,dz),True)

	# ----------------------------------------------------------------------
	def double(self, event):
		#self.app.selectBlocks()
		self._mouseAction = ACTION_SELECT_DOUBLE

	# ----------------------------------------------------------------------
	def setStatus(self, event):
		data="%.4f %.4f %.4f" % self.canvas2xyz(self.canvasx(event.x), self.canvasy(event.y))
		self.event_generate("<<Coords>>", data=data)

	# ----------------------------------------------------------------------
	def motion(self, event):
		self.setStatus(event)

	#----------------------------------------------------------------------
	# Get margins of selected items
	#----------------------------------------------------------------------
	def getMargins(self):
		bbox = self.bbox("sel")
		if not bbox: return None
		x1,y1,x2,y2 = bbox
		dx = (x2-x1-1)/self.zoom
		dy = (y2-y1-1)/self.zoom
		return dx,dy

	# ----------------------------------------------------------------------
	def pan(self, event):
		if self._mouseAction == ACTION_PAN:
			self.scan_dragto(event.x, event.y, gain=1)
		else:
			self.config(cursor=mouseCursor(ACTION_PAN))
			self.scan_mark(event.x, event.y)
			self._mouseAction = ACTION_PAN

	# ----------------------------------------------------------------------
	def panRelease(self, event):
		self._mouseAction = None
		self.config(cursor=mouseCursor(self.action))

	# ----------------------------------------------------------------------
	def panLeft(self, event=None):
		self.xview(SCROLL, -1, UNITS)

	def panRight(self, event=None):
		self.xview(SCROLL,  1, UNITS)

	def panUp(self, event=None):
		self.yview(SCROLL, -1, UNITS)

	def panDown(self, event=None):
		self.yview(SCROLL,  1, UNITS)

	# ----------------------------------------------------------------------
	def zoomCanvas(self, x, y, zoom):
		self._tx = x
		self._ty = y
		self._tzoom *= zoom
		if self._tafter:
			self.after_cancel(self._tafter)
		self._tafter = self.after(50, self._zoomCanvas)

	# ----------------------------------------------------------------------
	# Zoom on screen position x,y by a factor zoom
	# ----------------------------------------------------------------------
	def _zoomCanvas(self, event=None): #x, y, zoom):
		self._tafter = None
		x = self._tx
		y = self._ty
		zoom = self._tzoom

		#def zoomCanvas(self, x, y, zoom):
		self._tzoom = 1.0

		self.zoom *= zoom

		x0 = self.canvasx(0)
		y0 = self.canvasy(0)

		for i in self.find_all():
			self.scale(i, 0, 0, zoom, zoom)

		# Update last insert
		if self._lastGantry:
			self._drawGantry(*self.plotCoords([self._lastGantry])[0])
		else:
			self._drawGantry(0,0)

		self._updateScrollBars()
		x0 -= self.canvasx(0)
		y0 -= self.canvasy(0)

		# Perform pin zoom
		dx = self.canvasx(x) * (1.0-zoom)
		dy = self.canvasy(y) * (1.0-zoom)

		# Drag to new location to center viewport
		self.scan_mark(0,0)
		self.scan_dragto(int(round(dx-x0)), int(round(dy-y0)), 1)

		# Resize probe image if any
		if self._probeImage:
			self._projectProbeImage()
			self.itemconfig(self._probeImage, image=self._tkimage)

	# ----------------------------------------------------------------------
	# Return selected objects bounding box
	# ----------------------------------------------------------------------
	def selBbox(self):
		x1 = None
		bb = self.bbox('sel')
		if bb is not None:
			x1,y1,x2,y2 = bb

		bb = self.bbox('sel2')
		if bb is not None:
			if x1 is not None:
				x1 = min(x1,bb[0])
				y1 = min(y1,bb[1])
				x2 = max(x2,bb[2])
				y2 = max(y2,bb[3])
				return x1,y1,x2,y2
			else:
				return bb

		if x1 is None:
			return self.bbox('all')
		return x1,y1,x2,y2

	# ----------------------------------------------------------------------
	# Zoom to Fit to Screen
	# ----------------------------------------------------------------------
	def fit2Screen(self, event=None):
		bb = self.selBbox()
		if bb is None: return
		x1,y1,x2,y2 = bb

		try:
			zx = float(self.winfo_width()) / (x2-x1)
		except:
			return
		try:
			zy = float(self.winfo_height()) / (y2-y1)
		except:
			return
		if zx > 1.0:
			self._tzoom = min(zx,zy)
		else:
			self._tzoom = max(zx,zy)

		self._tx = self._ty = 0	
		self._zoomCanvas()

		# Find position of new selection
		x1,y1,x2,y2 = self.selBbox()
		xm = (x1+x2)//2
		ym = (y1+y2)//2
		sx1,sy1,sx2,sy2 = map(float,self.cget("scrollregion").split())
		midx = float(xm-sx1) / (sx2-sx1)
		midy = float(ym-sy1) / (sy2-sy1)

		a,b = self.xview()
		d = (b-a)/2.0
		self.xview_moveto(midx-d)

		a,b = self.yview()
		d = (b-a)/2.0
		self.yview_moveto(midy-d)

	# ----------------------------------------------------------------------
	def menuZoomIn(self, event=None):
		x = int(self.cget("width" ))//2
		y = int(self.cget("height"))//2
		self.zoomCanvas(x, y, 2.0)

	# ----------------------------------------------------------------------
	def menuZoomOut(self, event=None):
		x = int(self.cget("width" ))//2
		y = int(self.cget("height"))//2
		self.zoomCanvas(x, y, 0.5)

	# ----------------------------------------------------------------------
	def mouseZoomIn(self, event):
		self.zoomCanvas(event.x, event.y, 1.25)

	# ----------------------------------------------------------------------
	def mouseZoomOut(self,event):
		self.zoomCanvas(event.x, event.y, 1.0/1.25)

	# ----------------------------------------------------------------------
	# Change the insert marker location
	# ----------------------------------------------------------------------
	def activeMarker(self, item):
		if item is None: return
		b,i = item
		if i is None: return
		block = self.gcode[b]
		item = block._path[i]

		if item is not None and item != self._lastActive:
			if self._lastActive is not None:
				self.itemconfig(self._lastActive, arrow=NONE)
			self._lastActive = item
			self.itemconfig(self._lastActive, arrow=LAST)

	#----------------------------------------------------------------------
	# Display gantry
	#----------------------------------------------------------------------
	def gantry(self, wx, wy, wz, mx, my, mz):
		self._lastGantry = (wx,wy,wz)
		self._drawGantry(*self.plotCoords([(wx,wy,wz)])[0])

		dx = wx-mx
		dy = wy-my
		dz = wz-mz
		if abs(dx-self._dx) > 0.0001 or \
		   abs(dy-self._dy) > 0.0001 or \
		   abs(dz-self._dz) > 0.0001:
			self._dx = dx
			self._dy = dy
			self._dz = dz

			if not self.draw_workarea: return
			xmin = self._dx-CNC.travel_x
			ymin = self._dy-CNC.travel_y
			zmin = self._dz-CNC.travel_z
			xmax = self._dx
			ymax = self._dy
			zmax = self._dz

			xyz = [(xmin, ymin, 0.),
			       (xmax, ymin, 0.),
			       (xmax, ymax, 0.),
			       (xmin, ymax, 0.),
			       (xmin, ymin, 0.)]

			coords = []
			for x,y in self.plotCoords(xyz):
				coords.append(x)
				coords.append(y)
			self.coords(self._workarea, *coords)

	#----------------------------------------------------------------------
	# Clear highlight of selection
	#----------------------------------------------------------------------
	def clearSelection(self):
		if self._lastActive is not None:
			self.itemconfig(self._lastActive, arrow=NONE)
			self._lastActive = None
		self.itemconfig("sel",  width=1, fill=ENABLE_COLOR)
		self.itemconfig("sel2", width=1, fill=DISABLE_COLOR)
		self.dtag("sel")
		self.dtag("sel2")

	#----------------------------------------------------------------------
	# Highlight selected items
	#----------------------------------------------------------------------
	def select(self, items):
		for b, i in items:
			block = self.gcode[b]
			if block.enable:
				sel = "sel"
			else:
				sel = "sel2"
			if i is None:
				for path in block._path:
					if path is not None:
						self.addtag_withtag(sel, path)
			else:
				path = block._path[i]
				if path:
					self.addtag_withtag(sel, path)

		self.itemconfig("sel",  width=2, fill=SELECT_COLOR)
		self.itemconfig("sel2", width=2, fill=SELECT2_COLOR)

		margins = self.getMargins()

	#----------------------------------------------------------------------
	# Parse and draw the file from the editor to g-code commands
	#----------------------------------------------------------------------
	def draw(self, view=None): #, lines):
		if self._inDraw : return
		self._inDraw  = True

		self._tzoom  = 1.0
		self._tafter = None
		xyz = self.canvas2xyz(
				self.canvasx(self.winfo_width()/2),
				self.canvasy(self.winfo_height()/2))

		if view is not None: self.view = view

		self._last = (0.,0.,0.)
		self.initPosition()
		drawG = self.draw_rapid or self.draw_paths or self.draw_margin
		for i,block in enumerate(self.gcode.blocks):
			block.resetPath(self.cnc.x, self.cnc.y, self.cnc.z)
			for j,line in enumerate(block):
				#cmd = self.cnc.parseLine(line)
				try:
					cmd = CNC.breakLine(self.gcode.evaluate(CNC.parseLine2(line)))
				except:
					sys.stderr.write(">>> ERROR: %s\n"%(str(sys.exc_info()[1])))
					sys.stderr.write("     line: %s\n"%(line))
					cmd = None

				if cmd is None or not drawG:
					block.addPath(None)
				else:
					path = self.drawPath(cmd, block.enable)
					self._items[path] = i,j
					block.addPath(path)
			block.endPath(self.cnc.x, self.cnc.y, self.cnc.z)

		self.drawGrid()
		self.drawMargin()
		self.drawWorkarea()
		self.drawProbe()
		self.drawAxes()
#		self.tag_lower(self._workarea)
		if self._gantry1: self.tag_raise(self._gantry1)
		if self._gantry2: self.tag_raise(self._gantry2)
		self._updateScrollBars()

		ij = self.plotCoords([xyz])[0]
		dx = int(round(self.canvasx(self.winfo_width()/2)  - ij[0]))
		dy = int(round(self.canvasy(self.winfo_height()/2) - ij[1]))
		self.scan_mark(0,0)
		self.scan_dragto(int(round(dx)), int(round(dy)), 1)

		self._inDraw  = False

	#----------------------------------------------------------------------
	def initPosition(self):
		self.delete(ALL)
		if self.view in (VIEW_XY, VIEW_XZ, VIEW_YZ):
			# FIXME should be done as a triangle for XZ and YZ
			self._gantry1 = self.create_oval(
					(-GANTRY_R,-GANTRY_R),
					( GANTRY_R, GANTRY_R),
					width=2,
					outline=GANTRY_COLOR)
			self._gantry2 = None
		else:
			self._gantry1 = self.create_oval(
					(-GANTRY_X, -GANTRY_H-GANTRY_Y, GANTRY_X, -GANTRY_H+GANTRY_Y),
					width=2,
					outline=GANTRY_COLOR)
			self._gantry2 = self.create_line(
					(-GANTRY_X, -GANTRY_H, 0, 0, GANTRY_X, -GANTRY_H),
					width=2,
					fill=GANTRY_COLOR)

		self._lastInsert = None
		self._lastActive = None
		self._select = None
		self._vector = None
		self._items.clear()
		self.cnc.initPath()

	#----------------------------------------------------------------------
	def _drawGantry(self, x, y):
		if self._gantry2 is None:
			self.coords(self._gantry1,
				(x-GANTRY_R, y-GANTRY_R,
				 x+GANTRY_R, y+GANTRY_R))
		else:
			self.coords(self._gantry1,
					(x-GANTRY_X, y-GANTRY_H-GANTRY_Y,
					 x+GANTRY_X, y-GANTRY_H+GANTRY_Y))
			self.coords(self._gantry2,
					(x-GANTRY_X, y-GANTRY_H,
					 x, y,
					 x+GANTRY_X, y-GANTRY_H))

	#----------------------------------------------------------------------
	def drawAxes(self):
		self.delete("Axes")
		if not self.draw_axes: return
		if CNC.inch:
			s = 10.0
		else:
			s = 100.0
		xyz = [(0.,0.,0.), (s, 0., 0.)]
		self.create_line(self.plotCoords(xyz), tag="Axes", fill="Red", dash=(3,1), arrow=LAST)

		xyz = [(0.,0.,0.), (0., s, 0.)]
		self.create_line(self.plotCoords(xyz), tag="Axes", fill="Green", dash=(3,1), arrow=LAST)

		xyz = [(0.,0.,0.), (0., 0., s)]
		self.create_line(self.plotCoords(xyz), tag="Axes", fill="Blue",  dash=(3,1), arrow=LAST)

	#----------------------------------------------------------------------
	def drawMargin(self):
		if self._margin: self.delete(self._margin)
		if not self.draw_margin: return
		if not CNC.isMarginValid(): return
		xyz = [(CNC.vars["xmin"], CNC.vars["ymin"], 0.),
		       (CNC.vars["xmax"], CNC.vars["ymin"], 0.),
		       (CNC.vars["xmax"], CNC.vars["ymax"], 0.),
		       (CNC.vars["xmin"], CNC.vars["ymax"], 0.),
		       (CNC.vars["xmin"], CNC.vars["ymin"], 0.)]
		self._margin = self.create_line(
					self.plotCoords(xyz),
					fill=MARGIN_COLOR)
		self.tag_lower(self._margin)

	#----------------------------------------------------------------------
	def drawWorkarea(self):
		if self._workarea: self.delete(self._workarea)
		if not self.draw_workarea: return

		xmin = self._dx-CNC.travel_x
		ymin = self._dy-CNC.travel_y
		zmin = self._dz-CNC.travel_z
		xmax = self._dx
		ymax = self._dy
		zmax = self._dz

		xyz = [(xmin, ymin, 0.),
		       (xmax, ymin, 0.),
		       (xmax, ymax, 0.),
		       (xmin, ymax, 0.),
		       (xmin, ymin, 0.)]
		self._workarea = self.create_line(
					self.plotCoords(xyz),
					fill="Orange", dash=(3,1))
		self.tag_lower(self._workarea)

	#----------------------------------------------------------------------
	def drawGrid(self):
		self.delete("Grid")
		if not self.draw_grid: return
		if self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
			xmin = (CNC.vars["xmin"]//10)  *10
			xmax = (CNC.vars["xmax"]//10+1)*10
			ymin = (CNC.vars["ymin"]//10)  *10
			ymax = (CNC.vars["ymax"]//10+1)*10
			for i in range(int(CNC.vars["ymin"]//10), int(CNC.vars["ymax"]//10)+2):
				y = i*10.0
				xyz = [(xmin,y,0), (xmax,y,0)]
				item = self.create_line(self.plotCoords(xyz),
							tag="Grid",
							fill=GRID_COLOR,
							dash=(1,3))
				self.tag_lower(item)

			for i in range(int(CNC.vars["xmin"]//10), int(CNC.vars["xmax"]//10)+2):
				x = i*10.0
				xyz = [(x,ymin,0), (x,ymax,0)]
				item = self.create_line(self.plotCoords(xyz),
							fill=GRID_COLOR,
							tag="Grid",
							dash=(1,3))
				self.tag_lower(item)

	#----------------------------------------------------------------------
	# Display probe
	#----------------------------------------------------------------------
	def drawProbe(self):
		self.delete("Probe")
		if self._probeImage:
			self.delete(self._probeImage)
			self._probeImage = None
		if not self.draw_probe: return
		if self.view in (VIEW_XZ, VIEW_YZ): return

		# Draw probe grid
		probe = self.gcode.probe
		for x in bmath.frange(probe.xmin, probe.xmax+0.00001, probe.xstep()):
			xyz = [(x,probe.ymin,0.), (x,probe.ymax,0.)]
			item = self.create_line(self.plotCoords(xyz),
						tag="Probe",
						fill='Yellow')
			self.tag_lower(item)

		for y in bmath.frange(probe.ymin, probe.ymax+0.00001, probe.ystep()):
			xyz = [(probe.xmin,y,0.), (probe.xmax,y,0.)]
			item = self.create_line(self.plotCoords(xyz),
						tag="Probe",
						fill='Yellow')
			self.tag_lower(item)

		# Draw probe points
		for i,uv in enumerate(self.plotCoords(probe.points)):
			item = self.create_text(uv,
						text="%.*f"%(CNC.digits,probe.points[i][2]),
						tag="Probe",
						justify=CENTER,
						fill="Green")
			self.tag_lower(item)

		# Draw image map if numpy exists
		if numpy is not None and probe.matrix and self.view == VIEW_XY:
			array = numpy.array(list(reversed(probe.matrix)), numpy.float32)

			lw = array.min()
			hg = array.max()
			mx = max(abs(hg),abs(lw))
			#print "matrix=",probe.matrix
			#print "size=",array.size
			#print "array=",array
			#print "Limits:", lw, hg, mx
			# scale should be:
			#  -mx   .. 0 .. mx
			#  -127     0    127
			# -127 = light-blue
			#    0 = white
			#  127 = light-red
			dc = mx/127.		# step in colors
			palette = []
			for x in bmath.frange(lw, hg+1e-10, (hg-lw)/255.):
				i = int(math.floor(x / dc))
				if i<0:
					palette.append(0xff+i)
					palette.append(0xff+i)
					palette.append(0xff)
				elif i>0:
					palette.append(0xff)
					palette.append(0xff-i)
					palette.append(0xff-i)
				else:
					palette.append(0xff)
					palette.append(0xff)
					palette.append(0xff)
				#print ">>", x,i,palette[-3], palette[-2], palette[-1]
			#print "palette size=",len(palette)/3
			array = numpy.floor((array-lw)/(hg-lw)*255)
			self._image = Image.fromarray(array.astype(numpy.int16)).convert('L')
			self._image.putpalette(palette)
			self._image = self._image.convert("RGB")

			self._projectProbeImage()
			x,y = self.plotCoords([(probe.xmin, probe.ymin, 0.)])[0]
			self._probeImage = self.create_image(x,y, image=self._tkimage, anchor='sw')
			self.tag_lower(self._probeImage)

	#----------------------------------------------------------------------
	# Create the tkimage for the current projection
	#----------------------------------------------------------------------
	def _projectProbeImage(self):
		probe = self.gcode.probe
		size = (int((probe.xmax-probe.xmin + probe._xstep)*self.zoom),
			int((probe.ymax-probe.ymin + probe._ystep)*self.zoom))
		marginx = int(probe._xstep/2. * self.zoom)
		marginy = int(probe._ystep/2. * self.zoom)
		crop = (marginx, marginy, size[0]-marginx, size[1]-marginy)

		image = self._image.resize((size), resample=RESAMPLE).crop(crop)
		self._tkimage = ImageTk.PhotoImage(image)

#			if self.view == VIEW_ISO1:
#				w, h = size
#				size2 = (int(S60*(w+h)),
#					 int(C60*(w+h)))
#				image2 = self._image.transform(size2, Image.AFFINE,
#					( 0.5/S60, 0.5/C60, -h/2,
#					 -0.5/S60, 0.5/C60,  h/2),
#					 resample=RESAMPLE)

	#----------------------------------------------------------------------
	# Create path for one g command
	#----------------------------------------------------------------------
	def drawPath(self, cmds, enable=True):
		self.cnc.processPath(cmds)
		xyz = self.cnc.motionPath()
		self.cnc.motionPathEnd()
		if xyz:
			length = self.cnc.pathLength(xyz)
			self.cnc.pathMargins(xyz)
			if enable:
				if self.cnc.gcode == 0 and self.draw_rapid:
					xyz[0] = self._last
				self._last = xyz[-1]
			else:
				if self.cnc.gcode == 0:
					return None
			coords = self.plotCoords(xyz)
			if coords:
				if enable:
					fill = ENABLE_COLOR
				else:
					fill = DISABLE_COLOR
				if self.cnc.gcode == 0:
					if self.draw_rapid:
						return self.create_line(coords, fill=fill, width=0, dash=(4,3))
				elif self.draw_paths:
					return self.create_line(coords, fill=fill, width=0, cap="projecting")
		return None

	#----------------------------------------------------------------------
	# Return plotting coordinates for a 3d xyz path
	#----------------------------------------------------------------------
	def plotCoords(self, xyz):
		coords = None
		if self.view == VIEW_XY:
			coords = [(p[0]*self.zoom,-p[1]*self.zoom) for p in xyz]

		elif self.view == VIEW_XZ:
			coords = [(p[0]*self.zoom,-p[2]*self.zoom) for p in xyz]

		elif self.view == VIEW_YZ:
			coords = [(p[1]*self.zoom,-p[2]*self.zoom) for p in xyz]

		elif self.view == VIEW_ISO1:
			coords = [(( p[0]*S60 + p[1]*S60)*self.zoom,
				   (+p[0]*C60 - p[1]*C60 - p[2])*self.zoom)
					for p in xyz]

		elif self.view == VIEW_ISO2:
			coords = [(( p[0]*S60 - p[1]*S60)*self.zoom,
				   (-p[0]*C60 - p[1]*C60 - p[2])*self.zoom)
					for p in xyz]

		elif self.view == VIEW_ISO3:
			coords = [((-p[0]*S60 - p[1]*S60)*self.zoom,
				   (-p[0]*C60 + p[1]*C60 - p[2])*self.zoom)
					for p in xyz]

		# Check limits
		for i,(x,y) in enumerate(coords):
			if abs(x)>MAXDIST or abs(y)>MAXDIST:
				if   x<-MAXDIST: x = -MAXDIST
				elif x> MAXDIST: x =  MAXDIST
				if   y<-MAXDIST: y = -MAXDIST
				elif y> MAXDIST: y =  MAXDIST
				coords[i] = (x,y)

		return coords

	#----------------------------------------------------------------------
	# Canvas to real coordinates
	#----------------------------------------------------------------------
	def canvas2xyz(self, i, j):
		coords = None
		if self.view == VIEW_XY:
			x =  i / self.zoom
			y = -j / self.zoom
			z = 0

		elif self.view == VIEW_XZ:
			x =  i / self.zoom
			y = 0
			z = -j / self.zoom

		elif self.view == VIEW_YZ:
			x = 0
			y =  i / self.zoom
			z = -j / self.zoom

		elif self.view == VIEW_ISO1:
			x = (i/S60 + j/C60) / self.zoom / 2
			y = (i/S60 - j/C60) / self.zoom / 2
			z = 0

		elif self.view == VIEW_ISO2:
			x =  (i/S60 - j/C60) / self.zoom / 2
			y = -(i/S60 + j/C60) / self.zoom / 2
			z = 0

		elif self.view == VIEW_ISO3:
			x = -(i/S60 + j/C60) / self.zoom / 2
			y = -(i/S60 - j/C60) / self.zoom / 2
			z = 0

		return x,y,z

#==============================================================================
# Canvas Frame with toolbar
#==============================================================================
class CanvasFrame(Frame):
	def __init__(self, master, app, *kw, **kwargs):
		Frame.__init__(self, master, *kw, **kwargs)
		self.app = app

		self.draw_axes   = BooleanVar()
		self.draw_grid   = BooleanVar()
		self.draw_margin = BooleanVar()
		self.draw_probe  = BooleanVar()
		self.draw_paths  = BooleanVar()
		self.draw_rapid  = BooleanVar()
		self.draw_workarea = BooleanVar()
		self.view  = StringVar()

		self.loadConfig()

		self.view.trace('w', self.viewChange)

		toolbar = Frame(self, relief=RAISED)
		toolbar.grid(row=0, column=0, columnspan=2, sticky=EW)

		self.canvas = CNCCanvas(self, app, takefocus=True, background="White")
		self.canvas.grid(row=1, column=0, sticky=NSEW)
		sb = Scrollbar(self, orient=VERTICAL, command=self.canvas.yview)
		sb.grid(row=1, column=1, sticky=NS)
		self.canvas.config(yscrollcommand=sb.set)
		sb = Scrollbar(self, orient=HORIZONTAL, command=self.canvas.xview)
		sb.grid(row=2, column=0, sticky=EW)
		self.canvas.config(xscrollcommand=sb.set)

		self.createCanvasToolbar(toolbar)

		self.grid_rowconfigure(1, weight=1)
		self.grid_columnconfigure(0, weight=1)

	#----------------------------------------------------------------------
	def addWidget(self, widget):
		self.app.widgets.append(widget)

	#----------------------------------------------------------------------
	def loadConfig(self):
		global INSERT_COLOR, GANTRY_COLOR, MARGIN_COLOR, GRID_COLOR
		global BOX_SELECT, ENABLE_COLOR, DISABLE_COLOR, SELECT_COLOR
		global SELECT2_COLOR, PROCESS_COLOR, MOVE_COLOR, RULER_COLOR

		self.draw_axes.set(    bool(int(Utils.getBool("Canvas", "axes",    True))))
		self.draw_grid.set(    bool(int(Utils.getBool("Canvas", "grid",    True))))
		self.draw_margin.set(  bool(int(Utils.getBool("Canvas", "margin",  True))))
		self.draw_probe.set(   bool(int(Utils.getBool("Canvas", "probe",   False))))
		self.draw_paths.set(   bool(int(Utils.getBool("Canvas", "paths",   True))))
		self.draw_rapid.set(   bool(int(Utils.getBool("Canvas", "rapid",   True))))
		self.draw_workarea.set(bool(int(Utils.getBool("Canvas", "workarea",True))))

		self.view.set(Utils.getStr("Canvas", "view", VIEWS[0]))

		INSERT_COLOR  = Utils.getStr("Color", "canvas.insert", INSERT_COLOR)
		GANTRY_COLOR  = Utils.getStr("Color", "canvas.gantry", GANTRY_COLOR)
		MARGIN_COLOR  = Utils.getStr("Color", "canvas.margin", MARGIN_COLOR)
		GRID_COLOR    = Utils.getStr("Color", "canvas.grid",   GRID_COLOR)
		BOX_SELECT    = Utils.getStr("Color", "canvas.box",    BOX_SELECT)
		ENABLE_COLOR  = Utils.getStr("Color", "canvas.enable", ENABLE_COLOR)
		DISABLE_COLOR = Utils.getStr("Color", "canvas.disable",DISABLE_COLOR)
		SELECT_COLOR  = Utils.getStr("Color", "canvas.select", SELECT_COLOR)
		SELECT2_COLOR = Utils.getStr("Color", "canvas.select2",SELECT2_COLOR)
		PROCESS_COLOR = Utils.getStr("Color", "canvas.process",PROCESS_COLOR)
		MOVE_COLOR    = Utils.getStr("Color", "canvas.move",   MOVE_COLOR)
		RULER_COLOR   = Utils.getStr("Color", "canvas.ruler",  RULER_COLOR)

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setStr( "Canvas", "view",    self.view.get())
		Utils.setBool("Canvas", "axes",    self.draw_axes.get())
		Utils.setBool("Canvas", "grid",    self.draw_grid.get())
		Utils.setBool("Canvas", "margin",  self.draw_margin.get())
		Utils.setBool("Canvas", "probe",   self.draw_probe.get())
		Utils.setBool("Canvas", "paths",   self.draw_paths.get())
		Utils.setBool("Canvas", "rapid",   self.draw_rapid.get())
		Utils.setBool("Canvas", "workarea",self.draw_workarea.get())

	#----------------------------------------------------------------------
	# Canvas toolbar FIXME XXX should be moved to CNCCanvas
	#----------------------------------------------------------------------
	def createCanvasToolbar(self, toolbar):
		b = OptionMenu(toolbar, self.view, *VIEWS)
		b.config(padx=0, pady=1)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Change viewing angle")

		b = Button(toolbar, image=Utils.icons["zoom_in"],
				command=self.canvas.menuZoomIn)
		tkExtra.Balloon.set(b, "Zoom In [Ctrl-=]")
		b.pack(side=LEFT)

		b = Button(toolbar, image=Utils.icons["zoom_out"],
				command=self.canvas.menuZoomOut)
		tkExtra.Balloon.set(b, "Zoom Out [Ctrl--]")
		b.pack(side=LEFT)

		b = Button(toolbar, image=Utils.icons["zoom_on"],
				command=self.canvas.fit2Screen)
		tkExtra.Balloon.set(b, "Fit to screen [F]")
		b.pack(side=LEFT)


		Label(toolbar, text="Tool:",
				image=Utils.icons["sep"],
				compound=LEFT).pack(side=LEFT, padx=2)
		# -----
		# Tools
		# -----
		b = Radiobutton(toolbar, image=Utils.icons["select"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=ACTION_SELECT,
					command=self.canvas.setActionSelect)
		tkExtra.Balloon.set(b, "Select tool [S]")
		self.addWidget(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["gantry"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=ACTION_GANTRY,
					command=self.canvas.setActionGantry)
		tkExtra.Balloon.set(b, "Move gantry [G]")
		self.addWidget(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["ruler"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=ACTION_RULER,
					command=self.canvas.setActionRuler)
		tkExtra.Balloon.set(b, "Ruler [R]")
		b.pack(side=LEFT)

		# -----------
		# Draw flags
		# -----------
		Label(toolbar, text="Draw:",
				image=Utils.icons["sep"],
				compound=LEFT).pack(side=LEFT, padx=2)

		b = Checkbutton(toolbar,
				image=Utils.icons["axes"],
				indicatoron=False,
				variable=self.draw_axes,
				command=self.drawAxes)
		tkExtra.Balloon.set(b, "Toggle display of axes")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["grid"],
				indicatoron=False,
				variable=self.draw_grid,
				command=self.drawGrid)
		tkExtra.Balloon.set(b, "Toggle display of grid lines")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["margins"],
				indicatoron=False,
				variable=self.draw_margin,
				command=self.drawMargin)
		tkExtra.Balloon.set(b, "Toggle display of margins")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				text="P",
				image=Utils.icons["measure"],
				indicatoron=False,
				variable=self.draw_probe,
				command=self.drawProbe)
		tkExtra.Balloon.set(b, "Toggle display of probe")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["endmill"],
				indicatoron=False,
				variable=self.draw_paths,
				command=self.toggleDrawFlag)
		tkExtra.Balloon.set(b, "Toggle display of paths (G1,G2,G3)")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["rapid"],
				indicatoron=False,
				variable=self.draw_rapid,
				command=self.toggleDrawFlag)
		tkExtra.Balloon.set(b, "Toggle display of rapid motion (G0)")
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["workspace"],
				indicatoron=False,
				variable=self.draw_workarea,
				command=self.drawWorkarea)
		tkExtra.Balloon.set(b, "Toggle display of workarea")
		b.pack(side=LEFT)

	#----------------------------------------------------------------------
	def viewChange(self, a=None, b=None, c=None):
		self.event_generate("<<ViewChange>>")

	# ----------------------------------------------------------------------
	def viewXY(self, event=None):
		self.view.set(VIEWS[VIEW_XY])

	# ----------------------------------------------------------------------
	def viewXZ(self, event=None):
		self.view.set(VIEWS[VIEW_XZ])

	# ----------------------------------------------------------------------
	def viewYZ(self, event=None):
		self.view.set(VIEWS[VIEW_YZ])

	# ----------------------------------------------------------------------
	def viewISO1(self, event=None):
		self.view.set(VIEWS[VIEW_ISO1])

	# ----------------------------------------------------------------------
	def viewISO2(self, event=None):
		self.view.set(VIEWS[VIEW_ISO2])

	# ----------------------------------------------------------------------
	def viewISO3(self, event=None):
		self.view.set(VIEWS[VIEW_ISO3])

	#----------------------------------------------------------------------
	def toggleDrawFlag(self):
		self.canvas.draw_axes     = self.draw_axes.get()
		self.canvas.draw_grid     = self.draw_grid.get()
		self.canvas.draw_margin   = self.draw_margin.get()
		self.canvas.draw_probe    = self.draw_probe.get()
		self.canvas.draw_paths    = self.draw_paths.get()
		self.canvas.draw_rapid    = self.draw_rapid.get()
		self.canvas.draw_workarea = self.draw_workarea.get()
		self.event_generate("<<ViewChange>>")

	#----------------------------------------------------------------------
	def drawAxes(self, value=None):
		if value is not None: self.draw_axes.set(value)
		self.canvas.draw_axes = self.draw_axes.get()
		self.canvas.drawAxes()

	#----------------------------------------------------------------------
	def drawGrid(self, value=None):
		if value is not None: self.draw_grid.set(value)
		self.canvas.draw_grid = self.draw_grid.get()
		self.canvas.drawGrid()

	#----------------------------------------------------------------------
	def drawMargin(self, value=None):
		if value is not None: self.draw_margin.set(value)
		self.canvas.draw_margin = self.draw_margin.get()
		self.canvas.drawMargin()

	#----------------------------------------------------------------------
	def drawProbe(self, value=None):
		if value is not None: self.draw_probe.set(value)
		self.canvas.draw_probe = self.draw_probe.get()
		self.canvas.drawProbe()

	#----------------------------------------------------------------------
	def drawWorkarea(self, value=None):
		if value is not None: self.draw_workarea.set(value)
		self.canvas.draw_workarea = self.draw_workarea.get()
		self.canvas.drawWorkarea()
