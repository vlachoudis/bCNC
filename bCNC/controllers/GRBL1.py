# GRBL 1.0+ motion controller plugin

from __future__ import absolute_import
from __future__ import print_function
from _GenericGRBL import _GenericGRBL
from _GenericController import STATUSPAT, POSPAT, TLOPAT, DOLLARPAT, SPLITPAT, VARPAT
from CNC import CNC
import time

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


class Controller(_GenericGRBL):
	def __init__(self, master):
		self.gcode_case = 0
		self.has_override = True
		self.master = master
		#print("grbl1 loaded")

	def jog(self, dir):
		self.master.sendGCode("$J=G91 %s F100000"%(dir))

	def overrideSet(self):
		CNC.vars["_OvChanged"] = False	# Temporary
		# Check feed
		diff = CNC.vars["_OvFeed"] - CNC.vars["OvFeed"]
		if diff==0:
			pass
		elif CNC.vars["_OvFeed"] == 100:
			self.master.serial.write(OV_FEED_100)
		elif diff >= 10:
			self.master.serial.write(OV_FEED_i10)
			CNC.vars["_OvChanged"] = diff>10
		elif diff <= -10:
			self.master.serial.write(OV_FEED_d10)
			CNC.vars["_OvChanged"] = diff<-10
		elif diff >= 1:
			self.master.serial.write(OV_FEED_i1)
			CNC.vars["_OvChanged"] = diff>1
		elif diff <= -1:
			self.master.serial.write(OV_FEED_d1)
			CNC.vars["_OvChanged"] = diff<-1
		# Check rapid
		target  = CNC.vars["_OvRapid"]
		current = CNC.vars["OvRapid"]
		if target == current:
			pass
		elif target == 100:
			self.master.serial.write(OV_RAPID_100)
		elif target == 75:
			self.master.serial.write(OV_RAPID_50)	# FIXME: GRBL protocol does not specify 75% override command at all
		elif target == 50:
			self.master.serial.write(OV_RAPID_50)
		elif target == 25:
			self.master.serial.write(OV_RAPID_25)
		# Check Spindle
		diff = CNC.vars["_OvSpindle"] - CNC.vars["OvSpindle"]
		if diff==0:
			pass
		elif CNC.vars["_OvSpindle"] == 100:
			self.master.serial.write(OV_SPINDLE_100)
		elif diff >= 10:
			self.master.serial.write(OV_SPINDLE_i10)
			CNC.vars["_OvChanged"] = diff>10
		elif diff <= -10:
			self.master.serial.write(OV_SPINDLE_d10)
			CNC.vars["_OvChanged"] = diff<-10
		elif diff >= 1:
			self.master.serial.write(OV_SPINDLE_i1)
			CNC.vars["_OvChanged"] = diff>1
		elif diff <= -1:
			self.master.serial.write(OV_SPINDLE_d1)
			CNC.vars["_OvChanged"] = diff<-1


	def parseBracketAngle(self, line, cline):
		self.master.sio_status = False
		fields = line[1:-1].split("|")
		CNC.vars["pins"] = ""


		#Report if state has changed
		if CNC.vars["state"] != fields[0] or self.master.runningPrev != self.master.running:
			self.master.controllerStateChange(fields[0])
		self.master.runningPrev = self.master.running
		CNC.vars["state"] = fields[0]

		for field in fields[1:]:
			word = SPLITPAT.split(field)
			if word[0] == "MPos":
				try:
					CNC.vars["mx"] = float(word[1])
					CNC.vars["my"] = float(word[2])
					CNC.vars["mz"] = float(word[3])
					CNC.vars["wx"] = round(CNC.vars["mx"]-CNC.vars["wcox"], CNC.digits)
					CNC.vars["wy"] = round(CNC.vars["my"]-CNC.vars["wcoy"], CNC.digits)
					CNC.vars["wz"] = round(CNC.vars["mz"]-CNC.vars["wcoz"], CNC.digits)
					self.master._posUpdate = True
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "F":
				try:
					CNC.vars["curfeed"] = float(word[1])
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "FS":
				try:
					CNC.vars["curfeed"]    = float(word[1])
					CNC.vars["curspindle"] = float(word[2])
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "Bf":
				try:
					CNC.vars["planner"] = int(word[1])
					CNC.vars["rxbytes"] = int(word[2])
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "Ov":
				try:
					CNC.vars["OvFeed"]    = int(word[1])
					CNC.vars["OvRapid"]   = int(word[2])
					CNC.vars["OvSpindle"] = int(word[3])
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "WCO":
				try:
					CNC.vars["wcox"] = float(word[1])
					CNC.vars["wcoy"] = float(word[2])
					CNC.vars["wcoz"] = float(word[3])
				except (ValueError,IndexError):
					CNC.vars["state"] = "Garbage receive %s: %s"%(word[0],line)
					self.master.log.put((self.master.MSG_RECEIVE, CNC.vars["state"]))
					break
			elif word[0] == "Pn":
				try:
					CNC.vars["pins"] = word[1]
					if 'S' in word[1]:
						if CNC.vars["state"] == 'Idle' and not self.master.running:
							print("Stream requested by CYCLE START machine button")
							self.master.event_generate("<<Run>>", when = 'tail')
						else:
							print("Ignoring machine stream request, because of state: ", CNC.vars["state"], self.master.running)
				except (ValueError,IndexError):
					break


		# Machine is Idle buffer is empty stop waiting and go on
		if self.master.sio_wait and not cline and fields[0] not in ("Run", "Jog", "Hold"):
			#if not self.master.running: self.master.jobDone() #This is not a good idea, it purges the controller while waiting for toolchange. see #1061
			self.master.sio_wait = False
			self.master._gcount += 1

	def parseBracketSquare(self, line):
		word = SPLITPAT.split(line[1:-1])
		#print word
		if word[0] == "PRB":
			CNC.vars["prbx"] = float(word[1])
			CNC.vars["prby"] = float(word[2])
			CNC.vars["prbz"] = float(word[3])
			#if self.running:
			self.master.gcode.probe.add(
				 CNC.vars["prbx"]-CNC.vars["wcox"],
				 CNC.vars["prby"]-CNC.vars["wcoy"],
				 CNC.vars["prbz"]-CNC.vars["wcoz"])
			self.master._probeUpdate = True
			CNC.vars[word[0]] = word[1:]
		if word[0] == "G92":
			CNC.vars["G92X"] = float(word[1])
			CNC.vars["G92Y"] = float(word[2])
			CNC.vars["G92Z"] = float(word[3])
			CNC.vars[word[0]] = word[1:]
			self.master._gUpdate = True
		if word[0] == "G28":
			CNC.vars["G28X"] = float(word[1])
			CNC.vars["G28Y"] = float(word[2])
			CNC.vars["G28Z"] = float(word[3])
			CNC.vars[word[0]] = word[1:]
			self.master._gUpdate = True
		if word[0] == "G30":
			CNC.vars["G30X"] = float(word[1])
			CNC.vars["G30Y"] = float(word[2])
			CNC.vars["G30Z"] = float(word[3])
			CNC.vars[word[0]] = word[1:]
			self.master._gUpdate = True
		elif word[0] == "GC":
			CNC.vars["G"] = word[1].split()
			CNC.updateG()
			self.master._gUpdate = True
		elif word[0] == "TLO":
			CNC.vars[word[0]] = word[1]
			self.master._probeUpdate = True
			self.master._gUpdate = True
		else:
			CNC.vars[word[0]] = word[1:]
