#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import os

try:
	from Tkinter import *
	import ConfigParser
except ImportError:
	from tkinter import *
	import configparser as ConfigParser

import tkExtra

import Utils
import Ribbon
import CNCRibbon

#try:
#	from serial.tools.list_ports import comports
#except:
from Utils import comports

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200]

#===============================================================================
# Recent Menu button
#===============================================================================
class _RecentMenuButton(Ribbon.MenuButton):
	#----------------------------------------------------------------------
	def createMenu(self):
		menu = Menu(self, tearoff=0, activebackground=Ribbon._ACTIVE_COLOR)
		for i in range(Utils._maxRecent):
			filename = Utils.getRecent(i)
			if filename is None: break
			fn = os.path.basename(filename)
			menu.add_command(label="%d %s"%(i+1, fn),
				compound=LEFT,
				image=Utils.icons["new"],
				command=lambda s=self,i=i: s.event_generate("<<Recent%d>>"%(i)))
		if i==0: # no entry
			self.event_generate("<<Open>>")
			return None
		return menu

#===============================================================================
# File Group
#===============================================================================
class FileGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "File", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<<New>>",
				image=Utils.icons["new32"],
				text="New",
				compound=TOP,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "New gcode/dxf file")
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame, self, "<<Open>>",
				image=Utils.icons["open32"],
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Open existing gcode/dxf file [Ctrl-O]")
		self.addWidget(b)

		col,row=1,2
		b = _RecentMenuButton(self.frame, None,
				text="Open",
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Open recent file")
		self.addWidget(b)

		# ---
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, self, "<<Save>>",
				image=Utils.icons["save32"],
				command=app.save,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Save gcode/dxf file [Ctrl-S]")
		self.addWidget(b)

		col,row=2,2
		b = Ribbon.LabelButton(self.frame, self, "<<SaveAs>>",
				text="Save",
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Save gcode/dxf AS")
		self.addWidget(b)

#===============================================================================
# Options Group
#===============================================================================
class OptionsGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Options", app)
		self.grid3rows()

#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(self.frame, #self.page, "<<Config>>",
#				text="Config",
#				image=Utils.icons["config32"],
##				command=self.app.preferences,
#				state=DISABLED,
#				compound=TOP,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, "Open configuration dialog")

		# ===
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				text="Report",
				image=Utils.icons["debug"],
				compound=LEFT,
				command=Utils.ReportDialog.sendErrorReport,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, "Send Error Report")

		# ---
		col,row=1,1
		b = Ribbon.LabelButton(self.frame,
				text="Updates",
				image=Utils.icons["global"],
				compound=LEFT,
				state=DISABLED,
#				command=self.app.checkUpdates,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, "Check Updates")

		col,row=1,2
		b = Ribbon.LabelButton(self.frame,
				text="About",
				image=Utils.icons["about"],
				compound=LEFT,
				command=self.app.about,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, "About the program")

#===============================================================================
# Pendant Group
#===============================================================================
class PendantGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Pendant", app)
		self.grid3rows()

		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				text="Start",
				image=Utils.icons["start"],
				compound=LEFT,
				anchor=W,
				command=app.startPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Start pendant")

		row += 1
		b = Ribbon.LabelButton(self.frame,
				text="Stop",
				image=Utils.icons["stop"],
				compound=LEFT,
				anchor=W,
				command=app.stopPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Stop pendant")

#===============================================================================
# Close Group
#===============================================================================
class CloseGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Close", app)

		# ---
		b = Ribbon.LabelButton(self.frame,
				text="Exit",
				image=Utils.icons["exit32"],
				compound=TOP,
				command=app.quit,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		tkExtra.Balloon.set(b, "Close program [Ctrl-Q]")

#===============================================================================
# Serial Frame
#===============================================================================
class SerialFrame(CNCRibbon.PageLabelFrame):
	def __init__(self, master, app):
		CNCRibbon.PageLabelFrame.__init__(self, master, "Serial", app)

		self.autostart = BooleanVar()

		# ---
		col,row=0,0
		b = Label(self, text="Port:", background=Ribbon._BACKGROUND)
		b.grid(row=row,column=col,sticky=E)
		self.addWidget(b)

		self.portCombo = tkExtra.Combobox(self, False, background="White", width=16)
		self.portCombo.grid(row=row, column=col+1, sticky=EW)
		tkExtra.Balloon.set(self.portCombo, "Select (or manual enter) port to connect")
#		sys.stdout.write(comports())
		devices = sorted([x[0] for x in comports()])
		self.portCombo.fill(devices)
		self.portCombo.set(Utils.getStr("Connection","port"))
		self.addWidget(self.portCombo)

		# ---
		row += 1
		b = Label(self, text="Baud:", background=Ribbon._BACKGROUND)
		b.grid(row=row,column=col,sticky=E)

		self.baudCombo = tkExtra.Combobox(self, True, background="White")
		self.baudCombo.grid(row=row, column=col+1, sticky=EW)
		tkExtra.Balloon.set(self.baudCombo, "Select connection baud rate")
		self.baudCombo.fill(BAUDS)
		self.baudCombo.set(Utils.getStr("Connection","baud","115200"))
		self.addWidget(self.baudCombo)

		# ---
		row += 1
		b= Checkbutton(self,	text="Connect on startup",
					variable=self.autostart)
		b.grid(row=row, column=col, columnspan=2, sticky=W)
		tkExtra.Balloon.set(b, "Connect to serial on startup of the program")
		self.autostart.set(Utils.getBool("Connection","openserial"))
		self.addWidget(b)

		# ---
		col += 2
		row  = 0

		self.connectBtn = Ribbon.LabelButton(self,
				image=Utils.icons["serial32"],
				text="Open",
				compound=TOP,
				command=lambda s=self : s.event_generate("<<Connect>>"),
				background=Ribbon._BACKGROUND)
		self.connectBtn.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(self.connectBtn, "Open/Close serial port")
		self.grid_columnconfigure(1, weight=1)

	#-----------------------------------------------------------------------
	def saveConfig(self):
		# Connection
		Utils.setStr("Connection", "port",        self.portCombo.get())
		Utils.setStr("Connection", "baud",        self.baudCombo.get())
		Utils.setBool("Connection", "openserial", self.autostart.get())

#===============================================================================
# File Page
#===============================================================================
class FilePage(CNCRibbon.Page):
	"""File I/O and configuration"""
	_name_ = "File"
	_icon_ = "new"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((FileGroup, PendantGroup, OptionsGroup, CloseGroup),
			(SerialFrame,))
