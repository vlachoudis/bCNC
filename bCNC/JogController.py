import threading
import sys
import time
class JogController:
	last: float
	mutex: threading.Lock
	TIMEOUT: float = 0.1
	def __init__(self, tkBind, keys, terminateJogFunction):
		self.bind = tkBind
		self.keys = keys
		self.jogStopFunc = terminateJogFunction
		self.mutex = threading.Lock()
		self.last = 0
		

		self.symbs = []
		for (keysim,event) in keys.items():
			self.bind.bind(keysim,event)
			self.symbs += [keysim]

		self.bind.bind("<KeyPress>", self.press)
		self.bind.bind("<KeyRelease>",self.release)

		thread = threading.Thread(target=self.releaseKey)
		thread.start()


	def releaseKey(self):
		while(1):
			self.mutex.acquire(blocking=True)
			time.sleep(self.TIMEOUT*2)
			print("Test last={} actual={}".format(self.last,time.time()))
			if time.time()-self.last >= self.TIMEOUT:
				print("Stop Jog")
				sys.stdout.flush()
				self.jogStopFunc()



	def press(self,event):
		print(event)
	def release(self,event):
		st = str(event.keysym)
		found = False
		for s in self.symbs:
			filtered = s.replace('<','').replace('>','')
			if filtered in st:
				found = True
				break
		if not found:
			return 
		print(event)

		self.last = time.time()
		if self.mutex.locked():
			self.mutex.release()

