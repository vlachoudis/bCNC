# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# Please consult the flair documentation for the license
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#
# Author: Vasilis Vlachoudis
#  Email: Vasilis.Vlachoudis@cern.ch
#   Date: 12-Oct-2006

import sys
import time

from tkinter import (
    TclError,
    YES,
    W,
    E,
    CENTER,
    X,
    Y,
    BOTH,
    LEFT,
    RIGHT,
    RAISED,
    SOLID,
    HORIZONTAL,
    OUTSIDE,
    SEL,
    END,
    DISABLED,
    ACTIVE,
    BROWSE,
    Event,
    Tk,
    Toplevel,
    Button,
    Canvas,
    Entry,
    Frame,
    Label,
    Listbox,
    Menu,
    Scrollbar,
    Text,
    PhotoImage,
    LabelFrame,
)
from tkinter import ttk
from tkinter import font as tkfont
from tkinter.colorchooser import askcolor

import bFileDialog
import Unicode


# Key state codes

# Ansi escape sequences

_SAVEICON = """
R0lGODlhEAAQAOcBAAAAAP//////////////////////////////////////////////////////
/////////0xLS0RDRLO0ubO0ubO0ubO0ubS2ubS2u7a4vLe5vLi5vLm5vERDRExLS////////0JA
QVpZWfH0+vD0+vD0+vD0+vH0+vL1+vP2+/X4/Pf5/Pn7/WVjZEJAQf///////0A+P2JgYfn6/Zy2
z5y2z5y2z5y2z522z523z5630J+40P39/mJgYUA+P////////z08PV5cXfv8/fj5+/n5+/j5+/j5
+/f4+vX3+vT2+fL0+PL2+V5cXT08Pf///////zs6O1tZWu7z9+/z9+/z9+/z9+7z9+7y9u3x9uvw
9env9Oft81tZWjs6O////////zk3OFdVVuLq8YuiuIuiuIuiuIuiuIqht4qht4qgt4mgttzl7VdV
Vjk3OP///////zc1NlRSU9Te6NDd6NDd6NDd6NDc58/c58/b587b5s3a5s/a5lRSUzc1Nv//////
/zUzM1FOT1FOT1FOT1FOT1FOT1FOT1FOT1FOT1FOT1FOT1FOT1FOTzUzM////////zIwMU1KS01K
S01KS01KS01KS01KS01KS01KS01KS01KS01KS01KSzIwMf///////zAtLklFRklFRs3NzdbW1tbV
1dXV1dbW1tbW1tPT0ykmJyYjJElFRjAtLv///////yspKkI/QEI/QKenpz88PTUzM66urq6urq6u
rq6urkJAQSgnJ0ZDRCspKv///////yYkJTs4OTs4OZmZmTQxMiglJp+fn5+fn5+fn5+fn0E+PyYk
JVpXWCYkJf///////yQiIi0qKjUxMouKiysoKSEfIJCQkJCQkJCQkJCQkDYzNCEfIFFNTiMgIf//
/////yUfHx8dHR4bHHV1dXh4eHh4eHh4eHh4eHh4eHh4eBsZGhsZGR8cHSEfH///////////////
/////////////////////////////////////////////////////yH5BAEKAP8ALAAAAAAQABAA
AAj4AP8JHEiwoMAIEiZQqGDhAoYMGjZw6OBBYAgRI0iUMHECRQoVK1i0cCEwhowZNGrYuIEjh44d
PHr4EBhEyBAiRYwcQZJEyRImTZwIjCJlCpUqVq5gyaJlC5cuXgSGETOGTBkzZ9CkUbOGTRs3AuPI
mUOnjp07ePLo2cOnjx+BgQQNIlTI0CFEiRQtYtTIkcBIkiZRqmTpEqZMmjZx6uRJYChRo0iVMnUK
VSpVq1i1ciUwlqxZtGrZuoUrl65dvHr5EhhM2DBixYwdQ5ZM2TJmzZwJjCZtGrVq1q5hy6ZtG7du
3gSGEzeOXDlz59ClU7eOXTt3BrMTDAgAOw==
"""


# -----------------------------------------------------------------------------
# bind event with data as a replacement of the Tkinter bind for virtual
# events to send data <<...>>
#
# Example, instead of binding like
#       widget.bind("<<VirtualEvent>>", function)
# use it as
#       bindEventData(widget, "<<VirtualEvent>>", function)
#
# def function(event):
#       print event.serial, event.widget, event.data
#
# Send message as
#     widget.event_generate("<<VirtualEvent>>", data="Hello")
#     widget.event_generate("<<VirtualEvent>>", data=("One","Two"))
#     widget.event_generate("<<VirtualEvent>>", serial=10, data=("One","Two"))
#
# WARNING: Unfortunately it will convert data to STRING!!!
# -----------------------------------------------------------------------------
def bindEventData(widget, sequence, func, add=None):
    def _substitute(*args):
        e = Event()
        nsign, b, t, T, d, W = args
        try:
            e.serial = int(nsign)
        except Exception:
            e.serial = nsign
        try:
            e.num = int(b)
        except Exception:
            e.num = b
        try:
            e.time = int(t)
        except Exception:
            e.time = t
        e.type = T
        e.data = d
        try:
            e.widget = widget._nametowidget(W)
        except KeyError:
            e.widget = W
        return (e,)

    funcid = widget._register(func, _substitute, needcleanup=1)
    cmd = '{0}if {{"[{1} %# %b %t %T %d %W]" == "break"}} break\n'.format(
        "+" if add else "", funcid
    )
    widget.tk.call("bind", widget._w, sequence, cmd)


# =============================================================================
def _entryPaste(event):
    """global replacement for the Entry.paste"""
    try:
        event.widget.delete("sel.first", "sel.last")
    except TclError:
        pass  # nothing is selected

    # in tk.call() use the widget's string representation event.widget._w
    # instead of event.widget, which is the widget instance itself
    try:
        text = event.widget.tk.call(
            "::tk::GetSelection", event.widget._w, "CLIPBOARD")
    except TclError:
        return
    event.widget.insert("insert", text)
    event.widget.tk.call("tk::EntrySeeInsert", event.widget._w)
    return "break"


# -----------------------------------------------------------------------------
def _textPaste(event):
    """global replacement for the Text.paste"""
    oldSeparator = event.widget.cget("autoseparators")
    if oldSeparator:
        event.widget.config(autoseparators=0)
        event.widget.edit_separator()
    try:
        event.widget.delete("sel.first", "sel.last")
    except TclError:
        pass  # nothing is selected

    # in tk.call() use the widget's string representation event.widget._w
    # instead of event.widget, which is the widget instance itself
    try:
        text = event.widget.tk.call(
            "::tk::GetSelection", event.widget._w, "CLIPBOARD")
    except TclError:
        return
    event.widget.insert("insert", text)
    if oldSeparator:
        event.widget.edit_separator()
        event.widget.config(autoseparators=1)
    event.widget.see("insert")
    return "break"


# -----------------------------------------------------------------------------
def bindClasses(root):
    root.bind_class(
        "Entry", "<Control-Key-a>", lambda e: e.widget.selection_range(0, END)
    )
    root.bind_class("Entry", "<<Paste>>", _entryPaste)
    root.bind_class("Text", "<<Paste>>", _textPaste)


# =============================================================================
# LabelEntry. display a label when entry field is empty
# =============================================================================
class LabelEntry(ttk.Entry):
    def __init__(self, master, label=None, labelcolor=None, **kw):
        for key in ("background", "bg", "foreground", "fg"):
            kw.pop(key, None)
        ttk.Entry.__init__(self, master, **kw)
        self.label = label
        self._empty = True
        self._fg = ""  # the style's text color
        self._labelcolor = labelcolor
        self.bind("<FocusIn>", self._focusIn)
        self.bind("<FocusOut>", self._focusOut)
        self["validate"] = "key"
        self["validatecommand"] = (self.register(self.validate), "%P")
        self.winfo_toplevel().bind(
            "<<AppearanceChanged>>", self._recolor, add="+")
        self.showLabel()

    # ----------------------------------------------------------------------
    @property
    def labelcolor(self):
        if self._labelcolor is not None:
            return self._labelcolor
        return (DARK if isDark(self) else LIGHT)["disabled"]

    # ----------------------------------------------------------------------
    def _recolor(self, event=None):
        if self._empty:
            self["foreground"] = self.labelcolor

    # ----------------------------------------------------------------------
    def showLabel(self):
        self.delete(0, END)
        self.insert(0, self.label)
        self["foreground"] = self.labelcolor
        self._empty = True  # Restore empty since validation will destroy it

    # ----------------------------------------------------------------------
    def removeLabel(self):
        self.delete(0, END)
        self["foreground"] = self._fg

    # ----------------------------------------------------------------------
    def _focusIn(self, event):
        if self._empty:
            self.removeLabel()

    # ----------------------------------------------------------------------
    def _focusOut(self, event):
        if self._empty or self.get() == "":
            self.showLabel()

    # ----------------------------------------------------------------------
    def validate(self, value):
        self._empty = value == ""
        return True

    # ----------------------------------------------------------------------
    def set(self, value):
        self._empty = value == ""
        if self._empty:
            self.showLabel()
            self.master.focus_set()  # lose focus
        else:
            self.removeLabel()
            self.insert(0, value)

    # ----------------------------------------------------------------------
    def get(self):
        if self._empty:
            return ""
        else:
            return ttk.Entry.get(self)


# =============================================================================
# _ValidatingEntry
# =============================================================================
class _ValidatingEntry(ttk.Entry):
    """base class for validating entry widgets"""

    # ----------------------------------------------------------------------
    def __init__(self, master, value="", **kw):
        # ttk has no per-widget disabledforeground, use a derived style
        color = kw.pop("disabledforeground", None)
        if color:
            kw["style"] = f"Disabled{color}.TEntry"
            ttk.Style(master).map(
                kw["style"], foreground=[("disabled", color)])
        ttk.Entry.__init__(self, master, **kw)
        self["validate"] = "key"
        self["validatecommand"] = (self.register(self.validate), "%P")

    # ----------------------------------------------------------------------
    def validate(self, value):
        # override: return True if valid False if invalid
        return True

    # ----------------------------------------------------------------------
    def set(self, value):
        self.delete(0, END)
        self.insert(0, value)

    # ----------------------------------------------------------------------
    def getint(self, default=0):
        try:
            return int(self.get())
        except Exception:
            return default

    # ----------------------------------------------------------------------
    def getfloat(self, default=0.0):
        try:
            return float(self.get())
        except Exception:
            return default


# =============================================================================
# Integer Validating Entry
# =============================================================================
class IntegerEntry(_ValidatingEntry):
    """IntegerEntry accepting only integers"""

    # ----------------------------------------------------------------------
    def validate(self, value):
        try:
            if value:
                int(value)
            return True
        except ValueError:
            if value == "+" or value == "-":
                return True
        return False


# =============================================================================
# Floating Point Validating Entry
# =============================================================================
class FloatEntry(_ValidatingEntry):
    """accept only floating point numbers"""

    # ----------------------------------------------------------------------
    def validate(self, value):
        try:
            if value:
                float(value)
            return True
        except ValueError:
            if (
                value == "+"
                or value == "-"
                or value == "."
                or value == "+."
                or value == "-."
            ):
                return True
            if len(value) > 1:
                last = value[-1]
                if last == "e" or last == "E":
                    return True
                plast = value[-2]
                if ((plast == "e" or plast == "E")
                        and (last == "-" or last == "+")):
                    return True
        return False


# =============================================================================
# ProgressBar Canvas
# =============================================================================
class ProgressBar(Canvas):
    def __init__(self, master=None, **kw):
        Canvas.__init__(self, master, **kw)
        self.currBox = self.create_rectangle(0, 0, 0, 0,
                                             fill="Orange", width=0)
        self.doneBox = self.create_rectangle(
            0, 0, 0, 0, fill="DarkGreen", width=0)
        self.text = self.create_text(
            0, 0, text="", fill="White", anchor=CENTER, justify=CENTER
        )
        self.auto = True
        self.showTime = True

        self.bind("<Configure>", self.draw)
        self.setLimits()

    # ----------------------------------------------------------------------
    def setAuto(self, auto):
        self.auto = auto

    # ----------------------------------------------------------------------
    def setShowTime(self, b):
        self.showTime = b

    # ----------------------------------------------------------------------
    def setStartTime(self, t0):
        self.t0 = t0

    # ----------------------------------------------------------------------
    def setLimits(self, low=0.0, high=100.0, step=1.0):
        self.low = float(low)
        self.high = float(high)
        self.length = float(high - low)
        self.step = float(step)
        self.done = float(low)
        self.now = float(low)
        self.t0 = time.time()
        self.msg = ""

    # ----------------------------------------------------------------------
    def setProgress(self, now, done=None, txt=None):
        self.now = now
        if self.now < self.low:
            self.now = self.low
        elif self.now > self.high:
            self.now = self.high

        if done is None:
            self.done = now - self.step
        else:
            self.done = done

        if self.done < self.low:
            self.done = self.low
        elif self.done > self.high:
            self.done = self.high

        # calculate remaining time
        dt = time.time() - self.t0
        p = now - self.low
        if p > 0:
            tot = dt / p * (self.high - self.low)
        else:
            tot = 0.0

        # elapsed time
        dh, s = divmod(dt, 3600)
        dm, ds = divmod(s, 60)
        if dh > 0:
            elapsedTxt = f"{int(dh)}h{int(dm):02d}m"
        elif dm > 0:
            elapsedTxt = f"{int(dm)}m{int(ds):02d}s"
        else:
            elapsedTxt = f"{int(ds)}s"

        # total time
        th, s = divmod(tot, 3600)
        tm, ts = divmod(s, 60)
        if th > 0:
            totalTxt = f"Tot: {int(th)}h{int(tm):02d}m"
        elif tm > 0:
            totalTxt = f"Tot: {int(tm)}m{int(ts):02d}s"
        else:
            totalTxt = f"Tot: {int(ts):02d}s"

        # remain time
        remain = tot - dt
        if remain > 0:
            rh, s = divmod(remain, 3600)
            rm, rs = divmod(s, 60)
            if rh > 0:
                remainTxt = f"Rem: {int(rh)}h{int(rm):02d}m"
            elif rm > 0:
                remainTxt = f"Rem: {int(rm)}m{int(rs):02d}s"
            else:
                remainTxt = f"Rem: {int(rs):02d}s"
        else:
            remainTxt = ""

        self.draw()
        if txt is not None:
            self.setText(txt)

        elif self.auto:
            if self.showTime:
                self.autoText(f"[{elapsedTxt} {totalTxt} {remainTxt}]")
            else:
                self.autoText("")

    # ----------------------------------------------------------------------
    def clear(self):
        self.setProgress(0, 0)

    # ----------------------------------------------------------------------
    def setText(self, txt):
        self.itemconfig(self.text, text=txt)

    # ----------------------------------------------------------------------
    def configText(self, **args):
        self.itemconfig(self.text, **args)

    # ----------------------------------------------------------------------
    def autoText(self, tmsg):
        completed = self.done - self.low
        if self.low != 0:
            low = f"{int(self.low)} - "
        else:
            low = ""
        self.msg = " ".join([
            f"Current: {int(self.now)} [{low}{int(self.high)}]",
            f"Completed: {int((100 * completed) / self.length)}% {tmsg}"
        ])

        self.setText(self.msg)

    # ----------------------------------------------------------------------
    def getProgress(self):
        return (self.done, self.now)

    # ----------------------------------------------------------------------
    def draw(self, event=None):
        width = self.winfo_width()
        height = self.winfo_height()

        wn = int(width * (self.now - self.low) / self.length)
        wd = int(width * (self.done - self.low) / self.length)
        if wd >= wn:
            wd = wn - 1

        self.coords(self.currBox, 0, 0, wn, height)
        self.coords(self.doneBox, 0, 0, wd, height)

        if self.itemcget(self.text, "justify") == CENTER:
            self.coords(self.text, width / 2, height / 2)
        else:
            self.coords(self.text, 1, height / 2)


# =============================================================================
# Class to edit in place the contents of a listbox
# =============================================================================
class InPlaceEdit:
    def __init__(self,
                 listbox,
                 item=ACTIVE,
                 value=None,
                 x=None,
                 select=True,
                 **kw):
        # Return value
        self.value = None  # Result
        self.frame = None
        self.lastkey = None  # Last key that exited the editbox
        self.kw = kw
        self._x = x
        self._select = select

        # Find active
        try:
            self.active = listbox.index(item)
        except Exception:
            return

        self.item = item
        self.listbox = listbox

        # Create and set value
        self.frame = ttk.Frame(listbox)
        self.createWidget()
        self.old = self.set(value)
        self.defaultBinds()

        # Bindings
        self.frame.bind("<FocusOut>", self.focusOut)
        # Unmap creates core dump when Fn key is pressed
        self.frame.bind("<ButtonRelease-1>", self.clickOk)
        self.frame.bind("<ButtonRelease-3>", self.clickCancel)
        self.listbox.bind("<Configure>", self.resize)

        try:
            self._grab_window = self.frame.grab_current()
        except TclError:
            self._grab_window = None
        self.resize()
        self.show()

    # ----------------------------------------------------------------------
    def show(self):
        # Show and wait to be destroyed
        try:
            self.frame.wait_visibility()
            self.frame.grab_set()
            self.icursor()
            self.frame.wait_window()
        except TclError:
            pass

    # ----------------------------------------------------------------------
    # Options of the classic widgets that ttk widgets do not have
    # ----------------------------------------------------------------------
    def _kw(self):
        skip = ("bg", "background", "fg", "foreground", "relief", "bd",
                "borderwidth", "highlightthickness", "disabledforeground")
        return {k: v for k, v in self.kw.items() if k not in skip}

    # ----------------------------------------------------------------------
    # Override method if another widget is requested
    # ----------------------------------------------------------------------
    def createWidget(self):
        self.edit = ttk.Entry(self.frame, **self._kw())
        self.edit.pack(expand=YES, fill=BOTH)
        self.edit.focus_set()

    # ----------------------------------------------------------------------
    # set insert cursor at location
    # ----------------------------------------------------------------------
    def icursor(self):
        if self._x is not None:
            self.edit.icursor(f"@{int(self._x)}")

    # ----------------------------------------------------------------------
    # Set default bindings
    # ----------------------------------------------------------------------
    def defaultBinds(self):
        try:
            self.edit.bind("<Return>", self.ok)
            self.edit.bind("<KP_Enter>", self.ok)
            self.edit.bind("<Up>", self.ok)
            self.edit.bind("<Down>", self.ok)
            self.edit.bind("<Escape>", self.cancel)
        except AttributeError:
            pass

    # ----------------------------------------------------------------------
    def resize(self, event=None):
        if self.frame is None:
            return
        bbox = self.listbox.bbox(self.item)
        if bbox is None:
            return
        x, y, w, h = bbox
        w = self.listbox.winfo_width() - x
        h += 3
        try:
            self.frame.place(
                in_=self.listbox,
                x=x - 1,
                y=y - 1,
                width=w,
                height=h,
                bordermode=OUTSIDE,
            )
            self.frame.update_idletasks()
        except TclError:
            pass

    # ----------------------------------------------------------------------
    # Override method to set the value
    # ----------------------------------------------------------------------
    def set(self, value):
        if self.frame is None:
            return
        if value is None:
            value = self.listbox.get(self.item)
        self.edit.delete(0, END)
        self.edit.insert(0, value)
        if self._select:
            self.edit.selection_range(0, END)
        return value

    # ----------------------------------------------------------------------
    # Override method to get the value
    # ----------------------------------------------------------------------
    def get(self):
        if self.frame is None:
            return None
        return self.edit.get()

    # ----------------------------------------------------------------------
    def reset_grab(self):
        if self.frame is None:
            return
        self.frame.grab_release()
        if self._grab_window is not None:
            try:
                self._grab_window.grab_set()
            except TclError:
                pass

    # ----------------------------------------------------------------------
    def clickOk(self, event):
        # If clicked outside return ok
        if (
            event.x < 0
            or event.y < 0
            or event.x > self.frame.winfo_width()
            or event.y > self.frame.winfo_height()
        ):
            self.ok(event)

    # ----------------------------------------------------------------------
    def clickCancel(self, event):
        # If clicked outside return cancel
        if (
            event.x < 0
            or event.y < 0
            or event.x > self.frame.winfo_width()
            or event.y > self.frame.winfo_height()
        ):
            self.cancel(event)

    # ----------------------------------------------------------------------
    def focusOut(self, event=None):
        self.ok()

    # ----------------------------------------------------------------------
    def updateValue(self):
        if isinstance(self.listbox, Listbox):
            self.listbox.delete(self.active)
            self.listbox.insert(self.active, self.value)
        elif isinstance(self.listbox, ListView):
            self.listbox.set(self.active, self.value)

    # ----------------------------------------------------------------------
    def ok(self, event=None):
        if event:
            self.lastkey = event.keysym
        self.value = self.get()
        self.frame.unbind("<FocusOut>")

        act = self.listbox.index(ACTIVE)
        sel = self.listbox.selection_includes(self.active)
        self.updateValue()
        self.listbox.see(self.active)

        if sel:
            self.listbox.selection_set(self.active)
        self.listbox.activate(act)
        if self.value == self.old:
            self.value = None

        self.reset_grab()
        self.listbox.focus_set()
        self.frame.place_forget()
        self.frame.destroy()
        return "break"

    # ----------------------------------------------------------------------
    def cancel(self, event=None):
        self.reset_grab()
        self.listbox.focus_set()
        self.frame.place_forget()
        self.frame.destroy()
        return "break"


# =============================================================================
class InPlaceInteger(InPlaceEdit):
    # ----------------------------------------------------------------------
    def createWidget(self):
        self.edit = IntegerEntry(self.frame, **self._kw())
        self.edit.pack(expand=YES, fill=BOTH)
        self.edit.focus_set()


# =============================================================================
class InPlaceFloat(InPlaceEdit):
    # ----------------------------------------------------------------------
    def createWidget(self):
        self.edit = FloatEntry(self.frame, **self._kw())
        self.edit.pack(expand=YES, fill=BOTH)
        self.edit.focus_set()


# =============================================================================
class InPlaceList(InPlaceEdit):
    def __init__(self,
                 listbox,
                 item=ACTIVE,
                 value=None,
                 height=None,
                 values=[],
                 **kw):
        self.values = values
        self.height = height
        InPlaceEdit.__init__(self, listbox, item, value, **kw)

    # ----------------------------------------------------------------------
    def createWidget(self):
        self.frame.config(relief=RAISED, borderwidth=1)
        sb = ttk.Scrollbar(self.frame)
        sb.pack(side=RIGHT, fill=Y)
        if self.height is None:
            if len(self.values) < 10:
                self.height = max(len(self.values) + 1, 3)
            else:
                self.height = 10
        self.edit = ListView(
            self.frame,
            style="Tool.Treeview",
            selectmode=BROWSE,
            height=self.height,
            yscrollcommand=sb.set,
        )
        self.edit.tag_configure("row", font="TkDefaultFont")
        sb.config(command=self.edit.yview)
        self.edit.pack(side=LEFT, fill=BOTH, expand=YES)
        self.edit.bind("<ButtonRelease-1>", self.ok)
        self.edit.focus_set()

    # ----------------------------------------------------------------------
    def set(self, value):
        if value is None:
            value = self.listbox.get(self.item)

        # Fill&select listbox
        for item in self.values:
            self.edit.insert(END, item)
            if item == value:
                self.edit.activate(END)
                self.edit.selection_set(END)
        if len(self.edit.curselection()) == 0:
            self.edit.activate(0)
        self.edit.see(ACTIVE)
        return value

    # ----------------------------------------------------------------------
    def get(self):
        cur = self.edit.curselection()
        if len(cur) > 0:
            return self.edit.get(cur[0])
        else:
            return ""

    # ----------------------------------------------------------------------
    def defaultBinds(self):
        InPlaceEdit.defaultBinds(self)
        try:
            self.edit.unbind("<Up>")
            self.edit.unbind("<Down>")
        except AttributeError:
            pass

    # ----------------------------------------------------------------------
    def resize(self, event=None):
        if self.frame is None:
            return
        bbox = self.listbox.bbox(self.item)
        if bbox is None:
            return
        x, y, item_width, item_height = bbox
        list_width = self.listbox.winfo_width()
        list_height = self.listbox.winfo_height()
        h = item_height * self.height + 2

        if y + h > list_height:
            y = list_height - h
            if y <= 0:
                y = 0
                h = list_height

        try:
            self.frame.place(
                in_=self.listbox,
                x=x - 1,
                y=y,
                width=list_width,
                height=h,
                bordermode=OUTSIDE,
            )
            self.frame.update_idletasks()
        except TclError:
            pass


# =============================================================================
class InPlaceColor(InPlaceEdit):
    # ----------------------------------------------------------------------
    def createWidget(self):
        # Placeholder for get()/ok(); picker opens immediately in show()
        self.edit = ttk.Label(self.frame)
        self.edit.pack(expand=YES, fill=BOTH)

    # ----------------------------------------------------------------------
    def set(self, value):
        if value is None:
            value = self.listbox.get(self.item)
        self.value = value
        if value:
            try:
                self.edit.config(text=value, background=value)
            except TclError:
                pass
        return value

    # ----------------------------------------------------------------------
    def get(self):
        return self.value

    # ----------------------------------------------------------------------
    def show(self):
        # Open the color picker on first click; apply or cancel immediately
        try:
            self.frame.wait_visibility()
            self.selectColor()
            if self.frame is not None:
                try:
                    if self.frame.winfo_exists():
                        self.frame.wait_window()
                except TclError:
                    pass
        except TclError:
            pass

    # ----------------------------------------------------------------------
    def selectColor(self):
        try:
            self.frame.unbind("<FocusOut>")
            self.frame.grab_release()
        except TclError:
            pass

        initial = self.value if self.value else "White"
        try:
            rgb, colorStr = askcolor(
                title="Color",
                initialcolor=initial,
                parent=self.listbox.master
            )
        except TclError:
            colorStr = None

        if colorStr is not None:
            self.value = str(colorStr)
            try:
                self.edit.config(
                    text=self.value, background=self.value
                )
            except TclError:
                pass
            self.ok()
        else:
            self.value = None
            self.cancel()


# =============================================================================
class InPlaceText(InPlaceEdit):
    # ----------------------------------------------------------------------
    def show(self):
        self.toplevel.bind("<FocusOut>", self.focusOut)
        try:
            self.toplevel.wait_visibility()
            self.toplevel.grab_set()
            self.toplevel.wait_window()
        except TclError:
            pass

    # ----------------------------------------------------------------------
    def defaultBinds(self):
        InPlaceEdit.defaultBinds(self)
        self.toplevel.bind("<ButtonRelease-1>", self.clickOk)
        self.toplevel.bind("<ButtonRelease-3>", self.clickCancel)
        self.edit.bind("<Shift-Return>", self.shiftReturn)
        self.edit.bind("<Escape>", self.cancel)

    # ----------------------------------------------------------------------
    def createWidget(self):
        self.toplevel = Toplevel(self.listbox)
        self.toplevel.transient(self.listbox)
        if sys.platform in ("win32", "win64"):
            self.toplevel.update_idletasks()
        self.toplevel.overrideredirect(1)
        self.edit = Text(self.toplevel, width=70, height=10, undo=True)
        themeText(self.edit)
        self.edit.pack(side=LEFT, expand=YES, fill=BOTH)
        self.edit.focus_set()

    # ----------------------------------------------------------------------
    def resize(self, event=None):
        if self.frame is None:
            return
        bbox = self.listbox.bbox(self.item)
        if bbox is None:
            return
        x, y, w, h = bbox
        x += self.listbox.winfo_rootx()
        y += self.listbox.winfo_rooty()
        try:
            self.toplevel.wm_geometry(f"+{int(x)}+{int(y)}")
        except TclError:
            pass

    # ----------------------------------------------------------------------
    def set(self, value):
        if self.frame is None:
            return
        if value is None:
            value = self.listbox.get(self.item)
        self.edit.delete("0.0", END)
        self.edit.insert("0.0", value)
        self.edit.tag_add(SEL, "0.0", END)
        return value

    # ----------------------------------------------------------------------
    def get(self):
        if self.frame is None:
            return None
        return self.edit.get("0.0", END).strip()

    # ----------------------------------------------------------------------
    def shiftReturn(self, event):
        # Empty binding to avoid the Shift-Return to trigger the "ok"
        pass

    # ----------------------------------------------------------------------
    def clickOk(self, event):
        # If clicked outside return ok
        if (
            event.x < 0
            or event.y < 0
            or event.x > self.toplevel.winfo_width()
            or event.y > self.toplevel.winfo_height()
        ):
            self.ok(event)

    # ----------------------------------------------------------------------
    def clickCancel(self, event):
        # If clicked outside return cancel
        if (
            event.x < 0
            or event.y < 0
            or event.x > self.toplevel.winfo_width()
            or event.y > self.toplevel.winfo_height()
        ):
            self.cancel(event)

    # ----------------------------------------------------------------------
    def ok(self, event=None):
        InPlaceEdit.ok(self, event)
        self.toplevel.destroy()
        return "break"

    # ----------------------------------------------------------------------
    def cancel(self, event=None):
        InPlaceEdit.cancel(self, event)
        self.toplevel.destroy()
        return "break"


# =============================================================================
class InPlaceFile(InPlaceEdit):
    # ----------------------------------------------------------------------
    def __init__(
        self,
        listbox,
        item=ACTIVE,
        value=None,
        title=None,
        filetypes=None,
        save=True,
        **kw,
    ):
        self.title = title
        self.filetypes = filetypes
        self._save = save
        self._icon = PhotoImage(data=_SAVEICON)
        InPlaceEdit.__init__(self, listbox, item, value, **kw)

    # ----------------------------------------------------------------------
    def createWidget(self):
        self.edit = ttk.Entry(self.frame, width=5, **self._kw())
        self.edit.pack(side=LEFT, expand=YES, fill=BOTH)
        b = ttk.Button(
            self.frame,
            image=self._icon,
            width=0,
            command=self.fileDialog
        )
        b.pack(side=RIGHT)
        self.edit.focus_set()

    # ----------------------------------------------------------------------
    def fileDialog(self):
        self.frame.unbind("<FocusOut>")
        self.frame.grab_release()
        if self.value is None:
            filename = self.listbox.get(self.item)
        else:
            filename = self.value
        if self._save:
            fn = bFileDialog.asksaveasfilename(
                master=self.listbox,
                title=self.title,
                initialfile=filename,
                filetypes=self.filetypes,
            )
        else:
            fn = bFileDialog.askopenfilename(
                master=self.listbox,
                title=self.title,
                initialfile=filename,
                filetypes=self.filetypes,
            )
        self.frame.grab_set()
        self._icon = None
        if len(fn) > 0:
            self.edit.delete(0, END)
            self.edit.insert(0, fn)
            self.ok()
        else:
            self.cancel()


# =============================================================================
# Display a balloon message (only static methods)
# =============================================================================
class Balloon:
    _top = None
    _widget = None
    font = ("Helvetica", "-12")
    foreground = "Black"
    background = "LightYellow"
    delay = 1500
    x_mouse = 0
    y_mouse = 0

    # ----------------------------------------------------------------------
    # set a balloon message to a widget
    # ----------------------------------------------------------------------
    @staticmethod
    def set(widget, help):  # noqa: A002
        widget._help = help
        widget.bind("<Any-Enter>", Balloon.enter)
        widget.bind("<Any-Leave>", Balloon.leave)
        widget.bind("<Key>", Balloon.hide)

    # ----------------------------------------------------------------------
    @staticmethod
    def enter(event):
        if Balloon._widget is event.widget:
            return
        Balloon._widget = event.widget
        Balloon.x_mouse = event.x_root
        Balloon.y_mouse = event.y_root
        return event.widget.after(Balloon.delay, Balloon.show)

    # ----------------------------------------------------------------------
    @staticmethod
    def leave(event=None):
        Balloon._widget = None
        if Balloon._top is None:
            return
        try:
            if Balloon._top.winfo_ismapped():
                Balloon._top.withdraw()
        except TclError:
            Balloon._top = None

    hide = leave

    # ----------------------------------------------------------------------
    @staticmethod
    def setWidget(widget, x, y):
        Balloon._widget = widget
        Balloon.x_mouse = x
        Balloon.y_mouse = y

    # ----------------------------------------------------------------------
    @staticmethod
    def show():
        try:
            if Balloon._widget is None:
                return
            widget = Balloon._widget
            if Balloon._top is None:
                Balloon._top = Toplevel()
                Balloon._top.overrideredirect(1)
                Balloon._msg = ttk.Label(
                    Balloon._top,
                    wraplength=300,
                    padding=2,
                    foreground=Balloon.foreground,
                    background=Balloon.background,
                    relief=SOLID,
                    borderwidth=1,
                    font=Balloon.font,
                )
                Balloon._msg.pack()
                Balloon._top.bind("<1>", Balloon.hide)
                # the first mapping of the window has rounded corners
                Balloon._top.wm_attributes("-alpha", 0)
                Balloon._top.update()
                Balloon._top.withdraw()
                Balloon._top.wm_attributes("-alpha", 1)
            c = DARK if isDark(widget) else LIGHT
            Balloon._msg.config(
                text=widget._help, foreground=c["tipfg"], background=c["tipbg"])
            # Guess position
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            # if too far away use mouse
            if abs(x - Balloon.x_mouse) > 30:
                x = Balloon.x_mouse + 20
            if abs(y - Balloon.y_mouse) > 30:
                y = Balloon.y_mouse + 10
            Balloon._top.wm_geometry(f"+{int(x)}+{int(y)}")
            Balloon._top.deiconify()
            Balloon._top.lift()
            Balloon._top.update_idletasks()

            # Check if it is hidden on bottom-right sides
            move = False
            if (
                Balloon._top.winfo_rootx() + Balloon._top.winfo_width()
                >= Balloon._top.winfo_screenwidth()
            ):
                x = Balloon._top.winfo_screenwidth() - \
                    Balloon._top.winfo_width() - 20
                move = True
            if (
                Balloon._top.winfo_rooty() + Balloon._top.winfo_height()
                >= Balloon._top.winfo_screenheight()
            ):
                y = Balloon._top.winfo_screenheight() - \
                    Balloon._top.winfo_height() - 10
                move = True
            if move:
                Balloon._top.wm_geometry(f"+{int(x)}+{int(y)}")

        except TclError:
            Balloon._top = None


# =============================================================================
# A LabelFrame that can collapse/expand
# =============================================================================
class ExLabelFrame(ttk.LabelFrame):
    def __init__(self, master, *args, **kwargs):
        kwargs.pop("foreground", None)
        if "command" in kwargs:
            self.command = kwargs.get("command")
            del kwargs["command"]
        else:
            self.command = None

        ttk.LabelFrame.__init__(self, master, *args, **kwargs)
        self.frame = ttk.Frame(self)
        self.frame.pack(expand=YES, fill=BOTH)
        self.bind("<Button-1>", self.click)
        if self["height"] == 0:
            self["height"] = 20
        self.width = self["width"]

    # ----------------------------------------------------------------------
    def click(self, event=None):
        if self.frame.winfo_ismapped():
            self.collapse()
        else:
            self.expand()
        if self.command is not None:
            self.command(event)

    # ----------------------------------------------------------------------
    def collapse(self):
        self["width"] = self.winfo_width()
        self.frame.pack_forget()
        lbl = self["text"]
        if lbl[-1] in (
            Unicode.BLACK_UP_POINTING_TRIANGLE,
            Unicode.BLACK_DOWN_POINTING_TRIANGLE,
        ):
            lbl = lbl[:-1]
        self["text"] = lbl + Unicode.BLACK_UP_POINTING_TRIANGLE

    # ----------------------------------------------------------------------
    def expand(self):
        self["width"] = self.width
        self.frame.pack(fill=BOTH)
        lbl = self["text"]
        if lbl[-1] in (
            Unicode.BLACK_UP_POINTING_TRIANGLE,
            Unicode.BLACK_DOWN_POINTING_TRIANGLE,
        ):
            self["text"] = lbl[:-1]

    # ----------------------------------------------------------------------
    def isexpanded(self):
        return self.frame.winfo_ismapped()

    # ----------------------------------------------------------------------
    def __call__(self):
        return self.frame


# =============================================================================
# =============================================================================
class TtkCombobox(ttk.Combobox):
    def __init__(self, master, command=None, **kw):
        ttk.Combobox.__init__(self, master, **kw)
        self._readonly = kw.get("state") == "readonly"
        if command is not None:
            self.bind("<<ComboboxSelected>>", lambda e: command())

    # ----------------------------------------------------------------------
    def fill(self, values):
        # values may be an iterator (e.g. map), Tk needs a real sequence
        self["values"] = list(values)

    # ----------------------------------------------------------------------
    # enabling (state normal) a readonly combobox keeps it readonly
    def configure(self, cnf=None, **kw):
        if self._readonly:
            for d in (cnf, kw):
                if isinstance(d, dict) and d.get("state") == "normal":
                    d["state"] = "readonly"
        if "command" in kw:
            command = kw.pop("command")
            self.bind("<<ComboboxSelected>>", lambda e: command())
        return ttk.Combobox.configure(self, cnf, **kw)

    config = configure


# =============================================================================
# Combobox, the list is filled with insert() or fill()
# =============================================================================
class Combobox(TtkCombobox):
    def __init__(self, master, label=True, *args, **kw):
        for key in ("background", "foreground", "anchor", "justify"):
            kw.pop(key, None)
        TtkCombobox.__init__(
            self, master, state="readonly" if label else "normal", **kw)

    # ----------------------------------------------------------------------
    def insert(self, index, *elements):
        self["values"] = list(self["values"]) + list(elements)

    # ----------------------------------------------------------------------
    def get(self, first=None, last=None):
        if first is None:
            return TtkCombobox.get(self)
        return self["values"][first]


# =============================================================================
# ttk.Scale with a value label and optional resolution (snapping)
# =============================================================================
class ValueScale(ttk.Frame):
    def __init__(self, master, from_=0, to=100, resolution=1, variable=None,
                 command=None, orient=HORIZONTAL, **kw):
        ttk.Frame.__init__(self, master)
        to = float(kw.pop("to_", to))  # the config gives strings
        from_ = float(from_)
        self._resolution = resolution
        self._command = command
        self._variable = variable
        self._range = (from_, to)
        self.value = ttk.Label(self, width=4, anchor=E)
        self.value.pack(side=LEFT)
        self.scale = ttk.Scale(self, from_=from_, to=max(to, from_ + 1),
                               orient=orient, variable=variable,
                               command=self._changed, **kw)
        self.scale.pack(side=LEFT, fill=X, expand=YES)
        if variable is not None:
            variable.trace_add("write", lambda *a: self._showValue())
        self._showValue()

    # ----------------------------------------------------------------------
    def _snap(self, value):
        value = float(value)
        res = self._resolution
        if res:
            low = float(self._range[0])
            value = low + round((value - low) / res) * res
        return int(value) if value == int(value) else value

    # ----------------------------------------------------------------------
    def _showValue(self):
        try:
            self.value.config(text=str(self._snap(self.scale.get())))
        except (TclError, ValueError):
            pass

    # ----------------------------------------------------------------------
    def _changed(self, value):
        value = self._snap(value)
        if self._variable is not None and self.scale.get() != value:
            self._variable.set(value)
        self._showValue()
        if self._command is not None:
            self._command(str(value))

    # ----------------------------------------------------------------------
    def configure(self, cnf=None, **kw):
        kw.update(cnf or {})
        if "resolution" in kw:
            self._resolution = kw.pop("resolution")
        for key in ("to_", "from_"):
            if key in kw:
                kw[key[:-1]] = kw.pop(key)
        if "from" in kw or "to" in kw:
            # an empty range would put the handle on the right, keep the
            # real range here and give the scale a usable one
            low, high = self._range
            low = float(kw.pop("from", low))
            high = float(kw.pop("to", high))
            self._range = (low, high)
            self.scale.configure(**{"from": low, "to": max(high, low + 1)})
        if kw:
            self.scale.configure(**kw)
        self._showValue()

    config = configure

    # ----------------------------------------------------------------------
    def cget(self, key):
        if key in ("from", "to"):
            return float(self._range[key == "to"])
        return self.scale.cget(key)

    def get(self):
        return self._snap(self.scale.get())

    def set(self, value):
        self.scale.set(value)

    def bind(self, sequence=None, func=None, add=None):
        return self.scale.bind(sequence, func, add)

    # Balloon binds through bind() above, so events come from the inner scale
    @property
    def _help(self):
        return self.scale._help

    @_help.setter
    def _help(self, text):
        self.scale._help = text


# =============================================================================
# ttk.Treeview used as a Listbox: one text column, Listbox style methods
# =============================================================================
class ListView(ttk.Treeview):
    # color names used by the application, mapped to theme colors
    _SEMANTIC = {"Blue": "sent", "Red": "error", "Magenta": "info",
                 "Gray": "disabled", "LightYellow": "buffer"}
    textOffset = 8  # distance of the text from the left edge of a row

    def __init__(self, master, selectmode="extended", font=None, **kw):
        kw.setdefault("show", "tree")
        for key in ("exportselection", "background", "bg"):
            kw.pop(key, None)
        ttk.Treeview.__init__(
            self, master, columns=(), selectmode=selectmode, **kw)
        self.column("#0", stretch=True, width=100)
        self._iids = []
        self._colors = {}  # tag -> (foreground, background) as requested
        self._itemColors = {}  # item id -> (foreground, background)
        self._quiet = False
        self.tag_configure("row", font=font or listFont())
        self.winfo_toplevel().bind(
            "<<AppearanceChanged>>", self._recolor, add="+")
        # same virtual event as a Listbox, only for changes by the user
        self.bind("<<TreeviewSelect>>", self._selected, add="+")

    # ----------------------------------------------------------------------
    def _index(self, index, insert=False):
        if index == END:
            return len(self._iids) if insert else len(self._iids) - 1
        if index == ACTIVE:
            focus = self.focus()
            return self._iids.index(focus) if focus in self._iids else 0
        return int(index)

    # ----------------------------------------------------------------------
    def _color(self, color):
        name = self._SEMANTIC.get(color)
        if name is None:
            return color
        return (DARK if isDark(self) else LIGHT)[name]

    # ----------------------------------------------------------------------
    def _recolor(self, event=None):
        for tag, (color, back) in self._colors.items():
            options = {}
            if color:
                options["foreground"] = self._color(color)
            if back:
                options["background"] = self._color(back)
            if options:
                self.tag_configure(tag, **options)

    # ----------------------------------------------------------------------
    def _selected(self, event=None):
        if not self._quiet:
            self.event_generate("<<ListboxSelect>>")

    # ----------------------------------------------------------------------
    def _silently(self, func, *args):
        """Selection changes by the program do not send <<ListboxSelect>>"""
        self._quiet = True
        try:
            func(*args)
        finally:
            self.after_idle(self._unquiet)

    def _unquiet(self):
        self._quiet = False

    # ----------------------------------------------------------------------
    def configure(self, cnf=None, **kw):
        kw.update(cnf or {})
        if "state" in kw:
            self.state(["!disabled"] if kw.pop("state") != DISABLED
                       else ["disabled"])
        if kw:
            return ttk.Treeview.configure(self, **kw)

    config = configure

    def __setitem__(self, key, value):
        if key == "state":
            self.configure(state=value)
        else:
            ttk.Treeview.__setitem__(self, key, value)

    # ----------------------------------------------------------------------
    def insert(self, index, *items):
        pos = min(self._index(index, True), len(self._iids))
        for text in items:
            iid = ttk.Treeview.insert(
                self, "", pos, text=str(text), tags=("row",))
            self._iids.insert(pos, iid)
            pos += 1

    # ----------------------------------------------------------------------
    def delete(self, first, last=None):
        a = self._index(first)
        b = a if last is None else self._index(last)
        iids = self._iids[a:b + 1]
        if iids:
            ttk.Treeview.delete(self, *iids)
            del self._iids[a:b + 1]
            for iid in iids:
                self._itemColors.pop(iid, None)

    # ----------------------------------------------------------------------
    def get(self, first, last=None):
        a = self._index(first)
        if last is None:
            return self.item(self._iids[a], "text")
        b = self._index(last)
        return tuple(self.item(i, "text") for i in self._iids[a:b + 1])

    # ----------------------------------------------------------------------
    def size(self):
        return len(self._iids)

    # ----------------------------------------------------------------------
    def itemconfig(self, index, **kw):
        i = self._index(index)
        if not 0 <= i < len(self._iids):
            return
        iid = self._iids[i]
        # options accumulate like in a Listbox
        color, back = self._itemColors.get(iid, (None, None))
        color = kw.get("foreground", color)
        back = kw.get("background", back)
        self._itemColors[iid] = (color, back)
        if color or back:
            tag = f"c_{color}_{back}"
            self._colors[tag] = (color, back)
            self._recolor()
            self.item(iid, tags=("row", tag))


    # ----------------------------------------------------------------------
    def see(self, index):
        i = self._index(index)
        if 0 <= i < len(self._iids):
            ttk.Treeview.see(self, self._iids[i])

    # ----------------------------------------------------------------------
    def curselection(self):
        selected = set(self.selection())
        return tuple(i for i, iid in enumerate(self._iids) if iid in selected)

    # ----------------------------------------------------------------------
    # Listbox style selection and cursor handling (indices, not item ids)
    # ----------------------------------------------------------------------
    def activate(self, index):
        i = self._index(index)
        if 0 <= i < len(self._iids):
            self.focus(self._iids[i])

    # ----------------------------------------------------------------------
    def selection_set(self, first, last=None):
        a = self._index(first)
        b = a if last is None else self._index(last)
        self._silently(ttk.Treeview.selection_set, self, self._iids[a:b + 1])

    # ----------------------------------------------------------------------
    def selection_clear(self, first=None, last=None):
        self._silently(ttk.Treeview.selection_remove, self, self._iids)

    # ----------------------------------------------------------------------
    def selection_includes(self, index):
        i = self._index(index)
        return 0 <= i < len(self._iids) and self._iids[i] in self.selection()

    # ----------------------------------------------------------------------
    def index(self, index):
        return self._index(index)

    # ----------------------------------------------------------------------
    def nearest(self, y):
        iid = self.identify_row(y)
        if iid in self._iids:
            return self._iids.index(iid)
        return max(len(self._iids) - 1, 0)

    # ----------------------------------------------------------------------
    def bbox(self, index, column=None):
        i = self._index(index)
        if not 0 <= i < len(self._iids):
            return None
        box = ttk.Treeview.bbox(self, self._iids[i], column or "#0")
        return tuple(box) if box else None

    # ----------------------------------------------------------------------
    def set(self, index, text):
        i = self._index(index)
        if 0 <= i < len(self._iids):
            self.item(self._iids[i], text=str(text))

    # ----------------------------------------------------------------------
    def listbox(self, i=0):
        return self

    # ----------------------------------------------------------------------
    def popupMenu(self, event):
        i = self.nearest(event.y)
        menu = Menu(self, tearoff=0)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(self.get(i))
        menu.add_command(label="Copy", command=copy)
        menu.tk_popup(event.x_root, event.y_root)
        return "break"


# =============================================================================
# Two column list (name, value) for the tools; Listbox style access is by the
# value column, as the in-place editors and the tools work on the value
# =============================================================================
class ToolList(ListView):
    def __init__(self, master, **kw):
        kw.setdefault("selectmode", "browse")
        kw.setdefault("style", "Tool.Treeview")
        ListView.__init__(self, master, **kw)
        self.configure(columns=("value",))
        self.column("#0", stretch=False, width=190, minwidth=60)
        self.column("value", stretch=True, width=120)
        self.tag_configure("row", font="TkDefaultFont")
        self._raw = {}  # item id -> full value
        self.sortAssist = None
        # a Treeview without headings can not resize its columns, so the
        # border between the two columns is a handle that can be dragged
        self._divider = []
        for style in ("Divider.TFrame", "DividerLight.TFrame"):
            line = ttk.Frame(self, style=style, width=1, cursor="sb_h_double_arrow")
            line.bind("<B1-Motion>", self._dragDivider)
            self._divider.append(line)
        self.bind("<Configure>", self._placeDivider, add="+")

    # ----------------------------------------------------------------------
    def _placeDivider(self, event=None):
        x = int(self.column("#0", "width"))
        self._divider[0].place(x=x, y=0, relheight=1, width=1)
        self._divider[1].place(x=x + 1, y=0, relheight=1, width=1)

    # ----------------------------------------------------------------------
    def _dragDivider(self, event):
        x = event.x_root - self.winfo_rootx()
        x = max(60, min(x, self.winfo_width() - 60))
        self.column("#0", width=x)
        self._placeDivider()

    # ----------------------------------------------------------------------
    def insert(self, index, item):
        name, value = item
        pos = min(self._index(index, True), len(self._iids))
        iid = ttk.Treeview.insert(self, "", pos, text=str(name),
                                  values=(self._shown(value),), tags=("row",))
        self._iids.insert(pos, iid)
        self._raw[iid] = str(value)

    # ----------------------------------------------------------------------
    def get(self, first, last=None):
        return self._raw[self._iids[self._index(first)]]

    def row(self, index):
        i = self._index(index)
        return (self.item(self._iids[i], "text"), self._raw[self._iids[i]])

    # ----------------------------------------------------------------------
    @staticmethod
    def _shown(value):
        """Multi line values are shown on one line"""
        return str(value).replace("\r", "").replace("\n", " ")

    # ----------------------------------------------------------------------
    def delete(self, first, last=None):
        a = self._index(first)
        b = a if last is None else self._index(last)
        for iid in self._iids[a:b + 1]:
            self._raw.pop(iid, None)
        ListView.delete(self, first, last)

    # ----------------------------------------------------------------------
    def set(self, index, text):
        i = self._index(index)
        if 0 <= i < len(self._iids):
            self._raw[self._iids[i]] = str(text)
            self.item(self._iids[i], values=(self._shown(text),))

    # ----------------------------------------------------------------------
    def bbox(self, index, column="value"):
        return ListView.bbox(self, index, column)

    # ----------------------------------------------------------------------
    def bindList(self, sequence, func):
        return self.bind(sequence, func)

    # ----------------------------------------------------------------------
    def bindValue(self, sequence, func):
        """Binding that only reacts on the value column"""
        def handler(event):
            if event.type != "2" and self.identify_column(event.x) != "#1":
                return None
            return func(event)
        return self.bind(sequence, handler)

    # ----------------------------------------------------------------------
    def itemconfig(self, index, **kw):
        back = kw.get("background")
        if back:
            # contrasting text on the colored row
            try:
                r, g, b = (v // 256 for v in self.winfo_rgb(back))
                kw["foreground"] = "#000000" if (r * 299 + g * 587 + b * 114) \
                    > 128000 else "#FFFFFF"
            except TclError:
                return
        ListView.itemconfig(self, index, **kw)


# =============================================================================
# Multi column list with sortable headers for the file dialog. Items are rows
# (tuples); the first column is the one in the tree column
# =============================================================================
class FileList(ListView):
    def __init__(self, master, columns, height=20, selectmode="browse", **kw):
        kw.setdefault("style", "Tool.Treeview")
        kw["show"] = "tree headings"
        ListView.__init__(self, master, selectmode=selectmode,
                          height=height, **kw)
        self.configure(columns=[f"c{i}" for i in range(1, len(columns))])
        self.tag_configure("row", font="TkDefaultFont")
        self._titles = [title for title, _w, _a in columns]
        self._rows = {}  # item id -> row
        self._sortColumn = -1
        self._sortReverse = False
        measure = tkfont.nametofont("TkDefaultFont").measure("0")
        for i, (title, width, _a) in enumerate(columns):
            col = "#0" if i == 0 else f"c{i}"
            self.column(col, width=width * measure, stretch=i == 0)
            self.heading(col, text=title,
                         command=lambda i=i: self.sort(i))
        self.bind("<Button-3>", self._popup, add="+")
        self._menu = None

    # ----------------------------------------------------------------------
    def _color(self, color):
        """The color, darkened (light) or lightened (dark) until it can be
        read on the rows (4.5:1) and on the selected row (3:1)"""
        color = ListView._color(self, color)
        c = DARK if isDark(self) else LIGHT
        backs = [[v / 65535 for v in self.winfo_rgb(c[k])]
                 for k in ("field", "selected")]
        target = [1.0, 1.0, 1.0] if isDark(self) else [0.0, 0.0, 0.0]
        rgb = [v / 65535 for v in self.winfo_rgb(color)]

        def lum(rgb):
            lin = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
                   for v in rgb]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def contrast(a, b):
            hi, lo = max(lum(a), lum(b)), min(lum(a), lum(b))
            return (hi + 0.05) / (lo + 0.05)

        for step in range(21):
            mixed = [v + (t - v) * step / 20 for v, t in zip(rgb, target)]
            if (contrast(mixed, backs[0]) >= 4.5
                    and contrast(mixed, backs[1]) >= 3):
                break
        return "#%02x%02x%02x" % tuple(int(v * 255) for v in mixed)

    # ----------------------------------------------------------------------
    def insert(self, index, *rows):
        pos = min(self._index(index, True), len(self._iids))
        for row in rows:
            iid = ttk.Treeview.insert(
                self, "", pos, text=str(row[0]),
                values=[str(v) for v in row[1:]], tags=("row",))
            self._iids.insert(pos, iid)
            self._rows[iid] = tuple(row)
            pos += 1

    # ----------------------------------------------------------------------
    def delete(self, first, last=None):
        a = self._index(first)
        b = a if last is None else self._index(last)
        for iid in self._iids[a:b + 1]:
            self._rows.pop(iid, None)
        ListView.delete(self, first, last)

    # ----------------------------------------------------------------------
    def get(self, first, last=None):
        a = self._index(first)
        if last is None:
            return self._rows[self._iids[a]]
        b = self._index(last)
        return tuple(self._rows[i] for i in self._iids[a:b + 1])

    # ----------------------------------------------------------------------
    def set(self, index, text):
        i = self._index(index)
        if 0 <= i < len(self._iids):
            iid = self._iids[i]
            self._rows[iid] = (str(text),) + self._rows[iid][1:]
            self.item(iid, text=str(text))

    # ----------------------------------------------------------------------
    def setColor(self, index, color):
        self.itemconfig(index, foreground=color)

    # ----------------------------------------------------------------------
    def bindList(self, sequence, func):
        return self.bind(sequence, func)

    # ----------------------------------------------------------------------
    def sort(self, column, reverse=None):
        """Sort by a column; clicking the same one again reverses it"""
        if reverse is None:
            reverse = column == self._sortColumn and not self._sortReverse
        order = sorted(
            range(len(self._iids)), reverse=reverse,
            key=lambda i: self._rows[self._iids[i]][column])
        iids = [self._iids[i] for i in order]
        for pos, iid in enumerate(iids):
            self.move(iid, "", pos)
        self._iids[:] = iids
        for i, title in enumerate(self._titles):
            mark = ""
            if i == column:
                mark = " " + (Unicode.BLACK_DOWN_POINTING_TRIANGLE if reverse
                              else Unicode.BLACK_UP_POINTING_TRIANGLE)
            self.heading("#0" if i == 0 else f"c{i}", text=title + mark)
        self._sortColumn = column
        self._sortReverse = reverse
        self.event_generate("<<ListboxSort>>")

    # ----------------------------------------------------------------------
    def saveSort(self):
        return self._sortColumn, self._sortReverse

    # ----------------------------------------------------------------------
    def restoreSort(self, arg):
        if arg[0] >= 0:
            self.sort(*arg)

    # ----------------------------------------------------------------------
    def widths(self):
        return [self.column("#0", "width")] + [
            self.column(f"c{i}", "width") for i in range(1, len(self._titles))]

    # ----------------------------------------------------------------------
    def setWidths(self, widths):
        for i, width in enumerate(widths):
            self.column("#0" if i == 0 else f"c{i}", width=width)

    # ----------------------------------------------------------------------
    def setPopupMenu(self, items):
        self._menu = items

    # ----------------------------------------------------------------------
    def _popup(self, event):
        if not self._menu:
            return None
        iid = self.identify_row(event.y)
        if iid in self._iids:
            self.selection_set(self._iids.index(iid))
            self.activate(self._iids.index(iid))
        menu = Menu(self, tearoff=0)
        for label, underline, command in self._menu:
            menu.add_command(label=label, underline=underline,
                             command=command)
        menu.tk_popup(event.x_root, event.y_root)
        return "break"


# =============================================================================
class Separator(ttk.Frame):
    """The ttk separator draws its own bright 3D lines, this is one flat line"""

    def __init__(self, master, **kw):
        ttk.Frame.__init__(self, master, style="Separator.TFrame", width=1,
                           **kw)


# =============================================================================
class TtkProgressBar(ttk.Frame):
    """Progress bar with a text label on top, see ProgressBar"""

    setAuto = ProgressBar.setAuto
    setShowTime = ProgressBar.setShowTime
    setStartTime = ProgressBar.setStartTime
    setLimits = ProgressBar.setLimits
    setProgress = ProgressBar.setProgress
    getProgress = ProgressBar.getProgress
    autoText = ProgressBar.autoText
    clear = ProgressBar.clear

    def __init__(self, master, width=1, height=20):
        ttk.Frame.__init__(self, master, width=width, height=height)
        self.bar = ttk.Progressbar(self, maximum=100)
        self.bar.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.label = ttk.Label(self, style="Progress.TLabel", padding=0)
        self.label.place(relx=0.5, rely=0.5, relheight=1, height=-2, anchor="center")
        # drawn instead of the above while a program is running
        self.canvas = ProgressBar(self, height=height, highlightthickness=0)
        self.running = False
        self.auto = True
        self.showTime = True
        self.setLimits()
        self.winfo_toplevel().bind(
            "<<AppearanceChanged>>", self._appearanceChanged, add="+"
        )

    # ----------------------------------------------------------------------
    def _appearanceChanged(self, event=None):
        if self.running:
            self.canvas.config(background=self._emptyColor())

    # ----------------------------------------------------------------------
    def _emptyColor(self):
        return DARK["field"] if isDark(self) else "DarkGray"

    # ----------------------------------------------------------------------
    def draw(self, event=None):
        self.bar["value"] = 100 * (self.done - self.low) / self.length
        c = self.canvas
        c.low, c.high, c.length = self.low, self.high, self.length
        c.done, c.now = self.done, self.now
        c.draw()

    # ----------------------------------------------------------------------
    def setText(self, txt):
        self.label["text"] = txt
        self.canvas.setText(txt)

    # ----------------------------------------------------------------------
    def configText(self, text=None, anchor=None, fill=None):
        if text is not None:
            self.setText(text)
        if anchor == "w":
            self.label.place(relx=0, x=2, rely=0.5, relheight=1, height=-2, anchor="w")
            self.canvas.itemconfig(self.canvas.text, anchor="w", justify=LEFT)
        if fill is not None:
            self.canvas.configText(fill=fill)

    # ----------------------------------------------------------------------
    # DarkGray background is the running state, anything else the idle one
    def config(self, **kw):
        background = kw.pop("background", None)
        self.running = background == "DarkGray"
        if self.running:
            self.canvas.config(background=self._emptyColor())
            self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        elif background is not None:
            self.canvas.place_forget()
        if kw:
            ttk.Frame.config(self, **kw)


# =============================================================================
# Theme following the system appearance
# =============================================================================
LIGHT = {
    "background": "#D9D9D9", "foreground": "#000000", "field": "#FFFFFF",
    "active": "#ECECEC", "selected": "#ECECEC", "relief": "raised", "coord": "#8B0000", "separator": "#A0A0A0",
    "caption": "#A6A2A0", "readout": "#00008B",
    "light": "#F4F4F4", "darkc": "#A0A0A0", "border": "#7A7A7A",
    "tabborder": "#9A9A9A", "tablight": "#FFFFFF", "disabled": "#A3A3A3",
    "trough": "#C4C4C4", "edge": "#7A7A7A", "handle": "#ECECEC",
    "grip": "#8F8F8F",
    "sent": "#0000FF", "error": "#FF0000", "info": "#FF00FF",
    "buffer": "#FFFFE0", "tipbg": "#FFFFE0", "tipfg": "#000000",
}
DARK = {
    "background": "#2B2B2B", "foreground": "#EDEDED", "field": "#1E1E1E",
    "active": "#3C3C3C", "selected": "#4A4A4A", "relief": "raised",
    "light": "#505050", "darkc": "#181818", "border": "#101010",
    "coord": "#FF8080", "separator": "#444444",
    "tabborder": "#3A3A3A", "tablight": "#666666", "disabled": "#808080",
    "caption": "#202020", "readout": "#8CB4FF",
    "trough": "#1E1E1E", "edge": "#101010", "handle": "#4A4A4A",
    "grip": "#8A8A8A",
    "sent": "#7AA2FF", "error": "#FF6B6B", "info": "#FF8CFF",
    "buffer": "#3A3A28", "tipbg": "#4A4A3A", "tipfg": "#EDEDED",
}


def isDark(root):
    try:
        return sum(root.winfo_rgb("systemWindowBackgroundColor")) < 3 * 32768
    except TclError:  # not macOS
        return False


def stateColor(root, color, base="TButton"):
    """Style name of a button coloured with a machine state color"""
    dark = isDark(root)
    name = f"State{color}{int(dark)}.{base}"
    if dark:
        # same hue, dimmed to fit the dark panels
        rgb = [int(v * 0.5) // 256 for v in root.winfo_rgb(color)]
        color = "#%02x%02x%02x" % tuple(rgb)
    fg = "white" if dark else "black"
    style = ttk.Style(root)
    style.configure(name, background=color, foreground=fg)
    style.map(name, background=[("active", "LightYellow" if not dark
                                 else "#606040")])
    return name


_listFont = None


def listFont():
    """Platform fixed font, 2 sizes bigger, used by list views"""
    global _listFont
    if _listFont is None:
        _listFont = tkfont.nametofont("TkFixedFont").copy()
        size = int(_listFont.cget("size"))
        _listFont.configure(size=size + 2 if size > 0 else size - 2)
    return _listFont


_scaleImages = []
_scaleCount = 0


def _scaleElements(style, c):
    """Same slider look (bar trough, square grip handle) in every ttk theme"""
    global _scaleCount
    try:
        from PIL import Image, ImageDraw, ImageTk
    except ImportError:
        return

    dark, light = c["darkc"], c["light"]  # as the inputs and the buttons

    def bevel(img, fill, tl, br):
        """1px frame: tl on the top and left, br on the bottom and right"""
        w, h = img.size
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, w - 1, h - 1), fill=br)
        d.rectangle((0, 0, w - 2, h - 2), fill=tl)
        d.rectangle((1, 1, w - 2, h - 2), fill=fill)
        d.point((w - 1, 0), fill=br)
        d.point((0, h - 1), fill=br)

    def trough(fill, w=9, h=14):
        # sunken like the inputs
        img = Image.new("RGBA", (w, h))
        bevel(img, fill, dark, light)
        return img

    def handle(grip, w=28, h=12):
        # like the arrow button of a dropdown: an outline and inside it a 1px
        # raised edge; it sits inside the frame of the trough
        img = Image.new("RGBA", (w, h), c["border"])
        d = ImageDraw.Draw(img)
        d.rectangle((1, 1, w - 2, h - 2), fill=dark)
        d.rectangle((1, 1, w - 3, h - 3), fill=light)
        d.rectangle((2, 2, w - 3, h - 3), fill=c["background"])
        d.point((w - 2, 1), fill=dark)
        d.point((1, h - 2), fill=dark)
        mid = w // 2
        for x in (mid - 4, mid - 1, mid + 2):
            d.line((x, 4, x, h - 5), fill=grip[0])
            d.line((x + 1, 4, x + 1, h - 5), fill=grip[1])
        return img

    # an enabled slider has the background of the inputs
    bar = ImageTk.PhotoImage(trough(c["field"]))
    barOff = ImageTk.PhotoImage(trough(c["background"]))
    # the grooves are stronger than the other edges so the handle is easy to
    # see, in both themes
    groove = (("#000000", c["grip"]) if c["background"] < "#808080"
              else ("#555555", "#FFFFFF"))
    knob = ImageTk.PhotoImage(handle(groove))
    off = ImageTk.PhotoImage(handle((c["darkc"], c["light"])))
    _scaleImages.extend((barOff,))
    _scaleImages.extend((bar, knob, off))
    # element names must be unique, the node name is the last component
    _scaleCount += 1
    prefix = f"Custom{_scaleCount}.Scale"
    style.element_create(f"{prefix}.trough", "image", bar,
                         ("disabled", barOff), border=(1, 1, 1, 1),
                         sticky="ew")
    style.element_create(f"{prefix}.slider", "image", knob,
                         ("disabled", off))
    style.layout("Horizontal.TScale", [(f"{prefix}.trough", {
        "sticky": "nswe", "children": [
            (f"{prefix}.slider", {"side": "left", "sticky": ""})]})])


def readoutColor(widget):
    """Text color for values displayed in the current appearance"""
    return (DARK if isDark(widget) else LIGHT)["readout"]


def themeText(widget):
    """Colors a classic tk Text/Listbox like the ttk entries, also when the
    appearance changes"""
    def colors(event=None):
        c = DARK if isDark(widget) else LIGHT
        options = {"background": c["field"], "foreground": c["foreground"],
                   "insertbackground": c["foreground"],
                   "selectbackground": c["selected"],
                   "selectforeground": c["foreground"],
                   "highlightthickness": 0,
                   "relief": "sunken", "borderwidth": 2}
        try:
            known = widget.keys()
            widget.config(**{k: v for k, v in options.items() if k in known})
        except TclError:
            pass
    colors()
    widget.winfo_toplevel().bind("<<AppearanceChanged>>", colors, add="+")


_fieldImages = []


def _recessed(root, style, c):
    """Text inputs get a sunken 3D frame like the check boxes: dark on the top
    and left, light on the bottom and right, 1px. It is the built-in border
    of the buttons, drawn sunken and filled with the color of the inputs
    (images would make the layout of a page slow)"""
    for name in ("TEntry", "TSpinbox", "TCombobox"):
        field = name[1:] + ".field"
        layout = style.layout(name)
        arrow = [item for item in layout if item[0].endswith(".downarrow")]
        for i, (old, opts) in enumerate(layout):
            if old in (field, "Button.border"):
                new = dict(opts)
                new.pop("border", None)
                if name == "TCombobox" and old == field:
                    # the arrow button is inside the frame
                    new["children"] = arrow + list(opts["children"])
                layout[i] = ("Button.border", new)
        if name == "TCombobox":
            layout = [item for item in layout if item not in arrow]
        style.layout(name, layout)
        style.configure(name, relief="sunken", background=c["field"],
                        bordercolor=c["background"], lightcolor=c["light"],
                        darkcolor=c["darkc"])
        style.map(name, background=[("disabled", c["background"])],
                  bordercolor=[("focus", "#4a6984")],
                  relief=[("disabled", "sunken")])


def _groove(style, c):
    """Frames of the sections: a thin 3D groove, read top to bottom and left
    to right every side is one dark and then one light pixel"""
    dark, light = c["border"], c["light"]
    img = PhotoImage(width=5, height=5)
    for y in range(5):
        for x in range(5):
            if (x, y) == (2, 2):
                img.transparency_set(x, y, True)
            elif min(x, y) == 0 or max(x, y) == 4:  # outer line
                top_left = (y == 0 and x < 4) or (x == 0 and y < 4)
                img.put(dark if top_left else light, to=(x, y))
            else:  # inner line
                top_left = (y == 1 and x < 3) or (x == 1 and y < 3)
                img.put(light if top_left else dark, to=(x, y))
    _fieldImages.append(img)
    element = f"Recessed.groove{len(_fieldImages)}"
    style.element_create(element, "image", img, border=2, sticky="nswe")
    style.layout("TLabelframe", [(element, {"sticky": "nswe"})])


def applyTheme(root):
    dark = isDark(root)
    c = DARK if dark else LIGHT
    bg, fg, field = c["background"], c["foreground"], c["field"]
    style = ttk.Style(root)
    # one base theme for both appearances, so only colors differ and the
    # layout can not change when switching; clam allows to set the 3D edges
    style.theme_use("clam")
    style.configure(".", background=bg, foreground=fg)
    root.option_add("*Toplevel.background", bg)
    style.configure("Tab.Toolbutton", anchor="center")
    style.configure(".", lightcolor=c["light"], darkcolor=c["darkc"],
                    bordercolor=c["border"])
    # keep the sizes of the default theme
    # groove: dark outer line and light inner line on all four sides
    # disabled labels and checkboxes keep the panel background
    style.map(".", background=[("disabled", bg), ("active", c["active"])],
              foreground=[("disabled", c["disabled"])])
    style.configure("TLabelframe", relief="raised",
                    lightcolor=c["light"], darkcolor=c["light"])
    # tabs and tool buttons: flat, a pressed one gets the 1px sunken edge of
    # the inputs, no outline
    style.configure("Toolbutton", bordercolor=bg, lightcolor=c["light"],
                    darkcolor=c["darkc"])
    style.configure("TButton", padding="1.5p", width=-9)
    style.configure("Toolbutton", padding="0.75p")
    style.configure("TMenubutton", padding="7.5p 2.25p", width=-9)
    style.configure("TCheckbutton", padding="0.75p")
    style.configure("TRadiobutton", padding="0.75p")
    style.configure("TEntry", fieldbackground=field, foreground=fg,
                    insertcolor=fg)
    style.configure("TSpinbox", fieldbackground=field, foreground=fg,
                    insertcolor=fg, arrowcolor=fg)
    style.configure("TCombobox", fieldbackground=field, foreground=fg,
                    arrowcolor=fg)
    disabledBg = [("disabled", bg)]
    disabledFg = [("disabled", c.get("disabled", "#A3A3A3"))]
    style.map("TCombobox",
              fieldbackground=disabledBg + [("readonly", field)],
              foreground=disabledFg + [("readonly", fg)],
              selectbackground=[("readonly", field)],
              selectforeground=[("readonly", fg)])
    style.map("TEntry", fieldbackground=disabledBg, foreground=disabledFg)
    style.map("TSpinbox", fieldbackground=disabledBg, foreground=disabledFg)
    _groove(style, c)
    # raised 1px 3D edge on buttons, no outline: light top and left, dark
    # bottom and right
    for name in ("TButton", "TMenubutton"):
        style.configure(name, bordercolor=bg, lightcolor=c["light"],
                        darkcolor=c["darkc"])
    style.configure("Horizontal.TProgressbar", troughcolor=field if dark else bg)
    style.configure("Progress.TLabel", background=field if dark else bg)
    style.configure("Coord.TLabel", foreground=c["coord"])
    _scaleElements(style, c)
    # clam scrollbars are bright by default
    style.configure("TScrollbar", troughcolor=field, background=c["selected"],
                    bordercolor=c["border"], arrowcolor=fg,
                    lightcolor=c["light"], darkcolor=c["darkc"])
    style.map("TScrollbar", background=[("active", c["tablight"])])
    # entries, dropdowns and buttons are all 22px high
    style.configure("TButton", padding=(2, 0))
    style.configure("Editor.Treeview",
                    rowheight=listFont().metrics("linespace") + 2)
    style.configure("Tool.Treeview", rowheight=tkfont.nametofont(
        "TkDefaultFont").metrics("linespace") + 4)
    # list views (terminal, buffer)
    style.configure("Treeview", background=field, fieldbackground=field,
                    foreground=fg, borderwidth=1)
    style.map("Treeview", background=[("selected", c["selected"])],
              foreground=[("selected", fg)])
    style.configure("Buffer.Treeview", background=c["buffer"],
                    fieldbackground=c["buffer"])
    # rows sized to fit the platform's fixed font (set per item in ListView)
    style.configure("Treeview", rowheight=listFont().metrics("linespace") + 2)
    style.configure("Treeview.Item", padding=(6, 0, 0, 0))
    # no expand indicator in front of the text, only a small left padding
    style.layout("Treeview.Item", [("Treeitem.padding", {
        "sticky": "nswe", "children": [
            ("Treeitem.image", {"side": "left", "sticky": ""}),
            ("Treeitem.focus", {"side": "left", "sticky": "", "children": [
                ("Treeitem.text", {"side": "left", "sticky": ""})]})]})])
    # minimum button width in characters, same in both themes
    style.configure("TButton", width=-5)
    style.configure("Readout.TLabel", foreground=c["readout"])
    style.configure("Divider.TFrame", background=c["border"])
    style.configure("DividerLight.TFrame", background=c["light"])
    style.configure("Current.TButton", foreground=c["sent"])
    style.configure("Forward.TButton", foreground=c["disabled"])
    style.configure("Ribbon.TButton", padding=(8, "1.5p"), width=-5)
    style.configure("Left.Ribbon.TButton", anchor="w")
    # toggle (radio/check) buttons of the ribbon, same metrics as Ribbon.TButton
    style.configure("Ribbon.Toolbutton", padding=(8, "1.5p"), width=-5,
                    relief=c["relief"], anchor="center")
    style.configure("Left.Ribbon.Toolbutton", anchor="w")
    global _tabFont
    _tabFont = tkfont.nametofont("TkDefaultFont").copy()
    _tabFont.configure(weight="bold")
    style.configure("Tab.Toolbutton", font=_tabFont)
    global _wcsFont
    _wcsFont = tkfont.nametofont("TkDefaultFont").copy()
    _wcsFont.configure(weight="bold")
    style.configure("WCS.Toolbutton", font=_wcsFont, foreground=c["coord"],
                    anchor="center", justify="center", relief=c["relief"],
                    padding=1)
    global _statusFont
    _statusFont = tkfont.nametofont("TkDefaultFont").copy()
    _statusFont.configure(weight="bold")
    # taller buttons of the connection status and the DRO (X=0, Set WPOS...)
    pad = (2, 2)
    style.configure("Status.TButton", font=_statusFont, padding=pad)
    style.configure("Dro.TButton", padding=pad)
    global _executeFont
    _executeFont = tkfont.nametofont("TkDefaultFont").copy()
    _executeFont.configure(weight="bold")
    _executeFont.configure(size=int(_executeFont.cget("size")) + 2)
    style.configure("Execute.TButton", font=_executeFont,
                    foreground=c["coord"])
    style.configure("Center.Toolbutton", anchor="center", justify="center")
    style.configure("Caption.TLabel", background=c["caption"])
    style.configure("Caption.TButton", background=c["caption"])
    style.map("Caption.TButton", background=[("active", c["active"])])
    # Same metrics as Caption.TLabel (see LabelGroup in Ribbon.py)
    style.configure("Caption.TButton", padding=(2, 1), borderwidth=0,
                    font=("Sans", "-11"), shiftrelief=0)
    # Same element stack for both, so theme borders don't change their height
    style.layout("Caption.TButton", [("Label.padding", {"sticky": "nswe",
                 "children": [("Label.label", {"sticky": "nswe"})]})])
    style.layout("Caption.TLabel", [("Label.padding", {"sticky": "nswe",
                 "children": [("Label.label", {"sticky": "nswe"})]})])
    style.configure("Separator.TFrame", background=c["separator"])
    style.configure("Toolbutton", relief="flat")
    style.map("Toolbutton", relief=[("pressed", "sunken"),
                                    ("selected", "sunken")])
    for name in ("TButton", "TCombobox", "Toolbutton", "TMenubutton"):
        style.configure(name, background=bg)
        style.map(name, background=[("selected", c["selected"]),
                                    ("active", c["active"])])
    for name in ("TButton", "TCombobox", "TMenubutton"):
        style.configure(name, relief=c["relief"])
        style.map(name, background=[("selected", c["selected"]),
                                    ("active", c["active"])],
                  relief=[("pressed", "sunken"), ("selected", "sunken")])
    for name in ("TCheckbutton", "TRadiobutton"):
        style.map(name, background=[("active", c["active"])])
        # concave box: dark upper-left, light lower-right edge
        style.configure(name, indicatorbackground=field,
                        indicatorforeground=fg,
                        upperbordercolor=c["darkc"],
                        lowerbordercolor=c["light"])
        style.map(name, indicatorbackground=[("pressed", c["active"]),
                                             ("!pressed", field)],
                  indicatorforeground=[("disabled", c["selected"]),
                                       ("!disabled", fg)])
    root.option_add("*TCombobox*Listbox.background", field)
    root.option_add("*TCombobox*Listbox.foreground", fg)
    root.option_add("*TCombobox*Listbox.selectBackground", c["selected"])
    root.option_add("*TCombobox*Listbox.selectForeground", fg)
    # white focus ring around classic tk Entry widgets
    entry = {"highlightbackground": bg}
    root.option_add("*Entry.highlightBackground", bg)

    def recolor(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == "Entry":
                child.config(**entry)
            recolor(child)
    recolor(root)
    _recessed(root, style, c)  # after the button styles it builds on


def setTheme(root, interval=1000):
    state = [None]

    def check():
        dark = isDark(root)
        if dark != state[0]:
            state[0] = dark
            applyTheme(root)
            root.event_generate("<<AppearanceChanged>>")
        root.after(interval, check)

    check()
