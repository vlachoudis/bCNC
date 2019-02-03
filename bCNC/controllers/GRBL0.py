# GRBL <=0.9 motion controller plugin

from __future__ import absolute_import
from __future__ import print_function
from _GenericGRBL import _GenericGRBL
from _GenericController import STATUSPAT, POSPAT, TLOPAT, DOLLARPAT, SPLITPAT, VARPAT
from CNC import CNC
import time


class Controller(_GenericGRBL):
	def __init__(self, master):
		self.gcode_case = 0
		self.has_override = False
		self.master = master
		#print("grbl0 loaded")

	def parseBracketAngle(self, line, cline):
		self.master.sio_status = False
		pat = STATUSPAT.match(line)
		if pat:
			if not self.master._alarm:
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
			self.master._posUpdate = True
			if pat.group(1)[:4] != "Hold" and self.master._msg:
				self.master._msg = None

			# Machine is Idle buffer is empty
			# stop waiting and go on
			#print "<<< WAIT=",wait,sline,pat.group(1),sum(cline)
			#print ">>>", line
			if self.master.sio_wait and not cline and pat.group(1) not in ("Run", "Jog", "Hold"):
				#print ">>>",line
				self.master.sio_wait = False
				#print "<<< NO MORE WAIT"
				self.master._gcount += 1
			else:
				self.master.log.put((self.master.MSG_RECEIVE, line))

	def parseBracketSquare(self, line):
		pat = POSPAT.match(line)
		if pat:
			if pat.group(1) == "PRB":
				CNC.vars["prbx"] = float(pat.group(2))
				CNC.vars["prby"] = float(pat.group(3))
				CNC.vars["prbz"] = float(pat.group(4))
				#if self.running:
				self.master.gcode.probe.add(
					 CNC.vars["prbx"]
					+CNC.vars["wx"]
					-CNC.vars["mx"],
					 CNC.vars["prby"]
					+CNC.vars["wy"]
					-CNC.vars["my"],
					 CNC.vars["prbz"]
					+CNC.vars["wz"]
					-CNC.vars["mz"])
				self.master._probeUpdate = True
			CNC.vars[pat.group(1)] = \
				[float(pat.group(2)),
				 float(pat.group(3)),
				 float(pat.group(4))]
		else:
			pat = TLOPAT.match(line)
			if pat:
				CNC.vars[pat.group(1)] = pat.group(2)
				self.master._probeUpdate = True
			elif DOLLARPAT.match(line):
				CNC.vars["G"] = line[1:-1].split()
				CNC.updateG()
				self.master._gUpdate = True
