#
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
# Author:   Vasilis.Vlachoudis@cern.ch
# Date:     02-Aug-2006

from tkinter import (
    YES,
    X,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    IntVar,
    Toplevel,
)
from tkinter.ttk import (
    Button,
    Entry,
    Frame,
    Label,
    Spinbox,
)

import tkExtra

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


# =============================================================================
# Input dialog
# =============================================================================
class InputDialog(Toplevel):
    """
    Input dialog:
    valid types:
            str = any string
            int = any integer
            spin  = Spin box with limits from_, to_
            float = any float
    """

    def __init__(
        self, master, title, message, input_="",
        type_="str", from_=None, to_=None
    ):

        Toplevel.__init__(self, master)
        self.transient(master)
        Label(self, text=message,
              justify=LEFT).pack(expand=YES, fill=BOTH, side=TOP)

        if type_ == "int":
            self.entry = tkExtra.IntegerEntry(self)
            self.entry.insert(0, input_)
            w = self.entry

        elif type_ == "float":
            self.entry = tkExtra.FloatEntry(self)
            self.entry.insert(0, input_)
            w = self.entry

        elif type_ == "spin":
            self.entry = IntVar()
            self.entry.set(input_)
            w = Spinbox(self, textvariable=self.entry, from_=from_, to_=to_)

        else:  # default str
            self.entry = Entry(self)
            self.entry.insert(0, input_)
            w = self.entry

        w.pack(padx=5, expand=YES, fill=X)

        frame = Frame(self)
        b = Button(frame, text="Cancel", command=self.cancel)
        b.pack(side=RIGHT, pady=5)
        b = Button(frame, text="Ok", command=self.ok)
        b.pack(side=RIGHT, pady=5)
        frame.pack(fill=X)

        self.input = None
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.focus_set()
        w.focus_set()

    # --------------------------------------------------------------------
    def show(self):
        grab_window = self.grab_current()
        if grab_window is not None:
            grab_window.grab_release()
        self.wait_window()
        if grab_window is not None:
            grab_window.grab_set()
        return self.input

    # --------------------------------------------------------------------
    def ok(self, event=None):
        try:
            self.input = self.entry.get()
            self.destroy()
        except ValueError:
            pass

    # --------------------------------------------------------------------
    def cancel(self, event=None):
        self.destroy()
