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
# Terminal Page
#===============================================================================
class TerminalPage(CNCRibbon.Page):
	_name_ = "Terminal"
	_icon_ = "terminal"

	#----------------------------------------------------------------------
	def createRibbon(self):
		CNCRibbon.Page.createRibbon(self)

		# ========== Project ===========
		group = Ribbon.LabelGroup(self.ribbon, "Grbl")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_settings"],
				text="Settings",
				compound=LEFT,
				anchor=W,
				command=self.app.viewSettings,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$$ Display settings of Grbl")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_params"],
				text="Parameters",
				compound=LEFT,
				anchor=W,
				command=self.app.viewParameters,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$# Display parameters of Grbl")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_state"],
				text="State",
				compound=LEFT,
				anchor=W,
				command=self.app.viewState,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$G Display state of Grbl")

		# ---
		col += 1
		row  = 0
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_build"],
				text="Build",
				compound=LEFT,
				anchor=W,
				command=self.app.viewBuild,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$I Display build information of Grbl")

		row += 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_startup"],
				text="Startup",
				compound=LEFT,
				anchor=W,
				command=self.app.viewStartup,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$N Display startup configuration of Grbl")

		row += 1
		# FIXME Checkbutton!!!!!
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_check"],
				text="Check gcode",
				compound=LEFT,
				anchor=W,
				command=self.app.checkGcode,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$C Enable/Disable checking of gcode")

		# ---
		col += 1
		row  = 1
		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["grbl_help"],
				text="Help",
				compound=LEFT,
				anchor=W,
				command=self.app.grblhelp,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "$ Display build information of Grbl")

		# ========== Terminal ===========
		group = Ribbon.LabelGroup(self.ribbon, "Term")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		b = Ribbon.LabelButton(group.frame,
				image=Utils.icons["clean32"],
				text="Clear",
				compound=TOP,
				command=self.clear,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Clear terminal")

	#----------------------------------------------------------------------
	# Create Project page
	#----------------------------------------------------------------------
	def createPage(self):
		CNCRibbon.Page.createPage(self)

		self.terminal = Text(self.page,
					background="White",
					width=20,
					wrap=NONE,
					state=DISABLED)
		self.terminal.pack(side=LEFT, fill=BOTH, expand=YES)
		sb = Scrollbar(self.page, orient=VERTICAL, command=self.terminal.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.terminal.config(yscrollcommand=sb.set)
		self.terminal.tag_config("SEND",  foreground="Blue")
		self.terminal.tag_config("ERROR", foreground="Red")

	#----------------------------------------------------------------------
	def clear(self):
		self.terminal["state"] = NORMAL
		self.terminal.delete("1.0",END)
		self.terminal["state"] = DISABLED
