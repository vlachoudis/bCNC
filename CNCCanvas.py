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
DISABLE_COLOR = "Gray"
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

MAXDIST      = 10000

S60 = math.sin(math.radians(60))
C60 = math.cos(math.radians(60))

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
		self._vector      = None
		self._lastActive  = None
		self._lastGantry  = None

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
		self.app.statusbar["text"] = "Select objects with mouse"

	# ----------------------------------------------------------------------
	def setActionOrigin(self, event=None):
		self.setAction(ACTION_ORIGIN)
		self.app.statusbar["text"] = "Click to set the origin (zero)"

	# ----------------------------------------------------------------------
	def setActionMove(self, event=None):
		self.setAction(ACTION_MOVE)
		self.app.statusbar["text"] = "Move graphically objects"

	# ----------------------------------------------------------------------
	def setActionGantry(self, event=None):
		self.setAction(ACTION_GANTRY)
		self.app.statusbar["text"] = "Move CNC gantry to mouse location"

	# ----------------------------------------------------------------------
	def setActionRuler(self, event=None):
		self.setAction(ACTION_RULER)
		self.app.statusbar["text"] = "Drag a ruler to measure distances"

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
			self.app.statusbar["text"] = \
				"dx=%g  dy=%g  dz=%g  length=%g  angle=%g"\
					% (dx,dy,dz,math.sqrt(dx**2+dy**2+dz**2),
					math.degrees(math.atan2(dy,dx)))

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

				lines = []
				for i in closest:
					try: lines.append(self._items[i])
					except: pass

			elif self._mouseAction in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
				closest = self.find_closest(
						self.canvasx(event.x),
						self.canvasy(event.y),
						CLOSE_DISTANCE)

				lines = []
				for i in closest:
					try:
						lines.append(self._items[i])
						#i = None
					except KeyError:
						#i = self.find_below(i)
						pass
			if not lines: return

			self.app.select(lines, self._mouseAction==ACTION_SELECT_DOUBLE,
					event.state&CONTROL_MASK==0)
			self._mouseAction = None

		elif self._mouseAction == ACTION_MOVE:
			i = self.canvasx(event.x)
			j = self.canvasy(event.y)
			self._vx1, self._vy1, self._vz1 = self.canvas2xyz(i,j)
			dx=self._vx1-self._vx0
			dy=self._vy1-self._vy0
			dz=self._vz1-self._vz0
			self.app.statusbar["text"] = "Move by %g, %g, %g"%(dx,dy,dz)
			self.app.insertCommand("move %g %g %g"%(dx,dy,dz),True)

	# ----------------------------------------------------------------------
	def double(self, event):
		#self.app.selectBlocks()
		self._mouseAction = ACTION_SELECT_DOUBLE

	# ----------------------------------------------------------------------
	def setStatus(self, event):
		x,y,z = self.canvas2xyz(self.canvasx(event.x), self.canvasy(event.y))
		um = "mm"
		if (self.cnc.inch):
			[i * (1.0/25.4) for i in (x,y,z)]
			um = "inch"
		self.app.canvasbar["text"] ="X:%.4f  Y:%.4f  Z:%.4f [%s]" %(x,y,z,um)

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
			xmin = self._dx+CNC.travel_x
			ymin = self._dy+CNC.travel_y
			zmin = self._dz+CNC.travel_z
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
			block.resetPath()
			for j,line in enumerate(block):
				cmd = self.cnc.parseLine(line)
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
		if not self.draw_axes: return
		xyz = [(0.,0.,0.), (10.0, 0., 0.)]
		self.create_line(self.plotCoords(xyz), fill="Red",   dash=(3,1))

		xyz = [(0.,0.,0.), (0., 10.0, 0.)]
		self.create_line(self.plotCoords(xyz), fill="Green", dash=(3,1))

		xyz = [(0.,0.,0.), (0., 0., 10.0)]
		self.create_line(self.plotCoords(xyz), fill="Blue",  dash=(3,1))

	#----------------------------------------------------------------------
	def drawMargin(self):
		if not self.draw_margin: return
		if not self.cnc.isMarginValid(): return
		xyz = [(self.cnc.xmin, self.cnc.ymin, 0.),
		       (self.cnc.xmax, self.cnc.ymin, 0.),
		       (self.cnc.xmax, self.cnc.ymax, 0.),
		       (self.cnc.xmin, self.cnc.ymax, 0.),
		       (self.cnc.xmin, self.cnc.ymin, 0.)]
		self._margin = self.create_line(
					self.plotCoords(xyz),
					fill=MARGIN_COLOR)
		self.tag_lower(self._margin)

	#----------------------------------------------------------------------
	def drawWorkarea(self):
		if not self.draw_workarea: return

		xmin = self._dx+CNC.travel_x
		ymin = self._dy+CNC.travel_y
		zmin = self._dz+CNC.travel_z
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
		if not self.draw_grid: return
		if self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
			xmin = (self.cnc.xmin//10)  *10
			xmax = (self.cnc.xmax//10+1)*10
			ymin = (self.cnc.ymin//10)  *10
			ymax = (self.cnc.ymax//10+1)*10
			for i in range(int(self.cnc.ymin//10), int(self.cnc.ymax//10)+2):
				y = i*10.0
				xyz = [(xmin,y,0), (xmax,y,0)]
				item = self.create_line(self.plotCoords(xyz),
							fill=GRID_COLOR,
							dash=(1,3))
				self.tag_lower(item)

			for i in range(int(self.cnc.xmin//10), int(self.cnc.xmax//10)+2):
				x = i*10.0
				xyz = [(x,ymin,0), (x,ymax,0)]
				item = self.create_line(self.plotCoords(xyz),
							fill=GRID_COLOR,
							dash=(1,3))
				self.tag_lower(item)

	#----------------------------------------------------------------------
	# Display probe
	#----------------------------------------------------------------------
	def drawProbe(self):
		if not self.draw_probe: return

		# Draw probe grid
		probe = self.app.gcode.probe
		for x in bmath.frange(probe.xmin, probe.xmax, probe.xstep()):
			xyz = [(x,probe.ymin,0.), (x,probe.ymax,0.)]
			item = self.create_line(self.plotCoords(xyz),
						fill='Yellow')
			self.tag_lower(item)

		for y in bmath.frange(probe.ymin, probe.ymax, probe.ystep()):
			xyz = [(probe.xmin,y,0.), (probe.xmax,y,0.)]
			item = self.create_line(self.plotCoords(xyz),
						fill='Yellow')
			self.tag_lower(item)

		# Draw probe points
		for i,uv in enumerate(self.plotCoords(probe.points)):
			item = self.create_text(uv, text="%g"%(probe.points[i][2]),
					justify=CENTER, fill="Green")
			self.tag_lower(item)

	#----------------------------------------------------------------------
	# Draw a probe point
	#----------------------------------------------------------------------
	def drawProbePoint(self, xyz):
		if not self.draw_probe: return
		xyz[0] += self._dx
		xyz[1] += self._dy
		xyz[2] += self._dz
		uv = self.plotCoords([xyz])
		item = self.create_text(uv, text="%g"%(xyz[2]), justify=CENTER, fill="Green")

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
