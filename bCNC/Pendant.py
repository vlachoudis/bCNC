# -*- coding: ascii -*-
# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

from __future__ import absolute_import
from __future__ import print_function
__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import os
import re
import sys
#import cgi
import json
import urllib
import tempfile
import threading

from CNC import CNC
from Utils import prgpath

try:
	import urlparse
except ImportError:
	import urllib.parse as urlparse

try:
	from PIL import Image
except ImportError:
	Image = None

try:
	import BaseHTTPServer as HTTPServer
except ImportError:
	import http.server as HTTPServer

import Camera

HOSTNAME = "localhost"
port     = 8080

httpd    = None
webpath  = "%s/pendant"%(prgpath)
iconpath = "%s/icons/"%(prgpath)


#==============================================================================
# Simple Pendant controller for CNC
#==============================================================================
class Pendant(HTTPServer.BaseHTTPRequestHandler):
	camera = None

	#----------------------------------------------------------------------
	def log_message(self, fmt, *args):
		# Only requests to the main page log them, all other ignore
		if args[0].startswith("GET / ") or args[0].startswith("GET /send"):
			args = list(args)
			args[0] = self.address_string()+'" : "'+args[0]
			HTTPServer.BaseHTTPRequestHandler.log_message(self, fmt, *args)

	#----------------------------------------------------------------------
	def do_HEAD(self, rc=200, content="text/html", cl=0):
		self.send_response(rc)
		self.send_header("Content-type", content)
		if cl != 0:
			self.send_header("Content-length", cl)
		self.end_headers()

	#----------------------------------------------------------------------
	def do_GET(self):
		"""Respond to a GET request."""
		if "?" in self.path:
			page,arg = self.path.split("?",1)
			arg = dict(urlparse.parse_qsl(arg))
		else:
			page = self.path
			arg = None

#		print self.path,type(self.path)
#		print page
#		print arg

		if page == "/send":
			if arg is None: return
			for key,value in arg.items():
				if key=="gcode":
					for line in value.split('\n'):
						httpd.app.queue.put(line+"\n")
				elif key=="cmd":
					httpd.app.pendant.put(urlparse.unquote(value))
			#send empty response so browser does not generate errors
			self.do_HEAD(200, "text/text", cl=len(""))
			self.wfile.write("".encode())

		elif page == "/state":
			tmp = {}
			for name in ["controller", "state", "pins", "color", "msg", "wx", "wy", "wz", "G", "OvFeed", "OvRapid", "OvSpindle"]:
				tmp[name] = CNC.vars[name]
			contentToSend = json.dumps(tmp)
			self.do_HEAD(200, content="text/text", cl=len(contentToSend))
			self.wfile.write(contentToSend.encode())

		elif page == "/config":
			snd = {}
			snd["rpmmax"] = httpd.app.get("CNC","spindlemax")
			contentToSend = json.dumps(snd)
			self.do_HEAD(200, content="text/text", cl=len(contentToSend))
			self.wfile.write(contentToSend.encode())

		elif page == "/icon":
			if arg is None: return
			filename = os.path.join(iconpath, arg["name"]+".gif")
			self.do_HEAD(200, content="image/gif", cl=os.path.getsize(filename))
			try:
				f = open(filename,"rb")
				self.wfile.write(f.read())
				f.close()
			except:
				pass

		elif page == "/canvas":
			if not Image: return
			with tempfile.NamedTemporaryFile(suffix='.ps') as tmp:
				httpd.app.canvas.postscript(
					file=tmp.name,
					colormode='color',
				)
				tmp.flush()
				try:
					with tempfile.NamedTemporaryFile(suffix='.gif') as out:
						Image.open(tmp.name).save(out.name, 'GIF')
						out.flush()
						out.seek(0)
						self.do_HEAD(200, content="image/gif", cl=os.path.getsize(tmp.name))
						self.wfile.write(out.read())
				except:
					filename = os.path.join(iconpath, "warn.gif")
					self.do_HEAD(200, content="image/gif", cl=os.path.getsize(filename))
					try:
						f = open(filename,"rb")
						self.wfile.write(f.read())
						f.close()
					except:
						pass

		elif page == "/camera":
			if not Camera.hasOpenCV(): return
			if Pendant.camera is None:
				Pendant.camera = Camera.Camera("webcam")
				Pendant.camera.start()

			if Pendant.camera.read():
				Pendant.camera.save("camera.jpg")
				#cv.imwrite("camera.jpg",img)
				self.do_HEAD(200, content="image/jpeg", cl=os.path.getsize("camera.jpg"))
				try:
					f = open("camera.jpg","rb")
					self.wfile.write(f.read())
					f.close()
				except:
					pass
		else:
			self.mainPage(page[1:])

	#----------------------------------------------------------------------
	def deal_post_data(self):
		boundary = self.headers.plisttext.split("=")[1]
		remainbytes = int(self.headers['content-length'])
		line = self.rfile.readline()
		remainbytes -= len(line)
		if not boundary in line:
			return (False, "Content NOT begin with boundary")
		line = self.rfile.readline()
		remainbytes -= len(line)
		fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line)
		if not fn:
			return (False, "Can't find out file name...")
		path = os.path.expanduser("~")
		path = os.path.join(path, "bCNCUploads")
		if not os.path.exists(path):
		    os.makedirs(path)
		fn = os.path.join(path, fn[0])
		line = self.rfile.readline()
		remainbytes -= len(line)
		line = self.rfile.readline()
		remainbytes -= len(line)
		try:
			out = open(fn, 'wb')
		except IOError:
			return (False, "Can't create file to write, do you have permission to write?")

		preline = self.rfile.readline()
		remainbytes -= len(preline)
		while remainbytes > 0:
			line = self.rfile.readline()
			remainbytes -= len(line)
			if boundary in line:
				preline = preline[0:-1]
				if preline.endswith('\r'):
					preline = preline[0:-1]
				out.write(preline)
				out.close()
				return (True, "%s" % fn)
			else:
				out.write(preline)
				preline = line
		return (False, "Unexpected Ends of data.")

	#----------------------------------------------------------------------
	def do_POST(self):
		result,fMsg=self.deal_post_data()
		if(result):
			httpd.app._pendantFileUploaded=fMsg
		#send empty response so browser does not generate errors
		self.do_HEAD(200, "text/text")

	# ---------------------------------------------------------------------
	def mainPage(self, page):
		global webpath

		#handle certain filetypes
		filetype = page.rpartition('.')[2]
		if   filetype == "css": self.do_HEAD(content="text/css")
		elif filetype == "js":  self.do_HEAD(content="application/x-javascript")
		elif filetype == "json": self.do_HEAD(content="application/json")
		elif filetype == "jpg" or filetype == "jpeg" : self.do_HEAD(content="image/jpeg")
		elif filetype == "gif": self.do_HEAD(content="image/gif")
		elif filetype == "png": self.do_HEAD(content="image/png")
		elif filetype == "ico": self.do_HEAD(content="image/x-icon")
		else: self.do_HEAD()

		if page == "": page = "index.html"
		try:
			f = open(os.path.join(webpath,page),"rb")
			self.wfile.write(f.read())
			f.close()
		except IOError:
			self.wfile.write("""<!DOCTYPE html>
<html>
<head>
<title>Errortitle</title>
<meta name="viewport" content="width=device-width,initial-scale=1, user-scalable=yes" />
</head>
<body>
Page not found.
</body>
</html>
""".encode())


# -----------------------------------------------------------------------------
def _server(app):
	global httpd
	server_class = HTTPServer.HTTPServer
	try:
		httpd = server_class(('', port), Pendant)
		httpd.app = app
		httpd.serve_forever()
	except:
		httpd = None


# -----------------------------------------------------------------------------
def start(app):
	global httpd

	if httpd is not None: return False
	thread = threading.Thread(target=_server, args=(app,))
	thread.start()
	return True


# -----------------------------------------------------------------------------
def stop():
	global httpd
	if httpd is None: return False
	httpd.shutdown()
	httpd = None
	if Pendant.camera: Pendant.camera.stop()
	return True

if __name__ == '__main__':
	start()
