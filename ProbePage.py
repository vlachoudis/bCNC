# -*- coding: ascii -*-
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
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe", app)

		self.tab = StringVar()
		self.tab.set("Probe")

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
				image=Utils.icons["target32"],
				text=_("Center"),
				compound=TOP,
				variable=self.tab,
				value="Center",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Center probing using a ring"))

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["setsquare32"],
				text=_("Square"),
				compound=TOP,
				variable=self.tab,
				state=DISABLED,
				value="Square",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Probe X/Y axis by using a set square probe"))

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
				image=Utils.icons["endmill32"],
				text=_("Tool"),
				compound=TOP,
				variable=self.tab,
				value="Tool",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=5, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Setup probing for manual tool change"))

#===============================================================================
# Probe Group
#===============================================================================
class ProbeGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Probe", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2

		b = Ribbon.LabelButton(self.frame, self, "<<Probe>>",
				image=Utils.icons["gear32"],
				text=_("Probe"),
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a single probe cycle"))

#===============================================================================
# Center Group
#===============================================================================
class CenterGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Center", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2

		b = Ribbon.LabelButton(self.frame, self, "<<ProbeCenter>>",
				image=Utils.icons["gear32"],
				text=_("Center"),
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, _("Perform a center probe cycle"))

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

	#----------------------------------------------------------------------
	def tloSet(self, event=None):
		try:
			CNC.vars["TLO"] = float(ProbeCommonFrame.tlo.get())
			cmd = "g43.1z"+(ProbeCommonFrame.tlo.get())
			self.sendGrbl(cmd+"\n")
		except:
			pass

	#----------------------------------------------------------------------
	@staticmethod
	def probeUpdate():
		try:
			CNC.vars["prbfeed"] = float(ProbeCommonFrame.probeFeed.get())
			CNC.vars["prbcmd"]  = ProbeCommonFrame.probeCmd.get().split()[0]
			return False
		except:
			return True

	#----------------------------------------------------------------------
	def updateTlo(self):
		try:
			if self.focus_get() is not ProbeCommonFrame.tlo:
				state = ProbeCommonFrame.tlo.cget("state")
				state = ProbeCommonFrame.tlo["state"] = NORMAL
				ProbeCommonFrame.tlo.set(str(CNC.vars.get("TLO","")))
				state = ProbeCommonFrame.tlo["state"] = state
		except:
			pass

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "feed", ProbeCommonFrame.probeFeed.get())
		Utils.setFloat("Probe", "tlo",  ProbeCommonFrame.tlo.get())
		Utils.setFloat("Probe", "cmd",  ProbeCommonFrame.probeCmd.get().split()[0])

	#----------------------------------------------------------------------
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

		# WorkSpace -> Probe
		lframe = LabelFrame(self, text=_("Probe"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		row,col = 0,0
		Label(lframe, text=_("Probe:")).grid(row=row, column=col, sticky=E)

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
		Label(lframe, text=_("Pos:")).grid(row=row, column=col, sticky=E)

		col += 1
		self.probeXdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeXdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeXdir, _("Probe along X direction"))
		self.addWidget(self.probeXdir)

		col += 1
		self.probeYdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeYdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeYdir, _("Probe along Y direction"))
		self.addWidget(self.probeYdir)

		col += 1
		self.probeZdir = tkExtra.FloatEntry(lframe, background="White")
		self.probeZdir.grid(row=row, column=col, sticky=EW+S)
		tkExtra.Balloon.set(self.probeZdir, _("Probe along Z direction"))
		self.addWidget(self.probeZdir)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		self.loadConfig()

	#----------------------------------------------------------------------
	def loadConfig(self):
		self.probeXdir.set(Utils.getStr("Probe","x"))
		self.probeYdir.set(Utils.getStr("Probe","y"))
		self.probeZdir.set(Utils.getStr("Probe","z"))

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "x",    self.probeXdir.get())
		Utils.setFloat("Probe", "y",    self.probeYdir.get())
		Utils.setFloat("Probe", "z",    self.probeZdir.get())

	#----------------------------------------------------------------------
	def updateProbe(self):
		try:
			self._probeX["text"] = CNC.vars.get("prbx")
			self._probeY["text"] = CNC.vars.get("prby")
			self._probeZ["text"] = CNC.vars.get("prbz")
		except:
			pass

	#----------------------------------------------------------------------
	# Probe one Point
	#----------------------------------------------------------------------
	def probe(self, event=None):
		if ProbeCommonFrame.probeUpdate():
			tkMessageBox.showerror(_("Probe Error"),
				_("Invalid probe feed rate"),
				parent=self)
			return
		cmd = CNC.vars["prbcmd"]
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
		if v != "":
			cmd += "F"+str(CNC.vars["prbfeed"])

		if ok:
			self.sendGrbl(cmd+"\n")
		else:
			tkMessageBox.showerror(_("Probe Error"),
					_("At least one probe direction should be specified"))

#===============================================================================
# Center Frame
#===============================================================================
class ProbeCenterFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Center", app)

		# WorkSpace -> Probe
		lframe = LabelFrame(self, text=_("Center"), foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		Label(lframe, text=_("Diameter:")).pack(side=LEFT)
		self.diameter = tkExtra.FloatEntry(lframe, background="White")
		self.diameter.pack(side=LEFT, fill=X)
		tkExtra.Balloon.set(self.diameter, _("Probing ring internal diameter"))
		self.addWidget(self.diameter)

		self.loadConfig()

	#----------------------------------------------------------------------
	def loadConfig(self):
		self.diameter.set(Utils.getStr("Probe", "center"))

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "center",  self.diameter.get())

	#----------------------------------------------------------------------
	# Probe one Point
	#----------------------------------------------------------------------
	def probe(self, event=None):
		cmd = "g91 %s f%s"%(CNC.vars["prbcmd"], CNC.vars["prbfeed"])
		try:
			diameter = abs(float(self.diameter.get()))
		except:
			diameter = 0.0

		if diameter < 0.001:
			tkMessageBox.showerror(_("Probe Center Error"),
					_("Invalid diameter entered"),
					parent=self)
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
					background="gray95", width=5)
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
					background="gray95", width=5)
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

	#----------------------------------------------------------------------
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

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "xmin", self.probeXmin.get())
		Utils.setFloat("Probe", "xmax", self.probeXmax.get())
		Utils.setInt(  "Probe", "xn",   self.probeXbins.get())
		Utils.setFloat("Probe", "ymin", self.probeYmin.get())
		Utils.setFloat("Probe", "ymax", self.probeYmax.get())
		Utils.setInt(  "Probe", "yn",   self.probeYbins.get())
		Utils.setFloat("Probe", "zmin", self.probeZmin.get())
		Utils.setFloat("Probe", "zmax", self.probeZmax.get())

	#----------------------------------------------------------------------
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

	#----------------------------------------------------------------------
	def getMargins(self, event=None):
		self.probeXmin.set(str(CNC.vars["xmin"]))
		self.probeXmax.set(str(CNC.vars["xmax"]))
		self.probeYmin.set(str(CNC.vars["ymin"]))
		self.probeYmax.set(str(CNC.vars["ymax"]))
		self.draw()

	#----------------------------------------------------------------------
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
						parent=self)
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
						parent=self)
			error = True

		try:
			probe.zmin  = float(self.probeZmin.get())
			probe.zmax  = float(self.probeZmax.get())
		except ValueError:
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
					_("Invalid Z probing region"),
					parent=self)
			error = True

		if ProbeCommonFrame.probeUpdate():
			if verbose:
				tkMessageBox.showerror(_("Probe Error"),
					_("Invalid probe feed rate"),
					parent=self)
			error = True

		return error

	#----------------------------------------------------------------------
	def draw(self):
		if not self.change():
			self.event_generate("<<DrawProbe>>")

	#----------------------------------------------------------------------
	def setZero(self, event=None):
		x = CNC.vars["wx"]
		y = CNC.vars["wy"]
		self.app.gcode.probe.setZero(x,y)
		self.draw()

	#----------------------------------------------------------------------
	def clear(self, event=None):
		self.app.gcode.probe.clear()
		self.draw()

	#----------------------------------------------------------------------
	# Probe an X-Y area
	#----------------------------------------------------------------------
	def scan(self, event=None):
		if self.change(): return

		# absolute
		probe = self.app.gcode.probe
		probe.clear()
		self.app.run(lines=probe.scan())

#===============================================================================
# Tool Group
#===============================================================================
class ToolGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Tool", app)
		self.label["background"] = Ribbon._BACKGROUND_GROUP2

		b = Ribbon.LabelButton(self.frame, self, "<<ToolCalibrate>>",
				image=Utils.icons["probe32"],
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
				command=self.probe,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(b, _("Perform a calibration probing to determine the height"))
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=1)
		lframe.grid_columnconfigure(2,weight=1)
		lframe.grid_columnconfigure(3,weight=1)

		self.loadConfig()

	#----------------------------------------------------------------------
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

	#----------------------------------------------------------------------
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

	#----------------------------------------------------------------------
	def set(self):
		self.policyChange()
		try:
			CNC.vars["toolchangex"]  = float(self.changeX.get())
			CNC.vars["toolchangey"]  = float(self.changeY.get())
			CNC.vars["toolchangez"]  = float(self.changeZ.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool change position"),
					parent=self)
			return

		try:
			CNC.vars["toolprobex"]   = float(self.probeX.get())
			CNC.vars["toolprobey"]   = float(self.probeY.get())
			CNC.vars["toolprobez"]   = float(self.probeZ.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool probe location"),
					parent=self)
			return

		try:
			CNC.vars["tooldistance"] = abs(float(self.probeDistance.get()))
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool scanning distance entered"),
					parent=self)
			return

		try:
			CNC.vars["toolheight"]   = float(self.toolHeight.get())
		except:
			tkMessageBox.showerror(_("Probe Tool Change Error"),
					_("Invalid tool height or not calibrated"),
					parent=self)
			return

	#----------------------------------------------------------------------
	def policyChange(self):
		CNC.toolPolicy = int(TOOL_POLICY.index(self.toolPolicy.get()))

	#----------------------------------------------------------------------
	def waitChange(self):
		CNC.toolWaitAfterProbe = int(TOOL_WAIT.index(self.toolWait.get()))

	#----------------------------------------------------------------------
	def getChange(self):
		self.changeX.set(CNC.vars["mx"])
		self.changeY.set(CNC.vars["my"])
		self.changeZ.set(CNC.vars["mz"])

	#----------------------------------------------------------------------
	def getProbe(self):
		self.probeX.set(CNC.vars["mx"])
		self.probeY.set(CNC.vars["my"])
		self.probeZ.set(CNC.vars["mz"])

	#----------------------------------------------------------------------
	def updateTool(self):
		state = self.toolHeight.cget("state")
		self.toolHeight.config(state=NORMAL)
		self.toolHeight.set(CNC.vars["toolheight"])
		self.toolHeight.config(state=state)

	#----------------------------------------------------------------------
	def probe(self, event=None):
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

	#----------------------------------------------------------------------
	# FIXME should be replaced with the CNC.tolChange()
	#----------------------------------------------------------------------
	def change(self, event=None):
		ProbeCommonFrame.probeUpdate()
		self.set()
		lines = self.app.cnc.toolChange(0)
#		cmd = "g91 %s f%s"%(CNC.vars["prbcmd"], CNC.vars["prbfeed"])
#		lines = []
#		lines.append("g53 g0 z[toolchangez]")
#		lines.append("g53 g0 x[toolchangex] y[toolchangey]")
#		lines.append("%wait")
#		lines.append("%pause Manual Tool change")
#		lines.append("g53 g0 x[toolprobex] y[toolprobey]")
#		lines.append("g53 g0 z[toolprobez]")
#		lines.append("g91 [prbcmd] f[prbfeed] z[-tooldistance]")
##		lines.append("%wait")
#		p = WCS.index(CNC.vars["WCS"])+1
#		lines.append("G10L20P%d z[toolheight]"%(p))
#		lines.append("%wait")
##		lines.append("g53g0z-2.0")
##		lines.append("g53g0x-200.0y-100.0")
#		lines.append("g53 g0 z[toolchangez]")
#		lines.append("g53 g0 x[toolchangex] y[toolchangey]")
#		lines.append("g90")
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
	"""Probe configuration and probing"""

	_name_ = "Probe"
	_icon_ = "measure"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((ProbeTabGroup, ProbeGroup, CenterGroup, AutolevelGroup, ToolGroup),
			(ProbeCommonFrame, ProbeFrame, ProbeCenterFrame, AutolevelFrame, ToolFrame))

		self.tabGroup = CNCRibbon.Page.groups["Probe"]
		self.tabGroup.tab.set("Probe")
		self.tabGroup.tab.trace('w', self.tabChange)

	#----------------------------------------------------------------------
	def tabChange(self, a, b, c):
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
