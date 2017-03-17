# -*- coding: ascii -*-
# $Id: CNCCanvas.py,v 1.7 2014/10/15 15:04:06 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math
import time
import bmath
try:
	from Tkinter import *
	import Tkinter
except ImportError:
	from tkinter import *
	import tkinter as Tkinter

from CNC import Tab, CNC
import Utils
import Camera
import tkExtra

# Probe mapping we need PIL and numpy
try:
	from PIL import Image, ImageTk
	import numpy
	# Resampling image based on PIL library and converting to RGB.
	# options possible: NEAREST, BILINEAR, BICUBIC, ANTIALIAS
	RESAMPLE = Image.NEAREST	# resize type
	#RESAMPLE = Image.BILINEAR	# resize type
except:
	numpy    = None
	RESAMPLE = None

VIEW_XY   = 0
VIEW_XZ   = 1
VIEW_YZ   = 2
VIEW_ISO1 = 3
VIEW_ISO2 = 4
VIEW_ISO3 = 5
VIEW_XAF  = 6
VIEWS     = ["X-Y", "X-Z", "Y-Z", "ISO1", "ISO2", "ISO3", "XA (flat)"]

INSERT_WIDTH2 =  3
GANTRY_R      =  4
GANTRY_X      = GANTRY_R*2	# 10
GANTRY_Y      = GANTRY_R	# 5
GANTRY_H      = GANTRY_R*5	# 20
DRAW_TIME     = 5		# Maximum draw time permitted

INSERT_COLOR  = "Blue"
GANTRY_COLOR  = "Red"
MARGIN_COLOR  = "Magenta"
GRID_COLOR    = "Gray"
BOX_SELECT    = "Cyan"
TAB_COLOR     = "DarkOrange"
WORK_COLOR    = "Orange"
CAMERA_COLOR  = "Cyan"
CANVAS_COLOR  = "White"

ENABLE_COLOR  = "Black"
DISABLE_COLOR = "LightGray"
SELECT_COLOR  = "Blue"
SELECT2_COLOR = "DarkCyan"
PROCESS_COLOR = "Green"

MOVE_COLOR    = "DarkCyan"
RULER_COLOR   = "Green"
PROBE_TEXT_COLOR = "Green"

INFO_COLOR    = "Gold"

SELECTION_TAGS = ("sel", "sel2", "sel3", "sel4")

ACTION_SELECT        =  0
ACTION_SELECT_SINGLE =  1
ACTION_SELECT_AREA   =  2
ACTION_SELECT_DOUBLE =  3

ACTION_PAN           = 10
ACTION_ORIGIN        = 11

ACTION_MOVE          = 20
ACTION_ROTATE        = 21
ACTION_GANTRY        = 22
ACTION_WPOS          = 23

ACTION_RULER         = 30
ACTION_ADDORIENT     = 31

#ACTION_ADDTAB        = 40

SHIFT_MASK   = 1
CONTROL_MASK = 4
ALT_MASK     = 8
CONTROLSHIFT_MASK = SHIFT_MASK | CONTROL_MASK
CLOSE_DISTANCE = 5
MAXDIST      = 10000
ZOOM         = 1.25

S60 = math.sin(math.radians(60))
C60 = math.cos(math.radians(60))

DEF_CURSOR = ""
MOUSE_CURSOR = {
	ACTION_SELECT        : DEF_CURSOR,
	ACTION_SELECT_AREA   : "right_ptr",

	ACTION_PAN           : "fleur",
	ACTION_ORIGIN        : "cross",
#	ACTION_ORBIT         : "exchange",
#	ACTION_ZOOM_IN       : "sizing",
#	ACTION_ZOOM_OUT      : "sizing",
#	ACTION_ZOOM_ON       : "sizing",

#	ACTION_VIEW_CENTER   : "cross",
#	ACTION_VIEW_MOVE     : "fleur",
#	ACTION_VIEW_ROTATE   : "exchange",

#	ACTION_ADDTAB        : "tcross",

	ACTION_MOVE          : "hand1",
	ACTION_ROTATE        : "exchange",
	ACTION_GANTRY        : "target",
	ACTION_WPOS          : "diamond_cross",

	ACTION_RULER         : "tcross",
	ACTION_ADDORIENT     : "tcross",

#	ACTION_EDIT          : "pencil",
}

# ------------------------------------------------------------------------------
def mouseCursor(action):
	return MOUSE_CURSOR.get(action, DEF_CURSOR)

#==============================================================================
# Raise an alarm exception
#==============================================================================
class AlarmException(Exception):
	pass

#==============================================================================
# Drawing canvas
#==============================================================================
class CNCCanvas(Canvas):
	def __init__(self, master, app, *kw, **kwargs):
		Canvas.__init__(self, master, *kw, **kwargs)

		# Global variables
		self.view  = 0
		self.app   = app
		self.cnc   = app.cnc
		self.gcode = app.gcode
		self.actionVar = IntVar()

		# Canvas binding
		self.bind('<Configure>',	self.configureEvent)
		self.bind('<Motion>',		self.motion)

		self.bind('<Button-1>',		self.click)
		self.bind('<B1-Motion>',	self.buttonMotion)
		self.bind('<ButtonRelease-1>',	self.release)
		self.bind('<Double-1>',		self.double)

		self.bind('<B2-Motion>',	self.pan)
		self.bind('<ButtonRelease-2>',	self.panRelease)
		self.bind("<Button-4>",		self.mouseZoomIn)
		self.bind("<Button-5>",		self.mouseZoomOut)
		self.bind("<MouseWheel>",	self.wheel)

		self.bind('<Shift-Button-4>',	self.panLeft)
		self.bind('<Shift-Button-5>',	self.panRight)
		self.bind('<Control-Button-4>',	self.panUp)
		self.bind('<Control-Button-5>',	self.panDown)

		self.bind('<Control-Key-Left>',	self.panLeft)
		self.bind('<Control-Key-Right>',self.panRight)
		self.bind('<Control-Key-Up>',	self.panUp)
		self.bind('<Control-Key-Down>',	self.panDown)

		self.bind('<Escape>',		self.actionCancel)
#		self.bind('<Key-a>',		lambda e,s=self : s.event_generate("<<SelectAll>>"))
#		self.bind('<Key-A>',		lambda e,s=self : s.event_generate("<<SelectNone>>"))
#		self.bind('<Key-e>',		lambda e,s=self : s.event_generate("<<Expand>>"))
#		self.bind('<Key-f>',		self.fit2Screen)
#		self.bind('<Key-g>',		self.setActionGantry)
#		self.bind('<Key-l>',		lambda e,s=self : s.event_generate("<<EnableToggle>>"))
#		self.bind('<Key-m>',		self.setActionMove)
#		self.bind('<Key-n>',		lambda e,s=self : s.event_generate("<<ShowInfo>>"))
#		self.bind('<Key-o>',		self.setActionOrigin)
#		self.bind('<Key-r>',		self.setActionRuler)
#		self.bind('<Key-s>',		self.setActionSelect)
##		self.bind('<Key-t>',		self.setActionAddTab)
#		self.bind('<Key-x>',		self.setActionPan)
		self.bind('<Key>',		self.handleKey)

		self.bind('<Control-Key-S>',	self.cameraSave)
		self.bind('<Control-Key-t>',	self.__test)

		self.bind('<Control-Key-equal>',self.menuZoomIn)
		self.bind('<Control-Key-minus>',self.menuZoomOut)

#		self.bind('<Control-Key-x>',	self.cut)
#		self.bind('<Control-Key-c>',	self.copy)
#		self.bind('<Control-Key-v>',	self.paste)

#		self.bind('<Key-space>',	self.commandFocus)
#		self.bind('<Control-Key-space>',self.commandFocus)
#		self.bind('<Control-Key-a>',	self.selectAll)

		self.x0      = 0.0
		self.y0      = 0.0
		self.zoom    = 1.0
		self.__tzoom = 1.0		# delayed zoom (temporary)
		self._items  = {}

		self._x  = self._y  = 0
		self._xp = self._yp = 0
		self.action       = ACTION_SELECT
		self._mouseAction = None
		self._inDraw      = False		# semaphore for parsing
		self._gantry1     = None
		self._gantry2     = None
		self._select      = None
		self._margin      = None
		self._amargin     = None
		self._workarea    = None
		self._vector      = None
		self._lastActive  = None
		self._lastGantry  = None

		self._probeImage  = None
		self._probeTkImage= None
		self._probe       = None

		self.camera          = Camera.Camera("aligncam")
		self.cameraAnchor    = CENTER		# Camera anchor location "" for gantry
		self.cameraScale     = 10.0		# camera pixels/unit
		self.cameraEdge      = False		# edge detection
		self.cameraR         =  1.5875		# circle radius in units (mm/inched)
		self.cameraDx        = 0		# camera shift vs gantry
		self.cameraDy        = 0
		self.cameraZ         = None		# if None it will not make any Z movement for the camera
		self.cameraSwitch    = False		# Look at spindle(False) or camera(True)
		self._cameraAfter    = None		# Camera anchor location "" for gantry
		self._cameraMaxWidth = 640		# on zoom over this size crop the image
		self._cameraMaxHeight= 480
		self._cameraImage    = None
		self._cameraHori     = None		# cross hair items
		self._cameraVert     = None
		self._cameraCircle   = None
		self._cameraCircle2  = None

		self._tab         = None
		self._tabRect     = None

		self.draw_axes    = True		# Drawing flags
		self.draw_grid    = True
		self.draw_margin  = True
		self.draw_probe   = True
		self.draw_workarea= True
		self.draw_paths   = True
		self.draw_rapid   = True		# draw rapid motions
		self._wx = self._wy = self._wz = self._wa= 0.	# work position
		self._dx = self._dy = self._dz = self._da = 0.	# work-machine position

		self._vx0 = self._vy0 = self._vz0 = self._va0 = 0	# vector move coordinates
		self._vx1 = self._vy1 = self._vz1 = self._va1 = 0	# vector move coordinates

		self._orientSelected = None

		#self.config(xscrollincrement=1, yscrollincrement=1)
		self.reset()
		self.initPosition()

	# ----------------------------------------------------------------------
	def reset(self):
		self.zoom = 1.0

	# ----------------------------------------------------------------------
	# Set status message
	# ----------------------------------------------------------------------
	def status(self, msg):
		#self.event_generate("<<Status>>", data=msg.encode("utf8"))
		self.event_generate("<<Status>>", data=msg)

	# ----------------------------------------------------------------------
	def setMouseStatus(self, event):
		data="%.4f %.4f %.4f %.4f" % self.canvas2xyza(self.canvasx(event.x), self.canvasy(event.y))
		self.event_generate("<<Coords>>", data=data)

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
	def handleKey(self, event):
		ctrl  = event.state & CONTROL_MASK
		if event.char == "a":
			self.event_generate("<<SelectAll>>")
		elif event.char == "A":
			self.event_generate("<<SelectNone>>")
		elif event.char == "e":
			self.event_generate("<<Expand>>")
		elif event.char == "f":
			self.fit2Screen()
		elif event.char == "g":
			self.setActionGantry()
		elif event.char == "l":
			self.event_generate("<<EnableToggle>>")
		elif event.char == "m":
			self.setActionMove()
		elif event.char == "n":
			self.event_generate("<<ShowInfo>>")
		elif event.char == "o":
			self.setActionOrigin()
		elif event.char == "r":
			self.setActionRuler()
		elif event.char == "s":
			self.setActionSelect()
#		elif event.char == "t":
#			self.setActionAddTab()
		elif event.char == "x":
			self.setActionPan()
		elif event.char == "z":
			self.menuZoomIn()
		elif event.char == "Z":
			self.menuZoomOut()

	# ----------------------------------------------------------------------
	def setAction(self, action):
		self.action = action
		self.actionVar.set(action)
		self._mouseAction = None
		self.config(cursor=mouseCursor(self.action), background="White")

	# ----------------------------------------------------------------------
	def actionCancel(self, event=None):
		if self.action != ACTION_SELECT or \
		   (self._mouseAction != ACTION_SELECT and self._mouseAction is not None):
			self.setAction(ACTION_SELECT)
			return "break"
		#self.draw()

	# ----------------------------------------------------------------------
	def setActionSelect(self, event=None):
		self.setAction(ACTION_SELECT)
		self.status(_("Select objects with mouse"))

	# ----------------------------------------------------------------------
	def setActionPan(self, event=None):
		self.setAction(ACTION_PAN)
		self.status(_("Pan viewport"))

	# ----------------------------------------------------------------------
	def setActionOrigin(self, event=None):
		self.setAction(ACTION_ORIGIN)
		self.status(_("Click to set the origin (zero)"))

	# ----------------------------------------------------------------------
	def setActionMove(self, event=None):
		self.setAction(ACTION_MOVE)
		self.status(_("Move graphically objects"))

	# ----------------------------------------------------------------------
	def setActionGantry(self, event=None):
		self.setAction(ACTION_GANTRY)
		self.config(background="seashell")
		self.status(_("Move CNC gantry to mouse location"))

	# ----------------------------------------------------------------------
	def setActionWPOS(self, event=None):
		self.setAction(ACTION_WPOS)
		self.config(background="ivory")
		self.status(_("Set mouse location as current machine position (X/Y only)"))

	# ----------------------------------------------------------------------
	def setActionRuler(self, event=None):
		self.setAction(ACTION_RULER)
		self.status(_("Drag a ruler to measure distances"))

	# ----------------------------------------------------------------------
	def setActionAddMarker(self, event=None):
		self.setAction(ACTION_ADDORIENT)
		self.status(_("Add an orientation marker"))

#	# ----------------------------------------------------------------------
#	def setActionAddTab(self, event=None):
#		self.setAction(ACTION_ADDTAB)
#		self.status(_("Draw a square tab"))

	# ----------------------------------------------------------------------
	# Convert canvas cx,cy coordinates to machine space
	# ----------------------------------------------------------------------
	def canvas2Machine(self, cx, cy):
		u = cx / self.zoom
		v = cy / self.zoom

		if self.view == VIEW_XY:
			return u, -v, None, None

		if self.view == VIEW_XAF:
			return u, None, None, -v

		elif self.view == VIEW_XZ:
			return u, None, -v, None

		elif self.view == VIEW_YZ:
			return None, u, -v, None

		elif self.view == VIEW_ISO1:
			return 0.5*(u/S60+v/C60), 0.5*(u/S60-v/C60), None, None

		elif self.view == VIEW_ISO2:
			return 0.5*(u/S60-v/C60), -0.5*(u/S60+v/C60), None, None

		elif self.view == VIEW_ISO3:
			return -0.5*(u/S60+v/C60), -0.5*(u/S60-v/C60), None, None

	# ----------------------------------------------------------------------
	# Image (pixel) coordinates to machine
	# ----------------------------------------------------------------------
	def image2Machine(self, x, y):
		return self.canvas2Machine(self.canvasx(x), self.canvasy(y))

	# ----------------------------------------------------------------------
	# Move gantry to mouse location
	# ----------------------------------------------------------------------
	def actionGantry(self, x, y):
		u,v,w,a = self.image2Machine(x,y)
		self.app.goto(u,v,w,a)
		self.setAction(ACTION_SELECT)

	# ----------------------------------------------------------------------
	# Set the work coordinates to mouse location
	# ----------------------------------------------------------------------
	def actionWPOS(self, x, y):
		u,v,w,a = self.image2Machine(x,y)
		self.app.dro.wcsSet(u,v,w,a)
		self.setAction(ACTION_SELECT)

	# ----------------------------------------------------------------------
	# Add an orientation marker at mouse location
	# ----------------------------------------------------------------------
	def actionAddOrient(self, x, y):
		cx,cy = self.snapPoint(self.canvasx(x), self.canvasy(y))
		u,v,w = self.canvas2Machine(cx,cy)
		if u is None or v is None:
			self.status(_("ERROR: Cannot set X-Y marker  with the current view"))
			return
		self._orientSelected = len(self.gcode.orient)
		self.gcode.orient.add(CNC.vars["wx"], CNC.vars["wy"], u, v)
		self.event_generate("<<OrientSelect>>", data=self._orientSelected)
		#self.drawOrient()
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
					self._vx0, self._vy0, self._vz0, self._va0 = self.canvas2xyza(coords[0], coords[1])
					self._mouseAction = self.action
					return
				elif abs(coords[2]-i)<=CLOSE_DISTANCE and abs(coords[3]-j<=CLOSE_DISTANCE):
					self._mouseAction = self.action
					return

			if self._vector: self.delete(self._vector)
			if self.action == ACTION_MOVE:
				# Check if we clicked on a selected item
				try:
					for item in self.find_overlapping(i-CLOSE_DISTANCE, j-CLOSE_DISTANCE,
								i+CLOSE_DISTANCE, j+CLOSE_DISTANCE):
						tags = self.gettags(item)
						if "sel"  in tags or "sel2" in tags or \
						   "sel3" in tags or "sel4" in tags:
							break
					else:
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
			self._vx0, self._vy0, self._vz0, self._va0 = self.canvas2xyza(i,j)
			self._mouseAction = self.action

		# Move gantry to position
		elif self.action == ACTION_GANTRY:
			self.actionGantry(event.x,event.y)

		# Move gantry to position
		elif self.action == ACTION_WPOS:
			self.actionWPOS(event.x,event.y)

		# Add orientation marker
		elif self.action == ACTION_ADDORIENT:
			self.actionAddOrient(event.x,event.y)

		# Set coordinate origin
		elif self.action == ACTION_ORIGIN:
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			x,y,z,a = self.canvas2xyza(i,j)
			self.app.insertCommand(_("origin %g %g %g %g")%(x,y,z,a),True)
			self.setActionSelect()

		elif self.action == ACTION_PAN:
			self.pan(event)

#		# Add tab
#		elif self.action == ACTION_ADDTAB:
#			i = self.canvasx(event.x)
#			j = self.canvasy(event.y)
#			x,y,z = self.canvas2xyz(i,j)
#			x = round(x,CNC.digits)
#			y = round(y,CNC.digits)
#			z = round(z,CNC.digits)
#			# use the same z as the last tab added in gcode
#			if self.gcode.tabs: z = self.gcode.tabs[-1].z
#			self._tab = Tab(x,y,x,y,z)
#			self._tabRect = self._drawRect(
#						self._tab.x-self._tab.dx, self._tab.y-self._tab.dy,
#						self._tab.x+self._tab.dx, self._tab.y+self._tab.dy,
#						fill=TAB_COLOR)
#			self._mouseAction = self.action

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
				self.move("sel3", event.x-self._xp, event.y-self._yp)
				self.move("sel4", event.x-self._xp, event.y-self._yp)
				self._xp = event.x
				self._yp = event.y

			self._vx1, self._vy1, self._vz1, self._va1 = self.canvas2xyza(i,j)
			dx=self._vx1-self._vx0
			dy=self._vy1-self._vy0
			dz=self._vz1-self._vz0
			da=self._va1-self._va0
			self.status(_("dx=%g  dy=%g  dz=%g  da=%g  length=%g  angle=%g")\
					% (dx,dy,dz,da,math.sqrt(dx**2+dy**2+dz**2),
					math.degrees(math.atan2(dy,dx))))

		elif self._mouseAction == ACTION_PAN:
			self.pan(event)

		# Resize tab
#		elif self._mouseAction == ACTION_ADDTAB:
#			i = self.canvasx(event.x)
#			j = self.canvasy(event.y)
#			x,y,z = self.canvas2xyz(i,j)
#			x = round(x,CNC.digits)
#			y = round(y,CNC.digits)
#			self._tab.xmax = x
#			self._tab.ymax = y
#			self._rectCoords(self._tabRect,
#					self._tab.x-self._tab.dx, self._tab.y-self._tab.dy,
#					self._tab.x+self._tab.dx, self._tab.y+self._tab.dy)

		self.setMouseStatus(event)

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
				closest = self.find_closest(	self.canvasx(event.x),
								self.canvasy(event.y),
								CLOSE_DISTANCE)
				items = []
				for i in closest:
					try:
						items.append(self._items[i])
						#i = None
					except KeyError:
						tags = self.gettags(i)
						if "Orient" in tags:
							self.selectMarker(i)
							return
						#i = self.find_below(i)
						pass
			if not items: return

			self.app.select(items, self._mouseAction==ACTION_SELECT_DOUBLE,
					event.state&CONTROL_MASK==0)
			self._mouseAction = None

		elif self._mouseAction == ACTION_MOVE:
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			self._vx1, self._vy1, self._vz1, self._va1 = self.canvas2xyza(i,j)
			dx=self._vx1-self._vx0
			dy=self._vy1-self._vy0
			dz=self._vz1-self._vz0
			da=self._va1-self._va0
			self.status(_("Move by %g, %g, %g, %g")%(dx,dy,dz,da))
			self.app.insertCommand(("move %g %g %g %g")%(dx,dy,dz, da),True)

		elif self._mouseAction == ACTION_PAN:
			self.panRelease(event)

#		# Finalize tab
#		elif self._mouseAction == ACTION_ADDTAB:
#			self._tab.correct()
#			self.gcode.addUndo(self.gcode.addTabUndo(-1,self._tab))
#			self._tab = None
#			self._tabRect = None
#			self.setActionSelect()
#			self.event_generate("<<TabAdded>>")

	# ----------------------------------------------------------------------
	def double(self, event):
		#self.app.selectBlocks()
		self._mouseAction = ACTION_SELECT_DOUBLE

	# ----------------------------------------------------------------------
	def motion(self, event):
		self.setMouseStatus(event)

	#-----------------------------------------------------------------------
	# Testing routine
	#-----------------------------------------------------------------------
	def __test(self, event):
		i = self.canvasx(event.x)
		j = self.canvasy(event.y)
		x,y,z,a = self.canvas2xyza(i,j)
		blocks =  self.app.editor.getSelectedBlocks()

		from bmath import Vector
		P = Vector(x,y)
#		for bid in blocks:
#			for path in self.gcode.toPath(bid):
#				print path
#				print path.isInside(P)

	# ----------------------------------------------------------------------
	# Snap to the closest point if any
	# ----------------------------------------------------------------------
	def snapPoint(self, cx, cy):
		xs,ys = None,None
		if CNC.inch:
			dmin = (self.zoom/25.4)**2	# 1mm maximum distance ...
		else:
			dmin = (self.zoom)**2
		dmin  = (CLOSE_DISTANCE*self.zoom)**2

		# ... and if we are closer than 5pixels
		for item in self.find_closest(cx, cy, CLOSE_DISTANCE):
			try:
				bid,lid = self._items[item]
			except KeyError:
				continue

			# Very cheap and inaccurate approach :)
			coords = self.coords(item)
			x = coords[0]	# first
			y = coords[1]	# point
			d = (cx-x)**2 + (cy-y)**2
			if d<dmin:
				dmin = d
				xs,ys = x,y

			x = coords[-2]	# last
			y = coords[-1]	# point
			d = (cx-x)**2 + (cy-y)**2
			if d<dmin:
				dmin = d
				xs,ys = x,y

			# I need to check the real code and if
			# an arc check also the center?

		if xs is not None:
			return xs, ys
		else:
			return cx, cy

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

	#----------------------------------------------------------------------
	def xview(self, *args):
		ret = Canvas.xview(self, *args)
		if args: self.cameraPosition()
		return ret

	#----------------------------------------------------------------------
	def yview(self, *args):
		ret = Canvas.yview(self, *args)
		if args: self.cameraPosition()
		return ret

	#----------------------------------------------------------------------
	def configureEvent(self, event):
		self.cameraPosition()

	# ----------------------------------------------------------------------
	def pan(self, event):
		if self._mouseAction == ACTION_PAN:
			self.scan_dragto(event.x, event.y, gain=1)
			self.cameraPosition()

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
	# Delay zooming to cascade multiple zoom actions
	# ----------------------------------------------------------------------
	def zoomCanvas(self, x, y, zoom):
		self._tx = x
		self._ty = y
		self.__tzoom *= zoom
		self.after_idle(self._zoomCanvas)

	# ----------------------------------------------------------------------
	# Zoom on screen position x,y by a factor zoom
	# ----------------------------------------------------------------------
	def _zoomCanvas(self, event=None): #x, y, zoom):
		x = self._tx
		y = self._ty
		zoom = self.__tzoom

		#def zoomCanvas(self, x, y, zoom):
		self.__tzoom = 1.0

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
		if self._probe:
			self._projectProbeImage()
			self.itemconfig(self._probe, image=self._probeTkImage)
		self.cameraUpdate()

	# ----------------------------------------------------------------------
	# Return selected objects bounding box
	# ----------------------------------------------------------------------
	def selBbox(self):
		x1 = None
		for tag in ("sel","sel2","sel3","sel4"):
			bb = self.bbox(tag)
			if bb is None:
				continue
			elif x1 is None:
				x1,y1,x2,y2 = bb
			else:
				x1 = min(x1,bb[0])
				y1 = min(y1,bb[1])
				x2 = max(x2,bb[2])
				y2 = max(y2,bb[3])

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
			self.__tzoom = min(zx,zy)
		else:
			self.__tzoom = max(zx,zy)

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

		self.cameraPosition()

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
		self.zoomCanvas(event.x, event.y, ZOOM)

	# ----------------------------------------------------------------------
	def mouseZoomOut(self, event):
		self.zoomCanvas(event.x, event.y, 1.0/ZOOM)

	# ----------------------------------------------------------------------
	def wheel(self, event):
		self.zoomCanvas(event.x, event.y, pow(ZOOM,(event.delta//120)))

	# ----------------------------------------------------------------------
	# Change the insert marker location
	# ----------------------------------------------------------------------
	def activeMarker(self, item):
		if item is None: return
		b,i = item
		if i is None: return
		block = self.gcode[b]
		item = block.path(i)

		if item is not None and item != self._lastActive:
			if self._lastActive is not None:
				self.itemconfig(self._lastActive, arrow=NONE)
			self._lastActive = item
			self.itemconfig(self._lastActive, arrow=LAST)

	#----------------------------------------------------------------------
	# Display gantry
	#----------------------------------------------------------------------
	def gantry(self, wx, wy, wz, wa, mx, my, mz, ma):
		self._lastGantry = (wx,wy,wz,wa)
		self._drawGantry(*self.plotCoords([(wx,wy,wz,wa)])[0])
		if self._cameraImage and self.cameraAnchor==NONE:
			self.cameraPosition()

		dx = wx-mx
		dy = wy-my
		dz = wz-mz
		da = wa-ma
		if abs(dx-self._dx) > 0.0001 or \
		   abs(dy-self._dy) > 0.0001 or \
		   abs(dz-self._dz) > 0.0001 or \
		   abs(da-self._da) > 0.0001:
			self._dx = dx
			self._dy = dy
			self._dz = dz
			self._da = da

			if not self.draw_workarea: return
			xmin = self._dx-CNC.travel_x
			ymin = self._dy-CNC.travel_y
			zmin = self._dz-CNC.travel_z
			amin = self._da-CNC.travel_a
			xmax = self._dx
			ymax = self._dy
			zmax = self._dz
			amax = self._da

			xyza = [(xmin, ymin, 0., 0.),
			       (xmax, ymin, 0., 0.),
			       (xmax, ymax, 0., 0.),
			       (xmin, ymax, 0., 0.),
			       (xmin, ymin, 0., 0.)]

			coords = []
			for x,y in self.plotCoords(xyza):
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

		for i in self.find_withtag("sel"):
			bid,lid = self._items[i]
			if bid:
				try:
					block = self.gcode[bid]
					if block.color:
						fill = block.color
					else:
						fill = ENABLE_COLOR
				except IndexError:
					fill = ENABLE_COLOR
			else:
					fill = ENABLE_COLOR
			self.itemconfig(i,  width=1, fill=fill)

		self.itemconfig("sel2", width=1, fill=DISABLE_COLOR)
		self.itemconfig("sel3", width=1, fill=TAB_COLOR)
		self.itemconfig("sel4", width=1, fill=DISABLE_COLOR)
		for i in SELECTION_TAGS: self.dtag(i)
		self.delete("info")

	#----------------------------------------------------------------------
	# Highlight selected items
	#----------------------------------------------------------------------
	def select(self, items):
		for b, i in items:
			block = self.gcode[b]
			if i is None:
				sel = block.enable and "sel" or "sel2"
				for path in block._path:
					if path is not None:
						self.addtag_withtag(sel, path)
				sel = block.enable and "sel3" or "sel4"
				for tab in block.tabs:
					path = tab.path
					if path is not None:
						self.addtag_withtag(sel, tab.path)

			elif isinstance(i,int):
				path = block.path(i)
				if path:
					sel = block.enable and "sel" or "sel2"
					self.addtag_withtag(sel, path)

			elif isinstance(i,Tab):
				path = i.path
				if path:
					sel = block.enable and "sel3" or "sel4"
					self.addtag_withtag(sel, path)

		self.itemconfig("sel",  width=2, fill=SELECT_COLOR)
		self.itemconfig("sel2", width=2, fill=SELECT2_COLOR)
		self.itemconfig("sel3", width=2, fill=TAB_COLOR)
		self.itemconfig("sel4", width=2, fill=TAB_COLOR)
		for i in SELECTION_TAGS: self.tag_raise(i)
		self.drawMargin()

	#----------------------------------------------------------------------
	# Select orientation marker
	#----------------------------------------------------------------------
	def selectMarker(self, item):
		# find marker
		for i,paths in enumerate(self.gcode.orient.paths):
			if item in paths:
				self._orientSelected = i
				for j in paths:
					self.itemconfig(j, width=2)
				self.event_generate("<<OrientSelect>>", data=i)
				return
		self._orientSelected = None

	#----------------------------------------------------------------------
	# Highlight marker that was selected
	#----------------------------------------------------------------------
	def orientChange(self, marker):
		self.itemconfig("Orient", width=1)
		if marker >=0:
			self._orientSelected = marker
			try:
				for i in self.gcode.orient.paths[self._orientSelected]:
					self.itemconfig(i, width=2)
			except IndexError:
				self.drawOrient()
		else:
			self._orientSelected = None

	#----------------------------------------------------------------------
	# Display graphical information on selected blocks
	#----------------------------------------------------------------------
	def showInfo(self, blocks):
		self.delete("info")	# clear any previous information
		for bid in blocks:
			block = self.gcode.blocks[bid]
			xyza = [(block.xmin, block.ymin, 0., 0.),
			        (block.xmax, block.ymin, 0., 0.),
			        (block.xmax, block.ymax, 0., 0.),
			        (block.xmin, block.ymax, 0., 0.),
			        (block.xmin, block.ymin, 0., 0.)]
			self.create_line(self.plotCoords(xyza),
					fill=INFO_COLOR,
					tag="info")
			xc = (block.xmin + block.xmax)/2.0
			yc = (block.ymin + block.ymax)/2.0
			r  = min(block.xmax-xc, block.ymax-yc)
			closed, direction = self.gcode.info(bid)

			if closed==0:	# open path
				if direction==1:
					sf = math.pi/4.0
					ef = 2.0*math.pi - sf
				else:
					ef = math.pi/4.0
					sf = 2.0*math.pi - ef
			elif closed==1:
				if direction==1:
					sf = 0.
					ef = 2.0*math.pi
				else:
					ef = 0.
					sf = 2.0*math.pi

			elif closed is None:
				continue

			n = 64
			df = (ef-sf)/float(n)
			xyza = []
			f = sf
			for i in range(n+1):
				xyza.append((xc+r*math.sin(f), yc+r*math.cos(f), 0., 0.))	# towards up
				f += df
			self.create_line(self.plotCoords(xyza),
					fill=INFO_COLOR,
					width=5,
					arrow=LAST,
					arrowshape=(32,40,12),
					tag="info")

	#-----------------------------------------------------------------------
	def cameraOn(self, event=None):
		if not self.camera.start(): return
		self.cameraRefresh()

	#-----------------------------------------------------------------------
	def cameraOff(self, event=None):
		self.delete(self._cameraImage)
		self.delete(self._cameraHori)
		self.delete(self._cameraVert)
		self.delete(self._cameraCircle)
		self.delete(self._cameraCircle2)

		self._cameraImage = None
		if self._cameraAfter:
			self.after_cancel(self._cameraAfter)
			self._cameraAfter = None
		self.camera.stop()

	#-----------------------------------------------------------------------
	def cameraUpdate(self):
		if not self.camera.isOn(): return
		if self._cameraAfter:
			self.after_cancel(self._cameraAfter)
			self._cameraAfter = None
		self.cameraRefresh()
		self.cameraPosition()

	#-----------------------------------------------------------------------
	def cameraRefresh(self):
		if not self.camera.read():
			self.cameraOff()
			return
		if self.cameraEdge: self.camera.canny(50,200)
		if self.cameraAnchor==NONE or self.zoom/self.cameraScale>1.0:
			self.camera.resize(self.zoom/self.cameraScale, self._cameraMaxWidth, self._cameraMaxHeight)
		if self._cameraImage is None:
			self._cameraImage = self.create_image((0,0), tag="CameraImage")
			self.lower(self._cameraImage)
			# create cross hair at dummy location we will correct latter
			self._cameraHori    = self.create_line(0,0,1,0, fill=CAMERA_COLOR, tag="CrossHair")
			self._cameraVert    = self.create_line(0,0,0,1, fill=CAMERA_COLOR, tag="CrossHair")
			self._cameraCircle  = self.create_oval(0,0, 1,1, outline=CAMERA_COLOR, tag="CrossHair")
			self._cameraCircle2 = self.create_oval(0,0, 1,1, outline=CAMERA_COLOR,
							dash=(3,3), tag="CrossHair")
			self.cameraPosition()
		try:
			self.itemconfig(self._cameraImage, image=self.camera.toTk())
		except:
			pass
		self._cameraAfter = self.after(100, self.cameraRefresh);

	#-----------------------------------------------------------------------
	def cameraFreeze(self, freeze):
		if self.camera.isOn():
			self.camera.freeze(freeze)

	#-----------------------------------------------------------------------
	def cameraSave(self, event=None):
		try:
			self._count += 1
		except:
			self._count = 1
		self.camera.save("camera%02d.png"%(self._count))

	# ----------------------------------------------------------------------
	# Reposition camera and crosshair
	# ----------------------------------------------------------------------
	def cameraPosition(self):
		if self._cameraImage is None: return
		w = self.winfo_width()
		h = self.winfo_height()
		hc,wc = self.camera.image.shape[:2]
		wc //= 2
		hc //= 2
		x = w//2		# everything on center
		y = h//2
		if self.cameraAnchor == NONE:
			if self._lastGantry is not None:
				x,y = self.plotCoords([self._lastGantry])[0]
			else:
				x = y = 0
			if not self.cameraSwitch:
				x += self.cameraDx * self.zoom
				y -= self.cameraDy * self.zoom
			r  = self.cameraR  * self.zoom
		else:
			if self.cameraAnchor != CENTER:
				if N in self.cameraAnchor:
					y = hc
				elif S in self.cameraAnchor:
					y = h-hc
				if W in self.cameraAnchor:
					x = wc
				elif E in self.cameraAnchor:
					x = w-wc
			x = self.canvasx(x)
			y = self.canvasy(y)
			if self.zoom/self.cameraScale>1.0:
				r = self.cameraR * self.zoom
			else:
				r = self.cameraR * self.cameraScale

		self.coords(self._cameraImage,   x, y)
		self.coords(self._cameraHori,    x-wc, y, x+wc, y)
		self.coords(self._cameraVert,    x, y-hc, x, y+hc)
		self.coords(self._cameraCircle,  x-r, y-r, x+r, y+r)
		self.coords(self._cameraCircle2, x-r*2, y-r*2, x+r*2, y+r*2)

	# ----------------------------------------------------------------------
	# Crop center of camera and search it in subsequent movements
	# ----------------------------------------------------------------------
	def cameraMakeTemplate(self, r):
		if self._cameraImage is None: return
		self._template = self.camera.getCenterTemplate(r)

	# ----------------------------------------------------------------------
	def cameraMatchTemplate(self):
		return self.camera.matchTemplate(self._template)

	#----------------------------------------------------------------------
	# Parse and draw the file from the editor to g-code commands
	#----------------------------------------------------------------------
	def draw(self, view=None): #, lines):
		if self._inDraw : return
		self._inDraw  = True

		self.__tzoom = 1.0
		xyza = self.canvas2xyza(
				self.canvasx(self.winfo_width()/2),
				self.canvasy(self.winfo_height()/2))

		if view is not None: self.view = view

		self._last = (0.,0.,0.,0.)
		self.initPosition()

		self.drawPaths()
		self.drawGrid()
		self.drawMargin()
		self.drawWorkarea()
		self.drawProbe()
		self.drawOrient()
		self.drawAxes()
#		self.tag_lower(self._workarea)
		if self._gantry1: self.tag_raise(self._gantry1)
		if self._gantry2: self.tag_raise(self._gantry2)
		self._updateScrollBars()

		ij = self.plotCoords([xyza])[0]
		dx = int(round(self.canvasx(self.winfo_width()/2)  - ij[0]))
		dy = int(round(self.canvasy(self.winfo_height()/2) - ij[1]))
		self.scan_mark(0,0)
		self.scan_dragto(int(round(dx)), int(round(dy)), 1)

		self._inDraw  = False

	#----------------------------------------------------------------------
	# Initialize gantry position
	#----------------------------------------------------------------------
	def initPosition(self):
		self.configure(background=CANVAS_COLOR)
		self.delete(ALL)
		self._cameraImage = None
		gr = max(3,int(CNC.vars["diameter"]/2.0*self.zoom))
		if self.view in (VIEW_XY, VIEW_XAF):
			self._gantry1 = self.create_oval( (-gr,-gr), ( gr, gr),
					width=2,
					outline=GANTRY_COLOR)
			self._gantry2 = None
		else:
			gx = gr
			gy = gr//2
			gh = 3*gr
			if self.view in (VIEW_XZ, VIEW_YZ):
				self._gantry1 = None
				self._gantry2 = self.create_line((-gx,-gh, 0,0, gx,-gh, -gx,-gh),
						width=2,
						fill=GANTRY_COLOR)
			else:
				self._gantry1 = self.create_oval((-gx,-gh-gy, gx,-gh+gy),
						width=2,
						outline=GANTRY_COLOR)
				self._gantry2 = self.create_line((-gx, -gh, 0, 0, gx, -gh),
						width=2,
						fill=GANTRY_COLOR)

		self._lastInsert = None
		self._lastActive = None
		self._select = None
		self._vector = None
		self._items.clear()
		self.cnc.initPath()
		self.cnc.resetAllMargins()

	#----------------------------------------------------------------------
	# Draw gantry location
	#----------------------------------------------------------------------
	def _drawGantry(self, x, y):
		gr = max(3,int(CNC.vars["diameter"]/2.0*self.zoom))
		if self._gantry2 is None:
			self.coords(self._gantry1, (x-gr, y-gr, x+gr, y+gr))
		else:
			gx = gr
			gy = gr//2
			gh = 3*gr
			if self._gantry1 is None:
				self.coords(self._gantry2, (x-gx,y-gh, x,y, x+gx,y-gh, x-gx,y-gh))
			else:
				self.coords(self._gantry1, (x-gx, y-gh-gy, x+gx, y-gh+gy))
				self.coords(self._gantry2, (x-gx, y-gh, x, y, x+gx, y-gh))

	#----------------------------------------------------------------------
	# Draw system axes
	#----------------------------------------------------------------------
	def drawAxes(self):
		self.delete("Axes")
		if not self.draw_axes: return

		dx = CNC.vars["axmax"] - CNC.vars["axmin"]
		dy = CNC.vars["aymax"] - CNC.vars["aymin"]
		d = min(dx,dy)
		try:
			s = math.pow(10.0, int(math.log10(d)))
		except:
			if CNC.inch:
				s = 10.0
			else:
				s = 100.0
		xyza = [(0.,0.,0., 0.), (s, 0., 0., 0.)]
		self.create_line(self.plotCoords(xyza), tag="Axes", fill="Red", dash=(3,1), arrow=LAST)

		xyza = [(0.,0.,0., 0.), (0., s, 0., 0.)]
		self.create_line(self.plotCoords(xyza), tag="Axes", fill="Green", dash=(3,1), arrow=LAST)

		xyza = [(0.,0.,0., 0.), (0., 0., s, 0.)]
		self.create_line(self.plotCoords(xyza), tag="Axes", fill="Blue",  dash=(3,1), arrow=LAST)

		xyza = [(0.,0.,0., 0.), (0., 0., 0., s)]
		self.create_line(self.plotCoords(xyza), tag="Axes", fill="Orange", dash=(3,1), arrow=LAST)

	#----------------------------------------------------------------------
	# Draw margins of selected blocks
	#----------------------------------------------------------------------
	def drawMargin(self):
		if self._margin:  self.delete(self._margin)
		if self._amargin: self.delete(self._amargin)
		self._margin = self._amargin = None
		if not self.draw_margin: return

		if CNC.isMarginValid():
			xyza = [(CNC.vars["xmin"], CNC.vars["ymin"], 0., 0.),
			       (CNC.vars["xmax"], CNC.vars["ymin"], 0., 0.),
			       (CNC.vars["xmax"], CNC.vars["ymax"], 0., 0.),
			       (CNC.vars["xmin"], CNC.vars["ymax"], 0., 0.),
			       (CNC.vars["xmin"], CNC.vars["ymin"], 0., 0.)]
			self._margin = self.create_line(
						self.plotCoords(xyza),
						fill=MARGIN_COLOR)
			self.tag_lower(self._margin)

		if not CNC.isAllMarginValid(): return
		xyza = [(CNC.vars["axmin"], CNC.vars["aymin"], 0., 0.),
		       (CNC.vars["axmax"], CNC.vars["aymin"], 0., 0.),
		       (CNC.vars["axmax"], CNC.vars["aymax"], 0., 0.),
		       (CNC.vars["axmin"], CNC.vars["aymax"], 0., 0.),
		       (CNC.vars["axmin"], CNC.vars["aymin"], 0., 0.)]
		self._amargin = self.create_line(
					self.plotCoords(xyza),
					dash=(3,2),
					fill=MARGIN_COLOR)
		self.tag_lower(self._amargin)

	#----------------------------------------------------------------------
	# Change rectangle coordinates
	#----------------------------------------------------------------------
	def _rectCoords(self, rect, xmin, ymin, xmax, ymax, z=0.0):
		self.coords(rect, Tkinter._flatten(self.plotCoords(
			[(xmin, ymin, z),
			 (xmax, ymin, z),
			 (xmax, ymax, z),
			 (xmin, ymax, z),
			 (xmin, ymin, z)]
			)))

	#----------------------------------------------------------------------
	# Draw a 3D rectangle
	#----------------------------------------------------------------------
	def _drawRect(self, xmin, ymin, xmax, ymax, z=0.0, a=0.0, **kwargs):
		xyza = [(xmin, ymin, z, a),
		       (xmax, ymin, z, a),
		       (xmax, ymax, z, a),
		       (xmin, ymax, z, a),
		       (xmin, ymin, z, a)]
		rect = self.create_line(
				self.plotCoords(xyza),
				**kwargs),
		return rect

	#----------------------------------------------------------------------
	# Draw a workspace rectangle
	#----------------------------------------------------------------------
	def drawWorkarea(self):
		if self._workarea: self.delete(self._workarea)
		if not self.draw_workarea: return

		xmin = self._dx-CNC.travel_x
		ymin = self._dy-CNC.travel_y
		zmin = self._dz-CNC.travel_z
		amin = self._da-CNC.travel_a
		xmax = self._dx
		ymax = self._dy
		zmax = self._dz
		amax = self._da

		self._workarea = self._drawRect(xmin, ymin, xmax, ymax, 0., 0., fill=WORK_COLOR, dash=(3,2))
		self.tag_lower(self._workarea)

	#----------------------------------------------------------------------
	# Draw coordinates grid
	#----------------------------------------------------------------------
	def drawGrid(self):
		self.delete("Grid")
		if not self.draw_grid: return
		if self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
			xmin = (CNC.vars["axmin"]//10)  *10
			xmax = (CNC.vars["axmax"]//10+1)*10
			ymin = (CNC.vars["aymin"]//10)  *10
			ymax = (CNC.vars["aymax"]//10+1)*10
			for i in range(int(CNC.vars["aymin"]//10), int(CNC.vars["aymax"]//10)+2):
				y = i*10.0
				xyza = [(xmin,y,0,0), (xmax,y,0,0)]
				item = self.create_line(self.plotCoords(xyza),
							tag="Grid",
							fill=GRID_COLOR,
							dash=(1,3))
				self.tag_lower(item)

			for i in range(int(CNC.vars["axmin"]//10), int(CNC.vars["axmax"]//10)+2):
				x = i*10.0
				xyza = [(x,ymin,0,0), (x,ymax,0,0)]
				item = self.create_line(self.plotCoords(xyza),
							fill=GRID_COLOR,
							tag="Grid",
							dash=(1,3))
				self.tag_lower(item)

	#----------------------------------------------------------------------
	# Display orientation markers
	#----------------------------------------------------------------------
	def drawOrient(self, event=None):
		self.delete("Orient")
		#if not self.draw_probe: return
		if self.view in (VIEW_XZ, VIEW_YZ): return

		# Draw orient markers
		if CNC.inch:
			w = 0.1
		else:
			w = 2.5

		self.gcode.orient.clearPaths()
		for i,(xm,ym,x,y) in enumerate(self.gcode.orient.markers):
			paths = []
			# Machine position (cross)
			item = self.create_line(self.plotCoords([(xm-w,ym,0.),(xm+w,ym,0.)]),
						tag="Orient",
						fill="Green")
			self.tag_lower(item)
			paths.append(item)

			item = self.create_line(self.plotCoords([(xm,ym-w,0.),(xm,ym+w,0.)]),
						tag="Orient",
						fill="Green")
			self.tag_lower(item)
			paths.append(item)

			# GCode position (cross)
			item = self.create_line(self.plotCoords([(x-w,y,0.),(x+w,y,0.)]),
						tag="Orient",
						fill="Red")
			self.tag_lower(item)
			paths.append(item)

			item = self.create_line(self.plotCoords([(x,y-w,0.),(x,y+w,0.)]),
						tag="Orient",
						fill="Red")
			self.tag_lower(item)
			paths.append(item)

			# Draw error if any
			try:
				err = self.gcode.orient.errors[i]
				item = self.create_oval(self.plotCoords([(xm-err,ym-err,0.),(xm+err,ym+err,0.)]),
						tag="Orient",
						outline="Red")
				self.tag_lower(item)
				paths.append(item)

				err = self.gcode.orient.errors[i]
				item = self.create_oval(self.plotCoords([(x-err,y-err,0.),(x+err,y+err,0.)]),
						tag="Orient",
						outline="Red")
				self.tag_lower(item)
				paths.append(item)
			except IndexError:
				pass

			# Connecting line
			item = self.create_line(self.plotCoords([(xm,ym,0.),(x,y,0.)]),
						tag="Orient",
						fill="Blue",
						dash=(1,1))
			self.tag_lower(item)
			paths.append(item)

			self.gcode.orient.addPath(paths)

		if self._orientSelected is not None:
			try:
				for item in self.gcode.orient.paths[self._orientSelected]:
					self.itemconfig(item, width=2)
			except (IndexError, TclError):
				pass

	#----------------------------------------------------------------------
	# Display probe
	#----------------------------------------------------------------------
	def drawProbe(self):
		self.delete("Probe")
		if self._probe:
			self.delete(self._probe)
			self._probe = None
		if not self.draw_probe: return
		if self.view in (VIEW_XZ, VIEW_YZ): return

		# Draw probe grid
		probe = self.gcode.probe
		for x in bmath.frange(probe.xmin, probe.xmax+0.00001, probe.xstep()):
			xyza = [(x,probe.ymin,0.,0.), (x,probe.ymax,0.,0.)]
			item = self.create_line(self.plotCoords(xyza),
						tag="Probe",
						fill='Yellow')
			self.tag_lower(item)

		for y in bmath.frange(probe.ymin, probe.ymax+0.00001, probe.ystep()):
			xyza = [(probe.xmin,y,0.,0.), (probe.xmax,y,0.,0.)]
			item = self.create_line(self.plotCoords(xyza),
						tag="Probe",
						fill='Yellow')
			self.tag_lower(item)

		# Draw probe points
		for i,uv in enumerate(self.plotCoords(probe.points)):
			item = self.create_text(uv,
						text="%.*f"%(CNC.digits,probe.points[i][2]),
						tag="Probe",
						justify=CENTER,
						fill=PROBE_TEXT_COLOR)
			self.tag_lower(item)

		# Draw image map if numpy exists
		#if numpy is not None and probe.matrix and self.view == VIEW_XY:
		if numpy is not None and probe.matrix and self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
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
			if abs(dc)<1e-8: return
			palette = []
			for x in bmath.frange(lw, hg+1e-10, (hg-lw)/255.):
				i = int(math.floor(x / dc))
				j = i + i>>1	# 1.5*i
				if i<0:
					palette.append(0xff+j)
					palette.append(0xff+j)
					palette.append(0xff)
				elif i>0:
					palette.append(0xff)
					palette.append(0xff-j)
					palette.append(0xff-j)
				else:
					palette.append(0xff)
					palette.append(0xff)
					palette.append(0xff)
				#print ">>", x,i,palette[-3], palette[-2], palette[-1]
			#print "palette size=",len(palette)/3
			array = numpy.floor((array-lw)/(hg-lw)*255)
			self._probeImage = Image.fromarray(array.astype(numpy.int16)).convert('L')
			self._probeImage.putpalette(palette)

			# Add transparency for a possible composite operation latter on ISO*
			self._probeImage = self._probeImage.convert("RGBA")

			x,y = self._projectProbeImage()

			self._probe = self.create_image(x,y, image=self._probeTkImage, anchor='sw')
			self.tag_lower(self._probe)

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

		image = self._probeImage.resize((size), resample=RESAMPLE).crop(crop)

		if self.view in (VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
			w, h = image.size
			size2 = (int(S60*(w+h)),
				 int(C60*(w+h)))

			if self.view == VIEW_ISO1:
				transform = ( 0.5/S60, 0.5/C60, -h/2,
					     -0.5/S60, 0.5/C60,  h/2)
				xy = self.plotCoords([(probe.xmin, probe.ymin, 0.),
						      (probe.xmax, probe.ymin, 0.)])
				x = xy[0][0]
				y = xy[1][1]

			elif self.view == VIEW_ISO2:
				transform = ( 0.5/S60,-0.5/C60,  w/2,
					      0.5/S60, 0.5/C60, -w/2)

				xy = self.plotCoords([(probe.xmin, probe.ymax, 0.),
						      (probe.xmin, probe.ymin, 0.)])
				x = xy[0][0]
				y = xy[1][1]
			else:
				transform = (-0.5/S60,-0.5/C60, w+h/2,
					      0.5/S60,-0.5/C60, h/2)
				xy = self.plotCoords([(probe.xmax, probe.ymax, 0.),
						      (probe.xmin, probe.ymax, 0.)])
				x = xy[0][0]
				y = xy[1][1]

			affine = image.transform(size2, Image.AFFINE,
						transform,
						resample=RESAMPLE)
			# Super impose a white image
			white = Image.new('RGBA', affine.size, (255,)*4)
			# compose the two images affine and white with mask the affine
			image = Image.composite(affine, white, affine)
			del white

		else:
			x,y = self.plotCoords([(probe.xmin, probe.ymin, 0.)])[0]

		self._probeTkImage = ImageTk.PhotoImage(image)
		return x,y

	#----------------------------------------------------------------------
	# Draw the paths for the whole gcode file
	#----------------------------------------------------------------------
	def drawPaths(self):
		if not self.draw_paths:
			for block in self.gcode.blocks:
				block.resetPath()
			return

		try:
			n = 1
			startTime = time.time()
			self.cnc.resetAllMargins()
			drawG = self.draw_rapid or self.draw_paths or self.draw_margin
			for i,block in enumerate(self.gcode.blocks):
				start = True	# start location found
				block.resetPath()
				# Draw block tabs
				if self.draw_margin:
					for tab in block.tabs:
						color = block.enable and TAB_COLOR or DISABLE_COLOR
						item = self._drawRect(	tab.x-tab.dx/2., tab.y-tab.dy/2.,
									tab.x+tab.dx/2., tab.y+tab.dy/2.,
									0., 0., fill=color)
						tab.path = item
						self._items[item[0]] = i,tab
						self.tag_lower(item)
				# Draw block
				for j,line in enumerate(block):
					n -= 1
					if n==0:
						if time.time() - startTime > DRAW_TIME:
							raise AlarmException()
						n = 1000
					try:
						cmd = self.gcode.evaluate(CNC.compileLine(line))
						if isinstance(cmd,tuple):
							cmd = None
						else:
							cmd = CNC.breakLine(cmd)
					except AlarmException:
						raise
					except:
						sys.stderr.write(_(">>> ERROR: %s\n")%(str(sys.exc_info()[1])))
						sys.stderr.write(_("     line: %s\n")%(line))
						cmd = None
					if cmd is None or not drawG:
						block.addPath(None)
					else:
						path = self.drawPath(block, cmd)
						self._items[path] = i,j
						block.addPath(path)
						if start and self.cnc.gcode in (1,2,3):
							# Mark as start the first non-rapid motion
							block.startPath(self.cnc.x, self.cnc.y, self.cnc.z, self.cnc.a)
							start = False
				block.endPath(self.cnc.x, self.cnc.y, self.cnc.z, self.cnc.a)
		except AlarmException:
			self.status("Rendering takes TOO Long. Interrupted...")

	#----------------------------------------------------------------------
	# Create path for one g command
	#----------------------------------------------------------------------
	def drawPath(self, block, cmds):
		self.cnc.motionStart(cmds)
		xyza = self.cnc.motionPath()
		self.cnc.motionEnd()
		if xyza:
			self.cnc.pathLength(block, xyza)
			if self.cnc.gcode in (1,2,3):
				block.pathMargins(xyza)
				self.cnc.pathMargins(block)
			if block.enable:
				if self.cnc.gcode == 0 and self.draw_rapid:
					xyza[0] = self._last
				self._last = xyza[-1]
			else:
				if self.cnc.gcode == 0:
					return None
			coords = self.plotCoords(xyza)
			if coords:
				if block.enable:
					if block.color:
						fill = block.color
					else:
						fill = ENABLE_COLOR
				else:
					fill = DISABLE_COLOR
				if self.cnc.gcode == 0:
					if self.draw_rapid:
						return self.create_line(coords,
							fill=fill, width=0, dash=(4,3))
				elif self.draw_paths:
					return self.create_line(coords, fill=fill,
							width=0, cap="projecting")
		return None

	#----------------------------------------------------------------------
	# Return plotting coordinates for a 3d xyza path
	#
	# NOTE: Use the Tkinter._flatten() to pass to self.coords() function
	#----------------------------------------------------------------------
	def plotCoords(self, xyza):
		coords = None
		if self.view == VIEW_XY:
			coords = [(p[0]*self.zoom,-p[1]*self.zoom) for p in xyza]
		if self.view == VIEW_XAF:
			coords = [(p[0]*self.zoom,-p[3]*self.zoom) for p in xyza]
		elif self.view == VIEW_XZ:
			coords = [(p[0]*self.zoom,-p[2]*self.zoom) for p in xyza]
		elif self.view == VIEW_YZ:
			coords = [(p[1]*self.zoom,-p[2]*self.zoom) for p in xyza]
		elif self.view == VIEW_ISO1:
			coords = [(( p[0]*S60 + p[1]*S60)*self.zoom,
				   (+p[0]*C60 - p[1]*C60 - p[2])*self.zoom)
					for p in xyza]
		elif self.view == VIEW_ISO2:
			coords = [(( p[0]*S60 - p[1]*S60)*self.zoom,
				   (-p[0]*C60 - p[1]*C60 - p[2])*self.zoom)
					for p in xyza]
		elif self.view == VIEW_ISO3:
			coords = [((-p[0]*S60 - p[1]*S60)*self.zoom,
				   (-p[0]*C60 + p[1]*C60 - p[2])*self.zoom)
					for p in xyza]
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
	def canvas2xyza(self, i, j):
		coords = None
		if self.view == VIEW_XY:
			x =  i / self.zoom
			y = -j / self.zoom
			z = 0
			a = 0

		if self.view == VIEW_XAF:
			x =  i / self.zoom
			y = 0
			z = 0
			a = -j / self.zoom

		elif self.view == VIEW_XZ:
			x =  i / self.zoom
			y = 0
			z = -j / self.zoom
			a = 0

		elif self.view == VIEW_YZ:
			x = 0
			y =  i / self.zoom
			z = -j / self.zoom
			a = 0

		elif self.view == VIEW_ISO1:
			x = (i/S60 + j/C60) / self.zoom / 2
			y = (i/S60 - j/C60) / self.zoom / 2
			z = 0
			a = 0

		elif self.view == VIEW_ISO2:
			x =  (i/S60 - j/C60) / self.zoom / 2
			y = -(i/S60 + j/C60) / self.zoom / 2
			z = 0
			a = 0

		elif self.view == VIEW_ISO3:
			x = -(i/S60 + j/C60) / self.zoom / 2
			y = -(i/S60 - j/C60) / self.zoom / 2
			z = 0
			a = 0

		return x,y,z,a

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
		self.draw_workarea=BooleanVar()
		self.draw_camera = BooleanVar()
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
		global CAMERA_COLOR, PROBE_TEXT_COLOR, CANVAS_COLOR
		global DRAW_TIME

		self.draw_axes.set(    bool(int(Utils.getBool("Canvas", "axes",    True))))
		self.draw_grid.set(    bool(int(Utils.getBool("Canvas", "grid",    True))))
		self.draw_margin.set(  bool(int(Utils.getBool("Canvas", "margin",  True))))
		#self.draw_probe.set(   bool(int(Utils.getBool("Canvas", "probe",   False))))
		self.draw_paths.set(   bool(int(Utils.getBool("Canvas", "paths",   True))))
		self.draw_rapid.set(   bool(int(Utils.getBool("Canvas", "rapid",   True))))
		self.draw_workarea.set(bool(int(Utils.getBool("Canvas", "workarea",True))))
		#self.draw_camera.set(  bool(int(Utils.getBool("Canvas", "camera",  False))))

		self.view.set(Utils.getStr("Canvas", "view", VIEWS[0]))

		DRAW_TIME     = Utils.getInt("Canvas", "drawtime",     DRAW_TIME)

		INSERT_COLOR  = Utils.getStr("Color", "canvas.insert", INSERT_COLOR)
		GANTRY_COLOR  = Utils.getStr("Color", "canvas.gantry", GANTRY_COLOR)
		MARGIN_COLOR  = Utils.getStr("Color", "canvas.margin", MARGIN_COLOR)
		GRID_COLOR    = Utils.getStr("Color", "canvas.grid",   GRID_COLOR)
		BOX_SELECT    = Utils.getStr("Color", "canvas.selectbox",BOX_SELECT)
		ENABLE_COLOR  = Utils.getStr("Color", "canvas.enable", ENABLE_COLOR)
		DISABLE_COLOR = Utils.getStr("Color", "canvas.disable",DISABLE_COLOR)
		SELECT_COLOR  = Utils.getStr("Color", "canvas.select", SELECT_COLOR)
		SELECT2_COLOR = Utils.getStr("Color", "canvas.select2",SELECT2_COLOR)
		PROCESS_COLOR = Utils.getStr("Color", "canvas.process",PROCESS_COLOR)
		MOVE_COLOR    = Utils.getStr("Color", "canvas.move",   MOVE_COLOR)
		RULER_COLOR   = Utils.getStr("Color", "canvas.ruler",  RULER_COLOR)
		CAMERA_COLOR  = Utils.getStr("Color", "canvas.camera", CAMERA_COLOR)
		PROBE_TEXT_COLOR = Utils.getStr("Color", "canvas.probetext",  PROBE_TEXT_COLOR)
		CANVAS_COLOR  = Utils.getStr("Color", "canvas.background", CANVAS_COLOR)

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setInt( "Canvas", "drawtime",DRAW_TIME)
		Utils.setStr( "Canvas", "view",    self.view.get())
		Utils.setBool("Canvas", "axes",    self.draw_axes.get())
		Utils.setBool("Canvas", "grid",    self.draw_grid.get())
		Utils.setBool("Canvas", "margin",  self.draw_margin.get())
		Utils.setBool("Canvas", "probe",   self.draw_probe.get())
		Utils.setBool("Canvas", "paths",   self.draw_paths.get())
		Utils.setBool("Canvas", "rapid",   self.draw_rapid.get())
		Utils.setBool("Canvas", "workarea",self.draw_workarea.get())
		#Utils.setBool("Canvas", "camera",  self.draw_camera.get())

	#----------------------------------------------------------------------
	# Canvas toolbar FIXME XXX should be moved to CNCCanvas
	#----------------------------------------------------------------------
	def createCanvasToolbar(self, toolbar):
		b = OptionMenu(toolbar, self.view, *VIEWS)
		b.config(padx=0, pady=1)
		b.unbind("F10")
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, _("Change viewing angle"))

		b = Button(toolbar, image=Utils.icons["zoom_in"],
				command=self.canvas.menuZoomIn)
		tkExtra.Balloon.set(b, _("Zoom In [Ctrl-=]"))
		b.pack(side=LEFT)

		b = Button(toolbar, image=Utils.icons["zoom_out"],
				command=self.canvas.menuZoomOut)
		tkExtra.Balloon.set(b, _("Zoom Out [Ctrl--]"))
		b.pack(side=LEFT)

		b = Button(toolbar, image=Utils.icons["zoom_on"],
				command=self.canvas.fit2Screen)
		tkExtra.Balloon.set(b, _("Fit to screen [F]"))
		b.pack(side=LEFT)

		Label(toolbar, text=_("Tool:"),
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
		tkExtra.Balloon.set(b, _("Select tool [S]"))
		self.addWidget(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["pan"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=ACTION_PAN,
					command=self.canvas.setActionPan)
		tkExtra.Balloon.set(b, _("Pan viewport [X]"))
		b.pack(side=LEFT)

#		b = Radiobutton(toolbar, image=Utils.icons["gantry"],
#					indicatoron=FALSE,
#					variable=self.canvas.actionVar,
#					value=ACTION_GANTRY,
#					command=self.canvas.setActionGantry)
#		tkExtra.Balloon.set(b, _("Move gantry [g]"))
#		self.addWidget(b)
#		b.pack(side=LEFT)
#
#		b = Radiobutton(toolbar, image=Utils.icons["origin"],
#					indicatoron=FALSE,
#					variable=self.canvas.actionVar,
#					value=ACTION_WPOS,
#					command=self.canvas.setActionWPOS)
#		tkExtra.Balloon.set(b, _("Set WPOS to mouse location"))
#		self.addWidget(b)
#		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["ruler"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=ACTION_RULER,
					command=self.canvas.setActionRuler)
		tkExtra.Balloon.set(b, _("Ruler [R]"))
		b.pack(side=LEFT)

		# -----------
		# Draw flags
		# -----------
		Label(toolbar, text=_("Draw:"),
				image=Utils.icons["sep"],
				compound=LEFT).pack(side=LEFT, padx=2)

		b = Checkbutton(toolbar,
				image=Utils.icons["axes"],
				indicatoron=False,
				variable=self.draw_axes,
				command=self.drawAxes)
		tkExtra.Balloon.set(b, _("Toggle display of axes"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["grid"],
				indicatoron=False,
				variable=self.draw_grid,
				command=self.drawGrid)
		tkExtra.Balloon.set(b, _("Toggle display of grid lines"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["margins"],
				indicatoron=False,
				variable=self.draw_margin,
				command=self.drawMargin)
		tkExtra.Balloon.set(b, _("Toggle display of margins"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				text="P",
				image=Utils.icons["measure"],
				indicatoron=False,
				variable=self.draw_probe,
				command=self.drawProbe)
		tkExtra.Balloon.set(b, _("Toggle display of probe"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["endmill"],
				indicatoron=False,
				variable=self.draw_paths,
				command=self.toggleDrawFlag)
		tkExtra.Balloon.set(b, _("Toggle display of paths (G1,G2,G3)"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["rapid"],
				indicatoron=False,
				variable=self.draw_rapid,
				command=self.toggleDrawFlag)
		tkExtra.Balloon.set(b, _("Toggle display of rapid motion (G0)"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["workspace"],
				indicatoron=False,
				variable=self.draw_workarea,
				command=self.drawWorkarea)
		tkExtra.Balloon.set(b, _("Toggle display of workarea"))
		b.pack(side=LEFT)

		b = Checkbutton(toolbar,
				image=Utils.icons["camera"],
				indicatoron=False,
				variable=self.draw_camera,
				command=self.drawCamera)
		tkExtra.Balloon.set(b, _("Toggle display of camera"))
		b.pack(side=LEFT)
		if Camera.cv is None: b.config(state=DISABLED)

		b = Button(toolbar,
				image=Utils.icons["refresh"],
				command=self.viewChange)
		tkExtra.Balloon.set(b, _("Redraw display [Ctrl-R]"))
		b.pack(side=LEFT)

		# -----------
		self.drawTime = tkExtra.Combobox(toolbar,
				width=3,
				background="White",
				command=self.drawTimeChange)
		tkExtra.Balloon.set(self.drawTime, _("Draw timeout in seconds"))
		self.drawTime.fill(["inf", "1", "2", "3", "5", "10", "20", "30", "60", "120"])
		self.drawTime.set(DRAW_TIME)
		self.drawTime.pack(side=RIGHT)
		Label(toolbar, text="Timeout:").pack(side=RIGHT)

	#----------------------------------------------------------------------
	def redraw(self, event=None):
		self.canvas.reset()
		self.event_generate("<<ViewChange>>")

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

	#----------------------------------------------------------------------
	def drawCamera(self, value=None):
		if value is not None: self.draw_camera.set(value)
		if self.draw_camera.get():
			self.canvas.cameraOn()
		else:
			self.canvas.cameraOff()

	#----------------------------------------------------------------------
	def drawTimeChange(self):
		global DRAW_TIME
		try:
			DRAW_TIME = int(self.drawTime.get())
		except ValueError:
			DRAW_TIME = 5*60
		self.viewChange()
