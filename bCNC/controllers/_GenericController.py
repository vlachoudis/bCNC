# Generic motion controller definition
# All controller plugins inherit features from this one

import re
import time

from CNC import CNC, WCS

import Utils

# GRBLv1
SPLITPAT = re.compile(r"[:,]")

# GRBLv0 + Smoothie
STATUSPAT = re.compile(
    r"^<(\w*?),MPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*)(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?,WPos:([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*)(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?(?:,.*)?>$"
)
POSPAT = re.compile(
    r"^\[(...):([+\-]?\d*\.\d*),([+\-]?\d*\.\d*),([+\-]?\d*\.\d*)(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?(?:,[+\-]?\d*\.\d*)?(:(\d*))?\]$"
)
# FIXME: add example for strings this regexes shall convert

TLOPAT = re.compile(r"^\[(...):([+\-]?\d*\.\d*)\]$")
DOLLARPAT = re.compile(r"^\[G\d* .*\]$")

# Only used in this file
VARPAT = re.compile(r"^\$(\d+)=(\d*\.?\d*) *\(?.*")


class _GenericController:
    def test(self):
        print("test supergen")

    def initController(self):
        text = Utils.getStr("Controller","initstring")
        if text:
            # Deal with a device in feedhold from prior session
            self.master.serial_write("%~\n")
            time.sleep(1)
            # And write out the firmware config
            self.master.serial_write(text)

    def setTLO(self, tlo):
        self.master.sendGCode(f"G43.1Z{tlo}")    

    def executeCommand(self, oline, line, cmd):
        return False

    def hardResetPre(self):
        pass

    def hardResetAfter(self):
        pass

    def viewStartup(self):
        pass

    def checkGcode(self):
        pass

    def viewSettings(self):
        pass

    def grblRestoreSettings(self):
        pass

    def grblRestoreWCS(self):
        pass

    def grblRestoreAll(self):
        pass

    def purgeControllerExtra(self):
        pass

    def overrideSet(self):
        pass

    def hardReset(self):
        self.master.busy()
        if self.master.serial is not None:
            self.hardResetPre()
            self.master.openClose()
            self.hardResetAfter()
        self.master.openClose()
        self.master.stopProbe()
        self.master._alarm = False
        CNC.vars["_OvChanged"] = True  # force a feed change if any
        self.master.notBusy()

    # ----------------------------------------------------------------------
    def softReset(self, clearAlarm=True):
        if self.master.serial:
            self.master.serial_write(b"\030")
        self.master.stopProbe()
        if clearAlarm:
            self.master._alarm = False
        CNC.vars["_OvChanged"] = True  # force a feed change if any

    # ----------------------------------------------------------------------
    def unlock(self, clearAlarm=True):
        if clearAlarm:
            self.master._alarm = False
        self.master.sendGCode("$X")

    # ----------------------------------------------------------------------
    def home(self, event=None):
        self.master._alarm = False
        self.master.sendGCode("$H")

    def viewStatusReport(self):
        self.master.serial_write(b"?")
        self.master.sio_status = True

    def viewParameters(self):
        self.master.sendGCode("$#")

    def viewState(self):  # Maybe rename to viewParserState() ???
        self.master.sendGCode("$G")

    # ----------------------------------------------------------------------
    def jog(self, direction):
        self.master.sendGCode(f"G91G0{direction}")
        self.master.sendGCode("G90")

    # ----------------------------------------------------------------------
    def goto(self, x=None, y=None, z=None, a=None, b=None, c=None):
        cmd = "G90G0"
        if x is not None:
            cmd += f"X{x:g}"
        if y is not None:
            cmd += f"Y{y:g}"
        if z is not None:
            cmd += f"Z{z:g}"
        if a is not None:
            cmd += f"A{a:g}"
        if b is not None:
            cmd += f"B{b:g}"
        if c is not None:
            cmd += f"C{c:g}"
        self.master.sendGCode(f"{cmd}")

    # ----------------------------------------------------------------------
    def _wcsSet(self, x, y, z, a=None, b=None, c=None):
        p = WCS.index(CNC.vars["WCS"])
        if p < 6:
            cmd = "G10L20P%d" % (p + 1)
        elif p == 6:
            cmd = "G28.1"
        elif p == 7:
            cmd = "G30.1"
        elif p == 8:
            cmd = "G92"

        pos = ""
        if x is not None and abs(float(x)) < 10000.0:
            pos += "X" + str(x)
        if y is not None and abs(float(y)) < 10000.0:
            pos += "Y" + str(y)
        if z is not None and abs(float(z)) < 10000.0:
            pos += "Z" + str(z)
        if a is not None and abs(float(a)) < 10000.0:
            pos += "A" + str(a)
        if b is not None and abs(float(b)) < 10000.0:
            pos += "B" + str(b)
        if c is not None and abs(float(c)) < 10000.0:
            pos += "C" + str(c)
        cmd += pos
        self.master.sendGCode(cmd)
        self.viewParameters()
        self.master.event_generate(
            "<<Status>>",
            data=(_("Set workspace {} to {}").format(WCS[p], pos))
        )
        self.master.event_generate("<<CanvasFocus>>")

    # ----------------------------------------------------------------------
    def feedHold(self, event=None):
        if event is not None and not self.master.acceptKey(True):
            return
        if self.master.serial is None:
            return
        self.master.serial_write(b"!")
        self.master.serial.flush()
        self.master._pause = True

    # ----------------------------------------------------------------------
    def resume(self, event=None):
        if event is not None and not self.master.acceptKey(True):
            return
        if self.master.serial is None:
            return
        self.master.serial_write(b"~")
        self.master.serial.flush()
        self.master._msg = None
        self.master._alarm = False
        self.master._pause = False

    # ----------------------------------------------------------------------
    def pause(self, event=None):
        if self.master.serial is None:
            return
        if self.master._pause:
            self.master.resume()
        else:
            self.master.feedHold()

    # ----------------------------------------------------------------------
    # Purge the buffer of the controller. Unfortunately we have to perform
    # a reset to clear the buffer of the controller
    # ---------------------------------------------------------------------
    def purgeController(self):
        self.master.serial_write(b"!")
        self.master.serial.flush()
        time.sleep(1)
        # remember and send all G commands
        G = " ".join([x for x in CNC.vars["G"] if x[0] == "G"])  # remember $G
        TLO = CNC.vars["TLO"]
        self.softReset(False)  # reset controller
        self.purgeControllerExtra()
        self.master.runEnded()
        self.master.stopProbe()
        if G:
            self.master.sendGCode(G)  # restore $G
        self.master.sendGCode(f"G43.1Z{TLO}")  # restore TLO
        self.viewState()
        self.viewParameters()

    # ----------------------------------------------------------------------
    def displayState(self, state):
        state = state.strip()

        # Do not show g-code errors, when machine is already in alarm state
        if (CNC.vars["state"].startswith("ALARM:")
                and state.startswith("error:")):
            print(f"Suppressed: {state}")
            return

        # Do not show alarm without number when we already
        # display alarm with number
        if state == "Alarm" and CNC.vars["state"].startswith("ALARM:"):
            return

        CNC.vars["state"] = state

    # ----------------------------------------------------------------------
    def parseLine(self, line, cline, sline):
        if not line:
            return True

        elif line[0] == "<":
            if not self.master.sio_status:
                self.master.log.put((self.master.MSG_RECEIVE, line))
            else:
                self.parseBracketAngle(line, cline)

        elif line[0] == "[":
            self.master.log.put((self.master.MSG_RECEIVE, line))
            self.parseBracketSquare(line)

        elif "error:" in line or "ALARM:" in line:
            self.master.log.put((self.master.MSG_ERROR, line))
            self.master._gcount += 1
            if cline:
                del cline[0]
            if sline:
                CNC.vars["errline"] = sline.pop(0)
            if not self.master._alarm:
                self.master._posUpdate = True
            self.master._alarm = True
            self.displayState(line)
            if self.master.running:
                self.master._stop = True

        elif line.find("ok") >= 0:
            self.master.log.put((self.master.MSG_OK, line))
            self.master._gcount += 1
            if cline:
                del cline[0]
            if sline:
                del sline[0]

        elif line[0] == "$":
            self.master.log.put((self.master.MSG_RECEIVE, line))
            pat = VARPAT.match(line)
            if pat:
                CNC.vars[f"grbl_{pat.group(1)}"] = pat.group(2)

        elif line[:4] == "Grbl" or line[:13] == "CarbideMotion":
            self.master.log.put((self.master.MSG_RECEIVE, line))
            self.master._stop = True
            del cline[:]  # After reset clear the buffer counters
            del sline[:]
            CNC.vars["version"] = line.split()[1]
            # Detect controller
            if self.master.controller in ("GRBL0", "GRBL1"):
                self.master.controllerSet(
                    "GRBL%d" % (int(CNC.vars["version"][0])))

        else:
            # We return false in order to tell that we can't parse this line
            # Sender will log the line in such case
            return False

        # Parsing successful
        return True
