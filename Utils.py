#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	16-Apr-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import os
import glob
import traceback
from log import say
try:
	from Tkinter import *
	import ConfigParser
	import tkMessageBox
except ImportError:
	from tkinter import *
	import configparser as ConfigParser
	import tkinter.messagebox as tkMessageBox

__prg__     = "bCNC"

prgpath   = os.path.abspath(os.path.dirname(sys.argv[0]))
iniSystem = os.path.join(prgpath,"%s.ini"%(__prg__))
iniUser   = os.path.expanduser("~/.%s" % (__prg__))
hisFile   = os.path.expanduser("~/.%s.history" % (__prg__))
icons     = {}
config    = ConfigParser.ConfigParser()

_errorReport = True
errors    = []

#-----------------------------------------------------------------------------
def loadIcons():
	global icons
	icons = {}
	for img in glob.glob("%s%sicons%s*.gif"%(prgpath,os.sep,os.sep)):
		name,ext = os.path.splitext(os.path.basename(img))
		try:
			icons[name] = PhotoImage(file=img)
		except TclError:
			pass

#-------------------------------------------------------------------------------
def delIcons():
	global icons
	if len(icons) > 0:
		for i in icons.values():
			del i

#------------------------------------------------------------------------------
# Load configuration
#------------------------------------------------------------------------------
def loadConfiguration(systemOnly=False):
	global config, _errorReport
	if systemOnly:
		config.read(iniSystem)
	else:
		config.read([iniSystem, iniUser])
		_errorReport = getInt("Connection","errorreport",1)
		loadIcons()

#------------------------------------------------------------------------------
# Save configuration file
#------------------------------------------------------------------------------
def saveConfiguration():
	global config
	cleanConfiguration()
	f = open(iniUser,"w")
	config.write(f)
	f.close()
	delIcons()

#----------------------------------------------------------------------
# Remove items that are the same as in the default ini
#----------------------------------------------------------------------
def cleanConfiguration():
	global config
	newconfig = config	# Remember config
	config = ConfigParser.ConfigParser()

	loadConfiguration(True)

	# Compare items
	for section in config.sections():
		for item, value in config.items(section):
			try:
				new = newconfig.get(section, item)
				if value==new:
					newconfig.remove_option(section, item)
			except ConfigParser.NoOptionError:
				pass
	config = newconfig

#------------------------------------------------------------------------------
def getStr(section, name, default):
	global config
	try: return config.get(section, name)
	except: return default

#------------------------------------------------------------------------------
def getInt(section, name, default):
	global config
	try: return int(config.get(section, name))
	except: return default

#------------------------------------------------------------------------------
def getFloat(section, name, default):
	global config
	try: return float(config.get(section, name))
	except: return default

#------------------------------------------------------------------------------
# Return all comports when serial.tools.list_ports is not available!
#------------------------------------------------------------------------------
def comports():
	locations=[	'/dev/ttyACM',
			'/dev/ttyUSB',
			'/dev/ttyS',
			'com']

	comports = []
	for prefix in locations:
		for i in range(32):
			device = "%s%d"%(prefix,i)
			try:
				os.stat(device)
				comports.append((device,None,None))
			except OSError:
				pass
	return comports

#===============================================================================
def addException():
	global errors
	#self.widget._report_exception()
	try:
		typ, val, tb = sys.exc_info()
		traceback.print_exception(typ, val, tb)
		if errors: errors.append("")
		exception = traceback.format_exception(typ, val, tb)
		errors.extend(exception)
		if len(errors) > 100:
			# If too many errors are found send the error report
			ReportDialog(self.widget)
	except:
		say(sys.exc_info())

#===============================================================================
class CallWrapper:
	"""Replaces the Tkinter.CallWrapper with extra functionality"""
	def __init__(self, func, subst, widget):
		"""Store FUNC, SUBST and WIDGET as members."""
		self.func   = func
		self.subst  = subst
		self.widget = widget

	# ----------------------------------------------------------------------
	def __call__(self, *args):
		"""Apply first function SUBST to arguments, than FUNC."""
		try:
			if self.subst:
				args = self.subst(*args)
			return self.func(*args)
		# One possible fix is to make an external file for the wrapper
		# and import depending the version
		#except SystemExit, msg:	# python2.4 syntax
		#except SystemExit as msg:	# python3 syntax
		#	raise SystemExit(msg)
		except SystemExit:		# both
			raise SystemExit(sys.exc_info()[1])
		except KeyboardInterrupt:
			pass
		except:
			addException()

#===============================================================================
# Error message reporting dialog
#===============================================================================
class ReportDialog(Toplevel):
	_shown = False	# avoid re-entry when multiple errors are displayed

	def __init__(self, master):
		if ReportDialog._shown: return
		ReportDialog._shown = True

		Toplevel.__init__(self, master)
		self.title("%s Error Reporting"%(__name__))
		#self.transient(master)

		# Label Frame
		frame = LabelFrame(self, text="Report")
		frame.pack(side=TOP, expand=YES, fill=BOTH)

		l = Label(frame, text="The following report is about to be send "\
				"to the author of %s"%(__name__), justify=LEFT, anchor=W)
		l.pack(side=TOP)

		self.text = Text(frame, background="White")
		self.text.pack(side=LEFT, expand=YES, fill=BOTH)

		sb = Scrollbar(frame, orient=VERTICAL, command=self.text.yview)
		sb.pack(side=RIGHT, fill=Y)
		self.text.config(yscrollcommand=sb.set)

		# email frame
		frame = Frame(self)
		frame.pack(side=TOP, fill=X)

		l = Label(frame, text="Your email")
		l.pack(side=LEFT)

		self.email = Entry(frame, background="White")
		self.email.pack(side=LEFT, expand=YES, fill=X)

		# Automatic error reporting
		self.err = BooleanVar()
		self.err.set(_errorReport)
		b = Checkbutton(frame, text="Automatic error reporting",
			variable=self.err, anchor=E, justify=RIGHT)
		b.pack(side=RIGHT)

		# Buttons
		frame = Frame(self)
		frame.pack(side=BOTTOM, fill=X)

		b = Button(frame, text="Close",
				compound=LEFT,
				command=self.cancel)
		b.pack(side=RIGHT)
		b = Button(frame, text="Send report",
				compound=LEFT,
				command=self.send)
		b.pack(side=RIGHT)

		# Fill report
		txt = [ "Program     : %s"%(__prg__),
#			"Version     : %s"%(__version__),
#			"Revision    : %s"%(__revision__),
#			"Last Change : %s"%(__lastchange__),
			"Platform    : %s"%(sys.platform),
			"Python      : %s"%(sys.version),
			"TkVersion   : %s"%(TkVersion),
			"TclVersion  : %s"%(TclVersion),
			"\nTraceback:" ]
		for e in errors:
			if e!="" and e[-1] == "\n":
				txt.append(e[:-1])
			else:
				txt.append(e)

		self.text.insert('0.0', "\n".join(txt))

		# Guess email
		user = os.getenv("USER")
		host = os.getenv("HOSTNAME")
		if user and host:
			email = "%s@%s"%(user,host)
		else:
			email = ""
		self.email.insert(0,email)

		self.protocol("WM_DELETE_WINDOW", self.close)
		self.bind('<Escape>', self.close)

		# Wait action
		self.wait_visibility()
		self.grab_set()
		self.focus_set()
		self.wait_window()

	# ----------------------------------------------------------------------
	def close(self, event=None):
		ReportDialog._shown = False
		self.destroy()

	# ----------------------------------------------------------------------
	def send(self):
		import httplib, urllib
		global errors
		email = self.email.get()
		desc  = self.text.get('1.0', END).strip()

		# Send information
		self.config(cursor="watch")
		self.text.config(cursor="watch")
		self.update_idletasks()
		params = urllib.urlencode({"email":email, "desc":desc})
		headers = {"Content-type": "application/x-www-form-urlencoded",
			"Accept": "text/plain"}
		conn = httplib.HTTPConnection("www.fluka.org:80")
		try:
			conn.request("POST", "/flair/send_email.php", params, headers)
			response = conn.getresponse()
		except:
			tkMessageBox.showwarning("Error sending report",
				"There was a problem connecting to the web site",
				parent=self)
		else:
			if response.status == 200:
				tkMessageBox.showinfo("Report successfully send",
					"Report was successfully uploaded to web site",
					parent=self)
				del errors[:]
			else:
				tkMessageBox.showwarning("Error sending report",
					"There was an error sending the report\nCode=%d %s"%\
					(response.status, response.reason),
					parent=self)
		conn.close()
		self.config(cursor="")
		self.cancel()

	# ----------------------------------------------------------------------
	def cancel(self):
		global _errorReport, errors
		_errorReport = self.err.get()
		config.set("Connection", "errorreport", str(bool(self.err.get())))
		del errors[:]
		self.close()

	# ----------------------------------------------------------------------
	@staticmethod
	def sendErrorReport():
		ReportDialog(None)
