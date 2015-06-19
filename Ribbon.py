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
except ImportError:
	from tkinter import *

import time
import Utils
import tkExtra
import Unicode

_FONT       = ("Sans","-11")

#_BACKGROUND_DISABLE = "#D6D2D0"
#_BACKGROUND         = "White"
#_BACKGROUND_GROUP   = "LightGray"
#_BACKGROUND_GROUP2  = "#D0E0E0"
#_FOREGROUND_GROUP   = "Black"

_BACKGROUND_DISABLE = "#A6A2A0"
_BACKGROUND         = "#E6E2E0"
_BACKGROUND_GROUP   = "#B6B2B0"

_BACKGROUND_GROUP2  = "#B0C0C0"
_BACKGROUND_GROUP3  = "#A0C0A0"
_BACKGROUND_GROUP4  = "#B0C0A0"

_FOREGROUND_GROUP   = "White"
_ACTIVE_COLOR       = "LightYellow"
_LABEL_SELECT_COLOR = "#C0FFC0"

#===============================================================================
# Frame Group with a button at bottom
#===============================================================================
class LabelGroup(Frame):
	def __init__(self, master, name, command=None, **kw):
		Frame.__init__(self, master, **kw)
		self.config(	#bg="Green",
				background=_BACKGROUND,
				borderwidth=0,
				highlightthickness=0,
				pady=0)

		# right frame as a separator
		f = Frame(self, borderwidth=2, relief=GROOVE, background=_BACKGROUND_DISABLE)
		f.pack(side=RIGHT, fill=Y, padx=0, pady=0)

		# frame to insert the buttons
		self.frame = Frame(self,
				#bg="Orange",
				background=_BACKGROUND,
				padx=0,
				pady=0)
		self.frame.pack(side=TOP, expand=TRUE, fill=BOTH, padx=0, pady=0)

		if command:
			self.name = LabelButton(self, self, "<<%s>>"%(name), text=name)
			self.name.config(command=command,
				image=Utils.icons["triangle_down"],
				foreground=_FOREGROUND_GROUP,
				background=_BACKGROUND_GROUP,
				highlightthickness=0,
				borderwidth=0,
				pady=0,
				compound=RIGHT)
		else:
			self.name = Label(self, text=name,
					font       = _FONT,
					foreground = _FOREGROUND_GROUP,
					background = _BACKGROUND_GROUP,
					padx=2,
					pady=0)	# Button takes 1px for border width
		self.name.pack(side=BOTTOM, fill=X, pady=0)

#===============================================================================
class _KeyboardFocus:
	#----------------------------------------------------------------------
	def _bind(self):
		self.bind("<Return>",		self._invoke)
		self.bind("<FocusIn>",		self._focusIn)
		self.bind("<FocusOut>",		self._focusOut)

	#----------------------------------------------------------------------
	def _focusIn(self, event):
		self.__backgroundColor = self.cget("background")
		self.config(background = _ACTIVE_COLOR)

	#----------------------------------------------------------------------
	def _focusOut(self, event):
		self.config(background = self.__backgroundColor)

	#----------------------------------------------------------------------
	def _invoke(self, event):
		self.invoke()

#===============================================================================
# Button with Label that generates a Virtual Event or calls a command
#===============================================================================
class LabelButton(Button, _KeyboardFocus):
	def __init__(self, master, recipient=None, event=None, **kw):
		Button.__init__(self, master, **kw)
		self.config(	relief           = FLAT,
				activebackground = _ACTIVE_COLOR,
				font             = _FONT,
				borderwidth      = 1,
				highlightthickness = 0,
				padx             = 2,
				pady             = 0)
		_KeyboardFocus._bind(self)
		if recipient is not None:
			self.config(command = self.sendEvent)
			self._recipient = recipient
			self._event     = event
		else:
			self._recipient = None
			self._event     = None

	#----------------------------------------------------------------------
	def sendEvent(self):
		self._recipient.event_generate(self._event)

#===============================================================================
class LabelCheckbutton(Checkbutton, _KeyboardFocus):
	def __init__(self, master, **kw):
		Checkbutton.__init__(self, master, **kw)
		self.config(	selectcolor        = _LABEL_SELECT_COLOR,
				activebackground   = _ACTIVE_COLOR,
				background         = _BACKGROUND,
				indicatoron        = FALSE,
				relief             = FLAT,
				borderwidth        = 0,
				highlightthickness = 0,
				padx               = 0,
				pady               = 0,
				font               = _FONT
			)
		_KeyboardFocus._bind(self)

#===============================================================================
class LabelRadiobutton(Radiobutton, _KeyboardFocus):
	def __init__(self, master, **kw):
		Radiobutton.__init__(self, master, **kw)
		self.config(
			selectcolor        = _LABEL_SELECT_COLOR,
			activebackground   = _ACTIVE_COLOR,
			background         = _BACKGROUND,
			indicatoron        = FALSE,
			borderwidth        = 0,
			highlightthickness = 0,
			pady               = 0,
			font               = _FONT
		)
		_KeyboardFocus._bind(self)

#===============================================================================
class LabelCombobox(tkExtra.Combobox, _KeyboardFocus):
	def __init__(self, master, **kw):
		tkExtra.Combobox.__init__(self, master, **kw)
		self.config(background=_BACKGROUND, font=_FONT)
		Frame.config(self, background=_BACKGROUND, padx=0, pady=0)
		_KeyboardFocus._bind(self)

	#----------------------------------------------------------------------
	def _focusOut(self, event):
		self.config(background = _BACKGROUND) #self.__backgroundColor)
		Frame.config(self, background= _BACKGROUND) #self.__backgroundColor)

#===============================================================================
# Button with Label that popup a menu
#===============================================================================
class MenuButton(Button, _KeyboardFocus):
	def __init__(self, master, menulist, **kw):
		Button.__init__(self, master, **kw)
		self.config(	relief           = FLAT,
				activebackground = _ACTIVE_COLOR,
				font             = _FONT,
				borderwidth      = 0,
				highlightthickness= 0,
				padx             = 2,
				pady             = 0,
				command          = self.showMenu)

		_KeyboardFocus._bind(self)
		self.bind("<Return>", self.showMenu)
		if menulist is not None:
			self._menu = self.createMenuFromList(menulist)
		else:
			self._menu = None

	#----------------------------------------------------------------------
	def showMenu(self, event=None):
		if self._menu is not None:
			self._showMenu(self._menu)
		else:
			self._showMenu(self.createMenu())

	#----------------------------------------------------------------------
	def _showMenu(self, menu):
		if menu is not None:
			menu.tk_popup(
				self.winfo_rootx(),
				self.winfo_rooty() + self.winfo_height())

	#----------------------------------------------------------------------
	def createMenu(self):
		return None

	#----------------------------------------------------------------------
	def createMenuFromList(self, menulist):
		menu = Menu(self, tearoff=0, activebackground=_ACTIVE_COLOR)
		for item in menulist:
			if item is None:
				menu.add_separator()
			else:
				name, icon, cmd = item
				if icon is None: icon = "empty"
				menu.add_command(label=name,
						image=Utils.icons[icon],
						compound=LEFT,
						command=cmd)
		return menu

#===============================================================================
# A label group with a drop down menu
#===============================================================================
class MenuGroup(LabelGroup):
	def __init__(self, master, name, **kw):
		LabelGroup.__init__(self, master, name, command=self._showMenu, **kw)

	#----------------------------------------------------------------------
	def createMenu(self):
		return None

	#----------------------------------------------------------------------
	def _showMenu(self):
		menu = self.createMenu()
		if menu is not None:
			menu.tk_popup(
				self.winfo_rootx(),
				self.winfo_rooty() + self.winfo_height())

#===============================================================================
# Page Tab buttons
#===============================================================================
class TabButton(Radiobutton):
	def __init__(self, master, **kw):
		Radiobutton.__init__(self, master, **kw)
		self.config(	selectcolor        = _BACKGROUND,
				activebackground   = _ACTIVE_COLOR,
				indicatoron        = FALSE,
				relief             = FLAT,
				borderwidth        = 0,
				highlightthickness = 0,
				padx               = 5,
				pady               = 0,
				background         = _BACKGROUND_DISABLE
			)
		self.bind("<FocusIn>",		self._focusIn)
		self.bind("<FocusOut>",		self._focusOut)

	#----------------------------------------------------------------------
	# Bind events on TabFrame
	#----------------------------------------------------------------------
	def bindClicks(self, tabframe):
		self.bind("<Double-1>",         tabframe.double)
		self.bind("<Button-1>",         tabframe.dragStart)
		self.bind("<B1-Motion>",        tabframe.drag)
		self.bind("<ButtonRelease-1>",  tabframe.dragStop)
		self.bind("<Control-ButtonRelease-1>", tabframe.pinActive)

		self.bind("<Left>",		tabframe._tabLeft)
		self.bind("<Right>",		tabframe._tabRight)
		self.bind("<Down>",		tabframe._tabDown)

	#----------------------------------------------------------------------
	def _focusIn(self, evenl=None):
		self.config(selectcolor = _ACTIVE_COLOR)

	#----------------------------------------------------------------------
	def _focusOut(self, evenl=None):
		self.config(selectcolor = _BACKGROUND)

#===============================================================================
# Page
#===============================================================================
class Page:		# <--- should be possible to be a toplevel as well
	_motionClasses = (LabelButton, LabelRadiobutton, LabelCheckbutton, LabelCombobox, MenuButton)
	_name_ = None
	_icon_ = None
	_doc_  = "Tooltip"

	def __init__(self, master, **kw):
		self.master    = master
		self.name      = self._name_
		self._icon     = Utils.icons[self._icon_]
		self._tab      = None	# Tab button
		self.ribbon    = None	# Ribbon frame
		self.page      = None	# Page frame
		self.init()
		self.create()

	#----------------------------------------------------------------------
	# Override initialization
	#----------------------------------------------------------------------
	def init(self):
		pass

	#----------------------------------------------------------------------
	# The tab page can change master if undocked
	#----------------------------------------------------------------------
	def create(self):
		self.createPage()
		self.createRibbon()
#		self.createStatus()
#		self.createContextGroups()
#		self.ribbonBindMotion()
		self.refresh()

	#----------------------------------------------------------------------
	def createPage(self):
		self.page = Frame(self.master._pageFrame)
		return self.page

	#----------------------------------------------------------------------
	def createRibbon(self):
		self.ribbon = Frame(self.master, pady=0, background=_BACKGROUND)
		return self.ribbon

	#----------------------------------------------------------------------
	# Called when a page is activated
	#----------------------------------------------------------------------
	def activate(self):
		pass

	#----------------------------------------------------------------------
	def refresh(self):
		pass

	# ----------------------------------------------------------------------
	def canUndo(self):	return True
	def canRedo(self):	return True
	def resetUndo(self):	pass
	def undo(self, event=None): pass
	def redo(self, event=None): pass

	# ----------------------------------------------------------------------
	def refreshUndoButton(self):
		# Check if frame provides undo/redo
		if self.master is None: return
		if self.page is None: return

		if self.canUndo():
			state = NORMAL
		else:
			state = DISABLED
		self.master.tool["undo"].config(state=state)
		self.master.tool["undolist"].config(state=state)

		if self.canRedo():
			state = NORMAL
		else:
			state = DISABLED
		self.master.tool["redo"].config(state=state)

	#----------------------------------------------------------------------
	def keyboardFocus(self):
		self._tab.focus_set()

	#----------------------------------------------------------------------
	# Return the closest widget along a direction
	#----------------------------------------------------------------------
	@staticmethod
	def __compareDown(x,y,xw,yw):	return yw>y+1
	@staticmethod
	def __compareUp(x,y,xw,yw):	return yw<y-1
	@staticmethod
	def __compareRight(x,y,xw,yw):	return xw>x+1
	@staticmethod
	def __compareLeft(x,y,xw,yw):	return xw<x-1

	#----------------------------------------------------------------------
	@staticmethod
	def __closest(widget, compare, x, y):
		closest = None
		dc2 = 10000000
		if widget is None: return closest, dc2
		for child in widget.winfo_children():
			for class_ in Page._motionClasses:
				if isinstance(child, class_):
					if child["state"] == DISABLED: continue
					xw = child.winfo_rootx()
					yw = child.winfo_rooty()
					if compare(x,y,xw,yw):
						d2 = (xw-x)**2 + (yw-y)**2
						if d2 < dc2:
							closest = child
							dc2 = d2
					break
			else:
				c,d2 = Page.__closest(child, compare, x, y)
				if d2 < dc2:
					closest = c
					dc2 = d2
		return closest, dc2

	#----------------------------------------------------------------------
	# Select/Focus the closest element
	#----------------------------------------------------------------------
	def _ribbonUp(self, event=None):
		x = event.widget.winfo_rootx()
		y = event.widget.winfo_rooty()
		closest,d2 = Page.__closest(self.ribbon, Page.__compareUp, x, y)
		if closest is not None:
			closest.focus_set()

	#----------------------------------------------------------------------
	def _ribbonDown(self, event=None):
		x = event.widget.winfo_rootx()
		y = event.widget.winfo_rooty()
		closest,d2 = Page.__closest(self.ribbon, Page.__compareDown, x, y)
		if closest is not None:
			closest.focus_set()

	#----------------------------------------------------------------------
	def _ribbonLeft(self, event=None):
		x = event.widget.winfo_rootx()
		y = event.widget.winfo_rooty()
		closest,d2 = Page.__closest(self.ribbon, Page.__compareLeft, x, y)
		if closest is not None:
			closest.focus_set()

	#----------------------------------------------------------------------
	def _ribbonRight(self, event=None):
		x = event.widget.winfo_rootx()
		y = event.widget.winfo_rooty()
		closest,d2 = Page.__closest(self.ribbon, Page.__compareRight, x, y)
		if closest is not None:
			closest.focus_set()

#===============================================================================
# TabRibbonFrame
#===============================================================================
class TabRibbonFrame(Frame):
	def __init__(self, master, **kw):
		Frame.__init__(self, master, kw)
		self.config(background=_BACKGROUND_DISABLE)

		self.oldActive  = None
		self.activePage = StringVar(self)
		self.tool       = {}
		self.pages      = {}

		# === Top frame with buttons ===
		frame = Frame(self, background=_BACKGROUND_DISABLE)
		frame.pack(side=TOP, fill=X)

		# --- Basic buttons ---
		b = LabelButton(frame, self, "<<Save>>",
				image=Utils.icons["save"],
				background=_BACKGROUND_DISABLE)
		tkExtra.Balloon.set(b, "Save project [Ctrl-S]")
		b.pack(side=LEFT)

		b = LabelButton(frame, self, "<<Undo>>",
				image=Utils.icons["undo"],
				background=_BACKGROUND_DISABLE)
		tkExtra.Balloon.set(b, "Undo [Ctrl-Z]")
		b.pack(side=LEFT)
		self.tool["undo"] = b

		b = LabelButton(frame, image=Utils.icons["triangle_down"],
				command=self.undolist,
				background=_BACKGROUND_DISABLE)
		b.pack(side=LEFT)
		self.tool["undolist"] = b

		b = LabelButton(frame, self, "<<Redo>>",
				image=Utils.icons["redo"],
				background=_BACKGROUND_DISABLE)
		tkExtra.Balloon.set(b, "Redo [Ctrl-Y]")
		b.pack(side=LEFT)
		self.tool["redo"] = b

		Label(frame, image=Utils.icons["sep"],
				background=_BACKGROUND_DISABLE).pack(side=LEFT, padx=3)

		# --- Help ---
		b = LabelButton(frame, self, "<<Help>>",
				image=Utils.icons["info"],
				background=_BACKGROUND_DISABLE)
		tkExtra.Balloon.set(b, "Help [F1]")
		b.pack(side=RIGHT, padx=2)

		Label(frame, image=Utils.icons["sep"],
				background=_BACKGROUND_DISABLE).pack(side=RIGHT, padx=3)

		# --- TabBar ---
		self._tabFrame = Frame(frame, background=_BACKGROUND_DISABLE)
		self._tabFrame.pack(side=LEFT, fill=BOTH, expand=YES)

		# === Ribbon Frame with permanent and dynamic ribbons ===
		self._allRibbons = Frame(self, background=_BACKGROUND, pady=0)
		self._allRibbons.pack(side=TOP, fill=BOTH, pady=0)

		# --- Permanent Groups ---
		self.createClipboardGroup(self._allRibbons)

		# ==== Ribbon Frame ====
		self._ribbonFrame = Frame(self._allRibbons,
						#bg="Yellow",
						background=_BACKGROUND,
						relief=RAISED)
		self._ribbonFrame.pack(side=LEFT, fill=BOTH, padx=0, pady=0)

		# ==== RibbonRight Frame ====
		self._ribbonRight = Frame(self._allRibbons, background=_BACKGROUND, pady=0)
		self._ribbonRight.pack(side=RIGHT, fill=BOTH, pady=0)

		self.setPageFrame(None)

	#----------------------------------------------------------------------
	def createClipboardGroup(self, frame):
		group = LabelGroup(frame, "Clipboard")
		group.pack(side=LEFT, fill=BOTH, padx=0, pady=0)

		group.frame.grid_rowconfigure(0, weight=1)
		group.frame.grid_rowconfigure(1, weight=1)

		# ---
		b = LabelButton(group.frame, self, "<<Paste>>",
				image=Utils.icons["paste32"],
				text="Paste",
				compound=TOP,
				takefocus=FALSE,
				background=_BACKGROUND)
		b.grid(row=0, column=0, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Paste [Ctrl-V]")
		#self.tool["paste"] = b

		# ---
		b = LabelButton(group.frame, self, "<<Cut>>",
				image=Utils.icons["cut"],
				text="Cut",
				compound=LEFT,
				anchor=W,
				takefocus=FALSE,
				background=_BACKGROUND)
		tkExtra.Balloon.set(b, "Cut [Ctrl-X]")
		b.grid(row=0, column=1, padx=0, pady=1, sticky=NSEW)

		# ---
		b = LabelButton(group.frame, self, "<<Copy>>",
				image=Utils.icons["copy"],
				text="Copy",
				compound=LEFT,
				anchor=W,
				takefocus=FALSE,
				background=_BACKGROUND)
		tkExtra.Balloon.set(b, "Copy [Ctrl-C]")
		b.grid(row=1, column=1, padx=0, pady=1, sticky=NSEW)

	#----------------------------------------------------------------------
	def setPageFrame(self, frame):
		self._pageFrame = frame

	#----------------------------------------------------------------------
	def undolist(self, event=None): self.event_generate("<<UndoList>>")

	#----------------------------------------------------------------------
	def getActivePage(self):
		return self.pages[self.activePage.get()]

	#----------------------------------------------------------------------
	# Add page to the tabs
	#----------------------------------------------------------------------
	def addPage(self, page):
		self.pages[page.name] = page
		page._tab = TabButton(self._tabFrame,
				image    = page._icon,
				text     = page.name,
				compound = LEFT,
				value    = page.name,
				variable = self.activePage,
				command  = self.changePage)
		tkExtra.Balloon.set(page._tab, page.__doc__)

		page._tab.pack(side=LEFT, fill=Y, padx=5)

	# ----------------------------------------------------------------------
	# Change ribbon and page
	# ----------------------------------------------------------------------
	def changePage(self, page=None):
		#import traceback
		#traceback.print_stack()

		if page:
			if isinstance(page, str):
				try:
					page = self.pages[page]
				except KeyError:
					return
			self.activePage.set(page.name)
		else:
			try:
				page = self.pages[self.activePage.get()]
			except KeyError:
				return

		if page is self.oldActive: return

		if self.oldActive:
			self.oldActive.ribbon.pack_forget()
			if self.oldActive.page: self.oldActive.page.pack_forget()

		page.ribbon.pack(in_=self._ribbonFrame, fill=BOTH, expand=YES)
		if page.page:
			page.page.pack(fill=BOTH, expand=YES)
		self.oldActive = page
		page.activate()
		self.event_generate("<<ChangePage>>") #, data=pageName)

#	#----------------------------------------------------------------------
#	# Mouse is clicked => hide ribbon if temporary is active
#	#----------------------------------------------------------------------
##	def release(self, event):
##		if self._ribbonFrameStatus == RIBBON_HIDDEN:
##			if not isinstance(event.widget, TabButton): return
##			if time.time() - self.hideTime > 1.0:
##				self._ribbonFrameStatus = RIBBON_TEMP
##				self._allRibbons.pack(side=TOP, fill=BOTH)
##				self.hideTime = time.time()
##
##		elif self._ribbonFrameStatus == RIBBON_TEMP and \
##		     self._allRibbons.winfo_ismapped():
##			if isinstance(event.widget, TabButton): return
##			self._ribbonFrameStatus = RIBBON_HIDDEN
##			self._allRibbons.pack_forget()
#
#	#----------------------------------------------------------------------
#	# Give focus to the tab on the left
#	#----------------------------------------------------------------------
#	def _tabLeft(self, event=None):
#		slaves = self._tabFrame.pack_slaves()
#		try:
#			pos = slaves.index(event.widget)-1
#		except ValueError:
#			if event.widget is self.dynamic:
#				pos = len(slaves)-1
#			else:
#				return
#		if pos < 0: return	# Do not replace First tab
#		slaves[pos].select()
#		#self.changePage()
#		slaves[pos].focus_set()
#
#	#----------------------------------------------------------------------
#	# Give focus to the tab on the right
#	#----------------------------------------------------------------------
#	def _tabRight(self, event=None):
#		slaves = self._tabFrame.pack_slaves()
#		try:
#			pos = slaves.index(event.widget)+1
#		except ValueError:
#			return
#		if pos < len(slaves):
#			slaves[pos].select()
#			#self.changePage()
#			slaves[pos].focus_set()
#		else:
#			# Open dynamic menu
#			self.dynamic.select()
#			self.dynamic.focus_set()
#			self.dynamicMenu()
#
