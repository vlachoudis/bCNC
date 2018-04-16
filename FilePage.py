# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import os

try:
	from Tkinter import *
except ImportError:
	from tkinter import *

import tkExtra

import Utils
import Ribbon
import CNCRibbon

try:
	from serial.tools.list_ports import comports
except:
	from Utils import comports

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]

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
			path = os.path.dirname(filename)
			fn   = os.path.basename(filename)
			menu.add_command(label="%d %s"%(i+1, fn),
				compound=LEFT,
				image=Utils.icons["new"],
				accelerator=path, # Show as accelerator in order to be aligned
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
		CNCRibbon.ButtonGroup.__init__(self, master, N_("File"), app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<<New>>",
				image=Utils.icons["new32"],
				text=_("New"),
				compound=TOP,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("New gcode/dxf file"))
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame, self, "<<Open>>",
				image=Utils.icons["open32"],
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Open existing gcode/dxf file [Ctrl-O]"))
		self.addWidget(b)

		col,row=1,2
		b = _RecentMenuButton(self.frame, None,
				text=_("Open"),
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Open recent file"))
		self.addWidget(b)

		# ---
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, self, "<<Save>>",
				image=Utils.icons["save32"],
				command=app.save,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Save gcode/dxf file [Ctrl-S]"))
		self.addWidget(b)

		col,row=2,2
		b = Ribbon.LabelButton(self.frame, self, "<<SaveAs>>",
				text=_("Save"),
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Save gcode/dxf AS"))
		self.addWidget(b)

#===============================================================================
# Options Group
#===============================================================================
class OptionsGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Options"), app)
		self.grid3rows()

#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(self.frame, #self.page, "<<Config>>",
#				text=_("Config"),
#				image=Utils.icons["config32"],
##				command=self.app.preferences,
#				state=DISABLED,
#				compound=TOP,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, _("Open configuration dialog"))

		# ===
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				text=_("Report"),
				image=Utils.icons["debug"],
				compound=LEFT,
				command=Utils.ReportDialog.sendErrorReport,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, _("Send Error Report"))

		# ---
		col,row=1,1
		b = Ribbon.LabelButton(self.frame,
				text=_("Updates"),
				image=Utils.icons["global"],
				compound=LEFT,
				command=self.app.checkUpdates,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, _("Check Updates"))

		col,row=1,2
		b = Ribbon.LabelButton(self.frame,
				text=_("About"),
				image=Utils.icons["about"],
				compound=LEFT,
				command=self.app.about,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, _("About the program"))

#===============================================================================
# Pendant Group
#===============================================================================
class PendantGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Pendant"), app)
		self.grid3rows()

		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				text=_("Start"),
				image=Utils.icons["startPendant"],
				compound=LEFT,
				anchor=W,
				command=app.startPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Start pendant"))

		row += 1
		b = Ribbon.LabelButton(self.frame,
				text=_("Stop"),
				image=Utils.icons["stopPendant"],
				compound=LEFT,
				anchor=W,
				command=app.stopPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Stop pendant"))

#===============================================================================
# Close Group
#===============================================================================
class CloseGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Close"), app)

		# ---
		b = Ribbon.LabelButton(self.frame,
				text=_("Exit"),
				image=Utils.icons["exit32"],
				compound=TOP,
				command=app.quit,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		tkExtra.Balloon.set(b, _("Close program [Ctrl-Q]"))

#===============================================================================
# Serial Frame
#===============================================================================
class SerialFrame(CNCRibbon.PageLabelFrame):
	def __init__(self, master, app):
		CNCRibbon.PageLabelFrame.__init__(self, master, "Serial", app)

		self.autostart = BooleanVar()

		# ---
		col,row=0,0
		b = Label(self, text=_("Port:"))
		b.grid(row=row,column=col,sticky=E)
		self.addWidget(b)

		self.portCombo = tkExtra.Combobox(self, False, background="White", width=16)
		self.portCombo.grid(row=row, column=col+1, sticky=EW)
		tkExtra.Balloon.set(self.portCombo, _("Select (or manual enter) port to connect"))
#		sys.stdout.write(comports())
		devices = sorted([x[0] for x in comports()])
		self.portCombo.fill(devices)
		self.portCombo.set(Utils.getStr("Connection","port"))
		self.addWidget(self.portCombo)

		# ---
		row += 1
		b = Label(self, text=_("Baud:"))
		b.grid(row=row,column=col,sticky=E)

		self.baudCombo = tkExtra.Combobox(self, True, background="White")
		self.baudCombo.grid(row=row, column=col+1, sticky=EW)
		tkExtra.Balloon.set(self.baudCombo, _("Select connection baud rate"))
		self.baudCombo.fill(BAUDS)
		self.baudCombo.set(Utils.getStr("Connection","baud","115200"))
		self.addWidget(self.baudCombo)

		# ---
		row += 1
		b = Label(self, text=_("Controller:"))
		b.grid(row=row,column=col,sticky=E)

		self.ctrlCombo = tkExtra.Combobox(self, True,
					background="White",
					command=self.ctrlChange)
		self.ctrlCombo.grid(row=row, column=col+1, sticky=EW)
		tkExtra.Balloon.set(self.ctrlCombo, _("Select controller board"))
		self.ctrlCombo.fill(sorted(Utils.CONTROLLER.keys()))
		self.ctrlCombo.set(Utils.controllerName(app.controller))
		self.addWidget(self.ctrlCombo)

		# ---
		row += 1
		b= Checkbutton(self, text=_("Connect on startup"),
					variable=self.autostart)
		b.grid(row=row, column=col, columnspan=2, sticky=W)
		tkExtra.Balloon.set(b, _("Connect to serial on startup of the program"))
		self.autostart.set(Utils.getBool("Connection","openserial"))
		self.addWidget(b)

		# ---
		col += 2
		row  = 0

		self.connectBtn = Ribbon.LabelButton(self,
				image=Utils.icons["serial32"],
				text=_("Open"),
				compound=TOP,
				command=lambda s=self : s.event_generate("<<Connect>>"),
				background=Ribbon._BACKGROUND)
		self.connectBtn.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(self.connectBtn, _("Open/Close serial port"))
		self.grid_columnconfigure(1, weight=1)

	#-----------------------------------------------------------------------
	def ctrlChange(self):
		self.app.controller = Utils.CONTROLLER.get(self.ctrlCombo.get(), 0)

	#-----------------------------------------------------------------------
	def saveConfig(self):
		# Connection
		Utils.setStr("Connection", "controller",  Utils.controllerName(self.app.controller))
		Utils.setStr("Connection", "port",        self.portCombo.get())
		Utils.setStr("Connection", "baud",        self.baudCombo.get())
		Utils.setBool("Connection", "openserial", self.autostart.get())

#===============================================================================
# File Page
#===============================================================================
class FilePage(CNCRibbon.Page):
	__doc__ = _("File I/O and configuration")
	_name_  = N_("File")
	_icon_  = "new"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((FileGroup, PendantGroup, OptionsGroup, CloseGroup),
			(SerialFrame,))
