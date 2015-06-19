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

WCS  = ["G54", "G55", "G56", "G57", "G58", "G59"]

#===============================================================================
# Workspace Page
#===============================================================================
class WorkspacePage(CNCRibbon.Page):
	"""Workspace configuration and probing"""

	_name_ = "Workspace"
	_icon_ = "measure"

	#----------------------------------------------------------------------
	def createRibbon(self):
		CNCRibbon.Page.createRibbon(self)

		# ==========
		group = Ribbon.LabelGroup(self.ribbon, "WCS")
		group.pack(side=LEFT, fill=Y, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)
		group.frame.grid_rowconfigure(2, weight=1)

		# ==========
		group = Ribbon.LabelGroup(self.ribbon, "Probe")
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

		# WorkSpace -> WPS
		lframe = LabelFrame(self.page, text="WCS", foreground="DarkBlue")
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
					command=self.app.wcsChange)
			b.grid(row=row, column=col,  sticky=NSEW)
			self.addWidget(b)
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
		self.wcsX.bind("<Return>",   self.app.wcsSet)
		self.wcsX.bind("<KP_Enter>", self.app.wcsSet)
		self.addWidget(self.wcsX)

		col += 1
		self.wcsY = tkExtra.FloatEntry(lframe, background="White")
		self.wcsY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsY, "If not empty set the Y workspace")
		self.addWidget(self.wcsY)
		self.wcsY.bind("<Return>",   self.app.wcsSet)
		self.wcsY.bind("<KP_Enter>", self.app.wcsSet)

		col += 1
		self.wcsZ = tkExtra.FloatEntry(lframe, background="White")
		self.wcsZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.wcsZ, "If not empty set the Z workspace")
		self.addWidget(self.wcsZ)
		self.wcsZ.bind("<Return>",   self.app.wcsSet)
		self.wcsZ.bind("<KP_Enter>", self.app.wcsSet)

		col += 1
		b = Button(lframe, text="set",
				command=self.app.wcsSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)

		# set zero
		row += 1
		col  = 1
		b = Button(lframe, text="X=0",
				command=self.app.wcsSetX0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set X coordinate to zero")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text="Y=0",
				command=self.app.wcsSetY0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set Y coordinate to zero")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text="Z=0",
				command=self.app.wcsSetZ0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Set Z coordinate to zero")
		self.addWidget(b)

		col += 1
		b = Button(lframe, text="Zero",
				command=self.app.wcsSet0,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Zero all coordinates")
		self.addWidget(b)

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
		self.addWidget(self._tloin)
		self._tloin.bind("<Return>",   self.app.tloSet)
		self._tloin.bind("<KP_Enter>", self.app.tloSet)

		col += 1
		b = Button(lframe, text="set",
				command=self.app.tloSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)

		# Zero system
		row += 1
		col  = 1
		b = Button(lframe, text="G28", padx=2, pady=2, command=self.app.g28Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "G28: Go to zero via point")

		col += 1
		b = Button(lframe, text="G30", padx=2, pady=2, command=self.app.g30Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "G30: Go to zero via point")

		col += 1
		b = Button(lframe, text="G92", padx=2, pady=2, command=self.app.g92Command)
		b.grid(row=row, column=col,  sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "G92: Set zero system (LEGACY)")

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# ---- WorkSpace ----
		#frame = self.tabPage["Probe"]

		# WorkSpace -> Probe
		lframe = LabelFrame(self.page, text="Probe", foreground="DarkBlue")
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
		self.addWidget(self.probeXdir)

		col += 1
		self.probeYdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeYdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeYdir, "Probe along Y direction")
		self.addWidget(self.probeYdir)

		col += 1
		self.probeZdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeZdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeZdir, "Probe along Z direction")
		self.addWidget(self.probeZdir)

		# ---
		row += 1
		b = Button(lframe, text="Probe", command=self.app.probeOne)
		b.grid(row=row, column=col, sticky=E)
		tkExtra.Balloon.set(b, "Probe one point. Using the feed below")
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# WorkSpace -> Autolevel
		lframe = LabelFrame(self.page, text="Autolevel", foreground="DarkBlue")
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
		self.addWidget(self.probeXmin)

		col += 1
		self.probeXmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeXmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmax, "X maximum")
		self.addWidget(self.probeXmax)

		col += 1
		self.probeXstep = Label(lframe, foreground="DarkBlue", background="gray95", width=5)
		self.probeXstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXstep, "X step")

		col += 1
		self.probeXbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.app.probeChange,
					background="White",
					width=3)
		self.probeXbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXbins, "X bins")
		self.addWidget(self.probeXbins)

		# --- Y ---
		row += 1
		col  = 0
		Label(lframe, text="Y:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeYmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeYmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmin, "Y minimum")
		self.addWidget(self.probeYmin)

		col += 1
		self.probeYmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeYmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmax, "Y maximum")
		self.addWidget(self.probeYmax)

		col += 1
		self.probeYstep = Label(lframe,  foreground="DarkBlue", background="gray95", width=5)
		self.probeYstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYstep, "Y step")

		col += 1
		self.probeYbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.app.probeChange,
					background="White",
					width=3)
		self.probeYbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYbins, "Y bins")
		self.addWidget(self.probeYbins)

		# Max Z
		row += 1
		col  = 0

		Label(lframe, text="Z:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeZmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmin, "Z Minimum depth to scan")
		self.addWidget(self.probeZmin)

		col += 1
		self.probeZmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmax, "Z safe to move")
		self.addWidget(self.probeZmax)

		col += 1
		Label(lframe, text="Feed:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeFeed = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeFeed, "Probe feed rate")
		self.addWidget(self.probeFeed)

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
		self.app.probeChange()

		# Buttons
		row += 1
		col  = 0
		f = Frame(lframe)
		f.grid(row=row, column=col, columnspan=5, sticky=EW)

		b = Button(f, text="Scan", foreground="DarkRed", command=self.app.probeScanArea)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Scan probed area for level information")
		self.addWidget(b)

		b = Button(f, text="Draw", command=self.app.probeDraw)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Draw probe points on canvas")
		self.addWidget(b)

		b = Button(f, text="Set Zero", command=self.app.probeSetZero)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Set current location as Z-zero for leveling")
		self.addWidget(b)

		b = Button(f, text="Get Margins", command=self.app.probeGetMargins)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Get margins from gcode file")
		self.addWidget(b)

		b = Button(f, text="Clear", command=self.app.probeClear)
		b.pack(side=RIGHT)
		tkExtra.Balloon.set(b, "Clear probe points")
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=2)
		lframe.grid_columnconfigure(2,weight=2)
		lframe.grid_columnconfigure(3,weight=1)

