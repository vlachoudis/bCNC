#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
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
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	02-Aug-2006

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import sys
import time
import subprocess
try:
	import Tkinter as tk
except ImportError:
	import tkinter as tk
import tkExtra
import bFileDialog

#===============================================================================
# Similar to the Dialog.py from Tk but transient to master
#
# This class displays a dialog box, waits for a button in the dialog
# to be invoked, then returns the index of the selected button.  If the
# dialog somehow gets destroyed, -1 is returned.
#
# Arguments:
# w -		Window to use for dialog top-level.
# title -	Title to display in dialog's decorative frame.
# text -	Message to display in dialog.
# bitmap -	Bitmap to display in dialog (empty string means none).
# default -	Index of button that is to display the default ring
#		(-1 means none).
# args -	One or more strings to display in buttons across the
#		bottom of the dialog box.
#===============================================================================
class Dialog(tk.Toplevel):
	def __init__(self, master=None, cnf={}, **kw):
		tk.Toplevel.__init__(self, master, class_="Dialog", **kw)
		self.transient(master)
		self.title(cnf["title"])
		self.iconname("Dialog")
		self.protocol("WM_DELETE_WINDOW", self.close)
		self.num = cnf["default"]

		cnf = tk._cnfmerge((cnf, kw))

		# Fill the top part with bitmap and message (use the option
		# database for -wraplength and -font so that they can be
		# overridden by the caller).
		#self.option_add("*Dialog.msg.wrapLength","3i","widgetDefault")
		#self.option_add("*Dialog.msg.font","TkCaptionFont","widgetDefault")

		fbot = tk.Frame(self, relief=tk.RAISED, bd=1)
		ftop = tk.Frame(self, relief=tk.RAISED, bd=1)
		fbot.pack(side=tk.BOTTOM, fill=tk.BOTH)
		ftop.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)
		self.tk.call("grid", "anchor", fbot._w, tk.CENTER)
		#self.grid_anchor(CENTER)

		l = tk.Label(ftop, text=cnf["text"], wraplength="3i", font="TkCaptionFont", justify=tk.LEFT)
		l.pack(side=tk.RIGHT, fill=tk.BOTH, expand=tk.YES, padx="3m", pady="3m")

		if cnf["bitmap"]:
			l = tk.Label(ftop, bitmap=cnf["bitmap"])
			l.pack(side=tk.LEFT, padx="3m", pady="3m")

		# Create a row of buttons at the bottom of the dialog
		for i,s in enumerate(cnf["strings"]):
			b = tk.Button(fbot, text=s, command=lambda s=self,n=i:s.close(n))
			b.bind("<Return>", lambda e : e.widget.invoke())
			if i==cnf["default"]:
				b.config(default="active")
				b.focus_set()
			else:
				b.config(default="normal")
			b.grid(column=i, row=0, sticky=tk.EW, padx=10, pady=4)

		self.bind("<Escape>", lambda e,s=self:s.close())
		self.bind("<Right>", lambda e : e.widget.event_generate("<Tab>"))
		self.bind("<Left>",  lambda e : e.widget.event_generate("<Shift-Tab>"))

		self.deiconify()
		self.wait_visibility()
		self.grab_set()
		self.focus_set()
		self.wait_window()

	#-----------------------------------------------------------------------
	def close(self, num=-1):
		self.num = num
		self.destroy()

#=============================================================================
# Input dialog
#=============================================================================
class InputDialog(tk.Toplevel):
	"""
	Input dialog:
	valid types:
		str = any string
		int = any integer
		spin  = Spin box with limits from_, to_
		float = any float
	"""
	def __init__(self, master, title, message, inp="",
			type_="str", from_=None, to_=None):

		tk.Toplevel.__init__(self, master)
		self.transient(master)
		tk.Label(self, text=message, justify=tk.LEFT).pack(
			expand=tk.YES, fill=tk.BOTH, side=tk.TOP)

		if type_ == "int":
			self.entry = tkExtra.IntegerEntry(self)
			self.entry.insert(0,inp)
			w = self.entry

		elif type_ == "float":
			self.entry = tkExtra.FloatEntry(self)
			self.entry.insert(0,inp)
			w = self.entry

		elif type_ == "spin":
			self.entry = tk.IntVar()
			self.entry.set(inp)
			w = tk.Spinbox(self, text=self.entry, from_=from_, to_=to_)

		else:	# default str
			self.entry = tk.Entry(self)
			self.entry.insert(0, inp)
			w = self.entry

		w.pack(padx=5, expand=tk.YES, fill=tk.X)

		frame = tk.Frame(self)
		b = tk.Button(frame, text="Cancel", command=self.cancel)
		b.pack(side=tk.RIGHT, pady=5)
		b = tk.Button(frame, text="Ok", command=self.ok)
		b.pack(side=tk.RIGHT, pady=5)
		frame.pack(fill=tk.X)

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

#=============================================================================
# Find/Replace dialog
#=============================================================================
class FindReplaceDialog(tk.Toplevel):
	def __init__(self, master, replace=True):
		tk.Toplevel.__init__(self, master)
		self.transient(master)
		self.replace  = replace
		self.caseVar = tk.IntVar()

		main_frame = tk.Frame(self)
		main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

		bottom_frame = tk.Frame(main_frame)
		bottom_frame.pack(side=tk.BOTTOM, padx=10, pady=5)

		btn = tk.Button(bottom_frame, text="Find", underline=0,
					width=8, command=self._find)
		btn.pack(side=tk.LEFT)

		if self.replace:
			self.title('Replace')

			btn = tk.Button(bottom_frame,
					text="Replace", underline=0,
					width=8, command=self._replace)
			btn.pack(side=tk.LEFT)

			btn = tk.Button(bottom_frame,
					text="Replace All", underline=8,
					width=8, command=self._replaceAll)
			btn.pack(side=tk.LEFT)

		else:
			self.title("Find")

		btn = tk.Button(bottom_frame,
				text = "Close", underline=0,
				width=8, command=self._close)
		btn.pack(side=tk.RIGHT)

		top_frame = tk.Frame(main_frame)
		top_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES,
					padx=10, pady=5)
		findString_frame = tk.Frame(top_frame)
		findString_frame.pack(side=tk.TOP, fill=tk.X)

		label = tk.Label(findString_frame,
				text='Find string: ',
				width=12)
		label.pack(side=tk.LEFT)

		self.findString_entry = tk.Entry(findString_frame,
			background="White")
		self.findString_entry.pack(side=tk.RIGHT, fill=tk.X, expand=tk.YES)

		if self.replace:
			replaceString_frame = tk.Frame(top_frame)
			replaceString_frame.pack(side=tk.TOP, fill=tk.X)

			label = tk.Label(replaceString_frame,
					text='Replace to: ',
					width=12)
			label.pack(side=tk.LEFT)

			self.replaceString_entry = tk.Entry(replaceString_frame,
				background="White")
			self.replaceString_entry.pack(side=tk.RIGHT, fill=tk.X, expand=tk.YES)

		options_frame = tk.Frame(top_frame)
		options_frame.pack(side=tk.TOP, fill=tk.X)
		self.case_check = tk.Checkbutton(options_frame,
					text     = 'Match case? ',
					onvalue  = 0,
					offvalue = 1,
					variable = self.caseVar)
		self.case_check.pack(side = tk.RIGHT)
		self.case_check.deselect()

		self.bind('<Escape>', self._close)
		self.bind('<Alt-Key-c>', self._close)
		self.bind('<Alt-Key-f>', self._find)
		self.bind('<Control-Key-f>', self._find)
		self.bind('<Return>', self._find)
		self.bind('<Alt-Key-r>', self._replace)
		self.bind('<Control-Key-r>', self._replace)
		self.bind('<Alt-Key-a>', self._replaceAll)
		self.bind('<Control-Key-a>', self._replaceAll)

	# --------------------------------------------------------------------
	# Show dialog and wait for events
	# --------------------------------------------------------------------
	def show(self, find=None, replace=None, replaceAll=None, target=None):
		if target:
			self.findString_entry.insert('0', target)
			self.findString_entry.select_range('0',tk.END)
		else:
			self.findString_entry.delete('0', tk.END)
		self.objFind       = find
		self.objReplace    = replace
		self.objReplaceAll = replaceAll
		self.findString_entry.focus_set()
		self.grab_set()
		self.focus_set()
		self.wait_window()

	# --------------------------------------------------------------------
	def _find(self, event=None):
		self.findString = self.findString_entry.get()
		if self.objFind:
			self.objFind(self.findString, self.caseVar.get())

	# --------------------------------------------------------------------
	def _replace(self, event=None):
		self.findString    = self.findString_entry.get()
		self.replaceString = self.replaceString_entry.get()
		if self.objReplace:
			self.objReplace(self.findString,
					self.replaceString,
					self.caseVar.get())

	# --------------------------------------------------------------------
	def _replaceAll(self, event=None):
		self.findString    = self.findString_entry.get()
		self.replaceString = self.replaceString_entry.get()
		if self.objReplaceAll:
			self.objReplaceAll(self.findString,
					self.replaceString,
					self.caseVar.get())

	# --------------------------------------------------------------------
	def _close(self, event=None):
		self.destroy()

#=============================================================================
# Printer dialog
#=============================================================================
class Printer(tk.Toplevel):
	PAPER_FORMAT = { "A3" : (29.7, 42.0),
			 "B3" : (35.3, 50.0),
			 "A4" :	(21.0, 29.7),
			 "B4" :	(25.0, 35.3),
			 "A5" : (14.8, 21.0),
			 "B5" :	(17.6, 25.0),
			 "Letter": (21.6, 27.9) }
	printTo   = 1		# 1 = cmd, 0 = filename
	cmd       = "lpr -P%p"
	printer   = ""
	filename  = "output.ps"
	landscape = False
	paper     = "A4"
	copies    = 1

	def __init__(self, master):
		tk.Toplevel.__init__(self, master)
		self.transient(master)
		self.title('Print')

		self.printCmd  = tk.IntVar()
		self.printCmd.set(Printer.printTo)
		self.landscapeVar = tk.IntVar()
		self.landscapeVar.set(Printer.landscape)
		self.paperVar     = tk.StringVar()
		self.paperVar.set(Printer.paper)
		self.copiesVar    = tk.IntVar()
		self.copiesVar.set(Printer.copies)

		#self.geometry('+265+230')

		# -----
		frame = tk.LabelFrame(self, text="Print To")
		frame.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.YES)

		b = tk.Radiobutton(frame, text="Printer:",
			variable=self.printCmd, value=1,
			command=self.printToChange)
		b.grid(row=0, column=0, sticky=tk.W)

		self.printer_combo = tkExtra.Combobox(frame, width=30)
		self.printer_combo.grid(row=0, column=1, columnspan=2, sticky=tk.EW)
		self.fillPrinters()

		self.cmd_label = tk.Label(frame, text="Command:")
		self.cmd_label.grid(row=1, column=0, sticky=tk.E)

		self.cmd_entry = tk.Entry(frame, background="White", width=30)
		self.cmd_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW)
		self.cmd_entry.insert(0, Printer.cmd)

		b = tk.Radiobutton(frame, text="File Name:",
			variable=self.printCmd, value=0,
			command=self.printToChange)
		b.grid(row=2, column=0, sticky=tk.W)

		self.file_entry = tk.Entry(frame, background="White", width=25)
		self.file_entry.grid(row=2, column=1, sticky=tk.EW)

		self.browse_btn = tk.Button(frame, text="Browse",
				command=self.browse)
		self.browse_btn.grid(row=2, column=2, sticky=tk.EW)
		frame.grid_columnconfigure(1, weight=1)

		# ------
		frame = tk.LabelFrame(self, text="Options")
		frame.pack(fill=tk.BOTH)

		row = 0
		l = tk.Label(frame, text="Orientation")
		l.grid(row=row, column=0, sticky=tk.E)

		b = tk.Radiobutton(frame, text="Portrait",
			variable=self.landscapeVar, value=0)
		b.grid(row=row, column=1, sticky=tk.W)

		b = tk.Radiobutton(frame, text="Landscape",
			variable=self.landscapeVar, value=1)
		b.grid(row=row, column=2, columnspan=2, sticky=tk.W)

		row += 1
		l = tk.Label(frame, text="Paper Size")
		l.grid(row=row, column=0, sticky=tk.E)

		paperlist = sorted(Printer.PAPER_FORMAT.keys())
		o = tk.OptionMenu(frame, self.paperVar, *paperlist)
		o.grid(row=row, column=1, sticky=tk.W)

		l = tk.Label(frame, text="Copies")
		l.grid(row=row, column=2, sticky=tk.E)

		s = tk.Spinbox(frame, text=self.copiesVar, from_=1, to=100,
				background="White", width=3)
		s.grid(row=row, column=3, sticky=tk.W)

		frame.grid_columnconfigure(1, weight=1)
		frame.grid_columnconfigure(3, weight=1)

		# -------
		frame = tk.Frame(self)
		frame.pack(fill=tk.X)

		b = tk.Button(frame, text="Cancel", command=self.cancel)
		b.pack(side=tk.RIGHT)

		b = tk.Button(frame, text="Print", command=self.ok)
		b.pack(side=tk.RIGHT)

		self.bind('<Return>', self.ok)
		self.bind('<Escape>', self.cancel)

		# --- Basic Variables ---
		self.rc = False
		self.hnd = None
		self.printToChange()

	# --------------------------------------------------------------------
	def fillPrinters(self):
		# On unix
		if sys.platform in ("linux","linux2"):
			try:
				f = open("/etc/printcap","r")
				for line in f:
					if not line: continue
					if line[0] == '#': continue
					field = line.split(":")
					self.printer_combo.insert(tk.END, field[0])
					if Printer.printer == "":
						Printer.printer = field[0]
				f.close()
			except IOError:
				pass
		else:
			raise Exception("Unknown operating system")
		self.printer_combo.set(Printer.printer)

	# --------------------------------------------------------------------
	def show(self):
		# Return Variables
		self.rc = False
		self.hnd = None

		self.cmd_entry.config(state=tk.NORMAL)
		self.file_entry.config(state=tk.NORMAL)
		self.cmd_entry.delete(0, tk.END)
		self.cmd_entry.insert(0, Printer.cmd)
		self.file_entry.delete(0, tk.END)
		self.file_entry.insert(0, Printer.filename)

		self.printCmd.set(Printer.printTo)
		self.landscapeVar.set(Printer.landscape)
		self.paperVar.set(Printer.paper)

		self.printToChange()

		self.grab_set()
		self.wait_window()
		return self.rc

	# --------------------------------------------------------------------
	def ok(self, event=None):
		self.rc = True
		Printer.printTo   = self.printCmd.get()
		Printer.cmd       = self.cmd_entry.get()
		Printer.printer   = self.printer_combo.get()
		Printer.filename  = self.file_entry.get()
		Printer.landscape = self.landscapeVar.get()
		Printer.paper     = self.paperVar.get()
		Printer.copies    = self.copiesVar.get()
		self.destroy()

	# --------------------------------------------------------------------
	def cancel(self, event=None):
		self.rc = False
		self.destroy()

	# --------------------------------------------------------------------
	def printToChange(self):
		if self.printCmd.get():
			self.printer_combo.config(state=tk.NORMAL)
			self.cmd_label.config(state=tk.NORMAL)
			self.cmd_entry.config(state=tk.NORMAL)
			self.file_entry.config(state=tk.DISABLED)
			self.browse_btn.config(state=tk.DISABLED)
		else:
			self.printer_combo.config(state=tk.DISABLED)
			self.cmd_label.config(state=tk.DISABLED)
			self.cmd_entry.config(state=tk.DISABLED)
			self.file_entry.config(state=tk.NORMAL)
			self.browse_btn.config(state=tk.NORMAL)

	# --------------------------------------------------------------------
	def browse(self):
		fn = bFileDialog.asksaveasfilename(master=self,
				initialfile=self.file_entry.get(),
				filetypes=[("Postscript file","*.ps"),
					("Encapsulated postscript file","*.eps"),
					("All","*")])
		if fn:
			self.file_entry.delete(0, tk.END)
			self.file_entry.insert(0, fn)

	# --------------------------------------------------------------------
	# Return the printer command
	# --------------------------------------------------------------------
	@staticmethod
	def command():
		printer = Printer.printer
		bar = printer.find("|")
		if bar>0: printer = printer[:bar]

		if Printer.cmd.find("%p") == -1:
			cmd = Printer.cmd + " -P %s"%(printer)
		else:
			cmd = Printer.cmd.replace("%p","%s")%(printer)

		if cmd.find("%#") == -1:
			cmd += " -# %d"%(Printer.copies)
		else:
			cmd = cmd.replace("%#","%d") % (Printer.copies)
		#print "Printing command=\"%s\""%(cmd)
		return cmd

	# --------------------------------------------------------------------
	# I/O
	# Return a file handle or None where to write the data
	# --------------------------------------------------------------------
	def open(self):
		self.hnd = None
		if self.rc:
			if Printer.printTo:
				self.hnd = subprocess.Popen(Printer.command(),
						shell=True,
						stdout=subprocess.PIPE).stdout
			else:
				self.hnd = open(Printer.filename, "w")
		return self.hnd

	# --------------------------------------------------------------------
	def write(self, s):
		try:
			self.hnd.write(s)
			return True
		except:
			return False

	# --------------------------------------------------------------------
	def close(self):
		if self.hnd:
			self.hnd.close()

#=============================================================================
# Show progress information
#=============================================================================
class ProgressDialog(tk.Toplevel):
	def __init__(self, master, title):
		tk.Toplevel.__init__(self, master)
		self.transient(master)
		self.title(title)
		self.bar = tkExtra.ProgressBar(self, width=200, height=24, background="DarkGray")
		self.bar.pack(side=tk.TOP, expand=tk.YES, fill=tk.X)
		self.label = tk.Label(self, width=60)
		self.label.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)
		b = tk.Button(self, text="Stop", foreground="Darkred", command=self.stop)
		b.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
		self.ended = False

		self.bind("<Escape>", self.stop)
		self.protocol("WM_DELETE_WINDOW", self.stop)

		self.wait_visibility()
		self.update_idletasks()
		self.grab_set()

		x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width())/2
		y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height())/2
		self.geometry('+%d+%d' % (x,y))
		self.lastTime  = time.time()
		self.refreshInterval = 0.25

	# --------------------------------------------------------------------
	def setLimits(self, low=0.0, high=100.0, step=1.0):
		self.bar.setLimits(low,high,step)
		self.startTime = time.time()

	# --------------------------------------------------------------------
	def show(self, pos, text=None):
		if time.time() - self.lastTime < self.refreshInterval: return
		self.lastTime = time.time()
		self.bar.setProgress(pos)
		if text is not None: self.label["text"] = text
		#self.update_idletasks()
		self.update()
		return self.ended

	# --------------------------------------------------------------------
	def close(self):
		self.grab_release()
		self.destroy()

	# --------------------------------------------------------------------
	def stop(self):
		self.ended = True
		self.close()

#=============================================================================
if __name__ == "__main__":
	root = tk.Tk()
	sd = Printer(root)
	sd = FindReplaceDialog(root)
	#print("FindReplace=",sd.show(None,"Hello"))
	d = InputDialog(root,"Title","Message Line1\nMessage Line2")
	#print("Input=",d.show())
	root.mainloop()
