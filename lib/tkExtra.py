#!/bin/env python
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
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	12-Oct-2006

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import re
import time
import Unicode
import bFileDialog
from log import say

try:
	from Tkinter import *
	from Tkinter import _setit, _cnfmerge
	from tkColorChooser import askcolor
except ImportError:
	from tkinter import *
	from tkinter import _setit, _cnfmerge
	from tkinter.colorchooser import askcolor

ARROW_LEFT     = u"\u2190"
ARROW_UP       = u"\u2191"
ARROW_RIGHT    = u"\u2192"
ARROW_DOWN     = u"\u2193"

CROSS          = u"\u2A2F"	# x -cross product
MULT           = u"\u00D7"	# x -multiplication

DIAMOND_SQUARE = u"\u26CB"

# Key state codes
SHIFT_MASK	= 1
CONTROL_MASK	= 4
ALT_MASK	= 8

# Ansi escape sequences
ANSI_CLEAR	= "\033[2J"
ANSI_BOLD	= "\033[1m"
ANSI_UNDERLINE	= "\033[4m"
ANSI_REVERSE	= "\033[7m"
ANSI_NORMAL	= "\033[m"

# base64.encodestring(open("save.gif","rb").read())
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
_ALLICON = """
R0lGODlhEAAQAKUiAMwjzMcmx6wt2MEqv7ksxLosxL8su6wv1sMru4c4674swLwtvb8sv70tvbou
vrouwrovucQsurovurkwu7gxuLsxu7szu01N/9gtrNgtrbo1uro2uus4h61XraxZrP9NTYech03/
Tf//////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////yH5BAEKAD8ALAAAAAAQABAAAAaMwJ9Q
OEBgMojBcEmMcD4fTkTJ/AEQT2gUAagCMlptpsv8hqFjLzbM4VZ/AydUSl0CAAGI4WiABO5DDBYe
HRUSAQESDgIHDwo/DBsgISEgGw0LBAkXFwkEChaTlJUUE5ucnQ8do6MaBaioB6usIa6wnAehrCCl
p5wJD5Gilpiav5+Qgx0WDEIKD4yOP0EAOw==
"""
_NONEICON = """
R0lGODlhEAAQAKUhAAAAAA8EBAYLEBgHBwQPBAkLHgoKKwcOFQoLKwUTBQsOJyYKCgoSGysKCg4R
LwcYBy8MDBERRhISSQgeCEYRERgYYkkSEgomCgorCgwvDCAggGIYGIAgIBFGERJJEhhiGCCAIP//
////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////yH5BAEKAD8ALAAAAAAQABAAAAaGwJ9Q
OIBQLJDBcElsbDicTUPJFEKe0CikKrRksxbuz/vlhLnX72bLHTihUmoVEFgcFwEA85HpeC4EAAAC
ChESDgw/DxgfICAfGAkHCBUaGhUIDBmNjo8TBZWWlw4enZ0YBqKiEqWmIKiqlhKbph+foZYVDouc
kJKUuZmKfR4ZD0IMDoaIP0EAOw==
"""
_INVICON = """
R0lGODlhEAAQAOeLAFBQUFBQWFFRUVJSUk1UVE9UVFNUVFRUVFRVVVVVVdI1NVdXV1RYWNM2NlhY
XtM4OFlZXdM6OtM7O1lcXF5bW9Q8PNQ9PdQ+PtQ/P1phYdVAQGBgYNVBQWFhZNVCQmJiYtVDQ9VE
RG5gYGNjY9dERNVFRWZkZNZGRtpFRWVlZdZHRtZHR9hHR9ZISNZJSWdnZ9ZKStZKT9xJSdZLS2pq
a9dNTdhOToRlZWxsbNhPT9hPU21ta9hQUNlQUJthYdhRUdlRUdhSUNhSUppjY9lTVNlWVnJyctlX
V3V1WOFWVt5XV291dXR0dOBXV91YWNpZWdpZW6FpaXV1dXJ3d9pbXNpcXnd3d8liYtNgYNVgYNtf
X79nZ9xhYb1qatxiYnx8fHp9fX19fdZoaICAgN9oaN5sWYODg4WFhd9tbd9vb4mIiN9xceBzc7l+
fqeDg+B0dIOPj+F3d46Ojo+Pj5OTk5eXYZmZTJSUlJWUlKOUlJ2dVeWLWZ2dnZWioqGhoaenp+qj
T+2xUfLCRfLHWNnZON/fPODgMPbYSOPjMvffRvnmO///////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
/////////////////////////////////////////////////////yH5BAEKAP8ALAAAAAAQABAA
AAjhAP8JHOjlyRMvAxMKTMMDg4QHDSRUEMJGIZoWJTBEaKDgAYcQK9YMfGNjxgkOFh48sKChBIwa
cQRqASIDBQgNF1iWaFHjBxeBTqLA6dOGRAgPJ1QEKaOjiBgyIkxYOYMnj4sWMGIMOgSISpYhBhak
kDJGjRsWOY4kUiQIChYwCQLoqUODyZQtPYjsCVRFSRczB+wQMrSDwocMPrg0SXLlxpJ/A5AgKuQg
wYEDCAhMYFBAwJx/Lw50gJCgtGnTOATSAXC6dQIAfAbKEeC6NIA7Cv1sGHB6wIg/ChN+MWIkTPCA
ADs=
"""

#-------------------------------------------------------------------------------
# bind event with data as a replacement of the Tkinter bind for virtual
# events to send data <<...>>
#
# Example, instead of binding like
#	widget.bind("<<VirtualEvent>>", function)
# use it as
#	bindEventData(widget, "<<VirtualEvent>>", function)
#
# def function(event):
#	print event.serial, event.widget, event.data
#
# Send message as
#	widget.event_generate("<<VirtualEvent>>", data="Hello")
#	widget.event_generate("<<VirtualEvent>>", data=("One","Two"))
#	widget.event_generate("<<VirtualEvent>>", serial=10, data=("One","Two"))
#
# WARNING: Unfortunatelly it will convert data to STRING!!!
#-------------------------------------------------------------------------------
def bindEventData(widget, sequence, func, add = None):
	def _substitute(*args):
		e = Event()
		nsign, b, t, T, d, W = args
		try:    e.serial = int(nsign)
		except: e.serial = nsign
		try:    e.num    = int(b)
		except: e.num    = b
		try:    e.time   = int(t)
		except: e.time   = t
		e.type = T
		e.data = d
		try:
			e.widget = widget._nametowidget(W)
		except KeyError:
			e.widget = W
		return (e,)

	funcid = widget._register(func, _substitute, needcleanup=1)
	cmd = '{0}if {{"[{1} %# %b %t %T %d %W]" == "break"}} break\n'.format('+' if add else '', funcid)
	widget.tk.call('bind', widget._w, sequence, cmd)

#===============================================================================
# Sort Assist class for MultiListbox
#===============================================================================
class SortAssist:
	def __init__(self, column):
		self.column = column

	def __call__(self, x):
		return x[self.column]

#-------------------------------------------------------------------------------
# Multiple configuration of many widgets given in a list
# lst = list of widgets
#-------------------------------------------------------------------------------
def multiConfig(lst, **opts):
	"""Multiple configuration of many widgets"""
	for w in lst:
		w.config(**opts)

#-------------------------------------------------------------------------------
# Toggle toplevel window height
#-------------------------------------------------------------------------------
def toggleHeight(root, oldHeight):
	"""Toggle window height"""
	m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", root.wm_geometry())
	if not m:
		root.bell()
		return oldHeight

	width, height, x, y = map(int, m.groups())
	maxheight = root.winfo_screenheight()

	if sys.platform in ("win32", "win64"):
		newy = 0
		newheight = maxheight - 72
	else:
		#newy = 24
		newy = 0
		#newheight = maxheight - 96
		newheight = maxheight - 88

	if height >= newheight:
		try:
			newheight = oldHeight
		except:
			return oldHeight

	newgeom = "%dx%d+%d+%d" % (width, newheight, x, newy)
	root.wm_geometry(newgeom)
	return height

#===============================================================================
def _entryPaste(event):
	"""global replacement for the Entry.paste"""
	try:
		event.widget.delete('sel.first', 'sel.last')
	except TclError:
		pass	# nothing is selected

	# in tk.call() use the widget's string representation event.widget._w
	# instead of event.widget, which is the widget instance itself
	try:
		text = event.widget.tk.call('::tk::GetSelection', event.widget._w, 'CLIPBOARD')
	except TclError:
		return
	event.widget.insert('insert', text)
	event.widget.tk.call('tk::EntrySeeInsert', event.widget._w)
	return "break"

#-------------------------------------------------------------------------------
def _textPaste(event):
	"""global replacement for the Text.paste"""
	oldSeparator = event.widget.cget("autoseparators")
	if oldSeparator:
		event.widget.config(autoseparators=0)
		event.widget.edit_separator()
	try:
		event.widget.delete('sel.first', 'sel.last')
	except TclError:
		pass	# nothing is selected

	# in tk.call() use the widget's string representation event.widget._w
	# instead of event.widget, which is the widget instance itself
	try:
		text = event.widget.tk.call('::tk::GetSelection', event.widget._w, 'CLIPBOARD')
	except TclError:
		return
	event.widget.insert('insert', text)
	if oldSeparator:
		event.widget.edit_separator()
		event.widget.config(autoseparators=1)
	event.widget.see('insert')
	return "break"

#-------------------------------------------------------------------------------
def bindClasses(root):
	root.bind_class('Entry', '<Control-Key-a>', lambda e: e.widget.selection_range(0,END))
	root.bind_class('Entry', '<<Paste>>', _entryPaste)
	root.bind_class('Text',  '<<Paste>>', _textPaste)

#===============================================================================
# LabelEntry. display a label when entry field is empty
#===============================================================================
class LabelEntry(Entry):
	def __init__(self, master, label=None, labelcolor=None, **kw):
		Entry.__init__(self, master, **kw)
		self.label  = label
		self._empty = True
		self._fg    = self["foreground"]
		if labelcolor is not None:
			self.labelcolor = labelcolor
		else:
			self.labelcolor = self._fg
		self.bind("<FocusIn>",  self._focusIn)
		self.bind("<FocusOut>", self._focusOut)
		self["validate"] = "key"
		self["validatecommand"] = (self.register(self.validate), '%P')
		self.showLabel()

	# ----------------------------------------------------------------------
	def showLabel(self):
		self.delete(0,END)
		self.insert(0, self.label)
		self["foreground"] = self.labelcolor
		self._empty = True	# Restore empty since validation will destroy it

	# ----------------------------------------------------------------------
	def removeLabel(self):
		self.delete(0,END)
		self["foreground"] = self._fg

	# ----------------------------------------------------------------------
	def _focusIn(self, event):
		if self._empty:
			self.removeLabel()

	# ----------------------------------------------------------------------
	def _focusOut(self, event):
		if self._empty or self.get()=="":
			self.showLabel()

	# ----------------------------------------------------------------------
	def validate(self, value):
		self._empty = value == ""
		return True

	# ----------------------------------------------------------------------
	def set(self, value):
		self._empty = value==""
		if self._empty:
			self.showLabel()
			self.master.focus_set()	# lose focus
		else:
			self.removeLabel()
			self.insert(0, value)

	# ----------------------------------------------------------------------
	def get(self):
		if self._empty:
			return ""
		else:
			return Entry.get(self)

#===============================================================================
# _ValidatingEntry
#===============================================================================
class _ValidatingEntry(Entry):
	"""base class for validating entry widgets"""
	# ----------------------------------------------------------------------
	def __init__(self, master, value="", **kw):
		Entry.__init__(self, master, **kw)
		self["validate"] = "key"
		self["validatecommand"] = (self.register(self.validate), '%P')

	# ----------------------------------------------------------------------
	def validate(self, value):
		# override: return True if valid False if invalid
		return True

	# ----------------------------------------------------------------------
	def set(self, value):
		self.delete(0,END)
		self.insert(0, value)

	# ----------------------------------------------------------------------
	def getint(self, default=0):
		try:
			return int(self.get())
		except:
			return default

	# ----------------------------------------------------------------------
	def getfloat(self, default=0.0):
		try:
			return float(self.get())
		except:
			return default

#===============================================================================
# Maximum Length Entry
#===============================================================================
class MaxLengthEntry(_ValidatingEntry):
	"""MaxLengthEntry limit entry length maximum maxlength characters"""
	def __init__(self, master, value="", maxlength=None, **kw):
		_ValidatingEntry.__init__(self, master, value, **kw)
		self.maxlength = maxlength

	# ----------------------------------------------------------------------
	def insert(self, idx, value):
		m = self.maxlength
		self.maxlength = None
		_ValidatingEntry.insert(self, idx, value)
		self.maxlength = m

	# ----------------------------------------------------------------------
	def validate(self, value):
		if self.maxlength is not None:
			return len(value) <= self.maxlength
		return True

#===============================================================================
# Integer Validating Entry
#===============================================================================
class IntegerEntry(_ValidatingEntry):
	"""IntegerEntry accepting only integers"""
	# ----------------------------------------------------------------------
	def validate(self, value):
		try:
			if value: int(value)
			return True
		except ValueError:
			if value=="+" or value=="-": return True
		return False

#===============================================================================
# Floating Point Validating Entry
#===============================================================================
class FloatEntry(_ValidatingEntry):
	"""accept only floating point numbers"""
	# ----------------------------------------------------------------------
	def validate(self, value):
		try:
			if value: float(value)
			return True
		except ValueError:
			if value=="+" or value=="-" or value=="." or \
			   value=="+." or value=="-.": return True
			if len(value)>1:
				last = value[-1]
				if last=="e" or last=="E": return True
				plast = value[-2]
				if (plast=="e" or plast=="E") and \
				   (last=="-" or last=="+"): return True
		return False

#===============================================================================
# Vector Validating Entry
#===============================================================================
class VectorEntry(_ValidatingEntry):
	"""accept only vectors"""
	# ----------------------------------------------------------------------
	def validate(self, value):
		# remove from value comma, semicolon, and parenthesis () []
		for token in re.sub(r"[(),;\[\]]","",value).split():
			try:
				float(token)
			except ValueError:
				if token=="+" or token=="-" or token=="." or \
				   token=="+." or token=="-.": continue
				if len(token)>1:
					last = token[-1]
					if last=="e" or last=="E": continue
					plast = token[-2]
					if (plast=="e" or plast=="E") and \
					   (last=="-" or last=="+"): continue
				return False
		return True

	# ----------------------------------------------------------------------
	# Get contents as a list
	# ----------------------------------------------------------------------
	def getlist(self):
		return re.sub(r"[(),;\[\]]","",self.get()).split()

	# ---------------------------------------------------------------------
	# Split vector in to a list of widgets
	# ----------------------------------------------------------------------
	def split(self, widgets):
		value = self.get()
		for ch in " ,()[];":
			if ch in value:
				xyz = self.getlist()
				if xyz:
					self.set(xyz[0])
					for i,w in enumerate(widgets):
						if len(xyz)>i+1: w.set(xyz[i+1])
				return

#===============================================================================
# Auto Scroll Bar
# Author: Fredrik Lundh <www.pythonware.com>
#===============================================================================
class AutoScrollbar(Scrollbar):
	# ----------------------------------------------------------------------
	# a scrollbar that hides itself if it's not needed.  only
	# works if you use the grid geometry manager.
	# ----------------------------------------------------------------------
	def set(self, lo, hi):
		flo = float(lo)
		fhi = float(hi)
		try:
			g = self.get()
		except TclError:
			return
		if abs(flo-float(g[0]))<=0.001 and abs(fhi-float(g[1]))<=0.001: return
		if flo <= 0.001 and fhi >= 0.999:
			if self.method==0:
				# grid_remove is currently missing from Tkinter!
				self.tk.call("grid", "remove", self)
			else:
				self.tk.call("pack", "forget", self)

		elif flo > 0.001 or fhi < 0.999:
			if self.method==0:
				Scrollbar.grid(self)
			else:
				Scrollbar.pack(self)
		Scrollbar.set(self, lo, hi)

	# ----------------------------------------------------------------------
	def grid(self, **kw):
		self.method = 0
		Scrollbar.grid(self, **kw)

	# ----------------------------------------------------------------------
	def pack(self, **kw):
		self.method = 1
		Scrollbar.pack(self, **kw)
		#raise TclError("cannot use pack with this widget")

	# ----------------------------------------------------------------------
	def place(self, **kw):
		raise TclError("cannot use place with this widget")

#===============================================================================
# ProgressBar Canvas
#===============================================================================
class ProgressBar(Canvas):
	def __init__(self, master=None, **kw):
		Canvas.__init__(self, master, **kw)
		#self.config(background="DarkGray")
		self.currBox = self.create_rectangle(0, 0, 0, 0,
					fill='Orange',
					width=0)
		self.doneBox = self.create_rectangle(0, 0, 0, 0,
					fill='DarkGreen',
					width=0)
		self.text = self.create_text(0,0,
					text="",
					fill="White",
					anchor=CENTER,
					justify=CENTER)
		self.auto = True
		self.showTime = True

		self.bind('<Configure>', self.draw)
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
		self.low    = float(low)
		self.high   = float(high)
		self.length = float(high-low)
		self.step   = float(step)
		self.done   = float(low)
		self.now    = float(low)
		self.t0     = time.time()
		self.msg    = ""

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
		p  = now - self.low
		if p>0:
			tot = dt/p*(self.high-self.low)
		else:
			tot = 0.0

		# elapsed time
		dh,s  = divmod(dt,3600)
		dm,ds = divmod(s,60)
		if dh > 0:
			elapsedTxt = "%dh%02dm"%(dh,dm)
		elif dm > 0:
			elapsedTxt = "%dm%02ds"%(dm,ds)
		else:
			elapsedTxt = "%ds"%(ds)

		# total time
		th,s  = divmod(tot,3600)
		tm,ts = divmod(s,60)
		if th > 0:
			totalTxt = "Tot: %dh%02dm"%(th,tm)
		elif tm > 0:
			totalTxt = "Tot: %dm%02ds"%(tm,ts)
		else:
			totalTxt = "Tot: %ds"%(ts)

		# remain time
		remain = tot - dt
		if remain>0:
			rh,s  = divmod(remain,3600)
			rm,rs = divmod(s,60)
			if rh > 0:
				remainTxt = "Rem: %dh%02dm"%(rh,rm)
			elif rm > 0:
				remainTxt = "Rem: %dm%02ds"%(rm,rs)
			else:
				remainTxt = "Rem: %ds"%(rs)
		else:
			remainTxt = ""

		self.draw()
		if txt is not None:
			self.setText(txt)

		elif self.auto:
			if self.showTime:
				self.autoText("[%s %s %s]"%(elapsedTxt, totalTxt, remainTxt))
			else:
				self.autoText("")

	# ----------------------------------------------------------------------
	def clear(self):
		self.setProgress(0, 0);

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
			low = "%d - "%(self.low)
		else:
			low = ""
		self.msg = "Current: %d [%s%d]  Completed: %d%% %s" % \
			(self.now, low, self.high,
			 int((100*completed)/self.length),
			 tmsg)
		self.setText(self.msg)

	# ----------------------------------------------------------------------
	def getProgress(self):
		return (self.done, self.now)

	# ----------------------------------------------------------------------
	def draw(self, event=None):
		width  = self.winfo_width()
		height = self.winfo_height()

		wn = int(width * (self.now  - self.low) / self.length)
		wd = int(width * (self.done - self.low) / self.length)
		if wd >= wn: wd = wn - 1

		self.coords(self.currBox, 0, 0, wn, height)
		self.coords(self.doneBox, 0, 0, wd, height)

		if self.itemcget(self.text, "justify") == CENTER:
			self.coords(self.text, width/2, height/2)
		else:
			self.coords(self.text, 1,height/2)

#===============================================================================
# Extended Listbox
#===============================================================================
class ExListbox(Listbox):
	"""Listbox that allows keyboard scanning, and a popup menu"""

	_KEY_TIME_THRESHOLD = 1000	# ms
	_searchTop	    = None
	_searchLabel	    = None
	_search		    = ""
	_searchOrig	    = ""
	_time		    = 0

	def __init__(self, master, **kw):
		Listbox.__init__(self, master, **kw)
		ExListbox.resetSearch()
		self._single = kw.get('selectmode','') in [SINGLE, BROWSE]
#		self.bind('<Button-1>', lambda e,s=self:s.focus_set())
		self.bind('<Key>',	self.handleKey)
		self.bind('<Home>',	lambda e,s=self:s._scrollTo(0))
		self.bind('<Prior>',	lambda e,s=self:s._scrollTo(-1, PAGES))
		self.bind('<Next>',	lambda e,s=self:s._scrollTo( 1, PAGES))
		self.bind('<End>',	lambda e,s=self:s._scrollTo(END))
		self.bind('<FocusOut>',	ExListbox._hideSearch)
		self.bind('<Unmap>',	ExListbox._hideSearch)
		self.bind('<<Cut>>',	self.copy)
		self.bind('<<Copy>>',	self.copy)

		if not self._single:
			self.bind('<Control-Key-a>',	self.selectAll)
			self.bind('<Control-Shift-A>',	self.selectClear)
			self.bind('<Button-3>',		self.popupMenu)
			self.bind('<Control-Key-space>',self.popupMenu)

		# User variables to modify
		self.additionalChar = "-+._:$%#*"
		self.ignoreNonAlpha = True	# Ignore non-alpha characters
		self.ignoreCase     = True	# Ignore case of letters
		self.showSearch     = True
		self.usermenu	    = None	# Assign a user-popup menu
						# Should be a list with tuples
						#  in the form:
						#  (label, underline, commmand)
						# or None for separator

	# ----------------------------------------------------------------------
	def setPopupMenu(self, menu=None):
		"""Setup a popup menu list it should be in the form
		   [ (label, underline, command), ... ]"""
		self.usermenu = menu
		self.bind('<Button-3>',		self.popupMenu)
		self.bind('<Control-Key-space>',self.popupMenu)

	# ----------------------------------------------------------------------
	@staticmethod
	def resetSearch():
		"""Reset search string"""
		ExListbox._search     = ""
		ExListbox._searchOrig = ""
		ExListbox._time       = 0
		if ExListbox._searchTop is not None:
			try:
				ExListbox._searchTop.withdraw()
			except TclError:
				ExListbox._searchTop = None

	# ----------------------------------------------------------------------
	@staticmethod
	def _hideSearch(event=None):
		if ExListbox._searchTop is not None:
			try: ExListbox._searchTop.withdraw()
			except: pass

	# ----------------------------------------------------------------------
	def _showSearch(self):
		if ExListbox._searchTop is None:
			ExListbox._searchTop = Toplevel()
			ExListbox._searchTop.overrideredirect(1)
			ExListbox._searchLabel = Label(ExListbox._searchTop,
						anchor=E,
						relief=SOLID,
						background="Yellow",
						takefocus=False,
						borderwidth=1)
			ExListbox._searchLabel.pack(fill=BOTH)

		if ExListbox._searchOrig == "":
			ExListbox._hideSearch()
			return

		ExListbox._searchLabel["text"]=ExListbox._searchOrig
		ExListbox._searchTop.update_idletasks()

		# Guess position
		x = self.winfo_rootx() + self.winfo_width() \
				       - ExListbox._searchLabel.winfo_width()
		y = self.winfo_rooty() + self.winfo_height()-12
		ExListbox._searchTop.wm_geometry("+%d+%d" % (x,y))
		ExListbox._searchTop.deiconify()
		ExListbox._searchTop.lift()
		ExListbox._searchTop.update_idletasks()

	# ----------------------------------------------------------------------
	# Handle key events for quick searching
	# ----------------------------------------------------------------------
	def handleKey(self, event):
		"""handle key events for quick searching"""

		# Shift key -> ignore them
		if event.keysym in ("Shift_L","Shift_R"):
			return

		elif len(event.char)==0:
			ExListbox._time = 0
			return

		if self.ignoreCase:
			ch = event.char.upper()
		else:
			ch = event.char

		oldActive = self.index(ACTIVE)
		again = False

		# Delete search
		if event.keysym in ("Delete","Escape","Return","KP_Enter"):
			ExListbox.resetSearch()
			return
		# Search Again	Ctrl-G
		elif event.char=='\007':
			# Space bar selects...
			#(event.char==' ' and self.ignoreNonAlpha):
			self.activate(oldActive+1)
			again = True
		# Backspace
		elif event.keysym == "BackSpace":
			ExListbox._search     = ExListbox._search[:-1]
			ExListbox._searchOrig = ExListbox._searchOrig[:-1]

		# Ignore non-printable characters
		elif self.ignoreNonAlpha and \
		     not (ch.isalnum() or \
		     self.additionalChar.find(ch)>=0):
			return
		# Timeout
		elif event.time - ExListbox._time > ExListbox._KEY_TIME_THRESHOLD:
			# Start a new search
			ExListbox._search     = ch
			ExListbox._searchOrig = event.char
		else:
			ExListbox._search     += ch
			ExListbox._searchOrig += event.char

		if self.showSearch: self._showSearch()

		lsearch = len(ExListbox._search)
		ExListbox._time = event.time

		start  = 0
		cur    = self.index(ACTIVE)
		active = unicode(self.get(ACTIVE))

		if self.ignoreCase:
			try: active = active.upper()
			except: pass
		if len(active)>0:
			if self.ignoreNonAlpha:
				for pos in range(len(active)):
					if active[pos].isalnum() or self.additionalChar.find(active[pos])>=0:
						break
			else:
				pos = 0
			prefix = active[pos:pos+lsearch]
			if ExListbox._search == prefix:
				if self._single:
					self.selection_clear(0, END)
					self.selection_set(cur)
				self.activate(cur)
				self.see(cur)
				self.event_generate("<<ListboxSelect>>")
				return 'break'
			elif ExListbox._search[:-1] == prefix[:-1]:
				start = cur+1

		loop = 1
		while loop <= 2:
			if again:
				start = cur+1
				again = False
			#elif oldActive != self.index(ACTIVE):
			else:
				start = 0
				loop += 1

			for i in range(start, self.size()):
				item = unicode(self.get(i))
				if self.ignoreCase:
					try: item = item.upper()
					except: pass

				if len(item)>0:
					if self.ignoreNonAlpha:
						for pos in range(len(item)):
							if item[pos].isalnum() or self.additionalChar.find(item[pos])>=0:
								break
					else:
						pos = 0
					prefix = item[pos:pos+lsearch]
					if ExListbox._search == prefix:
						if self._single:
							self.selection_clear(0, END)
							self.selection_set(i)
						self.activate(i)
						self.see(i)
						self.event_generate("<<ListboxSelect>>")
						return "break"
			loop += 1

		if oldActive != self.index(ACTIVE):
			self.activate(oldActive)

	# ----------------------------------------------------------------------
	# Create the popup menu
	# ----------------------------------------------------------------------
	def popupMenu(self, event):
		"""Create popup menu with default actions"""
		if self["state"] == DISABLED: return
		self.focus_set()
		menu=Menu(self, tearoff=0)
		if self.usermenu:
			for entry in self.usermenu:
				if entry is None:
					menu.add_separator()
				else:
					name,und,cmd = entry[:3]
					if len(entry)>3:
						icon = entry[3]
					else:
						icon = None
					menu.add_command(label=name, underline=und,
							image=icon, compound=LEFT,
							command=cmd)
			if not self._single: menu.add_separator()

		if not self._single:
			self._ALLICON  = PhotoImage(data=_ALLICON)
			self._NONEICON = PhotoImage(data=_NONEICON)
			self._INVICON  = PhotoImage(data=_INVICON)
			menu.add_command(label='All', underline=0,
					image=self._ALLICON, compound=LEFT,
					command=self.selectAll)
			menu.add_command(label='Clear', underline=0,
					image=self._NONEICON, compound=LEFT,
					command=self.selectClear)
			menu.add_command(label='Invert', underline=0,
					image=self._INVICON, compound=LEFT,
					command=self.selectInvert)

		menu.tk_popup(event.x_root, event.y_root)
		return "break"

	# ----------------------------------------------------------------------
	# Selection
	# ----------------------------------------------------------------------
	def selectAll(self, event=None):
		"""Select all items"""
		self.selection_set(0, END)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def selectClear(self, event=None):
		"""Selection Clear"""
		self.selection_clear(0, END)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def selectInvert(self, event=None):
		"""Invert selection"""
		for i in range(self.size()):
			if self.select_includes(i):
				self.selection_clear(i)
			else:
				self.selection_set(i)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	# return active and selected items
	# ----------------------------------------------------------------------
	def getSelected(self):
		"""return a tuple of active and selected items
		   for restoring later"""
		return (self.index(ACTIVE), map(int, self.curselection()))

	# ----------------------------------------------------------------------
	# select active and selected items
	# ----------------------------------------------------------------------
	def selectSaved(self, save, default=None):
		"""selected the saved items.
		   If list has changed then selected the default item"""
		self.selection_clear(0,END)

		if save is not None:
			self.activate(save[0])
			for s in save[1]:
				self.selection_set(s)
			self.see(save[0])

		if default is not None:
			if save is None or \
			   (save is not None and save[0] >= self.size()):
				if isinstance(default, tuple):
					self.selection_set(default[0], default[1])
					self.activate(default[0])
				else:
					self.selection_set(default)
					self.activate(default)
		self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	def _scrollTo(self, pos, unit=None):
		if unit:
			self.yview_scroll(pos, unit)
		else:
			if self._single:
				self.selection_clear(0, END)
				self.selection_set(pos)
			self.activate(pos)
			self.see(pos)
		self.event_generate("<<ListboxSelect>>")
		return 'break'

	# ----------------------------------------------------------------------
	# Change the value of a list item
	# and return the value of the old one
	# ----------------------------------------------------------------------
	def set(self, index, value):
		"""Set/Change the value of a list item"""
		try:
			sel = self.selection_includes(index)
			act = self.index(ACTIVE)
			self.delete(index)
		except TclError:
			return
		self.insert(index, value)
		if sel: self.selection_set(index)
		self.activate(act)
		self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	# Swap two items in the list
	# ----------------------------------------------------------------------
	def swap(self, a, b):
		"""Swap two items in the list"""
		if a>b: a, b = b, a

		at = self.get(a);
		bt = self.get(b);

		self.delete(b);
		self.delete(a);

		self.insert(a, bt);
		self.insert(b, at);

	# ----------------------------------------------------------------------
	# Move up select items by one
	# ----------------------------------------------------------------------
	def moveUp(self):
		"""Move selected items up"""
		for i in map(int,self.curselection()):
			if i==0: continue
			prev = i-1
			if not self.selection_includes(prev):
				act = self.index(ACTIVE)
				self.swap(prev,i)
				self.selection_set(prev)
				if act == i: self.activate(prev)
		self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	# Move down select items by one
	# ----------------------------------------------------------------------
	def moveDown(self):
		"""Move selected items down"""
		sz  = self.size()-1
		lst = map(int,self.curselection())
		lst.reverse()
		for i in lst:
			if i >= sz: continue
			next = i+1
			if not self.selection_includes(next):
				act = self.index(ACTIVE)
				self.swap(i,next)
				self.selection_set(next)
				if act == i: self.activate(next)
		self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	def deleteByName(self, item):
		"""delete entry by name"""
		act = self.index(ACTIVE)
		for i in range(self.size()-1,-1,-1):
			it = self.get(i)
			if it == item:
				self.delete(i)
		self.activate(act)

	# ----------------------------------------------------------------------
	# Fill the listbox
	# ----------------------------------------------------------------------
	def fill(self, items=None):
		self.delete(0,END)
		for item in items: self.insert(END, item)

	# ----------------------------------------------------------------------
	# Copy current elements to clipboard
	# ----------------------------------------------------------------------
	def copy(self, event=None):
		sel = self.curselection()
		if not sel: return
		items = []
		for i in sel:
			items.append(self.get(i))
		self.clipboard_clear()
		self.clipboard_append("\n".join(items))

#===============================================================================
# Search Listbox
# A listbox that the list is narrowing down to the matching items
#===============================================================================
class SearchListbox(ExListbox):
	def __init__(self, master, **kw):
		ExListbox.__init__(self, master, **kw)
		self.prefixSearch = False
		self._items = []
		self._pos   = []

	# ----------------------------------------------------------------------
	# Fill the listbox
	# ----------------------------------------------------------------------
#	def fill(self, items=None):
#		del self._items[:]
#		if items is None:
#			for item in Listbox.get(self,0,END):
#				self._items.append(unicode(item))
#		else:
#			self.delete(0,END)
#			for item in items:
#				item = unicode(item)
#				self._items.append(item)
#				self.insert(END, item)
#		self._pos = range(len(self._items))

	# ----------------------------------------------------------------------
	def reset(self):
		if self._items and ExListbox._search:
			ExListbox.resetSearch()
			Listbox.delete(self, 0, END)
			for item in self._items:
				Listbox.insert(self, END, item)
			del self._items[:]
			del self._pos[:]

	# ----------------------------------------------------------------------
	def handleKey(self, event):
		"""handle key events for quick searching"""
		if len(event.char)==0:
			ExListbox._time = 0
			return

		backspace = False
		# Delete search
		if event.keysym in ("Delete", "Escape"):
			ExListbox.resetSearch()
			backspace = True

		# Backspace
		elif event.keysym == "BackSpace":
			ExListbox._search     = ExListbox._search[:-1]
			ExListbox._searchOrig = ExListbox._searchOrig[:-1]
			backspace = True

		# Ignore non-printable characters
		elif self.ignoreNonAlpha and \
		     not (event.char.isalnum() or \
			  self.additionalChar.find(event.char)>=0):
			return

		# Normal character
		else:
			if self.ignoreCase:
				ExListbox._search += event.char.upper()
			else:
				ExListbox._search += event.char
			ExListbox._searchOrig += event.char

		if self.showSearch: self._showSearch()

		# Remember time and active
		ExListbox._time = event.time
		active = Listbox.get(self,ACTIVE)
		activepos = 0

		search = ExListbox._search
		prefix = self.prefixSearch
		if search and search[0]=="*":
			search = search[1:]
			prefix = not prefix

		# Fill up the list of items
		if not self._items:
			for item in Listbox.get(self,0,END):
				self._items.append(unicode(item))
			self._pos = range(len(self._items))

		# if Search string is empty, fill the entire list
		if not search:
			Listbox.delete(self, 0, END)
			for i,item in enumerate(self._items):
				if active == item: activepos = i
				Listbox.insert(self, END, item)
			self._pos = range(len(self._items))

		# Backspace removes one character then we need to expand the list
		elif backspace:
			# FIXME I could find the correct position and insert it
			# instead of delete all and repopulate
			Listbox.delete(self, 0, END)
			del self._pos[:]
			for i,item in enumerate(self._items):
				if prefix:
					if self.ignoreCase:
						if item.upper().startswith(search):
							if active == item: activepos = i
							Listbox.insert(self, END, item)
							self._pos.append(i)
					else:
						if item.startswith(search):
							if active == item: activepos = i
							Listbox.insert(self, END, item)
							self._pos.append(i)
				else:
					if self.ignoreCase:
						if item.upper().find(search)>=0:
							if active == item: activepos = i
							Listbox.insert(self, END, item)
							self._pos.append(i)
					else:
						if item.find(search)>=0:
							if active == item: activepos = i
							Listbox.insert(self, END, item)
							self._pos.append(i)
		else:
			# FIXME I could use the fnmatch or re to allow * and ? as pattern

			# If a new character added then shrink the existing list
			# Scan in reverse order
			for i in range(Listbox.size(self)-1, -1, -1):
				item = Listbox.get(self, i)
				if active == item: activepos = i
				if self.ignoreCase: item = item.upper()
				if prefix:
					if not item.startswith(search):
						Listbox.delete(self, i)
						del self._pos[i]
				else:
					if item.find(search)<0:
						Listbox.delete(self, i)
						del self._pos[i]

		Listbox.selection_clear(self, 0, END)
		Listbox.selection_set(self, activepos)
		Listbox.activate(self, activepos)

	# ----------------------------------------------------------------------
	def insert(self, index, *elements):
		del self._items[:]
		return Listbox.insert(self, index, *elements)

	# ----------------------------------------------------------------------
	def delete(self, first, last=None):
		del self._items[:]
		return Listbox.delete(self, first, last)

	# ----------------------------------------------------------------------
	def curselection(self):
		if self._items:
			return [self._pos[int(x)] for x in Listbox.curselection(self)]
		else:
			return Listbox.curselection(self)

	# ----------------------------------------------------------------------
	# FIXME needs work to handle, ACTIVE, END...
	# ----------------------------------------------------------------------
	def get(self, first, last=None):
		#say("SearchListbox.get",first,type(first),last,type(last))
		if not self._items:
			return Listbox.get(self, first, last)

		elif first == ACTIVE:
			return Listbox.get(self, first, last)

		elif last is None:
			return self._items[first]

		elif last == END:
			last = len(self._items)

		else:
			last = int(last)+1

		if len(self._items)==0: return ""
		return self._items[int(first):last]

#===============================================================================
# MultiListbox based on recipe from
#	http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52266
# Author:	Brent Burley
# Date:		2001/03/14
#===============================================================================
class MultiListbox(Frame):
	"""Multilistbox class"""

	# Add default options if not supplied
	defopt = (("borderwidth",	0),
		  ("selectmode",	EXTENDED),
		  ("selectborderwidth",	0),
		  ("relief",		FLAT),
		  ("exportselection",	FALSE),
		  ("takefocus",		FALSE))

	def __init__(self, master, lists, **options):
		Frame.__init__(self, master)
		self.paneframe = PanedWindow(self, orient=HORIZONTAL,
				showhandle=0, handlepad=0, handlesize=0,
				sashwidth=2, opaqueresize=1)
		self.paneframe.pack(side=LEFT, expand=YES, fill=BOTH)
		self.paneframe.bind("<Button-1>",	 self._sashMark)
		self.paneframe.bind("<B1-Motion>",	 self._sashDrag)
		self.paneframe.bind("<ButtonRelease-1>", self._sashRelease)
		self._lists  = []
		self._labels = []
		col = 0
		if "header" in options:
			header = options["header"]
			del options["header"]
		else:
			header = 1

		if "stretch" in options:
			stretch = options["stretch"]
			del options["stretch"]
		else:
			stretch = "always"

		for n,o in MultiListbox.defopt:
			if n not in options:
				options[n] = o

		for l, w, a in lists:
			#if header:
			frame = Frame(self.paneframe, border=0)
			try: self.paneframe.add(frame, minsize=16, stretch=stretch)
			except: self.paneframe.add(frame, minsize=16)	# tk8.4
			if header:
				lbl = Label(frame, text=l, borderwidth=1,
						relief=RAISED)
				lbl.pack(fill=X)
				lbl.bind('<Button-1>', lambda e, s=self, c=col:
						s.sort(c))
				self._labels.append(lbl)
			#else:
			#	frame = self

			lb = ExListbox(frame, width=w, **options)
			#if header:
			#	lb.pack(expand=YES, fill=BOTH)
			#else:
			lb.pack(side=LEFT, expand=YES, fill=BOTH)
			self._lists.append(lb)

			lb.bind('<B2-Motion>', lambda e, s=self:
						s._b2motion(e.x, e.y))
			lb.bind('<Button-2>', lambda e, s=self:
						s._button2(e.x, e.y))
			lb.bind('<Button-4>', lambda e, s=self:
						s._scroll(SCROLL, -1, UNITS))
			lb.bind('<Button-5>', lambda e, s=self:
						s._scroll(SCROLL, 1, UNITS))
			lb.bind('<<ListboxSelect>>', lambda e, s=self, l=lb:
						s._updateSelect(l))
			col += 1

		self._lists[0]["takefocus"] = True

		if header:
			frame = Frame(self)
			frame.pack(side=RIGHT, fill=Y)
			Label(frame, borderwidth=1, relief=RAISED).pack(fill=X)

		self.scrollbar = Scrollbar(frame, orient=VERTICAL,
				takefocus=False,
				command=self._scroll)

		if header:
			self.scrollbar.pack(fill=Y, expand=YES)
		else:
			self.scrollbar.pack(side=RIGHT, fill=Y)

		self._lists[0]['yscrollcommand']=self.scrollbar.set
		self.activeList   = self._lists[0]
		self.sortAssist   = SortAssist
		self._sortOrder	  = None	# Array containing the previous order of the list after sort
		self._sortColumn  = -1
		self._sashIndex   = -1
		self._sortReverse = False
		self._sashx       = None

	# ----------------------------------------------------------------------
	# Bind left/right arrow to focusing different list
	# ----------------------------------------------------------------------
	def bindLeftRight(self):
		""" Default bindings of left/right arrow to focusing different lists"""
		self.bindList('<Left>',  self.focusLeft)
		self.bindList('<Right>', self.focusRight)

	# ----------------------------------------------------------------------
	def _updateSelect(self, lst=None):
		if lst is None: lst = self.activeList
		ypos = lst.yview()[0]
		sel = lst.curselection()
		act = lst.index(ACTIVE)
		for l in self._lists:
			if l is lst: continue
			l.selection_clear(0, END)
			for s in sel:
				l.selection_set(s)
			l.activate(act)
			l.yview_moveto(ypos)
		self.event_generate('<<ListboxSelect>>')

	# ----------------------------------------------------------------------
	# Update header labels
	# ----------------------------------------------------------------------
	def labels(self, names):
		for i,n in enumerate(names):
			if i>len(self._labels): return
			self._labels[i].config(text=n)

	# ----------------------------------------------------------------------
	def _button2(self, x, y):
		for l in self._lists:
			l.scan_mark(x, y)
		return 'break'

	# ----------------------------------------------------------------------
	def _b2motion(self, x, y):
		for l in self._lists:
			l.scan_dragto(x, y)
		return 'break'

	# ----------------------------------------------------------------------
	def _sashMark(self, event):
		self._sashIndex = -1
		try:
			self._sashIndex,which = self.paneframe.identify(event.x, event.y)
			if which == "sash":
				self._sashx = [self.paneframe.sash_coord(i)[0] \
						for i in range(len(self._lists)-1)]
				self._sashdx = self._sashx[self._sashIndex] - event.x
				self._sashDrag(event)
			else:
				self._sashIndex = -1
		except:
			return
		return 'break'

	# ----------------------------------------------------------------------
	def _sashDrag(self, event):
		if self._sashx and self._sashIndex >= 0:
			ddx = event.x - self._sashdx - self._sashx[self._sashIndex]
			self.paneframe.sash_place(self._sashIndex, event.x-self._sashdx, 1)
			for i in range(self._sashIndex+1, len(self._lists)-1):
				self.paneframe.sash_place(i, self._sashx[i]+ddx, 1)
		return 'break'

	# ----------------------------------------------------------------------
	def _sashRelease(self, event):
		if self._sashIndex >= 0:
			self._sashx = None
		return 'break'

	# ----------------------------------------------------------------------
	def _scroll(self, *args):
		for l in self._lists:
			l.yview(*args)
		return 'break'

	# ----------------------------------------------------------------------
	def curselection(self):
		return self._lists[0].curselection()

	# ----------------------------------------------------------------------
	def delete(self, first, last=None):
		for l in self._lists:
			l.delete(first, last)

	# ----------------------------------------------------------------------
	def get(self, first, last=None):
		result = []
		for l in self._lists:
			result.append(l.get(first, last))
		if last: return zip(*result)
		return result

	# ----------------------------------------------------------------------
	def listbox(self, i):
		return self._lists[i]

	# ----------------------------------------------------------------------
	def listboxes(self):
		return self._lists

	# ----------------------------------------------------------------------
	def listboxIndex(self, widget):
		return self._lists.index(widget)

	# ----------------------------------------------------------------------
	def bindList(self, event, func):
		self.bind(event, func)
		for l in self._lists:
			l.bind(event, func)

	# ----------------------------------------------------------------------
	def unbindList(self, event):
		self.unbind(event)
		for l in self._lists:
			l.bind(event)

	# ----------------------------------------------------------------------
	def index(self, item):
		return self._lists[0].index(item)

	# ----------------------------------------------------------------------
	def insert(self, index, *elements):
		for e in elements:
			for i,l in enumerate(self._lists):
				l.insert(index, e[i])
			if len(e) < len(self._lists):
				for l in self._lists[len(e) : len(self._lists)]:
					l.insert(index, "")

		if self._sortColumn>=0:
			txt = self._labels[self._sortColumn]["text"]
			self._labels[self._sortColumn].config(text=txt[:-1])
			self._sortColumn = -1

	# ----------------------------------------------------------------------
	# Change the value of a list item
	# and return the value of the old one
	# ----------------------------------------------------------------------
	def set(self, index, value):
		"""Set the value of a list item."""
		self.delete(index)
		self.insert(index, value)

	# ----------------------------------------------------------------------
	def size(self):
		return self._lists[0].size()

	# ----------------------------------------------------------------------
	def setPopupMenu(self, menu):
		"""Setup a popup menu list it should be in the form
		   [ (label, underline, command), ... ]"""
		for l in self._lists:
			l.setPopupMenu(menu)

	# ----------------------------------------------------------------------
	def nearest(self, y):
		return self._lists[0].nearest(y)

	# ----------------------------------------------------------------------
	def see(self, index):
		for l in self._lists:
			l.see(index)

	# ----------------------------------------------------------------------
	def configure(self, **kw):
		for l in self._lists:
			l.configure(**kw)
	config = configure

	# ----------------------------------------------------------------------
	def itemcget(self, index, option):
		"""Return the resource value for an ITEM and an OPTION."""
		return self._lists[0].itemcget(index, option)

	# ----------------------------------------------------------------------
	def itemconfigure(self, index, cnf=None, **kw):
		"""Configure resources of an ITEM.
		The values for resources are specified as keyword arguments.
		To get an overview about the allowed keyword arguments
		call the method without arguments.
		Valid resource names: background, bg, foreground, fg,
		selectbackground, selectforeground."""
		for l in self._lists:
			l.itemconfigure(index, cnf, **kw)
	itemconfig = itemconfigure

	# ----------------------------------------------------------------------
	# Override of the standard Tkinter cget() routine
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		return self._lists[0].cget(key)

	# ----------------------------------------------------------------------
	# Override of the standard Tkinter config() routine
	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		for l in self._lists:
			l[key] = value

	# ----------------------------------------------------------------------
	# Selection
	# ----------------------------------------------------------------------
	def selection_anchor(self, index):
		for l in self._lists:
			l.selection_anchor(index)

	# ----------------------------------------------------------------------
	def selection_includes(self, index):
		return self._lists[0].selection_includes(index)

	# ----------------------------------------------------------------------
	def selection_clear(self, first, last=None):
		for l in self._lists:
			l.selection_clear(first, last)

	# ----------------------------------------------------------------------
	def selection_set(self, first, last=None):
		for l in self._lists:
			l.selection_set(first, last)

	# ----------------------------------------------------------------------
	def selectAll(self, event=None):
		"""Select all items"""
		self.selection_set(0, END)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def selectClear(self, event=None):
		"""Unselect all items"""
		self.selection_clear(0, END)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def selectInvert(self, event=None):
		"""Invert selection"""
		l = self._lists[0]
		for i in range(l.size()):
			if l.select_includes(i):
				self.selection_clear(i)
			else:
				self.selection_set(i)
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def activate(self, index):
		for l in self._lists:
			l.activate(index)

	# ----------------------------------------------------------------------
	def focus_set(self):
		self._lists[0].focus_set()

	# ----------------------------------------------------------------------
	def focusLeft(self, event=None):
		listbox = self.focus_get()
		if listbox is None: return
		active = listbox.index(ACTIVE)
		try:
			lid = self._lists.index(listbox) - 1
			if lid>=0:
				self._lists[lid].activate(active)
				self._lists[lid].focus_set()
		except:
			pass

	# ----------------------------------------------------------------------
	def focusRight(self, event=None):
		listbox = self.focus_get()
		if listbox is None: return
		active = listbox.index(ACTIVE)
		try:
			lid = self._lists.index(listbox) + 1
			if lid < len(self._lists):
				self._lists[lid].activate(active)
				self._lists[lid].focus_set()
		except:
			pass

	# ----------------------------------------------------------------------
	def sort(self, column, reverse=None):
		""" Sort by a given column."""
		if self._lists[0].cget("state") == DISABLED: return
		if self.sortAssist is None: return
		if column == self._sortColumn:
			txt = self._labels[self._sortColumn]["text"][:-1]
			if reverse is None:
				reverse = not self._sortReverse
		else:
			if self._sortColumn>=0:
				txt = self._labels[self._sortColumn]["text"][:-1]
				self._labels[self._sortColumn].config(text=txt)
				self._sortColumn = -1
			txt = self._labels[column]["text"]
			if reverse is None:
				reverse = False

		#elements = self.get(0, END)
		elements = []
		lst = self._lists[0]
		for i in range(self.size()):
			item = []
			for l in self._lists:
				item.append(l.get(i))
			item.append(lst.selection_includes(i))	# Include selection
			item.append(i)				# Include position
			elements.append(item)

		try: active = int(self.index(ACTIVE))
		except: active = -1

		self.delete(0, END)

		elements.sort(key=self.sortAssist(column), reverse=reverse)

		# get selection status
		status = []
		self._sortOrder	= []
		newactive = -1
		for i,item in enumerate(elements):
			idx = item.pop()
			if active == idx: newactive = i
			self._sortOrder.append(idx)
			status.append(item.pop())

		self.insert(END, *elements)

		for i,s in enumerate(status):
			if s:
				self.selection_set(i)
				if newactive<0: newactive = i
		if newactive>=0:
			self.activate(newactive)

		self._sortColumn  = column
		self._sortReverse = reverse

		if reverse:
			self._labels[column].config(text=txt+Unicode.BLACK_DOWN_POINTING_TRIANGLE)
		else:
			self._labels[column].config(text=txt+Unicode.BLACK_UP_POINTING_TRIANGLE)
		self.event_generate("<<ListboxSort>>")

	# ----------------------------------------------------------------------
	def saveSort(self):
		return self._sortColumn, self._sortReverse

	# ----------------------------------------------------------------------
	def restoreSort(self, arg):
		if arg[0] >= 0:
			self.sort(*arg)

	# ----------------------------------------------------------------------
	def yview(self):
		return self._lists[0].yview()

	# ----------------------------------------------------------------------
	def yview_moveto(self, fraction):
		for l in self._lists:
			l.yview_moveto(fraction)

	# ----------------------------------------------------------------------
	def moveUp(self):
		for l in self._lists:
			l.moveUp()

	# ----------------------------------------------------------------------
	def moveDown(self):
		for l in self._lists:
			l.moveDown()

#===============================================================================
# A MultiListbox that remembers the color of items
#===============================================================================
class ColorMultiListbox(MultiListbox):
	# ----------------------------------------------------------------------
	def sort(self, column, dir=None):
		# remember colors
		colors = {}
		for i in range(self.size()):
			colors[self._lists[0].get(i)] = \
				self._lists[0].itemcget(i, "foreground")

		MultiListbox.sort(self, column, dir)

		# set colors
		for i in range(self.size()):
			self.setColor(i, colors[self._lists[0].get(i)])

		del colors

	# ----------------------------------------------------------------------
	def setColor(self, idx, color):
		for l in self._lists:
			l.itemconfigure(idx, foreground=color)

#===============================================================================
# Image list
#===============================================================================
class ImageListbox(Text):
	"""ImageListbox widget which can display a list of strings and images"""
	def __init__(self, master, **options):
		Text.__init__(self, master, **options)
		self.config(cursor="arrow",
			tabs="20p",
			#insertofftime=0,
			#insertontime=0,
			wrap=NONE,
			insertwidth=0,
			takefocus=TRUE,
			exportselection=0)
#			state=DISABLED)
		self.bind("<Button-1>",		self._button1)
		self.bind("<Control-Button-1>",	self._controlButton1)
		self.bind("<Shift-Button-1>",	self._motion1)
		self.bind("<B1-Motion>",	self._motion1)
		self.bind("<Control-B1-Motion>",self._controlMotion1)
		self.bind("<Key>",              self._key)
		self.bind("<Delete>",           self._break)
		self.bind("<Return>",           self._break)
		self.bind("<KeyRelease>",	self._break)

		self.bind("<<Cut>>",            self.cut)
		self.bind("<<Copy>>",           self.copy)
		self.bind("<<Paste>>",          self.paste)

		self._selection = []
		self._anchor = 0
		self._active = 0

	# ----------------------------------------------------------------------
	def insert(self, index, icon, text):
		"""Insert ELEMENTS at INDEX."""
#		self.config(state=NORMAL)
		if index != END:
			index = int(index)
			sindex = "%d.0"%(index+1)
			Text.insert(self, sindex, "\t%s\n"%(text))
			self.image_create(sindex, image=icon)
			self._selection.insert(index,False)
		else:
			self.image_create(END, image=icon)
			Text.insert(self, END, "\t%s\n"%(text))
			self._selection.append(False)
#		self.config(state=DISABLED)

	# ----------------------------------------------------------------------
	def delete(self, first, last=None):
		"""Delete items from FIRST to LAST (not included)."""
		if first == END:
			Text.delete(self, "end.0", END)
			self._selection.pop()
			return "break"
		if first == ACTIVE:
			first = self.index(ACTIVE)
		if last is None:
			i = int(first)
			if 0 <= i < len(self._selection):
				Text.delete(self, "%d.0"%(i+1), "%d.0 + 1 lines"%(i+1))
				del self._selection[i]
			return "break"

		if last == END:
			last = self.size()

		first = int(first)
		lines = int(last) - first
		Text.delete(self, "%d.0"%(first+1), "%d.0 + %d lines"%(first+1, lines))
		try:
			del self._selection[first:last]
		except IndexError:
			pass
		return "break"

	# ----------------------------------------------------------------------
	def size(self):
		"""Return the number of elements in the listbox."""
		return len(self._selection)

	# ----------------------------------------------------------------------
	def curselection(self):
		"""Return list of indices of currently selected item."""
		sel = []
		for i,x in enumerate(self._selection):
			if x: sel.append(i)
		return sel

	# ----------------------------------------------------------------------
	def nearest(self, y):
		"""Get index of item which is nearest to y coordinate Y."""
		index = Text.index(self,"@1,%d"%(y))
		i = int(index.split(".")[0])-1
		if i>= self.size(): i -= 1
		return i

	# ----------------------------------------------------------------------
	def _button1(self, event):
		self.focus()
		self.selection_anchor(self.nearest(event.y))
		self._active = self._anchor
		self._select()
		return "break"

	# ----------------------------------------------------------------------
	def _motion1(self, event):
		y = self.nearest(event.y)
		if self._active != y:
			self._active = y
			self._selectRange()
		return "break"

	# ----------------------------------------------------------------------
	def _controlButton1(self, event):
		self.selection_anchor(self.nearest(event.y))
		self._active = self._anchor
		self._selection[self._anchor] = not self._selection[self._anchor]
		self._tagSelection()
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def _controlMotion1(self, event):
		self._active = self.nearest(event.y)
		last = self._selection[self._anchor]
		if self._active < self._anchor:
			for i in range(self._active, self._anchor):
				self._selection[i] = last
		elif self._active > self._anchor:
			for i in range(self._anchor, self._active+1):
				self._selection[i] = last
		self._tagSelection()
		return "break"

	# ----------------------------------------------------------------------
	def _key(self, event):
		if event.keysym == "Up":
			if self._active == 0: return "break"
			self._active -= 1
			if event.state & SHIFT_MASK:
				self._selectRange()
			else:
				self._anchor = self._active
				self._select()

		elif event.keysym == "Down":
			self._active += 1
			if self._active >= self.size():
				self._active = self.size()-1
				return "break"
			if event.state & SHIFT_MASK:
				self._selectRange()
			else:
				self._anchor = self._active
				self._select()

		elif event.keysym in ("Prior", "Next", "Delete"):
			return

		if event.state & CONTROL_MASK != 0:
			# Let system handle all Control keys
			pass

		else:
			# Ignore all normal keys
			return "break"

	# ----------------------------------------------------------------------
	def _break(self, event):
		return "break"

	# ----------------------------------------------------------------------
	def _select(self):
		self._selection = [False] * len(self._selection)
		self.selection_set(self._active)
		idx = "%d.0"%(self._active+1)
		Text.see(self, idx)
		Text.index(self, idx)
		self.event_generate("<<ListboxSelect>>")

	# ----------------------------------------------------------------------
	def _selectRange(self):
		self._selection = [False] * len(self._selection)
		if self._active < self._anchor:
			for i in range(self._active, self._anchor):
				self._selection[i] = True
		elif self._active > self._anchor:
			for i in range(self._anchor, self._active+1):
				self._selection[i] = True
		try:
			self._selection[self._anchor] = True
		except IndexError:
			pass
		self._tagSelection()
		self.event_generate("<<ListboxSelect>>")
		return "break"

	# ----------------------------------------------------------------------
	def selection_anchor(self, index):
		"""Set the fixed end oft the selection to INDEX."""
		self._anchor = index

	select_anchor = selection_anchor

	# ----------------------------------------------------------------------
	def selection_clear(self, first, last=None):
		"""Clear the selection from FIRST to LAST (not included)."""
		self._selection = [False] * len(self._selection)
		self._tagSelection()

	select_clear = selection_clear

	# ----------------------------------------------------------------------
	def selection_includes(self, index):
		"""Return 1 if INDEX is part of the selection."""
		return self._selection[index]

	select_includes = selection_includes

	# ----------------------------------------------------------------------
	def selection_set(self, first, last=None):
		"""Set the selection from FIRST to LAST (not included) without
		changing the currently selected elements."""
		if first == END:
			self._selection[-1] = True
			self._tagSelection()
			return
		if last is None:
			i = int(first)
			if 0 <= i < len(self._selection):
				self._selection[int(first)] = True
				self._tagSelection()
			return

		if last == END:
			last = self.size()

		for i in range(int(first), last):
			self._selection[i] = True
		self._tagSelection()

	select_set = selection_set

	# ----------------------------------------------------------------------
	def see(self, index):
		"""Scroll such that INDEX is visible."""
		if index == END:
			Text.see(self, index)
		else:
			Text.see(self, "%d.0"%(int(index)+1))

	# ----------------------------------------------------------------------
	def _tagSelection(self):
		self.tag_delete("lola")
		for i,x in enumerate(self._selection):
			if x:
				self.tag_add("lola", "%d.0"%(i+1), "%d.0 +1 lines"%(i+1))
		self.tag_configure("lola", foreground="White", background="SteelBlue2")
		Text.selection_clear(self)

	# ----------------------------------------------------------------------
	#def bbox(self, *args):
	def bbox(self, index):
		"""Return a tuple of X1,Y1,X2,Y2 coordinates for a rectangle
		which encloses the item identified by index in ARGS."""
		if index == END:
			return Text.dlineinfo(self,index)[:4]
		if index == ACTIVE:
			index = self.index(index)
		return Text.bbox(self,"%d.2"%(int(index)+1))

	# ----------------------------------------------------------------------
	def dlineinfo(self,index):
		if index == END:
			return Text.dlineinfo(self,index)
		if index == ACTIVE:
			index = self.index(index)
		return Text.dlineinfo(self,"%d.0"%(int(index)+1))

	# ----------------------------------------------------------------------
	def activate(self, index):
		"""Activate item identified by INDEX."""
		if index == END:
			self._active = self.size()-1
		else:
			self._active = int(index)

	# ----------------------------------------------------------------------
	def get(self, first, last=None):
		"""Get list of items from FIRST to LAST (not included)."""
		if first == END:
			first = self.size()-1
		elif first == ACTIVE:
			first = self._active
		else:
			first = int(first)

		if last is None:
			if 0 <= first < len(self._selection):
				first += 1
				img = Text.image_cget(self, "%d.0"%(first), "image")
				txt = Text.get(self, "%d.2"%(first), "%d.end"%(first))
				return txt
			return None

		if last == END:
			last = self.size()
		elif last == ACTIVE:
			last = self._active
		else:
			last = int(last)

		# FIXME....
		# return list of text items

	# ----------------------------------------------------------------------
	# get both image and text
	# ----------------------------------------------------------------------
	def elicit(self, first, last=None):
		"""Get list of items from FIRST to LAST (not included)."""
		if first == END:
			first = self.size()-1
		elif first == ACTIVE:
			first = self._active
		else:
			first = int(first)

		if last is None:
			if 0 <= first < len(self._selection):
				first += 1
				img = Text.image_cget(self, "%d.0"%(first), "image")
				txt = Text.get(self, "%d.2"%(first), "%d.end"%(first))
				return img,txt
			return None,None

		if last == END:
			last = self.size()
		elif last == ACTIVE:
			last = self._active
		else:
			last = int(last)

		# FIXME....
		# return list of (image,text) items

	# ----------------------------------------------------------------------
	def index(self, index):
		"""Return index of item identified with INDEX."""
		if index == ACTIVE:
			return self._active
		else:
			return Text.index(self,index)

	# ----------------------------------------------------------------------
	def scan_mark(self, x, y):
		"""Remember the current X, Y coordinates."""
		pass

	# ----------------------------------------------------------------------
	def scan_dragto(self, x, y):
		"""Adjust the view of the listbox to 10 times the
		difference between X and Y and the coordinates given in
		scan_mark."""
		pass

	# ----------------------------------------------------------------------
	def itemcget(self, index, option):
		"""Return the resource value for an ITEM and an OPTION."""
		pass

	# ----------------------------------------------------------------------
	def itemconfigure(self, index, cnf=None, **kw):
		"""Configure resources of an ITEM.

		The values for resources are specified as keyword arguments.
		To get an overview about the allowed keyword arguments
		call the method without arguments.
		Valid resource names: background, bg, foreground, fg,
		selectbackground, selectforeground."""
		pass

	itemconfig = itemconfigure

	# ----------------------------------------------------------------------
	# Override cut,copy,paste to do nothing
	# ----------------------------------------------------------------------
	def cut(self, event=None):
		return "break"
	copy  = cut
	paste = cut

#===============================================================================
# Class to edit in place the contents of a listbox
#===============================================================================
class InPlaceEdit:
	def __init__(self, listbox, item=ACTIVE, value=None, x=None, select=True, **kw):
		# Return value
		self.value   = None	# Result
		self.frame   = None
		self.lastkey = None	# Last key that exited the editbox
		self.kw      = kw
		self._x      = x
		self._select = select

		# Find active
		try: self.active = listbox.index(item)
		except: return

		self.item    = item
		self.listbox = listbox

		# Create and set value
		self.frame = Frame(listbox, relief=None)
		self.createWidget()
		self.old = self.set(value)
		self.defaultBinds()

		# Bindings
		self.frame.bind("<FocusOut>",        self.focusOut)
		# Unmap creates core dump when Fn key is pressed
		self.frame.bind("<ButtonRelease-1>", self.clickOk)
		self.frame.bind("<ButtonRelease-3>", self.clickCancel)
		self.listbox.bind("<Configure>",     self.resize)
		#self.frame.bind("<Unmap>",          self._destroy)

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
		#self.listbox.focus_set()

	# ----------------------------------------------------------------------
	# Override method if another widget is requested
	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = Entry(self.frame, **self.kw)
		self.edit.pack(expand=YES, fill=BOTH)
		self.edit.focus_set()

	# ----------------------------------------------------------------------
	# set insert cursor at location
	# ----------------------------------------------------------------------
	def icursor(self):
		if self._x is not None:
			self.edit.icursor("@%d"%(self._x))

	# ----------------------------------------------------------------------
	# Set default bindings
	# ----------------------------------------------------------------------
	def defaultBinds(self):
		try:
			self.edit.bind("<Return>",   self.ok)
			self.edit.bind("<KP_Enter>", self.ok)
			self.edit.bind("<Up>",       self.ok)
			self.edit.bind("<Down>",     self.ok)
			self.edit.bind("<Escape>",   self.cancel)
		except AttributeError:
			pass

	# ----------------------------------------------------------------------
	def resize(self, event=None):
		if self.frame is None: return
		bbox = self.listbox.bbox(self.item)
		if bbox is None: return
		x, y, w, h = bbox
		w = self.listbox.winfo_width() - x
		h += 3
		try:
			self.frame.place(in_=self.listbox,
					x=x-1, y=y-1,
					width=w, height=h,
					bordermode=OUTSIDE)
			self.frame.update_idletasks()
		except TclError:
			pass

	# ----------------------------------------------------------------------
	# Override method to set the value
	# ----------------------------------------------------------------------
	def set(self, value):
		if self.frame is None: return
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
		if self.frame is None: return None
		return self.edit.get()

	# ----------------------------------------------------------------------
	def reset_grab(self):
		if self.frame is None: return
		self.frame.grab_release()
		if self._grab_window is not None:
			try:
				self._grab_window.grab_set()
			except TclError:
				pass

	# ----------------------------------------------------------------------
	def clickOk(self, event):
		# If clicked outside return ok
		if event.x < 0 or \
		   event.y < 0 or \
		   event.x > self.frame.winfo_width() or \
		   event.y > self.frame.winfo_height():
			self.ok(event)

	# ----------------------------------------------------------------------
	def clickCancel(self, event):
		# If clicked outside return cancel
		if event.x < 0 or \
		   event.y < 0 or \
		   event.x > self.frame.winfo_width() or \
		   event.y > self.frame.winfo_height():
			self.cancel(event)

	# ----------------------------------------------------------------------
	def focusOut(self, event=None):
		self.ok()

	# ----------------------------------------------------------------------
	def updateValue(self):
		if isinstance(self.listbox, Listbox):
			self.listbox.delete(self.active)
			self.listbox.insert(self.active, self.value)

	# ----------------------------------------------------------------------
	def ok(self, event=None):
		if event: self.lastkey = event.keysym
		self.value = self.get()
		self.frame.unbind('<FocusOut>')

		act = self.listbox.index(ACTIVE)
		sel = self.listbox.selection_includes(self.active)
		self.updateValue()
		self.listbox.see(self.active)

		if sel:
			self.listbox.selection_set(self.active)
		self.listbox.activate(act)
		if self.value == self.old: self.value = None

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

#===============================================================================
class InPlaceSpinbox(InPlaceEdit):
	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = Spinbox(self.frame, **self.kw)
		self.edit.pack(expand=YES, fill=BOTH)
		self.edit.focus_set()

	# ----------------------------------------------------------------------
	def set(self, value):
		if self.frame is None: return
		if value is None:
			value = self.listbox.get(self.item)
		self.edit.delete(0, END)
		self.edit.insert(0, value)
		return value

#===============================================================================
class InPlaceInteger(InPlaceEdit):
	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = IntegerEntry(self.frame, **self.kw)
		self.edit.pack(expand=YES, fill=BOTH)
		self.edit.focus_set()

#===============================================================================
class InPlaceFloat(InPlaceEdit):
	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = FloatEntry(self.frame, **self.kw)
		self.edit.pack(expand=YES, fill=BOTH)
		self.edit.focus_set()

#===============================================================================
class InPlaceList(InPlaceEdit):
	def __init__(self, listbox, item=ACTIVE, value=None, height=None, values=[], **kw):
		self.values = values
		self.height = height
		InPlaceEdit.__init__(self, listbox, item, value, **kw)

	# ----------------------------------------------------------------------
	def createWidget(self):
		self.frame.config(relief=RAISED)
		sb = Scrollbar(self.frame)
		sb.pack(side=RIGHT, fill=Y)
		if self.height is None:
			if len(self.values)<10:
				self.height = max(len(self.values)+1,3)
			else:
				self.height = 10
		self.edit = ExListbox(self.frame,
				selectmode=BROWSE,
				height=self.height,
				#background="White",
				yscrollcommand=sb.set)
		sb.config(command=self.edit.yview)
		self.edit.pack(side=LEFT, fill=BOTH, expand=YES)
		self.edit.bind('<ButtonRelease-1>', self.ok)
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
		if len(cur)>0:
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
		if self.frame is None: return
		bbox = self.listbox.bbox(self.item)
		if bbox is None: return
		x, y, item_width, item_height = bbox
		list_width  = self.listbox.winfo_width()
		list_height = self.listbox.winfo_height()
		h = item_height*self.height + 2

		if y+h > list_height:
			y = list_height - h
			if y <= 0:
				y = 0
				h = list_height

		try:
			self.frame.place(in_=self.listbox,
					x=x-1, y=y,
					width=list_width, height=h,
					bordermode=OUTSIDE)
			self.frame.update_idletasks()
		except TclError:
			pass

#===============================================================================
class InPlaceColor(InPlaceEdit):
	# ----------------------------------------------------------------------
	def createWidget(self):
		b = Button(self.frame, text="x",
			padx=0, pady=0, command=self.clearColor)
		b.pack(side=LEFT)
		self.edit = Button(self.frame, command=self.selectColor)
		self.edit.pack(side=RIGHT, expand=YES, fill=BOTH)
		self.edit.focus_set()

	# ----------------------------------------------------------------------
	def set(self, value):
		if value is None:
			value = self.listbox.get(self.item)
		self.value = value
		if self.value is None or self.value=="": self.value = "White"
		if value != "":
			self.edit.config(text=value,
					background=value,
					activebackground=value)
		return value

	# ----------------------------------------------------------------------
	def get(self):
		return self.edit["text"]

	# ----------------------------------------------------------------------
	def selectColor(self):
		self.frame.unbind("<FocusOut>")
		try:
			rgb, colorStr = askcolor(
				title="Color",
				initialcolor=self.value,
				parent=self.listbox.master)
		except TclError:
			colorStr = None
		if colorStr is not None:
			colorStr = str(colorStr)
			self.value = colorStr
			self.edit.config(text=colorStr,
					background=colorStr,
					activebackground=colorStr)
		self.frame.bind("<FocusOut>", self.cancel)
		self.edit.focus_set()

	# ----------------------------------------------------------------------
	def clearColor(self):
		self.frame.unbind("<FocusOut>")
		self.value = None
		self.edit.config(text="",
				background="White",
				activebackground="White")
		self.frame.bind("<FocusOut>", self.cancel)
		self.edit.focus_set()

#===============================================================================
class InPlaceMaxLength(InPlaceEdit):
	def __init__(self, listbox, item=ACTIVE, value=None, maxlength=None, **kw):
		self.maxlength = maxlength
		InPlaceEdit.__init__(self, listbox, item, value, **kw)

	# ----------------------------------------------------------------------
	# Override method if another widget is requested
	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = MaxLengthEntry(self.frame,
					maxlength=self.maxlength,
					**self.kw)
		self.edit.pack(expand=YES, fill=BOTH)
		self.edit.focus_set()

#===============================================================================
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
		#self.edit.bind("<ButtonRelease-1>", self.clickOk)
		#self.edit.bind("<ButtonRelease-3>", self.clickCancel)
		self.edit.bind("<Shift-Return>", self.shiftReturn)
		self.edit.bind("<Escape>", self.cancel)

	# ----------------------------------------------------------------------
	def createWidget(self):
		self.toplevel = Toplevel(self.listbox)
		self.toplevel.transient(self.listbox)
		if sys.platform in ("win32", "win64"):
			self.toplevel.update_idletasks()
		self.toplevel.overrideredirect(1)
		self.edit = Text(self.toplevel, width=70, height=10,
					background="White", undo=True)
		self.edit.pack(side=LEFT, expand=YES, fill=BOTH)
		self.edit.focus_set()

	# ----------------------------------------------------------------------
	def resize(self, event=None):
		if self.frame is None: return
		bbox = self.listbox.bbox(self.item)
		if bbox is None: return
		x, y, w, h = bbox
		x += self.listbox.winfo_rootx()
		y += self.listbox.winfo_rooty()
		w  = self.listbox.winfo_width()
		try:
			self.toplevel.wm_geometry("+%d+%d" % (x,y))
		except TclError:
			pass

	# ----------------------------------------------------------------------
	def set(self, value):
		if self.frame is None: return
		if value is None:
			value = self.listbox.get(self.item)
		self.edit.delete("0.0", END)
		self.edit.insert("0.0", value)
		self.edit.tag_add(SEL, "0.0", END)
		return value

	# ----------------------------------------------------------------------
	def get(self):
		if self.frame is None: return None
		return self.edit.get("0.0", END).strip()

	# ----------------------------------------------------------------------
	def shiftReturn(self, event):
		# Empty binding to avoid the Shift-Return to trigger the "ok"
		pass

	# ----------------------------------------------------------------------
	def clickOk(self, event):
		# If clicked outside return ok
		if event.x < 0 or \
		   event.y < 0 or \
		   event.x > self.toplevel.winfo_width() or \
		   event.y > self.toplevel.winfo_height():
			self.ok(event)

	# ----------------------------------------------------------------------
	def clickCancel(self, event):
		# If clicked outside return cancel
		if event.x < 0 or \
		   event.y < 0 or \
		   event.x > self.toplevel.winfo_width() or \
		   event.y > self.toplevel.winfo_height():
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

#===============================================================================
class InPlaceFile(InPlaceEdit):
	# ----------------------------------------------------------------------
	def __init__(self, listbox, item=ACTIVE, value=None,
			title=None, filetypes=None,
			save=True, **kw):
		self.title = title
		self.filetypes = filetypes
		self._save = save
		self._icon = PhotoImage(data=_SAVEICON)
		InPlaceEdit.__init__(self, listbox, item, value, **kw)

	# ----------------------------------------------------------------------
	def createWidget(self):
		self.edit = Entry(self.frame, width=5, **self.kw)
		self.edit.pack(side=LEFT, expand=YES, fill=BOTH)
		b = Button(self.frame, image=self._icon,
			padx=0, pady=0, command=self.fileDialog)
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
			fn = bFileDialog.asksaveasfilename(master=self.listbox,
				title=self.title,
				initialfile=filename,
				filetypes=self.filetypes)
		else:
			fn = bFileDialog.askopenfilename(master=self.listbox,
				title=self.title,
				initialfile=filename,
				filetypes=self.filetypes)
		self.frame.grab_set()
		#self.frame.bind("<FocusOut>", self.cancel)
		self._icon = None
		if len(fn) > 0:
			self.edit.delete(0, END)
			self.edit.insert(0, fn)
			self.ok()
		else:
			self.cancel()

#=============================================================================
# PopupList
# Show a popup list on a top level and return selected item
#=============================================================================
class PopupList(Toplevel):
	def __init__(self, master, items=None, selected=None, **kw):
		Toplevel.__init__(self, master, **kw)
		self.selected = selected
		self.overrideredirect(1)
		self.transient(master)

		# Create the listbox inside the dropdown window
		sb = Scrollbar(self)
		sb.pack(side=RIGHT, fill=Y)
		self._listbox = SearchListbox(self,
					selectmode=BROWSE,
					yscrollcommand=sb.set)
		self._listbox.pack(side=LEFT, expand=YES, fill=BOTH)
		sb.config(command=self._listbox.yview)

		if items:
			for item in items:
				self._listbox.insert(END, item)
				if selected == item:
					self._listbox.selection_set(END)
					self._listbox.activate(END)
					self.see(ACTIVE)

		self._listbox.bind('<Escape>',		self.close)
		self._listbox.bind('<Return>',		self._select)
		self._listbox.bind('<KP_Enter>',	self._select)
		self._listbox.bind('<Tab>',		self._select)
		self._listbox.bind('<Shift-Tab>',	self._select)
		self._listbox.bind('<ButtonRelease-1>',	self._release)
		self.bind('<FocusOut>',			self.close)

	# ----------------------------------------------------------------------
	def show(self, x, y):
		self.deiconify()
		if x is not None and y is not None:
			self.geometry('+%d+%d' % (x,y))
		self._listbox.focus_set()
		#self.wait_visibility()
		#self.grab_set()
		self.wait_window()
		return self.selected

	# ----------------------------------------------------------------------
	def close(self, event=None):
		self.grab_release()
		self.destroy()

	# ----------------------------------------------------------------------
	def _select(self, event=None):
		self.selected = self._listbox.get(ACTIVE)
		self.close()

	# ----------------------------------------------------------------------
	def _release(self, event):
		act = self._listbox.nearest(event.y)
		self._listbox.activate(act)
		self._select()

#=============================================================================
# Combobox
#=============================================================================
class Combobox(Frame):
	def __init__(self, master, label=True, *args, **kwargs):
		Frame.__init__(self, master, class_="Combobox")
		Frame.config(self, padx=0, pady=0)

		if "command" in kwargs:
			self.command = kwargs.get("command")
			del kwargs["command"]
		else:
			self.command = None

		# Create entry and button
		if label:
			self._text = Label(self, relief=GROOVE, anchor=W, *args, **kwargs)
		else:
			self._text = Entry(self, *args, **kwargs)
		self._text.pack(side=LEFT, expand=YES, fill=BOTH)

		# Arrow button
		self._post = IntVar()
		self._post.trace("w", self._showList)
		self._arrowBtn = Checkbutton(self,
			text=u"\u25BC",
			variable=self._post,
			indicatoron=False,
			padx=2, pady=0)
		self._arrowBtn.pack(side=RIGHT, fill=Y)

		# Bindings
		self._text.bind('<Up>',       self.postList)
		self._text.bind('<Down>',     self.postList)
		self._text.bind('<Return>',   self.postList)
		self._text.bind('<KP_Enter>', self.postList)
		self.bind('<Up>',       self.postList)
		self.bind('<Down>',     self.postList)
		self.bind('<Return>',   self.postList)
		self.bind('<KP_Enter>', self.postList)
		if label:
			self._text.bind('<Key-space>',       self.postList)
			self._text.bind('<Button-1>',        self._togglePost)
		else:
			self._text.bind('<Button-1>',        self.button1)
			self._text.bind('<ButtonRelease-1>', self.release1)

		# Need to unpost the popup if the entryfield is unmapped (eg:
		# its toplevel window is withdrawn) while the popup list is
		# displayed.
		self._text.bind('<Unmap>', self.unpostList)

		# Create a static popup window with dropdown list
		self._popup = Toplevel(master)
		self._popup.overrideredirect(1)
		self._popup.transient(master)
		self._popup.withdraw()

		# Create the listbox inside the dropdown window
		sb = Scrollbar(self._popup)
		sb.pack(side=RIGHT, fill=Y)
		for k in ("anchor","justify"):
			try: del kwargs[k]
			except KeyError: pass
		self._listbox = SearchListbox(self._popup,
					selectmode=BROWSE,
					yscrollcommand=sb.set,
					*args,
					**kwargs)
		self._listbox.pack(side=LEFT, expand=YES, fill=BOTH)
		sb.config(command=self._listbox.yview)

		# Bind events to the dropdown window.
		self._listbox.bind('<Escape>',		self.unpostList)
		self._listbox.bind('<Return>',		self._selectUnpost)
		self._listbox.bind('<KP_Enter>',	self._selectUnpost)
		self._listbox.bind('<Tab>',		self._selectUnpost)
		self._listbox.bind('<Shift-Tab>',	self._selectUnpost)
		self._listbox.bind('<ButtonRelease-1>', self._release)
		self._popup.bind('<FocusOut>',		self._focusOut)
		self._popup.bind('<Button-1>',		self.popupClick)
		self._popup.bind('<Button-3>',		self.popupClick)
		#self._popup.bind('<Shift-Tab>',	self._selectUnpostPrev)
		#self._popup.bind('<Tab>',	self._selectUnpostNext)
		#if sys.platform in ("linux","linux2"):
		#	self._popup.bind('<ISO_Left_Tab>', self._selectUnpostPrev)

		# grab_set redirects all mouse events to the list even
		# when the list is posted with a mouse click
		#self._hide_on_next_release = False
		self._grab_window = None

	# ----------------------------------------------------------------------
	# Unhide and post the list
	# ----------------------------------------------------------------------
	def _showList(self, a=False, b=False, c=False):
		if self._post.get():
			Balloon.hide()
			self._grab_window = None
			try:
				self._grab_window = self.grab_current()
				if self._grab_window is not None:
					self._grab_window.grab_release()
			except KeyError:
				pass
			if self._text.cget("state") == DISABLED:
				self._post.set(False)
				return

			ExListbox.resetSearch()
			self.beforeShow()

			h = self._popup.winfo_height()
			if h == 1:
				self._popup.deiconify()
				self._popup.lift()
				self._popup.update_idletasks()
				h = self._popup.winfo_height()
			w = self._text.winfo_width() + self._arrowBtn.winfo_width()

			x = self._text.winfo_rootx()
			y = self._text.winfo_rooty() + self._text.winfo_height()
			sh = self.winfo_screenheight()
			if y + h > sh and y > sh / 2:
				y = self._text.winfo_rooty() - h

			self._popup.deiconify()
			self._popup.geometry('%dx%d+%d+%d' % (w,h,x,y))
			self._popup.lift()
			self._popup.grab_set()
			self._popup.update_idletasks()

			# Grab the popup, so that all events are delivered to it, and
			# set focus to the listbox, to make keyboard navigation
			# easier.
			#self._popup.grab_set()
			#self._popup.focus_set()
			self._listbox.focus_set()
			self._showSelection()

		elif self._popup.winfo_ismapped():
			self._popup.grab_release()
			if self._grab_window:
				self._grab_window.grab_set()
				self._grab_window = None
			self._popup.withdraw()
			self._arrowBtn.focus_set()
			self.afterHide()

	# ----------------------------------------------------------------------
	def _showSelection(self):
		lb = self._listbox
		lb.selection_clear(0,END)
		item = self.get()
		# Test active
		if lb.get(ACTIVE) != item:
			# Scan list
			for i in range(lb.size()):
				if item == lb.get(i):
					lb.activate(i)
		lb.selection_set(ACTIVE)
		lb.see(ACTIVE)

	# ----------------------------------------------------------------------
	# Post list on click
	# ----------------------------------------------------------------------
	def button1(self, event):
		if self.focus_get() is not self._text:
			self.postList()
			return "break"

	# ----------------------------------------------------------------------
	# Edit on release
	# ----------------------------------------------------------------------
	def release1(self, event):
		if self.focus_get() is not self._text:
			self._text.focus_set()
			self._text.icursor("@%d"%(event.x))

	# ----------------------------------------------------------------------
	def postList(self, event=None):
		if self._arrowBtn.cget("state") != DISABLED:
			self._post.set(True)
		return "break"

	# ----------------------------------------------------------------------
	def unpostList(self, event=None):
		self._listbox.reset()
		if self._arrowBtn.cget("state") != DISABLED:
			self._post.set(False)
		return "break"

	# ----------------------------------------------------------------------
	def _togglePost(self, event):
		if self._text.cget("state") != DISABLED:
			self._post.set( not self._post.get() )
		return "break"

	# ----------------------------------------------------------------------
	def _focusOut(self, event):
		try:
			f = self._popup.focus_get()
		except KeyError:
			pass
		else:
			if f == self._popup or f == self._listbox:
				return
		self._focus = None
		self.unpostList()

	# ----------------------------------------------------------------------
	def _selectUnpost(self, event=None):
		if self._post.get():
			sel = self._listbox.get(ACTIVE)
			self.set(sel)
			self.unpostList()

	# ----------------------------------------------------------------------
	def invoke(self):
		if self.command is not None:
			self.command()

	# ----------------------------------------------------------------------
	def _release(self, event):
		act = self._listbox.nearest(event.y)
		self._listbox.activate(act)
		self._selectUnpost()

	# ----------------------------------------------------------------------
	def popupClick(self, event):
		if event.x < 0 or event.y < 0 or \
		   event.x > self._popup.winfo_width() or \
		   event.y > self._popup.winfo_height():
			self.unpostList()

	# ----------------------------------------------------------------------
	# The following methods are called before the show of the list ...
	# ----------------------------------------------------------------------
	def beforeShow(self):
		pass

	# ----------------------------------------------------------------------
	# ... and after hide it
	# The user should override them in case some special treatment is needed
	# ----------------------------------------------------------------------
	def afterHide(self):
		pass

	# ----------------------------------------------------------------------
	# Public methods
	# ----------------------------------------------------------------------
	def get(self, first=None, last=None):
		if first is None:
			if isinstance(self._text, Label):
				return self._text.cget("text")
			else:
				return self._text.get()
		else:
			return self._listbox.get(first, last)

	# ----------------------------------------------------------------------
	def set(self, txt):
		if isinstance(self._text, Label):
			self._text.config(text=txt)
		else:
			self._text.delete(0, END)
			self._text.insert(0, txt)
		self._text.update_idletasks()
		self.invoke()

	# ----------------------------------------------------------------------
	def size(self):
		return self._listbox.size()

	# ----------------------------------------------------------------------
	def clear(self):
		self.clearLabel()
		self.clearList()

	# ----------------------------------------------------------------------
	def clearLabel(self):
		if isinstance(self._text, Label):
			self._text.config(text="")
		else:
			self._text.delete(0, END)

	# ----------------------------------------------------------------------
	def clearList(self):
		self._listbox.delete(0, END)

	# ----------------------------------------------------------------------
	def insert(self, index, *elements):
		self._listbox.insert(index, *elements)

	# ----------------------------------------------------------------------
	def delete(self, first, last=None):
		self._listbox.delete(first, last)

	# ----------------------------------------------------------------------
	def fill(self, items):
		self.clearList()
		for item in items:
			self._listbox.insert(END, item)

	# ----------------------------------------------------------------------
	def select(self, index=None):
		if index is None:
			txt = self.get()
			for i in range(self.size()):
				if txt == self._listbox.get(i):
					return i
			return -1
		elif 0 <= index < self._listbox.size():
			self.set(self._listbox.get(index))

	# ----------------------------------------------------------------------
	def configure(self, **kwargs):
		if "command" in kwargs:
			self.command = kwargs.get("command")
			del kwargs["command"]
		self._text.configure(**kwargs)
		self._arrowBtn.configure(**kwargs)
	config = configure

	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		self.configure({key:value})

	# ----------------------------------------------------------------------
	def cget(self, key):
		return self._text.cget(key)
	__getitem__ = cget

	# ----------------------------------------------------------------------
	def bindWidgets(self, event, func):
		self._text.bind(event, func)
		self._arrowBtn.bind(event, func)

#===============================================================================
# ExOptionMenu
#===============================================================================
class ExOptionMenu(OptionMenu):
	def __init__(self, master, variable, value, *values, **kwargs):
		OptionMenu.__init__(self, master, variable, value,
			*values, **kwargs)
		self.variable = variable
		self.command  = kwargs.get("command")

	# ----------------------------------------------------------------------
	def delete(self, from_=0, to_=END):
		"""Delete items from menu"""
		self["menu"].delete(from_, to_)

	# ----------------------------------------------------------------------
	def add(self, value):
		"""Add an extra value to the menu"""
		menu = self["menu"]
		menu.add_command(label=value,
			command=_setit(self.variable, value, None))

	# ----------------------------------------------------------------------
	def set(self, valueList, value=None):
		"""
		clear and reload the menu with a new set of options.
		valueList - list of new options
		value - initial value to set the optionmenu's menubutton to
		"""
		self['menu'].delete(0, END)
		for item in valueList:
			self['menu'].add_command(label=item,
				command=_setit(self.variable, item, self.command))
		if value:
			self.variable.set(value)

#===============================================================================
# Splitter Frame
#===============================================================================
class Splitter(Frame):
	"""Base class for horizontal or vertical frame splitter"""
	def __init__(self, master, split=0.5, horizontal=True, absolute=False):
		Frame.__init__(self, master, class_="Splitter")

		self.f1 = Frame(self, bd=1, relief=SUNKEN)
		self.f2 = Frame(self, bd=1, relief=SUNKEN)
		self.dragFrame = Frame(self, bd=1, relief=GROOVE)

		self.dragFrame.bind("<B1-Motion>",       self.motion)	   # Overridden
		self.dragFrame.bind("<ButtonRelease-1>", self.placeChilds) # Overridden
		self.dragFrame.bind("<Double-Button-1>", self.toggle)
		self.split    = split
		self.save     = split
		self.absolute = absolute
		self.setRange()
		self.setOrientation(horizontal)
		if self.absolute:
			self.bind("<Configure>", self.placeChilds)

	# ----------------------------------------------------------------------
	def orient(self):      return self._hori
	def firstFrame(self):  return self.f1
	def secondFrame(self): return self.f2

	# ----------------------------------------------------------------------
	def setOrientation(self, horizontal=True):
		self._hori = horizontal	# True horizontal / False vertical
		self.f1.place_forget()
		self.f2.place_forget()
		if self._hori:
			self.dragFrame["cursor"] = "sb_h_double_arrow"
		else:
			self.dragFrame["cursor"] = "sb_v_double_arrow"
		self.placeChilds()

	# ----------------------------------------------------------------------
	def swapOrient(self):
		self.dragFrame.place_forget()
		self.setOrientation(not self._hori)

	# ----------------------------------------------------------------------
	def equal(self):
		self._setSplit(0.5)
		self.placeChilds()

	# ----------------------------------------------------------------------
	def minimize(self):
		self._setSplit(0.0)
		self.placeChilds()

	# ----------------------------------------------------------------------
	def maximize(self):
		self._setSplit(1.0)
		self.placeChilds()

	# ----------------------------------------------------------------------
	# Toggle position normally with double click
	# ----------------------------------------------------------------------
	def toggle(self, event=None):
		if self.absolute:
			if self.save == self.split: self.save = 100
			if self.split > 20:
				self.save = self.split
				self.split = 1
			else:
				self.split = self.save
		else:
			if self.save == self.split: self.save = 0.3
			if self.split <= self.min or self.split >= self.max:
				self.split = self.save
			elif self.split < 0.5:
				self.split = self.min
			else:
				self.split = self.max
		self.placeChilds()

	# ----------------------------------------------------------------------
	# Set acceptable range
	# ----------------------------------------------------------------------
	def setRange(self, _min=0.005, _max=0.995):
		if _min<0.01: _min=0.01
		if _max>0.99: _max=0.99
		self.margin = 5	# pixels on absolute
		self.min = _min
		self.max = _max

	# ----------------------------------------------------------------------
	def _setSplit(self, newSplit):
		if newSplit == self.split: return
		if self.absolute:
			if newSplit <= self.margin: newSplit = self.margin
			if self._hori:
				if newSplit + self.margin >= self.winfo_width():
					newSplit = self.winfo_width() - self.margin
			else:
				if newSplit + self.margin >= self.winfo_height():
					newSplit = self.winfo_height() - self.margin
		else:
			if newSplit <= self.min: newSplit = self.min
			if newSplit >= self.max: newSplit = self.max
		self.save  = self.split
		self.split = newSplit

	# ----------------------------------------------------------------------
	# Set the split position
	# ----------------------------------------------------------------------
	def setSplit(self, newSplit):
		"""Change the spliting position"""
		self._setSplit(newSplit)
		self.placeChilds()

	# ----------------------------------------------------------------------
	def motion(self, event):
		if self.absolute:
			if self._hori:
				# Horizontal
				self._setSplit(event.x_root - self.winfo_rootx())
				self.dragFrame.place(x=self.split-2,
						relheight=1.0, width=5)
			else:
				pass
		else:
			if self._hori:
				# Horizontal
				self._setSplit(float(event.x_root - self.winfo_rootx()) / \
					float(self.winfo_width()))
				self.dragFrame.place(relx=self.split, x=-2,
						relheight=1.0, width=5)
			else:
				# Vertical
				self._setSplit(float(event.y_root - self.winfo_rooty()) / \
					float(self.winfo_height()))
				self.dragFrame.place(rely=self.split, y=-2,
						relwidth=1.0, height=5)

	# ----------------------------------------------------------------------
	# Place the two frames
	# ----------------------------------------------------------------------
	def placeChilds(self, event=None):
		"""(Re)Place the two frames"""
		if self.absolute:
			if self._hori:
				# Horizontal
				self.f1.place(	relx=0.0,
						width=self.split,
						relheight=1.0)
				self.f2.place(	x=self.split+3,
						width=self.winfo_width()-self.split-4,
						relheight=1.0)
				self.dragFrame.place(x=self.split-1,
						relheight=1.0,
						width=3)
			else:
				# Vertical
				self.f1.place(	rely=0.0,
						height=self.split,
						relwidth=1.0)
				self.f2.place(	y=self.split+3,
						height=self.winfo_height()-self.split()-4,
						relwidth=1.0)
				self.dragFrame.place(y=self.split-1,
						relwidth=1.0,
						height=3)
		else:
			if self._hori:
				# Horizontal
				self.f1.place(	relx=0.0,
						relwidth=self.split,
						relheight=1.0)
				self.f2.place(	relx=self.split,
						x=3,
						relwidth=1.0-self.split,
						relheight=1.0)
				self.dragFrame.place(relx=self.split,
						x=-1,
						relheight=1.0,
						width=3)
			else:
				# Vertical
				self.f1.place(	rely=0.0,
						relheight=self.split,
						relwidth=1.0)
				self.f2.place(	rely=self.split,
						y=2,
						relheight=1.0-self.split,
						relwidth=1.0)
				self.dragFrame.place(rely=self.split,
						y=-2,
						relwidth=1.0,
						height=4)

#===============================================================================
# Horizontal Splitter
#===============================================================================
class HSplitter(Splitter):
	"""Horizontal frame splitter"""
	def __init__(self, master, split=0.5, absolute=False):
		Splitter.__init__(self, master, split, True, absolute)

	# ----------------------------------------------------------------------
	def leftFrame(self):  return self.firstFrame()
	left = leftFrame
	def rightFrame(self): return self.secondFrame()
	right = rightFrame

#===============================================================================
# Vertical Splitter
#===============================================================================
class VSplitter(Splitter):
	"""Vertical frame splitter"""
	def __init__(self, master, split=0.5, absolute=False):
		Splitter.__init__(self, master, split, False, absolute)

	# ----------------------------------------------------------------------
	def topFrame(self):    return self.firstFrame()
	top = topFrame
	def bottomFrame(self): return self.secondFrame()
	bottom = bottomFrame

#===============================================================================
# Splitter Node
#-------------------------------------------------------------------------------
class _SplitNode:
	def __init__(self, parent, widget, pos=0.5, hori=True):
		self.parent = parent	# Parent of node
		self.left   = None	# Left child node
		self.right  = None	# Right child node (None if end node)
		self.pos    = pos	# Splitting position (<0.0 inverts hori)
		self.hori   = hori	# Horizontal splitting (Vertical frames)
		if self.pos < 0.0:
			self.pos = -self.pos
			self.hori = not self.hori
		self.child  = widget
		self.split  = None	# drawing frame
		self._xy    = 0.0	# Absolute limits of window size for splitter
		self._wh    = 1.0

	# ----------------------------------------------------------------------
	def end(self):	return self.child is not None
	def full(self):	return self.left is not None and self.right is not None

	# ----------------------------------------------------------------------
	def getpos(self):
		if self.hori:
			return self.pos
		else:
			return -self.pos

	# ----------------------------------------------------------------------
	def setCursor(self):
		if self.split:
			if self.hori:
				self.split["cursor"] = "sb_h_double_arrow"
			else:
				self.split["cursor"] = "sb_v_double_arrow"

	# ----------------------------------------------------------------------
	def makeSplit(self, master, drag):
		self.split = Frame(master, bd=1, relief=GROOVE)
		self.split.bind("<B1-Motion>",drag)
		#split.bind("<ButtonRelease-1>", self.placeChilds)
		#split.bind("<Double-Button-1>", self.toggle)
		self.setCursor()

	# ----------------------------------------------------------------------
	def printNode(self, depth):
		if self.left: self.left.printNode(depth+1)
		if self.child:
			say("   "*depth, self.child, self.child["bg"])
		else:
			say("   "*depth, " ======== H=",self.hori," pos=",self.pos)
		if self.right: self.right.printNode(depth+1)

#===============================================================================
# Tree Splitter allows any nesting of splitting using a tree structure
#===============================================================================
class TreeSplitter(Frame):
	"""Splitter using a tree structure"""
	def __init__(self, master, **kw):
		Frame.__init__(self, master, class_="TreeSplitter", **kw)
		self.tree      = None
		self.width     =  3
		self.border    = 0.01
		self._maxchild = None
		self._splitters= {}		# Dictionary of splitters for faster lookup
		self._drag        = None
		self._dragFrame   = None
		self._drag_x_root = -1
		self._drag_y_root = -1

	# ----------------------------------------------------------------------
	def isempty(self): return self.tree is None

	# ----------------------------------------------------------------------
	# Add a new node under a parent
	# ----------------------------------------------------------------------
	def add(self, parent, child, pos=0.5, hori=True):
		node = self.node(child)
		if node is not None: return node
		if isinstance(parent, Widget):
			parent = self.node(parent)
		node = self._add(parent, child, pos, hori)
		self.placeChilds()
		return node

	# ----------------------------------------------------------------------
	def _add(self, parent, child, pos=0.5, hori=True):
		node = _SplitNode(parent, child, pos, hori)

		if parent is None:
			# Add to top
			if self.tree is None:
				self.tree = node	# Set up the root node
				self._maxchild = child
			else:
				oldtree = self.tree
				self.tree = parent = _SplitNode(None, None, pos, hori)

				parent.left = node
				node.parent = parent

				parent.right   = oldtree
				oldtree.parent = parent
				self._maxchild = None

		else:
			if parent.end():	# End node with only a child
				# Keep parent the same and make a new node for both childs
				parent.left  = _SplitNode(parent, parent.child, pos, hori)
				parent.right = node
				parent.child = None
			else:
				raise Exception("Parent node is full")
			self._maxchild = None

		if parent and parent.child is None:
			parent.makeSplit(self, self.dragSplitter)
			self._splitters[parent.split] = parent

		self.placeChilds()
		return node

	# ----------------------------------------------------------------------
	# Remove a child from the frame
	# ----------------------------------------------------------------------
	def remove(self, node):
		if isinstance(node,Widget):
			node = self.node(node)
			if node is None: return
		if node.child is self._maxchild: self._maxchild = None
		self._remove(node)
		self.placeChilds()

	# ----------------------------------------------------------------------
	def _remove(self, node):
		if not node.end():
			raise Exception("Only end nodes can be removed")

		if node.child is not None: node.child.place_forget()
		if node.split is not None:
			del self._splitters[node.split]
			node.split.place_forget()

		parent = node.parent
		if parent is None:
			self.tree = None

		elif parent.right is node:
			# re-parent left node
			grandpa = parent.parent
			if grandpa is None:	# root tree
				self.tree = parent.left
			elif grandpa.left is parent:
				grandpa.left = parent.left
			else:
				grandpa.right = parent.left
			parent.left.parent = grandpa
			if parent.split is not None:
				del self._splitters[parent.split]
				parent.split.place_forget()

		elif parent.left is node:
			# re-parent right node
			grandpa = parent.parent
			if grandpa is None:	# root tree
				self.tree = parent.right
			elif grandpa.left is parent:
				grandpa.left = parent.right
			else:
				grandpa.right = parent.right
			parent.right.parent = grandpa
			if parent.split is not None:
				del self._splitters[parent.split]
				parent.split.place_forget()

		else:
			raise Exception("TreeSplitter is broken")

	# ----------------------------------------------------------------------
	# Replace the child of the node
	# ----------------------------------------------------------------------
	def replace(self, node, child):
		place = node.child.place_info()
		if self._maxchild is node.child:
			self._maxchild = child
		node.child.place_forget()
		node.child = child
		node.child.place(**place)

	# ----------------------------------------------------------------------
	# Clean up the whole tree
	# ----------------------------------------------------------------------
	def removeAll(self):
		self.__remove(self.tree)
		self.tree = None
		self._splitters = {}
		self._maxchild = None

	# ----------------------------------------------------------------------
	def __remove(self, node):
		if node is None: return
		self.__remove(node.left)
		self.__remove(node.right)

		if node.child is not None: node.child.place_forget()
		if node.split is not None: node.split.place_forget()

	# ----------------------------------------------------------------------
	# Depending on rpn
	# if None: Return RPN expression of the tree
	# else:    Create the tree from the rpn expression
	# ----------------------------------------------------------------------
	def RPN(self, rpn=None):
		if rpn is not None:
			self.removeAll()
			stack = []
			for item in rpn:
				if isinstance(item, Widget):
					stack.append(_SplitNode(None, item))
				else:
					try:
						right = stack.pop()
						left  = stack.pop()
					except IndexError:
						break

					node = _SplitNode(None, None, item)

					node.makeSplit(self, self.dragSplitter)
					self._splitters[node.split] = node

					node.left    = left
					left.parent  = node
					node.right   = right
					right.parent = node

					stack.append(node)
			try:
				self.tree = stack.pop()
				self.placeChilds()
			except IndexError:
				pass
		else:
			rpn = []
			self.__rpn(self.tree, rpn)
			return rpn

	# ----------------------------------------------------------------------
	def __rpn(self, node, rpn):
		if node is None: return
		self.__rpn(node.left,  rpn)
		self.__rpn(node.right, rpn)

		if node.child is not None:
			rpn.append(node.child)
		else:
			rpn.append(node.getpos())

	# ----------------------------------------------------------------------
	def printTree(self):
		if self.tree: self.tree.printNode(0)

	# ----------------------------------------------------------------------
	def childs(self):
		"""Return list of child nodes"""
		lst = []
		self.__childNode(self.tree, lst)
		return lst

	# ----------------------------------------------------------------------
	def __childNode(self, node, lst):
		if node is None: return
		self.__childNode(node.left,  lst)
		self.__childNode(node.right, lst)
		if node.child is not None: lst.append(node.child)

	# ----------------------------------------------------------------------
	# return node that has as child the widget
	# ----------------------------------------------------------------------
	def __searchWidget(self, node, widget):
		if node is None: return None
		n = self.__searchWidget(node.left, widget)
		if n is not None: return n
		n = self.__searchWidget(node.right, widget)
		if n is not None: return n
		if node.child is widget: return node
		return None

	# ----------------------------------------------------------------------
	def node(self, widget):
		if widget is None: return None
		return self.__searchWidget(self.tree, widget)

	# ----------------------------------------------------------------------
	def __placeForget(self, node):
		if node is None: return
		if node.split is not None: node.split.place_forget()
		if node.child is not None: node.child.place_forget()
		self.__placeForget(node.left)
		self.__placeForget(node.right)

	# ----------------------------------------------------------------------
	def __placeNode(self, node, x, y, w, h):
		if node is None: return
		#say("placeNode", node, node.child)
		#say("    ",x, y, w, h)
		if node.end():
			# Place the child
			if x>0.0:   xx =  self.width
			else:	    xx =  0
			if x+w<1.0: ww = -self.width-xx
			else:	    ww =  0
			if y>0.0:   yy =  self.width
			else:	    yy =  0
			if y+h<1.0: hh = -self.width-yy
			else:	    hh =  0
			node.child.place(in_  = self,
					relx	 =  x,
					x	 = xx,
					relwidth =  w,
					width	 = ww,
					rely	 =  y,
					y	 = yy,
					relheight=  h,
					height	 = hh)
			return

		# Place the splitter
		if node.hori:	# Splitting along X => Vertical frames
			node._xy = x
			node._wh = w
			pos = x + w*node.pos
			sw  = pos - x
			if sw <= self.border:
				pos = min(x+self.border, x+w-self.border)
				sw  = pos - x
			if y>0.0:   yy =  self.width
			else:	    yy =  0
			if y+h<1.0: hh = -self.width
			else:	    hh =  0
			node.split.place(in_   = self,
				relx	  =   pos,
				x	  =  -self.width,
				relwidth  = 0.0,
				width	  = 2*self.width,
				rely	  = y,
				y	  = yy,
				relheight = h,
				height	  = hh)

			self.__placeNode(node.left,  x, y, sw, h)
			self.__placeNode(node.right, x+sw, y, w-sw, h)

		else:	# Splitting along Y => Horizontal frames
			node._xy = y
			node._wh = h
			pos = y + h*node.pos
			sh  = pos - y
			if sh <= self.border:
				pos = min(y+self.border, y+w-self.border)
				sh  = pos - y
			if x>0.0:   xx =  self.width
			else:	    xx =  0
			if x+w<1.0: ww = -self.width
			else:	    ww =  0
			node.split.place(in_   = self,
				relx	  = x,
				x	  = xx,
				relwidth  = w,
				width	  = ww,
				rely	  =   pos,
				y	  =  -self.width,
				relheight = 0.0,
				height	  = 2*self.width)

			self.__placeNode(node.left,  x, y, w, sh)
			self.__placeNode(node.right, x, y+sh, w, h-sh)

	# ----------------------------------------------------------------------
	# Place the frames [1..3]
	# ----------------------------------------------------------------------
	def placeChilds(self):
		if self.tree is None: return
		if self._maxchild is not None:
			self.__placeForget(self.tree)
			self._maxchild.place(in_ = self,
				relx=0.0, x=0, relwidth=1.0, width=0,
				rely=0.0, y=0, relheight=1.0, height=0)
		else:
			self.__placeNode(self.tree, 0.0, 0.0, 1.0, 1.0)

	# ----------------------------------------------------------------------
	# drag splitter and reposition childs
	# ----------------------------------------------------------------------
	def dragSplitter(self, event):
		node = self._splitters[event.widget]
		if node.hori:
			pos = float(event.x_root - self.winfo_rootx()) / \
				float(self.winfo_width())
		else:
			pos = float(event.y_root - self.winfo_rooty()) / \
				float(self.winfo_height())

		# Absolute positioning
		pos = min(max(pos,self.border),1.0-self.border)

		# Convert to relative
		node.pos = (pos - node._xy) / node._wh

		self.placeChilds()

	# ----------------------------------------------------------------------
	def maximize(self, child=None):
		if self._maxchild is child:
			self._maxchild = None
		else:
			self._maxchild = child
		self.placeChilds()

	# ----------------------------------------------------------------------
	def maxchild(self):
		return self._maxchild

	# ----------------------------------------------------------------------
	# return node containing x,y position in absolute coordinates
	# ----------------------------------------------------------------------
	def nodeContaining(self, node, x, y):
		if node is None: return None

		n = self.nodeContaining(node.left, x, y)
		if n is not None: return n

		n = self.nodeContaining(node.right, x, y)
		if n is not None: return n

		if node.child is not None:
			rx = node.child.winfo_rootx()
			ry = node.child.winfo_rooty()
			if rx <= x <= rx+node.child.winfo_width() and \
			   ry <= y <= ry+node.child.winfo_height():
				return node
		return None

	# ----------------------------------------------------------------------
	# Find position in screen
	# ----------------------------------------------------------------------
	def reposition(self, node, event):
		if self._maxchild is not None: return False
		# First check absolute placement
		x = float(event.x_root - self.winfo_rootx()) / float(self.winfo_width())
		y = float(event.y_root - self.winfo_rooty()) / float(self.winfo_height())
		if x<0.0 or x>1.0 or y<0.0 or y>1.0:
			return
		if x<0.1 or x>0.9 or y<0.1 or y>0.9:
			x1 = 1.0-x
			y1 = 1.0-y

			self._remove(node)
			newnode = self._add(None, node.child)
			parent = self.tree

			if x>y and x>y1:
				# Move to right
				parent.hori = True
				if parent.right is not None: # Swap to move to TOP
					parent.left, parent.right = parent.right, parent.left

			elif x1>y and x1>y1:
				# Move to left
				parent.hori = True

			elif y>x and y>x1:
				# Move to bottom
				parent.hori = False
				if parent.right is not None: # Swap to move to TOP
					parent.left, parent.right = parent.right, parent.left

			else:
				# Move to top
				parent.hori = False
			parent.setCursor()
			self.placeChilds()
			return True

		# Place inside another widget
		overnode = self.nodeContaining(self.tree, event.x_root, event.y_root)
		if overnode is None or overnode is node: return False
		overwidget = overnode.child

		# Then inside other widgets
		x = float(event.x_root - overwidget.winfo_rootx()) / float(overwidget.winfo_width())
		y = float(event.y_root - overwidget.winfo_rooty()) / float(overwidget.winfo_height())
		x1 = 1.0-x
		y1 = 1.0-y
		if 0.4<x<0.6 and 0.4<y<0.6:
			# Swap children
			overnode.child, node.child = node.child, overnode.child

		else:
			self._remove(node)
			overnode = self.node(overwidget)	# Maybe it has changed
			newnode  = self._add(overnode, node.child)
			parent = newnode.parent

			if x>y and x>y1:
				# Move to right
				parent.hori = True

			elif x1>y and x1>y1:
				# Move to left
				parent.hori = True
				if parent.right is not None: # Swap to move to TOP
					parent.left, parent.right = parent.right, parent.left

			elif y>x and y>x1:
				# Move to bottom
				parent.hori = False

			else:
				# Move to top
				parent.hori = False
				if parent.right is not None: # Swap to move to TOP
					parent.left, parent.right = parent.right, parent.left
			parent.setCursor()

		self.placeChilds()
		return True

	# ----------------------------------------------------------------------
	# Event handlers for dragging and placing
	# Bind to <Button-1>
	# ----------------------------------------------------------------------
	def dragStart(self, event):
		self._drag  = None
		self._dragFrame = None
		self._drag_x_root = event.x_root
		self._drag_y_root = event.y_root

	# ----------------------------------------------------------------------
	# Bind to <B1-Motion>
	# ----------------------------------------------------------------------
	def dragMove(self, event):
		if self._maxchild is not None: return
		if self.tree.child is not None: return	# Only one node
		if self._drag is None:
			if abs(self._drag_x_root - event.x_root)>10 or \
			   abs(self._drag_y_root - event.y_root)>10:
				self["cursor"] = "hand1"
				self._drag = self.nodeContaining(self.tree,
							self._drag_x_root,
							self._drag_y_root)
				if self._drag:
					self._dragFrame = Frame(self._drag.child.master,
								relief=RIDGE,
								borderwidth=2*self.width,
								bg="LightYellow")

		elif self._dragFrame is not None:
			# First check absolute placement
			sx = float(self.winfo_rootx())
			sy = float(self.winfo_rooty())
			sw = float(self.winfo_width())
			sh = float(self.winfo_height())
			x = (float(event.x_root) - sx) / sw
			y = (float(event.y_root) - sy) / sh

			if x<0.0 or x>1.0 or y<0.0 or y>1.0:
				self._dragFrame.place_forget()
				return

			if x<0.1 or x>0.9 or y<0.1 or y>0.9:
				x1 = 1.0-x
				y1 = 1.0-y

				if x>y and x>y1:
					# Move to right
					self._dragFrame.place(in_=self,
						relx = 0.5,
						relwidth = 0.5,
						rely = 0.0,
						relheight = 1.0)

				elif x1>y and x1>y1:
					# Move to left
					self._dragFrame.place(in_=self,
						relx = 0.0,
						relwidth = 0.5,
						rely = 0.0,
						relheight = 1.0)

				elif y>x and y>x1:
					# Move to bottom
					self._dragFrame.place(in_=self,
						relx = 0.0,
						relwidth = 1.0,
						rely = 0.5,
						relheight = 0.5)

				else:
					# Move to top
					self._dragFrame.place(in_=self,
						relx = 0.0,
						relwidth = 1.0,
						rely = 0.0,
						relheight = 0.5)
				self._dragFrame.lift()
				return

			# Test inside a widget
			over = self.nodeContaining(self.tree,
					event.x_root,
					event.y_root)

			if over is None or over is self._drag:
				self._dragFrame.place_forget()
				return

			overwidget = over.child

			# Then inside other widgets
			wx = float(overwidget.winfo_rootx())
			wy = float(overwidget.winfo_rooty())
			ww = float(overwidget.winfo_width())
			wh = float(overwidget.winfo_height())

			x = (float(event.x_root) - wx) / ww
			y = (float(event.y_root) - wy) / wh
			x1 = 1.0-x
			y1 = 1.0-y
			if 0.4<x<0.6 and 0.4<y<0.6:
				# Swap children
				self._dragFrame.place(in_=self,
					relx      = (wx-sx)/sw,
					relwidth  = ww/sw,
					rely      = (wy-sy)/sh,
					relheight = wh/sh)

			else:
				if x>y and x>y1:
					# Move to left
					self._dragFrame.place(in_=self,
						relx      = (wx+ww/2.0-sx)/sw,
						relwidth  = ww/sw/2.0,
						rely      = (wy-sy)/sh,
						relheight = wh/sh)

				elif x1>y and x1>y1:
					# Move to right
					self._dragFrame.place(in_=self,
						relx      = (wx-sx)/sw,
						relwidth  = ww/sw/2.0,
						rely      = (wy-sy)/sh,
						relheight = wh/sh)

				elif y>x and y>x1:
					# Move to bottom
					self._dragFrame.place(in_=self,
						relx      = (wx-sx)/sw,
						relwidth  = ww/sw,
						rely      = (wy+wh/2.0-sy)/sh,
						relheight = wh/sh/2.0)

				else:
					# Move to top
					self._dragFrame.place(in_=self,
						relx      = (wx-sx)/sw,
						relwidth  = ww/sw,
						rely      = (wy-sy)/sh,
						relheight = wh/sh/2.0)

	# ----------------------------------------------------------------------
	# Bind to <ButtonRelease-1>
	# ----------------------------------------------------------------------
	def dragEnd(self, event):
		if self._maxchild is not None: return
		if self._dragFrame is None: return
		if self._drag:
			self["cursor"] = ""
			self._dragFrame.place_forget()
			self._dragFrame = None
			return self.reposition(self._drag, event)
		return False

#=============================================================================
# Display a balloon message (only static methods)
#=============================================================================
class Balloon:
	_top	   = None
	_widget    = None
	font	   = ("Helvetica","-12")
	foreground = "Black"
	background = "LightYellow"
	delay	   = 1500
	x_mouse    = 0
	y_mouse    = 0

	# ----------------------------------------------------------------------
	# set a balloon message to a widget
	# ----------------------------------------------------------------------
	@staticmethod
	def set(widget, help):
		widget._help = help
		widget.bind('<Any-Enter>', Balloon.enter)
		widget.bind('<Any-Leave>', Balloon.leave)
		widget.bind('<Key>',	   Balloon.hide)

	# ----------------------------------------------------------------------
	@staticmethod
	def enter(event):
		if Balloon._widget is event.widget: return
		Balloon._widget = event.widget
		Balloon.x_mouse = event.x_root
		Balloon.y_mouse = event.y_root
		return event.widget.after(Balloon.delay, Balloon.show)

	# ----------------------------------------------------------------------
	@staticmethod
	def leave(event=None):
		Balloon._widget = None
		if Balloon._top is None: return
		try:
			if Balloon._top.winfo_ismapped():
				Balloon._top.withdraw()
		except TclError:
			Balloon._top = None
	hide=leave

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
			if Balloon._widget is None: return
			widget = Balloon._widget
			if Balloon._top is None:
				Balloon._top = Toplevel()
				Balloon._top.overrideredirect(1)
				Balloon._msg = Message(Balloon._top,
						aspect=300,
						foreground=Balloon.foreground,
						background=Balloon.background,
						relief=SOLID,
						borderwidth=1,
						font=Balloon.font)
				Balloon._msg.pack()
				Balloon._top.bind("<1>",Balloon.hide)
			Balloon._msg.config(text=widget._help)
			# Guess position
			x = widget.winfo_rootx() + widget.winfo_width()//2
			y = widget.winfo_rooty() + widget.winfo_height()+5
			# if too far away use mouse
			if abs(x - Balloon.x_mouse) > 30:
				x = Balloon.x_mouse + 20
			if abs(y - Balloon.y_mouse) > 30:
				y = Balloon.y_mouse + 10
			Balloon._top.wm_geometry("+%d+%d" % (x,y))
			Balloon._top.deiconify()
			Balloon._top.lift()
			Balloon._top.update_idletasks()

			# Check if it is hidden on bottom-right sides
			move = False
			if Balloon._top.winfo_rootx() + Balloon._top.winfo_width() >= \
			   Balloon._top.winfo_screenwidth():
				x = Balloon._top.winfo_screenwidth() \
					- Balloon._top.winfo_width() - 20
				move = True
			if Balloon._top.winfo_rooty() + Balloon._top.winfo_height() >= \
			   Balloon._top.winfo_screenheight():
				y = Balloon._top.winfo_screenheight() \
					- Balloon._top.winfo_height() - 10
				move = True
			if move:
				Balloon._top.wm_geometry("+%d+%d" % (x,y))

		except TclError:
			Balloon._top = None

#===============================================================================
# A LabelFrame that can collapse/expand
#===============================================================================
class ExLabelFrame(LabelFrame):
	def __init__(self, master, *args, **kwargs):
		if "command" in kwargs:
			self.command = kwargs.get("command")
			del kwargs["command"]
		else:
			self.command = None

		LabelFrame.__init__(self, master, *args, **kwargs)
		self.frame = Frame(self)
		self.frame.pack(expand=YES, fill=BOTH)
		self.bind("<Button-1>", self. click)
		if self["height"]==0:
			self["height"] = 20
		self.width   = self["width"]

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
		if lbl[-1] in (Unicode.BLACK_UP_POINTING_TRIANGLE, Unicode.BLACK_DOWN_POINTING_TRIANGLE):
			lbl = lbl[:-1]
		self["text"] = lbl+Unicode.BLACK_UP_POINTING_TRIANGLE

	# ----------------------------------------------------------------------
	def expand(self):
		self["width"] = self.width
		self.frame.pack(fill=BOTH)
		lbl = self["text"]
		if lbl[-1] in (Unicode.BLACK_UP_POINTING_TRIANGLE, Unicode.BLACK_DOWN_POINTING_TRIANGLE):
			self["text"] = lbl[:-1]

	# ----------------------------------------------------------------------
	def isexpanded(self):
		return self.frame.winfo_ismapped()

	# ----------------------------------------------------------------------
	def __call__(self): return self.frame

#================================================================================
# ScrollFrame based on Bruno's implementation
#================================================================================
class ScrollFrame(Frame):
	# ----------------------------------------------------------------------
	def __init__(self, master=None, stretch=True, cnf={}, **kw):
		Frame.__init__(self, master, cnf, **kw)
		self.client = Frame(self, border=0)

		# width and height of Scrollframe
		self.W = 1.0
		self.H = 1.0

		# top left corner coordinates of client frame
		self.client_x = 0
		self.client_y = 0

		# width and height of client frame
		self.client_w = 1.0
		self.client_h = 1.0

		# scroll commands (default)
		self.xscrollcommand=lambda *args:None
		self.yscrollcommand=lambda *args:None

		# scroll increments
		self.xscrollincrement = 15
		self.yscrollincrement = 15

		# stretches
		self.stretch   = stretch
		self.stretch_x = stretch
		self.stretch_y = stretch

		#self.bind("<Expose>",		self.updateScrollRegion)
		self.bind("<Configure>",	self.updateScrollRegion)

		self.defaultBinds()

		#w = self.client.winfo_toplevel()
		self.mult  = 1.0
		self._drag = None
		self._startx = self._startx = 0

	# ----------------------------------------------------------------------
	def cget(self,item):
		if not hasattr(self,item):
			return Frame.cget(self,item)
		else:
			getattr(self,item)
	__getitem__ = cget

	def __setitem__(self,item,value):self.configure({item:value})

	# ----------------------------------------------------------------------
	def configure(self,cnf=None,**kw):
		if kw: cnf=_cnfmerge((cnf,kw))
		for key in cnf.keys():
			if not hasattr(self,key):
				Frame.configure(self,cnf)
			else:
				setattr(self,key,cnf[key])
	config=configure

	# ----------------------------------------------------------------------
	# Use this method to get the parent widget of the frame
	# ----------------------------------------------------------------------
	def __call__(self): return self.client

	# ----------------------------------------------------------------------
	def position(self):
		return self.client_x, self.client_y

	#-------------------------------------------------------------------------------
	@staticmethod
	def bindChilds(widget, event, function, ignore=None):
		if ignore is None: ignore = [event]
		for child in widget.winfo_children():
			ScrollFrame.bindChilds(child, event, function, ignore)
			for e in ignore:
				if child.bind(e) or child.bind_class(child.__class__.__name__,e):
					break
			else:
				child.bind(event, function)

	#-------------------------------------------------------------------------------
	def defaultBinds(self):
		ignore = ["<2>", "<B2-Motion>", "<ButtonRelease-2>"]
		ScrollFrame.bindChilds(self.client, "<B2-Motion>",	self.drag, ignore)
		del ignore[1]	# delete motion that was already assigned
		ScrollFrame.bindChilds(self.client, "<ButtonRelease-2>",self.dragRelease, ignore)
		ScrollFrame.bindChilds(self.client, "<Button-4>",	self.scrollUp)
		ScrollFrame.bindChilds(self.client, "<Button-5>",	self.scrollDown)
		ScrollFrame.bindChilds(self.client, "<Shift-Button-4>",	self.scrollLeft)
		ScrollFrame.bindChilds(self.client, "<Shift-Button-5>",	self.scrollRight)

	# ----------------------------------------------------------------------
	def ischild(self, widget):
		if widget is None: return False
		if widget is self.client: return True
		return self.ischild(widget.master)

	# ----------------------------------------------------------------------
	def drag(self, event):
		if self._drag is not None:
			dx = (event.x_root - self._drag[0])*self.mult
			dy = (event.y_root - self._drag[1])*self.mult
			self.client_x = int(self._start_x + dx)
			self.client_y = int(self._start_y + dy)
			self.updateScrollx()
			self.updateScrolly()
			self.client.place_configure(x=self.client_x, y=self.client_y)
		else:
			if not self.ischild(event.widget): return
			self.config(cursor="hand2")
			self._drag = event.x_root, event.y_root
			self._start_x = self.client_x
			self._start_y = self.client_y
		return "break"

	# ----------------------------------------------------------------------
	def dragRelease(self, event):
		self._drag = None
		self.config(cursor="")
		return "break"

	# ----------------------------------------------------------------------
	def scrollUp(self, event):
		if not self.ischild(event.widget): return
		self.yview(SCROLL, -1, UNITS)
		return "break"

	# ----------------------------------------------------------------------
	def scrollDown(self, event):
		if not self.ischild(event.widget): return
		self.yview(SCROLL,  1, UNITS)
		return "break"

	# ----------------------------------------------------------------------
	def scrollLeft(self, event):
		if not self.ischild(event.widget): return
		self.xview(SCROLL, -1, UNITS)
		return "break"

	# ----------------------------------------------------------------------
	def scrollRight(self, event):
		if not self.ischild(event.widget): return
		self.xview(SCROLL,  1, UNITS)
		return "break"

	# ----------------------------------------------------------------------
	def xview(self, action, value, units='pages'):
		if action == "moveto":
			fraction = float(value)
			if fraction <= 0.0:
				self.client_x = 0
			elif fraction >= float(self.client_w-self.W)/self.client_w:
				self.client_x = self.W-self.client_w
			else:
				self.client_x = int(-self.client_w*fraction)

		elif action == "scroll":
			amount=int(value)
			if self.client_x == 0 and amount < 0:return
			if self.W >= self.client_w: return
			if self.client_x == self.W-self.client_w and amount > 0:return
			if units == "units":
				dx = self.xscrollincrement
			else:
				dx = amount*self.W*0.99
			self.client_x -= amount*dx
		else:
			return

		self.updateScrollx()
		self.client.place_configure(x=self.client_x)

	# ----------------------------------------------------------------------
	def yview(self, action, value, units='pages'):
		if action == "moveto":
			fraction=float(value)
			if fraction <= 0.0:
				self.client_y = 0
			elif fraction >= float(self.client_h-self.H)/self.client_h:
				self.client_y = self.H-self.client_h
			else:
				self.client_y = int(-self.client_h*fraction)

		elif action == "scroll":
			amount=int(value)
			if self.client_y == 0 and amount < 0:return
			if self.H >= self.client_h: return
			if self.client_y == self.H-self.client_h and amount > 0:return
			if units == "units":
				dy = self.yscrollincrement
			else:
				dy = self.H
			self.client_y -= amount*dy

		else:
			return

		self.updateScrolly()
		self.client.place_configure(y=self.client_y)

	# ----------------------------------------------------------------------
	def moveto(self, x, y):
		if x >= 0:
			self.client_x = 0
		elif x <= self.W - self.client_w:
			self.client_x = self.W-self.client_w
		else:
			self.client_x = x

		if y >= 0:
			self.client_y = 0
		elif y <= self.H - self.client_h:
			self.client_y = self.H-self.client_h
		else:
			self.client_y = y

		self.updateScrollx()
		self.updateScrolly()
		self.client.place_configure(x=self.client_x,y=self.client_y)

	# ----------------------------------------------------------------------
	def updateScrollx(self, *args):
		if self.client_x >= 0:
			low = 0.0
		else:
			low = -float(self.client_x)/self.client_w

		if self.client_x+self.client_w <= self.W:
			high = 1.0
		else:
			high = low+float(self.W)/self.client_w

		if low <= 0.0:
			self.client_x=0
		elif high >= 1.0:
			if self.client_w > self.W:
				self.client_x = self.W-self.client_w
				low  = -float(self.client_x)/self.client_w
			else:
				self.client_x = 0
				low = 0.0
			high = low+float(self.W)/self.client_w
		if self.client_w < self.W:
			self.stretch_x = self.stretch
		else:
			self.stretch_x = False
		self.xscrollcommand(low,high)

	# ----------------------------------------------------------------------
	def updateScrolly(self, *args):
		if self.client_y >= 0:
			low = 0.0
		else:
			low = -float(self.client_y)/self.client_h
		if self.client_y+self.client_h <= self.H:
			high = 1.0
		else:
			high = low+float(self.H)/self.client_h

		if low <= 0.0:
			self.client_y = 0
		elif high >= 1.0:
			if self.client_h > self.H:
				self.client_y = self.H-self.client_h
				low  = -float(self.client_y)/self.client_h
			else:
				self.client_y = 0
				low = 0.0
			high = low+float(self.H)/self.client_h

		if self.client_h < self.H:
			self.stretch_y = self.stretch
		else:
			self.stretch_y = False
		self.yscrollcommand(low,high)

	# ----------------------------------------------------------------------
	def updateScrollRegion(self, *args):
		if len(self.client.children):
			self.client_w = self.client.winfo_reqwidth()
			self.client_h = self.client.winfo_reqheight()
			self.W = self.winfo_width()
			self.H = self.winfo_height()

			self.updateScrolly()
			self.updateScrollx()

			if self.stretch_y:
				h = self.H
			else:
				h = self.client_h

			if self.stretch_x:
				w = self.W
			else:
				w = self.client_w

			self.client.place_configure(
				x=self.client_x,
				y=self.client_y,
				height=h,
				width=w,
				anchor="nw")
		else:
			self.xscrollcommand(0.0,1.0)
			self.yscrollcommand(0.0,1.0)
			self.client.place_forget()

#================================================================================
# The following is from idlelib (tabpage.py)
#================================================================================
class InvalidTabPage(Exception): pass
class AlreadyExists(Exception): pass

#===============================================================================
# A page tab frame button
#===============================================================================
class PageTab(Frame):
	"""
	a 'page tab' like framed button
	"""

	# ----------------------------------------------------------------------
	def __init__(self, parent):
		Frame.__init__(self, parent, borderwidth=2, relief=RIDGE)
		self.button=Radiobutton(self, padx=5, pady=2, takefocus=FALSE,
			indicatoron=FALSE, highlightthickness=0,
			borderwidth=0, selectcolor=self.cget('bg'))
		self.button.pack(fill=BOTH)

#===============================================================================
# Tab pages
#===============================================================================
class TabPageSet(Frame):
	"""
	a set of 'pages' with TabButtons for controlling their display
	"""

	# ----------------------------------------------------------------------
	def __init__(self, parent, pageNames=[], top=True, hidetext=False, **kw):
		"""
		pageNames - a list of strings, each string will be the dictionary key
		to a page's data, and the name displayed on the page's tab. Should be
		specified in desired page order. The first page will be the default
		and first active page.
		"""
		Frame.__init__(self, parent, kw)
		self.grid_location(0, 0)

		self.tabBar=Frame(self)
		self.top = top
		self.hidetext = hidetext

		if top:
			self.columnconfigure(0, weight=1)
			self.rowconfigure(1, weight=1)
			self.tabBar.grid(row=0, column=0, sticky=EW)
		else:
			self.columnconfigure(1, weight=1)
			self.rowconfigure(0, weight=1)
			self.tabBar.grid(row=0, column=0, sticky=NSEW)

		self.activePage=StringVar(self)
		self.defaultPage=''
		self.pages={}
		for name in pageNames:
			if isinstance(name,tuple):
				self.addPage(*name)
			else:
				self.addPage(name)

	# ----------------------------------------------------------------------
	def page(self, name):
		return self.pages[name]['page']

	# ----------------------------------------------------------------------
	def __getitem__(self, name): return self.page(name)

	# ----------------------------------------------------------------------
	def changePage(self, pageName=None):
		if pageName:
			if pageName in self.pages.keys():
				self.activePage.set(pageName)
			else:
				raise InvalidTabPage("Invalid TabPage Name")
		## pop up the active 'tab' only
		for page in self.pages.keys():
			tab = self.pages[page]['tab']
			tab.config(relief=RIDGE)
			tab.button.config(background="DarkGray",
					activebackground="DarkGray")
			if self.hidetext: tab.button.config(text="")

		tab = self.pages[self.getActivePage()]['tab']
		tab.config(relief=RAISED)
		tab.button.config(
			background="LightGray",
			activebackground="LightGray")
		if self.hidetext:
			tab.button.config(text=self.getActivePage())
		## switch page
		self.pages[self.getActivePage()]['page'].lift()

		self.event_generate("<<ChangePage>>") #, data=pageName)

	# ----------------------------------------------------------------------
	def getActivePage(self):
		return self.activePage.get()

	# ----------------------------------------------------------------------
	def addPage(self, pageName, icon=None):
		if pageName in self.pages.keys():
			raise AlreadyExists("TabPage Name Already Exists")

		self.pages[pageName]={
			'tab' : PageTab(self.tabBar),
			'page': Frame(self, borderwidth=2, relief=RAISED) }
		if icon:
			self.pages[pageName]['tab'].button.config(text=pageName,
				image=icon, compound=LEFT)
			self.icons = True
		else:
			self.pages[pageName]['tab'].button.config(text=pageName)
		self.pages[pageName]['tab'].button.config(
				command=self.changePage,
				variable=self.activePage,
				value=pageName)
		if self.top:
			self.pages[pageName]['tab'].pack(side=LEFT)
			self.pages[pageName]['page'].grid(row=1, column=0, sticky=NSEW)
		else:
			self.pages[pageName]['tab'].pack(side=TOP, fill=X)
			self.pages[pageName]['page'].grid(row=0, column=1, sticky=NSEW)

		if len(self.pages)==1: # adding first page
			self.defaultPage=pageName
			self.activePage.set(self.defaultPage)
			self.changePage()

	# ----------------------------------------------------------------------
	def removePage(self, pageName):
		if not pageName in self.pages.keys():
			raise InvalidTabPage("Invalid TabPage Name")
		self.pages[pageName]['tab'].pack_forget()
		self.pages[pageName]['page'].grid_forget()
		self.pages[pageName]['tab'].destroy()
		self.pages[pageName]['page'].destroy()
		del(self.pages[pageName])
		# handle removing last remaining, or default, or active page
		if not self.pages: # removed last remaining page
			self.defaultPage=''
			return
		if pageName==self.defaultPage: # set a new default page
			self.defaultPage=\
				self.tabBar.winfo_children()[0].button.cget('text')
		if pageName==self.getActivePage(): # set a new active page
			self.activePage.set(self.defaultPage)
		self.changePage()

	# ----------------------------------------------------------------------
	def renamePage(self, old, new):
		if not old in self.pages.keys():
			raise InvalidTabPage("Invalid TabPage Name")
		self.pages[new] = self.pages[old]
		del self.pages[old]
		self.pages[new]['tab'].button.config(text=new, value=new)
		if old == self.getActivePage():
			self.activePage.set(new)

#===============================================================================
if __name__ == "__main__":
	root = Tk()
	frame = Frame(root)
	frame.pack(side=TOP, fill=X)

	p = ProgressBar(frame, background="DarkGray", height=24)
	p.pack(side=TOP, fill=X)
	def addProg(ev):
		global p
		p.setProgress(p.getProgress()[0]+10.0)
		p.autoText()
	p.bind('<1>', addProg)

	frame = Frame(root)
	frame.pack(side=BOTTOM, expand=YES, fill=BOTH)
	hsplit	= HSplitter(frame, 0.7)
	vsplitL = VSplitter(hsplit.leftFrame(), 0.5)
	vsplitR = VSplitter(hsplit.rightFrame(), 0.3)

	Label(vsplitL.topFrame(), text='MultiListbox').pack()
	mlb = MultiListbox(vsplitL.topFrame(),
			(('Subject', 40, None),
			 ('Sender', 20, None),
			 ('Date', 10, None)))
	for i in range(100):
		mlb.insert(END, ('%d Important Message' % i,
				'John Doe', '10/10/%04d' % (1900+i)))
	mlb.pack(expand=YES, fill=BOTH)

	l = Label(vsplitL.bottomFrame(), text="Combobox")
	l.pack(side=TOP)
	cb = Combobox(vsplitL.bottomFrame(), label=True)
	cb.pack(side=BOTTOM, expand=YES, fill=X)
	cb.fill(("one","two","three","four", "fix-six-seven-eight-nine-ten"))
	cb.select(0)

	Label(vsplitR.topFrame(), text='SearchListbox').pack()
	lb = SearchListbox(vsplitR.topFrame(), selectmode=BROWSE,
		exportselection=FALSE)
	lb.insert(END,"Starting")
	lb.insert(END,"Loading card database")
	lb.insert(END,"Loading isotopes database")
	lb.insert(END,"Layout initialization")
	lb.insert(END,"Layout create Tree list")
	lb.insert(END,"--Initialize Tk")
	lb.insert(END,"After initialization of Tk")
	lb.insert(END,"Creating frames")
	lb.insert(END,"Creation of windows...")
	lb.insert(END,"Writing ini file")
	lb.insert(END,"Exiting program")
#	lb.fill()
	lb.pack(expand=YES, fill=BOTH)
	lb.focus_set()
	lb.ignoreCase	  = True
#	lb.ignoreNonAlpha = False

#	v = StringVar()
#	lst = ["One", "Two", "Three", "Four"]
#	v.set("One")
#	o = ExOptionMenu(vsplitR.bottomFrame(), v, *lst)
#	o.pack()
#	o.delete()
#	lst.reverse()
#	for i in lst:
#		o.add(i)

	#test dialog
	frame = vsplitR.bottomFrame()
	tabPage=TabPageSet(frame, pageNames=['Foobar','Baz'])
	tabPage.pack(expand=TRUE, fill=BOTH)
	Label(tabPage['Foobar'], text='Foo', pady=20).pack()
	Label(tabPage['Foobar'], text='Bar', pady=20).pack()
	Label(tabPage['Baz'], text='Baz').pack()
	entryPgName=Entry(frame)
	buttonAdd=Button(frame, text='Add Page',
		command=lambda:tabPage.addPage(entryPgName.get()))
	buttonRemove=Button(frame, text='Remove Page',
		command=lambda:tabPage.removePage(entryPgName.get()))
	labelPgName=Label(frame, text='name of page to add/remove:')
	buttonAdd.pack(padx=5, pady=5)
	buttonRemove.pack(padx=5, pady=5)
	labelPgName.pack(padx=5)
	entryPgName.pack(padx=5)
	tabPage.changePage()
	b = Button(root, text="Exit", command=root.destroy)
	Balloon.set(b, "Push me to exit")
	b.pack()
	e = FloatEntry(root)
	Balloon.set(e, "Enter a floating point number")
	e.pack()
	e = IntegerEntry(root)
	Balloon.set(e, "Enter an integer number")
	e.pack()
	root.geometry("800x600")

	root.mainloop()
