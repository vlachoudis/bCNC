#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Bruno Lahousse 
# Date:		Fev 2024  

__author__ = "Bruno Lahousse"
__email__ = ""

__name__ = _("LaserCut")
__version__ = "1.1"

from CNC import CNC,Block
from ToolsPage import Plugin
from tkinter import messagebox

"""
This plugin prepares gcode for laser cutting or engraving by adding Fxxx and Sxxxx gcode in selected blocks 
It attempts to cleanup all F,S and Z move commands in the selected blocks before F and S commands are added.
When selected, disabled blocks or blocks with no move commands will not be processed for updates.
'Header' and 'Footer' blocks are cleaned up and appended respectively with 'Mx S0' or 'M5' commands if not present. Manual updates to these blocks may be required.
Validated blocks can be repeated to achieve multiple passes, optionnaly with a Z down motion at each pass.

Updates done are as follows :
- 1st block. 
   Line 1: plugin tag ('-- LaserCut --').
   Line 2: G-code with the initial Z position, laser mode (M3 or M4), feed (F parm), power (S parm) values.
   Line n: cleanup all Fnnn,Snnn and Z move commands, check/change M3/M4 commands in tab sections.
- Repeated blocks.
   Line 1: plugin tag.
   Line 2: G-code with laser mode (M3 or M4), feed (F parm), power (S parm) values.
   Lines 3 & 4: G-code for the relative Z down move for each pass.
- Last repeated block.
   Line 1 to 4: Same as the previously repeated blocks.
   Last line: Z move command to the initial Z position.

Blocks already tagged can be modified provided the plugin tag is found in line 1. Repeated blocks are not repeatable.

It is strongly recommended to validate the content of the blocks after each modification.

Field descriptions.
===================
- Name: 
   Name of the current setup. The setup will be stored in the bCNC configuration file used at bCNC startup, default .bCNC.
- XYZ feed rate:
   G1/G2/G3 feed rate in mm/s or inch/s based on bCNC settting.
- Laser Power:
   Value for the laser power level. 
   The value is relative to the parameter $30 set in the GRBL controler.
   Ex: 500 with $30=1000 is 50% laser power. Optionally parameter $30=nnnn can be placed the header block. 
   M3/M4 support is driven by GRBL parameter $32. Optionally this parameter can be set/unset by commands $32=0 or $32=1 in the header block. 
- Laser mode:
   - Auto: use M3 or M4 per the 'Laser Adaptive Power' option set in the CNC configuration panel.
   - M3: constant PWR.
   - M4: dynamique/adaptative mode. 
   M3/M4 support is driven by GRBL parameter $32. Optionally this parameter can be set/unset by commands $32=0 or $32=1 in the header block. 
- Block count:
   Number of copies created for each selected block. Default is 1. Ignored for blocks previously modified by the plugin.
- ZStart:
   Value for the Z move command added at the top of the 1st block and at the end of the last repeated block. Default is 0. 
- Z down step:
   Z down motion command added in the repeated blocks. Value must be positive or null, default is 0.
- Keep Original:
   A disabled copy of the original block is kept if the option is checked.

Procedure to generate tabs created with bCNC for laser cutting/engraving.
=========================================================================
 1) Load file and use the 'Tabs' function with parameter Height = 0
 2) Run 'Cut' function with Surface Z = 0, Target Depth = Depth Increment, First cut at surface height unchecked. 
 3) Run 'LaserCut' plugin to change feed, speed, M3 or M4 commands in the selected blocks and repead selected blocks.

Change log:
Version 1.0: 
	Initial code.
Version 1.1: 
	Call Prepare_Block for the footer block.

"""

#==============================================================================
# Plugin to set laser mode,feed rate and power level for selected blocks.
#==============================================================================
class Tool(Plugin):
	# WARNING the __doc__ is needed to allow the string to be internationalized
	__doc__ = _("""Set laser mode,feed rate and power level""")	# This comment will be show as tooltip for the ribbon button
	
	def __init__(self, master):
		#  DataBase.__init__(self, master, "Stock")
		Plugin.__init__(self, master,"LaserCut")	# LaserCut: is the name of the plugin show in the tool ribbon button.
		self.icon = "lasercut"						# Name of gif file for the ribbon button. Installed in the "icons" subfolder.
		self.group = "CAM"							# This is the name of group that plugin belongs
		#  self.values = {}  # database of values
		#  self.listdb = {}  # lists database

		# Define the list of components for the GUI

		self.variables = [
			("name", "db", "", _("Name")), # Name of the settings stored in the internal database.
			("Feed", "int", 500, _("XYZ feed rate (F parm)")), # Feed rate in mm/s or inch/s based on bCNC setting.
			("Power", "int", 500, _("Power level (S parm)")), # Laser power level.
			("Mode", "Auto,M3,M4", "Auto", _("Laser mode")), # Laser mode. 
			("BlockCount", "int", 1, _("Block count")), # Number of repeated blocks.
			("ZStart", "float", 0, _("Z start position")), # Z start position. 
			("ZDownStep", "float", 0, _("Z down step")), # Z down step for repeated blocks. 
			("BackupBlock", "bool", True, _("Backup original blocks")), # Keep a copy of the original block.
		]
		self.buttons.append("exe")  #  This is the button added at bottom to call the execute method below
		
		self.help = """This plugin prepares gcode for laser cutting or engraving in selected blocks.
It attempts to cleanup all F,S and Z move commands in the selected blocks before F and S commands are added.

Field descriptions:
===================
- Name: Name of the current setup. 
- XYZ feed rate: G1/G2/G3 feed rate in mm/s or inch/s based on bCNC settting. Default is 500.
- Laser Power: Value for the laser power. Default is 500.
- Laser mode: 
   - Auto: use the 'Laser Adaptive Power' option in the  CNC configuration panel. This is the default.
   - M3: constant PWR.
   - M4: dynamique/adaptative mode.
- Block count: Number of copies created for each selected block. Default is 1. Ignored for blocks previously modified by the plugin.
- ZStart: Value for the Z move command added at the top of the 1st block and at the end of the last repeated block. Default is 0.
- Z down step: Z down motion command added in the repeated blocks. Value must be positive or null.
- Keep Original: A disabled copy of the original block is kept if the option is checked.

'Header' and 'Footer' blocks are cleaned up and appended respectively with 'Mx S0' or 'M5' commands if not present. Manual updates to these blocks may be required.

It is strongly recommended to validate the content of the blocks after each modification.
Read file LaserCut.py for more documentation.
"""

	# --------------------------------------------------------------------
	#
	# Prepare a block before it is updated with the user input.
	#
	# --------------------------------------------------------------------
	def Prepare_Block(self,block):
		# ----------------------------------------------------------------
		# Line_Cleanup
		# 	Cleanup Z,F,S commands in line L.
		# 	Replace M3/M4 commands with userLaserMode value.
		#	Delete the line if it only contains Z,F,S commands.
		# ----------------------------------------------------------------
		def Line_Cleanup(L):
			X_Chars = ["Z", "F", "S", "M3", "M4"]
			# Change line L to upper case to simplify cleanup.
			block[L] = block[L].upper()
			### L = block[L]
			for X_Char in X_Chars:
				# Search command begin/end positions.
				X_Index = block[L].find(X_Char)
				if X_Index != -1:
					# Get the last digit position of a command parameter.
					Last_Digit_Index = Find_Last_Digit(X_Index, L)
					# Set X_GIndex when Z,F or S commands are not the last commands in line.
					if (Last_Digit_Index < len(block[L])):
						X_GIndex = X_Index
					else:
						# Check if G command ahead of X_Char command.
						X_GIndex = Find_GIndex(X_Index, L)
					# Line cleanup.
					block[L] = block[L].replace(block[L][X_GIndex:Last_Digit_Index], "")
			return

		# ----------------------------------------------------------------
		#	Returns the index of the G char found before X_Index.
		#	Returns -1 if no G char is found.
		# ----------------------------------------------------------------
		def Find_GIndex(X_Index, L):
			# Search for Gx command ahead of X_Index.
			if X_Index == 0:
				return 0
			G_Index = -1
			G_Offsets = [2, 3]
			for G_Pos in G_Offsets:
				# G char found at position (X_Index - G_Pos).
				if (block[L][X_Index - G_Pos] == "G"):
					G_Index = X_Index - G_Pos
					return G_Index
			# Set G_Index if no Gx immediately precedes the X_Index. Ex G0 X10 Z50.
			if (G_Index == -1) and (block[L][X_Index - 1] == " "):
				G_Index = X_Index
			return G_Index

		# ----------------------------------------------------------------
		#	Returns the index of the last digit of the command parameter.
		#	Number scanned may include '-' or '.' characters.
		# ----------------------------------------------------------------
		def Find_Last_Digit(D_Index, L):
			# d = 2 to skip the 1st digit or possible blank space.
			d = 2
			for i in range(D_Index + d, len(block[L])):
				# Skip '-' or '.'chars.
				if block[L][D_Index + d].isdigit() or block[L][D_Index + d] == "-" or block[L][D_Index + d] == ".":
					d += 1
				if D_Index + d == len(block[L]):
					break
				# Space after the last parameter digit means there could be more command in the line..
				if block[L][D_Index + d] == " ":
					d +=1
					break
			return D_Index + d

		# ----------------------------------------------------------------
		# Cleanup commands in the current block.
		#	X_Chars area contains command types to be deleted.
		# ----------------------------------------------------------------
		L = 0
		while L < (len(block)):
			block[L] = block[L].strip()
			#
			# Update 'tab up' section generated by bCNC. 
			#
			if block[L].startswith("(tab up"):
				block[L] = "(laser off)"
				# Check for M5 command in next line.
				L += 1
				block[L] = block[L].upper()
				# Add M5 command if missing.
				if not block[L].startswith("M5"):
					block.insert(L, "M5")
					L += 1
				# Change G1 command to G0.
				block[L+1] = block[L+1].upper()
				if block[L+1].startswith("G1"):
					block[L+1] = block[L+1].replace("G1","G0")
				continue
			#
			# Update/fix (M3/M4 is sometime missing) 'tab down' section generated by bCNC. 
			#
			if block[L].startswith("(tab down"):
				block[L] = "(laser on)"
				# Change M3/M4 command to userLaserMode in next line.
				L += 1
				block[L] = block[L].upper()
				block[L] = block[L].replace("M3",userLaserMode)
				block[L] = block[L].replace("M4",userLaserMode)
				# Add M3 or M4 command if missing.
				if not (block[L].startswith("M3") or block[L].startswith("M4")):
					block.insert(L, userLaserMode)
				L += 1
				continue
			#
			# Clear line with '(pass ...) text added by the Cut function.
			#
			if block[L].startswith("(pass "):
				block[L] = ""
				continue
			#
			# Skip empty or comment line.
			#
			if (len(block[L]) == 0) or (block[L][0] in "(;"):
				L += 1
				continue
			#
			# Cleanup X_Chars commands in line L.
			#
			Line_Cleanup(L)
			L += 1
		#
		# Delete the empty lines in the current block.
		#
		L = 0
		while L < (len(block)):
			block[L] = block[L].strip()
			if len(block[L]) == 0:
				del(block[L])
				continue
			L += 1
		return


	# --------------------------------------------------------------------
	#
	# Update selected blocks.
	#
	# --------------------------------------------------------------------
	def Update_Selected_Blocks(self, app, Valid_Block_IDs):
		# ----------------------------------------------------------------
		# Process the selected blocks
		# ----------------------------------------------------------------
		Updated_BlockIDs = []
		New_Block_Count = 0	
		New_Block_ID = 0
		undoinfo = []
		Plugin_Tag = "(-- " + __name__ + " --)"
		FS_gcode = userLaserMode + " F" + str(userFeed) + " S" + str(userPower)
		# Retrieve all the blocks.
		All_Blocks = app.gcode.blocks
		#
		# Append command in the Header block to set laser power to 0.
		#
		if All_Blocks[0].name() == "Header":
			self.Prepare_Block(All_Blocks[0])
			if All_Blocks[0][-1].upper() in ("M3 S0", "M4 S0"):
				All_Blocks[0][-1] = All_Blocks[0][-1].replace("M3", userLaserMode)
				All_Blocks[0][-1] = All_Blocks[0][-1].replace("M4", userLaserMode)
			else:
				All_Blocks[0].append(userLaserMode + " S0")
		#
		# Cleanup Z commands and append M5 command to the Footer block.
		#
		if All_Blocks[-1].name() == "Footer":
			self.Prepare_Block(All_Blocks[-1])
			if All_Blocks[-1][-1] != "M5":
				All_Blocks[-1].append("M5")
		#
		# Update the valid blocks.
		#
		for Block_ID in Valid_Block_IDs:
			New_Block_ID = Block_ID + New_Block_Count
			# Show some progress messages.
			if (New_Block_Count % 10 == 0):
				app.setStatus(_("Processing block #" + str(New_Block_ID) + " of " + str(Valid_Block_IDs)))

			block = All_Blocks[New_Block_ID]
			# Disable the original block.
			undoinfo.append(app.gcode.setBlockEnableUndo(Block_ID + New_Block_Count, False))
			#
			# Process blocks not yet tagged. Prepare the source block.
			#
			if block[0] != Plugin_Tag:
				# Take a copy of the source block if userBackupBlock is true.
				if userBackupBlock:
					undoinfo.append(app.gcode.cloneBlockUndo(New_Block_ID,New_Block_ID + 1))
					Updated_BlockIDs.append(Block_ID + New_Block_Count)
					New_Block_Count += 1
				else:
					Updated_BlockIDs.append(Block_ID + New_Block_Count)	
				# Prepare block for laser engrave/cut.
				self.Prepare_Block(block)
				# Update block operation text.
				block.addOperation("lc:" + FS_gcode.lower(), remove=None)
				# Insert line 0 with the plugin tag.
				block.insert(0, Plugin_Tag)
				# Insert line 1 with F/S commands.
				block.insert(1, "G0 Z" + str(userZStart) + " " + FS_gcode)
				#
				# Repeat block per userBlockCount value.
				#
				for n in range(userBlockCount - 1):
					undoinfo.append(app.gcode.cloneBlockUndo(New_Block_ID + n))
					# Add Z step down command in the first repeated blocks. 
					if n == 0:
						block[1] = FS_gcode
						block.insert(2, "G91 G0 Z-" + str(userZDownStep))
						block.insert(3, "G90")
					# Append command to last repeated block to move Z to userZStart position.
					if n == userBlockCount - 2:
						block.append("G0 Z" + str(userZStart))
					# Append repeated block ID to Updated_BlockIDs
					Updated_BlockIDs.append(New_Block_ID + n + 1)
					New_Block_Count += 1
				New_Block_ID = Block_ID + New_Block_Count
			#
			# Process a block already tagged.
			#
			else:
				# Update block name with a new operation text.
				blk_name = block.name()
				splitted_name = blk_name.split("lc:")
				undoinfo.append(app.gcode.setBlockNameUndo(Block_ID, splitted_name[0] + "lc:" + FS_gcode.lower() + "]"))
				# Check if userLaserMode changed. 
				if splitted_name[1][0:2] != userLaserMode:
					#  Update block with new userLaserMode.
					for n in range(len(block)):
						block[n] = block[n].replace("M3", userLaserMode)
						block[n] = block[n].replace("M4", userLaserMode)
				# Update userZStart in Z command in the 1st block.
				if block[1].find("G0 Z") == 0:
					block[1] = "G0 Z" + str(userZStart) + " " + FS_gcode
				else:
					# Update line 1 in a repeated block.
					block[1] = FS_gcode
				# Update Z step down command in a repeated block. 
				if block[2].find("G91 G0 Z-") != - 1:
					block[2] = "G91 G0 Z-" + str(userZDownStep)
				# Update userZStart in Z command in the last repeated block.
				if block[-1].find("G0 Z") != -1:
					block[-1] = "G0 Z" + str(userZStart)
				Updated_BlockIDs.append(Block_ID)

			# Activate the undo list 
			app.addUndo(undoinfo)
		# Refresh editor to update the number of blocks after the updates.
		app.refresh()
		# Select the new blocks.
		app.editor.selectClear()
		for Block_ID in Updated_BlockIDs:
			app.editor.selectBlock(Block_ID)
			undoinfo.append(app.gcode.setBlockEnableUndo(Block_ID, True))
		return len(Updated_BlockIDs)

	# --------------------------------------------------------------------
	#
	# This method is executed when user presses the plugin execute button.
	#
	# --------------------------------------------------------------------
	def execute(self, app):
		# Exit if lasercutter is not set.
		if not CNC.lasercutter:
			messagebox.showerror(_("Lasercut error"), _("Please activate 'Laser Cutter' in the CNC configuration panel and restart bCNC."))
			return
		# Retreive data from user input.
		# Name of the setup.
		global userName
		userName = self["name"]
		if not userName or userName == "default": 
			userName="LaserCut"	
		# Motion speed in mm or inch per minute.
		global userFeed
		userFeed = self["Feed"]
		if not userFeed: userFeed = self.variables[1][2]
		# Laser % power.
		global userPower
		userPower = self["Power"]
		if not userPower: userPower = self.variables[2][2]
		# Laser mode
		global userLaserMode
		userLaserMode = self["Mode"]
		if not userLaserMode: userLaserMode = self.variables[3][2]
		if userLaserMode == "Auto":
			if CNC.laseradaptive: userLaserMode = "M4"
			else: userLaserMode = "M3"
		# Number of repeat for the valid selected blocks.
		global userBlockCount
		userBlockCount = self["BlockCount"]
		if not userBlockCount: userBlockCount = self.variables[4][2]
		# Z start position
		global userZStart
		userZStart = self["ZStart"]
		if not userZStart: userZStart = self.variables[5][2]
		# Z down step added to each repeated blocks.
		global userZDownStep
		userZDownStep = self["ZDownStep"]
		if not userZDownStep: userZDownStep = self.variables[6][2]
		# Backup the original block is true.
		global userBackupBlock
		userBackupBlock = self["BackupBlock"]
		
		# Get the IDs of the selected blocks from editor.
		Selected_Blocks = app.editor.getSelectedBlocks()
		Active_Blocks = app.editor.getActive()
		# Keep the valid blocks.
		Valid_Block_IDs = []
		for Block_ID in Selected_Blocks:
			# Skip blocks disabled or with no motion commands.
			if (len(app.gcode.toPath(Block_ID)) < 1) or (app.gcode.blocks[Block_ID].enable == False):
				continue
			Valid_Block_IDs.append(Block_ID)
		if not Valid_Block_IDs:
			messagebox.showerror(_("Lasercut error"), _("No valid block selected."))
			return
		#
		# Update the valid blocks.
		#
		n = self.Update_Selected_Blocks(app, Valid_Block_IDs)
		# Refresh editor & display result in the status bar.
		app.refresh()
		app.setStatus(_(str(n) + " block(s) updated."))
		return
