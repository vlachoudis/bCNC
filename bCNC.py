#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

__version__ = "0.6.0"
__date__    = "3 Sep 2015"
__author__  = "Vasilis Vlachoudis"
__email__   = "vvlachoudis@gmail.com"

import os
import re
import sys
import pdb
import time
import getopt
import serial
import socket
import traceback

try:
	import Tkinter
	from Queue import *
	from Tkinter import *
	import ConfigParser
	import tkMessageBox
except ImportError:
	import tkinter
	from queue import *
	from tkinter import *
	import configparser as ConfigParser
	import tkinter.messagebox as tkMessageBox

import rexx
import tkExtra
import Unicode
import bFileDialog

from CNC import CNC, GCode
import Utils
import Ribbon
import Pendant
from Sender import Sender, NOT_CONNECTED, STATECOLOR, STATECOLORDEF

import CNCList
import CNCCanvas
import webbrowser

from CNCRibbon    import Page
from ToolsPage	  import Tools, ToolsPage
from FilePage     import FilePage
from ControlPage  import ControlPage
from TerminalPage import TerminalPage
from ProbePage    import ProbePage
from EditorPage   import EditorPage

_openserial = True	# override ini parameters
_device     = None
_baud       = None

MONITOR_AFTER =  200	# ms
DRAW_AFTER    =  300	# ms

RX_BUFFER_SIZE = 128

MAX_HISTORY  = 500

#ZERO = ["G28", "G30", "G92"]

FILETYPES = [	("All accepted", ("*.ngc","*.nc", "*.gcode", "*.dxf", "*.probe")),
		("G-Code",("*.ngc","*.nc", "*.gcode")),
		("DXF",    "*.dxf"),
		("SVG",    "*.svg"),
		("Probe",  "*.probe"),
		("All",    "*")]

geometry = None

#==============================================================================
# Main Application window
#==============================================================================
class Application(Toplevel,Sender):
	def __init__(self, master, **kw):
		Toplevel.__init__(self, master, **kw)
		Sender.__init__(self)

		self.iconbitmap("@%s/bCNC.xbm"%(Utils.prgpath))
		self.title(Utils.__prg__)
		self.widgets = []

		# Global variables
		self.tools = Tools(self.gcode)
		self.loadConfig()

		# --- Ribbon ---
		self.ribbon = Ribbon.TabRibbonFrame(self)
		self.ribbon.pack(side=TOP, fill=X)

		# Main frame
		self.paned = PanedWindow(self, orient=HORIZONTAL)
		self.paned.pack(fill=BOTH, expand=YES)

		# Status bar
		frame = Frame(self)
		frame.pack(side=BOTTOM, fill=X)
		self.statusbar = tkExtra.ProgressBar(frame, height=20, relief=SUNKEN)
		self.statusbar.pack(side=LEFT, fill=X, expand=YES)
		self.statusbar.configText(fill="DarkBlue", justify=LEFT, anchor=W)

		self.statusz = Label(frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10)
		self.statusz.pack(side=RIGHT)
		self.statusy = Label(frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10)
		self.statusy.pack(side=RIGHT)
		self.statusx = Label(frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10)
		self.statusx.pack(side=RIGHT)

		# --- Left side ---
		frame = Frame(self.paned)
		self.paned.add(frame) #, minsize=340)

		pageframe = Frame(frame)
		pageframe.pack(side=TOP, expand=YES, fill=BOTH)
		self.ribbon.setPageFrame(pageframe)

		# Command bar
		f = Frame(frame)
		f.pack(side=BOTTOM, fill=X)
		self.cmdlabel = Label(f, text="Command:")
		self.cmdlabel.pack(side=LEFT)
		self.command = Entry(f, relief=SUNKEN, background="White")
		self.command.pack(side=RIGHT, fill=X, expand=YES)
		self.command.bind("<Return>",	self.cmdExecute)
		self.command.bind("<Up>",	self.commandHistoryUp)
		self.command.bind("<Down>",	self.commandHistoryDown)
		self.command.bind("<FocusIn>",	self.commandFocusIn)
		self.command.bind("<FocusOut>",	self.commandFocusOut)
		self.command.bind("<Control-Key-z>",	self.undo)
		self.command.bind("<Control-Key-Z>",	self.redo)
		self.command.bind("<Control-Key-y>",	self.redo)
		tkExtra.Balloon.set(self.command,
			"MDI Command line: Accept g-code commands or macro "
			"commands (RESET/HOME...) or editor commands "
			"(move,inkscape, round...) [Space or Ctrl-Space]")
		self.widgets.append(self.command)

		# --- Right side ---
		frame = Frame(self.paned)
		self.paned.add(frame)

		# --- Canvas ---
		self.canvasFrame = CNCCanvas.CanvasFrame(frame, self)
		self.canvasFrame.pack(side=TOP, fill=BOTH, expand=YES)
		#self.paned.add(self.canvasFrame)
# XXX FIXME do I need the self.canvas?
		self.canvas = self.canvasFrame.canvas

		# fist create Pages
		self.pages = {}
		for cls in (	ControlPage,
				EditorPage,
				FilePage,
				ProbePage,
				TerminalPage,
				ToolsPage):
			page = cls(self.ribbon, self)
			self.pages[page.name] = page

		# then add their properties (in separate loop)
		for name,page in self.pages.items():
			for n in Utils.getStr(Utils.__prg__,"%s.ribbon"%(page.name)).split():
				page.addRibbonGroup(n)

			for n in Utils.getStr(Utils.__prg__,"%s.page"%(page.name)).split():
				last = n[-1]
				if last == "*":
					page.addPageFrame(n[:-1],fill=BOTH,expand=TRUE)
				else:
					page.addPageFrame(n)

		# remember the editor list widget
		self.dro       = Page.frames["DRO"]
		self.gstate    = Page.frames["State"]
		self.control   = Page.frames["Control"]
		self.editor    = Page.frames["Editor"].editor
		self.terminal  = Page.frames["Terminal"].terminal

		# XXX FIXME Do we need it or I can takes from Page every time?
		self.autolevel = Page.frames["Probe:Autolevel"]

		# Left side
		for name in Utils.getStr(Utils.__prg__,"ribbon").split():
			last = name[-1]
			if last == '>':
				name = name[:-1]
				side = RIGHT
			else:
				side = LEFT
			self.ribbon.addPage(self.pages[name],side)

		# Restore last page
		self.ribbon.changePage(Utils.getStr(Utils.__prg__,"page", "File"))

		# Global bindings
		self.bind('<<Undo>>',           self.undo)
		self.bind('<<Redo>>',           self.redo)
		self.bind('<<Copy>>',           self.copy)
		self.bind('<<Cut>>',            self.cut)
		self.bind('<<Paste>>',          self.paste)

		self.bind('<<Connect>>',	self.openClose)

		self.bind('<<New>>',            self.newFile)
		self.bind('<<Open>>',           self.loadDialog)
		self.bind('<<Save>>',           self.saveAll)
		self.bind('<<SaveAs>>',         self.saveDialog)
		self.bind('<<Reload>>',         self.reload)

		self.bind('<<Recent0>>',        self._loadRecent0)
		self.bind('<<Recent1>>',        self._loadRecent1)
		self.bind('<<Recent2>>',        self._loadRecent2)
		self.bind('<<Recent3>>',        self._loadRecent3)
		self.bind('<<Recent4>>',        self._loadRecent4)
		self.bind('<<Recent5>>',        self._loadRecent5)
		self.bind('<<Recent6>>',        self._loadRecent6)
		self.bind('<<Recent7>>',        self._loadRecent7)
		self.bind('<<Recent8>>',        self._loadRecent8)
		self.bind('<<Recent9>>',        self._loadRecent9)

		self.bind('<<TerminalClear>>',  Page.frames["Terminal"].clear)
		self.bind('<<AlarmClear>>',     self.alarmClear)
		self.bind('<<Help>>',           self.help)

		tkExtra.bindEventData(self, "<<Status>>",    self.updateStatus)
		tkExtra.bindEventData(self, "<<Coords>>",    self.updateCanvasCoords)

		# Editor bindings
		self.bind("<<Add>>",			self.editor.insertItem)
		self.bind("<<Clone>>",			self.editor.clone)
		self.bind("<<Delete>>",			self.editor.deleteLine)
		self.canvas.bind("<Control-Key-Prior>",	self.editor.orderUp)
		self.canvas.bind("<Control-Key-Next>",	self.editor.orderDown)
		self.canvas.bind("<Delete>",		self.editor.deleteLine)
		self.canvas.bind("<BackSpace>",		self.editor.deleteLine)
		self.canvas.bind('<Control-Key-c>',	self.copy)
		self.canvas.bind('<Control-Key-x>',	self.cut)
		self.canvas.bind('<Control-Key-v>',	self.paste)
		try:
			self.canvas.bind("<KP_Delete>",	self.editor.deleteLine)
		except:
			pass
		self.bind('<<Invert>>',		self.editor.invertBlocks)
		self.bind('<<Expand>>',		self.editor.toggleExpand)
		self.bind('<<Enable>>',		self.editor.toggleEnable)

		# Canvas X-bindings
		self.bind("<<ViewChange>>",	self.viewChange)

		frame = Page.frames["Probe:Probe"]
		self.bind('<<Probe>>',            frame.probe)
		frame = Page.frames["Probe:Center"]
		self.bind('<<ProbeCenter>>',      frame.probe)
		frame = Page.frames["Probe:Tool"]
		self.bind('<<ToolCalibrate>>',    frame.probe)
		self.bind('<<ToolChange>>',       frame.change)

		self.bind('<<AutolevelMargins>>', self.autolevel.getMargins)
		self.bind('<<AutolevelZero>>',    self.autolevel.setZero)
		self.bind('<<AutolevelClear>>',   self.autolevel.clear)
		self.bind('<<AutolevelScan>>',    self.autolevel.scan)

		self.bind('<<CanvasFocus>>',	self.canvasFocus)
		self.bind('<<Draw>>',	        self.draw)
		self.bind('<<DrawProbe>>',	lambda e,c=self.canvasFrame:c.drawProbe(True))

		self.bind('<Escape>',		self.unselectAll)
		self.bind('<Control-Key-a>',	self.selectAll)
#		self.bind('<Control-Key-f>',	self.find)
#		self.bind('<Control-Key-g>',	self.findNext)
#		self.bind('<Control-Key-h>',	self.replace)
		self.bind('<Control-Key-e>',	self.editor.toggleExpand)
		self.bind('<Control-Key-l>',	self.editor.toggleEnable)
		self.bind('<Control-Key-q>',	self.quit)
		self.bind('<Control-Key-o>',	self.loadDialog)
		self.bind('<Control-Key-r>',	self.drawAfter)
		self.bind("<Control-Key-s>",	self.saveAll)
		self.bind('<Control-Key-y>',	self.redo)
		self.bind('<Control-Key-z>',	self.undo)
		self.bind('<Control-Key-Z>',	self.redo)
		self.canvas.bind('<Key-space>',	self.commandFocus)
		self.bind('<Control-Key-space>',self.commandFocus)

		tools = self.pages["Tools"]
		self.bind('<<ToolAdd>>',	tools.add)
		self.bind('<<ToolDelete>>',	tools.delete)
		self.bind('<<ToolClone>>',	tools.clone)
		self.bind('<<ToolRename>>',	tools.rename)

#		self.bind('<F1>',		self.help)
#		self.bind('<F2>',		self.rename)
#		self.bind('<F3>',		self.canvasFrame.viewXY)
#		self.bind('<F4>',		self.canvasFrame.viewXZ)
#		self.bind('<F5>',		self.canvasFrame.viewYZ)
#		self.bind('<F6>',		self.canvasFrame.viewISO1)
#		self.bind('<F7>',		self.canvasFrame.viewISO2)
#		self.bind('<F8>',		self.canvasFrame.viewISO3)

		self.bind('<Up>',		self.control.moveYup)
		self.bind('<Down>',		self.control.moveYdown)
		self.bind('<Right>',		self.control.moveXup)
		self.bind('<Left>',		self.control.moveXdown)
		self.bind('<Prior>',		self.control.moveZup)
		self.bind('<Next>',		self.control.moveZdown)

		self.bind('<Key-plus>',		self.control.incStep)
		self.bind('<Key-equal>',	self.control.incStep)
		self.bind('<KP_Add>',		self.control.incStep)
		self.bind('<Key-minus>',	self.control.decStep)
		self.bind('<Key-underscore>',	self.control.decStep)
		self.bind('<KP_Subtract>',	self.control.decStep)

		self.bind('<Key-asterisk>',	self.control.mulStep)
		self.bind('<KP_Multiply>',	self.control.mulStep)
		self.bind('<Key-slash>',	self.control.divStep)
		self.bind('<KP_Divide>',	self.control.divStep)

		self.bind('<Key-exclam>',	self.feedHold)
		self.bind('<Key-asciitilde>',	self.resume)

		for x in self.widgets:
			if isinstance(x,Entry):
				x.bind("<Escape>", self.canvasFocus)

		self.bind('<FocusIn>',		self.focusIn)
		self.protocol("WM_DELETE_WINDOW", self.quit)

		self.canvas.focus_set()

		# Fill basic global variables
		CNC.vars["state"] = NOT_CONNECTED
		CNC.vars["color"] = STATECOLOR[NOT_CONNECTED]
		self._pendantFileUploaded = None
		self._drawAfter = None	# after handle for modification
		self._inFocus   = False
		self.monitorSerial()
		self.canvasFrame.toggleDrawFlag()

		self.paned.sash_place(0, Utils.getInt(Utils.__prg__, "sash", 340), 0)

		# Auto start pendant and serial
		if Utils.getBool("Connection","pendant"):
			self.startPendant(False)

		if _openserial and Utils.getBool("Connection","openserial"):
			self.openClose()

	#-----------------------------------------------------------------------
	def setStatus(self, msg):
		self.statusbar.configText(text=msg, fill="DarkBlue")

	#-----------------------------------------------------------------------
	# Set a status message from an event
	#-----------------------------------------------------------------------
	def updateStatus(self, event):
		self.setStatus(event.data)

	#-----------------------------------------------------------------------
	# Update canvas coordinates
	#-----------------------------------------------------------------------
	def updateCanvasCoords(self, event):
		x,y,z = event.data.split()
		self.statusx["text"] = "X: "+x
		self.statusy["text"] = "Y: "+y
		self.statusz["text"] = "Z: "+z

	#-----------------------------------------------------------------------
	def quit(self, event=None):
		if self.running and self._quit<1:
			tkMessageBox.showinfo("Running",
				"CNC is currently running, please stop it before.",
				parent=self)
			self._quit += 1
			return
		del self.widgets[:]

		if self.gcode.isModified():
			# file is modified
			ans = tkMessageBox.askquestion("File modified",
				"Gcode was modified do you want to save it first?",
				parent=self)
			if ans==tkMessageBox.YES or ans==True:
				self.saveDialog()

		Sender.quit(self)
		self.saveConfig()
		self.destroy()
		if Utils.errors and Utils._errorReport:
			Utils.ReportDialog.sendErrorReport()
		tk.destroy()

	# ---------------------------------------------------------------------
	def configWidgets(self, var, value):
		for w in self.widgets:
			if isinstance(w,tuple):
				try:
					w[0].entryconfig(w[1], state=value)
				except TclError:
					pass
			elif isinstance(w,tkExtra.Combobox):
				w.configure(state=value)
			else:
				w[var] = value

	# ---------------------------------------------------------------------
	def busy(self):
		try:
			self.config(cursor="watch")
			self.update_idletasks()
		except TclError:
			pass

	# ----------------------------------------------------------------------
	def notBusy(self):
		try:
			self.config(cursor="")
		except TclError:
			pass

	# ---------------------------------------------------------------------
	def enable(self):
		self.configWidgets("state",NORMAL)

	def disable(self):
		self.configWidgets("state",DISABLED)

	#-----------------------------------------------------------------------
	def loadShortcuts(self):
		for name, value in Utils.config.items("Shortcut"):
			# Convert to uppercase
			key = name.title()
			self.unbind("<%s>"%(key))	# unbind any possible old value
			if value:
				self.bind("<%s>"%(key), lambda e,s=self,c=value : s.execute(c))

	#-----------------------------------------------------------------------
	def loadConfig(self):
		global geometry
		if geometry is None:
			geometry = "%sx%s" % (Utils.getInt(Utils.__prg__, "width",  900),
					      Utils.getInt(Utils.__prg__, "height", 650))
		try: self.geometry(geometry)
		except: pass

		#restore windowsState
		try:
			self.wm_state(Utils.getStr(Utils.__prg__, "windowstate", "normal"))
		except:
			pass

		self.tools.loadConfig()
		Sender.loadConfig(self)
		self.loadShortcuts()

	#-----------------------------------------------------------------------
	def saveConfig(self):
		# Program
		Utils.setInt(Utils.__prg__,  "width",    str(self.winfo_width()))
		Utils.setInt(Utils.__prg__,  "height",   str(self.winfo_height()))
		#Utils.setInt(Utils.__prg__,  "x",        str(self.winfo_rootx()))
		#Utils.setInt(Utils.__prg__,  "y",        str(self.winfo_rooty()))
		Utils.setInt(Utils.__prg__,  "sash",      str(self.paned.sash_coord(0)[0]))

		#save windowState
		Utils.setStr(Utils.__prg__,  "windowstate", str(self.wm_state()))
		Utils.setStr(Utils.__prg__,  "page",     str(self.ribbon.getActivePage().name))

		# Connection
		Page.saveConfig()
		Sender.saveConfig(self)
		self.tools.saveConfig()
		self.canvasFrame.saveConfig()

	#-----------------------------------------------------------------------
	def loadHistory(self):
		try:
			f = open(Utils.hisFile,"r")
		except:
			return
		self.history = [x.strip() for x in f]
		f.close()

	#-----------------------------------------------------------------------
	def saveHistory(self):
		try:
			f = open(Utils.hisFile,"w")
		except:
			return
		f.write("\n".join(self.history))
		f.close()

	#-----------------------------------------------------------------------
	def cut(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.cut()
			pass
#		elif focus:
#			focus.event_generate("<<Cut>>")

	#-----------------------------------------------------------------------
	def copy(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.copy()
			pass
#		elif focus:
#			focus.event_generate("<<Copy>>")

	#-----------------------------------------------------------------------
	def paste(self, event=None):
		focus = self.focus_get()
		if focus is self.canvas:
###			self.editor.paste()
			pass
#		elif focus:
#			focus.event_generate("<<Paste>>")

	#-----------------------------------------------------------------------
	def undo(self, event=None):
		if self.running: return
		if self.gcode.canUndo():
			self.gcode.undo();
			self.editor.fill()
			self.drawAfter()
		return "break"

	#-----------------------------------------------------------------------
	def redo(self, event=None):
		if self.running: return
		if self.gcode.canRedo():
			self.gcode.redo();
			self.editor.fill()
			self.drawAfter()
		return "break"

	#-----------------------------------------------------------------------
	def about(self, event=None):
		tkMessageBox.showinfo("About",
				"%s\nby %s [%s]\nVersion: %s\nLast Change: %s" % \
				(Utils.__prg__, __author__, __email__, __version__, __date__),
				parent=self)

	#-----------------------------------------------------------------------
	def alarmClear(self, event=None):
		self._alarm = False

	#-----------------------------------------------------------------------
	# FIXME Very primitive
	#-----------------------------------------------------------------------
	def showStats(self, event=None):
		msg  = "GCode: %s\n"%(self.gcode.filename)
		if not self.gcode.probe.isEmpty():
			msg += "Probe: %s\n"%(self.gcode.probe.filename)
		if CNC.inch:
			unit = "in"
		else:
			unit = "mm"
		msg += "Margins\tX:[%g .. %g]\n\tY:[%g .. %g]\n" % \
			(CNC.vars["xmin"], CNC.vars["xmax"], CNC.vars["ymin"], CNC.vars["ymax"])
		msg += "Movement Length: %g %s\n"%(self.cnc.totalLength, unit)
		msg += "Total Time: ~%.2g min\n"%(self.cnc.totalTime)
		tkMessageBox.showinfo("Statistics", msg, parent=self)

	#-----------------------------------------------------------------------
	def reportDialog(self, event=None):
		Utils.ReportDialog(self)

	#-----------------------------------------------------------------------
	def viewChange(self, event=None):
		if self.running:
			self._selectI = 0	# last selection pointer in items
		self.draw()

	# ----------------------------------------------------------------------
	def refresh(self, event=None):
		self.editor.fill()
		self.draw()

	# ----------------------------------------------------------------------
	def draw(self):
		view = CNCCanvas.VIEWS.index(self.canvasFrame.view.get())
		self.canvas.draw(view)
		self.selectionChange()

	# ----------------------------------------------------------------------
	# Redraw with a small delay
	# ----------------------------------------------------------------------
	def drawAfter(self, event=None):
		if self._drawAfter is not None: self.after_cancel(self._drawAfter)
		self._drawAfter = self.after(DRAW_AFTER, self.draw)

	#-----------------------------------------------------------------------
	def commandFocus(self, event=None):
		self.command.focus_set()

	#-----------------------------------------------------------------------
	def commandFocusIn(self, event=None):
		self.cmdlabel["foreground"] = "Blue"

	#-----------------------------------------------------------------------
	def commandFocusOut(self, event=None):
		self.cmdlabel["foreground"] = "Black"

	#-----------------------------------------------------------------------
	def canvasFocus(self, event=None):
		self.canvas.focus_set()
		return "break"

	#-----------------------------------------------------------------------
	def selectAll(self, event=None):
		self.ribbon.changePage("Editor")
		self.editor.selectAll()
		self.selectionChange()
		return "break"

	#-----------------------------------------------------------------------
	def unselectAll(self, event=None):
		focus = self.focus_get()
		if isinstance(focus, Entry) or \
		   isinstance(focus, Spinbox) or \
		   isinstance(focus, Listbox): return
		self.ribbon.changePage("Editor")
		self.editor.selectClear()
		self.selectionChange()
		return "break"

	#-----------------------------------------------------------------------
	def find(self, event=None):
		self.ribbon.changePage("Editor")
####		self.editor.findDialog()
#		return "break"
#
#	#-----------------------------------------------------------------------
	def findNext(self, event=None):
		self.ribbon.changePage("Editor")
####		self.editor.findNext()
#		return "break"
#
#	#-----------------------------------------------------------------------
	def replace(self, event=None):
		self.ribbon.changePage("Editor")
####		self.editor.replaceDialog()
#		return "break"

	#-----------------------------------------------------------------------
	def activeBlock(self):
		return self.editor.activeBlock()

	#-----------------------------------------------------------------------
	# Keyboard binding to <Return>
	#-----------------------------------------------------------------------
	def cmdExecute(self, event):
		self.commandExecute()

	# ----------------------------------------------------------------------
	def insertCommand(self, cmd, execute=False):
		self.command.delete(0,END)
		self.command.insert(0,cmd)
		if execute: self.commandExecute(False)

	#-----------------------------------------------------------------------
	# Execute command from command line
	#-----------------------------------------------------------------------
	def commandExecute(self, addHistory=True):
		line = self.command.get().strip()
		if not line: return

		if self._historyPos is not None:
			if self.history[self._historyPos] != line:
				self.history.append(line)
		elif not self.history or self.history[-1] != line:
			self.history.append(line)

		self._historyPos = None
		if len(self.history)>MAX_HISTORY:
			self.history.pop(0)
		self.command.delete(0,END)
		self.execute(line)

	#-----------------------------------------------------------------------
	# Execute a single command
	#-----------------------------------------------------------------------
	def execute(self, line):
		#print
		#print "<<<",line
		try:
			line = self.evaluate(line)
		except:
			tkMessageBox.showerror("Evaluation error",
				sys.exc_info()[1], parent=self)
			return
		#print ">>>",line

		if line is None: return

		if self.executeGcode(line): return

		oline = line.strip()
		line  = oline.replace(","," ").split()
		cmd   = line[0].upper()

		# ABO*UT: About dialog
		if rexx.abbrev("ABOUT",cmd,3):
			self.about()

		# CLE*AR: clear terminal
		elif rexx.abbrev("CLEAR",cmd,3) or cmd=="CLS":
			self.ribbon.changePage("Terminal")
			Page.frames["Terminal"].clear()

		# CONT*ROL: switch to control tab
		elif rexx.abbrev("CONTROL",cmd,4):
			self.ribbon.changePage("Control")

		# CUT [height] [pass-per-depth]: replicate selected blocks to cut-height
		# default values are taken from the active material
		elif cmd == "CUT":
			try:    h = float(line[1])
			except: h = None

			try:    d = float(line[2])
			except: d = None
			self.executeOnSelection("CUT", True, h, d)

		# DOWN: move downward in cutting order the selected blocks
		# UP: move upwards in cutting order the selected blocks
		elif cmd=="DOWN":
			self.editor.orderDown()
		elif cmd=="UP":
			self.editor.orderUp()

		# DRI*LL [depth] [peck]: perform drilling at all penetrations points
		elif rexx.abbrev("DRILL",cmd,3):
			try:    h = float(line[1])
			except: h = None

			try:    p = float(line[2])
			except: p = None
			self.executeOnSelection("DRILL", True, h, p)

		# ECHO <msg>: echo message
		elif cmd=="ECHO":
			self.setStatus(oline[5:].strip())

		# INV*ERT: invert selected blocks
		elif rexx.abbrev("INVERT",cmd,3):
			self.editor.invertBlocks()

		# MSG|MESSAGE <msg>: echo message
		elif cmd in ("MSG","MESSAGE"):
			tkMessageBox.showinfo("Message",oline[oline.find(" ")+1:].strip(), parent=self)

		# FIL*TER: filter editor blocks with text
		elif rexx.abbrev("FILTER",cmd,3) or cmd=="ALL":
			try:
				self.editor.filter = line[1]
			except:
				self.editor.filter = None
			self.editor.fill()

		# ED*IT: edit current line or item
		elif rexx.abbrev("EDIT",cmd,2):
			self.edit()

		# IM*PORT <filename>: import filename with gcode or dxf at cursor location
		# or at the end of the file
		elif rexx.abbrev("IMPORT",cmd,2):
			try:    self.importFile(line[1])
			except: self.importFile()

		# INK*SCAPE: remove uneccessary Z motion as a result of inkscape gcodetools
		elif rexx.abbrev("INKSCAPE",cmd,3):
			if len(line)>1 and rexx.abbrev("ALL",line[1].upper()):
				self.editor.selectAll()
			self.executeOnSelection("INKSCAPE", True)

		# ISO1: switch to ISO1 projection
		elif cmd=="ISO1":
			self.canvasFrame.viewISO1()
		# ISO2: switch to ISO2 projection
		elif cmd=="ISO2":
			self.canvasFrame.viewISO2()
		# ISO3: switch to ISO3 projection
		elif cmd=="ISO3":
			self.canvasFrame.viewISO3()

		# LO*AD [filename]: load filename containing g-code
		elif rexx.abbrev("LOAD",cmd,2) and len(line)==1:
			self.loadDialog()

		# MAT*ERIAL [name/height] [pass-per-depth] [feed]: set material from database or parameters
#		elif rexx.abbrev("MATERIAL",cmd,3):
#			tool = self.tools["Material"]
#			# MAT*ERIAL [height] [pass-depth] [feed]
#			try: self.height = float(line[1])
#			except: pass
#			try: self.depth_pass = float(line[2])
#			except: pass
#			try: self.feed = float(line[3])
#			except: pass
#			self.setStatus("Height: %g  Depth-per-pass: %g  Feed: %g"%(self.height,self.depth_pass, self.feed))

		# MIR*ROR [H*ORIZONTAL/V*ERTICAL]: mirror selected objects horizontally or vertically
		elif rexx.abbrev("MIRROR",cmd,3):
			if len(line)==1: return
			line1 = line[1].upper()
			#if nothing is selected:
			self.editor.selectAll()
			if rexx.abbrev("HORIZONTAL",line1):
				self.executeOnSelection("MIRRORH", False)
			elif rexx.abbrev("VERTICAL",line1):
				self.executeOnSelection("MIRRORV", False)

		elif rexx.abbrev("ORDER",cmd,2):
			if line[1].upper() == "UP":
				self.editor.orderUp()
			elif line[1].upper() == "DOWN":
				self.editor.orderDown()

		# MO*VE [|CE*NTER|BL|BR|TL|TR|UP|DOWN|x] [[y [z]]]:
		# move selected objects either by mouse or by coordinates
		elif rexx.abbrev("MOVE",cmd,2):
			if len(line)==1:
				self.canvas.setActionMove()
				return
			line1 = line[1].upper()
			dz = 0.0
			if rexx.abbrev("CENTER",line1,2):
				dx = -(CNC.vars["xmin"] + CNC.vars["xmax"])/2.0
				dy = -(CNC.vars["ymin"] + CNC.vars["ymax"])/2.0
				self.editor.selectAll()
			elif line1=="BL":
				dx = -CNC.vars["xmin"]
				dy = -CNC.vars["ymin"]
				self.editor.selectAll()
			elif line1=="BC":
				dx = -(CNC.vars["xmin"] + CNC.vars["xmax"])/2.0
				dy = -CNC.vars["ymin"]
				self.editor.selectAll()
			elif line1=="BR":
				dx = -CNC.vars["xmax"]
				dy = -CNC.vars["ymin"]
				self.editor.selectAll()
			elif line1=="TL":
				dx = -CNC.vars["xmin"]
				dy = -CNC.vars["ymax"]
				self.editor.selectAll()
			elif line1=="TC":
				dx = -(CNC.vars["xmin"] + CNC.vars["xmax"])/2.0
				dy = -CNC.vars["ymax"]
				self.editor.selectAll()
			elif line1=="TR":
				dx = -CNC.vars["xmax"]
				dy = -CNC.vars["ymax"]
				self.editor.selectAll()
			elif line1=="LC":
				dx = -CNC.vars["xmin"]
				dy = -(CNC.vars["ymin"] + CNC.vars["ymax"])/2.0
				self.editor.selectAll()
			elif line1=="RC":
				dx = -CNC.vars["xmax"]
				dy = -(CNC.vars["ymin"] + CNC.vars["ymax"])/2.0
				self.editor.selectAll()
			elif line1 in ("UP","DOWN"):
				dx = line1
				dy = dz = line1
			else:
				try:    dx = float(line[1])
				except: dx = 0.0
				try:    dy = float(line[2])
				except: dy = 0.0
				try:    dz = float(line[3])
				except: dz = 0.0
			self.executeOnSelection("MOVE", False, dx,dy,dz)

		# OPT*IIMZE: reorder selected blocks to minimize rapid motions
		elif rexx.abbrev("OPTIMIZE",cmd,3):
			self.executeOnSelection("OPTIMIZE", True)

		# ORI*GIN x y z: move origin to x,y,z by moving all to -x -y -z
		elif rexx.abbrev("ORIGIN",cmd,3):
			try:    dx = -float(line[1])
			except: dx = 0.0
			try:    dy = -float(line[2])
			except: dy = 0.0
			try:    dz = -float(line[3])
			except: dz = 0.0
			self.editor.selectAll()
			self.executeOnSelection("MOVE", False, dx,dy,dz)

		# PROF*ILE [offset]: create profile path
		elif rexx.abbrev("PROFILE",cmd,3):
			if len(line)>1:
				self.profile(line[1])
			else:
				self.profile()

		# REV*ERSE: reverse path direction
		elif rexx.abbrev("REVERSE", cmd, 3):
			self.executeOnSelection("REVERSE", True)

		# ROT*ATE [CCW|CW|FLIP|ang] [x0 [y0]]: rotate selected blocks
		# counter-clockwise(90) / clockwise(-90) / flip(180)
		# 90deg or by a specific angle and a pivot point
		elif rexx.abbrev("ROTATE",cmd,3):
			line1 = line[1].upper()
			x0 = y0 = 0.0
			if line1 == "CCW":
				ang = 90.0
				#self.editor.selectAll()
			elif line1 == "CW":
				ang = -90.0
				#self.editor.selectAll()
			elif line1=="FLIP":
				ang = 180.0
				#self.editor.selectAll()
			else:
				try: ang = float(line[1])
				except: pass
				try: x0 = float(line[2])
				except: pass
				try: y0 = float(line[3])
				except: pass
			self.executeOnSelection("ROTATE", False, ang,x0,y0)

		# ROU*ND [n]: round all digits to n fractional digits
		elif rexx.abbrev("ROUND",cmd,3):
			acc = None
			if len(line)>1:
				if rexx.abbrev("ALL",line[1].upper()):
					self.editor.selectAll()
				else:
					try:
						acc = int(line[1])
					except:
						pass
			self.executeOnSelection("ROUND", False, acc)

		# RU*LER: measure distances with mouse ruler
		elif rexx.abbrev("RULER",cmd,2):
			self.canvas.setActionRuler()

		# SET [x [y [z]]]: set x,y,z coordinates to current workspace
		elif cmd == "SET":
			try: x = float(line[1])
			except: x = None
			try: y = float(line[2])
			except: y = None
			try: z = float(line[3])
			except: z = None
			self._wcsSet(x,y,z)

		elif cmd == "SET0":
			self._wcsSet(0.,0.,0.)

		elif cmd == "SETX":
			try: x = float(line[1])
			except: x = ""
			self._wcsSet(x,None,None)

		elif cmd == "SETY":
			try: y = float(line[1])
			except: y = ""
			self._wcsSet(None,y,None)

		elif cmd == "SETZ":
			try: z = float(line[1])
			except: z = ""
			self._wcsSet(None,None,z)

		# STEP [s]: set motion step size to s
		elif cmd == "STEP":
			try:
				self.setStep(float(line[1]))
			except:
				pass

		# SPI*NDLE [ON|OFF|speed]: turn on/off spindle
		elif rexx.abbrev("SPINDLE",cmd,3):
			if len(line)>1:
				if line[1].upper()=="OFF":
					self.spindle.set(False)
				elif line[1].upper()=="ON":
					self.spindle.set(True)
				else:
					try:
						rpm = int(line[1])
						if rpm==0:
							self.spindleSpeed.set(0)
							self.spindle.set(False)
						else:
							self.spindleSpeed.set(rpm)
							self.spindle.set(True)
					except:
						pass
			else:
				# toggle spindle
				self.spindle.set(not self.spindle.get())
			self.spindleControl()

		# STOP: stop current run
		elif cmd == "STOP":
			self.stopRun()

		# TERM*INAL: switch to terminal tab
		elif rexx.abbrev("TERMINAL",cmd,4):
			self.ribbon.changePage("Terminal")

		# TOOL [diameter]: set diameter of cutting tool
		elif cmd in ("BIT","TOOL","MILL"):
			try:
				diam = float(line[1])
			except:
				tool = self.tools["EndMill"]
				diam = self.tools.fromMm(tool["diameter"])
			self.setStatus("EndMill: %s %g"%(tool["name"], diam))

		# TOOLS
		elif cmd=="TOOLS":
			self.ribbon.changePage("Tools")

		# UNL*OCK: unlock grbl
		elif rexx.abbrev("UNLOCK",cmd,3):
			self.unlock()

		# US*ER cmd: execute user command, cmd=number or name
		elif rexx.abbrev("USER",cmd,2):
			n = Utils.getInt("Buttons","n",6)
			try:
				idx = int(line[1])
			except:
				try:
					name = line[1].upper()
					for i in range(n):
						if name == Utils.getStr("Buttons","name.%d"%(i),"").upper():
							idx = i
							break
				except:
					return
			if idx<0 or idx>=n:
				self.setStatus("Invalid user command %s"%(line[1]))
				return
			cmd = Utils.getStr("Buttons","command.%d"%(idx),"")
			for line in cmd.splitlines():
				self.execute(line)

		# WCS [n]: switch to workspace index n
#		elif rexx.abbrev("WORKSPACE",cmd,4) or cmd=="WCS":
#			self.tabPage.changePage("WCS")
#			try:
#				self.wcsvar.set(WCS.index(line[1].upper()))
#			except:
#				pass

		# XY: switch to XY view
		# YX: switch to XY view
		elif cmd in ("XY","YX"):
			self.canvasFrame.viewXY()

		# XZ: switch to XZ view
		# ZX: switch to XZ view
		elif cmd in ("XZ","ZX"):
			self.canvasFrame.viewXZ()

		# YZ: switch to YZ view
		# ZY: switch to YZ view
		elif cmd in ("YZ","ZY"):
			self.canvasFrame.viewYZ()

		else:
			rc = self.executeCommand(oline)
			if rc:
				tkMessageBox.showerror(rc[0],rc[1], parent=self)
			return

	#-----------------------------------------------------------------------
	# Execute a command over the selected lines
	#-----------------------------------------------------------------------
	def executeOnSelection(self, cmd, blocksonly, *args):
		if blocksonly:
			items = self.editor.getSelectedBlocks()
		else:
			items = self.editor.getCleanSelection()
		if not items: return

		self.busy()
		sel = None
		if cmd == "CUT":
			sel = self.gcode.cut(items, *args)
		elif cmd == "DRILL":
			sel = self.gcode.drill(items, *args)
		elif cmd == "ORDER":
			self.gcode.orderLines(items, *args)
		elif cmd == "INKSCAPE":
			self.gcode.inkscapeLines()
		elif cmd == "MOVE":
			self.gcode.moveLines(items, *args)
		elif cmd == "OPTIMIZE":
			self.gcode.optimize(items)
		elif cmd == "REVERSE":
			self.gcode.reverse(items, *args)
		elif cmd == "ROUND":
			self.gcode.roundLines(items, *args)
		elif cmd == "ROTATE":
			self.gcode.rotateLines(items, *args)
		elif cmd == "MIRRORH":
			self.gcode.mirrorHLines(items)
		elif cmd == "MIRRORV":
			self.gcode.mirrorVLines(items)

		# Fill listbox and update selection
		self.editor.fill()
		if sel is not None:
			if isinstance(sel, str):
				tkMessageBox.showerror("Operation error", sel, parent=self)
			else:
				self.editor.select(sel,clear=True)
		self.drawAfter()
		self.notBusy()
		self.setStatus("%s %s"%(cmd," ".join([str(a) for a in args if a is not None])))

	#-----------------------------------------------------------------------
	def profile(self, direction=None, offset=0.0, cut=False, overcut=False, name=None):
		tool = self.tools["EndMill"]
		ofs  = self.tools.fromMm(tool["diameter"])/2.0
		sign = 1.0

		if direction is None:
			pass
		elif rexx.abbrev("INSIDE",direction.upper()):
			sign = -1.0
		elif rexx.abbrev("OUTSIDE",direction.upper()):
			sign = 1.0
		else:
			try:
				ofs = float(direction)/2.0
			except:
				pass

		# additional offset
		ofs += offset

		self.busy()
		blocks = self.editor.getSelectedBlocks()
		# on return we have the blocks with the new blocks to select
		msg = self.gcode.profile(blocks, ofs*sign, cut, overcut, name)
		if msg:
			tkMessageBox.showwarning("Open paths",
					"WARNING: %s"%(msg),
					parent=self)
		self.editor.fill()
		self.editor.selectBlocks(blocks)
		self.draw()
		self.notBusy()
		self.setStatus("Profile block distance=%g"%(ofs*sign))

	#-----------------------------------------------------------------------
	def edit(self, event=None):
		page = self.ribbon.getActivePage()
		if page.name == "Editor":
			self.editor.edit()
		elif page.name == "Tools":
			page.edit()

	#-----------------------------------------------------------------------
	def commandHistoryUp(self, event=None):
		if self._historyPos is None:
			if self.history:
				self._historyPos = len(self.history)-1
			else:
				return
		else:
			self._historyPos = max(0, self._historyPos-1)
		self.command.delete(0,END)
		self.command.insert(0,self.history[self._historyPos])

	#-----------------------------------------------------------------------
	def commandHistoryDown(self, event=None):
		if self._historyPos is None:
			return
		else:
			self._historyPos += 1
			if self._historyPos >= len(self.history):
				self._historyPos = None
		self.command.delete(0,END)
		if self._historyPos is not None:
			self.command.insert(0,self.history[self._historyPos])

	#-----------------------------------------------------------------------
	def select(self, items, double, clear, toggle=True):
		self.editor.select(items, double, clear, toggle)
		self.selectionChange()

	# ----------------------------------------------------------------------
	# Selection has changed highlight the canvas
	# ----------------------------------------------------------------------
	def selectionChange(self, event=None):
		items = self.editor.getSelection()
		self.canvas.clearSelection()
		if not items: return
		self.canvas.select(items)
		self.canvas.activeMarker(self.editor.getActive())

	#-----------------------------------------------------------------------
	def newFile(self, event=None):
		self.gcode.init()
		self.gcode.headerFooter()
		self.editor.fill()
		self.draw()
		self.title(Utils.__prg__)

	#-----------------------------------------------------------------------
	# load dialog
	#-----------------------------------------------------------------------
	def loadDialog(self, event=None):
		if self.running: return
		filename = bFileDialog.askopenfilename(master=self,
			title="Open file",
			initialfile=os.path.join(
					Utils.config.get("File", "dir"),
					Utils.config.get("File", "file")),
			filetypes=FILETYPES)
		if filename: self.load(filename)

	#-----------------------------------------------------------------------
	# save dialog
	#-----------------------------------------------------------------------
	def saveDialog(self, event=None):
		if self.running: return
		filename = bFileDialog.asksaveasfilename(master=self,
			title="Save file",
			initialfile=os.path.join(self.gcode.filename),
			filetypes=FILETYPES)
		if filename: self.save(filename)

	#-----------------------------------------------------------------------
	# Load a file into editor
	#-----------------------------------------------------------------------
	def load(self, filename):
		fn,ext = os.path.splitext(filename)
		if ext==".probe":
			pass
		elif self.gcode.isModified():
			ans = tkMessageBox.askquestion("File modified",
				"Gcode was modified do you want to save it first?",
				parent=self)
			if ans==tkMessageBox.YES or ans==True:
				self.save()

		Sender.load(self,filename)

		if ext==".probe":
			self.autolevel.setValues()
			self.event_generate("<<DrawProbe>>")
		else:
			self.editor.selectClear()
			self.editor.fill()
			self.draw()
			self.canvas.fit2Screen()

		self.setStatus("'%s' loaded"%(filename))
		self.title("%s: %s"%(Utils.__prg__,self.gcode.filename))

	#-----------------------------------------------------------------------
	def save(self, filename):
		Sender.save(self, filename)
		self.setStatus("'%s' saved"%(filename))
		self.title("%s: %s"%(Utils.__prg__,self.gcode.filename))

	#-----------------------------------------------------------------------
	def saveAll(self, event=None):
		if self.gcode.filename:
			Sender.saveAll(self)
		else:
			self.saveDialog()
		return "break"

	#-----------------------------------------------------------------------
	def reload(self, event=None):
		self.load(self.gcode.filename)

	#-----------------------------------------------------------------------
	def importFile(self, filename=None):
		if filename is None:
			filename = bFileDialog.askopenfilename(master=self,
				title="Import Gcode/DXF file",
				initialfile=os.path.join(
						Utils.config.get("File", "dir"),
						Utils.config.get("File", "file")),
				filetypes=[("G-Code",("*.ngc","*.nc", "*.gcode")),
					   ("DXF",    "*.dxf"),
					   ("All","*")])
		if filename:
			gcode = GCode()
			gcode.load(filename)
			sel = self.editor.getSelectedBlocks()
			if not sel:
				pos = None
			else:
				pos = sel[-1]
			self.gcode.addUndo(self.gcode.insBlocksUndo(pos, gcode.blocks))
			del gcode
			self.editor.fill()
			self.draw()
			self.canvas.fit2Screen()

	#-----------------------------------------------------------------------
	def focusIn(self, event):
		if self._inFocus: return
		# FocusIn is generated for all sub-windows, handle only the main window
		if self is not event.widget: return
		self._inFocus = True
		if self.gcode.checkFile():
			if self.gcode.isModified():
				ans = tkMessageBox.askquestion("Warning",
					"Gcode file %s was changed since editing started\n" \
					"Reload new version?"%(self.gcode.filename),
					parent=self)
				if ans==tkMessageBox.YES or ans==True:
					self.gcode.resetModified()
					self.load(self.gcode.filename)
			else:
				self.load(self.gcode.filename)
		self._inFocus = False

	#-----------------------------------------------------------------------
	def openClose(self, event=None):
		serialPage = Page.frames["Serial"]
		if self.serial is not None:
			self.close()
			serialPage.connectBtn.config(text="Open",
						background="LightGreen",
						activebackground="LightGreen")
		else:
			serialPage = Page.frames["Serial"]
			device   = _device or serialPage.portCombo.get()
			baudrate = _baud   or serialPage.baudCombo.get()
			if self.open(device, baudrate):
				serialPage.connectBtn.config(text="Close",
							background="Salmon",
							activebackground="Salmon")
				self.enable()

	#-----------------------------------------------------------------------
	def open(self, device, baudrate):
		try:
			return Sender.open(self, device, baudrate)
		except:
			self.serial = None
			self.thread = None
			tkMessageBox.showerror("Error opening serial",
					sys.exc_info()[1],
					parent=self)
		return False

	#-----------------------------------------------------------------------
	def close(self):
		if self.serial is None: return
		try:
			self.stopRun()
		except:
			pass
		self._runLines = 0
		self.thread = None
		time.sleep(1)
		self.serial.close()
		self.serial = None
		try:
			CNC.vars["state"] = NOT_CONNECTED
			CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
			self.dro.updateState()
		except TclError:
			pass

	#-----------------------------------------------------------------------
	def runEnded(self):
		Sender.runEnded(self)
		self.statusbar.clear()
		self.statusbar.config(background="LightGray")
		self.setStatus("Run ended")

	#-----------------------------------------------------------------------
	# Send enabled gcode file to the CNC machine
	#-----------------------------------------------------------------------
	def run(self, lines=None):
		if self.serial is None:
			tkMessageBox.showerror("Serial Error",
				"Serial is not connected",
				parent=self)
			return
		if self.running:
			if self._pause:
				self.resume()
				return
			tkMessageBox.showerror("Already running",
				"Please stop before",
				parent=self)
			return

		self.editor.selectClear()
		self.selectionChange()
		CNC.vars["errline"] = ""

		if lines is None:
			if not self.gcode.probe.isEmpty() and not self.gcode.probe.zeroed:
				tkMessageBox.showerror("Probe is not zeroed",
					"Please ZERO any location of the probe before starting a run",
					parent=self)
				return

			lines,paths = self.gcode.compile()
			if not lines:
				tkMessageBox.showerror("Empty gcode",
					"Not gcode file was loaded",
					parent=self)
				return

			# reset colors
			for ij in paths:
				if ij:
					self.canvas.itemconfig(
						self.gcode[ij[0]].path(ij[1]),
						width=1,
						fill=CNCCanvas.ENABLE_COLOR)
		else:
			lines = CNC.compile(lines)
			paths = None

		self.initRun()
		# the buffer of the machine should be empty?
		self.canvas.clearSelection()
		self._runLines = len(lines)
		self._gcount  = 0
		self._selectI = 0	# last selection pointer in items
		self._paths   = paths	# drawing paths for canvas

		self.statusbar.setLimits(0, self._runLines)
		self.statusbar.configText(fill="White")
		self.statusbar.config(background="DarkGray")

		for line in lines:
			if line is not None:
				if isinstance(line,str):
					self.queue.put(line+"\n")
				else:
					self.queue.put(line)

	#-----------------------------------------------------------------------
	# Start the web pendant
	#-----------------------------------------------------------------------
	def startPendant(self, showInfo=True):
		started=Pendant.start(self)
		if showInfo:
			hostName="http://%s:%d"%(socket.gethostname(),Pendant.port)
			if started:
				tkMessageBox.showinfo("Pendant",
					"Pendant started:\n"+hostName,
					parent=self)
			else:
				dr=tkMessageBox.askquestion("Pendant",
					"Pendant already started:\n"+hostName+"\nWould you like open it locally?",
					parent=self)
				if dr=="yes":
					webbrowser.open(hostName,new=2)

	#-----------------------------------------------------------------------
	# Stop the web pendant
	#-----------------------------------------------------------------------
	def stopPendant(self):
		if Pendant.stop():
			tkMessageBox.showinfo("Pendant","Pendant stopped", parent=self)

	#-----------------------------------------------------------------------
	# Inner loop to catch any generic exception
	#-----------------------------------------------------------------------
	def _monitorSerial(self):
		inserted = False

		# Check serial output
		t = time.time()
		while self.log.qsize()>0 and time.time()-t<0.1:
			try:
				io, line = self.log.get_nowait()
				if not inserted:
					self.terminal["state"] = NORMAL
					inserted = True
				if io:
					self.terminal.insert(END, line, "SEND")
				else:
					self.terminal.insert(END, line)
			except Empty:
				break

		# Check pendant
		try:
			cmd = self.pendant.get_nowait()
			self.execute(cmd)
		except Empty:
			pass

		# Load file from pendant
		if self._pendantFileUploaded!=None:
			self.load(self._pendantFileUploaded)
			self._pendantFileUploaded=None

		# Update position if needed
		if self._posUpdate:
			state = CNC.vars["state"]
			#print state
			#print Sender.ERROR_CODES[state]
			try:
				CNC.vars["color"] = STATECOLOR[state]
			except KeyError:
				if self._alarm:
					CNC.vars["color"] = STATECOLOR["Alarm"]
				else:
					CNC.vars["color"] = STATECOLORDEF
			self._pause = (state=="Hold")
			self.dro.updateState()
			self.dro.updateCoords()
			self.canvas.gantry(CNC.vars["wx"],
					   CNC.vars["wy"],
					   CNC.vars["wz"],
					   CNC.vars["mx"],
					   CNC.vars["my"],
					   CNC.vars["mz"])
			self._posUpdate = False

		# Update status string
		if self._gUpdate:
			self.gstate.updateG()
			self._gUpdate = False

		# Update probe and draw point
		if self._probeUpdate:
			try:
				probe = CNC.vars.get("PRB")
				self._probeX["text"] = probe[0]
				self._probeY["text"] = probe[1]
				self._probeZ["text"] = probe[2]
			except:
				pass
			self.canvas.drawProbe()
			self._probeUpdate = False

		# Update any possible variable?
		if self._update:
			if self._update == "toolheight":
				Page.frames["Probe:Tool"].updateTool()
			self._update = None

		if inserted:
			self.terminal.see(END)
			self.terminal["state"] = DISABLED

		if self.running:
			self.statusbar.setProgress(self._runLines-self.queue.qsize(),
						self._gcount)

			if self._selectI>=0 and self._paths:
				while self._selectI < self._gcount and self._selectI<len(self._paths):
					if self._paths[self._selectI]:
						i,j = self._paths[self._selectI]
						path = self.gcode[i].path(j)
						self.canvas.itemconfig(path, width=2, fill=CNCCanvas.PROCESS_COLOR)
					self._selectI += 1

			if self._gcount >= self._runLines:
				self.runEnded()

	#-----------------------------------------------------------------------
	# "thread" timed function looking for messages in the serial thread
	# and reporting back in the terminal
	#-----------------------------------------------------------------------
	def monitorSerial(self):
		try:
			self._monitorSerial()
		except:
			typ, val, tb = sys.exc_info()
			traceback.print_exception(typ, val, tb)
		self.after(MONITOR_AFTER, self.monitorSerial)

	#-----------------------------------------------------------------------
	def get(self, section, item):
		return Utils.config.get(section, item)

	#-----------------------------------------------------------------------
	def set(self, section, item, value):
		return Utils.config.set(section, item, value)

#------------------------------------------------------------------------------
def usage(rc):
	sys.stdout.write("%s V%s [%s]\n"%(Utils.__prg__, __version__, __date__))
	sys.stdout.write("%s <%s>\n\n"%(__author__, __email__))
	sys.stdout.write("Usage: [options] [filename...]\n\n")
	sys.stdout.write("Options:\n")
	sys.stdout.write("\t-b # | --baud #\t\tSet the baud rate\n")
	sys.stdout.write("\t-d\t\t\tEnable developer features\n")
	sys.stdout.write("\t-D\t\t\tDisable developer features\n")
	sys.stdout.write("\t-g #\t\tSet the default geometry\n")
	sys.stdout.write("\t-h | -? | --help\tThis help page\n")
	sys.stdout.write("\t-i # | --ini #\t\tAlternative ini file for testing\n")
	sys.stdout.write("\t-l | --list\t\tList all recently files\n")
	sys.stdout.write("\t-p # | --pendant #\tOpen pendant to specified port\n")
	sys.stdout.write("\t-P\t\t\tDo not start pendant\n")
	sys.stdout.write("\t-r | --recent\t\tLoad the most recent file opened\n")
	sys.stdout.write("\t-R #\t\t\tLoad the recent file matching the argument\n")
	sys.stdout.write("\t-s # | --serial #\tOpen serial port specified\n")
	sys.stdout.write("\t-S\t\t\tDo not open serial port\n")
	sys.stdout.write("\n")
	sys.exit(rc)

#------------------------------------------------------------------------------
if __name__ == "__main__":
	tk = Tk()
	tk.withdraw()
	try:
		Tkinter.CallWrapper = Utils.CallWrapper
	except:
		tkinter.CallWrapper = Utils.CallWrapper

	tkExtra.bindClasses(tk)
	Utils.loadConfiguration()

	# Parse arguments
	try:
		optlist, args = getopt.getopt(sys.argv[1:],
			'?b:dDhi:g:rlpPSs:',
			['help', 'ini=', 'recent', 'list','pendant=','serial=','baud='])
	except getopt.GetoptError:
		usage(1)

	recent   = None
	for opt, val in optlist:
		if opt in ("-h", "-?", "--help"):
			usage(0)
		elif opt in ("-i", "--ini"):
			Utils.iniUser = val
		elif opt == "-d":
			Utils.developer = True
		elif opt == "-D":
			Utils.developer = False
		elif opt == "-g":
			geometry = val
		elif opt in ("-r", "-R", "--recent", "-l", "--list"):
			if opt in ("-r","--recent"):
				r = 0
			elif opt in ("--list","-l"):
				r = -1
			else:
				try:
					r = int(val)-1
				except:
					# Scan in names
					for r in range(Utils._maxRecent):
						filename = Utils.getRecent(r)
						if filename is None: break
						fn, ext = os.path.splitext(os.path.basename(filename))
						if fn == val:
							break
					else:
						r = 0
			if r<0:
				# display list of recent files
				sys.stdout.write("Recent files:\n")
				for i in range(Utils._maxRecent):
					filename = Utils.getRecent(i)
					if filename is None: break
					d  = os.path.dirname(filename)
					fn = os.path.basename(filename)
					sys.stdout.write("  %2d: %-10s\t%s\n"%(i+1,fn,d))

				try:
					sys.stdout.write("Select one: ")
					r = int(sys.stdin.readline())-1
				except:
					pass
			try: recent = Utils.getRecent(r)
			except: pass

		elif opt == "-S":
			_openserial = False

		elif opt in ("-s", "--serial"):
			_openserial = True
			_device = val

		elif opt in ("-b", "--baud"):
			_baud = val

		elif opt == "-p":
			pass #startPendant()

		elif opt == "-P":
			pass #stopPendant()

		elif opt == "--pendant":
			pass #startPendant on port

	# Start application
	application = Application(tk)

	# Parse remaining arguments except files
	if recent: args.append(recent)
	for fn in args:
		application.load(fn)

	try:
		tk.mainloop()
	except KeyboardInterrupt:
		application.quit()

	application.close()
	Utils.saveConfiguration()
 #vim:ts=8:sw=8:sts=8:noet

