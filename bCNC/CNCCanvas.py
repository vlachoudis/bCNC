# $Id: CNCCanvas.py,v 1.7 2014/10/15 15:04:06 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math
import time
import sys
import gc

from tkinter import (
    TclError,
    FALSE,
    N,
    S,
    W,
    E,
    NS,
    EW,
    NSEW,
    CENTER,
    NONE,
    BOTH,
    LEFT,
    RIGHT,
    RAISED,
    HORIZONTAL,
    VERTICAL,
    ALL,
    DISABLED,
    LAST,
    SCROLL,
    UNITS,
    StringVar,
    IntVar,
    BooleanVar,
    Button,
    Canvas,
    Checkbutton,
    Frame,
    Label,
    Radiobutton,
    Scrollbar,
    OptionMenu,
)
import tkinter
import bmath
import Camera
import tkExtra
import Utils
from CNC import CNC, AlarmException

# Probe mapping we need PIL and numpy
try:
    from PIL import Image, ImageTk
    import numpy

    # Resampling image based on PIL library and converting to RGB.
    # options possible: NEAREST, BILINEAR, BICUBIC, ANTIALIAS
    RESAMPLE = Image.NEAREST  # resize type
except Exception:
    from tkinter import Image
    numpy = None
    RESAMPLE = None

ANTIALIAS_CHEAP = False

VIEW_XY = 0
VIEW_XZ = 1
VIEW_YZ = 2
VIEW_ISO1 = 3
VIEW_ISO2 = 4
VIEW_ISO3 = 5
VIEW_XY_IMG = 6
VIEWS = ["X-Y", "X-Z", "Y-Z", "ISO1", "ISO2", "ISO3", "XY-IMG"]

INSERT_WIDTH2 = 3
GANTRY_R = 4
GANTRY_X = GANTRY_R * 2  # 10
GANTRY_Y = GANTRY_R  # 5
GANTRY_H = GANTRY_R * 5  # 20
DRAW_TIME = 5  # Maximum draw time permitted
PROCESS_TIME = sys.maxsize # Maximum time for processing data or file

INSERT_COLOR = "Blue"
GANTRY_COLOR = "Red"
MARGIN_COLOR = "Magenta"
GRID_COLOR = "Gray"
BOX_SELECT = "Cyan"
TAB_COLOR = "DarkOrange"
TABS_COLOR = "Orange"
WORK_COLOR = "Orange"
CAMERA_COLOR = "Cyan"
CANVAS_COLOR = "White"

ENABLE_COLOR = "Black"
DISABLE_COLOR = "LightGray"
SELECT_COLOR = "Blue"
SELECT2_COLOR = "DarkCyan"
PROCESS_COLOR = "Green"
PROCESS_COLOR2 = "LightGreen"
PROGRESS_COLOR = "DarkGreen"
PROGRESS_TEXT_COLOR = "DarkBlue"

MOVE_COLOR = "DarkCyan"
RULER_COLOR = "Green"
PROBE_TEXT_COLOR = "Green"

INFO_COLOR = "Gold"

SELECTION_TAGS = ("sel", "sel2", "sel3", "sel4")
GANTRY_TAG = "Gantry"
PATH_WIDTH = 0
SELECT_WIDTH = 2
LINEMODE_ENABLED = 1
LINEMODE_RAPID = 2
LINEMODE_DISABLED = 3
PD_COORDS = 0
PD_COLOR = 1
PD_LINEMODE = 2
PD_FEEDRATE = 3
ADV_BLOCK_COLORS = True
FAST_RENDER = True
FILTER_S = True
FILTER_SVAL = 0
FILTER_Z = False
FILTER_ZVAL = 0

ACTION_SELECT = 0
ACTION_SELECT_SINGLE = 1
ACTION_SELECT_AREA = 2
ACTION_SELECT_DOUBLE = 3

ACTION_PAN = 10
ACTION_ORIGIN = 11

ACTION_MOVE = 20
ACTION_ROTATE = 21
ACTION_GANTRY = 22
ACTION_WPOS = 23

ACTION_RULER = 30
ACTION_ADDORIENT = 31

SHIFT_MASK = 1
CONTROL_MASK = 4
ALT_MASK = 8
CONTROLSHIFT_MASK = SHIFT_MASK | CONTROL_MASK
CLOSE_DISTANCE = 5
MAXDIST = (2**31)-1 # Imperically set for scroll bars.
ZOOM = 1.25
MIN_BOX = 16

S60 = math.sin(math.radians(60))
C60 = math.cos(math.radians(60))

DEF_CURSOR = ""
MOUSE_CURSOR = {
    ACTION_SELECT: DEF_CURSOR,
    ACTION_SELECT_AREA: "right_ptr",
    ACTION_PAN: "fleur",
    ACTION_ORIGIN: "cross",
    ACTION_MOVE: "hand1",
    ACTION_ROTATE: "exchange",
    ACTION_GANTRY: "target",
    ACTION_WPOS: "diamond_cross",
    ACTION_RULER: "tcross",
    ACTION_ADDORIENT: "tcross",
}


# -----------------------------------------------------------------------------
def mouseCursor(action):
    return MOUSE_CURSOR.get(action, DEF_CURSOR)


# =============================================================================
# Drawing canvas
# =============================================================================
class CNCCanvas(Canvas):
    def __init__(self, master, app, *kw, **kwargs):
        Canvas.__init__(self, master, *kw, **kwargs)

        # Global variables
        self.view = 0
        self.app = app
        self.cnc = app.cnc
        self.gcode = app.gcode
        self.actionVar = IntVar()

        # Canvas binding
        self.bind("<Configure>", self.configureEvent)
        self.bind("<Motion>", self.motion)

        self.bind("<Button-1>", self.click)
        self.bind("<B1-Motion>", self.buttonMotion)
        self.bind("<ButtonRelease-1>", self.release)
        self.bind("<Double-1>", self.double)

        self.bind("<B2-Motion>", self.pan)
        self.bind("<ButtonRelease-2>", self.panRelease)
        self.bind("<Button-4>", self.mouseZoomIn)
        self.bind("<Button-5>", self.mouseZoomOut)
        self.bind("<MouseWheel>", self.wheel)

        self.bind("<Shift-Button-4>", self.panLeft)
        self.bind("<Shift-Button-5>", self.panRight)
        self.bind("<Control-Button-4>", self.panUp)
        self.bind("<Control-Button-5>", self.panDown)

        self.bind("<Control-Key-Left>", self.panLeft)
        self.bind("<Control-Key-Right>", self.panRight)
        self.bind("<Control-Key-Up>", self.panUp)
        self.bind("<Control-Key-Down>", self.panDown)

        self.bind("<Escape>", self.actionCancel)
        self.bind("<Key>", self.handleKey)

        self.bind("<Control-Key-S>", self.cameraSave)
        self.bind("<Control-Key-t>", self.__test)

        self.bind("<Control-Key-equal>", self.menuZoomIn)
        self.bind("<Control-Key-minus>", self.menuZoomOut)

        self.x0 = 0.0
        self.y0 = 0.0
        self.zoom = 1.0
        self.__tzoom = 1.0  # delayed zoom (temporary)
        self._items = {}

        self._x = self._y = 0
        self._xp = self._yp = 0
        self.action = ACTION_SELECT
        self._mouseAction = None
        self._inDraw = False  # semaphore for parsing
        self._inDrawBlockPaths = False
        self._processed = False   # has each Block been processed
        self._inProcessing = False
        self._cancelProcessing = False
        self._drawn = False   # has each path been drawn
        self._in_zoom = False
        self._gantry1 = None
        self._gantry2 = None
        self._select = None
        self._margin = None
        self._amargin = None
        self._workarea = None
        self._vector = None
        self._lastActive = None
        self._lastGantry = None

        self._probeImage = None
        self._probeTkImage = None
        self._probe = None

        self.camera = Camera.Camera("aligncam")
        self.cameraAnchor = CENTER  # Camera anchor location "" for gantry
        self.cameraRotation = 0.0  # camera Z angle
        self.cameraXCenter = 0.0  # camera X center offset
        self.cameraYCenter = 0.0  # camera Y center offset
        self.cameraScale = 10.0  # camera pixels/unit
        self.cameraEdge = False  # edge detection
        self.cameraR = 1.5875  # circle radius in units (mm/inched)
        self.cameraDx = 0  # camera shift vs gantry
        self.cameraDy = 0
        self.cameraZ = None  # if None it will not make any Z movement for the camera
        self.cameraSwitch = False  # Look at spindle(False) or camera(True)
        self._cameraAfter = None  # Camera anchor location "" for gantry
        self._cameraMaxWidth = 640  # on zoom over this size crop the image
        self._cameraMaxHeight = 480
        self._cameraImage = None
        self._cameraHori = None  # cross hair items
        self._cameraVert = None
        self._cameraCircle = None
        self._cameraCircle2 = None

        self.draw_axes = True  # Drawing flags
        self.draw_grid = True
        self.draw_margin = True
        self.margin_mode = True
        self.draw_probe = True
        self.draw_workarea = True
        self.draw_paths = True
        self.draw_rapid = True  # draw rapid motions
        self.filter_inactive = True  # filter motions with inactive spindle
        self._wx = self._wy = self._wz = 0.0  # work position
        self._dx = self._dy = self._dz = 0.0  # work-machine position

        self._vx0 = self._vy0 = self._vz0 = 0  # vector move coordinates
        self._vx1 = self._vy1 = self._vz1 = 0  # vector move coordinates

        self._orientSelected = None

        self.reset()
        self.initPosition()
        self.cnc.initPath()

    # Calculate arguments for antialiasing
    def antialias_args(self, args, winc=0.5, cw=2):
        nargs = {}

        # set defaults
        nargs["width"] = 1
        nargs["fill"] = "#000"

        # get original args
        for arg in args:
            nargs[arg] = args[arg]
        if nargs["width"] == 0:
            nargs["width"] = 1

        # calculate width
        nargs["width"] += winc

        # calculate color
        cbg = self.winfo_rgb(self.cget("bg"))
        cfg = list(self.winfo_rgb(nargs["fill"]))
        cfg[0] = (cfg[0] + cbg[0] * cw) / (cw + 1)
        cfg[1] = (cfg[1] + cbg[1] * cw) / (cw + 1)
        cfg[2] = (cfg[2] + cbg[2] * cw) / (cw + 1)
        nargs["fill"] = "#{:02x}{:02x}{:02x}".format(
            int(cfg[0] / 256), int(cfg[1] / 256), int(cfg[2] / 256)
        )

        return nargs

    # Override alias method if antialiasing enabled:
    if ANTIALIAS_CHEAP:

        def create_line(self, *args, **kwargs):
            nkwargs = self.antialias_args(kwargs)
            super().create_line(*args, **nkwargs)
            return super().create_line(*args, **kwargs)

    # ----------------------------------------------------------------------
    def reset(self):
        self.zoom = 1.0

    # ----------------------------------------------------------------------
    # Set status message
    # ----------------------------------------------------------------------
    def status(self, msg):
        self.event_generate("<<Status>>", data=msg)

    # ----------------------------------------------------------------------
    def setMouseStatus(self, event):
        data = "%.4f %.4f %.4f" % self.canvas2xyz(
            self.canvasx(event.x), self.canvasy(event.y)
        )
        self.event_generate("<<Coords>>", data=data)

    # ----------------------------------------------------------------------
    # Update scrollbars. Returns True on error, else None
    # ----------------------------------------------------------------------
    def _updateScrollBars(self, absolute=True):
        """Update scroll region for new size"""
        # option 'absolute' can be False when full scrollbar coverage is not needed.
        if not absolute and self.selectLength() > 0:
            bb = self.getSelectBox()
        elif not absolute:
            bb = self.getMarginBox()
        else:
            bb = self.getMarginBox(absolute=True)

        if not bb and not absolute:
            bb = self.selBbox()
        elif not bb:
            bb = self.bbox('all')

        if bb is None:
            return True

        x1, y1, x2, y2 = bb
        dx = x2 - x1
        dy = y2 - y1

        # important checks for zero
        if dx == 0 and dy == 0:
            bb = self.selBbox()
            if not bb:
                return True
            x1, y1, x2, y2 = bb
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                return True
        if dx == 0:
            dx = dy
        elif dy == 0:
            dy = dx

        # make it 3 times bigger in each dimension
        # so when we zoom in/out we don't touch the borders
        ddx1 = x1 - dx
        ddy1 = y1 - dy
        ddx2 = x2 + dx
        ddy2 = y2 + dy
        if (abs(ddx1) >= MAXDIST or
            abs(ddx2) >= MAXDIST or
            abs(ddy1) >= MAXDIST or
            abs(ddy2) >= MAXDIST or
            abs(ddx2-ddx1) >= MAXDIST or
            abs(ddy2-ddy1) >= MAXDIST
         ):
            return True

        self.configure(scrollregion=(ddx1, ddy1, ddx2, ddy2))

    # ----------------------------------------------------------------------
    def handleKey(self, event):
        if event.char == "a":
            self.event_generate("<<SelectAll>>")
        elif event.char == "A":
            self.event_generate("<<SelectNone>>")
        elif event.char == "e":
            self.event_generate("<<Expand>>")
        elif event.char == "f":
            self.fit2Screen()
        elif event.char == "g":
            self.setActionGantry()
        elif event.char == "l":
            self.event_generate("<<EnableToggle>>")
        elif event.char == "m":
            self.setActionMove()
        elif event.char == "n":
            self.event_generate("<<ShowInfo>>")
        elif event.char == "o":
            self.setActionOrigin()
        elif event.char == "r":
            self.setActionRuler()
        elif event.char == "s":
            self.setActionSelect()
        elif event.char == "x":
            self.setActionPan()
        elif event.char == "z":
            self.menuZoomIn()
        elif event.char == "Z":
            self.menuZoomOut()

    # ----------------------------------------------------------------------
    def setAction(self, action):
        self.action = action
        self.actionVar.set(action)
        self._mouseAction = None
        self.config(cursor=mouseCursor(self.action), background="White")

    # ----------------------------------------------------------------------
    def actionCancel(self, event=None):
        if self.action != ACTION_SELECT or (
            self._mouseAction != ACTION_SELECT and self._mouseAction is not None
        ):
            lastAction = self._mouseAction
            self._mouseAction = None
            if lastAction != ACTION_MOVE:
                self.setAction(ACTION_SELECT)
                self.delete("selectbox")
            else:
                self.redraw()
            return "break"

    # ----------------------------------------------------------------------
    def setActionSelect(self, event=None):
        if self.action == ACTION_SELECT:
            self.event_generate("<<SelectNone>>")
        self.setAction(ACTION_SELECT)
        self.status(_("Select objects with mouse"))

    # ----------------------------------------------------------------------
    def setActionPan(self, event=None):
        self.setAction(ACTION_PAN)
        self.status(_("Pan viewport"))

    # ----------------------------------------------------------------------
    def setActionOrigin(self, event=None):
        self.setAction(ACTION_ORIGIN)
        self.status(_("Click to set the origin (zero)"))

    # ----------------------------------------------------------------------
    def setActionMove(self, event=None):
        self.setAction(ACTION_MOVE)
        self.status(_("Move graphically objects"))

    # ----------------------------------------------------------------------
    def setActionGantry(self, event=None):
        self.setAction(ACTION_GANTRY)
        self.config(background="seashell")
        self.status(_("Move CNC gantry to mouse location"))

    # ----------------------------------------------------------------------
    def setActionWPOS(self, event=None):
        self.setAction(ACTION_WPOS)
        self.config(background="ivory")
        self.status(
            _("Set mouse location as current machine position (X/Y only)"))

    # ----------------------------------------------------------------------
    def setActionRuler(self, event=None):
        if self.action == ACTION_RULER:
            self.clearRuler()
        self.setAction(ACTION_RULER)
        self.status(_("Drag a ruler to measure distances"))

    # ----------------------------------------------------------------------
    def setActionAddMarker(self, event=None):
        self.setAction(ACTION_ADDORIENT)
        self.status(_("Add an orientation marker"))

    # ----------------------------------------------------------------------
    # Convert canvas cx,cy coordinates to machine space
    # ----------------------------------------------------------------------
    def canvas2Machine(self, cx, cy):
        u = cx / self.zoom
        v = cy / self.zoom

        if self.view == VIEW_XY:
            return u, -v, None

        elif self.view == VIEW_XZ:
            return u, None, -v

        elif self.view == VIEW_YZ:
            return None, u, -v

        elif self.view == VIEW_XY_IMG:
            return u, v, None

        elif self.view == VIEW_ISO1:
            return 0.5 * (u / S60 + v / C60), 0.5 * (u / S60 - v / C60), None

        elif self.view == VIEW_ISO2:
            return 0.5 * (u / S60 - v / C60), -0.5 * (u / S60 + v / C60), None

        elif self.view == VIEW_ISO3:
            return -0.5 * (u / S60 + v / C60), -0.5 * (u / S60 - v / C60), None

    # ----------------------------------------------------------------------
    # Image (pixel) coordinates to machine
    # ----------------------------------------------------------------------
    def image2Machine(self, x, y):
        return self.canvas2Machine(self.canvasx(x), self.canvasy(y))

    # ----------------------------------------------------------------------
    # Move gantry to mouse location
    # ----------------------------------------------------------------------
    def actionGantry(self, x, y):
        u, v, w = self.image2Machine(x, y)
        self.app.goto(u, v, w)
        self.setAction(ACTION_SELECT)

    # ----------------------------------------------------------------------
    # Set the work coordinates to mouse location
    # ----------------------------------------------------------------------
    def actionWPOS(self, x, y):
        u, v, w = self.image2Machine(x, y)
        self.app.mcontrol._wcsSet(u, v, w)
        self.setAction(ACTION_SELECT)

    # ----------------------------------------------------------------------
    # Add an orientation marker at mouse location
    # ----------------------------------------------------------------------
    def actionAddOrient(self, x, y):
        cx, cy = self.snapPoint(self.canvasx(x), self.canvasy(y))
        u, v, w = self.canvas2Machine(cx, cy)
        if u is None or v is None:
            self.status(
                _("ERROR: Cannot set X-Y marker  with the current view"))
            return
        self._orientSelected = len(self.gcode.orient)
        self.gcode.orient.add(CNC.vars["wx"], CNC.vars["wy"], u, v)
        self.event_generate("<<OrientSelect>>", data=self._orientSelected)
        self.setAction(ACTION_SELECT)

    # ----------------------------------------------------------------------
    # Find item selected
    # ----------------------------------------------------------------------
    def click(self, event):
        self.focus_set()
        self._x = self._xp = event.x
        self._y = self._yp = event.y

        if self.action == ACTION_SELECT:
            self._mouseAction = ACTION_SELECT_SINGLE

        elif self.action in (ACTION_MOVE, ACTION_RULER):
            i = self.canvasx(event.x)
            j = self.canvasy(event.y)
            if self.action == ACTION_RULER and self._vector is not None:
                # Check if we hit the existing ruler
                coords = self.coords(self._vector)
                if abs(coords[0] - i) <= CLOSE_DISTANCE and abs(
                    coords[1] - j <= CLOSE_DISTANCE
                ):
                    # swap coordinates
                    coords[0], coords[2] = coords[2], coords[0]
                    coords[1], coords[3] = coords[3], coords[1]
                    self.coords(self._vector, *coords)
                    self._vx0, self._vy0, self._vz0 = self.canvas2xyz(
                        coords[0], coords[1]
                    )
                    self._mouseAction = self.action
                    return
                elif abs(coords[2] - i) <= CLOSE_DISTANCE and abs(
                    coords[3] - j <= CLOSE_DISTANCE
                ):
                    self._mouseAction = self.action
                    return

            self.clearRuler()
            if self.action == ACTION_MOVE:
                # Check if we clicked on a selected item
                try:
                    for item in self.find_overlapping(
                        i - CLOSE_DISTANCE,
                        j - CLOSE_DISTANCE,
                        i + CLOSE_DISTANCE,
                        j + CLOSE_DISTANCE,
                    ):
                        tags = self.gettags(item)
                        if (
                            "sel" in tags
                            or "sel2" in tags
                            or "sel3" in tags
                            or "sel4" in tags
                        ):
                            break
                    else:
                        self._mouseAction = ACTION_SELECT_SINGLE
                        return
                    fill = MOVE_COLOR
                    arrow = LAST
                except Exception:
                    self._mouseAction = ACTION_SELECT_SINGLE
                    return
            else:
                fill = RULER_COLOR
                arrow = BOTH
            self._vector = self.create_line(
                (i, j, i, j), fill=fill, arrow=arrow, tag="Ruler")
            self._vx0, self._vy0, self._vz0 = self.canvas2xyz(i, j)
            self._mouseAction = self.action

        # Move gantry to position
        elif self.action == ACTION_GANTRY:
            self.actionGantry(event.x, event.y)

        # Move gantry to position
        elif self.action == ACTION_WPOS:
            self.actionWPOS(event.x, event.y)

        # Add orientation marker
        elif self.action == ACTION_ADDORIENT:
            self.actionAddOrient(event.x, event.y)

        # Set coordinate origin
        elif self.action == ACTION_ORIGIN:
            i = self.canvasx(event.x)
            j = self.canvasy(event.y)
            x, y, z = self.canvas2xyz(i, j)
            self.app.insertCommand(_("origin {:g} {:g} {:g}").format(x, y, z),
                                   True)
            self.setActionSelect()

        elif self.action == ACTION_PAN:
            self.pan(event)

    # ----------------------------------------------------------------------
    # Canvas motion button 1
    # ----------------------------------------------------------------------
    def buttonMotion(self, event):
        if self._mouseAction == ACTION_SELECT_AREA:
            self.coords(
                self._select,
                self.canvasx(self._x),
                self.canvasy(self._y),
                self.canvasx(event.x),
                self.canvasy(event.y),
            )

        elif self._mouseAction in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
            if abs(event.x - self._x) > 4 or abs(event.y - self._y) > 4:
                self._mouseAction = ACTION_SELECT_AREA
                self._select = self.create_rectangle(
                    self.canvasx(self._x),
                    self.canvasy(self._y),
                    self.canvasx(event.x),
                    self.canvasy(event.y),
                    outline=BOX_SELECT,
                    tag="selectbox"
                )

        elif self._mouseAction in (ACTION_MOVE, ACTION_RULER):
            coords = self.coords(self._vector)
            i = self.canvasx(event.x)
            j = self.canvasy(event.y)
            coords[-2] = i
            coords[-1] = j
            self.coords(self._vector, *coords)
            if self._mouseAction == ACTION_MOVE:
                self.move("sel", event.x - self._xp, event.y - self._yp)
                self.move("sel2", event.x - self._xp, event.y - self._yp)
                self.move("sel3", event.x - self._xp, event.y - self._yp)
                self.move("sel4", event.x - self._xp, event.y - self._yp)
                self._xp = event.x
                self._yp = event.y

            self._vx1, self._vy1, self._vz1 = self.canvas2xyz(i, j)
            dx = self._vx1 - self._vx0
            dy = self._vy1 - self._vy0
            dz = self._vz1 - self._vz0
            self.status(
                _("dx={:g}  dy={:g}  dz={:g}  length={:g}  angle={:g}").format(
                    dx,
                    dy,
                    dz,
                    math.sqrt(dx**2 + dy**2 + dz**2),
                    math.degrees(math.atan2(dy, dx)),
                )
            )

        elif self._mouseAction == ACTION_PAN:
            self.pan(event)

        self.setMouseStatus(event)

    # ----------------------------------------------------------------------
    # Canvas release button1. Select area
    # ----------------------------------------------------------------------
    def release(self, event):
        if self._mouseAction in (
            ACTION_SELECT_SINGLE,
            ACTION_SELECT_DOUBLE,
            ACTION_SELECT_AREA,
        ):
            if self._mouseAction == ACTION_SELECT_AREA:
                if self._x < event.x:  # From left->right enclosed
                    closest = self.find_enclosed(
                        self.canvasx(self._x),
                        self.canvasy(self._y),
                        self.canvasx(event.x),
                        self.canvasy(event.y),
                    )
                else:  # From right->left overlapping
                    closest = self.find_overlapping(
                        self.canvasx(self._x),
                        self.canvasy(self._y),
                        self.canvasx(event.x),
                        self.canvasy(event.y),
                    )
                self.delete("selectbox")
                self._select = None
                items = []
                for i in closest:
                    try:
                        item = self._items[i]
                        bid, lid = item
                        enable = self.gcode.blocks[bid].enable
                        if enable:
                            items.append(item)
                    except Exception:
                        pass

            elif self._mouseAction in (ACTION_SELECT_SINGLE,
                                       ACTION_SELECT_DOUBLE):
                closest = self.find_closest(
                    self.canvasx(event.x),
                    self.canvasy(event.y),
                    CLOSE_DISTANCE
                )
                items = []
                for i in closest:
                    try:
                        item = self._items[i]
                        bid, lid = item
                        enable = self.gcode.blocks[bid].enable
                        if enable or self._mouseAction == ACTION_SELECT_DOUBLE:
                            items.append(item)
                    except KeyError:
                        tags = self.gettags(i)
                        if "Orient" in tags:
                            self.selectMarker(i)
                            return
                        pass
            if not items:
                return

            shift = (event.state & SHIFT_MASK == SHIFT_MASK) or \
                    (event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK)
            toggle =(event.state & CONTROL_MASK == CONTROL_MASK) or \
                    (event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK)
            self.app.select(
                items=items,
                double=self._mouseAction == ACTION_SELECT_DOUBLE,
                clear = (not shift),
                toggle=toggle
            )
            self._mouseAction = None

        elif self._mouseAction == ACTION_MOVE:
            i = self.canvasx(event.x)
            j = self.canvasy(event.y)
            self._vx1, self._vy1, self._vz1 = self.canvas2xyz(i, j)
            dx = self._vx1 - self._vx0
            dy = self._vy1 - self._vy0
            dz = self._vz1 - self._vz0
            self.status(_("Move by {:g}, {:g}, {:g}").format(dx, dy, dz))
            self.app.insertCommand(("move %g %g %g") % (dx, dy, dz), True)

        elif self._mouseAction == ACTION_PAN:
            self.panRelease(event)

    # ----------------------------------------------------------------------
    def double(self, event):
        self._mouseAction = ACTION_SELECT_DOUBLE

    # ----------------------------------------------------------------------
    def motion(self, event):
        self.setMouseStatus(event)

    # -----------------------------------------------------------------------
    # Testing routine
    # -----------------------------------------------------------------------
    def __test(self, event):
        i = self.canvasx(event.x)
        j = self.canvasy(event.y)
        x, y, z = self.canvas2xyz(i, j)

    # ----------------------------------------------------------------------
    # Snap to the closest point if any
    # ----------------------------------------------------------------------
    def snapPoint(self, cx, cy):
        xs, ys = None, None
        if CNC.inch:
            dmin = (self.zoom / 25.4) ** 2  # 1mm maximum distance ...
        else:
            dmin = (self.zoom) ** 2
        dmin = (CLOSE_DISTANCE * self.zoom) ** 2

        # ... and if we are closer than 5pixels
        for item in self.find_closest(cx, cy, CLOSE_DISTANCE):
            try:
                bid, lid = self._items[item]
            except KeyError:
                continue

            # Very cheap and inaccurate approach :)
            coords = self.coords(item)
            x = coords[0]  # first
            y = coords[1]  # point
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < dmin:
                dmin = d
                xs, ys = x, y

            x = coords[-2]  # last
            y = coords[-1]  # point
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < dmin:
                dmin = d
                xs, ys = x, y

            # I need to check the real code and if
            # an arc check also the center?

        if xs is not None:
            return xs, ys
        else:
            return cx, cy

    # ----------------------------------------------------------------------
    # Get margins of selected items
    # ----------------------------------------------------------------------
    def getMargins(self):
        bbox = self.bbox("sel")
        if not bbox:
            return None
        x1, y1, x2, y2 = bbox
        dx = (x2 - x1 - 1) / self.zoom
        dy = (y2 - y1 - 1) / self.zoom
        return dx, dy

    # ----------------------------------------------------------------------
    def xview(self, *args):
        ret = Canvas.xview(self, *args)
        if args:
            self.cameraPosition()
        return ret

    # ----------------------------------------------------------------------
    def yview(self, *args):
        ret = Canvas.yview(self, *args)
        if args:
            self.cameraPosition()
        return ret

    # ----------------------------------------------------------------------
    def configureEvent(self, event):
        self.cameraPosition()

    # ----------------------------------------------------------------------
    def pan(self, event):
        if self._mouseAction == ACTION_PAN:
            self.scan_dragto(event.x, event.y, gain=1)
            self.cameraPosition()
            self.status("Pan movement active...")
            self.update()
        else:
            self.config(cursor=mouseCursor(ACTION_PAN))
            self.status("Pan click active...")
            self.update()
            self.scan_mark(event.x, event.y)
            self._mouseAction = ACTION_PAN

    # ----------------------------------------------------------------------
    def panRelease(self, event):
        self._mouseAction = None
        self.config(cursor=mouseCursor(self.action))
        self.status("Rendering pan...")
        self.update()
        self.showPaths()
        self.status("Pan completed.")
        self.update()

    # ----------------------------------------------------------------------
    def panLeft(self, event=None):
        self.xview(SCROLL, -1, UNITS)

    def panRight(self, event=None):
        self.xview(SCROLL, 1, UNITS)

    def panUp(self, event=None):
        self.yview(SCROLL, -1, UNITS)

    def panDown(self, event=None):
        self.yview(SCROLL, 1, UNITS)

    # ----------------------------------------------------------------------
    # Delay zooming to cascade multiple zoom actions
    # ----------------------------------------------------------------------
    def zoomCanvas(self, x, y, zoom):
        self._tx = x
        self._ty = y
        self.__tzoom *= zoom
        self.after_idle(self._zoomCanvas)

    # ----------------------------------------------------------------------
    # Zoom on screen position x,y by a factor zoom
    # ----------------------------------------------------------------------
    def _zoomCanvas(self, event=None):  # x, y, zoom):
        if self._in_zoom:
            return
        try:
            self._in_zoom = True
            self.status("Rendering zoom...")
            self.update()

            x = self._tx
            y = self._ty
            zoom = self.__tzoom
            self.__tzoom = 1.0
            if zoom <= 0:
                zoom = 1.0/self.zoom  # un-zoom or just return
                #return
            elif zoom < 1.0:
                slen = self.selectLength()
                bb = self.selBbox()
                if CNC.isMarginValid():
                    x1, y1, x2, y2 = self.getMarginBox(enabled=False, absolute=True)
                elif bb is not None:
                    x1, y1, x2, y2 = bb
                else:
                    return
                if self.zoom < 1.0 and abs(x2-x1) <= MIN_BOX and abs(y2-y1) <= MIN_BOX:
                    return

            tzoom = self.zoom * zoom
            self.zoom = tzoom

            x0 = self.canvasx(0)
            y0 = self.canvasy(0)

            for i in self.find_all():
                self.scale(i, 0, 0, zoom, zoom)

            if self._updateScrollBars():
                #if self._updateScrollBars(absolute=False):
                undozoom = 1.0/zoom
                self.zoom /= zoom
                for i in self.find_all():
                    self.scale(i, 0, 0, undozoom, undozoom)
                return

            # Update last insert
            if self._lastGantry:
                self._drawGantry(*self.plotCoords([self._lastGantry])[0])
            else:
                self._drawGantry(0, 0)

            x0 -= self.canvasx(0)
            y0 -= self.canvasy(0)

            # Perform pin zoom
            dx = self.canvasx(x) * (1.0 - zoom)
            dy = self.canvasy(y) * (1.0 - zoom)

            # Drag to new location to center viewport
            try:
                self.scan_mark(0, 0)
                self.scan_dragto(int(round(dx - x0)), int(round(dy - y0)), 1)
            except TclError:
                pass

            # Resize probe image if any
            if self._probe:
                self._projectProbeImage()
                self.itemconfig(self._probe, image=self._probeTkImage)
            self.cameraUpdate()
        finally:
            self.status("Zoom completed.")
            self.update()
            self._in_zoom = False

    # ----------------------------------------------------------------------
    # Return selected objects bounding box
    # ----------------------------------------------------------------------
    def selBbox(self):
        x1 = None
        for tag in ("sel", "sel2", "sel3", "sel4"):
            bb = self.bbox(tag)
            if bb is None:
                continue
            elif x1 is None:
                x1, y1, x2, y2 = bb
            else:
                x1 = min(x1, bb[0])
                y1 = min(y1, bb[1])
                x2 = max(x2, bb[2])
                y2 = max(y2, bb[3])

        if x1 is None:
            return self.bbox("all")
        return x1, y1, x2, y2

    # ----------------------------------------------------------------------
    # Zoom to Fit to Screen
    # ----------------------------------------------------------------------
    def fit2Screen(self, event=None):
        """Zoom to Fit to Screen"""
        slen = self.selectLength()
        marginsValid = CNC.isMarginValid()
        if marginsValid and (slen <= 0 or not self.draw_paths):
            x1, y1, x2, y2 = self.getMarginBox()
        elif slen > 0:
            x1, y1, x2, y2 = self.getSelectBox()
        else:
            bb = self.selBbox()
            if bb is None:
                return
            x1, y1, x2, y2 = bb
        diffx = abs(x2 - x1)
        diffy = abs(y2 - y1)
        diffx = float(CNC.vars["diameter"]) if diffx <= 0 else diffx
        diffy = float(CNC.vars["diameter"]) if diffy <= 0 else diffy
        bbox_width = diffx * 1.05
        bbox_height = diffy * 1.05
        try:
            zxf = float(self.winfo_width()/bbox_width)
            zyf = float(self.winfo_height()/bbox_height)
            tzoom = min(zxf, zyf)
        except (ZeroDivisionError, ValueError):
            tzoom = 1.0/self.zoom

        self.__tzoom = tzoom
        self._tx = self._ty = 0
        self._zoomCanvas()

        # Find position of new selection
        if slen <= 0:
            x1, y1, x2, y2 = self.getMarginBox()
        else:
            x1, y1, x2, y2 = self.getSelectBox()
        xm = (x1 + x2) // 2
        ym = (y1 + y2) // 2
        sx1, sy1, sx2, sy2 = map(float, self.cget("scrollregion").split())
        midx = float(xm - sx1) / (sx2 - sx1)
        midy = float(ym - sy1) / (sy2 - sy1)

        a, b = self.xview()
        d = (b - a) / 2.0
        self.xview_moveto(midx - d)

        a, b = self.yview()
        d = (b - a) / 2.0
        self.yview_moveto(midy - d)

        self.cameraPosition()

    # ----------------------------------------------------------------------
    # Get the 4 plot coords of the margin box
    # ----------------------------------------------------------------------
    def getMarginBox(self, enabled=None, absolute=False):
        self.setMarginBounds()
        if not CNC.isMarginValid():
            return self.bbox('all')

        dzmin = CNC.vars["dzmin"]
        dzmax = CNC.vars["dzmax"]
        ezmin = CNC.vars["ezmin"]
        ezmax = CNC.vars["ezmax"]
        azmin = CNC.vars["azmin"]
        azmax = CNC.vars["azmax"]

        dvalid = CNC.isDisabledMarginValid()
        evalid = CNC.isEnabledMarginValid()
        trimMargins = (self.margin_mode and evalid) if enabled is None else enabled

        if absolute:
            xyz = [
                (CNC.vars["axmin"], CNC.vars["aymin"], azmin),
                (CNC.vars["axmin"], CNC.vars["aymax"], azmin),
                (CNC.vars["axmax"], CNC.vars["aymax"], azmin),
                (CNC.vars["axmax"], CNC.vars["aymin"], azmin),
                (CNC.vars["axmin"], CNC.vars["aymin"], azmax),
                (CNC.vars["axmin"], CNC.vars["aymax"], azmax),
                (CNC.vars["axmax"], CNC.vars["aymax"], azmax),
                (CNC.vars["axmax"], CNC.vars["aymin"], azmax),
            ]
        elif trimMargins and evalid:
            xyz = [
                (CNC.vars["exmin"], CNC.vars["eymin"], ezmin),
                (CNC.vars["exmin"], CNC.vars["eymax"], ezmin),
                (CNC.vars["exmax"], CNC.vars["eymax"], ezmin),
                (CNC.vars["exmax"], CNC.vars["eymin"], ezmin),
                (CNC.vars["exmin"], CNC.vars["eymin"], ezmax),
                (CNC.vars["exmin"], CNC.vars["eymax"], ezmax),
                (CNC.vars["exmax"], CNC.vars["eymax"], ezmax),
                (CNC.vars["exmax"], CNC.vars["eymin"], ezmax),
            ]
        elif not trimMargins and dvalid:
            xyz = [
                (CNC.vars["dxmin"], CNC.vars["dymin"], dzmin),
                (CNC.vars["dxmin"], CNC.vars["dymax"], dzmin),
                (CNC.vars["dxmax"], CNC.vars["dymax"], dzmin),
                (CNC.vars["dxmax"], CNC.vars["dymin"], dzmin),
                (CNC.vars["dxmin"], CNC.vars["dymin"], dzmax),
                (CNC.vars["dxmin"], CNC.vars["dymax"], dzmax),
                (CNC.vars["dxmax"], CNC.vars["dymax"], dzmax),
                (CNC.vars["dxmax"], CNC.vars["dymin"], dzmax),
            ]
        else:
            xyz = [
                (CNC.vars["axmin"], CNC.vars["aymin"], azmin),
                (CNC.vars["axmin"], CNC.vars["aymax"], azmin),
                (CNC.vars["axmax"], CNC.vars["aymax"], azmin),
                (CNC.vars["axmax"], CNC.vars["aymin"], azmin),
                (CNC.vars["axmin"], CNC.vars["aymin"], azmax),
                (CNC.vars["axmin"], CNC.vars["aymax"], azmax),
                (CNC.vars["axmax"], CNC.vars["aymax"], azmax),
                (CNC.vars["axmax"], CNC.vars["aymin"], azmax),
            ]

        xyzp = self.plotCoords(xyz)
        return self.minMaxPlotCoords(xyzp)

    # ----------------------------------------------------------------------
    # Get the 4 plot coords of selected blocks/paths using 3D projection.
    # ----------------------------------------------------------------------
    def getSelectBox(self, enabled=False):
        found = False
        items = self.getSelection()

        for item in items:
            if item is None or self._items[item] is None:
                continue
            bid, lid = self._items[item]
            pathdata = self.gcode.blocks[bid].pathdata(lid)
            if pathdata:
                xyz = pathdata[PD_COORDS]
                line_mode = pathdata[PD_LINEMODE]
                if enabled or (self.filter_inactive and line_mode != LINEMODE_ENABLED):
                    continue
                if not found:
                    xmin = min(i[0] for i in xyz)
                    ymin = min(i[1] for i in xyz)
                    zmin = min(i[2] for i in xyz)
                    xmax = max(i[0] for i in xyz)
                    ymax = max(i[1] for i in xyz)
                    zmax = max(i[2] for i in xyz)
                    found = True
                xmin = min(xmin, min(i[0] for i in xyz))
                ymin = min(ymin, min(i[1] for i in xyz))
                zmin = min(zmin, min(i[2] for i in xyz))
                xmax = max(xmax, max(i[0] for i in xyz))
                ymax = max(ymax, max(i[1] for i in xyz))
                zmax = max(zmax, max(i[2] for i in xyz))
        if found:
            xyz = [
                (xmin, ymin, zmin),
                (xmin, ymin, zmax),
                (xmax, ymin, zmin),
                (xmax, ymin, zmax),
                (xmax, ymax, zmin),
                (xmax, ymax, zmax),
                (xmin, ymax, zmin),
                (xmin, ymax, zmax),
            ]
            xyz_p = self.plotCoords(xyz)
            bb = self.minMaxPlotCoords(xyz_p)
            if bb:
                return bb

        return self.bbox('all')

    # ----------------------------------------------------------------------
    # Sort the minimum and maximum x and y plot coords, independently
    # ----------------------------------------------------------------------
    def minMaxPlotCoords(self, xyz_p):
        if not xyz_p:
            return None

        first = True
        for point in xyz_p:
            for point in xyz_p:
                if first:
                    x1 = point[0]
                    y1 = point[1]
                    x2 = point[0]
                    y2 = point[1]
                    first = False
                x1 = min(x1, point[0])
                y1 = min(y1, point[1])
                x2 = max(x2, point[0])
                y2 = max(y2, point[1])

        return x1, y1, x2, y2

    # ----------------------------------------------------------------------
    def menuZoomIn(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        x = int(self.cget("width"))/2
        y = int(self.cget("height"))/2
        self.zoomCanvas(round((w-x)/2), round((h-y)/2), 2.0)

    # ----------------------------------------------------------------------
    def menuZoomOut(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        x = int(self.cget("width"))/2
        y = int(self.cget("height"))/2
        self.zoomCanvas(round((w-x)/2), round((h-y)/2), 0.5)

    # ----------------------------------------------------------------------
    def mouseZoomIn(self, event):
        self.zoomCanvas(event.x, event.y, ZOOM)

    # ----------------------------------------------------------------------
    def mouseZoomOut(self, event):
        self.zoomCanvas(event.x, event.y, 1.0 / ZOOM)

    # ----------------------------------------------------------------------
    def wheel(self, event):
        self.zoomCanvas(event.x, event.y, pow(ZOOM, (event.delta // 120)))

    # ----------------------------------------------------------------------
    # Change the insert marker location
    # ----------------------------------------------------------------------
    def activeMarker(self, item):
        if item is None:
            return
        b, i = item
        if i is None:
            return
        block = self.gcode[b]
        item = block.path(i)

        if item is not None and item != self._lastActive:
            if self._lastActive is not None:
                self.itemconfig(self._lastActive, arrow=NONE)
            self._lastActive = item
            self.itemconfig(self._lastActive, arrow=LAST)

    # ----------------------------------------------------------------------
    # Display gantry
    # ----------------------------------------------------------------------
    def gantry(self, wx, wy, wz, mx, my, mz):
        self._lastGantry = (wx, wy, wz)
        self._drawGantry(*self.plotCoords([(wx, wy, wz)])[0])
        if self._cameraImage and self.cameraAnchor == NONE:
            self.cameraPosition()

        dx = wx - mx
        dy = wy - my
        dz = wz - mz
        if (
            abs(dx - self._dx) > 0.0001
            or abs(dy - self._dy) > 0.0001
            or abs(dz - self._dz) > 0.0001
        ):
            self._dx = dx
            self._dy = dy
            self._dz = dz

            if not self.draw_workarea:
                return
            xmin = self._dx - CNC.travel_x
            ymin = self._dy - CNC.travel_y
            xmax = self._dx
            ymax = self._dy

            xyz = [
                (xmin, ymin, 0.0),
                (xmax, ymin, 0.0),
                (xmax, ymax, 0.0),
                (xmin, ymax, 0.0),
                (xmin, ymin, 0.0),
            ]

            coords = []
            for x, y in self.plotCoords(xyz):
                coords.append(x)
                coords.append(y)
            self.coords(self._workarea, *coords)

    # ----------------------------------------------------------------------
    # Counts the number of items selected
    # ----------------------------------------------------------------------
    def selectLength(self):
        return len(self.getSelection())

    # ----------------------------------------------------------------------
    # Returns all items selected
    # ----------------------------------------------------------------------
    def getSelection(self):
        items = []
        for sel in SELECTION_TAGS:
            items += self.find_withtag(sel)
        return items

    # ----------------------------------------------------------------------
    # Clear highlight of selection
    # ----------------------------------------------------------------------
    def clearSelection(self):
        if self._lastActive is not None:
            self.itemconfig(self._lastActive, arrow=NONE)
            self._lastActive = None

        for i in self.find_withtag("sel") + self.find_withtag("sel2"):

            try:
                bid, lid = self._items[i]
                block = self.gcode[bid]
                pathdata = block.pathdata(lid)
                fill = pathdata[PD_COLOR] if pathdata else ENABLE_COLOR
                if not block.enable:
                    fill = DISABLE_COLOR
            except(KeyError, IndexError):
                fill = ENABLE_COLOR

            if fill == DISABLE_COLOR:
                self.tag_lower(i)
            self.itemconfig(i, width=PATH_WIDTH, fill=fill)

        self.itemconfig("sel3", width=PATH_WIDTH, fill=TAB_COLOR)
        self.itemconfig("sel4", width=PATH_WIDTH, fill=DISABLE_COLOR)
        for i in SELECTION_TAGS:
            self.dtag(i)
        self.delete("info")
        self.showPaths()

    # ----------------------------------------------------------------------
    # Highlight selected items
    # ----------------------------------------------------------------------
    def select(self, items):
        for b, i in items:
            block = self.gcode[b]
            if i is None:
                sel = block.enable and "sel" or "sel2"
                for j, path in enumerate(block._path):
                    pathdata = block.pathdata(j)
                    if path is not None:
                        color = pathdata[PD_COLOR] if pathdata else self.itemcget(path, "fill")
                        line_mode = pathdata[PD_LINEMODE] if pathdata else LINEMODE_ENABLED
                        if line_mode == LINEMODE_ENABLED:
                            self.addtag_withtag("sel", path)
                            sel = "sel"
                        elif line_mode == LINEMODE_DISABLED:
                            self.addtag_withtag("sel2", path)
                            sel = "sel2"
                sel = block.enable and "sel3" or "sel4"

            elif isinstance(i, int):
                path = block.path(i)
                if path:
                    pathdata = block.pathdata(i)
                    line_mode = pathdata[PD_LINEMODE] if pathdata else LINEMODE_ENABLED
                    sel = "sel2" if (line_mode != LINEMODE_ENABLED) else "sel"
                    self.addtag_withtag(sel, path)

        self.itemconfig("sel",  width=SELECT_WIDTH, fill=SELECT_COLOR)
        self.itemconfig("sel2", width=SELECT_WIDTH, fill=SELECT2_COLOR)
        self.itemconfig("sel3", width=SELECT_WIDTH, fill=TAB_COLOR)
        self.itemconfig("sel4", width=SELECT_WIDTH, fill=TABS_COLOR)
        for i in reversed(SELECTION_TAGS):
            if self.draw_paths:
                if (self.filter_inactive and i != 'sel2') or (not self.filter_inactive):
                    self.itemconfig(i, state='normal')
            self.tag_raise(i)
        self.raise_gantry()
        self.update()

    # ----------------------------------------------------------------------
    # Select orientation marker
    # ----------------------------------------------------------------------
    def selectMarker(self, item):
        # find marker
        for i, paths in enumerate(self.gcode.orient.paths):
            if item in paths:
                self._orientSelected = i
                for j in paths:
                    self.itemconfig(j, width=2)
                self.event_generate("<<OrientSelect>>", data=i)
                return
        self._orientSelected = None

    # ----------------------------------------------------------------------
    # Highlight marker that was selected
    # ----------------------------------------------------------------------
    def orientChange(self, marker):
        self.itemconfig("Orient", width=1)
        if marker >= 0:
            self._orientSelected = marker
            try:
                for i in self.gcode.orient.paths[self._orientSelected]:
                    self.itemconfig(i, width=2)
            except IndexError:
                self.drawOrient()
        else:
            self._orientSelected = None

    # ----------------------------------------------------------------------
    # Display graphical information on selected blocks
    # ----------------------------------------------------------------------
    def showInfo(self, blocks):
        self.delete("info")  # clear any previous information
        for bid in blocks:
            block = self.gcode.blocks[bid]
            xyz = [
                (block.xmin, block.ymin, 0.0),
                (block.xmax, block.ymin, 0.0),
                (block.xmax, block.ymax, 0.0),
                (block.xmin, block.ymax, 0.0),
                (block.xmin, block.ymin, 0.0),
            ]
            self.create_line(self.plotCoords(xyz), fill=INFO_COLOR, tag="info")
            xc = (block.xmin + block.xmax) / 2.0
            yc = (block.ymin + block.ymax) / 2.0
            r = min(block.xmax - xc, block.ymax - yc)
            closed, direction = self.gcode.info(bid)

            if closed == 0:  # open path
                if direction == 1:
                    sf = math.pi / 4.0
                    ef = 2.0 * math.pi - sf
                else:
                    ef = math.pi / 4.0
                    sf = 2.0 * math.pi - ef
            elif closed == 1:
                if direction == 1:
                    sf = 0.0
                    ef = 2.0 * math.pi
                else:
                    ef = 0.0
                    sf = 2.0 * math.pi

            elif closed is None:
                continue

            n = 64
            df = (ef - sf) / float(n)
            xyz = []
            f = sf
            for i in range(n + 1):
                xyz.append(
                    (xc + r * math.sin(f), yc + r * math.cos(f), 0.0)
                )  # towards up
                f += df
            self.create_line(
                self.plotCoords(xyz),
                fill=INFO_COLOR,
                width=5,
                arrow=LAST,
                arrowshape=(32, 40, 12),
                tag="info",
            )

    # -----------------------------------------------------------------------
    def cameraOn(self, event=None):
        if not self.camera.start():
            return
        self.cameraRefresh()

    # -----------------------------------------------------------------------
    def cameraOff(self, event=None):
        self.delete(self._cameraImage)
        self.delete(self._cameraHori)
        self.delete(self._cameraVert)
        self.delete(self._cameraCircle)
        self.delete(self._cameraCircle2)

        self._cameraImage = None
        if self._cameraAfter:
            self.after_cancel(self._cameraAfter)
            self._cameraAfter = None
        self.camera.stop()

    # -----------------------------------------------------------------------
    def cameraUpdate(self):
        if not self.camera.isOn():
            return
        if self._cameraAfter:
            self.after_cancel(self._cameraAfter)
            self._cameraAfter = None
        self.cameraRefresh()
        self.cameraPosition()

    # -----------------------------------------------------------------------
    def cameraRefresh(self):
        if not self.camera.read():
            self.cameraOff()
            return
        self.camera.rotation = self.cameraRotation
        self.camera.xcenter = self.cameraXCenter
        self.camera.ycenter = self.cameraYCenter
        if self.cameraEdge:
            self.camera.canny(50, 200)
        if self.cameraAnchor == NONE or self.zoom / self.cameraScale > 1.0:
            self.camera.resize(
                self.zoom / self.cameraScale,
                self._cameraMaxWidth,
                self._cameraMaxHeight,
            )
        if self._cameraImage is None:
            self._cameraImage = self.create_image((0, 0), tag="CameraImage")
            self.lower(self._cameraImage)
            # create cross hair at dummy location we will correct latter
            self._cameraHori = self.create_line(
                0, 0, 1, 0, fill=CAMERA_COLOR, tag="CrossHair"
            )
            self._cameraVert = self.create_line(
                0, 0, 0, 1, fill=CAMERA_COLOR, tag="CrossHair"
            )
            self._cameraCircle = self.create_oval(
                0, 0, 1, 1, outline=CAMERA_COLOR, tag="CrossHair"
            )
            self._cameraCircle2 = self.create_oval(
                0, 0, 1, 1, outline=CAMERA_COLOR, dash=(3, 3), tag="CrossHair"
            )
            self.cameraPosition()
        try:
            self.itemconfig(self._cameraImage, image=self.camera.toTk())
        except Exception:
            pass
        self._cameraAfter = self.after(100, self.cameraRefresh)

    # -----------------------------------------------------------------------
    def cameraFreeze(self, freeze):
        if self.camera.isOn():
            self.camera.freeze(freeze)

    # -----------------------------------------------------------------------
    def cameraSave(self, event=None):
        try:
            self._count += 1
        except Exception:
            self._count = 1
        self.camera.save("camera%02d.png" % (self._count))

    # ----------------------------------------------------------------------
    # Reposition camera and crosshair
    # ----------------------------------------------------------------------
    def cameraPosition(self):
        if self._cameraImage is None:
            return
        w = self.winfo_width()
        h = self.winfo_height()
        hc, wc = self.camera.image.shape[:2]
        wc //= 2
        hc //= 2
        x = w // 2  # everything on center
        y = h // 2
        if self.cameraAnchor is None:
            if self._lastGantry is not None:
                x, y = self.plotCoords([self._lastGantry])[0]
            else:
                x = y = 0
            if not self.cameraSwitch:
                x += self.cameraDx * self.zoom
                y -= self.cameraDy * self.zoom
            r = self.cameraR * self.zoom
        else:
            if self.cameraAnchor != CENTER:
                if N in self.cameraAnchor:
                    y = hc
                elif S in self.cameraAnchor:
                    y = h - hc
                if W in self.cameraAnchor:
                    x = wc
                elif E in self.cameraAnchor:
                    x = w - wc
            x = self.canvasx(x)
            y = self.canvasy(y)
            if self.zoom / self.cameraScale > 1.0:
                r = self.cameraR * self.zoom
            else:
                r = self.cameraR * self.cameraScale

        self.coords(self._cameraImage, x, y)
        self.coords(self._cameraHori, x - wc, y, x + wc, y)
        self.coords(self._cameraVert, x, y - hc, x, y + hc)
        self.coords(self._cameraCircle, x - r, y - r, x + r, y + r)
        self.coords(
            self._cameraCircle2, x - r * 2, y - r * 2, x + r * 2, y + r * 2)

    # ----------------------------------------------------------------------
    # Crop center of camera and search it in subsequent movements
    # ----------------------------------------------------------------------
    def cameraMakeTemplate(self, r):
        if self._cameraImage is None:
            return
        self._template = self.camera.getCenterTemplate(r)

    # ----------------------------------------------------------------------
    def cameraMatchTemplate(self):
        return self.camera.matchTemplate(self._template)

    # ----------------------------------------------------------------------
    # Parse and draw the file from the editor to g-code commands
    # ----------------------------------------------------------------------
    def draw(self, view=None, fit2screen=False):
        if self._inDraw:
            return

        try:
            self._inDraw = True

            if view is not None:
                self.view = view

            self.__tzoom = 1.0
            self.event_generate("<<Process>>")
            self.initPosition()
            self.drawGrid()
            self.drawWorkarea()
            self.drawProbe()
            self.drawOrient()
            self.drawAxes()
            self._updateScrollBars()

            if fit2screen:
                # use margins to find initial drawview
                drawmargin_ = self.draw_margin
                self.draw_margin = True
                self.drawMargin()
                self.fit2Screen()
                self.draw_margin = drawmargin_
                self.drawMargin()
                self.drawPaths()
                self.event_generate("<<ListboxSelect>>")
                if self.selectLength() > 0:
                    self.fit2Screen()
            else:
                self.drawMargin()
                self.drawPaths()
                self.event_generate("<<ListboxSelect>>")
                if not CNC.isMarginValid():
                    self.fit2Screen()

            self.update()
        finally:
            gc.collect()
            self._inDraw = False

    # ----------------------------------------------------------------------
    # Initialize gantry position
    # ----------------------------------------------------------------------
    def initPosition(self):
        self.configure(background=CANVAS_COLOR)
        self.delete(GANTRY_TAG)
        self._cameraImage = None
        gr = max(3, int(CNC.vars["diameter"] / 2.0 * self.zoom))
        if self.view in (VIEW_XY, VIEW_XY_IMG):
            self._gantry1 = self.create_oval(
                (-gr, -gr), (gr, gr), width=2, outline=GANTRY_COLOR, tag=GANTRY_TAG
            )
            self._gantry2 = None
        else:
            gx = gr
            gy = gr // 2
            gh = 3 * gr
            if self.view in (VIEW_XZ, VIEW_YZ):
                self._gantry1 = None
                self._gantry2 = self.create_line(
                    (-gx, -gh, 0, 0, gx, -gh, -gx, -gh),
                    width=2, fill=GANTRY_COLOR, tag=GANTRY_TAG
                )
            else:
                self._gantry1 = self.create_oval(
                    (-gx, -gh - gy, gx, -gh + gy), width=2,
                    outline=GANTRY_COLOR, tag=GANTRY_TAG
                )
                self._gantry2 = self.create_line(
                    (-gx, -gh, 0, 0, gx, -gh), width=2, fill=GANTRY_COLOR, tag=GANTRY_TAG
                )

        self._lastInsert = None
        self._lastActive = None
        self._select = None
        self._vector = None

    # ----------------------------------------------------------------------
    # Draw gantry location
    # ----------------------------------------------------------------------
    def _drawGantry(self, x, y):
        gr = max(3, int(CNC.vars["diameter"] / 2.0 * self.zoom))
        if self._gantry2 is None:
            self.coords(self._gantry1, (x - gr, y - gr, x + gr, y + gr))
        else:
            gx = gr
            gy = gr // 2
            gh = 3 * gr
            if self._gantry1 is None:
                self.coords(
                    self._gantry2,
                    (x - gx, y - gh, x, y, x + gx, y - gh, x - gx, y - gh),
                )
            else:
                self.coords(
                    self._gantry1, (x - gx, y - gh - gy, x + gx, y - gh + gy))
                self.coords(
                    self._gantry2, (x - gx, y - gh, x, y, x + gx, y - gh))

    # ----------------------------------------------------------------------
    # Raise gantry on canvas
    # ----------------------------------------------------------------------
    def raise_gantry(self):
        if self._gantry1:
            self.tag_raise(self._gantry1)
        if self._gantry2:
            self.tag_raise(self._gantry2)

    # ----------------------------------------------------------------------
    # Draw system axes
    # ----------------------------------------------------------------------
    def drawAxes(self):
        self.delete("Axes")
        if not self.draw_axes:
            return

        dx = CNC.vars["axmax"] - CNC.vars["axmin"]
        dy = CNC.vars["aymax"] - CNC.vars["aymin"]
        d = min(dx, dy)
        try:
            s = math.pow(10.0, int(math.log10(d)))
        except Exception:
            if CNC.inch:
                s = 10.0
            else:
                s = 100.0
        xyz = [(0.0, 0.0, 0.0), (s, 0.0, 0.0)]
        self.create_line(
            self.plotCoords(xyz), tag="Axes", fill="Red",
            dash=(3, 1), arrow=LAST
        )

        xyz = [(0.0, 0.0, 0.0), (0.0, s, 0.0)]
        self.create_line(
            self.plotCoords(xyz), tag="Axes", fill="Green",
            dash=(3, 1), arrow=LAST
        )

        xyz = [(0.0, 0.0, 0.0), (0.0, 0.0, s)]
        self.create_line(
            self.plotCoords(xyz), tag="Axes", fill="Blue",
            dash=(3, 1), arrow=LAST
        )
        self.tag_raise("Axes")

    # ----------------------------------------------------------------------
    # Draw margins of selected blocks
    # ----------------------------------------------------------------------
    def drawMargin(self):
        if self._margin:
            self.delete(self._margin)
        if self._amargin:
            self.delete(self._amargin)
        self._margin = self._amargin = None
        self.setMarginBounds()

        if not self.draw_margin:
            return

        if self.margin_mode and CNC.isEnabledMarginValid():
            xyz = [
                (CNC.vars["exmin"], CNC.vars["eymin"], 0.0),
                (CNC.vars["exmax"], CNC.vars["eymin"], 0.0),
                (CNC.vars["exmax"], CNC.vars["eymax"], 0.0),
                (CNC.vars["exmin"], CNC.vars["eymax"], 0.0),
                (CNC.vars["exmin"], CNC.vars["eymin"], 0.0),
            ]
            self._margin = self.create_line(self.plotCoords(xyz),
                                            fill=MARGIN_COLOR)
            self.tag_raise(self._margin)
        elif CNC.isDisabledMarginValid():
            xyz = [
                (CNC.vars["dxmin"], CNC.vars["dymin"], 0.0),
                (CNC.vars["dxmax"], CNC.vars["dymin"], 0.0),
                (CNC.vars["dxmax"], CNC.vars["dymax"], 0.0),
                (CNC.vars["dxmin"], CNC.vars["dymax"], 0.0),
                (CNC.vars["dxmin"], CNC.vars["dymin"], 0.0),
            ]
            self._margin = self.create_line(self.plotCoords(xyz),
                                            fill=MARGIN_COLOR)
            self.tag_raise(self._margin)

        if not CNC.isAllMarginValid():
            return
        xyz = [
            (CNC.vars["axmin"], CNC.vars["aymin"], 0.0),
            (CNC.vars["axmax"], CNC.vars["aymin"], 0.0),
            (CNC.vars["axmax"], CNC.vars["aymax"], 0.0),
            (CNC.vars["axmin"], CNC.vars["aymax"], 0.0),
            (CNC.vars["axmin"], CNC.vars["aymin"], 0.0),
        ]
        self._amargin = self.create_line(
            self.plotCoords(xyz), dash=(3, 2), fill=MARGIN_COLOR
        )
        self.tag_raise(self._amargin)
        self.raise_gantry()

    # ----------------------------------------------------------------------
    # Sets margin variables for drawing
    # ----------------------------------------------------------------------
    def setMarginBounds(self):
        if self.margin_mode and CNC.isEnabledMarginValid():
            CNC.vars["xmin"] = CNC.vars["exmin"]
            CNC.vars["ymin"] = CNC.vars["eymin"]
            CNC.vars["zmin"] = CNC.vars["ezmin"]
            CNC.vars["xmax"] = CNC.vars["exmax"]
            CNC.vars["ymax"] = CNC.vars["eymax"]
            CNC.vars["zmax"] = CNC.vars["ezmax"]
        elif CNC.isDisabledMarginValid():
            CNC.vars["xmin"] = CNC.vars["dxmin"]
            CNC.vars["ymin"] = CNC.vars["dymin"]
            CNC.vars["zmin"] = CNC.vars["dzmin"]
            CNC.vars["xmax"] = CNC.vars["dxmax"]
            CNC.vars["ymax"] = CNC.vars["dymax"]
            CNC.vars["zmax"] = CNC.vars["dzmax"]
        else:
            CNC.vars["xmin"] = CNC.vars["axmin"]
            CNC.vars["ymin"] = CNC.vars["aymin"]
            CNC.vars["zmin"] = CNC.vars["azmin"]
            CNC.vars["xmax"] = CNC.vars["axmax"]
            CNC.vars["ymax"] = CNC.vars["aymax"]
            CNC.vars["zmax"] = CNC.vars["azmax"]


    # ----------------------------------------------------------------------
    # Change rectangle coordinates
    # ----------------------------------------------------------------------
    def _rectCoords(self, rect, xmin, ymin, xmax, ymax, z=0.0):
        self.coords(
            rect,
            tkinter._flatten(
                self.plotCoords(
                    [
                        (xmin, ymin, z),
                        (xmax, ymin, z),
                        (xmax, ymax, z),
                        (xmin, ymax, z),
                        (xmin, ymin, z),
                    ]
                )
            ),
        )

    # ----------------------------------------------------------------------
    # Draw a 3D path
    # ----------------------------------------------------------------------
    def _drawPath(self, path, z=0.0, **kwargs):
        xyz = []
        for segment in path:
            xyz.append((segment.A[0], segment.A[1], z))
            xyz.append((segment.B[0], segment.B[1], z))
        rect = (self.create_line(self.plotCoords(xyz), **kwargs),)
        return rect

    # ----------------------------------------------------------------------
    # Draw a 3D rectangle
    # ----------------------------------------------------------------------
    def _drawRect(self, xmin, ymin, xmax, ymax, z=0.0, **kwargs):
        xyz = [
            (xmin, ymin, z),
            (xmax, ymin, z),
            (xmax, ymax, z),
            (xmin, ymax, z),
            (xmin, ymin, z),
        ]
        rect = (self.create_line(self.plotCoords(xyz), **kwargs),)
        return rect

    # ----------------------------------------------------------------------
    # Draw a workspace rectangle
    # ----------------------------------------------------------------------
    def drawWorkarea(self):
        if self._workarea:
            self.delete(self._workarea)
        if not self.draw_workarea:
            return

        xmin = self._dx - CNC.travel_x
        ymin = self._dy - CNC.travel_y
        xmax = self._dx
        ymax = self._dy

        self._workarea = self._drawRect(
            xmin, ymin, xmax, ymax, 0.0, fill=WORK_COLOR, dash=(3, 2)
        )
        self.tag_raise(self._workarea)

    # ----------------------------------------------------------------------
    # Draw coordinates grid
    # ----------------------------------------------------------------------
    def drawGrid(self):
        self.delete("Grid")
        if not self.draw_grid:
            return
        if self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3, VIEW_XY_IMG):
            xmin, ymin, xmax, ymax, scalex, scaley = self.getGridScale()
            for i in range(
                int(CNC.vars["aymin"] // scaley), int(CNC.vars["aymax"] // scaley) + 2
            ):
                y = i * float(scaley)
                xyz = [(xmin, y, 0), (xmax, y, 0)]
                item = self.create_line(
                    self.plotCoords(xyz), tag="Grid",
                    fill=GRID_COLOR, dash=(1, 3)
                )
                self.tag_lower(item)

            for i in range(
                int(CNC.vars["axmin"] // scalex), int(CNC.vars["axmax"] // scalex) + 2
            ):
                x = i * float(scalex)
                xyz = [(x, ymin, 0), (x, ymax, 0)]
                item = self.create_line(
                    self.plotCoords(xyz), fill=GRID_COLOR, tag="Grid", dash=(1, 3)
                )
                self.tag_lower(item)
        self.tag_raise("Grid")

    # ----------------------------------------------------------------------
    # Calculate a renderable grid using the absolute margins of XY plane
    # ----------------------------------------------------------------------
    def getGridScale(self):
        axmin = CNC.vars["axmin"]
        axmax = CNC.vars["axmax"]
        aymin = CNC.vars["aymin"]
        aymax = CNC.vars["aymax"]
        dx = abs(axmax-axmin)
        dy = abs(aymax-aymin)
        scalex = max(10, 10**(len(str(int(dx)))-3))
        scaley = max(10, 10**(len(str(int(dy)))-3))
        xmin = (axmin // scalex    ) * scalex
        xmax = (axmax // scalex + 1) * scalex
        ymin = (aymin // scaley    ) * scaley
        ymax = (aymax // scaley + 1) * scaley
        return xmin, ymin, xmax, ymax, scalex, scaley

    # ----------------------------------------------------------------------
    # Display orientation markers
    # ----------------------------------------------------------------------
    def drawOrient(self, event=None):
        self.delete("Orient")
        if self.view in (VIEW_XZ, VIEW_YZ):
            return

        # Draw orient markers
        if CNC.inch:
            w = 0.1
        else:
            w = 2.5

        self.gcode.orient.clearPaths()
        for i, (xm, ym, x, y) in enumerate(self.gcode.orient.markers):
            paths = []
            # Machine position (cross)
            item = self.create_line(
                self.plotCoords([(xm - w, ym, 0.0), (xm + w, ym, 0.0)]),
                tag="Orient",
                fill="Green",
            )
            self.tag_lower(item)
            paths.append(item)

            item = self.create_line(
                self.plotCoords([(xm, ym - w, 0.0), (xm, ym + w, 0.0)]),
                tag="Orient",
                fill="Green",
            )
            self.tag_lower(item)
            paths.append(item)

            # GCode position (cross)
            item = self.create_line(
                self.plotCoords([(x - w, y, 0.0), (x + w, y, 0.0)]),
                tag="Orient",
                fill="Red",
            )
            self.tag_lower(item)
            paths.append(item)

            item = self.create_line(
                self.plotCoords([(x, y - w, 0.0), (x, y + w, 0.0)]),
                tag="Orient",
                fill="Red",
            )
            self.tag_lower(item)
            paths.append(item)

            # Draw error if any
            try:
                err = self.gcode.orient.errors[i]
                item = self.create_oval(
                    self.plotCoords(
                        [(xm - err, ym - err, 0.0), (xm + err, ym + err, 0.0)]
                    ),
                    tag="Orient",
                    outline="Red",
                )
                self.tag_lower(item)
                paths.append(item)

                err = self.gcode.orient.errors[i]
                item = self.create_oval(
                    self.plotCoords([(x - err, y - err, 0.0),
                                     (x + err, y + err, 0.0)]),
                    tag="Orient",
                    outline="Red",
                )
                self.tag_lower(item)
                paths.append(item)
            except IndexError:
                pass

            # Connecting line
            item = self.create_line(
                self.plotCoords([(xm, ym, 0.0), (x, y, 0.0)]),
                tag="Orient",
                fill="Blue",
                dash=(1, 1),
            )
            self.tag_lower(item)
            paths.append(item)

            self.gcode.orient.addPath(paths)

        if self._orientSelected is not None:
            try:
                for item in self.gcode.orient.paths[self._orientSelected]:
                    self.itemconfig(item, width=2)
            except (IndexError, TclError):
                pass

    # ----------------------------------------------------------------------
    # Display probe
    # ----------------------------------------------------------------------
    def drawProbe(self):
        self.delete("Probe")
        if self._probe:
            self.delete(self._probe)
            self._probe = None
        if not self.draw_probe:
            return
        if self.view in (VIEW_XZ, VIEW_YZ):
            return

        # Draw probe grid
        probe = self.gcode.probe
        for x in bmath.frange(probe.xmin, probe.xmax + 0.00001, probe.xstep()):
            xyz = [(x, probe.ymin, 0.0), (x, probe.ymax, 0.0)]
            item = self.create_line(
                self.plotCoords(xyz), tag="Probe", fill="Yellow")
            self.tag_lower(item)

        for y in bmath.frange(probe.ymin, probe.ymax + 0.00001, probe.ystep()):
            xyz = [(probe.xmin, y, 0.0), (probe.xmax, y, 0.0)]
            item = self.create_line(
                self.plotCoords(xyz), tag="Probe", fill="Yellow")
            self.tag_lower(item)

        # Draw probe points
        for i, uv in enumerate(self.plotCoords(probe.points)):
            item = self.create_text(
                uv,
                text=f"{probe.points[i][2]:.{CNC.digits}f}",
                tag="Probe",
                justify=CENTER,
                fill=PROBE_TEXT_COLOR,
            )
            self.tag_lower(item)

        # Draw image map if numpy exists
        if (
            numpy is not None
            and probe.matrix
            and self.view in (VIEW_XY, VIEW_ISO1, VIEW_ISO2, VIEW_ISO3, VIEW_XY_IMG)
        ):
            array = numpy.array(list(reversed(probe.matrix)), numpy.float32)

            lw = array.min()
            hg = array.max()
            mx = max(abs(hg), abs(lw))
            # scale should be:
            #  -mx   .. 0 .. mx
            #  -127     0    127
            # -127 = light-blue
            #    0 = white
            #  127 = light-red
            dc = mx / 127.0  # step in colors
            if abs(dc) < 1e-8:
                return
            palette = []
            for x in bmath.frange(lw, hg + 1e-10, (hg - lw) / 255.0):
                i = int(math.floor(x / dc))
                j = i + i >> 1  # 1.5*i
                if i < 0:
                    palette.append(0xFF + j)
                    palette.append(0xFF + j)
                    palette.append(0xFF)
                elif i > 0:
                    palette.append(0xFF)
                    palette.append(0xFF - j)
                    palette.append(0xFF - j)
                else:
                    palette.append(0xFF)
                    palette.append(0xFF)
                    palette.append(0xFF)
            array = numpy.floor((array - lw) / (hg - lw) * 255)
            self._probeImage = Image.fromarray(
                array.astype(numpy.int16)).convert("L")
            self._probeImage.putpalette(palette)

            # Add transparency for a possible composite operation latter on ISO*
            self._probeImage = self._probeImage.convert("RGBA")

            x, y = self._projectProbeImage()

            self._probe = self.create_image(
                x, y, image=self._probeTkImage, anchor="sw")
            self.tag_lower(self._probe)
        self.tag_raise("Probe")

    # ----------------------------------------------------------------------
    # Create the tkimage for the current projection
    # ----------------------------------------------------------------------
    def _projectProbeImage(self):
        probe = self.gcode.probe
        size = (
            int((probe.xmax - probe.xmin + probe._xstep) * self.zoom),
            int((probe.ymax - probe.ymin + probe._ystep) * self.zoom),
        )
        marginx = int(probe._xstep / 2.0 * self.zoom)
        marginy = int(probe._ystep / 2.0 * self.zoom)
        crop = (marginx, marginy, size[0] - marginx, size[1] - marginy)

        image = self._probeImage.resize((size), resample=RESAMPLE).crop(crop)

        if self.view in (VIEW_ISO1, VIEW_ISO2, VIEW_ISO3):
            w, h = image.size
            size2 = (int(S60 * (w + h)), int(C60 * (w + h)))

            if self.view == VIEW_ISO1:
                transform = (
                    0.5 / S60, 0.5 / C60, -h / 2, -0.5 / S60, 0.5 / C60, h / 2)
                xy = self.plotCoords(
                    [(probe.xmin, probe.ymin, 0.0),
                     (probe.xmax, probe.ymin, 0.0)]
                )
                x = xy[0][0]
                y = xy[1][1]

            elif self.view == VIEW_ISO2:
                transform = (
                    0.5 / S60, -0.5 / C60, w / 2, 0.5 / S60, 0.5 / C60, -w / 2)

                xy = self.plotCoords(
                    [(probe.xmin, probe.ymax, 0.0),
                     (probe.xmin, probe.ymin, 0.0)]
                )
                x = xy[0][0]
                y = xy[1][1]
            else:
                transform = (
                    -0.5 / S60,
                    -0.5 / C60,
                    w + h / 2,
                    0.5 / S60,
                    -0.5 / C60,
                    h / 2,
                )
                xy = self.plotCoords(
                    [(probe.xmax, probe.ymax, 0.0),
                     (probe.xmin, probe.ymax, 0.0)]
                )
                x = xy[0][0]
                y = xy[1][1]

            affine = image.transform(
                size2, Image.AFFINE, transform, resample=RESAMPLE)
            # Super impose a white image
            white = Image.new("RGBA", affine.size, (255,) * 4)
            # compose the two images affine and white with mask the affine
            image = Image.composite(affine, white, affine)
            del white

        else:
            x, y = self.plotCoords([(probe.xmin, probe.ymin, 0.0)])[0]

        self._probeTkImage = ImageTk.PhotoImage(image)
        return x, y

    # ----------------------------------------------------------------------
    # Process/Compile all lines of all blocks for paths
    # ----------------------------------------------------------------------
    def processPaths(self):
        linecount = 0
        curline = 0
        status_fill = None

        if self._processed or PROCESS_TIME <= 0 or self.isProcessing() or self.app.running:
            return

        try:
            self._inProcessing = True
            self.status("Processing Block Paths...")
            self.update()
            gc.collect()
            self._last = (0.0, 0.0, 0.0)
            self.cnc.initPath()
            self.cnc.resetAllMargins()
            startTime = before = time.time()
            blockcount = len(self.gcode.blocks)

            enabledBlocks = []
            disabledBlocks = []
            lastEnabledMap = {}
            lastEnabled = None
            for bid, block in enumerate(self.gcode.blocks):
                if self._cancelProcessing:
                    msg = "Canceled processing block paths."
                    self.status(msg)
                    return
                if time.time() - startTime > PROCESS_TIME:
                    errmsg = "Timeout while processing blocks in sorting. Processed 0 blocks."
                    sys.stderr.write(_("{0}\n").format(errmsg))
                    raise AlarmException(errmsg)
                if time.time() - before > 0.25:
                    self.update()
                    before = time.time()

                if block.enable:
                    enabledBlocks.append( (bid,block) )
                    linecount += len(block)
                    lastEnabled = block
                else:
                    disabledBlocks.append( (bid,block) )
                    linecount += len(block)
                    lastEnabledMap[bid] = lastEnabled

            if linecount:
                # get fancy with a status bar
                status_fill = self.app.statusbar.itemcget(self.app.statusbar.doneBox, "fill")
                self.app.statusbar.itemconfig(self.app.statusbar.doneBox, fill="DarkGrey")
                self.app.statusbar.setLimits(0, linecount)
                self.app.statusbar.setProgress(0, 0)

            n = 1
            for i, (bid, block) in enumerate(enabledBlocks + disabledBlocks):
                start = True  # start location found
                block.resetPath()
                linenum = len(block)
                if bid in lastEnabledMap:
                    lb = lastEnabledMap[bid]
                    if lb is None:
                        self._last = (0.0, 0.0, 0.0)
                        self.cnc.initPath()
                    else:
                        self._last = (lb.ex, lb.ey, lb.ez)
                        self.cnc.initPath(lb.ex, lb.ey, lb.ez)

                # Process block paths
                for j, line in enumerate(block):
                    n -= 1
                    curline += 1
                    if n <= 0:
                        # Force a periodic update since this loop can take time
                        if self._cancelProcessing:
                            msg = "Canceled processing block paths."
                            self.status(msg)
                            return
                        if time.time() - startTime > PROCESS_TIME:
                            errmsg = "Timeout while processing blocks. Processed {0} blocks.".format(i)
                            sys.stderr.write(_("{0}\n").format(errmsg))
                            raise AlarmException(errmsg)
                        if time.time() - before > 0.25:
                            if linecount:
                                self.app.statusbar.setProgress(curline, linecount)
                            self.status("Processing Block: {0}/{1} | Line: {2}/{3}".format(
                                i+1, blockcount, j+1, linenum))
                            self.update()
                            before = time.time()
                        n = 1000
                    start = self.processLine(block, line, i, j, start)

        except AlarmException:
            errmsg = "Processing takes TOO Long: {0}. Interrupted...".format(PROCESS_TIME)
            sys.stderr.write(_("{0}\n").format(errmsg))
            sys.stderr.flush()
            self.status(errmsg)
            self.update()
        except Exception:
            errmsg = "Unexpected Error.."
            sys.stderr.write(_("{0}\n").format(errmsg))
            sys.stderr.flush()
            self.status(errmsg)
            self.update()
            raise
        else:
            if linecount:
                self.app.statusbar.setProgress(curline, linecount)
            msg = "Finished processing block paths."
            self.status(msg)
            self.update()
        finally:
            if status_fill is not None:
                self.app.statusbar.itemconfig(self.app.statusbar.doneBox, fill=status_fill)
            self.app.statusbar.clear()
            gc.collect()
            self.gcode.calculateMargins()
            self._inProcessing = False
            self._processed = True

    # ----------------------------------------------------------------------
    # Process/Compile a single line of a block
    # ----------------------------------------------------------------------
    def processLine(self, block, line, i, j, start):
        try:
            cmd = self.gcode.evaluate(
                CNC.compileLine(line), self.app)
            if isinstance(cmd, tuple):
                cmd = None
            else:
                cmd = CNC.breakLine(cmd)
        except AlarmException:
            errmsg = "Timeout while processing block command. Processed {0}/{1} blocks. Line #{2}/{3}"\
                .format(i, len(self.gcode.blocks), j, len(block))
            sys.stderr.write(_("{0}\n").format(errmsg))
            raise AlarmException(errmsg)
        except Exception:
            sys.stderr.write(
                _(">>> ERROR: {}\n").format(str(sys.exc_info()[1]))
            )
            sys.stderr.write(_("     line: {}\n").format(line))
            cmd = None

        if cmd is None:
            block.addPathData(None)
        else:
            pathdata = self.processPath(block, cmd, start)
            block.addPathData(pathdata)
            block.endPath(self.cnc.x, self.cnc.y, self.cnc.z)
            if start and self.cnc.gcode in (1, 2, 3):
                # Mark as start the first non-rapid motion
                block.startPath(self.cnc.x, self.cnc.y, self.cnc.z)
                return False
        return start

    # ----------------------------------------------------------------------
    # Process a motion command into the tuple (coordinate, color, line_mode)
    # ----------------------------------------------------------------------
    def processPath(self, block, cmds, start=False):
        self.cnc.motionStart(cmds)
        active = self.isActive()
        color = ENABLE_COLOR if block.color is None else block.color

        xyz = self.cnc.motionPath()
        self.cnc.motionEnd()
        if xyz:
            self.cnc.pathLength(block, xyz)
            if self.cnc.gcode in (1, 2, 3):
                block.pathMargins(xyz, active, start)
                self.cnc.pathMargins(block)
            if block.enable:
                if self.cnc.gcode == 0 and self.draw_rapid:
                    xyz[0] = self._last
                self._last = xyz[-1]

            if self.cnc.gcode == 0:
                line_mode = LINEMODE_RAPID
                return (xyz, color, line_mode, self.cnc.feed)
            elif self.cnc.gcode in (1, 2, 3):
                line_mode = LINEMODE_ENABLED if active else LINEMODE_DISABLED
                if not active:
                    color = DISABLE_COLOR
                return (xyz, color, line_mode, self.cnc.feed)

        return None

    # ----------------------------------------------------------------------
    # Calculate if the current motion path is active or inactive
    # ----------------------------------------------------------------------
    def isActive(self):
        if not ADV_BLOCK_COLORS:
            return True
        if not (FILTER_S or FILTER_Z):
            return True

        if FILTER_S and self.cnc.sval is not None:
            # show if greater than zero/threshold
            active = self.cnc.sval > FILTER_SVAL
        else:
            active = True

        if FILTER_Z:
            # show if at surface or below
            active = active and self.cnc.zval <= FILTER_ZVAL

        return active

    # ----------------------------------------------------------------------
    # Draw the paths for the whole gcode file
    # ----------------------------------------------------------------------
    def drawPaths(self):
        if self._processed and self._drawn:
            self.showPaths()
            self.event_generate("<<ListboxSelect>>")
        elif self._processed:
            self.drawBlockPaths()
            self.event_generate("<<ListboxSelect>>")
        else:
            self.event_generate("<<Reprocess>>")

    # ----------------------------------------------------------------------
    # Draw block paths. As many as possible until timeout.
    # ----------------------------------------------------------------------
    def drawBlockPaths(self, drawAll=True):
        if DRAW_TIME <= 0:
            self.showPaths()
            self.event_generate("<<ListboxSelect>>")
            self._drawn = True
            return

        try:
            self._inDrawBlockPaths = True
            self.update()
            startTime = before = time.time()
            n = 1
            pathcount = pathtotal = 0
            blockcount = len(self.gcode.blocks)
            for i, block in enumerate(self.gcode.blocks):
                if not drawAll and (not block.enable or len(block._path) > 0):
                    continue
                pathcount = len(block._pathdata)
                for j, pathdata in enumerate(block._pathdata):
                    n -= 1
                    pathtotal += 1
                    if n <= 0:
                        if time.time() - startTime > DRAW_TIME:
                            raise AlarmException()
                        # Force a periodic update since this loop can take time
                        if time.time() - before > 0.1:
                            if not self.app.running:
                                self.status("Drawing Block: {0}/{1} | Path: {2}/{3}"\
                                    .format(i+1, blockcount, j+1, pathcount))
                            if not FAST_RENDER:
                                self.showPaths()
                            self.update()
                            before = time.time()
                        n = 1000
                    path = self.drawPath(pathdata, block.enable)
                    block.addPath(path)
                    if path:
                        self._items[path] = i, j
            msg = "Rendering {0} Blocks, {1} Paths...".format(blockcount, pathtotal)
            interrupted = "."
        except AlarmException:
            msg = "Drawing paths takes TOO Long: {0}s. Interrupted Block: {1}/{2} | Path: {3}/{4} Rendering..."\
                .format(DRAW_TIME, i+1, blockcount, j+1, pathcount)
            interrupted = "...Interrupted."
            sys.stderr.write(_("{0}\n").format(msg))
            sys.stderr.flush()
        finally:
            self._inDrawBlockPaths = False
        self.status(msg)
        self.update()
        self.showPaths()
        self.status("Rendered {0} Blocks, {1} Paths{2}".format(blockcount, pathtotal, interrupted))
        self.update()
        self._drawn = True

    # ----------------------------------------------------------------------
    # Show paths. Show or hide existing path lines on canvas, depending on settings
    # ----------------------------------------------------------------------
    def showPaths(self):
        if self.draw_paths:
            self.itemconfig("Path:enabled", state='normal')
            if self.hide_disabled:
                self.itemconfig("Path:enabled:hidden", state='hidden')
            else:
                self.itemconfig("Path:enabled:hidden", state='normal')

            if self.filter_inactive:
                self.itemconfig("Path:disabled", state='hidden')
                self.itemconfig("Path:disabled:hidden", state='hidden')
            else:
                self.itemconfig("Path:disabled", state='normal')
                if self.hide_disabled:
                    self.itemconfig("Path:disabled:hidden", state='hidden')
                else:
                    self.itemconfig("Path:disabled:hidden", state='normal')
        else:
            self.itemconfig("Path:enabled", state='hidden')
            self.itemconfig("Path:disabled", state='hidden')
            self.itemconfig("Path:enabled:hidden", state='hidden')
            self.itemconfig("Path:disabled:hidden", state='hidden')

        if self.draw_rapid:
            self.itemconfig("Path:rapid", state='normal')
            if self.hide_disabled:
                 self.itemconfig("Path:rapid:hidden", state='hidden')
            else:
                 self.itemconfig("Path:rapid:hidden", state='normal')
        else:
             self.itemconfig("Path:rapid", state='hidden')
             self.itemconfig("Path:rapid:hidden", state='hidden')

        self.tag_raise("Path:rapid")
        self.tag_raise("Path:disabled")
        self.tag_raise("Path:enabled")
        self.tag_raise("Path")
        self.raise_gantry()
        self.update()

    # ----------------------------------------------------------------------
    # Hide paths. Hide path lines on canvas
    # ----------------------------------------------------------------------
    def hidePaths(self):
        self.itemconfig("Path", state='hidden')
        self.update()

    # ----------------------------------------------------------------------
    # Draw path. Add line to canvas
    # ----------------------------------------------------------------------
    def drawPath(self, pathdata, enable=True):
        if not pathdata:
            return None
        xyz = pathdata[PD_COORDS]
        fill = pathdata[PD_COLOR]
        line_mode = pathdata[PD_LINEMODE]
        if not enable:
            fill = DISABLE_COLOR
        coords = self.plotCoords(xyz)
        if coords:
            tag_postfix = "" if enable else ":hidden"
            if line_mode == LINEMODE_RAPID:
                return self.create_line(
                    coords, fill=fill, width=0,
                    dash=(4, 3), tags=["Path", "Path:rapid{0}".format(tag_postfix)],
                    state='hidden'
                )
            elif line_mode == LINEMODE_ENABLED:
                return self.create_line(
                    coords, fill=fill, width=0,
                    cap="projecting",
                    tags=["Path", "Path:enabled{0}".format(tag_postfix)],
                    state='hidden'
                )
            elif line_mode == LINEMODE_DISABLED:
                return self.create_line(
                    coords, fill=fill, width=0, cap="projecting",
                    tags=["Path", "Path:disabled{0}".format(tag_postfix)],
                    state='hidden'
                )

        return None

    # ----------------------------------------------------------------------
    # Clear canvas and all references to path data.
    # ----------------------------------------------------------------------
    def reprocessPathData(self):
        if self.isProcessing() or self.app.running:
            return
        self._processed = False
        self.processPaths()

    # ----------------------------------------------------------------------
    # Clear and redraw canvas and all references to path data.
    # ----------------------------------------------------------------------
    def redraw(self, view=None, fit2screen=False):
        if self.isProcessing() or self._inDraw:
            return
        try:
            self._inDraw = True
            self.delete('all')
            self.clearPaths()
        finally:
            self._inDraw = False
        self.draw(view=view, fit2screen=fit2screen)

    # ----------------------------------------------------------------------
    def isProcessing(self):
        return self._inProcessing or self._cancelProcessing

    # ----------------------------------------------------------------------
    # Clear canvas and all references to path data.
    # ----------------------------------------------------------------------
    def clearPaths(self, event=None):
        self.itemconfig("Path", state='hidden')
        self.delete('Path')
        self._drawn = False
        self._in_zoom = False
        self._items.clear()
        for block in self.gcode.blocks:

            for path in block._path:
                if path is not None:
                    self.delete(path)
                    if path in self._items:
                        del self._items[path]
            block.clearPaths()

        gc.collect()
        self.update()

    # ----------------------------------------------------------------------
    # Clear canvas and all references to path data.
    # ----------------------------------------------------------------------
    def redrawBlockPaths(self, bid):

        if bid >= len(self.gcode.blocks):
            return
        block = self.gcode[bid]
        if block is None:
            return

        pathcount = len(block._path)
        for path in block._path:
            if path is not None:
                self.delete(path)
                del self._items[path]
            if self.isProcessing():
                return

        block.clearPaths()
        for j, pathdata in enumerate(block._pathdata):
            if self.isProcessing():
                return
            if j >= pathcount:
                # only redraw the same number as before, could be 0
                break
            path = None
            if pathdata is not None:
                path = self.drawPath(pathdata, block.enable)
            block.addPath(path)
            if path:
                self._items[path] = bid, j
        gc.collect()
        self.showPaths()

    # ----------------------------------------------------------------------
    # Clear ruler line
    # ----------------------------------------------------------------------
    def clearRuler(self):
        if self._vector:
            self.delete(self._vector)
            self._vector = None
        self.delete("Ruler")

    # ----------------------------------------------------------------------
    # Return plotting coordinates for a 3d xyz path
    #
    # NOTE: Use the tkinter._flatten() to pass to self.coords() function
    # ----------------------------------------------------------------------
    def plotCoords(self, xyz):
        coords = None
        if self.view == VIEW_XY:
            coords = [(p[0] * self.zoom, -p[1] * self.zoom) for p in xyz]
        elif self.view == VIEW_XZ:
            coords = [(p[0] * self.zoom, -p[2] * self.zoom) for p in xyz]
        elif self.view == VIEW_YZ:
            coords = [(p[1] * self.zoom, -p[2] * self.zoom) for p in xyz]
        if self.view == VIEW_XY_IMG:
            coords = [(p[0] * self.zoom, p[1] * self.zoom) for p in xyz]
        elif self.view == VIEW_ISO1:
            coords = [
                (
                    (p[0] * S60 + p[1] * S60) * self.zoom,
                    (+p[0] * C60 - p[1] * C60 - p[2]) * self.zoom,
                )
                for p in xyz
            ]
        elif self.view == VIEW_ISO2:
            coords = [
                (
                    (p[0] * S60 - p[1] * S60) * self.zoom,
                    (-p[0] * C60 - p[1] * C60 - p[2]) * self.zoom,
                )
                for p in xyz
            ]
        elif self.view == VIEW_ISO3:
            coords = [
                (
                    (-p[0] * S60 - p[1] * S60) * self.zoom,
                    (-p[0] * C60 + p[1] * C60 - p[2]) * self.zoom,
                )
                for p in xyz
            ]
        # Check limits handling should be done by caller, elsewhere on the stack.
        # Keep full precision otherwise.
        # Example: _updateScrollBars() checks after calling windowing functions that call plotCoords().
        return coords

    # ----------------------------------------------------------------------
    # Canvas to real coordinates
    # ----------------------------------------------------------------------
    def canvas2xyz(self, i, j):
        if self.view == VIEW_XY:
            x = i / self.zoom
            y = -j / self.zoom
            z = 0

        elif self.view == VIEW_XZ:
            x = i / self.zoom
            y = 0
            z = -j / self.zoom

        elif self.view == VIEW_YZ:
            x = 0
            y = i / self.zoom
            z = -j / self.zoom

        elif self.view == VIEW_ISO1:
            x = (i / S60 + j / C60) / self.zoom / 2
            y = (i / S60 - j / C60) / self.zoom / 2
            z = 0

        elif self.view == VIEW_ISO2:
            x = (i / S60 - j / C60) / self.zoom / 2
            y = -(i / S60 + j / C60) / self.zoom / 2
            z = 0

        elif self.view == VIEW_ISO3:
            x = -(i / S60 + j / C60) / self.zoom / 2
            y = -(i / S60 - j / C60) / self.zoom / 2
            z = 0

        elif self.view == VIEW_XY_IMG:
            x = i / self.zoom
            y = j / self.zoom
            z = 0

        return x, y, z


# =============================================================================
# Canvas Frame with toolbar
# =============================================================================
class CanvasFrame(Frame):
    def __init__(self, master, app, *kw, **kwargs):
        Frame.__init__(self, master, *kw, **kwargs)
        self.app = app

        self.draw_axes = BooleanVar()
        self.draw_grid = BooleanVar()
        self.draw_margin = BooleanVar()
        self.margin_mode = BooleanVar()
        self.draw_probe = BooleanVar()
        self.draw_paths = BooleanVar()
        self.draw_rapid = BooleanVar()
        self.filter_inactive = BooleanVar()
        self.hide_disabled = BooleanVar()
        self.draw_workarea = BooleanVar()
        self.draw_camera = BooleanVar()
        self.view = StringVar()

        self.loadConfig()

        self.view.trace("w", self.viewChange)

        toolbar = Frame(self, relief=RAISED)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=EW)

        self.canvas = CNCCanvas(self, app, takefocus=True, background="White")
        # OpenGL context
        print(f"self.canvas.winfo_id(): {self.canvas.winfo_id()}")
        self.canvas.grid(row=1, column=0, sticky=NSEW)
        sb = Scrollbar(self, orient=VERTICAL, command=self.canvas.yview)
        sb.grid(row=1, column=1, sticky=NS)
        self.canvas.config(yscrollcommand=sb.set)
        sb = Scrollbar(self, orient=HORIZONTAL, command=self.canvas.xview)
        sb.grid(row=2, column=0, sticky=EW)
        self.canvas.config(xscrollcommand=sb.set)

        self.createCanvasToolbar(toolbar)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ----------------------------------------------------------------------
    def addWidget(self, widget):
        self.app.widgets.append(widget)

    # ----------------------------------------------------------------------
    def loadConfig(self):
        global INSERT_COLOR, GANTRY_COLOR, MARGIN_COLOR, GRID_COLOR
        global BOX_SELECT, ENABLE_COLOR, DISABLE_COLOR, SELECT_COLOR, SELECT2_COLOR
        global PROCESS_COLOR, PROCESS_COLOR2, MOVE_COLOR, RULER_COLOR
        global CAMERA_COLOR, PROBE_TEXT_COLOR, CANVAS_COLOR
        global DRAW_TIME, PROCESS_TIME
        global ADV_BLOCK_COLORS, FAST_RENDER
        global FILTER_S, FILTER_SVAL, FILTER_Z, FILTER_ZVAL

        self.draw_axes.set(bool(int(Utils.getBool("Canvas", "axes", True))))
        self.draw_grid.set(bool(int(Utils.getBool("Canvas", "grid", True))))
        self.draw_margin.set(bool(int(Utils.getBool("Canvas", "margin", True))))
        self.margin_mode.set(bool(int(Utils.getBool("Canvas", "margin_mode", True))))
        self.draw_probe.set(bool(int(Utils.getBool("Canvas", "probe", True))))
        self.draw_paths.set(bool(int(Utils.getBool("Canvas", "paths", True))))
        self.draw_rapid.set(bool(int(Utils.getBool("Canvas", "rapid", True))))
        self.filter_inactive.set(bool(int(Utils.getBool("Canvas", "filter_inactive", True))))
        self.hide_disabled.set(bool(int(Utils.getBool("Canvas", "hide_disabled", True))))
        self.draw_workarea.set(bool(int(Utils.getBool("Canvas", "workarea", True))))

        self.view.set(Utils.getStr("Canvas", "view", VIEWS[0]))

        DRAW_TIME = Utils.getInt("Canvas", "drawtime", DRAW_TIME)
        PROCESS_TIME = Utils.getInt("Canvas", "processtime", PROCESS_TIME)
        ADV_BLOCK_COLORS = Utils.getBool("Canvas", "adv_block_colors", ADV_BLOCK_COLORS)
        FAST_RENDER = Utils.getBool("Canvas", "fast_render", FAST_RENDER)
        FILTER_S = Utils.getBool("Canvas", "filter_s", FILTER_S)
        FILTER_Z = Utils.getBool("Canvas", "filter_z", FILTER_Z)
        FILTER_SVAL = Utils.getFloat("Canvas", "filter_sval", FILTER_SVAL)
        FILTER_ZVAL = Utils.getFloat("Canvas", "filter_zval", FILTER_ZVAL)

        INSERT_COLOR = Utils.getStr("Color", "canvas.insert", INSERT_COLOR)
        GANTRY_COLOR = Utils.getStr("Color", "canvas.gantry", GANTRY_COLOR)
        MARGIN_COLOR = Utils.getStr("Color", "canvas.margin", MARGIN_COLOR)
        GRID_COLOR = Utils.getStr("Color", "canvas.grid", GRID_COLOR)
        BOX_SELECT = Utils.getStr("Color", "canvas.selectbox", BOX_SELECT)
        ENABLE_COLOR = Utils.getStr("Color", "canvas.enable", ENABLE_COLOR)
        DISABLE_COLOR = Utils.getStr("Color", "canvas.disable", DISABLE_COLOR)
        SELECT_COLOR = Utils.getStr("Color", "canvas.select", SELECT_COLOR)
        SELECT2_COLOR = Utils.getStr("Color", "canvas.select2", SELECT2_COLOR)
        PROCESS_COLOR = Utils.getStr("Color", "canvas.process", PROCESS_COLOR)
        PROCESS_COLOR2 = Utils.getStr("Color", "canvas.process2", PROCESS_COLOR2)
        MOVE_COLOR = Utils.getStr("Color", "canvas.move", MOVE_COLOR)
        RULER_COLOR = Utils.getStr("Color", "canvas.ruler", RULER_COLOR)
        CAMERA_COLOR = Utils.getStr("Color", "canvas.camera", CAMERA_COLOR)
        PROBE_TEXT_COLOR = Utils.getStr("Color", "canvas.probetext", PROBE_TEXT_COLOR)
        CANVAS_COLOR = Utils.getStr("Color", "canvas.background", CANVAS_COLOR)

    # ----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setInt("Canvas", "drawtime", DRAW_TIME)
        Utils.setInt("Canvas", "processtime", PROCESS_TIME)
        Utils.setStr("Canvas", "view", self.view.get())
        Utils.setBool("Canvas", "axes", self.draw_axes.get())
        Utils.setBool("Canvas", "grid", self.draw_grid.get())
        Utils.setBool("Canvas", "margin", self.draw_margin.get())
        Utils.setBool("Canvas", "margin_mode", self.margin_mode.get())
        Utils.setBool("Canvas", "probe", self.draw_probe.get())
        Utils.setBool("Canvas", "paths", self.draw_paths.get())
        Utils.setBool("Canvas", "rapid", self.draw_rapid.get())
        Utils.setBool( "Canvas", "adv_block_colors", ADV_BLOCK_COLORS)
        Utils.setBool( "Canvas", "fast_render", FAST_RENDER)
        Utils.setBool( "Canvas", "hide_disabled", self.hide_disabled.get())
        Utils.setBool( "Canvas", "filter_inactive", self.filter_inactive.get())
        Utils.setBool( "Canvas", "filter_s", FILTER_S)
        Utils.setBool( "Canvas", "filter_z", FILTER_Z)
        Utils.setFloat("Canvas", "filter_sval", FILTER_SVAL)
        Utils.setFloat("Canvas", "filter_zval", FILTER_ZVAL)
        Utils.setBool( "Canvas", "workarea", self.draw_workarea.get())

    # ----------------------------------------------------------------------
    # Canvas toolbar FIXME XXX should be moved to CNCCanvas
    # ----------------------------------------------------------------------
    def createCanvasToolbar(self, toolbar):
        b = OptionMenu(toolbar, self.view, *VIEWS)
        b.config(padx=0, pady=1)
        b.unbind("F10")
        b.pack(side=LEFT)
        tkExtra.Balloon.set(b, _("Change viewing angle"))

        b = Button(
            toolbar, image=Utils.icons["zoom_in"],
            command=self.canvas.menuZoomIn
        )
        tkExtra.Balloon.set(b, _("Zoom In [Ctrl-=]"))
        b.pack(side=LEFT)

        b = Button(
            toolbar, image=Utils.icons["zoom_out"],
            command=self.canvas.menuZoomOut
        )
        tkExtra.Balloon.set(b, _("Zoom Out [Ctrl--]"))
        b.pack(side=LEFT)

        b = Button(
            toolbar, image=Utils.icons["zoom_on"],
            command=self.canvas.fit2Screen
        )
        tkExtra.Balloon.set(b, _("Fit to screen [F]"))
        b.pack(side=LEFT)

        Label(toolbar, text=_("Tool:"),
              image=Utils.icons["sep"], compound=LEFT).pack(
            side=LEFT, padx=2
        )
        # -----
        # Tools
        # -----
        b = Radiobutton(
            toolbar,
            image=Utils.icons["select"],
            indicatoron=FALSE,
            variable=self.canvas.actionVar,
            value=ACTION_SELECT,
            command=self.canvas.setActionSelect,
        )
        tkExtra.Balloon.set(b, _("Select tool [S]"))
        self.addWidget(b)
        b.pack(side=LEFT)

        b = Radiobutton(
            toolbar,
            image=Utils.icons["pan"],
            indicatoron=FALSE,
            variable=self.canvas.actionVar,
            value=ACTION_PAN,
            command=self.canvas.setActionPan,
        )
        tkExtra.Balloon.set(b, _("Pan viewport [X]"))
        b.pack(side=LEFT)

        b = Radiobutton(
            toolbar,
            image=Utils.icons["ruler"],
            indicatoron=FALSE,
            variable=self.canvas.actionVar,
            value=ACTION_RULER,
            command=self.canvas.setActionRuler,
        )
        tkExtra.Balloon.set(b, _("Ruler [R]"))
        b.pack(side=LEFT)

        # -----------
        # Draw flags
        # -----------
        Label(toolbar, text=_("Draw:"), image=Utils.icons["sep"],
              compound=LEFT).pack(
            side=LEFT, padx=2
        )

        b = Checkbutton(
            toolbar,
            image=Utils.icons["axes"],
            indicatoron=False,
            variable=self.draw_axes,
            command=self.drawAxes,
        )
        tkExtra.Balloon.set(b, _("Toggle display of axes"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["grid"],
            indicatoron=False,
            variable=self.draw_grid,
            command=self.drawGrid,
        )
        tkExtra.Balloon.set(b, _("Toggle display of grid lines"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["margins"],
            indicatoron=False,
            variable=self.draw_margin,
            command=self.drawMargin,
        )
        tkExtra.Balloon.set(b, _("Toggle display of margins"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["margin_trim"],
            indicatoron=False,
            variable=self.margin_mode,
            command=self.drawMarginMode,
        )
        tkExtra.Balloon.set(b, _("Toggle trim margins (inactive)"))
        if ADV_BLOCK_COLORS:
            b.pack(side=LEFT)
        else:
            b.pack_forget()

        b = Checkbutton(
            toolbar,
            text="P",
            image=Utils.icons["measure"],
            indicatoron=False,
            variable=self.draw_probe,
            command=self.drawProbe,
        )
        tkExtra.Balloon.set(b, _("Toggle display of probe"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["endmill"],
            indicatoron=False,
            variable=self.draw_paths,
            command=self.toggleDrawPathsFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle display of paths (G1,G2,G3)"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["rapid"],
            indicatoron=False,
            variable=self.draw_rapid,
            command=self.toggleDrawRapidFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle display of rapid motion (G0)"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["edge"],
            indicatoron=False,
            variable=self.filter_inactive,
            command=self.toggleFilterInactiveFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle filter inactive spindle"))
        if ADV_BLOCK_COLORS:
            b.pack(side=LEFT)
        else:
            b.pack_forget()

        b = Checkbutton(
            toolbar,
            image=Utils.icons["SimpleRectangleAC"],
            indicatoron=False,
            variable=self.hide_disabled,
            command=self.toggleFilterDisabledFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle hide disabled blocks."))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["workspace"],
            indicatoron=False,
            variable=self.draw_workarea,
            command=self.drawWorkarea,
        )
        tkExtra.Balloon.set(b, _("Toggle display of workarea"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["camera"],
            indicatoron=False,
            variable=self.draw_camera,
            command=self.drawCamera,
        )
        tkExtra.Balloon.set(b, _("Toggle display of camera"))
        b.pack(side=LEFT)
        if Camera.cv is None:
            b.config(state=DISABLED)

        # -----------
        # Refresh/redraw/reprocess
        # -----------

        Label(toolbar, image=Utils.icons["sep"],
              compound=LEFT).pack(
            side=LEFT, padx=5
        )

        b = Button(toolbar, image=Utils.icons["refresh"],
                   command=self.refreshPaths)
        tkExtra.Balloon.set(b, _("Refresh paths and motion"))
        b.pack(side=LEFT)

        b = Button(toolbar, image=Utils.icons["refresh_green"],
                   command=self.redraw)
        tkExtra.Balloon.set(b, _("Redraw display [Ctrl-R]"))
        b.pack(side=LEFT)

        b = Button(toolbar, image=Utils.icons["refresh_red"],
                   command=self.reprocessPathData)
        tkExtra.Balloon.set(b, _("Reprocess Path data"))
        self.addWidget(b)
        b.pack(side=LEFT)


        # -----------
        # Draw Timeout
        self.drawTime = tkExtra.Combobox(
            toolbar, width=3, background="White", command=self.drawTimeChange
        )
        tkExtra.Balloon.set(self.drawTime, _("Draw timeout in seconds"))
        self.drawTime.fill(
            ["inf", "0", "1", "2", "3", "5", "10", "15", "20", "30", "45", "60", "120"])
        dt = "inf" if DRAW_TIME == sys.maxsize else DRAW_TIME
        self.drawTime.set(dt)
        self.drawTime.pack(side=RIGHT)
        Label(toolbar, text=_("Draw Timeout:")).pack(side=RIGHT)


        # -----------
        # Process Timeout
        Label(toolbar, image=Utils.icons["sep"],
              compound=RIGHT).pack(
            side=RIGHT, padx=1
        )
        self.processTime = tkExtra.Combobox(
            toolbar, width=3, background="White", command=self.processTimeChange
        )
        tkExtra.Balloon.set(self.processTime, _("Timeout of data processing in seconds"))
        self.processTime.fill(
            ["inf", "0", "1", "5", "10", "30", "60", "120", "180", "300", "600"])
        pt = "inf" if PROCESS_TIME == sys.maxsize else PROCESS_TIME
        self.processTime.set(pt)
        self.processTime.pack(side=RIGHT)
        Label(toolbar, text=_("Process Timeout:")).pack(side=RIGHT)

        # -----------
        # Settings
        Label(toolbar, image=Utils.icons["sep"],
              compound=RIGHT).pack(
            side=RIGHT, padx=1
        )
        b = Button(toolbar, image=Utils.icons["gear"],
                   command=self.settingsPage)
        tkExtra.Balloon.set(b, _("Render Settings"))
        self.addWidget(b)
        b.pack(side=RIGHT)

    # ----------------------------------------------------------------------
    def settingsPage(self):
        self.canvas.app.ribbon.changePage("CAM")
        self.app.tools.setActive("Canvas")

    # ----------------------------------------------------------------------
    def viewChange(self, a=None, b=None, c=None):
        self.event_generate("<<ViewChange>>")

    # ----------------------------------------------------------------------
    def viewXY(self, event=None):
        self.view.set(VIEWS[VIEW_XY])

    # ----------------------------------------------------------------------
    def viewXZ(self, event=None):
        self.view.set(VIEWS[VIEW_XZ])

    # ----------------------------------------------------------------------
    def viewYZ(self, event=None):
        self.view.set(VIEWS[VIEW_YZ])

    # ----------------------------------------------------------------------
    def viewISO1(self, event=None):
        self.view.set(VIEWS[VIEW_ISO1])

    # ----------------------------------------------------------------------
    def viewISO2(self, event=None):
        self.view.set(VIEWS[VIEW_ISO2])

    # ----------------------------------------------------------------------
    def viewISO3(self, event=None):
        self.view.set(VIEWS[VIEW_ISO3])

    # ----------------------------------------------------------------------
    def viewIMG(self, event=None):
        self.view.set(VIEWS[VIEW_XY_IMG])

    # ----------------------------------------------------------------------
    def refreshPaths(self):
        self.canvas.status("Refreshing paths...")
        self.update()
        self.toggleDrawFlag()
        self.canvas.showPaths()
        self.event_generate("<<ListboxSelectRefresh>>")
        self.canvas.status("Refreshed all paths.")
        self.update()

    # ----------------------------------------------------------------------
    def redraw(self, event=None):
        self.toggleDrawFlag()
        self.event_generate("<<Redraw>>")

    # ----------------------------------------------------------------------
    def reprocessPathData(self, event=None):
        self.event_generate("<<Reprocess>>")

    # ----------------------------------------------------------------------
    def toggleDrawFlag(self):
        self.canvas.draw_axes = self.draw_axes.get()
        self.canvas.draw_grid = self.draw_grid.get()
        self.canvas.draw_margin = self.draw_margin.get()
        self.canvas.margin_mode = self.margin_mode.get()
        self.canvas.draw_probe = self.draw_probe.get()
        self.canvas.draw_paths = self.draw_paths.get()
        self.canvas.draw_rapid = self.draw_rapid.get()
        self.canvas.filter_inactive = self.filter_inactive.get()
        self.canvas.hide_disabled = self.hide_disabled.get()
        self.canvas.draw_workarea = self.draw_workarea.get()
        self.canvas.view = VIEWS.index(self.view.get())

    # ----------------------------------------------------------------------
    def toggleDrawPathsFlag(self):
        status = "Showing" if self.draw_paths.get() else "Hiding"
        self.canvas.status("Rendering... {0} paths (G1, G2, G3)...".format(status))
        self.update()
        self.toggleDrawFlag()
        self.canvas.showPaths()
        if self.canvas.draw_paths:
            self.event_generate("<<ListboxSelectRefresh>>")
        self.canvas.status("{0} paths (G1, G2, G3).".format(status))
        self.update()

    # ----------------------------------------------------------------------
    def toggleDrawRapidFlag(self):
        status = "Showing" if self.draw_rapid.get() else "Hiding"
        self.canvas.status("Rendering... {0} rapid paths (G0)...".format(status))
        self.update()
        self.toggleDrawFlag()
        self.canvas.showPaths()
        self.event_generate("<<ListboxSelectRefresh>>")
        self.canvas.tag_raise("Path:rapid")
        self.canvas.tag_raise("Path:rapid:hidden")
        self.canvas.status("{0} rapid paths (G0).".format(status))
        self.update()

    # ----------------------------------------------------------------------
    def toggleFilterInactiveFlag(self):
        status = "Showing" if not self.filter_inactive.get() else "Hiding"
        self.canvas.status("Rendering... {0} inactive paths...".format(status))
        self.update()
        self.toggleDrawFlag()
        self.canvas.showPaths()
        self.event_generate("<<ListboxSelectRefresh>>")
        self.canvas.status("{0} inactive paths.".format(status))
        self.update()

    # ----------------------------------------------------------------------
    def toggleFilterDisabledFlag(self):
        status = "Showing" if not self.filter_inactive.get() else "Hiding"
        self.canvas.status("Rendering... {0} disabled blocks (Editor)...".format(status))
        self.update()
        self.toggleDrawFlag()
        self.canvas.showPaths()
        self.event_generate("<<ListboxSelectRefresh>>")
        self.canvas.status("{0} disabled blocks (Editor).".format(status))
        self.update()

    # ----------------------------------------------------------------------
    def drawAxes(self, value=None):
        if value is not None:
            self.draw_axes.set(value)
        self.canvas.draw_axes = self.draw_axes.get()
        self.canvas.drawAxes()

    # ----------------------------------------------------------------------
    def drawGrid(self, value=None):
        if value is not None:
            self.draw_grid.set(value)
        self.canvas.draw_grid = self.draw_grid.get()
        self.canvas.drawGrid()

    # ----------------------------------------------------------------------
    def drawMargin(self, value=None):
        if value is not None:
            self.draw_margin.set(value)
        self.canvas.margin_mode = self.margin_mode.get()
        self.canvas.draw_margin = self.draw_margin.get()
        self.canvas.drawMargin()

    # ----------------------------------------------------------------------
    def drawMarginMode(self, value=None):
        if value is not None:
            self.margin_mode.set(value)
        self.drawMargin()

    # ----------------------------------------------------------------------
    def drawProbe(self, value=None):
        if value is not None:
            self.draw_probe.set(value)
        self.canvas.draw_probe = self.draw_probe.get()
        self.canvas.drawProbe()

    # ----------------------------------------------------------------------
    def drawWorkarea(self, value=None):
        if value is not None:
            self.draw_workarea.set(value)
        self.canvas.draw_workarea = self.draw_workarea.get()
        self.canvas.drawWorkarea()

    # ----------------------------------------------------------------------
    def drawCamera(self, value=None):
        if value is not None:
            self.draw_camera.set(value)
        if self.draw_camera.get():
            self.canvas.cameraOn()
        else:
            self.canvas.cameraOff()

    # ----------------------------------------------------------------------
    def drawTimeChange(self):
        self.update()
        global DRAW_TIME
        try:
            dt = self.drawTime.get()
            DRAW_TIME = sys.maxsize if dt == "inf" else int(dt)
        except ValueError:
            DRAW_TIME = 5 * 60
        self.redraw()

    # ----------------------------------------------------------------------
    def processTimeChange(self):
        self.update()
        global PROCESS_TIME
        try:
            pt = self.processTime.get()
            PROCESS_TIME = sys.maxsize if pt == "inf" else int(pt)
        except ValueError:
            PROCESS_TIME = 5 * 60
