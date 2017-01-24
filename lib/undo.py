#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)

# Please consult the flair documentation for the license
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#
# Sketch - A Python-based interactive drawing program
# Copyright (C) 1997, 1998 by Bernhard Herzog
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


#
#	Sketch's undo handler
#
# For a description of the representation and generation of undo
# information, see the Developer's Guide in the Doc directory.
#

import sys

UNDO_LIMIT = 100

# Check existence of Unicode not in python3
try:
	u = unicode
	del u
except NameError:
	unicode = str

# -----------------------------------------------------------------------------
def undo(info):
	# execute a single undoinfo
	func = info[0]
	if isinstance(func, str) or isinstance(func, unicode):
		text = func
		func = info[1]
		args = info[2:]
	else:
		args = info[1:]
		text = None

	#print " *U*", info
	redo = func(*args)
	#print " *R*", redo
	if text is not None and callable(redo[0]):
		return (text,) + redo
	else:
		return redo

# -----------------------------------------------------------------------------
def undoList(infos):
	#import pprint
	#print "----------> UndoList <--------------"
	#pprint.pprint(infos)
	#print

	undoinfo = list(map(undo, infos))
	undoinfo.reverse()

	#print "----------> RedoList <--------------"
	#pprint.pprint(undoinfo)
	#print

	return (undoList, undoinfo)

# -----------------------------------------------------------------------------
def _get_callable(info):
	if isinstance(info[0], str) or isinstance(info[0], unicode):
		return info[1]
	return info[0]

# -----------------------------------------------------------------------------
def createListUndo(infos, text=None):
	infos.reverse()
	undolist = []
	for info in infos:
		if info is NullUndo:
			continue
		if info[0] is undoList:
			undolist[len(undolist):] = list(info[-1])
		else:
			undolist.append(info)
	if undolist:
		if len(undolist) == 1:
			return undolist[0]
		if text is not None:
			return (text, undoList, undolist)
		else:
			return (undoList, undolist)
	return NullUndo

# -----------------------------------------------------------------------------
def createMultiUndo(*infos):
	if len(infos) > 1:
		return createListUndo(list(infos))
	return infos[0]

# =============================================================================
# UndoInfo list, which permits to append either lists or tuples
# =============================================================================
class UndoInfo(list):
	# ---------------------------------------------------------------------
	def append(self, info):
		if isinstance(info, tuple):
			list.append(self, info)
		elif isinstance(info, list):
			self.extend(info)
		elif info is NullUndo:
			pass
		else:
			raise UndoTypeError("info to append is not a tuple nor a list")

	# ---------------------------------------------------------------------
	def create(self, text=None):
		return createListUndo(self, text)

# -----------------------------------------------------------------------------
def undoAfter(undo_info, after_info):
	return (undoAfter, undo(undo_info), undo(after_info))

# NullUndo: undoinfo that does nothing. Useful when undoinfo has to be
# returned but nothing has really changed.
def _NullUndo(*ignore):
	return NullUndo
NullUndo = (_NullUndo,)

# -----------------------------------------------------------------------------
class UndoTypeError(Exception):
	pass

# -----------------------------------------------------------------------------
def check_info(info):
	# Check whether INFO has the correct format for undoinfo. Raise
	# UndoTypeError if the format is invalid.
	if not isinstance(info, tuple):
		raise UndoTypeError("undo info is not a tuple (%s, type %s)"
				% (info, type(info)))
	if len(info) < 1:
		raise UndoTypeError("undo info is empty tuple")
	f = info[0]
	if isinstance(f, str) or isinstance(f, unicode):
		if len(info) > 1:
			f = info[1]
	if not callable(f):
		raise UndoTypeError("undo info has no callable item")

# -----------------------------------------------------------------------------
def check_info_silently(info):
	# Return true if INFO is valid undo information, false otherwise.
	try:
		check_info(info)
		return 1
	except UndoTypeError:
		return 0

# =============================================================================
# UndoRedo class
# =============================================================================
class UndoRedo:
	# A Class that manages lists of of undo and redo information
	#
	# It also manages the undo count. This is the number of operations
	# performed on the document since the last save operation. It
	# increased by adding undo info, that is, by editing the document or
	# by Redo, and is decreased by undoing something. The undo count can
	# be used to determine whether the document was changed since the
	# last save or not.

	undo_count = 0

	# ----------------------------------------------------------------------
	def __init__(self):
		self.undoinfo = []
		self.redoinfo = []
		self.setUndoLimit(UNDO_LIMIT)
		if not self.undo_count:
			self.undo_count = 0

	# ----------------------------------------------------------------------
	def setUndoLimit(self, undo_limit):
		if undo_limit is None:
			# unlimited undo. approximate by choosing a very large number
			undo_limit = 0x7ffffff
		if undo_limit >= 1:
			self.max_undo = undo_limit
		else:
			self.max_undo = 1

	# ----------------------------------------------------------------------
	def canUndo(self):
		# Return true, iff an undo operation can be performed.
		return len(self.undoinfo) > 0

	# ----------------------------------------------------------------------
	def canRedo(self):
		# Return true, iff a redo operation can be performed.
		return len(self.redoinfo) > 0

	# ----------------------------------------------------------------------
	def queued(self):
		"""Return elements queued in undo"""
		return len(self.undoinfo)

	# ----------------------------------------------------------------------
	def undo(self):
		# If undo info is available, perform a single undo and add the
		# redo info to the redo list. Also, decrement the undo count.
		if len(self.undoinfo) > 0:
			self.addRedo(undo(self.undoinfo[0]))
			del self.undoinfo[0]
			self.undo_count = self.undo_count - 1

	# ----------------------------------------------------------------------
	def addUndo(self, info, clear_redo=True):
		# Add the undo info INFO to the undo list. If the undo list is
		# longer than self.max_undo, discard the excessive undo info.
		# Also increment the undo count and discard all redo info.
		#
		# The flag CLEAR_REDO is used for internal purposes and inhibits
		# clearing the redo info if it is false. This flag is only used
		# by the Redo method. Code outside of this class should not use
		# this parameter.
		check_info(info)
		if info:
			self.undoinfo.insert(0, info)
			self.undo_count = self.undo_count + 1
			if len(self.undoinfo) > self.max_undo:
				del self.undoinfo[self.max_undo:]
			if clear_redo:
				self.redoinfo = []

	# ----------------------------------------------------------------------
	def redo(self):
		# If redo info is available, perform a single redo and add the
		# undo info to the undo list. The undo count is taken care of by
		# the AddUndo method.
		if len(self.redoinfo) > 0:
			self.addUndo(undo(self.redoinfo[0]), False)
			if self.redoinfo:
				del self.redoinfo[0]

	# ----------------------------------------------------------------------
	def addRedo(self, info):
		# Internal method: add a single redo info
		check_info(info)
		self.redoinfo.insert(0, info)

	# ----------------------------------------------------------------------
	def popUndo(self):
		if self.undoinfo:
			self.undo_count = self.undo_count - 1
			return self.undoinfo.pop(0)
		return None

	# ----------------------------------------------------------------------
	def peekUndo(self):
		# Return the undoinfo tuple of the next undo
		if self.undoinfo:
			return self.undoinfo[0]
		return None

	# ----------------------------------------------------------------------
	def peekRedo(self):
		# Return the undoinfo tuple of the next redo
		if self.redoinfo:
			return self.redoinfo[0]
		return None

	# ----------------------------------------------------------------------
	def undoText(self):
		# Return a string to describe the operation that
		# would be undone next, in a format suitable
		# for a menu entry.
		if self.undoinfo:
			undolabel = self.undoinfo[0][0]
			if isinstance(undolabel, str) or isinstance(undolabel, unicode) :
				return "Undo %s" % undolabel
		return "Undo"

	# ----------------------------------------------------------------------
	def undoTextList(self):
		lst = []
		for u in self.undoinfo:
			if isinstance(u[0], str) or isinstance(u[0], unicode):
				lst.append(u[0])
			else:
				lst.append("undo")
		return lst

	# ----------------------------------------------------------------------
	def redoText(self):
		# Return a string to describe the operation that
		# would be redone next, in a format suitable
		# for a menu entry.
		if self.redoinfo:
			redolabel = self.redoinfo[0][0]
			if isinstance(redolabel, str) or isinstance(redolabel, unicode):
				return "Redo %s" % redolabel
		return "Redo"

	# ----------------------------------------------------------------------
	def reset(self):
		# Forget all undo/redo information
		self.undoinfo = []
		self.redoinfo = []
		self.undo_count = 0

	# ----------------------------------------------------------------------
	def resetUndoCount(self):
		self.undo_count = 0

	# ----------------------------------------------------------------------
	def undoCount(self):
		return self.undo_count
