# -*- coding: latin1 -*-
# $Id: CNCPendant.py,v 1.3 2014/10/15 15:04:48 bnv Exp bnv $
#
# Author:	Vasilis.Vlachoudis@cern.ch
# Date:	06-Oct-2014

__author__ = "Vasilis Vlachoudis"
__email__  = "Vasilis.Vlachoudis@cern.ch"

import os
import sys
#import cgi
import json
import threading
import urllib
import re

try:
	import urlparse
except ImportError:
	import urllib.parse as urlparse

try:
	import BaseHTTPServer as HTTPServer
except ImportError:
	import http.server as HTTPServer

HOSTNAME = "localhost"
port = 8080

httpd = None
prgpath = os.path.abspath(os.path.dirname(sys.argv[0]))

#==============================================================================
# Simple Pendant controller for CNC
#==============================================================================
class Pendant(HTTPServer.BaseHTTPRequestHandler):
	#----------------------------------------------------------------------
	def log_message(self, fmt, *args):
		# Only requests to the main page log them, all other ignore
		if args[0].startswith("GET / "):
			HTTPServer.BaseHTTPRequestHandler.log_message(self, fmt, *args)

	#----------------------------------------------------------------------
	def do_HEAD(self, rc=200, content="text/html"):
		self.send_response(rc)
		self.send_header("Content-type", content)
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

		#print self.path,type(self.path)
		#print page
		#print arg

		if page == "/send":
			if arg is None: return
			for key,value in arg.items():
				if key=="gcode":
					for line in value.split('\n'):
						httpd.app.queue.put(line+"\n")
				elif key=="cmd":
					httpd.app.pendant.put(urllib.unquote(value))
			#send empty response so browser does not generate errors
			self.do_HEAD(200, "text/text")
			self.wfile.write("")

		elif page == "/state":
			self.do_HEAD(200, "text/text")
			self.wfile.write(json.dumps(httpd.app._pos))

		elif page == "/config":
			self.do_HEAD(200, "text/text")
			snd = {}
			snd["rpmmax"] = httpd.app.get("CNC","spindlemax")
			self.wfile.write(json.dumps(snd))

		elif page == "/icon":
			if arg is None: return
			self.do_HEAD(200, "image/gif")

			filename = os.path.join(
					os.path.abspath(
						os.path.dirname(sys.argv[0])),
					"icons",
					arg["name"]+".gif")
			try:
				f = open(filename,"rb")
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
		global prgpath

		#handle certain filetypes
		filetype = page.rpartition('.')[2]
		if filetype == "css": self.do_HEAD(content="text/css")
		elif filetype == "js": self.do_HEAD(content="text/javascript")
		else: self.do_HEAD()

		if page == "": page = "index.html"
		try:
			f = open(os.path.join(prgpath,page),"r")
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
""")

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
	return True

if __name__ == '__main__':
	start()
