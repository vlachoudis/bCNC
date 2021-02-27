#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @DodoLaSaumure Pierre KLein
# Date: 9 feb 2021


from __future__ import print_function
from __future__ import print_function

from copy import deepcopy
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
import math
import os.path
import re
from struct import unpack
import sys

from CNC import CNC, Block  # ,toPath,importPath,addUndo
from ToolsPage import Plugin
from bmath import Vector
from bpath import EPS, eq, Path, Segment
from Cython.Compiler.TreePath import operations

__author__ = "@DodoLaSaumure  (Pierre Klein)"
#__email__  = ""

__name__ = _("stlSlicer")
__version__ = "0.0.1"

try:
	import Tkinter
	from Tkinter import *
	import tkMessageBox
	from SimpleDialog import *
# 	from Dialog import Dialog
except ImportError:
	import tkinter
	from tkinter import *
	import tkinter.messagebox as tkMessageBox
	from  tkinter.simpledialog import *
# 	from  tkinter.dialog import Dialog
DIALOG_ICON = 'questhead'

HEADER_SIZE =80
COUNT_SIZE =4
class CustomDialog():
	def __init__(self,app,buttons):
		self.app=app
		self.buttons = buttons
	def createDial(self):
		self.box = Toplevel(self.app)
		for button in self.buttons :
			w = Button(self.box,text=button["text"], width=10, command=button["action"], default=ACTIVE)
			w.pack(side=LEFT, padx=5, pady=5)
		self.box.wait_visibility()
		self.box.grab_set()
		self.box.wait_window(self.box)
	def destroy(self):
		self.box.destroy()

class stlImporter():
	def __init__(self,filename,scale):
		self.scale = scale
		self.triangles = []
		f=open(filename,"rb")
		header = f.read(HEADER_SIZE)
		facet_count = unpack("<I",f.read(COUNT_SIZE))[0]
		print(facet_count)
		self.parse(f,facet_count)
		f.close()
		self.maximums = [self.maxx,self.maxy,self.maxz,self.minx,self.miny,self.minz]
		print ("deltax",self.maxx-self.minx)
		print ("deltay",self.maxy-self.miny)
		print ("deltaz",self.maxz-self.minz)
		print ("minx,maxx",self.minx,self.maxx)
		print ("miny,maxy",self.miny,self.maxy)
		print ("minz,maxz",self.minz,self.maxz)
		self.nbTriangles = len(self.triangles)
		print ("nbTriangles",self.nbTriangles)
	def parse(self,f,facet_count):
		self.maxx=self.maxy=self.maxz = -float("inf")
		self.minx=self.miny=self.minz = float("inf")
		for i in range(1, facet_count + 1):
			n1 = unpack("<f", f.read(4))[0]*self.scale
			n2 = unpack("<f", f.read(4))[0]*self.scale
			n3 = unpack("<f", f.read(4))[0]*self.scale
			
			n = [float(n1), float(n2), float(n3)]
			
			v11 = unpack("<f", f.read(4))[0]*self.scale
			v12 = unpack("<f", f.read(4))[0]*self.scale
			v13 = unpack("<f", f.read(4))[0]*self.scale
			self.checkMaxMin(v11,v12,v13)
			p1 = [float(v11), float(v12), float(v13)]
			
			v21 = unpack("<f", f.read(4))[0]*self.scale
			v22 = unpack("<f", f.read(4))[0]*self.scale
			v23 = unpack("<f", f.read(4))[0]*self.scale
			self.checkMaxMin(v21,v22,v23)
			p2 = [float(v21), float(v22), float(v23)]
			
			v31 = unpack("<f", f.read(4))[0]*self.scale
			v32 = unpack("<f", f.read(4))[0]*self.scale
			v33 = unpack("<f", f.read(4))[0]*self.scale
			self.checkMaxMin(v31,v32,v33)
			p3 = [float(v31), float(v32), float(v33)]
			
			f.read(2)
			self.triangles.append(Triangle3D(Point3D(p1),Point3D(p2),Point3D(p3),Vecteur(n)))
			
	def checkMaxMin(self,x,y,z):
		if x > self.maxx : 
			self.maxx = x
		if y > self.maxy :
			self.maxy = y
		if z > self.maxz :
			self.maxz =z 
		if x < self.minx :
			self.minx =x
		if y < self.miny :
			self.miny = y
		if z < self.minz :
			self.minz =z

	def Offset(self,xoff,yoff,zoff):
		self.maxx=self.maxy=self.maxz = -float("inf")
		self.minx=self.miny=self.minz = float("inf")
		for triangle in self.triangles:
			triangle = triangle.offset(xoff,yoff,zoff)
			self.checkMaxMin(triangle.p1.x, triangle.p1.y, triangle.p1.z)
			self.checkMaxMin(triangle.p2.x, triangle.p2.y, triangle.p2.z)
			self.checkMaxMin(triangle.p3.x, triangle.p3.y, triangle.p3.z)
		print ("deltax",self.maxx-self.minx)
		print ("deltay",self.maxy-self.miny)
		print ("deltaz",self.maxz-self.minz)
		print ("minx,maxx",self.minx,self.maxx)
		print ("miny,maxy",self.miny,self.maxy)
		print ("minz,maxz",self.minz,self.maxz)


class SliceRemoval:
	def __init__(self,stlObj,xstart,xend,ystart,yend,zstart,zend,zstep,toolStep,direction,AdditionalCut):
		self.stlObj = stlObj
		self.xstart = xstart
		self.xend = xend
		self.ystart = ystart
		self.yend = yend
		self.zstart = zstart
		self.zend = zend
		self.toolStep = toolStep
		self.direction = direction
		self.zstep = zstep
		self.AdditionalCut = AdditionalCut
# 		self.sliceRemoveX(zstart/2.+zend/2.):
	def sliceRemoveX(self,height):
		y = self.ystart
		z= height
		slices = self.stlObj.getSlices(z)
		while y < self.yend:
# 			operations
			y+self.toolStep
			y=min(y,self.yend)
			
class Vecteur():
	def __init__(self,coordsTuple=None):
		if coordsTuple is None :
			coordsTuple = [0,0,1]
		[self.x,self.y,self.z] = coordsTuple
	def __str__(self):
		return "vect [x=%2f,y=%2f,z=%2f,module=%2f]"%(self.x,self.y,self.z,self.module())
	def module(self):
		return math.sqrt(self.x**2+self.y**2+self.z**2)
	def ProduitScalaire(self,other):
		return self.x*other.x+self.y*other.y+self.z*other.z
	def ProduitVectoriel(self,other):
		PVx = self.y*other.z-self.z*other.y
		PVy=self.z*other.x-self.x*other.z
		PVz = self.x*other.y-self.y*other.x
		return Vecteur([PVx,PVy,PVz])
	def addition(self,other):
		return Vecteur([self.x+other.x,self.y+other.y,self.z+other.z])
	def soustraction(self,other):
		return Vecteur([self.x-other.x,self.y-other.y,self.z-other.z])
	def __sub__(self,other):
		return Vecteur([self.x-other.x,self.y-other.y,self.z-other.z])
	def __add__(self,other):
		return self.addition(other)
	def divise(self,scale):
		return Vecteur([self.x/scale,self.y/scale,self.z/scale])
	def multiply(self,scale):
		scale = float(scale)
		return Vecteur([self.x*scale,self.y*scale,self.z*scale])
	def normalize(self):
		return self.divise(self.module())
	def isNull(self):
		if self.x == 0 and self.y ==0 and self.z==0 :
			return True
		else :
			return False
	def rotate (self,norm,alpha):#retourne rotation de self autour de norm, de alpha degres
		#https://fr.wikipedia.org/wiki/Rotation_vectorielle
		alpha = alpha * math.pi/180.0
		v1 = self.multiply(math.cos(alpha))
		v2 =norm.multiply(self.ProduitScalaire(norm)*(1.0-math.cos(alpha)))
		v3 = norm.ProduitVectoriel(self).multiply(math.sin(alpha))
		rotated = v1.addition(v2).addition(v3)
		return rotated
class Point2D():
	def __init__(self,coordsTuple):
		[self.x,self.y]=coordsTuple
	def __str__(self):
		return "Point2D [x=%2f,y=%2f]"%(self.x,self.y)
	def translate(self,translation):
		x= self.x+translation[0]
		y =self.y+translation[1]
		return Point2D([x,y])
	def scale(self,scalexy):
		x = self.x*scalexy[0]
		y = self.y*scalexy[1]
		return Point2D([x,y])
	def isEqual(self,other):
		if not isinstance(other,Point2D):
			return False
		if (self.x - other.x)**2 + (self.y - other.y)**2 < 0.01 :
			return True
		return False
	def dist(self,x,y):
		return math.sqrt((self.x-x)**2+(self.y-y)**2)


# class Line2D():
#	 def __init__(self,p1=None,p2=None):
#		 self.p1 = p1 if p1 is not None and isinstance(p1, Point2D) else Point2D()
#		 self.p2 = p2 if p2 is not None and isinstance(p2,Point2D) else Point2D()
#		 self.lines2d = [self]
#	 def __str__(self):
#		 result = "Line2D : %s %s"%(self.p1,self.p2)
#		 return result
#	 def isEqual(self,other):
#		 if not isinstance(other,Line2D):
#			 return False
#		 return self.p1.isEqual(other.p1) and self.p2.isEqual(other.p2)
#	 def dist(self,x,y):
#		 x1 = self.p1.x
#		 x2 = self.p2.x
#		 y1 = self.p1.y
#		 y2 = self.p2.y
#		 xM = float(x)
#		 yM = float(y)
#		 matrice = Matrix([
#						   [x1-x2,y1-y2,0.],
#						   [1.,0.,x1-x2],
#						   [0.,1.,y1-y2]
#						   ])
#		 res = Matrix(
#					  [[xM*(x1-x2)+yM*(y1-y2)],
#					  [x1],
#					  [y1]]
#					  )
#		 X = matrice.invert()*res
#		 xH = X.M[0][0]
#		 yH =X.M[1][0]
#		 k = X.M[2][0]
#		 pH = Point2D([xH,yH])
#		 if k> 0 and k<1 :
#			 dist = pH.dist(xM, yM)
#		 elif k<0 :
#			 dist = self.p1.dist(xM, yM)
#		 else :
#			 dist = self.p2.dist(xM,yM)
#		 return dist

class Point3D():
	def __init__(self,coordsTuple=None):
		if coordsTuple is None : 
			coordsTuple = [0,0,0]
		[self.x,self.y,self.z]=coordsTuple
	def __str__(self):
		return "Point3D [x=%2f,y=%2f,z=%2f]"%(self.x,self.y,self.z)
	def Vect(self,P2):
		return Vecteur([P2.x-self.x,P2.y-self.y,P2.z-self.z])
	def scale(self,scale):
		return Point3D([self.x*scale,self.y*scale,self.z*scale])
	def __add__(self,other):
		return Point3D([self.x+other.x,self.y+other.y,self.z+other.z])
	def __sub__(self,other):
		return Point3D([self.x-other.x,self.y-other.y,self.z-other.z])
	def addVect(self,vect):
		return Point3D([self.x+vect.x,self.y+vect.y,self.z+vect.z])
	def rotate(self,center,axis,angle):
		p2 = self.sub(center)
		origin = Point3D([0.,0.,0.])
		toRotate = origin.Vect(p2)
		rotatedVect =toRotate.rotate(axis.normalize(), angle)
		rotatedPoint = Point3D([rotatedVect.x,rotatedVect.y,rotatedVect.z])
		result = rotatedPoint.add(center)
		return result

class Triangle3D():
	def __init__(self,Point1,Point2,Point3,Normale):
		self.p1 = Point1
		self.p2 = Point2
		self.p3 = Point3
		self.n = Normale
		self.cam = None
		self.bary =Point3D([(Point1.x+Point2.x+Point3.x)/3.0,(Point1.y+Point2.y+Point3.y)/3.0,(Point1.z+Point2.z+Point3.z)/3.0])
		self.dist = float("inf")
		self.visible = True
		self.points2D = []
		self.lines3d = [Line3D(self.p1,self.p2),
					  Line3D(self.p1,self.p3),
					  Line3D(self.p2,self.p3)]
	def droite(self,Point1,Point2,Point3):
		[xa,ya] = [Point1.x,Point1.y]
		[xb,yb] = [Point2.x,Point2.y]
		[xc,yc ] = [Point3.x,Point3.y]
		a = ya-yb
		b = xb-xa
		c = yb*xa-ya*xb
		signe = math.copysign(1, a*xc+b*yc+c)
		return[a,b,c,signe]
#	 def belongsToTriangle(self,triangle,):
	def setCam(self,cam):
		self.cam = cam
		self.calcDist()
	def setwindow(self,window):
		self.window = [self.windowx,self.windowy]= window
		self.getPixelPosISO()

	def scaleto2DWidnow(self,minx,miny,scale):
		for index in range(4):
			self.points2D[index]= self.points2D[index].translate([-minx,-miny]).scale([scale,-scale]).translate([0,self.windowy])
	def calcDist (self):
		if self.cam is not None :
			self.dist = Vecteur([self.bary.x-self.cam.pos.x,self.bary.y-self.cam.pos.y,self.bary.z-self.cam.pos.z]).ProduitScalaire(self.cam.norm)
	def getPixelPosISO(self):
		
		for point in [self.p1,self.p2,self.p3,self.bary]:
			VecteurOM = Vecteur([point.x,point.y,point.z])
			pixelPosx = VecteurOM.ProduitScalaire(self.cam.horizVector)
			pixelPosy = VecteurOM.ProduitScalaire(self.cam.vertVector)
			p2d =  Point2D([pixelPosx,pixelPosy])
			self.points2D.append(p2d)
#		 return self.points2D
	def selfBelongsToTriangle(self,triangle):
		q1,q2,q3  = triangle.points2D[0],triangle.points2D[1],triangle.points2D[2]
		d1 = self.droite(q1,q2,q3)
		d2 =self.droite(q1,q3,q2)
		d3 =self.droite(q2,q3,q1)
		cond1 =( math.copysign(1,d1[0]*self.points2D[3].x+d1[1]*self.points2D[3].y+d1[2])==d1[3])
		cond2 = (math.copysign(1,d2[0]*self.points2D[3].x+d2[1]*self.points2D[3].y+d2[2])==d2[3])
		cond3 = (math.copysign(1,d3[0]*self.points2D[3].x+d3[1]*self.points2D[3].y+d3[2])==d3[3])
#		 print("cond1",cond1)
#		 print("cond2",cond2)
#		 print("cond3",cond3)
		return cond1 and cond2 and cond3
		
	def isbehind(self,triangle):
#		 p1,p2,p3 = self.points2D[0],self.points2D[1],self.points2D[2]
		depth1 = self.dist
		depth2 = triangle.dist
		if depth1 <= depth2 :
			return False
		return self.selfBelongsToTriangle(triangle)

	def offset(self,xoff,yoff,zoff):
		self.p1 = self.p1+Point3D([xoff,yoff,zoff])
		self.p2 = self.p2+Point3D([xoff,yoff,zoff])
		self.p3 = self.p3+Point3D([xoff,yoff,zoff])
		return self

class Line3D():
	def __init__(self,p1=None,p2=None):
		self.p1 = p1 if p1 is not None and isinstance(p1, Point3D) else Point3D()
		self.p2 = p2 if p2 is not None and isinstance(p2,Point3D) else Point3D()
		self.lines3d = [self]
	def __str__(self):
		result = "Line3D : %s %s"%(self.p1,self.p2)
		return result
	def center(self):
		return self.p1.add(self.p2).scale(0.5)
	def translate(self,p):
		result = Line3D(self.p1.add(p),self.p2.add(p))
		return result
	def rotate(self,center,axis,angle):
		result = Line3D(self.p1.rotate(center,axis,angle),self.p2.rotate(center,axis,angle))
		return result


class Tool(Plugin):
	__doc__ = _("Generate Slices from Stl")

	def __init__(self, master):
		Plugin.__init__(self, master, __name__)
		self.icon  = "mesh"
		self.group = "Development"
		self.variables = [
			("name"    ,    "db" ,    "", _("Name")),
			("file"    ,    "file" ,    "", _(".STL binary file to slice"), "What file to slice"),
			("endmill",   "db" ,    "", _("End Mill")),
			("marginxlow"    ,    "float" ,    10., _("max x additional bound to model"), "x max additional bound"),
			("marginxhigh"    ,    "float" ,    10., _("min x additional bound to model"), "x min additional bound"),
			("marginylow"    ,    "float" ,    10., _("max y additional bound to model"), "y max additional bound"),
			("marginyhihgh"    ,    "float" ,    10., _("min y additional bound to model"), "y min additional bound"),
			("marginZHigh"    ,    "mm" ,    1., _("max Z height mm above model"), "Height to start slicing"),
			("marginZlow"    ,    "mm" ,   0., _("min Z height mm under model"), "Height to stop slicing"),
			("xoff"  ,    "bool" ,    True, _("Set xmin to Zero"), "This will place the xmin bound to zero"),
			("yoff"  ,    "bool" ,    True, _("Set ymin to Zero"), "This will place the ymin bound to zero"),
			("zoff"  ,    "bool" ,    True, _("Set Zmax to Zero"), "This will place the higher point of bound to zero"),
			("direction","x,y","x",_("main direction x or y"),_("direction for Slice removal / Surface removal")),
			("scale"    ,    "float" ,    1,_("scale factor"), "Size will be multiplied by this factor"),
			("zstep"    ,    "mm" ,    0.1, _("layer height (0 = only single zmin)"), "Distance between layers of slices"),
			("AdditionalCut"  ,         "mm" ,     0., _("Additional offset (mm)"), _('acts like a tool corrector inside the material')),
			("operation","1-Slice removal(cylindrical nose),2-Slice finish(Cylindrical nose),3-Surface removal(ball nose),4-Surface finish(ball nose)",
			"Slice removal(cylindrical nose)",_("Operation Type"),"choose your operation here")
			]
		self.help = '''This plugin can slice meshes'''
		self.buttons.append("exe")
		self.okpressed =False
		self.cancelpressed = False
	# ----------------------------------------------------------------------
	def ok(self):
		self.okpressed =True
		print("ok")
		self.dial.destroy()
	def cancel(self):
		self.cancelpressed = True
		print("cancel")
		self.dial.destroy()
	def execute(self, app):
		self.app = app
		file = self["file"]
		tool = app.tools["EndMill"]
		diameter = app.tools.fromMm(tool["diameter"])
		try:
			stepover = tool["stepover"] / 100.0
		except TypeError:
			stepover = 0.
		toolStep  = diameter*stepover
		marginxlow = float(self["marginxlow"])
		marginxhigh = float(self["marginxhigh"])
		marginylow = float(self["marginylow"])
		marginyhihgh = float(self["marginyhihgh"])
		marginZHigh = float(self["marginZHigh"])
		marginZlow = float(self["marginZlow"])
		scale = float(self["scale"])
		xoff =bool(self["xoff"])
		yoff =bool(self["yoff"])
		zoff = bool(self["zoff"])
		zstep = float(self["zstep"])
		direction = self["direction"]
		AdditionalCut = self["AdditionalCut"]
		app.busy()
		app.setStatus(_("Loading file...")+file,True)
# 		b1 = {"text":"validate","action":self.ok}
# 		b2 = {"text":"annulate","action":self.cancel}
# 		self.dial = CustomDialog(app, buttons =[b1,b2])
# 		self.dial.createDial()
		stlObj =stlImporter(file,scale)
		zoffToApply=yoffToApply=xoffToApply=0.0
		deltax = stlObj.maxx-stlObj.minx
		deltay = stlObj.maxy-stlObj.miny
		if xoff :
			xoffToApply=-stlObj.minx+marginxlow
		if yoff :
			yoffToApply=-stlObj.miny+marginylow
		if zoff :
			zoffToApply=-stlObj.maxz-marginZHigh
		if xoff or yoff or zoff:
			app.setStatus(_("Making offset...")+file,True)
			stlObj.Offset(xoffToApply,yoffToApply,zoffToApply)
		xstart = stlObj.minx-marginxlow
		xend = stlObj.maxx+marginxhigh
		ystart = stlObj.miny-marginylow
		yend = stlObj.maxy + marginyhihgh
		zstart = stlObj.maxz+marginZHigh
		zend = stlObj.minz-marginZlow
		print("xstart",xstart)
		print("xend",xend)
		print("ystart",ystart)
		print("yend",yend)
		print("zstart",zstart)
		print("zend",zend)
		dictoperation = 			{"1-Slice removal(cylindrical nose)":1,
									"2-Slice finish(Cylindrical nose)":2,
									"3-Surface removal(ball nose)":3,
									"4-Surface finish(ball nose)":4,
									}
		operation = dictoperation.get(self["operation"],1)
		if operation ==1 :
			sliceremoval = SliceRemoval(stlObj,xstart,xend,ystart,yend,zstart,zend,zstep,toolStep,direction,AdditionalCut)
		
		
# 		app.draw()
		app.notBusy()
		app.setStatus(_("Path Generated")+"..done")
