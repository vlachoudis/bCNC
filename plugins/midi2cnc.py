#!/usr/bin/python
# -*- coding: ascii -*-
# $Id$
#
# Author:	Filippo Rivato
# Date: 20Dicember 2015
# Porting of midi2cnc https://github.com/michthom/MIDI-to-CNC

__author__ = "Filippo Rivato"
__email__  = "f.rivato@gmail.com"

__name__ = "Midi2CNC"
__version__= "0.0.1"

from ToolsPage import DataBase

import math
from bmath import Vector
from CNC import CNC,Block
from ToolsPage import Plugin

#==============================================================================
#Midi2CNC class
#==============================================================================
class Midi2CNC:
	def __init__(self,name="Midi2CNC"):
		self.name = name

#==============================================================================
# Create pyrograph
#==============================================================================
class Tool(Plugin):
	__doc__ = _("Sound your machine from a midi file")
	def __init__(self, master):
		Plugin.__init__(self, master)
		self.name  = "Midi2CNC"
		self.icon  = "midi2cnc"
		self.group = "Artistic"

		self.axes_dict = dict( {
		'X':[0],       'Y':[1],    'Z':[2],
		'XY':[0,1],    'YX':[1,0], 'XZ':[0,2],
		'ZX':[2,0],    'YZ':[1,2], 'ZY':[2,1],
		'XYZ':[0,1,2], 'XZY':[0,2,1],
		'YXZ':[1,0,2], 'YZX':[1,2,0],
		'ZXY':[2,0,1], 'ZYX':[2,1,0]
		})

		self.variables = [
			("name",	 "db" ,	   "", _("Name")),
			("ppu_X"  ,   "float" , 200.0, _("Pulse per unit for X")),
			("ppu_Y"  ,   "float" , 200.0, _("Pulse per unit for Y")),
			("ppu_Z"  ,  "float" ,  200.0, _("Pulse per unit for Z")),
			("max_X"  ,  "int" ,       50, _("Maximum X travel")),
			("max_Y"  ,  "int" ,       50, _("Maximum Y travel")),
			("max_Z"  ,  "int" ,       20, _("Maximum Z travel")),
			("AxisUsed", ",".join(self.axes_dict.keys()), "XYZ", _("Axis to be used")),
			("File"  ,   "file" ,	   "", _("Midi to process")),
		]
		self.buttons.append("exe")

	# ----------------------------------------------------------------------
	def reached_limit(self,current, distance, direction, min, max):
		# Returns true if the proposed movement will exceed the
		# safe working limits of the machine but the movement is
		# allowable in the reverse direction
		#
		# Returns false if the movement is allowable in the
		# current direction
		#
		# Aborts if the movement is not possible in either direction

		if ( ( (current + (distance * direction)) < max ) and
			 ( (current + (distance * direction)) > min ) ):
			# Movement in the current direction is within safe limits,
			return False

		elif ( ( (current + (distance * direction)) >= max ) and
			   ( (current - (distance * direction)) >  min ) ):
			# Movement in the current direction violates maximum safe
			# value, but would be safe if the direction is reversed
			return True

		elif ( ( (current + (distance * direction)) <= min ) and
			   ( (current - (distance * direction)) <  max ) ):
			# Movement in the current direction violates minimum safe
			# value, but would be safe if the direction is reversed
			return True

		else:
			# Movement in *either* direction violates the safe working
			# envelope, so abort.
			exit(2);

	# ----------------------------------------------------------------------
	def execute(self, app):
		try:
			import midiparser as midiparser
		except:
			app.setStatus(_("Error: This plugin requires midiparser.py"))
			return

		n = self["name"]
		if not n or n=="default": n="Midi2CNC"

		fileName = self["File"]

		x=0.0
		y=0.0
		z=0.0

		x_dir=1.0;
		y_dir=1.0;
		z_dir=1.0;

		# List of MIDI channels (instruments) to import.
		# Channel 10 is percussion, so better to omit it
		channels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] 

		axes = self["AxisUsed"]
		active_axes = len(axes)

		transpose = (0,0,0)
		ppu = [ 200, 200, 200 ]
		ppu[0] = self["ppu_X"]
		ppu[1] = self["ppu_X"]
		ppu[2] = self["ppu_X"]

		safemin = [ 0, 0, 0 ]
		safemax = [ 100, 100, 50 ]
		safemax[0] = self["max_X"]
		safemax[1] = self["max_Y"]
		safemax[2] = self["max_Z"]

		try:
			midi = midiparser.File(fileName)
		except:
			app.setStatus(_("Error: Sorry can't parse the Midi file."))
			return

		noteEventList=[]
		all_channels=set()

		for track in midi.tracks:
			#channels=set()
			for event in track.events:
				if event.type == midiparser.meta.SetTempo:
					tempo=event.detail.tempo

				# filter undesired instruments
				if ((event.type == midiparser.voice.NoteOn) and (event.channel in channels)):

					if event.channel not in channels:
						channels.add(event.channel)

					# NB: looks like some use "note on (vel 0)" as equivalent to note off, so check for vel=0 here and treat it as a note-off.
					if event.detail.velocity > 0:
						noteEventList.append([event.absolute, 1, event.detail.note_no, event.detail.velocity])
					else:
						noteEventList.append([event.absolute, 0, event.detail.note_no, event.detail.velocity])

				if (event.type == midiparser.voice.NoteOff) and (event.channel in channels):
					if event.channel not in channels:
						channels.add(event.channel)
					noteEventList.append([event.absolute, 0, event.detail.note_no, event.detail.velocity])

			# Finished with this track
			if len(channels) > 0:
				msg=', ' . join(['%2d' % ch for ch in sorted(channels)])
				#print 'Processed track %d, containing channels numbered: [%s ]' % (track.number, msg)
				all_channels = all_channels.union(channels)

		# List all channels encountered
		if len(all_channels) > 0:
			msg=', ' . join(['%2d' % ch for ch in sorted(all_channels)])
			#print 'The file as a whole contains channels numbered: [%s ]' % msg

		# We now have entire file's notes with abs time from all channels
		# We don't care which channel/voice is which, but we do care about having all the notes in order
		# so sort event list by abstime to dechannelify

		noteEventList.sort()
		# print noteEventList
		# print len(noteEventList)

		last_time=-0
		active_notes={} # make this a dict so we can add and remove notes by name

		# Start the output
		#Init blocks
		blocks = []
		block = Block(self.name)
		block.append("(Midi2CNC)")
		block.append("(Midi:%s)" % fileName)
		block.append(CNC.zsafe())
		block.append(CNC.grapid(0,0))
		block.append(CNC.zenter(0))

		for note in noteEventList:
			# note[timestamp, note off/note on, note_no, velocity]
			if last_time < note[0]:

				freq_xyz=[0,0,0]
				feed_xyz=[0,0,0]
				distance_xyz=[0,0,0]
				duration=0

				# "i" ranges from 0 to "the number of active notes *or* the number of active axes,
				# whichever is LOWER". Note that the range operator stops
				# short of the maximum, so this means 0 to 2 at most for a 3-axis machine.
				# E.g. only look for the first few active notes to play despite what
				# is going on in the actual score.

				for i in range(0, min(len(active_notes.values()), active_axes)):

					# Which axis are should we be writing to?
					#
					j = self.axes_dict.get(axes)[i]

					# Debug
					# print"Axes %s: item %d is %d" % (axes_dict.get(args.axes), i, j)

					# Sound higher pitched notes first by sorting by pitch then indexing by axis
					#
					nownote=sorted(active_notes.values(), reverse=True)[i]

					# MIDI note 69	 = A4(440Hz)
					# 2 to the power (69-69) / 12 * 440 = A4 440Hz
					# 2 to the power (64-69) / 12 * 440 = E4 329.627Hz
					#
					freq_xyz[j] = pow(2.0, (nownote-69 + transpose[j])/12.0)*440.0

					# Here is where we need smart per-axis feed conversions
					# to enable use of X/Y *and* Z on a Makerbot
					#
					# feed_xyz[0] = X; feed_xyz[1] = Y; feed_xyz[2] = Z;
					#
					# Feed rate is expressed in mm / minutes so 60 times
					# scaling factor is required.

					feed_xyz[j] = ( freq_xyz[j] * 60.0 ) / ppu[j]

					# Get the duration in seconds from the MIDI values in divisions, at the given tempo
					duration = ( ( ( note[0] - last_time ) + 0.0 ) / ( midi.division + 0.0 ) * ( tempo / 1000000.0 ) )

					# Get the actual relative distance travelled per axis in mm
					distance_xyz[j] = ( feed_xyz[j] * duration ) / 60.0

				# Now that axes can be addressed in any order, need to make sure
				# that all of them are silent before declaring a rest is due.
				if distance_xyz[0] + distance_xyz[1] + distance_xyz[2] > 0:
					# At least one axis is playing, so process the note into
					# movements
					combined_feedrate = math.sqrt(feed_xyz[0]**2 + feed_xyz[1]**2 + feed_xyz[2]**2)

					# Turn around BEFORE crossing the limits of the
					# safe working envelope
					if self.reached_limit( x, distance_xyz[0], x_dir, safemin[0], safemax[0] ):
						x_dir = x_dir * -1
					x = (x + (distance_xyz[0] * x_dir))

					if self.reached_limit( y, distance_xyz[1], y_dir, safemin[1], safemax[1] ):
						y_dir = y_dir * -1
					y = (y + (distance_xyz[1] * y_dir))

					if self.reached_limit( z, distance_xyz[2], z_dir, safemin[2], safemax[2] ):
						z_dir = z_dir * -1
					z = (z + (distance_xyz[2] * z_dir))

					v = (x,y,z)
					block.append(CNC.glinev(1,v,combined_feedrate))

				else:
					# Handle 'rests' in addition to notes.
					duration = (((note[0]-last_time)+0.0)/(midi.division+0.0)) * (tempo/1000000.0)
					block.append(CNC.gcode(4, [("P",duration)]))

				# finally, set this absolute time as the new starting time
				last_time = note[0]

			if note[1]==1: # Note on
				if active_notes.has_key(note[2]):
					pass
				else:
					# key and value are the same, but we don't really care.
					active_notes[note[2]]=note[2]
			elif note[1]==0: # Note off
				if(active_notes.has_key(note[2])):
					active_notes.pop(note[2])

		blocks.append(block)
		active = app.activeBlock()
		if active==0: active=1
		app.gcode.insBlocks(active, blocks, "Midi2CNC")
		app.refresh()
		app.setStatus(_("Generated Midi2CNC, ready to play?"))
