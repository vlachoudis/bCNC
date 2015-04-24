#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id$
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	16-Apr-2015

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import os
import glob
try:
	from Tkinter import *
	import ConfigParser
except ImportError:
	from tkinter import *
	import configparser as ConfigParser

__prg__     = "bCNC"

prgpath   = os.path.abspath(os.path.dirname(sys.argv[0]))
iniSystem = os.path.join(prgpath,"%s.ini"%(__prg__))
iniUser   = os.path.expanduser("~/.%s" % (__prg__))
hisFile   = os.path.expanduser("~/.%s.history" % (__prg__))
icons     = {}
config    = ConfigParser.ConfigParser()

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
def loadConfiguration():
	global config
	config.read([iniSystem, iniUser])
	loadIcons()

#------------------------------------------------------------------------------
def saveConfiguration():
	global config
	f = open(iniUser,"w")
	config.write(f)
	f.close()
	delIcons()

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
