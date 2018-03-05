#!/bin/env python

# Author: vvlachoudis@gmail.com
# Date:	5-Apr-2007

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import time
import json
import tkinter as tk
import http.client as http

import Utils
import tkExtra

#===============================================================================
# Check for updates of bCNC
#===============================================================================
class CheckUpdateDialog(tk.Toplevel):
	def __init__(self, master, version):
		tk.Toplevel.__init__(self, master)
		self.title("Check for updates")
		self.transient(master)

		# Variables
		self.version  = version

		# -----
		l = tk.Label(self, image=Utils.icons["bCNC"],
				relief=tk.RAISED,
				padx=0, pady=0)
		l.pack(side=tk.TOP, fill=tk.BOTH)

		# ----
		frame = tk.LabelFrame(self, text="Version", padx=3, pady=5)
		frame.pack(side=tk.TOP, fill=tk.BOTH)

		l = tk.Label(frame, text=_("Installed Version:"))
		l.grid(row=0, column=0, sticky=tk.E, pady=1)

		l = tk.Label(frame, text=version, anchor=tk.W)
		l.grid(row=0, column=1, sticky=tk.EW)
		tkExtra.Balloon.set(l, _("Running version of bCNC"))

		l = tk.Label(frame, text=_("Latest Github Version:"))
		l.grid(row=1, column=0, sticky=tk.E, pady=1)

		self.webversion = tk.Label(frame, anchor=tk.W)
		self.webversion.grid(row=1, column=1, sticky=tk.EW)
		tkExtra.Balloon.set(self.webversion,
			_("Latest release version on on github"))
		l = tk.Label(frame, text=_("Published at:"))
		l.grid(row=2, column=0, sticky=tk.E, pady=1)

		self.published = tk.Label(frame, anchor=tk.W)
		self.published.grid(row=2, column=1, sticky=tk.EW)
		tkExtra.Balloon.set(self.published,
			_("Published date of the latest github release"))

		frame.grid_columnconfigure(1, weight=1)

		# ----
		frame = tk.LabelFrame(self, text=_("Check Interval"), padx=3, pady=5)
		frame.pack(fill=tk.BOTH)

		l = tk.Label(frame, text=_("Last Check:"))
		l.grid(row=0, column=0, sticky=tk.E, pady=1)

		# Last check
		lastCheck = Utils.getInt(Utils.__prg__,"lastcheck",0)
		if lastCheck == 0:
			lastCheckStr = "unknown"
		else:
			lastCheckStr = time.asctime(time.localtime(lastCheck))

		l = tk.Label(frame, text=lastCheckStr, anchor=tk.W)
		l.grid(row=0, column=1, sticky=tk.EW)
		tkExtra.Balloon.set(l, _("Date of last checking"))

		l = tk.Label(frame, text=_("Interval (days):"))
		l.grid(row=1, column=0, sticky=tk.E, pady=1)

		checkInt = Utils.getInt(Utils.__prg__,"checkinterval",30)
		self.checkInterval = tk.IntVar()
		self.checkInterval.set(checkInt)

		s = tk.Spinbox(frame, text=self.checkInterval, from_=0, to_=365,
				background="White")
		s.grid(row=1, column=1, sticky=tk.EW)
		frame.grid_columnconfigure(1, weight=1)
		tkExtra.Balloon.set(s, _("Days-interval to remind again for checking"))

		# ----
		frame = tk.Frame(self)
		frame.pack(side=tk.BOTTOM,fill=tk.X)
		b = tk.Button(frame,text=_("Close"),
				image=Utils.icons["x"],
				compound=tk.LEFT,
				command=self.later)
		b.pack(side=tk.RIGHT)

		self.checkButton = tk.Button(frame,text=_("Check Now"),
				image=Utils.icons["global"],
				compound=tk.LEFT,
				command=self.check)
		self.checkButton.pack(side=tk.RIGHT)
		tkExtra.Balloon.set(self.checkButton,
				_("Check the web site for new versions of bCNC"))

		self.bind('<Escape>', self.close)

		#x = master.winfo_rootx() + 200
		#y = master.winfo_rooty() + 50
		#self.geometry("+%d+%d" % (x,y))
		#self.wait_visibility()
		self.wait_window()

	# ----------------------------------------------------------------------
	def isNewer(self, version):
		av = map(int, self.version.split("."))
		bv = map(int, version.split("."))
		for a, b in zip(av, bv):
			if b>a: return True
		return False

	# ----------------------------------------------------------------------
	def check(self):
		h = http.HTTPSConnection("api.github.com")
		h.request("GET","/repos/vlachoudis/bCNC/releases/latest",None,{"User-Agent":"bCNC"})
		r = h.getresponse()
		if r.status == http.OK:
			data = json.loads(r.read().decode("utf-8"))
			latest_version = data["tag_name"]

			self.webversion.config(text=latest_version)
			self.published.config(text=data["published_at"])

			if self.isNewer(latest_version):
				self.webversion.config(background="LightGreen")
				self.checkButton.config(text=_("Download"),
						background="LightYellow",
						command=self.download)
				tkExtra.Balloon.set(self.checkButton, _("Open web browser to download bCNC"))
			else:
				self.checkButton.config(state=tk.DISABLED)

		else:
			self.webversion.config(text=_("Error %d in connection")%(r.status))

		#self.laterButton.config(state=tk.DISABLED)

		# Save today as lastcheck date
		Utils.config.set(Utils.__prg__,
			"lastcheck", str(int(time.time())))

	# ----------------------------------------------------------------------
	def later(self):
		# Save today as lastcheck date
		Utils.config.set(Utils.__prg__, "lastcheck", str(int(time.time())))
		self.close()

	# ----------------------------------------------------------------------
	def download(self):
		import webbrowser
		webbrowser.open("https://github.com/vlachoudis/bCNC/releases/latest")
		self.checkButton.config(background="LightGray")

	# ----------------------------------------------------------------------
	def close(self, event=None):
		try:
			Utils.config.set(Utils.__prg__,
				"checkinterval", str(int(self.checkInterval.get())))
		except TypeError:
			pass
		self.destroy()

#-------------------------------------------------------------------------------
# Check if interval has passed from last check
#-------------------------------------------------------------------------------
def need2Check():
	lastCheck = Utils.getInt(Utils.__prg__,"lastcheck",0)
	if lastCheck == 0:	# Unknown
		return True

	checkInt = Utils.getInt(Utils.__prg__,"checkinterval",30)
	if checkInt == 0:	# Check never
		return False

	return lastCheck + checkInt*86400 < int(time.time())

#===============================================================================
#if __name__ == "__main__":
#	root = tk.Tk()
#	Utils.loadIcons()
#	Utils.loadConfiguration()
#	dlg = CheckUpdateDialog(root,0)
#	root.mainloop()
