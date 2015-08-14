#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

__version__ = "0.4.13"
__date__    = "12 Aug 2015"
__author__  = "Vasilis Vlachoudis"
__email__   = "vvlachoudis@gmail.com"

import os
import re
import sys
import pdb
import glob
import math
import time
import getopt
import string
import serial
import socket
import threading
import webbrowser
try:
	from serial.tools.list_ports import comports
except:
	from Utils import comports

try:
	import Tkinter
	from Queue import *
	from Tkinter import *
	import ConfigParser
	import tkMessageBox
except ImportError:
	import tkinter
	from queue import *
	from tkinter import *
	import configparser as ConfigParser
	import tkinter.messagebox as tkMessageBox

import rexx
import tkExtra
import Unicode
import bFileDialog

import CNC
import Utils
import CNCList
import CNCTools
import CNCCanvas
import CNCPendant

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200]

SERIAL_POLL   = 0.250	# s
G_POLL        = 10	# s
MONITOR_AFTER =  250	# ms
DRAW_AFTER    =  300	# ms

RX_BUFFER_SIZE = 128

MAX_HISTORY  = 500

GPAT     = re.compile(r"[A-Za-z]\d+.*")
LINEPAT  = re.compile(r"^(.*?)\n(.*)", re.DOTALL|re.MULTILINE)
STATUSPAT= re.compile(r"^<(\w*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),?(.*)>$")
POSPAT   = re.compile(r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*):?(\d*)\]$")
TLOPAT   = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")

_LOWSTEP   = 0.0001
_HIGHSTEP  = 1000.0

NOT_CONNECTED = "Not connected"

WCS  = ["G54", "G55", "G56", "G57", "G58", "G59"]
ZERO = ["G28", "G30", "G92"]

STATECOLOR = {	"Alarm": "Red",
		"Run"  : "LightGreen",
		"Hold" : "Orange",
		"Connected" : "Orange",
		NOT_CONNECTED: "OrangeRed"}
STATECOLORDEF = "LightYellow"

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

#==============================================================================
# Main Application window
#==============================================================================
class Application(Toplevel):
	def __init__(self, master, **kw):
		Toplevel.__init__(self, master, **kw)
		self.iconbitmap("@%s/bCNC.xbm"%(Utils.prgpath))
		self.title(Utils.__prg__)
		self.widgets = []

		# Global variables
		self.history     = []
		self._historyPos = None
		CNC.CNC.loadConfig(Utils.config)
		self.gcode = CNC.GCode()
		self.cnc   = self.gcode.cnc
		self.view  = StringVar()
		self.view.set(CNCCanvas.VIEWS[0])
		self.view.trace('w', self.viewChange)
		self.tools = CNCTools.Tools(self.gcode)
		self.loadConfig()	# load rest of config
		self.gstate = {}	# $G state results widget dictionary

		self.draw_axes   = BooleanVar()
		self.draw_axes.set(bool(int(Utils.config.get("Canvas","axes"))))
		self.draw_grid   = BooleanVar()
		self.draw_grid.set(bool(int(Utils.config.get("Canvas","grid"))))
		self.draw_margin = BooleanVar()
		self.draw_margin.set(bool(int(Utils.config.get("Canvas","margin"))))
		self.draw_probe  = BooleanVar()
		self.draw_probe.set(bool(int(Utils.config.get("Canvas","probe"))))
		self.draw_paths  = BooleanVar()
		self.draw_paths.set(bool(int(Utils.config.get("Canvas","paths"))))
		self.draw_rapid  = BooleanVar()
		self.draw_rapid.set(bool(int(Utils.config.get("Canvas","rapid"))))
		self.draw_workarea = BooleanVar()
		self.draw_workarea.set(bool(int(Utils.config.get("Canvas","workarea"))))

		# --- Toolbar ---
		toolbar = Frame(self, relief=RAISED)
		toolbar.pack(side=TOP, fill=X)

		# Main frame
		paned = PanedWindow(self, orient=HORIZONTAL)
		paned.pack(fill=BOTH, expand=YES)

		# Status bar
		f = Frame(self)
		f.pack(side=BOTTOM, fill=X)
		self.statusbar = Label(f, relief=SUNKEN,
			foreground="DarkBlue", justify=LEFT, anchor=W)
		self.statusbar.pack(side=LEFT, fill=X, expand=TRUE)

		self.canvasbar = Label(f, relief=SUNKEN,
			foreground="DarkBlue", justify=LEFT, anchor=W)
		self.canvasbar.pack(side=RIGHT, fill=X, expand=TRUE)

		# Command bar
		f = Frame(self)
		f.pack(side=BOTTOM, fill=X)
		self.cmdlabel = Label(f, text="Command:")
		self.cmdlabel.pack(side=LEFT)
		self.command = Entry(f, relief=SUNKEN, background="White")
		self.command.pack(side=RIGHT, fill=X, expand=YES)
		self.command.bind("<Return>",	self.cmdExecute)
		self.command.bind("<Up>",	self.commandHistoryUp)
		self.command.bind("<Down>",	self.commandHistoryDown)
		self.command.bind("<FocusIn>",	self.commandFocusIn)
		self.command.bind("<FocusOut>",	self.commandFocusOut)
		self.command.bind("<Control-Key-z>",	self.undo)
		self.command.bind("<Control-Key-Z>",	self.redo)
		self.command.bind("<Control-Key-y>",	self.redo)
		tkExtra.Balloon.set(self.command,
			"MDI Command line: Accept g-code commands or macro "
			"commands (RESET/HOME...) or editor commands "
			"(move,inkscape, round...) [Space or Ctrl-Space]")
		self.widgets.append(self.command)

		# --- Editor ---
		panedframe = Frame(paned)
		paned.add(panedframe, minsize=240)

		frame = Frame(panedframe, relief=RAISED)
		frame.pack(side=TOP, fill=X, pady=1)

		row = 0
		col = 0
		Label(frame,text="Status:").grid(row=row,column=col,sticky=E)
		col += 1
		self.state = Label(frame,
				text=NOT_CONNECTED,
				font=self.drofont,
				background=STATECOLOR[NOT_CONNECTED])
		self.state.grid(row=row,column=col, columnspan=3, sticky=EW)

		row += 1
		col = 0
		Label(frame,text="WPos:").grid(row=row,column=col,sticky=E)

		# work
		col += 1
		self.xwork = Label(frame, font=self.drofont, background="White",anchor=E)
		self.xwork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.xwork, "X work position")

		# ---
		col += 1
		self.ywork = Label(frame, font=self.drofont, background="White",anchor=E)
		self.ywork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.ywork, "Y work position")

		# ---
		col += 1
		self.zwork = Label(frame, font=self.drofont, background="White", anchor=E)
		self.zwork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.zwork, "Z work position")

		# Machine
		row += 1
		col = 0
		Label(frame,text="MPos:").grid(row=row,column=col,sticky=E)

		col += 1
		self.xmachine = Label(frame, font=self.drofont, background="White",anchor=E)
		self.xmachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.ymachine = Label(frame, font=self.drofont, background="White",anchor=E)
		self.ymachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.zmachine = Label(frame, font=self.drofont, background="White", anchor=E)
		self.zmachine.grid(row=row,column=col,padx=1,sticky=EW)

		frame.grid_columnconfigure(1, weight=1)
		frame.grid_columnconfigure(2, weight=1)
		frame.grid_columnconfigure(3, weight=1)

		# Tab page set
		self.tabPage = tkExtra.TabPageSet(panedframe, pageNames=
					[("Control",  Utils.icons["control"]),
					 ("Terminal", Utils.icons["terminal"]),
					 ("WCS",      Utils.icons["measure"]),
					 ("Tools",    Utils.icons["tools"]),
					 ("Editor",   Utils.icons["edit"])])
		self.tabPage.pack(fill=BOTH, expand=YES)
		self.tabPage.bind("<<ChangePage>>", self.changePage)

		self._controlTab()
		self._terminalTab()
		self._wcsTab()
		self._editorTab()

		# ---- Tools ----
		frame = self.tabPage["Tools"]

		self.toolFrame = CNCTools.ToolFrame(frame, self, self.tools)
		self.toolFrame.pack(fill=BOTH, expand=YES)

		# --- Canvas ---
		frame = Frame(paned)
		paned.add(frame)

		self.canvas = CNCCanvas.CNCCanvas(frame, self, takefocus=True, background="White")
		self.canvas.grid(row=0, column=0, sticky=NSEW)
		sb = Scrollbar(frame, orient=VERTICAL, command=self.canvas.yview)
		sb.grid(row=0, column=1, sticky=NS)
		self.canvas.config(yscrollcommand=sb.set)
		sb = Scrollbar(frame, orient=HORIZONTAL, command=self.canvas.xview)
		sb.grid(row=1, column=0, sticky=EW)
		self.canvas.config(xscrollcommand=sb.set)

		frame.grid_rowconfigure(0, weight=1)
		frame.grid_columnconfigure(0, weight=1)

		# Canvas bindings
		self.canvas.bind('<Control-Key-c>',	self.copy)
		self.canvas.bind('<Control-Key-x>',	self.cut)
		self.canvas.bind('<Control-Key-v>',	self.paste)
#		self.canvas.bind("<Control-Key-Up>",	self.commandOrderUp)
#		self.canvas.bind("<Control-Key-Down>",	self.commandOrderDown)
		self.canvas.bind("<Delete>",		self.gcodelist.deleteLine)
		self.canvas.bind("<BackSpace>",		self.gcodelist.deleteLine)
		try:
			self.canvas.bind("<KP_Delete>",	self.gcodelist.deleteLine)
		except:
			pass

		# Global bindings
		self.bind('<Escape>',		self.unselectAll)
		self.bind('<Control-Key-a>',	self.selectAll)
		self.bind('<Control-Key-f>',	self.find)
		self.bind('<Control-Key-g>',	self.findNext)
		self.bind('<Control-Key-h>',	self.replace)
		self.bind('<Control-Key-e>',	self.gcodelist.toggleExpand)
		self.bind('<Control-Key-l>',	self.gcodelist.toggleEnable)
		self.bind("<Control-Key-q>",	self.quit)
		self.bind("<Control-Key-o>",	self.loadDialog)
		self.bind("<Control-Key-r>",	self.drawAfter)
		self.bind("<Control-Key-s>",	self.saveAll)
		self.bind('<Control-Key-y>',	self.redo)
		self.bind('<Control-Key-z>',	self.undo)
		self.bind('<Control-Key-Z>',	self.redo)
		self.canvas.bind('<Key-space>',	self.commandFocus)
		self.bind('<Control-Key-space>',self.commandFocus)

#		self.bind('<F1>',		self.help)
#		self.bind('<F2>',		self.rename)

		self.bind('<F3>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XY]))
		self.bind('<F4>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XZ]))
		self.bind('<F5>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_YZ]))
		self.bind('<F6>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO1]))
		self.bind('<F7>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO2]))
		self.bind('<F8>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO3]))

		self.bind('<Up>',		self.moveYup)
		self.bind('<Down>',		self.moveYdown)
		self.bind('<Right>',		self.moveXup)
		self.bind('<Left>',		self.moveXdown)
		self.bind('<Prior>',		self.moveZup)
		self.bind('<Next>',		self.moveZdown)

		self.bind('<Key-plus>',		self.incStep)
		self.bind('<Key-equal>',	self.incStep)
		self.bind('<KP_Add>',		self.incStep)
		self.bind('<Key-minus>',	self.decStep)
		self.bind('<Key-underscore>',	self.decStep)
		self.bind('<KP_Subtract>',	self.decStep)

		self.bind('<Key-asterisk>',	self.mulStep)
		self.bind('<KP_Multiply>',	self.mulStep)
		self.bind('<Key-slash>',	self.divStep)
		self.bind('<KP_Divide>',	self.divStep)

		self.bind('<Key-exclam>',	self.feedHold)
		self.bind('<Key-asciitilde>',	self.resume)

		self.bind('<FocusIn>',		self.focusIn)

		self.protocol("WM_DELETE_WINDOW", self.quit)

		for x in self.widgets:
			if isinstance(x,Entry):
				x.bind("<Escape>", self.canvasFocus)

		# Tool bar and Menu
		self.createToolbar(toolbar)
		self.createMenu()

		self.canvas.focus_set()

		# Highlight variables
		self.queue       = Queue()	# Command queue to send to GRBL
		self.log         = Queue()	# Log queue returned from GRBL
		self.pendant     = Queue()	# Command queue to be executed from Pendant
		self.serial      = None
		self.thread      = None
		self._dx = self._dy = self._dz = 0.0
		self._pos        = {"wx":0.0, "wy":0.0, "wz":0.0,
				    "mx":0.0, "my":0.0, "mz":0.0,
				    "state": NOT_CONNECTED,
				    "color": STATECOLOR[NOT_CONNECTED],
				    "G": ["G20","G54"]}
		self._posUpdate  = False
		self._wcsUpdate  = False
		self._probeUpdate= False
		self._gUpdate    = False
		self._pendantFileUploaded = None
		self.running     = False
		self._stop       = False	# Raise to stop current run
		self._runLines   = 0
		#self._runLineMap = []
		self._quit       = 0
		self._pause      = False
		self._drawAfter  = None	# after handle for modification
		self._alarm      = True
		self._inFocus    = False
		self.monitorSerial()
		self.toggleDrawFlag()

		# Create tools
		self.toolFrame.fill()
		try:
			self.toolFrame.set(Utils.config.get(Utils.__prg__, "tool"))
		except:
			self.toolFrame.set("Box")

		if int(Utils.config.get("Connection","pendant")):
			self.startPendant(False)

		if int(Utils.config.get("Connection","openserial")):
			self.openClose()

	#----------------------------------------------------------------------
	# Control
	#----------------------------------------------------------------------
	def _controlTab(self):
		frame = self.tabPage["Control"]

		# Control -> Connection
		lframe = LabelFrame(frame, text="Connection", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		Label(lframe,text="Port:").grid(row=0,column=0,sticky=E)
		self.portCombo = tkExtra.Combobox(lframe, False, background="White", width=8)
		self.portCombo.grid(row=0, column=1, columnspan=2, sticky=EW)
		devices = sorted([x[0] for x in comports()])
		self.portCombo.fill(devices)
		self.portCombo.set(Utils.config.get("Connection","port"))

		self.connectBtn = Button(lframe, text="Open",
					compound=LEFT,
					image=Utils.icons["serial"],
					command=self.openClose,
					background="LightGreen",
					activebackground="LightGreen",
					padx=2, pady=2)
		self.connectBtn.grid(row=0,column=3,sticky=EW)
		tkExtra.Balloon.set(self.connectBtn, "Open/Close serial port")

		b = Button(lframe, text="Home",
				compound=LEFT,
				image=Utils.icons["home"],
				command=self.home,
				padx=2)
		b.grid(row=1,column=1,sticky=EW)
		tkExtra.Balloon.set(b, "Perform a homing cycle")
		self.widgets.append(b)

		b = Button(lframe, text="Unlock",
				compound=LEFT,
				image=Utils.icons["unlock"],
				command=self.unlock,
				padx=2)
		b.grid(row=1,column=2,sticky=EW)
		tkExtra.Balloon.set(b, "Unlock device")
		self.widgets.append(b)

		b = Button(lframe, text="Reset",
				compound=LEFT,
				image=Utils.icons["reset"],
				command=self.softReset,
				foreground="DarkRed",
				background="LightYellow",
				activebackground="LightYellow",
				padx=2,pady=1)
		b.grid(row=1,column=3,sticky=EW)
		tkExtra.Balloon.set(b, "Software reset of controller")
		self.widgets.append(b)

		lframe.grid_columnconfigure(1, weight=1)
		lframe.grid_columnconfigure(2, weight=1)

		# Control -> Control
		lframe = LabelFrame(frame, text="Control", foreground="DarkBlue")
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
					width=width, height=height,
					command=self.moveZup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Z")
		self.widgets.append(b)

		col += 2
		b = Button(lframe, text=Unicode.UPPER_LEFT_TRIANGLE,
					width=width, height=height,
					command=self.moveXdownYup)

		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X +Y")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveYup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Y")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text=Unicode.UPPER_RIGHT_TRIANGLE,
					width=width, height=height,
					command=self.moveXupYup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X +Y")
		self.widgets.append(b)

		col += 2
		b = Button(lframe, text=u"\u00D710", width=3, padx=1, pady=1, command=self.mulStep)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Multiply step by 10")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text="+", width=3, padx=1, pady=1, command=self.incStep)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Increase step by 1 unit")
		self.widgets.append(b)

		# ---
		row += 1
		col = 0
		b = Button(lframe, text=Unicode.LARGE_CIRCLE,
					width=width, height=height)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move to Z0")
		self.widgets.append(b)

		col += 1
		col = 1
		Label(lframe, text="X", width=3, anchor=E).grid(row=row, column=col, sticky=E)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveXdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X")
		self.widgets.append(b)

		col += 1
		b = Utils.UserButton(lframe, self, 0, text=Unicode.LARGE_CIRCLE,
					width=width, height=height,
					command=self.go2origin)
		b.grid(row=row, column=col, sticky=EW)
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveXup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X")
		self.widgets.append(b)

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
		self.widgets.append(self.step)

		# ---
		row += 1
		col = 0

		b = Button(lframe, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveZdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Z")
		self.widgets.append(b)

		col += 2
		b = Button(lframe, text=Unicode.LOWER_LEFT_TRIANGLE,
					width=width, height=height,
					command=self.moveXdownYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X -Y")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Y")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text=Unicode.LOWER_RIGHT_TRIANGLE,
					width=width, height=height,
					command=self.moveXupYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X -Y")
		self.widgets.append(b)

		col += 2
		b = Button(lframe, text=u"\u00F710", padx=1, pady=1, command=self.divStep)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Divide step by 10")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text="-", padx=1, pady=1, command=self.decStep)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Decrease step by 1 unit")
		self.widgets.append(b)

		#lframe.grid_columnconfigure(6,weight=1)

		lframe = LabelFrame(frame, text="User", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		n = Utils.getInt("Buttons","n",6)
		for i in range(1,n):
			b = Utils.UserButton(lframe, self, i)
			b.grid(row=0, column=i-1, sticky=NSEW)
			lframe.grid_columnconfigure(i-1, weight=1)
			self.widgets.append(b)

		# Control -> State
		lframe = LabelFrame(frame, text="State", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		# State
		f = Frame(lframe)
		f.pack(side=TOP, fill=X)

		# Absolute or relative mode
		row, col = 0, 0
		Label(f, text="Distance:").grid(row=row, column=col, sticky=E)
		col += 1
		self.distanceMode = tkExtra.Combobox(f, True,
					width=5,
					background="White",
					command=self.distanceChange)
		self.distanceMode.fill(sorted(DISTANCE_MODE.values()))
		self.distanceMode.grid(row=row, column=col, columnspan=2, sticky=EW)
		tkExtra.Balloon.set(self.distanceMode, "Distance Mode [G90,G91]")

		# populate gstate dictionary
		for k,v in DISTANCE_MODE.items(): self.gstate[k] = (self.distanceMode, v)

		# Units mode
		col += 2
		Label(f, text="Units:").grid(row=row, column=col, sticky=E)
		col += 1
		self.units = tkExtra.Combobox(f, True,
					width=5,
					background="White",
					command=self.unitsChange)
		self.units.fill(sorted(UNITS.values()))
		self.units.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.units, "Units [G20, G21]")
		for k,v in UNITS.items(): self.gstate[k] = (self.units, v)

		# Feed mode
		row += 1
		col = 0
		Label(f, text="Feed:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedRate = tkExtra.FloatEntry(f, background="White", width=5)
		self.feedRate.grid(row=row, column=col, sticky=EW)
		self.feedRate.bind('<Return>',   self.setFeedRate)
		self.feedRate.bind('<KP_Enter>', self.setFeedRate)
		tkExtra.Balloon.set(self.feedRate, "Feed Rate [F#]")

		col += 1
		b = Button(f, text="set",
				command=self.setFeedRate,
				padx=1, pady=1)
		b.grid(row=row, column=col, columnspan=2, sticky=W)

		col += 1
		Label(f, text="Mode:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedMode = tkExtra.Combobox(f, True,
					width=5,
					background="White",
					command=self.feedModeChange)
		self.feedMode.fill(sorted(FEED_MODE.values()))
		self.feedMode.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.feedMode, "Feed Mode [G93, G94, G95]")
		for k,v in FEED_MODE.items(): self.gstate[k] = (self.feedMode, v)

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
				command=self.setTool,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=W)

		# Plane
		col += 1
		Label(f, text="Plane:").grid(row=row, column=col, sticky=E)
		col += 1
		self.plane = tkExtra.Combobox(f, True,
					width=5,
					background="White",
					command=self.planeChange)
		self.plane.fill(sorted(PLANE.values()))
		self.plane.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.plane, "Plane [G17,G18,G19]")
		for k,v in PLANE.items(): self.gstate[k] = (self.plane, v)

		f.grid_columnconfigure(1, weight=1)
		f.grid_columnconfigure(4, weight=1)

		# Spindle
		f = Frame(lframe)
		f.pack(side=BOTTOM, fill=X)
		self.spindle = BooleanVar()
		self.spindleSpeed = IntVar()

		b = Checkbutton(f, text="Spindle",
				image=Utils.icons["spinningtop"],
				compound=LEFT,
				indicatoron=False,
				variable=self.spindle,
				command=self.spindleControl)
		tkExtra.Balloon.set(b, "Start/Stop spindle (M3/M5)")
		b.pack(side=LEFT, fill=Y)
		self.widgets.append(b)

		b = Scale(f, command=self.spindleControl,
				variable=self.spindleSpeed,
				showvalue=True,
				orient=HORIZONTAL,
				from_=Utils.config.get("CNC","spindlemin"),
				to_=Utils.config.get("CNC","spindlemax"))
		tkExtra.Balloon.set(b, "Set spindle RPM")
		b.pack(side=RIGHT, expand=YES, fill=X)
		self.widgets.append(b)

		# Control -> Run
		lframe = LabelFrame(frame, text="Run", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)
		f = Frame(lframe)
		f.pack(side=TOP,fill=X)
		b = Button(f, text="Run",
				compound=LEFT,
				image=Utils.icons["start"],
				padx=3, pady=2,
				command=self.run)
		b.pack(side=LEFT,expand=YES,fill=X)
		tkExtra.Balloon.set(b, "Send g-code commands from editor to CNC")
		self.widgets.append(b)

		b = Button(f, text="Pause",
				compound=LEFT,
				image=Utils.icons["pause"],
				padx=3, pady=2,
				command=self.pause)
		b.pack(side=LEFT,expand=YES,fill=X)
		tkExtra.Balloon.set(b, "Pause running program. Sends either FEED_HOLD ! or CYCLE_START ~")

		b = Button(f, text="Stop",
				compound=LEFT,
				image=Utils.icons["stop"],
				padx=3, pady=2,
				command=self.stopRun)
		tkExtra.Balloon.set(b, "Stop running program")
		b.pack(side=LEFT,expand=YES,fill=X)

		self.progress = tkExtra.ProgressBar(lframe, height=24)
		self.progress.pack(fill=X)

	#----------------------------------------------------------------------
	# Terminal
	#----------------------------------------------------------------------
	def _terminalTab(self):
		frame = self.tabPage["Terminal"]
		self.terminal = Text(frame,
					background="White",
					width=20,
					wrap=NONE,
					state=DISABLED)
		self.terminal.pack(side=LEFT, fill=BOTH, expand=YES)
		sb = Scrollbar(frame, orient=VERTICAL, command=self.terminal.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.terminal.config(yscrollcommand=sb.set)
		self.terminal.tag_config("SEND",  foreground="Blue")
		self.terminal.tag_config("ERROR", foreground="Red")

	#----------------------------------------------------------------------
	# WorkSpace
	#----------------------------------------------------------------------
	def _wcsTab(self):
		frame = self.tabPage["WCS"]

		# WorkSpace -> WPS
		lframe = LabelFrame(frame, text="WCS", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		self.wcsvar = IntVar()
		self.wcsvar.set(0)

		row=0

		row += 1
		col  = 0
		for p,w in enumerate(WCS):
			col += 1
			b = Radiobutton(lframe, text=w,
					foreground="DarkRed",
					font = "Helvetica,14",
					padx=2, pady=2,
					variable=self.wcsvar,
					value=p,
					indicatoron=FALSE,
					command=self.wcsChange)
			b.grid(row=row, column=col,  sticky=NSEW)
			self.widgets.append(b)
			if col%3==0:
				row += 1
				col  = 0

		row += 1
		col=1
		Label(lframe, text="X").grid(row=row, column=col)
		col += 1
		Label(lframe, text="Y").grid(row=row, column=col)
		col += 1
		Label(lframe, text="Z").grid(row=row, column=col)

		row += 1
		col = 1
		x = Label(lframe, foreground="DarkBlue", background="gray95")
		x.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

		col += 1
		y = Label(lframe, foreground="DarkBlue", background="gray95")
		y.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

		col += 1
		z = Label(lframe, foreground="DarkBlue", background="gray95")
		z.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

		self.wcs = (x,y,z)

		# Set workspace
		row += 1
		col  = 1
		self.wcsX = tkExtra.FloatEntry(lframe, background="White")
		self.wcsX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsX, "If not empty set the X workspace")
		self.wcsX.bind("<Return>",   self.wcsSet)
		self.wcsX.bind("<KP_Enter>", self.wcsSet)
		self.widgets.append(self.wcsX)

		col += 1
		self.wcsY = tkExtra.FloatEntry(lframe, background="White")
		self.wcsY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsY, "If not empty set the Y workspace")
		self.widgets.append(self.wcsY)
		self.wcsY.bind("<Return>",   self.wcsSet)
		self.wcsY.bind("<KP_Enter>", self.wcsSet)

		col += 1
		self.wcsZ = tkExtra.FloatEntry(lframe, background="White")
		self.wcsZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsZ, "If not empty set the Z workspace")
		self.widgets.append(self.wcsZ)
		self.wcsZ.bind("<Return>",   self.wcsSet)
		self.wcsZ.bind("<KP_Enter>", self.wcsSet)

		col += 1
		b = Button(lframe, text="set",
				command=self.wcsSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.widgets.append(b)

		# set zero
		row += 1
		col  = 1
		b = Button(lframe, text="X=0",
				command=self.wcsSetX0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set X coordinate to zero")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text="Y=0",
				command=self.wcsSetY0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set Y coordinate to zero")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text="Z=0",
				command=self.wcsSetZ0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set Z coordinate to zero")
		self.widgets.append(b)

		col += 1
		b = Button(lframe, text="Zero",
				command=self.wcsSet0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Zero all coordinates")
		self.widgets.append(b)

		# Tool offset
		row += 1
		col =  0
		Label(lframe, text="TLO", foreground="DarkRed").grid(
				row=row, rowspan=2, column=col, sticky=EW)
		col += 2
		self._tlo = Label(lframe, foreground="DarkBlue", background="gray95")
		self._tlo.grid(row=row, column=col, sticky=EW)

		col += 1
		self._tloin = tkExtra.FloatEntry(lframe, background="White")
		self._tloin.grid(row=row, column=col, sticky=EW)
		self.widgets.append(self._tloin)
		self._tloin.bind("<Return>",   self.tloSet)
		self._tloin.bind("<KP_Enter>", self.tloSet)

		col += 1
		b = Button(lframe, text="set",
				command=self.tloSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.widgets.append(b)

		# Zero system
		row += 1
		col  = 1
		b = Button(lframe, text="G28", padx=2, pady=2, command=self.g28Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.widgets.append(b)
		tkExtra.Balloon.set(b, "G28: Go to zero via point")

		col += 1
		b = Button(lframe, text="G30", padx=2, pady=2, command=self.g30Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.widgets.append(b)
		tkExtra.Balloon.set(b, "G30: Go to zero via point")

		col += 1
		b = Button(lframe, text="G92", padx=2, pady=2, command=self.g92Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.widgets.append(b)
		tkExtra.Balloon.set(b, "G92: Set zero system (LEGACY)")

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# ---- WorkSpace ----
		#frame = self.tabPage["Probe"]

		# WorkSpace -> Probe
		lframe = LabelFrame(frame, text="Probe", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		Label(lframe, text="Probe:").grid(row=row, column=col, sticky=E)

		col += 1
		self._probeX = Label(lframe, foreground="DarkBlue", background="gray95")
		self._probeX.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self._probeY = Label(lframe, foreground="DarkBlue", background="gray95")
		self._probeY.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self._probeZ = Label(lframe, foreground="DarkBlue", background="gray95")
		self._probeZ.grid(row=row, column=col, padx=1, sticky=EW+S)

		# ---
		row,col = row+1,0
		Label(lframe, text="Pos:").grid(row=row, column=col, sticky=E)

		col += 1
		self.probeXdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeXdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeXdir, "Probe along X direction")
		self.widgets.append(self.probeXdir)

		col += 1
		self.probeYdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeYdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeYdir, "Probe along Y direction")
		self.widgets.append(self.probeYdir)

		col += 1
		self.probeZdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeZdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeZdir, "Probe along Z direction")
		self.widgets.append(self.probeZdir)

		# ---
		row += 1
		b = Button(lframe, text="Probe", command=self.probeOne)
		b.grid(row=row, column=col, sticky=E)
		tkExtra.Balloon.set(b, "Probe one point. Using the feed below")
		self.widgets.append(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# WorkSpace -> Autolevel
		lframe = LabelFrame(frame, text="Autolevel", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		# Empty
		col += 1
		Label(lframe, text="Min").grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text="Max").grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text="Step").grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text="N").grid(row=row, column=col, sticky=EW)

		# --- X ---
		row += 1
		col = 0
		Label(lframe, text="X:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeXmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeXmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmin, "X minimum")
		self.widgets.append(self.probeXmin)

		col += 1
		self.probeXmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeXmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmax, "X maximum")
		self.widgets.append(self.probeXmax)

		col += 1
		self.probeXstep = Label(lframe, foreground="DarkBlue", background="gray95", width=5)
		self.probeXstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXstep, "X step")

		col += 1
		self.probeXbins = Spinbox(lframe, from_=2, to_=1000, command=self.probeChange,
					background="White", width=3)
		self.probeXbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXbins, "X bins")
		self.widgets.append(self.probeXbins)

		# --- Y ---
		row += 1
		col  = 0
		Label(lframe, text="Y:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeYmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeYmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmin, "Y minimum")
		self.widgets.append(self.probeYmin)

		col += 1
		self.probeYmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeYmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmax, "Y maximum")
		self.widgets.append(self.probeYmax)

		col += 1
		self.probeYstep = Label(lframe,  foreground="DarkBlue", background="gray95", width=5)
		self.probeYstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYstep, "Y step")

		col += 1
		self.probeYbins = Spinbox(lframe, from_=2, to_=1000, command=self.probeChange,
					background="White", width=3)
		self.probeYbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYbins, "Y bins")
		self.widgets.append(self.probeYbins)

		# Max Z
		row += 1
		col  = 0

		Label(lframe, text="Z:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeZmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmin, "Z Minimum depth to scan")
		self.widgets.append(self.probeZmin)

		col += 1
		self.probeZmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmax, "Z safe to move")
		self.widgets.append(self.probeZmax)

		col += 1
		Label(lframe, text="Feed:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeFeed = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeFeed, "Probe feed rate")
		self.widgets.append(self.probeFeed)

		# Set variables
		self.probeXdir.set(Utils.config.get("Probe","x"))
		self.probeYdir.set(Utils.config.get("Probe","y"))
		self.probeZdir.set(Utils.config.get("Probe","z"))

		self.probeXmin.set(Utils.config.get("Probe","xmin"))
		self.probeXmax.set(Utils.config.get("Probe","xmax"))
		self.probeYmin.set(Utils.config.get("Probe","ymin"))
		self.probeYmax.set(Utils.config.get("Probe","ymax"))
		self.probeZmin.set(Utils.config.get("Probe","zmin"))
		self.probeZmax.set(Utils.config.get("Probe","zmax"))
		self.probeFeed.set(Utils.config.get("Probe","feed"))

		self.probeXbins.delete(0,END)
		self.probeXbins.insert(0,max(2,Utils.getInt("Probe","xn",5)))

		self.probeYbins.delete(0,END)
		self.probeYbins.insert(0,max(2,Utils.getInt("Probe","yn",5)))
		self.probeChange()

		# Buttons
		row += 1
		col  = 0
		f = Frame(lframe)
		f.grid(row=row, column=col, columnspan=5, sticky=EW)

		b = Button(f, text="Scan", foreground="DarkRed", command=self.probeScanArea)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Scan probed area for level information")
		self.widgets.append(b)

		b = Button(f, text="Draw", command=self.probeDraw)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Draw probe points on canvas")
		self.widgets.append(b)

		b = Button(f, text="Set Zero", command=self.probeSetZero)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Set current location as Z-zero for leveling")
		self.widgets.append(b)

		b = Button(f, text="Get Margins", command=self.probeGetMargins)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Get margins from gcode file")
		self.widgets.append(b)

		b = Button(f, text="Clear", command=self.probeClear)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Clear probe points")
		self.widgets.append(b)

		lframe.grid_columnconfigure(1,weight=2)
		lframe.grid_columnconfigure(2,weight=2)
		lframe.grid_columnconfigure(3,weight=1)

	#----------------------------------------------------------------------
	# GCode Editor
	#----------------------------------------------------------------------
	def _editorTab(self):
		frame = self.tabPage["Editor"]

		self.gcodelist = CNCList.CNCListbox(frame, self,
						selectmode=EXTENDED,
						exportselection=0,
						background="White")

		self.gcodelist.bind("<<ListboxSelect>>",	self.selectionChange)
		self.gcodelist.bind("<<Modified>>",		self.drawAfter)

		self.gcodelist.pack(side=LEFT,expand=TRUE, fill=BOTH)
		self.widgets.append(self.gcodelist)
		sb = Scrollbar(frame, orient=VERTICAL, command=self.gcodelist.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.gcodelist.config(yscrollcommand=sb.set)

		self.tabPage.changePage()

	#----------------------------------------------------------------------
	def createToolbar(self, toolbar):
		b = Button(toolbar, image=Utils.icons["load"], command=self.loadDialog)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Load g-code file")

		b = Button(toolbar, image=Utils.icons["save"], command=self.saveAll)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Save g-code to file")

		# ---
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=Utils.icons["undo"], command=self.undo)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Undo last edit")

		b = Button(toolbar, image=Utils.icons["redo"], command=self.redo)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Redo last undo command")

		# ---
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=Utils.icons["cut"], command=self.cut)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Cut to clipboard")

		b = Button(toolbar, image=Utils.icons["copy"], command=self.copy)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Copy to clipboard")

		b = Button(toolbar, image=Utils.icons["paste"], command=self.paste)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Paste from clipboard")

		# ---
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=Utils.icons["reset"], command=self.softReset)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Software reset of controller")

		b = Button(toolbar, image=Utils.icons["unlock"], command=self.unlock)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Unlock CNC")

		b = Button(toolbar, image=Utils.icons["home"], command=self.home)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Run homing cycle")

		# -----
		# Zoom
		# -----
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

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

		# -----
		# Tools
		# -----
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

		b = Radiobutton(toolbar, image=Utils.icons["select"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_SELECT,
					command=self.canvas.setActionSelect)
		tkExtra.Balloon.set(b, "Select tool [S]")
		self.widgets.append(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["pan"],	# FIXME replace with move
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_MOVE,
					command=self.canvas.setActionMove)
		tkExtra.Balloon.set(b, "Move objects [M]")
		self.widgets.append(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["gantry"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_GANTRY,
					command=self.canvas.setActionGantry)
		tkExtra.Balloon.set(b, "Move gantry [G]")
		self.widgets.append(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["origin"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_ORIGIN,
					command=self.canvas.setActionOrigin)
		tkExtra.Balloon.set(b, "Place origin [O]")
		self.widgets.append(b)
		b.pack(side=LEFT)

		b = Radiobutton(toolbar, image=Utils.icons["ruler"],
					indicatoron=FALSE,
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_RULER,
					command=self.canvas.setActionRuler)
		tkExtra.Balloon.set(b, "Ruler [R]")
		b.pack(side=LEFT)

		# ---
		Label(toolbar, image=Utils.icons["sep"]).pack(side=LEFT, padx=3)

		b = OptionMenu(toolbar, self.view, *CNCCanvas.VIEWS)
		b.config(padx=0, pady=1)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Change viewing angle")


	#----------------------------------------------------------------------
	def createMenu(self):
		# Menu bar
		menubar = Menu(self)
		self.config(menu=menubar)

		# File Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="File", underline=0, menu=menu)
		i = 1
		menu.add_command(label="New", underline=0,
					image=Utils.icons["new"],
					compound=LEFT,
					command=self.newFile)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Open", underline=0,
					image=Utils.icons["load"],
					compound=LEFT,
					accelerator="Ctrl-O",
					command=self.loadDialog)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Save", underline=0,
					image=Utils.icons["save"],
					compound=LEFT,
					accelerator="Ctrl-S",
					command=self.saveAll)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Save As", underline=0,
					image=Utils.icons["save"],
					compound=LEFT,
					command=self.saveDialog)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Reload", underline=0,
					image=Utils.icons["load"],
					compound=LEFT,
					command=self.reload)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Import", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.importFile)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		submenu = Menu(menu)
		menu.add_cascade(label="Probe", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					menu=submenu)

		ii = 1
		submenu.add_command(label="Open", underline=0,
					image=Utils.icons["load"],
					compound=LEFT,
					command=self.loadProbeDialog)
		self.widgets.append((submenu,ii))

		ii += 1
		submenu.add_command(label="Save", underline=0,
					image=Utils.icons["save"],
					compound=LEFT,
					command=self.saveProbe)
		self.widgets.append((submenu,ii))

		ii += 1
		submenu.add_command(label="Save As", underline=0,
					image=Utils.icons["save"],
					compound=LEFT,
					command=self.saveProbeDialog)
		self.widgets.append((submenu,ii))

		menu.add_separator()
		menu.add_command(label="Quit", underline=0,
					image=Utils.icons["quit"],
					compound=LEFT,
					accelerator="Ctrl-Q",
					command=self.quit)

		# Edit Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Edit", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Undo", underline=0,
					image=Utils.icons["undo"],
					compound=LEFT,
					accelerator="Ctrl-Z",
					command=self.undo)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Redo", underline=0,
					image=Utils.icons["redo"],
					compound=LEFT,
					accelerator="Ctrl-Y",
					command=self.redo)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Cut", underline=2,
					image=Utils.icons["cut"],
					compound=LEFT,
					accelerator="Ctrl-X",
					command=self.cut)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Copy", underline=0,
					image=Utils.icons["copy"],
					compound=LEFT,
					accelerator="Ctrl-C",
					command=self.copy)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Paste", underline=0,
					image=Utils.icons["paste"],
					compound=LEFT,
					accelerator="Ctrl-V",
					command=self.paste)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Insert Block", underline=0,
					image=Utils.icons["add"],
					compound=LEFT,
					accelerator="Ctrl-B",
					command=self.insertBlock)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Insert Line", underline=0,
					image=Utils.icons["add"],
					compound=LEFT,
					accelerator="Ctrl-Enter",
					command=self.insertLine)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Find", underline=0,
					image=Utils.icons["find"],
					compound=LEFT,
					accelerator="Ctrl-F",
					state=DISABLED,
					command=self.find)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Find Next", underline=0,
					image=Utils.icons["find"],
					compound=LEFT,
					accelerator="Ctrl-G",
					state=DISABLED,
					command=self.findNext)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Replace", underline=0,
					image=Utils.icons["replace"],
					compound=LEFT,
					accelerator="Ctrl-H",
					state=DISABLED,
					command=self.replace)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Select All", underline=8,
					image=Utils.icons["all"],
					compound=LEFT,
					accelerator="Ctrl-A",
					command=self.selectAll)
		self.widgets.append((menu,i))

		# Tools Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Tools", underline=0, menu=menu)

		# ---
		i = 1
		menu.add_radiobutton(label="Select", underline=0,
					accelerator="S",
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_SELECT,
					command=self.canvas.setActionSelect)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		# ---
		i += 1
		menu.add_radiobutton(label="Move objects", underline=0,
					accelerator="M",
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_MOVE,
					command=self.canvas.setActionMove)
		self.widgets.append((submenu,ii))

		i += 1
		menu.add_radiobutton(label="Move gantry", underline=5,
					accelerator="G",
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_GANTRY,
					command=self.canvas.setActionGantry)
		self.widgets.append((menu,i))

		i += 1
		menu.add_radiobutton(label="Origin", underline=0,
					accelerator="O",
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_ORIGIN,
					command=self.canvas.setActionOrigin)
		self.widgets.append((menu,i))

		i += 1
		menu.add_radiobutton(label="Ruler", underline=0,
					accelerator="R",
					variable=self.canvas.actionVar,
					value=CNCCanvas.ACTION_RULER,
					command=self.canvas.setActionRuler)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Toggle Expand", underline=7,
					accelerator="Ctrl-E",
					command=self.gcodelist.toggleExpand)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Toggle Enable", underline=7,
					accelerator="Ctrl-L",
					command=self.gcodelist.toggleEnable)
		self.widgets.append((menu,i))


		i += 1
		menu.add_separator()

		# ---
		i += 1
		menu.add_command(label="Inkscape", underline=0,
					command=lambda s=self:s.insertCommand("INKSCAPE all",True))
		self.widgets.append((menu,i))
		i += 1

		# --- Mirror ---
		submenu = Menu(menu)
		menu.add_cascade(label="Mirror", underline=0, menu=submenu)
		i += 1

		ii = 0
		submenu.add_command(label="Horizontal (X=-X)", underline=0,
					command=lambda s=self:s.insertCommand("MIRROR HOR", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Vertical (Y=-Y)", underline=0,
					command=lambda s=self:s.insertCommand("MIRROR VER", True))
		self.widgets.append((submenu,ii))

		# --- Move ---
		submenu = Menu(menu)
		menu.add_cascade(label="Move", underline=0, menu=submenu)
		i += 1

		ii = 0
		submenu.add_command(label="Move center", underline=6,
					command=lambda s=self:s.insertCommand("MOVE CENTER", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Move Bottom Left", underline=6,
					command=lambda s=self:s.insertCommand("MOVE BL", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Move Bottom Right", underline=7,
					command=lambda s=self:s.insertCommand("MOVE BR", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Move Top Right", underline=6,
					command=lambda s=self:s.insertCommand("MOVE TL", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Move Top Right", underline=8,
					command=lambda s=self:s.insertCommand("MOVE TR", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Move command", underline=0,
					command=lambda s=self:s.insertCommand("MOVE x y z", False))
		self.widgets.append((submenu,ii))

		# --- Order ---
		submenu = Menu(menu)
		menu.add_cascade(label="Order", underline=0, menu=submenu)
		i += 1

		ii = 0
		submenu.add_command(label="Order UP", underline=6, accelerator="Ctrl-Up",
					command=self.commandOrderUp)
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Order DOWN", underline=6, accelerator="Ctrl-Down",
					command=self.commandOrderDown)
		self.widgets.append((submenu,ii))

		# ---
		i += 1
		menu.add_command(label="Reverse", underline=1,
					command=lambda s=self:s.insertCommand("REVERSE", True))
		self.widgets.append((menu,i))

		# --- Rotate ---
		submenu = Menu(menu)
		menu.add_cascade(label="Rotate", underline=0, menu=submenu)
		i += 1

		ii = 0
		submenu.add_command(label="Rotate command", underline=0,
					command=lambda s=self:s.insertCommand("ROTATE ang x0 y0", False))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Rotate CCW (90)", underline=7,
					command=lambda s=self:s.insertCommand("ROTATE CCW", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Rotate CW (-90)", underline=8,
					command=lambda s=self:s.insertCommand("ROTATE CW", True))
		self.widgets.append((submenu,ii))
		ii += 1
		submenu.add_command(label="Rotate FLIP (180)", underline=7,
					command=lambda s=self:s.insertCommand("ROTATE FLIP", True))
		self.widgets.append((submenu,ii))

		# ---
		i += 1
		menu.add_command(label="Round", underline=0,
					command=lambda s=self:s.insertCommand("ROUND all", True))
		self.widgets.append((menu,i))

		# Machine Menu
#		menu = Menu(menubar)
#		menubar.add_cascade(label="Machine", underline=0, menu=menu)
#		i = 1
#		menu.add_command(label="Material", underline=0,
#					image=Utils.icons["material"],
#					compound=LEFT,
#					command=self.material)

		# Control Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Control", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Hard Reset", underline=0,
					image=Utils.icons["reset"],
					compound=LEFT,
					command=self.hardReset)
		i += 1
		menu.add_command(label="Soft Reset", underline=0,
					image=Utils.icons["reset"],
					compound=LEFT,
					command=self.softReset)
		self.widgets.append((menu,i))
		i += 1
		menu.add_separator()
		i += 1
		menu.add_command(label="Home",       underline=0,
					image=Utils.icons["home"],
					compound=LEFT,
					command=self.home)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Unlock",     underline=2,
					image=Utils.icons["unlock"],
					compound=LEFT,
					command=self.unlock)
		self.widgets.append((menu,i))
		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Settings",   underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.viewSettings)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Parameters", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.viewParameters)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="State",      underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.viewState)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Build",      underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.viewBuild)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Startup",    underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.viewStartup)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Check gcode",underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.checkGcode)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()
		i += 1
		menu.add_command(label="Clear",underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.clearTerminal)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Grbl Help",underline=0,
					image=Utils.icons["info"],
					compound=LEFT,
					command=self.grblhelp)
		self.widgets.append((menu,i))

		# Run Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Run", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Run",       underline=0,
					image=Utils.icons["start"],
					compound=LEFT,
					command=self.run)
		self.widgets.append((menu,i))

		menu.add_command(label="Pause", underline=0,
					image=Utils.icons["pause"],
					compound=LEFT,
					accelerator="!/~",
					command=self.pause)
		menu.add_command(label="Cancel",    underline=0,
					image=Utils.icons["stop"],
					compound=LEFT,
					command=self.stopRun)
		# View Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="View", underline=0, menu=menu)

		menu.add_command(label="Redraw", underline=2,
					image=Utils.icons["empty"],
					compound=LEFT,
					accelerator="Ctrl-R",
					command=self.drawAfter)

		menu.add_command(label="Zoom In", underline=2,
					image=Utils.icons["zoom_in"],
					compound=LEFT,
					accelerator="Ctrl-=",
					command=self.canvas.menuZoomIn)

		menu.add_command(label="Zoom Out", underline=2,
					image=Utils.icons["zoom_out"],
					compound=LEFT,
					accelerator="Ctrl--",
					command=self.canvas.menuZoomOut)

		menu.add_command(label="Fit to screen", underline=0,
					image=Utils.icons["zoom_on"],
					compound=LEFT,
					accelerator="F",
					command=self.canvas.fit2Screen)

		# -----------------
		menu.add_separator()
		menu.add_command(label="Expand", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					accelerator="Ctrl-E",
					command=self.gcodelist.toggleExpand)
		menu.add_command(label="Visibility", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					accelerator="Ctrl-L",
					command=self.gcodelist.toggleEnable)

		# -----------------
		menu.add_separator()

		menu.add_checkbutton(label="Axes", underline=0,
					variable=self.draw_axes,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="Grid", underline=0,
					variable=self.draw_grid,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="Margin", underline=0,
					variable=self.draw_margin,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="Paths (G1,G2,G3)", underline=0,
					variable=self.draw_paths,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="Probe", underline=0,
					variable=self.draw_probe,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="Rapid Motion (G0)", underline=0,
					variable=self.draw_rapid,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="WorkArea", underline=0,
					variable=self.draw_workarea,
					command=self.toggleDrawFlag)

		# -----------------
		menu.add_separator()

		submenu = Menu(menu)
		menu.add_cascade(label="Projection", underline=0, menu=submenu)

		submenu.add_radiobutton(label="X-Y", underline=0,
					accelerator="F3",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_XY],
					variable=self.view)

		submenu.add_radiobutton(label="X-Z", underline=2,
					accelerator="F4",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_XZ],
					variable=self.view)

		submenu.add_radiobutton(label="Y-Z", underline=0,
					accelerator="F5",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_YZ],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 1", underline=4,
					accelerator="F6",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO1],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 2", underline=4,
					accelerator="F7",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO2],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 3", underline=4,
					accelerator="F8",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO3],
					variable=self.view)

		# About menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Pendant", underline=0, menu=menu)

		menu.add_command(label="Start", underline=0,
					image=Utils.icons["start"],
					compound=LEFT,
					command=self.startPendant)

		menu.add_command(label="Stop", underline=0,
					image=Utils.icons["stop"],
					compound=LEFT,
					command=self.stopPendant)

		# About menu
		menu = Menu(menubar)
		menubar.add_cascade(label="About", underline=0, menu=menu)

		menu.add_command(label="Report", underline=0,
					image=Utils.icons["empty"],
					compound=LEFT,
					command=self.reportDialog)

		menu.add_command(label="About", underline=0,
					image=Utils.icons["about"],
					compound=LEFT,
					command=self.about)

	#----------------------------------------------------------------------
	def quit(self, event=None):
		global config

		if self.running and self._quit<1:
			tkMessageBox.showinfo("Running",
				"CNC is currently running, please stop it before.",
				parent=self)
			self._quit += 1
			return
		del self.widgets[:]

		if self.gcode.isModified():
			# file is modified
			ans = tkMessageBox.askquestion("File modified",
				"Gcode was modified do you want to save it first?",
				parent=self)
			if ans==tkMessageBox.YES or ans==True:
				self.saveDialog()

		self.saveConfig()

		CNCPendant.stop()
		self.destroy()
		if Utils.errors and Utils._errorReport:
			Utils.ReportDialog.sendErrorReport()
		tk.destroy()

	# ---------------------------------------------------------------------
	def configWidgets(self, var, value):
		for w in self.widgets:
			if isinstance(w,tuple):
				try:
					w[0].entryconfig(w[1], state=value)
				except TclError:
					pass
			elif isinstance(w,tkExtra.Combobox):
				w.configure(state=value)
			else:
				w[var] = value

	# ---------------------------------------------------------------------
	def busy(self):
		try:
			self.config(cursor="watch")
			self.update_idletasks()
		except TclError:
			pass

	# ----------------------------------------------------------------------
	def notBusy(self):
		try:
			self.config(cursor="")
		except TclError:
			pass

	# ---------------------------------------------------------------------
	def enable(self):
		self.configWidgets("state",NORMAL)

	def disable(self):
		self.configWidgets("state",DISABLED)

	#----------------------------------------------------------------------
	def loadConfig(self):
		geom = "%sx%s" % (Utils.getInt(Utils.__prg__, "width", 900),
				  Utils.getInt(Utils.__prg__, "height", 650))
		try: self.geometry(geom)
		except: pass

		self.drofont = Utils.getFont("DRO",('Helvetica',12))

		#restore windowsState
		try:
			self.wm_state(Utils.getStr(Utils.__prg__, "windowstate", "normal"))
		except:
			pass

		CNCPendant.port = Utils.getInt("Connection","pendantport",CNCPendant.port)

		# Create tools
		self.tools.load(Utils.config)
		self.loadHistory()

	#----------------------------------------------------------------------
	def saveConfig(self):
		# Program
		Utils.config.set(Utils.__prg__,  "width",    str(self.winfo_width()))
		Utils.config.set(Utils.__prg__,  "height",   str(self.winfo_height()))
		#Utils.config.set(Utils.__prg__,  "x",        str(self.winfo_rootx()))
		#Utils.config.set(Utils.__prg__,  "y",        str(self.winfo_rooty()))

		#save windowState
		Utils.config.set(Utils.__prg__,  "windowstate", str(self.wm_state()))

		Utils.config.set(Utils.__prg__,  "tool",     self.toolFrame.get())

		# Connection
		Utils.config.set("Connection", "port", self.portCombo.get())

		# Canvas
		Utils.config.set("Canvas","axes",    str(int(self.draw_axes.get())))
		Utils.config.set("Canvas","grid",    str(int(self.draw_grid.get())))
		Utils.config.set("Canvas","margin",  str(int(self.draw_margin.get())))
		Utils.config.set("Canvas","probe",   str(int(self.draw_probe.get())))
		Utils.config.set("Canvas","paths",   str(int(self.draw_paths.get())))
		Utils.config.set("Canvas","rapid",   str(int(self.draw_rapid.get())))
		Utils.config.set("Canvas","workarea",str(int(self.draw_workarea.get())))

		# Control
		Utils.config.set("Control", "step", self.step.get())

		# Probe
		Utils.config.set("Probe", "x",    self.probeXdir.get())
		Utils.config.set("Probe", "y",    self.probeYdir.get())
		Utils.config.set("Probe", "z",    self.probeZdir.get())

		Utils.config.set("Probe", "xmin", self.probeXmin.get())
		Utils.config.set("Probe", "xmax", self.probeXmax.get())
		Utils.config.set("Probe", "xn",   self.probeXbins.get())
		Utils.config.set("Probe", "ymin", self.probeYmin.get())
		Utils.config.set("Probe", "ymax", self.probeYmax.get())
		Utils.config.set("Probe", "yn",   self.probeYbins.get())
		Utils.config.set("Probe", "zmin", self.probeZmin.get())
		Utils.config.set("Probe", "zmax", self.probeZmax.get())
		Utils.config.set("Probe", "feed", self.probeFeed.get())

		# Tools
		self.tools.save(Utils.config)

		self.saveHistory()

	#----------------------------------------------------------------------
	def loadHistory(self):
		try:
			f = open(Utils.hisFile,"r")
		except:
			return
		self.history = [x.strip() for x in f]
		f.close()

	#----------------------------------------------------------------------
	def saveHistory(self):
		try:
			f = open(Utils.hisFile,"w")
		except:
			return
		f.write("\n".join(self.history))
		f.close()

	#----------------------------------------------------------------------
	def cut(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.cut()
			pass
		elif focus:
			focus.event_generate("<<Cut>>")

	#----------------------------------------------------------------------
	def copy(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.copy()
			pass
		elif focus:
			focus.event_generate("<<Copy>>")

	#----------------------------------------------------------------------
	def paste(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.paste()
			pass
		elif focus:
			focus.event_generate("<<Paste>>")

	#----------------------------------------------------------------------
	def undo(self, event=None):
		if self.gcode.canUndo():
			self.gcode.undo();
			self.gcodelist.fill()
			self.drawAfter()
		return "break"

	#----------------------------------------------------------------------
	def redo(self, event=None):
		if self.gcode.canRedo():
			self.gcode.redo();
			self.gcodelist.fill()
			self.drawAfter()
		return "break"

	#----------------------------------------------------------------------
	def about(self, event=None):
		tkMessageBox.showinfo("About",
				"%s\nby %s [%s]\nVersion: %s\nLast Change: %s" % \
				(Utils.__prg__, __author__, __email__, __version__, __date__),
				parent=self)

	#----------------------------------------------------------------------
	def reportDialog(self, event=None):
		Utils.ReportDialog(self)

	#----------------------------------------------------------------------
	def insertBlock(self):
		self.tabPage.changePage("Editor")
		self.gcodelist.insertBlock()

	#----------------------------------------------------------------------
	def insertLine(self):
		self.tabPage.changePage("Editor")
		self.gcodelist.insertLine()

	#----------------------------------------------------------------------
	def toggleDrawFlag(self):
		self.canvas.draw_axes     = self.draw_axes.get()
		self.canvas.draw_grid     = self.draw_grid.get()
		self.canvas.draw_margin   = self.draw_margin.get()
		self.canvas.draw_probe    = self.draw_probe.get()
		self.canvas.draw_paths    = self.draw_paths.get()
		self.canvas.draw_rapid    = self.draw_rapid.get()
		self.canvas.draw_workarea = self.draw_workarea.get()
		self.viewChange()

	#----------------------------------------------------------------------
	def viewChange(self, a=None, b=None, c=None):
		self.draw()
		if self.running:
			self._selectI = 0	# last selection pointer in items
		else:
			self.selectionChange()

	# ----------------------------------------------------------------------
	def viewXY(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XY])

	# ----------------------------------------------------------------------
	def viewXZ(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XZ])

	# ----------------------------------------------------------------------
	def viewYZ(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_YZ])

	# ----------------------------------------------------------------------
	def viewISO1(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO1])

	# ----------------------------------------------------------------------
	def viewISO2(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO2])

	# ----------------------------------------------------------------------
	def viewISO3(self, event=None):
		self.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO3])

	# ----------------------------------------------------------------------
	def draw(self):
		view = CNCCanvas.VIEWS.index(self.view.get())
		self.canvas.draw(view)
		self.selectionChange()

	# ----------------------------------------------------------------------
	# Redraw with a small delay
	# ----------------------------------------------------------------------
	def drawAfter(self, event=None):
		if self._drawAfter is not None: self.after_cancel(self._drawAfter)
		self._drawAfter = self.after(DRAW_AFTER, self.draw)

	# ----------------------------------------------------------------------
	def changePage(self, event=None):
		page = self.tabPage.getActivePage()
		if page == "WCS":
			self.sendGrbl("$#\n$G\n")
			return
		#elif page == "Probe":
		#	self.probeChange(False)

		focus = self.focus_get()
		if focus and focus is self.gcodelist and page != "Editor":
			# if the focus was on the editor, but the Editor page is not active
			# set the focus to the canvas
			self.canvas.focus_set()

	#----------------------------------------------------------------------
	def commandFocus(self, event=None):
		self.command.focus_set()

	#----------------------------------------------------------------------
	def commandFocusIn(self, event=None):
		self.cmdlabel["foreground"] = "Blue"

	#----------------------------------------------------------------------
	def commandFocusOut(self, event=None):
		self.cmdlabel["foreground"] = "Black"

	#----------------------------------------------------------------------
	def canvasFocus(self, event=None):
		self.canvas.focus_set()
		return "break"

	#----------------------------------------------------------------------
	def selectAll(self, event=None):
		#self.tabPage.changePage("Editor")
		self.gcodelist.selectAll()
		self.selectionChange()
		return "break"

	#----------------------------------------------------------------------
	def unselectAll(self, event=None):
		#self.tabPage.changePage("Editor")
		self.gcodelist.selectClear()
		self.selectionChange()
		return "break"

	#----------------------------------------------------------------------
	def find(self, event=None):
		self.tabPage.changePage("Editor")
###		self.editor.findDialog()
		return "break"

	#----------------------------------------------------------------------
	def findNext(self, event=None):
		self.tabPage.changePage("Editor")
###		self.editor.findNext()
		return "break"

	#----------------------------------------------------------------------
	def replace(self, event=None):
		self.tabPage.changePage("Editor")
###		self.editor.replaceDialog()
		return "break"

	#----------------------------------------------------------------------
	# Keyboard binding to <Return>
	#----------------------------------------------------------------------
	def cmdExecute(self, event):
		self.commandExecute()

	# ----------------------------------------------------------------------
	def insertCommand(self, cmd, execute=False):
		self.command.delete(0,END)
		self.command.insert(0,cmd)
		if execute: self.commandExecute(False)

	#----------------------------------------------------------------------
	# Execute command from command line
	#----------------------------------------------------------------------
	def commandExecute(self, addHistory=True):
		line = self.command.get().strip()
		if not line: return

		if self._historyPos is not None:
			if self.history[self._historyPos] != line:
				self.history.append(line)
		elif not self.history or self.history[-1] != line:
			self.history.append(line)

		self._historyPos = None
		if len(self.history)>MAX_HISTORY:
			self.history.pop(0)
		self.command.delete(0,END)
		self.execute(line)

	#----------------------------------------------------------------------
	# Execute a single command
	#----------------------------------------------------------------------
	def execute(self, line):
		if line[0] in ("$","!","~","?","(","@") or GPAT.match(line):
			self.sendGrbl(line+"\n")
			return

###		elif line[0] == "/":
###			self.editor.find(line[1:])
###			return
###		elif line[0] == ":":
###			self.editor.setInsert("%s.0"%(line[1:]))
###			return

		line = line.replace(","," ").split()
		cmd = line[0].upper()

		# ABO*UT: About dialog
		if rexx.abbrev("ABOUT",cmd,3):
			self.about()

		# ABS*OLUTE: Set absolute coordinates
		elif rexx.abbrev("ABSOLUTE",cmd,3):
			self.sendGrbl("G90\n")

		# CLE*AR: clear terminal
		elif rexx.abbrev("CLEAR",cmd,3) or cmd=="CLS":
			self.clearTerminal()

		# BOX [dx] [dy] [dz] [nx] [ny] [nz] [tool]: create a finger box
		elif cmd == "BOX":
			tool = self.tools["Box"]
			try:    tool["dx"] = float(line[1])
			except: pass
			try:    tool["dy"] = float(line[2])
			except: pass
			try:    tool["dz"] = float(line[3])
			except: pass

			try:    tool["nx"] = float(line[4])
			except: pass
			try:    tool["ny"] = float(line[5])
			except: pass
			try:    tool["nz"] = float(line[6])
			except: pass

			try:
				tool["profile"] = int(rexx.abbrev("PROFILE",line[7].upper()))
			except: pass
			try:
				tool["cut"] = int(rexx.abbrev("CUT",line[7].upper()))
			except: pass
			tool.execute(self)

		# CONT*ROL: switch to control tab
		elif rexx.abbrev("CONTROL",cmd,4):
			self.tabPage.changePage("Control")

		# CUT [height] [pass-per-depth]: replicate selected blocks to cut-height
		# default values are taken from the active material
		elif cmd == "CUT":
			try:    h = float(line[1])
			except: h = None

			try:    d = float(line[2])
			except: d = None
			self.executeOnSelection("CUT",h, d)

		# DOWN: move downward in cutting order the selected blocks
		# UP: move upwards in cutting order the selected blocks
		elif cmd=="DOWN":
			self.gcodelist.orderDown()
		elif cmd=="UP":
			self.gcodelist.orderUp()

		# DRI*LL [depth] [peck]: perform drilling at all penetrations points
		elif rexx.abbrev("DRILL",cmd,3):
			try:    h = float(line[1])
			except: h = None

			try:    p = float(line[2])
			except: p = None
			self.executeOnSelection("DRILL",h, p)

		# FIL*TER: filter editor blocks with text
		elif rexx.abbrev("FILTER",cmd,3) or cmd=="ALL":
			try:
				self.gcodelist.filter = line[1]
			except:
				self.gcodelist.filter = None
			self.gcodelist.fill()

		# ED*ITOR: switch to editor tab
		elif rexx.abbrev("EDITOR",cmd,2):
			self.tabPage.changePage("Editor")

		# HOME: perform a homing cycle
		elif cmd == "HOME":
			self.home()

		# HOLE: create a hole
		elif cmd == "HOLE":
			try: radius = float(line[1])
			except: return
			if radius<0:
				radius = self.tool/2 - radius
			else:
				radius += self.tool/2

			self.gcode.box(self.gcodelist.activeBlock(), radius)
			self.gcodelist.fill()
			self.draw()
			self.statusbar["text"] = "BOX with fingers generated"


		# IM*PORT <filename>: import filename with gcode or dxf at cursor location
		# or at the end of the file
		elif rexx.abbrev("IMPORT",cmd,2):
			try:
				self.importFile(line[1])
			except:
				pass

		# INK*SCAPE: remove uneccessary Z motion as a result of inkscape gcodetools
		elif rexx.abbrev("INKSCAPE",cmd,3):
			if len(line)>1 and rexx.abbrev("ALL",line[1].upper()):
				self.gcodelist.selectAll()
			self.executeOnSelection("INKSCAPE")

		# ISO1: switch to ISO1 projection
		elif cmd=="ISO1":
			self.viewISO1()
		# ISO2: switch to ISO2 projection
		elif cmd=="ISO2":
			self.viewISO2()
		# ISO3: switch to ISO3 projection
		elif cmd=="ISO3":
			self.viewISO3()

		# LO*AD [filename]: load filename containing g-code
		elif rexx.abbrev("LOAD",cmd,2):
			if len(line)>1:
				self.load(line[1])
			else:
				self.loadDialog()

		# MAT*ERIAL [name/height] [pass-per-depth] [feed]: set material from database or parameters
#		elif rexx.abbrev("MATERIAL",cmd,3):
#			tool = self.tools["Material"]
#			# MAT*ERIAL [height] [pass-depth] [feed]
#			try: self.height = float(line[1])
#			except: pass
#			try: self.depth_pass = float(line[2])
#			except: pass
#			try: self.feed = float(line[3])
#			except: pass
#			self.statusbar["text"] = "Height: %g  Depth-per-pass: %g  Feed: %g"%(self.height,self.depth_pass, self.feed)

		# MIR*ROR [H*ORIZONTAL/V*ERTICAL]: mirror selected objects horizontally or vertically
		elif rexx.abbrev("MIRROR",cmd,3):
			if len(line)==1: return
			line1 = line[1].upper()
			#if nothing is selected:
			self.gcodelist.selectAll()
			if rexx.abbrev("HORIZONTAL",line1):
				self.executeOnSelection("MIRRORH")
			elif rexx.abbrev("VERTICAL",line1):
				self.executeOnSelection("MIRRORV")

		elif rexx.abbrev("ORDER",cmd,2):
			if line[1].upper() == "UP":
				self.gcodelist.orderUp()
			elif line[1].upper() == "DOWN":
				self.gcodelist.orderDown()

		# MO*VE [|CE*NTER|BL|BR|TL|TR|UP|DOWN|x] [[y [z]]]:
		# move selected objects either by mouse or by coordinates
		elif rexx.abbrev("MOVE",cmd,2):
			if len(line)==1:
				self.canvas.setActionMove()
				return
			line1 = line[1].upper()
			if rexx.abbrev("CENTER",line1,2):
				dx = -(self.cnc.xmin + self.cnc.xmax)/2.0
				dy = -(self.cnc.ymin + self.cnc.ymax)/2.0
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="BL":
				dx = -self.cnc.xmin
				dy = -self.cnc.ymin
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="BR":
				dx = -self.cnc.xmax
				dy = -self.cnc.ymin
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="TL":
				dx = -self.cnc.xmin
				dy = -self.cnc.ymax
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="TR":
				dx = -self.cnc.xmax
				dy = -self.cnc.ymax
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1 in ("UP","DOWN"):
				dx = line1
				dy = dz = line1
			else:
				try:    dx = float(line[1])
				except: dx = 0.0
				try:    dy = float(line[2])
				except: dy = 0.0
				try:    dz = float(line[3])
				except: dz = 0.0
			self.executeOnSelection("MOVE",dx,dy,dz)

		# ORI*GIN x y z: move origin to x,y,z by moving all to -x -y -z
		elif rexx.abbrev("ORIGIN",cmd,3):
			try:    dx = -float(line[1])
			except: dx = 0.0
			try:    dy = -float(line[2])
			except: dy = 0.0
			try:    dz = -float(line[3])
			except: dz = 0.0
			self.gcodelist.selectAll()
			self.executeOnSelection("MOVE",dx,dy,dz)

		# OPEN: open serial connection to grbl
		# CLOSE: close serial connection to grbl
		elif cmd in ("OPEN","CLOSE"):
			self.openClose()

		# QU*IT: quit program
		# EX*IT: exit program
		elif rexx.abbrev("QUIT",cmd,2) or rexx.abbrev("EXIT",cmd,2):
			self.quit()

		# PAUSE: pause cycle
		elif cmd == "PAUSE":
			self.pause()

		# PROF*ILE [offset]: create profile path
		elif rexx.abbrev("PROFILE",cmd,3):
			if len(line)>1:
				self.profile(line[1])
			else:
				self.profile()

		# REL*ATIVE: switch to relative coordinates
		elif rexx.abbrev("RELATIVE",cmd,3):
			self.sendGrbl("G91\n")

		# RESET: perform a soft reset to grbl
		elif cmd == "RESET":
			self.softReset()

		# REV*ERSE: reverse path direction
		elif rexx.abbrev("REVERSE", cmd, 3):
			self.executeOnSelection("REVERSE")

		# RUN: run g-code
		elif cmd == "RUN":
			self.run()

		# ROT*ATE [CCW|CW|FLIP|ang] [x0 [y0]]: rotate selected blocks
		# counter-clockwise(90) / clockwise(-90) / flip(180)
		# 90deg or by a specific angle and a pivot point
		elif rexx.abbrev("ROTATE",cmd,3):
			line1 = line[1].upper()
			x0 = y0 = 0.0
			if line1 == "CCW":
				ang = 90.0
				#self.gcodelist.selectAll()
			elif line1 == "CW":
				ang = -90.0
				#self.gcodelist.selectAll()
			elif line1=="FLIP":
				ang = 180.0
				#self.gcodelist.selectAll()
			else:
				try: ang = float(line[1])
				except: pass
				try: x0 = float(line[2])
				except: pass
				try: y0 = float(line[3])
				except: pass
			self.executeOnSelection("ROTATE",ang,x0,y0)

		# ROU*ND [n]: round all digits to n fractional digits
		elif rexx.abbrev("ROUND",cmd,3):
			acc = None
			if len(line)>1:
				if rexx.abbrev("ALL",line[1].upper()):
					self.gcodelist.selectAll()
				else:
					try:
						acc = int(line[1])
					except:
						pass
			self.executeOnSelection("ROUND",acc)

		# RU*LER: measure distances with mouse ruler
		elif rexx.abbrev("RULER",cmd,2):
			self.canvas.setActionRuler()

		# SAFE [z]: safe z to move
		elif cmd=="SAFE":
			try: self.cnc.safe = float(line[1])
			except: pass
			self.statusbar["text"] = "Safe Z= %g"%(self.cnc.safe)

		# SA*VE [filename]: save to filename or to default name
		elif rexx.abbrev("SAVE",cmd,2):
			if len(line)>1:
				self.save(line[1])
			else:
				self.saveAll()

		# SET [x [y [z]]]: set x,y,z coordinates to current workspace
		elif cmd == "SET":
			try: x = float(line[1])
			except: x = ""
			try: y = float(line[2])
			except: y = ""
			try: z = float(line[3])
			except: z = ""
			self._wcsSet(x,y,z)

		elif cmd == "SET0":
			self.wcsSet0()

		elif cmd == "SETX":
			try: x = float(line[1])
			except: x = ""
			self._wcsSet(x,"","")

		elif cmd == "SETY":
			try: y = float(line[1])
			except: y = ""
			self._wcsSet("",y,"")

		elif cmd == "SETZ":
			try: z = float(line[1])
			except: z = ""
			self._wcsSet("","",z)

		# STEP [s]: set motion step size to s
		elif cmd == "STEP":
			try:
				self.setStep(float(line[1]))
			except:
				pass

		# SPI*NDLE [ON|OFF|speed]: turn on/off spindle
		elif rexx.abbrev("SPINDLE",cmd,3):
			if len(line)>1:
				if line[1].upper()=="OFF":
					self.spindle.set(False)
				elif line[1].upper()=="ON":
					self.spindle.set(True)
				else:
					try:
						rpm = int(line[1])
						if rpm==0:
							self.spindleSpeed.set(0)
							self.spindle.set(False)
						else:
							self.spindleSpeed.set(rpm)
							self.spindle.set(True)
					except:
						pass
			else:
				# toggle spindle
				self.spindle.set(not self.spindle.get())
			self.spindleControl()

		# STOP: stop current run
		elif cmd == "STOP":
			self.stopRun()

		# TERM*INAL: switch to terminal tab
		elif rexx.abbrev("TERMINAL",cmd,4):
			self.tabPage.changePage("Terminal")

		# TOOL [diameter]: set diameter of cutting tool
		elif cmd in ("BIT","TOOL","MILL"):
			try:
				diam = float(line[1])
			except:
				tool = self.tools["EndMill"]
				diam = self.tools.fromMm(tool["diameter"])
			self.statusbar["text"] = "EndMill: %s %g"%(tool["name"], diam)

		# TOOLS
		elif cmd=="TOOLS":
			self.tabPage.changePage("Tools")

		# UNL*OCK: unlock grbl
		elif rexx.abbrev("UNLOCK",cmd,3):
			self.unlock()

		# US*ER cmd: execute user command, cmd=number or name
		elif rexx.abbrev("USER",cmd,2):
			n = Utils.getInt("Buttons","n",6)
			try:
				idx = int(line[1])
			except:
				try:
					name = line[1].upper()
					for i in range(n):
						if name == Utils.getStr("Buttons","name.%d"%(i),"").upper():
							idx = i
							break
				except:
					return
			if idx<0 or idx>=n:
				self.statusbar["text"] = "Invalid user command %s"%(line[1])
				return
			cmd = Utils.getStr("Buttons","command.%d"%(idx),"")
			for line in cmd.splitlines():
				self.execute(line)

		# WCS [n]: switch to workspace index n
		elif rexx.abbrev("WORKSPACE",cmd,4) or cmd=="WCS":
			self.tabPage.changePage("WCS")
			try:
				self.wcsvar.set(WCS.index(line[1].upper()))
			except:
				pass

		# XY: switch to XY view
		# YX: switch to XY view
		elif cmd in ("XY","YX"):
			self.viewXY()

		# XZ: switch to XZ view
		# ZX: switch to XZ view
		elif cmd in ("XZ","ZX"):
			self.viewXZ()

		# YZ: switch to YZ view
		# ZY: switch to YZ view
		elif cmd in ("YZ","ZY"):
			self.viewYZ()

		else:
			tkMessageBox.showerror("Unknown command",
					"Unknown command '%s'"%(string.join(line)),
					parent=self)
			return

	#----------------------------------------------------------------------
	# Execute a command over the selected lines
	#----------------------------------------------------------------------
	def executeOnSelection(self, cmd, *args):
		items = self.gcodelist.getCleanSelection()
		if not items: return

		self.busy()
		sel = None
		if cmd == "CUT":
			sel = self.gcode.cut(items, *args)
		elif cmd == "DRILL":
			sel = self.gcode.drill(items, *args)
		elif cmd == "ORDER":
			self.gcode.orderLines(items, *args)
		elif cmd == "INKSCAPE":
			self.gcode.inkscapeLines()
		elif cmd == "MOVE":
			self.gcode.moveLines(items, *args)
		elif cmd == "REVERSE":
			self.gcode.reverse(items, *args)
		elif cmd == "ROUND":
			self.gcode.roundLines(items, *args)
		elif cmd == "ROTATE":
			self.gcode.rotateLines(items, *args)
		elif cmd == "MIRRORH":
			self.gcode.mirrorHLines(items)
		elif cmd == "MIRRORV":
			self.gcode.mirrorVLines(items)

		# Fill listbox and update selection
		self.gcodelist.fill()
		if sel is not None:
			if isinstance(sel, str):
				tkMessageBox.showerror("Operation error", sel, parent=self)
			else:
				self.gcodelist.select(sel,clear=True)
		self.drawAfter()
		self.notBusy()
		self.statusbar["text"] = "%s %s"%(cmd," ".join([str(a) for a in args if a is not None]))

	#----------------------------------------------------------------------
	def profile(self, direction=None):
		tool = self.tools["EndMill"]
		ofs  = self.tools.fromMm(tool["diameter"])/2.0
		sign = 1.0

		if direction is None:
			pass
		elif rexx.abbrev("INSIDE",direction.upper()):
			sign = -1.0
		elif rexx.abbrev("OUTSIDE",direction.upper()):
			sign = 1.0
		else:
			try:
				ofs = float(direction)/2.0
			except:
				pass

		self.busy()
		msg = self.gcode.profile(self.gcodelist.getSelectedBlocks(), ofs*sign)
		if msg:
			tkMessageBox.showwarning("Open paths",
					"WARNING: %s"%(msg),
					parent=self)
		self.gcodelist.fill()
		self.draw()
		self.notBusy()
		self.statusbar["text"] = "Profile block with ofs=%g"%(ofs*sign)

	#----------------------------------------------------------------------
	def commandOrderUp(self, event=None):
		self.insertCommand("UP",True)
		return "break"

	#----------------------------------------------------------------------
	def commandOrderDown(self, event=None):
		self.insertCommand("DOWN",True)
		return "break"

	#----------------------------------------------------------------------
	def commandHistoryUp(self, event=None):
		if self._historyPos is None:
			if self.history:
				self._historyPos = len(self.history)-1
			else:
				return
		else:
			self._historyPos = max(0, self._historyPos-1)
		self.command.delete(0,END)
		self.command.insert(0,self.history[self._historyPos])

	#----------------------------------------------------------------------
	def commandHistoryDown(self, event=None):
		if self._historyPos is None:
			return
		else:
			self._historyPos += 1
			if self._historyPos >= len(self.history):
				self._historyPos = None
		self.command.delete(0,END)
		if self._historyPos is not None:
			self.command.insert(0,self.history[self._historyPos])

	#----------------------------------------------------------------------
	def select(self, items, double, clear, toggle=True):
		self.gcodelist.select(items, double, clear, toggle)
		self.selectionChange()

	# ----------------------------------------------------------------------
	# Selection has changed highlight the canvas
	# ----------------------------------------------------------------------
	def selectionChange(self, event=None):
		items = self.gcodelist.getSelection()
		self.canvas.clearSelection()
		if not items: return
		self.canvas.select(items)
		self.canvas.activeMarker(self.gcodelist.getActive())

	#----------------------------------------------------------------------
	def newFile(self, event=None):
		self.gcode.init()
		self.gcode.headerFooter()
		self.gcodelist.fill()
		self.draw()
		self.title(Utils.__prg__)

	#----------------------------------------------------------------------
	# load dialog
	#----------------------------------------------------------------------
	def loadDialog(self, event=None):
		filename = bFileDialog.askopenfilename(master=self,
			title="Open file",
			initialfile=os.path.join(
					Utils.config.get("File", "dir"),
					Utils.config.get("File", "file")),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("DXF",    "*.dxf"),
				   ("Probe",  "*.probe"),
				   ("All","*")])
		if filename: self.load(filename)

	#----------------------------------------------------------------------
	def loadProbeDialog(self, event=None):
		try:
			pfilename = Utils.config.get("File", "probe")
		except:
			pfilename = "probe"
		filename = bFileDialog.askopenfilename(master=self,
			title="Open Probe file",
			initialfile=os.path.join(
					Utils.config.get("File", "dir"),
					pfilename),
			filetypes=[("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.loadProbe(filename)

	#----------------------------------------------------------------------
	# save dialog
	#----------------------------------------------------------------------
	def saveDialog(self, event=None):
		filename = bFileDialog.asksaveasfilename(master=self,
			title="Save file",
			initialfile=os.path.join(self.gcode.filename),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("DXF",    "*.dxf"),
				   ("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.save(filename)

	#----------------------------------------------------------------------
	def saveProbeDialog(self, event=None):
		try:
			pfilename = Utils.config.get("File", "probe")
		except:
			pfilename = "probe"
		filename = bFileDialog.asksaveasfilename(master=self,
			title="Save probe file",
			initialfile=os.path.join(
					Utils.config.get("File", "dir"),
					pfilename),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.saveProbe(filename)

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename):
		fn,ext = os.path.splitext(filename)
		if ext==".probe":
			self.loadProbe(filename)
		elif ext==".dxf":
			self.gcode.init()
			if self.gcode.importDXF(filename):
				self.gcodelist.fill()
				self.draw()
				self.statusbar["text"] = "DXF imported from "+filename
		else:
			self.loadGcode(filename)

	#----------------------------------------------------------------------
	def importFile(self, filename=None):
		if filename is None:
			filename = bFileDialog.askopenfilename(master=self,
				title="Import Gcode/DXF file",
				initialfile=os.path.join(
						Utils.config.get("File", "dir"),
						Utils.config.get("File", "file")),
				filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
					   ("DXF",    "*.dxf"),
					   ("All","*")])
		if filename:
			gcode = CNC.GCode()
			gcode.load(filename)
			sel = self.gcodelist.getSelectedBlocks()
			if not sel:
				pos = None
			else:
				pos = sel[-1]
			self.gcode.addUndo(self.gcode.insBlocksUndo(pos, gcode.blocks))
			del gcode
			self.gcodelist.fill()
			self.draw()
			self.canvas.fit2Screen()

	#----------------------------------------------------------------------
	def save(self, filename):
		global config
		fn,ext = os.path.splitext(filename)
		if ext == ".probe":
			self.gcode.probe.save(filename)
		elif ext == ".dxf":
			if self.gcode.saveDXF(filename):
				self.statusbar["text"] = "DXF exported to "+filename
		else:
			self.saveGcode(filename)

	#----------------------------------------------------------------------
	def reload(self, event=None):
		self.loadGcode(self.gcode.filename)

	#----------------------------------------------------------------------
	def loadGcode(self, filename=None):
		if filename:
			Utils.config.set("File", "dir",  os.path.dirname(os.path.abspath(filename)))
			Utils.config.set("File", "file", os.path.basename(filename))

		if self.gcode.isModified():
			ans = tkMessageBox.askquestion("File modified",
				"Gcode was modified do you want to save it first?",
				parent=self)
			if ans==tkMessageBox.YES or ans==True:
				self.save()

		self.gcodelist.selectClear()
		self.gcode.load(filename)
		self.gcodelist.fill()
		self.draw()
		self.canvas.fit2Screen()
		self.title("%s: %s"%(Utils.__prg__,self.gcode.filename))

	#----------------------------------------------------------------------
	def loadProbe(self, filename):
		Utils.config.set("File", "probe", os.path.basename(filename))
		self.gcode.probe.load(filename)
		self.probeSet()

	#----------------------------------------------------------------------
	def saveAll(self, event=None):
		if self.gcode.filename:
			self.saveGcode()
			self.saveProbe()
		else:
			self.saveDialog()

	#----------------------------------------------------------------------
	def saveGcode(self, filename=None):
		if filename is not None:
			Utils.config.set("File", "dir",  os.path.dirname(os.path.abspath(filename)))
			Utils.config.set("File", "file", os.path.basename(filename))
			self.gcode.filename = filename

		if not self.gcode.save():
			tkMessageBox.showerror("Error",
					"Error saving file '%s'"%(self.gcode.filename),
					parent=self)
			return
		self.title("%s: %s"%(Utils.__prg__,self.gcode.filename))

	#----------------------------------------------------------------------
	def saveProbe(self, filename=None):
		if filename is not None:
			Utils.config.set("File", "probe", os.path.basename(filename))
			self.gcode.probe.filename = filename

		# save probe
		if not self.gcode.probe.isEmpty():
			self.gcode.probe.save()

	#----------------------------------------------------------------------
	def focusIn(self, event):
		if self._inFocus: return
		# FocusIn is generated for all sub-windows, handle only the main window
		if self is not event.widget: return
		self._inFocus = True
		if self.gcode.checkFile():
			if self.gcode.isModified():
				ans = tkMessageBox.askquestion("Warning",
					"Gcode file %s was changed since editing started\n" \
					"Reload new version?"%(self.gcode.filename),
					parent=self)
				if ans==tkMessageBox.YES or ans==True:
					self.gcode.resetModified()
					self.loadGcode()
			else:
				self.loadGcode()
		self._inFocus = False

	#----------------------------------------------------------------------
	def openClose(self):
		if self.serial is not None:
			self.close()
			self.connectBtn.config(text="Open",
					background="LightGreen",
					activebackground="LightGreen")
		else:
			device  = self.portCombo.get()
			baudrate = int(Utils.config.get("Connection","baud"))
			if self.open(device, baudrate):
				self.connectBtn.config(text="Close",
						background="Salmon",
						activebackground="Salmon")
				self.enable()

	#----------------------------------------------------------------------
	def open(self, device, baudrate):
		try:
			self.serial = serial.Serial(	device,
							baudrate,
							bytesize=serial.EIGHTBITS,
							parity=serial.PARITY_NONE,
							stopbits=serial.STOPBITS_ONE,
							timeout=0.1,
							xonxoff=False,
							rtscts=False)
			# Toggle DTR to reset Arduino
			self.serial.setDTR(0)
			time.sleep(1)
			# toss any data already received, see
			# http://pyserial.sourceforge.net/pyserial_api.html#serial.Serial.flushInput
			self.serial.flushInput()
			self.serial.setDTR(1)
			self._pos["state"] = "Connected"
			self._pos["color"] = STATECOLOR[self._pos["state"]]
			self.state.config(text=self._pos["state"],
					background=self._pos["color"])
			self.serial.write("\r\n\r\n")
			self._gcount = 0
			self._alarm  = True
			self.thread  = threading.Thread(target=self.serialIO)
			self.thread.start()
			return True
		except:
			self.serial = None
			self.thread = None
			tkMessageBox.showerror("Error opening serial",
					sys.exc_info()[1],
					parent=self)
		return False

	#----------------------------------------------------------------------
	def close(self):
		if self.serial is None: return
		try:
			self.stopRun()
		except:
			pass
		self._runLines = 0
		self.thread = None
		time.sleep(1)
		self.serial.close()
		self.serial = None
		self._pos["state"] = NOT_CONNECTED
		self._pos["color"] = STATECOLOR[self._pos["state"]]
		try:
			self.state.config(text=self._pos["state"],
					background=self._pos["color"])
		except TclError:
			pass

	#----------------------------------------------------------------------
	# Send to grbl
	#----------------------------------------------------------------------
	def sendGrbl(self, cmd):
		if self.serial and not self.running:
			self.queue.put(cmd)

	#----------------------------------------------------------------------
	def hardReset(self):
		if self.serial is not None:
			self.openClose()
		self.openClose()

	#----------------------------------------------------------------------
	def softReset(self):
		if self.serial:
			self.serial.write("\030")
			self._alarm = True

	def unlock(self):
		self._alarm = False
		self.sendGrbl("$X\n")

	def home(self):
		self._alarm = False
		self.sendGrbl("$H\n")

	#----------------------------------------------------------------------
	def viewSettings(self):
		self.sendGrbl("$$\n")
		self.tabPage.changePage("Terminal")

	def viewParameters(self):
		self.sendGrbl("$#\n$G\n")
		self.tabPage.changePage("WCS")

	def viewState(self):
		self.sendGrbl("$G\n")
		self.tabPage.changePage("Terminal")

	def viewBuild(self):
		self.sendGrbl("$I\n")
		self.tabPage.changePage("Terminal")

	def viewStartup(self):
		self.sendGrbl("$N\n")
		self.tabPage.changePage("Terminal")

	def checkGcode(self):
		self.sendGrbl("$C\n")

	def grblhelp(self):
		self.sendGrbl("$\n")
		self.tabPage.changePage("Terminal")

	def clearTerminal(self):
		self.terminal["state"] = NORMAL
		self.terminal.delete("1.0",END)
		self.terminal["state"] = DISABLED

	#----------------------------------------------------------------------
	def _gChange(self, value, dictionary):
		for k,v in dictionary.items():
			if v==value:
				self.sendGrbl("%s\n"%(k))
				return

	#----------------------------------------------------------------------
	def distanceChange(self):
		if self._gUpdate: return
		self._gChange(self.distanceMode.get(), DISTANCE_MODE)

	#----------------------------------------------------------------------
	def unitsChange(self):
		if self._gUpdate: return
		self._gChange(self.units.get(), UNITS)

	#----------------------------------------------------------------------
	def feedModeChange(self):
		if self._gUpdate: return
		self._gChange(self.feedMode.get(), FEED_MODE)

	#----------------------------------------------------------------------
	def planeChange(self):
		if self._gUpdate: return
		self._gChange(self.plane.get(), PLANE)

	#----------------------------------------------------------------------
	def setFeedRate(self, event=None):
		if self._gUpdate: return
		try:
			feed = float(self.feedRate.get())
			self.sendGrbl("F%g\n"%(feed))
			self.canvasFocus()
		except ValueError:
			pass

	#----------------------------------------------------------------------
	def setTool(self, event=None):
		pass

	#----------------------------------------------------------------------
	def spindleControl(self, event=None):
		if self.spindle.get():
			self.sendGrbl("M3 S%d\n"%(self.spindleSpeed.get()))
		else:
			self.sendGrbl("M5\n")

	#----------------------------------------------------------------------
	def acceptKey(self, skipRun=False):
		if self.tabPage.getActivePage() == "Editor": return False
		if not skipRun and self.running: return False
		focus = self.focus_get()
		if isinstance(focus, Entry) or \
		   isinstance(focus, Spinbox) or \
		   isinstance(focus, Text): return False
		return True

	#----------------------------------------------------------------------
	def setStep(self, value):
		self.step.set("%.4g"%(value))
		self.statusbar["text"] = "Step: %g"%(value)

	def _stepPower(self):
		try:
			step = float(self.step.get())
			if step <= 0.0: step = 1.0
		except:
			step = 1.0
		power = math.pow(10.0,math.floor(math.log10(step)))
		return round(step/power)*power, power

	def incStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step+power
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.setStep(s)

	def decStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step-power
		if s<=0.0: s = step-power/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.setStep(s)

	def mulStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step*10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.setStep(s)

	def divStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.setStep(s)

	#----------------------------------------------------------------------
	def goto(self, x=None, y=None, z=None):
		cmd = "G90G0"
		if x is not None: cmd += "X%g"%(x)
		if y is not None: cmd += "Y%g"%(y)
		if z is not None: cmd += "Z%g"%(z)
		self.sendGrbl("%s\n"%(cmd))

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
		self.sendGrbl("G91G0X-%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYup(self, event=None):
		self.sendGrbl("G91G0X%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXdownYdown(self, event=None):
		self.sendGrbl("G91G0X-%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYdown(self, event=None):
		self.sendGrbl("G91G0X%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveZup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z%s\nG90\n"%(self.step.get()))

	def moveZdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z-%s\nG90\n"%(self.step.get()))

	def go2origin(self, event=None):
		self.sendGrbl("G90G0X0Y0Z0\n")

	def resetCoords(self, event):
		if not self.running: self.sendGrbl("G10P0L20X0Y0Z0\n")

	def resetX(self, event):
		if not self.running: self.sendGrbl("G10P0L20X0\n")

	def resetY(self, event):
		if not self.running: self.sendGrbl("G10P0L20Y0\n")

	def resetZ(self, event):
		if not self.running: self.sendGrbl("G10P0L20Z0\n")

	#----------------------------------------------------------------------
	def feedHold(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("!")
		self.serial.flush()
		self._pause = True

	#----------------------------------------------------------------------
	def resume(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("~")
		self.serial.flush()
		self._pause = False

	#----------------------------------------------------------------------
	def pause(self, event=None):
		if self.serial is None: return
		if self._pause:
			self.resume()
		else:
			self.feedHold()

	#----------------------------------------------------------------------
	def wcsSet(self, event=None):
		self._wcsSet(self.wcsX.get(), self.wcsY.get(), self.wcsZ.get())
		self.wcsX.delete(0,END)
		self.wcsY.delete(0,END)
		self.wcsZ.delete(0,END)

	#----------------------------------------------------------------------
	def wcsSet0(self): self._wcsSet(0.0,0.0,0.0)
	def wcsSetX0(self): self._wcsSet(0.0,"","")
	def wcsSetY0(self): self._wcsSet("",0.0,"")
	def wcsSetZ0(self): self._wcsSet("","",0.0)

	#----------------------------------------------------------------------
	def wcsChange(self):
		idx = self.wcsvar.get()
		self.sendGrbl(WCS[idx]+"\n$G\n")

	#----------------------------------------------------------------------
	# Return the X%g Y%g Z%g from user input
	#----------------------------------------------------------------------
	def _wcsXYZ(self, x, y, z):
		cmd = ""
		if x!="": cmd += "X"+str(x)
		if y!="": cmd += "Y"+str(y)
		if z!="": cmd += "Z"+str(z)
		return cmd

	#----------------------------------------------------------------------
	def _wcsSet(self, x, y, z):
		p = self.wcsvar.get()
		if p<6:
			cmd = "G10L20P%d"%(p+1)
		elif p==6:
			cmd = "G28.1"
		elif p==7:
			cmd = "G30.1"
		elif p==8:
			cmd = "G92"

		cmd += self._wcsXYZ(x,y,z)

		self.sendGrbl(cmd+"\n$#\n")
		self.statusbar["text"] = "Set workspace %s to X%s Y%s Z%s"% \
					(WCS[p],str(x),str(y),str(z))

	#----------------------------------------------------------------------
	# FIXME ????
	#----------------------------------------------------------------------
	def g28Command(self):
		self.sendGrbl("G28.1\n")

	#----------------------------------------------------------------------
	# FIXME ????
	#----------------------------------------------------------------------
	def g30Command(self):
		self.sendGrbl("G30.1\n")

	#----------------------------------------------------------------------
	def g92Command(self):
		cmd = "G92"+self._wcsXYZ(self.wcsX.get(), self.wcsY.get(), self.wcsZ.get())
		self.sendGrbl(cmd+"\n$#\n")
		self.statusbar["text"] = "Set legacy zero location"

	#----------------------------------------------------------------------
	def tloSet(self, event=None):
		cmd = "G43.1Z"+(self._tloin.get())
		self.sendGrbl(cmd+"\n$#\n")

	#----------------------------------------------------------------------
	def probeGetMargins(self):
		self.probeXmin.set(str(self.cnc.xmin))
		self.probeXmax.set(str(self.cnc.xmax))
		self.probeYmin.set(str(self.cnc.ymin))
		self.probeYmax.set(str(self.cnc.ymax))
		self.probeChange()

	#----------------------------------------------------------------------
	def probeChange(self, verbose=True):
		probe = self.gcode.probe
		error = False
		try:
			probe.xmin = float(self.probeXmin.get())
			probe.xmax = float(self.probeXmax.get())
			probe.xn   = max(2,int(self.probeXbins.get()))
			self.probeXstep["text"] = "%.5g"%(probe.xstep())
		except ValueError:
			self.probeXstep["text"] = ""
			if verbose:
				tkMessageBox.showerror("Probe Error",
						"Invalid X probing region",
						parent=self)
			error = True

		try:
			probe.ymin = float(self.probeYmin.get())
			probe.ymax = float(self.probeYmax.get())
			probe.yn   = max(2,int(self.probeYbins.get()))
			self.probeYstep["text"] = "%.5g"%(probe.ystep())
		except ValueError:
			self.probeYstep["text"] = ""
			if verbose:
				tkMessageBox.showerror("Probe Error",
						"Invalid Y probing region",
						parent=self)
			error = True

		try:
			probe.zmin  = float(self.probeZmin.get())
			probe.zmax  = float(self.probeZmax.get())
		except ValueError:
			if verbose:
				tkMessageBox.showerror("Probe Error",
					"Invalid Z probing region",
					parent=self)
			error = True

		try:
			probe.feed  = float(self.probeFeed.get())
		except:
			if verbose:
				tkMessageBox.showerror("Probe Error",
					"Invalid probe feed rate",
					parent=self)
			error = True

		return error

	#----------------------------------------------------------------------
	def probeSet(self):
		probe = self.gcode.probe
		self.probeXmin.set(str(probe.xmin))
		self.probeXmax.set(str(probe.xmax))
		self.probeXbins.delete(0,END)
		self.probeXbins.insert(0,probe.xn)
		self.probeXstep["text"] = str(probe.xstep())

		self.probeYmin.set(str(probe.ymin))
		self.probeYmax.set(str(probe.ymax))
		self.probeYbins.delete(0,END)
		self.probeYbins.insert(0,probe.yn)
		self.probeYstep["text"] = str(probe.ystep())

		self.probeZmin.set(str(probe.zmin))
		self.probeZmax.set(str(probe.zmax))
		self.probeFeed.set(str(probe.feed))

	#----------------------------------------------------------------------
	def probeSetZero(self):
		x = self._pos["wx"]
		y = self._pos["wy"]
		self.gcode.probe.setZero(x,y)
		self.draw()

	#----------------------------------------------------------------------
	def probeDraw(self):
		self.draw_probe.set(True)
		self.canvas.draw_probe = self.draw_probe.get()
		self.probeChange(False)
		self.draw()

	#----------------------------------------------------------------------
	def probeClear(self):
		self.gcode.probe.clear()
		self.draw()

	#----------------------------------------------------------------------
	# Probe one Point
	#----------------------------------------------------------------------
	def probeOne(self):
		cmd = "G38.2"
		ok = False
		v = self.probeXdir.get()
		if v != "":
			cmd += "X"+str(v)
			ok = True
		v = self.probeYdir.get()
		if v != "":
			cmd += "Y"+str(v)
			ok = True
		v = self.probeZdir.get()
		if v != "":
			cmd += "Z"+str(v)
			ok = True
		v = self.probeFeed.get()
		if v != "":
			cmd += "F"+str(v)

		if ok:
			self.queue.put(cmd+"\n")
		else:
			tkMessageBox.showerror("Probe Error",
					"At least one probe direction should be specified")

	#----------------------------------------------------------------------
	# Probe an X-Y area
	#----------------------------------------------------------------------
	def probeScanArea(self):
		if self.probeChange(): return

		if self.serial is None or self.running: return
		probe = self.gcode.probe
		self.initRun()

		# absolute
		probe.clear()
		lines = probe.scan()
		self._runLines = len(lines)
		self._gcount   = 0
		self._selectI  = -1		# do not show any lines selected

		self.progress.setLimits(0, self._runLines)

		self.running = True
		# Push commands
		for line in lines:
			self.queue.put(line)

	#----------------------------------------------------------------------
	def emptyQueue(self):
		while self.queue.qsize()>0:
			try:
				self.queue.get_nowait()
			except Empty:
				break

	#----------------------------------------------------------------------
	def initRun(self):
		self._quit  = 0
		self._pause = False
		self._paths = None
		self.disable()
		self.emptyQueue()
		self.queue.put(self.tools["CNC"]["startup"]+"\n")
		time.sleep(1)

	#----------------------------------------------------------------------
	# Send enabled gcode file to the CNC machine
	#----------------------------------------------------------------------
	def run(self):
		if self.serial is None:
			tkMessageBox.showerror("Serial Error",
				"Serial is not connected",
				parent=self)
			return
		if self.running:
			if self._pause:
				self.resume()
				return
			tkMessageBox.showerror("Already running",
				"Please stop before",
				parent=self)
			return
		if not self.gcode.probe.isEmpty() and not self.gcode.probe.zeroed:
			tkMessageBox.showerror("Probe is not zeroed",
				"Please ZERO any location of the probe before starting a run",
				parent=self)
			return

		lines,paths = self.gcode.prepare2Run()
		if not lines:
			tkMessageBox.showerror("Empty gcode",
				"Not gcode file was loaded",
				parent=self)
			return

		# reset colors
		for ij in paths:
			if ij:
				self.canvas.itemconfig(
					self.gcode[ij[0]].path(ij[1]),
					width=1,
					fill=CNCCanvas.ENABLE_COLOR)

		self.initRun()
		# the buffer of the machine should be empty?
		self._runLines = len(lines)
		#self._runLines = 0
		#del self._runLineMap[:]
		#lineno = 0
		#for line in lines:
		#	#print "***",lineno,line
		#	if line is not None:
		#		self._runLines += 1
		#		self._runLineMap.append(lineno)
		#		if line and line[0]!=' ': lineno += 1	# ignore expanded lines
		#	else:
		#		lineno += 1			# count commented lines

		self.canvas.clearSelection()
		self._gcount  = 0
		self._selectI = 0	# last selection pointer in items
		self._paths   = paths	# drawing paths for canvas
		self.progress.setLimits(0, self._runLines)

		self.running = True
		for line in lines:
			if line is not None:
				self.queue.put(line+"\n")

	#----------------------------------------------------------------------
	# Called when run is finished
	#----------------------------------------------------------------------
	def runEnded(self):
		self._runLines = 0
		self._quit     = 0
		self._pause    = False
		self.running   = False
		self.enable()

	#----------------------------------------------------------------------
	# Stop the current run
	#----------------------------------------------------------------------
	def stopRun(self):
		self.feedHold()
		self._stop = True
		time.sleep(1)
		self.softReset()
		time.sleep(1)
		self.unlock()
		self.runEnded()

	#----------------------------------------------------------------------
	# Start the web pendant
	#----------------------------------------------------------------------
	def startPendant(self, showInfo=True):
		started=CNCPendant.start(self)
		if showInfo:
			hostName="http://%s:%d"%(socket.gethostname(),CNCPendant.port)
			if started:
				tkMessageBox.showinfo("Pendant",
					"Pendant started:\n"+hostName,
					parent=self)
			else:
				dr=tkMessageBox.askquestion("Pendant",
				"Pendant already started:\n"+hostName+"\nWould you like open it locally?")
				if dr=="yes":
					webbrowser.open(hostName,new=2)

	#----------------------------------------------------------------------
	# Stop the web pendant
	#----------------------------------------------------------------------
	def stopPendant(self):
		if CNCPendant.stop():
			tkMessageBox.showinfo("Pendant","Pendant stopped", parent=self)

	#----------------------------------------------------------------------
	# thread performing I/O on serial line
	#----------------------------------------------------------------------
	def serialIO(self):
		from CNC import WAIT
		cline = []
		tosend = None
		self.wait = False
		tr = tg = time.time()
		while self.thread:
			t = time.time()
			if t-tr > SERIAL_POLL:
				# Send one ?
				self.serial.write("?")
				tr = t

			if tosend is None and not self.wait and not self._pause and self.queue.qsize()>0:
				try:
					tosend = self.queue.get_nowait()
					cline.append(len(tosend))
					self.log.put((True,tosend))
				except Empty:
					break

			if tosend is None or self.serial.inWaiting():
				line = self.serial.readline().strip()
				if line:
					if line[0]=="<":
						pat = STATUSPAT.match(line)
						if pat:
							if not self._alarm:
								self._pos["state"] = pat.group(1)
							self._pos["mx"] = float(pat.group(2))
							self._pos["my"] = float(pat.group(3))
							self._pos["mz"] = float(pat.group(4))
							self._pos["wx"] = float(pat.group(5))
							self._pos["wy"] = float(pat.group(6))
							self._pos["wz"] = float(pat.group(7))
							self._posUpdate = True
						else:
							self.log.put((False, line+"\n"))

					elif line[0]=="[":
						self.log.put((False, line+"\n"))
						pat = POSPAT.match(line)
						if pat:
							if pat.group(1) == "PRB":
								if self.running:
									self.gcode.probe.add(
										 float(pat.group(2))+self._pos["wx"]-self._pos["mx"],
										 float(pat.group(3))+self._pos["wy"]-self._pos["my"],
										 float(pat.group(4))+self._pos["wz"]-self._pos["mz"])
								self._probeUpdate = True
							else:
								self._wcsUpdate = True
							self._pos[pat.group(1)] = \
								[float(pat.group(2)),
								 float(pat.group(3)),
								 float(pat.group(4))]
						else:
							pat = TLOPAT.match(line)
							if pat:
								self._pos[pat.group(1)] = pat.group(2)
							else:
								self._pos["G"] = line[1:-1].split()
								self._gUpdate = True

					else:
						self.log.put((False, line+"\n"))
						uline = line.upper()
						if uline.find("ERROR")>=0 or uline.find("ALARM")>=0:
							self._gcount += 1
							if cline: del cline[0]
							if not self._alarm:
								self._posUpdate = True
							self._alarm = True
							self._pos["state"] = line
							if self.running:
								self.emptyQueue()
								# Dangerous calling state of Tk if not reentrant
								self.runEnded()
								tosend = None
								del cline[:]

						elif line.find("ok")>=0:
							self._gcount += 1
							if cline: del cline[0]

						if self.wait and not cline:
							# buffer is empty go one
							self._gcount += 1
							self.wait = False
			# Message came to stop
			if self._stop:
				self.emptyQueue()
				tosend = None
				del cline[:]
				self._stop = False

			if tosend is not None and sum(cline) <= RX_BUFFER_SIZE-2:
#				if isinstance(tosend, list):
#					self.serial.write(str(tosend.pop(0)))
#					if not tosend: tosend = None
				if isinstance(tosend, unicode):
					self.serial.write(tosend.encode("ascii","replace"))
				else:
					self.serial.write(str(tosend))
				tosend = None

				if not self.running and t-tg > G_POLL:
					self.serial.write("$G\n")
					tg = t

	#----------------------------------------------------------------------
	# "thread" timed function looking for messages in the serial thread
	# and reporting back in the terminal
	#----------------------------------------------------------------------
	def monitorSerial(self):
		inserted = False

		# Check serial output
		t = time.time()
		while self.log.qsize()>0 and time.time()-t<0.1:
			try:
				io, line = self.log.get_nowait()
				if not inserted:
					self.terminal["state"] = NORMAL
					inserted = True
				if io:
					self.terminal.insert(END, line, "SEND")
				else:
					self.terminal.insert(END, line)
			except Empty:
				break

		# Check pendant
		try:
			cmd = self.pendant.get_nowait()
			self.execute(cmd)
		except Empty:
			pass

		# Update position if needed
		if self._posUpdate:
			state = self._pos["state"]
			self.state["text"] = state
			try:
				self._pos["color"] = STATECOLOR[state]
			except KeyError:
				if self._alarm:
					self._pos["color"] = STATECOLOR["Alarm"]
				else:
					self._pos["color"] = STATECOLORDEF
			self._pause = (state=="Hold")

			self.state["background"] = self._pos["color"]

			self.xwork["text"] = self._pos["wx"]
			self.ywork["text"] = self._pos["wy"]
			self.zwork["text"] = self._pos["wz"]

			self.xmachine["text"] = self._pos["mx"]
			self.ymachine["text"] = self._pos["my"]
			self.zmachine["text"] = self._pos["mz"]

			self.canvas.gantry(self._pos["wx"],
					   self._pos["wy"],
					   self._pos["wz"],
					   self._pos["mx"],
					   self._pos["my"],
					   self._pos["mz"])
			self._posUpdate = False

		# Update parameters if needed
		if self._wcsUpdate:
			try:
				value = self._pos[WCS[self.wcsvar.get()]]
				for i in range(3):
					self.wcs[i]["text"] = value[i]
			except KeyError:
				pass

			self._tlo["text"] = self._pos.get("TLO","")
			self._wcsUpdate = False

		# Update status string
		if self._gUpdate:
			for g in self._pos["G"]:
				if g[0]=='G':
					try:
						w, v = self.gstate[g]
						w.set(v)
					except KeyError:
						try:
							self.wcsvar.set(WCS.index(g))
						except ValueError:
							pass
				elif g[0] == 'F':
					if self.focus_get() is not self.feedRate:
						self.feedRate.delete(0,END)
						self.feedRate.insert(0,g[1:])

				elif g[0] == 'T':
					if self.focus_get() is not self.toolEntry:
						self.toolEntry.delete(0,END)
						self.toolEntry.insert(0,g[1:])

				elif g[0] == 'S':
					self.spindleSpeed.set(int(float(g[1:])))
			self._gUpdate = False

		# Update probe and draw point
		if self._probeUpdate:
			try:
				probe = self._pos.get("PRB")
				self._probeX["text"] = probe[0]
				self._probeY["text"] = probe[1]
				self._probeZ["text"] = probe[2]
			except:
				pass
			self.canvas.drawProbePoint(probe)
			self._probeUpdate = False

		if inserted:
			self.terminal.see(END)
			self.terminal["state"] = DISABLED

		if self.running:
			self.progress.setProgress(self._runLines-self.queue.qsize(),
						self._gcount)

			if self._selectI>=0 and self._paths:
				while self._selectI < self._gcount and self._selectI<len(self._paths):
					if self._paths[self._selectI]:
						i,j = self._paths[self._selectI]
						path = self.gcode[i].path(j)
						self.canvas.itemconfig(path, width=2, fill=CNCCanvas.PROCESS_COLOR)
					self._selectI += 1

			if self._gcount >= self._runLines:
				self.runEnded()

		# Load file from pendant
		if self._pendantFileUploaded!=None:
			self.load(self._pendantFileUploaded)
			self._pendantFileUploaded=None

		self.after(MONITOR_AFTER, self.monitorSerial)

	#----------------------------------------------------------------------
	def get(self, section, item):
		return Utils.config.get(section, item)

	#----------------------------------------------------------------------
	def set(self, section, item, value):
		return Utils.config.set(section, item, value)

#------------------------------------------------------------------------------
if __name__ == "__main__":
	tk = Tk()
	tk.withdraw()
	try:
		Tkinter.CallWrapper = Utils.CallWrapper
	except:
		tkinter.CallWrapper = Utils.CallWrapper

	tkExtra.bindClasses(tk)
	Utils.loadConfiguration()

	application = Application(tk)
	if len(sys.argv)>1:
		application.load(sys.argv[1])
	try:
		tk.mainloop()
	except KeyboardInterrupt:
		application.quit()

	application.close()
	Utils.saveConfiguration()
	sys.exit()		# <--- for Mac to exit from the menu?
 #vim:ts=8:sw=8:sts=8:noet
