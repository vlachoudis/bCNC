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
# Probe Group
#===============================================================================
class ProbeGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["target32"],
				text="Center",
				compound=TOP,
#				command=self.clear,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Center probing using a ring")

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["level32"],
				text="Autolevel",
				compound=TOP,
#				command=self.clear,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Perform auto leveling in the Z plane")

#===============================================================================
# Probe Frame
#===============================================================================
class ProbeFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe", app)

		# WorkSpace -> Probe
		lframe = LabelFrame(self, text="Probe", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		Label(lframe, text="Probe:").grid(row=row, column=col, sticky=E)

		col += 1
		self.app._probeX = Label(lframe, foreground="DarkBlue", background="gray95")
		self.app._probeX.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self.app._probeY = Label(lframe, foreground="DarkBlue", background="gray95")
		self.app._probeY.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self.app._probeZ = Label(lframe, foreground="DarkBlue", background="gray95")
		self.app._probeZ.grid(row=row, column=col, padx=1, sticky=EW+S)

		# ---
		row,col = row+1,0
		Label(lframe, text="Pos:").grid(row=row, column=col, sticky=E)

		col += 1
		self.app.probeXdir = tkExtra.FloatEntry(lframe, background="White")
		self.app.probeXdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.app.probeXdir, "Probe along X direction")
		self.addWidget(self.app.probeXdir)

		col += 1
		self.app.probeYdir = tkExtra.FloatEntry(lframe, background="White")
		self.app.probeYdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.app.probeYdir, "Probe along Y direction")
		self.addWidget(self.app.probeYdir)

		col += 1
		self.app.probeZdir = tkExtra.FloatEntry(lframe, background="White")
		self.app.probeZdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.app.probeZdir, "Probe along Z direction")
		self.addWidget(self.app.probeZdir)

		# ---
		row += 1
		b = Button(lframe, text="Probe", command=self.app.probeOne)
		b.grid(row=row, column=col, sticky=E)
		tkExtra.Balloon.set(b, "Probe one point. Using the feed below")
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		# Set variables
		self.app.probeXdir.set(Utils.config.get("Probe","x"))
		self.app.probeYdir.set(Utils.config.get("Probe","y"))
		self.app.probeZdir.set(Utils.config.get("Probe","z"))

#===============================================================================
# Autolevel Frame
#===============================================================================
class AutolevelFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Autolevel", app)

		# WorkSpace -> Autolevel
		lframe = LabelFrame(self, text="Autolevel", foreground="DarkBlue")
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
		self.app.probeXmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeXmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeXmin, "X minimum")
		self.addWidget(self.app.probeXmin)

		col += 1
		self.app.probeXmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeXmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeXmax, "X maximum")
		self.addWidget(self.app.probeXmax)

		col += 1
		self.app.probeXstep = Label(lframe, foreground="DarkBlue", background="gray95", width=5)
		self.app.probeXstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeXstep, "X step")

		col += 1
		self.app.probeXbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.app.probeChange,
					background="White",
					width=3)
		self.app.probeXbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeXbins, "X bins")
		self.addWidget(self.app.probeXbins)

		# --- Y ---
		row += 1
		col  = 0
		Label(lframe, text="Y:").grid(row=row, column=col, sticky=E)
		col += 1
		self.app.probeYmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeYmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeYmin, "Y minimum")
		self.addWidget(self.app.probeYmin)

		col += 1
		self.app.probeYmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeYmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeYmax, "Y maximum")
		self.addWidget(self.app.probeYmax)

		col += 1
		self.probeYstep = Label(lframe,  foreground="DarkBlue", background="gray95", width=5)
		self.probeYstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYstep, "Y step")

		col += 1
		self.app.probeYbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.app.probeChange,
					background="White",
					width=3)
		self.app.probeYbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeYbins, "Y bins")
		self.addWidget(self.app.probeYbins)

		# Max Z
		row += 1
		col  = 0

		Label(lframe, text="Z:").grid(row=row, column=col, sticky=E)
		col += 1
		self.app.probeZmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeZmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeZmin, "Z Minimum depth to scan")
		self.addWidget(self.app.probeZmin)

		col += 1
		self.app.probeZmax = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeZmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeZmax, "Z safe to move")
		self.addWidget(self.app.probeZmax)

		col += 1
		Label(lframe, text="Feed:").grid(row=row, column=col, sticky=E)
		col += 1
		self.app.probeFeed = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.app.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.app.probeFeed, "Probe feed rate")
		self.addWidget(self.app.probeFeed)

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

		# Set variables
		self.app.probeXmin.set(Utils.config.get("Probe","xmin"))
		self.app.probeXmax.set(Utils.config.get("Probe","xmax"))
		self.app.probeYmin.set(Utils.config.get("Probe","ymin"))
		self.app.probeYmax.set(Utils.config.get("Probe","ymax"))
		self.app.probeZmin.set(Utils.config.get("Probe","zmin"))
		self.app.probeZmax.set(Utils.config.get("Probe","zmax"))
		self.app.probeFeed.set(Utils.config.get("Probe","feed"))

		self.app.probeXbins.delete(0,END)
		self.app.probeXbins.insert(0,max(2,Utils.getInt("Probe","xn",5)))

		self.app.probeYbins.delete(0,END)
		self.app.probeYbins.insert(0,max(2,Utils.getInt("Probe","yn",5)))
		self.app.probeChange()

#===============================================================================
# Probe Page
#===============================================================================
class ProbePage(CNCRibbon.Page):
	"""Probe configuration and probing"""

	_name_ = "Probe"
	_icon_ = "measure"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((ProbeGroup,),
			(ProbeFrame, AutolevelFrame))
