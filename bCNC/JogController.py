import threading
import sys
import time
class JogController:
	def __init__(self, app, keys):
		myConfigFile = open("jogConf.txt","r")
		self.mapKeyToCode = {}
		for line in myConfigFile.readlines():
			key,code,sym = line.split(' ')
			sym = sym[:len(sym)-1]
			self.mapKeyToCode[key] = int(code),sym
		myConfigFile.close()

		self.app = app
		self.keys = keys
		
		for (key,(code,sym)) in self.mapKeyToCode.items():
			print("Bind {},{} to {}".format(code,sym,key))
			self.app.bind("<"+str(sym)+">",self.keys[key])

