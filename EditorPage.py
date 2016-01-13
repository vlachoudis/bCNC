# -*- coding: ascii -*-
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
# Clipboard Group
#===============================================================================
class ClipboardGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Clipboard"), app)
		self.grid2rows()

		# ---
		b = Ribbon.LabelButton(self.frame, self, "<<Paste>>",
				image=Utils.icons["paste32"],
				text=_("Paste"),
				compound=TOP,
				takefocus=FALSE,
				background=Ribbon._BACKGROUND)
		b.grid(row=0, column=0, rowspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Paste [Ctrl-V]"))
		self.addWidget(b)

		# ---
		b = Ribbon.LabelButton(self.frame, self, "<<Cut>>",
				image=Utils.icons["cut"],
				text=_("Cut"),
				compound=LEFT,
				anchor=W,
				takefocus=FALSE,
				background=Ribbon._BACKGROUND)
		tkExtra.Balloon.set(b, _("Cut [Ctrl-X]"))
		b.grid(row=0, column=1, padx=0, pady=1, sticky=NSEW)
		self.addWidget(b)

		# ---
		b = Ribbon.LabelButton(self.frame, self, "<<Copy>>",
				image=Utils.icons["copy"],
				text=_("Copy"),
				compound=LEFT,
				anchor=W,
				takefocus=FALSE,
				background=Ribbon._BACKGROUND)
		tkExtra.Balloon.set(b, _("Copy [Ctrl-C]"))
		b.grid(row=1, column=1, padx=0, pady=1, sticky=NSEW)
		self.addWidget(b)

#===============================================================================
# Select Group
#===============================================================================
class SelectGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Select"), app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, app, "<<SelectAll>>",
				image=Utils.icons["select_all"],
				text=_("All"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Select all blocks [Ctrl-A]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<SelectNone>>",
				image=Utils.icons["select_none"],
				text=_("None"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Unselect all blocks [Ctrl-Shift-A]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<SelectInvert>>",
				image=Utils.icons["select_invert"],
				text=_("Invert"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Invert selection [Ctrl-I]"))
		self.addWidget(b)

#===============================================================================
# Edit Group
#===============================================================================
class EditGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("Edit"), app,
			[(_("Import"),    "load",     lambda a=app:a.insertCommand("IMPORT",True)),
			 (_("Inkscape"),  "inkscape", lambda a=app:a.insertCommand("INKSCAPE all",True)),
			 (_("Round"),     "digits",   lambda s=app:s.insertCommand("ROUND", True)),
			 (_("Statistics"),"stats",    app.showStats)
			])
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, app, "<<Add>>",
				image=Utils.icons["add"],
				text=_("Add"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Insert a new block or line of code [Ins or Ctrl-Enter]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<Clone>>",
				image=Utils.icons["clone"],
				text=_("Clone"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Clone selected lines or blocks [Ctrl-D]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, app, "<<Delete>>",
				image=Utils.icons["x"],
				text=_("Delete"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Delete selected lines or blocks [Del]"))
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame, self.app, "<<EnableToggle>>",
				image=Utils.icons["toggle"],
				#text=_("Toggle"),
				#compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Toggle enable/disable block of g-code [Ctrl-L]"))
		self.addWidget(b)

		menulist = [	(_("Enable"),   "enable",
				lambda a=self.app : a.event_generate("<<Enable>>")),
				(_("Disable"),  "disable",
				lambda a=self.app : a.event_generate("<<Disable>>"))]
		b = Ribbon.MenuButton(self.frame, menulist,
				text=_("Active"),
				image=Utils.icons["triangle_down"],
				compound=RIGHT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col+1, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Enable or disable blocks of gcode"))


		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self.app, "<<Expand>>",
				image=Utils.icons["expand"],
				text=_("Expand"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Toggle expand/collapse blocks of gcode [Ctrl-E]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["comment"],
				text=_("Comment"),
				compound=LEFT,
				anchor=W,
				state=DISABLED,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("(Un)Comment selected lines"))
		self.addWidget(b)

#===============================================================================
# Move Group
#===============================================================================
class MoveGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Move"), app)
		self.grid3rows()

		# ===
		col,row = 0,0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["move32"],
				text=_("Move"),
				compound=TOP,
				anchor=W,
				variable=app.canvas.actionVar,
				value=ACTION_MOVE,
				command=app.canvas.setActionMove,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move objects [M]"))
		self.addWidget(b)

		# ===
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TL"],
				text=_("T-L"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TL",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Top-Left corner"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["LC"],
				text=_("L"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE LC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Left side"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BL"],
				text=_("B-L"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BL",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Bottom-Left corner"))
		self.addWidget(b)

		# ====
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TC"],
				text=_("Top"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Top side"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["center"],
				text=_("Center"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE CENTER",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to center"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BC"],
				text=_("Bottom"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Bottom side"))
		self.addWidget(b)

		# ===
		col += 1
		row = 0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["TR"],
				text=_("T-R"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE TR",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Top-Right corner"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["RC"],
				text=_("R"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE RC",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Right side"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["BR"],
				text=_("B-R"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MOVE BR",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move origin of g-code to Bottom-Right corner"))
		self.addWidget(b)

		# ---
		col += 1
		row = 0
		b = Ribbon.LabelRadiobutton(self.frame,
				image=Utils.icons["origin"],
				text=_("Origin"),
				compound=LEFT,
				anchor=W,
				variable=app.canvas.actionVar,
				value=ACTION_ORIGIN,
				command=app.canvas.setActionOrigin,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Place origin with the mouse on canvas [O]"))
		self.addWidget(b)


#===============================================================================
# Order Group
#===============================================================================
class OrderGroup(CNCRibbon.ButtonMenuGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("Order"), app,
			[(_("Optimize"),  "optimize", lambda a=app:a.insertCommand("OPTIMIZE",True)),
			])
		self.grid2rows()

		# ===
		col,row=0,0
		b = Ribbon.LabelButton(self.frame, self, "<Control-Key-Prior>",
				image=Utils.icons["up"],
				text=_("Up"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move selected g-code up [Ctrl-Up, Ctrl-PgUp]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<Control-Key-Next>",
				image=Utils.icons["down"],
				text=_("Down"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Move selected g-code down [Ctrl-Down, Ctrl-PgDn]"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame, self, "<<Invert>>",
				image=Utils.icons["swap"],
				text=_("Invert"),
				compound=LEFT,
				anchor=W,
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Invert cutting order of selected blocks"))
		self.addWidget(b)

#===============================================================================
# Transform Group
#===============================================================================
class TransformGroup(CNCRibbon.ButtonGroup):
	def __init__(self, master, app):
		CNCRibbon.ButtonGroup.__init__(self, master, N_("Transform"), app)
		self.grid3rows()

		# ---
		col,row=0,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate90"],
				text=_("CW"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE CW",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Rotate selected gcode clock-wise (-90deg)"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate180"],
				text=_("Flip"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE FLIP",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Rotate selected gcode by 180deg"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["rotate270"],
				text=_("CCW"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("ROTATE CCW",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Rotate selected gcode counter-clock-wise (90deg)"))
		self.addWidget(b)

		# ---
		col,row=1,0
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["flip-horizontal"],
				text=_("Horizontal"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MIRROR horizontal",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Mirror horizontally X=-X selected gcode"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["flip-vertical"],
				text=_("Vertical"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("MIRROR vertical",True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Mirror vertically Y=-Y selected gcode"))
		self.addWidget(b)

		# ---
		row += 1
		b = Ribbon.LabelButton(self.frame,
				image=Utils.icons["reverse"],
				text=_("Reverse"),
				compound=LEFT,
				anchor=W,
				command=lambda s=app:s.insertCommand("REVERSE", True),
				background=Ribbon._BACKGROUND)
		b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
		tkExtra.Balloon.set(b, _("Reverse direction of selected gcode blocks"))
		self.addWidget(b)

#		submenu.add_command(label=_("Rotate command"), underline=0,
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

		sb = Scrollbar(self, orient=VERTICAL, command=self.editor.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.editor.config(yscrollcommand=sb.set)

#===============================================================================
# Editor Page
#===============================================================================
class EditorPage(CNCRibbon.Page):
	__doc__ = _("GCode editor")
	_name_  = N_("Editor")
	_icon_  = "edit"

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def register(self):
		self._register((ClipboardGroup, SelectGroup, EditGroup, MoveGroup, OrderGroup, TransformGroup),
			(EditorFrame,))
