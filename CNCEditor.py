# -*- coding: latin1 -*-
# $Id: CNCEditor.py,v 1.9 2014/10/15 15:04:38 bnv Exp $
#
# Author:       Vasilis.Vlachoudis@cern.ch
# Date: 24-Aug-2014

try:
	from Tkinter import *
except ImportError:
	from tkinter import *

import tkDialogs
import CNCCanvas

# List contains order of match with regular expression
HIGHLIGHT = {	"c": (r"\(.*\)",                "Blue"),
		"C": (r";.*",                   "Blue"),
		"X": (r"[xX] *[+\-]?\d*\.?\d*", "DarkRed"  ),
		"Y": (r"[yY] *[+\-]?\d*\.?\d*", "DarkGreen"),
		"Z": (r"[zZ] *[+\-]?\d*\.?\d*", "DarkBlue" ),

		"I": (r"[iI] *[+\-]?\d*\.?\d*", "Maroon"),
		"J": (r"[jJ] *[+\-]?\d*\.?\d*", "Maroon"),
		"K": (r"[kK] *[+\-]?\d*\.?\d*", "Maroon"),
		"R": (r"[rR] *[+\-]?\d*\.?\d*", "Maroon"),

		"G": (r"[gG] *\d+\.?\d*",       "Dark Orchid"),
		"M": (r"[mM]\d+",               "DarkGrey"),
		"F": (r"[fF][+\-]?\d*\.?\d*",   "Yellow4"),
		"P": (r"[pP]\d+",               "Orange") }

#==============================================================================
# CNC Text Editor
#==============================================================================
class CNCEditor(Frame):
	def __init__(self, master, app, *kw, **kwargs):
		Frame.__init__(self, master, *kw, **kwargs)

		# Global variables
		self.app = app
		self.cnc = app.cnc

		self.text = Text(self, background="White", width=40, wrap=NONE, undo=True)
		self.text.pack(side=LEFT, expand=TRUE, fill=BOTH)
		self._editorSB = Scrollbar(self, orient=VERTICAL, command=self.text.yview)
		self._editorSB.pack(side=RIGHT, fill=Y)
		self.text.config(yscrollcommand=self.textScroll)

		# bindings
		self.text.bind('<<Modified>>',		self.app.drawAfter)
		self.text.bind('<<Selection>>',		self.selectionChange)
		self.text.bind('<KeyRelease>',		self.selectionChange)
		self.text.bind('<ButtonRelease-1>',	self.selectionChange)
		self.text.bind('<Double-1>',		self.double)
		self.text.bind('<Control-Key-h>',       self.replaceDialog)

		self._highAfter  = None
		self._highStart  = 0
		self._highLast   = 0
		self._skipSelection = False
		self._findStr    = None		# find string
		self._findVar    = IntVar()	# find length count
		self._findCase   = None		# Match case

	# ----------------------------------------------------------------------
	def set(self, txt):
		self.text.delete("1.0", END)
		self.text.insert("1.0", txt)
		self.text.edit_reset()
		self.highlight()

	# ----------------------------------------------------------------------
	def get(self, start="1.0", end=END):
		return self.text.get(start, end)

	# ----------------------------------------------------------------------
	def delete(self, start, end):
		return self.text.delete(start, end)

	# ----------------------------------------------------------------------
	def insert(self, pos, txt):
		return self.text.insert(pos, txt)

	# ----------------------------------------------------------------------
	def setInsert(self, pos):
		self.text.mark_set(INSERT, pos)

	# ----------------------------------------------------------------------
	def cut(self, event=None):
		self.text.event_generate("<<Cut>>")

	# ----------------------------------------------------------------------
	def copy(self, event=None):
		self.text.event_generate("<<Copy>>")

	# ----------------------------------------------------------------------
	def paste(self, event=None):
		self.text.event_generate("<<Paste>>")

	# ----------------------------------------------------------------------
	def undo(self, event=None):
		try:
			self.text.edit_undo()
		except TclError:
			pass

	# ----------------------------------------------------------------------
	def redo(self, event=None):
		try:
			self.text.edit_redo()
		except TclError:
			pass

	#----------------------------------------------------------------------
	def textScroll(self, a, b):
		self._highStart = int(len(self.app.canvas.items)*float(a))+1
		self._editorSB.set(a,b)
		self.highlightAfter()

	#----------------------------------------------------------------------
	# Find start of block from line (G0 or M code)
	#----------------------------------------------------------------------
	def findBlockStart(self, line):
		while line>0:
			start = "%d.0"%(line)
			end   = "%d.end"%(line)
			cmd = self.cnc.parseLine(self.text.get(start,end))
			found = False
			if cmd:
				for c in cmd:
					if c[0] in ('m','M') or \
					  (c[0] in ('g','G') and int(c[1:])==0):
						found = True
			if found: break
			line -= 1
		return line

	#----------------------------------------------------------------------
	# Find end of block from line
	#----------------------------------------------------------------------
	def findBlockEnd(self, line):
		while line<=len(self.app.canvas.items):
			start = "%d.0"%(line)
			end   = "%d.end"%(line)
			cmd = self.cnc.parseLine(self.text.get(start,end))
			line += 1
			if cmd is None: continue
			found = False
			for c in cmd:
				if c[0] in ('m','M') or \
				  (c[0] in ('g','G') and int(c[1:])==0):
					found = True
			if found: break
		line -= 1
		return line

	#----------------------------------------------------------------------
	# Find Previous Block Start
	#----------------------------------------------------------------------
#	def findPrevBlockStart(self, line):
#		# First skip all G0 and M codes
#		while line>0:
#			start = "%d.0"%(line)
#			end   = "%d.end"%(line)
#			cmd = self.cnc.parseLine(self.text.get(start,end))
#			found = False
#			if cmd:
#				for c in cmd:
#					if c[0] in ('m','M') or \
#					  (c[0] in ('g','G') and int(c[1:])==0):
#						found = True
#			if not found: break
#			line -= 1
#		return self.findBlockStart(line)

	#----------------------------------------------------------------------
	# Select a block of gcode from line
	#----------------------------------------------------------------------
	def selectBlock(self, line):
		startLine = self.findBlockStart(line)
		endLine   = self.findBlockEnd(line)
		start = "%d.0"%(startLine)
		end   = "%d.end"%(endLine)
		self.text.mark_set(INSERT,start)
		self.text.tag_add(SEL, start, end)
		self.text.see(start)

	#----------------------------------------------------------------------
	def double(self, event=None):
		line = int(self.text.index(INSERT).split('.')[0])
		self._skipSelection = False
		if event and event.state & CNCCanvas.CONTROL_MASK==0:
			self.text.tag_remove(SEL, "1.0", END)
		self.selectBlock(line)
		self._skipSelection = True
		return "break"

	#----------------------------------------------------------------------
	# Select items select from canvas
	#----------------------------------------------------------------------
	def select(self, lines, block, clear=False):
		self._skipSelection = True
		if clear:
			self.text.tag_remove(SEL, "1.0", END)

		if block:
			for lineNo in lines:
				self.selectBlock(lineNo)

		else:
			for lineNo in lines:
				start = "%d.0"%(lineNo)
				end   = "%d.end"%(lineNo)
				self.text.tag_add(SEL, start, end)
			self.text.mark_set(INSERT,start)
			self.text.see(start)
		self._skipSelection = False
		self.selectionChange()

	#----------------------------------------------------------------------
	def selectSet(self, start, end):
		self.text.tag_add(SEL, start, end)

	#----------------------------------------------------------------------
	def selectAll(self):
		self.text.tag_add(SEL, "1.0", END)

	#----------------------------------------------------------------------
	def unselectAll(self):
		self.text.tag_remove(SEL, "1.0", END)

	# ----------------------------------------------------------------------
	def selectionChange(self, event=None):
		if self._skipSelection: return
		self.app.selectionChange()

	# ----------------------------------------------------------------------
	def skipSelection(self, skip):
		self._skipSelection = skip

	# ----------------------------------------------------------------------
	def getSelect(self):
		return self.text.tag_ranges(SEL)

	# ----------------------------------------------------------------------
	def index(self, mark):
		return self.text.index(mark)

	# ----------------------------------------------------------------------
	def insertPosition(self):
		return int(str(self.text.index(INSERT)).split("."))

	# ----------------------------------------------------------------------
	# Highlight text
	# ----------------------------------------------------------------------
	def highlight(self):
		#t0 = time.time()
		start = self.text.index("%d.0"%(self._highStart))
		if not self.text.edit_modified() and self._highLast == start: return
		self._highLast = start

		end   = self.text.index("%d.0"%(self._highStart+100))
		count = IntVar()

		self.text.tag_remove("*", start, end)

		# First search for the first occurance of all patterns
		found = {}
		for tag,(pat,color) in HIGHLIGHT.items():
			index = self.text.search(pat, start, end, count=count, regexp=True)
			if index != "":
				found[tag] = (index, count.get())
				#print "Found:", tag, index, count.get()

		# Main loop
		while True:
			# Find the top-most pattern to highlight
			nextTag   = None
			nextIndex = end
			nextCount = 0
			for tag,(index,c) in found.items():
				if self.text.compare(index,"<",nextIndex):
					nextTag   = tag
					nextIndex = index
					nextCount = c

			#print "Minimum:", nextTag, nextIndex, nextCount
			if nextTag is None: break
			#start = self.text.index("%s+%sc"%(nextIndex,nextCount))
			start = "%s+%sc"%(nextIndex,nextCount)
			self.text.tag_add(nextTag, nextIndex, start)

			# Update tags
			foundItems = found.items()
			for tag,(index,c) in foundItems:
				#print ">>",tag,index
				if self.text.compare(index,"<",start):
					index = self.text.search(HIGHLIGHT[tag][0],
							start, end,
							count=count,
							regexp=True)
					if index != "":
						#print "Update:", tag, index, count.get()
						found[tag] = (index, count.get())
					else:
						#print "Update:", tag, "-None-"
						del found[tag]

		# Set properties to tags
		for tag,(pat,color) in HIGHLIGHT.items():
			self.text.tag_config(tag,foreground=color)

		self._highAfter = None
		self.text.edit_modified(False)
		#print "Highlight:",time.time()-t0

	# ----------------------------------------------------------------------
	def highlightAfter(self):
		if self._highAfter is not None: self.after_cancel(self._highAfter)
		self._highAfter = self.after(50, self.highlight)

	# --------------------------------------------------------------------
	# FindDialog
	# --------------------------------------------------------------------
	def findDialog(self, event=None):
		sel = self.getSelect()
		if not sel:
			txt = ""
		else:
			txt = self.text.get(sel[0], sel[1])
		fd = tkDialogs.FindReplaceDialog(self, replace=False)
		fd.show(self.find, None, None, txt)
		return "break"

	# ----------------------------------------------------------------------
	# Find and Replace dialog
	# ----------------------------------------------------------------------
	def replaceDialog(self, event=None):
		sel = self.getSelect()
		if not sel:
			txt = ""
		else:
			txt = self.text.get(sel[0], sel[1])
		fd = tkDialogs.FindReplaceDialog(self, replace=True)
		fd.show(self.replaceFind, self.replace, self.replaceAll, txt)
		return "break"

	# ----------------------------------------------------------------------
	# Find target(s)
	# ----------------------------------------------------------------------
	def find(self, pattern=None, matchCase=None, moveEnd=True):
		if pattern is not None:
			self._findStr = pattern
		elif self._findStr is None:
			return
		if matchCase is not None:
			self._findCase = matchCase

		self.text.tag_remove(SEL, "1.0", END)
		index = str(self.text.search(self._findStr,
				"insert + 1 c",
				regexp=True,
				count=self._findVar,
				nocase=self._findCase))

		if index:
			end = "%s + %d c"%(index, self._findVar.get())
			self.text.tag_add(SEL, index, end)
			if moveEnd:
				self.text.mark_set(INSERT, end)
			else:
				self.text.mark_set(INSERT, index)
			self.text.see(index)

	# ----------------------------------------------------------------------
	def findNext(self):
		self.find()

	# ----------------------------------------------------------------------
	def replaceFind(self, pattern=None, matchCase=None):
		self.find(pattern, matchCase, False)

	# ----------------------------------------------------------------------
	def replace(self, pattern, repl, matchCase=None):
		if pattern is not None:
			self._findStr = pattern
		elif self._findStr is None:
			return
		if matchCase is not None:
			self._findCase = matchCase

		self.text.tag_remove(SEL, "1.0", END)
		index = str(self.text.search(self._findStr,
				INSERT,
				regexp=True,
				count=self._findVar,
				nocase=matchCase))

		if index:
			self.text.delete(index, "%s + %d c"%(index, self._findVar.get()))
			self.text.insert(index, repl, SEL)
			self.text.mark_set(INSERT, "%s + %d c"%(index, len(repl)))
			self.text.see(index)
			self.replaceFind()

	# ----------------------------------------------------------------------
	def replaceAll(self, pattern, repl, matchCase=None):
		if pattern is not None:
			self._findStr = pattern
		elif self._findStr is None:
			return
		if matchCase is not None:
			self._findCase = matchCase

		self.text.tag_remove(SEL, "1.0", END)
		self.text.mark_set(INSERT, "1.0")

		while True:
			index = str(self.text.search(self._findStr,
					INSERT,
					regexp=True,
					stopindex=END,
					count=self._findVar,
					nocase=matchCase))

			if not index: break

			self.text.delete(index, "%s + %d c"%(index, self._findVar.get()))
			self.text.insert(index, repl, SEL)
			self.text.mark_set(INSERT, "%s + %d c"%(index, len(repl)))

		self.text.see(INSERT)
