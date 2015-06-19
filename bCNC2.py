#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

__version__ = "0.4.9"
__date__    = "15 Jun 2015"
__author__  = "Vasilis Vlachoudis"
__email__   = "vvlachoudis@gmail.com"

import os
import re
import sys
import pdb
import math
import time
import serial
import socket

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

from CNC import CNC, GCode
import Utils
import Tools
import Ribbon
import Pendant
from Control import Control, NOT_CONNECTED, STATECOLOR, STATECOLORDEF

import CNCList
import CNCCanvas

from FilePage      import FilePage
from ControlPage   import ControlPage
from TerminalPage  import TerminalPage
from WorkspacePage import WorkspacePage
from ToolsPage     import ToolsPage
from EditorPage    import EditorPage

SERIAL_POLL   = 0.250	# s
G_POLL        = 10	# s
MONITOR_AFTER =  250	# ms
DRAW_AFTER    =  300	# ms

RX_BUFFER_SIZE = 128

MAX_HISTORY  = 500

_LOWSTEP   = 0.0001
_HIGHSTEP  = 1000.0


#ZERO = ["G28", "G30", "G92"]

#==============================================================================
# Main Application window
#==============================================================================
class Application(Toplevel,Control):
	def __init__(self, master, **kw):
		Toplevel.__init__(self, master, **kw)
		Control.__init__(self)

		self.iconbitmap("@%s/bCNC.xbm"%(Utils.prgpath))
		self.title(Utils.__prg__)
		self.widgets = []

		# Global variables
		self.view  = StringVar()
		self.view.set(CNCCanvas.VIEWS[0])
		self.view.trace('w', self.viewChange)
		self.tools = Tools.Tools(self.gcode)
		self.loadConfig()

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

		# --- Ribbon ---
		self.ribbon = Ribbon.TabRibbonFrame(self)
		self.ribbon.pack(side=TOP, fill=X)

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

		# --- Control ---
		panedframe = Frame(paned)
		paned.add(panedframe, minsize=340)

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
		tkExtra.Balloon.set(self.xwork, "X work position")

		# ---
		col += 1
		self.ywork = Label(frame, background="White",anchor=E)
		self.ywork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.ywork, "Y work position")

		# ---
		col += 1
		self.zwork = Label(frame, background="White", anchor=E)
		self.zwork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.zwork, "Z work position")

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

		# progress
		row += 1
		col = 0
		Label(frame,text="Run:").grid(row=row,column=col,sticky=E)
		col += 1
		self.progress = tkExtra.ProgressBar(frame, height=24)
		self.progress.grid(row=row, column=1, columnspan=3, sticky=EW)

		frame.grid_columnconfigure(1, weight=1)
		frame.grid_columnconfigure(2, weight=1)
		frame.grid_columnconfigure(3, weight=1)

		# Tab page set
		pageframe = Frame(panedframe, relief=GROOVE)
		pageframe.pack(fill=BOTH, expand=YES)
		self.ribbon.setPageFrame(pageframe)

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

		# Create Pages
		self._file     = FilePage(self.ribbon, self)
		self._control  = ControlPage(self.ribbon, self)
		self._terminal = TerminalPage(self.ribbon, self)
		self._wcs      = WorkspacePage(self.ribbon, self)
		self._tools    = ToolsPage(self.ribbon, self)
		self._editor   = EditorPage(self.ribbon, self)

		for page in (	self._file,
				self._control,
				self._terminal,
				self._wcs,
				self._tools,
				self._editor):
			self.ribbon.addPage(page)
		self.ribbon.changePage("Control")

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
		self.bind('<<Undo>>',           self.undo)
		self.bind('<<Redo>>',           self.redo)
		self.bind('<<Copy>>',           self.copy)
		self.bind('<<Cut>>',            self.cut)
		self.bind('<<Paste>>',          self.paste)

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

		self.bind('<Up>',		self._control.moveYup)
		self.bind('<Down>',		self._control.moveYdown)
		self.bind('<Right>',		self._control.moveXup)
		self.bind('<Left>',		self._control.moveXdown)
		self.bind('<Prior>',		self._control.moveZup)
		self.bind('<Next>',		self._control.moveZdown)

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
#		self.createToolbar(toolbar)
#		self.createMenu()

		self.canvas.focus_set()

		# Fill basic global variables
		CNC.vars["state"] = NOT_CONNECTED
		CNC.vars["color"] = STATECOLOR[NOT_CONNECTED]
		self._posUpdate  = False
		self._wcsUpdate  = False
		self._probeUpdate= False
		self._gUpdate    = False
		self.running     = False
		self._runLines   = 0
		self._quit       = 0
		self._drawAfter  = None	# after handle for modification
		self._inFocus    = False
		self.monitorSerial()
		self.toggleDrawFlag()

		# Create tools
		self._tools.fill()

		if int(Utils.config.get("Connection","pendant")):
			self.startPendant(False)

		if int(Utils.config.get("Connection","openserial")):
			self.openClose()

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

		# ---
		i += 1
		menu.add_separator()

		# ---
		i += 1
		menu.add_command(label="Statistics", underline=0, command=self.showStats)

		# ---
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

	#----------------------------------------------------------------------
	def quit(self, event=None):
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

		Control.quit(self)
		self.saveConfig()
		self.destroy()
		if Utils.errors and Utils._errorReport:
			Utils.ReportDialog.sendErrorReport()
		Utils.delIcons()
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

		#restore windowsState
		try:
			self.wm_state(Utils.getStr(Utils.__prg__, "windowstate", "normal"))
		except:
			pass

		self.tools.load(Utils.config)

		Control.loadConfig(self)

	#----------------------------------------------------------------------
	def saveConfig(self):
		return

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

		self.tools.save(Utils.config)

		Control.saveConfig(self)

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
	# FIXME Very primitive
	#----------------------------------------------------------------------
	def showStats(self, event=None):
		msg  = "GCode: %s\n"%(self.gcode.filename)
		if not self.gcode.probe.isEmpty():
			msg += "Probe: %s\n"%(self.gcode.probe.filename)
		if CNC.inch:
			unit = "in"
		else:
			unit = "mm"
		msg += "Movement Length: %g %s\n"%(self.cnc.totalLength, unit)
		msg += "Total Time: ~%.2g min\n"%(self.cnc.totalTime)
		tkMessageBox.showinfo("Statistics", msg, parent=self)

	#----------------------------------------------------------------------
	def reportDialog(self, event=None):
		Utils.ReportDialog(self)

	#----------------------------------------------------------------------
	def insertBlock(self):
		self.ribbon.changePage("Editor")
		self.gcodelist.insertBlock()

	#----------------------------------------------------------------------
	def insertLine(self):
		self.ribbon.changePage("Editor")
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
		#print
		#print "<<<",line
		try:
			line = self.evaluate(line)
		except:
			tkMessageBox.showerror("Evaluation error",
				sys.exc_info()[1], parent=self)
			return
		#print ">>>",line

		if line is None: return

		if self.executeGcode(line): return

		oline = line.strip()
		line  = oline.replace(","," ").split()
		cmd   = line[0].upper()

		# ABO*UT: About dialog
		if rexx.abbrev("ABOUT",cmd,3):
			self.about()

		# CLE*AR: clear terminal
		elif rexx.abbrev("CLEAR",cmd,3) or cmd=="CLS":
			self._terminal.clear()

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

		# ECHO <msg>: echo message
		elif cmd=="ECHO":
			self.statusbar["text"] = oline[5:].strip()

		# MSG|MESSAGE <msg>: echo message
		elif cmd in ("MSG","MESSAGE"):
			tkMessageBox.showinfo("Message",oline[oline.find(" ")+1:].strip(), parent=self)

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
		elif rexx.abbrev("LOAD",cmd,2) and len(line)==0:
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
				dx = -(CNC.vars["xmin"] + CNC.vars["xmax"])/2.0
				dy = -(CNC.vars["ymin"] + CNC.vars["ymax"])/2.0
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="BL":
				dx = -CNC.vars["xmin"]
				dy = -CNC.vars["ymin"]
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="BR":
				dx = -CNC.vars["xmax"]
				dy = -CNC.vars["ymin"]
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="TL":
				dx = -CNC.vars["xmin"]
				dy = -CNC.vars["ymax"]
				dz = 0.0
				self.gcodelist.selectAll()
			elif line1=="TR":
				dx = -CNC.vars["xmax"]
				dy = -CNC.vars["ymax"]
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

		# PROF*ILE [offset]: create profile path
		elif rexx.abbrev("PROFILE",cmd,3):
			if len(line)>1:
				self.profile(line[1])
			else:
				self.profile()

		# REV*ERSE: reverse path direction
		elif rexx.abbrev("REVERSE", cmd, 3):
			self.executeOnSelection("REVERSE")

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
			rc = self.executeCommand(oline)
			if rc:
				tkMessageBox.showerror(rc[0],rc[1], parent=self)
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
			gcode = GCode()
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
			self.serial = serial.Serial(device,baudrate,timeout=0.1)
			time.sleep(1)
			CNC.vars["state"] = "Connected"
			CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
			self.state.config(text=CNC.vars["state"],
					background=CNC.vars["color"])
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
		CNC.vars["state"] = NOT_CONNECTED
		CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
		try:
			self.state.config(text=CNC.vars["state"],
					background=CNC.vars["color"])
		except TclError:
			pass


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
		self.probeXmin.set(str(CNC.vars["xmin"]))
		self.probeXmax.set(str(CNC.vars["xmax"]))
		self.probeYmin.set(str(CNC.vars["ymin"]))
		self.probeYmax.set(str(CNC.vars["ymax"]))
		self.probeChange()

	#----------------------------------------------------------------------
	def probeChange(self, verbose=True):
		return
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
		x = CNC.vars["wx"]
		y = CNC.vars["wy"]
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
				if isinstance(line,str):
					self.queue.put(line+"\n")
				else:
					self.queue.put(line)

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
		time.sleep(1);
		self.softReset()
		self.emptyQueue()
		self._runLines = 0
		self._quit     = 0
		self._pause    = False
		self.enable()

	#----------------------------------------------------------------------
	# Start the web pendant
	#----------------------------------------------------------------------
	def startPendant(self, showInfo=True):
		started=Pendant.start(self)
		if showInfo:
			hostName="http://%s:%d"%(socket.gethostname(),Pendant.port)
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
		if Pendant.stop():
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

			if tosend is None and not self.wait and self.queue.qsize()>0:
				try:
					tosend = self.queue.get_nowait()
					if isinstance(tosend, int):
						if tosend == WAIT: # wait to empty the grbl buffer
							self.wait = True
						tosend = None
					elif not isinstance(tosend, str):
						try:
							tosend = self.gcode.evaluate(tosend)
#							if isinstance(tosend, list):
#								cline.append(len(tosend[0]))
#								self.log.put((True,tosend[0]))
							if isinstance(tosend,str):
								tosend += "\n"
							else:
								# Count commands as well
								self._gcount += 1
						except:
							self.log.put((True,sys.exc_info()[1]))
							tosend = None
					if tosend is not None:
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
								CNC.vars["state"] = pat.group(1)
							CNC.vars["mx"] = float(pat.group(2))
							CNC.vars["my"] = float(pat.group(3))
							CNC.vars["mz"] = float(pat.group(4))
							CNC.vars["wx"] = float(pat.group(5))
							CNC.vars["wy"] = float(pat.group(6))
							CNC.vars["wz"] = float(pat.group(7))
							self._posUpdate = True
						else:
							self.log.put((False, line+"\n"))

					elif line[0]=="[":
						self.log.put((False, line+"\n"))
						pat = POSPAT.match(line)
						if pat:
							if pat.group(1) == "PRB":
								CNC.vars["prbx"] = float(pat.group(2))
								CNC.vars["prby"] = float(pat.group(3))
								CNC.vars["prbz"] = float(pat.group(4))
								if self.running:
									self.gcode.probe.add(
										 float(pat.group(2))
											+CNC.vars["wx"]
											-CNC.vars["mx"],
										 float(pat.group(3))
											+CNC.vars["wy"]
											-CNC.vars["my"],
										 float(pat.group(4))
											+CNC.vars["wz"]
											-CNC.vars["mz"])
								self._probeUpdate = True
							else:
								self._wcsUpdate = True
							CNC.vars[pat.group(1)] = \
								[float(pat.group(2)),
								 float(pat.group(3)),
								 float(pat.group(4))]
						else:
							pat = TLOPAT.match(line)
							if pat:
								CNC.vars[pat.group(1)] = pat.group(2)
							else:
								CNC.vars["G"] = line[1:-1].split()
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
							CNC.vars["state"] = line
							if self.running: self.stopRun()

						elif line.find("ok")>=0:
							self._gcount += 1
							if cline: del cline[0]

						if self.wait and not cline:
							# buffer is empty go one
							self._gcount += 1
							self.wait = False

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
					self._terminal.terminal["state"] = NORMAL
					inserted = True
				if io:
					self._terminal.terminal.insert(END, line, "SEND")
				else:
					self._terminal.terminal.insert(END, line)
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
			state = CNC.vars["state"]
			self.state["text"] = state
			try:
				CNC.vars["color"] = STATECOLOR[state]
			except KeyError:
				if self._alarm:
					CNC.vars["color"] = STATECOLOR["Alarm"]
				else:
					CNC.vars["color"] = STATECOLORDEF
			if state == "Hold": self._pause = True

			self.state["background"] = CNC.vars["color"]

			self.xwork["text"] = CNC.vars["wx"]
			self.ywork["text"] = CNC.vars["wy"]
			self.zwork["text"] = CNC.vars["wz"]

			self.xmachine["text"] = CNC.vars["mx"]
			self.ymachine["text"] = CNC.vars["my"]
			self.zmachine["text"] = CNC.vars["mz"]

			self.canvas.gantry(CNC.vars["wx"],
					   CNC.vars["wy"],
					   CNC.vars["wz"],
					   CNC.vars["mx"],
					   CNC.vars["my"],
					   CNC.vars["mz"])
			self._posUpdate = False

		# Update parameters if needed
		if self._wcsUpdate:
			try:
				value = CNC.vars[WCS[self.wcsvar.get()]]
				for i in range(3):
					self.wcs[i]["text"] = value[i]
			except KeyError:
				pass

			self._tlo["text"] = CNC.vars.get("TLO","")
			self._wcsUpdate = False

		# Update status string
		if self._gUpdate:
			for g in CNC.vars["G"]:
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
				probe = CNC.vars.get("PRB")
				self._probeX["text"] = probe[0]
				self._probeY["text"] = probe[1]
				self._probeZ["text"] = probe[2]
			except:
				pass
			self.canvas.drawProbePoint(probe)
			self._probeUpdate = False

		if inserted:
			self._terminal.terminal.see(END)
			self._terminal.terminal["state"] = DISABLED

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
 #vim:ts=8:sw=8:sts=8:noet
