# Placed into Public Domain in June 2006 by Sean D. Spencer

# Sean D. Spencer
# sean_don4@lycos.com
# 2/19/2006
# Last Revision: 4/19/2007

# MIDI Parsing Library for Python.

TRUE = -1
FALSE = 0


class format_:
    SingleTrack = 0
    MultipleTracksSync = 1
    MultipleTracksAsync = 2


class voice:
    NoteOff = 0x80
    NoteOn = 0x90
    PolyphonicKeyPressure = 0xA0  # note aftertouch
    ControllerChange = 0xB0
    ProgramChange = 0xC0
    ChannelPressure = 0xD0
    PitchBend = 0xE0


class meta:
    FileMetaEvent = 0xFF
    SMPTEOffsetMetaEvent = 0x54
    SystemExclusive = 0xF0
    SystemExclusivePacket = 0xF7
    SequenceNumber = 0x00
    TextMetaEvent = 0x01
    CopyrightMetaEvent = 0x02
    TrackName = 0x03
    InstrumentName = 0x04
    Lyric = 0x05
    Marker = 0x06
    CuePoint = 0x07
    ChannelPrefix = 0x20
    MidiPort = 0x21
    EndTrack = 0x2F
    SetTempo = 0x51
    TimeSignature = 0x58
    KeySignature = 0x59
    SequencerSpecificMetaEvent = 0x7F


class EventNote:
    def __init__(self):
        self.note_no = None
        self.velocity = None


class EventValue:
    def __init__(self):
        self.type_ = None
        self.value = None


class EventAmount:
    def __init__(self):
        self.amount = None


class MetaEventKeySignature:
    def __init__(self):
        self.fifths = None
        self.mode = None


class MetaEventTimeSignature:
    def __init__(self):
        self.numerator = None
        self.log_denominator = None
        self.midi_clocks = None
        self.thirty_seconds = None


class MetaEventText:
    def __init__(self):
        self.length = None
        self.text = None


class MetaEventSMPTEOffset:
    def __init__(self):
        self.hour = None
        self.minute = None
        self.second = None
        self.frame = None
        self.sub_frame = None


class MetaValues:
    def __init__(self):
        self.length = None
        self.values = None


def getNumber(theString, length):
    # MIDI uses big-endian for everything
    sum_ = 0
    for i in range(length):
        sum_ = (sum_ << 8) + ord(theString[i])
    return sum_, theString[length:]


def getVariableLengthNumber(str_):
    sum_ = 0
    i = 0
    while 1:
        x = ord(str_[i])
        i = i + 1
        sum_ = (sum_ << 7) + (x & 0x7F)
        # Is 7th bit clear?
        if not (x & 0x80):
            return sum_, str_[i:]


def getValues(str_, n=16):
    temp = []
    for x in str_[:n]:
        temp.append(repr(ord(x)))
    return temp


class File:
    def __init__(self, file):
        self.file = file
        self.format = None
        self.num_tracks = None
        self.division = None
        self.tracks = []

        self.file = open(self.file, "rb")
        str_ = self.file.read()
        self.file.close()

        self.read(str_)

    def read(self, str_):
        assert str_[:4] == "MThd"
        str_ = str_[4:]

        length, str_ = getNumber(str_, 4)
        assert length == 6

        self.format, str_ = getNumber(str_, 2)

        self.num_tracks, str_ = getNumber(str_, 2)
        self.division, str_ = getNumber(str_, 2)

        for i in range(self.num_tracks):
            track = Track(i + 1)
            str_ = track.read(str_)
            self.tracks.append(track)


class Track:
    def __init__(self, index):
        self.number = index
        self.length = None
        self.events = []

    def read(self, str_):
        self.length, str_ = getNumber(str_[4:], 4)
        track_str = str_[: self.length]

        prev_absolute = 0
        prev_status = 0

        i = 0
        while track_str:
            event = Event(self.number, i + 1)
            track_str = event.read(prev_absolute, prev_status, track_str)

            prev_absolute += event.delta
            prev_status = event.status
            self.events.append(event)
            i += 1

        return str_[self.length:]


class Event:
    def __init__(self, track, index):
        self.number = index
        self.type_ = None
        self.delta = None
        self.absolute = None
        self.status = None
        self.channel = None

    def read(self, prev_time, prev_status, str_):
        self.delta, str_ = getVariableLengthNumber(str_)
        self.absolute = prev_time + self.delta

        # use running status?
        if not (ord(str_[0]) & 0x80):
            # squeeze a duplication of the running status into the data string
            str_ = prev_status + str_

        self.status = str_[0]
        self.channel = ord(self.status) & 0xF

        # increment one byte, past the status
        str_ = str_[1:]

        has_channel = has_meta = TRUE

        # handle voice events
        channel_msg = ord(self.status) & 0xF0
        if (
            channel_msg == voice.NoteOn
            or channel_msg == voice.NoteOff
            or channel_msg == voice.PolyphonicKeyPressure
        ):
            self.detail = EventNote()
            self.detail.note_no = ord(str_[0])
            self.detail.velocity = ord(str_[1])
            str_ = str_[2:]

        elif channel_msg == voice.ControllerChange:
            self.detail = EventValue()
            self.detail.type_ = ord(str_[0])
            self.detail.value = ord(str_[1])
            str_ = str_[2:]

        elif (channel_msg == voice.ProgramChange
              or channel_msg == voice.ChannelPressure):
            self.detail = EventAmount()
            self.detail.amount = ord(str_[0])
            str_ = str_[1:]

        elif channel_msg == voice.PitchBend:
            # Pitch bend uses high accuracy 14 bit unsigned integer.
            self.detail = EventAmount()
            self.detail.amount = (ord(str_[0]) << 7) | ord(str_[1])
            str_ = str_[2:]

        else:
            has_channel = FALSE

        # handle meta events
        meta_msg = ord(self.status)
        if meta_msg == meta.FileMetaEvent:

            meta_msg = type_ = ord(str_[0])
            length, str_ = getVariableLengthNumber(str_[1:])

            if type_ == meta.SetTempo or type_ == meta.ChannelPrefix:

                self.detail = EventAmount()
                self.detail.tempo, str_ = getNumber(str_, length)

            elif type_ == meta.KeySignature:
                self.detail = MetaEventKeySignature()
                self.detail.fifths = ord(str_[0])

                if ord(str_[1]):
                    self.detail.mode = "minor"
                else:
                    self.detail.mode = "major"

                str_ = str_[length:]

            elif type_ == meta.TimeSignature:
                self.detail = MetaEventTimeSignature()
                self.detail.numerator = ord(str_[0])
                self.detail.log_denominator = ord(str_[1])
                self.detail.midi_clocks = ord(str_[2])
                self.detail.thirty_seconds = ord(str_[3])
                str_ = str_[length:]

            elif (
                type_ == meta.TrackName
                or type_ == meta.TextMetaEvent
                or type_ == meta.Lyric
                or type_ == meta.CuePoint
                or type_ == meta.CopyrightMetaEvent
            ):

                self.detail = MetaEventText()
                self.detail.length = length
                self.detail.text = str_[:length]
                str_ = str_[length:]

            elif type_ == meta.SMPTEOffsetMetaEvent:
                self.detail = MetaEventSMPTEOffset()
                self.detail.hour = ord(str_[0])
                self.detail.minute = ord(str_[1])
                self.detail.second = ord(str_[2])
                self.detail.frame = ord(str_[3])
                self.detail.sub_frame = ord(str_[4])
                str_ = str_[length:]

            elif type_ == meta.EndTrack:
                str_ = str_[length:]  # pass on to next track

            else:
                has_meta = FALSE

        elif (meta_msg == meta.SystemExclusive
              or meta_msg == meta.SystemExclusivePacket):
            self.detail = MetaValues()
            self.detail.length, str_ = getVariableLengthNumber(str_)
            self.detail.values = getValues(str_, self.detail.length)
            str_ = str_[self.detail.length:]

        else:
            has_meta = FALSE

        if has_channel:
            self.type_ = channel_msg
        elif has_meta:
            self.type_ = meta_msg
        else:
            # raise "Unknown event."
            self.type_ = None
        return str_
