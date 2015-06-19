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

import Tools
import Utils
import Ribbon
import CNCRibbon

#===============================================================================
# Tools Page
#===============================================================================
class ToolsPage(CNCRibbon.Page):
	"""GCode manipulation tools and user plugins"""

	_name_ = "Tools"
	_icon_ = "tools"

	#----------------------------------------------------------------------
	def createRibbon(self):
		CNCRibbon.Page.createRibbon(self)

		# ========== Project ===========
		group = Ribbon.LabelGroup(self.ribbon, "Control")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(group.frame,
#				image=tkFlair.icons["newflair32"],
#				#command=self.flair.newProject,
#				command=self.openTemplate,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "New project with the basic template as input")
#
#		col,row=0,2
#		b = Ribbon._TemplateMenuButton(group.frame, self,
#				text="New",
#				image=tkFlair.icons["triangle_down"],
#				compound=RIGHT,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "New project + input from template")
#
#		# ---
#		col,row=1,0
#		b = Ribbon.LabelButton(group.frame,
#				image=tkFlair.icons["openflair32"],
#				command=self.flair.openProject,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Open project")
#
#		col,row=1,2
#		b = _RecentMenuButton(group.frame, self,
#				text="Open",
#				image=tkFlair.icons["triangle_down"],
#				compound=RIGHT,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Open recent project")
#
#		# ---
#		col,row=2,0
#		b = Ribbon.LabelButton(group.frame,
#				image=tkFlair.icons["saveflair32"],
#				command=self.flair.saveProject,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Save project")
#
#		col,row=2,2
#		b = Ribbon.LabelButton(group.frame,
#				text="Save",
#				image=tkFlair.icons["triangle_down"],
#				compound=RIGHT,
#				command=self.flair.saveProjectAs,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Save project as")
#
#		# ========== Edit ==============
#		group = _EditGroup(self.ribbon, self, "Edit")
#		group.pack(side=LEFT, fill=Y, padx=0, pady=0)
#
#		group.frame.grid_rowconfigure(0, weight=1)
#		group.frame.grid_rowconfigure(1, weight=1)
#		group.frame.grid_rowconfigure(2, weight=1)
#
#		col,row = 0,0
#		self.styleCombo = Ribbon.LabelCombobox(group.frame,
#					width=12,
#					command=self.setStyleFromCombo)
#		self.styleCombo.grid(row=row, column=col, columnspan=5, padx=0, pady=0, sticky=EW)
#		tkExtra.Balloon.set(self.styleCombo, "Set editing style")
#		self.styleCombo.fill(self.notes.styleList())
#
#		# ---
#		col,row = 0,1
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["alignleft"],
#				variable=self._style,
#				value="Left")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Align left text")
#
#		# ---
#		col,row = 1,1
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["aligncenter"],
#				variable=self._style,
#				value="Center")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Align center text")
#
#		# ---
#		col,row = 2,1
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["alignright"],
#				variable=self._style,
#				value="Right")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Align right text")
#
#		# ---
#		col,row = 3,1
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["hyperlink"],
#				variable=self._style,
#				value="Link")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Bold font [Ctrl-B]")
#
#		# ---
#		col,row = 4,1
#		b = Ribbon.LabelButton(group.frame,
#				image=tkFlair.icons["image"],
#				command=self.insertImage,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Insert image")
#
#		# ---
#		col,row = 0,2
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["bold"],
#				variable=self._style,
#				value="Bold")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Bold font [Ctrl-B]")
#
#		# ---
#		col,row = 1,2
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["italic"],
#				variable=self._style,
#				value="Italic")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Italics font [Ctrl-I]")
#
#		# ---
#		col,row = 2,2
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["underline"],
#				variable=self._style,
#				value="Underline")
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Underline font [Ctrl-U]")
#
#		# ---
#		col,row = 3,2
#		b = Ribbon.LabelRadiobutton(group.frame,
#				image=tkFlair.icons["overstrike"],
#				variable=self._style,
#				value="Overstrike")
#		b.grid(row=row,  column=col, padx=0, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, "Overstrike font [Ctrl-O]")
#
#		# ========== Publish ==============
#		group = Ribbon.LabelGroup(self.ribbon, "Publish")
#		group.pack(side=LEFT, fill=Y, padx=0, pady=0)
#
#		group.frame.grid_rowconfigure(0, weight=1)
#		group.frame.grid_rowconfigure(1, weight=1)
#		group.frame.grid_rowconfigure(2, weight=1)
#
#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(group.frame, self.page, "<<Document>>",
#				text="Document",
#				image=tkFlair.icons["new32"],
#				#anchor=S,
#				compound=TOP,
#				state=DISABLED,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, "Create document from project")
#
#		# ---
#		col,row=1,0
#		b = Ribbon.LabelButton(group.frame,
#				text="Print",
#				command=self.hardcopy,
#				image=tkFlair.icons["print32"],
#				compound=TOP,
#				#anchor=S,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, "Print input")
#
#		# ---
#		col,row=2,0
#		b = Ribbon.LabelButton(group.frame,
#				text="Refresh",
#				command=self.refreshButton,
#				image=tkFlair.icons["refresh32"],
#				compound=TOP,
#				#anchor=S,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, "Refresh document")
#
#		# ========== Tools ==============
#		group = Ribbon.LabelGroup(self.ribbon, "Tools")
#		group.pack(side=LEFT, fill=Y, padx=0, pady=0)
#
#		group.frame.grid_rowconfigure(0, weight=1)
#		group.frame.grid_rowconfigure(1, weight=1)
#		group.frame.grid_rowconfigure(2, weight=1)
#
#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(group.frame, #self.page, "<<Config>>",
#				text="Config",
#				image=tkFlair.icons["config32"],
#				command=self.flair.preferences,
#				compound=TOP,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NS)
#		tkExtra.Balloon.set(b, "Open configuration dialog")
#
#		# ===
#		col,row=1,0
#		b = Ribbon.LabelButton(group.frame,
#				text="Report",
#				image=tkFlair.icons["debug"],
#				compound=LEFT,
#				command=tkFlair.ReportDialog.sendErrorReport,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
#		tkExtra.Balloon.set(b, "Send Error Report")
#
#		# ---
#		col,row=1,1
#		b = Ribbon.LabelButton(group.frame,
#				text="Updates",
#				image=tkFlair.icons["GLOBAL"],
#				compound=LEFT,
#				command=self.flair.checkUpdates,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
#		tkExtra.Balloon.set(b, "Check Updates")
#
#		col,row=1,2
#		b = Ribbon.LabelButton(group.frame,
#				text="About",
#				image=tkFlair.icons["about"],
#				compound=LEFT,
#				command=lambda s=self: tkFlair.aboutDialog(s.page),
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
#		tkExtra.Balloon.set(b, "About flair")
#
#		# ========== Tools ==============
#		group = Ribbon.LabelGroup(self.ribbon, "Close")
#		group.pack(side=RIGHT, fill=Y, padx=0, pady=0)
#
#		group.frame.grid_rowconfigure(0, weight=1)
#
#		# ---
#		col,row=0,0
#		b = Ribbon.LabelButton(group.frame,
#				text="Exit",
#				image=tkFlair.icons["exit32"],
#				compound=TOP,
#				command=self.flair.quit,
#				anchor=W,
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
#		tkExtra.Balloon.set(b, "Close program")

	#----------------------------------------------------------------------
	# Create Project page
	#----------------------------------------------------------------------
	def createPage(self):
		CNCRibbon.Page.createPage(self)

		self.toolFrame = Tools.ToolFrame(self.page, self.app, self.app.tools)
		self.toolFrame.pack(fill=BOTH, expand=YES)


	#----------------------------------------------------------------------
	def fill(self):
		# Create tools
		self.toolFrame.fill()
		try:
			self.toolFrame.set(Utils.config.get(Utils.__prg__, "tool"))
		except:
			self.toolFrame.set("Box")
