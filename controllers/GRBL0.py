from Sender import ControllerGeneric
import time

class Controller(ControllerGeneric):
	def __init__(self, master):
		self.master = master
		print("grbl0 loaded")

	def executeCommand(self, oline, line, cmd):
		return False

	def hardResetPre(self):
		pass

	def hardResetAfter(self):
		pass

	def viewSettings(self):
		self.master.sendGCode("$$")

	def viewBuild(self):
		self.master.sendGCode("$I")

	def viewStartup(self):
		self.master.sendGCode("$N")

	def checkGcode(self):
		self.master.sendGCode("$C")

	def grblHelp(self):
		self.master.sendGCode("$")

	def grblRestoreSettings(self):
		self.master.sendGCode("$RST=$")

	def grblRestoreWCS(self):
		self.master.sendGCode("$RST=#")

	def grblRestoreAll(self):
		self.master.sendGCode("$RST=#")

	def purgeController(self):
		time.sleep(1)
		self.master.unlock(False)
