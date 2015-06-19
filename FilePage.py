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
import CNCRibbon

#===============================================================================
# Recent Menu button
#===============================================================================
class _RecentMenuButton(Ribbon.MenuButton):
	#----------------------------------------------------------------------
	def createMenu(self):
#		rf = [	self.page.loadRecent0,
#			self.page.loadRecent1,
#			self.page.loadRecent2,
#			self.page.loadRecent3,
#			self.page.loadRecent4,
#			self.page.loadRecent5,
#			self.page.loadRecent6,
#			self.page.loadRecent7,
#			self.page.loadRecent8,
#			self.page.loadRecent9 ]
		menu = Menu(self, tearoff=0, activebackground=Ribbon._ACTIVE_COLOR)
		return menu
#		empty = True
#		for i in range(tkFlair._maxRecent):
#			try:
#				filename = tkFlair.config.get(tkFlair.__name__,
#						"recent.%d"%(i))
#				fn = os.path.basename(filename)
#				menu.add_command(label="%d %s"%(i+1, fn),
#					compound=LEFT, image=tkFlair.icons["project"],
#					command=rf[i])
#				empty = False
#			except:
#				pass
#		if empty:
#			self.page.flair.openProject()
#			return None
#		else:
#			return menu

#===============================================================================
# File Page
#===============================================================================
class FilePage(CNCRibbon.Page):
	"""File I/O and configuration"""

	_name_ = "File"
	_icon_ = "new"

	#----------------------------------------------------------------------
	def createRibbon(self):
		CNCRibbon.Page.createRibbon(self)

		# ========== File ===========
		group = Ribbon.LabelGroup(self.ribbon, "File")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["new32"],
				text="New",
				compound=TOP,
#				command=self.openTemplate,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "New gcode/dxf file")

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["open32"],
#				command=self.app.openProject,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Open existing gcode/dxf file [Ctrl-O]")

		col,row=1,2
		b = _RecentMenuButton(group.frame, None,
				text="Open",
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Open recent file")

		# ---
		col,row=2,0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["save32"],
#				command=self.app.saveProject,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Save gcode/dxf file [Ctrl-S]")

		col,row=2,2
		b = Ribbon.LabelButton(group.frame,
				text="Save",
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
#				command=self.app.saveProjectAs,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Save gcode/dxf AS")

		# ==========
		group = Ribbon.LabelGroup(self.ribbon, "Pendant")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		col,row=0,0
		b = Ribbon.LabelButton(group.frame,
				text="Start",
				image=Utils.icons["start"],
				compound=LEFT,
				anchor=W,
				command=self.app.startPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Start pendant")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				text="Stop",
				image=Utils.icons["stop"],
				compound=LEFT,
				anchor=W,
				command=self.app.startPendant,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Stop pendant")

#	FIXME Port or checkbutton to start on start up
#		row += 1
#		b = Ribbon.LabelButton(group.frame,
#				text="Stop",
#				image=Utils.icons["stop"],
#				compound=LEFT,
#				anchor=W,
#				command=self.app.startPendant,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Port")

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ========== Tools ==============
		group = Ribbon.LabelGroup(self.ribbon, "Tools")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(group.frame, #self.page, "<<Config>>",
				text="Config",
				image=Utils.icons["config32"],
#				command=self.app.preferences,
				state=DISABLED,
				compound=TOP,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
		tkExtra.Balloon.set(b, "Open configuration dialog")

		# ===
		col,row=1,0
		b = Ribbon.LabelButton(group.frame,
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
		b = Ribbon.LabelButton(group.frame,
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
		b = Ribbon.LabelButton(group.frame,
				text="About",
				image=Utils.icons["about"],
				compound=LEFT,
				command=self.app.about,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, "About the program")

		# ========== Tools ==============
		group = Ribbon.LabelGroup(self.ribbon, "Close")
		group.pack(side=RIGHT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(group.frame,
				text="Exit",
				image=Utils.icons["exit32"],
				compound=TOP,
				command=self.app.quit,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
		tkExtra.Balloon.set(b, "Close program [Ctrl-Q]")

	#----------------------------------------------------------------------
	# Create Project page
	#----------------------------------------------------------------------
	def createPage(self):
		return
#		CNCRibbon.Page.createPage(self)
#		l = Label(self.page, text="File page")
#		l.pack()
