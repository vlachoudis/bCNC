# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import sys
# import time
import math

try:
	from Tkinter import *
	import tkMessageBox
except ImportError:
	from tkinter import *
	import tkinter.messagebox as tkMessageBox

from CNC import CNC, Block
import Utils
import Camera
import Ribbon
import tkExtra

import CNCRibbon

PROBE_CMD = [	_("G38.2 stop on contact else error"),
		_("G38.3 stop on contact"),
		_("G38.4 stop on loss contact else error"),
		_("G38.5 stop on loss contact")
	]

TOOL_POLICY = [ _("Send M6 commands"),		 # 0
		_("Ignore M6 commands"),	 # 1
		_("Manual Tool Change (WCS)"),	 # 2
		_("Manual Tool Change (TLO)"),	 # 3
		_("Manual Tool Change (NoProbe)")# 4
		]

TOOL_WAIT = [	_("ONLY before probing"),
		_("BEFORE & AFTER probing")
		]

CAMERA_LOCATION = { "Gantry"       : NONE,
		    "Top-Left"     : NW,
		    "Top"          : N,
		    "Top-Right"    : NE,
		    "Left"         : W,
		    "Center"       : CENTER,
		    "Right"        : E,
		    "Bottom-Left"  : SW,
		    "Bottom"       : S,
		    "Bottom-Right" : SE,
		}
CAMERA_LOCATION_ORDER = [
		    "Gantry",
		    "Top-Left",
		    "Top",
		    "Top-Right",
		    "Left",
		    "Center",
		    "Right",
		    "Bottom-Left",
		    "Bottom",
		    "Bottom-Right"]


#===============================================================================
# Probe Tab Group
#===============================================================================
class ProbeTabGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Probe"), app)

		self.tab = StringVar()
		# ---
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["probe32"],
				text=_("Probe"),
				compound=TOP,
				variable=self.tab,
				value="Probe",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Simple probing along a direction"))

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["level32"],
				text=_("Autolevel"),
				compound=TOP,
				variable=self.tab,
				value="Autolevel",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Autolevel Z surface"))

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["camera32"],
				text=_("Camera"),
				compound=TOP,
				variable=self.tab,
				value="Camera",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Work surface camera view and alignment"))
		if Camera.cv is None: b.config(state=DISABLED)

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["endmill32"],
				text=_("Tool"),
				compound=TOP,
				variable=self.tab,
				value="Tool",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Setup probing for manual tool change"))

		self.frame.grid_rowconfigure(0, weight=1)


#===============================================================================
# Autolevel Group
#===============================================================================
class AutolevelGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Autolevel", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelMargins>>",
				image=Utils.icons["margins"],
				text=_("Margins"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Get margins from gcode file"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelZero>>",
				image=Utils.icons["origin"],
				text=_("Zero"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Set current XY location as autoleveling Z-zero (recalculate probed data to be relative to this XY origin point)"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelClear>>",
				image=Utils.icons["clear"],
				text=_("Clear"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Clear probe data"))
		self.addWidget(b)

		# ---
		row = 0
		col += 1
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelScanMargins>>",
				image=Utils.icons["margins"],
				text=_("Scan"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Scan Autolevel Margins"))
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["level"],
				text=_("Autolevel"),
				compound=LEFT,
				anchor=W,
				command=lambda a=app:a.insertCommand("AUTOLEVEL",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Modify selected G-Code to match autolevel"))
		self.addWidget(b)

		# ---
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelScan>>",
				image=Utils.icons["gear32"],
				text=_("Scan"),
				compound=TOP,
				justify=CENTER,
				width=48,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Scan probed area for level information on Z plane"))


#===============================================================================
# Probe Common Offset
#===============================================================================
class ProbeCommonFrame(CNCRibbon.PageFrame):
	probeFeed = None
	tlo       = None
	probeCmd  = None

	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "ProbeCommon", app)

		lframe = tkExtra.ExLabelFrame(self, text=_("Common"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)
		frame = lframe.frame

		# ----
		row = 0
		col = 0

		# ----
		# Fast Probe Feed
		Label(frame, text=_("Fast Probe Feed:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.fastProbeFeed = StringVar()
		self.fastProbeFeed.trace("w", lambda *_: ProbeCommonFrame.probeUpdate())
		ProbeCommonFrame.fastProbeFeed = tkExtra.FloatEntry(frame,
							background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5,
							textvariable=self.fastProbeFeed)
		ProbeCommonFrame.fastProbeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.fastProbeFeed,
			_("Set initial probe feed rate for tool change and calibration"))
		self.addWidget(ProbeCommonFrame.fastProbeFeed)

		# ----
		# Probe Feed
		row += 1
		col  = 0
		Label(frame, text=_("Probe Feed:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeFeedVar = StringVar()
		self.probeFeedVar.trace("w", lambda *_: ProbeCommonFrame.probeUpdate())
		ProbeCommonFrame.probeFeed = tkExtra.FloatEntry(frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5,
								textvariable=self.probeFeedVar)
		ProbeCommonFrame.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.probeFeed, _("Set probe feed rate"))
		self.addWidget(ProbeCommonFrame.probeFeed)

		# ----
		# Tool offset
		row += 1
		col  = 0
		Label(frame, text=_("TLO")).grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.tlo = tkExtra.FloatEntry(frame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		ProbeCommonFrame.tlo.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.tlo, _("Set tool offset for probing"))
		self.addWidget(ProbeCommonFrame.tlo)
		self.tlo.bind("<Return>",   self.tloSet)
		self.tlo.bind("<KP_Enter>", self.tloSet)

		col += 1
		b = Button(frame, text=_("set"),
				command=self.tloSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)

		# ---
		# feed command
		row += 1
		col  = 0
		Label(frame, text=_("Probe Command")).grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.probeCmd = tkExtra.Combobox(frame, True,
						background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
						width=16,
						command=ProbeCommonFrame.probeUpdate)
		ProbeCommonFrame.probeCmd.grid(row=row, column=col, sticky=EW)
		ProbeCommonFrame.probeCmd.fill(PROBE_CMD)
		self.addWidget(ProbeCommonFrame.probeCmd)

		frame.grid_columnconfigure(1,weight=1)
		self.loadConfig()

	#------------------------------------------------------------------------
	def tloSet(self, event=None):
		try:
			CNC.vars["TLO"] = float(ProbeCommonFrame.tlo.get())
			cmd = "G43.1Z"+str(ProbeCommonFrame.tlo.get())
			self.sendGCode(cmd)
		except:
			pass
		self.app.mcontrol.viewParameters()

	#------------------------------------------------------------------------
	@staticmethod
	def probeUpdate():
		try:
			CNC.vars["fastprbfeed"] = float(ProbeCommonFrame.fastProbeFeed.get())
			CNC.vars["prbfeed"]     = float(ProbeCommonFrame.probeFeed.get())
			CNC.vars["prbcmd"]      = str(ProbeCommonFrame.probeCmd.get().split()[0])
			return False
		except:
			return True

	#------------------------------------------------------------------------
	def updateTlo(self):
		try:
			if self.focus_get() is not ProbeCommonFrame.tlo:
				state = ProbeCommonFrame.tlo.cget("state")
				state = ProbeCommonFrame.tlo["state"] = NORMAL
				ProbeCommonFrame.tlo.set(str(CNC.vars.get("TLO","")))
				state = ProbeCommonFrame.tlo["state"] = state
		except:
			pass

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "fastfeed", ProbeCommonFrame.fastProbeFeed.get())
		Utils.setFloat("Probe", "feed", ProbeCommonFrame.probeFeed.get())
		Utils.setFloat("Probe", "tlo",  ProbeCommonFrame.tlo.get())
		Utils.setFloat("Probe", "cmd",  ProbeCommonFrame.probeCmd.get().split()[0])

	#-----------------------------------------------------------------------
	def loadConfig(self):
		ProbeCommonFrame.fastProbeFeed.set(Utils.getFloat("Probe","fastfeed"))
		ProbeCommonFrame.probeFeed.set(Utils.getFloat("Probe","feed"))
		ProbeCommonFrame.tlo.set(      Utils.getFloat("Probe","tlo"))
		cmd = Utils.getStr("Probe","cmd")
		for p in PROBE_CMD:
			if p.split()[0] == cmd:
				ProbeCommonFrame.probeCmd.set(p)
				break


#===============================================================================
# Probe Frame
#===============================================================================
class ProbeFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Probe", app)

		#----------------------------------------------------------------
		# Record point
		#----------------------------------------------------------------

		recframe = tkExtra.ExLabelFrame(self, text=_("Record"), foreground="DarkBlue")
		recframe.pack(side=TOP, expand=YES, fill=X)

		#Label(lframe(), text=_("Diameter:")).pack(side=LEFT)
		#self.diameter = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		#self.diameter.pack(side=LEFT, expand=YES, fill=X)

		self.recz=IntVar()
		self.reczb = Checkbutton(recframe(), text=_("Z"),
			variable=self.recz, #onvalue=1, offvalue=0,
			activebackground="LightYellow",
			padx=2, pady=1)
		tkExtra.Balloon.set(self.reczb, _("Record Z coordinate?"))
		self.reczb.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.reczb)

		self.rr = Button(recframe(), text=_("RAPID"),
			command=self.recordRapid,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.rr.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.rr)

		self.rr = Button(recframe(), text=_("FEED"),
			command=self.recordFeed,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.rr.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.rr)

		self.rr = Button(recframe(), text=_("POINT"),
			command=self.recordPoint,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.rr.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.rr)

		self.rr = Button(recframe(), text=_("CIRCLE"),
			command=self.recordCircle,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.rr.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.rr)

		self.rr = Button(recframe(), text=_("FINISH"),
			command=self.recordFinishAll,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.rr.pack(side=LEFT, expand=YES, fill=X)
		self.addWidget(self.rr)

		self.recsiz = tkExtra.FloatEntry(recframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		tkExtra.Balloon.set(self.recsiz, _("Circle radius"))
		self.recsiz.set(10)
		self.recsiz.pack(side=BOTTOM, expand=YES, fill=X)
		self.addWidget(self.recsiz)

		#----------------------------------------------------------------
		# Single probe
		#----------------------------------------------------------------
		lframe = tkExtra.ExLabelFrame(self, text=_("Probe"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		Label(lframe(), text=_("Probe:")).grid(row=row, column=col, sticky=E)

		col += 1
		self._probeX = Label(lframe(), foreground="DarkBlue", background="gray90")
		self._probeX.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self._probeY = Label(lframe(), foreground="DarkBlue", background="gray90")
		self._probeY.grid(row=row, column=col, padx=1, sticky=EW+S)

		col += 1
		self._probeZ = Label(lframe(), foreground="DarkBlue", background="gray90")
		self._probeZ.grid(row=row, column=col, padx=1, sticky=EW+S)

		# ---
		col += 1
		self.probeautogotonext = False
		self.probeautogoto=IntVar()
		self.autogoto = Checkbutton(lframe(), "",
			variable=self.probeautogoto, #onvalue=1, offvalue=0,
			activebackground="LightYellow",
			padx=2, pady=1)
		self.autogoto.select()
		tkExtra.Balloon.set(self.autogoto, _("Automatic GOTO after probing"))
		#self.autogoto.pack(side=LEFT, expand=YES, fill=X)
		self.autogoto.grid(row=row, column=col, padx=1, sticky=EW)
		self.addWidget(self.autogoto)

		# ---
		col += 1
		b = Button(lframe(),
				image=Utils.icons["rapid"],
				text=_("Goto"),
				compound=LEFT,
				command=self.goto2Probe,
#				width=48,
				padx=5, pady=0)
		b.grid(row=row, column=col, padx=1, sticky=EW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Rapid goto to last probe location"))

		# ---
		row,col = row+1,0
		Label(lframe(), text=_("Pos:")).grid(row=row, column=col, sticky=E)

		col += 1
		self.probeXdir = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.probeXdir.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXdir, _("Probe along X direction"))
		self.addWidget(self.probeXdir)

		col += 1
		self.probeYdir = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.probeYdir.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYdir, _("Probe along Y direction"))
		self.addWidget(self.probeYdir)

		col += 1
		self.probeZdir = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.probeZdir.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZdir, _("Probe along Z direction"))
		self.addWidget(self.probeZdir)

		# ---
		col += 2
		b = Button(lframe(), #"<<Probe>>",
				image=Utils.icons["probe32"],
				text=_("Probe"),
				compound=LEFT,
				command=self.probe,
#				width=48,
				padx=5, pady=0)
		b.grid(row=row, column=col, padx=1, sticky=EW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a single probe cycle"))


		lframe().grid_columnconfigure(1,weight=1)
		lframe().grid_columnconfigure(2,weight=1)
		lframe().grid_columnconfigure(3,weight=1)

		#----------------------------------------------------------------
		# Center probing
		#----------------------------------------------------------------
		lframe = tkExtra.ExLabelFrame(self, text=_("Center"), foreground="DarkBlue")
		lframe.pack(side=TOP, expand=YES, fill=X)

		Label(lframe(), text=_("Diameter:")).pack(side=LEFT)
		self.diameter = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.diameter.pack(side=LEFT, expand=YES, fill=X)
		tkExtra.Balloon.set(self.diameter, _("Probing ring internal diameter"))
		self.addWidget(self.diameter)

		# ---
		b = Button(lframe(),
				image=Utils.icons["target32"],
				text=_("Center"),
				compound=TOP,
				command=self.probeCenter,
				width=48,
				padx=5, pady=0)
		b.pack(side=RIGHT)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Center probing using a ring"))

		#----------------------------------------------------------------
		# Align / Orient / Square ?
		#----------------------------------------------------------------
		lframe = tkExtra.ExLabelFrame(self, text=_("Orient"), foreground="DarkBlue")
		lframe.pack(side=TOP, expand=YES, fill=X)

		# ---
		row, col = 0,0

		Label(lframe(), text=_("Markers:")).grid(row=row, column=col, sticky=E)
		col += 1

		self.scale_orient = Scale(lframe(),
					from_=0, to_=0,
					orient=HORIZONTAL,
					showvalue=1,
					state=DISABLED,
					command=self.changeMarker)
		self.scale_orient.grid(row=row, column=col, columnspan=2, sticky=EW)
		tkExtra.Balloon.set(self.scale_orient, _("Select orientation marker"))

		# Add new point
		col += 2
		b = Button(lframe(), text=_("Add"),
				image=Utils.icons["add"],
				compound=LEFT,
				command=lambda s=self: s.event_generate("<<AddMarker>>"),
				padx = 1,
				pady = 1)
		b.grid(row=row, column=col, sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Add an orientation marker. " \
				"Jog first the machine to the marker position " \
				"and then click on canvas to add the marker."))

		# ----
		row += 1
		col = 0
		Label(lframe(), text=_("Gcode:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.x_orient = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.x_orient.grid(row=row, column=col, sticky=EW)
		self.x_orient.bind("<FocusOut>", self.orientUpdate)
		self.x_orient.bind("<Return>",   self.orientUpdate)
		self.x_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.x_orient, _("GCode X coordinate of orientation point"))

		col += 1
		self.y_orient = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.y_orient.grid(row=row, column=col, sticky=EW)
		self.y_orient.bind("<FocusOut>", self.orientUpdate)
		self.y_orient.bind("<Return>",   self.orientUpdate)
		self.y_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.y_orient, _("GCode Y coordinate of orientation point"))

		# Buttons
		col += 1
		b = Button(lframe(), text=_("Delete"),
				image=Utils.icons["x"],
				compound=LEFT,
				command = self.orientDelete,
				padx = 1,
				pady = 1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Delete current marker"))

		# ---
		row += 1
		col = 0

		Label(lframe(), text=_("WPos:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.xm_orient = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.xm_orient.grid(row=row, column=col, sticky=EW)
		self.xm_orient.bind("<FocusOut>", self.orientUpdate)
		self.xm_orient.bind("<Return>",   self.orientUpdate)
		self.xm_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.xm_orient, _("Machine X coordinate of orientation point"))

		col += 1
		self.ym_orient = tkExtra.FloatEntry(lframe(), background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.ym_orient.grid(row=row, column=col, sticky=EW)
		self.ym_orient.bind("<FocusOut>", self.orientUpdate)
		self.ym_orient.bind("<Return>",   self.orientUpdate)
		self.ym_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.ym_orient, _("Machine Y coordinate of orientation point"))

		# Buttons
		col += 1
		b = Button(lframe(), text=_("Clear"),
				image=Utils.icons["clear"],
				compound=LEFT,
				command = self.orientClear,
				padx = 1,
				pady = 1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Delete all markers"))

		# ---
		row += 1
		col = 0
		Label(lframe(), text=_("Angle:")).grid(row=row, column=col, sticky=E)

		col += 1
		self.angle_orient = Label(lframe(), foreground="DarkBlue", background="gray90", anchor=W)
		self.angle_orient.grid(row=row, column=col, columnspan=2, sticky=EW, padx=1, pady=1)

		# Buttons
		col += 2
		b = Button(lframe(), text=_("Orient"),
				image=Utils.icons["setsquare32"],
				compound=TOP,
				command = lambda a=app:a.insertCommand("ORIENT",True),
				padx = 1,
				pady = 1)
		b.grid(row=row, rowspan=3, column=col, sticky=EW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Align GCode with the machine markers"))

		# ---
		row += 1
		col = 0
		Label(lframe(), text=_("Offset:")).grid(row=row, column=col, sticky=E)

		col += 1
		self.xo_orient = Label(lframe(), foreground="DarkBlue", background="gray90", anchor=W)
		self.xo_orient.grid(row=row, column=col, sticky=EW, padx=1)

		col += 1
		self.yo_orient = Label(lframe(), foreground="DarkBlue", background="gray90", anchor=W)
		self.yo_orient.grid(row=row, column=col, sticky=EW, padx=1)

		# ---
		row += 1
		col = 0
		Label(lframe(), text=_("Error:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.err_orient = Label(lframe(), foreground="DarkBlue", background="gray90", anchor=W)
		self.err_orient.grid(row=row, column=col, columnspan=2, sticky=EW, padx=1, pady=1)

		lframe().grid_columnconfigure(1, weight=1)
		lframe().grid_columnconfigure(2, weight=1)

		#----------------------------------------------------------------
		self.warn = True
		self.loadConfig()

	#-----------------------------------------------------------------------
	def loadConfig(self):
		self.probeXdir.set(Utils.getStr("Probe", "x"))
		self.probeYdir.set(Utils.getStr("Probe", "y"))
		self.probeZdir.set(Utils.getStr("Probe", "z"))
		self.diameter.set(Utils.getStr("Probe",  "center"))
		self.warn = Utils.getBool("Warning", "probe", self.warn)

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "x",      self.probeXdir.get())
		Utils.setFloat("Probe", "y",      self.probeYdir.get())
		Utils.setFloat("Probe", "z",      self.probeZdir.get())
		Utils.setFloat("Probe", "center", self.diameter.get())
		Utils.setBool("Warning","probe",  self.warn)

	#-----------------------------------------------------------------------
	def updateProbe(self):
		try:
			self._probeX["text"] = CNC.vars.get("prbx")
			self._probeY["text"] = CNC.vars.get("prby")
			self._probeZ["text"] = CNC.vars.get("prbz")
		except:
			return

		if self.probeautogotonext:
			self.probeautogotonext = False
			self.goto2Probe()


	#-----------------------------------------------------------------------
	def warnMessage(self):
		if self.warn:
			ans = tkMessageBox.askquestion(_("Probe connected?"),
				_("Please verify that the probe is connected.\n\nShow this message again?"),
				icon='warning',
				parent=self.winfo_toplevel())
			if ans != YES:
				self.warn = False

	#-----------------------------------------------------------------------
	# Probe one Point
	#-----------------------------------------------------------------------
	def probe(self, event=None):
		if self.probeautogoto.get() == 1:
			self.probeautogotonext = True

		if ProbeCommonFrame.probeUpdate():
			tkMessageBox.showerror(_("Probe Error"),
				_("Invalid probe feed rate"),
				parent=self.winfo_toplevel())
			return
		self.warnMessage()

		cmd = str(CNC.vars["prbcmd"])
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

		v = ProbeCommonFrame.probeFeed.get()
		if v != "":
			cmd += "F"+str(v)

		if ok:
			self.sendGCode(cmd)
		else:
			tkMessageBox.showerror(_("Probe Error"),
					_("At least one probe direction should be specified"))

	#-----------------------------------------------------------------------
	# Rapid move to the last probed location
	#-----------------------------------------------------------------------
	def goto2Probe(self, event=None):
		try:
			cmd = "G53 G0 X%g Y%g Z%g\n"%(CNC.vars["prbx"], CNC.vars["prby"], CNC.vars["prbz"])
		except:
			return
		self.sendGCode(cmd)

	#-----------------------------------------------------------------------
	# Probe Center
	#-----------------------------------------------------------------------
	def probeCenter(self, event=None):
		self.warnMessage()

		cmd = "G91 %s F%s"%(CNC.vars["prbcmd"], CNC.vars["prbfeed"])
		try:
			diameter = abs(float(self.diameter.get()))
		except:
			diameter = 0.0

		if diameter < 0.001:
			tkMessageBox.showerror(_("Probe Center Error"),
					_("Invalid diameter entered"),
					parent=self.winfo_toplevel())
			return

		lines = []
		lines.append("%s x-%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("tmp=prbx")
		lines.append("g53 g0 x[prbx+%g]"%(diameter/10))
		lines.append("%wait")
		lines.append("%s x%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 x[0.5*(tmp+prbx)]")
		lines.append("%wait")
		lines.append("%s y-%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("tmp=prby")
		lines.append("g53 g0 y[prby+%g]"%(diameter/10))
		lines.append("%wait")
		lines.append("%s y%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 y[0.5*(tmp+prby)]")
		lines.append("%wait")
		lines.append("g90")
		self.app.run(lines=lines)

	#-----------------------------------------------------------------------
	# Solve the system and update fields
	#-----------------------------------------------------------------------
	def orientSolve(self, event=None):
		try:
			phi, xo, yo = self.app.gcode.orient.solve()
			self.angle_orient["text"]="%*f"%(CNC.digits, math.degrees(phi))
			self.xo_orient["text"]="%*f"%(CNC.digits, xo)
			self.yo_orient["text"]="%*f"%(CNC.digits, yo)

			minerr, meanerr, maxerr = self.app.gcode.orient.error()
			self.err_orient["text"] = "Avg:%*f  Max:%*f  Min:%*f"%\
				(CNC.digits, meanerr, CNC.digits, maxerr, CNC.digits, minerr)

		except:
			self.angle_orient["text"] = sys.exc_info()[1]
			self.xo_orient["text"]    = ""
			self.yo_orient["text"]    = ""
			self.err_orient["text"]   = ""

	#-----------------------------------------------------------------------
	# Delete current orientation point
	#-----------------------------------------------------------------------
	def orientDelete(self, event=None):
		marker = self.scale_orient.get()-1
		if marker<0 or marker >= len(self.app.gcode.orient): return
		self.app.gcode.orient.clear(marker)
		self.orientUpdateScale()
		self.changeMarker(marker+1)
		self.orientSolve()
		self.event_generate("<<DrawOrient>>")

	#-----------------------------------------------------------------------
	# Clear all markers
	#-----------------------------------------------------------------------
	def orientClear(self, event=None):
		if self.scale_orient.cget("to") == 0: return
		ans = tkMessageBox.askquestion(_("Delete all markers"),
			_("Do you want to delete all orientation markers?"),
			parent=self.winfo_toplevel())
		if ans!=tkMessageBox.YES: return
		self.app.gcode.orient.clear()
		self.orientUpdateScale()
		self.event_generate("<<DrawOrient>>")

	#-----------------------------------------------------------------------
	# Update orientation scale
	#-----------------------------------------------------------------------
	def orientUpdateScale(self):
		n = len(self.app.gcode.orient)
		if n:
			self.scale_orient.config(state=NORMAL, from_=1, to_=n)
		else:
			self.scale_orient.config(state=DISABLED, from_=0, to_=0)

	#-----------------------------------------------------------------------
	def orientClearFields(self):
		self.x_orient.delete(0,END)
		self.y_orient.delete(0,END)
		self.xm_orient.delete(0,END)
		self.ym_orient.delete(0,END)
		self.angle_orient["text"] = ""
		self.xo_orient["text"]    = ""
		self.yo_orient["text"]    = ""
		self.err_orient["text"]   = ""

	#-----------------------------------------------------------------------
	# Update orient with the current marker
	#-----------------------------------------------------------------------
	def orientUpdate(self, event=None):
		marker = self.scale_orient.get()-1
		if marker<0 or marker >= len(self.app.gcode.orient):
			self.orientClearFields()
			return
		xm,ym,x,y = self.app.gcode.orient[marker]
		try:    x = float(self.x_orient.get())
		except: pass
		try:    y = float(self.y_orient.get())
		except: pass
		try:    xm = float(self.xm_orient.get())
		except: pass
		try:    ym = float(self.ym_orient.get())
		except: pass
		self.app.gcode.orient.markers[marker] = xm,ym,x,y

		self.orientUpdateScale()
		self.changeMarker(marker+1)
		self.orientSolve()
		self.event_generate("<<DrawOrient>>")

	#-----------------------------------------------------------------------
	# The index will be +1 to appear more human starting from 1
	#-----------------------------------------------------------------------
	def changeMarker(self, marker):
		marker = int(marker)-1
		if marker<0 or marker >= len(self.app.gcode.orient):
			self.orientClearFields()
			self.event_generate("<<OrientChange>>", data=-1)
			return

		xm,ym,x,y = self.app.gcode.orient[marker]
		d = CNC.digits
		self.x_orient.set("%*f"%(d,x))
		self.y_orient.set("%*f"%(d,y))
		self.xm_orient.set("%*f"%(d,xm))
		self.ym_orient.set("%*f"%(d,ym))
		self.orientSolve()
		self.event_generate("<<OrientChange>>", data=marker)

	#-----------------------------------------------------------------------
	# Select marker
	#-----------------------------------------------------------------------
	def selectMarker(self, marker):
		self.orientUpdateScale()
		self.scale_orient.set(marker+1)

	def recordAppend(self, line):
		hasblock = None
		for bid,block in enumerate(self.app.gcode):
			if block._name == 'recording':
				hasblock = bid
				eblock = block

		if hasblock is None:
			hasblock = -1
			eblock = Block('recording')
			self.app.gcode.insBlocks(hasblock, [eblock], "Recorded point")

		eblock.append(line)
		self.app.refresh()
		self.app.setStatus(_("Pointrec"))

		#print "hello",x,y,z
		#print self.app.editor.getSelectedBlocks()

	def recordCoords(self, gcode='G0', point=False):
		#print "Z",self.recz.get()
		x = CNC.vars["wx"]
		y = CNC.vars["wy"]
		z = CNC.vars["wz"]

		coords = "X%s Y%s"%(x, y)
		if self.recz.get() == 1:
			coords += " Z%s"%(z)

		if point:
			self.recordAppend('G0 Z%s'%(CNC.vars["safe"]))
		self.recordAppend('%s %s'%(gcode, coords))
		if point:
			self.recordAppend('G1 Z0')

	def recordRapid(self):
		self.recordCoords()

	def recordFeed(self):
		self.recordCoords('G1')

	def recordPoint(self):
		self.recordCoords('G0', True)

	def recordCircle(self):
		r = float(self.recsiz.get())
		#self.recordCoords('G02 R%s'%(r))
		x = CNC.vars["wx"]-r
		y = CNC.vars["wy"]
		z = CNC.vars["wz"]

		coords = "X%s Y%s"%(x, y)
		if self.recz.get() == 1:
			coords += " Z%s"%(z)

		#self.recordAppend('G0 %s R%s'%(coords, r))
		self.recordAppend('G0 %s'%(coords))
		self.recordAppend('G02 %s I%s'%(coords, r))

	def recordFinishAll(self):
		for bid,block in enumerate(self.app.gcode):
			if block._name == 'recording':
				self.app.gcode.setBlockNameUndo(bid, 'recorded')
		self.app.refresh()
		self.app.setStatus(_("Finished recording"))


#===============================================================================
# Autolevel Frame
#===============================================================================
class AutolevelFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Autolevel", app)

		lframe = LabelFrame(self, text=_("Autolevel"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		# Empty
		col += 1
		Label(lframe, text=_("Min")).grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text=_("Max")).grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text=_("Step")).grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text=_("N")).grid(row=row, column=col, sticky=EW)

		# --- X ---
		row += 1
		col = 0
		Label(lframe, text=_("X:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeXmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeXmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmin, _("X minimum"))
		self.addWidget(self.probeXmin)

		col += 1
		self.probeXmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeXmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmax, _("X maximum"))
		self.addWidget(self.probeXmax)

		col += 1
		self.probeXstep = Label(lframe, foreground="DarkBlue",
					background="gray90", width=5)
		self.probeXstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXstep, _("X step"))

		col += 1
		self.probeXbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.draw,
					background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
					width=3)
		self.probeXbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXbins, _("X bins"))
		self.addWidget(self.probeXbins)

		# --- Y ---
		row += 1
		col  = 0
		Label(lframe, text=_("Y:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeYmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeYmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmin, _("Y minimum"))
		self.addWidget(self.probeYmin)

		col += 1
		self.probeYmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeYmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmax, _("Y maximum"))
		self.addWidget(self.probeYmax)

		col += 1
		self.probeYstep = Label(lframe,  foreground="DarkBlue",
					background="gray90", width=5)
		self.probeYstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYstep, _("Y step"))

		col += 1
		self.probeYbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.draw,
					background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
					width=3)
		self.probeYbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYbins, _("Y bins"))
		self.addWidget(self.probeYbins)

		# Max Z
		row += 1
		col  = 0

		Label(lframe, text=_("Z:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeZmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeZmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmin, _("Z Minimum depth to scan"))
		self.addWidget(self.probeZmin)

		col += 1
		self.probeZmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeZmax.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmax, _("Z safe to move"))
		self.addWidget(self.probeZmax)

		lframe.grid_columnconfigure(1,weight=2)
		lframe.grid_columnconfigure(2,weight=2)
		lframe.grid_columnconfigure(3,weight=1)

		self.loadConfig()

	#-----------------------------------------------------------------------
	def setValues(self):
		probe = self.app.gcode.probe
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

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "xmin", self.probeXmin.get())
		Utils.setFloat("Probe", "xmax", self.probeXmax.get())
		Utils.setInt(  "Probe", "xn",   self.probeXbins.get())
		Utils.setFloat("Probe", "ymin", self.probeYmin.get())
		Utils.setFloat("Probe", "ymax", self.probeYmax.get())
		Utils.setInt(  "Probe", "yn",   self.probeYbins.get())
		Utils.setFloat("Probe", "zmin", self.probeZmin.get())
		Utils.setFloat("Probe", "zmax", self.probeZmax.get())

	#-----------------------------------------------------------------------
	def loadConfig(self):
		self.probeXmin.set(Utils.getFloat("Probe","xmin"))
		self.probeXmax.set(Utils.getFloat("Probe","xmax"))
		self.probeYmin.set(Utils.getFloat("Probe","ymin"))
		self.probeYmax.set(Utils.getFloat("Probe","ymax"))
		self.probeZmin.set(Utils.getFloat("Probe","zmin"))
		self.probeZmax.set(Utils.getFloat("Probe","zmax"))

		self.probeXbins.delete(0,END)
		self.probeXbins.insert(0,max(2,Utils.getInt("Probe","xn",5)))

		self.probeYbins.delete(0,END)
		self.probeYbins.insert(0,max(2,Utils.getInt("Probe","yn",5)))
		self.change(False)

	#-----------------------------------------------------------------------
	def getMargins(self, event=None):
		self.probeXmin.set(str(CNC.vars["xmin"]))
		self.probeXmax.set(str(CNC.vars["xmax"]))
		self.probeYmin.set(str(CNC.vars["ymin"]))
		self.probeYmax.set(str(CNC.vars["ymax"]))
		self.draw()

	#-----------------------------------------------------------------------
	def change(self, verbose=True):
		probe = self.app.gcode.probe
		error = False
		try:
			probe.xmin = float(self.probeXmin.get())
			probe.xmax = float(self.probeXmax.get())
			probe.xn   = max(2,int(self.probeXbins.get()))
			self.probeXstep["text"] = "%.5g"%(probe.xstep())
		except ValueError:
			self.probeXstep["text"] = ""
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
						_("Invalid X probing region"),
						parent=self.winfo_toplevel())
			error = True

		if probe.xmin >= probe.xmax:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
						_("Invalid X range [xmin>=xmax]"),
						parent=self.winfo_toplevel())
			error = True

		try:
			probe.ymin = float(self.probeYmin.get())
			probe.ymax = float(self.probeYmax.get())
			probe.yn   = max(2,int(self.probeYbins.get()))
			self.probeYstep["text"] = "%.5g"%(probe.ystep())
		except ValueError:
			self.probeYstep["text"] = ""
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
						_("Invalid Y probing region"),
						parent=self.winfo_toplevel())
			error = True

		if probe.ymin >= probe.ymax:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
						_("Invalid Y range [ymin>=ymax]"),
						parent=self.winfo_toplevel())
			error = True

		try:
			probe.zmin  = float(self.probeZmin.get())
			probe.zmax  = float(self.probeZmax.get())
		except ValueError:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
					_("Invalid Z probing region"),
					parent=self.winfo_toplevel())
			error = True

		if probe.zmin >= probe.zmax:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
						_("Invalid Z range [zmin>=zmax]"),
						parent=self.winfo_toplevel())
			error = True

		if ProbeCommonFrame.probeUpdate():
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
					_("Invalid probe feed rate"),
					parent=self.winfo_toplevel())
			error = True

		return error

	#-----------------------------------------------------------------------
	def draw(self):
		if not self.change():
			self.event_generate("<<DrawProbe>>")

	#-----------------------------------------------------------------------
	def setZero(self, event=None):
		x = CNC.vars["wx"]
		y = CNC.vars["wy"]
		self.app.gcode.probe.setZero(x,y)
		self.draw()

	#-----------------------------------------------------------------------
	def clear(self, event=None):
		ans = tkMessageBox.askquestion(_("Delete autolevel information"),
			_("Do you want to delete all autolevel in formation?"),
			parent=self.winfo_toplevel())
		if ans!=tkMessageBox.YES: return
		self.app.gcode.probe.clear()
		self.draw()

	#-----------------------------------------------------------------------
	# Probe an X-Y area
	#-----------------------------------------------------------------------
	def scan(self, event=None):
		if self.change(): return
		self.event_generate("<<DrawProbe>>")
		# absolute
		self.app.run(lines=self.app.gcode.probe.scan())

	#-----------------------------------------------------------------------
	# Scan autolevel margins
	#-----------------------------------------------------------------------
	def scanMargins(self, event=None):
		if self.change(): return
		self.app.run(lines=self.app.gcode.probe.scanMargins())


#===============================================================================
# Camera Group
#===============================================================================
class CameraGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Camera", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2
		self.grid3rows()

		self.switch = BooleanVar()
		self.edge   = BooleanVar()
		self.freeze = BooleanVar()

		# ---
		col,row=0,0
		self.switchButton = Ribbon.LabelCheckbutton(self.frame,
				image=Utils.icons["camera32"],
				text=_("Switch To"),
				compound=TOP,
				variable=self.switch,
				command=self.switchCommand,
				background=Ribbon._BACKGROUND)
		self.switchButton.grid(row=row, column=col, rowspan=3, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(self.switchButton, _("Switch between camera and spindle"))

		# ---
		col,row=1,0
		b = Ribbon.LabelCheckbutton(self.frame,
				image=Utils.icons["edge"],
				text=_("Edge Detection"),
				compound=LEFT,
				variable=self.edge,
				anchor=W,
				command=self.edgeDetection,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Turn on/off edge detection"))

		# ---
		row += 1
		b = Ribbon.LabelCheckbutton(self.frame,
				image=Utils.icons["freeze"],
				text=_("Freeze"),
				compound=LEFT,
				variable=self.freeze,
				anchor=W,
				command=self.freezeImage,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Turn on/off freeze image"))

	#-----------------------------------------------------------------------
	# Move camera to spindle location and change coordinates to relative
	# to camera via g92
	#-----------------------------------------------------------------------
	def switchCommand(self, event=None):
		wx = CNC.vars["wx"]
		wy = CNC.vars["wy"]
		dx = self.app.canvas.cameraDx
		dy = self.app.canvas.cameraDy
		z  = self.app.canvas.cameraZ
		if self.switch.get():
			self.switchButton.config(image=Utils.icons["endmill32"])
			self.sendGCode("G92X%gY%g"%(dx+wx,dy+wy))
			self.app.canvas.cameraSwitch = True
		else:
			self.switchButton.config(image=Utils.icons["camera32"])
			self.sendGCode("G92.1")
			self.app.canvas.cameraSwitch = False
		if z is None:
			self.sendGCode("G0X%gY%g"%(wx,wy))
		else:
			self.sendGCode("G0X%gY%gZ%g"%(wx,wy,z))

	#-----------------------------------------------------------------------
	def switchCamera(self, event=None):
		self.switch.set(not self.switch.get())
		self.switchCommand()

	#-----------------------------------------------------------------------
	def edgeDetection(self):
		self.app.canvas.cameraEdge = self.edge.get()

	#-----------------------------------------------------------------------
	def freezeImage(self):
		self.app.canvas.cameraFreeze(self.freeze.get())


#===============================================================================
# Camera Frame
#===============================================================================
class CameraFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Camera", app)

		# ==========
		lframe = LabelFrame(self, text=_("Camera"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X, expand=YES)

		# ----
		row = 0
		Label(lframe, text=_("Location:")).grid(row=row, column=0, sticky=E)
		self.location = tkExtra.Combobox(lframe, True,
					background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
					width=16)
		self.location.grid(row=row, column=1, columnspan=3, sticky=EW)
		self.location.fill(CAMERA_LOCATION_ORDER)
		self.location.set(CAMERA_LOCATION_ORDER[0])
		tkExtra.Balloon.set(self.location, _("Camera location inside canvas"))

		# ----
		row += 1
		Label(lframe, text=_("Rotation:")).grid(row=row, column=0, sticky=E)
		self.rotation = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.rotation.grid(row=row, column=1, sticky=EW)
		self.rotation.bind("<Return>",   self.updateValues)
		self.rotation.bind("<KP_Enter>", self.updateValues)
		self.rotation.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.rotation, _("Camera rotation [degrees]"))
		# ----
		row += 1
		Label(lframe, text=_("Haircross Offset:")).grid(row=row, column=0, sticky=E)
		self.xcenter = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.xcenter.grid(row=row, column=1, sticky=EW)
		self.xcenter.bind("<Return>",   self.updateValues)
		self.xcenter.bind("<KP_Enter>", self.updateValues)
		self.xcenter.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.xcenter, _("Haircross X offset [unit]"))

		self.ycenter = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.ycenter.grid(row=row, column=2, sticky=EW)
		self.ycenter.bind("<Return>",   self.updateValues)
		self.ycenter.bind("<KP_Enter>", self.updateValues)
		self.ycenter.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.ycenter, _("Haircross Y offset [unit]"))
		# ----

		row += 1
		Label(lframe, text=_("Scale:")).grid(row=row, column=0, sticky=E)
		self.scale = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.scale.grid(row=row, column=1, sticky=EW)
		self.scale.bind("<Return>",   self.updateValues)
		self.scale.bind("<KP_Enter>", self.updateValues)
		self.scale.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.scale, _("Camera scale [pixels / unit]"))

		# ----
		row += 1
		Label(lframe, text=_("Crosshair:")).grid(row=row, column=0, sticky=E)
		self.diameter = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.diameter.grid(row=row, column=1, sticky=EW)
		self.diameter.bind("<Return>",   self.updateValues)
		self.diameter.bind("<KP_Enter>", self.updateValues)
		self.diameter.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.diameter, _("Camera cross hair diameter [units]"))

		b = Button(lframe, text=_("Get"), command=self.getDiameter, padx=1, pady=1)
		b.grid(row=row, column=2, sticky=W)
		tkExtra.Balloon.set(b, _("Get diameter from active endmill"))

		# ----
		row += 1
		Label(lframe, text=_("Offset:")).grid(row=row, column=0, sticky=E)
		self.dx = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.dx.grid(row=row, column=1, sticky=EW)
		self.dx.bind("<Return>",   self.updateValues)
		self.dx.bind("<KP_Enter>", self.updateValues)
		self.dx.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.dx, _("Camera offset from gantry"))

		self.dy = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.dy.grid(row=row, column=2, sticky=EW)
		self.dy.bind("<Return>",   self.updateValues)
		self.dy.bind("<KP_Enter>", self.updateValues)
		self.dy.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.dy, _("Camera offset from gantry"))

		self.z = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND)
		self.z.grid(row=row, column=3, sticky=EW)
		self.z.bind("<Return>",   self.updateValues)
		self.z.bind("<KP_Enter>", self.updateValues)
		self.z.bind("<FocusOut>", self.updateValues)
		tkExtra.Balloon.set(self.z, _("Spindle Z position when camera was registered"))

		row += 1
		Label(lframe, text=_("Register:")).grid(row=row, column=0, sticky=E)
		b = Button(lframe, text=_("1. Spindle"),
				command=self.registerSpindle,
				padx=1,
				pady=1)
		tkExtra.Balloon.set(b, _("Mark spindle position for calculating offset"))
		b.grid(row=row, column=1, sticky=EW)
		b = Button(lframe, text=_("2. Camera"),
				command=self.registerCamera,
				padx=1,
				pady=1)
		tkExtra.Balloon.set(b, _("Mark camera position for calculating offset"))
		b.grid(row=row, column=2, sticky=EW)

		lframe.grid_columnconfigure(1, weight=1)
		lframe.grid_columnconfigure(2, weight=1)
		lframe.grid_columnconfigure(3, weight=1)

		self.loadConfig()
		self.location.config(command=self.updateValues)
		self.spindleX = None
		self.spindleY = None

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setStr(  "Camera", "aligncam_anchor",self.location.get())
		Utils.setFloat("Camera", "aligncam_d",     self.diameter.get())
		Utils.setFloat("Camera", "aligncam_scale", self.scale.get())
		Utils.setFloat("Camera", "aligncam_dx",    self.dx.get())
		Utils.setFloat("Camera", "aligncam_dy",    self.dy.get())
		Utils.setFloat("Camera", "aligncam_z",     self.z.get())
		Utils.setFloat("Camera", "aligncam_rotation",     self.rotation.get())
		Utils.setFloat("Camera", "aligncam_xcenter",     self.xcenter.get())
		Utils.setFloat("Camera", "aligncam_ycenter",     self.ycenter.get())

	#-----------------------------------------------------------------------
	def loadConfig(self):
		self.location.set(Utils.getStr("Camera",  "aligncam_anchor"))
		self.diameter.set(Utils.getFloat("Camera","aligncam_d"))
		self.scale.set( Utils.getFloat("Camera",  "aligncam_scale"))
		self.dx.set(    Utils.getFloat("Camera",  "aligncam_dx"))
		self.dy.set(    Utils.getFloat("Camera",  "aligncam_dy"))
		self.z.set(     Utils.getFloat("Camera",  "aligncam_z", ""))
		self.rotation.set(Utils.getFloat("Camera","aligncam_rotation"))
		self.xcenter.set(Utils.getFloat("Camera", "aligncam_xcenter"))
		self.ycenter.set(Utils.getFloat("Camera", "aligncam_ycenter"))
		self.updateValues()

	#-----------------------------------------------------------------------
	# Return camera Anchor
	#-----------------------------------------------------------------------
	def cameraAnchor(self):
		return CAMERA_LOCATION.get(self.location.get(),CENTER)

	#-----------------------------------------------------------------------
	def getDiameter(self):
		self.diameter.set(CNC.vars["diameter"])
		self.updateValues()

	#-----------------------------------------------------------------------
	# Update canvas with values
	#-----------------------------------------------------------------------
	def updateValues(self, *args):
		self.app.canvas.cameraAnchor = self.cameraAnchor()
		try: self.app.canvas.cameraRotation = float(self.rotation.get())
		except ValueError: pass
		try: self.app.canvas.cameraXCenter = float(self.xcenter.get())
		except ValueError: pass
		try: self.app.canvas.cameraYCenter = float(self.ycenter.get())
		except ValueError: pass
		try: self.app.canvas.cameraScale = max(0.0001, float(self.scale.get()))
		except ValueError: pass
		try: self.app.canvas.cameraR = float(self.diameter.get())/2.0
		except ValueError: pass
		try: self.app.canvas.cameraDx = float(self.dx.get())
		except ValueError: pass
		try: self.app.canvas.cameraDy = float(self.dy.get())
		except ValueError: pass
		try:
			self.app.canvas.cameraZ  = float(self.z.get())
		except ValueError:
			self.app.canvas.cameraZ  = None
		self.app.canvas.cameraUpdate()

	#-----------------------------------------------------------------------
	# Register spindle position
	#-----------------------------------------------------------------------
	def registerSpindle(self):
		self.spindleX = CNC.vars["wx"]
		self.spindleY = CNC.vars["wy"]
		self.event_generate("<<Status>>", data=_("Spindle position is registered"))

	#-----------------------------------------------------------------------
	# Register camera position
	#-----------------------------------------------------------------------
	def registerCamera(self):
		if self.spindleX is None:
			tkMessageBox.showwarning(_("Spindle position is not registered"),
					_("Spindle position must be registered before camera"),
					parent=self)
			return
		self.dx.set(str(self.spindleX - CNC.vars["wx"]))
		self.dy.set(str(self.spindleY - CNC.vars["wy"]))
		self.z.set(str(CNC.vars["wz"]))
		self.event_generate("<<Status>>", data=_("Camera offset is updated"))
		self.updateValues()

#	#-----------------------------------------------------------------------
#	def findScale(self):
#		return
#		self.app.canvas.cameraMakeTemplate(30)
#
#		self.app.control.moveXup()
#		#self.app.wait4Idle()
#		time.sleep(2)
#		dx,dy = self.app.canvas.cameraMatchTemplate()	# right
#
#		self.app.control.moveXdown()
#		self.app.control.moveXdown()
#		#self.app.wait4Idle()
#		time.sleep(2)
#		dx,dy = self.app.canvas.cameraMatchTemplate()	# left
#
#		self.app.control.moveXup()
#		self.app.control.moveYup()
#		#self.app.wait4Idle()
#		time.sleep(2)
#		dx,dy = self.app.canvas.cameraMatchTemplate()	# top
#
#		self.app.control.moveYdown()
#		self.app.control.moveYdown()
#		#self.app.wait4Idle()
#		time.sleep(2)
#		dx,dy = self.app.canvas.cameraMatchTemplate()	# down
#
#		self.app.control.moveYup()

	#-----------------------------------------------------------------------
	# Move camera to spindle location and change coordinates to relative
	# to camera via g92
	#-----------------------------------------------------------------------
#	def switch2Camera(self, event=None):
#		print "Switch to camera"
#		wx = CNC.vars["wx"]
#		wy = CNC.vars["wy"]
#		dx = float(self.dx.get())
#		dy = float(self.dy.get())
#		if self.switchVar.get():
#			self.sendGCode("G92X%gY%g"%(dx+wx,dy+wy))
#		else:
#			self.sendGCode("G92.1")
#		self.sendGCode("G0X%gY%g"%(wx,wy))


#===============================================================================
# Tool Group
#===============================================================================
class ToolGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Tool", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2

		b = Ribbon.LabelButton(self.frame, self, "<<ToolCalibrate>>",
				image=Utils.icons["calibrate32"],
				text=_("Calibrate"),
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a single a tool change cycle to set the calibration field"))

		b = Ribbon.LabelButton(self.frame, self, "<<ToolChange>>",
				image=Utils.icons["endmill32"],
				text=_("Change"),
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a tool change cycle"))


#===============================================================================
# Tool Frame
#===============================================================================
class ToolFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Tool", app)

		lframe = LabelFrame(self, text=_("Manual Tool Change"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		# --- Tool policy ---
		row,col = 0,0
		Label(lframe, text=_("Policy:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.toolPolicy = tkExtra.Combobox(lframe, True,
					background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
					command=self.policyChange,
					width=16)
		self.toolPolicy.grid(row=row, column=col, columnspan=3, sticky=EW)
		self.toolPolicy.fill(TOOL_POLICY)
		self.toolPolicy.set(TOOL_POLICY[0])
		tkExtra.Balloon.set(self.toolPolicy, _("Tool change policy"))
		self.addWidget(self.toolPolicy)

		# ----
		row += 1
		col  = 0
		Label(lframe, text=_("Pause:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.toolWait = tkExtra.Combobox(lframe, True,
					background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
					command=self.waitChange,
					width=16)
		self.toolWait.grid(row=row, column=col, columnspan=3, sticky=EW)
		self.toolWait.fill(TOOL_WAIT)
		self.toolWait.set(TOOL_WAIT[1])
		self.addWidget(self.toolWait)

		# ----
		row += 1
		col  = 1
		Label(lframe, text=_("MX")).grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text=_("MY")).grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text=_("MZ")).grid(row=row, column=col, sticky=EW)

		# --- Tool Change position ---
		row += 1
		col = 0
		Label(lframe, text=_("Change:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.changeX = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.changeX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeX, _("Manual tool change Machine X location"))
		self.addWidget(self.changeX)
		self.changeX.bind('<KeyRelease>',   self.setProbeParams)
		self.changeX.bind('<FocusOut>',   self.setProbeParams)

		col += 1
		self.changeY = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.changeY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeY, _("Manual tool change Machine Y location"))
		self.addWidget(self.changeY)
		self.changeY.bind('<KeyRelease>',   self.setProbeParams)
		self.changeY.bind('<FocusOut>',   self.setProbeParams)

		col += 1
		self.changeZ = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.changeZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeZ, _("Manual tool change Machine Z location"))
		self.addWidget(self.changeZ)
		self.changeZ.bind('<KeyRelease>',   self.setProbeParams)
		self.changeZ.bind('<FocusOut>', self.setProbeParams)

		col += 1
		b = Button(lframe, text=_("get"),
				command=self.getChange,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, _("Get current gantry position as machine tool change location"))
		self.addWidget(b)

		# --- Tool Probe position ---
		row += 1
		col = 0
		Label(lframe, text=_("Probe:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeX = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeX, _("Manual tool change Probing MX location"))
		self.addWidget(self.probeX)
		self.probeX.bind('<KeyRelease>',   self.setProbeParams)
		self.probeX.bind('<FocusOut>', self.setProbeParams)

		col += 1
		self.probeY = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeY, _("Manual tool change Probing MY location"))
		self.addWidget(self.probeY)
		self.probeY.bind('<KeyRelease>',   self.setProbeParams)
		self.probeY.bind('<FocusOut>', self.setProbeParams)

		col += 1
		self.probeZ = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZ, _("Manual tool change Probing MZ location"))
		self.addWidget(self.probeZ)
		self.probeZ.bind('<KeyRelease>',   self.setProbeParams)
		self.probeZ.bind('<FocusOut>', self.setProbeParams)

		col += 1
		b = Button(lframe, text=_("get"),
				command=self.getProbe,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, _("Get current gantry position as machine tool probe location"))
		self.addWidget(b)

		# --- Probe Distance ---
		row += 1
		col = 0
		Label(lframe, text=_("Distance:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.probeDistance = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.probeDistance.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeDistance,
				_("After a tool change distance to scan starting from ProbeZ"))
		self.addWidget(self.probeDistance)
		self.probeDistance.bind('<KeyRelease>',   self.setProbeParams)
		self.probeDistance.bind('<FocusOut>', self.setProbeParams)

		# --- Calibration ---
		row += 1
		col = 0
		Label(lframe, text=_("Calibration:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.toolHeight = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
		self.toolHeight.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.toolHeight, _("Tool probe height"))
		self.addWidget(self.toolHeight)

		col += 1
		b = Button(lframe, text=_("Calibrate"),
				command=self.calibrate,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, _("Perform a calibration probing to determine the height"))
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		self.loadConfig()

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setInt(  "Probe", "toolpolicy",  TOOL_POLICY.index(self.toolPolicy.get()))
		Utils.setInt(  "Probe", "toolwait",    TOOL_WAIT.index(self.toolWait.get()))
		Utils.setFloat("Probe", "toolchangex", self.changeX.get())
		Utils.setFloat("Probe", "toolchangey", self.changeY.get())
		Utils.setFloat("Probe", "toolchangez", self.changeZ.get())

		Utils.setFloat("Probe", "toolprobex", self.probeX.get())
		Utils.setFloat("Probe", "toolprobey", self.probeY.get())
		Utils.setFloat("Probe", "toolprobez", self.probeZ.get())

		Utils.setFloat("Probe", "tooldistance",self.probeDistance.get())
		Utils.setFloat("Probe", "toolheight",  self.toolHeight.get())
		Utils.setFloat("Probe", "toolmz",      CNC.vars.get("toolmz",0.))

	#-----------------------------------------------------------------------
	def loadConfig(self):
		self.changeX.set(Utils.getFloat("Probe","toolchangex"))
		self.changeY.set(Utils.getFloat("Probe","toolchangey"))
		self.changeZ.set(Utils.getFloat("Probe","toolchangez"))

		self.probeX.set(Utils.getFloat("Probe","toolprobex"))
		self.probeY.set(Utils.getFloat("Probe","toolprobey"))
		self.probeZ.set(Utils.getFloat("Probe","toolprobez"))

		self.probeDistance.set(Utils.getFloat("Probe","tooldistance"))
		self.toolHeight.set(   Utils.getFloat("Probe","toolheight"))
		self.toolPolicy.set(TOOL_POLICY[Utils.getInt("Probe","toolpolicy",0)])
		self.toolWait.set(TOOL_WAIT[Utils.getInt("Probe","toolwait",1)])
		CNC.vars["toolmz"] = Utils.getFloat("Probe","toolmz")
		self.set()

	#-----------------------------------------------------------------------
	def set(self):
		self.policyChange()
		self.waitChange()
		try:
			CNC.vars["toolchangex"]  = float(self.changeX.get())
			CNC.vars["toolchangey"]  = float(self.changeY.get())
			CNC.vars["toolchangez"]  = float(self.changeZ.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool change position"),
					parent=self.winfo_toplevel())
			return

		try:
			CNC.vars["toolprobex"]   = float(self.probeX.get())
			CNC.vars["toolprobey"]   = float(self.probeY.get())
			CNC.vars["toolprobez"]   = float(self.probeZ.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool probe location"),
					parent=self.winfo_toplevel())
			return

		try:
			CNC.vars["tooldistance"] = abs(float(self.probeDistance.get()))
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool scanning distance entered"),
					parent=self.winfo_toplevel())
			return

		try:
			CNC.vars["toolheight"]   = float(self.toolHeight.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool height or not calibrated"),
					parent=self.winfo_toplevel())
			return

	#-----------------------------------------------------------------------
	def check4Errors(self):
		if CNC.vars["tooldistance"] <= 0.0:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool scanning distance entered"),
					parent=self.winfo_toplevel())
			return True
		return False

	#-----------------------------------------------------------------------
	def policyChange(self):
		CNC.toolPolicy = int(TOOL_POLICY.index(self.toolPolicy.get()))

	#-----------------------------------------------------------------------
	def waitChange(self):
		CNC.toolWaitAfterProbe = int(TOOL_WAIT.index(self.toolWait.get()))


	#-----------------------------------------------------------------------
	def setProbeParams(self, dummy=None):
		print("probe chg handler")
		CNC.vars["toolchangex"] = float(self.changeX.get())
		CNC.vars["toolchangey"] = float(self.changeY.get())
		CNC.vars["toolchangez"] = float(self.changeZ.get())
		CNC.vars["toolprobex"] = float(self.probeX.get())
		CNC.vars["toolprobey"] = float(self.probeY.get())
		CNC.vars["toolprobez"] = float(self.probeZ.get())
		CNC.vars["tooldistance"] = float(self.probeDistance.get())

	#-----------------------------------------------------------------------
	def getChange(self):
		self.changeX.set(CNC.vars["mx"])
		self.changeY.set(CNC.vars["my"])
		self.changeZ.set(CNC.vars["mz"])
		self.setProbeParams()

	#-----------------------------------------------------------------------
	def getProbe(self):
		self.probeX.set(CNC.vars["mx"])
		self.probeY.set(CNC.vars["my"])
		self.probeZ.set(CNC.vars["mz"])
		self.setProbeParams()

	#-----------------------------------------------------------------------
	def updateTool(self):
		state = self.toolHeight.cget("state")
		self.toolHeight.config(state=NORMAL)
		self.toolHeight.set(CNC.vars["toolheight"])
		self.toolHeight.config(state=state)

	#-----------------------------------------------------------------------
	def calibrate(self, event=None):
		self.set()
		if self.check4Errors(): return
		lines = []
		lines.append("g53 g0 z[toolchangez]")
		lines.append("g53 g0 x[toolchangex] y[toolchangey]")
		lines.append("g53 g0 x[toolprobex] y[toolprobey]")
		lines.append("g53 g0 z[toolprobez]")
		if CNC.vars["fastprbfeed"]:
			prb_reverse = {"2": "4", "3": "5", "4": "2", "5": "3"}
			CNC.vars["prbcmdreverse"] = (CNC.vars["prbcmd"][:-1] +
						prb_reverse[CNC.vars["prbcmd"][-1]])
			currentFeedrate = CNC.vars["fastprbfeed"]
			while currentFeedrate > CNC.vars["prbfeed"]:
				lines.append("%wait")
				lines.append("g91 [prbcmd] %s z[toolprobez-mz-tooldistance]" \
						% CNC.fmt('f',currentFeedrate))
				lines.append("%wait")
				lines.append("[prbcmdreverse] %s z[toolprobez-mz]" \
						% CNC.fmt('f',currentFeedrate))
				currentFeedrate /= 10
		lines.append("%wait")
		lines.append("g91 [prbcmd] f[prbfeed] z[toolprobez-mz-tooldistance]")
		lines.append("g4 p1")	# wait a sec
		lines.append("%wait")
		lines.append("%global toolheight; toolheight=wz")
		lines.append("%global toolmz; toolmz=prbz")
		lines.append("%update toolheight")
		lines.append("g53 g0 z[toolchangez]")
		lines.append("g53 g0 x[toolchangex] y[toolchangey]")
		lines.append("g90")
		self.app.run(lines=lines)

	#-----------------------------------------------------------------------
	# FIXME should be replaced with the CNC.toolChange()
	#-----------------------------------------------------------------------
	def change(self, event=None):
		self.set()
		if self.check4Errors(): return
		lines = self.app.cnc.toolChange(0)
		self.app.run(lines=lines)

##===============================================================================
## Help Frame
##===============================================================================
#class HelpFrame(CNCRibbon.PageFrame):
#	def __init__(self, master, app):
#		CNCRibbon.PageFrame.__init__(self, master, "Help", app)
#
#		lframe = tkExtra.ExLabelFrame(self, text="Help", foreground="DarkBlue")
#		lframe.pack(side=TOP, fill=X)
#		frame = lframe.frame
#
#		self.text = Label(frame,
#				text="One\nTwo\nThree",
#				image=Utils.icons["gear32"],
#				compound=TOP,
#				anchor=W,
#				justify=LEFT)
#		self.text.pack(fill=BOTH, expand=YES)


#===============================================================================
# Probe Page
#===============================================================================
class ProbePage(CNCRibbon.Page):
	__doc__ = _("Probe configuration and probing")
	_name_  = "Probe"
	_icon_  = "measure"

	#-----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#-----------------------------------------------------------------------
	def register(self):
		self._register((ProbeTabGroup, AutolevelGroup, CameraGroup, ToolGroup),
			(ProbeCommonFrame, ProbeFrame, AutolevelFrame, CameraFrame, ToolFrame))

		self.tabGroup = CNCRibbon.Page.groups["Probe"]
		self.tabGroup.tab.set("Probe")
		self.tabGroup.tab.trace('w', self.tabChange)

	#-----------------------------------------------------------------------
	def tabChange(self, a=None, b=None, c=None):
		tab = self.tabGroup.tab.get()
		self.master._forgetPage()

		# remove all page tabs with ":" and add the new ones
		self.ribbons = [ x for x in self.ribbons if ":" not in x[0].name ]
		self.frames  = [ x for x in self.frames  if ":" not in x[0].name ]

		try:
			self.addRibbonGroup("Probe:%s"%(tab))
		except KeyError:
			pass
		try:
			self.addPageFrame("Probe:%s"%(tab))
		except KeyError:
			pass

		self.master.changePage(self)
