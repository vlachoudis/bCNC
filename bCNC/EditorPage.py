# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

from tkinter import (
    FALSE,
    TRUE,
    W,
    NSEW,
    Y,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    VERTICAL,
    EXTENDED,
    Menu,
    Scrollbar,
)

import CNCList
import CNCRibbon
import Ribbon
import tkExtra
import Utils
from CNCCanvas import ACTION_MOVE, ACTION_ORIGIN

from Helpers import N_

__author__ = "Vasilis Vlachoudis"
__email__ = "vvlachoudis@gmail.com"


# =============================================================================
# Clipboard Group
# =============================================================================
class ClipboardGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Clipboard"), app)
        self.grid2rows()

        # ---
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Paste>>",
            image=Utils.icons["paste32"],
            text=_("Paste"),
            compound=TOP,
            takefocus=FALSE,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=0, column=0, rowspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Paste [Ctrl-V]"))
        self.addWidget(b)

        # ---
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Cut>>",
            image=Utils.icons["cut"],
            text=_("Cut"),
            compound=LEFT,
            anchor=W,
            takefocus=FALSE,
            background=Ribbon._BACKGROUND,
        )
        tkExtra.Balloon.set(b, _("Cut [Ctrl-X]"))
        b.grid(row=0, column=1, padx=0, pady=1, sticky=NSEW)
        self.addWidget(b)

        # ---
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Copy>>",
            image=Utils.icons["copy"],
            text=_("Copy"),
            compound=LEFT,
            anchor=W,
            takefocus=FALSE,
            background=Ribbon._BACKGROUND,
        )
        tkExtra.Balloon.set(b, _("Copy [Ctrl-C]"))
        b.grid(row=1, column=1, padx=0, pady=1, sticky=NSEW)
        self.addWidget(b)


# =============================================================================
# Select Group
# =============================================================================
class SelectGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Select"), app)
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<SelectAll>>",
            image=Utils.icons["select_all"],
            text=_("All"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Select all blocks [Ctrl-A]"))
        self.addWidget(b)

        # ---
        col += 1
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<SelectNone>>",
            image=Utils.icons["select_none"],
            text=_("None"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Unselect all blocks [Ctrl-Shift-A]"))
        self.addWidget(b)

        # ---
        col, row = 0, 1
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<SelectInvert>>",
            image=Utils.icons["select_invert"],
            text=_("Invert"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Invert selection [Ctrl-I]"))
        self.addWidget(b)

        # ---
        col += 1
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<SelectLayer>>",
            image=Utils.icons["select_layer"],
            text=_("Layer"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Select all blocks from current layer"))
        self.addWidget(b)

        # ---
        col, row = 0, 2
        self.filterString = tkExtra.LabelEntry(
            self.frame,
            _("Filter"),
            "DarkGray",
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=16,
        )
        self.filterString.grid(
            row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW
        )
        tkExtra.Balloon.set(self.filterString, _("Filter blocks"))
        self.addWidget(self.filterString)
        self.filterString.bind("<Return>", self.filter)
        self.filterString.bind("<KP_Enter>", self.filter)

    # -----------------------------------------------------------------------
    def filter(self, event=None):
        txt = self.filterString.get()
        self.app.insertCommand(f"FILTER {txt}", True)


# =============================================================================
# Edit Group
# =============================================================================
class EditGroup(CNCRibbon.ButtonMenuGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonMenuGroup.__init__(
            self,
            master,
            N_("Edit"),
            app,
            [
                (
                    _("Autolevel"),
                    "level",
                    lambda a=app: a.insertCommand("AUTOLEVEL", True),
                ),
                (
                    _("Color"),
                    "color",
                    lambda a=app: a.event_generate("<<ChangeColor>>"),
                ),
                (_("Import"), "load", lambda a=app: a.insertCommand("IMPORT", True)),
                (
                    _("Postprocess Inkscape g-code"),
                    "inkscape",
                    lambda a=app: a.insertCommand("INKSCAPE all", True),
                ),
                (_("Round"), "digits", lambda s=app: s.insertCommand("ROUND", True)),
            ],
        )
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<Add>>",
            image=Utils.icons["add"],
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Insert a new block or line of code [Ins or Ctrl-Enter]")
        )
        self.addWidget(b)

        menulist = [
            (
                _("Line"),
                "add",
                lambda a=self.app: a.event_generate("<<AddLine>>")
            ),
            (
                _("Block"),
                "add",
                lambda a=self.app: a.event_generate("<<AddBlock>>")
            ),
        ]
        b = Ribbon.MenuButton(
            self.frame,
            menulist,
            text=_("Add"),
            image=Utils.icons["triangle_down"],
            compound=RIGHT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col + 1, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Insert a new block or line of code [Ins or Ctrl-Enter]")
        )

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<Clone>>",
            image=Utils.icons["clone"],
            text=_("Clone"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Clone selected lines or blocks [Ctrl-D]"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            app,
            "<<Delete>>",
            image=Utils.icons["x"],
            text=_("Delete"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Delete selected lines or blocks [Del]"))
        self.addWidget(b)

        # ---
        col, row = 2, 0
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<EnableToggle>>",
            image=Utils.icons["toggle"],
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _("Toggle enable/disable block of g-code [Ctrl-L]")
        )
        self.addWidget(b)

        menulist = [
            (
                _("Enable"),
                "enable",
                lambda a=self.app: a.event_generate("<<Enable>>")
            ),
            (
                _("Disable"),
                "disable",
                lambda a=self.app: a.event_generate("<<Disable>>"),
            ),
        ]
        b = Ribbon.MenuButton(
            self.frame,
            menulist,
            text=_("Active"),
            image=Utils.icons["triangle_down"],
            compound=RIGHT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col + 1, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Enable or disable blocks of gcode"))

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<Expand>>",
            image=Utils.icons["expand"],
            text=_("Expand"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _("Toggle expand/collapse blocks of gcode [Ctrl-E]")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<Comment>>",
            image=Utils.icons["comment"],
            text=_("Comment"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("(Un)Comment selected lines"))
        self.addWidget(b)
        # ---
        col += 2
        row = 0
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<Join>>",
            image=Utils.icons["union"],
            text=_("Join"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Join selected blocks"))
        self.addWidget(b)
        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self.app,
            "<<Split>>",
            image=Utils.icons["cut"],
            text=_("Split"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, columnspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Split selected blocks"))
        self.addWidget(b)


# =============================================================================
# Move Group
# =============================================================================
class MoveGroup(CNCRibbon.ButtonMenuGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonMenuGroup.__init__(self, master, N_("Move"), app)
        self.grid3rows()

        # ===
        col, row = 0, 0
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["move32"],
            text=_("Move"),
            compound=TOP,
            anchor=W,
            variable=app.canvas.actionVar,
            value=ACTION_MOVE,
            command=app.canvas.setActionMove,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Move objects [M]"))
        self.addWidget(b)

        # ---
        col += 1
        b = Ribbon.LabelRadiobutton(
            self.frame,
            image=Utils.icons["origin32"],
            text=_("Origin"),
            compound=TOP,
            anchor=W,
            variable=app.canvas.actionVar,
            value=ACTION_ORIGIN,
            command=app.canvas.setActionOrigin,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Move all gcode such as origin is on mouse location [O]")
        )
        self.addWidget(b)

    # ----------------------------------------------------------------------
    def createMenu(self):
        menu = Menu(self, tearoff=0)
        for i, n, c in (
            ("tl", _("Top-Left"), "MOVE TL"),
            ("lc", _("Left"), "MOVE LC"),
            ("bl", _("Bottom-Left"), "MOVE BL"),
            ("tc", _("Top"), "MOVE TC"),
            ("center", _("Center"), "MOVE CENTER"),
            ("bc", _("Bottom"), "MOVE BC"),
            ("tr", _("Top-Right"), "MOVE TR"),
            ("rc", _("Right"), "MOVE RC"),
            ("br", _("Bottom-Right"), "MOVE BR"),
        ):
            menu.add_command(
                label=n,
                image=Utils.icons[i],
                compound=LEFT,
                command=lambda a=self.app, c=c: a.insertCommand(c, True),
            )
        return menu


# =============================================================================
# Order Group
# =============================================================================
class OrderGroup(CNCRibbon.ButtonMenuGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonMenuGroup.__init__(
            self,
            master,
            N_("Order"),
            app,
            [
                (
                    _("Optimize"),
                    "optimize",
                    lambda a=app: a.insertCommand("OPTIMIZE", True),
                ),
            ],
        )
        self.grid2rows()

        # ===
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<Control-Key-Prior>",
            image=Utils.icons["up"],
            text=_("Up"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _("Move selected g-code up [Ctrl-Up, Ctrl-PgUp]")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<Control-Key-Next>",
            image=Utils.icons["down"],
            text=_("Down"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _("Move selected g-code down [Ctrl-Down, Ctrl-PgDn]")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Invert>>",
            image=Utils.icons["swap"],
            text=_("Invert"),
            compound=LEFT,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Invert cutting order of selected blocks"))
        self.addWidget(b)


# =============================================================================
# Transform Group
# =============================================================================
class TransformGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Transform"), app)
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["rotate_90"],
            text=_("CW"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("ROTATE CW", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Rotate selected gcode clock-wise (-90deg)"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["rotate_180"],
            text=_("Flip"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("ROTATE FLIP", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Rotate selected gcode by 180deg"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["rotate_270"],
            text=_("CCW"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("ROTATE CCW", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Rotate selected gcode counter-clock-wise (90deg)"))
        self.addWidget(b)

        # ---
        col, row = 1, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["flip_horizontal"],
            text=_("Horizontal"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("MIRROR horizontal", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Mirror horizontally X=-X selected gcode"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["flip_vertical"],
            text=_("Vertical"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("MIRROR vertical", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Mirror vertically Y=-Y selected gcode"))
        self.addWidget(b)


# =============================================================================
# Route Group
# =============================================================================
class RouteGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Route"), app)
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["conventional"],
            text=_("Conventional"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand(
                "DIRECTION CONVENTIONAL", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b,
            _("Change cut direction to conventional for selected gcode blocks")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["climb"],
            text=_("Climb"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("DIRECTION CLIMB", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Change cut direction to climb for selected gcode blocks")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["reverse"],
            text=_("Reverse"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("REVERSE", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Reverse cut direction for selected gcode blocks"))
        self.addWidget(b)

        # ---
        col, row = 1, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["rotate_90"],
            text=_("Cut CW"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("DIRECTION CW", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Change cut direction to CW for selected gcode blocks")
        )
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["rotate_270"],
            text=_("Cut CCW"),
            compound=LEFT,
            anchor=W,
            command=lambda s=app: s.insertCommand("DIRECTION CCW", True),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Change cut direction to CCW for selected gcode blocks")
        )
        self.addWidget(b)


# =============================================================================
# Info Group
# =============================================================================
class InfoGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Info"), app)
        self.grid2rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["stats"],
            text=_("Statistics"),
            compound=LEFT,
            anchor=W,
            command=app.showStats,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Show statistics for enabled gcode"))
        self.addWidget(b)

        # ---
        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["info"],
            text=_("Info"),
            compound=LEFT,
            anchor=W,
            command=app.showInfo,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(
            b, _("Show cutting information on selected blocks [Ctrl-n]")
        )
        self.addWidget(b)


# =============================================================================
# Main Frame of Editor
# =============================================================================
class EditorFrame(CNCRibbon.PageFrame):
    def __init__(self, master, app):
        CNCRibbon.PageFrame.__init__(self, master, "Editor", app)
        self.editor = CNCList.CNCListbox(
            self,
            app,
            selectmode=EXTENDED,
            exportselection=0,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        self.editor.pack(side=LEFT, expand=TRUE, fill=BOTH)
        self.addWidget(self.editor)

        sb = Scrollbar(self, orient=VERTICAL, command=self.editor.yview)
        sb.pack(side=RIGHT, fill=Y)
        self.editor.config(yscrollcommand=sb.set)


# =============================================================================
# Editor Page
# =============================================================================
class EditorPage(CNCRibbon.Page):
    __doc__ = _("GCode editor")
    _name_ = N_("Editor")
    _icon_ = "edit"

    # ----------------------------------------------------------------------
    # Add a widget in the widgets list to enable disable during the run
    # ----------------------------------------------------------------------
    def register(self):
        self._register(
            (
                ClipboardGroup,
                SelectGroup,
                EditGroup,
                MoveGroup,
                OrderGroup,
                TransformGroup,
                RouteGroup,
                InfoGroup,
            ),
            (EditorFrame,),
        )
