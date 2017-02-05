#!/usr/bin/python
# -*- coding: ascii -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 17-Jun-2015

__author__  = "Vasilis Vlachoudis"
__email__   = "vvlachoudis@gmail.com"

import os
import re
import sys
import rexx
import time
import threading
import webbrowser

from datetime import datetime
try:
	import serial
except:
	serial = None
try:
	from Queue import *
except ImportError:
	from queue import *

from CNC import WAIT, MSG, UPDATE, WCS, CNC, GCode
import Utils
import Pendant

WIKI = "https://github.com/vlachoudis/bCNC/wiki"

SERIAL_POLL   = 0.125	# s
G_POLL	      = 10	# s
RX_BUFFER_SIZE = 128

OV_FEED_100     = chr(0x90)        # Extended override commands
OV_FEED_i10     = chr(0x91)
OV_FEED_d10     = chr(0x92)
OV_FEED_i1      = chr(0x93)
OV_FEED_d1      = chr(0x94)

OV_RAPID_100    = chr(0x95)
OV_RAPID_50     = chr(0x96)
OV_RAPID_25     = chr(0x97)

OV_SPINDLE_100  = chr(0x99)
OV_SPINDLE_i10  = chr(0x9A)
OV_SPINDLE_d10  = chr(0x9B)
OV_SPINDLE_i1   = chr(0x9C)
OV_SPINDLE_d1   = chr(0x9D)

OV_SPINDLE_STOP = chr(0x9E)

OV_FLOOD_TOGGLE = chr(0xA0)
OV_MIST_TOGGLE  = chr(0xA1)


GPAT	  = re.compile(r"[A-Za-z]\d+.*")
STATUSPAT = re.compile(r"^<(\w*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),?(.*)>$")
POSPAT	  = re.compile(r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*):?(\d*)\]$")
TLOPAT	  = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")
DOLLARPAT = re.compile(r"^\[G\d* .*\]$")
FEEDPAT   = re.compile(r"^(.*)[fF](\d+\.?\d+)(.*)$")
SPLITPAT  = re.compile(r"[:,]")
VARPAT    = re.compile(r"^\$(\d+)=(\d*\.?\d*) *\(?.*")

CONNECTED     = "Connected"
NOT_CONNECTED = "Not connected"

STATECOLOR = {	"Alarm"       : "Red",
		"Run"	      : "LightGreen",
		"Hold"	      : "Orange",
		"Hold:0"      : "Orange",
		"Hold:1"      : "Orange",
		CONNECTED     : "Orange",
		NOT_CONNECTED : "OrangeRed"
		}

STATE_DESC = {
		"Hold:0" : "Hold complete",
		"Hold:1" : "Hold in-progress",
		"Door:0" : "Door closed",
		"Door:1" : "Machine stopped",
		"Door:2" : "Door opened",
		"Door:3" : "Door closed and resuming",
	}

STATECOLORDEF = "LightYellow"

# From https://github.com/grbl/grbl/wiki/Interfacing-with-Grbl
ERROR_CODES = {
	"Run"	   : _("bCNC is currently sending a gcode program to Grbl"),
	"Idle"	   : _("Grbl is in idle state and waiting for user commands"),
	"Hold"	   : _("Grbl is on hold state. Click on resume (pause) to continue"),
	"Alarm"    : _("Alarm is an emergency state. Something has gone terribly wrong when these occur. Typically, they are caused by limit error when the machine has moved or wants to move outside the machine space and crash into something. They also report problems if Grbl is lost and can't guarantee positioning or a probe command has failed. Once in alarm-mode, Grbl will lock out and shut down everything until the user issues a reset. Even after a reset, Grbl will remain in alarm-mode, block all G-code from being executed, but allows the user to override the alarm manually. This is to ensure the user knows and acknowledges the problem and has taken steps to fix or account for it."),
	NOT_CONNECTED : _("Grbl is not connected. Please specify the correct port and click Open."),
	CONNECTED     : _("Connection is established with Grbl"),

	"ok" : _("All is good! Everything in the last line was understood by Grbl and was successfully processed and executed."),

	"error:1"  : _("G-code words consist of a letter and a value. Letter was not found."),
	"error:2"  : _("Numeric value format is not valid or missing an expected value."),
	"error:3"  : _("Grbl '$' system command was not recognized or supported."),
	"error:4"  : _("Negative value received for an expected positive value."),
	"error:5"  : _("Homing cycle is not enabled via settings."),
	"error:6"  : _("Minimum step pulse time must be greater than 3usec"),
	"error:7"  : _("EEPROM read failed. Reset and restored to default values."),
	"error:8"  : _("Grbl '$' command cannot be used unless Grbl is IDLE. Ensures smooth operation during a job."),
	"error:9"  : _("G-code locked out during alarm or jog state"),
	"error:10" : _("Soft limits cannot be enabled without homing also enabled."),
	"error:11" : _("Max characters per line exceeded. Line was not processed and executed."),
	"error:12" : _("(Compile Option) Grbl '$' setting value exceeds the maximum step rate supported."),
	"error:13" : _("Safety door detected as opened and door state initiated."),
	"error:14" : _("(Grbl-Mega Only) Build info or startup line exceeded EEPROM line length limit."),
	"error:15" : _("Jog target exceeds machine travel. Command ignored."),
	"error:16" : _("Jog command with no '=' or contains prohibited g-code."),
	"error:20" : _("Unsupported or invalid g-code command found in block."),
	"error:21" : _("More than one g-code command from same modal group found in block."),
	"error:22" : _("Feed rate has not yet been set or is undefined."),
	"error:23" : _("G-code command in block requires an integer value."),
	"error:24" : _("Two G-code commands that both require the use of the XYZ axis words were detected in the block."),
	"error:25" : _("A G-code word was repeated in the block."),
	"error:26" : _("A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected."),
	"error:27" : _("N line number value is not within the valid range of 1 - 9,999,999."),
	"error:28" : _("A G-code command was sent, but is missing some required P or L value words in the line."),
	"error:29" : _("Grbl supports six work coordinate systems G54-G59. G59.1, G59.2, and G59.3 are not supported."),
	"error:30" : _("The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active."),
	"error:31" : _("There are unused axis words in the block and G80 motion mode cancel is active."),
	"error:32" : _("A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc."),
	"error:33" : _("The motion command has an invalid target. G2, G3, and G38.2 generates this error, if the arc is impossible to generate or if the probe target is the current position."),
	"error:34" : _("A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semi-circles or quadrants, or redefine them with the arc offset definition."),
	"error:35" : _("A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc."),
	"error:36" : _("There are unused, leftover G-code words that aren't used by any command in the block."),
	"error:37" : _("The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis."),
	"error:38" : _("An invalid tool number sent to the parser"),

	"ALARM:1" : _("Hard limit triggered. Machine position is likely lost due to sudden and immediate halt. Re-homing is highly recommended."),
	"ALARM:2" : _("G-code motion target exceeds machine travel. Machine position safely retained. Alarm may be unlocked."),
	"ALARM:3" : _("Reset while in motion. Grbl cannot guarantee position. Lost steps are likely. Re-homing is highly recommended."),
	"ALARM:4" : _("Probe fail. The probe is not in the expected initial state before starting probe cycle, where G38.2 and G38.3 is not triggered and G38.4 and G38.5 is triggered."),
	"ALARM:5" : _("Probe fail. Probe did not contact the workpiece within the programmed travel for G38.2 and G38.4."),
	"ALARM:6" : _("Homing fail. Reset during active homing cycle."),
	"ALARM:7" : _("Homing fail. Safety door was opened during active homing cycle."),
	"ALARM:8" : _("Homing fail. Cycle failed to clear limit switch when pulling off. Try increasing pull-off setting or check wiring."),
	"ALARM:9" : _("Homing fail. Could not find limit switch within search distance. Defined as 1.5 * max_travel on search and 5 * pulloff on locate phases."),

	"Hold:0" : _("Hold complete. Ready to resume."),
	"Hold:1" : _("Hold in-progress. Reset will throw an alarm."),
	"Door:0" : _("Door closed. Ready to resume."),
	"Door:1" : _("Machine stopped. Door still ajar. Can't resume until closed."),
	"Door:2" : _("Door opened. Hold (or parking retract) in-progress. Reset will throw an alarm."),
	"Door:3" : _("Door closed and resuming. Restoring from park, if applicable. Reset will throw an alarm."),
}

# Convert Grbl V1.0 codes to Grbl V0.9
for e1,e0 in (	("error: Expected command letter", "error:1"),
		("error: Bad number format", "error:2"),
		("error: Invalid statement", "error:3"),
		("error: Value < 0", "error:4"),
		("error: Setting disabled", "error:5"),
		("error: Value < 3 usec", "error:6"),
		("error: EEPROM read fail. Using defaults", "error:7"),
		("error: Not idle", "error:8"),
		("error: G-code lock", "error:9"),
		("error: Homing not enabled", "error:10"),
		("error: Line overflow", "error:11"),
		("error: Step rate > 30kHz*", "error:12"),
		("error: Check Door", "error:13"),
		("error: Line length exceeded", "error:14"),
		("error: Travel exceeded", "error:15"),
		("error: Invalid jog command", "error:16"),
		("error: Unsupported command", "error:20"),
		("error: Modal group violation", "error:21"),
		("error: Undefined feed rate", "error:22"),
		("error: Invalid gcode ID:23", "error:23"),
		("error: Invalid gcode ID:24", "error:24"),
		("error: Invalid gcode ID:25", "error:25"),
		("error: Invalid gcode ID:26", "error:26"),
		("error: Invalid gcode ID:27", "error:27"),
		("error: Invalid gcode ID:28", "error:28"),
		("error: Invalid gcode ID:29", "error:29"),
		("error: Invalid gcode ID:30", "error:30"),
		("error: Invalid gcode ID:31", "error:31"),
		("error: Invalid gcode ID:32", "error:32"),
		("error: Invalid gcode ID:33", "error:33"),
		("error: Invalid gcode ID:34", "error:34"),
		("error: Invalid gcode ID:35", "error:35"),
		("error: Invalid gcode ID:36", "error:36"),
		("error: Invalid gcode ID:37", "error:37"),
		("ALARM: Hard limit", "ALARM:1"),
		("ALARM: Soft limit", "ALARM:2"),
		("ALARM: Abort during cycle", "ALARM:3"),
		("ALARM: Probe fail", "ALARM:4"),
		("ALARM: Probe fail", "ALARM:5"),
		("ALARM: Homing fail", "ALARM:6"),
		("ALARM: Homing fail", "ALARM:7"),
		("ALARM: Homing fail", "ALARM:8"),
		("ALARM: Homing fail", "ALARM:9") ):
	ERROR_CODES[e1] = ERROR_CODES[e0]

#==============================================================================
# bCNC Sender class
#==============================================================================
class Sender:
	# Messages types for log Queue
	MSG_BUFFER  =  0	# write to buffer one command
	MSG_SEND    =  1	# send message
	MSG_RECEIVE =  2	# receive message from controller
	MSG_OK	    =  3	# ok response from controller, move top most command to terminal
	MSG_ERROR   =  4	# error message or exception
	MSG_RUNEND  =  5	# run ended
	MSG_CLEAR   =  6	# clear buffer

	def __init__(self):
		# Global variables
		self.history	 = []
		self._historyPos = None
		CNC.loadConfig(Utils.config)
		self.gcode = GCode()
		self.cnc   = self.gcode.cnc

		self.log	 = Queue()	# Log queue returned from GRBL
		self.queue	 = Queue()	# Command queue to be send to GRBL
		self.pendant	 = Queue()	# Command queue to be executed from Pendant
		self.serial	 = None
		self.thread	 = None
		self.controller  = Utils.CONTROLLER["Grbl"]

		self._posUpdate  = False	# Update position
		self._probeUpdate= False	# Update probe
		self._gUpdate	 = False	# Update $G
		self._update	 = None		# Generic update

		self.running	 = False
		self._runLines	 = 0
		self._quit	 = 0		# Quit counter to exit program
		self._stop	 = False	# Raise to stop current run
		self._pause	 = False	# machine is on Hold
		self._alarm	 = True		# Display alarm message if true
		self._msg	 = None
		self._sumcline	 = 0
		self._lastFeed	 = 0
		self._newFeed	 = 0

		self._onStart    = ""
		self._onStop     = ""

	#----------------------------------------------------------------------
	def quit(self, event=None):
		self.saveConfig()
		Pendant.stop()

	#----------------------------------------------------------------------
	def loadConfig(self):
		self.controller  = Utils.CONTROLLER.get(Utils.getStr("Connection", "controller"), Utils.GRBL0)
		Pendant.port	 = Utils.getInt("Connection","pendantport",Pendant.port)
		GCode.LOOP_MERGE = Utils.getBool("File","dxfloopmerge")
		self.loadHistory()

	#----------------------------------------------------------------------
	def saveConfig(self):
		self.saveHistory()

	#----------------------------------------------------------------------
	def loadHistory(self):
		try:
			f = open(Utils.hisFile,"r")
		except:
			return
		self.history = [x.strip() for x in f]
		f.close()

	#----------------------------------------------------------------------
	def saveHistory(self):
		try:
			f = open(Utils.hisFile,"w")
		except:
			return
		f.write("\n".join(self.history))
		f.close()

	#----------------------------------------------------------------------
	# Evaluate a line for possible expressions
	# can return a python exception, needs to be catched
	#----------------------------------------------------------------------
	def evaluate(self, line):
		return self.gcode.evaluate(CNC.compileLine(line,True))

	#----------------------------------------------------------------------
	# Execute a line as gcode if pattern matches
	# @return True on success
	#	  False otherwise
	#----------------------------------------------------------------------
	def executeGcode(self, line):
		if isinstance(line, tuple) or \
		   line[0] in ("$","!","~","?","(","@") or GPAT.match(line):
			self.sendGCode(line)
			return True
		return False

	#----------------------------------------------------------------------
	# Execute a single command
	#----------------------------------------------------------------------
	def executeCommand(self, line):
		#print
		#print "<<<",line
		#try:
		#	line = self.gcode.evaluate(CNC.compileLine(line,True))
		#except:
		#	return "Evaluation error", sys.exc_info()[1]
		#print ">>>",line

		if line is None: return

		oline = line.strip()
		line  = oline.replace(","," ").split()
		cmd   = line[0].upper()

		# ABS*OLUTE: Set absolute coordinates
		if rexx.abbrev("ABSOLUTE",cmd,3):
			self.sendGCode("G90")

		# HELP: open browser to display help
		elif cmd == "HELP":
			self.help()

		# HOME: perform a homing cycle
		elif cmd == "HOME":
			self.home()

		# LO*AD [filename]: load filename containing g-code
		elif rexx.abbrev("LOAD",cmd,2):
			self.load(line[1])

		# OPEN: open serial connection to grbl
		# CLOSE: close serial connection to grbl
		elif cmd in ("OPEN","CLOSE"):
			self.openClose()

		# QU*IT: quit program
		# EX*IT: exit program
		elif rexx.abbrev("QUIT",cmd,2) or rexx.abbrev("EXIT",cmd,2):
			self.quit()

		# PAUSE: pause cycle
		elif cmd == "PAUSE":
			self.pause()

		# RESUME: resume
		elif cmd == "RESUME":
			self.resume()

		# FEEDHOLD: feedhold
		elif cmd == "FEEDHOLD":
			self.feedHold()

		# REL*ATIVE: switch to relative coordinates
		elif rexx.abbrev("RELATIVE",cmd,3):
			self.sendGCode("G91")

		# RESET: perform a soft reset to grbl
		elif cmd == "RESET":
			self.softReset()

		# RUN: run g-code
		elif cmd == "RUN":
			self.run()

		# SAFE [z]: safe z to move
		elif cmd=="SAFE":
			try: self.cnc.safe = float(line[1])
			except: pass
			self.statusbar["text"] = "Safe Z= %g"%(self.cnc.safe)

		# SA*VE [filename]: save to filename or to default name
		elif rexx.abbrev("SAVE",cmd,2):
			if len(line)>1:
				self.save(line[1])
			else:
				self.saveAll()

		# SENDHEX: send a hex-char in grbl
		elif cmd == "SENDHEX":
			self.sendHex(line[1])

		# SET [x [y [z]]]: set x,y,z coordinates to current workspace
		elif cmd == "SET":
			try: x = float(line[1])
			except: x = None
			try: y = float(line[2])
			except: y = None
			try: z = float(line[3])
			except: z = None
			self._wcsSet(x,y,z)

		elif cmd == "SET0":
			self._wcsSet(0.,0.,0.)

		elif cmd == "SETX":
			try: x = float(line[1])
			except: x = ""
			self._wcsSet(x,None,None)

		elif cmd == "SETY":
			try: y = float(line[1])
			except: y = ""
			self._wcsSet(None,y,None)

		elif cmd == "SETZ":
			try: z = float(line[1])
			except: z = ""
			self._wcsSet(None,None,z)

		# STOP: stop current run
		elif cmd == "STOP":
			self.stopRun()

		# UNL*OCK: unlock grbl
		elif rexx.abbrev("UNLOCK",cmd,3):
			self.unlock()

		# Send commands to SMOOTHIE
		elif self.controller == Utils.SMOOTHIE:
			if line[0] in (	"help", "version", "mem", "ls",
					"cd", "pwd", "cat", "rm", "mv",
					"remount", "play", "progress", "abort",
					"reset", "dfu", "break", "config-get",
					"config-set", "get", "set_temp", "get",
					"get", "net", "load", "save", "upload",
					"calc_thermistor", "thermistors", "md5sum"):
				self.serial.write(oline+"\n")

		else:
			return _("unknown command"),_("Invalid command %s")%(oline)

	#----------------------------------------------------------------------
	def help(self, event=None):
		webbrowser.open(WIKI,new=2)

	#----------------------------------------------------------------------
	def loadRecent(self, recent):
		filename = Utils.getRecent(recent)
		if filename is None: return
		self.load(filename)

	#----------------------------------------------------------------------
	def _loadRecent0(self,event): self.loadRecent(0)
	def _loadRecent1(self,event): self.loadRecent(1)
	def _loadRecent2(self,event): self.loadRecent(2)
	def _loadRecent3(self,event): self.loadRecent(3)
	def _loadRecent4(self,event): self.loadRecent(4)
	def _loadRecent5(self,event): self.loadRecent(5)
	def _loadRecent6(self,event): self.loadRecent(6)
	def _loadRecent7(self,event): self.loadRecent(7)
	def _loadRecent8(self,event): self.loadRecent(8)
	def _loadRecent9(self,event): self.loadRecent(9)

	#----------------------------------------------------------------------
	def _saveConfigFile(self, filename=None):
		if filename is None:
			filename = self.gcode.filename
		Utils.setUtf("File", "dir",   os.path.dirname(os.path.abspath(filename)))
		Utils.setUtf("File", "file",  os.path.basename(filename))
		Utils.setUtf("File", "probe", os.path.basename(self.gcode.probe.filename))

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename):
		fn,ext = os.path.splitext(filename)
		ext = ext.lower()
		if ext==".probe":
			if filename is not None:
				self.gcode.probe.filename = filename
				self._saveConfigFile()
			self.gcode.probe.load(filename)
		elif ext == ".orient":
			# save orientation file
			self.gcode.orient.load(filename)
		elif ext == ".stl":
			# FIXME: implements solid import???
			pass
		elif ext==".dxf":
			self.gcode.init()
			self.gcode.importDXF(filename)
			self._saveConfigFile(filename)
		else:
			self.gcode.load(filename)
			self._saveConfigFile()
		Utils.addRecent(filename)

	#----------------------------------------------------------------------
	def save(self, filename):
		fn,ext = os.path.splitext(filename)
		ext = ext.lower()
		if ext == ".probe":
			# save probe
			if filename is not None:
				self.gcode.probe.filename = filename
				self._saveConfigFile()
			if not self.gcode.probe.isEmpty():
				self.gcode.probe.save()
		elif ext == ".orient":
			# save orientation file
			self.gcode.orient.save(filename)
		elif ext == ".stl":
			#save probe as STL
			self.gcode.probe.saveAsSTL(filename)
		elif ext == ".dxf":
			return self.gcode.saveDXF(filename)
		elif ext == ".txt":
			#save gcode as txt (only enable blocks and no bCNC metadata)
			return self.gcode.saveTXT(filename)
		else:
			if filename is not None:
				self.gcode.filename = filename
				self._saveConfigFile()
			Utils.addRecent(self.gcode.filename)
			return self.gcode.save()

	#----------------------------------------------------------------------
	def saveAll(self, event=None):
		if self.gcode.filename:
			self.save(self.gcode.filename)
			if self.gcode.probe.filename:
				self.save(self.gcode.probe.filename)
		return "break"

	#----------------------------------------------------------------------
	# Open serial port
	#----------------------------------------------------------------------
	def open(self, device, baudrate):
		self.serial = serial.Serial(	device,
						baudrate,
						bytesize=serial.EIGHTBITS,
						parity=serial.PARITY_NONE,
						stopbits=serial.STOPBITS_ONE,
						timeout=0.1,
						xonxoff=False,
						rtscts=False)
		# Toggle DTR to reset Arduino
		try:
			self.serial.setDTR(0)
		except IOError:
			pass
		time.sleep(1)
		CNC.vars["state"] = CONNECTED
		CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
		#self.state.config(text=CNC.vars["state"],
		#		background=CNC.vars["color"])
		# toss any data already received, see
		# http://pyserial.sourceforge.net/pyserial_api.html#serial.Serial.flushInput
		self.serial.flushInput()
		try:
			self.serial.setDTR(1)
		except IOError:
			pass
		time.sleep(1)
		self.serial.write(b"\n\n")
		self._gcount = 0
		self._alarm  = True
		self.thread  = threading.Thread(target=self.serialIO)
		self.thread.start()
		return True

	#----------------------------------------------------------------------
	# Close serial port
	#----------------------------------------------------------------------
	def close(self):
		if self.serial is None: return
		try:
			self.stopRun()
		except:
			pass
		self._runLines = 0
		self.thread = None
		time.sleep(1)
		self.serial.close()
		self.serial = None
		CNC.vars["state"] = NOT_CONNECTED
		CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]

	#----------------------------------------------------------------------
	# Send to controller a gcode or command
	# WARNING: it has to be a single line!
	#----------------------------------------------------------------------
	def sendGCode(self, cmd):
		if self.serial and not self.running:
			if isinstance(cmd,tuple):
				self.queue.put(cmd)
			else:
				self.queue.put(cmd+"\n")

	#----------------------------------------------------------------------
	def sendHex(self, hexcode):
		if self.serial is None: return
		self.serial.write(chr(int(hexcode,16)))
		self.serial.flush()

	#----------------------------------------------------------------------
	def hardReset(self):
		self.busy()
		if self.serial is not None:
			if self.controller == Utils.SMOOTHIE:
				self.serial.write(b"reset\n")
			self.openClose()
			if self.controller == Utils.SMOOTHIE:
				time.sleep(6)
		self.openClose()
		self.stopProbe()
		self._alarm = False
		CNC.vars["_OvChanged"] = True	# force a feed change if any
		self.notBusy()

	#----------------------------------------------------------------------
	def softReset(self):
		if self.serial:
		#	if self.controller in (Utils.GRBL, Utils.GRBL1):
				self.serial.write(b"\030")
		#	elif self.controller == Utils.SMOOTHIE:
		#		self.serial.write(b"reset\n")
		self.stopProbe()
		self._alarm = False
		CNC.vars["_OvChanged"] = True	# force a feed change if any

	#----------------------------------------------------------------------
	def unlock(self):
		self._alarm = False
		self.sendGCode("$X")

	#----------------------------------------------------------------------
	def home(self, event=None):
		self._alarm = False
		self.sendGCode("$H")

	#----------------------------------------------------------------------
	def viewSettings(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$$")

	def viewParameters(self):
		self.sendGCode("$#")

	def viewState(self):
		self.sendGCode("$G")

	def viewBuild(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$I")
		elif self.controller == Utils.SMOOTHIE:
			self.serial.write(b"version\n")

	def viewStartup(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$N")

	def checkGcode(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$C")

	def grblHelp(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$")
		elif self.controller == Utils.SMOOTHIE:
			self.serial.write(b"help\n")

	def grblRestoreSettings(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$RST=$")

	def grblRestoreWCS(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$RST=#")

	def grblRestoreAll(self):
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			self.sendGCode("$RST=#")

	#----------------------------------------------------------------------
	def goto(self, x=None, y=None, z=None):
		cmd = "G90G0"
		if x is not None: cmd += "X%g"%(x)
		if y is not None: cmd += "Y%g"%(y)
		if z is not None: cmd += "Z%g"%(z)
		self.sendGCode("%s"%(cmd))

	#----------------------------------------------------------------------
	# FIXME Duplicate with ControlPage
	#----------------------------------------------------------------------
	def _wcsSet(self, x, y, z):
		p = WCS.index(CNC.vars["WCS"])
		if p<6:
			cmd = "G10L20P%d"%(p+1)
		elif p==6:
			cmd = "G28.1"
		elif p==7:
			cmd = "G30.1"
		elif p==8:
			cmd = "G92"

		pos = ""
		if x is not None and abs(x)<10000.0: pos += "X"+str(x)
		if y is not None and abs(y)<10000.0: pos += "Y"+str(y)
		if z is not None and abs(z)<10000.0: pos += "Z"+str(z)
		cmd += pos
		self.sendGCode(cmd)
		self.sendGCode("$#")
		self.event_generate("<<Status>>",
			data=(_("Set workspace %s to %s")%(WCS[p],pos)))
			#data=(_("Set workspace %s to %s")%(WCS[p],pos)).encode("utf8"))
		self.event_generate("<<CanvasFocus>>")

	#----------------------------------------------------------------------
	def feedHold(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write(b"!")
		self.serial.flush()
		self._pause = True

	#----------------------------------------------------------------------
	def resume(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write(b"~")
		self.serial.flush()
		self._msg   = None
		self._alarm = False
		self._pause = False

	#----------------------------------------------------------------------
	def pause(self, event=None):
		if self.serial is None: return
		if self._pause:
			self.resume()
		else:
			self.feedHold()

	#----------------------------------------------------------------------
	# FIXME ????
	#----------------------------------------------------------------------
	def g28Command(self):
		self.sendGCode("G28.1")

	#----------------------------------------------------------------------
	# FIXME ????
	#----------------------------------------------------------------------
	def g30Command(self):
		self.sendGCode("G30.1")

	#----------------------------------------------------------------------
	def emptyQueue(self):
		while self.queue.qsize()>0:
			try:
				self.queue.get_nowait()
			except Empty:
				break

	#----------------------------------------------------------------------
	def stopProbe(self):
		if self.gcode.probe.start:
			self.gcode.probe.clear()

	#----------------------------------------------------------------------
	def getBufferFill(self):
		return self._sumcline * 100. / RX_BUFFER_SIZE

	#----------------------------------------------------------------------
	def initRun(self):
		self._quit   = 0
		self._pause  = False
		self._paths  = None
		self.running = True
		self.disable()
		self.emptyQueue()
		time.sleep(1)

	#----------------------------------------------------------------------
	# Called when run is finished
	#----------------------------------------------------------------------
	def runEnded(self):
		if self.running:
			self.log.put((Sender.MSG_RUNEND,_("Run ended")))
			self.log.put((Sender.MSG_RUNEND, str(datetime.now())))
			self.log.put((Sender.MSG_RUNEND, str(CNC.vars["msg"])))
			if self._onStop:
				try:
					os.system(self._onStop)
				except:
					pass
		self._runLines = 0
		self._quit     = 0
		self._msg      = None
		self._pause    = False
		self.running   = False
		CNC.vars["running"] = False

	#----------------------------------------------------------------------
	# Purge the buffer of the controller. Unfortunately we have to perform
	# a reset to clear the buffer of the controller
	#---------------------------------------------------------------------
	def purgeController(self):
		time.sleep(1)
		# remember and send all G commands
		G = " ".join([x for x in CNC.vars["G"] if x[0]=="G"])	# remember $G
		TLO = CNC.vars["TLO"]
		self.softReset()			# reset controller
		if self.controller in (Utils.GRBL0, Utils.GRBL1):
			time.sleep(1)
			self.unlock()
		self.runEnded()
		self.stopProbe()
		if G: self.sendGCode(G)			# restore $G
		self.sendGCode("G43.1Z%s"%(TLO))	# restore TLO
		self.sendGCode("$G")

	#----------------------------------------------------------------------
	# Stop the current run
	#----------------------------------------------------------------------
	def stopRun(self, event=None):
		self.feedHold()
		self._stop = True
		# if we are in the process of submitting do not do anything
		if self._runLines != sys.maxint:
			self.purgeController()

	#----------------------------------------------------------------------
	# thread performing I/O on serial line
	#----------------------------------------------------------------------
	def serialIO(self):
		cline  = []		# length of pipeline commands
		sline  = []		# pipeline commands
		wait   = False		# wait for commands to complete (status change to Idle)
		tosend = None		# next string to send
		status = False		# waiting for status <...> report
		tr = tg = time.time()	# last time a ? or $G was send to grbl

		while self.thread:
			t = time.time()
			# refresh machine position?
			if t-tr > SERIAL_POLL:
				self.serial.write(b"?")
				status = True
				tr = t

				#If Override change, attach feed
				if CNC.vars["_OvChanged"] and self.controller == Utils.GRBL1:
					CNC.vars["_OvChanged"] = False	# Temporary
					# Check feed
					diff = CNC.vars["_OvFeed"] - CNC.vars["OvFeed"]
					if diff==0:
						pass
					elif CNC.vars["_OvFeed"] == 100:
						self.serial.write(OV_FEED_100)
					elif diff >= 10:
						self.serial.write(OV_FEED_i10)
						CNC.vars["_OvChanged"] = diff>10
					elif diff <= -10:
						self.serial.write(OV_FEED_d10)
						CNC.vars["_OvChanged"] = diff<-10
					elif diff >= 1:
						self.serial.write(OV_FEED_i1)
						CNC.vars["_OvChanged"] = diff>1
					elif diff <= -1:
						self.serial.write(OV_FEED_d1)
						CNC.vars["_OvChanged"] = diff<-1
					# Check rapid
					target  = CNC.vars["_OvRapid"]
					current = CNC.vars["OvRapid"]
					if target == current:
						pass
					elif target == 100:
						self.serial.write(OV_RAPID_100)
					elif target == 75:
						self.serial.write(OV_RAPID_50)	# FIXME
					elif target == 50:
						self.serial.write(OV_RAPID_50)
					elif target == 25:
						self.serial.write(OV_RAPID_25)
					# Check Spindle
					diff = CNC.vars["_OvSpindle"] - CNC.vars["OvSpindle"]
					if diff==0:
						pass
					elif CNC.vars["_OvSpindle"] == 100:
						self.serial.write(OV_SPINDLE_100)
					elif diff >= 10:
						self.serial.write(OV_SPINDLE_i10)
						CNC.vars["_OvChanged"] = diff>10
					elif diff <= -10:
						self.serial.write(OV_SPINDLE_d10)
						CNC.vars["_OvChanged"] = diff<-10
					elif diff >= 1:
						self.serial.write(OV_SPINDLE_i1)
						CNC.vars["_OvChanged"] = diff>1
					elif diff <= -1:
						self.serial.write(OV_SPINDLE_d1)
						CNC.vars["_OvChanged"] = diff<-1

			# Fetch new command to send if...
			if tosend is None and not wait and not self._pause and self.queue.qsize()>0:
				try:
					tosend = self.queue.get_nowait()
					#print "+++",repr(tosend)
					if isinstance(tosend, tuple):
						#print "gcount tuple=",self._gcount
						# wait to empty the grbl buffer and status is Idle
						if tosend[0] == WAIT:
							# Don't count WAIT until we are idle!
							wait = True
							#print "+++ WAIT ON"
							#print "gcount=",self._gcount, self._runLines
						elif tosend[0] == MSG:
							# Count executed commands as well
							self._gcount += 1
							if tosend[1] is not None:
								# show our message on machine status
								self._msg = tosend[1]
						elif tosend[0] == UPDATE:
							# Count executed commands as well
							self._gcount += 1
							self._update = tosend[1]
						else:
							# Count executed commands as well
							self._gcount += 1
						tosend = None

					elif not isinstance(tosend,str) and not isinstance(tosend,unicode):
						try:
							tosend = self.gcode.evaluate(tosend)
#							if isinstance(tosend, list):
#								cline.append(len(tosend[0]))
#								sline.append(tosend[0])
							if isinstance(tosend,str) or isinstance(tosend,unicode):
								tosend += "\n"
							else:
								# Count executed commands as well
								self._gcount += 1
								#print "gcount str=",self._gcount
							#print "+++ eval=",repr(tosend),type(tosend)
						except:
							for s in str(sys.exc_info()[1]).splitlines():
								self.log.put((Sender.MSG_ERROR,s))
							self._gcount += 1
							tosend = None
				except Empty:
					break

				if tosend is not None:
					# All modification in tosend should be
					# done before adding it to cline
					if isinstance(tosend, unicode):
						tosend = tosend.encode("ascii","replace")

					#Keep track of last feed
					pat = FEEDPAT.match(tosend)
					if pat is not None:
						self._lastFeed = pat.group(2)

					if self.controller in (Utils.GRBL0, Utils.SMOOTHIE):
						if CNC.vars["_OvChanged"]:
							CNC.vars["_OvChanged"] = False
							self._newFeed = float(self._lastFeed)*CNC.vars["_OvFeed"]/100.0
							if pat is None and self._newFeed!=0:
								tosend = "f%g" % (self._newFeed) + tosend

						#Apply override Feed
						if CNC.vars["_OvFeed"] != 100 and self._newFeed!=0:
							pat = FEEDPAT.match(tosend)
							if pat is not None:
								try:
									tosend = "%sf%g%s\n" % \
										(pat.group(1),
										 self._newFeed,
										 pat.group(3))
								except:
									pass

					# Bookkeeping of the buffers
					sline.append(tosend)
					cline.append(len(tosend))

			# Anything to receive?
			if self.serial.inWaiting() or tosend is None:
				line = str(self.serial.readline()).strip()
				#print "<R<",repr(line)
				#print "*-* stack=",sline,"sum=",sum(cline),"wait=",wait,"pause=",self._pause
				if not line:
					pass

				elif line[0]=="<":
					if not status:
						self.log.put((Sender.MSG_RECEIVE, line))

					elif self.controller == Utils.GRBL1:
						status = False
						fields = line[1:-1].split("|")
						#print fields
						if not self._alarm:
							CNC.vars["state"] = fields[0]
						for field in fields[1:]:
							word = SPLITPAT.split(field)
							if word[0] == "MPos":
								CNC.vars["mx"] = float(word[1])
								CNC.vars["my"] = float(word[2])
								CNC.vars["mz"] = float(word[3])
								CNC.vars["wx"] = round(CNC.vars["mx"]-CNC.vars["wcox"], CNC.digits)
								CNC.vars["wy"] = round(CNC.vars["my"]-CNC.vars["wcoy"], CNC.digits)
								CNC.vars["wz"] = round(CNC.vars["mz"]-CNC.vars["wcoz"], CNC.digits)
								self._posUpdate = True
							elif word[0] == "F":
								CNC.vars["curfeed"] = float(word[1])
							elif word[0] == "FS":
								CNC.vars["curfeed"]    = float(word[1])
								CNC.vars["curspindle"] = float(word[2])
							elif word[0] == "Bf":
								CNC.vars["planner"] = int(word[1])
								CNC.vars["rxbytes"] = int(word[2])
							elif word[0] == "Ov":
								CNC.vars["OvFeed"]    = int(word[1])
								CNC.vars["OvRapid"]   = int(word[2])
								CNC.vars["OvSpindle"] = int(word[2])
							elif word[0] == "WCO":
								CNC.vars["wcox"] = float(word[1])
								CNC.vars["wcoy"] = float(word[2])
								CNC.vars["wcoz"] = float(word[3])

						# Machine is Idle buffer is empty stop waiting and go on
						if wait and not cline and fields[0]=="Idle":
							wait = False
							self._gcount += 1

					else:
						status = False
						pat = STATUSPAT.match(line)
						if pat:
							if not self._alarm:
								CNC.vars["state"] = pat.group(1)
							CNC.vars["mx"] = float(pat.group(2))
							CNC.vars["my"] = float(pat.group(3))
							CNC.vars["mz"] = float(pat.group(4))
							CNC.vars["wx"] = float(pat.group(5))
							CNC.vars["wy"] = float(pat.group(6))
							CNC.vars["wz"] = float(pat.group(7))
							CNC.vars["wcox"] = CNC.vars["mx"] - CNC.vars["wx"]
							CNC.vars["wcoy"] = CNC.vars["my"] - CNC.vars["wy"]
							CNC.vars["wcoz"] = CNC.vars["mz"] - CNC.vars["wz"]
							self._posUpdate = True
							if pat.group(1)[:4] != "Hold" and self._msg:
								self._msg = None

							# Machine is Idle buffer is empty
							# stop waiting and go on
							#print "<<< WAIT=",wait,sline,pat.group(1),sum(cline)
							#print ">>>", line
							if wait and not cline and pat.group(1)=="Idle":
								#print ">>>",line
								wait = False
								#print "<<< NO MORE WAIT"
								self._gcount += 1
						else:
							self.log.put((Sender.MSG_RECEIVE, line))

				elif line[0]=="[":
					self.log.put((Sender.MSG_RECEIVE, line))
					if self.controller == Utils.GRBL1:
						word = SPLITPAT.split(line[1:-1])
						#print word
						if word[0] == "PRB":
							CNC.vars["prbx"] = float(word[1])
							CNC.vars["prby"] = float(word[2])
							CNC.vars["prbz"] = float(word[3])
							#if self.running:
							self.gcode.probe.add(
								 CNC.vars["prbx"]-CNC.vars["wcox"],
								 CNC.vars["prby"]-CNC.vars["wcoy"],
								 CNC.vars["prbz"]-CNC.vars["wcoy"])
							self._probeUpdate = True
							CNC.vars[word[0]] = word[1:]
						elif word[0] == "GC":
							CNC.vars["G"] = word[1].split()
							CNC.updateG()
							self._gUpdate = True
						elif word[0] == "TLO":
							CNC.vars[word[0]] = word[1]
							self._probeUpdate = True
						else:
							CNC.vars[word[0]] = word[1:]
					else:
						pat = POSPAT.match(line)
						if pat:
							if pat.group(1) == "PRB":
								CNC.vars["prbx"] = float(pat.group(2))
								CNC.vars["prby"] = float(pat.group(3))
								CNC.vars["prbz"] = float(pat.group(4))
								#if self.running:
								self.gcode.probe.add(
									 CNC.vars["prbx"]
									+CNC.vars["wx"]
									-CNC.vars["mx"],
									 CNC.vars["prby"]
									+CNC.vars["wy"]
									-CNC.vars["my"],
									 CNC.vars["prbz"]
									+CNC.vars["wz"]
									-CNC.vars["mz"])
								self._probeUpdate = True
							CNC.vars[pat.group(1)] = \
								[float(pat.group(2)),
								 float(pat.group(3)),
								 float(pat.group(4))]
						else:
							pat = TLOPAT.match(line)
							if pat:
								CNC.vars[pat.group(1)] = pat.group(2)
								self._probeUpdate = True
							elif DOLLARPAT.match(line):
								CNC.vars["G"] = line[1:-1].split()
								CNC.updateG()
								self._gUpdate = True

				elif "error:" in line or "ALARM:" in line:
					self.log.put((Sender.MSG_ERROR, line))
					self._gcount += 1
					#print "gcount ERROR=",self._gcount
					if cline: del cline[0]
					if sline: CNC.vars["errline"] = sline.pop(0)
					if not self._alarm: self._posUpdate = True
					self._alarm = True
					CNC.vars["state"] = line
					if self.running:
						self._stop = True
						self.runEnded()

				elif line.find("ok")>=0:
					self.log.put((Sender.MSG_OK, line))
					self._gcount += 1
					if cline: del cline[0]
					if sline: del sline[0]
					#print "SLINE:",sline
#					if  self._alarm and not self.running:
#						# turn off alarm for connected status once
#						# a valid gcode event occurs
#						self._alarm = False

				elif line[0] == "$":
					self.log.put((Sender.MSG_RECEIVE, line))
					pat = VARPAT.match(line)
					if pat:
						CNC.vars["grbl_%s"%(pat.group(1))] = pat.group(2)

				elif line[:4]=="Grbl" or line[:13]=="CarbideMotion": # and self.running:
					tg = time.time()
					self.log.put((Sender.MSG_RECEIVE, line))
					self._stop = True
					del cline[:]	# After reset clear the buffer counters
					del sline[:]
					self.runEnded()
					CNC.vars["version"] = line.split()[1]
					# Detect controller
					if self.controller in (Utils.GRBL0, Utils.GRBL1):
						self.controller = int(CNC.vars["version"][0])

				else:
					self.log.put((Sender.MSG_RECEIVE, line))

			# Received external message to stop
			if self._stop:
				self.emptyQueue()
				tosend = None
				self.log.put((Sender.MSG_CLEAR, ""))
				# WARNING if maxint then it means we are still preparing/sending
				# lines from from bCNC.run(), so don't stop
				if self._runLines != sys.maxint:
					self._stop = False

			#print "tosend='%s'"%(repr(tosend)),"stack=",sline,
			#	"sum=",sum(cline),"wait=",wait,"pause=",self._pause
			if tosend is not None and sum(cline) < RX_BUFFER_SIZE:
				self._sumcline = sum(cline)
#				if isinstance(tosend, list):
#					self.serial.write(str(tosend.pop(0)))
#					if not tosend: tosend = None

				#print ">S>",repr(tosend),"stack=",sline,"sum=",sum(cline)
				if self.controller==Utils.SMOOTHIE: tosend = tosend.upper()
				self.serial.write(bytes(tosend))
				#self.serial.write(tosend.encode("utf8"))
				#self.serial.flush()
				self.log.put((Sender.MSG_BUFFER,tosend))

				tosend = None
				if not self.running and t-tg > G_POLL:
					tosend = b"$G\n"
					sline.append(tosend)
					cline.append(len(tosend))
					tg = t
