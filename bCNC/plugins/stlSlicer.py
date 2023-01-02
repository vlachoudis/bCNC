#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @LittlePierre Pierre KLein
# Date: 28 feb 2021

# for further information about the algorithms,
# Please refer to https://github.com/vlachoudis/bCNC/pull/1561

from __future__ import print_function

from copy import deepcopy
# from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod
import math
import os.path
import re
from struct import unpack
import sys

from CNC import CNC, Block
from ToolsPage import Plugin
from bmath import Vector
from bpath import EPS, EPSV,eq, Path, Segment


__author__ = "@DodoLaSaumure  (Pierre Klein)"
#__email__  = ""

__name__ = _("stl3DSlicer")
__version__ = "0.0.1"

try:
	import Tkinter
	from Tkinter import *
	import tkMessageBox
except ImportError:
	import tkinter
	from tkinter import *
	import tkinter.messagebox as tkMessageBox

# DIALOG_ICON = 'questhead'

HEADER_SIZE =80
COUNT_SIZE =4


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
		print ("initial model :")
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
		print ("+++++")
		print ("model offset :")
		print ("deltax",self.maxx-self.minx)
		print ("deltay",self.maxy-self.miny)
		print ("deltaz",self.maxz-self.minz)
		print ("minx,maxx",self.minx,self.maxx)
		print ("miny,maxy",self.miny,self.maxy)
		print ("minz,maxz",self.minz,self.maxz)

	def convertTriangles(self,dirIndexes):
		newTriangles = []
		for triangle in self.triangles:
			points = [triangle.p1,triangle.p2, triangle.p3]
			newPoints = []
			for point in points :
				xyz = [point.x,point.y,point.z]
				newx = xyz[dirIndexes[0]]
				newy = xyz[dirIndexes[1]]
				newz = xyz[dirIndexes[2]]
				newpoint = Point3D([newx,newy,newz])
				newPoints.append(newpoint)
			newtriangle = Triangle3D(newPoints[0],newPoints[1],newPoints[2])
			newTriangles.append(newtriangle)
		return newTriangles

	def getSliceAlongDir(self,direction,height):
		dirDict = {"y":[1,2,0],"x":[0,2,1],"z":[0,1,2]}
		dirIndexes = dirDict.get(direction,[0,1,2])
		path = Path("slice "+str(height))
		def findIndex(p1sign,p2sign,p3sign,signToFind):
			index = 0
			for psign in [p1sign,p2sign,p3sign]:
				if psign == signToFind:
					return index
				index +=1
			return -1
		def getPointZero(p1,p2,height):
			x1,y1,z1 = p1.x,p1.y,p1.z
			x2,y2,z2 = p2.x,p2.y,p2.z
			if z2==z1 : 
				return None
			t = (height-z1)/(z2-z1)
			x = x1+t*(x2-x1)
			y = y1+t*(y2-y1)
			return Vector(x,y)
		
		convertedTriangles = self.convertTriangles(dirIndexes)
		for triangle in convertedTriangles :
			p1sign = (triangle.p1.z-height)>0
			p2sign = (triangle.p2.z-height)>0
			p3sign = (triangle.p3.z-height)>0
			activeTriangle = (p1sign^p2sign)or (p1sign^p3sign) or (p2sign^p3sign)
			signToFind = not ((p1sign and p2sign) or (p1sign and p3sign) or (p2sign and p3sign) )
			isZero = triangle.p1.z-height==0 or triangle.p2.z-height==0 or triangle.p3.z-height==0
			index = -1
			if activeTriangle and not isZero:
				index=findIndex(p1sign,p2sign,p3sign,signToFind)
			q1q2q3 = None
			if index>= 0:
				q1q2q3 = [[triangle.p1,triangle.p2,triangle.p3][index]]
				for i in range(3):
					if not i == index:
						q1q2q3.append([triangle.p1,triangle.p2,triangle.p3][i])
			if q1q2q3 is not None :
				[q1,q2,q3]=q1q2q3
				r1=getPointZero(q1,q2,height)
				r2=getPointZero(q1,q3,height)
				if r1 is not None and r2 is not None:
					segm = Segment(Segment.LINE,r1,r2)
					if segm.length() > 0 :
						path.append(segm)
		return path


class SliceRemoval:
	def __init__(self,stlObj,xstart,xend,ystart,yend,
				z,toolStep,direction,AdditionalOffsetRadius,diameter):
		self.stlObj = stlObj
		self.xstart = xstart
		self.xend = xend
		self.ystart = ystart
		self.yend = yend
		self.z = z
		self.toolStep = toolStep
		self.AdditionalOffsetRadius = AdditionalOffsetRadius
		self.diameter = diameter
		self.direction = direction
		
	def getpathListSlice(self):
		self.computeRawSlice(self.z)
		return self.RawSlicePathList
# 		return [self.FullPathRoughList,self.RawSlicePathList,self.RawSlicePathList]

	def computeRawSlice(self,height):
		z= height
		slicePath = self.stlObj.getSliceAlongDir("z",z)
		splitList = slicePath.split2contours()
		self.RawSlicePathList = deepcopy(splitList)



class Surfacer():
	def __init__(self,stlObj,xstart,xend,ystart,yend,toolStep,direction,AdditionalOffsetRadius,diameter,zend,finishfeed):
		self.stlObj = stlObj
		self.xstart = xstart
		self.xend = xend
		self.ystart = ystart
		self.yend = yend
		self.zend = zend
		self.toolStep = toolStep
		self.AdditionalOffsetRadius = AdditionalOffsetRadius
		self.finishfeed = finishfeed
		self.diameter = diameter
		self.direction = direction
		self.radiusCorrected = self.diameter/2.+AdditionalOffsetRadius
		self.ballSlicesOffsets()
		print ("self.zend",self.zend)
	def ballSlicesOffsets(self):
		slicesToolSteps = []
		sliceToolStep = 0.
		while sliceToolStep < self.radiusCorrected :
			slicesToolSteps.append(sliceToolStep)
			if sliceToolStep >0 :
				slicesToolSteps.append(-sliceToolStep)
			sliceToolStep+=self.toolStep
		slicesToolSteps.sort()
		self.slicesOffsets = []
		for sliceToolStep in slicesToolSteps :
			self.slicesOffsets.append([sliceToolStep,self.offsetZ(sliceToolStep)])

	def offsetZ(self,sliceStep):
		return abs(self.radiusCorrected*math.sin(math.acos(abs(sliceStep)/self.radiusCorrected)))
	
	def orderSegs(self,segList):
		def xA(seg):
			return seg.A[0]
		newPath = Path("path")
		for seg in segList :
			if seg.A[0]>seg.B[0]:
				seg.invert()
			if not seg in newPath:
				newPath.append(seg)
		newPath.sort(key=xA)
		return newPath
	
	def postClean(self,path):
		if len(path)<1:
			return path
		newpath = Path("PostCleaned")
		tmppath = Path("tmpPath")
		lastpos = path[0].A
		zlimit = self.zend+self.diameter/2.
		for seg in path:
			newpos =seg.A
			if (lastpos-newpos).length()>EPS :#and seg.B[1]>=zlimit and seg.A[1] >= zlimit: #and  :#and lastpos[1]>zlimit :#new A <> last B=>move from last B to A, then new A to B
				if newpos[0]>lastpos[0] :
					tmppath.append(Segment(Segment.LINE,lastpos,newpos))
					lastpos = newpos
				if seg.B[0]> lastpos[0] :
					tmppath.append(Segment(Segment.LINE,lastpos,seg.B))
					lastpos = seg.B
		lastSeg=tmppath[0]
		return tmppath
# 

	def areSuperposed(self,seg0,seg1):
		return max(seg0.minx,seg1.minx) < min(seg0.maxx,seg1.maxx)

	def completePath(self,path):
		seg0 = path[0]
		seglast = path[-1]
		seg00 = Segment(Segment.LINE,Vector(seg0.A[0],self.zend),seg0.A)
		path.insert(0,seg00)
		seglastLast=Segment(Segment.LINE,seglast.B,Vector(seglast.B[0],self.zend))
		path.append(seglastLast)
		return path
	def getTopSegs2(self,pathlist,postClean=True):
		newPath = Path("max")
		listx = []
		for path in pathlist :
			path=self.orderSegs(path)
			for seg in path:
				xA = seg.A[0]
				xB = seg.B[0]
				if not xA in listx:
					listx.append(xA)
				if not xB in listx:
					listx.append(xB)
		listx.sort()
		for x in listx:
			linex = Segment(Segment.LINE,Vector(x,1000.),Vector(x,-1000.))
			maxSeg = None
			maxz = - float("inf")
			matchingSegs = []
			for path in pathlist:
				for seg in path :
					if seg.minx<=x and seg.maxx > x and not seg in matchingSegs:
						matchingSegs.append(seg)
			for seg in matchingSegs:
				P1,P2 = linex.intersect(seg)
				if P1 is not None:
					z = P1[1]
					if z > maxz and seg.length()>0 :
						maxz = z
						maxSeg = seg
			if not maxSeg in newPath:
				newPath.append(maxSeg)
		if postClean : result = self.postClean(newPath)
		else : result = newPath
		return result
	
	def applyOffsets(self,rotatingBufferSlicesPathList):
		newlist = []
		for index,path in enumerate(rotatingBufferSlicesPathList):
			offZ = self.slicesOffsets[index][1]
			opath = path.offset(offZ)
		# Post clean
			if opath:
				opath.intersectSelf()
				opath.removeExcluded(path, offZ)
				opath.removeZeroLength(abs(offZ)/100.)
				newlist.append(self.postClean(opath))
			else :
				newlist.append(Path("Empty"))
		return newlist
		
	def reverse(self,path):
		newpath = list(reversed(path))
		for seg in newpath:
			seg.invert()
		return newpath
	
	def generategcode(self,sliceNmax,evenSense):
		self.diameterz = self.diameter
# 		self.diameterz = 0.
		newblock = []
		if sliceNmax is None or len(sliceNmax)<1:
			return newblock
		if not evenSense:
			sliceOriented = self.reverse(sliceNmax)
		else:
			sliceOriented = sliceNmax
		seg = sliceOriented[0]
		if self.direction == "x":
			newblock.append(CNC.gline(x=seg.A[0],f=self.finishfeed))
		else :
			newblock.append(CNC.gline(y=seg.A[0],f=self.finishfeed))
# 		newblock.append(CNC.gline(z=seg.A[1]+self.diameter/2.,f=self.finishfeed))
		newblock.append(CNC.gline(z=seg.A[1]-self.diameterz/2.,f=self.finishfeed))
		lastpos = Vector(seg.A[0],self.zend)
		for seg in sliceOriented :
			newpos = seg.A
			if self.direction == "x":
				if (lastpos-newpos).length()>EPSV :
# 					newblock.append(CNC.gline(x=seg.A[0],z=seg.A[1]+self.diameter/2.,f=self.finishfeed))
					newblock.append(CNC.gline(x=seg.A[0],z=seg.A[1]-self.diameterz/2.,f=self.finishfeed))
# 				newblock.append(CNC.gline(x=seg.B[0],z=seg.B[1]+self.diameter/2.,f=self.finishfeed))
				newblock.append(CNC.gline(x=seg.B[0],z=seg.B[1]-self.diameterz/2.,f=self.finishfeed))
			else :
				if (lastpos-newpos).length()>EPSV :
# 					newblock.append(CNC.gline(y=seg.A[0],z=seg.A[1]+self.diameter/2.,f=self.finishfeed))
					newblock.append(CNC.gline(y=seg.A[0],z=seg.A[1]-self.diameterz/2.,f=self.finishfeed))
# 				newblock.append(CNC.gline(y=seg.B[0],z=seg.B[1]+self.diameter/2.,f=self.finishfeed))
				newblock.append(CNC.gline(y=seg.B[0],z=seg.B[1]-self.diameterz/2.,f=self.finishfeed))
			lastpos = seg.B
		newblock.append(CNC.gline(z=self.zend,f=self.finishfeed))
		return newblock
	def sliceRemoveXY(self,z,app):
		self.PathSliceRoughList=[]
		self.FullPathRoughList = []
		[dir1start,dir1end] = [self.xstart,self.xend] if self.direction =="x" else [self.ystart,self.yend]
		[dir2start,dir2end] = [self.ystart,self.yend] if self.direction =="x" else [self.xstart,self.xend] 
		currentposdir2 = dir2start
		even = False
		indexSlice = 0
		while currentposdir2 < dir2end:
			currentslice = self.allSlices[indexSlice]
			even = not even
			dir1startstart = dir1start if even else dir1end
			dir1endend = dir1end if even else dir1start
			if self.direction =="x":
# 				lineIntersect = Segment(Segment.LINE,Vector(dir1startstart,currentposdir2),Vector(dir1endend,currentposdir2))
				lineIntersect = Segment(Segment.LINE,Vector(dir1startstart,z),Vector(dir1endend,z))
			else :
# 				lineIntersect = Segment(Segment.LINE,Vector(currentposdir2,dir1startstart),Vector(currentposdir2,dir1endend))
# 				lineIntersect = Segment(Segment.LINE,Vector(currentposdir2,z),Vector(currentposdir2,z))
				lineIntersect = Segment(Segment.LINE,Vector(dir1startstart,z),Vector(dir1endend,z))
			self.PathSliceRoughList = []
			self.tmpSlicePath = Path("tmp")
			self.PathLineIntersect = Path("line intersect")
			self.PathLineIntersect.append(lineIntersect)
			intersectionsPoints =[]
			currentsliceCopy = deepcopy(currentslice)
			inter = currentsliceCopy.intersectPath(self.PathLineIntersect)
			for point in inter:
				intersectionsPoints.append(point[2])
			indice = 0 if self.direction == "x" else 0
			liste = sorted(intersectionsPoints, key=lambda point: point[indice],reverse = not even)
			currentdir1pos = dir1startstart
			index = -1
			for point in liste :
				index +=1
				if self.direction =="x":
					segment = Segment(Segment.LINE,Vector(currentdir1pos,currentposdir2),Vector(point[0],currentposdir2))
				else :
					segment = Segment(Segment.LINE,Vector(currentposdir2,currentdir1pos),Vector(currentposdir2,point[0]))
				if index %2 ==0:
					if segment.length()>0:
						self.tmpSlicePath.append(segment)
					self.PathSliceRoughList.append(self.tmpSlicePath)
					self.tmpSlicePath = Path("tmp")
				currentdir1pos = point[0]# if self.direction == "x" else point[0]
			if self.direction =="x":
				segment = Segment(Segment.LINE,Vector(currentdir1pos,currentposdir2),Vector(dir1endend,currentposdir2))
			else :
				segment = Segment(Segment.LINE,Vector(currentposdir2,currentdir1pos),Vector(currentposdir2,dir1endend))
			self.tmpSlicePath.append(segment)
			if self.direction =="x":
				segment = Segment(Segment.LINE,Vector(dir1endend,currentposdir2),Vector(dir1endend,currentposdir2+self.toolStep))
			else :
				segment = Segment(Segment.LINE,Vector(currentposdir2,dir1endend),Vector(currentposdir2+self.toolStep,dir1endend))
			if currentposdir2 +self.toolStep < dir2end :
				self.tmpSlicePath.append(segment)
			if currentposdir2 == dir2end:
				break
			currentposdir2+=self.toolStep
			currentposdir2=min(currentposdir2,dir2end)
			self.PathSliceRoughList.append(self.tmpSlicePath)
			self.FullPathRoughList.extend(self.PathSliceRoughList)
			indexSlice +=1
		return self.FullPathRoughList
		
	def getAllSlicesWithOfssetAlongDir(self,app):
		allSlices = []
# 		[dir1start,dir1end] = [self.xstart,self.xend] if self.direction =="x" else [self.ystart,self.yend]
		[dir2start,dir2end] = [self.ystart,self.yend] if self.direction =="x" else [self.xstart,self.xend]
		currentposdir2 = dir2start
		while dir2end>=currentposdir2:
			RawSlicePath = self.stlObj.getSliceAlongDir(self.direction,currentposdir2)
			RawSlicePath =self.getTopSegs2([RawSlicePath])
			offZ = self.radiusCorrected
			opath = RawSlicePath.offset(offZ)
		# Post clean
			if opath:
				opath.intersectSelf()
				opath.removeExcluded(RawSlicePath, offZ)
				opath.removeZeroLength(abs(offZ)/100.)
				opath=self.getTopSegs2([opath])
			if len(opath)>0:
				opath=self.completePath(opath)
			allSlices.append(opath)
			currentposdir2+=self.toolStep
# 			currentposdir2=min(currentposdir2,dir2end)
			app.setStatus("step 1/2 : progress %.2f "%(currentposdir2/dir2end*100.)+"%",True)
		self.allSlices = allSlices
		return allSlices
	def calcGcode(self,app):
		app.setStatus(_("initializing"),True)
		blocks = []
		block = Block("Ball Finish")
		block.append(CNC.grapid(x=self.xstart,y=self.ystart))
		block.append(CNC.grapid(z=CNC.vars["safe"]))
		block.append(CNC.gline(z=self.zend,f=self.finishfeed))
		block.append("(entered)")
		blocks.append(block)
		[dir1start,dir1end] = [self.xstart,self.xend] if self.direction =="x" else [self.ystart,self.yend]
		[dir2start,dir2end] = [self.ystart,self.yend] if self.direction =="x" else [self.xstart,self.xend]
		currentposdir2 = dir2start
		rotatingBufferSlicesPathList = [] #rotating buffer to avoid computing all slices at each tool step
		for index,sliceOffset in enumerate(self.slicesOffsets) :
			app.setStatus(_("initializing %.02f"%(float(index)/float(len(self.slicesOffsets))*100.)),True)
			sliceToolStep = sliceOffset[0]
			RawSliceNPath = self.stlObj.getSliceAlongDir(self.direction,currentposdir2+sliceToolStep).arcFit()#.split2contours()
			sliceNmaxPath = self.getTopSegs2([RawSliceNPath])
			rotatingBufferSlicesPathList.append(sliceNmaxPath)
		app.setStatus(_("init done"),True)
		evenSense = False #direction along dir1 (going forwards / Back
		while abs(currentposdir2 - dir2end)>EPSV:
			block = Block("Ball Finish dir:%s %.02f"%(self.direction,currentposdir2))
			evenSense = not evenSense
			dir1endend = dir1end if evenSense else dir1start
			#do the stuff
			offsetPathList = self.applyOffsets(rotatingBufferSlicesPathList)
			offsetPathTopIntersected = self.getTopSegs2(offsetPathList)
# 			print ("intersect done")
			l = len(rotatingBufferSlicesPathList)
			n = int((l-1)/2)
			block.extend( self.generategcode(offsetPathTopIntersected,evenSense))
			if self.direction =="x":
				block.append(CNC.gline(x=dir1endend,f=self.finishfeed))
			else :
				block.append(CNC.gline(y=dir1endend,f=self.finishfeed))
			currentposdir2+=self.toolStep
			currentposdir2=min(currentposdir2,dir2end)
			if self.direction =="x":
				block.append(CNC.gline(y=currentposdir2,z=self.zend,f=self.finishfeed))
			else :
				block.append(CNC.gline(x=currentposdir2,z=self.zend,f=self.finishfeed))
			blocks.append(block)
			delta = currentposdir2-dir2end
			if abs(currentposdir2 -dir2end)<EPSV:
				break
			rotatingBufferSlicesPathList = rotatingBufferSlicesPathList[1:] #+ rotatingBufferSlicesPathList[:1]#rotate buffer left
			newRawSliceNlast = self.stlObj.getSliceAlongDir(self.direction,currentposdir2+self.slicesOffsets[-1][0])#.split2contours()
			sliceNmax = self.getTopSegs2([newRawSliceNlast])
			rotatingBufferSlicesPathList.extend([sliceNmax])
			app.setStatus("progress %.2f "%(currentposdir2/dir2end*100.)+"%",True)
		return blocks

	def fromPath(self,pathlist,z,zsafe):
		block = Block("new")
		lastSeg = pathlist[0][0]
		for path in pathlist :
			for seg in path:
				if not eq(lastSeg.B,seg.A) :
					block.append(CNC.grapid(z=zsafe))
					block.append(CNC.grapid(x=seg.A[0],y=seg.A[1]))
					block.append(CNC.gline(z=z,f=CNC.vars["cutfeedz"]))
# 				block.append(CNC.gline(x=seg.A[0], y=seg.A[1],z=z,f=CNC.vars["cutfeedz"]))
				block.append(CNC.gline(x=seg.B[0],y=seg.B[1],z=z,f=CNC.vars["cutfeed"]))
				lastSeg = seg
		return block

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


class Point3D():
	def __init__(self,coordsTuple=None):
		if coordsTuple is None : 
			coordsTuple = [0,0,0]
		[self.x,self.y,self.z]=coordsTuple
	def __str__(self):
		return "Point3D [x=%2f,y=%2f,z=%2f]"%(self.x,self.y,self.z)
	def __repr__(self):
		return self.__str__()
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
	def __init__(self,Point1,Point2,Point3,Normale=None):
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
	__doc__ = _("Generate 3d removal from Stl")

	def __init__(self, master):
		Plugin.__init__(self, master, __name__)#"3D Slicer")
		self.icon = "mesh"
		self.group = "Development"
		self.variables = [
			("name", "db", "", _("Name")),
			("file", "file", "", _(".STL binary file to slice"), "What file to slice"),
			("endmill", "db", "", _("End Mill")),
			("marginxlow", "mm",10., _("max x additional bound to model"), "x max additional bound"),
			("marginxhigh", "mm", 10., _("min x additional bound to model"), "x min additional bound"),
			("marginylow", "mm", 10., _("max y additional bound to model"), "y max additional bound"),
			("marginyhihgh", "mm", 10., _("min y additional bound to model"), "y min additional bound"),
			("marginZHigh", "mm", 1., _("max Z height mm above model"), "Height to start slicing"),
			("marginZlow", "mm", 0., _("min Z height mm under model"), "Height to stop slicing"),
			("xoff", "bool", True, _("Set xmin to Zero"), "This will place the xmin bound to zero"),
			("yoff", "bool", True, _("Set ymin to Zero"), "This will place the ymin bound to zero"),
			("zoff", "bool", True, _("Set Zmax to Zero"), "This will place the higher point of bound to zero"),
			("direction","x,y","x",_("main direction x or y"),_("direction for Slice removal / Surface removal")),
			("scale", "float", 1.,_("scale factor"), "Size will be multiplied by this factor"),
			("zstep", "mm", 3., _("layer height"), "Distance between layers of slices"),
			("toolstep", "mm", -1., _("tool step (-1: From tool database)"), "tool step along x y"),
			("finishfeed", "mm", 100, _("finish xyz feed"), "finish feed (x,y,z)"),
			("AdditionalOffsetRadius", "mm" , 0., _("radius offset outside material (mm)"), _('acts like a tool corrector outside the material')),
			("operations","0-Raw Slice(information only),1-Rough Slice rough removal(cylindrical nose),2-Finish Surface removal (ball nose)",
			"1-Rough Slice rough removal(cylindrical nose)",_("Operation Type"),"choose your operation here"),
			]
		self.help = '''This plugin can slice meshes
Please refer to https://github.com/vlachoudis/bCNC/pull/1561
NB : This plugin does not work for flat surfaces, please use Offset, Profile, Cut functions for this purpose

'''
		self.buttons.append("exe")
	# ----------------------------------------------------------------------
	def execute(self, app):
		self.app = app
		import time
		t0 = time.time()
		name = self["name"]
		if name=="default" or name=="": name=None
		file = self["file"]
		tool = app.tools["EndMill"]
		diameter = app.tools.fromMm(tool["diameter"])
		toolLength = app.tools.fromMm(tool["length"])
		try:
			stepover = tool["stepover"] / 100.0
		except TypeError:
			stepover = 0.
		if float(self["toolstep"])<=0:
			toolStep = diameter*stepover
		else :
			toolStep = float(self["toolstep"])
		print ("toolStep",toolStep)
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
		AdditionalOffsetRadius = self["AdditionalOffsetRadius"]
		finishfeed = self["finishfeed"]
		app.busy()
		app.setStatus(_("Loading file...")+file,True)
		if os.path.isfile(file):
			stlObj =stlImporter(file,scale)
		else :
			stlObj = None
		zoffToApply=yoffToApply=xoffToApply=0.0
		if stlObj is not None:
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
		dictoperation = {
			"0-Raw Slice(information only)":0,
			"1-Rough Slice rough removal(cylindrical nose)":1,
# 			"2-Rough Slice contour(cylindrical nose)":2,
			"2-Finish Surface removal (ball nose)":2,
									}
		operation = dictoperation.get(self["operations"],1)
		RawSliceOperation = operation ==0
		RoughRemovalOperation =operation ==1
# 		RoughContourOperation = operation ==2
		FinishSurfaceOperation = operation ==2
		gcode = app.gcode
		gcode.headerFooter()
		if RawSliceOperation and stlObj is not None:
			z = zstart
# 			previousSliceList=[]
# 			previousRawSliceList = []
			rawSliceList=[]
			while z > zend:
				print ("z",z,"/zend",zend)
				blocks = []
				app.setStatus(_("Making slice...z=")+str(z)+"/"+str(zend)+"->%.2f%%"%(z/zend*100.),True)
				sliceremoval = SliceRemoval(stlObj,xstart,xend,ystart,yend,
										z,toolStep,direction,AdditionalOffsetRadius,diameter)
				pathlist = []
				rawSliceList= sliceremoval.getpathListSlice()
				pathlist.extend(rawSliceList)
				if len(pathlist)>0:
					allblocks = gcode.blocks
					newblocks = gcode.fromPath(pathlist,z=z,zstart=z)
					block = Block("Slice z="+str(z))
					block.extend(newblocks)
					blocks.append(block)
					bid = len (allblocks)-1
					app.gcode.addBlockUndo( bid, block)
				z -= zstep
		if FinishSurfaceOperation and stlObj is not None:
			ballfinish = Surfacer(stlObj,xstart,xend,ystart,yend,
										toolStep,direction,AdditionalOffsetRadius,diameter,zend,finishfeed)
			blocks = ballfinish.calcGcode(app)
			allblocks = gcode.blocks
			bid = len (allblocks)-1
			app.gcode.insBlocks(bid, blocks, _("BALL FINISH"))
		if RoughRemovalOperation and stlObj is not None:
			RoughSurfacer = Surfacer(stlObj,xstart,xend,ystart,yend,
					toolStep,direction,AdditionalOffsetRadius,diameter,zend,finishfeed)
			slices = RoughSurfacer.getAllSlicesWithOfssetAlongDir(app)
			z = zstart
			while z > zend:
				app.setStatus("step 2/2 : progress %.2f "%(z/zend*100.)+"%",True)
				blocks = []
				pathlist = []
				roughRemoval= RoughSurfacer.sliceRemoveXY(z,app)
				pathlist.extend(roughRemoval)
				if len(pathlist)>0:
					allblocks = gcode.blocks
# 					newblocks = gcode.fromPath(pathlist,z=z+AdditionalOffsetRadius,zstart=z+AdditionalOffsetRadius)
# 					block = Block("Slice z="+str(z+AdditionalOffsetRadius))
					newblocks = RoughSurfacer.fromPath(roughRemoval,z=z,zsafe=CNC.vars["safe"])
					block = Block("Slice z="+str(z))
					block.extend(newblocks)
					blocks.append(block)
					bid = len (allblocks)-1
					app.gcode.addBlockUndo( bid, block)
				z -= zstep
		if zend < -toolLength :
			msg = "Be careful, the tool length might be too short..."
			tkMessageBox.showwarning(_("Tool Length too short"),
		_("WARNING: %s")%(msg),
			parent=app)
		t1 = time.time()
		print ("time for compute ",t1-t0)
		app.refresh()
		t2 = time.time()
		print ("time for refresh ",t2-t1)
		print ("total time",t2-t0)
		app.notBusy()
		app.setStatus(_("Path Generated")+"..done")


