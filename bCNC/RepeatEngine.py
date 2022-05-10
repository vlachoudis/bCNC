from CNCRibbon    import Page
#==============================================================================
# BJM Repeat Commands Class 
#==============================================================================
class RepeatEngine:
	TYPE_NONE = 0
	TYPE_M47 = 1
	TYPE_M48 = 2
	TIMEOUT_TO_REPEAT = 0.5
	repeatType: int
	m48MaxTimes: int
	m48CurrentTime: int
	app: any
	fromSD: bool
	def __init__(self, CNCRef):
		self.cleanState()
		self.CNCRef = CNCRef

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
			if not self.fromSD:
				self.m48MaxTimes = self.CNCRef.vars["M30CounterLimit"]
			Page.groups["Run"].setM30Counter(self.m48CurrentTime)
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
			try:
				self.m48MaxTimes = int(lin[lin.find('P')+1:])
				Page.groups["Run"].setM30CounterLimit(self.m48MaxTimes)
				self.CNCRef.vars["M30CounterLimit"] = self.m48MaxTimes
			except:
				pass
			return True and not self.fromSD
		return 0
