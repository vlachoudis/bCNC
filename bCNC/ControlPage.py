# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

import math
from tkinter import (
    TclError,
    FALSE,
    YES,
    N,
    S,
    W,
    E,
    EW,
    NSEW,
    CENTER,
    X,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BOTTOM,
    FLAT,
    HORIZONTAL,
    END,
    NORMAL,
    DISABLED,
    #  UNITS,
    IntVar,
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    Menu,
    Radiobutton,
    Scale,
    messagebox,
)

from CNC import CNC
import CNCRibbon
import Ribbon
import Sender
import tkExtra
import Unicode
import Utils
from CNC import DISTANCE_MODE, FEED_MODE, PLANE, WCS
from _GenericGRBL import ERROR_CODES

from Helpers import N_

__author__ = "Vasilis Vlachoudis"
__email__ = "vvlachoudis@gmail.com"


_LOWSTEP = 0.0001
_HIGHSTEP = 1000.0
_HIGHZSTEP = 10.0
_NOZSTEP = "XY"
_HIGHASTEP = 90.0
_NOASTEP = "BC"

OVERRIDES = ["Feed", "Rapid", "Spindle"]

# override for init
UNITS = {"G20": "inch", "G21": "mm"}

# =============================================================================
# Connection Group
# =============================================================================


class ConnectionGroup(CNCRibbon.ButtonMenuGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonMenuGroup.__init__(
            self,
            master,
            N_("Connection"),
            app,
            [(_("Hard Reset"), "reset", app.hardReset)],
        )
        self.grid2rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["home32"],
            text=_("Home"),
            compound=TOP,
            anchor=W,
            command=app.home,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Perform a homing cycle [$H] now"))
        self.addWidget(b)

        # ---
        col, row = 1, 0
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["unlock"],
            text=_("Unlock"),
            compound=LEFT,
            anchor=W,
            command=app.unlock,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Unlock controller [$X]"))
        self.addWidget(b)

        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["serial"],
            text=_("Connection"),
            compound=LEFT,
            anchor=W,
            command=lambda s=self: s.event_generate("<<Connect>>"),
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Open/Close connection"))
        self.addWidget(b)

        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            image=Utils.icons["reset"],
            text=_("Reset"),
            compound=LEFT,
            anchor=W,
            command=app.softReset,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Software reset of controller [ctrl-x]"))
        self.addWidget(b)


# =============================================================================
# User Group
# =============================================================================
class UserGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, "User", app)
        self.grid3rows()

        n = Utils.getInt("Buttons", "n", 6)
        for i in range(1, n):
            b = Utils.UserButton(
                self.frame, self.app, i, anchor=W,
                background=Ribbon._BACKGROUND
            )
            col, row = divmod(i - 1, 3)
            b.grid(row=row, column=col, sticky=NSEW)
            self.addWidget(b)


# =============================================================================
# Run Group
# =============================================================================
class RunGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, "Run", app)

        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Run>>",
            image=Utils.icons["start32"],
            text=_("Start"),
            compound=TOP,
            background=Ribbon._BACKGROUND,
        )
        b.pack(side=LEFT, fill=BOTH)
        tkExtra.Balloon.set(
            b, _("Run g-code commands from editor to controller"))
        self.addWidget(b)

        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Pause>>",
            image=Utils.icons["pause32"],
            text=_("Pause"),
            compound=TOP,
            background=Ribbon._BACKGROUND,
        )
        b.pack(side=LEFT, fill=BOTH)
        tkExtra.Balloon.set(
            b,
            _("Pause running program. Sends either FEED_HOLD ! "
              + "or CYCLE_START ~")
        )

        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Stop>>",
            image=Utils.icons["stop32"],
            text=_("Stop"),
            compound=TOP,
            background=Ribbon._BACKGROUND,
        )
        b.pack(side=LEFT, fill=BOTH)
        tkExtra.Balloon.set(
            b, _("Pause running program and soft reset controller to "
                 + "empty the buffer.")
        )


# =============================================================================
# DRO Frame
# =============================================================================
class DROFrame(CNCRibbon.PageFrame):
    dro_status = ("Helvetica", 12, "bold")
    dro_wpos = ("Helvetica", 12, "bold")
    dro_mpos = ("Helvetica", 12)

    def __init__(self, master, app):
        CNCRibbon.PageFrame.__init__(self, master, "DRO", app)

        DROFrame.dro_status = Utils.getFont("dro.status", DROFrame.dro_status)
        DROFrame.dro_wpos = Utils.getFont("dro.wpos", DROFrame.dro_wpos)
        DROFrame.dro_mpos = Utils.getFont("dro.mpos", DROFrame.dro_mpos)

        row = 0
        col = 0
        Label(self, text=_("Status:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.state = Button(
            self,
            text=Sender.NOT_CONNECTED,
            font=DROFrame.dro_status,
            command=self.showState,
            cursor="hand1",
            background=Sender.STATECOLOR[Sender.NOT_CONNECTED],
            activebackground="LightYellow",
        )
        self.state.grid(row=row, column=col, columnspan=3, sticky=EW)
        tkExtra.Balloon.set(
            self.state,
            _(
                "Show current state of the machine\n"
                "Click to see details\n"
                "Right-Click to clear alarm/errors"
            ),
        )
        self.state.bind("<Button-3>", self.stateMenu)

        row += 1
        col = 0
        Label(self, text=_("WPos:")).grid(row=row, column=col, sticky=E)

        # work
        col += 1
        self.xwork = Entry(
            self,
            font=DROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.xwork.grid(row=row, column=col, padx=1, sticky=EW)
        tkExtra.Balloon.set(self.xwork, _("X work position (click to set)"))
        self.xwork.bind("<FocusIn>", self.workFocus)
        self.xwork.bind("<Return>", self.setX)
        self.xwork.bind("<KP_Enter>", self.setX)

        # ---
        col += 1
        self.ywork = Entry(
            self,
            font=DROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.ywork.grid(row=row, column=col, padx=1, sticky=EW)
        tkExtra.Balloon.set(self.ywork, _("Y work position (click to set)"))
        self.ywork.bind("<FocusIn>", self.workFocus)
        self.ywork.bind("<Return>", self.setY)
        self.ywork.bind("<KP_Enter>", self.setY)

        # ---
        col += 1
        self.zwork = Entry(
            self,
            font=DROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.zwork.grid(row=row, column=col, padx=1, sticky=EW)
        tkExtra.Balloon.set(self.zwork, _("Z work position (click to set)"))
        self.zwork.bind("<FocusIn>", self.workFocus)
        self.zwork.bind("<Return>", self.setZ)
        self.zwork.bind("<KP_Enter>", self.setZ)

        # Machine
        row += 1
        col = 0
        Label(self, text=_("MPos:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.xmachine = Label(
            self,
            font=DROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.xmachine.grid(row=row, column=col, padx=1, sticky=EW)

        col += 1
        self.ymachine = Label(
            self,
            font=DROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.ymachine.grid(row=row, column=col, padx=1, sticky=EW)

        col += 1
        self.zmachine = Label(
            self,
            font=DROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.zmachine.grid(row=row, column=col, padx=1, sticky=EW)

        # Set buttons
        row += 1
        col = 1

        self.xzero = Button(
            self,
            text=_("X=0"),
            command=self.setX0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.xzero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            self.xzero, _("Set X coordinate to zero "
                          + "(or to typed coordinate in WPos)")
        )
        self.addWidget(self.xzero)

        col += 1
        self.yzero = Button(
            self,
            text=_("Y=0"),
            command=self.setY0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.yzero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            self.yzero, _("Set Y coordinate to zero "
                          + "(or to typed coordinate in WPos)")
        )
        self.addWidget(self.yzero)

        col += 1
        self.zzero = Button(
            self,
            text=_("Z=0"),
            command=self.setZ0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.zzero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            self.zzero, _("Set Z coordinate to zero "
                          + "(or to typed coordinate in WPos)")
        )
        self.addWidget(self.zzero)

        # Set buttons
        row += 1
        col = 1
        self.xyzero = Button(
            self,
            text=_("XY=0"),
            command=self.setXY0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.xyzero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            self.xyzero, _("Set XY coordinate to zero "
                           + "(or to typed coordinate in WPos)")
        )
        self.addWidget(self.xyzero)

        col += 1
        self.xyzzero = Button(
            self,
            text=_("XYZ=0"),
            command=self.setXYZ0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        self.xyzzero.grid(row=row, column=col, pady=0, sticky=EW, columnspan=2)
        tkExtra.Balloon.set(
            self.xyzzero,
            _("Set XYZ coordinate to zero (or to typed coordinate in WPos)"),
        )
        self.addWidget(self.xyzzero)

        # Set buttons
        row += 1
        col = 1
        f = Frame(self)
        f.grid(row=row, column=col, columnspan=3, pady=0, sticky=EW)

        b = Button(
            f,
            text=_("Set WPOS"),
            image=Utils.icons["origin"],
            compound=LEFT,
            activebackground="LightYellow",
            command=lambda s=self: s.event_generate("<<SetWPOS>>"),
            padx=2,
            pady=1,
        )
        b.pack(side=LEFT, fill=X, expand=YES)
        tkExtra.Balloon.set(b, _("Set WPOS to mouse location"))
        self.addWidget(b)

        b = Button(
            f,
            text=_("Move Gantry"),
            image=Utils.icons["gantry"],
            compound=LEFT,
            activebackground="LightYellow",
            command=lambda s=self: s.event_generate("<<MoveGantry>>"),
            padx=2,
            pady=1,
        )
        b.pack(side=RIGHT, fill=X, expand=YES)
        tkExtra.Balloon.set(b, _("Move gantry to mouse location [g]"))
        self.addWidget(b)

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

    # ----------------------------------------------------------------------
    def stateMenu(self, event=None):
        menu = Menu(self, tearoff=0)

        menu.add_command(
            label=_("Show Info"),
            image=Utils.icons["info"],
            compound=LEFT,
            command=self.showState,
        )
        menu.add_command(
            label=_("Clear Message"),
            image=Utils.icons["clear"],
            compound=LEFT,
            command=lambda s=self: s.event_generate("<<AlarmClear>>"),
        )
        menu.add_separator()

        menu.add_command(
            label=_("Feed hold"),
            image=Utils.icons["pause"],
            compound=LEFT,
            command=lambda s=self: s.event_generate("<<FeedHold>>"),
        )
        menu.add_command(
            label=_("Resume"),
            image=Utils.icons["start"],
            compound=LEFT,
            command=lambda s=self: s.event_generate("<<Resume>>"),
        )

        menu.tk_popup(event.x_root, event.y_root)

    # ----------------------------------------------------------------------
    def updateState(self):
        msg = self.app._msg or CNC.vars["state"]
        if CNC.vars["pins"] is not None and CNC.vars["pins"] != "":
            msg += " [" + CNC.vars["pins"] + "]"
        self.state.config(text=msg, background=CNC.vars["color"])

    # ----------------------------------------------------------------------
    def updateCoords(self):
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
        if focus is not self.xwork:
            self.xwork.delete(0, END)
            self.xwork.insert(0, self.padFloat(CNC.drozeropad, CNC.vars["wx"]))
        if focus is not self.ywork:
            self.ywork.delete(0, END)
            self.ywork.insert(0, self.padFloat(CNC.drozeropad, CNC.vars["wy"]))
        if focus is not self.zwork:
            self.zwork.delete(0, END)
            self.zwork.insert(0, self.padFloat(CNC.drozeropad, CNC.vars["wz"]))

        self.xmachine["text"] = self.padFloat(CNC.drozeropad, CNC.vars["mx"])
        self.ymachine["text"] = self.padFloat(CNC.drozeropad, CNC.vars["my"])
        self.zmachine["text"] = self.padFloat(CNC.drozeropad, CNC.vars["mz"])
        self.app.abcdro.updateCoords()

    # ----------------------------------------------------------------------
    def padFloat(self, decimals, value):
        if decimals > 0:
            return f"{value:0.{decimals}f}"
        else:
            return value

    # ----------------------------------------------------------------------
    # Do not give the focus while we are running
    # ----------------------------------------------------------------------
    def workFocus(self, event=None):
        if self.app.running:
            self.app.focus_set()

    # ----------------------------------------------------------------------
    def setX0(self, event=None):
        self.app.mcontrol._wcsSet("0", None, None, None, None, None)

    # ----------------------------------------------------------------------
    def setY0(self, event=None):
        self.app.mcontrol._wcsSet(None, "0", None, None, None, None)

    # ----------------------------------------------------------------------
    def setZ0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, "0", None, None, None)

    # ----------------------------------------------------------------------
    def setXY0(self, event=None):
        self.app.mcontrol._wcsSet("0", "0", None, None, None, None)

    # ----------------------------------------------------------------------
    def setXYZ0(self, event=None):
        self.app.mcontrol._wcsSet("0", "0", "0", None, None, None)

    # ----------------------------------------------------------------------
    def setX(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.xwork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(value, None, None, None, None, None)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def setY(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.ywork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(None, value, None, None, None, None)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def setZ(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.zwork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(None, None, value, None, None, None)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def showState(self):
        err = CNC.vars["errline"]
        if err:
            msg = _("Last error: {}\n").format(CNC.vars["errline"])
        else:
            msg = ""

        state = CNC.vars["state"]
        msg += ERROR_CODES.get(
            state, _("No info available.\nPlease contact the author.")
        )
        messagebox.showinfo(_("State: {}").format(state), msg, parent=self)


# =============================================================================
# DRO Frame ABC
# =============================================================================
class abcDROFrame(CNCRibbon.PageExLabelFrame):

    dro_status = ("Helvetica", 12, "bold")
    dro_wpos = ("Helvetica", 12, "bold")
    dro_mpos = ("Helvetica", 12)

    def __init__(self, master, app):
        CNCRibbon.PageExLabelFrame.__init__(
            self, master, "abcDRO", _("abcDRO"), app)

        frame = Frame(self())
        frame.pack(side=TOP, fill=X)

        abcDROFrame.dro_status = Utils.getFont(
            "dro.status", abcDROFrame.dro_status)
        abcDROFrame.dro_wpos = Utils.getFont("dro.wpos", abcDROFrame.dro_wpos)
        abcDROFrame.dro_mpos = Utils.getFont("dro.mpos", abcDROFrame.dro_mpos)

        row = 0
        col = 0
        Label(frame, text=_("abcWPos:")).grid(row=row, column=col)

        # work
        col += 1
        self.awork = Entry(
            frame,
            font=abcDROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=8,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.awork.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.awork, _("A work position (click to set)"))
        self.awork.bind("<FocusIn>", self.workFocus)
        self.awork.bind("<Return>", self.setA)
        self.awork.bind("<KP_Enter>", self.setA)

        # ---
        col += 1
        self.bwork = Entry(
            frame,
            font=abcDROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=8,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.bwork.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.bwork, _("B work position (click to set)"))
        self.bwork.bind("<FocusIn>", self.workFocus)
        self.bwork.bind("<Return>", self.setB)
        self.bwork.bind("<KP_Enter>", self.setB)

        # ---
        col += 1
        self.cwork = Entry(
            frame,
            font=abcDROFrame.dro_wpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=8,
            relief=FLAT,
            borderwidth=0,
            justify=RIGHT,
        )
        self.cwork.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.cwork, _("C work position (click to set)"))
        self.cwork.bind("<FocusIn>", self.workFocus)
        self.cwork.bind("<Return>", self.setC)
        self.cwork.bind("<KP_Enter>", self.setC)

        # Machine
        row += 1
        col = 0
        Label(frame, text=_("MPos:")).grid(row=row, column=col, sticky=E),

        col += 1
        self.amachine = Label(
            frame,
            font=abcDROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.amachine.grid(row=row, column=col, padx=1, sticky=EW)
        col += 1
        self.bmachine = Label(
            frame,
            font=abcDROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.bmachine.grid(row=row, column=col, padx=1, sticky=EW)

        col += 1
        self.cmachine = Label(
            frame,
            font=abcDROFrame.dro_mpos,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            anchor=E,
        )
        self.cmachine.grid(row=row, column=col, padx=1, sticky=EW)

        # Set buttons
        row += 1
        col = 1

        azero = Button(
            frame,
            text=_("A=0"),
            command=self.setA0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        azero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            azero, _("Set A coordinate to zero "
                     + "(or to typed coordinate in WPos)")
        )
        self.addWidget(azero)

        col += 1
        bzero = Button(
            frame,
            text=_("B=0"),
            command=self.setB0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        bzero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            bzero, _("Set B coordinate to zero "
                     + "(or to typed coordinate in WPos)")
        )
        self.addWidget(bzero)

        col += 1
        czero = Button(
            frame,
            text=_("C=0"),
            command=self.setC0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        czero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            czero, _("Set C coordinate to zero "
                     + "(or to typed coordinate in WPos)")
        )
        self.addWidget(czero)

        # Set buttons
        row += 1
        col = 1
        bczero = Button(
            frame,
            text=_("BC=0"),
            command=self.setBC0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        bczero.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(
            bczero, _("Set BC coordinate to zero "
                      + "(or to typed coordinate in WPos)")
        )
        self.addWidget(bczero)

        col += 1
        abczero = Button(
            frame,
            text=_("ABC=0"),
            command=self.setABC0,
            activebackground="LightYellow",
            padx=2,
            pady=1,
        )
        abczero.grid(row=row, column=col, pady=0, sticky=EW, columnspan=2)
        tkExtra.Balloon.set(
            abczero, _("Set ABC coordinate to zero "
                       + "(or to typed coordinate in WPos)")
        )
        self.addWidget(abczero)

    # ----------------------------------------------------------------------

    def updateCoords(self):
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
            if focus is not self.awork:
                self.awork.delete(0, END)
                self.awork.insert(0, self.padFloat(CNC.drozeropad,
                                                   CNC.vars["wa"]))
            if focus is not self.bwork:
                self.bwork.delete(0, END)
                self.bwork.insert(0, self.padFloat(CNC.drozeropad,
                                                   CNC.vars["wb"]))
            if focus is not self.cwork:
                self.cwork.delete(0, END)
                self.cwork.insert(0, self.padFloat(CNC.drozeropad,
                                                   CNC.vars["wc"]))

            self.amachine["text"] = self.padFloat(CNC.drozeropad,
                                                  CNC.vars["ma"])
            self.bmachine["text"] = self.padFloat(CNC.drozeropad,
                                                  CNC.vars["mb"])
            self.cmachine["text"] = self.padFloat(CNC.drozeropad,
                                                  CNC.vars["mc"])

    # ----------------------------------------------------------------------

    def padFloat(self, decimals, value):
        if decimals > 0:
            return f"{value:0.{decimals}f}"
        else:
            return value

    # ----------------------------------------------------------------------
    # Do not give the focus while we are running
    # ----------------------------------------------------------------------

    def workFocus(self, event=None):
        if self.app.running:
            self.app.focus_set()

    # ----------------------------------------------------------------------

    def setA0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, None, "0", None, None)

    # ----------------------------------------------------------------------
    def setB0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, None, None, "0", None)

    # ----------------------------------------------------------------------
    def setC0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, None, None, None, "0")

    # ----------------------------------------------------------------------
    def setBC0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, None, "0", "0", None)

    # ----------------------------------------------------------------------
    def setABC0(self, event=None):
        self.app.mcontrol._wcsSet(None, None, None, "0", "0", "0")

    # ----------------------------------------------------------------------
    def setA(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.awork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(None, None, None, value, None, None)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def setB(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.bwork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(None, None, None, None, value, None)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def setC(self, event=None):
        if self.app.running:
            return
        try:
            value = round(eval(self.cwork.get(), None, CNC.vars), 3)
            self.app.mcontrol._wcsSet(None, None, None, None, None, value)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    def showState(self):
        err = CNC.vars["errline"]
        if err:
            msg = _("Last error: {}\n").format(CNC.vars["errline"])
        else:
            msg = ""

            state = CNC.vars["state"]
            msg += ERROR_CODES.get(
                state, _("No info available.\nPlease contact the author.")
            )
            messagebox.showinfo(_("State: {}").format(state), msg, parent=self)


# =============================================================================
# ControlFrame
# =============================================================================
class ControlFrame(CNCRibbon.PageExLabelFrame):
    def __init__(self, master, app):
        CNCRibbon.PageExLabelFrame.__init__(
            self, master, "Control", _("Control"), app)

        frame = Frame(self())
        frame.pack(side=TOP, fill=X)

        row, col = 0, 0
        Label(frame, text=_("Z")).grid(row=row, column=col)

        col += 3
        Label(frame, text=_("Y")).grid(row=row, column=col)

        # ---
        row += 1
        col = 0

        width = 3
        height = 2

        b = Button(
            frame,
            text=Unicode.BLACK_UP_POINTING_TRIANGLE,
            command=self.moveZup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +Z"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame,
            text=Unicode.UPPER_LEFT_TRIANGLE,
            command=self.moveXdownYup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -X +Y"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_UP_POINTING_TRIANGLE,
            command=self.moveYup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +Y"))
        self.addWidget(b)
        col += 1
        b = Button(
            frame,
            text=Unicode.UPPER_RIGHT_TRIANGLE,
            command=self.moveXupYup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +X +Y"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame, text="\u00D710", command=self.mulStep,
            width=3, padx=1, pady=1
        )
        b.grid(row=row, column=col, sticky=EW + S)
        tkExtra.Balloon.set(b, _("Multiply step by 10"))
        self.addWidget(b)

        col += 1
        b = Button(frame, text=_("+"), command=self.incStep,
                   width=3, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + S)
        tkExtra.Balloon.set(b, _("Increase step by 1 unit"))
        self.addWidget(b)

        # ---
        row += 1

        col = 1
        Label(frame, text=_("X"),
              width=3, anchor=E).grid(row=row, column=col, sticky=E)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
            command=self.moveXdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -X"))
        self.addWidget(b)

        col += 1
        b = Utils.UserButton(
            frame,
            self.app,
            0,
            text=Unicode.LARGE_CIRCLE,
            command=self.go2origin,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(
            b,
            _("Move to Origin.\nUser configurable button.\n"
              + "Right click to configure."),
        )
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
            command=self.moveXup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +X"))
        self.addWidget(b)

        # --
        col += 1
        Label(frame, "", width=2).grid(row=row, column=col)

        col += 1
        self.step = tkExtra.Combobox(
            frame, width=6, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.step.grid(row=row, column=col, columnspan=2, sticky=EW)
        self.step.set(Utils.config.get("Control", "step"))
        self.step.fill(
            map(float, Utils.config.get("Control", "steplist").split()))
        tkExtra.Balloon.set(self.step, _("Step for every move operation"))
        self.addWidget(self.step)

        # -- Separate zstep --
        try:
            zstep = Utils.config.get("Control", "zstep")
            self.zstep = tkExtra.Combobox(
                frame, width=4, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
            )
            self.zstep.grid(row=row, column=0, columnspan=1, sticky=EW)
            self.zstep.set(zstep)
            zsl = [_NOZSTEP]
            zsl.extend(
                map(float, Utils.config.get("Control", "zsteplist").split()))
            self.zstep.fill(zsl)
            tkExtra.Balloon.set(self.zstep, _("Step for Z move operation"))
            self.addWidget(self.zstep)
        except Exception:
            self.zstep = self.step

        # Default steppings
        try:
            self.step1 = Utils.getFloat("Control", "step1")
        except Exception:
            self.step1 = 0.1

        try:
            self.step2 = Utils.getFloat("Control", "step2")
        except Exception:
            self.step2 = 1

        try:
            self.step3 = Utils.getFloat("Control", "step3")
        except Exception:
            self.step3 = 10

        # ---
        row += 1
        col = 0

        b = Button(
            frame,
            text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
            command=self.moveZdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -Z"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame,
            text=Unicode.LOWER_LEFT_TRIANGLE,
            command=self.moveXdownYdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -X -Y"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
            command=self.moveYdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -Y"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.LOWER_RIGHT_TRIANGLE,
            command=self.moveXupYdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +X -Y"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame, text="\u00F710", command=self.divStep, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + N)
        tkExtra.Balloon.set(b, _("Divide step by 10"))
        self.addWidget(b)

        col += 1
        b = Button(frame, text=_("-"), command=self.decStep, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + N)
        tkExtra.Balloon.set(b, _("Decrease step by 1 unit"))
        self.addWidget(b)

        try:
            self.tk.call("grid", "anchor", self, CENTER)
        except TclError:
            pass

    # ----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setFloat("Control", "step", self.step.get())
        if self.zstep is not self.step:
            Utils.setFloat("Control", "zstep", self.zstep.get())

    # ----------------------------------------------------------------------
    # Jogging
    # ----------------------------------------------------------------------
    def getStep(self, axis="x"):
        if axis == "z":
            zs = self.zstep.get()
            if zs == _NOZSTEP:
                return self.step.get()
            else:
                return zs
        else:
            return self.step.get()

    def moveXup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X{self.step.get()}")

    def moveXdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X-{self.step.get()}")

    def moveYup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"Y{self.step.get()}")

    def moveYdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"Y-{self.step.get()}")

    def moveXdownYup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X-{self.step.get()}Y{self.step.get()}")

    def moveXupYup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X{self.step.get()}Y{self.step.get()}")

    def moveXdownYdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X-{self.step.get()}Y-{self.step.get()}")

    def moveXupYdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"X{self.step.get()}Y-{self.step.get()}")

    def moveZup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"Z{self.getStep('z')}")

    def moveZdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"Z-{self.getStep('z')}")

    def go2origin(self, event=None):
        self.sendGCode("G90")
        self.sendGCode("G0Z%d" % (CNC.vars["safe"]))
        self.sendGCode("G0X0Y0")
        self.sendGCode("G0Z0")

    # ----------------------------------------------------------------------
    def setStep(self, s, zs=None):
        self.step.set(f"{s:.4g}")
        if self.zstep is self.step or zs is None:
            self.event_generate("<<Status>>", data=_("Step: {:g}").format(s))
        else:
            self.zstep.set(f"{zs:.4g}")
            self.event_generate(
                "<<Status>>", data=_("Step: {:g}  Zstep: {:g} ").format(s, zs))

    # ----------------------------------------------------------------------
    @staticmethod
    def _stepPower(step):
        try:
            step = float(step)
            if step <= 0.0:
                step = 1.0
        except Exception:
            step = 1.0
        power = math.pow(10.0, math.floor(math.log10(step)))
        return round(step / power) * power, power

    # ----------------------------------------------------------------------
    def incStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = ControlFrame._stepPower(self.step.get())
        s = step + power
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.zstep is not self.step and self.zstep.get() != _NOZSTEP:
            step, power = ControlFrame._stepPower(self.zstep.get())
            zs = step + power
            if zs < _LOWSTEP:
                zs = _LOWSTEP
            elif zs > _HIGHZSTEP:
                zs = _HIGHZSTEP
        else:
            zs = None
        self.setStep(s, zs)

    # ----------------------------------------------------------------------
    def decStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = ControlFrame._stepPower(self.step.get())
        s = step - power
        if s <= 0.0:
            s = step - power / 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.zstep is not self.step and self.zstep.get() != _NOZSTEP:
            step, power = ControlFrame._stepPower(self.zstep.get())
            zs = step - power
            if zs <= 0.0:
                zs = step - power / 10.0
            if zs < _LOWSTEP:
                zs = _LOWSTEP
            elif zs > _HIGHZSTEP:
                zs = _HIGHZSTEP
        else:
            zs = None
        self.setStep(s, zs)

    # ----------------------------------------------------------------------
    def mulStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = ControlFrame._stepPower(self.step.get())
        s = step * 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.zstep is not self.step and self.zstep.get() != _NOZSTEP:
            step, power = ControlFrame._stepPower(self.zstep.get())
            zs = step * 10.0
            if zs < _LOWSTEP:
                zs = _LOWSTEP
            elif zs > _HIGHZSTEP:
                zs = _HIGHZSTEP
        else:
            zs = None
        self.setStep(s, zs)

    # ----------------------------------------------------------------------
    def divStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = ControlFrame._stepPower(self.step.get())
        s = step / 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.zstep is not self.step and self.zstep.get() != _NOZSTEP:
            step, power = ControlFrame._stepPower(self.zstep.get())
            zs = step / 10.0
            if zs < _LOWSTEP:
                zs = _LOWSTEP
            elif zs > _HIGHZSTEP:
                zs = _HIGHZSTEP
        else:
            zs = None
        self.setStep(s, zs)

    # ----------------------------------------------------------------------
    def setStep1(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step1, self.step1)

    # ----------------------------------------------------------------------
    def setStep2(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step2, self.step2)

    # ----------------------------------------------------------------------
    def setStep3(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step3, self.step2)


# =============================================================================
# abc ControlFrame
# =============================================================================


class abcControlFrame(CNCRibbon.PageExLabelFrame):
    def __init__(self, master, app):
        CNCRibbon.PageExLabelFrame.__init__(
            self, master, "abcControl", _("abcControl"), app
        )

        frame = Frame(self())
        frame.pack(side=TOP, fill=X)

        row, col = 0, 0
        Label(frame, text=_("A")).grid(row=row, column=col)

        col += 3
        Label(frame, text=_("C")).grid(row=row, column=col)

        # ---
        row += 1
        col = 0

        width = 3
        height = 2

        b = Button(
            frame,
            text=Unicode.BLACK_UP_POINTING_TRIANGLE,
            command=self.moveAup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +A"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame,
            text=Unicode.UPPER_LEFT_TRIANGLE,
            command=self.moveBdownCup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )

        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -B +C"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_UP_POINTING_TRIANGLE,
            command=self.moveCup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +C"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.UPPER_RIGHT_TRIANGLE,
            command=self.moveBupCup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +B +C"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame, text="\u00D710", command=self.mulStep,
            width=3, padx=1, pady=1
        )
        b.grid(row=row, column=col, sticky=EW + S)
        tkExtra.Balloon.set(b, _("Multiply step by 10"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame, text=_("+"), command=self.incStep, width=3, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + S)
        tkExtra.Balloon.set(b, _("Increase step by 1 unit"))
        self.addWidget(b)

        # ---
        row += 1

        col = 1
        Label(frame, text=_("B"),
              width=3, anchor=E).grid(row=row, column=col, sticky=E)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_LEFT_POINTING_TRIANGLE,
            command=self.moveBdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -B"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.LARGE_CIRCLE,
            command=self.go2abcorigin,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Return ABC to 0."))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_RIGHT_POINTING_TRIANGLE,
            command=self.moveBup,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +B"))
        self.addWidget(b)

        # --
        col += 1
        Label(frame, "", width=2).grid(row=row, column=col)

        col += 1
        self.step = tkExtra.Combobox(
            frame, width=6, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.step.grid(row=row, column=col, columnspan=2, sticky=EW)
        self.step.set(Utils.config.get("abcControl", "step"))
        self.step.fill(
            map(float, Utils.config.get("abcControl", "abcsteplist").split())
        )
        tkExtra.Balloon.set(self.step, _("Step for every move operation"))
        self.addWidget(self.step)

        # -- Separate astep --
        try:
            astep = Utils.config.get("abcControl", "astep")
            self.astep = tkExtra.Combobox(
                frame, width=4, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
            )
            self.astep.grid(row=row, column=0, columnspan=1, sticky=EW)
            self.astep.set(astep)
            asl = [_NOASTEP]
            asl.extend(
                map(float,
                    Utils.config.get("abcControl", "asteplist").split()))
            self.astep.fill(asl)
            tkExtra.Balloon.set(self.astep, _("Step for A move operation"))
            self.addWidget(self.astep)
        except Exception:
            self.astep = self.step

        # Default steppings
        try:
            self.step1 = Utils.getFloat("abcControl", "step1")
        except Exception:
            self.step1 = 0.1

        try:
            self.step2 = Utils.getFloat("abcControl", "step2")
        except Exception:
            self.step2 = 1

        try:
            self.step3 = Utils.getFloat("abcControl", "step3")
        except Exception:
            self.step3 = 10

        # ---
        row += 1
        col = 0

        b = Button(
            frame,
            text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
            command=self.moveAdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -A"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame,
            text=Unicode.LOWER_LEFT_TRIANGLE,
            command=self.moveBdownCdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -B -C"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.BLACK_DOWN_POINTING_TRIANGLE,
            command=self.moveCdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move -C"))
        self.addWidget(b)

        col += 1
        b = Button(
            frame,
            text=Unicode.LOWER_RIGHT_TRIANGLE,
            command=self.moveBupCdown,
            width=width,
            height=height,
            activebackground="LightYellow",
        )
        b.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(b, _("Move +B -C"))
        self.addWidget(b)

        col += 2
        b = Button(
            frame, text="\u00F710", command=self.divStep, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + N)
        tkExtra.Balloon.set(b, _("Divide step by 10"))
        self.addWidget(b)

        col += 1
        b = Button(frame, text=_("-"), command=self.decStep, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=EW + N)
        tkExtra.Balloon.set(b, _("Decrease step by 1 unit"))
        self.addWidget(b)

        try:
            self.tk.call("grid", "anchor", self, CENTER)
        except TclError:
            pass

    # ----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setFloat("abcControl", "step", self.step.get())
        if self.astep is not self.step:
            Utils.setFloat("abcControl", "astep", self.astep.get())

    # ----------------------------------------------------------------------
    # Jogging
    # ----------------------------------------------------------------------
    def getStep(self, axis="a"):
        if axis == "a":
            aas = self.astep.get()
            if aas == _NOASTEP:
                return self.step.get()
            else:
                return aas
        else:
            return self.step.get()

    def moveBup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"B{self.step.get()}")

    def moveBdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"B-{self.step.get()}")

    def moveCup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"C{self.step.get()}")

    def moveCdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"C-{self.step.get()}")

    def moveBdownCup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        # XXX: Possible error in original code lead to %C string; fixed by guessing from methods below.
        # Original: self.app.mcontrol.jog("B-%C%s"%(self.step.get(),self.step.get()))
        self.app.mcontrol.jog(f"B-{self.step.get()}C{self.step.get()}")

    def moveBupCup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"B{self.step.get()}C{self.step.get()}")

    def moveBdownCdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"B-{self.step.get()}C-{self.step.get()}")

    def moveBupCdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"B{self.step.get()}C-{self.step.get()}")

    def moveAup(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"A{self.getStep('z')}")

    def moveAdown(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.app.mcontrol.jog(f"A-{self.getStep('z')}")

    def go2abcorigin(self, event=None):
        self.sendGCode("G90")
        self.sendGCode("G0B0C0")
        self.sendGCode("G0A0")

    # ----------------------------------------------------------------------
    def setStep(self, s, aas=None):
        self.step.set(f"{s:.4g}")
        if self.astep is self.step or aas is None:
            self.event_generate("<<Status>>", data=_("Step: {:g}").format(s))
        else:
            self.astep.set(f"{aas:.4g}")
            self.event_generate(
                "<<Status>>", data=_("Step: {:g}   Astep:{:g} ").format(s, aas)
            )

    # ----------------------------------------------------------------------
    @staticmethod
    def _stepPower(step):
        try:
            step = float(step)
            if step <= 0.0:
                step = 1.0
        except Exception:
            step = 1.0
        power = math.pow(10.0, math.floor(math.log10(step)))
        return round(step / power) * power, power

    # ----------------------------------------------------------------------
    def incStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = abcControlFrame._stepPower(self.step.get())
        s = step + power
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.astep is not self.step and self.astep.get() != _NOASTEP:
            step, power = abcControlFrame._stepPower(self.astep.get())
            aas = step + power
            if aas < _LOWSTEP:
                aas = _LOWSTEP
            elif aas > _HIGHASTEP:
                aas = _HIGHASTEP
        else:
            aas = None
        self.setStep(s, aas)

    # ----------------------------------------------------------------------
    def decStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = abcControlFrame._stepPower(self.step.get())
        s = step - power
        if s <= 0.0:
            s = step - power / 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.astep is not self.step and self.astep.get() != _NOASTEP:
            step, power = abcControlFrame._stepPower(self.astep.get())
            aas = step - power
            if aas <= 0.0:
                aas = step - power / 10.0
            if aas < _LOWSTEP:
                aas = _LOWSTEP
            elif aas > _HIGHASTEP:
                aas = _HIGHASTEP
        else:
            aas = None
        self.setStep(s, aas)

    # ----------------------------------------------------------------------
    def mulStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = abcControlFrame._stepPower(self.step.get())
        s = step * 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.astep is not self.step and self.astep.get() != _NOASTEP:
            step, power = abcControlFrame._stepPower(self.astep.get())
            aas = step * 10.0
            if aas < _LOWSTEP:
                aas = _LOWSTEP
            elif aas > _HIGHASTEP:
                aas = _HIGHASTEP
        else:
            aas = None
        self.setStep(s, aas)

    # ----------------------------------------------------------------------
    def divStep(self, event=None):
        if event is not None and not self.acceptKey():
            return
        step, power = abcControlFrame._stepPower(self.step.get())
        s = step / 10.0
        if s < _LOWSTEP:
            s = _LOWSTEP
        elif s > _HIGHSTEP:
            s = _HIGHSTEP
        if self.astep is not self.step and self.astep.get() != _NOASTEP:
            step, power = abcControlFrame._stepPower(self.astep.get())
            aas = step / 10.0
            if aas < _LOWSTEP:
                aas = _LOWSTEP
            elif aas > _HIGHASTEP:
                aas = _HIGHASTEP
        else:
            aas = None
        self.setStep(s, aas)

    # ----------------------------------------------------------------------
    def setStep1(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step1, self.step1)

    # ----------------------------------------------------------------------
    def setStep2(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step2, self.step2)

    # ----------------------------------------------------------------------

    def setStep3(self, event=None):
        if event is not None and not self.acceptKey():
            return
        self.setStep(self.step3, self.step2)


# =============================================================================
# StateFrame
# =============================================================================


class StateFrame(CNCRibbon.PageExLabelFrame):
    def __init__(self, master, app):
        global wcsvar
        CNCRibbon.PageExLabelFrame.__init__(
            self, master, "State", _("State"), app)
        self._gUpdate = False

        # State
        f = Frame(self())
        f.pack(side=TOP, fill=X)

        # ===
        col, row = 0, 0
        f2 = Frame(f)
        f2.grid(row=row, column=col, columnspan=5, sticky=EW)
        for p, w in enumerate(WCS):
            col += 1
            b = Radiobutton(
                f2,
                text=w,
                foreground="DarkRed",
                font="Helvetica,14",
                padx=1,
                pady=1,
                variable=wcsvar,
                value=p,
                indicatoron=FALSE,
                activebackground="LightYellow",
                command=self.wcsChange,
            )
            b.pack(side=LEFT, fill=X, expand=YES)
            tkExtra.Balloon.set(b, _("Switch to workspace {}").format(w))
            self.addWidget(b)

        # Absolute or relative mode
        row += 1
        col = 0
        Label(f, text=_("Distance:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.distance = tkExtra.Combobox(
            f,
            True,
            command=self.distanceChange,
            width=5,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        self.distance.fill(sorted(DISTANCE_MODE.values()))
        self.distance.grid(row=row, column=col, columnspan=2, sticky=EW)
        tkExtra.Balloon.set(self.distance, _("Distance Mode [G90,G91]"))
        self.addWidget(self.distance)

        # populate gstate dictionary
        self.gstate = {}  # $G state results widget dictionary
        for k, v in DISTANCE_MODE.items():
            self.gstate[k] = (self.distance, v)

        # Units mode
        col += 2
        Label(f, text=_("Units:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.units = tkExtra.Combobox(
            f,
            True,
            command=self.unitsChange,
            width=5,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        self.units.fill(sorted(UNITS.values()))
        self.units.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.units, _("Units [G20, G21]"))
        for k, v in UNITS.items():
            self.gstate[k] = (self.units, v)
        self.addWidget(self.units)

        # Tool
        row += 1
        col = 0
        Label(f, text=_("Tool:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.toolEntry = tkExtra.IntegerEntry(
            f, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5
        )
        self.toolEntry.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.toolEntry, _("Tool number [T#]"))
        self.addWidget(self.toolEntry)

        col += 1
        b = Button(f, text=_("set"), command=self.setTool, padx=1, pady=1)
        b.grid(row=row, column=col, sticky=W)
        self.addWidget(b)

        # Plane
        col += 1
        Label(f, text=_("Plane:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.plane = tkExtra.Combobox(
            f,
            True,
            command=self.planeChange,
            width=5,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        self.plane.fill(sorted(PLANE.values()))
        self.plane.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.plane, _("Plane [G17,G18,G19]"))
        self.addWidget(self.plane)

        for k, v in PLANE.items():
            self.gstate[k] = (self.plane, v)

        # Feed speed
        row += 1
        col = 0
        Label(f, text=_("Feed:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.feedRate = tkExtra.FloatEntry(
            f,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            disabledforeground="Black",
            width=5,
        )
        self.feedRate.grid(row=row, column=col, sticky=EW)
        self.feedRate.bind("<Return>", self.setFeedRate)
        self.feedRate.bind("<KP_Enter>", self.setFeedRate)
        tkExtra.Balloon.set(self.feedRate, _("Feed Rate [F#]"))
        self.addWidget(self.feedRate)

        col += 1
        b = Button(f, text=_("set"), command=self.setFeedRate, padx=1, pady=1)
        b.grid(row=row, column=col, columnspan=2, sticky=W)
        self.addWidget(b)

        # Feed mode
        col += 1
        Label(f, text=_("Mode:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.feedMode = tkExtra.Combobox(
            f,
            True,
            command=self.feedModeChange,
            width=5,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        self.feedMode.fill(sorted(FEED_MODE.values()))
        self.feedMode.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.feedMode, _("Feed Mode [G93, G94, G95]"))
        for k, v in FEED_MODE.items():
            self.gstate[k] = (self.feedMode, v)
        self.addWidget(self.feedMode)

        # TLO
        row += 1
        col = 0
        Label(f, text=_("TLO:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.tlo = tkExtra.FloatEntry(
            f,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            disabledforeground="Black",
            width=5,
        )
        self.tlo.grid(row=row, column=col, sticky=EW)
        self.tlo.bind("<Return>", self.setTLO)
        self.tlo.bind("<KP_Enter>", self.setTLO)
        tkExtra.Balloon.set(self.tlo, _("Tool length offset [G43.1#]"))
        self.addWidget(self.tlo)

        col += 1
        b = Button(f, text=_("set"), command=self.setTLO, padx=1, pady=1)
        b.grid(row=row, column=col, columnspan=2, sticky=W)
        self.addWidget(b)

        # g92
        col += 1
        Label(f, text=_("G92:")).grid(row=row, column=col, sticky=E)

        col += 1
        self.g92 = Label(f, text="")
        self.g92.grid(row=row, column=col, columnspan=3, sticky=EW)
        tkExtra.Balloon.set(self.g92, _("Set position [G92 X# Y# Z#]"))
        self.addWidget(self.g92)

        # ---
        f.grid_columnconfigure(1, weight=1)
        f.grid_columnconfigure(4, weight=1)

        # Spindle
        f = Frame(self())
        f.pack(side=BOTTOM, fill=X)

        self.override = IntVar()
        self.override.set(100)
        self.spindle = BooleanVar()
        self.spindleSpeed = IntVar()

        col, row = 0, 0
        self.overrideCombo = tkExtra.Combobox(
            f, width=8, command=self.overrideComboChange
        )
        self.overrideCombo.fill(OVERRIDES)
        self.overrideCombo.grid(row=row, column=col, pady=0, sticky=EW)
        tkExtra.Balloon.set(self.overrideCombo, _("Select override type."))

        b = Button(f, text=_("Reset"), pady=0, command=self.resetOverride)
        b.grid(row=row + 1, column=col, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Reset override to 100%"))

        col += 1
        self.overrideScale = Scale(
            f,
            command=self.overrideChange,
            variable=self.override,
            showvalue=True,
            orient=HORIZONTAL,
            from_=25,
            to_=200,
            resolution=1,
        )
        self.overrideScale.bind("<Double-1>", self.resetOverride)
        self.overrideScale.bind("<Button-3>", self.resetOverride)
        self.overrideScale.grid(
            row=row, column=col, rowspan=2, columnspan=4, sticky=EW)
        tkExtra.Balloon.set(
            self.overrideScale,
            _("Set Feed/Rapid/Spindle Override. "
              + "Right or Double click to reset."),
        )

        self.overrideCombo.set(OVERRIDES[0])

        # ---
        row += 2
        col = 0
        b = Checkbutton(
            f,
            text=_("Spindle"),
            image=Utils.icons["spinningtop"],
            command=self.spindleControl,
            compound=LEFT,
            indicatoron=False,
            variable=self.spindle,
            padx=1,
            pady=0,
        )
        tkExtra.Balloon.set(b, _("Start/Stop spindle (M3/M5)"))
        b.grid(row=row, column=col, pady=0, sticky=NSEW)
        self.addWidget(b)

        col += 1
        b = Scale(
            f,
            variable=self.spindleSpeed,
            command=self.spindleControl,
            showvalue=True,
            orient=HORIZONTAL,
            from_=Utils.config.get("CNC", "spindlemin"),
            to_=Utils.config.get("CNC", "spindlemax"),
        )
        tkExtra.Balloon.set(b, _("Set spindle RPM"))
        b.grid(row=row, column=col, sticky=EW, columnspan=3)
        self.addWidget(b)

        f.grid_columnconfigure(1, weight=1)

        # Coolant control

        self.coolant = BooleanVar()
        self.mist = BooleanVar()
        self.flood = BooleanVar()

        row += 1
        col = 0
        Label(f, text=_("Coolant:")).grid(row=row, column=col, sticky=E)
        col += 1

        coolantDisable = Checkbutton(
            f,
            text=_("OFF"),
            command=self.coolantOff,
            indicatoron=False,
            variable=self.coolant,
            padx=1,
            pady=0,
        )
        tkExtra.Balloon.set(coolantDisable, _("Stop cooling (M9)"))
        coolantDisable.grid(row=row, column=col, pady=0, sticky=NSEW)
        self.addWidget(coolantDisable)

        col += 1
        floodEnable = Checkbutton(
            f,
            text=_("Flood"),
            command=self.coolantFlood,
            indicatoron=False,
            variable=self.flood,
            padx=1,
            pady=0,
        )
        tkExtra.Balloon.set(floodEnable, _("Start flood (M8)"))
        floodEnable.grid(row=row, column=col, pady=0, sticky=NSEW)
        self.addWidget(floodEnable)

        col += 1
        mistEnable = Checkbutton(
            f,
            text=_("Mist"),
            command=self.coolantMist,
            indicatoron=False,
            variable=self.mist,
            padx=1,
            pady=0,
        )
        tkExtra.Balloon.set(mistEnable, _("Start mist (M7)"))
        mistEnable.grid(row=row, column=col, pady=0, sticky=NSEW)
        self.addWidget(mistEnable)
        f.grid_columnconfigure(1, weight=1)

    # ----------------------------------------------------------------------
    def overrideChange(self, event=None):
        n = self.overrideCombo.get()
        c = self.override.get()
        CNC.vars["_Ov" + n] = c
        CNC.vars["_OvChanged"] = True

    # ----------------------------------------------------------------------
    def resetOverride(self, event=None):
        self.override.set(100)
        self.overrideChange()

    # ----------------------------------------------------------------------
    def overrideComboChange(self):
        n = self.overrideCombo.get()
        if n == "Rapid":
            self.overrideScale.config(to_=100, resolution=25)
        else:
            self.overrideScale.config(to_=200, resolution=1)
        self.override.set(CNC.vars["_Ov" + n])

    # ----------------------------------------------------------------------
    def _gChange(self, value, dictionary):
        for k, v in dictionary.items():
            if v == value:
                self.sendGCode(k)
                return

    # ----------------------------------------------------------------------
    def distanceChange(self):
        if self._gUpdate:
            return
        self._gChange(self.distance.get(), DISTANCE_MODE)

    # ----------------------------------------------------------------------
    def unitsChange(self):
        if self._gUpdate:
            return
        self._gChange(self.units.get(), UNITS)

    # ----------------------------------------------------------------------
    def feedModeChange(self):
        if self._gUpdate:
            return
        self._gChange(self.feedMode.get(), FEED_MODE)

    # ----------------------------------------------------------------------
    def planeChange(self):
        if self._gUpdate:
            return
        self._gChange(self.plane.get(), PLANE)

    # ----------------------------------------------------------------------
    def setFeedRate(self, event=None):
        if self._gUpdate:
            return
        try:
            feed = float(self.feedRate.get())
            self.sendGCode(f"F{feed:g}")
            self.event_generate("<<CanvasFocus>>")
        except ValueError:
            pass

    # ----------------------------------------------------------------------
    def setTLO(self, event=None):
        try:
            tlo = float(self.tlo.get())
            self.app.mcontrol.setTLO(tlo)
            self.app.mcontrol.viewParameters()
            self.event_generate("<<CanvasFocus>>")
        except ValueError:
            pass

    # ----------------------------------------------------------------------
    def setTool(self, event=None):
        pass

    # ----------------------------------------------------------------------
    def spindleControl(self, event=None):
        if self._gUpdate:
            return
        # Avoid sending commands before unlocking
        if CNC.vars["state"] in (Sender.CONNECTED, Sender.NOT_CONNECTED):
            return
        if self.spindle.get():
            self.sendGCode("M3 S%d" % (self.spindleSpeed.get()))
        else:
            self.sendGCode("M5")

    # ----------------------------------------------------------------------
    def coolantMist(self, event=None):
        if self._gUpdate:
            return
        # Avoid sending commands before unlocking
        if CNC.vars["state"] in (Sender.CONNECTED, Sender.NOT_CONNECTED):
            self.mist.set(False)
            return
        self.coolant.set(False)
        self.mist.set(True)
        self.sendGCode("M7")

    # ----------------------------------------------------------------------
    def coolantFlood(self, event=None):
        if self._gUpdate:
            return
        # Avoid sending commands before unlocking
        if CNC.vars["state"] in (Sender.CONNECTED, Sender.NOT_CONNECTED):
            self.flood.set(False)
            return
        self.coolant.set(False)
        self.flood.set(True)
        self.sendGCode("M8")

    # ----------------------------------------------------------------------
    def coolantOff(self, event=None):
        if self._gUpdate:
            return
        # Avoid sending commands before unlocking
        if CNC.vars["state"] in (Sender.CONNECTED, Sender.NOT_CONNECTED):
            self.coolant.set(False)
            return
        self.flood.set(False)
        self.mist.set(False)
        self.coolant.set(True)
        self.sendGCode("M9")

    # ----------------------------------------------------------------------
    def updateG(self):
        global wcsvar
        self._gUpdate = True

        try:
            wcsvar.set(WCS.index(CNC.vars["WCS"]))
            self.feedRate.set(str(CNC.vars["feed"]))
            self.feedMode.set(FEED_MODE[CNC.vars["feedmode"]])
            self.spindle.set(CNC.vars["spindle"] == "M3")
            self.spindleSpeed.set(int(CNC.vars["rpm"]))
            self.toolEntry.set(CNC.vars["tool"])
            self.units.set(UNITS[CNC.vars["units"]])
            self.distance.set(DISTANCE_MODE[CNC.vars["distance"]])
            self.plane.set(PLANE[CNC.vars["plane"]])
            self.tlo.set(str(CNC.vars["TLO"]))
            self.g92.config(text=str(CNC.vars["G92"]))
        except KeyError:
            pass

        self._gUpdate = False

    # ----------------------------------------------------------------------
    def updateFeed(self):
        if self.feedRate.cget("state") == DISABLED:
            self.feedRate.config(state=NORMAL)
            self.feedRate.delete(0, END)
            self.feedRate.insert(0, CNC.vars["curfeed"])
            self.feedRate.config(state=DISABLED)

    # ----------------------------------------------------------------------
    def wcsChange(self):
        global wcsvar
        self.sendGCode(WCS[wcsvar.get()])
        self.app.mcontrol.viewState()


# =============================================================================
# Control Page
# =============================================================================
class ControlPage(CNCRibbon.Page):
    __doc__ = _("CNC communication and control")
    _name_ = N_("Control")
    _icon_ = "control"

    # ----------------------------------------------------------------------
    # Add a widget in the widgets list to enable disable during the run
    # ----------------------------------------------------------------------
    def register(self):
        global wcsvar
        wcsvar = IntVar()
        wcsvar.set(0)

        self._register(
            (ConnectionGroup, UserGroup, RunGroup),
            (DROFrame, abcDROFrame, ControlFrame, abcControlFrame, StateFrame),
        )
