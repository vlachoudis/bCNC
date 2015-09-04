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

import os
import glob
import Utils
import Ribbon
import tkExtra
import CNCRibbon

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
		self.icon      = None
		self.plugin    = False
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
	# Load from a configuration file
	# ----------------------------------------------------------------------
	def loadConfig(self):
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
					self.listdb[p].append(Utils.getStr(self.name, key))

			for lst in self.listdb.values():
				lst.sort()

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
	def saveConfig(self):
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
		self.buttons  = ["add","delete","clone","rename"]

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
class Plugin(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.plugin = True

#==============================================================================
# CNC machine configuration
#==============================================================================
class CNC(Base):
	def __init__(self, master):
		Base.__init__(self, master)
		self.name = "CNC"
		self.variables = [
			("units"         , "bool", 0    , "Units (inches)")   ,
			("lasercutter"   , "bool", 0    , "Lasercutter")   ,
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
		stockmat = self.master["stock"]["material"]
		if stockmat=="" or stockmat==self["name"]:
			self.master.cnc()["cutfeed"]  = self.master.fromMm(self["feed"])
			self.master.cnc()["cutfeedz"] = self.master.fromMm(self["feedz"])
			self.master.cnc()["stepz"]    = self.master.fromMm(self["stepz"])
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
		self.master.cnc()["diameter"] = self.master.fromMm(self["diameter"])
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
		self.master.cnc()["safe"]      = self.master.fromMm(self["safe"])
		self.master.cnc()["surface"]   = self.master.fromMm(self["surface"])
		self.master.cnc()["thickness"] = self.master.fromMm(self["thickness"])
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
			("name",      "db" ,    "", "Name"),
			("depth"  ,   "mm" ,    "", "Target Depth"),
			("stepz"  ,   "mm" ,    "", "Depth Increment")
		]
		self.buttons.append("exe")

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
		app.setStatus("CUT selected paths")

#==============================================================================
# Drill material
#==============================================================================
class Drill(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Drill"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("depth",     "mm" ,    "", "Target Depth"),
			("peck",      "mm" ,    "", "Peck depth")
		]
		self.buttons.append("exe")

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
		app.setStatus("DRILL selected points")

#==============================================================================
# Profile
#==============================================================================
class Profile(DataBase):
	def __init__(self, master):
		DataBase.__init__(self, master)
		self.name = "Profile"
		self.variables = [
			("name",      "db" ,    "", "Name"),
			("endmill",   "db" ,    "", "End Mill"),
			("direction","inside,outside" , "outside", "Direction"),
			("scale",   "float",   1.0, "Scale tool diameter"),
			("overcut",  "bool",     1, "Overcut"),
			("cut",      "bool",     0, "Cut")
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		if self["endmill"]:
			self.master["endmill"].makeCurrent(self["endmill"])
		direction = self["direction"]
		app.profile(direction, self["scale"], self["cut"], self["overcut"])
		app.setStatus("Generate profile path")

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
		for cls in [ CNC, Cut, Drill, EndMill, Material, Profile, Stock]:
			tool = cls(self)
			self.addTool(tool)

		# Find plugins in the plugins directory and load them
		for f in sorted(glob.glob("%s/plugins/*.py"%(Utils.prgpath))):
			name,ext = os.path.splitext(os.path.basename(f))
			try:
				exec("import %s"%(name))
			except ImportError:
				continue
			try:
				tool = eval("%s.Tool(self)"%(name))
				self.addTool(tool)
			except AttributeError:
				continue

	# ----------------------------------------------------------------------
	def addTool(self, tool):
		self.tools[tool.name.upper()] = tool

	# ----------------------------------------------------------------------
	# Return a list of plugins
	# ----------------------------------------------------------------------
	def pluginList(self):
		return [x for x in self.tools.values() if x.plugin]

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
	def loadConfig(self):
		self.active.set(Utils.getStr(Utils.__prg__, "tool", "CNC"))
		for tool in self.tools.values():
			tool.loadConfig()

	# ----------------------------------------------------------------------
	def saveConfig(self):
		Utils.setStr(Utils.__prg__, "tool", self.active.get())
		for tool in self.tools.values():
			tool.saveConfig()

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

#===============================================================================
# DataBase Group
#===============================================================================
class DataBaseGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Database", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["stock32"],
				text="Stock",
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Stock",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=2, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Stock material currently on machine")
		self.addWidget(b)

		# ===
		col,row=1,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["material"],
				text="Material",
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Material",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Editable database of material properties")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["endmill"],
				text="End Mill",
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="EndMill",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Editable database of EndMills properties")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolRename>>",
				image=Utils.icons["rename"],
				text="Rename",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Edit name of current operation/object")
		self.addWidget(b)
		app.tools.addButton("rename",b)

		# ===
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, app, "<<ToolAdd>>",
				image=Utils.icons["add"],
				text="Add",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Add a new operation/object")
		self.addWidget(b)
		app.tools.addButton("add",b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolClone>>",
				image=Utils.icons["clone"],
				text="Clone",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Clone selected operation/object")
		self.addWidget(b)
		app.tools.addButton("clone",b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<ToolDelete>>",
				image=Utils.icons["x"],
				text="Delete",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Delete selected operation/object")
		self.addWidget(b)
		app.tools.addButton("delete",b)

#===============================================================================
# CAM Group
#===============================================================================
class CAMGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "CAM", app)
		self.grid3rows()

		# ===
		col,row=0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["cut32"],
				text="Cut",
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Cut",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Cut for the full stock thickness selected code")
		self.addWidget(b)

		# ===
		col,row=1,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["profile32"],
				text="Profile",
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="Profile",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=1, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Perform a profile operation on selected code")
		self.addWidget(b)

		# ===
		col,row=2,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["pocket"],
				text="Pocket",
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Pocket",
				state=DISABLED,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Perform a pocket operation on selected code")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["drill"],
				text="Drill",
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Drill",
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Insert a drill cycle on current objects/location")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["tab"],
				text="Tabs",
				compound=LEFT,
				anchor=W,
				variable=app.tools.active,
				value="Tabs",
				state=DISABLED,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Insert holding tabs")
		self.addWidget(b)

#===============================================================================
# Macros Group
#===============================================================================
class MacrosGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Macros", app)
		self.grid3rows()

		col,row=0,0
		# Find plugins in the plugins directory and load them
		for tool in app.tools.pluginList():
			# ===
			b = Ribbon.LabelRadiobutton(self.frame,
					image=Utils.icons[tool.icon],
					text=tool.name,
					compound=LEFT,
					anchor=W,
					variable=app.tools.active,
					value=tool.name,
					background=Ribbon._BACKGROUND)
			b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
			tkExtra.Balloon.set(b, tool.__doc__)
			self.addWidget(b)

			row += 1
			if row==3:
				col += 1
				row  = 0

#===============================================================================
# Config
#===============================================================================
class ConfigGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Config", app)

		# ===
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["config32"],
				text="Config",
				compound=TOP,
				anchor=W,
				variable=app.tools.active,
				value="CNC",
				background=Ribbon._BACKGROUND)
		b.pack(fill=BOTH, expand=YES)
		tkExtra.Balloon.set(b, "Configuration for bCNC")
		self.addWidget(b)

#==============================================================================
# Tools Frame
#==============================================================================
class ToolsFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Tools", app)
		self.tools = app.tools

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

		app.tools.active.trace('w',self.change)
		self.change()

	#----------------------------------------------------------------------
	# Populate listbox with new values
	#----------------------------------------------------------------------
	def change(self, a=None, b=None, c=None):
		tool = self.tools.getActive()
		tool.populate()
		tool.update()
		self.tools.activateButtons(tool)

	#----------------------------------------------------------------------
	# Edit tool listbox
	#----------------------------------------------------------------------
	def edit(self, event=None):
		self.tools.getActive().edit(event)

	#----------------------------------------------------------------------
	def rename(self, event=None):
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

#===============================================================================
# Tools Page
#===============================================================================
class ToolsPage(CNCRibbon.Page):
	"""GCode manipulation tools and user plugins"""

	_name_ = "Tools"
	_icon_ = "tools"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((DataBaseGroup,CAMGroup,MacrosGroup,ConfigGroup), (ToolsFrame,))

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
