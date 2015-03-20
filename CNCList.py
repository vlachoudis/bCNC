# -*- coding: latin1 -*-
# $Id: CNCEditor.py,v 1.9 2014/10/15 15:04:38 bnv Exp $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

try:
	from Tkinter import *
	import tkFont
except ImportError:
	from tkinter import *
	import tkinter.font as tkFont

import CNC
import tkExtra
#import tkDialogs

BLOCK_COLOR = "LightYellow"

#==============================================================================
# CNC Listbox
#==============================================================================
class CNCListbox(Listbox):
	def __init__(self, master, app, *kw, **kwargs):
		Listbox.__init__(self, master, *kw, **kwargs)
		self.bind("<Button-1>",		self.button1)
		self.bind("<ButtonRelease-1>",	self.release1)
		self.bind("<Double-1>",		self.double)
		self.bind("<Return>",		self.edit)
		self.bind("<KP_Enter>",		self.edit)
		self.bind("<Insert>",		self.insertItem)
		self.bind("<Control-Key-Return>",self.insertItem)
		self.bind("<Control-Key-space>",self.commandFocus)
		self.bind("<Delete>",		self.deleteLine)
		self.bind("<BackSpace>",	self.deleteLine)
		try:
			self.bind("<KP_Delete>",self.deleteLine)
		except:
			pass

		self.bind("<Control-Key-b>",	self.insertBlock)
		self.bind("<Control-Key-r>",	self.fill)

		self._blockPos = []
		self._items    = []
		self.app       = app
		self.gcode     = app.gcode
		self.font      = tkFont.nametofont(self.cget("font"))
		self._ystart   = 0
		self._double   = False	# double clicked handled
		self._hadfocus = False

	# ----------------------------------------------------------------------
	def commandFocus(self, event=None):
		self.app.commandFocus(event)
		return "break"

	# ----------------------------------------------------------------------
	# Change the value of a list item
	# and return the value of the old one
	# ----------------------------------------------------------------------
	def set(self, index, value):
		"""Set/Change the value of a list item"""
		try:
			sel = self.selection_includes(index)
			act = self.index(ACTIVE)
			self.delete(index)
		except TclError:
			return
		self.insert(index, value)
		if sel: self.selection_set(index)
		self.activate(act)

	# ----------------------------------------------------------------------
	# Fill listbox with visible items
	# ----------------------------------------------------------------------
	def fill(self, event=None):
		act = self.index(ACTIVE)
		sel = self.curselection()

		self.delete(0,END)

		del self._blockPos[:]
		del self._items[:]
		y = 0
		for bi,block in enumerate(self.gcode.blocks):
			self._blockPos.append(y)
			self.insert(END, block.header())
			y += 1
			self._items.append((bi,None))
			self.itemconfig(END, background=BLOCK_COLOR)
			if not block.expand: continue

			for lj,line in enumerate(block):
				self.insert(END, line)
				y += 1
				if line and line[0] in ("(","%"):
					self.itemconfig(END, foreground="Blue")
				self._items.append((bi, lj))

		for i in sel: self.selection_set(i)
		self.activate(act)

	# ----------------------------------------------------------------------
	# Edit active item
	# ----------------------------------------------------------------------
	def edit(self, event=None):
		active = self.index(ACTIVE)
		txt = self.get(active)
		if event:
			x = event.x
		else:
			x = 0

		ypos = self.yview()[0]
		bid, lid = self._items[active]
		if lid is None:
			txt0 = txt
			txt = self.gcode.blocks[bid].name()
			self.set(active, txt)
			edit = tkExtra.InPlaceEdit(self, select=False, bg=self.cget("bg"))
		else:
			edit = tkExtra.InPlaceEdit(self,x=x, select=False, bg=self.cget("bg"))

		if edit.value is None or edit.value==txt:
			if lid is None:
				self.set(active,txt0)
				self.itemconfig(active, background=BLOCK_COLOR)
			return

		if lid is None:
			self.gcode.addUndo(self.gcode.setBlockNameUndo(bid, edit.value))
		else:
			self.gcode.addUndo(self.gcode.setLineUndo(bid, lid, edit.value))

		if lid is None:
			self.set(active, self.gcode.blocks[bid].header())
			self.itemconfig(active, background=BLOCK_COLOR)
		else:
			self.set(active, edit.value)

		if edit.value and edit.value[0] in ("(","%"):
			self.itemconfig(active, foreground="Blue")

		self.yview_moveto(ypos)
		self.event_generate("<<Modified>>")

	# ----------------------------------------------------------------------
	# return active block id
	# ----------------------------------------------------------------------
	def activeBlock(self):
		active = self.index(ACTIVE)
		if self._items:
			bid, lid = self._items[active]
		else:
			bid = 0
		return bid

	# ----------------------------------------------------------------------
	# Insert a line or a block
	# ----------------------------------------------------------------------
	def insertItem(self, event=None):
		active = self.index(ACTIVE)
		if active is None: return
		if self._items[active][1] is None:
			self.insertBlock()
		else:
			self.insertLine()

	# ----------------------------------------------------------------------
	# Insert New Block
	# ----------------------------------------------------------------------
	def insertBlock(self, event=None):
		active = self.index(ACTIVE)
		if self._items:
			bid, lid = self._items[active]
			bid += 1
		else:
			bid = 0

		block = CNC.Block()
		block.expand = True
		block.append("G0 X0 Y0")
		block.append("G0 Z0")
		block.append("G0 Z%g"%(self.gcode.cnc.safeZ))
		self.gcode.addUndo(self.gcode.addBlockUndo(bid,block))
		self.selection_clear(0,END)
		self.fill()
		# find location of new block
		while active < self.size():
			if self._items[active][0] == bid:
				break
			active += 1
		self.selection_set(active)
		self.see(active)
		self.activate(active)
		self.edit()
		self.event_generate("<<Modified>>")

	# ----------------------------------------------------------------------
	# Insert a new line below cursor
	# ----------------------------------------------------------------------
	def insertLine(self, event=None):
		active = self.index(ACTIVE)
		if active is None: return
		bid, lid = self._items[active]
		active += 1
		self.insert(active,"")
		self.selection_clear(0,END)
		self.activate(active)
		self.selection_set(active)
		self.see(active)

		edit = tkExtra.InPlaceEdit(self, bg=self.cget("bg"))
		ypos = self.yview()[0]
		self.delete(active)

		if edit.value is None:
			# Cancel and leave
			active -= 1
			self.activate(active)
			self.selection_set(active)
			self.see(active)
			return

		self.insert(active, edit.value)
		self.selection_set(active)
		self.activate(active)
		if edit.value and edit.value[0] in ("(","%"):
			self.itemconfig(active, foreground="Blue")
		self.yview_moveto(ypos)

		# Correct pointers
		self._items.insert(active, (bid, lid+1))
		for i in range(bid+1, len(self._blockPos)):
			self._blockPos[i] += 1	# shift all blocks below by one

		self.gcode.addUndo(self.gcode.insLineUndo(bid, lid+1, edit.value))
		self.event_generate("<<Modified>>")

	# ----------------------------------------------------------------------
	# Delete selected lines
	# ----------------------------------------------------------------------
	def deleteLine(self, event=None):
		sel = list(map(int,self.curselection()))
		if not sel: return

		ypos = self.yview()[0]
		undoinfo = []
		for i in reversed(sel):
			bid, lid = self._items[i]
			if lid is None:
				undoinfo.append(self.gcode.delBlockLinesUndo(bid))
			else:
				undoinfo.append(self.gcode.delLineUndo(bid, lid))
		self.gcode.addUndo(undoinfo)

		self.selection_clear(0,END)
		self.fill()
		self.yview_moveto(ypos)
		self.selection_set(ACTIVE)
		self.see(ACTIVE)
		self.event_generate("<<Modified>>")

	# ----------------------------------------------------------------------
	# Button1 clicked
	# ----------------------------------------------------------------------
	def button1(self, event):
		if self._double: return

		# Remember if we had the focus before clicking
		# to be used later in editing
		self._hadfocus = self.focus_get() == self

		# from a single click
		self._ystart = self.nearest(event.y)
		selected = self.selection_includes(self._ystart)
		loc = self._headerLocation(event)
		if loc is None:
			pass
		elif self._headerLocation(event)<2 and selected:
			return "break"	# do not alter selection!

	# ----------------------------------------------------------------------
	# Release button-1. Warning on separation of double or single click or
	# click and drag
	# ----------------------------------------------------------------------
	def release1(self, event):
		if not self._items: return
		if self._double:
			self._double = False
			return

		self._double = False

		# from a single click
		y = self.nearest(event.y)
		if y != self._ystart: return

		loc = self._headerLocation(event)
		if loc is None:
			# Normal line
			if self.index(ACTIVE)==y:
				self.activate(y)
				# In place edit if we had already the focus
				if self._hadfocus:
					self.edit(event)
		elif loc == 0:
			self.toggleExpand()
		elif loc == 1:
			self.toggleVisibility()

	# ----------------------------------------------------------------------
	def double(self, event):
		if self._headerLocation(event) == 2:
			self.edit()
			self._double = True
		else:
			self._double = False

	# ----------------------------------------------------------------------
	# Return location where we clicked on header
	#  0 = expand arrow
	#  1 = visible ballot box
	#  2 = name
	# ----------------------------------------------------------------------
	def _headerLocation(self, event):
		if not self._items: return None
		# from a single click
		y = self.nearest(event.y)

		block,line = self._items[y]
		if line is not None: return None

		txt = self.get(y)
		if event.x <= self.font.measure(txt[:2]):
			return 0
		elif event.x <= self.font.measure(txt[:5]):
			return 1
		else:
			return 2

	# ----------------------------------------------------------------------
	# Toggle expand selection
	# ----------------------------------------------------------------------
	def toggleExpand(self, event=None):
		items   = list(map(int,self.curselection()))
		changed = False
		expand  = None
		for i in reversed(items):
			block,line = self._items[i]
			if line is not None: continue
			if expand is None: expand = not self.gcode[block].expand
			self.gcode[block].expand = expand
			changed = True

		if changed:
			active = self.index(ACTIVE)
			self.fill()
			self.activate(active)
			self.see(active)

	# ----------------------------------------------------------------------
	# toggle visibility
	# ----------------------------------------------------------------------
	def toggleVisibility(self, event=None):
		items   = list(map(int,self.curselection()))
		active  = self.index(ACTIVE)
		changed = False
		visible = None
		ypos = self.yview()[0]
		for i in items:
			block,line = self._items[i]
			if line is not None: continue
			if visible is None: visible = not self.gcode[block].visible
			self.gcode[block].visible = visible

			sel = self.selection_includes(i)
			self.delete(i)
			self.insert(i, self.gcode[block].header())
			self.itemconfig(i, background=BLOCK_COLOR)
			if sel: self.selection_set(i)
			changed = True

		if changed:
			self.activate(active)
			self.yview_moveto(ypos)
			self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	# Select lines in the form of (block, item)
	# ----------------------------------------------------------------------
	def select(self, lines, double=False, clear=False):
		if clear: self.selection_clear(0,END)
		first = True
		for b,i in lines:
			block = self.gcode[b]
			if double:
				# select whole block
				y = self._blockPos[b]

			elif i is not None and block.expand:
				# find line of block
				y = self._blockPos[b]+i+1

			else:
				# select whole block
				y = self._blockPos[b]

			self.selection_set(y)
			if first:
				self.activate(y)
				self.see(y)
				first = False

	# ----------------------------------------------------------------------
	# Return list of [(blocks,lines),...] currently being selected
	# ----------------------------------------------------------------------
	def getSelection(self):
		return [self._items[int(i)] for i in self.curselection()]

	# ----------------------------------------------------------------------
	def getActive(self):
		active = self.index(ACTIVE)
		if active is None: return None
		if not self.selection_includes(active):
			active = self.curselection()[0]
		return self._items[int(active)]

	# ----------------------------------------------------------------------
	def selectAll(self):
		self.selection_set(0,END)

	# ----------------------------------------------------------------------
	def selectClear(self):
		self.selection_clear(0,END)
