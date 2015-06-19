#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 18-Jun-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "vvlachoudis@gmail.com"

import Ribbon

#===============================================================================
# CNC Page interface between the basic Page class and the bCNC class
#===============================================================================
class Page(Ribbon.Page):
	def __init__(self, master, app, **kw):
		self.app = app
		Ribbon.Page.__init__(self, master, **kw)

	#----------------------------------------------------------------------
	# Add a widget in the widgets list to enable disable during the run
	#----------------------------------------------------------------------
	def addWidget(self, widget):
		self.app.widgets.append(widget)

	#----------------------------------------------------------------------
	# Send a command to Grbl
	#----------------------------------------------------------------------
	def sendGrbl(self, cmd):
		self.app.sendGrbl(cmd)

	#----------------------------------------------------------------------
	# Accept the user key if not editing any text
	#----------------------------------------------------------------------
	def acceptKey(self, skipRun=False):
		if self.getActivePage() == "Editor": return False
		if not skipRun and self.app.running: return False
		focus = self.focus_get()
		if isinstance(focus, Entry) or \
		   isinstance(focus, Spinbox) or \
		   isinstance(focus, Text): return False
		return True

