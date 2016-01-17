#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Frank Wiebenga
# Date:	14-Jan-2016

__author__ = "Frank Wiebenga"
__email__  = "atrueresistance@gmail.com"

__name__ = _("multipass")
__version__ = "0.0.1"

import math, re
from bmath import *

from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
# Take selected gcode, and generate multiple passes using depth per pass
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Take selected gcode, and generate multiple passes using depth per pass")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name = "multipass"
		self.icon = "layers"
		self.variables = [
			("name",      "db",    "", _("Name")),
			("np",       "int",     3, "Number of passes"),
			("dpp",      "int",     3, "Depth per Pass")
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def execute(self, app):
		# Get selected blocks from editor
		blocks = app.editor.getSelectedBlocks()
		if not blocks:
			app.editor.selectAll()
			blocks = app.editor.getSelectedBlocks()

		if not blocks:
			tkMessageBox.showerror(_("Tile error"),
				_("No g-code blocks selected"))
			return

		try:
			np = float(self["np"])
		except:
			np = 0.0

		try:
			dpp = float(self["dpp"])
		except:
			dpp = 0.0


		zreg = '(Zz? ?-?(\d+(\.\d+)?))'
		zregexp = re.compile(zreg)

		pos = blocks[-1]
		pos += 1
		for block in blocks:

			newblock = Block(self.name)
			newblocks = []
			for passnum in range(0, int(np), 1):
				for line in app.editor.gcode.blocks[block]:
					z = zregexp.search(line)
					#check if line has a Z value, if so increment/decrement
					if z is not None:
						curzval = z.group(0)
						repzval = (dpp * (passnum + 1)) + float(curzval[1:])
						line = zregexp.sub(lambda match: z.group(0).replace(curzval, 'Z' + str(repzval)), line)
						#append modified line to new block
						newblock.append(line)

				newblocks.append((pos, newblock))
			app.gcode.addBlockUndo(pos, newblocks)
			pos += 1


		app.refresh()
		app.setStatus(_("Multipass blocks are now in the editor"))

