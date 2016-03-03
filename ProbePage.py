# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import sys
import math

try:
	from Tkinter import *
	import tkMessageBox
except ImportError:
	from tkinter import *
	import tkinter.messagebox as tkMessageBox

from CNC import WCS,CNC
import Utils
import Ribbon
import tkExtra
import CNCRibbon

PROBE_CMD = [	_("G38.2 stop on contact else error"),
		_("G38.3 stop on contact"),
		_("G38.4 stop on loss contact else error"),
		_("G38.5 stop on loss contact")
	]

TOOL_POLICY = [ _("Send M6 commands"),		# 0
		_("Ignore M6 commands"),	# 1
		_("Manual Tool Change (WCS)"),	# 2
		_("Manual Tool Change (TLO)")	# 3
		]

TOOL_WAIT = [	_("ONLY before probing"),
		_("BEFORE & AFTER probing")
		]

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
		tkExtra.Balloon.set(b, _("Set current location as Z-zero for leveling"))
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
		col,row=1,0
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

		lframe = tkExtra.ExLabelFrame(self, text="Common", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)
		frame = lframe.frame

		# ----
		row = 0
		col = 0

		Label(frame, text=_("Probe Feed:")).grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.probeFeed = tkExtra.FloatEntry(frame, background="White", width=5)
		ProbeCommonFrame.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.probeFeed, _("Set probe feed rate"))
		self.addWidget(ProbeCommonFrame.probeFeed)

		# ----
		# Tool offset
		row += 1
		col  = 0
		Label(frame, text=_("TLO")).grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.tlo = tkExtra.FloatEntry(frame, background="White")
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
						background="White",
						width=16)
		ProbeCommonFrame.probeCmd.grid(row=row, column=col, sticky=EW)
		ProbeCommonFrame.probeCmd.fill(PROBE_CMD)
		self.addWidget(ProbeCommonFrame.probeCmd)

		frame.grid_columnconfigure(1,weight=1)
		self.loadConfig()

	#------------------------------------------------------------------------
	def tloSet(self, event=None):
		try:
			CNC.vars["TLO"] = float(ProbeCommonFrame.tlo.get())
			cmd = "g43.1z"+str(ProbeCommonFrame.tlo.get())
			self.sendGrbl(cmd+"\n")
		except:
			pass

	#------------------------------------------------------------------------
	@staticmethod
	def probeUpdate():
		try:
			CNC.vars["prbfeed"] = float(ProbeCommonFrame.probeFeed.get())
			CNC.vars["prbcmd"]  = str(ProbeCommonFrame.probeCmd.get().split()[0])
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
		Utils.setFloat("Probe", "feed", ProbeCommonFrame.probeFeed.get())
		Utils.setFloat("Probe", "tlo",  ProbeCommonFrame.tlo.get())
		Utils.setFloat("Probe", "cmd",  ProbeCommonFrame.probeCmd.get().split()[0])

	#-----------------------------------------------------------------------
	def loadConfig(self):
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
		b = Button(lframe(), #"<<Probe>>",
				image=Utils.icons["probe32"],
				text=_("Probe"),
				compound=TOP,
				command=self.probe)
		b.grid(row=row, column=col, rowspan=2, padx=1, sticky=EW+S)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a single probe cycle"))

		# ---
		row,col = row+1,0
		Label(lframe(), text=_("Pos:")).grid(row=row, column=col, sticky=E)

		col += 1
		self.probeXdir = tkExtra.FloatEntry(lframe(), background="White")
		self.probeXdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeXdir, _("Probe along X direction"))
		self.addWidget(self.probeXdir)

		col += 1
		self.probeYdir = tkExtra.FloatEntry(lframe(), background="White")
		self.probeYdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeYdir, _("Probe along Y direction"))
		self.addWidget(self.probeYdir)

		col += 1
		self.probeZdir = tkExtra.FloatEntry(lframe(), background="White")
		self.probeZdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeZdir, _("Probe along Z direction"))
		self.addWidget(self.probeZdir)

		lframe().grid_columnconfigure(1,weight=1)
		lframe().grid_columnconfigure(2,weight=1)
		lframe().grid_columnconfigure(3,weight=1)

		#----------------------------------------------------------------
		# Center probing
		#----------------------------------------------------------------
		lframe = tkExtra.ExLabelFrame(self, text=_("Center"), foreground="DarkBlue")
		lframe.pack(side=TOP, expand=YES, fill=X)

		Label(lframe(), text=_("Diameter:")).pack(side=LEFT)
		self.diameter = tkExtra.FloatEntry(lframe(), background="White")
		self.diameter.pack(side=LEFT, expand=YES, fill=X)
		tkExtra.Balloon.set(self.diameter, _("Probing ring internal diameter"))
		self.addWidget(self.diameter)

		# ---
		b = Button(lframe(),
				image=Utils.icons["target32"],
				text=_("Center"),
				compound=TOP,
				command=self.probeCenter)
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
		Label(lframe(), text="Gcode:").grid(row=row, column=col, sticky=E)
		col += 1
		self.x_orient = tkExtra.FloatEntry(lframe(), background="White")
		self.x_orient.grid(row=row, column=col, sticky=EW)
		self.x_orient.bind("<FocusOut>", self.orientUpdate)
		self.x_orient.bind("<Return>",   self.orientUpdate)
		self.x_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.x_orient, _("GCode X coordinate of orientation point"))

		col += 1
		self.y_orient = tkExtra.FloatEntry(lframe(), background="White")
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

		Label(lframe(), text="WPos:").grid(row=row, column=col, sticky=E)
		col += 1
		self.xm_orient = tkExtra.FloatEntry(lframe(), background="White")
		self.xm_orient.grid(row=row, column=col, sticky=EW)
		self.xm_orient.bind("<FocusOut>", self.orientUpdate)
		self.xm_orient.bind("<Return>",   self.orientUpdate)
		self.xm_orient.bind("<KP_Enter>", self.orientUpdate)
		tkExtra.Balloon.set(self.xm_orient, _("Machine X coordinate of orientation point"))

		col += 1
		self.ym_orient = tkExtra.FloatEntry(lframe(), background="White")
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
		self.probeXdir.set(Utils.getStr("Probe","x"))
		self.probeYdir.set(Utils.getStr("Probe","y"))
		self.probeZdir.set(Utils.getStr("Probe","z"))
		self.diameter.set(Utils.getStr("Probe", "center"))
		self.warn = Utils.getBool("Warning","probe",self.warn)

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "x",    self.probeXdir.get())
		Utils.setFloat("Probe", "y",    self.probeYdir.get())
		Utils.setFloat("Probe", "z",    self.probeZdir.get())
		Utils.setFloat("Probe", "center",  self.diameter.get())
		Utils.setBool("Warning", "probe", self.warn)

	#-----------------------------------------------------------------------
	def updateProbe(self):
		try:
			self._probeX["text"] = CNC.vars.get("prbx")
			self._probeY["text"] = CNC.vars.get("prby")
			self._probeZ["text"] = CNC.vars.get("prbz")
		except:
			pass

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
			self.sendGrbl(cmd+"\n")
		else:
			tkMessageBox.showerror(_("Probe Error"),
					_("At least one probe direction should be specified"))

	#-----------------------------------------------------------------------
	# Probe Center
	#-----------------------------------------------------------------------
	def probeCenter(self, event=None):
		self.warnMessage()

		cmd = "g91 %s f%s"%(CNC.vars["prbcmd"], CNC.vars["prbfeed"])
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
		lines.append("%s x%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 x[0.5*(tmp+prbx)]")
		lines.append("%s y-%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("tmp=prby")
		lines.append("%s y%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 y[0.5*(tmp+prby)]")
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

#===============================================================================
# Autolevel Frame
#===============================================================================
class AutolevelFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Autolevel", app)

		lframe = LabelFrame(self, text="Autolevel", foreground="DarkBlue")
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
		Label(lframe, text="N").grid(row=row, column=col, sticky=EW)

		# --- X ---
		row += 1
		col = 0
		Label(lframe, text="X:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeXmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeXmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXmin, _("X minimum"))
		self.addWidget(self.probeXmin)

		col += 1
		self.probeXmax = tkExtra.FloatEntry(lframe, background="White", width=5)
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
					background="White",
					width=3)
		self.probeXbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXbins, _("X bins"))
		self.addWidget(self.probeXbins)

		# --- Y ---
		row += 1
		col  = 0
		Label(lframe, text="Y:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeYmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeYmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYmin, _("Y minimum"))
		self.addWidget(self.probeYmin)

		col += 1
		self.probeYmax = tkExtra.FloatEntry(lframe, background="White", width=5)
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
					background="White",
					width=3)
		self.probeYbins.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYbins, _("Y bins"))
		self.addWidget(self.probeYbins)

		# Max Z
		row += 1
		col  = 0

		Label(lframe, text="Z:").grid(row=row, column=col, sticky=E)
		col += 1
		self.probeZmin = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZmin.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZmin, _("Z Minimum depth to scan"))
		self.addWidget(self.probeZmin)

		col += 1
		self.probeZmax = tkExtra.FloatEntry(lframe, background="White", width=5)
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

		try:
			probe.zmin  = float(self.probeZmin.get())
			probe.zmax  = float(self.probeZmax.get())
		except ValueError:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
					_("Invalid Z probing region"),
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

#===============================================================================
# Camera Group
#===============================================================================
class CameraGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Camera", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2

		self.cameraFlag = BooleanVar()

		b = Ribbon.LabelCheckbutton(self.frame,
				image=Utils.icons["camera32"],
				text=_("On/Off"),
				compound=TOP,
				width=48,
				variable = self.cameraFlag,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Turn on/off display of alignment camera"))

		self.cameraFlag.trace('w', self.cameraToggle)

	#-----------------------------------------------------------------------
	def cameraToggle(self, a=None, b=None, c=None):
		if self.cameraFlag.get():
			self.event_generate("<<CameraOn>>")
		else:
			self.event_generate("<<CameraOff>>")

#===============================================================================
# Camera Frame
#===============================================================================
class CameraFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Camera", app)

		# FIXME VERY CRUDE for testing

		lframe = LabelFrame(self, text=_("Location"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		self.anchor = StringVar()
		self.anchor.set(CENTER)

		# ===
		b = Radiobutton(lframe, text=_("T-L"),
					variable = self.anchor,
					value = NW)
		b.grid(row=0, column=0, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Top-Left corner"))

		# ---
		b = Radiobutton(lframe, text=_("Top"),
					variable = self.anchor,
					value = N)
		b.grid(row=0, column=1, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Top"))

		# ---
		b = Radiobutton(lframe, text=_("T-R"),
					variable = self.anchor,
					value = NE)
		b.grid(row=0, column=2, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Top-Right corner"))

		# ===
		b = Radiobutton(lframe, text=_("Left"),
					variable = self.anchor,
					value = W)
		b.grid(row=1, column=0, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Left"))

		# ---
		b = Radiobutton(lframe, text=_("Center"),
					variable = self.anchor,
					value = CENTER)
		b.grid(row=1, column=1, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to center"))

		# ---
		b = Radiobutton(lframe, text=_("Right"),
					variable = self.anchor,
					value = E)
		b.grid(row=1, column=2, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Right"))

		# ===
		b = Radiobutton(lframe, text=_("B-L"),
					variable = self.anchor,
					value = SW)
		b.grid(row=2, column=0, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Bottom-Left corner"))

		# ---
		b = Radiobutton(lframe, text=_("Bottom"),
					variable = self.anchor,
					value = S)
		b.grid(row=2, column=1, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Bottom"))

		# ---
		b = Radiobutton(lframe, text=_("B-R"),
					variable = self.anchor,
					value = SE)
		b.grid(row=2, column=2, sticky=W)
		tkExtra.Balloon.set(b, _("Anchor camera to Bottom-Right corner"))

		# ===
		b = Radiobutton(lframe, text=_("Gantry"),
					variable = self.anchor,
					value = NONE)
		b.grid(row=3, column=0)
		tkExtra.Balloon.set(b, _("Anchor camera to Gantry location plus offset"))

		lframe.grid_columnconfigure(0, weight=1)
		lframe.grid_columnconfigure(1, weight=1)
		lframe.grid_columnconfigure(2, weight=1)

		# ==========
		lframe = LabelFrame(self, text=_("Scale"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		# ----
		Label(lframe, text="Scale:").grid(row=0, column=0, sticky=E)
		self.scale = tkExtra.FloatEntry(lframe, background="White")
		self.scale.grid(row=0, column=1, sticky=EW)
		self.scale.bind("<Return>",   self.updateValues)
		self.scale.bind("<KP_Enter>", self.updateValues)
		tkExtra.Balloon.set(self.scale, _("Camera scale pixels/unit"))

		# ----
		Label(lframe, text="Radius:").grid(row=1, column=0, sticky=E)
		self.radius = tkExtra.FloatEntry(lframe, background="White")
		self.radius.grid(row=1, column=1, sticky=EW)
		self.radius.bind("<Return>",   self.updateValues)
		self.radius.bind("<KP_Enter>", self.updateValues)
		tkExtra.Balloon.set(self.radius, _("Camera cross hair circular radius (units)"))

		# ----
		Label(lframe, text="Offset:").grid(row=2, column=0, sticky=E)
		self.dx = tkExtra.FloatEntry(lframe, background="White")
		self.dx.grid(row=2, column=1, sticky=EW)
		tkExtra.Balloon.set(self.dx, _("Camera offset from gantry"))

		self.dy = tkExtra.FloatEntry(lframe, background="White")
		self.dy.grid(row=2, column=2, sticky=EW)
		tkExtra.Balloon.set(self.dy, _("Camera offset from gantry"))

		Button(lframe, text="Update", command=self.updateValues).grid(row=3, column=0, columnspan=3)

		self.loadConfig()
		self.anchor.trace("w", self.updateValues)

	#-----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setStr(  "Camera", "aligncam_anchor",self.anchor.get())
		Utils.setFloat("Camera", "aligncam_r",     self.radius.get())
		Utils.setFloat("Camera", "aligncam_scale", self.scale.get())

	#-----------------------------------------------------------------------
	def loadConfig(self):
		self.anchor.set(Utils.getStr(  "Camera", "aligncam_anchor"))
		self.radius.set(Utils.getFloat("Camera", "aligncam_r"))
		self.scale.set( Utils.getFloat("Camera", "aligncam_scale"))
		self.updateValues()

	#-----------------------------------------------------------------------
	def updateValues(self, *args):
		self.app.canvas.cameraAnchor = self.anchor.get()
		try: self.app.canvas.cameraScale = float(self.scale.get())
		except ValueError: pass
		try: self.app.canvas.cameraR = float(self.radius.get())
		except ValueError: pass
		try: self.app.canvas.cameraDx = float(self.dx.get())
		except ValueError: pass
		try: self.app.canvas.cameraDy = float(self.dy.get())
		except ValueError: pass
		self.app.canvas.cameraUpdate()

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
					background="White",
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
					background="White",
					command=self.policyChange,
					width=16)
		self.toolWait.grid(row=row, column=col, columnspan=3, sticky=EW)
		self.toolWait.fill(TOOL_WAIT)
		self.toolWait.set(TOOL_WAIT[1])
		self.addWidget(self.toolWait)

		# ----
		row += 1
		col  = 1
		Label(lframe, text="MX").grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text="MY").grid(row=row, column=col, sticky=EW)
		col += 1
		Label(lframe, text="MZ").grid(row=row, column=col, sticky=EW)

		# --- Tool Change position ---
		row += 1
		col = 0
		Label(lframe, text=_("Change:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.changeX = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.changeX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeX, _("Manual tool change Machine X location"))
		self.addWidget(self.changeX)

		col += 1
		self.changeY = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.changeY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeY, _("Manual tool change Machine Y location"))
		self.addWidget(self.changeY)

		col += 1
		self.changeZ = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.changeZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.changeZ, _("Manual tool change Machine Z location"))
		self.addWidget(self.changeZ)

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
		self.probeX = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeX.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeX, _("Manual tool change Probing MX location"))
		self.addWidget(self.probeX)

		col += 1
		self.probeY = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeY.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeY, _("Manual tool change Probing MY location"))
		self.addWidget(self.probeY)

		col += 1
		self.probeZ = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeZ.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeZ, _("Manual tool change Probing MZ location"))
		self.addWidget(self.probeZ)

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
		self.probeDistance = tkExtra.FloatEntry(lframe, background="White", width=5)
		self.probeDistance.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeDistance,
				_("After a tool change distance to scan starting from ProbeZ"))
		self.addWidget(self.probeDistance)

		# --- Calibration ---
		row += 1
		col = 0
		Label(lframe, text=_("Calibration:")).grid(row=row, column=col, sticky=E)
		col += 1
		self.toolHeight = tkExtra.FloatEntry(lframe, background="White", width=5)
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
		Utils.setInt(  "Probe", "toolpolicy",  TOOL_POLICY.index(self.toolPolicy.get().encode("utf8")))
		Utils.setInt(  "Probe", "toolwait",    TOOL_WAIT.index(self.toolWait.get().encode("utf8")))
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
	def policyChange(self):
		CNC.toolPolicy = int(TOOL_POLICY.index(self.toolPolicy.get().encode("utf8")))

	#-----------------------------------------------------------------------
	def waitChange(self):
		CNC.toolWaitAfterProbe = int(TOOL_WAIT.index(self.toolWait.get().encode("utf8")))

	#-----------------------------------------------------------------------
	def getChange(self):
		self.changeX.set(CNC.vars["mx"])
		self.changeY.set(CNC.vars["my"])
		self.changeZ.set(CNC.vars["mz"])

	#-----------------------------------------------------------------------
	def getProbe(self):
		self.probeX.set(CNC.vars["mx"])
		self.probeY.set(CNC.vars["my"])
		self.probeZ.set(CNC.vars["mz"])

	#-----------------------------------------------------------------------
	def updateTool(self):
		state = self.toolHeight.cget("state")
		self.toolHeight.config(state=NORMAL)
		self.toolHeight.set(CNC.vars["toolheight"])
		self.toolHeight.config(state=state)

	#-----------------------------------------------------------------------
	def calibrate(self, event=None):
		ProbeCommonFrame.probeUpdate()
		self.set()

		cmd = "g91 %s f%s"%(CNC.vars["prbcmd"], CNC.vars["prbfeed"])

		lines = []
		lines.append("g53 g0 z[toolchangez]")
		lines.append("g53 g0 x[toolchangex] y[toolchangey]")
		lines.append("g53 g0 x[toolprobex] y[toolprobey]")
		lines.append("g53 g0 z[toolprobez]")
		lines.append("g91 [prbcmd] f[prbfeed] z[-tooldistance]")
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
	# FIXME should be replaced with the CNC.tolChange()
	#-----------------------------------------------------------------------
	def change(self, event=None):
		ProbeCommonFrame.probeUpdate()
		self.set()
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
