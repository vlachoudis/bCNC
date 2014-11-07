# -*- coding: latin1 -*-
# $Id: CNCCanvas.py,v 1.7 2014/10/15 15:04:06 bnv Exp $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

import math
import bmath
try:
	from Tkinter import *
except ImportError:
	from tkinter import *

VIEW_XY      = 0
VIEW_XZ      = 1
VIEW_YZ      = 2
VIEW_ISO1    = 3
VIEW_ISO2    = 4
VIEW_ISO3    = 5

VIEWS = ["X-Y", "X-Z", "Y-Z", "ISO1", "ISO2", "ISO3"]

INSERT_COLOR  = "Blue"
INSERT_WIDTH2 = 3
GANTRY_COLOR  = "Red"
GANTRY_WIDTH2 = 4
MARGIN_COLOR  = "Magenta"
SELECT_COLOR  = "Blue"
BOX_SELECT    = "Cyan"

ACTION_SELECT_SINGLE   = 0
ACTION_SELECT_AREA     = 1
ACTION_SELECT_DOUBLE   = 2

SHIFT_MASK   = 1
CONTROL_MASK = 4
ALT_MASK     = 8
CONTROLSHIFT_MASK = SHIFT_MASK | CONTROL_MASK

MAXDIST      = 10000

S60 = math.sin(math.radians(60))
C60 = math.cos(math.radians(60))

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

		# Canvas binding
		self.bind('<Button-1>',		self.click)
		self.bind('<B1-Motion>',	self.buttonMotion)
		self.bind('<ButtonRelease-1>',	self.release)
		self.bind('<Double-1>',		self.double)

		self.bind('<ButtonRelease-2>',	self.panRelease)
		self.bind('<B2-Motion>',	self.pan)
		self.bind('<ButtonRelease-2>',	self.panRelease)
		self.bind("<Button-4>",		self.mouseZoomIn)
		self.bind("<Button-5>",		self.mouseZoomOut)
		self.bind('<Shift-Button-4>',	lambda e,s=self: s.xview(SCROLL, -1, UNITS))
		self.bind('<Shift-Button-5>',	lambda e,s=self: s.xview(SCROLL,  1, UNITS))
		self.bind('<Control-Button-4>',	lambda e,s=self: s.yview(SCROLL, -1, UNITS))
		self.bind('<Control-Button-5>',	lambda e,s=self: s.yview(SCROLL,  1, UNITS))

		self.bind('<Delete>',		self.app.delete)
		self.bind('<BackSpace>',	self.app.delete)
#		self.bind('<Key-equal>',	self.menuZoomIn)
#		self.bind('<Key-plus>',		self.menuZoomIn)
#		self.bind('<Key-minus>',	self.menuZoomOut)
#		self.bind('<Key-underscore>',	self.menuZoomOut)
#		self.bind('<KP_plus>',		self.menuZoomIn)
#		self.bind('<KP_minus>',		self.menuZoomOut)

#		self.bind('<Control-Key-x>',	self.cut)
#		self.bind('<Control-Key-c>',	self.copy)
#		self.bind('<Control-Key-v>',	self.paste)

#		self.bind('<F1>',		lambda e,s=self : s.view.set(VIEW_XY))
#		self.bind('<F2>',		lambda e,s=self : s.view.set(VIEW_XZ))
#		self.bind('<F3>',		lambda e,s=self : s.view.set(VIEW_YZ))
#		self.bind('<F4>',		lambda e,s=self : s.view.set(VIEW_ISO1))
#		self.bind('<F5>',		lambda e,s=self : s.view.set(VIEW_ISO2))
#		self.bind('<F6>',		lambda e,s=self : s.view.set(VIEW_ISO3))

#		self.bind('<Key-space>',	self.commandFocus)
#		self.bind('<Control-Key-space>',self.commandFocus)
#		self.bind('<Control-Key-a>',	self.selectAll)

		self._pan = False
		self.x0   = 0.0
		self.y0   = 0.0
		self.zoom = 1.0
		self.items = []

		self._action = ACTION_SELECT_SINGLE
		self._x = self._y = 0
		self._inParse     = False	# semaphore for parsing
		self._gantry      = None
		self._select      = None
		self._insert      = None
		self._margin      = None
		self._lastInsert  = None
		self._lastGantry  = None

		self.draw_axes    = True	# Drawing flags
		self.draw_grid    = True
		self.draw_margin  = True
		self.draw_probe   = True
		self.draw_workarea= True
		self._wx = self._wy = self._wz = 0.	# work position
		self._dx = self._dy = self._dz = 0.	# work-machine position
		# Highlight variables
#		self._highAfter  = None
#		self._highStart  = 0
#		self._highLast   = 0
#		self.history     = []
#		self._historyPos = None
#		self._skipSelection = False
		self.initPosition()

	# ----------------------------------------------------------------------
	# Update scrollbars
	# ----------------------------------------------------------------------
	def _updateScrollBars(self):
		"""Update scroll region for new size"""
		bb = self.bbox('all')
		if bb is None: return
		x1,y1,x2,y2 = bb
		self.configure(scrollregion=(x1+1,y1+1,x2,y2))

	# ----------------------------------------------------------------------
	# Find item selected
	# ----------------------------------------------------------------------
	def click(self, event):
		self.focus_set()
		self._x = event.x
		self._y = event.y

		if event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK:
			u = self.canvasx(self._x) / self.zoom
			v = self.canvasy(self._y) / self.zoom

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
		else:
			self._action = ACTION_SELECT_SINGLE

	# ----------------------------------------------------------------------
	# Canvas motion button 1
	# ----------------------------------------------------------------------
	def buttonMotion(self, event):
		if self._action == ACTION_SELECT_AREA:
			self.coords(self._select,
				self.canvasx(self._x),
				self.canvasy(self._y),
				self.canvasx(event.x),
				self.canvasy(event.y))

		elif self._action in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
			if abs(event.x-self._x)>4 or abs(event.y-self._y)>4:
				self._action = ACTION_SELECT_AREA
				self._select = self.create_rectangle(
						self.canvasx(self._x),
						self.canvasy(self._y),
						self.canvasx(event.x),
						self.canvasy(event.y),
						outline=BOX_SELECT)

	# ----------------------------------------------------------------------
	# Canvas release button1. Select area
	# ----------------------------------------------------------------------
	def release(self, event):
		if self._action in (ACTION_SELECT_SINGLE,
				ACTION_SELECT_DOUBLE,
				ACTION_SELECT_AREA):
			if self._action == ACTION_SELECT_AREA:
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
					try: lines.append(self.items.index(i)+1)
					except: pass

			elif self._action in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
				closest = self.find_closest(
						self.canvasx(event.x),
						self.canvasy(event.y),
						4)

				lines = []
				for i in closest:
					#while i is not None:
						try:
							lines.append(self.items.index(i)+1)
							i = None
						except ValueError:
							#i = self.find_below(i)
							pass
			if not lines: return

			self.app.editor.select(lines, self._action==ACTION_SELECT_DOUBLE,
					event.state & CONTROL_MASK==0)

	# ----------------------------------------------------------------------
	def double(self, event):
		self._action = ACTION_SELECT_DOUBLE

	# ----------------------------------------------------------------------
	def pan(self, event):
		if self._pan:
			self.scan_dragto(event.x, event.y, gain=1)
		else:
			self.config(cursor="hand2")
			self.scan_mark(event.x, event.y)
			self._pan = True

	# ----------------------------------------------------------------------
	def panRelease(self, event):
		self._pan = False
		self.config(cursor="")

	# ----------------------------------------------------------------------
	def zoomCanvas(self, x0, y0, zoom):
		self.zoom *= zoom
		for i in self.find_all():
			self.scale(i, 0, 0, zoom, zoom)

		# Update last insert
		if self._lastInsert:
			coords = self.coords(self._lastInsert)
			x = coords[-2]
			y = coords[-1]
		else:
			x = y = 0
		self.coords(self._insert,
			(x-INSERT_WIDTH2, y-INSERT_WIDTH2,
			 x+INSERT_WIDTH2, y+INSERT_WIDTH2))

		# Update last insert
		if self._lastGantry:
			x,y = self.plotCoords([self._lastGantry])[0]
		else:
			x = y = 0
		self.coords(self._gantry,
			(x-INSERT_WIDTH2, y-INSERT_WIDTH2,
			 x+INSERT_WIDTH2, y+INSERT_WIDTH2))

		self._updateScrollBars()
		self.update_idletasks()

	# ----------------------------------------------------------------------
	def menuZoomIn(self, event=None):
		x = int(self.cget("width" ))/2.0
		y = int(self.cget("height"))/2.0
		self.zoomCanvas(x, y, 2.0)

	# ----------------------------------------------------------------------
	def menuZoomOut(self, event=None):
		x = int(self.cget("width" ))/2.0
		y = int(self.cget("height"))/2.0
		self.zoomCanvas(x, y, 0.5)

	# ----------------------------------------------------------------------
	def mouseZoomIn(self, event):
		self.zoomCanvas(self.canvasx(event.x), self.canvasy(event.y), 1.25)

	# ----------------------------------------------------------------------
	def mouseZoomOut(self,event):
		self.zoomCanvas(self.canvasx(event.x), self.canvasy(event.y), 1.0/1.25)

	# ----------------------------------------------------------------------
	# Change the insert marker location
	# ----------------------------------------------------------------------
	def insertMarker(self, no):
		try:
			item = self.items[no]
		except IndexError:
			return
		if item is not None and item != self._lastInsert:
			self._lastInsert = item
			coords = self.coords(item)
			x = coords[-2]
			y = coords[-1]
			self.coords(self._insert,
				(x-INSERT_WIDTH2, y-INSERT_WIDTH2,
				 x+INSERT_WIDTH2, y+INSERT_WIDTH2))

	#----------------------------------------------------------------------
	def gantry(self, wx, wy, wz, mx, my, mz):
		self._lastGantry = (wx,wy,wz)
		x,y = self.plotCoords([(wx,wy,wz)])[0]
		self.coords(self._gantry,
			(x-GANTRY_WIDTH2, y-GANTRY_WIDTH2,
			 x+GANTRY_WIDTH2, y+GANTRY_WIDTH2))

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
			xmin = self._dx-self.cnc.travel_x
			ymin = self._dy-self.cnc.travel_y
			zmin = self._dz-self.cnc.travel_z
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
	# Parse and draw the file from the editor to g-code commands
	#----------------------------------------------------------------------
	def draw(self, view, lines):
		if self._inParse: return
		self.view = view
		self._inParse = True
		self.initPosition()
		x0 = self.xview()[0]
		y0 = self.yview()[0]
		for no,line in enumerate(lines.splitlines()):
			cmd = self.cnc.parseLine(line)
			if cmd is None:
				self.items.append(None)
			else:
				self.items.append(self.drawPath(cmd))
		self.drawGrid()
		self.drawAxes()
		self.drawMargin()
		self.drawWorkarea()
		self.drawProbe()
#		self.tag_lower(self._workarea)
		self._updateScrollBars()
		self.xview_moveto(x0)
		self.yview_moveto(y0)
		self._inParse = False

	#----------------------------------------------------------------------
	def initPosition(self):
		self.delete(ALL)
		self._gantry = self.create_oval(
					(-GANTRY_WIDTH2,-GANTRY_WIDTH2),
					( GANTRY_WIDTH2, GANTRY_WIDTH2),
					width=2,
					outline=GANTRY_COLOR)
		self._lastInsert  = None
		self._insert = self.create_oval(
					(-INSERT_WIDTH2,-INSERT_WIDTH2),
					( INSERT_WIDTH2, INSERT_WIDTH2),
					fill=INSERT_COLOR)
		self._select = None
		self.items = []
		self.cnc.initPath()

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

		xmin = self._dx-self.cnc.travel_x
		ymin = self._dy-self.cnc.travel_y
		zmin = self._dz-self.cnc.travel_z
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
			for i in range(int(self.cnc.ymin//10), int(self.cnc.ymax//10)+1):
				y = i*10.0
				xyz = [(xmin,y,0), (xmax,y,0)]
				item = self.create_line(self.plotCoords(xyz),
							fill='Gray',
							dash=(1,2))
				self.tag_lower(item)

			for i in range(int(self.cnc.xmin//10), int(self.cnc.xmax//10)+1):
				x = i*10.0
				xyz = [(x,ymin,0), (x,ymax,0)]
				item = self.create_line(self.plotCoords(xyz),
							fill='Gray',
							dash=(1,2))
				self.tag_lower(item)

	#----------------------------------------------------------------------
	def drawProbe(self):
		if not self.draw_probe: return

		# Draw probe grid
		probe = self.cnc.probe
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
		for i,uv in enumerate(self.plotCoords(self.cnc.probe.points)):
			item = self.create_text(uv, text="%g"%(self.cnc.probe.points[i][2]),
					justify=CENTER, fill="Green")
			self.tag_lower(item)

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
	def drawPath(self, cmds):
		self.cnc.processPath(cmds)
		xyz = self.cnc.motionPath()
		if xyz:
			length = self.cnc.pathLength(xyz)
			self.cnc.pathMargins(xyz)
			coords = self.plotCoords(xyz)
			if coords:
				if self.cnc.gcode == 0:
					dash = (4,3)
				else:
					dash = None
				return self.create_line(coords, fill="Black", dash=dash)
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
