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
# Terminal Group
#===============================================================================
class TerminalGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Terminal", app)

		b = Ribbon.LabelButton(self.frame, self, "<<TerminalClear>>",
				image=Utils.icons["clean32"],
				text="Clear",
				compound=TOP,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		tkExtra.Balloon.set(b, "Clear terminal")

#===============================================================================
# Commands Group
#===============================================================================
class CommandsGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Commands", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_settings"],
				text="Settings",
				compound=LEFT,
				anchor=W,
				command=self.app.viewSettings,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$$ Display settings of Grbl")
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_params"],
				text="Parameters",
				compound=LEFT,
				anchor=W,
				command=self.app.viewParameters,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$# Display parameters of Grbl")
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_state"],
				text="State",
				compound=LEFT,
				anchor=W,
				command=self.app.viewState,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$G Display state of Grbl")
		self.addWidget(b)

		# ---
		col += 1
		row  = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_build"],
				text="Build",
				compound=LEFT,
				anchor=W,
				command=self.app.viewBuild,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$I Display build information of Grbl")
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_startup"],
				text="Startup",
				compound=LEFT,
				anchor=W,
				command=self.app.viewStartup,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$N Display startup configuration of Grbl")
		self.addWidget(b)

		row += 1
		# FIXME Checkbutton!!!!!
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_check"],
				text="Check gcode",
				compound=LEFT,
				anchor=W,
				command=self.app.checkGcode,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$C Enable/Disable checking of gcode")
		self.addWidget(b)

		# ---
		col += 1
		row  = 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_help"],
				text="Help",
				compound=LEFT,
				anchor=W,
				command=self.app.grblhelp,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$ Display build information of Grbl")
		self.addWidget(b)

#===============================================================================
class TerminalFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Terminal", app)
		self.terminal = Text(self,
					background="White",
					width=20,
					wrap=NONE,
					state=DISABLED)
		self.terminal.pack(side=LEFT, fill=BOTH, expand=YES)
		sb = Scrollbar(self, orient=VERTICAL, command=self.terminal.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.terminal.config(yscrollcommand=sb.set)
		self.terminal.tag_config("SEND",  foreground="Blue")
		self.terminal.tag_config("ERROR", foreground="Red")

	#----------------------------------------------------------------------
	def clear(self, event=None):
		self.terminal["state"] = NORMAL
		self.terminal.delete("1.0",END)
		self.terminal["state"] = DISABLED

#===============================================================================
# Terminal Page
#===============================================================================
class TerminalPage(CNCRibbon.Page):
	_name_ = "Terminal"
	_icon_ = "terminal"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((CommandsGroup,TerminalGroup),
				(TerminalFrame,))
