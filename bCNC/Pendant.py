# $Id$
#
# Author: vvlachoudis@gmail.com
# Date: 24-Aug-2014

import json
import os
import re
import tempfile
import threading
import io

import Camera
from CNC import CNC
from Utils import prgpath

import urllib.parse as urlparse
import http.server as httpserver

try:
    from PIL import Image
except ImportError:
    Image = None

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"

HOSTNAME = "localhost"
port = 8080

httpd = None
webpath = f"{prgpath}/pendant"
iconpath = f"{prgpath}/icons/"


# =============================================================================
# Simple Pendant controller for CNC
# =============================================================================
class Pendant(httpserver.BaseHTTPRequestHandler):
    camera = None

    # ----------------------------------------------------------------------
    def get_file_size(fh):
	# Returns file length. 
	# This is workaround for os.path.getsize() function - IDK why, 
	# but it returns wrong value.
        cur_pos=fh.tell()
        fh.seek(0,2)
        content_length=fh.tell()
        fh.seek(cur_pos,0)
        return content_length

    # ----------------------------------------------------------------------
    def log_message(self, fmt, *args):
        # Only requests to the main page log them, all other ignore
        # 2025-01-04 str(args[0]) added to handle enum in case of error message
        #   (<HTTPStatus.REQUEST_URI_TOO_LONG: 414>, 'Request-URI Too Long')
        if str(args[0]).startswith("GET / ") or str(args[0]).startswith("GET /send"):
            args = list(args)
            args[0] = self.address_string() + '" : "' + args[0]
            httpserver.BaseHTTPRequestHandler.log_message(self, fmt, *args)

    # ----------------------------------------------------------------------
    def do_HEAD(self, rc=200, content="text/html", cl=0, headers_extra=[]):
        self.send_response(rc)
        self.send_header("Content-type", content)
        if cl != 0:
            self.send_header("Content-length", cl)
        for header in headers_extra:
            self.send_header(*header)
        self.end_headers()

    # ----------------------------------------------------------------------
    def do_GET(self):
        """Respond to a GET request."""
        if "?" in self.path:
            page, arg = self.path.split("?", 1)
            arg = dict(urlparse.parse_qsl(arg))
        else:
            page = self.path
            arg = None

        if page == "/send":
            if arg is None:
                return
            for key, value in arg.items():
                if key == "gcode":
                    for line in value.split("\n"):
                        httpd.app.queue.put(line + "\n")
                elif key == "cmd":
                    httpd.app.pendant.put(urlparse.unquote(value))
            # send empty response so browser does not generate errors
            self.do_HEAD(200, "text/text", cl=len(""))
            self.wfile.write(b"")

        elif page == "/state":
            tmp = {}
            for name in [
                "controller",
                "state",
                "pins",
                "color",
                "msg",
                "wx",
                "wy",
                "wz",
                "wa",
                "wb",
                "wc",
                "mx",
                "my",
                "mz",
                "ma",
                "mb",
                "mc",
                "G",
                "OvFeed",
                "OvRapid",
                "OvSpindle",
            ]:
                tmp[name] = CNC.vars[name]
            contentToSend = json.dumps(tmp)
            self.do_HEAD(200, content="text/text", cl=len(contentToSend))
            self.wfile.write(contentToSend.encode())

        elif page == "/config":
            snd = {}
            snd["rpmmax"] = httpd.app.get("CNC", "spindlemax")
            contentToSend = json.dumps(snd)
            self.do_HEAD(200, content="text/text", cl=len(contentToSend))
            self.wfile.write(contentToSend.encode())

        elif page == "/icon":
            if arg is None:
                return
            filename = os.path.join(iconpath, arg["name"] + ".gif")
            try:
                f = open(filename,"rb")
                self.do_HEAD(200, content="image/gif", cl=self.get_file_size(f))
                self.wfile.write(f.read())
                f.close()
            except Exception:
                pass

        elif page == "/canvas":
            if not Image:
                return
            ps = httpd.app.canvas.postscript(colormode="color")
            try:
                with io.BytesIO() as out:
                    Image.open(io.BytesIO(ps.encode('utf-8'))).save(out, "gif")
                    self.do_HEAD(200, content="image/gif", cl=out.tell())
                    out.seek(0)
                    self.wfile.write(out.read())
            except Exception:
                filename = os.path.join(iconpath, "warn.gif")
                try:
                    f = open(filename,"rb")
                    self.do_HEAD(200, content="image/gif", cl=self.get_file_size(f))
                    self.wfile.write(f.read())
                    f.close()
                except Exception:
                    pass

        elif page == "/camera":
            if not Camera.hasOpenCV():
                return
            if Pendant.camera is None:
                Pendant.camera = Camera.Camera("webcam")
                if not Pendant.camera.start():
                    Pendant.camera = None

            if Pendant.camera.read():
                try:
                    img = Pendant.camera.jpg()
                    self.do_HEAD(200, content="image/jpeg", cl=len(img))
                    self.wfile.write(img)
                except Exception:
                    pass

        elif page == "/text.ngc":
            #Provide loaded g-code via web interface, so we can use nice webgl preview in the future
            self.do_HEAD(200, content="text/text", headers_extra=[['Access-Control-Allow-Origin', '*']])
            for block in httpd.app.gcode.blocks:
                block.write_encoded(f=self.wfile)

        else:
            self.mainPage(page[1:])

    # ----------------------------------------------------------------------
    def deal_post_data(self):
        str_ok = True
        b_tmp = False
        try:
            boundary = self.headers.plisttext.split("=")[1]
        except Exception:
            str_ok=False
            boundary=self.headers.get_boundary()
            pass
        remainbytes = int(self.headers["content-length"])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if (str_ok):
            b_tmp = not boundary in line
        else:
            b_tmp = not boundary.encode() in line
        if b_tmp:
                return (False, "Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        if (str_ok):
            fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line)
        else:
            fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"'.encode(), line)
        if not fn:
            return (False, "Can't find out file name...")
        path = os.path.expanduser("~")
        path = os.path.join(path, "bCNCUploads")
        if not os.path.exists(path):
            os.makedirs(path)
        if (str_ok):
            fn = os.path.join(path, fn[0])
        else:
            fn = os.path.join(path.encode(), fn[0])
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, "wb")
        except OSError:
            return (
                False,
                "Can't create file to write, do you have permission to write?",
            )

        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if (str_ok):
                b_tmp= boundary in line
            else:
                b_tmp= boundary.encode() in line
            if b_tmp:
                preline = preline[0:-1]
                if preline.endswith("\r".encode()):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                if (str_ok):
                    return (True, f"{fn}")
                else:
                    return (True, fn)
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpected Ends of data.")

    # ----------------------------------------------------------------------
    def do_POST(self):
        result, fMsg = self.deal_post_data()
        if result:
            httpd.app._pendantFileUploaded = fMsg
        # send empty response so browser does not generate errors
        self.do_HEAD(200, "text/text")

    # ---------------------------------------------------------------------
    def mainPage(self, page):
        global webpath

        # handle certain filetypes
        filetype = page.rpartition(".")[2]
        if filetype == "css":
            self.do_HEAD(content="text/css")
        elif filetype == "js":
            self.do_HEAD(content="application/x-javascript")
        elif filetype == "json":
            self.do_HEAD(content="application/json")
        elif filetype == "jpg" or filetype == "jpeg":
            self.do_HEAD(content="image/jpeg")
        elif filetype == "gif":
            self.do_HEAD(content="image/gif")
        elif filetype == "png":
            self.do_HEAD(content="image/png")
        elif filetype == "ico":
            self.do_HEAD(content="image/x-icon")
        else:
            self.do_HEAD()

        if page == "":
            page = "index.html"
        try:
            f = open(os.path.join(webpath, page), "rb")
            self.wfile.write(f.read())
            f.close()
        except OSError:
            self.wfile.write(("\n".join([
                u"<!DOCTYPE html>",
                u"<html>",
                u"<head>",
                u"<title>Errortitle</title>",
                u"<meta name=\"viewport\" content=\"width=device-width,"
                u"initial-scale=1, user-scalable=yes\" />",
                u"</head>",
                u"<body>",
                u"Page not found.",
                u"</body>",
                u"</html>"
            ])).encode())


# -----------------------------------------------------------------------------
def _server(app):
    global httpd
    server_class = httpserver.HTTPServer
    try:
        httpd = server_class(("", port), Pendant)
        httpd.app = app
        httpd.serve_forever()
    except Exception:
        httpd = None


# -----------------------------------------------------------------------------
def start(app):
    global httpd

    if httpd is not None:
        return False
    thread = threading.Thread(target=_server, args=(app,))
    thread.start()
    return True


# -----------------------------------------------------------------------------
def stop():
    global httpd
    if httpd is None:
        return False
    httpd.shutdown()
    httpd = None
    if Pendant.camera:
        Pendant.camera.stop()
    return True


if __name__ == "__main__":
    start()

