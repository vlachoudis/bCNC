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
	import tkMessageBox
except ImportError:
	from tkinter import *
	import tkinter.messagebox as tkMessageBox

import math

from CNC import CNC
import Utils
import Ribbon
import Sender
import tkExtra
import Unicode
import CNCRibbon
from Sender import ERROR_CODES
from CNC import WCS, DISTANCE_MODE, FEED_MODE, UNITS, PLANE

_LOWSTEP   = 0.0001
_HIGHSTEP  = 1000.0
_HIGHZSTEP = 10.0

#===============================================================================
# Connection Group
#===============================================================================
class ConnectionGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, "Connection", app,
			[("Hard Reset",  "reset",     app.hardReset)
			])
		self.grid2rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["home32"],
				text="Home",
				compound=TOP,
				anchor=W,
				command=app.home,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Perform a homing cycle [$H]")
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["unlock"],
				text="Unlock",
				compound=LEFT,
				anchor=W,
				command=app.unlock,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Unlock controller [$X]")
		self.addWidget(b)

		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["reset"],
				text="Reset",
				compound=LEFT,
				anchor=W,
				command=app.softReset,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Software reset of controller [ctrl-x]")
		self.addWidget(b)

#===============================================================================
# User Group
#===============================================================================
class UserGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "User", app)
		self.grid3rows()

		n = Utils.getInt("Buttons","n",6)
		for i in range(1,n):
			b = Utils.UserButton(self.frame, self.app, i,
					anchor=W,
					background=Ribbon._BACKGROUND)
			col,row = divmod(i-1,3)
			b.grid(row=row, column=col, sticky=NSEW)
			self.addWidget(b)

#===============================================================================
# Run Group
#===============================================================================
class RunGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Run", app)

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["start32"],
				text="Start",
				compound=TOP,
				command=app.run,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Run g-code commands from editor to controller")
		self.addWidget(b)

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["pause32"],
				text="Pause",
				compound=TOP,
				command=app.pause,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Pause running program. Sends either FEED_HOLD ! or CYCLE_START ~")

		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["stop32"],
				text="Stop",
				compound=TOP,
				command=app.stopRun,
				background=Ribbon._BACKGROUND)
		b.pack(side=LEFT, fill=BOTH)
		tkExtra.Balloon.set(b, "Pause running program and soft reset controller to empty the buffer.")

#===============================================================================
# DRO Frame
#===============================================================================
class DROFrame(CNCRibbon.PageFrame):
	dro_status = ('Helvetica',12,'bold')
	dro_wpos   = ('Helvetica',12,'bold')
	dro_mpos   = ('Helvetica',12)

	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "DRO", app)

		DROFrame.dro_status = Utils.getFont("dro_status", DROFrame.dro_status)
		DROFrame.dro_wpos   = Utils.getFont("dro_wpos",   DROFrame.dro_wpos)
		DROFrame.dro_mpos   = Utils.getFont("dro_mpos",   DROFrame.dro_mpos)

		row = 0
		col = 0
		Label(self,text="Status:").grid(row=row,column=col,sticky=E)
		col += 1
		self.state = Button(self,
				text=Sender.NOT_CONNECTED,
				font=DROFrame.dro_status,
				command=self.showState,
				cursor="hand1",
				background=Sender.STATECOLOR[Sender.NOT_CONNECTED],
				activebackground="LightYellow")
		self.state.grid(row=row,column=col, columnspan=3, sticky=EW)
		tkExtra.Balloon.set(self.state, "Show current state of the machine")

		row += 1
		col = 0
		Label(self,text="WPos:").grid(row=row,column=col,sticky=E)

		# work
		col += 1
		self.xwork = tkExtra.FloatEntry(self,
					font=DROFrame.dro_wpos,
					background="White",
					relief=FLAT,
					borderwidth=0,
					justify=RIGHT)
		self.xwork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.xwork, "X work position (click to set)")
		self.xwork.bind('<FocusIn>',  self.workFocus)
		self.xwork.bind('<Return>',   self.setX)
		self.xwork.bind('<KP_Enter>', self.setX)

		# ---
		col += 1
		self.ywork = tkExtra.FloatEntry(self,
					font=DROFrame.dro_wpos,
					background="White",
					relief=FLAT,
					borderwidth=0,
					justify=RIGHT)
		self.ywork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.ywork, "Y work position (click to set)")
		self.ywork.bind('<FocusIn>',  self.workFocus)
		self.ywork.bind('<Return>',   self.setY)
		self.ywork.bind('<KP_Enter>', self.setY)

		# ---
		col += 1
		self.zwork = tkExtra.FloatEntry(self,
					font=DROFrame.dro_wpos,
					background="White",
					relief=FLAT,
					borderwidth=0,
					justify=RIGHT)
		self.zwork.grid(row=row,column=col,padx=1,sticky=EW)
		tkExtra.Balloon.set(self.zwork, "Z work position (click to set)")
		self.zwork.bind('<FocusIn>',  self.workFocus)
		self.zwork.bind('<Return>',   self.setZ)
		self.zwork.bind('<KP_Enter>', self.setZ)

		# Machine
		row += 1
		col = 0
		Label(self,text="MPos:").grid(row=row,column=col,sticky=E)

		col += 1
		self.xmachine = Label(self, font=DROFrame.dro_mpos, background="White",anchor=E)
		self.xmachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.ymachine = Label(self, font=DROFrame.dro_mpos, background="White",anchor=E)
		self.ymachine.grid(row=row,column=col,padx=1,sticky=EW)

		col += 1
		self.zmachine = Label(self, font=DROFrame.dro_mpos, background="White", anchor=E)
		self.zmachine.grid(row=row,column=col,padx=1,sticky=EW)

		# Set buttons
		row += 1
		col = 1

		self.xzero = Button(self, text="X=0",
				command=self.setX0,
				activebackground="LightYellow",
				padx=2, pady=1)
		self.xzero.grid(row=row, column=col, pady=0, sticky=EW)
		tkExtra.Balloon.set(self.xzero, "Set X coordinate to zero (or to typed coordinate in WPos)")
		self.addWidget(self.xzero)

		col += 1
		self.yzero = Button(self, text="Y=0",
				command=self.setY0,
				activebackground="LightYellow",
				padx=2, pady=1)
		self.yzero.grid(row=row, column=col, pady=0, sticky=EW)
		tkExtra.Balloon.set(self.yzero, "Set Y coordinate to zero (or to typed coordinate in WPos)")
		self.addWidget(self.yzero)

		col += 1
		self.zzero = Button(self, text="Z=0",
				command=self.setZ0,
				activebackground="LightYellow",
				padx=2, pady=1)
		self.zzero.grid(row=row, column=col, pady=0, sticky=EW)
		tkExtra.Balloon.set(self.zzero, "Set Z coordinate to zero (or to typed coordinate in WPos)")
		self.addWidget(self.zzero)

		self.grid_columnconfigure(1, weight=1)
		self.grid_columnconfigure(2, weight=1)
		self.grid_columnconfigure(3, weight=1)

	#----------------------------------------------------------------------
	def updateState(self):
		msg = self.app._msg or CNC.vars["state"]
		self.state.config(text=msg, background=CNC.vars["color"])

	#----------------------------------------------------------------------
	def updateCoords(self):
		try:
			focus = self.focus_get()
		except:
			focus = None
		if focus is not self.xwork: self.xwork.set(CNC.vars["wx"])
		if focus is not self.ywork: self.ywork.set(CNC.vars["wy"])
		if focus is not self.zwork: self.zwork.set(CNC.vars["wz"])

		self.xmachine["text"] = CNC.vars["mx"]
		self.ymachine["text"] = CNC.vars["my"]
		self.zmachine["text"] = CNC.vars["mz"]

	#----------------------------------------------------------------------
	# Do not give the focus while we are running
	#----------------------------------------------------------------------
	def workFocus(self, event=None):
		if self.app.running:
			self.app.focus_set()

	#----------------------------------------------------------------------
	def setX0(self, event=None):
		self._wcsSet("0",None,None)

	#----------------------------------------------------------------------
	def setY0(self, event=None):
		self._wcsSet(None,"0",None)

	#----------------------------------------------------------------------
	def setZ0(self, event=None):
		self._wcsSet(None,None,"0")

	#----------------------------------------------------------------------
	def setX(self, event=None):
		if self.app.running: return
		self._wcsSet(self.xwork.get(),None,None)

	#----------------------------------------------------------------------
	def setY(self, event=None):
		if self.app.running: return
		self._wcsSet(None,self.ywork.get(),None)

	#----------------------------------------------------------------------
	def setZ(self, event=None):
		if self.app.running: return
		self._wcsSet(None,None,self.zwork.get())

	#----------------------------------------------------------------------
	def _wcsSet(self, x, y, z):
		global wcsvar
		p = wcsvar.get()
		if p<6:
			cmd = "G10L20P%d"%(p+1)
		elif p==6:
			cmd = "G28.1"
		elif p==7:
			cmd = "G30.1"
		elif p==8:
			cmd = "G92"

		if x is not None: cmd += "X"+str(x)
		if y is not None: cmd += "Y"+str(y)
		if z is not None: cmd += "Z"+str(z)
		self.sendGrbl(cmd+"\n$#\n")
		self.event_generate("<<Status>>",
			data="Set workspace %s to X%s Y%s Z%s"%(WCS[p],str(x),str(y),str(z)))
		self.event_generate("<<CanvasFocus>>")

	#----------------------------------------------------------------------
	def showState(self):
		err = CNC.vars["errline"]
		if err:
			msg  = "Last error: %s\n"%(CNC.vars["errline"])
		else:
			msg = ""

		state = CNC.vars["state"]
		msg += ERROR_CODES.get(state,
				"No info available.\nPlease contact the author.")
		tkMessageBox.showinfo("State: %s"%(state), msg, parent=self)

#===============================================================================
# ControlFrame
#===============================================================================
class ControlFrame(CNCRibbon.PageLabelFrame):
	def __init__(self, master, app):
		CNCRibbon.PageLabelFrame.__init__(self, master, "Control", app)

		row,col = 0,0
		Label(self, text="Z").grid(row=row, column=col)

		col += 3
		Label(self, text="Y").grid(row=row, column=col)

		# ---
		row += 1
		col = 0

		width=3
		height=2

		b = Button(self, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
					command=self.moveZup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Z")
		self.addWidget(b)

		col += 2
		b = Button(self, text=Unicode.UPPER_LEFT_TRIANGLE,
					command=self.moveXdownYup,
					width=width, height=height,
					activebackground="LightYellow")

		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X +Y")
		self.addWidget(b)

		col += 1
		b = Button(self, text=Unicode.BLACK_UP_POINTING_TRIANGLE,
					command=self.moveYup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +Y")
		self.addWidget(b)

		col += 1
		b = Button(self, text=Unicode.UPPER_RIGHT_TRIANGLE,
					command=self.moveXupYup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X +Y")
		self.addWidget(b)

		col += 2
		b = Button(self, text=u"\u00D710",
				command=self.mulStep,
				width=3,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Multiply step by 10")
		self.addWidget(b)

		col += 1
		b = Button(self, text="+",
				command=self.incStep,
				width=3,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(b, "Increase step by 1 unit")
		self.addWidget(b)

		# ---
		row += 1

		col = 1
		Label(self, text="X", width=3, anchor=E).grid(row=row, column=col, sticky=E)

		col += 1
		b = Button(self, text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
					command=self.moveXdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X")
		self.addWidget(b)

		col += 1
		b = Utils.UserButton(self, self.app, 0, text=Unicode.LARGE_CIRCLE,
					command=self.go2origin,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move to Origin.\nUser configurable button.\nRight click to configure.")
		self.addWidget(b)

		col += 1
		b = Button(self, text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
					command=self.moveXup,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X")
		self.addWidget(b)

		# --
		col += 1
		Label(self,"",width=2).grid(row=row,column=col)

		col += 1
		self.step = tkExtra.Combobox(self, width=6, background="White")
		self.step.grid(row=row, column=col, columnspan=2, sticky=EW)
		self.step.set(Utils.config.get("Control","step"))
		self.step.fill(["0.001",
				"0.005",
				"0.01",
				"0.05",
				"0.1",
				"0.5",
				"1",
				"5",
				"10",
				"50",
				"100",
				"500"])
		tkExtra.Balloon.set(self.step, "Step for every move operation")
		self.addWidget(self.step)

		# -- Separate zstep --
		try:
			zstep = Utils.config.get("Control","zstep")
			self.zstep = tkExtra.Combobox(self, width=1, background="White")
			self.zstep.grid(row=row, column=0, columnspan=1, sticky=EW)
			self.zstep.set(zstep)
			self.zstep.fill(["0.001",
					"0.005",
					"0.01",
					"0.05",
					"0.1",
					"0.5",
					"1",
					"5",
					"10"])
			tkExtra.Balloon.set(self.zstep, "Step for Z move operation")
			self.addWidget(self.zstep)
		except:
			self.zstep = self.step

		# ---
		row += 1
		col = 0

		b = Button(self, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					command=self.moveZdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Z")
		self.addWidget(b)

		col += 2
		b = Button(self, text=Unicode.LOWER_LEFT_TRIANGLE,
					command=self.moveXdownYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -X -Y")
		self.addWidget(b)

		col += 1
		b = Button(self, text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
					command=self.moveYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move -Y")
		self.addWidget(b)

		col += 1
		b = Button(self, text=Unicode.LOWER_RIGHT_TRIANGLE,
					command=self.moveXupYdown,
					width=width, height=height,
					activebackground="LightYellow")
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, "Move +X -Y")
		self.addWidget(b)

		col += 2
		b = Button(self, text=u"\u00F710",
					command=self.divStep,
					padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Divide step by 10")
		self.addWidget(b)

		col += 1
		b = Button(self, text="-",
					command=self.decStep,
					padx=1, pady=1)
		b.grid(row=row, column=col, sticky=EW+N)
		tkExtra.Balloon.set(b, "Decrease step by 1 unit")
		self.addWidget(b)

		#self.grid_columnconfigure(6,weight=1)
		try:
#			self.grid_anchor(CENTER)
			self.tk.call("grid","anchor",self,CENTER)
		except TclError:
			pass

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Control", "step", self.step.get())
		if self.zstep is not self.step:
			Utils.setFloat("Control", "zstep", self.zstep.get())

	#----------------------------------------------------------------------
	# Jogging
	#----------------------------------------------------------------------
	def moveXup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%s\nG90\n"%(self.step.get()))

	def moveXdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%s\nG90\n"%(self.step.get()))

	def moveYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Y%s\nG90\n"%(self.step.get()))

	def moveYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Y-%s\nG90\n"%(self.step.get()))

	def moveXdownYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%sY%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXdownYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X-%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveXupYdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0X%sY-%s\nG90\n"%(self.step.get(),self.step.get()))

	def moveZup(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z%s\nG90\n"%(self.zstep.get()))

	def moveZdown(self, event=None):
		if event is not None and not self.acceptKey(): return
		self.sendGrbl("G91G0Z-%s\nG90\n"%(self.zstep.get()))

	def go2origin(self, event=None):
		self.sendGrbl("G90G0X0Y0Z0\n")

	#----------------------------------------------------------------------
	def setStep(self, s, zs=None):
		self.step.set("%.4g"%(s))
		if self.zstep is self.step or zs is None:
			self.event_generate("<<Status>>",data="Step: %g"%(s))
		else:
			self.zstep.set("%.4g"%(zs))
			self.event_generate("<<Status>>",data="Step: %g    Zstep:%g "%(s,zs))

	@staticmethod
	def _stepPower(step):
		try:
			step = float(step)
			if step <= 0.0: step = 1.0
		except:
			step = 1.0
		power = math.pow(10.0,math.floor(math.log10(step)))
		return round(step/power)*power, power

	def incStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = ControlFrame._stepPower(self.step.get())
		s = step+power
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		if self.zstep is not self.step:
			step, power = ControlFrame._stepPower(self.zstep.get())
			zs = step+power
			if zs<_LOWSTEP: zs = _LOWSTEP
			elif zs>_HIGHZSTEP: zs = _HIGHZSTEP
		else:
			zs=None
		self.setStep(s, zs)

	def decStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = ControlFrame._stepPower(self.step.get())
		s = step-power
		if s<=0.0: s = step-power/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		if self.zstep is not self.step:
			step, power = ControlFrame._stepPower(self.zstep.get())
			zs = step-power
			if zs<=0.0: zs = step-power/10.0
			if zs<_LOWSTEP: zs = _LOWSTEP
			elif zs>_HIGHZSTEP: zs = _HIGHZSTEP
		else:
			zs=None
		self.setStep(s, zs)

	def mulStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = ControlFrame._stepPower(self.step.get())
		s = step*10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		if self.zstep is not self.step:
			step, power = ControlFrame._stepPower(self.zstep.get())
			zs = step*10.0
			if zs<_LOWSTEP: zs = _LOWSTEP
			elif zs>_HIGHZSTEP: zs = _HIGHZSTEP
		else:
			zs=None
		self.setStep(s, zs)

	def divStep(self, event=None):
		if event is not None and not self.acceptKey(): return
		step, power = ControlFrame._stepPower(self.step.get())
		s = step/10.0
		if s<_LOWSTEP: s = _LOWSTEP
		elif s>_HIGHSTEP: s = _HIGHSTEP
		if self.zstep is not self.step:
			step, power = ControlFrame._stepPower(self.zstep.get())
			zs = step/10.0
			if zs<_LOWSTEP: zs = _LOWSTEP
			elif zs>_HIGHZSTEP: zs = _HIGHZSTEP
		else:
			zs=None
		self.setStep(s, zs)

#===============================================================================
# StateFrame
#===============================================================================
class StateFrame(CNCRibbon.PageExLabelFrame):
	def __init__(self, master, app):
		global wcsvar
		CNCRibbon.PageExLabelFrame.__init__(self, master, "State", app)
		self._gUpdate = False

		# State
		f = Frame(self())
		f.pack(side=TOP, fill=X)

		# ===
		col,row=0,0
		f2 = Frame(f)
		f2.grid(row=row, column=col, columnspan=5,sticky=EW)
		for p,w in enumerate(WCS):
			col += 1
			b = Radiobutton(f2, text=w,
					foreground="DarkRed",
					font = "Helvetica,14",
					padx=1, pady=1,
					variable=wcsvar,
					value=p,
					indicatoron=FALSE,
					activebackground="LightYellow",
					command=self.wcsChange)
			b.pack(side=LEFT, fill=X, expand=YES)
			tkExtra.Balloon.set(b, "Switch to workspace %s"%(w))
			self.addWidget(b)

		# Absolute or relative mode
		row += 1
		col = 0
		Label(f, text="Distance:").grid(row=row, column=col, sticky=E)
		col += 1
		self.distance = tkExtra.Combobox(f, True,
					command=self.distanceChange,
					width=5,
					background="White")
		self.distance.fill(sorted(DISTANCE_MODE.values()))
		self.distance.grid(row=row, column=col, columnspan=2, sticky=EW)
		tkExtra.Balloon.set(self.distance, "Distance Mode [G90,G91]")
		self.addWidget(self.distance)

		# populate gstate dictionary
		self.gstate = {}	# $G state results widget dictionary
		for k,v in DISTANCE_MODE.items():
			self.gstate[k] = (self.distance, v)

		# Units mode
		col += 2
		Label(f, text="Units:").grid(row=row, column=col, sticky=E)
		col += 1
		self.units = tkExtra.Combobox(f, True,
					command=self.unitsChange,
					width=5,
					background="White")
		self.units.fill(sorted(UNITS.values()))
		self.units.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.units, "Units [G20, G21]")
		for k,v in UNITS.items(): self.gstate[k] = (self.units, v)
		self.addWidget(self.units)

		# Tool
		row += 1
		col = 0
		Label(f, text="Tool:").grid(row=row, column=col, sticky=E)

		col += 1
		self.toolEntry = tkExtra.IntegerEntry(f, background="White", width=5)
		self.toolEntry.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.toolEntry, "Tool number [T#]")
		self.addWidget(self.toolEntry)

		col += 1
		b = Button(f, text="set",
				command=self.setTool,
				padx=1, pady=1)
		b.grid(row=row, column=col, sticky=W)
		self.addWidget(b)

		# Plane
		col += 1
		Label(f, text="Plane:").grid(row=row, column=col, sticky=E)
		col += 1
		self.plane = tkExtra.Combobox(f, True,
					command=self.planeChange,
					width=5,
					background="White")
		self.plane.fill(sorted(PLANE.values()))
		self.plane.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.plane, "Plane [G17,G18,G19]")
		self.addWidget(self.plane)

		for k,v in PLANE.items(): self.gstate[k] = (self.plane, v)

		# Feed mode
		row += 1
		col = 0
		Label(f, text="Feed:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedRate = tkExtra.FloatEntry(f, background="White", width=5)
		self.feedRate.grid(row=row, column=col, sticky=EW)
		self.feedRate.bind('<Return>',   self.setFeedRate)
		self.feedRate.bind('<KP_Enter>', self.setFeedRate)
		tkExtra.Balloon.set(self.feedRate, "Feed Rate [F#]")
		self.addWidget(self.feedRate)

		col += 1
		b = Button(f, text="set",
				command=self.setFeedRate,
				padx=1, pady=1)
		b.grid(row=row, column=col, columnspan=2, sticky=W)
		self.addWidget(b)

		col += 1
		Label(f, text="Mode:").grid(row=row, column=col, sticky=E)

		col += 1
		self.feedMode = tkExtra.Combobox(f, True,
					command=self.feedModeChange,
					width=5,
					background="White")
		self.feedMode.fill(sorted(FEED_MODE.values()))
		self.feedMode.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.feedMode, "Feed Mode [G93, G94, G95]")
		for k,v in FEED_MODE.items(): self.gstate[k] = (self.feedMode, v)
		self.addWidget(self.feedMode)

		# ---
		f.grid_columnconfigure(1, weight=1)
		f.grid_columnconfigure(4, weight=1)

		# Spindle
		f = Frame(self())
		f.pack(side=BOTTOM, fill=X)

		self.override = IntVar()
		self.override.set(100)
		self.spindle = BooleanVar()
		self.spindleSpeed = IntVar()

		col,row=0,0
		b = Button(f,	text="Feed\nOverride:",
				command=self.resetOverride,
				padx=1,
				pady=0,
				justify=CENTER)
		b.grid(row=row, column=col, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Reset Feed Override to 100%")

		col += 1
		b = Scale(f,
				command=self.overrideControl,
				variable=self.override,
				showvalue=True,
				orient=HORIZONTAL,
				from_=25,
				to_=200,
				resolution=5)
		b.grid(row=row, column=col, columnspan=4, sticky=EW)
		tkExtra.Balloon.set(b, "Set Feed Override")

		# ---
		row += 1
		col = 0
		b = Checkbutton(f, text="Spindle",
				image=Utils.icons["spinningtop"],
				command=self.spindleControl,
				compound=LEFT,
				indicatoron=False,
				variable=self.spindle,
				padx=1,
				pady=0)
		tkExtra.Balloon.set(b, "Start/Stop spindle (M3/M5)")
		b.grid(row=row, column=col, pady=0, sticky=NSEW)
		self.addWidget(b)

		col += 1
		b = Scale(f,	variable=self.spindleSpeed,
				command=self.spindleControl,
				showvalue=True,
				orient=HORIZONTAL,
				from_=Utils.config.get("CNC","spindlemin"),
				to_=Utils.config.get("CNC","spindlemax"))
		tkExtra.Balloon.set(b, "Set spindle RPM")
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)

		f.grid_columnconfigure(1, weight=1)

	#----------------------------------------------------------------------
	def overrideControl(self, event=None):
		CNC.vars["override"] = self.override.get()

	#----------------------------------------------------------------------
	def resetOverride(self, event=None):
		self.override.set(100)
		self.overrideControl()

	#----------------------------------------------------------------------
	def _gChange(self, value, dictionary):
		for k,v in dictionary.items():
			if v==value:
				self.sendGrbl("%s\n"%(k))
				return

	#----------------------------------------------------------------------
	def distanceChange(self):
		if self._gUpdate: return
		self._gChange(self.distance.get(), DISTANCE_MODE)

	#----------------------------------------------------------------------
	def unitsChange(self):
		if self._gUpdate: return
		self._gChange(self.units.get(), UNITS)

	#----------------------------------------------------------------------
	def feedModeChange(self):
		if self._gUpdate: return
		self._gChange(self.feedMode.get(), FEED_MODE)

	#----------------------------------------------------------------------
	def planeChange(self):
		if self._gUpdate: return
		self._gChange(self.plane.get(), PLANE)

	#----------------------------------------------------------------------
	def setFeedRate(self, event=None):
		if self._gUpdate: return
		try:
			feed = float(self.feedRate.get())
			self.sendGrbl("F%g\n"%(feed))
			self.event_generate("<<CanvasFocus>>")
		except ValueError:
			pass

	#----------------------------------------------------------------------
	def setTool(self, event=None):
		pass

	#----------------------------------------------------------------------
	def spindleControl(self, event=None):
		if self._gUpdate: return
		# Avoid sending commands before unlocking
		if CNC.vars["state"] in (Sender.CONNECTED, Sender.NOT_CONNECTED): return
		if self.spindle.get():
			self.sendGrbl("M3 S%d\n"%(self.spindleSpeed.get()))
		else:
			self.sendGrbl("M5\n")

	#----------------------------------------------------------------------
	def updateG(self):
		global wcsvar
		self._gUpdate = True
		try:
			focus = self.focus_get()
		except:
			focus = None

		wcsvar.set(WCS.index(CNC.vars["WCS"]))
		self.feedRate.set(str(CNC.vars["feed"]))
		self.feedMode.set(FEED_MODE[CNC.vars["feedmode"]])
		self.spindle.set(CNC.vars["spindle"]=="M3")
		self.spindleSpeed.set(int(CNC.vars["rpm"]))
		self.toolEntry.set(CNC.vars["tool"])
		self.units.set(UNITS[CNC.vars["units"]])
		self.distance.set(DISTANCE_MODE[CNC.vars["distance"]])
		self.plane.set(PLANE[CNC.vars["plane"]])

		self._gUpdate = False

	#----------------------------------------------------------------------
	def wcsChange(self):
		global wcsvar
		self.sendGrbl(WCS[wcsvar.get()]+"\n$G\n")

#===============================================================================
# Control Page
#===============================================================================
class ControlPage(CNCRibbon.Page):
	"""CNC communication and control"""

	_name_ = "Control"
	_icon_ = "control"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		global wcsvar
		wcsvar = IntVar()
		wcsvar.set(0)

		self._register((ConnectionGroup, UserGroup, RunGroup),
			(DROFrame, ControlFrame, StateFrame))
