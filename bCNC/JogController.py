import threading
import sys
import time
class JogController:
	last: float
	mutex: threading.Lock
	TIMEOUT: float = 0.01
	def __init__(self, app, keys):
		self.app = app
		self.keys = keys
		self.mutex = threading.Lock()
		self.last = 0
		self.jogBlockMode = True
		

		self.symbs = []
		for (keysim,event) in keys.items():
			self.app.bind(keysim,event)
			self.symbs += [keysim]

		self.app.bind("<KeyRelease>",self.release)

		self.thread = threading.Thread(target=self.releaseKey)
		self.thread.start()

	def activateBlock(self):
		self.jogBlockMode = True
	def deactivateBlock(self):
		self.jogBlockMode = False

	def releaseKey(self):
		while(1):
			self.mutex.acquire(blocking=True)
			time.sleep(self.TIMEOUT*2)
			if time.time()-self.last >= self.TIMEOUT:
				for _ in range(5):
					self.app.sendHex("85")
					time.sleep(0.01)

	def release(self,event):
		st = int(event.keycode)
		found = False
		for s in self.symbs:
			if s == st:
				found = True
				break
		if not found:
			return 
		self.last = time.time()
		if self.mutex.locked() and self.jogBlockMode and self.app.running==False:
			self.mutex.release()

