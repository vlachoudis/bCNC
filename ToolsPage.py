# -*- coding: ascii -*-
# $Id$
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

__author__  = "Vasilis Vlachoudis"
__email__   = "Vasilis.Vlachoudis@cern.ch"

import traceback
try:
	from Tkinter import *
	import tkMessageBox
except ImportError:
	from tkinter import *
	import tkinter.messagebox as tkMessageBox
from operator import attrgetter

import os
import time
import glob
import Utils
import Ribbon
import tkExtra
import Unicode
import CNCRibbon

from CNC import CNC

_EXE_FONT = ("Helvetica",12,"bold")

#===============================================================================
class InPlaceText(tkExtra.InPlaceText):
	def defaultBinds(self):
		tkExtra.InPlaceText.defaultBinds(self)
		self.edit.bind("<Escape>", self.ok)

#==============================================================================
# Tools Base class
#==============================================================================
class _Base:
	def __init__(self, master):
		self.master    = master
		self.name      = None
		self.icon      = None
		self.plugin    = False
		self.variables = []		# name, type, default, label
		self.values    = {}		# database of values
		self.listdb    = {}		# lists database
		self.current   = None		# currently editing index
		self.n         = 0
		self.buttons   = []

	# ----------------------------------------------------------------------
	def __setitem__(self, name, value):
		if self.current is None:
			self.values[name] = value
		else:
			self.values["%s.%d"%(name,self.current)] = value

	# ----------------------------------------------------------------------
	def __getitem__(self, name):
		if self.current is None:
			return self.values.get(name,"")
		else:
			return self.values.get("%s.%d"%(name,self.current),"")

	# ----------------------------------------------------------------------
	def gcode(self):
		return self.master.gcode

	# ----------------------------------------------------------------------
	# Return a sorted list of all names
	# ----------------------------------------------------------------------
	def names(self):
		lst = []
		for i in range(1000):
			key = "name.%d"%(i)
			value = self.values.get(key)
			if value is None: break
			lst.append(value)
		lst.sort()
		return lst

	# ----------------------------------------------------------------------
	def _get(self, key, t, default):
		if t in ("float","mm"):
			return Utils.getFloat(self.name, key, default)
		elif t == "int":
			return Utils.getInt(self.name, key, default)
		elif t == "bool":
			return Utils.getInt(self.name, key, default)
		else:
			return Utils.getStr(self.name, key, default)

	# ----------------------------------------------------------------------
	# Override with execute command
	# ----------------------------------------------------------------------
	def execute(self, app):
		pass

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		return False

	# ----------------------------------------------------------------------
	def event_generate(self, msg, **kwargs):
		self.master.listbox.event_generate(msg, **kwargs)

	# ----------------------------------------------------------------------
	def beforeChange(self, app):
		pass

	# ----------------------------------------------------------------------
	def populate(self):
		self.master.listbox.delete(0,END)
		for n, t, d, l in self.variables:
			value = self[n]
			if t == "bool":
				if value:
					value = Unicode.BALLOT_BOX_WITH_X
				else:
					value = Unicode.BALLOT_BOX
			elif t == "mm" and self.master.inches:
				try:
					value /= 25.4
					value = round(value, self.master.digits)
				except:
					value = ""
			elif t == "float":
				try:
					value = round(value, self.master.digits)
				except:
					value = ""
			#elif t == "list":
			#	value += " " + Unicode.BLACK_DOWN_POINTING_TRIANGLE
			self.master.listbox.insert(END, (l, value))

			if t=="color":
				try:
					self.master.listbox.lists[1].itemconfig(END, background=value)
				except TclError:
					pass

	#----------------------------------------------------------------------
	def _sendReturn(self, active):
		self.master.listbox.selection_clear(0,END)
		self.master.listbox.selection_set(active)
		self.master.listbox.activate(active)
		self.master.listbox.see(active)
		n, t, d, l = self.variables[active]
		if t=="bool": return	# Forbid changing value of bool
		self.master.listbox.event_generate("<Return>")

	#----------------------------------------------------------------------
	def _editPrev(self):
		active = self.master.listbox.index(ACTIVE)-1
		if active<0: return
		self._sendReturn(active)

	#----------------------------------------------------------------------
	def _editNext(self):
		active = self.master.listbox.index(ACTIVE)+1
		if active>=self.master.listbox.size(): return
		self._sendReturn(active)

	#----------------------------------------------------------------------
	# Make current "name" from the database
	#----------------------------------------------------------------------
	def makeCurrent(self, name):
		if not name: return
		# special handling
		for i in range(1000):
			if name==self.values.get("name.%d"%(i)):
				self.current = i
				self.update()
				return True
		return False

	#----------------------------------------------------------------------
	# Edit tool listbox
	#----------------------------------------------------------------------
	def edit(self, event=None, rename=False):
		lb = self.master.listbox.lists[1]
		if event is None or event.type=="2":
			keyboard = True
		else:
			keyboard = False
		if keyboard:
			# keyboard event
			active = lb.index(ACTIVE)
		else:
			active = lb.nearest(event.y)
			self.master.listbox.activate(active)

		ypos = lb.yview()[0]	# remember y position
		save = lb.get(ACTIVE)

		n, t, d, l = self.variables[active]

		if t == "int":
			edit = tkExtra.InPlaceInteger(lb)
		elif t in ("float", "mm"):
			edit = tkExtra.InPlaceFloat(lb)
		elif t == "bool":
			edit = None
			value = int(lb.get(active) == Unicode.BALLOT_BOX)
			if value:
				lb.set(active, Unicode.BALLOT_BOX_WITH_X)
			else:
				lb.set(active, Unicode.BALLOT_BOX)
		elif t == "list":
			edit = tkExtra.InPlaceList(lb, values=self.listdb[n])
		elif t == "db":
			if n=="name":
				# Current database
				if rename:
					edit = tkExtra.InPlaceEdit(lb)
				else:
					edit = tkExtra.InPlaceList(lb, values=self.names())
			else:
				# Refers to names from another database
				tool = self.master[n]
				names = tool.names()
				names.insert(0,"")
				edit = tkExtra.InPlaceList(lb, values=names)
		elif t == "text":
			edit = InPlaceText(lb)
		elif "," in t:
			choices = [""]
			choices.extend(t.split(","))
			edit = tkExtra.InPlaceList(lb, values=choices)
		elif t == "file":
			edit = tkExtra.InPlaceFile(lb, save=False)
		elif t == "output":
			edit = tkExtra.InPlaceFile(lb, save=True)
		elif t == "color":
			edit = tkExtra.InPlaceColor(lb)
			if edit.value is not None:
				try:
					lb.itemconfig(ACTIVE, background=edit.value)
				except TclError:
					pass
		else:
			edit = tkExtra.InPlaceEdit(lb)

		if edit is not None:
			value = edit.value
			if value is None:
				return

		if value == save:
			if edit.lastkey == "Up":
				self._editPrev()
			elif edit.lastkey in ("Return", "KP_Enter", "Down"):
				self._editNext()
			return

		if t == "int":
			try:
				value = int(value)
			except ValueError:
				value = ""
		elif t in ("float","mm"):
			try:
				value = float(value)
				if t=="mm" and self.master.inches:
					value *= 25.4
			except ValueError:
				value = ""

		if n=="name" and not rename:
			if self.makeCurrent(value):
				self.populate()
		else:
			self[n] = value
			if self.update():
				self.populate()

		self.master.listbox.selection_set(active)
		self.master.listbox.activate(active)
		self.master.listbox.yview_moveto(ypos)
		if edit is not None and not rename:
			if edit.lastkey == "Up":
				self._editPrev()
			elif edit.lastkey in ("Return", "KP_Enter", "Down") and active>0:
				self._editNext()

	#==============================================================================
	# Additional persistence class for config
	#==============================================================================
	#class _Config:
	# ----------------------------------------------------------------------
	# Load from a configuration file
	# ----------------------------------------------------------------------
	def load(self):
		# Load lists
		lists = []
		for n, t, d, l in self.variables:
			if t=="list":
				lists.append(n)
		if lists:
			for p in lists:
				self.listdb[p] = []
				for i in range(1000):
					key = "_%s.%d"%(p, i)
					value = Utils.getStr(self.name, key).strip()
					if value:
						self.listdb[p].append(value)
					else:
						break

		# Check if there is a current
		try:
			self.current = int(Utils.config.get(self.name, "current"))
		except:
			self.current = None

		# Load values
		if self.current is not None:
			self.n = self._get("n", "int", 0)
			for i in range(self.n):
				key = "name.%d"%(i)
				self.values[key] = Utils.getStr(self.name, key)
				for n, t, d, l in self.variables:
					key = "%s.%d"%(n,i)
					self.values[key] = self._get(key, t, d)
		else:
			for n, t, d, l in self.variables:
				self.values[n] = self._get(n, t, d)
		self.update()

	# ----------------------------------------------------------------------
	# Save to a configuration file
	# ----------------------------------------------------------------------
	def save(self):
		# if section do not exist add it
		Utils.addSection(self.name)

		if self.listdb:
			for name,lst in self.listdb.items():
				for i,value in enumerate(lst):
					Utils.setStr(self.name, "_%s.%d"%(name,i), value)

		# Save values
		if self.current is not None:
			Utils.setStr(self.name, "current", str(self.current))
			Utils.setStr(self.name, "n", str(self.n))

			for i in range(self.n):
				key = "name.%d"%(i)
				value = self.values.get(key)
				if value is None: break
				Utils.setStr(self.name, key, value)

				for n, t, d, l in self.variables:
					key = "%s.%d"%(n,i)
					Utils.setStr(self.name, key,
						str(self.values.get(key,d)))
		else:
			for n, t, d, l in self.variables:
				Utils.setStr(self.name, n, str(self.values.get(n,d)))

	# ----------------------------------------------------------------------
	def fromMm(self, name, default=0.0):
		try:
			return self.master.fromMm(float(self[name]))
		except ValueError:
			return default

#==============================================================================
# Base class of all databases
#==============================================================================
class DataBase(_Base):
	def __init__(self, master):
		_Base.__init__(self, master)
		self.buttons  = ["add","delete","clone","rename"]

	# ----------------------------------------------------------------------
	# Add a new item
	# ----------------------------------------------------------------------
	def add(self, rename=True):
		self.current = self.n
		self.values["name.%d"%(self.n)] = "%s %02d"%(self.name, self.n+1)
		self.n += 1
		self.populate()
		if rename:
			self.rename()

	# ----------------------------------------------------------------------
	# Delete selected item
	# ----------------------------------------------------------------------
	def delete(self):
		if self.n==0: return
		for n, t, d, l in self.variables:
			for i in range(self.current, self.n):
				try:
					self.values["%s.%d"%(n,i)] = self.values["%s.%d"%(n,i+1)]
				except KeyError:
					try:
						del self.values["%s.%d"%(n,i)]
					except KeyError:
						pass

		self.n -= 1
		if self.current >= self.n:
			self.current = self.n - 1
		self.populate()

	# ----------------------------------------------------------------------
	# Clone selected item
	# ----------------------------------------------------------------------
	def clone(self):
		if self.n==0: return
		for n, t, d, l in self.variables:
			try:
				if n=="name":
					self.values["%s.%d"%(n,self.n)] = \
						self.values["%s.%d"%(n,self.current)] + " clone"
				else:
					self.values["%s.%d"%(n,self.n)] = \
						self.values["%s.%d"%(n,self.current)]
			except KeyError:
				pass
		self.n += 1
		self.current = self.n - 1
		self.populate()

	# ----------------------------------------------------------------------
	# Rename current item
	# ----------------------------------------------------------------------
	def rename(self):
		self.master.listbox.selection_clear(0,END)
		self.master.listbox.selection_set(0)
		self.master.listbox.activate(0)
		self.master.listbox.see(0)
		self.edit(None,True)

#==============================================================================
class Plugin(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.plugin = True
		self.group  = "Macros"

#==============================================================================
# Generic ini configuration
#==============================================================================
class Ini(_Base):
	def __init__(self, master, name, vartype):
		_Base.__init__(self, master)
		self.name = name

		# detect variables from ini file
		self.variables = []
		for name,value in Utils.config.items(self.name):
			self.variables.append((name, vartype, value, name))

#------------------------------------------------------------------------------
class Font(Ini):
	def __init__(self, master):
		Ini.__init__(self, master, "Font", "str")

#------------------------------------------------------------------------------
class Color(Ini):
	def __init__(self, master):
		Ini.__init__(self, master, "Color", "color")

#------------------------------------------------------------------------------
class Camera(Ini):
	def __init__(self, master):
		Ini.__init__(self, master, "Camera", "int")

#------------------------------------------------------------------------------
class Events(Ini):
	def __init__(self, master):
		Ini.__init__(self, master, "Events", "str")

#------------------------------------------------------------------------------
class Shortcut(Ini):
	def __init__(self, master):
		Ini.__init__(self, master, "Shortcut", "str")
		self.buttons.append("exe")

	#----------------------------------------------------------------------
	def execute(self, app):
		self.save()
		app.loadShortcuts()

#==============================================================================
# CNC machine configuration
#==============================================================================
class Config(_Base):
	def __init__(self, master):
		_Base.__init__(self, master)
		self.name = "CNC"
		self.variables = [
			("units"         , "bool", 0    , _("Units (inches)"))   ,
			("lasercutter"   , "bool", 0    , _("Lasercutter"))   ,
			("doublesizeicon", "bool", 0    , _("Double Size Icon"))   ,
			("acceleration_x", "mm"  , 25.0 , _("Acceleration x"))   ,
			("acceleration_y", "mm"  , 25.0 , _("Acceleration y"))   ,
			("acceleration_z", "mm"  , 5.0  , _("Acceleration z"))   ,
			("feedmax_x"     , "mm"  , 3000., _("Feed max x"))       ,
			("feedmax_y"     , "mm"  , 3000., _("Feed max y"))       ,
			("feedmax_z"     , "mm"  , 2000., _("Feed max z"))       ,
			("travel_x"      , "mm"  , 200  , _("Travel x"))         ,
			("travel_y"      , "mm"  , 200  , _("Travel y"))         ,
			("travel_z"      , "mm"  , 100  , _("Travel z"))         ,
			("round"         , "int" , 4    , _("Decimal digits"))   ,
			("accuracy"      , "mm"  , 0.1  , _("Plotting Arc accuracy")),
			("startup"       , "str" , "G90", _("Start up"))          ,
			("spindlemin"    , "int" , 0    , _("Spindle min (RPM)")),
			("spindlemax"    , "int" , 12000, _("Spindle max (RPM)")),
			("drozeropad"    , "int" , 0    , _("DRO Zero padding")),
			("header"        , "text" ,   "", _("Header gcode")),
			("footer"        , "text" ,   "", _("Footer gcode"))
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.inches        = self["units"]
		self.master.digits        = int(self["round"])
		self.master.cnc().decimal = self.master.digits
		self.master.cnc().startup = self["startup"]
		self.master.gcode.header  = self["header"]
		self.master.gcode.footer  = self["footer"]
		return False

#==============================================================================
# Material database
#==============================================================================
class Material(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Material"
		self.variables = [
			("name",    "db",    "", _("Name")),
			("comment","str",    "", _("Comment")),
			("feed",    "mm"  , 10., _("Feed")),
			("feedz",   "mm"  ,  1., _("Plunge Feed")),
			("stepz",   "mm"  ,  1., _("Depth Increment"))
		 ]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		# update ONLY if stock material is empty:
		stockmat = self.master["stock"]["material"]
		if stockmat=="" or stockmat==self["name"]:
			self.master.cnc()["cutfeed"]  = self.fromMm("feed")
			self.master.cnc()["cutfeedz"] = self.fromMm("feedz")
			self.master.cnc()["stepz"]    = self.fromMm("stepz")
		return False

#==============================================================================
# EndMill Bit database
#==============================================================================
class EndMill(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "EndMill"
		self.variables = [
			("name",       "db",     "", _("Name")),
			("comment",   "str",     "", _("Comment")),
			("type",     "list",     "", _("Type")),
			("shape",    "list",     "", _("Shape")),
			("material", "list",     "", _("Material")),
			("coating",  "list",     "", _("Coating")),
			("diameter",   "mm",  3.175, _("Diameter")),
			("axis",       "mm",  3.175, _("Mount Axis")),
			("flutes",    "int",      2, _("Flutes")),
			("length",     "mm",   20.0, _("Length")),
			("angle",   "float",     "", _("Angle")),
			("stepover","float",   40.0, _("Stepover %"))
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.cnc()["diameter"] = self.fromMm("diameter")
		self.master.cnc()["stepover"] = self["stepover"]
		return False

#==============================================================================
# Stock material on worksurface
#==============================================================================
class Stock(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Stock"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("comment",  "str",     "", _("Comment")),
			("material",  "db" ,    "", _("Material")),
			("safe"  ,    "mm" ,   3.0, _("Safe Z")),
			("surface",   "mm" ,   0.0, _("Surface Z")),
			("thickness", "mm" ,   5.0, _("Thickness"))
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.cnc()["safe"]      = self.fromMm("safe")
		self.master.cnc()["surface"]   = self.fromMm("surface")
		self.master.cnc()["thickness"] = self.fromMm("thickness")
		if self["material"]:
			self.master["material"].makeCurrent(self["material"])
		return False

#==============================================================================
# Cut material
#==============================================================================
class Cut(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Cut"
		self.variables = [
			("name",         "db" ,    "", _("Name")),
			("surface",      "mm" ,    "", _("Surface Z")),
			("depth"  ,      "mm" ,    "", _("Target Depth")),
			("stepz"  ,      "mm" ,    "", _("Depth Increment")),
			("feed",         "mm" ,    "", _("Feed")),
			("feedz",        "mm" ,    "", _("Plunge Feed")),
			("cutFromTop", "bool" , False, _("First cut at surface height"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		surface = self.fromMm("surface", None)
		depth   = self.fromMm("depth", None)
		step    = self.fromMm("stepz", None)
		try:    feed = self.fromMm("feed", None)
		except: feed = None
		try:    feedz = self.fromMm("feedz", None)
		except: feedz = None
		cutFromTop = self["cutFromTop"]
		app.executeOnSelection("CUT", True, depth, step, surface, feed, feedz, cutFromTop)
		app.setStatus(_("CUT selected paths"))

#==============================================================================
# Drill material
#==============================================================================
class Drill(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Drill"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("depth",     "mm" ,    "", _("Target Depth")),
			("peck",      "mm" ,    "", _("Peck depth")),
			("dwell",     "float" , "", _("Dwell (s)")),
			("distance",  "mm" ,    "", _("Distance (mm)")),
			("number",    "int" ,   "", _("Number"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		h = self.fromMm("depth", None)
		p = self.fromMm("peck",  None)
		e = self.fromMm("distance", None)
		try:
			d = self["dwell"]
		except:
			d = None
		try:
			n = int(self["number"])
		except:
			n = 0
		app.executeOnSelection("DRILL", True, h, p, d, e, n)
		app.setStatus(_("DRILL selected points"))

#==============================================================================
# Profile
#==============================================================================
class Profile(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Profile"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("endmill",   "db" ,    "", _("End Mill")),
			("direction","inside,outside" , "outside", _("Direction")),
			("offset",   "float",  0.0, _("Additional offset distance")),
			("overcut",  "bool",     1, _("Overcut"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		direction = self["direction"]
		name = self["name"]
		if name=="default" or name=="": name=None
		app.profile(direction, self["offset"], self["overcut"], name)
		app.setStatus(_("Generate profile path"))

#==============================================================================
# Pocket
#==============================================================================
class Pocket(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Pocket"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("endmill",   "db" ,    "", _("End Mill")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		name = self["name"]
		if name=="default" or name=="": name=None
		app.pocket(name)
		app.setStatus(_("Generate pocket path"))

#==============================================================================
# Tabs
#==============================================================================
class Tabs(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Tabs"
		self.variables = [
			("name",      "db" ,    "", _("Name")),
			("ntabs",     "int",     5, _("Number of tabs")),
			("dtabs",     "mm",    0.0, _("Min. Distance of tabs")),
			("dx",        "mm",    5.0,   "Dx"),
			("dy",        "mm",    5.0,   "Dy"),
			("z",         "mm",   -3.0, _("Height"))
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self,app):
		try:
			ntabs = int(self["ntabs"])
		except:
			ntabs = 0

		dtabs = self.fromMm("dtabs", 0.)
		dx    = self.fromMm("dx", self.master.fromMm(5.))
		dy    = self.fromMm("dy", self.master.fromMm(5.))
		z     = self.fromMm("z", -self.master.fromMm(3.))

		if ntabs<0: ntabs=0
		if dtabs<0.: dtabs=0

		if ntabs==0 and dtabs==0:
			tkMessageBox.showerror(_("Tabs error"),
				_("You cannot have both the number of tabs or distance equal to zero"))

		app.executeOnSelection("TABS", True, ntabs, dtabs, dx, dy, z)
		app.setStatus(_("Create tabs on blocks"))

#==============================================================================
# Controller setup
#==============================================================================
class Controller(_Base):
	def __init__(self, master):
		_Base.__init__(self, master)
		self.name = "Controller"
		self.variables = [
			("grbl_0",   "int",     10,     _("$0 Step pulse time [us]")),
			("grbl_1",   "int",     25,     _("$1 Step idle delay [ms]")),
			("grbl_2",   "int",      0,     _("$2 Step pulse invert [mask]")),
			("grbl_3",   "int",      0,     _("$3 Step direction invert [mask]")),
			("grbl_4",   "bool",     0,     _("$4 Invert step enable pin")),
			("grbl_5",   "bool",     0,     _("$5 Invert limit pins")),
			("grbl_6",   "bool",     0,     _("$6 Invert probe pin")),
			("grbl_10",  "int",      1,     _("$10 Status report options [mask]")),
			("grbl_11",  "float",    0.010, _("$11 Junction deviation [mm]")),
			("grbl_12",  "float",    0.002, _("$12 Arc tolerance [mm]")),
			("grbl_13",  "bool",     0,     _("$13 Report in inches")),
			("grbl_20",  "bool",     0,     _("$20 Soft limits enable")),
			("grbl_21",  "bool",     0,     _("$21 Hard limits enable")),
			("grbl_22",  "bool",     0,     _("$22 Homing cycle enable")),
			("grbl_23",  "int",      0,     _("$23 Homing direction invert [mask]")),
			("grbl_24",  "float",   25.,    _("$24 Homing locate feed rate [mm/min]")),
			("grbl_25",  "float",  500.,    _("$25 Homing search seek rate [mm/min]")),
			("grbl_26",  "int",    250,     _("$26 Homing switch debounce delay, ms")),
			("grbl_27",  "float",    1.,    _("$27 Homing switch pull-off distance [mm]")),
			("grbl_30",  "float", 1000.,    _("$30 Maximum spindle speed [RPM]")),
			("grbl_31",  "float",    0.,    _("$31 Minimum spindle speed [RPM]")),
			("grbl_32",  "bool",     0,     _("$32 Laser-mode enable")),
			("grbl_100", "float",  250.,    _("$100 X-axis steps per mm")),
			("grbl_101", "float",  250.,    _("$101 Y-axis steps per mm")),
			("grbl_102", "float",  250.,    _("$102 Z-axis steps per mm")),
			("grbl_110", "float",  500.,    _("$110 X-axis maximum rate [mm/min]")),
			("grbl_111", "float",  500.,    _("$111 Y-axis maximum rate [mm/min]")),
			("grbl_112", "float",  500.,    _("$112 Z-axis maximum rate [mm/min]")),
			("grbl_120", "float",   10.,    _("$120 X-axis acceleration [mm/sec^2]")),
			("grbl_121", "float",   10.,    _("$121 Y-axis acceleration [mm/sec^2]")),
			("grbl_122", "float",   10.,    _("$122 Z-axis acceleration [mm/sec^2]")),
			("grbl_130", "float",  200.,    _("$130 X-axis maximum travel [mm]")),
			("grbl_131", "float",  200.,    _("$131 Y-axis maximum travel [mm]")),
			("grbl_132", "float",  200.,    _("$132 Z-axis maximum travel [mm]"))]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		lines = []
		for n,t,d,c in self.variables:
			v = self[n]
			try:
				if t=="float":
					if v == float(CNC.vars[n]): continue
				else:
					if v == int(CNC.vars[n]): continue
			except:
				continue
			lines.append("$%s=%s"%(n[5:],str(v)))
			lines.append("%wait")
		lines.append("$$")
		app.run(lines=lines)

	# ----------------------------------------------------------------------
	def beforeChange(self, app):
		app.sendGCode("$$")
		time.sleep(1)

	# ----------------------------------------------------------------------
	def populate(self):
		for n, t, d, l in self.variables:
			try:
				if t=="float":
					self.values[n] = float(CNC.vars[n])
				else:
					self.values[n] = int(CNC.vars[n])
			except KeyError:
				pass
		_Base.populate(self)

#==============================================================================
# Tools container class
#==============================================================================
class Tools:
	def __init__(self, gcode):
		self.gcode  = gcode
		self.inches = False
		self.digits = 4
		self.active = StringVar()

		self.tools   = {}
		self.buttons = {}
		self.listbox = None

		# CNC should be first to load the inches
		for cls in [ Config, Font, Color, Controller, Cut, Drill, EndMill, Events,
			     Material, Pocket, Profile, Shortcut, Stock,
			     Tabs]:
			tool = cls(self)
			self.addTool(tool)

		# Find plugins in the plugins directory and load them
		for f in glob.glob("%s/plugins/*.py"%(Utils.prgpath)):
			name,ext = os.path.splitext(os.path.basename(f))
			try:
				exec("import %s"%(name))
				tool = eval("%s.Tool(self)"%(name))
				self.addTool(tool)
			except (ImportError, AttributeError):
				typ, val, tb = sys.exc_info()
				traceback.print_exception(typ, val, tb)

	# ----------------------------------------------------------------------
	def addTool(self, tool):
		self.tools[tool.name.upper()] = tool

	# ----------------------------------------------------------------------
	# Return a list of plugins
	# ----------------------------------------------------------------------
	def pluginList(self):
		plugins = [x for x in self.tools.values() if x.plugin]
		return sorted(plugins, key=attrgetter('name'))

	# ----------------------------------------------------------------------
	def setListbox(self, listbox):
		self.listbox = listbox

	# ----------------------------------------------------------------------
	def __getitem__(self, name):
		return self.tools[name.upper()]

	# ----------------------------------------------------------------------
	def getActive(self):
		try:
			return self.tools[self.active.get().upper()]
		except:
			self.active.set("CNC")
			return self.tools["CNC"]

	# ----------------------------------------------------------------------
	def setActive(self, value):
		self.active.set(value)

	# ----------------------------------------------------------------------
	def toMm(self, value):
		if self.inches:
			return value*25.4
		else:
			return value

	# ----------------------------------------------------------------------
	def fromMm(self, value):
		if self.inches:
			return value/25.4
		else:
			return value

	# ----------------------------------------------------------------------
	def names(self):
		lst = [x.name for x in self.tools.values()]
		lst.sort()
		return lst

	# ----------------------------------------------------------------------
	# Load from config file
	# ----------------------------------------------------------------------
	def loadConfig(self):
		self.active.set(Utils.getStr(Utils.__prg__, "tool", "CNC"))
		for tool in self.tools.values():
			tool.load()

	# ----------------------------------------------------------------------
	# Save to config file
	# ----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setStr(Utils.__prg__, "tool", self.active.get())
		for tool in self.tools.values():
			tool.save()

	# ----------------------------------------------------------------------
	def cnc(self):
		return self.gcode.cnc

	# ----------------------------------------------------------------------
	def addButton(self, name, button):
		self.buttons[name] = button

	# ----------------------------------------------------------------------
	def activateButtons(self, tool):
		for btn in self.buttons.values():
			btn.config(state=DISABLED)
		for name in tool.buttons:
			self.buttons[name].config(state=NORMAL)
		self.buttons["exe"].config(text=self.active.get())

#===============================================================================
# DataBase Group
#===============================================================================
class DataBaseGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Database"), app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["stock32"],
				text=_("Stock"),
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Stock",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=2, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Stock material currently on machine"))
		self.addWidget(b)

		# ===
		col,row=1,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["material"],
				text=_("Material"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Material",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Editable database of material properties"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["endmill"],
				text=_("End Mill"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="EndMill",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Editable database of EndMills properties"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolRename>>",
				image=Utils.icons["rename"],
				text=_("Rename"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Edit name of current operation/object"))
		self.addWidget(b)
		app.tools.addButton("rename",b)

		# ===
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, app, "<<ToolAdd>>",
				image=Utils.icons["add"],
				text=_("Add"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Add a new operation/object"))
		self.addWidget(b)
		app.tools.addButton("add",b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolClone>>",
				image=Utils.icons["clone"],
				text=_("Clone"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Clone selected operation/object"))
		self.addWidget(b)
		app.tools.addButton("clone",b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolDelete>>",
				image=Utils.icons["x"],
				text=_("Delete"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Delete selected operation/object"))
		self.addWidget(b)
		app.tools.addButton("delete",b)

#===============================================================================
# CAM Group
#===============================================================================
class CAMGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("CAM"), app)
		self.grid3rows()

		# ===
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["cut32"],
				text=_("Cut"),
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Cut",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Cut for the full stock thickness selected code"))
		self.addWidget(b)

		# ===
		col,row=1,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["profile32"],
				text=_("Profile"),
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Profile",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Perform a profile operation on selected code"))
		self.addWidget(b)

		# ===
		col,row=2,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["pocket"],
				text=_("Pocket"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Pocket",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=2, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Perform a pocket operation on selected code"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["drill"],
				text=_("Drill"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Drill",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=2, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Insert a drill cycle on current objects/location"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["tab"],
				text=_("Tabs"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Tabs",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=2, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Insert holding tabs"))
		self.addWidget(b)

		# ---
		col += 1
		row  = 0
		# Find plugins in the plugins directory and load them
		for tool in app.tools.pluginList():
			if tool.group != "CAM": continue
			# ===
			b = Ribbon.LabelRadiobutton(self.frame,
					image=Utils.icons[tool.icon],
					text=tool.name,
					compound=LEFT,
					anchor=W,
					variable=app.tools.active,
					value=tool.name,
					background=Ribbon._BACKGROUND)
			b.grid(row=row, column=col, padx=2, pady=0, sticky=NSEW)
			tkExtra.Balloon.set(b, tool.__doc__)
			self.addWidget(b)

			row += 1
			if row==3:
				col += 1
				row  = 0

	#----------------------------------------------------------------------
	def createMenu(self):
		menu = Menu(self, tearoff=0)
		#for group in ("Artistic", "Generator", "Macros"):
		for group in ("Artistic", "Generator"):
			submenu = Menu(menu, tearoff=0)
			menu.add_cascade(label=group, menu=submenu)
			# Find plugins in the plugins directory and load them
			for tool in self.app.tools.pluginList():
				if tool.group != group: continue
				submenu.add_radiobutton(
						label=tool.name,
						image=Utils.icons[tool.icon],
						compound=LEFT,
						variable=self.app.tools.active,
						value=tool.name)
		return menu

#===============================================================================
# Plugins Group
#===============================================================================
#class PluginsGroup(CNCRibbon.ButtonGroup):
#	def __init__(self, master, group, app):
#		CNCRibbon.ButtonGroup.__init__(self, master, group, app)
#		self.grid3rows()
#
#		col,row=0,0
#		# Find plugins in the plugins directory and load them
#		for tool in app.tools.pluginList():
#			if tool.group != group: continue
#			# ===
#			b = Ribbon.LabelRadiobutton(self.frame,
#					image=Utils.icons[tool.icon],
#					text=tool.name,
#					compound=LEFT,
#					anchor=W,
#					variable=app.tools.active,
#					value=tool.name,
#					background=Ribbon._BACKGROUND)
#			b.grid(row=row, column=col, padx=2, pady=0, sticky=NSEW)
#			tkExtra.Balloon.set(b, tool.__doc__)
#			self.addWidget(b)
#
#			row += 1
#			if row==3:
#				col += 1
#				row  = 0

#===============================================================================
# Macros Groups based on plugins
#===============================================================================
#class MacrosGroup(PluginsGroup):
#	def __init__(self, master, app):
#		PluginsGroup.__init__(self, master, N_("Macros"), app)
#
#class GeneratorGroup(PluginsGroup):
#	def __init__(self, master, app):
#		PluginsGroup.__init__(self, master, N_("Generator"), app)
#
#class ArtisticGroup(PluginsGroup):
#	def __init__(self, master, app):
#		PluginsGroup.__init__(self, master, N_("Artistic"), app)

#===============================================================================
# Config
#===============================================================================
class ConfigGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		#CNCRibbon.ButtonGroup.__init__(self, master, N_("Config"), app)
		CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("Config"), app)
		self.grid3rows()

		# ===
		col,row=0,0
		f = Frame(self.frame)
		f.grid(row=row, column=col, columnspan=3, padx=0, pady=0, sticky=NSEW)

		b = Label(f, image=Utils.icons["globe"], background=Ribbon._BACKGROUND)
		b.pack(side=LEFT)

		self.language = Ribbon.LabelCombobox(f,
				command=self.languageChange,
				width=16)
		self.language.pack(side=RIGHT, fill=X, expand=YES)
		tkExtra.Balloon.set(self.language, _("Change program language restart is required"))
		self.addWidget(self.language)

		self.fillLanguage()

		# ===
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["camera"],
				text=_("Camera"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Camera",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Camera Configuration"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["color"],
				text=_("Colors"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Color",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Color configuration"))
		self.addWidget(b)

		# ===
		col,row = col+1,1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["config"],
				text=_("Config"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="CNC",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Machine configuration for bCNC"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["arduino"],
				text=_("Controller"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Controller",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Controller (GRBL) configuration"))
		self.addWidget(b)

		# ===
		col,row = col+1,1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["font"],
				text=_("Fonts"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Font",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Font configuration"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["shortcut"],
				text=_("Shortcuts"),
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Shortcut",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Shortcuts configuration"))
		self.addWidget(b)
#
#		# ---
#		row += 1
#		b = Ribbon.LabelRadiobutton(self.frame,
#				image=Utils.icons["event"],
#				text=_("Events"),
#				compound=LEFT,
#				anchor=W,
#				variable=app.tools.active,
#				value="Events",
#				background=Ribbon._BACKGROUND)
#		b.grid(row=row, column=col, padx=1, pady=0, sticky=NSEW)
#		tkExtra.Balloon.set(b, _("Events configuration"))
#		self.addWidget(b)

	#----------------------------------------------------------------------
	def fillLanguage(self):
		self.language.set(Utils.LANGUAGES.get(Utils.language,""))
		self.language.fill(list(sorted(Utils.LANGUAGES.values())))

	#----------------------------------------------------------------------
	def languageChange(self):
		lang = self.language.get()
		# find translation
		for a,b in Utils.LANGUAGES.items():
			if b == lang:
				if Utils.language == a: return
				Utils.language = a
				Utils.setStr(Utils.__prg__,  "language", Utils.language)
				tkMessageBox.showinfo(_("Language change"),
					_("Please restart the program."),
					parent=self.winfo_toplevel())
				return

	#----------------------------------------------------------------------
	def createMenu(self):
		menu = Menu(self, tearoff=0)
		menu.add_radiobutton(
				label=_("Events"),
				image=Utils.icons["event"], compound=LEFT,
				variable=self.app.tools.active,
				value="Events")
		menu.add_command(
				label=_("User File"),
				image=Utils.icons["about"], compound=LEFT,
				command=self.app.showUserFile)
		return menu

#==============================================================================
# Tools Frame
#==============================================================================
class ToolsFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Tools", app)
		self.tools = app.tools

		b = Button(self, text=_("Execute"),
				image=Utils.icons["gear"],
				compound=LEFT,
				foreground="DarkRed",
				activeforeground="DarkRed",
				activebackground="LightYellow",
				font=_EXE_FONT,
				command=self.execute)
		b.pack(side=TOP, fill=X)
		self.tools.addButton("exe",b)

		self.toolList = tkExtra.MultiListbox(self,
					((_("Name"),  24, None),
					 (_("Value"), 24, None)),
					 header = False,
					 stretch = "last",
					 background = "White")
		self.toolList.sortAssist = None
		self.toolList.pack(side=BOTTOM, fill=BOTH, expand=YES)
		self.toolList.bindList("<Double-1>",	self.edit)
		self.toolList.bindList("<Return>",	self.edit)
		self.toolList.bindList("<Key-space>",	self.edit)
#		self.toolList.bindList("<Key-space>",	self.commandFocus)
#		self.toolList.bindList("<Control-Key-space>",	self.commandFocus)
		self.toolList.lists[1].bind("<ButtonRelease-1>", self.edit)
		self.tools.setListbox(self.toolList)
		self.addWidget(self.toolList)

		app.tools.active.trace('w',self.change)
		self.change()

	#----------------------------------------------------------------------
	# Populate listbox with new values
	#----------------------------------------------------------------------
	def change(self, a=None, b=None, c=None):
		tool = self.tools.getActive()
		tool.beforeChange(self.app)
		tool.populate()
		tool.update()
		self.tools.activateButtons(tool)
	populate = change

	#----------------------------------------------------------------------
	# Edit tool listbox
	#----------------------------------------------------------------------
	def edit(self, event=None):
		sel = self.toolList.curselection()
		if not sel: return
		if sel[0] == 0 and (event is None or event.keysym==0):
			self.tools.getActive().rename()
		else:
			self.tools.getActive().edit(event)

	#----------------------------------------------------------------------
	def execute(self, event=None):
		self.tools.getActive().execute(self.app)

	#----------------------------------------------------------------------
	def add(self, event=None):
		self.tools.getActive().add()

	#----------------------------------------------------------------------
	def delete(self, event=None):
		self.tools.getActive().delete()

	#----------------------------------------------------------------------
	def clone(self, event=None):
		self.tools.getActive().clone()

	#----------------------------------------------------------------------
	def rename(self, event=None):
		self.tools.getActive().rename()

	#----------------------------------------------------------------------
#	def selectTab(self, tabid):
#

#===============================================================================
# Tools Page
#===============================================================================
class ToolsPage(CNCRibbon.Page):
	__doc__ = _("GCode manipulation tools and user plugins")
	_name_  = N_("Tools")
	_icon_  = "tools"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register(
			(DataBaseGroup,
			CAMGroup,
			#GeneratorGroup,
			#ArtisticGroup,
			#MacrosGroup,
			ConfigGroup), (ToolsFrame,))

	#----------------------------------------------------------------------
	def edit(self, event=None):
		CNCRibbon.Page.frames["Tools"].edit()

	#----------------------------------------------------------------------
	def add(self, event=None):
		CNCRibbon.Page.frames["Tools"].add()

	#----------------------------------------------------------------------
	def clone(self, event=None):
		CNCRibbon.Page.frames["Tools"].clone()

	#----------------------------------------------------------------------
	def delete(self, event=None):
		CNCRibbon.Page.frames["Tools"].delete()

	#----------------------------------------------------------------------
	def rename(self, event=None):
		CNCRibbon.Page.frames["Tools"].rename()
