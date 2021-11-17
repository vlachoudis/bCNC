from CNCRibbon    import Page
#==============================================================================
# BJM Repeat Commands Class 
#==============================================================================
class RepeatEngine:
	TYPE_NONE = 0
	TYPE_M47 = 1
	TYPE_M48 = 2
	TIMEOUT_TO_REPEAT = 0
	repeatType: int
	m48MaxTimes: int
	m48CurrentTime: int
	app: any
	fromSD: bool
	def __init__(self):
		self.cleanState()

	def isRepeatable(self):
		if self.repeatType == self.TYPE_M47:
			return True
		self.updateState()
		if self.repeatType == self.TYPE_M48 and self.m48MaxTimes - self.m48CurrentTime > 0:
			return True
		return False

	def countRepetition(self):
		self.m48CurrentTime += 1
		self.updateState()
	
	def updateState(self):
		try:
			self.m48MaxTimes = Page.groups["Run"].getM48Max()
			Page.groups["Run"].setM48RepeatNumber(self.m48CurrentTime)
		except:
			pass
	
	def cleanState(self):
		self.m48CurrentTime = 0
		self.m48MaxTimes = 0
		self.repeatType = self.TYPE_NONE
		self.fromSD = False
		self.updateState()
		

	def isRepeatCommand(self, line:str):
		lin = line[:]
		lin = lin.upper().replace(' ','')
		if lin.find('M47')!=-1:
			self.repeatType = self.TYPE_M47
			return True and not self.fromSD
		if lin.find('M48')!=-1:
			self.repeatType = self.TYPE_M48
			return True and not self.fromSD
		return 0
