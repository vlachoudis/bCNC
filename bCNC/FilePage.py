# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

import os
import sys
from tkinter import (
    YES,
    W,
    E,
    EW,
    NSEW,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BooleanVar,
    Checkbutton,
    Label,
    Menu,
)
import CNCRibbon
import Ribbon
import tkExtra
import Utils

from Helpers import N_

__author__ = "Vasilis Vlachoudis"
__email__ = "vvlachoudis@gmail.com"

try:
    from serial.tools.list_ports import comports
except Exception:
    print("Using fallback Utils.comports()!")
    from Utils import comports

BAUDS = [2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]

# =============================================================================
# Recent Menu button
# =============================================================================


class _RecentMenuButton(Ribbon.MenuButton):
    # ----------------------------------------------------------------------
    def createMenu(self):
        menu = Menu(self, tearoff=0, activebackground=Ribbon._ACTIVE_COLOR)
        for i in range(Utils._maxRecent):
            filename = Utils.getRecent(i)
            if filename is None:
                break
            path = os.path.dirname(filename)
            fn = os.path.basename(filename)
            menu.add_command(
                label="%d %s" % (i + 1, fn),
                compound=LEFT,
                image=Utils.icons["new"],
                accelerator=path,  # Show as accelerator in order to be aligned
                command=lambda s=self, i=i: s.event_generate(
                    "<<Recent%d>>" % (i)),
            )
        if i == 0:  # no entry
            self.event_generate("<<Open>>")
            return None
        return menu


# =============================================================================
# File Group
# =============================================================================
class FileGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("File"), app)
        self.grid3rows()

        # ---
        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<New>>",
            image=Utils.icons["new32"],
            text=_("New"),
            compound=TOP,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("New gcode/dxf file"))
        self.addWidget(b)

        # ---
        col, row = 1, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Open>>",
            image=Utils.icons["open32"],
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Open existing gcode/dxf file [Ctrl-O]"))
        self.addWidget(b)

        col, row = 1, 2
        b = _RecentMenuButton(
            self.frame,
            None,
            text=_("Open"),
            image=Utils.icons["triangle_down"],
            compound=RIGHT,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Open recent file"))
        self.addWidget(b)

        # ---
        col, row = 2, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Import>>",
            image=Utils.icons["import32"],
            text=_("Import"),
            compound=TOP,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Import gcode/dxf file"))
        self.addWidget(b)

        # ---
        col, row = 3, 0
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<Save>>",
            image=Utils.icons["save32"],
            command=app.save,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, rowspan=2, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Save gcode/dxf file [Ctrl-S]"))
        self.addWidget(b)

        col, row = 3, 2
        b = Ribbon.LabelButton(
            self.frame,
            self,
            "<<SaveAs>>",
            text=_("Save"),
            image=Utils.icons["triangle_down"],
            compound=RIGHT,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Save gcode/dxf AS"))
        self.addWidget(b)


# =============================================================================
# Options Group
# =============================================================================
class OptionsGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Options"), app)
        self.grid3rows()

        # ===
        col, row = 1, 0
        b = Ribbon.LabelButton(
            self.frame,
            text=_("Report"),
            image=Utils.icons["debug"],
            compound=LEFT,
            command=Utils.ReportDialog.sendErrorReport,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
        tkExtra.Balloon.set(b, _("Send Error Report"))

        # ---
        col, row = 1, 1
        b = Ribbon.LabelButton(
            self.frame,
            text=_("Updates"),
            image=Utils.icons["global"],
            compound=LEFT,
            command=self.app.checkUpdates,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
        tkExtra.Balloon.set(b, _("Check Updates"))

        col, row = 1, 2
        b = Ribbon.LabelButton(
            self.frame,
            text=_("About"),
            image=Utils.icons["about"],
            compound=LEFT,
            command=self.app.about,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=EW)
        tkExtra.Balloon.set(b, _("About the program"))


# =============================================================================
# Pendant Group
# =============================================================================
class PendantGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Pendant"), app)
        self.grid3rows()

        col, row = 0, 0
        b = Ribbon.LabelButton(
            self.frame,
            text=_("Start"),
            image=Utils.icons["start_pendant"],
            compound=LEFT,
            anchor=W,
            command=app.startPendant,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Start pendant"))

        row += 1
        b = Ribbon.LabelButton(
            self.frame,
            text=_("Stop"),
            image=Utils.icons["stop_pendant"],
            compound=LEFT,
            anchor=W,
            command=app.stopPendant,
            background=Ribbon._BACKGROUND,
        )
        b.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(b, _("Stop pendant"))


# =============================================================================
# Close Group
# =============================================================================
class CloseGroup(CNCRibbon.ButtonGroup):
    def __init__(self, master, app):
        CNCRibbon.ButtonGroup.__init__(self, master, N_("Close"), app)

        # ---
        b = Ribbon.LabelButton(
            self.frame,
            text=_("Exit"),
            image=Utils.icons["exit32"],
            compound=TOP,
            command=app.quit,
            anchor=W,
            background=Ribbon._BACKGROUND,
        )
        b.pack(fill=BOTH, expand=YES)
        tkExtra.Balloon.set(b, _("Close program [Ctrl-Q]"))


# =============================================================================
# Serial Frame
# =============================================================================
class SerialFrame(CNCRibbon.PageLabelFrame):
    def __init__(self, master, app):
        CNCRibbon.PageLabelFrame.__init__(
            self, master, "Serial", _("Serial"), app)
        self.autostart = BooleanVar()

        # ---
        col, row = 0, 0
        b = Label(self, text=_("Port:"))
        b.grid(row=row, column=col, sticky=E)
        self.addWidget(b)

        self.portCombo = tkExtra.Combobox(
            self,
            False,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            width=16,
            command=self.comportClean,
        )
        self.portCombo.grid(row=row, column=col + 1, sticky=EW)
        tkExtra.Balloon.set(
            self.portCombo, _("Select (or manual enter) port to connect")
        )
        self.portCombo.set(Utils.getStr("Connection", "port"))
        self.addWidget(self.portCombo)

        self.comportRefresh()

        # ---
        row += 1
        b = Label(self, text=_("Baud:"))
        b.grid(row=row, column=col, sticky=E)

        self.baudCombo = tkExtra.Combobox(
            self, True, background=tkExtra.GLOBAL_CONTROL_BACKGROUND
        )
        self.baudCombo.grid(row=row, column=col + 1, sticky=EW)
        tkExtra.Balloon.set(self.baudCombo, _("Select connection baud rate"))
        self.baudCombo.fill(BAUDS)
        self.baudCombo.set(Utils.getStr("Connection", "baud", "115200"))
        self.addWidget(self.baudCombo)

        # ---
        row += 1
        b = Label(self, text=_("Controller:"))
        b.grid(row=row, column=col, sticky=E)

        self.ctrlCombo = tkExtra.Combobox(
            self,
            True,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
            command=self.ctrlChange,
        )
        self.ctrlCombo.grid(row=row, column=col + 1, sticky=EW)
        tkExtra.Balloon.set(self.ctrlCombo, _("Select controller board"))
        self.ctrlCombo.fill(self.app.controllerList())
        self.ctrlCombo.set(app.controller)
        self.addWidget(self.ctrlCombo)

        # ---
        row += 1
        b = Checkbutton(self, text=_("Connect on startup"),
                        variable=self.autostart)
        b.grid(row=row, column=col, columnspan=2, sticky=W)
        tkExtra.Balloon.set(
            b, _("Connect to serial on startup of the program"))
        self.autostart.set(Utils.getBool("Connection", "openserial"))
        self.addWidget(b)

        # ---
        col += 2
        self.comrefBtn = Ribbon.LabelButton(
            self,
            image=Utils.icons["refresh"],
            text=_("Refresh"),
            compound=TOP,
            command=lambda s=self: s.comportRefresh(True),
            background=Ribbon._BACKGROUND,
        )
        self.comrefBtn.grid(row=row, column=col, padx=0, pady=0, sticky=NSEW)
        tkExtra.Balloon.set(self.comrefBtn, _("Refresh list of serial ports"))

        # ---
        row = 0

        self.connectBtn = Ribbon.LabelButton(
            self,
            image=Utils.icons["serial48"],
            text=_("Open"),
            compound=TOP,
            command=lambda s=self: s.event_generate("<<Connect>>"),
            background=Ribbon._BACKGROUND,
        )
        self.connectBtn.grid(
            row=row, column=col, rowspan=3, padx=0, pady=0, sticky=NSEW
        )
        tkExtra.Balloon.set(self.connectBtn, _("Open/Close serial port"))
        self.grid_columnconfigure(1, weight=1)

    # -----------------------------------------------------------------------
    def ctrlChange(self):
        self.app.controllerSet(self.ctrlCombo.get())

    # -----------------------------------------------------------------------
    def comportClean(self, event=None):
        clean = self.portCombo.get().split("\t")[0]
        if self.portCombo.get() != clean:
            print("comport fix")
            self.portCombo.set(clean)

    # -----------------------------------------------------------------------
    def comportsGet(self):
        try:
            return comports(include_links=True)
        except TypeError:
            print("Using old style comports()!")
            return comports()

    def comportRefresh(self, dbg=False):
        # Detect devices
        hwgrep = []
        for i in self.comportsGet():
            if dbg:
                # Print list to console if requested
                comport = ""
                for j in i:
                    comport += j + "\t"
                print(comport)
            for hw in i[2].split(" "):
                hwgrep += ["hwgrep://" + hw + "\t" + i[1]]

        # Populate combobox
        devices = sorted(x[0] + "\t" + x[1] for x in self.comportsGet())
        devices += [""]
        devices += sorted(set(hwgrep))
        devices += [""]
        # Pyserial raw spy currently broken in python3
        # TODO: search for python3 replacement for raw spy
        if sys.version_info[0] != 3:
            devices += sorted(
                "spy://" + x[0] + "?raw&color" + "\t(Debug) " + x[1]
                for x in self.comportsGet()
            )
        else:
            devices += sorted(
                "spy://" + x[0] + "?color" + "\t(Debug) " + x[1]
                for x in self.comportsGet()
            )
        devices += ["", "socket://localhost:23", "rfc2217://localhost:2217"]

        # Clean neighbour duplicates
        devices_clean = []
        devprev = ""
        for i in devices:
            if i.split("\t")[0] != devprev:
                devices_clean += [i]
            devprev = i.split("\t")[0]

        self.portCombo.fill(devices_clean)

    # -----------------------------------------------------------------------
    def saveConfig(self):
        # Connection
        Utils.setStr("Connection", "controller", self.app.controller)
        Utils.setStr("Connection", "port", self.portCombo.get().split("\t")[0])
        Utils.setStr("Connection", "baud", self.baudCombo.get())
        Utils.setBool("Connection", "openserial", self.autostart.get())


# =============================================================================
# File Page
# =============================================================================
class FilePage(CNCRibbon.Page):
    __doc__ = _("File I/O and configuration")
    _name_ = N_("File")
    _icon_ = "new"

    # ----------------------------------------------------------------------
    # Add a widget in the widgets list to enable disable during the run
    # ----------------------------------------------------------------------
    def register(self):
        self._register(
            (FileGroup, PendantGroup, OptionsGroup, CloseGroup), (SerialFrame,)
        )
