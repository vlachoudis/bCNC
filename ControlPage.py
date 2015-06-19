#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

try:
	from Tkinter import *
except ImportError:
	from tkinter import *

import Utils
import Ribbon
import tkExtra
import Unicode
import CNCRibbon

try:
	from serial.tools.list_ports import comports
except:
	from Utils import comports

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200]

DISTANCE_MODE = { "G90" : "Absolute",
		  "G91" : "Incremental" }
FEED_MODE     = { "G93" : "1/Time",
		  "G94" : "unit/min",
		  "G95" : "unit/rev"}
UNITS         = { "G20" : "inch",
		  "G21" : "mm" }
PLANE         = { "G17" : "XY",
		  "G18" : "ZX",
		  "G19" : "YZ" }

#===============================================================================
class RunLabelGroup(Ribbon.LabelGroup):
	def __init__(self, master, app):
		Ribbon.LabelGroup.__init__(self, master, "Run")

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["start32"],
				text="Run",
				compound=TOP,
				command=app.run,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Run g-code commands from editor to controller")

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["pause32"],
				text="Pause",
				compound=TOP,
				command=app.pause,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Pause running program. Sends either FEED_HOLD ! or CYCLE_START ~")

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["stop32"],
				text="Stop",
				compound=TOP,
				command=app.stopRun,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Pause running program and soft reset controller to empty the buffer.")

#===============================================================================
# Control Page
#===============================================================================
class ControlPage(CNCRibbon.Page):
	"""CNC communication and control"""

	_name_ = "Control"
	_icon_ = "control"

	#----------------------------------------------------------------------
	def createRibbon(self):
		CNCRibbon.Page.createRibbon(self)

		# ==========
		group = Ribbon.LabelGroup(self.ribbon, "Connection")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["home"],
				text="Home",
				compound=LEFT,
				anchor=W,
				command=self.app.home,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Perform a homing cycle")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["unlock"],
				text="Unlock",
				compound=LEFT,
				anchor=W,
				command=self.app.unlock,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Unlock controller")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["reset"],
				text="Reset",
				compound=LEFT,
				anchor=W,
				command=self.app.softReset,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Software reset of controller")

		# ==========
		group = Ribbon.LabelGroup(self.ribbon, "Serial")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		col,row=0,0
		b = Label(group.frame, text="Port:", background=Ribbon._BACKGROUND)
		b.grid(row=row,column=col,sticky=E)

		self.app.portCombo = tkExtra.Combobox(group.frame, False, background="White", width=16)
		self.app.portCombo.grid(row=row, column=col+1, sticky=EW)
		devices = sorted([x[0] for x in comports()])
		self.app.portCombo.fill(devices)
		self.app.portCombo.set(Utils.config.get("Connection","port"))

		row += 1
		b = Label(group.frame, text="Baud:", background=Ribbon._BACKGROUND)
		b.grid(row=row,column=col,sticky=E)

		self.app.baudCombo = tkExtra.Combobox(group.frame, True, background="White")
		self.app.baudCombo.grid(row=row, column=col+1, sticky=EW)
		self.app.baudCombo.fill(BAUDS)
		self.app.baudCombo.set(Utils.config.get("Connection","baud"))

		# ---
		col += 2
		row  = 0

		self.app.connectBtn = Ribbon.LabelButton(group.frame,
				image=Utils.icons["serial32"],
				text="Open",
				compound=TOP,
				command=self.app.openClose,
				background=Ribbon._BACKGROUND)
		self.app.connectBtn.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(self.app.connectBtn, "Open/Close serial port")

		# ==========
		self.runGroup = RunLabelGroup(self.ribbon, self.app)
		self.runGroup.pack(side=LEFT, fill=Y, padx=0, pady=0)

	#----------------------------------------------------------------------
	# Create Project page
	#----------------------------------------------------------------------
	def createPage(self):
		CNCRibbon.Page.createPage(self)

		# Control -> Control
		lframe = LabelFrame(self.page, text="Control", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		Label(lframe, text="Z").grid(row=row, column=col)

		col += 3
		Label(lframe, text="Y").grid(row=row, column=col)

		# ---
		row += 1
		col = 0

		width=3
		height=2

		b = Button(lframe, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
#					command=self.moveZup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Z")
		self.addWidget(b)

		col += 2
		b = Button(lframe, text=Unicode.UPPER_LEFT_TRIANGLE,
#					command=self.moveXdownYup,
					width=width, height=height,
					activebackground="LightYellow")

		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X +Y")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
#					command=self.moveYup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Y")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text=Unicode.UPPER_RIGHT_TRIANGLE,
#					command=self.moveXupYup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X +Y")
		self.addWidget(b)

		col += 2
		b = Button(lframe, text=u"\u00D710",
#				command=self.mulStep,
				width=3,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Multiply step by 10")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text="+",
#				command=self.incStep,
				width=3,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Increase step by 1 unit")
		self.addWidget(b)

		# ---
		row += 1

		# -- Addition --
		col = 0
#		if Utils.config.get("Control","zstep"):
#			self.zstep = tkExtra.Combobox(lframe, width=1, background="White")
#			self.zstep.grid(row=row, column=col, columnspan=1, sticky=EW)
#			self.zstep.set(Utils.config.get("Control","zstep"))
#			self.zstep.fill(["0.001",
#					"0.005",
#					"0.01",
#					"0.05",
#					"0.1",
#					"0.5",
#					"1",
#					"5",
#					"10"])
#			tkExtra.Balloon.set(self.zstep, "Step for Z move operation")
#			self.addWidget(self.zstep)
#		else:
#			self.zstep = self.step

		col = 1
		Label(lframe, text="X", width=3, anchor=E).grid(row=row, column=col, sticky=E)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
#					command=self.moveXdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X")
		self.addWidget(b)

		col += 1
		b = Utils.UserButton(lframe, self.app, 0, text=Unicode.LARGE_CIRCLE,
#					command=self.go2origin,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move to Origin.\nUser configurable button.\nRight click to configure.")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
#					command=self.moveXup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X")
		self.addWidget(b)

		# --
		col += 1
		Label(lframe,"",width=2).grid(row=row,column=col)

		col += 1
		self.step = tkExtra.Combobox(lframe, width=6, background="White")
		self.step.grid(row=row, column=col, columnspan=2, sticky=EW)
		self.step.set(Utils.config.get("Control","step"))
		self.step.fill(["0.001",
				"0.005",
				"0.01",
				"0.05",
				"0.1",
				"0.5",
				"1",
				"5",
				"10",
				"50",
				"100",
				"500"])
		tkExtra.Balloon.set(self.step, "Step for every move operation")
		self.addWidget(self.step)

		# Onekk request
		self.zstep = self.step

		# ---
		row += 1
		col = 0

		b = Button(lframe, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
#					command=self.moveZdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Z")
		self.addWidget(b)

		col += 2
		b = Button(lframe, text=Unicode.LOWER_LEFT_TRIANGLE,
#					command=self.moveXdownYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X -Y")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
#					command=self.moveYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Y")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text=Unicode.LOWER_RIGHT_TRIANGLE,
#					command=self.moveXupYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X -Y")
		self.addWidget(b)

		col += 2
		b = Button(lframe, text=u"\u00F710",
#					command=self.divStep,
					padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Divide step by 10")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text="-",
#					command=self.decStep,
					padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Decrease step by 1 unit")
		self.addWidget(b)

		#lframe.grid_columnconfigure(6,weight=1)

		lframe = LabelFrame(self.page, text="User", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		n = Utils.getInt("Buttons","n",6)
		for i in range(1,n):
			b = Utils.UserButton(lframe, self.app, i)
			b.grid(row=0, column=i-1, sticky=NSEW)
			lframe.grid_columnconfigure(i-1, weight=1)
			self.addWidget(b)

		# Control -> State
		lframe = LabelFrame(self.page, text="State", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		# State
		f = Frame(lframe)
		f.pack(side=TOP, fill=X)

		# Absolute or relative mode
		row, col = 0, 0
		Label(f, text="Distance:").grid(row=row, column=col, sticky=E)
		col += 1
		self.distanceMode = tkExtra.Combobox(f, True,
#					command=self.distanceChange,
					width=5,
					background="White")
		self.distanceMode.fill(sorted(DISTANCE_MODE.values()))
		self.distanceMode.grid(row=row, column=col, columnspan=2, sticky=EW)
		tkExtra.Balloon.set(self.distanceMode, "Distance Mode [G90,G91]")

		# populate gstate dictionary
		for k,v in DISTANCE_MODE.items(): self.app.gstate[k] = (self.distanceMode, v)

		# Units mode
		col += 2
		Label(f, text="Units:").grid(row=row, column=col, sticky=E)
		col += 1
		self.units = tkExtra.Combobox(f, True,
#					command=self.unitsChange,
					width=5,
					background="White")
		self.units.fill(sorted(UNITS.values()))
		self.units.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.units, "Units [G20, G21]")
		for k,v in UNITS.items(): self.app.gstate[k] = (self.units, v)

		# Feed mode
		row += 1
		col = 0
		Label(f, text="Feed:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedRate = tkExtra.FloatEntry(f, background="White", width=5)
		self.feedRate.grid(row=row, column=col, sticky=EW)
#		self.feedRate.bind('<Return>',   self.setFeedRate)
#		self.feedRate.bind('<KP_Enter>', self.setFeedRate)
		tkExtra.Balloon.set(self.feedRate, "Feed Rate [F#]")

		col += 1
		b = Button(f, text="set",
#				command=self.setFeedRate,
				padx=1, pady=1)
		b.grid(row=row, column=col, columnspan=2, sticky=W)

		col += 1
		Label(f, text="Mode:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedMode = tkExtra.Combobox(f, True,
#					command=self.feedModeChange,
					width=5,
					background="White")
		self.feedMode.fill(sorted(FEED_MODE.values()))
		self.feedMode.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.feedMode, "Feed Mode [G93, G94, G95]")
		for k,v in FEED_MODE.items(): self.app.gstate[k] = (self.feedMode, v)

		# Tool
		row += 1
		col = 0
		Label(f, text="Tool:").grid(row=row, column=col, sticky=E)

		col += 1
		self.toolEntry = tkExtra.IntegerEntry(f, background="White", width=5)
		self.toolEntry.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.toolEntry, "Tool number [T#]")

		col += 1
		b = Button(f, text="set",
#				command=self.setTool,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=W)

		# Plane
		col += 1
		Label(f, text="Plane:").grid(row=row, column=col, sticky=E)
		col += 1
		self.plane = tkExtra.Combobox(f, True,
#					command=self.planeChange,
					width=5,
					background="White")
		self.plane.fill(sorted(PLANE.values()))
		self.plane.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.plane, "Plane [G17,G18,G19]")
		for k,v in PLANE.items(): self.app.gstate[k] = (self.plane, v)

		f.grid_columnconfigure(1, weight=1)
		f.grid_columnconfigure(4, weight=1)

		# Spindle
		f = Frame(lframe)
		f.pack(side=BOTTOM, fill=X)
		self.spindle = BooleanVar()
		self.spindleSpeed = IntVar()

		b = Checkbutton(f, text="Spindle",
				image=Utils.icons["spinningtop"],
#				command=self.spindleControl,
				compound=LEFT,
				indicatoron=False,
				variable=self.spindle)
		tkExtra.Balloon.set(b, "Start/Stop spindle (M3/M5)")
		b.pack(side=LEFT, fill=Y)
		self.addWidget(b)

		b = Scale(f,	variable=self.spindleSpeed,
#				command=self.spindleControl,
				showvalue=True,
				orient=HORIZONTAL,
				from_=Utils.config.get("CNC","spindlemin"),
				to_=Utils.config.get("CNC","spindlemax"))
		tkExtra.Balloon.set(b, "Set spindle RPM")
		b.pack(side=RIGHT, expand=YES, fill=X)
		self.addWidget(b)

	#----------------------------------------------------------------------
	# Jogging
	#----------------------------------------------------------------------
	def moveXup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%s\nG90\n"%(self.step.get()))

	def moveXdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%s\nG90\n"%(self.step.get()))

	def moveYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Y%s\nG90\n"%(self.step.get()))

	def moveYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Y-%s\nG90\n"%(self.step.get()))

	def moveXdownYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXdownYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveZup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z%s\nG90\n"%(self.zstep.get()))

	def moveZdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z-%s\nG90\n"%(self.zstep.get()))

	def go2origin(self, event=None):
		self.sendGrbl("G90G0X0Y0Z0\n")

	def resetCoords(self, event):
		if not self.app.running: self.sendGrbl("G10P0L20X0Y0Z0\n")

	def resetX(self, event):
		if not self.app.running: self.sendGrbl("G10P0L20X0\n")

	def resetY(self, event):
		if not self.app.running: self.sendGrbl("G10P0L20Y0\n")

	def resetZ(self, event):
		if not self.app.running: self.sendGrbl("G10P0L20Z0\n")
