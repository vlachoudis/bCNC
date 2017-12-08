#!/usr/bin/python
# -*- coding: ascii -*-
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
# DAMAGES.
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	29-Nov-2009

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import os
import time
import fnmatch
from stat import *

if "_" not in dir(): _ = lambda x: x

try:
	from Tkinter import *
	import tkMessageBox as messagebox
except ImportError:
	from tkinter import *
	import tkinter.messagebox as messagebox
import tkExtra

_DIR_TYPE     = " <DIR>"
_FILE_TYPE    = "-file-"
_LINK_TYPE    = "-link-"
_BACKUP_TYPE  = "-backup-"
_TIME_FORMAT  = "%Y.%m.%d %H:%M:%S"
DISABLE_FILE  = "DarkGray"

COLORS = {
		"gz":	"Red",
		"tgz":	"Red",
		"zip":	"Red",
		"tbz":	"Red",
		"rpm":	"Red",
		"deb":	"Red",

		"flair":"DarkGreen",
		"fluka":"#109010",
		"inp":	"#109010",
		"out":	"#109010",
		"log":	"#109010",
		"err":	"Red",
		"lis":	"#109010",

		"py":	"Blue",
		"f":	"Blue",
		"F":	"Blue",
		"for":	"Blue",
		"FOR":	"Blue",
		"c":	"Blue",
		"C":	"Blue",
		"cc":	"Blue",
		"cpp":	"Blue",
		"a":	"Blue",
		"so":	"Blue",

		"eps":	"Purple",
		"ps":	"Purple",
		"gif":	"Purple",
		"png":	"Purple",
		"jpg":	"Purple",
		"bmp":	"Purple",
		"tif":	"Purple",

		"vxl":  "DarkRed",
		"dcm":  "DarkRed",

		"ngc":  "Brown",
		"nc" :  "Brown",

		"probe": "DarkOrange",
		"stl"  : "DarkOrange",

		_LINK_TYPE:	"DarkCyan",
		_BACKUP_TYPE:	"DarkGray",
		_DIR_TYPE:	"DarkBlue",
	}

DESCRIPTION = {
		"gz":	"Package gzip",
		"tgz":	"Package tgz",
		"zip":	"Package zip",
		"tbz":	"Package tbz",
		"rpm":	"Package rpm",
		"deb":	"Package deb",

		"flair":"FLAIR",
		"fluka":"Input",
		"inp":	"Input",
		"out":	"Output",
		"log":	"Log",
		"err":	"Error",
		"lis":	"Listing",

		"py":	"Python",
		"f":	"Fortran",
		"F":	"Fortran",
		"for":	"Fortran",
		"FOR":	"Fortran",
		"c":	"C",
		"C":	"C",
		"cc":	"C++",
		"cpp":	"C++",
		"a":	"Lib a",
		"so":	"Lib so",

		"eps":	"Image eps",
		"gif":	"Image gif",
		"jpg":	"Image jpg",
		"png":	"Image png",
		"bmp":	"Image bmp",
		"ps":	"Image ps",
		"tif":	"Image tif",

		"vxl":  "Voxel",
		"dcm":  "Dicom",

		_LINK_TYPE   : _LINK_TYPE,
		_BACKUP_TYPE : _BACKUP_TYPE,
		_DIR_TYPE    : _DIR_TYPE,
	}

# Converted from GIF to base64 PhotoImage
# base64.encodestring(open(iconfile,"rb").read())
_ICON = """
R0lGODlhEAAQAMZcABAQECEQECEYEDEgITEwIUI4MVJJQmNJIWNZQmNhWvw/Afw+DnNhUvxADv9B
D3NlSoRpIZRxIYRxUvRbM4R5Y6V5IfxhHvpnGvlsAZSCY7WCEPFwM5SKc5yKa5SKhPJ4QMaKENaK
EMaSAJyShPqDHqWShNaSAOuDZdaSEP+BSaWahP+LPqWilLWihLWilOWWfueiIeeiMbWqlP+ZauKg
itaqUveqMcaylOCql9ayc/eyMca6lN20o/e6QtbDhNbDlPfDQv+8i87Htf/DUs7LtefLhP/LUv/Q
Lv/RMf/TUufTpf/TY/fThP/Tc//bY/fbhP/bc//bhPfjlP/jhP/jlPfrpf3rlP/rpffzpffztf/z
pf31xf//////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////yH5
BAEKAH8ALAAAAAAQABAAAAe6gH+Cg4SFhoU4PIeFCjgKJy+KgjKUlEKCCgokDYMySllZWlcuRBYY
W1YXE4IuWKFXV1AsKitIRx+DLlWiV1FOTkEOKRsLNIIsVbA3N5QtLTMnJSUeHCpSV0UyU9vcU1BQ
NSPWVDI7UL9OS0lGPTEPfyVP2VNN6UtGQD06EB3wTDI/oCy5N0SfjRAHBHnwoe0ePh02YKCAkEAQ
Bxc5TGgUAUKDhgoRElrMQEECAwQGChAYIABAgEUwBQUCADs=
"""
_history     = []

#-------------------------------------------------------------------------------
def append2History(path):
	global _history
	if not path: return
	if path not in _history:
		_history.append(path)

#-------------------------------------------------------------------------------
def fileTypeColor(filename):
	fn = os.path.basename(filename)
	dot = fn.rfind(".")
	if dot>=0:
		ext = fn[dot+1:].lower()
	else:
		ext = _FILE_TYPE
	color  = None		# Default

	try: s = os.lstat(filename)
	except: return ext,color

	mode  = s[ST_MODE]
	isdir = S_ISDIR(mode)
	islnk = S_ISLNK(mode)

	if isdir:
		color = COLORS.get(_DIR_TYPE)
		ext   = DESCRIPTION.get(_DIR_TYPE)

	elif islnk:
		color = COLORS.get(_LINK_TYPE)
		ext   = DESCRIPTION.get(_LINK_TYPE)

	else:
		if fn[-1] == "~":
			color = COLORS.get(_BACKUP_TYPE)
		else:
			color = COLORS.get(ext,color)
			ext   = DESCRIPTION.get(ext,ext)

	return ext,color

#===============================================================================
# FileDialog
#===============================================================================
class FileDialog(Toplevel):
	_active   = False	# Avoid re-entrance of the dialog if by accident
				# someone double clicks a button
	sort      = None
	width     = -1
	height    = -1
	sash      = None
	newfolder = None

	# ----------------------------------------------------------------------
	def __init__(self, title=None,
			master=None,
			initialdir=None,
			initialfile=None,
			defaultextension=None,
			multiple=False,
			filetypes=None,
			**kw):

		Toplevel.__init__(self)
		self.transient(master)
		self.title(title)
		self.protocol("WM_DELETE_WINDOW", self.close)

		FileDialog._active = True

		if title is None: title = self._title

		self.dirframe = Frame(self)
		self.dirframe.pack(side=TOP, fill=X)
		Label(self.dirframe, text=_("Directory:")).grid(
			row=0, column=0)

		self.downButton = Label(self.dirframe, text=u"\u25BC",
				padx=3, pady=1, relief=RAISED)
		self.downButton.bind("<Button-1>", self.history)
		self.downButton.grid(row=0, column=99)

		if FileDialog.newfolder is None:
			FileDialog.newfolder = PhotoImage(data=_ICON)

		Button(self.dirframe, image=FileDialog.newfolder,
			padx=3, pady=3,
			command=self.newFolder).grid(
			row=0, column=100)
		self.dirframe.grid_columnconfigure(98,weight=1)
		self.buttons = []

		self.multiple = multiple
		if multiple:
			selectmode = EXTENDED
		else:
			selectmode = BROWSE
		self.fileList = tkExtra.ColorMultiListbox(self,
			((_("Name"), 30, None),
			 (_("Type"), 12, None),
			 (_("Size"),  8, None),
			 (_("Date"), 17, None)),
			 height=20,
			 selectmode=selectmode)
		self.fileList.pack(expand=YES, fill=BOTH)
		self.fileList.setPopupMenu(
			[('Rename', 0, self.rename),
			 ('Delete', 0, self.delete),
			 ('New Folder', 0, self.newFolder) ])

		self.fileList.bindList("<Double-1>",      self.double)
		self.fileList.bindList('<Return>',        self.double)
		self.fileList.bindList('<F2>',            self.rename)
		self.fileList.bindList("<Key-BackSpace>", self.upDir)
		self.fileList.bind("<<ListboxSelect>>",   self.select)
		self.fileList.bind("<<ListboxSort>>",     self.sortChanged)
		self.fileList.bind("<Configure>",         self.resize)

		frame = Frame(self)
		frame.pack(side=BOTTOM, fill=X)

		l = Label(frame, text=_("File name:"))
		l.grid(row=0, column=0, sticky=E)
		self.filename = Entry(frame, background="White")
		self.filename.grid(row=0, column=1, sticky=EW)
		self.ok = Button(frame, text=_("Open"), command=self.openFilename)
		self.ok.grid(row=0, column=2, sticky=EW)

		l = Label(frame, text=_("Files of type:"))
		l.grid(row=1, column=0, sticky=E)

		self.typeCombo = tkExtra.Combobox(frame, command=self.typeChange)
		self.typeCombo.grid(row=1, column=1, sticky=NSEW)

		self.filter = None
		self.filetypes = {}
		if filetypes:
			if isinstance(filetypes[0],str):
				filetypes = (filetypes,)
			self.filter = filetypes[0]
			for desc,ext in filetypes:
				if isinstance(ext,str):
					s = "%s (%s)"%(desc,ext)
					ext = (ext,)
				else:
					s = "%s (%s)"%(desc, ",".join(ext))
				self.typeCombo.insert(END, s)
				self.filetypes[s] = ext

		b = Button(frame, text=_("Cancel"), command=self.cancel)
		b.grid(row=1, column=2, sticky=EW)
		frame.grid_columnconfigure(1, weight=1)

		self.bind("<Return>", self.openFilename)
		self.bind("<Escape>", self.cancel)

		# Variables
		# 1st set the path if any
		if initialdir:
			self.path = os.path.abspath(initialdir)
		else:	# otherwise to the current directory
			self.path = os.getcwd()

		if initialfile:
			# if a file is specified and has a different path
			initialfile = os.path.abspath(initialfile)
			d,n = os.path.split(initialfile)
			if d != "": self.path = d
			self.filename.insert(0, n)
			self.filename.select_range(0,END)

		# Flags
		self.hidden = False	# Show hidden files
		self.links  = True	# Show links
		self.dirs   = True	# Show directories
		self.files  = True	# Show files
		self.seldir = False	# Select directory instead of file
		self.selFile = ""	# Selected files
		append2History(self.path)

		# popup history
		self._popup = None
		self._historyOldLen = len(_history)

	# ----------------------------------------------------------------------
	def show(self):
		self.deiconify()
		if FileDialog.width > 0:
			self.geometry("%dx%d" \
				%(FileDialog.width, FileDialog.height))

		self.buttonPath(self.path)
		self.typeCombo.set(self.typeCombo.get(0))	# will fill the files
		try:
			self.lift()
			self.focus_set()
			self.filename.focus_set()
			self.wait_visibility()
			self.grab_set()
			self.wait_window()
		except TclError:
			pass
		return self.selFile

	# ----------------------------------------------------------------------
	# Restore sash size on creation
	# ----------------------------------------------------------------------
	def resize(self, event):
		if FileDialog.sash is not None:
			FileDialog.sash.reverse()
			# XXX XXX ERROR: paneframe doesn't update the width/height
			# so all sash placement is wrong
			self.fileList.paneframe.update()
			#self.fileList.paneframe.update_idletasks()
			if FileDialog.sash is not None:
				n = len(FileDialog.sash)-1
				for i,x in enumerate(FileDialog.sash):
					self.fileList.paneframe.sash_place(n-i,x,1)
				FileDialog.sash = None

	# ----------------------------------------------------------------------
	# Create buttons for the path
	# ----------------------------------------------------------------------
	def buttonPath(self, path):
		path = path.split(os.sep)
		if path[0] == "": path[0] = os.sep
		if path[-1] == "": del path[-1]
		lp = len(path)
		lb = len(self.buttons)

		i = 0
		same = True
		while i < min(lp, lb):
			b = self.buttons[i]
			if path[i] != b["text"]:
				b["text"] = path[i]
				same = False
			i += 1

		if lb < lp:	# Create new buttons
			while i < lp:
				self.buttons.append(Button(self.dirframe,
					text=path[i],
					command=lambda s=self,b=i:s.button(b),
					padx=1))
				i += 1
				self.buttons[-1].grid(row=0, column=i)

		elif lp < lb and not same:	# Use existing buttons
			while i < lb:
				self.buttons[i].grid_forget()
				i += 1
			del self.buttons[lp:]

		for i in range(lp):
			self.buttons[i]["foreground"] = "black"
			self.buttons[i]["activeforeground"] = "black"
		self.buttons[lp-1]["foreground"] = "blue"
		self.buttons[lp-1]["activeforeground"] = "blue"
		for i in range(lp, len(self.buttons)):
			self.buttons[i]["foreground"] = "darkgray"
			self.buttons[i]["activeforeground"] = "darkgray"

	# ----------------------------------------------------------------------
	def button(self, b):
		path = [ x["text"] for x in self.buttons[0:b+1] ]
		if path[0] == os.sep:
			path = os.sep + os.sep.join(path[1:])
		else:
			path = os.sep.join(path)
		if path=="": path=os.sep
		self.fileList.focus_set()
		self.changePath(path)

	# ----------------------------------------------------------------------
	def history(self, event=None):
		if self._popup is not None:
			self._historyDestroy()
			return
		self.downButton["relief"] = SUNKEN
		self._popup = Toplevel(self)
		self._popup.transient(self)
		self._popup.overrideredirect(1)
		self._popup.withdraw()
		self._popup.bind('<Escape>',	self._historyDestroy)
		self._popup.bind('<FocusOut>',	self._historyFocusOut)

		x = self.buttons[0].winfo_rootx()
		y = self.buttons[0].winfo_rooty() + self.buttons[0].winfo_height() - 2
		w = self.downButton.winfo_rootx() + self.downButton.winfo_width() - x
		h = self.fileList.winfo_height() - 20
		self._popup.geometry('%dx%d+%d+%d' % (w,h,x,y))

		sb = Scrollbar(self._popup, orient=VERTICAL, takefocus=False)
		sb.pack(side=RIGHT, fill=Y)
		self._popupList = Listbox(self._popup,
			background="White",
			selectmode=BROWSE,
			takefocus=True,
			yscrollcommand=sb.set)
		self._popupList.pack(side=LEFT, fill=BOTH, expand=YES)
		self._popupList.bind("<ButtonRelease-1>", self._historyClick)
		self._popupList.bind("<Return>", self._historyClick)
		sb.config(command=self._popupList.yview)
		for h in sorted(_history):
			self._popupList.insert(END, h)
		self._popupList.selection_set(0)
		self._popupList.activate(0)

		self.grab_release()
		self._popup.deiconify()
		self._popup.lift()
		self._popup.focus_set()
		self._popupList.focus_set()
		self._popup.update_idletasks()

	# ----------------------------------------------------------------------
	def _historyFocusOut(self, event):
		try:
			f = self.focus_get()
		except KeyError:
			pass
		else:
			if f == self._popup or f == self._popupList:
				return
		self._historyDestroy()

	# ----------------------------------------------------------------------
	def _historyClick(self, event):
		try:
			sel = self._popupList.curselection()[0]
			self.changePath(self._popupList.get(sel))
			self._historyDestroy()
		except:
			pass

	# ----------------------------------------------------------------------
	def _historyDestroy(self, event=None):
		self.downButton["relief"] = RAISED
		self._popup.destroy()
		self._popup = None
		self.grab_set()
		self.focus_set()
		return "break"

	# ----------------------------------------------------------------------
	def upDir(self, event):
		if not tkExtra.ExListbox._search:
			self.changePath(os.path.dirname(self.path))
		else:
			event.widget.handleKey(event)

	# ----------------------------------------------------------------------
	def changePath(self, path):
		if path[-1] != os.sep: path += os.sep
		path = os.path.abspath(path)
		try: os.lstat(path)
		except OSError:
			messagebox.showerror(_("Error"),
				_("Cannot access path \"%s\"")%(path),
				parent=self)
			return
		self.buttonPath(path)
		self.path = path
		self.fill()
		append2History(self.path)

	# ----------------------------------------------------------------------
	def fill(self, path=None):
		self.fileList.delete(0,END)
		self.fileList.listbox(0).resetSearch()

		if path is None: path = self.path

		# Populate list but sorted
		try:
			for fn in os.listdir(path):
				if not self.hidden and fn[0]==".": continue
				filename = os.path.join(path, fn)
				ext, color = fileTypeColor(filename)

				try: s = os.lstat(filename)
				except: continue

				size  = 0
				islnk = S_ISLNK(s[ST_MODE])
				if islnk:
					try: s = os.stat(filename)
					except: continue
				isdir = S_ISDIR(s[ST_MODE])

				if self.filter is not None and not isdir and not islnk:
					match = False
					for pat in self.filter:
						if fnmatch.fnmatch(fn, pat):
							match = True
							break
				else:
					match = True

				if isdir:
					if not self.dirs: continue
				elif islnk:
					if not self.links: continue
				else:
					size = s[ST_SIZE]

				if match:
					self.fileList.insert(END, (fn, ext, size,
						 time.strftime(_TIME_FORMAT,
							time.localtime(s[ST_MTIME]))))
					if not self.files and not isdir:
						self.fileList.setColor(END, DISABLE_FILE)
					elif color:
						self.fileList.setColor(END, color)
		except OSError:
			messagebox.showerror(_("Error"),
				_("Error listing folder \"%s\"")%(path),
				parent=self)

		if FileDialog.sort is None:
			self.fileList.sort(0, False)		# First short by name
			# Move all directories to top
			self.fileList.sort(1, False)		# then by type
			FileDialog.sort = None
		else:
			self.fileList.restoreSort(FileDialog.sort)

		# Find item to select
		fn = self.filename.get()
		if self.seldir: fn = os.path.basename(fn)
		for i in range(self.fileList.size()):
			if fn == self.fileList.listbox(0).get(i):
				self.fileList.see(i)
				self.fileList.activate(i)
				self.fileList.selection_set(i)
				break
		else:
			self.fileList.see(0)
			self.fileList.activate(0)
			self.fileList.selection_set(0)

	# ----------------------------------------------------------------------
	def sortChanged(self, event=None):
		FileDialog.sort = self.fileList.saveSort()

	# ----------------------------------------------------------------------
	def open(self, fn):
		if self.seldir and self.path == fn:
			self.selFile = self.path

		# Single file selection
		elif fn.find('","')<0:
			# Check for path
			try:
				filename = os.path.join(self.path, fn)
				s = os.stat(filename)
				if S_ISDIR(s[ST_MODE]):
					self.changePath(filename)
					self.filename.delete(0,END)
					return
			except OSError:
				pass

			# Check for a pattern
			if fn.find('*')>=0 or fn.find('?')>=0:
				self.filter = (fn,)
				self.fill()
				return

			# Check for extension
			if self.filter:
				fn,ext = os.path.splitext(filename)
				if ext == "":
					ffn,ffext = os.path.splitext(self.filter[0])
					if ffext!="":
						filename = fn+ffext

			if self.multiple:
				self.selFile = [filename]
			else:
				self.selFile = filename

		# Multiple file selection
		else:
			self.selFile = [os.path.join(self.path,f) \
					for f in fn[1:-1].split('","')]

		if self.check():
			global _history
			# Delete all temporary directories and keep only the last one
			if len(_history) > self._historyOldLen:
				del _history[self._historyOldLen:]
			append2History(self.path)
			self.close()

	# ----------------------------------------------------------------------
	# Open the filename entered in the entry box
	# ----------------------------------------------------------------------
	def openFilename(self, event=None):
		fn = self.filename.get()
		# Single file selection?
		if fn=="":
			self.select()
			fn = self.filename.get()
			if fn=="": return
		self.open(fn)

	# ----------------------------------------------------------------------
	def check(self): return True

	# ----------------------------------------------------------------------
	def cancel(self, event=None):
		if self._popup is not None:
			self._historyDestroy()
		else:
			self.selFile = ""
			self.close()

	# ----------------------------------------------------------------------
	def close(self):
		FileDialog._active = False
		FileDialog.width   = self.winfo_width()
		FileDialog.height  = self.winfo_height()
		FileDialog.sash    = [self.fileList.paneframe.sash_coord(i)[0]
					for i in range(len(self.fileList.listboxes())-1)]
		tkExtra.ExListbox.resetSearch()
		self.grab_release()
		self.destroy()

	# ----------------------------------------------------------------------
	def double(self, event):
		sel = self.fileList.curselection()
		if len(sel)!=1: return
		item = self.fileList.get(sel[0])
		if item[1] == _DIR_TYPE:
			self.changePath(os.path.join(self.path, item[0]))
			return "break"
		elif item[1] == _LINK_TYPE:
			# maybe a directory?
			path = os.path.join(self.path, item[0])
			try:
				s = os.stat(path)
				if S_ISDIR(s[ST_MODE]):
					self.changePath(path)
					return "break"
			except: pass
		self.openFilename()

	# ----------------------------------------------------------------------
	# Select current file from listbox
	# ----------------------------------------------------------------------
	def select(self, event=None):
		sel = self.fileList.curselection()

		if len(sel)==1:
			item = self.fileList.get(sel[0])[0]
			fn = os.path.join(self.path, item)
			if self.seldir:
				try:
					s = os.stat(fn)
					if not S_ISDIR(s[ST_MODE]):
						fn = os.path.dirname(fn)
				except OSError:
					pass
				self.filename.delete(0, END)
				self.filename.insert(0, fn)
			else:
				try:
					s = os.stat(fn)
					if not S_ISDIR(s[ST_MODE]):
						self.filename.delete(0, END)
						self.filename.insert(0, item)
				except OSError:
					pass
		else:
			lget = self.fileList.get
			files = ["\"%s\""%(lget(i)[0]) for i in sel]

			if files:
				self.filename.delete(0, END)
				self.filename.insert(0, ",".join(files))

			elif self.seldir:
				self.filename.delete(0, END)
				self.filename.insert(0, self.path)

	# ----------------------------------------------------------------------
	def typeChange(self, event=None):
		pat = self.typeCombo.get()
		self.filter = self.filetypes.get(pat,None)
		self.fill()
		if self.filter is None or self.seldir: return

		# Change extension if needed
		first = None
		filename = self.filename.get()
		if filename == "" or "," in filename: return
		fn,ext = os.path.splitext(filename)
		for i in self.filter:
			f,e = os.path.splitext(i)
			if first is None and e: first = e
			if e == ext: return
		else:
			if first:
				# not found, change the filename to the first extension
				self.filename.delete(0, END)
				self.filename.insert(0, fn+first)

	# ----------------------------------------------------------------------
	def newFolder(self):
		self.fileList.insert(END, (_("NewFolder"), _DIR_TYPE, 0,
					 time.strftime(_TIME_FORMAT,
					 time.localtime(time.time()))))
		self.fileList.see(END)
		self.fileList.selection_clear(0,END)
		self.fileList.selection_set(END)
		self.fileList.activate(END)
		edit = tkExtra.InPlaceEdit(self.fileList.listbox(0))
		if edit.value:
			try:
				os.mkdir(os.path.join(self.path, edit.value))
			except OSError:
				messagebox.showerror(_("Error"),
					_("Error creating folder \"%s\"")%(edit.value),
					parent=self)
				self.fileList.delete(END)
				return
			self.fileList.selection_set(END)
			self.fileList.see(END)
			self.fileList.setColor(END, COLORS.get(_DIR_TYPE))
			self.select()
		else:
			try:
				self.fileList.delete(END)
			except TclError:
				pass

	# ----------------------------------------------------------------------
	def rename(self,event=None):
		fn = self.fileList.listbox(0).get(ACTIVE)
		edit = tkExtra.InPlaceEdit(self.fileList.listbox(0))
		if edit.value and edit.value != fn:
			try:
				os.rename(os.path.join(self.path, fn),
					os.path.join(self.path, edit.value))
			except OSError:
				messagebox.showerror(_("Error"),
					_("Error renaming \"%s\" to \"%s\"") \
						%(fn, edit.value),
					parent=self)
		self.select()

	# ----------------------------------------------------------------------
	def delete(self):
		sel = map(int,self.fileList.curselection())
		sel.reverse()
		if not sel: return
		try:
			for i in sel:
				fn = self.fileList.listbox(0).get(i)
				filename = os.path.join(self.path, fn)
				s = os.lstat(filename)
				if S_ISDIR(s[ST_MODE]):
					os.rmdir(filename)
				else:
					os.remove(filename)
				self.fileList.delete(i)
		except OSError:
			messagebox.showerror(_("Error"),
					_("Error deleting file \"%s\"")%(fn),
					parent=self)
		self.select()

#===============================================================================
class OpenDialog(FileDialog):
	_title = _("Open")

	# ----------------------------------------------------------------------
	# Check if file exist
	# ----------------------------------------------------------------------
	def check(self):
		if isinstance(self.selFile, list):
			for f in self.selFile:
				try:
					os.lstat(f)
				except:
					messagebox.showwarning(_("File does not exist"),
						_("File \"%s\" does not exist")%(f),
						parent=self)
					self.selFile = ""
					return False
		else:
			try:
				os.lstat(self.selFile)
			except:
				messagebox.showwarning(_("File does not exist"),
					_("File \"%s\" does not exist")%(self.selFile),
					parent=self)
				self.selFile = ""
				return False
		return True

#===============================================================================
class SaveAsDialog(FileDialog):
	_title = _("Save As")

	# ----------------------------------------------------------------------
	def __init__(self, **kw):
		FileDialog.__init__(self, **kw)
		self.ok["text"] = _("Save")

	# ----------------------------------------------------------------------
	def check(self):
		try:
			os.lstat(self.selFile)
			ans = messagebox.askyesno(_("File already exists"),
				_("Overwrite existing file %r?")%(self.selFile),
				parent=self)
			if str(ans)!=messagebox.YES and not ans:
				self.selFile = ""
				return False
		except:
			pass
		return True

#===============================================================================
class DirectoryDialog(FileDialog):
	_title = _("Choose Directory")
	def __init__(self, **kw):
		FileDialog.__init__(self, **kw)
		self.files  = False
		self.seldir = True
		self.filename.insert(0, self.path)

	# ----------------------------------------------------------------------
	def changePath(self, path):
		path = os.path.abspath(path)
		FileDialog.changePath(self, path)
		self.filename.delete(0, END)
		self.filename.insert(0, path)

#===============================================================================
def askfilename(**options):
	"""Ask for a filename"""
	if FileDialog._active: return ""
	return FileDialog(**options).show()

def askopenfilename(**options):
	"""Ask for a filename to open"""
	if FileDialog._active: return ""
	return OpenDialog(**options).show()

def askopenfilenames(**options):
	"""Ask for a multiple filenames to open"""
	if FileDialog._active: return ()
	options["multiple"] = True
	return OpenDialog(**options).show()

def asksaveasfilename(**options):
	"""Ask for a filename to save as"""
	if FileDialog._active: return ""
	return SaveAsDialog(**options).show()

def askdirectory(**options):
	"""Ask for a directory"""
	if FileDialog._active: return ""
	return DirectoryDialog(**options).show()

#===============================================================================
if __name__ == "__main__":
	import sys

	root = Tk()
	root.withdraw()
	initdir = None
	if len(sys.argv)>1:
		initdir = os.path.abspath(sys.argv[1])
	#print askdirectory()

	files = asksaveasfilename(title=_("Open"),
			initialdir=initdir,
#			initialfile="test.f",
			filetypes=(("All","*"),
				("Python", "*.py"),
				("Flair",("*.flair", "*.inp"))))
	#print files

	#import tkFileDialog
	#print tkFileDialog.asksaveasfilename( title="Open flair project",
	#		initialdir=initdir,
	#		filetypes=(("All","*"),
	#			("Python", "*.py"),
	#			("Flair",("*.flair", "*.inp"))))
