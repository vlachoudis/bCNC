#!/usr/bin/python
# -*- coding: latin1 -*-
# $Id: bCNC.py,v 1.6 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author: vvlachoudis@gmail.com
# Date: 17-Jun-2015

__version__ = "0.4.9"
__date__    = "15 Jun 2015"
__author__  = "Vasilis Vlachoudis"
__email__   = "vvlachoudis@gmail.com"

import os
import re
import sys
import rexx
import time
import serial
import threading
try:
	from Queue import *
except ImportError:
	from queue import *

from CNC import CNC, GCode
import Utils
import Pendant

SERIAL_POLL   = 0.250	# s
G_POLL        = 10	# s

RX_BUFFER_SIZE = 128

GPAT     = re.compile(r"[A-Za-z]\d+.*")
STATUSPAT= re.compile(r"^<(\w*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),?(.*)>$")
POSPAT   = re.compile(r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*):?(\d*)\]$")
TLOPAT   = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")
FEEDPAT  = re.compile(r"^(.*)[fF](\d+\.?\d+)(.*)$")

NOT_CONNECTED = "Not connected"

STATECOLOR = {	"Alarm"       : "Red",
		"Run"         : "LightGreen",
		"Hold"        : "Orange",
		"Connected"   : "Orange",
		NOT_CONNECTED : "OrangeRed"}

STATECOLORDEF = "LightYellow"

ERROR_CODES = {
	23 : "A G or M command value in the block is not an integer. For example, G4 can't be G4.13. Some G-code commands are floating point (G92.1), but these are ignored.",
	24 : "Two G-code commands that both require the use of the XYZ axis words were detected in the block.",
	25 : "A G-code word was repeated in the block.",
	26 : "A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected.",
	27 : "The G-code protocol mandates N line numbers to be within the range of 1-99,999. We think that's a bit silly and arbitrary. So, we increased the max number to 9,999,999. This error occurs when you send a number more than this.",
	28 : "A G-code command was sent, but is missing some important P or L value words in the line. Without them, the command can't be executed. Check your G-code.",
	29 : "Grbl supports six work coordinate systems G54-G59. This error happens when trying to use or configure an unsupported work coordinate system, such as G59.1, G59.2, and G59.3.",
	30 : "The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active.",
	31 : "There are unused axis words in the block and G80 motion mode cancel is active.",
	32 : "A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc.",
	33 : "The motion command has an invalid target. G2, G3, and G38.2 generates this error. For both probing and arcs traced with the radius definition, the current position cannot be the same as the target. This also errors when the arc is mathematically impossible to trace, where the current position, the target position, and the radius of the arc doesn't define a valid arc.",
	34 : "A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semi-circles or quadrants, or redefine them with the arc offset definition.",
	35 : "A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc.",
	36 : "There are unused, leftover G-code words that aren't used by any command in the block.",
	37 : "The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis.",
}

#==============================================================================
# bCNC Sender class
#==============================================================================
class Sender:
	def __init__(self):
		# Global variables
		self.history     = []
		self._historyPos = None
		CNC.loadConfig(Utils.config)
		self.gcode = GCode()
		self.cnc   = self.gcode.cnc
		self.wait  = False	# wait for commands to complete

		self.log         = Queue()	# Log queue returned from GRBL
		self.queue       = Queue()	# Command queue to send to GRBL
		self.pendant     = Queue()	# Command queue to be executed from Pendant
		self.serial      = None
		self.thread      = None

		self._posUpdate  = False
		self._wcsUpdate  = False
		self._probeUpdate= False
		self._gUpdate    = False
		self.running     = False
		self._stop       = False	# Raise to stop current run
		self._runLines   = 0
		self._pause      = False
		self._alarm      = True

	#----------------------------------------------------------------------
	def quit(self, event=None):
		self.saveConfig()
		Pendant.stop()

	#----------------------------------------------------------------------
	def loadConfig(self):
		Pendant.port = Utils.getInt("Connection","pendantport",Pendant.port)
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
		return self.gcode.evaluate(CNC.parseLine2(line,True))

	#----------------------------------------------------------------------
	# Execute a line as gcode if pattern matches
	# @return True on success
	#         False otherwise
	#----------------------------------------------------------------------
	def executeGcode(self, line):
		if isinstance(line, int):
			self.sendGrbl(line)
			return True

		elif line[0] in ("$","!","~","?","(","@") or GPAT.match(line):
			self.sendGrbl(line+"\n")
			return True
		return False

	#----------------------------------------------------------------------
	# Execute a single command
	#----------------------------------------------------------------------
	def executeCommand(self, line):
		#print
		#print "<<<",line
		#try:
		#	line = self.gcode.evaluate(CNC.parseLine2(line,True))
		#except:
		#	return "Evaluation error", sys.exc_info()[1]
		#print ">>>",line

		if line is None: return

		oline = line.strip()
		line  = oline.replace(","," ").split()
		cmd   = line[0].upper()

		# ABS*OLUTE: Set absolute coordinates
		if rexx.abbrev("ABSOLUTE",cmd,3):
			self.sendGrbl("G90\n")

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

		# REL*ATIVE: switch to relative coordinates
		elif rexx.abbrev("RELATIVE",cmd,3):
			self.sendGrbl("G91\n")

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

		# STOP: stop current run
		elif cmd == "STOP":
			self.stopRun()

		# UNL*OCK: unlock grbl
		elif rexx.abbrev("UNLOCK",cmd,3):
			self.unlock()

		else:
			return "unknown command","Invalid command %s"%(oline)

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
		Utils.setStr("File", "dir",   os.path.dirname(os.path.abspath(filename)))
		Utils.setStr("File", "file",  os.path.basename(filename))
		Utils.setStr("File", "probe", os.path.basename(self.gcode.probe.filename))

	#----------------------------------------------------------------------
	# Load a file into editor
	#----------------------------------------------------------------------
	def load(self, filename):
		fn,ext = os.path.splitext(filename)
		if ext==".probe":
			if filename is not None:
				self.gcode.probe.filename = filename
				self._saveConfigFile()
			self.gcode.probe.load(filename)
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
		if ext == ".probe":
			# save probe
			if filename is not None:
				self.gcode.probe.filename = filename
				self._saveConfigFile()
			if not self.gcode.probe.isEmpty():
				self.gcode.probe.save()
		elif ext == ".dxf":
			return self.gcode.saveDXF(filename)
		else:
			if filename is not None:
				self.gcode.filename = filename
				self._saveConfigFile()
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
		self.serial.setDTR(0)
		time.sleep(1)
		CNC.vars["state"] = "Connected"
		CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
		#self.state.config(text=CNC.vars["state"],
		#		background=CNC.vars["color"])
		# toss any data already received, see
		# http://pyserial.sourceforge.net/pyserial_api.html#serial.Serial.flushInput
		self.serial.flushInput()
		self.serial.setDTR(1)
		self.serial.write("\r\n\r\n")
		self._gcount = 0
		self._alarm  = True
		self.thread  = threading.Thread(target=self.serialIO)
		self.thread.start()
		return True

#	#----------------------------------------------------------------------
#	def close(self):
#		if self.serial is None: return
#		try:
#			self.stopRun()
#		except:
#			pass
#		self._runLines = 0
#		self.thread = None
#		time.sleep(1)
#		self.serial.close()
#		self.serial = None
#		CNC.vars["state"] = NOT_CONNECTED
#		CNC.vars["color"] = STATECOLOR[CNC.vars["state"]]
#		try:
#			self.state.config(text=CNC.vars["state"],
#					background=CNC.vars["color"])
#		except TclError:
#			pass

	#----------------------------------------------------------------------
	# Send to grbl
	#----------------------------------------------------------------------
	def sendGrbl(self, cmd):
#		print
#		print ">>>",cmd
#		import traceback
#		traceback.print_stack()
		if self.serial and not self.running:
			self.queue.put(cmd)

	#----------------------------------------------------------------------
	def hardReset(self):
		if self.serial is not None:
			self.openClose()
		self.openClose()

	#----------------------------------------------------------------------
	def softReset(self):
		if self.serial:
			self.serial.write("\030")

	def unlock(self):
		self._alarm = False
		self.sendGrbl("$X\n")

	def home(self):
		self._alarm = False
		self.sendGrbl("$H\n")

	#----------------------------------------------------------------------
	def viewSettings(self):
		self.sendGrbl("$$\n")

	def viewParameters(self):
		self.sendGrbl("$#\n$G\n")

	def viewState(self):
		self.sendGrbl("$G\n")

	def viewBuild(self):
		self.sendGrbl("$I\n")

	def viewStartup(self):
		self.sendGrbl("$N\n")

	def checkGcode(self):
		self.sendGrbl("$C\n")

	def grblhelp(self):
		self.sendGrbl("$\n")

	#----------------------------------------------------------------------
	def goto(self, x=None, y=None, z=None):
		cmd = "G90G0"
		if x is not None: cmd += "X%g"%(x)
		if y is not None: cmd += "Y%g"%(y)
		if z is not None: cmd += "Z%g"%(z)
		self.sendGrbl("%s\n"%(cmd))

	def go2origin(self, event=None):
		self.sendGrbl("G90G0X0Y0Z0\n")

	def resetCoords(self, event):
		if not self.running: self.sendGrbl("G10P0L20X0Y0Z0\n")

	def resetX(self, event):
		if not self.running: self.sendGrbl("G10P0L20X0\n")

	def resetY(self, event):
		if not self.running: self.sendGrbl("G10P0L20Y0\n")

	def resetZ(self, event):
		if not self.running: self.sendGrbl("G10P0L20Z0\n")

	#----------------------------------------------------------------------
	def feedHold(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("!")
		self.serial.flush()
		self._pause = True

	#----------------------------------------------------------------------
	def resume(self, event=None):
		if event is not None and not self.acceptKey(True): return
		if self.serial is None: return
		self.serial.write("~")
		self.serial.flush()
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
		self.sendGrbl("G28.1\n")

	#----------------------------------------------------------------------
	# FIXME ????
	#----------------------------------------------------------------------
	def g30Command(self):
		self.sendGrbl("G30.1\n")

	#----------------------------------------------------------------------
	# Probe an X-Y area
	#----------------------------------------------------------------------
	def probeScanArea(self):
		if self.probeChange(): return

		if self.serial is None or self.running: return
		probe = self.gcode.probe
		self.initRun()

		# absolute
		probe.clear()
		lines = probe.scan()
		self._runLines = len(lines)
		self._gcount   = 0
		self._selectI  = -1		# do not show any lines selected

		self.progress.setLimits(0, self._runLines)

		self.running = True
		# Push commands
		for line in lines:
			self.queue.put(line)

	#----------------------------------------------------------------------
	def emptyQueue(self):
		while self.queue.qsize()>0:
			try:
				self.queue.get_nowait()
			except Empty:
				break

	#----------------------------------------------------------------------
	def initRun(self):
		self._quit  = 0
		self._pause = False
		self._paths = None
		self.disable()
		self.emptyQueue()
		self.queue.put(self.tools["CNC"]["startup"]+"\n")
		time.sleep(1)

	#----------------------------------------------------------------------
	# Send enabled gcode file to the CNC machine
	#----------------------------------------------------------------------
# FIXME To be cleaned up from bCNC.py
#	def run(self):
#		if self.serial is None:
#			return ("Serial Error", "Serial is not connected")
#		if self.running:
#			if self._pause:
#				self.resume()
#				return
#			return ("Already running", "Please stop before")
#		if not self.gcode.probe.isEmpty() and not self.gcode.probe.zeroed:
#			return ("Probe is not zeroed",
#				"Please ZERO any location of the probe before starting a run")
#
#		lines,paths = self.gcode.prepare2Run()
#		if not lines:
#			return ("Empty gcode", "Not gcode file was loaded")
#
#		# reset colors
##		for ij in paths:
##			if ij:
##				self.canvas.itemconfig(
##					self.gcode[ij[0]].path(ij[1]),
##					width=1,
##					fill=CNCCanvas.ENABLE_COLOR)
#
#		self.initRun()
#		# the buffer of the machine should be empty?
#		self._runLines = len(lines)
#		#self._runLines = 0
#		#del self._runLineMap[:]
#		#lineno = 0
#		#for line in lines:
#		#	#print "***",lineno,line
#		#	if line is not None:
#		#		self._runLines += 1
#		#		self._runLineMap.append(lineno)
#		#		if line and line[0]!=' ': lineno += 1	# ignore expanded lines
#		#	else:
#		#		lineno += 1			# count commented lines
#
#		self.canvas.clearSelection()
#		self._gcount  = 0
#		self._selectI = 0	# last selection pointer in items
#		self._paths   = paths	# drawing paths for canvas
#		self.progress.setLimits(0, self._runLines)
#
#		self.running = True
#		for line in lines:
#			if line is not None:
#				if isinstance(line,str):
#					self.queue.put(line+"\n")
#				else:
#					self.queue.put(line)
#
	#----------------------------------------------------------------------
	# Called when run is finished
	#----------------------------------------------------------------------
	def runEnded(self):
		self._runLines = 0
		self._quit     = 0
		self._pause    = False
		self.running   = False
		self.enable()

	#----------------------------------------------------------------------
	# Stop the current run
	#----------------------------------------------------------------------
	def stopRun(self):
		self.feedHold()
		self._stop = True
		time.sleep(1)
		self.softReset()
		time.sleep(1)
		self.unlock()
		self.runEnded()


	#----------------------------------------------------------------------
	# thread performing I/O on serial line
	#----------------------------------------------------------------------
	def serialIO(self):
		from CNC import WAIT
		cline = []
		tosend = None
		self.wait = False
		tr = tg = time.time()
		while self.thread:
			t = time.time()
			if t-tr > SERIAL_POLL:
				# Send one ?
				self.serial.write("?")
				tr = t

			if tosend is None and not self.wait and not self._pause and self.queue.qsize()>0:
				try:
					tosend = self.queue.get_nowait()
					if isinstance(tosend, int):
						if tosend == WAIT: # wait to empty the grbl buffer
							self.wait = True
						tosend = None
					elif not isinstance(tosend, str):
						try:
							tosend = self.gcode.evaluate(tosend)
#							if isinstance(tosend, list):
#								cline.append(len(tosend[0]))
#								self.log.put((True,tosend[0]))
							if isinstance(tosend,str):
								tosend += "\n"
							else:
								# Count commands as well
								self._gcount += 1
						except:
							self.log.put((True,sys.exc_info()[1]))
							tosend = None
					if tosend is not None:
						cline.append(len(tosend))
						self.log.put((True,tosend))
				except Empty:
					break

			if tosend is None or self.serial.inWaiting():
				line = self.serial.readline().strip()
				if line:
					if line[0]=="<":
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
							self._posUpdate = True
						else:
							self.log.put((False, line+"\n"))

					elif line[0]=="[":
						self.log.put((False, line+"\n"))
						pat = POSPAT.match(line)
						if pat:
							if pat.group(1) == "PRB":
								CNC.vars["prbx"] = float(pat.group(2))
								CNC.vars["prby"] = float(pat.group(3))
								CNC.vars["prbz"] = float(pat.group(4))
								if self.running:
									self.gcode.probe.add(
										 float(pat.group(2))
											+CNC.vars["wx"]
											-CNC.vars["mx"],
										 float(pat.group(3))
											+CNC.vars["wy"]
											-CNC.vars["my"],
										 float(pat.group(4))
											+CNC.vars["wz"]
											-CNC.vars["mz"])
								self._probeUpdate = True
							else:
								self._wcsUpdate = True
							CNC.vars[pat.group(1)] = \
								[float(pat.group(2)),
								 float(pat.group(3)),
								 float(pat.group(4))]
						else:
							pat = TLOPAT.match(line)
							if pat:
								CNC.vars[pat.group(1)] = pat.group(2)
							else:
								CNC.vars["G"] = line[1:-1].split()
								self._gUpdate = True

					else:
						self.log.put((False, line+"\n"))
						uline = line.upper()
						if uline.find("ERROR")>=0 or uline.find("ALARM")>=0:
							self._gcount += 1
							if cline: del cline[0]
							if not self._alarm:
								self._posUpdate = True
							self._alarm = True
							CNC.vars["state"] = line
							if self.running:
								self.emptyQueue()
								# Dangerous calling state of Tk if not reentrant
								self.runEnded()
								tosend = None
								del cline[:]

						elif line.find("ok")>=0:
							self._gcount += 1
							if cline: del cline[0]

						if self.wait and not cline:
							# buffer is empty go one
							self._gcount += 1
							self.wait = False
			# Message came to stop
			if self._stop:
				self.emptyQueue()
				tosend = None
				del cline[:]
				self._stop = False

			if tosend is not None and sum(cline) <= RX_BUFFER_SIZE-2:
#				if isinstance(tosend, list):
#					self.serial.write(str(tosend.pop(0)))
#					if not tosend: tosend = None
				if isinstance(tosend, unicode):
					tosend = tosend.encode("ascii","replace")

				if CNC.vars["override"] != 100:
					pat = FEEDPAT.match(tosend)
					if pat is not None:
						try:
							tosend = "%sf%g%s"%(pat.group(0),
									float(pat.group(1))*CNC.vars["override"]/100.0,
									pat.group(2))
						except:
							pass

				self.serial.write(str(tosend))
				tosend = None

				if not self.running and t-tg > G_POLL:
					self.serial.write("$G\n")
					tg = t

	#----------------------------------------------------------------------
	def get(self, section, item):
		return Utils.config.get(section, item)

	#----------------------------------------------------------------------
	def set(self, section, item, value):
		return Utils.config.set(section, item, value)
