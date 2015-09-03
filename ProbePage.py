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

from CNC import CNC
import Utils
import Ribbon
import tkExtra
import CNCRibbon

#===============================================================================
# Probe Tab Group
#===============================================================================
class ProbeTabGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe", app)
		self.grid3rows()

		self.tab = StringVar()
		self.tab.set("Probe")

		# ---
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["probe32"],
				text="Probe",
				compound=TOP,
				variable=self.tab,
				value="Probe",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Simple probing along a direction")

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["target32"],
				text="Center",
				compound=TOP,
				variable=self.tab,
				value="Center",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Center probing using a ring")

		# ---
		col += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["level32"],
				text="Autolevel",
				compound=TOP,
				variable=self.tab,
				value="Autolevel",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Autolevel Z surface")

#===============================================================================
# Probe Group
#===============================================================================
class ProbeGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Probe", app)

		b = Ribbon.LabelButton(self.frame, self, "<<Probe>>",
				image=Utils.icons["gear32"],
				text="Probe",
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "Perform a single probe cycle")

#===============================================================================
# Center Group
#===============================================================================
class CenterGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Center", app)

		b = Ribbon.LabelButton(self.frame, self, "<<ProbeCenter>>",
				image=Utils.icons["gear32"],
				text="Center",
				compound=TOP,
				width=48,
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "Perform a center probe cycle")

#===============================================================================
# Autolevel Group
#===============================================================================
class AutolevelGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Probe:Autolevel", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelMargins>>",
				image=Utils.icons["margins"],
				text="Margins",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Get margins from gcode file")

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelZero>>",
				image=Utils.icons["origin"],
				text="Zero",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Set current location as Z-zero for leveling")

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelClear>>",
				image=Utils.icons["clear"],
				text="Clear",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Clear probe data")

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame, self, "<<AutolevelScan>>",
				image=Utils.icons["gear32"],
				text="Scan",
				compound=TOP,
				justify=CENTER,
				width=48,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		self.addWidget(b)
		tkExtra.Balloon.set(b, "Scan probed area for level information on Z plane")

#===============================================================================
# Probe Common Offset
#===============================================================================
class ProbeCommonFrame(CNCRibbon.PageFrame):
	probeFeed = None
	tlo       = None

	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "ProbeCommon", app)

		lframe = LabelFrame(self, text="Common", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		# ----
		row = 0
		col = 0

		Label(lframe, text="Probe Feed:").grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.probeFeed = tkExtra.FloatEntry(lframe, background="White", width=5)
		ProbeCommonFrame.probeFeed.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.probeFeed, "Set probe feed rate")
		self.addWidget(ProbeCommonFrame.probeFeed)

		# ----
		# Tool offset
		row += 1
		col  = 0
		Label(lframe, text="TLO").grid(row=row, column=col, sticky=E)
		col += 1
		ProbeCommonFrame.tlo = tkExtra.FloatEntry(lframe, background="White")
		ProbeCommonFrame.tlo.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(ProbeCommonFrame.tlo, "Set tool offset for probing")
		self.addWidget(self.tlo)
		self.tlo.bind("<Return>",   self.tloSet)
		self.tlo.bind("<KP_Enter>", self.tloSet)

		col += 1
		b = Button(lframe, text="set",
				command=self.tloSet,
				padx=2, pady=1)
		b.grid(row=row, column=col, sticky=EW)
		self.addWidget(b)

		lframe.grid_columnconfigure(1,weight=1)
		self.loadConfig()

	#----------------------------------------------------------------------
	def tloSet(self, event=None):
		cmd = "G43.1Z"+(ProbeCommonFrame.tlo.get())
		self.sendGrbl(cmd+"\n$#\n")

	#----------------------------------------------------------------------
	@staticmethod
	def feedSet(probe):
		try:
			CNC.vars["prbfeed"] = float(ProbeCommonFrame.probeFeed.get())
			return False
		except:
			return True

	#----------------------------------------------------------------------
	def updateTlo(self):
		try:
			if self.focus_get() is not ProbeCommonFrame.tlo:
				ProbeCommonFrame.tlo.set(CNC.vars.get("TLO",""))
		except:
			pass

	#----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setFloat("Probe", "feed", ProbeCommonFrame.probeFeed.get())
		Utils.setFloat("Probe", "tlo",  ProbeCommonFrame.tlo.get())

	#----------------------------------------------------------------------
	def loadConfig(self):
		ProbeCommonFrame.probeFeed.set(Utils.getFloat("Probe","feed"))
		ProbeCommonFrame.tlo.set(      Utils.getFloat("Probe","tlo"))

#===============================================================================
# Probe Frame
#===============================================================================
class ProbeFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Probe", app)

		# WorkSpace -> Probe
		lframe = LabelFrame(self, text="Probe", foreground="DarkBlue")
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
	# Probe one Point
	#----------------------------------------------------------------------
	def probe(self, event=None):
		cmd = CNC.vars["prbcmd"]
		if ProbeCommonFrame.feedSet(probe):
			tkMessageBox.showerror("Probe Error",
				"Invalid probe feed rate",
				parent=self)
			return
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
			self.sendGrbl(cmd)
		else:
			tkMessageBox.showerror("Probe Error",
					"At least one probe direction should be specified")

#===============================================================================
# Center Frame
#===============================================================================
class ProbeCenterFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Probe:Center", app)

		# WorkSpace -> Probe
		lframe = LabelFrame(self, text="Center", foreground="DarkBlue")
		lframe.pack(side=TOP, fill=X)

		Label(lframe, text="Diameter:").pack(side=LEFT)
		self.diameter = tkExtra.FloatEntry(lframe, background="White")
		self.diameter.pack(side=LEFT, fill=X)
		tkExtra.Balloon.set(self.diameter, "Probing ring internal diameter")
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
			tkMessageBox.showerror("Probe Center Error",
					"Invalid diameter entered",
					parent=self)
			return

		lines = []
		lines.append("%s x-%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("low=prbx")
		lines.append("%s x%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 x[0.5*(low+high)]")
		lines.append("%s y-%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("low=prby")
		lines.append("%s y%s"%(cmd,diameter))
		lines.append("%wait")
		lines.append("g53 g0 y[0.5*(low+high)]")
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
		self.probeXstep = Label(lframe, foreground="DarkBlue",
					background="gray95", width=5)
		self.probeXstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeXstep, "X step")

		col += 1
		self.probeXbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.draw,
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
		self.probeYstep = Label(lframe,  foreground="DarkBlue",
					background="gray95", width=5)
		self.probeYstep.grid(row=row, column=col, sticky=EW)
		tkExtra.Balloon.set(self.probeYstep, "Y step")

		col += 1
		self.probeYbins = Spinbox(lframe,
					from_=2, to_=1000,
					command=self.draw,
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
				tkMessageBox.showerror("Probe Error",
						"Invalid X probing region",
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
				tkMessageBox.showerror("Probe Error",
						"Invalid Y probing region",
						parent=self)
			error = True

		try:
			probe.zmin  = float(self.probeZmin.get())
			probe.zmax  = float(self.probeZmax.get())
		except ValueError:
			if verbose:
				tkMessageBox.showerror("Probe Error",
					"Invalid Z probing region",
					parent=self)
			error = True

		if ProbeCommonFrame.feedSet(probe):
			if verbose:
				tkMessageBox.showerror("Probe Error",
					"Invalid probe feed rate",
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
		self._register((ProbeTabGroup, ProbeGroup, CenterGroup, AutolevelGroup),
			(ProbeCommonFrame, ProbeFrame, ProbeCenterFrame, AutolevelFrame))

		self.tabGroup = CNCRibbon.Page.groups["Probe"]
		self.tabGroup.tab.trace('w', self.tabChange)
		#self.tabGroup.tab.set("Probe")

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
