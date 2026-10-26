#!/usr/bin/env python3
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

import contextlib
import os
import socket
import sys
import time
import traceback
import webbrowser
from datetime import datetime
import tkinter
from queue import Empty
from tkinter import (
    TclError,
    NO,
    YES,
    TRUE,
    W,
    E,
    NW,
    NE,
    EW,
    X,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BOTTOM,
    RAISED,
    SUNKEN,
    HORIZONTAL,
    END,
    NORMAL,
    DISABLED,
    Tk,
    Toplevel,
    Button,
    Entry,
    Frame,
    Label,
    Listbox,
    Text,
    PhotoImage,
    Spinbox,
    LabelFrame,
    PanedWindow,
    messagebox,
)

try:
    import serial
except ImportError:
    serial = None
    print("testing mode, could not import serial")

import Utils

import bFileDialog
import CNCCanvas

import rexx
import Updates
import tkDialogs
import tkExtra
# Load configuration before anything else
# and if needed replace the  translate function _()
# before any string is initialized
from CNC import CNC, WAIT
from GCode import GCode
import Ribbon
import Pendant
from CNCRibbon import Page
from ControlPage import ControlPage
from EditorPage import EditorPage
from FilePage import FilePage
from ProbePage import ProbePage
from Sender import NOT_CONNECTED, STATECOLOR, STATECOLORDEF, Sender
from TerminalPage import TerminalPage
from ToolsPage import Tools, ToolsPage

Utils.loadConfiguration()

__version__ = Utils.__version__
__date__ = Utils.__date__
__author__ = Utils.__author__
__email__ = Utils.__email__

if not (sys.version_info.major == 3 and sys.version_info.minor >= 8):
    print("ERROR: Python3.8 or newer is required to run bCNC!!")
    exit(1)

__platform_fingerprint__ = "".join([
    f"({sys.platform} ",
    f"py{sys.version_info.major}.",
    f"{sys.version_info.minor}.",
    f"{sys.version_info.micro})"
])

_openserial = True  # override ini parameters
_device = None
_baud = None

MONITOR_AFTER = 200  # ms
DRAW_AFTER = 300  # ms

RX_BUFFER_SIZE = 128

MAX_HISTORY = 500

FILETYPES = [
    (
        _("All accepted"),
        (
            "*.ngc",
            "*.cnc",
            "*.nc",
            "*.tap",
            "*.gcode",
            "*.dxf",
            "*.probe",
            "*.orient",
            "*.stl",
            "*.svg",
        ),
    ),
    (_("G-Code"), ("*.ngc", "*.cnc", "*.nc", "*.tap", "*.gcode")),
    (_("G-Code clean"), ("*.txt")),
    ("DXF", "*.dxf"),
    ("SVG", "*.svg"),
    (_("Probe"), ("*.probe", "*.xyz")),
    (_("Orient"), "*.orient"),
    ("STL", "*.stl"),
    (_("All"), "*"),
]

geometry = None


# =============================================================================
# Main Application window
# =============================================================================
class Application(Tk, Sender):
    def __init__(self, **kw):
        Tk.__init__(self, **kw)
        Sender.__init__(self)

        Utils.loadIcons()
        tkinter.CallWrapper = Utils.CallWrapper
        tkExtra.bindClasses(self)

        photo = PhotoImage(file=f"{Utils.prgpath}/bCNC.png")
        self.iconphoto(True, photo)
        self.title(f"{Utils.__prg__} {__version__} {__platform_fingerprint__}")
        self.widgets = []

        # Global variables
        self.tools = Tools(self.gcode)
        self.registerCommands()
        self.controller = None
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

        self.statusz = Label(
            frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10
        )
        self.statusz.pack(side=RIGHT)
        self.statusy = Label(
            frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10
        )
        self.statusy.pack(side=RIGHT)
        self.statusx = Label(
            frame, foreground="DarkRed", relief=SUNKEN, anchor=W, width=10
        )
        self.statusx.pack(side=RIGHT)

        # Buffer bar
        self.bufferbar = tkExtra.ProgressBar(
            frame, height=20, width=40, relief=SUNKEN)
        self.bufferbar.pack(side=RIGHT, expand=NO)
        self.bufferbar.setLimits(0, 100)
        tkExtra.Balloon.set(self.bufferbar, _("Controller buffer fill"))

        # --- Left side ---
        frame = Frame(self.paned)
        self.paned.add(frame)  # , minsize=340)

        pageframe = Frame(frame)
        pageframe.pack(side=TOP, expand=YES, fill=BOTH)
        self.ribbon.setPageFrame(pageframe)

        # Command bar
        f = Frame(frame)
        f.pack(side=BOTTOM, fill=X)
        self.cmdlabel = Label(f, text=_("Command:"))
        self.cmdlabel.pack(side=LEFT)
        self.command = Entry(f, relief=SUNKEN, background="White")  # !!!
        self.command.pack(side=RIGHT, fill=X, expand=YES)
        self.command.bind("<Return>", self.cmdExecute)
        self.command.bind("<Up>", self.commandHistoryUp)
        self.command.bind("<Down>", self.commandHistoryDown)
        self.command.bind("<FocusIn>", self.commandFocusIn)
        self.command.bind("<FocusOut>", self.commandFocusOut)
        self.command.bind("<Key>", self.commandKey)
        self.command.bind("<Control-Key-z>", self.undo)
        self.command.bind("<Control-Key-Z>", self.redo)
        self.command.bind("<Control-Key-y>", self.redo)
        tkExtra.Balloon.set(
            self.command,
            _(
                "MDI Command line: Accept g-code commands or macro "
                "commands (RESET/HOME...) or editor commands "
                "(move,inkscape, round...) [Space or Ctrl-Space]"
            ),
        )
        self.widgets.append(self.command)

        # --- Right side ---
        frame = Frame(self.paned)
        self.paned.add(frame)

        self.canvasContainer = Frame(frame)
        self.canvasContainer.pack(side='top', expand=True, fill='both')

        # --- 3D Canvas ---
        self.canvasFrame = CNCCanvas.CanvasFrame(self.canvasContainer, self)
        self.canvasFrame.pack(fill='both', expand=True)
        
        self.canvas = self.canvasFrame.canvas

        # fist create Pages
        self.pages = {}
        for cls in (
            ControlPage,
            EditorPage,
            FilePage,
            ProbePage,
            TerminalPage,
            ToolsPage,
        ):
            page = cls(self.ribbon, self)
            self.pages[page.name] = page

        # then add their properties (in separate loop)
        errors = []
        for name, page in self.pages.items():
            for n in Utils.getStr(Utils.__prg__,
                                  f"{page.name}.ribbon").split():
                try:
                    page.addRibbonGroup(n)
                except KeyError:
                    errors.append(n)

            for n in Utils.getStr(Utils.__prg__, f"{page.name}.page").split():
                last = n[-1]
                if ((n == "abcDRO" or n == "abcControl")
                        and CNC.enable6axisopt is False):
                    sys.stdout.write("Not Loading 6 axis displays\n")

                else:
                    try:
                        if last == "*":
                            page.addPageFrame(n[:-1], fill=BOTH, expand=TRUE)
                        else:
                            page.addPageFrame(n)
                    except KeyError:
                        errors.append(n)

        if errors:
            messagebox.showwarning(
                "bCNC configuration",
                f"The following pages \"{' '.join(errors)}\" are found in "
                "your bCNC config file, which are either spelled wrongly or "
                "no longer exist in bCNC",
                parent=self,
            )

        # remember the editor list widget
        self.dro = Page.frames["DRO"]
        self.abcdro = Page.frames["abcDRO"]
        self.gstate = Page.frames["State"]
        self.control = Page.frames["Control"]
        self.abccontrol = Page.frames["abcControl"]
        self.editor = Page.frames["Editor"].editor
        self.terminal = Page.frames["Terminal"].terminal
        self.buffer = Page.frames["Terminal"].buffer

        # XXX FIXME Do we need it or I can takes from Page every time?
        self.autolevel = Page.frames["Probe:Autolevel"]

        # Left side
        for name in Utils.getStr(Utils.__prg__, "ribbon").split():
            last = name[-1]
            if last == ">":
                name = name[:-1]
                side = RIGHT
            else:
                side = LEFT
            self.ribbon.addPage(self.pages[name], side)

        # Restore last page
        # Select "Probe:Probe" tab to show the dialogs!
        self.pages["Probe"].tabChange()
        self.ribbon.changePage(Utils.getStr(Utils.__prg__, "page", "File"))

        probe = Page.frames["Probe:Probe"]
        tkExtra.bindEventData(
            self, "<<OrientSelect>>", lambda e, f=probe: f.selectMarker(
                int(e.data))
        )
        tkExtra.bindEventData(
            self,
            "<<OrientChange>>",
            lambda e, s=self: s.canvas.orientChange(int(e.data)),
        )
        self.bind("<<OrientUpdate>>", probe.orientUpdate)

        # Global bindings
        self.bind("<<Undo>>", self.undo)
        self.bind("<<Redo>>", self.redo)
        self.bind("<<Copy>>", self.copy)
        self.bind("<<Cut>>", self.cut)
        self.bind("<<Paste>>", self.paste)

        self.bind("<<Connect>>", self.openClose)

        self.bind("<<New>>", self.newFile)
        self.bind("<<Open>>", self.loadDialog)
        self.bind("<<Import>>", lambda x, s=self: s.importFile())
        self.bind("<<Save>>", self.saveAll)
        self.bind("<<SaveAs>>", self.saveDialog)
        self.bind("<<Reload>>", self.reload)

        self.bind("<<Recent0>>", self._loadRecent0)
        self.bind("<<Recent1>>", self._loadRecent1)
        self.bind("<<Recent2>>", self._loadRecent2)
        self.bind("<<Recent3>>", self._loadRecent3)
        self.bind("<<Recent4>>", self._loadRecent4)
        self.bind("<<Recent5>>", self._loadRecent5)
        self.bind("<<Recent6>>", self._loadRecent6)
        self.bind("<<Recent7>>", self._loadRecent7)
        self.bind("<<Recent8>>", self._loadRecent8)
        self.bind("<<Recent9>>", self._loadRecent9)

        self.bind("<<TerminalClear>>", Page.frames["Terminal"].clear)
        self.bind("<<AlarmClear>>", self.alarmClear)
        self.bind("<<Help>>", self.help)
        # Do not send the event otherwise it will skip the feedHold/resume
        self.bind("<<FeedHold>>", lambda e, s=self: s.feedHold())
        self.bind("<<Resume>>", lambda e, s=self: s.resume())
        self.bind("<<Run>>", lambda e, s=self: s.run())
        self.bind("<<Stop>>", self.stopRun)
        self.bind("<<Pause>>", self.pause)

        tkExtra.bindEventData(self, "<<Status>>", self.updateStatus)
        tkExtra.bindEventData(self, "<<Coords>>", self.updateCanvasCoords)

        # Editor bindings
        self.bind("<<Add>>", self.editor.insertItem)
        self.bind("<<AddBlock>>", self.editor.insertBlock)
        self.bind("<<AddLine>>", self.editor.insertLine)
        self.bind("<<Clone>>", self.editor.clone)
        self.canvas.bind("<Control-Key-Prior>", self.editor.orderUp)
        self.canvas.bind("<Control-Key-Next>", self.editor.orderDown)
        self.canvas.bind("<Control-Key-d>", self.editor.clone)
        self.canvas.bind("<Control-Key-c>", self.copy)
        self.canvas.bind("<Control-Key-x>", self.cut)
        self.canvas.bind("<Control-Key-v>", self.paste)
        self.bind("<<Delete>>", self.editor.deleteBlock)
        self.canvas.bind("<Delete>", self.editor.deleteBlock)
        self.canvas.bind("<BackSpace>", self.editor.deleteBlock)
        with contextlib.suppress(Exception):
            self.canvas.bind("<KP_Delete>", self.editor.deleteBlock)
        self.bind("<<Invert>>", self.editor.invertBlocks)
        self.bind("<<Expand>>", self.editor.toggleExpand)
        self.bind("<<EnableToggle>>", self.editor.toggleEnable)
        self.bind("<<Enable>>", self.editor.enable)
        self.bind("<<Disable>>", self.editor.disable)
        self.bind("<<ChangeColor>>", self.editor.changeColor)
        self.bind("<<Comment>>", self.editor.commentRow)
        self.bind("<<Join>>", self.editor.joinBlocks)
        self.bind("<<Split>>", self.editor.splitBlocks)

        # Canvas X-bindings
        self.bind("<<ViewChange>>", self.viewChange)
        self.bind("<<AddMarker>>", self.canvas.setActionAddMarker)
        self.bind("<<MoveGantry>>", self.canvas.setActionGantry)
        self.bind("<<SetWPOS>>", self.canvas.setActionWPOS)

        frame = Page.frames["Probe:Tool"]
        self.bind("<<ToolCalibrate>>", frame.calibrate)
        self.bind("<<ToolChange>>", frame.change)

        self.bind("<<AutolevelMargins>>", self.autolevel.getMargins)
        self.bind("<<AutolevelZero>>", self.autolevel.setZero)
        self.bind("<<AutolevelClear>>", self.autolevel.clear)
        self.bind("<<AutolevelScan>>", self.autolevel.scan)
        self.bind("<<AutolevelScanMargins>>", self.autolevel.scanMargins)

        self.bind("<<CameraOn>>", self.canvas.cameraOn)
        self.bind("<<CameraOff>>", self.canvas.cameraOff)

        self.bind("<<CanvasFocus>>", self.canvasFocus)
        self.bind("<<Draw>>", self.draw)
        self.bind("<<DrawProbe>>", lambda e,
                  c=self.canvasFrame: c.drawProbe(True))
        self.bind("<<DrawOrient>>", self.canvas.drawOrient)

        self.bind("<<ListboxSelect>>", self.selectionChange)
        self.bind("<<Modified>>", self.drawAfter)

        self.bind("<Control-Key-a>", self.selectAll)
        self.bind("<Control-Key-A>", self.unselectAll)
        self.bind("<Escape>", self.unselectAll)
        self.bind("<Control-Key-i>", self.selectInvert)

        self.bind("<<SelectAll>>", self.selectAll)
        self.bind("<<SelectNone>>", self.unselectAll)
        self.bind("<<SelectInvert>>", self.selectInvert)
        self.bind("<<SelectLayer>>", self.selectLayer)

        self.bind("<Control-Key-e>", self.editor.toggleExpand)
        self.bind("<Control-Key-n>", self.showInfo)
        self.bind("<<ShowInfo>>", self.showInfo)
        self.bind("<Control-Key-l>", self.editor.toggleEnable)
        self.bind("<Control-Key-q>", self.quit)
        self.bind("<Control-Key-o>", self.loadDialog)
        self.bind("<Control-Key-r>", self.drawAfter)
        self.bind("<Control-Key-s>", self.saveAll)
        self.bind("<Control-Key-y>", self.redo)
        self.bind("<Control-Key-z>", self.undo)
        self.bind("<Control-Key-Z>", self.redo)
        self.canvas.bind("<Key-space>", self.commandFocus)
        self.bind("<Control-Key-space>", self.commandFocus)
        self.bind("<<CommandFocus>>", self.commandFocus)

        tools = self.pages["CAM"]
        self.bind("<<ToolAdd>>", tools.add)
        self.bind("<<ToolDelete>>", tools.delete)
        self.bind("<<ToolClone>>", tools.clone)
        self.bind("<<ToolRename>>", tools.rename)

        self.bind("<Prior>", self.control.moveZup)
        self.bind("<Next>", self.control.moveZdown)

        if self._swapKeyboard == 1:
            self.bind("<Right>", self.control.moveYup)
            self.bind("<Left>", self.control.moveYdown)
            self.bind("<Up>", self.control.moveXdown)
            self.bind("<Down>", self.control.moveXup)
            self.bind(".", self.abccontrol.moveAup)
            self.bind(",", self.abccontrol.moveAdown)
        elif self._swapKeyboard == -1:
            self.bind("<Right>", self.control.moveYdown)
            self.bind("<Left>", self.control.moveYup)
            self.bind("<Up>", self.control.moveXup)
            self.bind("<Down>", self.control.moveXdown)
            self.bind(",", self.abccontrol.moveAup)
            self.bind(".", self.abccontrol.moveAdown)
        else:
            self.bind("<Right>", self.control.moveXup)
            self.bind("<Left>", self.control.moveXdown)
            self.bind("<Up>", self.control.moveYup)
            self.bind("<Down>", self.control.moveYdown)
            self.bind(".", self.abccontrol.moveAup)
            self.bind(",", self.abccontrol.moveAdown)

        try:
            self.bind("<KP_Prior>", self.control.moveZup)
            self.bind("<KP_Next>", self.control.moveZdown)

            if self._swapKeyboard == 1:
                self.bind("<KP_Right>", self.control.moveYup)
                self.bind("<KP_Left>", self.control.moveYdown)
                self.bind("<KP_Up>", self.control.moveXdown)
                self.bind("<KP_Down>", self.control.moveXup)
            elif self._swapKeyboard == -1:
                self.bind("<KP_Right>", self.control.moveYdown)
                self.bind("<KP_Left>", self.control.moveYup)
                self.bind("<KP_Up>", self.control.moveXup)
                self.bind("<KP_Down>", self.control.moveXdown)
            else:
                self.bind("<KP_Right>", self.control.moveXup)
                self.bind("<KP_Left>", self.control.moveXdown)
                self.bind("<KP_Up>", self.control.moveYup)
                self.bind("<KP_Down>", self.control.moveYdown)
        except TclError:
            pass

        self.bind("<Key-plus>", self.control.incStep)
        self.bind("<Key-equal>", self.control.incStep)
        self.bind("<KP_Add>", self.control.incStep)
        self.bind("<Key-minus>", self.control.decStep)
        self.bind("<Key-underscore>", self.control.decStep)
        self.bind("<KP_Subtract>", self.control.decStep)

        self.bind("<Key-asterisk>", self.control.mulStep)
        self.bind("<KP_Multiply>", self.control.mulStep)
        self.bind("<Key-slash>", self.control.divStep)
        self.bind("<KP_Divide>", self.control.divStep)

        self.bind("<Key-1>", self.control.setStep1)
        self.bind("<Key-2>", self.control.setStep2)
        self.bind("<Key-3>", self.control.setStep3)

        self.bind("<Key-exclam>", self.feedHold)
        self.bind("<Key-asciitilde>", self.resume)

        for x in self.widgets:
            if isinstance(x, Entry):
                x.bind("<Escape>", self.canvasFocus)

        self.bind("<FocusIn>", self.focusIn)
        self.protocol("WM_DELETE_WINDOW", self.quit)

        self.canvas.focus_set()

        # Fill basic global variables
        CNC.vars["state"] = NOT_CONNECTED
        CNC.vars["color"] = STATECOLOR[NOT_CONNECTED]
        self._pendantFileUploaded = None
        self._drawAfter = None  # after handle for modification
        self._inFocus = False
        # END - insertCount lines where ok was applied to for $xxx commands
        self._insertCount = (0)
        self._selectI = 0
        self.lastProcessedPath = 0
        self.monitorSerial()
        self.canvasFrame.toggleDrawFlag()

        self.paned.sash_place(0, Utils.getInt(Utils.__prg__, "sash", 340), 0)

        # Auto start pendant and serial
        if Utils.getBool("Connection", "pendant"):
            self.startPendant(False)

        if _openserial and Utils.getBool("Connection", "openserial"):
            self.openClose()

        # Filedialog Load history
        for i in range(Utils._maxRecent):
            filename = Utils.getRecent(i)
            if filename is None:
                break
            bFileDialog.append2History(os.path.dirname(filename))

    # -----------------------------------------------------------------------
    def setStatus(self, msg, force_update=False):
        self.statusbar.configText(text=msg, fill="DarkBlue")
        if force_update:
            self.statusbar.update_idletasks()
            self.bufferbar.update_idletasks()

    # -----------------------------------------------------------------------
    # Set a status message from an event
    # -----------------------------------------------------------------------
    def updateStatus(self, event):
        self.setStatus(_(event.data))

    # -----------------------------------------------------------------------
    # Show popup dialog asking for value entry, useful in g-code scripts
    # -----------------------------------------------------------------------
    def entry(
        self,
        message="Enter value",
        title="",
        input_="",
        type_="str",
        from_=None,
        to_=None,
    ):
        d = tkDialogs.InputDialog(
            self, title, message, input, type_, from_, to_)
        v = d.show()

        if isinstance(v, (str, bytes)):
            v = v.strip()
        print("entered " + str(type(v)) + ": " + str(v))
        return v

    # -----------------------------------------------------------------------
    # Update canvas coordinates
    # -----------------------------------------------------------------------
    def updateCanvasCoords(self, event):
        x, y, z = event.data.split()
        self.statusx["text"] = "X: " + x
        self.statusy["text"] = "Y: " + y
        self.statusz["text"] = "Z: " + z

    # ----------------------------------------------------------------------
    # Accept the user key if not editing any text
    # ----------------------------------------------------------------------
    def acceptKey(self, skipRun=False):
        if not skipRun and self.running:
            return False
        focus = self.focus_get()
        if (
            isinstance(focus, Entry)
            or isinstance(focus, Spinbox)
            or isinstance(focus, Listbox)
            or isinstance(focus, Text)
        ):
            return False
        return True

    # -----------------------------------------------------------------------
    def quit(self, event=None):
        if self.running and self._quit < 1:
            messagebox.showinfo(
                _("Running"),
                _("CNC is currently running, please stop it before."),
                parent=self,
            )
            self._quit += 1
            return
        del self.widgets[:]

        if self.fileModified():
            return

        self.canvas.cameraOff()
        Sender.quit(self)
        self.saveConfig()
        self.destroy()
        if Utils.errors and Utils._errorReport:
            Utils.ReportDialog.sendErrorReport()

    # ---------------------------------------------------------------------
    def configWidgets(self, var, value):
        for w in self.widgets:
            if isinstance(w, tuple):
                try:
                    w[0].entryconfig(w[1], state=value)
                except TclError:
                    pass
            elif isinstance(w, tkExtra.Combobox):
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
        self.configWidgets("state", NORMAL)
        self.statusbar.clear()
        self.statusbar.config(background="LightGray")
        self.bufferbar.clear()
        self.bufferbar.config(background="LightGray")
        self.bufferbar.setText("")

    # ---------------------------------------------------------------------
    def disable(self):
        self.configWidgets("state", DISABLED)

    # ----------------------------------------------------------------------
    # Check for updates
    # ----------------------------------------------------------------------
    def checkUpdates(self):
        # Find bCNC version
        Updates.CheckUpdateDialog(self, __version__)

    # ----------------------------------------------------------------------
    # Show the error message, if no serial is present
    # ----------------------------------------------------------------------
    def showSerialError(self):
        messagebox.showerror(
            _("python serial missing"),
            _(
                "ERROR: Please install the python pyserial module\n"
                "Windows:\n\tC:\\PythonXX\\Scripts\\easy_install pyserial\n"
                "Mac:\tpip install pyserial\n"
                "Linux:\tsudo apt-get install python-serial\n"
                "\tor yum install python-serial\n"
                "\tor dnf install python-pyserial"
            ),
            parent=self,
        )

    # -----------------------------------------------------------------------
    def loadShortcuts(self):
        for name, value in Utils.config.items("Shortcut"):
            # Convert to uppercase
            key = name.title()
            self.unbind(f"<{key}>")  # unbind any possible old value
            if value:
                self.bind(f"<{key}>", lambda e, s=self, c=value: s.execute(c))

    # -----------------------------------------------------------------------
    def showUserFile(self):
        webbrowser.open(Utils.iniUser)
        # os.startfile(Utils.iniUser)

    # -----------------------------------------------------------------------
    def loadConfig(self):
        global geometry

        if geometry is None:
            geometry = "x".join([
                f"{Utils.getInt(Utils.__prg__, 'width', 900)}",
                f"{Utils.getInt(Utils.__prg__, 'height', 650)}"
            ])
        with contextlib.suppress(Exception):
            self.geometry(geometry)

        # restore windowsState
        with contextlib.suppress(Exception):
            self.wm_state(Utils.getStr(Utils.__prg__, "windowstate", "normal"))

        self._swapKeyboard = Utils.getInt("Control", "swap", 0)

        self._onStart = Utils.getStr("Events", "onstart", "")
        self._onStop = Utils.getStr("Events", "onstop", "")

        tkExtra.Balloon.font = Utils.getFont("balloon", tkExtra.Balloon.font)

        Ribbon._FONT = Utils.getFont("ribbon.label", Ribbon._FONT)
        Ribbon._TABFONT = Utils.getFont("ribbon.tab", Ribbon._TABFONT)

        Ribbon._ACTIVE_COLOR = Utils.getStr(
            "Color", "ribbon.active", Ribbon._ACTIVE_COLOR
        )
        Ribbon._LABEL_SELECT_COLOR = Utils.getStr(
            "Color", "ribbon.select", Ribbon._LABEL_SELECT_COLOR
        )

        self.tools.loadConfig()
        Sender.loadConfig(self)
        self.loadShortcuts()

    # -----------------------------------------------------------------------
    def saveConfig(self):
        # Program
        Utils.setInt(Utils.__prg__, "width", str(self.winfo_width()))
        Utils.setInt(Utils.__prg__, "height", str(self.winfo_height()))
        Utils.setInt(Utils.__prg__, "sash", str(self.paned.sash_coord(0)[0]))

        # save windowState (do not persist minimized, or next launch stays hidden)
        state = str(self.wm_state())
        if state in ("iconic", "withdrawn"):
            state = "normal"
        Utils.setStr(Utils.__prg__, "windowstate", state)
        Utils.setStr(Utils.__prg__, "page", str(
            self.ribbon.getActivePage().name))

        # Connection
        Page.saveConfig()
        Sender.saveConfig(self)
        self.tools.saveConfig()
        self.canvasFrame.saveConfig()

    # -----------------------------------------------------------------------
    def loadHistory(self):
        try:
            f = open(Utils.hisFile)
        except Exception:
            return
        self.history = [x.strip() for x in f]
        self._historySearch = None
        f.close()

    # -----------------------------------------------------------------------
    def saveHistory(self):
        try:
            f = open(Utils.hisFile, "w")
        except Exception:
            return
        f.write("\n".join(self.history))
        f.close()

    # -----------------------------------------------------------------------
    def cut(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.editor.cut()
            return "break"

    # -----------------------------------------------------------------------
    def copy(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.editor.copy()
            return "break"

    # -----------------------------------------------------------------------
    def paste(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.editor.paste()
            return "break"

    # -----------------------------------------------------------------------
    def undo(self, event=None):
        if not self.running and self.gcode.canUndo():
            self.gcode.undo()
            self.editor.fill()
            self.drawAfter()
        return "break"

    # -----------------------------------------------------------------------
    def redo(self, event=None):
        if not self.running and self.gcode.canRedo():
            self.gcode.redo()
            self.editor.fill()
            self.drawAfter()
        return "break"

    # -----------------------------------------------------------------------
    def addUndo(self, undoinfo):
        self.gcode.addUndo(undoinfo)

    # -----------------------------------------------------------------------
    def about(self, event=None, timer=None):
        toplevel = Toplevel(self)
        toplevel.transient(self)
        toplevel.title(_("About {} v{}").format(Utils.__prg__, __version__))

        bg = "#707070"
        fg = "#ffffff"

        font2 = "Helvetica -12"
        font3 = "Helvetica -10"

        frame = Frame(toplevel, borderwidth=2, relief=SUNKEN, background=bg)
        frame.pack(side=TOP, expand=TRUE, fill=BOTH, padx=5, pady=5)

        # -----
        row = 0
        la = Label(
            frame,
            image=Utils.icons["bCNC"],
            foreground=fg,
            background=bg,
            relief=RAISED,
            padx=0,
            pady=0,
        )
        la.grid(row=row, column=0, columnspan=2, padx=5, pady=5)

        row += 1
        la = Label(
            frame,
            text=_(
                "bCNC/\tAn advanced fully featured\n"
                "\tg-code sender for GRBL."
            ),
            font=font3,
            foreground=fg,
            background=bg,
            justify=LEFT,
        )
        la.grid(row=row, column=0, columnspan=2, sticky=W, padx=10, pady=1)

        # -----
        row += 1
        f = Frame(frame, borderwidth=1, relief=SUNKEN, height=2, background=bg)
        f.grid(row=row, column=0, columnspan=2, sticky=EW, padx=5, pady=5)

        # -----
        row += 1
        la = Label(
            frame,
            text="www:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2
        )
        la.grid(row=row, column=0, sticky=E, padx=10, pady=2)

        la = Label(
            frame,
            text=Utils.__www__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            activeforeground="Blue",
            font=font2,
            cursor="hand1",
        )
        la.grid(row=row, column=1, sticky=W, padx=2, pady=2)
        la.bind("<Button-1>", lambda e: webbrowser.open(Utils.__www__))

        # -----
        row += 1
        la = Label(
            frame,
            text="email:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2
        )
        la.grid(row=row, column=0, sticky=E, padx=10, pady=2)

        la = Label(
            frame,
            text=__email__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=W, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="author:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=NE, padx=10, pady=2)

        la = Label(
            frame,
            text=__author__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="contributors:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=NE, padx=10, pady=2)

        la = Label(
            frame,
            text=Utils.__contribute__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="translations:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=NE, padx=10, pady=2)

        la = Label(
            frame,
            text=Utils.__translations__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="credits:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=NE, padx=10, pady=2)

        la = Label(
            frame,
            text=Utils.__credits__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="version:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=E, padx=10, pady=2)

        la = Label(
            frame,
            text=__version__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        # -----
        row += 1
        la = Label(
            frame,
            text="last change:",
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2,
        )
        la.grid(row=row, column=0, sticky=E, padx=10, pady=2)

        la = Label(
            frame,
            text=__date__,
            foreground=fg,
            background=bg,
            justify=LEFT,
            font=font2
        )
        la.grid(row=row, column=1, sticky=NW, padx=2, pady=2)

        def closeFunc(e=None, t=toplevel):
            return t.destroy()

        b = Button(toplevel, text=_("Close"), command=closeFunc)
        b.pack(pady=5)
        frame.grid_columnconfigure(1, weight=1)

        toplevel.bind("<Escape>", closeFunc)
        toplevel.bind("<Return>", closeFunc)
        toplevel.bind("<KP_Enter>", closeFunc)

        toplevel.deiconify()
        toplevel.wait_visibility()
        toplevel.resizable(False, False)

        with contextlib.suppress(Exception):
            toplevel.grab_set()
        b.focus_set()
        toplevel.lift()
        if timer:
            toplevel.after(timer, closeFunc)
        toplevel.wait_window()

    # -----------------------------------------------------------------------
    def alarmClear(self, event=None):
        self._alarm = False

    # -----------------------------------------------------------------------
    # Display information on selected blocks
    # -----------------------------------------------------------------------
    def showInfo(self, event=None):
        self.canvas.showInfo(self.editor.getSelectedBlocks())
        return "break"

    # -----------------------------------------------------------------------
    # FIXME Very primitive
    # -----------------------------------------------------------------------
    def showStats(self, event=None):
        toplevel = Toplevel(self)
        toplevel.transient(self)
        toplevel.title(_("Statistics"))

        if CNC.inch:
            unit = "in"
        else:
            unit = "mm"

        # count enabled blocks
        e = 0
        le = 0
        r = 0
        t = 0
        for block in self.gcode.blocks:
            if block.enable:
                e += 1
                le += block.length
                r += block.rapid
                t += block.time

        # ===========
        frame = LabelFrame(toplevel, text=_(
            "Enabled GCode"), foreground="DarkRed")
        frame.pack(fill=BOTH)

        # ---
        row, col = 0, 0
        Label(frame, text=_("Margins X:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['xmin']:g} .. {CNC.vars['xmax']:g} "
                 + f"[{CNC.vars['xmax'] - CNC.vars['xmin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text="... Y:").grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['ymin']:g} .. {CNC.vars['ymax']:g} "
                 + f"[{CNC.vars['ymax'] - CNC.vars['ymin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text="... Z:").grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['zmin']:g} .. {CNC.vars['zmax']:g} "
                 + f"[{CNC.vars['zmax'] - CNC.vars['zmin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text=_("# Blocks:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(frame, text=str(e), foreground="DarkBlue").grid(
            row=row, column=col, sticky=W
        )

        # ---
        row += 1
        col = 0
        Label(frame, text=_("Length:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(frame, text=f"{le:g} {unit}", foreground="DarkBlue").grid(
            row=row, column=col, sticky=W
        )

        # ---
        row += 1
        col = 0
        Label(frame, text=_("Rapid:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(frame, text=f"{r:g} {unit}", foreground="DarkBlue").grid(
            row=row, column=col, sticky=W
        )

        # ---
        row += 1
        col = 0
        Label(frame, text=_("Time:")).grid(row=row, column=col, sticky=E)
        col += 1
        h, m = divmod(t, 60)  # t in min
        s = (m - int(m)) * 60
        Label(
            frame,
            text=f"{int(h)}:{int(m):02}:{int(s):02} s",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        frame.grid_columnconfigure(1, weight=1)

        # ===========
        frame = LabelFrame(toplevel, text=_("All GCode"), foreground="DarkRed")
        frame.pack(fill=BOTH)

        # ---
        row, col = 0, 0
        Label(frame, text=_("Margins X:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['axmin']:g} .. {CNC.vars['axmax']:g} "
                 + f"[{CNC.vars['axmax'] - CNC.vars['axmin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text="... Y:").grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['aymin']:g} .. {CNC.vars['aymax']:g} "
                 + f"[{CNC.vars['aymax'] - CNC.vars['aymin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text="... Z:").grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{CNC.vars['azmin']:g} .. {CNC.vars['azmax']:g} "
                 + f"[{CNC.vars['azmax'] - CNC.vars['azmin']:g}] {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text=_("# Blocks:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=str(len(self.gcode.blocks)),
            foreground="DarkBlue"
        ).grid(
            row=row,
            column=col,
            sticky=W
        )
        # ---
        row += 1
        col = 0
        Label(frame, text=_("Length:")).grid(row=row, column=col, sticky=E)
        col += 1
        Label(
            frame,
            text=f"{self.cnc.totalLength:g} {unit}",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        # ---
        row += 1
        col = 0
        Label(frame, text=_("Time:")).grid(row=row, column=col, sticky=E)
        col += 1
        h, m = divmod(self.cnc.totalTime, 60)  # t in min
        s = (m - int(m)) * 60
        Label(
            frame,
            text=f"{int(int(h))}:{int(int(m)):02}:{int(int(s)):02} s",
            foreground="DarkBlue",
        ).grid(row=row, column=col, sticky=W)

        frame.grid_columnconfigure(1, weight=1)

        # ===========
        frame = Frame(toplevel)
        frame.pack(fill=X)

        def closeFunc(e=None, t=toplevel):
            return t.destroy()

        b = Button(frame, text=_("Close"), command=closeFunc)
        b.pack(pady=5)
        frame.grid_columnconfigure(1, weight=1)

        toplevel.bind("<Escape>", closeFunc)
        toplevel.bind("<Return>", closeFunc)
        toplevel.bind("<KP_Enter>", closeFunc)

        # ----
        toplevel.deiconify()
        toplevel.wait_visibility()
        toplevel.resizable(False, False)

        with contextlib.suppress(Exception):
            toplevel.grab_set()
        b.focus_set()
        toplevel.lift()
        toplevel.wait_window()

    # -----------------------------------------------------------------------
    def reportDialog(self, event=None):
        Utils.ReportDialog(self)

    # -----------------------------------------------------------------------
    def viewChange(self, event=None):
        if self.running:
            self._selectI = 0  # last selection pointer in items
        self.draw()

    # ----------------------------------------------------------------------
    def refresh(self, event=None):
        self.editor.fill()
        self.draw()

    # ----------------------------------------------------------------------
    def draw(self):
        self.canvas.updateAll()
        self.selectionChange()

    # ----------------------------------------------------------------------
    # Redraw with a small delay
    # ----------------------------------------------------------------------
    def drawAfter(self, event=None):
        if self._drawAfter is not None:
            self.after_cancel(self._drawAfter)
        self._drawAfter = self.after(DRAW_AFTER, self.draw)
        return "break"

    # -----------------------------------------------------------------------
    def canvasFocus(self, event=None):
        self.canvas.focus_set()
        return "break"

    # -----------------------------------------------------------------------
    def selectAll(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.editor.copy()
            self.ribbon.changePage("Editor")
            self.editor.selectAll()
            self.selectionChange()
            return "break"

    # -----------------------------------------------------------------------
    def unselectAll(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.ribbon.changePage("Editor")
            self.editor.selectClear()
            self.selectionChange()
            return "break"

    # -----------------------------------------------------------------------
    def selectInvert(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.ribbon.changePage("Editor")
            self.editor.selectInvert()
            self.selectionChange()
            return "break"

    # -----------------------------------------------------------------------
    def selectLayer(self, event=None):
        focus = self.focus_get()
        if focus in (self.canvas, self.editor):
            self.ribbon.changePage("Editor")
            self.editor.selectLayer()
            self.selectionChange()
            return "break"

    # -----------------------------------------------------------------------
    def find(self, event=None):
        self.ribbon.changePage("Editor")

    # -----------------------------------------------------------------------
    def findNext(self, event=None):
        self.ribbon.changePage("Editor")

    # -----------------------------------------------------------------------
    def replace(self, event=None):
        self.ribbon.changePage("Editor")

    # -----------------------------------------------------------------------
    def activeBlock(self):
        return self.editor.activeBlock()

    # -----------------------------------------------------------------------
    # Keyboard binding to <Return>
    # -----------------------------------------------------------------------
    def cmdExecute(self, event):
        self.commandExecute()

    # ----------------------------------------------------------------------
    def insertCommand(self, cmd, execute=False):
        self.command.delete(0, END)
        self.command.insert(0, cmd)
        if execute:
            self.commandExecute(False)

    # -----------------------------------------------------------------------
    # Execute command from command line
    # -----------------------------------------------------------------------
    def commandExecute(self, addHistory=True):
        self._historyPos = None
        self._historySearch = None

        line = self.command.get().strip()
        if not line:
            return

        if self._historyPos is not None:
            if self.history[self._historyPos] != line:
                self.history.append(line)
        elif not self.history or self.history[-1] != line:
            self.history.append(line)

        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)
        self.command.delete(0, END)
        self.execute(line)

    # -----------------------------------------------------------------------
    # Register CLI handlers (plugins + builtins)
    # -----------------------------------------------------------------------
    def registerCommands(self):
        for tool in self.tools.pluginList():
            for name, spec in getattr(tool, "commands", {}).items():
                self.registerCommand(
                    name, *(spec if isinstance(spec, tuple) else (spec,))
                )

        R = self.registerCommand
        A = Application
        # one-liners as lambdas; heavier cmds as methods below
        R("ABOUT", lambda a, args, o: a.about(), 3)
        R("AUTOLEVEL", lambda a, args, o: a.executeOnSelection(True, a.gcode.autolevel), 4)
        R("CAMERA", A.cmdCamera, 3)
        R("CLEAR", A.cmdClear, 3)
        R("CLS", A.cmdClear)
        R("CONTROL", lambda a, args, o: a.ribbon.changePage("Control"), 4)
        R("DOWN", lambda a, args, o: a.editor.orderDown())
        R("UP", lambda a, args, o: a.editor.orderUp())
        R("ECHO", A.cmdEcho)
        R("FEED", A.cmdFeed)
        R("INVERT", lambda a, args, o: a.editor.invertBlocks(), 3)
        R("MSG", A.cmdMsg)
        R("MESSAGE", A.cmdMsg)
        R("FILTER", A.cmdFilter, 3)
        R("ALL", A.cmdFilter)
        R("EDIT", lambda a, args, o: a.edit(), 2)
        R("IMPORT", A.cmdImport, 2)
        R("ISO1", lambda a, args, o: a.canvasFrame.viewISO1())
        R("ISO2", lambda a, args, o: a.canvasFrame.viewISO2())
        R("ISO3", lambda a, args, o: a.canvasFrame.viewISO3())
        R("LOAD", A.cmdLoad, 2)
        R("MIRROR", A.cmdMirror, 3)
        R("ORDER", A.cmdOrder, 2)
        R("MOVE", A.cmdMove, 2)
        R("OPTIMIZE", A.cmdOptimize, 3)
        R("ORIENT", A.cmdOrient, 4)
        R("ORIGIN", A.cmdOrigin, 3)
        R("ROTATE", A.cmdRotate, 3)
        R("ROUND", A.cmdRound, 3)
        R("RULER", lambda a, args, o: a.canvas.setActionRuler(), 2)
        R("STATISTICS", lambda a, args, o: a.showStats(), 4)
        R("STEP", A.cmdStep)
        R("SPINDLE", A.cmdSpindle, 3)
        R("STOP", lambda a, args, o: a.stopRun())
        R("TERMINAL", lambda a, args, o: a.ribbon.changePage("Terminal"), 4)
        R("BIT", A.cmdTool)
        R("TOOL", A.cmdTool)
        R("MILL", A.cmdTool)
        R("TOOLS", lambda a, args, o: a.ribbon.changePage("CAM"))
        R("UNLOCK", lambda a, args, o: a.unlock(), 3)
        R("USER", A.cmdUser, 2)
        R("RRAPID", lambda a, args, o: Page.frames["Probe:Probe"].recordRapid(), 2)
        R("RFEED", lambda a, args, o: Page.frames["Probe:Probe"].recordFeed(), 2)
        R("RPOINT", lambda a, args, o: Page.frames["Probe:Probe"].recordPoint(), 2)
        R("RCIRCLE", lambda a, args, o: Page.frames["Probe:Probe"].recordCircle(), 2)
        R("RFINISH", lambda a, args, o: Page.frames["Probe:Probe"].recordFinishAll(), 3)
        R("XY", lambda a, args, o: a.canvasFrame.viewXY())
        R("YX", lambda a, args, o: a.canvasFrame.viewXY())
        R("XZ", lambda a, args, o: a.canvasFrame.viewXZ())
        R("ZX", lambda a, args, o: a.canvasFrame.viewXZ())
        R("YZ", lambda a, args, o: a.canvasFrame.viewYZ())
        R("ZY", lambda a, args, o: a.canvasFrame.viewYZ())
        R("ABSOLUTE", lambda a, args, o: a.sendGCode("G90"), 3)
        R("HELP", lambda a, args, o: a.help())
        R("HOME", lambda a, args, o: a.home())
        R("OPEN", lambda a, args, o: a.openClose())
        R("QUIT", lambda a, args, o: a.quit(), 2)
        R("EXIT", lambda a, args, o: a.quit(), 2)
        R("PAUSE", lambda a, args, o: a.pause())
        R("RESUME", lambda a, args, o: a.resume())
        R("FEEDHOLD", lambda a, args, o: a.feedHold())
        R("RELATIVE", lambda a, args, o: a.sendGCode("G91"), 3)
        R("RESET", lambda a, args, o: a.softReset())
        R("RUN", lambda a, args, o: a.run())
        R("SAFE", A.cmdSafe)
        R("SAVE", A.cmdSave, 2)
        R("SENDHEX", lambda a, args, o: a.sendHex(args[1]))
        R("SET", A.cmdSet)
        R("SET0", lambda a, args, o: a._wcsSet(0.0, 0.0, 0.0))
        R("SETX", A.cmdSetX)
        R("SETY", A.cmdSetY)
        R("SETZ", A.cmdSetZ)

    # -----------------------------------------------------------------------
    # Execute a single command
    # -----------------------------------------------------------------------
    def execute(self, line):
        try:
            line = self.evaluate(line)
        except Exception:
            messagebox.showerror(
                _("Evaluation error"), sys.exc_info()[1], parent=self
            )
            return "break"

        if line is None:
            return "break"

        if self.executeGcode(line):
            return "break"

        rc = self.executeCommand(line.strip())
        if rc:
            messagebox.showerror(rc[0], rc[1], parent=self)
        return "break"

    def cmdCamera(self, args, oline=None):
        # FIXME will make crazy the button state
        if rexx.abbrev("SWITCH", args[1].upper(), 1):
            Page.groups["Probe:Camera"].switchCamera()
        elif rexx.abbrev("SPINDLE", args[1].upper(), 2):
            Page.frames["Probe:Camera"].registerSpindle()
        elif rexx.abbrev("CAMERA", args[1].upper(), 1):
            Page.frames["Probe:Camera"].registerCamera()

    def cmdClear(self, args, oline=None):
        self.ribbon.changePage("Terminal")
        Page.frames["Terminal"].clear()

    def cmdEcho(self, args, oline):
        self.setStatus(oline[5:].strip())

    def cmdFeed(self, args, oline=None):
        try:
            CNC.appendFeed = args[1].upper() == "ON"
        except Exception:
            CNC.appendFeed = True
        self.setStatus(
            CNC.appendFeed
            and "Feed appending turned on"
            or "Feed appending turned off"
        )

    def cmdMsg(self, args, oline):
        messagebox.showinfo(
            "Message", oline[oline.find(" ") + 1:].strip(), parent=self
        )

    def cmdFilter(self, args, oline=None):
        try:
            self.editor.filter = args[1]
        except Exception:
            self.editor.filter = None
        self.editor.fill()

    def cmdImport(self, args, oline=None):
        try:
            self.importFile(args[1])
        except Exception:
            self.importFile()

    def cmdLoad(self, args, oline=None):
        if len(args) == 1:
            self.loadDialog()
        else:
            self.load(args[1])

    def cmdMirror(self, args, oline=None):
        if len(args) == 1:
            return "break"
        line1 = args[1].upper()
        if not self.editor.curselection():
            self.editor.selectAll()
        if rexx.abbrev("HORIZONTAL", line1):
            self.executeOnSelection(False, self.gcode.mirrorHLines)
        elif rexx.abbrev("VERTICAL", line1):
            self.executeOnSelection(False, self.gcode.mirrorVLines)

    def cmdOrder(self, args, oline=None):
        if args[1].upper() == "UP":
            self.editor.orderUp()
        elif args[1].upper() == "DOWN":
            self.editor.orderDown()

    def cmdMove(self, args, oline=None):
        if len(args) == 1:
            self.canvas.setActionMove()
            return "break"
        line1 = args[1].upper()
        dz = 0.0
        if rexx.abbrev("CENTER", line1, 2):
            dx = -(CNC.vars["xmin"] + CNC.vars["xmax"]) / 2.0
            dy = -(CNC.vars["ymin"] + CNC.vars["ymax"]) / 2.0
            self.editor.selectAll()
        elif line1 == "BL":
            dx = -CNC.vars["xmin"]
            dy = -CNC.vars["ymin"]
            self.editor.selectAll()
        elif line1 == "BC":
            dx = -(CNC.vars["xmin"] + CNC.vars["xmax"]) / 2.0
            dy = -CNC.vars["ymin"]
            self.editor.selectAll()
        elif line1 == "BR":
            dx = -CNC.vars["xmax"]
            dy = -CNC.vars["ymin"]
            self.editor.selectAll()
        elif line1 == "TL":
            dx = -CNC.vars["xmin"]
            dy = -CNC.vars["ymax"]
            self.editor.selectAll()
        elif line1 == "TC":
            dx = -(CNC.vars["xmin"] + CNC.vars["xmax"]) / 2.0
            dy = -CNC.vars["ymax"]
            self.editor.selectAll()
        elif line1 == "TR":
            dx = -CNC.vars["xmax"]
            dy = -CNC.vars["ymax"]
            self.editor.selectAll()
        elif line1 == "LC":
            dx = -CNC.vars["xmin"]
            dy = -(CNC.vars["ymin"] + CNC.vars["ymax"]) / 2.0
            self.editor.selectAll()
        elif line1 == "RC":
            dx = -CNC.vars["xmax"]
            dy = -(CNC.vars["ymin"] + CNC.vars["ymax"]) / 2.0
            self.editor.selectAll()
        elif line1 in ("UP", "DOWN"):
            dx = line1
            dy = dz = line1
        else:
            try:
                dx = float(args[1])
            except Exception:
                dx = 0.0
            try:
                dy = float(args[2])
            except Exception:
                dy = 0.0
            try:
                dz = float(args[3])
            except Exception:
                dz = 0.0
        self.executeOnSelection(False, self.gcode.moveLines, dx, dy, dz)

    def cmdOptimize(self, args, oline=None):
        if not self.editor.curselection():
            messagebox.showinfo(
                _("Optimize"),
                _("Please select the blocks of gcode you want "
                  + "to optimize."),
                parent=self,
            )
        else:
            self.executeOnSelection(True, self.gcode.optimize)

    def cmdOrient(self, args, oline=None):
        if not self.editor.curselection():
            self.editor.selectAll()
        self.executeOnSelection(False, self.gcode.orientLines)

    def cmdOrigin(self, args, oline=None):
        try:
            dx = -float(args[1])
        except Exception:
            dx = 0.0
        try:
            dy = -float(args[2])
        except Exception:
            dy = 0.0
        try:
            dz = -float(args[3])
        except Exception:
            dz = 0.0
        self.editor.selectAll()
        self.executeOnSelection(False, self.gcode.moveLines, dx, dy, dz)

    def cmdRotate(self, args, oline=None):
        line1 = args[1].upper()
        x0 = y0 = 0.0
        if line1 == "CCW":
            ang = 90.0
        elif line1 == "CW":
            ang = -90.0
        elif line1 == "FLIP":
            ang = 180.0
        else:
            try:
                ang = float(args[1])
            except Exception:
                ang = 0.0
            try:
                x0 = float(args[2])
            except Exception:
                x0 = 0.0
            try:
                y0 = float(args[3])
            except Exception:
                y0 = 0.0
        self.executeOnSelection(False, self.gcode.rotateLines, ang, x0, y0)

    def cmdRound(self, args, oline=None):
        acc = None
        if len(args) > 1:
            if rexx.abbrev("ALL", args[1].upper()):
                self.editor.selectAll()
            else:
                try:
                    acc = int(args[1])
                except Exception:
                    acc = None
        self.executeOnSelection(False, self.gcode.roundLines, acc)

    def cmdStep(self, args, oline=None):
        with contextlib.suppress(Exception):
            self.control.setStep(float(args[1]))

    def cmdSpindle(self, args, oline=None):
        if len(args) > 1:
            if args[1].upper() == "OFF":
                self.gstate.spindle.set(False)
            elif args[1].upper() == "ON":
                self.gstate.spindle.set(True)
            else:
                try:
                    rpm = int(args[1])
                except Exception:
                    rpm = None
                if rpm == 0:
                    self.gstate.spindleSpeed.set(0)
                    self.gstate.spindle.set(False)
                elif rpm is not None:
                    self.gstate.spindleSpeed.set(rpm)
                    self.gstate.spindle.set(True)
        else:
            self.gstate.spindle.set(not self.gstate.spindle.get())
        self.gstate.spindleControl()

    def cmdTool(self, args, oline=None):
        tool = self.tools["EndMill"]
        try:
            diam = float(args[1])
        except Exception:
            diam = self.tools.fromMm(tool["diameter"])
        self.setStatus(_("EndMill: {} {}").format(tool["name"], diam))

    def cmdUser(self, args, oline=None):
        n = Utils.getInt("Buttons", "n", 6)
        try:
            idx = int(args[1])
        except Exception:
            try:
                name = args[1].upper()
                for i in range(n):
                    if name == Utils.getStr(
                        "Buttons", f"name.{int(i)}", ""
                    ).upper():
                        idx = i
                        break
            except Exception:
                return "break"
        if idx < 0 or idx >= n:
            self.setStatus(_("Invalid user command {}").format(args[1]))
            return "break"
        cmd = Utils.getStr("Buttons", f"command.{int(idx)}", "")
        for line in cmd.splitlines():
            self.execute(line)

    def cmdSafe(self, args, oline=None):
        with contextlib.suppress(Exception):
            CNC.vars["safe"] = float(args[1])
        self.statusbar["text"] = f"Safe Z= {CNC.vars['safe']:g}"

    def cmdSave(self, args, oline=None):
        if len(args) > 1:
            self.save(args[1])
        else:
            self.saveAll()

    def cmdSet(self, args, oline=None):
        try:
            x = float(args[1])
        except Exception:
            x = None
        try:
            y = float(args[2])
        except Exception:
            y = None
        try:
            z = float(args[3])
        except Exception:
            z = None
        self._wcsSet(x, y, z)

    def cmdSetX(self, args, oline=None):
        try:
            x = float(args[1])
        except Exception:
            x = ""
        self._wcsSet(x, None, None)

    def cmdSetY(self, args, oline=None):
        try:
            y = float(args[1])
        except Exception:
            y = ""
        self._wcsSet(None, y, None)

    def cmdSetZ(self, args, oline=None):
        try:
            z = float(args[1])
        except Exception:
            z = ""
        self._wcsSet(None, None, z)

    # -----------------------------------------------------------------------
    # Run fn(items, *args) on the editor selection with busy/redraw.
    # fn may return: None, an error string, or a new selection.
    # -----------------------------------------------------------------------
    def executeOnSelection(self, blocksonly, fn, *args):
        if blocksonly:
            items = self.editor.getSelectedBlocks()
        else:
            items = self.editor.getCleanSelection()
        if not items:
            messagebox.showwarning(
                _("Nothing to do"),
                _("Operation requires some gcode to be selected"),
                parent=self,
            )
            return

        self.busy()
        sel = fn(items, *args)
        self.editor.fill()
        if sel is not None:
            if isinstance(sel, str):
                messagebox.showerror(_("Operation error"), sel, parent=self)
            else:
                self.editor.select(sel, clear=True)
        self.drawAfter()
        self.notBusy()
        return sel

    # -----------------------------------------------------------------------
    def edit(self, event=None):
        page = self.ribbon.getActivePage()
        if page.name == "Editor":
            self.editor.edit()
        elif page.name == "CAM":
            page.edit()

    # -----------------------------------------------------------------------
    def commandFocus(self, event=None):
        self.command.focus_set()

    # -----------------------------------------------------------------------
    def commandFocusIn(self, event=None):
        self.cmdlabel["foreground"] = "Blue"

    # -----------------------------------------------------------------------
    def commandFocusOut(self, event=None):
        self.cmdlabel["foreground"] = "Black"

    # -----------------------------------------------------------------------
    # FIXME why it is not called?
    # -----------------------------------------------------------------------
    def commandKey(self, event):
        if event.char or event.keysym in ("BackSpace"):
            self._historyPos = None
            self._historySearch = None

    # -----------------------------------------------------------------------
    def commandHistoryUp(self, event=None):
        if self._historyPos is None:
            s = self.command.get()
            if self.history:
                self._historyPos = len(self.history) - 1
            else:
                self._historySearch = None
                return
            if s and self._historySearch is None:
                self._historySearch = s.strip().upper()
        else:
            self._historyPos = max(0, self._historyPos - 1)

        if self._historySearch:
            for i in range(self._historyPos, -1, -1):
                h = self.history[i]
                if h.upper().startswith(self._historySearch):
                    self._historyPos = i
                    break

        self.command.delete(0, END)
        self.command.insert(0, self.history[self._historyPos])

    # -----------------------------------------------------------------------
    def commandHistoryDown(self, event=None):
        if self._historyPos is None:
            self._historySearch = None
            return
        else:
            self._historyPos += 1
            if self._historyPos >= len(self.history):
                self._historyPos = None
                self._historySearch = None

        if self._historySearch:
            for i in range(self._historyPos, len(self.history)):
                h = self.history[i]
                if h.upper().startswith(self._historySearch):
                    self._historyPos = i
                    break

        self.command.delete(0, END)
        if self._historyPos is not None:
            self.command.insert(0, self.history[self._historyPos])

    # -----------------------------------------------------------------------
    def select(self, items, double, clear, toggle=True):
        self.editor.select(items, double, clear, toggle)
        self.selectionChange()

    # ----------------------------------------------------------------------
    # Selection has changed highlight the canvas
    # ----------------------------------------------------------------------
    def selectionChange(self, event=None):
        items = self.editor.getSelection()
        self.canvas.clearSelection()
        if not items:
            return
        self.canvas.select(items)
        self.canvas.activeMarker(self.editor.getActive())

    # -----------------------------------------------------------------------
    # Create a new file
    # -----------------------------------------------------------------------
    def newFile(self, event=None):
        if self.running:
            return
        if self.fileModified():
            return
        self.gcode.init()
        self.gcode.headerFooter()
        self.editor.fill()
        self.draw()
        self.title(f"{Utils.__prg__} {__version__} {__platform_fingerprint__}")

    # -----------------------------------------------------------------------
    # load dialog
    # -----------------------------------------------------------------------
    def loadDialog(self, event=None):
        if self.running:
            return
        filename = bFileDialog.askopenfilename(
            master=self,
            title=_("Open file"),
            initialfile=os.path.join(
                Utils.getUtf("File", "dir"), Utils.getUtf("File", "file")
            ),
            filetypes=FILETYPES,
        )
        if filename:
            self.load(filename)
        return "break"

    # -----------------------------------------------------------------------
    # save dialog
    # -----------------------------------------------------------------------
    def saveDialog(self, event=None):
        if self.running:
            return
        fn, ext = os.path.splitext(Utils.getUtf("File", "file"))
        if ext in (".dxf", ".DXF"):
            ext = ".ngc"
        filename = bFileDialog.asksaveasfilename(
            master=self,
            title=_("Save file"),
            initialfile=os.path.join(Utils.getUtf("File", "dir"), fn + ext),
            filetypes=FILETYPES,
        )
        if filename:
            self.save(filename)
        return "break"

    # -----------------------------------------------------------------------
    def fileModified(self):
        if self.gcode.isModified():
            ans = messagebox.askquestion(
                _("File modified"),
                _("Gcode was modified do you want to save it first?"),
                type=messagebox.YESNOCANCEL,
                parent=self,
            )
            if ans == messagebox.CANCEL:
                return True
            if ans == messagebox.YES or ans is True:
                self.saveAll()

        if not self.gcode.probe.isEmpty() and not self.gcode.probe.saved:
            ans = messagebox.askquestion(
                _("Probe File modified"),
                _("Probe was modified do you want to save it first?"),
                type=messagebox.YESNOCANCEL,
                parent=self,
            )
            if ans == messagebox.CANCEL:
                return True
            if ans == messagebox.YES or ans is True:
                if self.gcode.probe.filename == "":
                    self.saveDialog()
                else:
                    self.gcode.probe.save()
        return False

    # -----------------------------------------------------------------------
    # Load a file into editor
    # -----------------------------------------------------------------------
    def load(self, filename, autoloaded=False):
        fn, ext = os.path.splitext(filename)
        if ext == ".probe":
            pass
        else:
            if self.fileModified():
                return

            if not self.gcode.probe.isEmpty():
                ans = messagebox.askquestion(
                    _("Existing Autolevel"),
                    _("Autolevel/probe information already exists.\nDelete it?"),
                    parent=self,
                )
                if ans == messagebox.YES or ans is True:
                    self.gcode.probe.init()

        self.setStatus(_("Loading: {} ...").format(filename), True)
        Sender.load(self, filename)

        if ext == ".probe":
            self.autolevel.setValues()
            self.event_generate("<<DrawProbe>>")

        elif ext == ".orient":
            self.event_generate("<<DrawOrient>>")
            self.event_generate("<<OrientSelect>>", data=0)
            self.event_generate("<<OrientUpdate>>")

        else:
            self.editor.selectClear()
            self.editor.fill()
            self.canvas.reset()
            self.draw()
            self.canvas.fit2Screen()
            Page.frames["CAM"].populate()

        if autoloaded:
            self.setStatus(
                _("'{}' reloaded at '{}'").format(
                    filename, str(datetime.now()))
            )
        else:
            self.setStatus(_("'{}' loaded").format(filename))
        self.title(
            f"{Utils.__prg__} {__version__}: {self.gcode.filename} "
            + f"{__platform_fingerprint__}"
        )

    # -----------------------------------------------------------------------
    def save(self, filename):
        Sender.save(self, filename)
        self.setStatus(_("'{}' saved").format(filename))
        self.title(
            f"{Utils.__prg__} {__version__}: {self.gcode.filename} "
            + f"{__platform_fingerprint__}"
        )

    # -----------------------------------------------------------------------
    def saveAll(self, event=None):
        if self.gcode.filename:
            Sender.saveAll(self)
        else:
            self.saveDialog()
        return "break"

    # -----------------------------------------------------------------------
    def reload(self, event=None):
        self.load(self.gcode.filename)

    # -----------------------------------------------------------------------
    def importFile(self, filename=None):
        if filename is None:
            filename = bFileDialog.askopenfilename(
                master=self,
                title=_("Import Gcode/DXF file"),
                initialfile=os.path.join(
                    Utils.getUtf("File", "dir"), Utils.getUtf("File", "file")
                ),
                filetypes=[
                    (_("G-Code"), ("*.ngc", "*.nc", "*.gcode")),
                    ("DXF", "*.dxf"),
                    ("All", "*"),
                ],
            )
        if filename:
            fn, ext = os.path.splitext(filename)
            ext = ext.lower()
            gcode = GCode()
            if ext == ".dxf":
                gcode.importDXF(filename)
            elif ext == ".svg":
                gcode.importSVG(filename)
            else:
                gcode.load(filename)
            sel = self.editor.getSelectedBlocks()
            if not sel:
                pos = None
            else:
                pos = sel[-1]
            self.addUndo(self.gcode.insBlocksUndo(pos, gcode.blocks))
            del gcode
            self.editor.fill()
            self.draw()
            self.canvas.fit2Screen()

    # -----------------------------------------------------------------------
    def focusIn(self, event):
        if self._inFocus:
            return
        # FocusIn is generated for all sub-windows, handle only the main window
        if self is not event.widget:
            return
        self._inFocus = True
        if self.gcode.checkFile():
            if self.gcode.isModified():
                ans = messagebox.askquestion(
                    _("Warning"),
                    _(
                        "Gcode file {} was changed since "
                        "editing started\n"
                        "Reload new version?"
                    ).format(self.gcode.filename),
                    parent=self,
                )
                if ans == messagebox.YES or ans is True:
                    self.gcode.resetModified()
                    self.load(self.gcode.filename)
            else:
                self.load(self.gcode.filename, True)
        self._inFocus = False
        self.gcode.syncFileTime()

    # -----------------------------------------------------------------------
    def openClose(self, event=None):
        serialPage = Page.frames["Serial"]
        if self.serial is not None:
            self.close()
            serialPage.connectBtn.config(
                text=_("Open"), background="Salmon", activebackground="Salmon"
            )
        else:
            serialPage = Page.frames["Serial"]
            device = _device or serialPage.portCombo.get()  # .split("\t")[0]
            baudrate = _baud or serialPage.baudCombo.get()
            if self.open(device, baudrate):
                serialPage.connectBtn.config(
                    text=_("Close"),
                    background="LightGreen",
                    activebackground="LightGreen",
                )
                self.enable()

    # -----------------------------------------------------------------------
    def open(self, device, baudrate):
        try:
            return Sender.open(self, device, baudrate)
        except Exception:
            self.serial = None
            self.thread = None
            messagebox.showerror(
                _("Error opening serial"), sys.exc_info()[1], parent=self
            )
        return False

    # -----------------------------------------------------------------------
    def close(self):
        Sender.close(self)
        # Refresh DRO from monitorSerial (safe if called from serial thread)
        self._posUpdate = True

    # -----------------------------------------------------------------------
    # An entry function should be called periodically during compiling
    # to check if the Pause or Stop buttons are pressed
    # @return true if the compile has to abort
    # -----------------------------------------------------------------------
    def checkStop(self):
        try:
            self.update()  # very tricky function of Tk
        except TclError:
            pass
        return self._stop

    # -----------------------------------------------------------------------
    # Send enabled gcode file to the CNC machine
    # -----------------------------------------------------------------------
    def run(self, lines=None):
        self.cleanAfter = True  # Clean when this operation stops
        print("Will clean after this operation")

        if self.serial is None and not CNC.developer:
            messagebox.showerror(
                _("Serial Error"), _("Serial is not connected"), parent=self
            )
            return
        if self.running:
            if self._pause:
                self.resume()
                return
            messagebox.showerror(
                _("Already running"), _("Please stop before"), parent=self
            )
            return

        self.editor.selectClear()
        self.selectionChange()
        CNC.vars["errline"] = ""

        # the buffer of the machine should be empty?
        self.initRun()
        self.canvas.clearSelection()
        self._runLines = sys.maxsize  # temporary WARNING this value is used
        # by Sender._serialIO to check if we
        # are still sending or we finished
        self._gcount = 0  # count executed lines
        self._selectI = 0  # last selection pointer in items
        self._paths = None  # temporary
        CNC.vars["running"] = True  # enable running status
        CNC.vars["_OvChanged"] = True  # force a feed change if any
        if self._onStart:
            with contextlib.suppress(Exception):
                os.system(self._onStart)

        if lines is None:
            self.statusbar.setLimits(0, 9999)
            self.statusbar.setProgress(0, 0)
            self._paths = self.gcode.compile(self.queue, self.checkStop)
            if self._paths is None:
                self.emptyQueue()
                self.purgeController()
                return
            elif not self._paths:
                self.runEnded()
                messagebox.showerror(
                    _("Empty gcode"),
                    _("Not gcode file was loaded"),
                    parent=self
                )
                return

            # reset colors
            self.lastProcessedPath = 0

            # the buffer of the machine should be empty?
            self._runLines = len(self._paths) + 1  # plus the wait
        else:
            n = 1  # including one wait command
            for line in CNC.compile(lines):
                if line is not None:
                    if isinstance(line, str):
                        self.queue.put(line + "\n")
                    else:
                        self.queue.put(line)
                    n += 1
            # set it at the end to be sure that all lines are queued
            self._runLines = n
        self.queue.put((WAIT,))  # wait at the end to become idle

        self.setStatus(_("Running..."))
        self.statusbar.setLimits(0, self._runLines)
        self.statusbar.configText(fill="White")
        self.statusbar.config(background="DarkGray")

        self.bufferbar.configText(fill="White")
        self.bufferbar.config(background="DarkGray")
        self.bufferbar.setText("")

    # -----------------------------------------------------------------------
    # Start the web pendant
    # -----------------------------------------------------------------------
    def startPendant(self, showInfo=True):
        started = Pendant.start(self)
        if showInfo:
            hostName = f"http://{socket.gethostname()}:{Pendant.port}"
            if started:
                messagebox.showinfo(
                    _("Pendant"),
                    _("Pendant started:\n") + hostName,
                    parent=self
                )
            else:
                dr = messagebox.askquestion(
                    _("Pendant"),
                    _("Pendant already started:\n")
                    + hostName
                    + _("\nWould you like open it locally?"),
                    parent=self,
                )
                if dr == "yes":
                    webbrowser.open(hostName, new=2)

    # -----------------------------------------------------------------------
    # Stop the web pendant
    # -----------------------------------------------------------------------
    def stopPendant(self):
        if Pendant.stop():
            messagebox.showinfo(_("Pendant"), _(
                "Pendant stopped"), parent=self)

    # -----------------------------------------------------------------------
    # Inner loop to catch any generic exception
    # -----------------------------------------------------------------------
    def _monitorSerial(self):
        # Check serial output
        t = time.time()

        # dump in the terminal what ever you can in less than 0.1s
        inserted = False
        while self.log.qsize() > 0 and time.time() - t < 0.1:
            try:
                msg, line = self.log.get_nowait()
                line = str(line).rstrip("\n")
                inserted = True

                if msg == Sender.MSG_BUFFER:
                    self.buffer.insert(END, line)

                elif msg == Sender.MSG_SEND:
                    self.terminal.insert(END, line)
                    self.terminal.itemconfig(END, foreground="Blue")

                elif msg == Sender.MSG_RECEIVE:
                    self.terminal.insert(END, line)
                    if self._insertCount:
                        # when counting is started, then continue
                        self._insertCount += 1
                    elif line and line[0] in ("[", "$"):
                        # start the counting on the first line received
                        # starting with $ or [
                        self._insertCount = 1

                elif msg == Sender.MSG_OK:
                    if self.terminal.size() > 0 and self.buffer.size() > 0:
                        if self._insertCount:
                            pos = self.terminal.size() - self._insertCount
                            self._insertCount = 0
                        else:
                            pos = END
                        self.terminal.insert(pos, self.buffer.get(0))
                        self.terminal.itemconfig(pos, foreground="Blue")
                        self.buffer.delete(0)
                    self.terminal.insert(END, line)

                elif msg == Sender.MSG_ERROR:
                    if self.terminal.size() > 0 and self.buffer.size() > 0:
                        if self._insertCount:
                            pos = self.terminal.size() - self._insertCount
                            self._insertCount = 0
                        else:
                            pos = END
                        self.terminal.insert(pos, self.buffer.get(0))
                        self.terminal.itemconfig(pos, foreground="Blue")
                        self.buffer.delete(0)
                    self.terminal.insert(END, line)
                    self.terminal.itemconfig(END, foreground="Red")

                elif msg == Sender.MSG_RUNEND:
                    self.terminal.insert(END, line)
                    self.terminal.itemconfig(END, foreground="Magenta")
                    self.setStatus(line)
                    self.enable()

                elif msg == Sender.MSG_CLEAR:
                    self.buffer.delete(0, END)

                else:
                    # Unknown?
                    self.buffer.insert(END, line)
                    self.terminal.itemconfig(END, foreground="Magenta")

                if self.terminal.size() > 1000:
                    self.terminal.delete(0, 500)
            except Empty:
                break

        if inserted:
            self.terminal.see(END)

        # Check pendant
        try:
            cmd = self.pendant.get_nowait()
            self.execute(cmd)
        except Empty:
            pass

        # Load file from pendant
        if self._pendantFileUploaded is not None:
            self.load(self._pendantFileUploaded)
            self._pendantFileUploaded = None

        # Update position if needed
        if self._posUpdate:
            state = CNC.vars["state"]
            try:
                CNC.vars["color"] = STATECOLOR[state]
            except KeyError:
                if self._alarm:
                    CNC.vars["color"] = STATECOLOR["Alarm"]
                else:
                    CNC.vars["color"] = STATECOLORDEF
            self._pause = "Hold" in state
            self.dro.updateState()
            self.dro.updateCoords()
            self.canvas.gantry(
                CNC.vars["wx"],
                CNC.vars["wy"],
                CNC.vars["wz"],
                CNC.vars["mx"],
                CNC.vars["my"],
                CNC.vars["mz"],
            )
            if state == "Run":
                self.gstate.updateFeed()
            self._posUpdate = False

        # Update status string
        if self._gUpdate:
            self.gstate.updateG()
            self._gUpdate = False

        # Update probe and draw point
        if self._probeUpdate:
            Page.frames["Probe:Probe"].updateProbe()
            Page.frames["ProbeCommon"].updateTlo()
            self.canvas.drawProbe()
            self._probeUpdate = False

        # Update any possible variable?
        if self._update:
            if self._update == "toolheight":
                Page.frames["Probe:Tool"].updateTool()
            elif self._update == "TLO":
                Page.frames["ProbeCommon"].updateTlo()
            self._update = None

        # Deferred from serial thread (Tk / purge must run on main thread)
        if self._cycleStartRun:
            self._cycleStartRun = False
            self.event_generate("<<Run>>")

        if self._jobDonePending:
            self._jobDonePending = False
            self.jobDone()

        if self.running:
            self.statusbar.setProgress(
                self._runLines - self.queue.qsize(), self._gcount
            )
            CNC.vars["msg"] = self.statusbar.msg
            self.bufferbar.setProgress(Sender.getBufferFill(self))
            self.bufferbar.setText(f"{Sender.getBufferFill(self):3.0f}%")

            if self._selectI >= 0 and self._paths:
                while self._selectI <= self._gcount and self._selectI < len(
                    self._paths
                ):
                    if self._paths[self._selectI]:
                        i, j = self._paths[self._selectI]
                        path = self.gcode[i].path(j)
                        if path:
                            self.lastProcessedPath = path
                    self._selectI += 1

            if self._gcount >= self._runLines:
                self.runEnded()

    # -----------------------------------------------------------------------
    # "thread" timed function looking for messages in the serial thread
    # and reporting back in the terminal
    # -----------------------------------------------------------------------
    def monitorSerial(self):
        try:
            self._monitorSerial()
        except Exception:
            typ, val, tb = sys.exc_info()
            traceback.print_exception(typ, val, tb)
        self.after(MONITOR_AFTER, self.monitorSerial)

    # -----------------------------------------------------------------------
    def get(self, section, item):
        return Utils.config.get(section, item)

    # -----------------------------------------------------------------------
    def set(self, section, item, value):
        return Utils.config.set(section, item, value)


if __name__ == "__main__":
    sys.stderr.write("ERROR: The program cannot be started from this file!\n")
    sys.stderr.write("\tPlease use __main__.py instead!\n")

    sys.exit()
