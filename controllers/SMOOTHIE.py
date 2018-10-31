from Sender import ControllerGeneric
import time

class Controller(ControllerGeneric):
	def __init__(self, master):
		self.master = master
		print("smoothie loaded")

	def executeCommand(self, oline, line, cmd):
		if line[0] in ( "help", "version", "mem", "ls",
				"cd", "pwd", "cat", "rm", "mv",
				"remount", "play", "progress", "abort",
				"reset", "dfu", "break", "config-get",
				"config-set", "get", "set_temp", "get",
				"get", "net", "load", "save", "upload",
				"calc_thermistor", "thermistors", "md5sum"):
			self.master.serial.write(oline+"\n")
			return True
		return False

	def hardResetPre(self):
		self.master.serial.write(b"reset\n")

	def hardResetAfter(self):
		time.sleep(6)

	def viewSettings(self):
		pass

	def viewBuild(self):
		self.master.serial.write(b"version\n")
		self.master.sendGCode("$I")

	def viewStartup(self):
		pass

	def checkGcode(self):
		pass

	def grblHelp(self):
		self.master.serial.write(b"help\n")

	def grblRestoreSettings(self):
		pass

	def grblRestoreWCS(self):
		pass

	def grblRestoreAll(self):
		pass

	def purgeController(self):
		pass
