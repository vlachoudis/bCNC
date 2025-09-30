# $Id: Updates.py 3349 2014-11-28 14:09:26Z bnv $

# Author:   vvlachoudis@gmail.com
# Date:     5-Apr-2007

import json
import time
from datetime import datetime
import http.client as http
from tkinter import (
    W,
    E,
    EW,
    X,
    BOTH,
    LEFT,
    TOP,
    RIGHT,
    BOTTOM,
    RAISED,
    DISABLED,
    IntVar,
    Tk,
    Toplevel,
    Button,
    Frame,
    Label,
    Spinbox,
    LabelFrame,
)

import tkExtra
import Utils

__author__ = "Vasilis Vlachoudis"
__email__ = "vvlachoudis@gmail.com"


# =============================================================================
# Check for updates of bCNC
# =============================================================================
class CheckUpdateDialog(Toplevel):
    def __init__(self, master, version):
        Toplevel.__init__(self, master)
        self.title("Check for updates")
        self.transient(master)

        # Variables
        self.version = version

        # -----
        la = Label(self, image=Utils.icons["bCNC"],
                   relief=RAISED, padx=0, pady=0)
        la.pack(side=TOP, fill=BOTH)

        # ----
        frame = LabelFrame(self, text="Version", padx=3, pady=5)
        frame.pack(side=TOP, fill=BOTH)

        la = Label(frame, text=_("Installed Version:"))
        la.grid(row=0, column=0, sticky=E, pady=1)

        la = Label(frame, text=version, anchor=W)
        la.grid(row=0, column=1, sticky=EW)
        tkExtra.Balloon.set(la, _("Running version of bCNC"))

        la = Label(frame, text=_("Latest PyPI Version:"))
        la.grid(row=1, column=0, sticky=E, pady=1)

        self.webversion = Label(frame, anchor=W)
        self.webversion.grid(row=1, column=1, sticky=EW)
        tkExtra.Balloon.set(self.webversion,
                            _("Latest release version on PyPI"))
        la = Label(frame, text=_("Published at:"))
        la.grid(row=2, column=0, sticky=E, pady=1)

        self.published = Label(frame, anchor=W)
        self.published.grid(row=2, column=1, sticky=EW)
        tkExtra.Balloon.set(
            self.published, _("Published date of the latest PyPI release")
        )

        frame.grid_columnconfigure(1, weight=1)

        # ----
        frame = LabelFrame(self, text=_("Check Interval"), padx=3, pady=5)
        frame.pack(fill=BOTH)

        la = Label(frame, text=_("Last Check:"))
        la.grid(row=0, column=0, sticky=E, pady=1)

        # Last check
        lastCheck = Utils.getInt(Utils.__prg__, "lastcheck", 0)
        if lastCheck == 0:
            lastCheckStr = "unknown"
        else:
            lastCheckStr = time.asctime(time.localtime(lastCheck))

        la = Label(frame, text=lastCheckStr, anchor=W)
        la.grid(row=0, column=1, sticky=EW)
        tkExtra.Balloon.set(la, _("Date last checked"))

        la = Label(frame, text=_("Interval (days):"))
        la.grid(row=1, column=0, sticky=E, pady=1)

        checkInt = Utils.getInt(Utils.__prg__, "checkinterval", 30)
        self.checkInterval = IntVar()
        self.checkInterval.set(checkInt)

        s = Spinbox(
            frame,
            text=self.checkInterval,
            from_=0,
            to_=365,
            background=tkExtra.GLOBAL_CONTROL_BACKGROUND,
        )
        s.grid(row=1, column=1, sticky=EW)
        frame.grid_columnconfigure(1, weight=1)
        tkExtra.Balloon.set(s, _("Days-interval to remind again for checking"))

        # ----
        frame = Frame(self)
        frame.pack(side=BOTTOM, fill=X)
        b = Button(
            frame,
            text=_("Close"),
            image=Utils.icons["x"],
            compound=LEFT,
            command=self.later,
        )
        b.pack(side=RIGHT)

        self.checkButton = Button(
            frame,
            text=_("Check Now"),
            image=Utils.icons["global"],
            compound=LEFT,
            command=self.check,
        )
        self.checkButton.pack(side=RIGHT)
        tkExtra.Balloon.set(
            self.checkButton, _("Check the web site for new versions of bCNC")
        )

        self.bind("<Escape>", self.close)

        self.wait_window()

    # ----------------------------------------------------------------------
    def isNewer(self, version):
        av = map(int, self.version.split("."))
        bv = map(int, version.split("."))
        for a, b in zip(av, bv):
            if b > a:
                return True
        return False

    # ----------------------------------------------------------------------
    def check(self):
        h = http.HTTPSConnection("pypi.org")
        h.request(
            "GET",
            "/pypi/bCNC/json",
            None,
            {"User-Agent": "bCNC"},
        )
        r = h.getresponse()
        if r.status == http.OK:
            data = json.loads(r.read().decode("utf-8"))
            latest_version = data["info"]["version"]

            self.webversion.config(text=latest_version)
            # Parse upload_time in ISO8601 format to local date time string

            upload_time_iso = data["urls"][0]["upload_time_iso_8601"]  # e.g. "2025-03-22T19:40:50.268938Z"
            dtUTC = datetime.fromisoformat(upload_time_iso)
            timestamp = dtUTC.timestamp()
            uploadTimeStr = time.asctime(time.localtime(timestamp))
            self.published.config(text=uploadTimeStr)

            if self.isNewer(latest_version):
                self.webversion.config(background="LightGreen")
                self.checkButton.config(
                    text=_("Download"), background="LightYellow",
                    command=self.download
                )
                tkExtra.Balloon.set(
                    self.checkButton, _("Open web browser to download bCNC")
                )
            else:
                self.checkButton.config(state=DISABLED)

        else:
            self.webversion.config(
                text=_("Error {} in connection").format(r.status))

        # Save today as lastcheck date
        Utils.config.set(Utils.__prg__, "lastcheck", str(int(time.time())))

    # ----------------------------------------------------------------------
    def later(self):
        # Save today as lastcheck date
        Utils.config.set(Utils.__prg__, "lastcheck", str(int(time.time())))
        self.close()

    # ----------------------------------------------------------------------
    def download(self):
        import webbrowser

        webbrowser.open("https://pypi.org/project/bCNC/")
        self.checkButton.config(background="LightGray")

    # ----------------------------------------------------------------------
    def close(self, event=None):
        try:
            Utils.config.set(
                Utils.__prg__, "checkinterval",
                str(int(self.checkInterval.get()))
            )
        except TypeError:
            pass
        self.destroy()


# -----------------------------------------------------------------------------
# Check if interval has passed from last check
# -----------------------------------------------------------------------------
def need2Check():
    lastCheck = Utils.getInt(Utils.__prg__, "lastcheck", 0)
    if lastCheck == 0:  # Unknown
        return True

    checkInt = Utils.getInt(Utils.__prg__, "checkinterval", 30)
    if checkInt == 0:  # Check never
        return False

    return lastCheck + checkInt * 86400 < int(time.time())


# =============================================================================
if __name__ == "__main__":
    tk = Tk()
    Utils.loadIcons()
    Utils.loadConfiguration()
    dlg = CheckUpdateDialog(tk, 0)
    tk.mainloop()
