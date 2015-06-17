#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

__author__  = "Vasilis Vlachoudis"
__email__   = "Vasilis.Vlachoudis@cern.ch"

import Unicode
try:
	from Tkinter import *
except ImportError:
	from tkinter import *

import Utils
import tkExtra

#===============================================================================
class InPlaceText(tkExtra.InPlaceText):
	def defaultBinds(self):
		tkExtra.InPlaceText.defaultBinds(self)
		self.edit.bind("<Escape>", self.ok)

#==============================================================================
# Tools
#==============================================================================
class Base:
	def __init__(self, master):
		self.master    = master
		self.name      = None
		self.variables = []		# name, type, default, label
		self.values    = {}		# database of values
		self.listdb    = {}		# lists database
		self.current   = None		# currently editing index
		self.n         = 0
		self.buttons   = None

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
	def _get(self, config, key, t, default):
		try:
			value = config.get(self.name, key)
			if t in ("float","mm"):
				return float(value)
			elif t == "int":
				return int(value)
			elif t == "bool":
				return int(value)
			else:
				return value
		except:
			return default

	# ----------------------------------------------------------------------
	# Load from a configuration file
	# ----------------------------------------------------------------------
	def load(self, config):
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
					try:
						self.listdb[p].append(config.get(self.name, key))
					except:
						break

			for lst in self.listdb.values():
				lst.sort()

		# Check if there is a current
		try:
			self.current = int(config.get(self.name, "current"))
		except:
			self.current = None

		# Load values
		if self.current is not None:
			self.n = self._get(config, "n", "int", 0)
			for i in range(self.n):
				key = "name.%d"%(i)
				self.values[key] = config.get(self.name, key)
				for n, t, d, l in self.variables:
					key = "%s.%d"%(n,i)
					self.values[key] = self._get(config, key, t, d)
		else:
			for n, t, d, l in self.variables:
				self.values[n] = self._get(config, n, t, d)
		self.update()

	# ----------------------------------------------------------------------
	# Save to a configuration file
	# ----------------------------------------------------------------------
	def save(self, config):
		if self.listdb:
			for name,lst in self.listdb.items():
				for i,value in enumerate(lst):
					config.set(self.name, "_%s.%d"%(name,i), value)

		# Save values
		if self.current is not None:
			config.set(self.name, "current", str(self.current))
			config.set(self.name, "n", str(self.n))

			for i in range(self.n):
				key = "name.%d"%(i)
				value = self.values.get(key)
				if value is None: break
				config.set(self.name, key, value)

				for n, t, d, l in self.variables:
					key = "%s.%d"%(n,i)
					config.set(self.name, key, str(self.values.get(key,d)))
		else:
			for n, t, d, l in self.variables:
				config.set(self.name, n, str(self.values.get(n,d)))

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

	#----------------------------------------------------------------------
	def _sendReturn(self, active):
		self.master.listbox.selection_clear(0,END)
		self.master.listbox.selection_set(active)
		self.master.listbox.activate(active)
		self.master.listbox.see(active)
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
			elif edit.lastkey in ("Return", "KP_Enter", "Down"):
				self._editNext()

#==============================================================================
# Base class of all databases
#==============================================================================
class DataBase(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.buttons  = ("add","del","clone","rename")

	# ----------------------------------------------------------------------
	# Add a new item
	# ----------------------------------------------------------------------
	def add(self):
		self.current = self.n
		self.values["name.%d"%(self.n)] = self.name
		self.n += 1
		self.populate()
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
# Create a BOX
#==============================================================================
class Box(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Box"
		self.variables = [
			("name",      "db",    "", "Name"),
			("dx",        "mm", 100.0, "Width Dx"),
			("dy",        "mm",  70.0, "Depth Dy"),
			("dz",        "mm",  50.0, "Height Dz"),
			("nx",       "int",    11, "Fingers Nx"),
			("ny",       "int",     7, "Fingers Ny"),
			("nz",       "int",     5, "Fingers Nz"),
			("profile", "bool",     0, "Profile"),
			("overcut", "bool",     1, "Overcut"),
			("cut",     "bool",     0, "Cut")
		]
		self.buttons  = self.buttons + ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		app.gcode.box(app.gcodelist.activeBlock(),
				self["dx"], self["dy"], self["dz"],
				self["nx"], self["ny"], self["nz"],
				self["profile"], self["cut"], self["overcut"])
		app.gcodelist.fill()
		app.draw()
		app.statusbar["text"] = "BOX with fingers generated"

#==============================================================================
# CNC machine configuration
#==============================================================================
class CNC(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "CNC"
		self.variables = [
			("units"         , "bool", 0    , "Units (inches)")   ,
			("acceleration_x", "mm"  , 25.0 , "Acceleration x")   ,
			("acceleration_y", "mm"  , 25.0 , "Acceleration y")   ,
			("acceleration_z", "mm"  , 5.0  , "Acceleration z")   ,
			("feedmax_x"     , "mm"  , 3000., "Feed max x")       ,
			("feedmax_y"     , "mm"  , 3000., "Feed max y")       ,
			("feedmax_z"     , "mm"  , 2000., "Feed max z")       ,
			("travel_x"      , "mm"  , 200  , "Travel x")         ,
			("travel_y"      , "mm"  , 200  , "Travel y")         ,
			("travel_z"      , "mm"  , 100  , "Travel z")         ,
			("round"         , "int" , 4    , "Decimal digits")   ,
			("accuracy"      , "mm"  , 0.1  , "Plotting Arc accuracy")     ,
			("startup"       , "str" , "G90", "startup")          ,
			("spindlemin"    , "int" , 0    , "Spindle min (RPM)"),
			("spindlemax"    , "int" , 12000, "Spindle max (RPM)"),
			("header"        , "text" ,   "", "Header gcode"),
			("footer"        , "text" ,   "", "Footer gcode")
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.inches = self["units"]
		self.master.digits = int(self["round"])
		self.master.cnc().decimal = self.master.digits
		self.master.gcode.header = self["header"]
		self.master.gcode.footer = self["footer"]
		return False

#==============================================================================
# Material database
#==============================================================================
class Material(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Material"
		self.variables = [
			("name",    "db",    "", "Name"),
			("feed",    "mm"  , 10., "Feed"),
			("feedz",   "mm"  ,  1., "Plunge Feed"),
			("stepz",   "mm"  ,  1., "Depth Increment")
		 ]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		# update ONLY if stock material is empty:
		if self.master["stock"]["material"] == "":
			self.master.gcode.feed  = self.master.fromMm(self["feed"])
			self.master.gcode.feedz = self.master.fromMm(self["feedz"])
			self.master.gcode.stepz = self.master.fromMm(self["stepz"])
		return False

#==============================================================================
# EndMill Bit database
#==============================================================================
class EndMill(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "EndMill"
		self.variables = [
			("name",       "db",     "", "Name"),
			("type",     "list",     "", "Type"),
			("shape",    "list",     "", "Shape"),
			("material", "list",     "", "Material"),
			("coating",  "list",     "", "Coating"),
			("diameter",   "mm",  3.175, "Diameter"),
			("axis",       "mm",  3.175, "Mount Axis"),
			("flutes",    "int",      2, "Flutes"),
			("length",     "mm",   20.0, "Length"),
			("angle",   "float",     "", "Angle")
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.gcode.diameter  = self.master.fromMm(self["diameter"])
		return False

#==============================================================================
# Stock material on worksurface
#==============================================================================
class Stock(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Stock"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("material",  "db" ,    "", "Material"),
			("safe"  ,    "mm" ,   3.0, "Safe Z"),
			("surface",   "mm" ,   0.0, "Surface Z"),
			("thickness", "mm" ,   5.0, "Thickness")
		]

	# ----------------------------------------------------------------------
	# Update variables after edit command
	# ----------------------------------------------------------------------
	def update(self):
		self.master.gcode.safe      = self.master.fromMm(self["safe"])
		self.master.gcode.surface   = self.master.fromMm(self["surface"])
		self.master.gcode.thickness = self.master.fromMm(self["thickness"])
		if self["material"]:
			self.master["material"].makeCurrent(self["material"])
		return False

#==============================================================================
# Cut material
#==============================================================================
class Cut(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "Cut"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("depth"  ,   "mm" ,    "", "Target Depth"),
			("stepz"  ,   "mm" ,    "", "Depth Increment")
		]
		self.buttons  = ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		try:
			h = self.master.fromMm(float(self["depth"]))
		except:
			h = None
		try:
			s =  self.master.fromMm(float(self["stepz"]))
		except:
			s = None
		app.executeOnSelection("CUT",h, s)
		app.statusbar["text"] = "CUT selected paths"

#==============================================================================
# Drill material
#==============================================================================
class Drill(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "Drill"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("depth",     "mm" ,    "", "Target Depth"),
			("peck",      "mm" ,    "", "Peck depth")
		]
		self.buttons  = ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		try:
			h = self.master.fromMm(float(self["depth"]))
		except:
			h = None
		try:
			p =  self.master.fromMm(float(self["peck"]))
		except:
			p = None
		app.executeOnSelection("DRILL",h, p)
		app.statusbar["text"] = "DRILL selected points"

#==============================================================================
# Profile
#==============================================================================
class Profile(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "Profile"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("endmill",   "db" ,    "", "End Mill"),
			("overcut",  "bool",     1, "Overcut"),
			("direction","inside,outside" , "outside", "Direction"),
			("cut",      "bool",     0, "Cut")
		]
		self.buttons  = ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		direction = self["direction"]
		app.profile(direction)
		#if self["cut"]:
		#	app.executeOnSelection("CUT")
		app.statusbar["text"] = "Generate profile path"

#==============================================================================
class Spirograph(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "Spirograph"
		self.variables = [
			("Name",      "db" ,    "Spirograph", "Name"),
			("Depth"  ,   "mm" ,    0, "Target Depth"),
            ("ZSafe"  ,   "mm" ,    5, "Z safe height"),
			("RadiusExternal"  ,   "mm" ,    100, "External Radius"),
			("RadiusInternal"  ,   "mm" ,    65, "Internal Radius"),
			("RadiusOffset"  ,   "mm" ,    40, "Offset radius"),
            ("Feed"  ,   "int" ,    100, "Feed"),
		]
		self.buttons  = ("exe",)

	# ----------------------------------------------------------------------
	def execute(self, app):
		app.gcode.spirograph(app.gcodelist.activeBlock(),
				self["RadiusExternal"],
				self["RadiusInternal"],
				self["RadiusOffset"],
                self["Depth"],
                self["ZSafe"],
                self["Feed"])
		app.gcodelist.fill()
		app.draw()
		app.statusbar["text"] = "Spirograph generated"

#==============================================================================
# Tools container class
#==============================================================================
class Tools:
	def __init__(self, gcode):
		self.gcode  = gcode
		self.inches = False
		self.digits = 4

		self.tools   = {}
		self.buttons = {}
		self.listbox = None
		# CNC should be first to load the inches
		#	"Cut"       #	"Hole"      #	"Profile"   #	"Rectangle" #	"Tab"
		for cls in [ CNC, Box, Cut, Drill, EndMill, Material, Profile, Stock, Spirograph]:
			tool = cls(self)
			self.tools[tool.name.upper()] = tool

	# ----------------------------------------------------------------------
	def setListbox(self, listbox):
		self.listbox = listbox

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
	def load(self, config):
		for tool in self.tools.values():
			tool.load(config)

	# ----------------------------------------------------------------------
	def save(self, config):
		for tool in self.tools.values():
			tool.save(config)

	# ----------------------------------------------------------------------
	def __getitem__(self, name):
		return self.tools[name.upper()]

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
		if tool.buttons is None: return
		for name in tool.buttons:
			self.buttons[name].config(state=NORMAL)

#==============================================================================
class ToolFrame(Frame):
	def __init__(self, master, app, tools):
		Frame.__init__(self, master)
		self.app   = app
		self.tools = tools

		f = Frame(self)
		f.pack(side=TOP, fill=X)

		self.combo = tkExtra.Combobox(f, True,
					#foreground="DarkBlue",
					background="White",
					command=self.change)
		self.combo.pack(side=LEFT, expand=YES, fill=X)

		b = Button(f, image=Utils.icons["x"], command=self.delete)
		b.pack(side=RIGHT)
		self.tools.addButton("del",b)

		b = Button(f, image=Utils.icons["clone"], command=self.clone)
		b.pack(side=RIGHT)
		self.tools.addButton("clone",b)

		b = Button(f, image=Utils.icons["add"], command=self.add)
		b.pack(side=RIGHT)
		self.tools.addButton("add",b)

		b = Button(f, image=Utils.icons["rename"], command=self.rename)
		b.pack(side=RIGHT)
		self.tools.addButton("rename",b)

		b = Button(self, text="Execute",
				image=Utils.icons["gear"],
				compound=LEFT,
				foreground="DarkRed",
				background="LightYellow",
				command=self.execute)
		b.pack(side=BOTTOM, fill=X)
		self.tools.addButton("exe",b)

		self.toolList = tkExtra.MultiListbox(self,
					(("Name", 16, None),
					 ("Value", 24, None)),
					 header = False,
					 stretch = "last",
					 background = "White")
		self.toolList.sortAssist = None
		self.toolList.pack(side=BOTTOM, fill=BOTH, expand=YES)
		self.toolList.bindList("<Double-1>",	self.edit)
		self.toolList.bindList("<F2>",		self.rename)
		self.toolList.bindList("<Return>",	self.edit)
#		self.toolList.bindList("<Key-space>",	self.commandFocus)
#		self.toolList.bindList("<Control-Key-space>",	self.commandFocus)
		self.toolList.lists[1].bind("<ButtonRelease-1>", self.edit)
		self.tools.setListbox(self.toolList)

	#----------------------------------------------------------------------
	# Populate listbox with new values
	#----------------------------------------------------------------------
	def change(self):
		tool = self.tools[self.combo.get()]
		tool.populate()
		self.tools.activateButtons(tool)

	#----------------------------------------------------------------------
	# Edit tool listbox
	#----------------------------------------------------------------------
	def edit(self, event=None):
		self.tools[self.combo.get()].edit(event)

	#----------------------------------------------------------------------
	def rename(self, event=None):
		self.tools[self.combo.get()].edit(event)

	#----------------------------------------------------------------------
	def execute(self, event=None):
		self.tools[self.combo.get()].execute(self.app)

	#----------------------------------------------------------------------
	def add(self, event=None):
		self.tools[self.combo.get()].add()

	#----------------------------------------------------------------------
	def delete(self, event=None):
		self.tools[self.combo.get()].delete()

	#----------------------------------------------------------------------
	def clone(self, event=None):
		self.tools[self.combo.get()].clone()

	#----------------------------------------------------------------------
	def rename(self, event=None):
		self.tools[self.combo.get()].rename()

	#----------------------------------------------------------------------
	def set(self, tool):
		self.combo.set(tool)

	#----------------------------------------------------------------------
	def get(self):
		return self.combo.get()

	#----------------------------------------------------------------------
	def fill(self):
		self.combo.fill(self.tools.names())
