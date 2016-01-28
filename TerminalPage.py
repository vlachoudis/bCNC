# -*- coding: ascii -*-
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
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Terminal"), app)

		b = Ribbon.LabelButton(self.frame, self, "<<TerminalClear>>",
				image=Utils.icons["clean32"],
				text=_("Clear"),
				compound=TOP,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		tkExtra.Balloon.set(b, _("Clear terminal"))

#===============================================================================
# Commands Group
#===============================================================================
class CommandsGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("Commands"), app,
			[(_("Restore Settings"),  "grbl_settings",  app.grblRestoreSettings),
			 (_("Restore Workspace"), "grbl_params",    app.grblRestoreWCS),
			 (_("Restore All"),       "reset",          app.grblRestoreAll),
			])
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_settings"],
				text=_("Settings"),
				compound=LEFT,
				anchor=W,
				#state=app.controller==Utils.GRBL and NORMAL or DISABLED,
				command=self.app.viewSettings,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$$ Display settings of Grbl"))
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_params"],
				text=_("Parameters"),
				compound=LEFT,
				anchor=W,
				command=self.app.viewParameters,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$# Display parameters of Grbl"))
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_state"],
				text=_("State"),
				compound=LEFT,
				anchor=W,
				command=self.app.viewState,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$G Display state of Grbl"))
		self.addWidget(b)

		# ---
		col += 1
		row  = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_build"],
				text=_("Build"),
				compound=LEFT,
				anchor=W,
				command=self.app.viewBuild,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$I Display build information of Grbl"))
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_startup"],
				text=_("Startup"),
				compound=LEFT,
				anchor=W,
				command=self.app.viewStartup,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$N Display startup configuration of Grbl"))
		self.addWidget(b)

		row += 1
		# FIXME Checkbutton!!!!!
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_check"],
				text=_("Check gcode"),
				compound=LEFT,
				anchor=W,
				command=self.app.checkGcode,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$C Enable/Disable checking of gcode"))
		self.addWidget(b)

		# ---
		col += 1
		row  = 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["grbl_help"],
				text=_("Help"),
				compound=LEFT,
				anchor=W,
				command=self.app.grblHelp,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("$ Display build information of Grbl"))
		self.addWidget(b)

#===============================================================================
class TerminalFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, N_("Terminal"), app)
		self.terminal = Text(self,
					background="White",
					width=20,
					height=3,
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

	#----------------------------------------------------------------------
	def copy(self, event=None):
		return "break"

#===============================================================================
# Terminal Page
#===============================================================================
class TerminalPage(CNCRibbon.Page):
	__doc__ = _("Serial Terminal")
	_name_  = "Terminal"
	_icon_  = "terminal"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((CommandsGroup,TerminalGroup),
				(TerminalFrame,))
