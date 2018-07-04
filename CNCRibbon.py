# -*- coding: utf-8 -*-
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import tkinter as tk

import Ribbon
import tkExtra

#===============================================================================
# Link to main app
#===============================================================================
class _LinkApp:
	def __init__(self, app):
		self.app = app

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def addWidget(self, widget):
		self.app.widgets.append(widget)

	#----------------------------------------------------------------------
	# Send a command to Grbl
	#----------------------------------------------------------------------
	def sendGCode(self, cmd):
		self.app.sendGCode(cmd)

	#----------------------------------------------------------------------
	# Accept the user key if not editing any text
	#----------------------------------------------------------------------
	def acceptKey(self, skipRun=False):
		return self.app.acceptKey(skipRun)

	#----------------------------------------------------------------------
	def saveConfig(self):
		pass

	#----------------------------------------------------------------------
	def loadConfig(self):
		pass

#===============================================================================
# Button Group, a group of widgets that will be placed in the ribbon
#===============================================================================
class ButtonGroup(Ribbon.LabelGroup, _LinkApp):
	def __init__(self, master, name, app):
		Ribbon.LabelGroup.__init__(self, master, name)
		_LinkApp.__init__(self, app)
		if ":" in name:
			self.label["text"] = name.split(":")[1]

#===============================================================================
# Button Group, a group of widgets that will be placed in the ribbon
#===============================================================================
class ButtonMenuGroup(Ribbon.MenuGroup, _LinkApp):
	def __init__(self, master, name, app, menulist=None):
		Ribbon.MenuGroup.__init__(self, master, name, menulist)
		_LinkApp.__init__(self, app)

#===============================================================================
# Page, Frame
#===============================================================================
class PageFrame(tk.Frame, _LinkApp):
	def __init__(self, master, name, app):
		super().__init__(master)
		_LinkApp.__init__(self, app)
		self.name = name

#===============================================================================
# Page, LabelFrame
#===============================================================================
class PageLabelFrame(tk.LabelFrame, _LinkApp):
	def __init__(self, master, name, name_alias_lng, app):
		tk.LabelFrame.__init__(self, master, text=name_alias_lng, foreground="DarkBlue")
		_LinkApp.__init__(self, app)
		self.name = name

#===============================================================================
# Page, ExLabelFrame
#===============================================================================
class PageExLabelFrame(tkExtra.ExLabelFrame, _LinkApp):
	def __init__(self, master, name, name_alias_lng, app):
		tkExtra.ExLabelFrame.__init__(self, master, text=name_alias_lng, foreground="DarkBlue")
		_LinkApp.__init__(self, app)
		self.name = name

#===============================================================================
# CNC Page interface between the basic Page class and the bCNC class
#===============================================================================
class Page(Ribbon.Page):
	groups = {}
	frames = {}

	def __init__(self, master, app, **kw):
		self.app = app
		super().__init__(master, **kw)
		self.register()

	#----------------------------------------------------------------------
	# Should be overridden with the groups and frames to register
	#----------------------------------------------------------------------
	def register(self):
		pass

	#----------------------------------------------------------------------
	# Register groups
	#----------------------------------------------------------------------
	def _register(self, groups, frames):
		if groups:
			for g in groups:
				w = g(self.master._ribbonFrame, self.app)
				Page.groups[w.name] = w

		if frames:
			for f in frames:
				w = f(self.master._pageFrame, self.app)
				Page.frames[w.name] = w

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def addWidget(self, widget):
		self.app.widgets.append(widget)

	#----------------------------------------------------------------------
	# Send a command to Grbl
	#----------------------------------------------------------------------
	def sendGCode(self, cmd):
		self.app.sendGCode(cmd)

	#----------------------------------------------------------------------
	def addRibbonGroup(self, name, **args):
		if not args: args = {"side":tk.LEFT, "fill":tk.BOTH}
		self.ribbons.append((Page.groups[name], args))

	#----------------------------------------------------------------------
	def addPageFrame(self, name, **args):
		if not args: args = {"side":tk.TOP, "fill":tk.BOTH}
		if isinstance(name,str):
			self.frames.append((Page.frames[name], args))
		else:
			self.frames.append((name, args))

	#----------------------------------------------------------------------
	@staticmethod
	def saveConfig():
		for frame in Page.frames.values():
			frame.saveConfig()

	#----------------------------------------------------------------------
	@staticmethod
	def loadConfig():
		for frame in Page.frames.values():
			frame.loadConfig()
