#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

__version__ = "0.0"
__prg__     = "bCNC"
__author__  = "Vasilis Vlachoudis"
__email__   = "Vasilis.Vlachoudis@cern.ch"

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
import serial.tools.list_ports

try:
	from Queue import *
	from Tkinter import *
	import ConfigParser
	import tkMessageBox
except ImportError:
	from queue import *
	from tkinter import *
	import configparser as ConfigParser
	import tkinter.messagebox as TkMessageBox

import rexx
import tkExtra
import Unicode
import bFileDialog

import CNC
import CNCEditor
import CNCCanvas
import CNCPendant

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200]

SERIAL_POLL   = 0.250 # s
MONITOR_AFTER =  250 # ms
DRAW_AFTER    =  300 # ms

RX_BUFFER_SIZE = 128

GPAT         = re.compile(r"[A-Za-z]\d+.*")
LINEPAT      = re.compile(r"^(.*?)\n(.*)", re.DOTALL|re.MULTILINE)
STATUSPAT    = re.compile(r"^<(.*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*)>$")
POSPAT       = re.compile(r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*)\]$")
TLOPAT       = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")

_LOWSTEP   = 0.0001
_HIGHSTEP  = 1000.0

NOT_CONNECTED = "Not connected"

WCS = ["G54", "G55", "G56", "G57", "G58", "G59", "G28", "G30", "G92"]

config = ConfigParser.ConfigParser()

STATECOLOR = {	"Alarm": "Red",
		"Run"  : "LightGreen",
		"Connected" : "Orange",
		NOT_CONNECTED: "OrangeRed"}
STATECOLORDEF = "LightYellow"

prgpath = os.path.abspath(os.path.dirname(sys.argv[0]))

#==============================================================================
# Main Application window
#==============================================================================
class Application(Toplevel):
	def __init__(self, master, **kw):
		global config

		Toplevel.__init__(self, master, **kw)
		self.iconbitmap("@%s/bCNC.xbm"%(prgpath))
		self.title(__prg__)
		self.widgets = []

		# Global variables
		self.cnc  = CNC.CNC()
		self.cnc.loadConfig(config)
		self.view = StringVar()
		self.view.set(CNCCanvas.VIEWS[0])
		self.view.trace('w',self.viewChange)

		self.draw_axes   = BooleanVar()
		self.draw_axes.set(bool(config.get("Canvas","axes")))
		self.draw_grid   = BooleanVar()
		self.draw_grid.set(bool(config.get("Canvas","grid")))
		self.draw_margin = BooleanVar()
		self.draw_margin.set(bool(config.get("Canvas","margin")))
		self.draw_probe  = BooleanVar()
		self.draw_probe.set(bool(config.get("Canvas","axes")))
		self.draw_workarea = BooleanVar()
		self.draw_workarea.set(bool(int(config.get("Canvas","workarea"))))

		# --- Toolbar ---
		self.createToolbar()

		# Main frame
		paned = PanedWindow(self, orient=HORIZONTAL)
		paned.pack(fill=BOTH, expand=YES)

		# Status bar
		self.statusbar = Label(self, relief=SUNKEN,
			foreground="DarkBlue", justify=LEFT, anchor=W)
		self.statusbar.pack(side=BOTTOM, fill=X)

		# Command bar
		self.command = Entry(self, relief=SUNKEN, background="White")
		self.command.pack(side=BOTTOM, fill=X)
		self.command.bind("<Return>",	self.commandExecute)
		self.command.bind("<Up>",	self.commandHistoryUp)
		self.command.bind("<Down>",	self.commandHistoryDown)
		tkExtra.Balloon.set(self.command, "Command line: Accept g-code commands or macro commands (RESET/HOME...) or editor commands (move,inkscape, round...)")
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
		self.state = Label(frame, text=NOT_CONNECTED,
				background=STATECOLOR[NOT_CONNECTED])
		self.state.grid(row=row,column=col, columnspan=3, sticky=EW)

		row += 1
		col = 0
		Label(frame,text="WPos:").grid(row=row,column=col,sticky=E)

		# work
		col += 1
		self.xwork = Label(frame, background="White",anchor=E)
		self.xwork.grid(row=row,column=col,padx=1,sticky=EW)
		self.xwork.bind("<1>", self.resetX)
		tkExtra.Balloon.set(self.xwork, "X work position. Click to set to ZERO")

		# ---
		col += 1
		self.ywork = Label(frame, background="White",anchor=E)
		self.ywork.grid(row=row,column=col,padx=1,sticky=EW)
		self.ywork.bind("<1>", self.resetY)
		tkExtra.Balloon.set(self.ywork, "Y work position. Click to set to ZERO")

		# ---
		col += 1
		self.zwork = Label(frame, background="White", anchor=E)
		self.zwork.grid(row=row,column=col,padx=1,sticky=EW)
		self.zwork.bind("<1>", self.resetZ)
		tkExtra.Balloon.set(self.zwork, "Z work position. Click to set to ZERO")

		# Machine
		row += 1
		col = 0
		Label(frame,text="MPos:").grid(row=row,column=col,sticky=E)

		col += 1
		self.xmachine = Label(frame, background="White",anchor=E)
		self.xmachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.ymachine = Label(frame, background="White",anchor=E)
		self.ymachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.zmachine = Label(frame, background="White", anchor=E)
		self.zmachine.grid(row=row,column=col,padx=1,sticky=EW)

		frame.grid_columnconfigure(1, weight=1)
		frame.grid_columnconfigure(2, weight=1)
		frame.grid_columnconfigure(3, weight=1)

		# Tab page set
		self.tabPage = tkExtra.TabPageSet(panedframe, pageNames=
					[("Control",  icons["control"]),
					 ("Terminal", icons["terminal"]),
					 ("WCS",      icons["axes"]),
					 ("Probe",    icons["measure"]),
					 ("Editor",   icons["edit"])])
		self.tabPage.pack(fill=BOTH, expand=YES)
		self.tabPage.bind("<<ChangePage>>", self.changePage)

		# Control
		frame = self.tabPage["Control"]

		# Control -> Connection
		lframe = LabelFrame(frame, text="Connection")
		lframe.pack(side=TOP, fill=X)

		Label(lframe,text="Port:").grid(row=0,column=0,sticky=E)
		self.portCombo = tkExtra.Combobox(lframe, False, background="White", width=8)
		self.portCombo.grid(row=0, column=1, columnspan=2, sticky=EW)
		devices = sorted([x[0] for x in serial.tools.list_ports.comports()])
		self.portCombo.fill(devices)
		self.portCombo.set(config.get("Connection","port"))

		self.connectBtn = Button(lframe, text="Open",
					compound=LEFT,
					image=icons["serial"],
					command=self.openClose,
					background="LightGreen",
					activebackground="LightGreen",
					padx=2, pady=2)
		self.connectBtn.grid(row=0,column=3,sticky=EW)
		tkExtra.Balloon.set(self.connectBtn, "Open/Close serial port")

		b = Button(lframe, text="Home",
				compound=LEFT,
				image=icons["home"],
				command=self.home,
				padx=2)
		b.grid(row=1,column=1,sticky=EW)
		tkExtra.Balloon.set(b, "Perform a homing cycle")
		self.widgets.append(b)

		b = Button(lframe, text="Unlock",
				compound=LEFT,
				image=icons["unlock"],
				command=self.unlock,
				padx=2)
		b.grid(row=1,column=2,sticky=EW)
		tkExtra.Balloon.set(b, "Unlock device")
		self.widgets.append(b)

		b = Button(lframe, text="Reset",
				compound=LEFT,
				image=icons["reset"],
				command=self.softReset,
				foreground="DarkRed",
				background="LightYellow",
				activebackground="LightYellow",
				padx=2,pady=1)
		b.grid(row=1,column=3,sticky=EW)
		tkExtra.Balloon.set(b, "Soft reset close/re-open")
		self.widgets.append(b)

		lframe.grid_columnconfigure(1, weight=1)
		lframe.grid_columnconfigure(2, weight=1)

		# Control -> Control
		lframe = LabelFrame(frame, text="Control")
		lframe.pack(side=TOP, fill=X)

		f = Frame(lframe)
		f.pack()

		row,col = 0,0
		Label(f, text="Z").grid(row=row, column=col)

		col += 3
		Label(f, text="Y").grid(row=row, column=col)

		# ---
		row += 1
		col = 0

		width=3
		height=2

		b = Button(f, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveZup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Z")
		self.widgets.append(b)

		col += 2
		b = Button(f, text=Unicode.UPPER_LEFT_TRIANGLE,
					width=width, height=height,
					command=self.moveXdownYup)

		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X +Y")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveYup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Y")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.UPPER_RIGHT_TRIANGLE,
					width=width, height=height,
					command=self.moveXupYup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X +Y")
		self.widgets.append(b)

		col += 2
		b = Button(f, text=u"\u00D710", width=3, padx=1, pady=1, command=self.mulStep)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Multiply step by 10")
		self.widgets.append(b)

		col += 1
		b = Button(f, text="+", width=3, padx=1, pady=1, command=self.incStep)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Increase step by 1 unit")
		self.widgets.append(b)

		# ---
		row += 1
		col = 1
		Label(f, text="X", width=3, anchor=E).grid(row=row, column=col, sticky=E)

		col += 1
		b = Button(f, text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveXdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.LARGE_CIRCLE,
					width=width, height=height,
					command=self.go2origin)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move to 0, 0, 0")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveXup)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X")
		self.widgets.append(b)

		# --
		col += 1
		Label(f,"",width=2).grid(row=row,column=col)

		col += 1
		self.step = tkExtra.Combobox(f, width=6, background="White")
		self.step.grid(row=row, column=col, columnspan=2, sticky=EW)
		self.step.set(config.get("Control","step"))
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

		b = Button(f, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveZdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Z")
		self.widgets.append(b)

		col += 2
		b = Button(f, text=Unicode.LOWER_LEFT_TRIANGLE,
					width=width, height=height,
					command=self.moveXdownYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X -Y")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					width=width, height=height,
					command=self.moveYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Y")
		self.widgets.append(b)

		col += 1
		b = Button(f, text=Unicode.LOWER_RIGHT_TRIANGLE,
					width=width, height=height,
					command=self.moveXupYdown)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X -Y")
		self.widgets.append(b)

		col += 2
		b = Button(f, text=u"\u00F710", padx=1, pady=1, command=self.divStep)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Divide step by 10")
		self.widgets.append(b)

		col += 1
		b = Button(f, text="-", padx=1, pady=1, command=self.decStep)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Decrease step by 1 unit")
		self.widgets.append(b)

		#f.grid_columnconfigure(6,weight=1)

		# Control -> Spindle
		lframe = LabelFrame(frame, text="Spindle")
		lframe.pack(side=TOP, fill=X)

		self.spindle = BooleanVar()
		self.spindleSpeed = IntVar()

		b = Checkbutton(lframe, text="Spindle",
				image=icons["spinningtop"],
				compound=LEFT,
				indicatoron=False,
				variable=self.spindle,
				command=self.spindleControl)
		tkExtra.Balloon.set(b, "Start/Stop spindle (M3/M5)")
		b.pack(side=LEFT, fill=Y)
		self.widgets.append(b)

		b = Scale(lframe, command=self.spindleControl,
				variable=self.spindleSpeed,
				showvalue=True,
				orient=HORIZONTAL,
				from_=config.get("CNC","spindlemin"),
				to_=config.get("CNC","spindlemax"))
		tkExtra.Balloon.set(b, "Set spindle RPM")
		b.pack(side=RIGHT, expand=YES, fill=X)
		self.widgets.append(b)

		# Control -> Run
		lframe = LabelFrame(frame, text="Run")
		lframe.pack(side=TOP, fill=X)
		f = Frame(lframe)
		f.pack(side=TOP,fill=X)
		b = Button(f, text="Run",
				compound=LEFT,
				image=icons["start"],
				padx=3, pady=2,
				command=self.run)
		b.pack(side=LEFT,expand=YES,fill=X)
		tkExtra.Balloon.set(b, "Send g-code commands from editor to CNC")
		self.widgets.append(b)

		b = Button(f, text="Pause",
				compound=LEFT,
				image=icons["pause"],
				padx=3, pady=2,
				command=self.pause)
		b.pack(side=LEFT,expand=YES,fill=X)
		tkExtra.Balloon.set(b, "Pause running program")

		b = Button(f, text="Stop",
				compound=LEFT,
				image=icons["stop"],
				padx=3, pady=2,
				command=self.stopRun)
		tkExtra.Balloon.set(b, "Stop running program")
		b.pack(side=LEFT,expand=YES,fill=X)

		self.progress = tkExtra.ProgressBar(lframe, height=24)
		self.progress.pack(fill=X)

		# ---- Terminal ----
		frame = self.tabPage["Terminal"]
		self.terminal = Text(frame, background="White", width=20, wrap=NONE, state=DISABLED)
		self.terminal.pack(side=LEFT, fill=BOTH, expand=YES)
		sb = Scrollbar(frame, orient=VERTICAL, command=self.terminal.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.terminal.config(yscrollcommand=sb.set)
		self.terminal.tag_config("SEND",  foreground="Blue")
		self.terminal.tag_config("ERROR", foreground="Red")

		# ---- WorkSpace ----
		frame = self.tabPage["WCS"]

		# WorkSpace -> WPS
		lframe = LabelFrame(frame, text="WCS")
		lframe.pack(side=TOP, fill=X)

		self.wcs = []
		self.wcsvar = IntVar()
		self.wcsvar.set(0)

		row=0
		col=1
		Label(lframe, text="X").grid(row=row, column=col)
		col += 1
		Label(lframe, text="Y").grid(row=row, column=col)
		col += 1
		Label(lframe, text="Z").grid(row=row, column=col)

		for p in range(9):
			row += 1
			col=0
			b = Radiobutton(lframe, text=WCS[p],
					foreground="DarkRed",
					font = "Helvetica,14",
					padx=2, pady=2,
					variable=self.wcsvar,
					value=p,
					indicatoron=FALSE,
					command=self.wcsChange)
			b.grid(row=row, column=col,  sticky=NSEW)
			self.widgets.append(b)

			col += 1
			x = Label(lframe, foreground="DarkBlue", background="gray95")
			x.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

			col += 1
			y = Label(lframe, foreground="DarkBlue", background="gray95")
			y.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

			col += 1
			z = Label(lframe, foreground="DarkBlue", background="gray95")
			z.grid(row=row, column=col, padx=1, pady=1, sticky=NSEW)

			self.wcs.append((x,y,z))

			row += 1

		# Set workspace
		row += 1
		col  = 1
		self.wcsX = tkExtra.FloatEntry(lframe, background="White")
		self.wcsX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsX, "If not empty set the X workspace")
		self.widgets.append(self.wcsX)

		col += 1
		self.wcsY = tkExtra.FloatEntry(lframe, background="White")
		self.wcsY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsY, "If not empty set the Y workspace")
		self.widgets.append(self.wcsY)

		col += 1
		self.wcsZ = tkExtra.FloatEntry(lframe, background="White")
		self.wcsZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsZ, "If not empty set the Z workspace")
		self.widgets.append(self.wcsZ)

		col += 1
		b = Button(lframe, text="set",
				command=self.wcsSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
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

		col += 1
		b = Button(lframe, text="set",
				command=self.tloSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.widgets.append(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# WorkSpace -> Probing

		#lframe = LabelFrame(frame, text="Probing")
		#lframe.pack(side=TOP, fill=X)

		#lframe = LabelFrame(frame, text="AutoLevel")
		#lframe.pack(side=TOP, fill=X)

		# ---- WorkSpace ----
		frame = self.tabPage["Probe"]

		# WorkSpace -> Probe
		lframe = LabelFrame(frame, text="Probe")
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
		lframe = LabelFrame(frame, text="Autolevel")
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
		self.probeXbins.delete(0,END)
		self.probeXbins.insert(0,"5")
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
		self.probeXdir.set(config.get("Probe","x"))
		self.probeYdir.set(config.get("Probe","y"))
		self.probeZdir.set(config.get("Probe","z"))

		self.probeXmin.set(config.get("Probe","xmin"))
		self.probeXmax.set(config.get("Probe","xmax"))
		self.probeYmin.set(config.get("Probe","ymin"))
		self.probeYmax.set(config.get("Probe","ymax"))
		self.probeZmin.set(config.get("Probe","zmin"))
		self.probeZmax.set(config.get("Probe","zmax"))
		self.probeFeed.set(config.get("Probe","feed"))

		self.probeXbins.delete(0,END)
		self.probeXbins.insert(0,config.get("Probe","xn"))

		self.probeYbins.delete(0,END)
		self.probeYbins.insert(0,config.get("Probe","yn"))
		self.probeChange()

		# Buttons
		row += 1
		col  = 0
		f = Frame(lframe)
		f.grid(row=row, column=col, columnspan=5, sticky=EW)

		b = Button(f, text="Scan", command=self.probeScanArea)
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

		# --- GCode Editor ---
		frame = self.tabPage["Editor"]

		self.editor = CNCEditor.CNCEditor(frame, self)
		self.editor.pack(expand=TRUE, fill=BOTH)
		self.widgets.append(self.editor.text)

		self.tabPage.changePage()

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
		self.canvas.bind("<Motion>",		self.canvasMotion)
		self.canvas.bind('<Control-Key-c>',	self.copy)
		self.canvas.bind('<Control-Key-x>',	self.cut)
		self.canvas.bind('<Control-Key-v>',	self.paste)

		# Global bindings
		self.bind('<Escape>',		self.unselectAll)
		self.bind('<Control-Key-a>',	self.selectAll)
		self.bind('<Control-Key-f>',	self.find)
		self.bind('<Control-Key-g>',	self.findNext)
		self.bind('<Control-Key-h>',	self.replace)
		self.bind("<Control-Key-l>",	self.loadDialog)
		self.bind("<Control-Key-q>",	self.quit)
		self.bind("<Control-Key-s>",	self.saveAll)
		self.bind('<Control-Key-y>',	self.redo)
		self.bind('<Control-Key-z>',	self.undo)
#		self.bind('<Control-Key-Z>',	self.redo)
		self.canvas.bind('<Key-space>',	self.commandFocus)
		self.bind('<Control-Key-space>',self.commandFocus)

		self.bind('<F1>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XY]))
		self.bind('<F2>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_XZ]))
		self.bind('<F3>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_YZ]))
		self.bind('<F4>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO1]))
		self.bind('<F5>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO2]))
		self.bind('<F6>',		lambda e,s=self : s.view.set(CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO3]))

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

		self.protocol("WM_DELETE_WINDOW", self.quit)

		for x in self.widgets:
			if isinstance(x,Entry):
				x.bind("<Escape>", self.canvasFocus)

		# Menu
		self.createMenu()

		self.canvas.focus_set()

		# Highlight variables
		self.history     = []
		self._historyPos = None
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
				    "G": ["G54"]}
		self._posUpdate  = False
		self._posUpdate2 = False
		self._posUpdate3 = False
		self.running     = False
		self._runLines   = 0
		self._runLineMap = []
		self._quit       = 0
		self._pause      = False
		self._drawAfter  = None	# after handle for modification
		self._alarm      = True
		self.monitorSerial()
		self.toggleDrawFlag()
		if int(config.get("Connection","pendant")):
			self.startPendant(False)

	#----------------------------------------------------------------------
	def createToolbar(self):
		toolbar = Frame(self, relief=RAISED)
		toolbar.pack(side=TOP, fill=X)

		b = Button(toolbar, image=icons["load"], command=self.loadDialog)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Load g-code file")

		b = Button(toolbar, image=icons["save"], command=self.saveAll)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Save g-code to file")

		# ---
		Label(toolbar, image=icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=icons["undo"], command=self.undo)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Undo last edit")

		b = Button(toolbar, image=icons["redo"], command=self.redo)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Redo last undo command")

		# ---
		Label(toolbar, image=icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=icons["cut"], command=self.cut)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Cut to clipboard")

		b = Button(toolbar, image=icons["copy"], command=self.copy)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Copy to clipboard")

		b = Button(toolbar, image=icons["paste"], command=self.paste)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Paste from clipboard")

		# ---
		Label(toolbar, image=icons["sep"]).pack(side=LEFT, padx=3)

		b = Button(toolbar, image=icons["home"], command=self.home)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Run homing cycle")

		b = Button(toolbar, image=icons["unlock"], command=self.unlock)
		self.widgets.append(b)
		b.pack(side=LEFT)
		tkExtra.Balloon.set(b, "Unlock CNC")

		# ---
		Label(toolbar, image=icons["sep"]).pack(side=LEFT, padx=3)

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
					image=icons["new"],
					compound=LEFT,
					command=self.newFile)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Open", underline=0,
					image=icons["load"],
					compound=LEFT,
					accelerator="Ctrl-O",
					command=self.loadDialog)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Save", underline=0,
					image=icons["save"],
					compound=LEFT,
					accelerator="Ctrl-S",
					command=self.saveAll)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Save As", underline=0,
					image=icons["save"],
					compound=LEFT,
					command=self.saveDialog)
		self.widgets.append((menu,i))

		i += 1
		submenu = Menu(menu)
		menu.add_cascade(label="Probe", underline=0,
					image=icons["empty"],
					compound=LEFT,
					menu=submenu)

		ii = 1
		submenu.add_command(label="Open", underline=0,
					image=icons["load"],
					compound=LEFT,
					command=self.loadProbeDialog)
		self.widgets.append((submenu,ii))

		ii += 1
		submenu.add_command(label="Save", underline=0,
					image=icons["save"],
					compound=LEFT,
					command=self.saveProbe)
		self.widgets.append((submenu,ii))

		ii += 1
		submenu.add_command(label="Save As", underline=0,
					image=icons["save"],
					compound=LEFT,
					command=self.saveProbeDialog)
		self.widgets.append((submenu,ii))

		menu.add_separator()
		menu.add_command(label="Quit", underline=0,
					image=icons["quit"],
					compound=LEFT,
					accelerator="Ctrl-Q",
					command=self.quit)

		# Edit Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Edit", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Undo", underline=0,
					image=icons["undo"],
					compound=LEFT,
					accelerator="Ctrl-Z",
					command=self.undo)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Redo", underline=0,
					image=icons["redo"],
					compound=LEFT,
					accelerator="Ctrl-Y",
					command=self.redo)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Cut", underline=2,
					image=icons["cut"],
					compound=LEFT,
					accelerator="Ctrl-X",
					command=self.cut)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Copy", underline=0,
					image=icons["copy"],
					compound=LEFT,
					accelerator="Ctrl-C",
					command=self.copy)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Paste", underline=0,
					image=icons["paste"],
					compound=LEFT,
					accelerator="Ctrl-V",
					command=self.paste)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Find", underline=0,
					image=icons["find"],
					compound=LEFT,
					accelerator="Ctrl-F",
					command=self.find)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Find Next", underline=0,
					image=icons["find"],
					compound=LEFT,
					accelerator="Ctrl-G",
					command=self.findNext)
		self.widgets.append((menu,i))

		i += 1
		menu.add_command(label="Replace", underline=0,
					image=icons["replace"],
					compound=LEFT,
					accelerator="Ctrl-H",
					command=self.replace)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Select All", underline=8,
					image=icons["all"],
					compound=LEFT,
					accelerator="Ctrl-A",
					command=self.selectAll)
		self.widgets.append((menu,i))

		# Tools Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Tools", underline=0, menu=menu)

		i = 1
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
		submenu.add_command(label="Move command", underline=0,
					command=lambda s=self:s.insertCommand("MOVE x y z", False))
		self.widgets.append((submenu,ii))
		ii += 1
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

		# Control Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Control", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Hard Reset", underline=0,
					image=icons["reset"],
					compound=LEFT,
					command=self.hardReset)
		i += 1
		menu.add_command(label="Soft Reset", underline=0,
					image=icons["reset"],
					compound=LEFT,
					command=self.softReset)
		self.widgets.append((menu,i))
		i += 1
		menu.add_separator()
		i += 1
		menu.add_command(label="Home",       underline=0,
					image=icons["home"],
					compound=LEFT,
					command=self.home)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Unlock",     underline=2,
					image=icons["unlock"],
					compound=LEFT,
					command=self.unlock)
		self.widgets.append((menu,i))
		i += 1
		menu.add_separator()

		i += 1
		menu.add_command(label="Settings",   underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.viewSettings)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Parameters", underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.viewParameters)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="State",      underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.viewState)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Build",      underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.viewBuild)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Startup",    underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.viewStartup)
		self.widgets.append((menu,i))
		i += 1
		menu.add_command(label="Check gcode",underline=0,
					image=icons["empty"],
					compound=LEFT,
					command=self.checkGcode)
		self.widgets.append((menu,i))

		i += 1
		menu.add_separator()
		i += 1
		menu.add_command(label="Grbl Help",underline=0,
					image=icons["info"],
					compound=LEFT,
					command=self.grblhelp)
		self.widgets.append((menu,i))

		# Run Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Run", underline=0, menu=menu)

		i = 1
		menu.add_command(label="Run",       underline=0,
					image=icons["start"],
					compound=LEFT,
					command=self.run)
		self.widgets.append((menu,i))

		menu.add_command(label="Pause", underline=0,
					image=icons["pause"],
					compound=LEFT,
					accelerator="!/~",
					command=self.pause)
		menu.add_command(label="Cancel",    underline=0,
					image=icons["stop"],
					compound=LEFT,
					command=self.stopRun)
		# View Menu
		menu = Menu(menubar)
		menubar.add_cascade(label="View", underline=0, menu=menu)

		menu.add_command(label="Zoom In", underline=2,
					image=icons["zoom_in"],
					compound=LEFT,
					accelerator="[=]",
					command=self.canvas.menuZoomIn)

		menu.add_command(label="Zoom Out", underline=2,
					image=icons["zoom_out"],
					compound=LEFT,
					accelerator="[-]",
					command=self.canvas.menuZoomOut)

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

		menu.add_checkbutton(label="Probe", underline=0,
					variable=self.draw_probe,
					command=self.toggleDrawFlag)

		menu.add_checkbutton(label="WorkArea", underline=0,
					variable=self.draw_workarea,
					command=self.toggleDrawFlag)

		# -----------------
		menu.add_separator()

		submenu = Menu(menu)
		menu.add_cascade(label="Projection", underline=0, menu=submenu)

		submenu.add_radiobutton(label="X-Y", underline=0,
					accelerator="[F1]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_XY],
					variable=self.view)

		submenu.add_radiobutton(label="X-Z", underline=2,
					accelerator="[F2]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_XZ],
					variable=self.view)

		submenu.add_radiobutton(label="Y-Z", underline=0,
					accelerator="[F3]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_YZ],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 1", underline=4,
					accelerator="[F4]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO1],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 2", underline=4,
					accelerator="[F5]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO2],
					variable=self.view)

		submenu.add_radiobutton(label="ISO 3", underline=4,
					accelerator="[F6]",
					value=CNCCanvas.VIEWS[CNCCanvas.VIEW_ISO3],
					variable=self.view)

		# About menu
		menu = Menu(menubar)
		menubar.add_cascade(label="Pendant", underline=0, menu=menu)

		menu.add_command(label="Start", underline=0,
					image=icons["start"],
					compound=LEFT,
					command=self.startPendant)

		menu.add_command(label="Stop", underline=0,
					image=icons["stop"],
					compound=LEFT,
					command=self.stopPendant)

		# About menu
		menu = Menu(menubar)
		menubar.add_cascade(label="About", underline=0, menu=menu)

		menu.add_command(label="About", underline=0,
					image=icons["about"],
					compound=LEFT,
					command=self.about)

	#----------------------------------------------------------------------
	def quit(self, event=None):
		global config

		if self.running and self._quit<2:
			tkMessageBox.showinfo("Running",
				"CNC is currently running, please stop it before.",
				parent=self)
			self._quit += 1
			return
		del self.widgets[:]

		# Connection
		config.set("Connection", "port", self.portCombo.get())

		# Canvas
		config.set("Canvas","axes",    str(int(self.draw_axes.get())))
		config.set("Canvas","grid",    str(int(self.draw_grid.get())))
		config.set("Canvas","margin",  str(int(self.draw_margin.get())))
		config.set("Canvas","probe",   str(int(self.draw_probe.get())))
		config.set("Canvas","workarea",str(int(self.draw_workarea.get())))

		# Control
		config.set("Control", "step", self.step.get())

		# Probe
		config.set("Probe", "x",    self.probeXdir.get())
		config.set("Probe", "y",    self.probeYdir.get())
		config.set("Probe", "z",    self.probeZdir.get())

		config.set("Probe", "xmin", self.probeXmin.get())
		config.set("Probe", "xmax", self.probeXmax.get())
		config.set("Probe", "xn",   self.probeXbins.get())
		config.set("Probe", "ymin", self.probeYmin.get())
		config.set("Probe", "ymax", self.probeYmax.get())
		config.set("Probe", "yn",   self.probeYbins.get())
		config.set("Probe", "zmin", self.probeZmin.get())
		config.set("Probe", "zmax", self.probeZmax.get())
		config.set("Probe", "feed", self.probeFeed.get())

		CNCPendant.stop()
		self.destroy()
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
	def enable(self):
		self.configWidgets("state",NORMAL)

	def disable(self):
		self.configWidgets("state",DISABLED)

	#----------------------------------------------------------------------
	def cut(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
			self.editor.cut()
		elif focus:
			focus.event_generate("<<Cut>>")

	def copy(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
			self.editor.copy()
		elif focus:
			focus.event_generate("<<Copy>>")

	def paste(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
			self.editor.paste()
		elif focus:
			focus.event_generate("<<Paste>>")

	def undo(self, event=None):
		focus = self.focus_get()
		if focus is self.editor.text or focus is self.canvas:
			self.editor.undo()

	def redo(self, event=None):
		focus = self.focus_get()
		if focus is self.editor.text or focus is self.canvas:
			self.editor.redo()

	#----------------------------------------------------------------------
	def about(self, event=None):
		tkMessageBox.showinfo("About",
				"%s\nby %s [%s]\nVersion %s" % \
				(__prg__, __author__, __email__, __version__),
				parent=self)

	#----------------------------------------------------------------------
	def toggleDrawFlag(self):
		self.canvas.draw_axes     = self.draw_axes.get()
		self.canvas.draw_grid     = self.draw_grid.get()
		self.canvas.draw_margin   = self.draw_margin.get()
		self.canvas.draw_probe    = self.draw_probe.get()
		self.canvas.draw_workarea = self.draw_workarea.get()
		self.viewChange()

	#----------------------------------------------------------------------
	def viewChange(self, a=None, b=None, c=None):
		self.draw()
		if self.running:
			self.selectRangeInit()
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
		self.canvas.draw(view, self.editor.get())
		self.editor.text.edit_modified(False)

	# ----------------------------------------------------------------------
	# Redraw with a small delay
	# ----------------------------------------------------------------------
	def drawAfter(self, event):
		self.editor.highlight()
		if self._drawAfter is not None: self.after_cancel(self._drawAfter)
		self._drawAfter = self.after(DRAW_AFTER, self.draw)

	# ----------------------------------------------------------------------
	def canvasMotion(self, event):
		#print
		#print event.x, event.y, self.zoom
		x =  self.canvas.canvasx(event.x) / self.canvas.zoom
		y = -self.canvas.canvasy(event.y) / self.canvas.zoom
		#print x,y,self.canvasx(0), self.canvasy(0)
		wh = "WxH: %gx%g"% ((self.cnc.xmax-self.cnc.xmin), (self.cnc.ymax-self.cnc.ymin))
		if self.canvas.view == CNCCanvas.VIEW_XY:
			self.statusbar["text"] = "X:%.4f  Y:%.4f  %s  Length: %.4f mm   Time: %g min"\
				%(x,y, wh, self.cnc.totalLength, self.cnc.totalTime)

		elif self.canvas.view == CNCCanvas.VIEW_XZ:
			self.statusbar["text"] = "X:%.4f  Z:%.4f  %s  Length: %.4f mm   Time: %g min"\
				%(x,y, wh, self.cnc.totalLength, self.cnc.totalTime)

		elif self.canvas.view == CNCCanvas.VIEW_YZ:
			self.statusbar["text"] = "Y:%.4f  Z:%.4f  %s  Length: %.4f mm   Time: %g min"\
				%(x,y, wh, self.cnc.totalLength, self.cnc.totalTime)

	# ----------------------------------------------------------------------
	def changePage(self, event=None):
		page = self.tabPage.getActivePage()
		if page == "WCS":
			self.send("$#\n$G\n")
			return
		elif page == "Probe":
			self.probeChange(False)

		focus = self.focus_get()
		if focus and focus is self.editor.text and page != "Editor":
			# if the focus was on the editor, but the Editor page is not active
			# set the focus to the canvas
			self.canvas.focus_set()

	#----------------------------------------------------------------------
	def commandFocus(self, event=None):
		self.command.focus_set()

	#----------------------------------------------------------------------
	def canvasFocus(self, event=None):
			self.canvas.focus_set()

	#----------------------------------------------------------------------
	def selectAll(self, event=None):
		self.tabPage.changePage("Editor")
		self.editor.selectAll()
		return "break"

	#----------------------------------------------------------------------
	def unselectAll(self, event=None):
		self.tabPage.changePage("Editor")
		self.editor.unselectAll()
		return "break"

	#----------------------------------------------------------------------
	def find(self, event=None):
		self.tabPage.changePage("Editor")
		self.editor.findDialog()
		return "break"

	#----------------------------------------------------------------------
	def findNext(self, event=None):
		self.tabPage.changePage("Editor")
		self.editor.findNext()
		return "break"

	#----------------------------------------------------------------------
	def replace(self, event=None):
		self.tabPage.changePage("Editor")
		self.editor.replaceDialog()
		return "break"

	# ----------------------------------------------------------------------
	def insertCommand(self, cmd, execute=False):
		self.command.delete(0,END)
		self.command.insert(0,cmd)
		if execute: self.commandExecute()

	#----------------------------------------------------------------------
	# Execute command from command line
	#----------------------------------------------------------------------
	def commandExecute(self, event=None):
		line = self.command.get().strip()
		if not line: return
		self._historyPos = None
		if not self.history or self.history[-1] != line:
			self.history.append(line)
		self.command.delete(0,END)
		self.execute(line)

	#----------------------------------------------------------------------
	# Execute a single command
	#----------------------------------------------------------------------
	def execute(self, line):
		ch = line[0]
		if ch in ("$","!","~","?","(") or GPAT.match(line):
			self.send(line+"\n")
			return

		elif ch == "/":
			self.editor.find(line[1:])
			return
		elif ch == ":":
			self.editor.setInsert("%s.0"%(line[1:]))
			return

		line = line.replace(","," ").split()
		cmd = line[0].upper()

		if rexx.abbrev("ABOUT",cmd,2):
			self.about()

		elif rexx.abbrev("CLEAR",cmd,3):
			self.terminal["state"] = NORMAL
			self.terminal.delete(0,END)
			self.terminal["state"] = DISABLED

		elif rexx.abbrev("CONTROL",cmd,4):
			self.tabPage.changePage("Control")

		elif rexx.abbrev("EDITOR",cmd,4):
			self.tabPage.changePage("Editor")

		elif rexx.abbrev("HOME",cmd,2):
			self.home()

		elif rexx.abbrev("INKSCAPE",cmd,3):
			if len(line)>1 and rexx.abbrev("ALL",line[1].upper()):
				self.editor.selectAll()
			self._execute("INKSCAPE")

		elif cmd=="ISO1":
			self.viewISO1()
		elif cmd=="ISO2":
			self.viewISO2()
		elif cmd=="ISO3":
			self.viewISO3()

		elif rexx.abbrev("LOAD",cmd,2):
			if len(line)>1:
				self.load(line[1])
			else:
				self.loadDialog()

		elif rexx.abbrev("MIRROR",cmd,3):
			if len(line)==1: return
			line1 = line[1].upper()
			#if nothing is selected:
			#self.editor.selectAll()
			if rexx.abbrev("HORIZONTAL",line1):
				self._execute("MIRRORH")
			elif rexx.abbrev("VERTICAL",line1):
				self._execute("MIRRORV")

		elif rexx.abbrev("MOVE",cmd,2):
			if len(line)==1: return
			line1 = line[1].upper()
			if rexx.abbrev("CENTER",line1,2):
				dx = -(self.cnc.xmin + self.cnc.xmax)/2.0
				dy = -(self.cnc.ymin + self.cnc.ymax)/2.0
				dz = 0.0
				self.editor.selectAll()
			elif line1=="BL":
				dx = -self.cnc.xmin
				dy = -self.cnc.ymin
				dz = 0.0
				self.editor.selectAll()
			elif line1=="BR":
				dx = -self.cnc.xmax
				dy = -self.cnc.ymin
				dz = 0.0
				self.editor.selectAll()
			elif line1=="TL":
				dx = -self.cnc.xmin
				dy = -self.cnc.ymax
				dz = 0.0
				self.editor.selectAll()
			elif line1=="TR":
				dx = -self.cnc.xmax
				dy = -self.cnc.ymax
				dz = 0.0
				self.editor.selectAll()
			else:
				try: dx = float(line[1])
				except: dx = 0.0
				try: dy = float(line[2])
				except: dy = 0.0
				try: dz = float(line[3])
				except: dz = 0.0
			self._execute("MOVE",dx,dy,dz)

		elif cmd in ("OPEN","CLOSE"):
			self.openClose()

		elif rexx.abbrev("QUIT",cmd,2) or rexx.abbrev("EXIT",cmd,2):
			self.quit()

		elif cmd == "PAUSE":
			self.pause()

		elif cmd == "RESET":
			self.softReset()

		elif cmd == "RUN":
			self.run()

		elif rexx.abbrev("ROTATE",cmd,3):
			line1 = line[1].upper()
			x0 = y0 = 0.0
			if line1 == "CCW":
				ang = 90.0
				self.editor.selectAll()
			elif line1 == "CW":
				ang = -90.0
				self.editor.selectAll()
			elif line1 == "CW":
				ang = -90.0
				self.editor.selectAll()
			elif line1=="FLIP":
				ang = 180.0
				self.editor.selectAll()
			else:
				try: ang = float(line[1])
				except: pass
				try: x0 = float(line[2])
				except: pass
				try: y0 = float(line[3])
				except: pass
			self._execute("ROTATE",ang,x0,y0)

		elif rexx.abbrev("ROUND",cmd,3):
			acc = None
			if len(line)>1:
				if rexx.abbrev("ALL",line[1].upper()):
					self.editor.selectAll()
				else:
					try:
						acc = int(line[1])
					except:
						pass
			self._execute("ROUND",acc)

		elif rexx.abbrev("SAVE",cmd,2):
			if len(line)>1:
				self.save(line[1])
			else:
				self.saveAll()

		elif cmd == "STEP":
			try:
				self.step.set(float(line[1]))
			except:
				pass

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

		elif cmd == "STOP":
			self.stopRun()

		elif rexx.abbrev("TERMINAL",cmd,4):
			self.tabPage.changePage("Terminal")

#		elif cmd=="UP"
#			self._execute("UP")

		elif rexx.abbrev("UNLOCK",cmd,3):
			self.unlock()

		elif rexx.abbrev("WORKSPACE",cmd,4) or cmd=="WCS":
			self.tabPage.changePage("WCS")

		elif cmd in ("XY","YX"):
			self.viewXY()
		elif cmd in ("XZ","ZX"):
			self.viewXZ()
		elif cmd in ("YZ","ZY"):
			self.viewYZ()

		else:
			tkMessageBox.showerror("Unknown command",
					string.join(line),
					parent=self)
			return

	#----------------------------------------------------------------------
	# Execute a command over the selected lines
	#----------------------------------------------------------------------
	def _execute(self, cmd, *args):
		sel = self.editor.getSelect()
		if not sel: return

		i = 0
		self.editor.skipSelection(True)
		while i < len(sel):
			s = int(str(sel[i]).split(".")[0])-1
			e = int(str(sel[i+1]).split(".")[0])-1
			i += 2
			start = "%d.0"%(s)
			end   = "%d.end"%(e)
			lines = self.editor.get(start,end).splitlines()
			self.editor.delete(start,end)

			#for j in range(s,e+1):
			#	if self.items[j]:
			if cmd=="INKSCAPE":
				lines = self.cnc.inkscapeLines(lines)
			elif cmd=="MOVE":
				lines = self.cnc.moveLines(lines, *args)
			elif cmd=="ROUND":
				lines = self.cnc.roundLines(lines, *args)
			elif cmd=="ROTATE":
				lines = self.cnc.rotateLines(lines, *args)
			elif cmd=="MIRRORH":
				lines = self.cnc.mirrorHLines(lines)
			elif cmd=="MIRRORV":
				lines = self.cnc.mirrorVLines(lines)

			# Reselect the range in case it was changed
			self.editor.insert(start,"\n".join(lines))
			self.editor.selectSet(start,end)
		self.editor.skipSelection(False)
		self.selectionChange()

		self.statusbar["text"] = "%s %s"%(cmd," ".join(map(str,args)))

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

	# ----------------------------------------------------------------------
	# Selection has changed highlight the canvas
	# ----------------------------------------------------------------------
	def selectionChange(self):
		sel = self.editor.getSelect()
		self.canvas.itemconfig(SEL, width=1, fill="Black")
		self.canvas.dtag(SEL)
		if not sel:
			# select current line of cursor
			cur = self.editor.index(INSERT)
			sel = [cur,cur]

		i = 0
		while i < len(sel):
			s = int(str(sel[i]).split(".")[0])-1
			e = int(str(sel[i+1]).split(".")[0])-1
			i += 2
			for j in range(s,e+1):
				if j<len(self.canvas.items) and self.canvas.items[j]:
					self.canvas.addtag_withtag(SEL, self.canvas.items[j])
		#print self.canvas.getMargins()
		self.canvas.itemconfig(SEL, width=2, fill="Blue")
		self.insertMarker()

	# ----------------------------------------------------------------------
	def selectRangeInit(self, idx=0):
		self.canvas.itemconfig(SEL, width=1, fill="Black")
		self.canvas.dtag(SEL)
		self._selectI = idx	# last selection pointer in items
		self._selectP = 0	# last selection gcount

	# ----------------------------------------------------------------------
	def selectRange(self, pos):
		while self._selectP < pos and self._selectI<len(self.canvas.items):
			if self.canvas.items[self._selectI]:
				self.canvas.itemconfig(self.canvas.items[self._selectI], width=2, fill="Blue")
				self._selectP += 1
			self._selectI += 1

	# ----------------------------------------------------------------------
	# Change the insert marker location
	# ----------------------------------------------------------------------
	def insertMarker(self, event=None):
		self.canvas.insertMarker(int(str(self.editor.index(INSERT)).split(".")[0])-1)

	# ----------------------------------------------------------------------
	def delete(self, event):
		sel = self.editor.getSelect()
		self.canvas.itemconfig(SEL, width=1, fill="Black")
		self.canvas.dtag(SEL)
		if not sel: return
		i = 0
		while i < len(sel):
			self.editor.delete(sel[i], sel[i+1])
			i += 2

	#----------------------------------------------------------------------
	def newFile(self, event=None):
		self.cnc.__init__()
		self.editor.set("")
		self.draw()
		self.title(__prg__)

	#----------------------------------------------------------------------
	# load dialog
	#----------------------------------------------------------------------
	def loadDialog(self, event=None):
		filename = bFileDialog.askopenfilename(master=self,
			title="Open file",
			initialfile=os.path.join(
					config.get("File", "dir"),
					config.get("File", "file")),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.load(filename)

	#----------------------------------------------------------------------
	def loadProbeDialog(self, event=None):
		try:
			pfilename = config.get("File", "probe")
		except:
			pfilename = "probe"
		filename = bFileDialog.askopenfilename(master=self,
			title="Open Probe file",
			initialfile=os.path.join(
					config.get("File", "dir"),
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
			initialfile=os.path.join(
					config.get("File", "dir"),
					self.cnc.filename),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.save(filename)

	#----------------------------------------------------------------------
	def saveProbeDialog(self, event=None):
		try:
			pfilename = config.get("File", "probe")
		except:
			pfilename = "probe"
		filename = bFileDialog.asksaveasfilename(master=self,
			title="Save probe file",
			initialfile=os.path.join(
					config.get("File", "dir"),
					pfilename),
			filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
				   ("Probe", ("*.probe")),
				   ("All","*")])
		if filename: self.saveProbe(filename)

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename):
		global config
		fn,ext = os.path.splitext(filename)
		if ext==".probe":
			self.loadProbe(filename)
		else:
			self.loadGcode(filename)

	#----------------------------------------------------------------------
	def loadGcode(self, filename=None):
		if filename:
			config.set("File", "dir",  os.path.dirname(os.path.abspath(filename)))
			config.set("File", "file", os.path.basename(filename))
		self.editor.set(self.cnc.load(filename))
		self.draw()
		self.title("%s: %s"%(__prg__,filename))

	#----------------------------------------------------------------------
	def loadProbe(self, filename):
		config.set("File", "probe", os.path.basename(filename))
		self.cnc.probe.load(filename)
		self.probeSet()

	#----------------------------------------------------------------------
	def save(self, filename):
		global config
		fn,ext = os.path.splitext(filename)
		if ext == ".probe":
			self.cnc.probe.save(filename)
		else:
			self.saveGcode(filename)

	#----------------------------------------------------------------------
	def saveAll(self, event=None):
		self.saveGcode()
		self.saveProbe()

	#----------------------------------------------------------------------
	def saveGcode(self, filename=None):
		if filename is not None:
			config.set("File", "dir",  os.path.dirname(os.path.abspath(filename)))
			config.set("File", "file", os.path.basename(filename))
			self.cnc.filename = filename

		if not self.cnc.save(self.editor.get()):
			tkMessageBox.showerror("Error",
					"Error opening file '%s'"%(self.cnc.filename),
					parent=self)
			return
		self.title("%s: %s"%(__prg__,self.cnc.filename))

	#----------------------------------------------------------------------
	def saveProbe(self, filename=None):
		if filename is not None:
			config.set("File", "probe", os.path.basename(filename))
			self.cnc.probe.filename = filename

		# save probe
		if not self.cnc.probe.isEmpty():
			self.cnc.probe.save()

	#----------------------------------------------------------------------
	def openClose(self):
		if self.serial is not None:
			self.close()
			self.connectBtn.config(text="Open",
					background="LightGreen",
					activebackground="LightGreen")
		else:
			device  = self.portCombo.get()
			baudrate = int(config.get("Connection","baud"))
			if self.open(device, baudrate):
				self.connectBtn.config(text="Close",
						background="Salmon",
						activebackground="Salmon")
				self.enable()

	#----------------------------------------------------------------------
	def open(self, device, baudrate):
		try:
			self.serial = serial.Serial(device,baudrate,timeout=0.1)
			time.sleep(1)
			self._pos["state"] = "Connected"
			self._pos["color"] = STATECOLOR[self._pos["state"]]
			self.state.config(text=self._pos["state"],
					background=self._pos["color"])
			self.serial.write("\r\n\r\n")
			self._gcount = 0
			self._alarm  = True
			self._cline  = []
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
		if self.serial is not None:
			self.stopRun()
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
			self.state

	#----------------------------------------------------------------------
	def send(self, cmd):
		if self.serial and not self.running:
			self.queue.put(cmd)

	#----------------------------------------------------------------------
	def hardReset(self):
		if self.serial is not None:
			self.openClose()
		self.openClose()

	#----------------------------------------------------------------------
	def softReset(self):
		if self.serial: self.serial.write("\030")

	def unlock(self):
		self._alarm = False
		self.send("$X\n")

	def home(self):
		self._alarm = False
		self.send("$H\n")

	def viewSettings(self):
		self.send("$$\n")
		self.tabPage.changePage("Terminal")

	def viewParameters(self):
		self.send("$#\n$G\n")
		self.tabPage.changePage("WCS")

	def viewState(self):
		self.send("$G\n")
		self.tabPage.changePage("Terminal")

	def viewBuild(self):
		self.send("$I\n")
		self.tabPage.changePage("Terminal")

	def viewStartup(self):
		self.send("$N\n")
		self.tabPage.changePage("Terminal")

	def checkGcode(self):
		self.send("$C\n")
		self.tabPage.changePage("Terminal")

	def grblhelp(self):
		self.send("$\n")
		self.tabPage.changePage("Terminal")

	#----------------------------------------------------------------------
	def spindleControl(self, event=None):
		if self.spindle.get():
			self.send("M3 S%d\n"%(self.spindleSpeed.get()))
		else:
			self.send("M5\n")

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
		self.step.set("%.4g"%(s))

	def decStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step-power
		if s<=0.0: s = step-power/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.step.set("%.4g"%(s))

	def mulStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step*10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.step.set("%.4g"%(s))

	def divStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = self._stepPower()
		s = step/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		self.step.set("%.4g"%(s))

	#----------------------------------------------------------------------
	def goto(self, x=None, y=None, z=None):
		cmd = "G90G0"
		if x is not None: cmd += "X%g"%(x)
		if y is not None: cmd += "Y%g"%(y)
		if z is not None: cmd += "Z%g"%(z)
		self.send("%s\n"%(cmd))

	def moveXup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0X%s\n"%(self.step.get()))

	def moveXdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0X-%s\n"%(self.step.get()))

	def moveYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0Y%s\n"%(self.step.get()))

	def moveYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0Y-%s\n"%(self.step.get()))

	def moveXdownYup(self, event=None):
		self.send("G91G0X-%sY%s\n"%(self.step.get(),self.step.get()))

	def moveXupYup(self, event=None):
		self.send("G91G0X%sY%s\n"%(self.step.get(),self.step.get()))

	def moveXdownYdown(self, event=None):
		self.send("G91G0X-%sY-%s\n"%(self.step.get(),self.step.get()))

	def moveXupYdown(self, event=None):
		self.send("G91G0X%sY-%s\n"%(self.step.get(),self.step.get()))

	def moveZup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0Z%s\n"%(self.step.get()))

	def moveZdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.send("G91G0Z-%s\n"%(self.step.get()))

	def go2origin(self, event=None):
		self.send("G90G0X0Y0Z0\n")

	def resetCoords(self, event):
		if not self.running: self.send("G10P0L20X0Y0Z0\n")

	def resetX(self, event):
		if not self.running: self.send("G10P0L20X0\n")

	def resetY(self, event):
		if not self.running: self.send("G10P0L20Y0\n")

	def resetZ(self, event):
		if not self.running: self.send("G10P0L20Z0\n")

	def feedHold(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("!")
		self._pause = False

	def resume(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("~")
		self._pause = True

	def pause(self, event=None):
		if self.serial is None: return
		if self._pause:
			self.feedHold()
		else:
			self.resume()

	#----------------------------------------------------------------------
	def wcsSet(self):
		p = self.wcsvar.get()
		if p<6:
			cmd = "G10L20P%d"%(p+1)
		elif p==6:
			cmd = "G28.1"
		elif p==7:
			cmd = "G30.1"
		elif p==8:
			cmd = "G92"

		for i,x in enumerate((self.wcsX, self.wcsY, self.wcsZ)):
			if x.get() != "":
				cmd += "XYZ"[i] + str(x.get())
				x.delete(0,END)
		self.canvasFocus()
		self.send(cmd+"\n$#\n")

	#----------------------------------------------------------------------
	def tloSet(self):
		cmd = "G43.1Z"+(self._tloin.get())
		self.send(cmd+"\n$#\n")

	#----------------------------------------------------------------------
	def wcsChange(self):
		idx = self.wcsvar.get()
		for i,(x,y,z) in enumerate(self.wcs):
			if i == idx:
				color = "LightYellow"
			else:
				color = "gray95"
			x["background"] = color
			y["background"] = color
			z["background"] = color
		self.send(WCS[idx]+"\n")

	#----------------------------------------------------------------------
	def probeGetMargins(self):
		self.probeXmin.set(str(self.cnc.xmin))
		self.probeXmax.set(str(self.cnc.xmax))
		self.probeYmin.set(str(self.cnc.ymin))
		self.probeYmax.set(str(self.cnc.ymax))
		self.probeChange()

	#----------------------------------------------------------------------
	def probeChange(self, verbose=True):
		probe = self.cnc.probe
		error = False
		try:
			probe.xmin = float(self.probeXmin.get())
			probe.xmax = float(self.probeXmax.get())
			probe.xn   = int(self.probeXbins.get())
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
			probe.yn   = int(self.probeYbins.get())
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
		probe = self.cnc.probe
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
		self.cnc.probe.setZero(x,y)
		self.draw()

	#----------------------------------------------------------------------
	def probeDraw(self):
		self.probeChange(False)
		self.draw()

	#----------------------------------------------------------------------
	def probeClear(self):
		self.cnc.probe.clear()
		self.draw()

	#----------------------------------------------------------------------
	# Probe one Point
	#----------------------------------------------------------------------
	def probeOne(self):
		cmd = "G38.2"
		v = self.probeXdir.get()
		if v != "": cmd += "X"+str(v)
		v = self.probeYdir.get()
		if v != "": cmd += "Y"+str(v)
		v = self.probeZdir.get()
		if v != "": cmd += "Z"+str(v)
		v = self.probeFeed.get()
		if v != "": cmd += "F"+str(v)

		self.queue.put(cmd+"\n")

	#----------------------------------------------------------------------
	# Probe an X-Y area
	#----------------------------------------------------------------------
	def probeScanArea(self):
		if self.probeChange(): return

		if self.serial is None or self.running: return
		probe = self.cnc.probe
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
		self.disable()
		self.emptyQueue()
		self.queue.put(self.cnc.startup+"\n")
		time.sleep(1)

	#----------------------------------------------------------------------
	def run(self):
		if self.serial is None or self.running: return
		if not self.cnc.probe.isEmpty() and not self.cnc.probe.zeroed:
			tkMessageBox.showerror("Probe is not zeroed",
				"Please ZERO any location of the probe before starting a run",
				parent=self)
			return

		self.initRun()
		lines = self.editor.get().splitlines()
		lines = self.cnc.prepare2Run(lines)

		# the buffer of the machine should be empty?
		self._runLines = 0
		del self._runLineMap[:]
		lineno = 0
		for line in lines:
			#print "***",lineno,line
			if line is not None:
				self._runLines += 1
				self._runLineMap.append(lineno)
				if line and line[0]!=' ': lineno += 1	# ignore expanded lines
			else:
				lineno += 1			# count commented lines

		self._gcount   = 0
		self.selectRangeInit()
		self.progress.setLimits(0, self._runLines)

		self.running = True
		for line in lines:
			if line is not None:
				self.queue.put(line+"\n")

	#----------------------------------------------------------------------
	def runEnded(self):
		self._runLines = 0
		self._quit     = 0
		self._pause    = False
		self.running   = False
		self.enable()

	#----------------------------------------------------------------------
	def stopRun(self):
		self.feedHold()
		self.emptyQueue()
		self._runLines = 0
		self._quit     = 0
		self._pause    = False
		self.enable()

	#----------------------------------------------------------------------
	def startPendant(self, showInfo=True):
		CNCPendant.start(self)
		if showInfo:
			tkMessageBox.showinfo("Pendant",
				"Pendant started:\n"\
				"http://%s:8080"%(socket.gethostname()), parent=self)

	#----------------------------------------------------------------------
	def stopPendant(self):
		if CNCPendant.stop():
			tkMessageBox.showinfo("Pendant","Stopped pendant", parent=self)

	#----------------------------------------------------------------------
	# thread performing I/O on serial line
	#----------------------------------------------------------------------
	def serialIO(self):
		# Send one ?
		tosend = None
		t = time.time()
		while self.thread:
			if time.time()-t > SERIAL_POLL:
				self.serial.write("?")
				t = time.time()

			if tosend is None and self.queue.qsize()>0:
				try:
					tosend = self.queue.get_nowait()
					self._cline.append(len(tosend))
					self.log.put((True,tosend))
				except Empty:
					break

			if tosend is None or self.serial.inWaiting():
				line = self.serial.readline().strip()
				if line:
					ch = line[0]
					if ch=="<":
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

					elif ch=="[":
						self.log.put((False, line+"\n"))
						pat = POSPAT.match(line)
						if pat:
							if pat.group(1) == "PRB":
								if self.running:
									self.cnc.probe.add(
										 float(pat.group(2))+self._pos["wx"]-self._pos["mx"],
										 float(pat.group(3))+self._pos["wy"]-self._pos["my"],
										 float(pat.group(4))+self._pos["wz"]-self._pos["mz"])
								self._posUpdate3 = True
							else:
								self._posUpdate2 = True
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

					else:
						self.log.put((False, line+"\n"))
						if line.find("error")>=0 or line.find("ALARM")>=0:
							self._gcount += 1
							if self._cline: del self._cline[0]
							if not self._alarm:
								self._posUpdate = True
							self._alarm = True
							self._pos["state"] = line
							if self.running: self.stopRun()

						elif line.find("ok")>=0:
							self._gcount += 1
							if self._cline: del self._cline[0]

			if tosend is not None and sum(self._cline) <= RX_BUFFER_SIZE-2:
				if isinstance(tosend, unicode):
					self.serial.write(tosend.encode("ascii","replace"))
				else:
					self.serial.write(str(tosend))
				tosend = None

	#----------------------------------------------------------------------
	# thread performing I/O on serial line
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
		if self._posUpdate2:
			for p in range(9):
				g = WCS[p]
				try:
					value = self._pos[g]
					lbl   = self.wcs[p]
					for i in range(3):
						lbl[i]["text"] = value[i]
				except KeyError:
					pass

			self._tlo["text"] = self._pos.get("TLO","")

			try:
				for g in self._pos["G"]:
					try:
						self.wcsvar.set(WCS.index(g))
					except ValueError:
						pass
			except KeyError:
				pass
			self._posUpdate2 = False

		# Update probe and draw point
		if self._posUpdate3:
			try:
				probe = self._pos.get("PRB")
				self._probeX["text"] = probe[0]
				self._probeY["text"] = probe[1]
				self._probeZ["text"] = probe[2]
			except:
				pass
			self.canvas.drawProbePoint(probe)
			self._posUpdate3 = False

		if inserted:
			self.terminal.see(END)
			self.terminal["state"] = DISABLED

		if self.running:
			self.progress.setProgress(self._runLines-self.queue.qsize(),
						self._gcount)

			if self._selectI>=0:
				try:
					self.selectRange(self._runLineMap[self._gcount])
				except IndexError:
					pass

			if self._gcount >= self._runLines:
				self.runEnded()

		self.after(MONITOR_AFTER, self.monitorSerial)

	#----------------------------------------------------------------------
	def get(self, section, item):
		return config.get(section, item)

	#----------------------------------------------------------------------
	def set(self, section, item, value):
		return config.set(section, item, value)

#-----------------------------------------------------------------------------
def loadIcons():
	global icons
	icons = {}
	for img in glob.glob("%s%sicons%s*.gif"%(prgpath,os.sep,os.sep)):
		name,ext = os.path.splitext(os.path.basename(img))
		try:
			icons[name] = PhotoImage(file=img)
		except TclError:
			pass

#-------------------------------------------------------------------------------
def delIcons():
	global icons
	if len(icons) > 0:
		for i in icons.values():
			del i

#------------------------------------------------------------------------------
def loadConfiguration():
	global iniUser, config
	iniSystem = os.path.join(prgpath,"%s.ini"%(__prg__))
	iniUser = os.path.expanduser("~/.%s" % (__prg__))
	config.read([iniSystem, iniUser])
	loadIcons()

#------------------------------------------------------------------------------
def saveConfiguration():
	global iniUser, config
	f = open(iniUser,"w")
	config.write(f)
	f.close()
	delIcons()

#------------------------------------------------------------------------------
def usage():
	sys.exit(0)

#------------------------------------------------------------------------------
if __name__ == "__main__":
	tk = Tk()
	tk.withdraw()

	loadConfiguration()

	try:
		optlist, args = getopt.getopt(sys.argv[1:],
			'?hwp:b:',
			['help', 'pendant', 'port=', 'baud='])
	except getopt.GetoptError:
		usage(1)

	application = Application(tk)
	application.geometry("800x600")
	if len(sys.argv)>1:
		fn,ext = os.path.splitext(sys.argv[1])
		application.loadGcode(sys.argv[1])
		try:
			application.loadProbe(fn+".probe")
		except:
			pass
	try:
		tk.mainloop()
	except KeyboardInterrupt:
		application.quit()

	application.close()
	saveConfiguration()
 #vim:ts=8:sw=8:sts=8:noet
