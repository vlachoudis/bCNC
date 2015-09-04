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

import tkExtra

import Utils
import Ribbon
import CNCList
import CNCRibbon

from CNCCanvas import ACTION_MOVE, ACTION_ORIGIN

#===============================================================================
# Edit Group
#===============================================================================
class EditGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, "Edit", app,
			[("Import",    "load",     lambda a=app:a.insertCommand("IMPORT",True)),
			 ("Inkscape",  "inkscape", lambda a=app:a.insertCommand("INKSCAPE all",True)),
			 ("Statistics","stats",    app.showStats)
			])
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, app, "<<Add>>",
				image=Utils.icons["add"],
				text="Add",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Insert a new block or line of code [Ins or Ctrl-Enter]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<Clone>>",
				image=Utils.icons["clone"],
				text="Clone",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Clone selected lines or blocks [Ctrl-D]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<Delete>>",
				image=Utils.icons["x"],
				text="Delete",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Delete selected lines or blocks [Del]")
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame, self.app, "<<Enable>>",
				image=Utils.icons["toggle"],
				text="Toggle",
				compound=LEFT,
				anchor=W,
#				command=app.editor.toggleEnable,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Toggle enable/disable block of g-code [Ctrl-L]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["digits"],
				text="Round",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("REVERSE", True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Round precision of numbers for selected lines")
		self.addWidget(b)

		# ---
		col,row=2,0
		b = Ribbon.LabelButton(self.frame, self.app, "<<Expand>>",
				image=Utils.icons["expand"],
				text="Expand",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Toggle expand/collapse blocks of gcode [Ctrl-E]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["comment"],
				text="Comment",
				compound=LEFT,
				anchor=W,
				state=DISABLED,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "(Un)Comment selected lines")
		self.addWidget(b)

#===============================================================================
# Move Group
#===============================================================================
class MoveGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Move", app)
		self.grid3rows()

		# ===
		col,row = 0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["pan"],
				text="Move",
				compound=LEFT,
				anchor=W,
				variable=app.canvas.actionVar,
				value=ACTION_MOVE,
				command=app.canvas.setActionMove,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move objects [M]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["origin"],
				text="Origin",
				compound=LEFT,
				anchor=W,
				variable=app.canvas.actionVar,
				value=ACTION_ORIGIN,
				command=app.canvas.setActionOrigin,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Place origin with the mouse on canvas [O]")
		self.addWidget(b)

		# ===
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TL"],
				text="T-L",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TL",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Top-Left corner")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["LC"],
				text="L",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE LC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Left side")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BL"],
				text="B-L",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BL",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Bottom-Left corner")
		self.addWidget(b)

		# ====
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TC"],
				text="Top",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Top side")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["center"],
				text="Center",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE CENTER",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to center")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BC"],
				text="Bottom",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Bottom side")
		self.addWidget(b)

		# ===
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TR"],
				text="T-R",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TR",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Top-Right corner")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["RC"],
				text="R",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE RC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Right side")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BR"],
				text="B-R",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BR",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move origin of g-code to Bottom-Right corner")
		self.addWidget(b)

#===============================================================================
# Order Group
#===============================================================================
class OrderGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Order", app)
		self.grid2rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<Control-Key-Prior>",
				image=Utils.icons["up"],
				text="Up",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move selected g-code up [Ctrl-Up, Ctrl-PgUp]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<Control-Key-Next>",
				image=Utils.icons["down"],
				text="Down",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Move selected g-code down [Ctrl-Down, Ctrl-PgDn]")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<Invert>>",
				image=Utils.icons["swap"],
				text="Invert",
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Invert cutting order of selected blocks")
		self.addWidget(b)

#===============================================================================
# Transform Group
#===============================================================================
class TransformGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, "Transform", app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate90"],
				text="CW",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE CW",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Rotate selected gcode clock-wise (-90deg)")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate180"],
				text="Flip",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE FLIP",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Rotate selected gcode by 180deg")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate270"],
				text="CCW",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE CCW",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Rotate selected gcode counter-clock-wise (90deg)")
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["flip-horizontal"],
				text="Horizontal",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MIRROR horizontal",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Mirror horizontally X=-X selected gcode")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["flip-vertical"],
				text="Vertical",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MIRROR vertical",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Mirror vertically Y=-Y selected gcode")
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["reverse"],
				text="Reverse",
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("REVERSE", True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, "Reverse direction of selected gcode blocks")
		self.addWidget(b)

#		submenu.add_command(label="Rotate command", underline=0,
#					command=lambda s=self:s.insertCommand("ROTATE ang x0 y0", False))

#===============================================================================
class EditorFrame(CNCRibbon.PageFrame):
	def __init__(self, master, app):
		CNCRibbon.PageFrame.__init__(self, master, "Editor", app)
		self.editor = CNCList.CNCListbox(self, app,
						selectmode=EXTENDED,
						exportselection=0,
						background="White")
		self.editor.pack(side=LEFT,expand=TRUE, fill=BOTH)
		self.addWidget(self.editor)

		# FIXME XXX MOVE TO app
		self.editor.bind("<<ListboxSelect>>",	app.selectionChange)
		self.editor.bind("<<Modified>>",	app.drawAfter)

		sb = Scrollbar(self, orient=VERTICAL, command=self.editor.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.editor.config(yscrollcommand=sb.set)

#===============================================================================
# Editor Page
#===============================================================================
class EditorPage(CNCRibbon.Page):
	"""GCode editor"""

	_name_ = "Editor"
	_icon_ = "edit"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((EditGroup, MoveGroup, OrderGroup, TransformGroup),
			(EditorFrame,))
