#!/usr/bin/python
# -*- coding: ascii -*-

# Author: @harvie Tomas Mudrunka
# Date: 7 july 2018
# Additional options: @apshu
# Date: 11 july 2019

from __future__ import absolute_import
from __future__ import print_function
__author__ = "@harvie Tomas Mudrunka"
#__email__  = ""

__name__ = _("FlatPath")
__version__ = "0.2"

import math
import os.path
import re
from CNC import CNC,Block
from ToolsPage import Plugin
from math import pi, sqrt, sin, cos, asin, acos, atan2, hypot, degrees, radians, copysign, fmod


class Tool(Plugin):
	__doc__ = _("""Flatten the path""")			#<<< This comment will be show as tooltip for the ribbon button

	def __init__(self, master):
		Plugin.__init__(self, master,"FlatPath")
		self.icon = "flatpath"			#<<< This is the name of file used as icon for the ribbon button. It will be search in the "icons" subfolder
		self.group = "CAM"	#<<< This is the name of group that plugin belongs
		self.variables = [
			("name",              "db" ,        "", _("Name")),
			("Method","Unwind helical,Movements at stock surface,Remove Z parameter" ,"Remove Z parameter", _("Flattening method")),
		]
		self.help = """Path Z flattening in three different ways:
 * Unwind helical : Unwind helical path cut
 
 * Movements at stock surface : all Z parameter values are replaced with stock surface value within the selected block(s)
 
 * Remove Z parameter : all Z parameter entries are replaced with empty string within the selected block(s). Good for machines without a Z axis, like laser engravers.
"""
		self.buttons.append("exe")
		self.zparamRegexp = re.compile('(?:\\(.+\\))*(?<!;)([Zz]([-+]?[0-9]*\\.[0-9]+|[0-9]+))*') #if group1 is full z and number, group 2 is number only

	# ----------------------------------------------------------------------
	# This method is executed when user presses the plugin execute button
	# ----------------------------------------------------------------------
	def execute(self, app):
		flatmethod = self['Method']
		name = self['Name']
		if name == "default" or name == "":	name = None
		if flatmethod == 'Unwind helical':
			blocks = self.unwind_helical(app=app, parname=name)
		elif flatmethod == 'Remove Z parameter':
			blocks = self.replace_z(app=app, parname=name)
		elif flatmethod == 'Movements at stock surface':
			blocks = self.replace_z(app=app, parname=name, zrepl=CNC.fmt('z',CNC.vars['surface']))
		elif flatmethod == '':
			app.setStatus(_("Operator Error: FlatPath-Please select flattening method"))  # <<< feed back result
			return
		else:
			app.setStatus(_("Internal Error: FlatPath-Unkown method"))  # <<< feed back result
			return

		active=-1 #add to end
		if blocks:
			app.gcode.insBlocks(active, blocks, "Shape flattened") #<<< insert blocks over active block in the editor
			app.refresh()                                                                                           #<<< refresh editor
			app.setStatus(_("Generated: FlatPath"))                           #<<< feed back result
		else:
			app.setStatus(_("Nothing Generated: FlatPath (Did you select a work path?)"))                           #<<< feed back result

	def unwind_helical(self, app, parname):
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue
			eblock = Block((parname or 'flat ')+app.gcode[bid].name())
			eblock = app.gcode.fromPath(app.gcode.toPath(bid)[0],eblock)
			blocks.append(eblock)
		return blocks

	def replace_z(self, app, parname, zrepl = None):
		def zreplacer(matchobj):
			if matchobj.lastindex == 1:
				return zrepl
			return matchobj.string[matchobj.regs[0][0]:matchobj.regs[0][1]]
		zrepl = zrepl or ''
		blocks  = []
		for bid in app.editor.getSelectedBlocks():
			if len(app.gcode.toPath(bid)) < 1: continue
			nblock = Block((parname or 'flat ')+app.gcode[bid].name())
			for gline in app.gcode[bid]:
				line = self.zparamRegexp.sub(zreplacer,gline)
				nblock.append(line)
			blocks.append(nblock)

		return blocks