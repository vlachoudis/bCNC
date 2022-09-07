# Generic GRBL motion controller definition
# All GRBL versions inherit features from this one

import time

from _GenericController import _GenericController

# From https://github.com/grbl/grbl/wiki/Interfacing-with-Grbl
# and  https://github.com/terjeio/grblHAL
ERROR_CODES = {
    "Run": _("bCNC is currently sending a gcode program to Grbl"),
    "Idle": _("Grbl is in idle state and waiting for user commands"),
    "Hold": _("Grbl is on hold state. Click on resume (pause) to continue"),
    "Alarm": _(
        "Alarm is an emergency state. Something has gone terribly wrong when these occur. Typically, they are caused by limit error when the machine has moved or wants to move outside the machine space and crash into something. They also report problems if Grbl is lost and can't guarantee positioning or a probe command has failed. Once in alarm-mode, Grbl will lock out and shut down everything until the user issues a reset. Even after a reset, Grbl will remain in alarm-mode, block all G-code from being executed, but allows the user to override the alarm manually. This is to ensure the user knows and acknowledges the problem and has taken steps to fix or account for it."
    ),
    "Check": _(
        "Grbl is in g-code check mode. If you send g-code to it, it will only check it without actually doing any motion. You can exit this by $C command (Or equivalent button in terminal tab)"
    ),
    "Jog": _("Grbl executes jogging motion"),
    "Sleep": _(
        "Grbl is in sleep mode. Motors are disabled, so you can move them manually. That also means that your machine might have lost the position (or microsteps) and you may need to re-zero. Perform reset+unlock (or stop) to wake Grbl again."
    ),
    "Queue": _(
        "Grbl is in queue state. This also means you have relatively old GRBL version, there are even 0.9 versions newer than this."
    ),
    "Not connected": _(
        "Grbl is not connected. Please specify the correct port and click Open."
    ),
    "Connected": _("Connection is established with Grbl"),
    "ok": _(
        "All is good! Everything in the last line was understood by Grbl and was successfully processed and executed."
    ),
    "error:1": _("G-code words consist of a letter and a value. Letter was not found."),
    "error:2": _("Numeric value format is not valid or missing an expected value."),
    "error:3": _("Grbl '$' system command was not recognized or supported."),
    "error:4": _("Negative value received for an expected positive value."),
    "error:5": _("Homing cycle is not enabled via settings."),
    "error:6": _("Minimum step pulse time must be greater than 3usec"),
    "error:7": _("EEPROM read failed. Reset and restored to default values."),
    "error:8": _(
        "Grbl '$' command cannot be used unless Grbl is IDLE. Ensures smooth operation during a job."
    ),
    "error:9": _("G-code locked out during alarm or jog state"),
    "error:10": _("Soft limits cannot be enabled without homing also enabled."),
    "error:11": _(
        "Max characters per line exceeded. Line was not processed and executed."
    ),
    "error:12": _(
        "(Compile Option) Grbl '$' setting value exceeds the maximum step rate supported."
    ),
    "error:13": _("Safety door detected as opened and door state initiated."),
    "error:14": _(
        "(Grbl-Mega Only) Build info or startup line exceeded EEPROM line length limit."
    ),
    "error:15": _("Jog target exceeds machine travel. Command ignored."),
    "error:16": _("Jog command with no '=' or contains prohibited g-code."),
    "error:17": _("Laser mode requires PWM output."),
    "error:20": _("Unsupported or invalid g-code command found in block."),
    "error:21": _("More than one g-code command from same modal group found in block."),
    "error:22": _("Feed rate has not yet been set or is undefined."),
    "error:23": _("G-code command in block requires an integer value."),
    "error:24": _(
        "Two G-code commands that both require the use of the XYZ axis words were detected in the block."
    ),
    "error:25": _("A G-code word was repeated in the block."),
    "error:26": _(
        "A G-code command implicitly or explicitly requires XYZ axis words in the block, but none were detected."
    ),
    "error:27": _(
        "N line number value is not within the valid range of 1 - 9,999,999."
    ),
    "error:28": _(
        "A G-code command was sent, but is missing some required P or L value words in the line."
    ),
    "error:29": _(
        "Grbl supports six work coordinate systems G54-G59. G59.1, G59.2, and G59.3 are not supported."
    ),
    "error:30": _(
        "The G53 G-code command requires either a G0 seek or G1 feed motion mode to be active. A different motion was active."
    ),
    "error:31": _(
        "There are unused axis words in the block and G80 motion mode cancel is active."
    ),
    "error:32": _(
        "A G2 or G3 arc was commanded but there are no XYZ axis words in the selected plane to trace the arc."
    ),
    "error:33": _(
        "The motion command has an invalid target. G2, G3, and G38.2 generates this error, if the arc is impossible to generate or if the probe target is the current position."
    ),
    "error:34": _(
        "A G2 or G3 arc, traced with the radius definition, had a mathematical error when computing the arc geometry. Try either breaking up the arc into semi-circles or quadrants, or redefine them with the arc offset definition."
    ),
    "error:35": _(
        "A G2 or G3 arc, traced with the offset definition, is missing the IJK offset word in the selected plane to trace the arc."
    ),
    "error:36": _(
        "There are unused, leftover G-code words that aren't used by any command in the block."
    ),
    "error:37": _(
        "The G43.1 dynamic tool length offset command cannot apply an offset to an axis other than its configured axis. The Grbl default axis is the Z-axis."
    ),
    "error:38": _(
        "Tool number greater than max supported value or undefined tool selected. (grblHAL)"
    ),
    "error:39": _("Value out of range. (grblHAL)"),
    "error:40": _("G-code command not allowed when tool change is pending. (grblHAL)"),
    "error:41": _(
        "Spindle not running when motion commanded in CSS or spindle sync mode. (grblHAL)"
    ),
    "error:42": _("Plane must be ZX for threading. (grblHAL)"),
    "error:43": _("Max. feed rate exceeded. (grblHAL)"),
    "error:44": _("RPM out of range. (grblHAL)"),
    "error:45": _("Only homing is allowed when a limit switch is engaged. (grblHAL)"),
    "error:46": _("Home machine to continue. (grblHAL)"),
    "error:47": _("ATC: current tool is not set. Set current tool with M61. (grblHAL)"),
    "error:48": _("Value word conflict. (grblHAL)"),
    "error:50": _("Emergency stop active. (grblHAL)"),
    "error:59": _("(grblHAL internal)"),
    "error:60": _("SD Card mount failed. (grblHAL bdring)"),
    "error:61": _("SD Card file open/read failed. (grblHAL bdring)"),
    "error:62": _("SD Card directory listing failed. (grblHAL bdring)"),
    "error:63": _("SD Card directory not found. (grblHAL bdring)"),
    "error:64": _("SD Card file empty. (grblHAL bdring)"),
    "error:70": _("Bluetooth initialisation failed. (grblHAL bdring)"),
    "ALARM:1": _(
        "Hard limit triggered. Machine position is likely lost due to sudden and immediate halt. Re-homing is highly recommended."
    ),
    "ALARM:2": _(
        "G-code motion target exceeds machine travel. Machine position safely retained. Alarm may be unlocked."
    ),
    "ALARM:3": _(
        "Reset while in motion. Grbl cannot guarantee position. Lost steps are likely. Re-homing is highly recommended."
    ),
    "ALARM:4": _(
        "Probe fail. The probe is not in the expected initial state before starting probe cycle, where G38.2 and G38.3 is not triggered and G38.4 and G38.5 is triggered."
    ),
    "ALARM:5": _(
        "Probe fail. Probe did not contact the workpiece within the programmed travel for G38.2 and G38.4."
    ),
    "ALARM:6": _("Homing fail. Reset during active homing cycle."),
    "ALARM:7": _("Homing fail. Safety door was opened during active homing cycle."),
    "ALARM:8": _(
        "Homing fail. Cycle failed to clear limit switch when pulling off. Try increasing pull-off setting or check wiring."
    ),
    "ALARM:9": _(
        "Homing fail. Could not find limit switch within search distance. Defined as 1.5 * max_travel on search and 5 * pulloff on locate phases."
    ),
    "ALARM:10": _("EStop asserted. Clear and reset (grblHAL)"),
    "ALARM:11": _(
        "Homing required. Execute homing command ($H) to continue. (grblHAL)"
    ),
    "ALARM:12": _("Limit switch engaged. Clear before continuing. (grblHAL)"),
    "ALARM:13": _("Probe protection triggered. Clear before continuing. (grblHAL)"),
    "ALARM:14": _("Spindle at speed timeout. Clear before continuing. (grblHAL)"),
    "ALARM:15": _(
        "Homing fail. Could not find second limit switch for auto squared axis within search distances. Try increasing max travel, decreasing pull-off distance, or check wiring. (grblHAL)"
    ),
    "Hold:0": _("Hold complete. Ready to resume."),
    "Hold:1": _("Hold in-progress. Reset will throw an alarm."),
    "Door:0": _("Door closed. Ready to resume."),
    "Door:1": _("Machine stopped. Door still ajar. Can't resume until closed."),
    "Door:2": _(
        "Door opened. Hold (or parking retract) in-progress. Reset will throw an alarm."
    ),
    "Door:3": _(
        "Door closed and resuming. Restoring from park, if applicable. Reset will throw an alarm."
    ),
}


# Convert Grbl V1.0 codes to Grbl V0.9
for e1, e0 in (
    ("error: Expected command letter", "error:1"),
    ("error: Bad number format", "error:2"),
    ("error: Invalid statement", "error:3"),
    ("error: Value < 0", "error:4"),
    ("error: Setting disabled", "error:5"),
    ("error: Value < 3 usec", "error:6"),
    ("error: EEPROM read fail. Using defaults", "error:7"),
    ("error: Not idle", "error:8"),
    ("error: G-code lock", "error:9"),
    ("error: Homing not enabled", "error:10"),
    ("error: Line overflow", "error:11"),
    ("error: Step rate > 30kHz*", "error:12"),
    ("error: Check Door", "error:13"),
    ("error: Line length exceeded", "error:14"),
    ("error: Travel exceeded", "error:15"),
    ("error: Invalid jog command", "error:16"),
    ("error: Unsupported command", "error:20"),
    ("error: Modal group violation", "error:21"),
    ("error: Undefined feed rate", "error:22"),
    ("error: Invalid gcode ID:23", "error:23"),
    ("error: Invalid gcode ID:24", "error:24"),
    ("error: Invalid gcode ID:25", "error:25"),
    ("error: Invalid gcode ID:26", "error:26"),
    ("error: Invalid gcode ID:27", "error:27"),
    ("error: Invalid gcode ID:28", "error:28"),
    ("error: Invalid gcode ID:29", "error:29"),
    ("error: Invalid gcode ID:30", "error:30"),
    ("error: Invalid gcode ID:31", "error:31"),
    ("error: Invalid gcode ID:32", "error:32"),
    ("error: Invalid gcode ID:33", "error:33"),
    ("error: Invalid gcode ID:34", "error:34"),
    ("error: Invalid gcode ID:35", "error:35"),
    ("error: Invalid gcode ID:36", "error:36"),
    ("error: Invalid gcode ID:37", "error:37"),
    ("ALARM: Hard limit", "ALARM:1"),
    ("ALARM: Soft limit", "ALARM:2"),
    ("ALARM: Abort during cycle", "ALARM:3"),
    ("ALARM: Probe fail", "ALARM:4"),
    ("ALARM: Probe fail", "ALARM:5"),
    ("ALARM: Homing fail", "ALARM:6"),
    ("ALARM: Homing fail", "ALARM:7"),
    ("ALARM: Homing fail", "ALARM:8"),
    ("ALARM: Homing fail", "ALARM:9"),
):
    ERROR_CODES[e1] = ERROR_CODES[e0]


class _GenericGRBL(_GenericController):
    def test(self):
        print("test supergen grbl")

    def viewSettings(self):
        self.master.sendGCode("$$")

    def viewBuild(self):
        self.master.sendGCode("$I")

    def viewStartup(self):
        self.master.sendGCode("$N")

    def checkGcode(self):
        self.master.sendGCode("$C")

    def grblHelp(self):
        self.master.sendGCode("$")

    def grblRestoreSettings(self):
        self.master.sendGCode("$RST=$")

    def grblRestoreWCS(self):
        self.master.sendGCode("$RST=#")

    def grblRestoreAll(self):
        self.master.sendGCode("$RST=#")

    def purgeControllerExtra(self):
        time.sleep(1)
        self.master.unlock(False)
