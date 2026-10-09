# $Id: CNCCanvas.py,v 1.7 2014/10/15 15:04:06 bnv Exp $
#
# Author:       vvlachoudis@gmail.com
# Date: 24-Aug-2014

import math
import time
import sys
import tkDialogs
from numpy import deg2rad
from tkinter_gl import GLCanvas


try:
    import cv2 as cv
except ImportError:
    cv = None

from OpenGL.GL import *
from ctypes import c_void_p
from pyglm.glm import mat4x4, mat3x3, ortho, identity, value_ptr, inverse, translate, rotate, vec2, vec3, vec4, normalize, lookAt, dot, cross, distance, length2
import os

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
    DoubleVar,
    Button,
    Canvas,
    Checkbutton,
    Frame,
    Label,
    Radiobutton,
    Scrollbar,
    OptionMenu,
    Toplevel,
    LabelFrame,
    Variable,
    messagebox,
    Scale
)
import tkinter

import bmath
import Camera
import tkExtra
import Utils
from CNC import CNC, Probe

# Probe mapping we need PIL and numpy
try:
    from PIL import Image, ImageFont, ImageDraw
    import numpy

except Exception:
    from tkinter import Image
    numpy = None

try:
    import OpenGL
    if sys.platform == 'linux':
        # PyOpenGL is broken with wayland:
        OpenGL.setPlatform('x11')
    from OpenGL import GL
except ImportError:
    raise ImportError(
        """
        This example requires PyOpenGL.

        You can install it with "pip install PyOpenGL".
        """)



VIEW_XY = 0
VIEW_XZ = 1
VIEW_YZ = 2
VIEW_ISO1 = 3
VIEW_ISO2 = 4
VIEW_ISO3 = 5
VIEWS = ["X-Y", "X-Z", "Y-Z", "ISO1", "ISO2", "ISO3"]

INSERT_WIDTH2 = 3
GANTRY_R = 4
GANTRY_X = GANTRY_R * 2  # 10
GANTRY_Y = GANTRY_R  # 5
GANTRY_H = GANTRY_R * 5  # 20
DRAW_TIME = 5  # Maximum draw time permitted

# Customizable colors
GANTRY_COLOR = DEFAULT_GANTRY_COLOR ="Red"
MARGIN_COLOR = DEFAULT_MARGIN_COLOR = "Magenta"
GRID_COLOR = DEFAULT_GRID_COLOR ="Gray"
ENABLE_COLOR = DEFAULT_ENABLE_COLOR = "Black"
DISABLE_COLOR = DEFAULT_DISABLE_COLOR = "LightGray"
SELECT_COLOR = DEFAULT_SELECT_COLOR = "Blue"
SELECT2_COLOR = DEFAULT_SELECT2_COLOR = "DarkCyan"
PROCESS_COLOR = DEFAULT_PROCESS_COLOR = "Green"
MOVE_COLOR = DEFAULT_MOVE_COLOR = "DarkCyan"
RULER_COLOR = DEFAULT_RULER_COLOR = "Green"
CAMERA_COLOR = DEFAULT_CAMERA_COLOR = "Cyan"
PROBE_TEXT_COLOR = DEFAULT_PROBE_TEXT_COLOR = "Green"
CANVAS_COLOR_UP = DEFAULT_CANVAS_COLOR_UP = "White" # If 2 different colors are given for the backgound, a vertical gradient is shown
CANVAS_COLOR_DOWN = DEFAULT_CANVAS_COLOR_DOWN = "White"
AXES_TEXT_COLOR = DEFAULT_AXES_TEXT_COLOR = "Black"
RAPID_COLOR = DEFAULT_RAPID_COLOR = ""
customColors = {
    "canvas.gantry": {"color": "GANTRY_COLOR", "description": "Gantry", "canBeBlank": False},
    "canvas.margin": {"color": "MARGIN_COLOR", "description": "Margin (Requires Redraw)", "canBeBlank": False},
    "canvas.grid": {"color": "GRID_COLOR", "description": "Grid (Requires Redraw)", "canBeBlank": False},
    "canvas.enable": {"color": "ENABLE_COLOR", "description": "Enabled Path (Requires Redraw)", "canBeBlank": False},
    "canvas.disable": {"color": "DISABLE_COLOR", "description": "Disabled Path", "canBeBlank": False},
    "canvas.select": {"color": "SELECT_COLOR", "description": "Selected Active", "canBeBlank": False},
    "canvas.select2": {"color": "SELECT2_COLOR", "description": "Selected Inactive", "canBeBlank": False},
    "canvas.process": {"color": "PROCESS_COLOR", "description": "Processed line", "canBeBlank": False},
    "canvas.move": {"color": "MOVE_COLOR", "description": "Move arrow", "canBeBlank": False},
    "canvas.ruler": {"color": "RULER_COLOR", "description": "Ruler", "canBeBlank": False},
    "canvas.camera": {"color": "CAMERA_COLOR", "description": "Camera", "canBeBlank": False},
    "canvas.probetext": {"color": "PROBE_TEXT_COLOR", "description": "Probe Text", "canBeBlank": False},
    "canvas.backgroundUp": {"color": "CANVAS_COLOR_UP", "description": "Background Upper", "canBeBlank": False},
    "canvas.backgroundDown": {"color": "CANVAS_COLOR_DOWN", "description": "Background Lower", "canBeBlank": False},
    "canvas.axestext": {"color": "AXES_TEXT_COLOR", "description": "Axes Text (Requires App restart)", "canBeBlank": False},
    "canvas.rapid": {"color": "RAPID_COLOR", "description": "Rapid Moves (G0) (Requires Redraw)", "canBeBlank": True}
    }

# Fixed colors
INSERT_COLOR = "Blue"
WORK_COLOR = "Orange"
INFO_COLOR = "Gold"

ACTION_SELECT = 0
ACTION_SELECT_SINGLE = 1
ACTION_SELECT_AREA = 2
ACTION_SELECT_DOUBLE = 3

ACTION_PAN = 10
ACTION_ORIGIN = 11
ACTION_ZOOM = 12

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
CLOSE_DISTANCE_TO_ENDS = 15 # Snap to line ends instead to line, if closer than this
MAXDIST = 10000
ZOOM = 1.25
AXIS_LENGTH = 100 # Coord system axis length in pixels


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
    ACTION_ZOOM: "circle"
}

# Path lines Flags are stored in a float32 value for each vertex. 
# Each flag is represented by a bit in that value. It can store up to 24 tags (24 representative bits in an integer float32)
FLAG_SELECTED = 0b1
FLAG_ENABLED = 0b10
#FLAG_XXX = 0b100
#FLAG_XXX = 0b1000

openglFolder = f"{os.path.abspath(os.path.dirname(__file__))}{os.sep}opengl{os.sep}v120{os.sep}"

# Simulator variables
HEIGHTMAP_RES = 10000
MESH_RES = 1000
STOCK_MIN_X = 0
STOCK_MAX_X = 100
STOCK_MIN_Y = 0
STOCK_MAX_Y = 100
STOCK_MIN_Z = -10.
STOCK_MAX_Z = 0.
MILL_TYPES = {"Flat": 0, "Ball": 1}
MILL_TYPE = "Flat"
MILL_DIAMETER = 6.

# -----------------------------------------------------------------------------
def mouseCursor(action):
    return MOUSE_CURSOR.get(action, DEF_CURSOR)
    
# =============================================================================
# Raise an alarm exception
# =============================================================================
class AlarmException(Exception):
    pass


# =============================================================================
# Drawing canvas
# =============================================================================
class CNCCanvas(GLCanvas):
    profile = 'legacy' # Opengl 2.1

    MODE_CNC = 0
    MODE_SIM = 1

    def rgb8(self, colorName):
        return (numpy.array(self.winfo_rgb(colorName)) * 255. / 65535.).astype(int)
    

    def __init__(self, master, app, *kw, **kwargs):
        super().__init__(master) # TODO: Handle takefocus and background parameters
        
        self.parentFrame : Frame = master

        # Global variables
        self.view = 0
        self.app = app
        self.cnc = app.cnc
        self.gcode = app.gcode
        self.actionVar = IntVar()

        self.mode = CNCCanvas.MODE_CNC

        self._gl_initialized_cnc = False
        self._gl_initialized_sim = False

        self.windowing_system = self.app.call('tk', 'windowingsystem')
        version = self.app.call("info", "patchlevel")
        
        # On MacOS / tk <=8.6, swap middle and right mouse buttons
        aqua = self.windowing_system == "aqua"
        major, minor, *_ = map(int, version.split("."))
        old_aqua = aqua and (major, minor) < (8, 7)
        if old_aqua:
            button_mid = "3"
            button_right = "2"
        else:
            button_mid = "2"
            button_right = "3"
        
        # GLSL Version
        self.glslVersion = None

        # Canvas binding
        self.bind("<Configure>", self.configureEvent)
        self.bind("<Motion>", self.motion)
        self.bind("<Button-1>", self.click)
        self.bind("<B1-Motion>", self.buttonMotion)
        self.bind("<ButtonRelease-1>", self.release)
        self.bind("<Double-1>", self.double)

        self.bind("<Button-" + button_mid + ">", self.midClick)
        self.bind("<Shift-B" + button_mid + "-Motion>", self.midRightZoom)
        self.bind("<Shift-B" + button_right + "-Motion>", self.midRightZoom)
        self.bind("<B" + button_mid + "-Motion>", self.pan)
        self.bind("<ButtonRelease-" + button_mid + ">", self.midRelease)
        self.bind("<Button-4>", self.mouseZoomIn)
        self.bind("<Button-5>", self.mouseZoomOut)
        self.bind("<MouseWheel>", self.wheel)
        self.bind("<Button-" + button_right + ">", self.rightClick)
        self.bind("<B" + button_right + "-Motion>", self.rotate)
        self.bind("<ButtonRelease-" + button_right + ">", self.rightRelease)

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

        self.bind("<Control-Key-equal>", self.menuZoomIn)
        self.bind("<Control-Key-minus>", self.menuZoomOut)

        self.x0 = 0.0
        self.y0 = 0.0
        self.zoom = 1.
        self.__tzoom = 1.0  # delayed zoom (temporary)
        self._items = {}
        self._x = self._y = 0
        self._xp = self._yp = 0
        self.action = ACTION_SELECT
        self._mouseAction = None
        self._vector = None
        self._lastActive = None
        self._lastGantry = None
        self._gantryLocation = vec3(0, 0, 0)
        self._drawRequested = False

        self._snapPoint = None
        self._snapPointType = 0

        self.probeMapHeightScale = 1

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
        self.cameraLocation = vec2(0., 0.)
        self._cameraAfter = None  # Camera anchor location "" for gantry
        self._showCamera = False

        self.highlightRuler = False

        self.draw_axes = True  # Drawing flags
        self.draw_grid = True
        self.draw_margin = True
        self.draw_probe = True
        self.draw_workarea = True
        self.draw_paths = True
        self.draw_rapid = True  # draw rapid motions
        self._wx = self._wy = self._wz = 0.0  # work position
        self._dx = self._dy = self._dz = 0.0  # work-machine position

        self._orientSelected = None

        # OPENGL vars
        self.MVMatrix = identity(mat4x4) # Model View Matrix
        self.PMatrix = ortho(-100, 100, -100, 100, -10000, 10000) # Projection matrix. Updated on resize
        
        # self.lines: Dictionary of lines to be drawn. 
        # key: line_id (We increment it for each new line)
        self._line_id = 1
        # item: [x1, y1, z1, x2, y2, z2, dashRatio, selected]
        # dashRatio: 0-1. 1 is solid line
        # Selected: 1 or 0
        self.pathDict = {}
        self.orientDict = {}
        self.probeDict = {}
        self.vectorDict = {}
        
        self.infoVertices = numpy.array([], dtype=numpy.float32)
        self.pathVertices = numpy.array([], dtype=numpy.float32)

        # Selection Rectangle
        self.SelectionRectVertices = numpy.array([], dtype=numpy.float32)
        
        self.pathArrows = {}
        self.infoArrows = {}
        self.vectorArrowsDict = {}
        
        self._modelCenter = vec3(0, 0, 0)
        self._modelSize = 100.0
        # Text items
        self._text_id = 1
        self.text = {} # text_id[location, text value, color]
        self.probeText = {}
        
        self.reset()

        # Print OpenGL version info
        print("========== OpenGL ==========")
        print("OpenGL version:", glGetString(GL_VERSION))
        print("OpenGL renderer:", glGetString(GL_RENDERER))
        print("GLSL version:", glGetString(GL_SHADING_LANGUAGE_VERSION))

        try:
            profile_mask = glGetIntegerv(GL_CONTEXT_PROFILE_MASK)
        except:
            profile_mask = "?"
            
        print("Profile mask:", profile_mask)

        # Try GLSL 1.20. If failed, change to 1.50
        global openglFolder
        try:
            self.initGL()
            print("Running GLSL 1.20")
            self.glslVersion = "1.20"
        except Exception as e:
            print("----------")
            print(e)
            print("GLSL 1.20 failed. Trying GLSL 1.50...")
            print("----------")

            try:
                openglFolder = f"{os.path.abspath(os.path.dirname(__file__))}{os.sep}opengl{os.sep}v150{os.sep}"
                self.initGL()
                print("Running GLSL 1.50")
                self.glslVersion = "1.50"
            except Exception as e:
                print("----------")
                print(e)
                print("GLSL 1.50 failed. Trying GLSL 1.00...")
                print("----------")
                openglFolder = f"{os.path.abspath(os.path.dirname(__file__))}{os.sep}opengl{os.sep}v100{os.sep}"
                self.initGL()
                print("Running GLSL 1.00")
                self.glslVersion = "1.00"
        
        print("============================")

        # Data of Texture atlas for text rendering
        self.create_char_texture(f"{os.path.abspath(os.path.dirname(__file__))}{os.sep}opengl{os.sep}DejaVuSans.ttf", 12)

        self.createAxes(AXIS_LENGTH)
        self.createGantry()

        self.initPosition()

        # Milling vars
        self.millType = StringVar(value="Flat")
        self.millDiameter = DoubleVar(value=6.0)
        self.stockOpacity = IntVar(value=100)
        self.millSelectedPathsOnly = BooleanVar(value=False)
    
    def set_mode(self, mode):
        if mode == self.mode:
            return

        self.mode = mode

        if mode == CNCCanvas.MODE_SIM:
            self.initGL()

        self.fit2Screen()
    
    def get_camera_image(self):
        if (self.camera.image is None) or (cv is None):
            return None
        
        tex = cv.flip(cv.cvtColor(self.camera.image, cv.COLOR_BGR2RGBA), 0)
    
        return tex

    def create_char_texture(self, font_name, font_size):
        font = ImageFont.truetype(font_name, font_size)

        # Get font metrics (ascent = top above baseline, descent = below baseline)
        ascent, descent = font.getmetrics()

        # Full safe height for drawing
        self.textHeight = ascent + descent

        # Printable ASCII only — Pillow+libraqm fails on control chars
        self.charOffsetAndWidth = [[0, 0] for _ in range(128)]
        offset = 0
        for ch in range(32, 127):
            width = font.getlength(chr(ch))
            self.charOffsetAndWidth[ch] = [offset, width]
            offset += width
        
        image = Image.new("RGBA", (int(offset), int(self.textHeight)), (0, 0, 0, 0)) # type: ignore
        
        # Create a drawing object
        draw = ImageDraw.Draw(image)

        # Create an image with all the ascii chars
        for ch in range(32, 127):
            draw.text((self.charOffsetAndWidth[ch][0], 0), chr(ch), fill="white", font=font)
        
        image = image.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL expects the y-axis to be flipped

        self.charTextureAtlas = numpy.array(image)

        glBindTexture(GL_TEXTURE_2D, self.textTexture)

        # Set the texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        # Upload texture data to OpenGL
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, len(self.charTextureAtlas[0]), len(self.charTextureAtlas), 0, GL_RGBA, GL_UNSIGNED_BYTE, self.charTextureAtlas)

        # Generate Mipmap
        glGenerateMipmap(GL_TEXTURE_2D)
    
    def create_text(self, textDict, location, text, color):
        # Color is a tuple or numpy array of three 8bit integers
        textDict[self._text_id] = [location, text, color]

        id = self._text_id
        self._text_id += 1

        return id

    def initGL(self):
        if self.mode == CNCCanvas.MODE_CNC:
            self.initGL_cnc()
        elif self.mode == CNCCanvas.MODE_SIM:
            self.initGL_sim()

    
    def initGL_cnc(self):
        if self._gl_initialized_cnc == True:
            return
        
        self._gl_initialized_cnc = True

        # Create all the OpenGL shader programs

        # ----- BACKGROUND PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "BackgroundVS.shd", "r") as file:
            BackgroundVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "BackgroundFS.shd", "r") as file:
            BackgroundFSCode = file.read()

        self.backgroundProgram = self.createProgram(BackgroundVSCode, BackgroundFSCode)

        # Create a Vertex Buffer Object (VBO)
        self.backgroundVBO = glGenBuffers(1)
        
        # Since the background is fixed, we set the buffer data here
        glUseProgram(self.backgroundProgram)      
        glBindBuffer(GL_ARRAY_BUFFER, self.backgroundVBO)
        
        vertices = numpy.array([1, 2, 3, 1, 3, 4], dtype=numpy.float32)
        
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        
        # ----- LINES PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "LinesVS.shd", "r") as file:
            LinesVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "LinesFS.shd", "r") as file:
            LinesFSCode = file.read()

        self.linesProgram = self.createProgram(LinesVSCode, LinesFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.marginsVBO = glGenBuffers(1)
        self.workAreaVBO = glGenBuffers(1)
        self.infoVBO = glGenBuffers(1)
        self.orientVBO = glGenBuffers(1)
        self.probeVBO = glGenBuffers(1)
        self.vectorVBO = glGenBuffers(1)
        self.gridVBO = glGenBuffers(1)

        self.linesProgram_id = glGetAttribLocation(self.linesProgram, "id")
        self.linesProgram_xyz = glGetAttribLocation(self.linesProgram, "xyz")
        self.linesProgram_pos = glGetAttribLocation(self.linesProgram, "pos")
        self.linesProgram_colorValue = glGetAttribLocation(self.linesProgram, "colorValue")
        self.linesProgram_dashRatio = glGetAttribLocation(self.linesProgram, "dashRatio")
        self.linesProgram_flags = glGetAttribLocation(self.linesProgram, "flags")
        self.linesProgram_mvp = glGetUniformLocation(program=self.linesProgram, name="MVP")
        self.linesProgram_zoom = glGetUniformLocation(program=self.linesProgram, name="zoom")
        self.linesProgram_select_color = glGetUniformLocation(program=self.linesProgram, name="selectColor")
        self.linesProgram_select2_color = glGetUniformLocation(program=self.linesProgram, name="select2Color")
        self.linesProgram_disable_color = glGetUniformLocation(program=self.linesProgram, name="disableColor")
        
        # ----- TOOLPATH PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "ToolPathVS.shd", "r") as file:
            ToolPathVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "ToolPathFS.shd", "r") as file:
            ToolPathFSCode = file.read()

        self.toolPathProgram = self.createProgram(ToolPathVSCode, ToolPathFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.pathVBO = glGenBuffers(1)

        # ----- AXES PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "AxesVS.shd", "r") as file:
            AxesVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "AxesFS.shd", "r") as file:
            AxesFSCode = file.read()

        self.axesProgram = self.createProgram(AxesVSCode, AxesFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.axesVBO = glGenBuffers(1)
        
        # ----- GANTRY PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "GantryVS.shd", "r") as file:
            GantryVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "GantryFS.shd", "r") as file:
            GantryFSCode = file.read()

        self.gantryProgram = self.createProgram(GantryVSCode, GantryFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.gantryVBO = glGenBuffers(1)

        # ----- GANTRY LINES PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "GantryLinesVS.shd", "r") as file:
            GantryLinesVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "GantryLinesFS.shd", "r") as file:
            GantryLinesFSCode = file.read()

        self.gantryLinesProgram = self.createProgram(GantryLinesVSCode, GantryLinesFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.gantryLinesVBO = glGenBuffers(1)

        # ----- SELECTION RECT PROGRAM ------
        # Program to draw the selection rectangle
        # Vertex Shader code
        with open(openglFolder + "SelectionRectVS.shd", "r") as file:
            SelectionRectVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "SelectionRectFS.shd", "r") as file:
            SelectionRectFSCode = file.read()

        self.SelectionRectProgram = self.createProgram(SelectionRectVSCode, SelectionRectFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.SelectionRectVBO = glGenBuffers(1)

        # ----- TEXT PROGRAM ------
        # Program to draw text
        # Vertex Shader code
        with open(openglFolder + "TextVS.shd", "r") as file:
            TextVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "TextFS.shd", "r") as file:
            TextFSCode = file.read()

        self.TextProgram = self.createProgram(TextVSCode, TextFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.TextVBO = glGenBuffers(1)
        self.AxesTextVBO = glGenBuffers(1)
        self.ProbeTextVBO = glGenBuffers(1)

        # ----- PROBE MAP PROGRAM ------
        # Program to draw text
        # Vertex Shader code
        with open(openglFolder + "ProbeMapVS.shd", "r") as file:
            ProbeMapVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "ProbeMapFS.shd", "r") as file:
            ProbeMapFSCode = file.read()

        self.ProbeMapProgram = self.createProgram(ProbeMapVSCode, ProbeMapFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.ProbeMapVBO = glGenBuffers(1)

        # ----- IMAGE PROGRAM ------
        # Program to draw images
        # Vertex Shader code
        with open(openglFolder + "ImageVS.shd", "r") as file:
            ImageVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "ImageFS.shd", "r") as file:
            ImageFSCode = file.read()

        self.ImageProgram = self.createProgram(ImageVSCode, ImageFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.CameraVBO = glGenBuffers(1)

        # Create textures
        self.textTexture = glGenTextures(1)
        self.cameraTexture = glGenTextures(1)

        # Fill the buffer of the camera rectangle, which is fixed
        glBindBuffer(GL_ARRAY_BUFFER, self.CameraVBO)
        CameraRectVertices = numpy.array([1., 2., 3., 1., 3., 4.], dtype=numpy.float32)
        glBufferData(GL_ARRAY_BUFFER, CameraRectVertices.nbytes, CameraRectVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        
        # ----- ARROW PROGRAM ------
        # Program to draw arrows
        # Vertex Shader code
        with open(openglFolder + "ArrowVS.shd", "r") as file:
            ArrowVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "ArrowFS.shd", "r") as file:
            ArrowFSCode = file.read()

        self.ArrowProgram = self.createProgram(ArrowVSCode, ArrowFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.pathArrowsVBO = glGenBuffers(1)
        self.infoArrowsVBO = glGenBuffers(1)
        self.vectorArrowsVBO = glGenBuffers(1)
        
        # ----- CROSSHAIR PROGRAM ------
        # Program to draw the Camera Crosshair
        # Vertex Shader code
        with open(openglFolder + "CrossHairVS.shd", "r") as file:
            CrossHairVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "CrossHairFS.shd", "r") as file:
            CrossHairFSCode = file.read()

        self.CrossHairProgram = self.createProgram(CrossHairVSCode, CrossHairFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.CrossHairVBO = glGenBuffers(1)

        # Fill the buffer of the crosshair, which is fixed
        glBindBuffer(GL_ARRAY_BUFFER, self.CrossHairVBO)
        CrossHairVertices = numpy.arange(1, 293, dtype=numpy.float32)
        glBufferData(GL_ARRAY_BUFFER, CrossHairVertices.nbytes, CrossHairVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    # ----- SNAP POINT PROGRAM ------
        # Program to draw the Snap Point
        # Vertex Shader code
        with open(openglFolder + "SnapPointVS.shd", "r") as file:
            SnapPointVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "SnapPointFS.shd", "r") as file:
            SnapPointFSCode = file.read()

        self.SnapPointProgram = self.createProgram(SnapPointVSCode, SnapPointFSCode)
        
        # Create a Vertex Buffer Object (VBO)
        self.SnapPointVBO = glGenBuffers(1)

        # Fill the buffer of the snappoint, which is fixed
        glBindBuffer(GL_ARRAY_BUFFER, self.SnapPointVBO)
        SnapPointVertices = numpy.array([1, 2, 3, 4, 1], dtype=numpy.float32)
        glBufferData(GL_ARRAY_BUFFER, SnapPointVertices.nbytes, SnapPointVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glClearColor(0., 0., 0., 1.0)
    
    def initGL_sim(self):
        if self._gl_initialized_sim == True:
            return
        
        self._gl_initialized_sim = True

        # Create textures (height map) and framebuffers for milling simulation.
        # The MillFS fragment shader reads the mapheight from FBO 0, writes changes to FBO 1, and then that area is copied back to FBO 0.
        self.textures = glGenTextures(2)
        self.fbos = glGenFramebuffers(2)

        for i in range(2):
            glBindTexture(GL_TEXTURE_2D, self.textures[i])

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

            # One-channel 32-bit floating point height.
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RG8, HEIGHTMAP_RES, HEIGHTMAP_RES, 0, GL_RG, GL_UNSIGNED_BYTE, None)
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[i])
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.textures[i], 0)
            glDrawBuffers([GL_COLOR_ATTACHMENT0])

            status = glCheckFramebufferStatus(GL_FRAMEBUFFER)

            if status != GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError("Height FBO {} incomplete: {}".format(i, hex(status)))

        glBindTexture(GL_TEXTURE_2D, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        self.resetStock()

        # Create all the OpenGL shader programs

        # ----- MILLING PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "MillVS.shd", "r") as file:
            MillVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "MillFS.shd", "r") as file:
            MillFSCode = file.read()

        self.millProgram = self.createProgram(MillVSCode, MillFSCode)

        # Create a Vertex Buffer Object (VBO)
        self.millVBO = glGenBuffers(1)

        self.millProgram_pos = glGetAttribLocation(self.millProgram, "pos")
        self.millProgram_heightMap = glGetUniformLocation(self.millProgram, "heightMap")
        self.millProgram_pA = glGetUniformLocation(self.millProgram, "pA")
        self.millProgram_pB = glGetUniformLocation(self.millProgram, "pB")
        self.millProgram_toolRadius = glGetUniformLocation(self.millProgram, "toolRadius")
        self.millProgram_toolType = glGetUniformLocation(self.millProgram, "toolType")
        self.millProgram_workMin = glGetUniformLocation(self.millProgram, "workMin")
        self.millProgram_workMax = glGetUniformLocation(self.millProgram, "workMax")

        # We create the fixed fullscreen triangle for the milling texture rendering
        vertices = numpy.array([-1, -1, 3, -1, -1, 3], dtype=numpy.float32)
        glBindBuffer(GL_ARRAY_BUFFER, self.millVBO)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # ----- STOCK TOP PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "StockMaterialVS.shd", "r") as file:
            StockMaterialVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "StockMaterialFS.shd", "r") as file:
            StockMaterialFSCode = file.read()

        self.stockTopProgram = self.createProgram(StockMaterialVSCode, StockMaterialFSCode)

        # Create a Vertex Buffer Object (VBO)
        self.stockTopVBO = glGenBuffers(1)

        # Create an Element Buffer Object (EBO)
        self.stockTopEBO = glGenBuffers(1)

        # Create the stock material vertices and indices
        self.updateStockMaterialBuffers(MESH_RES, MESH_RES)

        # ----- STOCK BOTTOM PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "StockBottomVS.shd", "r") as file:
            StockBottomVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "StockBottomFS.shd", "r") as file:
            StockBottomFSCode = file.read()

        self.stockBottomProgram = self.createProgram(StockBottomVSCode, StockBottomFSCode)

        # Create a Vertex Buffer Object (VBO)
        self.stockBottomVBO = glGenBuffers(1)

        # Create the stock bottom vertex indices
        indices = numpy.array([1, 3, 2, 1, 4, 3], dtype=numpy.float32)
              
        glBindBuffer(GL_ARRAY_BUFFER, self.stockBottomVBO)     
        glBufferData(GL_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # ----- STOCK SIDE PROGRAM ------
        # Vertex Shader code
        with open(openglFolder + "StockSideVS.shd", "r") as file:
            StockSideVSCode = file.read()

        # Fragment Shader code
        with open(openglFolder + "StockSideFS.shd", "r") as file:
            StockSideFSCode = file.read()

        self.stockSideProgram = self.createProgram(StockSideVSCode, StockSideFSCode)

        # Create a Vertex Buffer Object (VBO)
        self.stockSideVBO = glGenBuffers(1)

        self.stockSideProgram_index = glGetAttribLocation(self.stockSideProgram, "index")
        self.stockSideProgram_mvp = glGetUniformLocation(program=self.stockSideProgram, name="MVP")
        self.stockSideProgram_heightMap = glGetUniformLocation(self.stockSideProgram, "heightMap")
        self.stockSideProgram_side = glGetUniformLocation(self.stockSideProgram, "side")
        self.stockSideProgram_zmin = glGetUniformLocation(self.stockSideProgram, "zmin")
        self.stockSideProgram_zmax = glGetUniformLocation(self.stockSideProgram, "zmax")
        self.stockSideProgram_p1 = glGetUniformLocation(self.stockSideProgram, "p1")
        self.stockSideProgram_p2 = glGetUniformLocation(self.stockSideProgram, "p2")
        self.stockSideProgram_opacity = glGetUniformLocation(self.stockSideProgram, "opacity")
        self.stockSideProgram_light1dir = glGetUniformLocation(program=self.stockSideProgram, name="light1dir")
        self.stockSideProgram_light2dir = glGetUniformLocation(program=self.stockSideProgram, name="light2dir")

        # Create the stock side vertex indices
        indices = numpy.array([1, 2, 3, 1, 3, 4], dtype=numpy.float32)
              
        glBindBuffer(GL_ARRAY_BUFFER, self.stockSideVBO)     
        glBufferData(GL_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def updateStockMaterialBuffers(self, nx, ny):
        # Vertices (normalized from 0. to 1.)

        xval, yval = numpy.indices((nx, ny), dtype=numpy.float32)
        xval /= nx - 1
        yval /= ny - 1
        vertices = numpy.stack([xval.T.ravel(), yval.T.ravel()], axis=1)
              
        glBindBuffer(GL_ARRAY_BUFFER, self.stockTopVBO)     
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Indices

        i = numpy.arange(nx - 1, dtype=numpy.uint32)
        j = numpy.arange(ny - 1, dtype=numpy.uint32)

        I, J = numpy.meshgrid(i, j)

        bl = J * nx + I
        br = bl + 1
        tl = bl + nx
        tr = tl + 1

        indices = numpy.stack([
            bl, br, tr,
            bl, tr, tl
        ], axis=-1).ravel()

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.stockTopEBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        
    def createProgram(self, vertexShaderCode, fragmentShaderCode):
        # Compile Vertex Shader
        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertexShaderCode)
        glCompileShader(vertex_shader)
        if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(vertex_shader))

        # Compile Fragment Shader
        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragmentShaderCode)
        glCompileShader(fragment_shader)
        if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(fragment_shader))

        # Link Shaders into a Program
        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glLinkProgram(shader_program)
        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(shader_program))

        # Clean up shaders (no longer needed after linking)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        
        return shader_program
        
    def create_line(self, linesDict, xyz, colorRGB, dashRatio, flags = FLAG_ENABLED):
        # xyz is an array of arrays of 3d coords
        linesDict[self._line_id] = [xyz, colorRGB, dashRatio, flags]
        
        id = self._line_id
        # Increment the line id for the next line
        self._line_id += 1
        
        return id
    
    def create_arrow(self, arrows, id, location, direction, width, height, colorRGB, flags = FLAG_ENABLED):
        arrows[id] = [location, direction, width, height, colorRGB, flags]
    
    def set_arrow(self, arrows, arrowsBuffer, linesVertices, lineId, position, width = 0, height = 0):
        """
        Add arrow to a line id from the numpy array linesVertices.
        Position can be 'none', 'first', 'last' or 'both'
        """

        if position == 'none':
            if (lineId + 0.1) in arrows:
                del arrows[lineId + 0.1]

            if (lineId + 0.2) in arrows:
                del arrows[lineId + 0.2]
        
        else:
            lines16 = numpy.reshape(linesVertices, (-1, 16))
            line16 = lines16[lines16[:, 0] == lineId]

            if len(line16) == 0:
                return
            
            if position == 'first' or position == 'both':
                p_tip = vec3(line16[0, 1:4])
                p_base = vec3(line16[0, 9:12])
                dir = p_tip - p_base
                colorValue = line16[0, 5]
                R = (int(colorValue) & 0xFF0000) >> 16
                G = (int(colorValue) & 0xFF00) >> 8
                B = int(colorValue) & 0xFF
                colorRGB = [R, G, B]
                flags = line16[0, 7]

                self.create_arrow(arrows, lineId + 0.1, p_tip, dir, width, height, colorRGB, flags)
            
            if position == 'last' or position == 'both':
                p_tip = vec3(line16[-1, 9:12])
                p_base = vec3(line16[-1, 1:4])
                dir = p_tip - p_base
                colorValue = line16[-1, 5]
                R = (int(colorValue) & 0xFF0000) >> 16
                G = (int(colorValue) & 0xFF00) >> 8
                B = int(colorValue) & 0xFF
                colorRGB = [R, G, B]
                flags = line16[-1, 7]

                self.create_arrow(arrows, lineId + 0.2, p_tip, dir, width, height, colorRGB, flags)
        
        self.update_arrows_buffer(arrowsBuffer, arrows)


    
    def create_oval(self, lines, xyz_bottomleft, xyz_topright, colorRGB, dashRatio, flags = FLAG_ENABLED):
        p_bl = vec3(xyz_bottomleft)
        p_tr = vec3(xyz_topright)
        center = (p_bl + p_tr) / 2.
        Rx = abs(p_tr.x - center.x)
        Ry = abs(p_tr.y - center.y)
        
        xyz = []
        
        for angle in range(0, 360, 5):
            xyz.append([center.x + Rx * numpy.cos(numpy.deg2rad(angle)),
                        center.y + Ry * numpy.sin(numpy.deg2rad(angle)),
                        center.z])
            xyz.append([center.x + Rx * numpy.cos(numpy.deg2rad(angle + 5)),
                        center.y + Ry * numpy.sin(numpy.deg2rad(angle + 5)),
                        center.z])
            
        
        return self.create_line(lines, xyz, colorRGB, dashRatio, flags)
    
    def update_lines_buffer(self, buffer, linesDict, updateModelDimensions = False):        
        # In order to be compatible with Pi 3, we are using GLSL 1.0. It doesn't allow constant parameters per line in the fragment shader. They are always
        # interpolated between vertices. Then, we must assign the parameter twice, once per vertex, with the same value
        vertexArray = []
        
        maxX = maxY = maxZ = -999999
        minX = minY = minZ = 999999
        
        for id, data in linesDict.items():
            xyz = data[0]
            # We take xyz coords in pairs to create separate lines
            for i in range(len(xyz) - 1):
                
                length = math.sqrt(math.pow(xyz[i+1][0]-xyz[i][0], 2) + math.pow(xyz[i+1][1]-xyz[i][1], 2) + math.pow(xyz[i+1][2]-xyz[i][2], 2))
                colorValue = (data[1][0] << 16) + (data[1][1] << 8) + data[1][2] # RGB
                
                vertexArray.extend([
                    # Vertex 1
                    id,
                    xyz[i][0], # x1
                    xyz[i][1], # y1
                    xyz[i][2], # z1
                    0, # 0 for starting point, length for end point
                    colorValue, # RGB
                    data[2], # dashRatio
                    data[3], # flags
                    # Vertex 2
                    id,
                    xyz[i+1][0], # x1
                    xyz[i+1][1], # y1
                    xyz[i+1][2], # z1
                    length,
                    colorValue, # RGB
                    data[2], # dashRatio
                    data[3], # flags
                ])
                
                if updateModelDimensions:
                    maxX = max(max(maxX, xyz[i][0]), xyz[i+1][0])
                    maxY = max(max(maxY, xyz[i][1]), xyz[i+1][1])
                    maxZ = max(max(maxZ, xyz[i][2]), xyz[i+1][2])
                    minX = min(min(minX, xyz[i][0]), xyz[i+1][0])
                    minY = min(min(minY, xyz[i][1]), xyz[i+1][1])
                    minZ = min(min(minZ, xyz[i][2]), xyz[i+1][2])

        if updateModelDimensions:
            if len(linesDict) == 0:
                self._modelCenter = vec3(0, 0, 0)
                self._modelSize = 100
            else:
                self._modelCenter = vec3((maxX + minX) / 2, (maxY + minY) / 2, (maxZ + minZ) / 2)
                self._modelSize = math.sqrt(math.pow(maxX-minX, 2) + math.pow(maxY-minY, 2) + math.pow(maxZ-minZ, 2))
        
        vertices = numpy.array(vertexArray, dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the VBO

        return vertices


    def update_arrows_from_lines(self, arrows, arrowsBuffer, linesVertices):
        """
        Update arrow color and flags from lines
        """

        if len(arrows) == 0:
            return
        
        lines16 = numpy.reshape(linesVertices, (-1, 16))

        for arrowId in arrows:
            lineId = int(arrowId)
            line16 = lines16[lines16[:, 0] == lineId]
            if len(line16) > 0:
                line16 = line16[0]
                #arrows[id] = [location, direction, width, height, colorRGB, flags]

                # Copy color from line
                colorValue = line16[5]
                R = (int(colorValue) & 0xFF0000) >> 16
                G = (int(colorValue) & 0xFF00) >> 8
                B = int(colorValue) & 0xFF
                colorRGB = [R, G, B]
                arrows[arrowId][4] = colorRGB
                
                # Copy flags from line
                arrows[arrowId][5] = line16[7]
        
        self.update_arrows_buffer(arrowsBuffer, arrows)


    def update_arrows_buffer(self, buffer, arrows):        
        vertexArray = []
        
        for id, data in arrows.items():
            colorValue = (data[4][0] << 16) + (data[4][1] << 8) + data[4][2] # RGB
            
            vertexArray.extend([
                # Vertex 1
                id,
                1.,
                data[0][0], # location.x
                data[0][1], # location.y
                data[0][2], # location.z
                data[1][0], # direction.x
                data[1][1], # direction.y
                data[1][2], # direction.z
                data[2], # width
                data[3], # height
                colorValue,
                data[5], # flags
                # Vertex 2
                id,
                2.,
                data[0][0], # location.x
                data[0][1], # location.y
                data[0][2], # location.z
                data[1][0], # direction.x
                data[1][1], # direction.y
                data[1][2], # direction.z
                data[2], # width
                data[3], # height
                colorValue,
                data[5], # flags
                # Vertex 3
                id,
                3.,
                data[0][0], # location.x
                data[0][1], # location.y
                data[0][2], # location.z
                data[1][0], # direction.x
                data[1][1], # direction.y
                data[1][2], # direction.z
                data[2], # width
                data[3], # height
                colorValue,
                data[5], # flags
            ])
        
        vertices = numpy.array(vertexArray, dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the VBO

        return vertices
    
    def update_text_buffer(self, buffer, textDict: dict):
        char_data = []
        
        for id in textDict.keys():
            hOffset = 0

            location = textDict[id][0]
            text = textDict[id][1]
            color = textDict[id][2]
            colorValue = (color[0] << 16) + (color[1] << 8) + color[2] # RGB

            for ch in range(len(text)):
                # We define a quad as 2 triangles (6 vertices)
                char_data.extend([
                # Bottom left
                    id, # Text id
                    1, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                # Bottom left
                    id, # Text id
                    2, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                # Bottom left
                    id, # Text id
                    3, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                # Bottom left
                    id, # Text id
                    1, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                # Bottom left
                    id, # Text id
                    3, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                # Bottom left
                    id, # Text id
                    4, # Vertex index
                    location[0], # Location of the bottom left corner
                    location[1],
                    location[2],
                    hOffset,
                    self.charOffsetAndWidth[ord(text[ch])][0], # Char offset in texture atlas in pixels
                    self.charOffsetAndWidth[ord(text[ch])][1], # Char width in texture atlas in pixels
                    self.textHeight, #Char height in texture atlas
                    colorValue,
                ])

                hOffset += self.charOffsetAndWidth[ord(text[ch])][1]
            
        textVertices = numpy.array(char_data, dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glBufferData(GL_ARRAY_BUFFER, textVertices.nbytes, textVertices, GL_DYNAMIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the VBO

        return textVertices


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
        # Snapping point?
        if self._snapPoint is not None:
            data = "%.4f %.4f %.4f" % (self._snapPoint.x, self._snapPoint.y, self._snapPoint.z)
        # XY view?
        elif self.viewAngle(vec3(0, 0, 1)) == 0:
            xy_w = self.canvas2WorldXY(vec2(event.x, event.y), 0)
            data = "%.4f %.4f -" % (xy_w.x, xy_w.y)
        # YZ view?
        elif self.viewAngle(vec3(1, 0, 0)) == 0:
            xy_w = self.canvas2WorldYZ(vec2(event.x, event.y), 0)
            data = "- %.4f %.4f" % (xy_w.y, xy_w.z)
        # XZ view?
        elif self.viewAngle(vec3(0, 1, 0)) == 0:
            xy_w = self.canvas2WorldXZ(vec2(event.x, event.y), 0)
            data = "%.4f - %.4f" % (xy_w.x, xy_w.z)
        # Other views perpendicular to the Z axis
        elif abs(self.viewAngle(vec3(0, 0, 1))) == 90:
            angleX = self.viewAngle(vec3(1, 0, 0))
            if angleX > 45:
                xy_w = self.canvas2WorldXZ(vec2(event.x, event.y), 0)
                data = "%.4f - %.4f" % (xy_w.x, xy_w.z)
            else:
                xy_w = self.canvas2WorldYZ(vec2(event.x, event.y), 0)
                data = "- %.4f %.4f" % (xy_w.y, xy_w.z)
        # Any other view
        else:
            xy_w = self.canvas2WorldXY(vec2(event.x, event.y), 0)
            data = "%.4f %.4f %.4f" % (xy_w.x, xy_w.y, 0)
        
        self.event_generate("<<Coords>>", data=data)

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
        self.configure(cursor=mouseCursor(self.action))

        if self.action == ACTION_SELECT:
            self._snapPoint = None
        
        # Erase the RULER / MOVE arrow
        self._vector = None

        self.queueDraw()

    # ----------------------------------------------------------------------
    def actionCancel(self, event=None):
        if self.action != ACTION_SELECT or (
            self._mouseAction != ACTION_SELECT and self._mouseAction is not None
        ):
            self.setAction(ACTION_SELECT)
            return "break"

    # ----------------------------------------------------------------------
    def setActionSelect(self, event=None):
        self.setAction(ACTION_SELECT)
        self.status(_("Select objects with mouse"))

    # ----------------------------------------------------------------------
    def setActionPan(self, event=None):
        self.setAction(ACTION_PAN)
        self.status(_("Pan viewport"))

    # ----------------------------------------------------------------------
    def setActionOrigin(self, event=None):
        self.setAction(ACTION_ORIGIN)
        self._mouseAction = ACTION_ORIGIN
        self.status(_("Click to set the origin (zero)"))

    # ----------------------------------------------------------------------
    def setActionMove(self, event=None):
        self.setAction(ACTION_MOVE)
        self.status(_("Move selected objects horizontally (Hold SHIFT Key to move in Z)"))

    # ----------------------------------------------------------------------
    def setActionGantry(self, event=None):
        self.setAction(ACTION_GANTRY)
        self.status(_("Move CNC gantry to mouse location"))

    # ----------------------------------------------------------------------
    def setActionWPOS(self, event=None):
        self.setAction(ACTION_WPOS)
        self.status(
            _("Set mouse location as current machine position (X/Y only)"))

    # ----------------------------------------------------------------------
    def setActionRuler(self, event=None):
        self.setAction(ACTION_RULER)
        self.status(_("Drag a ruler to measure distances"))

    # ----------------------------------------------------------------------
    def setActionAddMarker(self, event=None):
        self.setAction(ACTION_ADDORIENT)
        self.status(_("Add an orientation marker"))

    # ----------------------------------------------------------------------
    # Move gantry to mouse location
    # ----------------------------------------------------------------------
    def actionGantry(self, x, y):
        xy_w = self.canvas2WorldXY(vec2(x, y))
        
        if xy_w is not None:
            self.app.goto(xy_w.x, xy_w.y, None)
        else:
            self.status(
                _("ERROR: Cannot set Gantry location with the current view (Too parallel to the XY plane)"))
        
        self.setAction(ACTION_SELECT)

    # ----------------------------------------------------------------------
    # Set the work coordinates to mouse location
    # ----------------------------------------------------------------------
    def actionWPOS(self, x, y):
        xy_w = self.canvas2WorldXY(vec2(x, y))
        
        if xy_w is not None:
            self.app.mcontrol._wcsSet(xy_w.x, xy_w.y, None)
        else:
            self.status(
                _("ERROR: Cannot set WPOS with the current view (Too parallel to the XY plane)"))
        
        self.setAction(ACTION_SELECT)

    # ----------------------------------------------------------------------
    # Add an orientation marker at mouse location
    # ----------------------------------------------------------------------
    def actionAddOrient(self, x, y):
        clickedPoint, pointType = self.snapPoint(vec2(x, y))
        
        # Proyect the canvas cx, cy point to the world xy plane
        if clickedPoint is None:
            uv = self.canvas2WorldXY(vec2(x, y))
        else:
            uv = vec2(clickedPoint.x, clickedPoint.y)

        if uv is None:
            self.status(
                _("ERROR: Cannot set X-Y marker with the current view (Too parallel to the XY plane)"))
            return
        
        self._orientSelected = len(self.gcode.orient)
        self.gcode.orient.add(CNC.vars["wx"], CNC.vars["wy"], uv.x, uv.y)
        self.event_generate("<<OrientSelect>>", data=self._orientSelected)
        self.setAction(ACTION_SELECT)

        self.status(
                _("X-Y marker created."))

    # ----------------------------------------------------------------------
    # Find item selected
    # ----------------------------------------------------------------------
    def click(self, event):
        self.focus_set()
        self._x = self._xp = event.x
        self._y = self._yp = event.y

        if event.state & CONTROLSHIFT_MASK == CONTROLSHIFT_MASK:
            self.actionGantry(event.x, event.y)
            return

        elif self.action == ACTION_SELECT:
            self._mouseAction = ACTION_SELECT_SINGLE

        elif self.action == ACTION_MOVE:
            self._vector = None
            self.vectorDict = {}
            self.vectorArrowsDict = {}

            # Check if we clicked on a selected item
            try:
                for item in self.find_overlapping(
                    event.x - CLOSE_DISTANCE,
                    event.y - CLOSE_DISTANCE,
                    event.x + CLOSE_DISTANCE,
                    event.y + CLOSE_DISTANCE,
                    self.pathVertices
                ):
                    if self.isSelected(item, self.pathVertices):
                        break
                else:
                    self._mouseAction = ACTION_SELECT_SINGLE
                    return
            except Exception:
                self._mouseAction = ACTION_SELECT_SINGLE
                return
            
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))
            
            if self._snapPoint is None:
                return
            
            start = self._snapPoint

            self._moveFrom = start
            
            self._vector = self.create_line(self.vectorDict,
                                            [[start.x, start.y, start.z], [start.x, start.y, start.z]],
                                            self.rgb8(MOVE_COLOR),
                                            1.)
            vectorVertices = self.update_lines_buffer(self.vectorVBO, self.vectorDict)

            # Draw arrows
            self.set_arrow(self.vectorArrowsDict,
                            self.vectorArrowsVBO,
                            vectorVertices,
                            self._vector,
                            'last',
                            10,
                            10)
            
            self._lastEnd = start
            self._mouseAction = ACTION_MOVE

        elif self.action  == ACTION_RULER:
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))
            
            # Are we clicking on an already existing measure end?
            if self._vector is not None and self._snapPoint is not None:
                currentStart = self.vectorDict[self._vector][0][0]
                currentEnd = self.vectorDict[self._vector][0][1]

                if distance(self._snapPoint, currentEnd) * self.zoom <= CLOSE_DISTANCE:
                    self._mouseAction = ACTION_RULER
                    return
                
                if distance(self._snapPoint, currentStart) * self.zoom <= CLOSE_DISTANCE:
                    self.vectorDict[self._vector][0][0] = currentEnd
                    self._mouseAction = ACTION_RULER
                    return
            
            self._vector = None
            self.vectorDict = {}
            self.vectorArrowsDict = {}
            self.status("")

            start = self._snapPoint

            if start is not None:
                self._vector = self.create_line(self.vectorDict,
                                                [[start.x, start.y, start.z], [start.x, start.y, start.z]],
                                                self.rgb8(RULER_COLOR),
                                                1.)
                vectorVertices = self.update_lines_buffer(self.vectorVBO, self.vectorDict)

                # Draw arrows
                self.set_arrow(self.vectorArrowsDict,
                                self.vectorArrowsVBO,
                                vectorVertices,
                                self._vector,
                                'both',
                                10,
                                10)
                
                self._lastEnd = start
                self._mouseAction = ACTION_RULER

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
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))

            if self._snapPoint is None:
                xy_w = self.canvas2WorldXY(vec2(event.x, event.y))
            else:
                xy_w = self._snapPoint
                
            if xy_w is not None:
                self.app.insertCommand(_("origin {:g} {:g} {:g}").format(xy_w.x, xy_w.y, 0),
                                   True)
            else:
                self.status(
                _("ERROR: Cannot set Origin with the current view (Too parallel to the XY plane)"))
            
            self.setActionSelect()

        elif self.action == ACTION_PAN:
            self.pan(event)
        
        self.queueDraw()

    def isSelected(self, lineId, lineVertices) -> bool:
        lines16 = numpy.reshape(lineVertices, (-1, 16))
        line16 = lines16[lines16[:, 0] == lineId]

        if len(line16) == 0:
            return False
        
        # Flags at item 7 of the line data
        return (int(line16[0][7]) & FLAG_SELECTED) == FLAG_SELECTED



    def midClick(self, event):
        self.focus_set()
        self._x = self._xp = event.x
        self._y = self._yp = event.y
    
    def rightClick(self, event):
        self.focus_set()
        self._x = event.x
        self._y = event.y
    
    def rotate(self, event):
        if (self._x == event.x and self._y == event.y):
            return
        
        self.configure(cursor=mouseCursor(ACTION_ROTATE))
        self._mouseAction = ACTION_ROTATE

        RotAxis = normalize(vec4(event.y - self._y, event.x - self._x, 0, 0))
        
        RotAxis = inverse(self.MVMatrix) * RotAxis

        # Rotate about the Center of the screen
        rotationCenter = self.canvas2World(vec2(self.winfo_width() / 2., self.winfo_height() / 2.))

        self.MVMatrix = translate(self.MVMatrix, rotationCenter)

        self.MVMatrix = rotate(self.MVMatrix,
            0.01 * math.sqrt(pow(event.y - self._y, 2) + math.pow(event.x - self._x, 2)),
            vec3(RotAxis.x, RotAxis.y, RotAxis.z)) # type: ignore

        self.MVMatrix = translate(self.MVMatrix, -rotationCenter)
        
        self._x = event.x
        self._y = event.y
        
        self.cameraPosition()
        
        self.queueDraw()
    
    def projectPoint(self, point : vec3, planePoint : vec3, planeNormal : vec3) -> vec3:
        """
        Return the projection of a point to a plane, which is defined by a point and vector
        """
        vPlanePoint = point - planePoint
        N = normalize(planeNormal)
        distance = dot(vPlanePoint, N)

        return point - distance * N
    
    def viewNormal(self) -> vec3:
        """
        Return the current view normal vector in world coordinates
        """
        MVPinv = inverse(self.PMatrix * self.MVMatrix)

        # We define a line perpendicular to the canvas
        p1 = (MVPinv * vec4(0, 0, 1, 1)).xyz
        p2 = (MVPinv * vec4(0, 0, 0, 1)).xyz
        
        v12 = p2 - p1
        return normalize(v12)
    # ----------------------------------------------------------------------
    # Canvas motion button 1
    # ----------------------------------------------------------------------
    def buttonMotion(self, event):
        if self._mouseAction == ACTION_SELECT_AREA:
            self.updateSelectionRect(self._x, self._y, event.x, event.y)

        elif self._mouseAction in (ACTION_SELECT_SINGLE, ACTION_SELECT_DOUBLE):
            if abs(event.x - self._x) > 4 or abs(event.y - self._y) > 4:
                self._mouseAction = ACTION_SELECT_AREA
                self.updateSelectionRect(self._x, self._y, event.x, event.y)

        elif self._mouseAction == ACTION_MOVE:
            if self._vector:
                # Calculate the end snap point
                self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y), True)

                if (event.state & SHIFT_MASK) == 0: # Horizontal move
                    if self._snapPoint is None:
                        if abs(self.viewAngle(vec3(0, 0, 1))) == 90: # Current view parallel to the XY plane
                            end = self.canvas2WorldPlane(vec2(event.x, event.y), self.viewNormal(), self._moveFrom, 0)
                            end = self.projectPoint(end, self._moveFrom, vec3(0, 0, 1))
                        else: # Other views
                            end = self.canvas2WorldPlane(vec2(event.x, event.y), vec3(0, 0, 1), self._moveFrom, 0)
                    else:
                        end = self.projectPoint(self._snapPoint, self._moveFrom, vec3(0, 0, 1))
                
                else: # Z move
                    if self._snapPoint is None:
                        moveFrom_u = self.world2Canvas(self._moveFrom)
                        p1 = self.canvas2World(moveFrom_u)
                        p2 = self.canvas2World(vec2(event.x, event.y))
                        v12 = p2 - p1
                        translation = dot(v12, vec3(0, 0, 1)) * vec3(0, 0, 1)
                        end = self._moveFrom + translation
                    else:
                        end = vec3(self._moveFrom.x, self._moveFrom.y, self._snapPoint.z)

                # Change the _vector line end and update the corresponding opengl buffer
                self.vectorDict[self._vector][0][1] = [end.x, end.y, end.z]
                vectorVertices = self.update_lines_buffer(self.vectorVBO, self.vectorDict)

                # Draw arrows
                self.set_arrow(self.vectorArrowsDict,
                               self.vectorArrowsVBO,
                               vectorVertices,
                               self._vector,
                               'last',
                               10,
                               10)

                selectedIds = self.getSelection(self.pathVertices)

                self.move(self.pathVertices, selectedIds, end - self._lastEnd, self.pathVBO)

                start = vec3(self.vectorDict[self._vector][0][0])
                v12 = end - start

                self.status(
                    _("dx={:g}  dy={:g}  dz={:g}  length={:g}  dxy={:g}  angleXY={:g}").format(
                        v12.x,
                        v12.y,
                        v12.z,
                        distance(start, end),
                        distance(vec2(v12.x, v12.y), vec2(0, 0)),
                        math.degrees(math.atan2(v12.y, v12.x)),
                    )
                )
                
                self._lastEnd = end

                self.queueDraw()
        
        elif self._mouseAction == ACTION_RULER:
            if self._vector:
                # Calculate the end snap point
                self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))

                # Draw the line to the current cursor point or to the snap point, if found
                if self._snapPoint is None:
                    if abs(self.viewAngle(vec3(0, 0, 1))) == 90:
                        end = self.canvas2World(vec2(event.x, event.y))
                    else:    
                        end = self.canvas2WorldXY(vec2(event.x, event.y), 0)
                else:
                    end = self._snapPoint

                # Change the _vector line end and update the corresponding opengl buffer
                self.vectorDict[self._vector][0][1] = [end.x, end.y, end.z]
                vectorVertices = self.update_lines_buffer(self.vectorVBO, self.vectorDict)

                # Draw arrows
                self.set_arrow(self.vectorArrowsDict,
                               self.vectorArrowsVBO,
                               vectorVertices,
                               self._vector,
                               'both',
                               10,
                               10)

                start = vec3(self.vectorDict[self._vector][0][0])
                v12 = end - start

                if self._snapPoint is not None:
                    self.status(
                        _("dx={:g}  dy={:g}  dz={:g}  length={:g}  dxy={:g}  angleXY={:g}").format(
                            v12.x,
                            v12.y,
                            v12.z,
                            distance(start, end),
                            distance(vec2(v12.x, v12.y), vec2(0, 0)),
                            math.degrees(math.atan2(v12.y, v12.x)),
                        )
                    )
                else:
                    self.status("")
                
                self._lastEnd = end

                self.queueDraw()

        elif self._mouseAction == ACTION_PAN:
            self.pan(event)

        self.setMouseStatus(event)

        self.queueDraw()
    
    def move(self, linesVertices, lineIds, translation : vec3, bufferToUpdate = None):
        lines16 = numpy.reshape(linesVertices, (-1, 16))
        mask = numpy.isin(lines16[:, 0], lineIds)

        lines16[mask, 1:4] += translation
        lines16[mask, 9:12] += translation

        if bufferToUpdate:
            glBindBuffer(GL_ARRAY_BUFFER, bufferToUpdate)
            glBufferSubData(GL_ARRAY_BUFFER, 0, linesVertices.nbytes, linesVertices)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            self.queueDraw()

    def find_overlapping(self, x1, y1, x2, y2, lines):
        # Unit coordinates of the selection area boundaries
        xy1 = self.canvas2Unit(vec2(x1, y1))
        xy2 = self.canvas2Unit(vec2(x2, y2))

        xmin = min(xy1.x, xy2.x)
        xmax = max(xy1.x, xy2.x)
        ymin = min(xy1.y, xy2.y)
        ymax = max(xy1.y, xy2.y)
        
        # lines is a numpy array containing data for n lines
        # It has a size of 16·n, dtype=float32
        # It contains alternatively the starting and end point of a line in World coordinates.
        # A point is defined with 8 float32 numbers
        
        points = (numpy.reshape(lines, (-1, 8))[:, 1:4]).reshape((-1, 3))# x,y,z
        additionalColumn = numpy.ones((points.shape[0], 1), dtype=numpy.float32)
        
        points = numpy.hstack((points, additionalColumn)).reshape((-1, 4))

        # Change world coordinates of the line points to canvas unit coords
        MVP = numpy.array(self.PMatrix * self.MVMatrix)
        
        pointsCanvasUnit = (MVP @ points.T).T
        
        # Keep just x and y. Reshape to have starting and end point of each line in the same row
        linesCanvasUnit = pointsCanvasUnit[:, :2].reshape((-1, 4))

        dx = linesCanvasUnit[:, 2] - linesCanvasUnit[:, 0]
        dy = linesCanvasUnit[:, 3] - linesCanvasUnit[:, 1]

        p = numpy.stack([-dx, dx, -dy, dy], axis=1)  # shape (N, 4)
        q = numpy.stack([linesCanvasUnit[:, 0] - xmin, xmax - linesCanvasUnit[:, 0],
                    linesCanvasUnit[:, 1] - ymin, ymax - linesCanvasUnit[:, 1]], axis=1)

        with numpy.errstate(divide='ignore', invalid='ignore'):
            r = q / p  # shape (N, 4)

        # Identify conditions
        mask_neg = p < 0
        mask_pos = p > 0
        mask_zero_and_q_neg = (p == 0) & (q < 0)
        any_outside = numpy.any(mask_zero_and_q_neg, axis=1)

        # Initialize u1 and u2
        u1 = numpy.where(mask_neg, r, 0.0)
        u2 = numpy.where(mask_pos, r, 1.0)

        u1_max = numpy.max(u1, axis=1)
        u2_min = numpy.min(u2, axis=1)

        intersects = (u1_max <= u2_min) & ~any_outside
        
        # Get the ids of the overlapped lines (id is the 1st parameter of the lines array)
        lineIds = lines.reshape((-1, 16))[:, 0]
        
        selectedIds = numpy.unique(lineIds[intersects]).tolist()
        
        return selectedIds
        
    def find_enclosed(self, x1, y1, x2, y2, lines):
        # Unit coordinates of the selection area boundaries
        xy1 = self.canvas2Unit(vec2(x1, y1))
        xy2 = self.canvas2Unit(vec2(x2, y2))

        xmin = min(xy1.x, xy2.x)
        xmax = max(xy1.x, xy2.x)
        ymin = min(xy1.y, xy2.y)
        ymax = max(xy1.y, xy2.y)
        
        # lines is a numpy array containing data for n lines
        # It has a size of 16·n, dtype=float32
        # It contains alternatively the starting and end point of a line in World coordinates.
        # A point is defined with 8 float32 numbers
        
        points = (numpy.reshape(lines, (-1, 8))[:, 1:4]).reshape((-1, 3))# x,y,z
        additionalColumn = numpy.ones((points.shape[0], 1), dtype=numpy.float32)
        
        points = numpy.hstack((points, additionalColumn)).reshape((-1, 4))

        # Change world coordinates of the line points to canvas unit coords
        MVP = numpy.array(self.PMatrix * self.MVMatrix)
        
        pointsCanvasUnit = (MVP @ points.T).T
        
        # Keep just x and y. Reshape to have starting and end point of each line in the same row
        linesCanvasUnit = pointsCanvasUnit[:, :2].reshape((-1, 4))

        # Boolean mask for both endpoints inside
        mask = (
            (linesCanvasUnit[:, 0] >= xmin) & (linesCanvasUnit[:, 0] <= xmax) &
            (linesCanvasUnit[:, 1] >= ymin) & (linesCanvasUnit[:, 1] <= ymax) &
            (linesCanvasUnit[:, 2] >= xmin) & (linesCanvasUnit[:, 2] <= xmax) &
            (linesCanvasUnit[:, 3] >= ymin) & (linesCanvasUnit[:, 3] <= ymax)
        )

        lines_16 = numpy.reshape(lines, (-1, 16))[:, 0]
        
        return numpy.unique(lines_16[mask]).tolist() 
    
    def find_closest(self, x, y, lines, tolerance, returnIndex = False, excludeSelected = False):
        # Unit coordinates of the selection area boundaries
        xy = self.canvas2Unit(vec2(x, y))

        # tolerance in unit distance
        unitTolX = tolerance / self.winfo_width() * 2
        unitTolY = tolerance / self.winfo_height() * 2
        
        xmin = xy.x - unitTolX
        xmax = xy.x + unitTolX
        ymin = xy.y - unitTolY
        ymax = xy.y + unitTolY
        
        # lines is a numpy array containing data for n lines
        # It has a size of 16·n, dtype=float32
        # It contains alternatively the starting and end point of a line in World coordinates.
        # A point is defined with 8 float32 numbers
        
        points = (numpy.reshape(lines, (-1, 8))[:, 1:4]).reshape((-1, 3))# x,y,z
        additionalColumn = numpy.ones((points.shape[0], 1), dtype=numpy.float32)
        
        points = numpy.hstack((points, additionalColumn)).reshape((-1, 4))

        # Change world coordinates of the line points to canvas unit coords
        MVP = numpy.array(self.PMatrix * self.MVMatrix)
        
        pointsCanvasUnit = (MVP @ points.T).T
        
        # Keep just x and y. Reshape to have starting and end point of each line in the same row
        linesCanvasUnit = pointsCanvasUnit[:, :2].reshape((-1, 4))

        dx = linesCanvasUnit[:, 2] - linesCanvasUnit[:, 0]
        dy = linesCanvasUnit[:, 3] - linesCanvasUnit[:, 1]

        p = numpy.stack([-dx, dx, -dy, dy], axis=1)  # shape (N, 4)
        q = numpy.stack([linesCanvasUnit[:, 0] - xmin, xmax - linesCanvasUnit[:, 0],
                    linesCanvasUnit[:, 1] - ymin, ymax - linesCanvasUnit[:, 1]], axis=1)

        with numpy.errstate(divide='ignore', invalid='ignore'):
            r = q / p  # shape (N, 4)

        # Identify conditions
        mask_neg = p < 0
        mask_pos = p > 0
        mask_zero_and_q_neg = (p == 0) & (q < 0)
        any_outside = numpy.any(mask_zero_and_q_neg, axis=1)

        # Initialize u1 and u2
        u1 = numpy.where(mask_neg, r, 0.0)
        u2 = numpy.where(mask_pos, r, 1.0)

        u1_max = numpy.max(u1, axis=1)
        u2_min = numpy.min(u2, axis=1)

        intersects = (u1_max <= u2_min) & ~any_outside

        if excludeSelected:
            lines16 = numpy.reshape(lines, (-1, 16))
            selection_mask = (lines16[:, 7].astype(int) & FLAG_SELECTED) == FLAG_SELECTED
            intersects = intersects & ~selection_mask
        
        # TODO: Return the closest one, not the first in the list...

        # If returnIndex is True, return the index of the closest line in the lines array, instead of the closest line ID
        if returnIndex:
            indices = numpy.arange(lines.size / 16)
            selectedIndices = indices[intersects].tolist()

            if len(selectedIndices) == 0:
                return []
            else:
                return [selectedIndices[0]]
            
        else:
            # Get the ids of the overlapped lines (id is the 1st parameter of the lines array)
            lineIds = lines.reshape((-1, 16))[:, 0]
            
            selectedIds = numpy.unique(lineIds[intersects]).tolist()
            
            if len(selectedIds) == 0:
                return []
            else:
                return [selectedIds[0]]
    
    # ----------------------------------------------------------------------
    # Canvas release button1. Select area
    # ----------------------------------------------------------------------
    def release(self, event):
        if self._mouseAction in (
            ACTION_SELECT_SINGLE,
            ACTION_SELECT_DOUBLE,
            ACTION_SELECT_AREA,
        ):
            closest = numpy.array([])
            
            if self._mouseAction == ACTION_SELECT_AREA:
                if self._x < event.x:  # From left->right enclosed
                    try:
                        closest = self.find_enclosed(
                            self._x,
                            self._y,
                            event.x,
                            event.y,
                            self.pathVertices
                        )
                    except Exception:
                        pass

                else:  # From right->left overlapping
                    try:
                        closest = self.find_overlapping(
                            self._x,
                            self._y,
                            event.x,
                            event.y,
                            self.pathVertices
                        )
                    except Exception:
                        pass

                items = []
                for i in closest:
                    try:
                        items.append(self._items[i])
                    except Exception:
                        pass

            elif self._mouseAction in (ACTION_SELECT_SINGLE,
                                       ACTION_SELECT_DOUBLE):
                try:
                    closest = self.find_closest(
                        event.x,
                        event.y,
                        self.pathVertices,
                        CLOSE_DISTANCE
                    )
                except Exception:
                    pass

                items = []
                for i in closest:
                    try:
                        items.append(self._items[i])
                    except KeyError:
                        pass
            if items:
                self.app.select(
                    items,
                    self._mouseAction == ACTION_SELECT_DOUBLE,
                    event.state & CONTROL_MASK == 0,
                )

            self._mouseAction = None
            self.queueDraw()

        elif self._mouseAction == ACTION_MOVE:
            moveFrom = self._moveFrom #vec3(self.vectorDict[self._vector][0][0])
            moveTo = self._lastEnd
            translation = moveTo - moveFrom

            self.status(_("Move by {:g}, {:g}, {:g}").format(translation.x, translation.y, translation.z))
            self.app.insertCommand(("move %g %g %g") % (translation.x, translation.y, translation.z), True)
        
        elif self._mouseAction == ACTION_RULER:
            if self._snapPoint is None:
                self._vector = None
                self.queueDraw()
            else:
                self._snapPoint = None

        elif self._mouseAction == ACTION_PAN:
            self.midRelease(event)

    # ----------------------------------------------------------------------
    def double(self, event):
        self._mouseAction = ACTION_SELECT_DOUBLE

    # ----------------------------------------------------------------------
    def motion(self, event):
        if self.action == ACTION_ADDORIENT:
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))
            # Project to the XY plane
            if self._snapPoint is not None:
                self._snapPoint.z = 0

            self.queueDraw()

        elif self.action == ACTION_MOVE or self.action == ACTION_RULER:
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))

            if self.action == ACTION_RULER:
                self.highlightRuler = False

                # Is the pointer close to a dimension end?
                if self._vector is not None and self._snapPoint is not None:
                    currentStart = self.vectorDict[self._vector][0][0]
                    currentEnd = self.vectorDict[self._vector][0][1]

                    if (distance(self._snapPoint, currentEnd) * self.zoom <= CLOSE_DISTANCE) or (distance(self._snapPoint, currentStart) * self.zoom <= CLOSE_DISTANCE):
                        self.highlightRuler = True

            self.queueDraw()
        
        elif self.action == ACTION_ORIGIN:
            self._snapPoint, self._snapPointType = self.snapPoint(vec2(event.x, event.y))

            self.queueDraw()


        self.setMouseStatus(event)

    def get_ends_and_center(self, lines, id):
        # lines is an array with lines vertex data as self.pathLines
        
        # Reshape to have one line per row. Each row has the info of the 2 vertices (location, ...)
        lines16 = numpy.reshape(lines, (-1, 16))

        # Filter the lines with id. If there is more than one, it is an arc composed by multiple lines
        line16 = lines16[lines16[:, 0] == id]

        if len(line16) == 0:
            return None, None, None
        
        elif len(line16) == 1: # Just one row. We picked on a line
            return vec3(line16[0, 1:4]), vec3(line16[0, 9:12]), None
        
        else: # Multiple rows. We picked on an arc. We return the first point of the first line and the last point of the last line
            p_start = vec3(line16[0, 1:4])
            p_end = vec3(line16[-1, 9:12])
            
            # If it's a closed arc (a circle), pick the starting point of the last line, instead of the end point
            if distance(p_start, p_end) == 0.:
                p_end = vec3(line16[-1, 1:4])
            
            numlines = len(line16)
            p_mid = vec3(line16[int(numpy.ceil(numlines / 2.)), 1:4])
            
            # Compute the arc center
            SM = p_mid - p_start
            SE = p_end - p_start

            cross_prod = cross(SM, SE)
            denom = 2.0 * length2(cross_prod)

            if denom == 0:
                p_center = None # Points are collinear
            else:
                term1 = cross(cross_prod, SM) * length2(SE)
                term2 = cross(SE, cross_prod) * length2(SM)

                p_center = p_start + (term1 + term2) / denom
                
            return p_start, p_end, p_center

    # ----------------------------------------------------------------------
    # Snap to the closest point if any
    # ----------------------------------------------------------------------
    def snapPoint(self, clickPoint: vec2, excludeSelected = False): # -> tuple[vec3 | None, int | None]
        """
        When clicking on the canvas at point clickPoint, return the world coordinates of a close path point, or none
        And the snap point type: 0: Point on Line ; 1: Line End ; 2: Arc Center
        """
        snapPoint = None

        item = self.find_closest(clickPoint.x, clickPoint.y, self.pathVertices, CLOSE_DISTANCE, excludeSelected=excludeSelected)

        if len(item) == 0:
            return None, None
        
        # Get the ends of the closest line, in canvas coordinates
        start, end, center = self.get_ends_and_center(self.pathVertices, item)

        if start is None or end is None:
            return None, None

        start_c = self.world2Canvas(start)
        end_c = self.world2Canvas(end)

        dist_start = distance(clickPoint, start_c)
        dist_end = distance(clickPoint, end_c)

        if dist_start <= dist_end and dist_start < CLOSE_DISTANCE_TO_ENDS:
            return start, 1
        elif dist_end < dist_start and dist_end < CLOSE_DISTANCE_TO_ENDS:
            return end, 1
        else: # We are on the line/arc, far from the ends
            if center is not None: # We clicked on an arc, far from the ends. Return the center point
                return center, 2
            else: # We are on a line, far from the ends
                # If pickLine does not exactly intersect line, we get 2 points:
                # C1: closest point at pickLine
                # C2: closest point at line
                MVPinv = inverse(self.PMatrix * self.MVMatrix)

                # We define a line perpendicular to the canvas
                clickPoint_u = self.canvas2Unit(clickPoint)
                p1 = (MVPinv * vec4(clickPoint_u.x, clickPoint_u.y, 1, 1)).xyz
                p2 = (MVPinv * vec4(clickPoint_u.x, clickPoint_u.y, 0, 1)).xyz
                C1, C2, dist, intersect = self.closest_points_between_lines(p1, p2, start, end)
                return C2, 0

    def setCustomColors(self):
        dialog = CustomColorsDialog(self.parentFrame, self)
        dialog.transient(self.parentFrame)
        self.wait_window(dialog)  # makes it modal-like
        self.queueDraw()
    # ----------------------------------------------------------------------
    def configureEvent(self, event):
        width = self.winfo_width()
        height = self.winfo_height()
        
        self.PMatrix = ortho(-width / 2.0 / self.zoom, 
                             width / 2.0 / self.zoom, 
                             -height / 2.0 / self.zoom,
                             height / 2.0 / self.zoom, 
                             -10000,
                             10000)
        self.cameraPosition()
        self.queueDraw()

    def closest_points_between_lines(self, P1, P2, Q1, Q2, eps=1e-9):
        """
        Compute closest points between two infinite 3D lines.

        Line 1: P1 + t*(P2-P1)
        Line 2: Q1 + u*(Q2-Q1)

        Returns:
            C1 : closest point on line 1
            C2 : closest point on line 2
            distance : minimum distance between lines
            intersect : True if lines intersect (within tolerance)
        """

        r = P2 - P1
        s = Q2 - Q1
        w0 = P1 - Q1

        a = dot(r, r)
        b = dot(r, s)
        c = dot(s, s)
        d = dot(r, w0)
        e = dot(s, w0)

        denom = a * c - b * b

        # If denom is zero, lines are parallel
        if abs(denom) < eps:
            # choose arbitrary t = 0
            t = 0.0
            u = e / c if c > eps else 0.0
        else:
            t = (b * e - c * d) / denom
            u = (a * e - b * d) / denom

        C1 = P1 + t * r
        C2 = Q1 + u * s

        dist = distance(C1, C2)
        intersect = dist < eps

        return C1, C2, dist, intersect

    def blue2red(self, v: float, vmin: float, vmax: float) -> vec3:
        """
        Return an interpolated RGB tuple, based on the value v between vmin and vmax
        v==vmin -> blue
        v==vmax -> red
        """
        if vmax <= vmin or v < vmin or v > vmax:
            return vec3(0, 0, 0)  # fallback
    
        t = (v - vmin) / (vmax - vmin)
        t = max(0, min(1, t))

        R = int(255 * t)
        G = 0
        B = int(255 * (1 - t))

        return vec3(R, G, B)

    # ----------------------------------------------------------------------
    def pan(self, event):
        if self._mouseAction != ACTION_PAN:
            self.configure(cursor=mouseCursor(ACTION_PAN))
            self._mouseAction = ACTION_PAN
            
        self.pan_delta(event.x - self._x, event.y - self._y)
        
        self._x = event.x
        self._y = event.y

    def pan_delta(self, deltaX, deltaY):
        """
        Pan a number of pixels in X and/or Y
        """
        width = self.winfo_width()
        height = self.winfo_height()
        
        MVPinv = inverse(self.PMatrix * self.MVMatrix)
        
        pointFrom = MVPinv * vec4(-1, 1, 0, 1) # Screen (0, 0)
        pointTo = MVPinv * vec4(2 * (deltaX - width / 2.0) / width, 2 * (height / 2.0 - deltaY) / height, 0, 1) # Screen (deltaX, deltaY)

        self.MVMatrix = translate(self.MVMatrix, vec3((pointTo - pointFrom).x, (pointTo - pointFrom).y, (pointTo - pointFrom).z)) # type: ignore
        
        self.cameraPosition()
        
        self.queueDraw()
    # ----------------------------------------------------------------------
    def midRelease(self, event):
        # If there was no pan (just mid-click), and the user clicked on a path, 
        # change the rotation center to the closest point of that line to the point where the user clicked
        if self._mouseAction != ACTION_PAN and self._mouseAction != ACTION_ZOOM:
            newRotationCenter, pointType = self.snapPoint(vec2(event.x, event.y))

            if newRotationCenter is not None:
                RS = mat3x3(self.MVMatrix)
                new_translation = -RS * newRotationCenter
                self.MVMatrix[3] = vec4(new_translation, 1)

                self.queueDraw()

        self._mouseAction = None
        self.configure(cursor=mouseCursor(self.action))

    def rightRelease(self, event):
        if self._mouseAction != ACTION_PAN and self._mouseAction != ACTION_ROTATE and self._mouseAction != ACTION_ZOOM:
            newRotationCenter, pointType = self.snapPoint(vec2(event.x, event.y))

            if newRotationCenter is not None:
                RS = mat3x3(self.MVMatrix)
                new_translation = -RS * newRotationCenter
                self.MVMatrix[3] = vec4(new_translation, 1)

                self.queueDraw()

        self._mouseAction = None
        self.configure(cursor=mouseCursor(self.action))

    # ----------------------------------------------------------------------
    def panLeft(self, event=None):
        self.pan_delta(15, 0) # 15 pixels, as in the original canvas

    def panRight(self, event=None):
        self.pan_delta(-15, 0)

    def panUp(self, event=None):
        self.pan_delta(0, 15)

    def panDown(self, event=None):
        self.pan_delta(0, -15)

    def canvas2Unit(self, coords : vec2) -> vec2:
        """
        Map screen pixel coordinates to opengl screen coords [-1.0 -> 1.0]
        In OpenGL, y goes positive upwards
        """
        width = self.winfo_width()
        height = self.winfo_height()
        
        return vec2(
            coords.x / (width / 2.0) - 1,
            1 - coords.y / (height / 2.0)
        )
    
    def unit2Canvas(self, coords : vec2) -> vec2:
        """
        Map opengl screen coords [-1.0 -> 1.0] to screen pixel coordinates
        In OpenGL, y goes positive upwards
        """
        width = self.winfo_width()
        height = self.winfo_height()
        
        return vec2(
            (coords.x + 1.) * (width / 2.),
            (1 - coords.y) * (height / 2.)
        )
    
    def world2Canvas(self, coords : vec3) -> vec2:
        MVP = self.PMatrix * self.MVMatrix
        unitCoords = (MVP * vec4(coords, 1)).xy

        return self.unit2Canvas(unitCoords)

    def canvas2World(self, coords : vec2) -> vec3:
        coordsUnit = self.canvas2Unit(coords)
        
        MVPinv = inverse(self.PMatrix * self.MVMatrix)
        
        return (MVPinv * vec4(coordsUnit, 0, 1)).xyz
    
    def canvas2WorldXY(self, coords : vec2, thresholdAngle = 20): # -> vec3 | None:
        intersection = self.canvas2WorldPlane(coords, vec3(0, 0, 1), vec3(0, 0, 0), thresholdAngle)
        if intersection == None:
            return None
        else:
            return intersection
    
    def canvas2WorldYZ(self, coords : vec2, thresholdAngle = 20): # -> vec3 | None:
        intersection = self.canvas2WorldPlane(coords, vec3(1, 0, 0), vec3(0, 0, 0), thresholdAngle)
        if intersection == None:
            return None
        else:
            return intersection
    
    def canvas2WorldXZ(self, coords : vec2, thresholdAngle = 20): # -> vec3 | None:
        intersection = self.canvas2WorldPlane(coords, vec3(0, 1, 0), vec3(0, 0, 0), thresholdAngle)
        if intersection == None:
            return None
        else:
            return intersection
    
    def viewAngle(self, planeNormal : vec3) -> float:
        """
        Return the angle between the current view and a specific plane normal in 3D
        """

        MVPinv = inverse(self.PMatrix * self.MVMatrix)

        # We define a line perpendicular to the canvas
        p1 = (MVPinv * vec4(0, 0, 0, 1)).xyz
        p2 = (MVPinv * vec4(0, 0, 1, 1)).xyz

        v12 = p2 - p1

        return numpy.rad2deg(numpy.arccos(abs(dot(normalize(v12), planeNormal))))

    def canvas2WorldPlane(self, coords: vec2, planeNormal : vec3, planePoint : vec3, thresholdAngle = 20): # -> vec3 | None:
        # return the point of the plane where we picked on the canvas, in world coordinates
        # If the plane is too parallel to the screen (less than thresholdAngle), return None
        coords_u = self.canvas2Unit(coords)

        MVPinv = inverse(self.PMatrix * self.MVMatrix)

        # We define a line perpendicular to the canvas
        p1 = (MVPinv * vec4(coords_u, 0, 1)).xyz
        p2 = (MVPinv * vec4(coords_u, 1, 1)).xyz
        
        v12 = p2 - p1

        # If we are too parallel to the plane, return None
        angle = 90 - numpy.rad2deg(numpy.arccos(abs(dot(normalize(v12), planeNormal))))
        if angle == 0 or angle < abs(thresholdAngle):
            return None

        n = normalize(planeNormal)
        denom = dot(n, v12)
        t = dot(n, planePoint - p1) / denom

        intersection = p1 + v12 * t

        return intersection
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
        x = self._tx
        y = self._ty
        zoom = self.__tzoom

        self.__tzoom = 1.0

        width = self.winfo_width()
        height = self.winfo_height()     
        
        MVP = self.PMatrix * self.MVMatrix          
        
        # We zoom around the (x, y) screen location 
        zoomOrigin3d = self.canvas2World(vec2(x, y))
        
        screenCenter3d = (inverse(MVP) * vec4(0, 0, 0, 1)).xyz
        
        # Vector from zoom origin to projected center
        vZoomOriginToCenter = screenCenter3d - zoomOrigin3d
        
        # Translate the model, so that the origin keeps fixed when zooming
        self.MVMatrix = translate(self.MVMatrix, vZoomOriginToCenter * (1- 1/zoom))
        

        # Zoom around the mouse location
        
        self.zoom *= zoom
        
        self.PMatrix = ortho(-width / 2.0 / self.zoom, 
                             width / 2.0 / self.zoom, 
                             -height / 2.0 / self.zoom,
                             height / 2.0 / self.zoom, 
                             -10000,
                             10000)
        
        self.cameraPosition()

        self.queueDraw()


    # ----------------------------------------------------------------------
    # Zoom to Fit to Screen
    # ----------------------------------------------------------------------

    def fit2Screen(self, event=None):
        """
        Zoom to Fit to Screen
        """
        
        upVector = inverse(self.MVMatrix) * vec4(0, 1, 0, 0)
        depthVector = inverse(self.MVMatrix) * vec4(0, 0, 1, 0)

        # If we are in SIM mode, include the stock cube in the model dimensions
        if self.mode == CNCCanvas.MODE_SIM:
            minx = min(self._modelCenter.x - self._modelSize / 2., STOCK_MIN_X)
            maxx = max(self._modelCenter.x + self._modelSize / 2., STOCK_MAX_X)
            miny = min(self._modelCenter.y - self._modelSize / 2., STOCK_MIN_Y)
            maxy = max(self._modelCenter.y + self._modelSize / 2., STOCK_MAX_Y)
            minz = min(self._modelCenter.z - self._modelSize / 2., STOCK_MIN_Z)
            maxz = max(self._modelCenter.z + self._modelSize / 2., STOCK_MAX_Z)

            modelSize = math.sqrt(pow(maxx - minx, 2.) + pow(maxy - miny, 2.) + pow(maxz - minz, 2.))
            modelCenter = vec3((maxx + minx) / 2., (maxy + miny) / 2., (maxz + minz) / 2.)
        
        else:
            modelSize = self._modelSize
            modelCenter = self._modelCenter

        
        self.MVMatrix = lookAt(
            modelCenter + depthVector.xyz, # eye
            modelCenter, # target
            upVector.xyz # up
            )
        # Adjust the Projection Matrix
        width = self.winfo_width()
        height = self.winfo_height()
        
        self.zoom = min(width, height) / modelSize
        
        self.PMatrix = ortho(-width / 2.0 / self.zoom, 
                             width / 2.0 / self.zoom, 
                             -height / 2.0 / self.zoom,
                             height / 2.0 / self.zoom, 
                             -10000,
                             10000)

        self.cameraPosition()
        self.queueDraw()

    # ----------------------------------------------------------------------
    def menuZoomIn(self, event=None):
        x = self.winfo_width() // 2
        y = self.winfo_height() // 2
        self.zoomCanvas(x, y, 2.0)

    # ----------------------------------------------------------------------
    def menuZoomOut(self, event=None):
        x = self.winfo_width() // 2
        y = self.winfo_height() // 2
        self.zoomCanvas(x, y, 0.5)

    # ----------------------------------------------------------------------
    def mouseZoomIn(self, event):
        self.zoomCanvas(event.x, event.y, ZOOM)

    # ----------------------------------------------------------------------
    def mouseZoomOut(self, event):
        self.zoomCanvas(event.x, event.y, 1.0 / ZOOM)

    # ----------------------------------------------------------------------
    def wheel(self, event):
        # In windows, each wheel step counts 120
        if self.windowing_system == "win32":
            wheel_step = 120
        else:
            wheel_step = 1

        self.zoomCanvas(event.x, event.y, pow(ZOOM, (event.delta // wheel_step)))
    
    # ----------------------------------------------------------------------
    # Zoom in/out with shift+midbutton
    # ----------------------------------------------------------------------
    def midRightZoom(self, event):
        if self._mouseAction != ACTION_ZOOM:
            self.configure(cursor=mouseCursor(ACTION_ZOOM))
            self._mouseAction = ACTION_ZOOM

        self.zoomCanvas(self._xp, self._yp, pow(1.01, self._y - event.y))
        
        self._x = event.x
        self._y = event.y

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
                self.set_arrow(self.pathArrows, self.pathArrowsVBO, self.pathVertices, self._lastActive, 'none')
            self._lastActive = item
            self.set_arrow(self.pathArrows, self.pathArrowsVBO, self.pathVertices, self._lastActive, 'last', 10, 10)

    # ----------------------------------------------------------------------
    # Display gantry
    # ----------------------------------------------------------------------
    def gantry(self, wx, wy, wz, mx, my, mz):
        self._lastGantry = (wx, wy, wz)
        self.updateGantry(wx, wy, wz)
        if self._showCamera and self.cameraAnchor == NONE:
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
            
            self.updateWorkArea()

    # ----------------------------------------------------------------------
    # Clear highlight of selection
    # ----------------------------------------------------------------------
    def clearSelection(self):
        if self._lastActive is not None:
            self.set_arrow(self.pathArrows, self.pathArrowsVBO, self.pathVertices, self._lastActive, 'none')
            self._lastActive = None
        
        self.deselectAll(self.pathVertices, self.pathVBO)
         
        self.deleteInfo()
        

    # ----------------------------------------------------------------------
    # Highlight selected items
    # ----------------------------------------------------------------------
    def select(self, items):
        linesAndFlags = []
        
        for b, i in items:
            block = self.gcode[b]
            flags = FLAG_SELECTED | (FLAG_ENABLED if block.enable else 0)
            
            if i is None:
                for path in block._path:
                    if path is not None:
                        linesAndFlags.append([path, flags])

            elif isinstance(i, int):
                path = block.path(i)
                if path:
                    linesAndFlags.append([path, flags])
        
        self.setFlags(self.pathVertices, FLAG_SELECTED | FLAG_ENABLED, linesAndFlags, self.pathVBO)

        # Update arrows, if any
        self.update_arrows_from_lines(self.pathArrows, self.pathArrowsVBO, self.pathVertices)
                
        self.updateMargin()
    
    def getSelection(self, linesVertices):
        lines16 = numpy.reshape(linesVertices, (-1, 16))
        selection = lines16[(lines16[:, 7].astype(int) & FLAG_SELECTED) == FLAG_SELECTED]
        return numpy.unique(selection[:, 0]).tolist()


    def setFlags(self, linesVertices, flagsToModify, linesAndFlags, bufferToUpdate = None):
        # linesAndTags must be an array of arrays (nx2)
        # The first item of each array is the line number, and the second item the value with the Tags to be activated
        selections = numpy.array(linesAndFlags, dtype=numpy.float32).reshape((-1, 2))
        lookup = dict(selections)
        
        linesArray16 = linesVertices.reshape((-1, 16))
        mask = numpy.isin(linesArray16[:, 0], selections[:, 0])
        
        matched_keys = linesArray16[mask, 0]
        
        # Since linesArray16 is a reshaped view of linesArray, changes are reflected in the original array
        # First, clear the bits
        linesArray16[mask, 7] = linesArray16[mask, 7].astype(int) & ~flagsToModify
        linesArray16[mask, 15] = linesArray16[mask, 15].astype(int) & ~flagsToModify
        # Then, set the ones to modify
        if matched_keys.size > 0:
            linesArray16[mask, 7] = linesArray16[mask, 7].astype(int) | ((numpy.vectorize(lookup.get)(matched_keys)).astype(int) & flagsToModify)
            linesArray16[mask, 15] = linesArray16[mask, 15].astype(int) | ((numpy.vectorize(lookup.get)(matched_keys)).astype(int) & flagsToModify)
        
            if bufferToUpdate:
                glBindBuffer(GL_ARRAY_BUFFER, bufferToUpdate)
                glBufferSubData(GL_ARRAY_BUFFER, 0, linesVertices.nbytes, linesVertices)
                glBindBuffer(GL_ARRAY_BUFFER, 0)
                self.queueDraw()

    def deleteLines(self, lines, linesVertices, linesBuffer, updateModelDimensions = False):
        lines.clear()
        linesVertices = self.update_lines_buffer(linesBuffer, lines, updateModelDimensions)

        return linesVertices
    
    def deleteArrows(self, arrows, arrowsBuffer):
        arrows.clear()
        self.update_arrows_buffer(arrowsBuffer, arrows)

    def deselectAll(self, linesArray, bufferToUpdate = None):
        linesArray16 = linesArray.reshape((-1, 16))
        
        linesArray16[:, 7] = linesArray16[:, 7].astype(int) & ~FLAG_SELECTED
        linesArray16[:, 15] = linesArray16[:, 15].astype(int) & ~FLAG_SELECTED
        
        if bufferToUpdate:
            glBindBuffer(GL_ARRAY_BUFFER, bufferToUpdate)
            glBufferSubData(GL_ARRAY_BUFFER, 0, linesArray.nbytes, linesArray)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            self.queueDraw()
    
    # ----------------------------------------------------------------------
    # Select orientation marker
    # ----------------------------------------------------------------------
    def selectMarker(self, item):
        # find marker
        for i, paths in enumerate(self.gcode.orient.paths):
            if item in paths:
                self._orientSelected = i
                for j in paths:
                    self.orientDict[j][3] = FLAG_ENABLED | FLAG_SELECTED
                
                self.update_lines_buffer(self.orientVBO, self.orientDict)

                self.event_generate("<<OrientSelect>>", data=i)
                return
            
        self._orientSelected = None

    # ----------------------------------------------------------------------
    # Highlight marker that was selected
    # ----------------------------------------------------------------------
    def orientChange(self, marker):
        for id in self.orientDict:
            self.orientDict[id][3] = FLAG_ENABLED

        if marker >= 0:
            self._orientSelected = marker
            try:
                for i in self.gcode.orient.paths[self._orientSelected]:
                    self.orientDict[i][3] = FLAG_ENABLED | FLAG_SELECTED

            except IndexError:
                self.drawOrient()
        else:
            self._orientSelected = None
        
        self.update_lines_buffer(self.orientVBO, self.orientDict)

        self.queueDraw()

    # ----------------------------------------------------------------------
    # Display graphical information on selected blocks
    # ----------------------------------------------------------------------
    def showInfo(self, blocks):
        # Clear any previous information
        self.infoLines = {}

        self.deleteArrows(self.infoArrows, self.infoArrowsVBO)


        infoArcs = []

        for bid in blocks:
            block = self.gcode.blocks[bid]
            xyz = [
                (block.xmin, block.ymin, 0.0),
                (block.xmax, block.ymin, 0.0),
                (block.xmax, block.ymax, 0.0),
                (block.xmin, block.ymax, 0.0),
                (block.xmin, block.ymin, 0.0),
            ]

            self.create_line(self.infoLines,
                             xyz,
                             self.rgb8(INFO_COLOR),
                             1)
            
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

            infoArcs.append(self.create_line(
                self.infoLines,
                xyz,
                self.rgb8(INFO_COLOR),
                1
            ))
        
        self.infoVertices = self.update_lines_buffer(self.infoVBO, self.infoLines)

        for arc in infoArcs:
            self.set_arrow(self.infoArrows, self.infoArrowsVBO, self.infoVertices, arc, 'last', 20, 20)

        self.queueDraw()
    
    def deleteInfo(self):
        self.showInfo([])

    # -----------------------------------------------------------------------
    def cameraOn(self, event=None):
        if not self.camera.start():
            return
        self.cameraRefresh()

    # -----------------------------------------------------------------------
    def cameraOff(self, event=None):
        self._showCamera = False

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

        if not self._showCamera:
            self._showCamera = True
        
        self.cameraPosition()

        try:
            self.cameraImage = self.get_camera_image()
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.cameraTexture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                         len(self.cameraImage[0]),
                         len(self.cameraImage),
                         0, GL_RGBA, GL_UNSIGNED_BYTE, self.cameraImage)
            
            self.queueDraw()

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
        if not self._showCamera:
            return
        
        w = self.winfo_width()
        h = self.winfo_height()
        hc, wc = self.camera.image.shape[:2]
        zoomx = self.PMatrix[0][0]
        zoomy = self.PMatrix[1][1]
        wc *= 0.5 / self.cameraScale * zoomx * w / 2.
        hc *= 0.5 / self.cameraScale * zoomy * h / 2.
        x = w / 2  # everything on center
        y = h / 2

        if self.cameraAnchor == NONE: # Center on Gantry
            dx = dy = 0
            if not self.cameraSwitch:
                dx = self.cameraDx
                dy = self.cameraDy

            x, y = self.world2Canvas(vec3(self._gantryLocation) + vec3(dx, dy, 0))
            
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
        
        self.cameraLocation = vec2(x, y)


    # ----------------------------------------------------------------------
    # Parse and draw the file from the editor to g-code commands
    # ----------------------------------------------------------------------
    def draw(self):
        width, height = self.winfo_width(), self.winfo_height()
        
        # Check readiness of the buffer
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            self._drawRequested = False
            self.queueDraw()
            return

        glViewport(0, 0, width, height)
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # type: ignore
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_BLEND)
        glDisable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        # Draw background
        self.drawBackground()
        # Ensure that the next items are drawn on top of this
        glClear(GL_DEPTH_BUFFER_BIT)

        # Draw Camera
        if self._showCamera:
            self.drawCamera()
            # Ensure that the next items are drawn on top of this
            glClear(GL_DEPTH_BUFFER_BIT)
            # Draw Crosshair
            self.drawCrossHair()
            # Ensure that the next items are drawn on top of this
            glClear(GL_DEPTH_BUFFER_BIT)

        # Draw grid
        if self.draw_grid:
            self.drawLines(self.gridVBO, 1)
        
        # Draw margins
        if self.draw_margin:
            self.drawLines(self.marginsVBO, 1)
        
        # Draw work area
        if self.draw_workarea:
            self.drawLines(self.workAreaVBO, 1)
        
        # Draw orient markers
        glClear(GL_DEPTH_BUFFER_BIT)
        self.drawLines(self.orientVBO, 3)
        
        # Draw paths
        glClear(GL_DEPTH_BUFFER_BIT)
        if self.pathVertices.size > 0:
            self.drawPaths(self.pathVBO, 2)
        
        # Draw arrows
        if len(self.pathArrows) > 0:
            self.drawArrows(self.pathArrowsVBO)
        
        # Draw Snap Point
        if self._snapPoint:
            self.drawSnapPoint()
        
        # Draw probe grid, map and text
        if self.draw_probe:
            self.drawLines(self.probeVBO, 1)
            self.drawProbeMap()
            self.drawText(self.ProbeTextVBO)

        # Draw info lines
        if self.infoVertices.size > 0:
            self.drawLines(self.infoVBO, 2)
        
        # Draw info arrows
        if len(self.infoArrows) > 0:
            self.drawArrows(self.infoArrowsVBO)
        
        if self.mode == CNCCanvas.MODE_SIM:
            # Draw stock material
            glDisable(GL_CULL_FACE)
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            self.drawStockTop()
            self.drawStockBottom()
            self.drawStockSide(1)
            self.drawStockSide(2)
            self.drawStockSide(3)
            self.drawStockSide(4)
        
        # Draw Text
        if len(self.text) > 0:
            self.drawText(self.TextVBO)

        # Draw axes
        if self.draw_axes:
            self.drawAxes()
        
        # Draw gantry
        self.drawGantry()
        
        # Draw selection rectangle
        if self._mouseAction == ACTION_SELECT_AREA:
            self.drawSelectionRectangle()
        
        # Draw ruler
        if self._vector:
            self.drawLines(self.vectorVBO, 3 if self.highlightRuler else 2)
            self.drawArrows(self.vectorArrowsVBO)

        glUseProgram(0)
        
        self.swap_buffers()
        
        self._drawRequested = False

    def drawBackground(self):
        glUseProgram(self.backgroundProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.backgroundVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(glGetAttribLocation(self.backgroundProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(0*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.backgroundProgram, "index"))

        canvas_color_rgb_up = vec3(self.rgb8(CANVAS_COLOR_UP))
        canvas_color_rgb_up_loc = glGetUniformLocation(program=self.backgroundProgram, name="canvas_color_rgb_up")
        glUniform3fv(canvas_color_rgb_up_loc, 1, value_ptr(canvas_color_rgb_up))

        canvas_color_rgb_down = vec3(self.rgb8(CANVAS_COLOR_DOWN))
        canvas_color_rgb_down_loc = glGetUniformLocation(program=self.backgroundProgram, name="canvas_color_rgb_down")
        glUniform3fv(canvas_color_rgb_down_loc, 1, value_ptr(canvas_color_rgb_down))

        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def drawCamera(self):
        glDisable(GL_CULL_FACE)
        glUseProgram(self.ImageProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.CameraVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(glGetAttribLocation(self.ImageProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glEnableVertexAttribArray(glGetAttribLocation(self.ImageProgram, "index"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.ImageProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        location_loc = glGetUniformLocation(program=self.ImageProgram, name="location")
        glUniform2fv(location_loc, 1, value_ptr(self.cameraLocation))

        # Set the uniform variable 'ourTexture' to texture unit 0
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.cameraTexture)
        glUniform1i(glGetUniformLocation(self.ImageProgram, "ourTexture"), 0)

        width_loc = glGetUniformLocation(program=self.ImageProgram, name="width")
        glUniform1f(width_loc, len(self.cameraImage[0]))

        height_loc = glGetUniformLocation(program=self.ImageProgram, name="height")
        glUniform1f(height_loc, len(self.cameraImage))

        canvasWidth_loc = glGetUniformLocation(program=self.ImageProgram, name="canvasWidth")
        glUniform1f(canvasWidth_loc, self.winfo_width())

        canvasHeight_loc = glGetUniformLocation(program=self.ImageProgram, name="canvasHeight")
        glUniform1f(canvasHeight_loc, self.winfo_height())

        # We get the zoom from the projection matrix
        zoomx = self.PMatrix[0][0]
        zoomy = self.PMatrix[1][1]
        zoom_loc = glGetUniformLocation(program=self.ImageProgram, name="zoom")
        glUniform2f(zoom_loc, zoomx, zoomy)
        
        cameraScale_loc = glGetUniformLocation(program=self.ImageProgram, name="cameraScale")
        glUniform1f(cameraScale_loc, self.cameraScale)

        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def drawCrossHair(self):
        glUseProgram(self.CrossHairProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.CrossHairVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(glGetAttribLocation(self.CrossHairProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glEnableVertexAttribArray(glGetAttribLocation(self.CrossHairProgram, "index"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.CrossHairProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        location_loc = glGetUniformLocation(program=self.CrossHairProgram, name="location")
        glUniform2fv(location_loc, 1, value_ptr(self.cameraLocation))

        width_loc = glGetUniformLocation(program=self.CrossHairProgram, name="width")
        glUniform1f(width_loc, len(self.cameraImage[0]))

        height_loc = glGetUniformLocation(program=self.CrossHairProgram, name="height")
        glUniform1f(height_loc, len(self.cameraImage))

        canvasWidth_loc = glGetUniformLocation(program=self.CrossHairProgram, name="canvasWidth")
        glUniform1f(canvasWidth_loc, self.winfo_width())

        canvasHeight_loc = glGetUniformLocation(program=self.CrossHairProgram, name="canvasHeight")
        glUniform1f(canvasHeight_loc, self.winfo_height())

        R_loc = glGetUniformLocation(program=self.CrossHairProgram, name="R")
        glUniform1f(R_loc, self.cameraR)

        # We get the zoom from the projection matrix
        zoomx = self.PMatrix[0][0]
        zoomy = self.PMatrix[1][1]
        zoom_loc = glGetUniformLocation(program=self.CrossHairProgram, name="zoom")
        glUniform2f(zoom_loc, zoomx, zoomy)

        cameraScale_loc = glGetUniformLocation(program=self.CrossHairProgram, name="cameraScale")
        glUniform1f(cameraScale_loc, self.cameraScale)

        glLineWidth(1.5)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_LINES, 0, size // PARAMETERS_PER_VERTEX)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawSnapPoint(self):
        if self._snapPoint is None:
            return
        
        glUseProgram(self.SnapPointProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.SnapPointVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(glGetAttribLocation(self.SnapPointProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glEnableVertexAttribArray(glGetAttribLocation(self.SnapPointProgram, "index"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.SnapPointProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))
 
        location_loc = glGetUniformLocation(program=self.SnapPointProgram, name="location")
        glUniform3fv(location_loc, 1, value_ptr(self._snapPoint))

        canvasWidth_loc = glGetUniformLocation(program=self.SnapPointProgram, name="canvasWidth")
        glUniform1f(canvasWidth_loc, self.winfo_width())

        canvasHeight_loc = glGetUniformLocation(program=self.SnapPointProgram, name="canvasHeight")
        glUniform1f(canvasHeight_loc, self.winfo_height())

        pointType_loc = glGetUniformLocation(program=self.SnapPointProgram, name="pointType")
        glUniform1f(pointType_loc, self._snapPointType)

        glLineWidth(2)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_LINE_LOOP, 0, size // PARAMETERS_PER_VERTEX)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def drawSelectionRectangle(self):

        glDisable(GL_CULL_FACE)
        glUseProgram(self.SelectionRectProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.SelectionRectVBO)
        PARAMETERS_PER_VERTEX = 2
        glVertexAttribPointer(glGetAttribLocation(self.SelectionRectProgram, "uv"), 2, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glEnableVertexAttribArray(glGetAttribLocation(self.SelectionRectProgram, "uv"))
        
        # Selection to the right -> Blue. To the left -> Green
        if self.SelectionRectVertices[2] > self.SelectionRectVertices[0]:
            rect_color = vec3(0, 0, 1)
        else:
            rect_color = vec3(0, 1, 0)
        color_loc = glGetUniformLocation(program=self.SelectionRectProgram, name="color")
        glUniform3fv(color_loc, 1, value_ptr(rect_color))
        
        glLineWidth(2)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        glDrawArrays(GL_TRIANGLES, 0, len(self.SelectionRectVertices) // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def drawLines(self, vbo, lineWidth):

        glEnable(GL_DEPTH_TEST)
        glUseProgram(self.linesProgram)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        PARAMETERS_PER_VERTEX = 8
        glVertexAttribPointer(self.linesProgram_id, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(self.linesProgram_xyz, 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(1*4))
        glVertexAttribPointer(self.linesProgram_pos, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(4*4))
        glVertexAttribPointer(self.linesProgram_colorValue, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(5*4))
        glVertexAttribPointer(self.linesProgram_dashRatio, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(6*4))
        glVertexAttribPointer(self.linesProgram_flags, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(7*4))
        glEnableVertexAttribArray(self.linesProgram_id)  
        glEnableVertexAttribArray(self.linesProgram_xyz)  
        glEnableVertexAttribArray(self.linesProgram_pos)  
        glEnableVertexAttribArray(self.linesProgram_colorValue)  
        glEnableVertexAttribArray(self.linesProgram_dashRatio)  
        glEnableVertexAttribArray(self.linesProgram_flags)


        MVP = self.PMatrix * self.MVMatrix
        glUniformMatrix4fv(self.linesProgram_mvp, 1, False, value_ptr(MVP))

        glUniform1f(self.linesProgram_zoom, self.zoom)

        select_color = vec3(self.rgb8(SELECT_COLOR))
        glUniform3fv(self.linesProgram_select_color, 1, value_ptr(select_color))

        select2_color = vec3(self.rgb8(SELECT2_COLOR))
        glUniform3fv(self.linesProgram_select2_color, 1, value_ptr(select2_color))

        disable_color = vec3(self.rgb8(DISABLE_COLOR))
        glUniform3fv(self.linesProgram_disable_color, 1, value_ptr(disable_color))



        glLineWidth(lineWidth)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_LINES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawPaths(self, vbo, lineWidth):

        glEnable(GL_DEPTH_TEST)
        glUseProgram(self.toolPathProgram)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        PARAMETERS_PER_VERTEX = 8
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "id"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "xyz"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(1*4))
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "pos"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(4*4))
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "colorValue"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(5*4))
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "dashRatio"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(6*4))
        glVertexAttribPointer(glGetAttribLocation(self.toolPathProgram, "flags"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(7*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "id"))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "xyz"))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "pos"))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "colorValue"))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "dashRatio"))
        glEnableVertexAttribArray(glGetAttribLocation(self.toolPathProgram, "flags"))


        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.toolPathProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        zoom_loc = glGetUniformLocation(program=self.toolPathProgram, name="zoom")
        glUniform1f(zoom_loc, self.zoom)

        select_color = vec3(self.rgb8(SELECT_COLOR))
        select_color_loc = glGetUniformLocation(program=self.toolPathProgram, name="selectColor")
        glUniform3fv(select_color_loc, 1, value_ptr(select_color))

        select2_color = vec3(self.rgb8(SELECT2_COLOR))
        select2_color_loc = glGetUniformLocation(program=self.toolPathProgram, name="select2Color")
        glUniform3fv(select2_color_loc, 1, value_ptr(select2_color))

        disable_color = vec3(self.rgb8(DISABLE_COLOR))
        disable_color_loc = glGetUniformLocation(program=self.toolPathProgram, name="disableColor")
        glUniform3fv(disable_color_loc, 1, value_ptr(disable_color))
        
        process_color = vec3(self.rgb8(PROCESS_COLOR))
        process_color_loc = glGetUniformLocation(program=self.toolPathProgram, name="processColor")
        glUniform3fv(process_color_loc, 1, value_ptr(process_color))
        
        lastProcessedPath_loc = glGetUniformLocation(program=self.toolPathProgram, name="lastProcessedPath")
        glUniform1f(lastProcessedPath_loc, self.app.lastProcessedPath)

        glLineWidth(lineWidth)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_LINES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawGantry(self):

        # Draw cone faces
        glUseProgram(self.gantryProgram)
        glEnable(GL_CULL_FACE)
        glBindBuffer(GL_ARRAY_BUFFER, self.gantryVBO)
        PARAMETERS_PER_VERTEX = 6
        glVertexAttribPointer(glGetAttribLocation(self.gantryProgram, "xyz"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.gantryProgram, "normal"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(3*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.gantryProgram, "xyz"))
        glEnableVertexAttribArray(glGetAttribLocation(self.gantryProgram, "normal"))
        
        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.gantryProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        gantry_color = vec3(self.rgb8(GANTRY_COLOR))
        gantry_color_loc = glGetUniformLocation(program=self.gantryProgram, name="gantryColor")
        glUniform3fv(gantry_color_loc, 1, value_ptr(gantry_color))
        
        location_loc = glGetUniformLocation(program=self.gantryProgram, name="location")
        glUniform3fv(location_loc, 1, value_ptr(self._gantryLocation))
        
        light1dir = normalize(inverse(MVP) * vec4(1.0, -0.25, -1.0, 0)).xyz
        light2dir = normalize(inverse(MVP) * vec4(-0.5, -0.125, -0.5, 0)).xyz
        
        light1dir_loc = glGetUniformLocation(program=self.gantryProgram, name="light1dir")
        glUniform3fv(light1dir_loc, 1, value_ptr(light1dir))
        light2dir_loc = glGetUniformLocation(program=self.gantryProgram, name="light2dir")
        glUniform3fv(light2dir_loc, 1, value_ptr(light2dir))

        #diameter = max(6., CNC.vars["diameter"])
        diameter = CNC.vars["diameter"]
        diameter_loc = glGetUniformLocation(program=self.gantryProgram, name="diameter")
        glUniform1f(diameter_loc, diameter)
        
        glLineWidth(2)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_TRIANGLES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Draw gantry lines (When the view is so close to XY that the cone tip is hidden)
        if self.viewAngle(vec3(0, 0, 1)) < 18.435:
            glDisable(GL_DEPTH_TEST)
            glUseProgram(self.gantryLinesProgram)
            glBindBuffer(GL_ARRAY_BUFFER, self.gantryLinesVBO)
            PARAMETERS_PER_VERTEX = 3
            glVertexAttribPointer(glGetAttribLocation(self.gantryLinesProgram, "xyz"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
            glEnableVertexAttribArray(glGetAttribLocation(self.gantryLinesProgram, "xyz"))

            gantry_color = vec3(self.rgb8(GANTRY_COLOR))
            gantry_color_loc = glGetUniformLocation(program=self.gantryLinesProgram, name="gantryColor")
            glUniform3fv(gantry_color_loc, 1, value_ptr(gantry_color))
            
            MVP = self.PMatrix * self.MVMatrix
            mv_loc = glGetUniformLocation(program=self.gantryLinesProgram, name="MVP")
            glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))
            
            location_loc = glGetUniformLocation(program=self.gantryLinesProgram, name="location")
            glUniform3fv(location_loc, 1, value_ptr(self._gantryLocation))

            #diameter = max(6., CNC.vars["diameter"])
            diameter = CNC.vars["diameter"]
            diameter_loc = glGetUniformLocation(program=self.gantryLinesProgram, name="diameter")
            glUniform1f(diameter_loc, diameter)
            
            glLineWidth(1)
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
            glDrawArrays(GL_LINES, 0, size // PARAMETERS_PER_VERTEX)
            glBindBuffer(GL_ARRAY_BUFFER, 0)


    def drawArrows(self, vbo):

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glUseProgram(self.ArrowProgram)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        PARAMETERS_PER_VERTEX = 12
        #glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "id"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(1*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "location"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(2*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "dir"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(5*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "width"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(8*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "height"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(9*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "colorValue"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(10*4))
        glVertexAttribPointer(glGetAttribLocation(self.ArrowProgram, "flags"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(11*4))
        #glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "id"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "index"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "location"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "dir"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "width"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "height"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "colorValue"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ArrowProgram, "flags"))


        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.ArrowProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))
        
        MVPinv = inverse(MVP)
        mvpinv_loc = glGetUniformLocation(program=self.ArrowProgram, name="MVPinv")
        glUniformMatrix4fv(mvpinv_loc, 1, False, value_ptr(MVPinv))

        zoom_loc = glGetUniformLocation(program=self.ArrowProgram, name="zoom")
        glUniform1f(zoom_loc, self.zoom)

        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_TRIANGLES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawAxes(self):

        glDisable(GL_DEPTH_TEST)
        glUseProgram(self.axesProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.axesVBO)
        PARAMETERS_PER_VERTEX = 5
        glVertexAttribPointer(glGetAttribLocation(self.axesProgram, "xyz"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.axesProgram, "position"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(3*4))
        glVertexAttribPointer(glGetAttribLocation(self.axesProgram, "axis"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(4*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.axesProgram, "xyz"))
        glEnableVertexAttribArray(glGetAttribLocation(self.axesProgram, "position"))
        glEnableVertexAttribArray(glGetAttribLocation(self.axesProgram, "axis"))
        
        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.axesProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))
        
        zoom_loc = glGetUniformLocation(program=self.axesProgram, name="zoom")
        glUniform1f(zoom_loc, self.zoom)
        
        glLineWidth(2)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_LINES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Draw axes text. Update text location with the current zoom
        self.axesText[1][0] = vec3(AXIS_LENGTH / self.zoom, 0, 0)
        self.axesText[2][0] = vec3(0, AXIS_LENGTH / self.zoom, 0)
        self.axesText[3][0] = vec3(0, 0, AXIS_LENGTH / self.zoom)
        self.update_text_buffer(self.AxesTextVBO, self.axesText)
        self.drawText(self.AxesTextVBO)
    
    def drawText(self, textBuffer):

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glUseProgram(self.TextProgram)
        glBindBuffer(GL_ARRAY_BUFFER, textBuffer)
        PARAMETERS_PER_VERTEX = 10
        #glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "id"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(1*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "location"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(2*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "hOffset"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(5*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "charoffset"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(6*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "charwidth"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(7*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "charheight"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(8*4))
        glVertexAttribPointer(glGetAttribLocation(self.TextProgram, "colorValue"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(9*4))
        #glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "id"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "index"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "location"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "hOffset"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "charoffset"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "charwidth"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "charheight"))
        glEnableVertexAttribArray(glGetAttribLocation(self.TextProgram, "colorValue"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.TextProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        textAtlasWidth_loc = glGetUniformLocation(program=self.TextProgram, name="textAtlasWidth")
        glUniform1f(textAtlasWidth_loc, len(self.charTextureAtlas[0]))

        canvasWidth_loc = glGetUniformLocation(program=self.TextProgram, name="canvasWidth")
        glUniform1f(canvasWidth_loc, self.winfo_width())
        canvasHeight_loc = glGetUniformLocation(program=self.TextProgram, name="canvasHeight")
        glUniform1f(canvasHeight_loc, self.winfo_height())

        # Set the uniform variable 'ourTexture' to texture unit 0
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.textTexture)
        glUniform1i(glGetUniformLocation(self.TextProgram, "ourTexture"), 0)
        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_TRIANGLES, 0, size // PARAMETERS_PER_VERTEX)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        
    def queueDraw(self):
        if self._drawRequested:
            return
        
        self._drawRequested = True
        
        self.after('idle', self.draw)
        
    def updateAll(self, view=None):
        
        self._last = (0.0, 0.0, 0.0)
        self.initPosition()
        
        self.createPaths()
        self.pathVertices = self.update_lines_buffer(self.pathVBO, self.pathDict, True)

        self.updateGrid()
        self.updateMargin()
        self.updateWorkArea()

        self.drawProbe()

        self.drawOrient()
        
        self.queueDraw()

    # ----------------------------------------------------------------------
    # Initialize gantry position
    # ----------------------------------------------------------------------
    def initPosition(self):
        
        # TODO: Anything apart from paths must be deleted...?
        #self.delete(ALL)
        self.pathVertices = self.deleteLines(self.pathDict, self.pathVertices, self.pathVBO)
        self.deleteArrows(self.pathArrows, self.pathArrowsVBO)

        self.updateGantry(0, 0, 0)

        self._lastInsert = None
        self._lastActive = None
        self._vector = None
        self._items.clear()
        self.cnc.initPath()
        self.cnc.resetAllMargins()

    # ----------------------------------------------------------------------
    # Update gantry location
    # ----------------------------------------------------------------------
    def updateGantry(self, x, y, z):
        self._gantryLocation = vec3(x, y, z)
        self.queueDraw()

    def createGantry(self):
        # Gantry geometry of diameter 1. We scale it with the actual diameter in the shader
        gr = 0.5
        gh = 3 * gr
        
        NUM_FACES = 32 # Number of faces in the whole turn of 360º
        
        # We create the gantry as a conical closed surface made up of triangles
        faceAngle = 2 * math.pi / NUM_FACES
        coneAngle = math.atan(gr / gh)
        
        vertices = []
        
        # We also calculate the normal vector for each vertex, in order to shade lights
        
        for f in range(NUM_FACES):
            # Lower Cone
            vertices.extend([
                gr * math.cos(faceAngle * f),
                gr * math.sin(faceAngle * f),
                gh,
                math.cos(coneAngle) * math.cos(faceAngle * f), math.cos(coneAngle) * math.sin(faceAngle * f), -math.sin(coneAngle)])
            vertices.extend([
                0, 0, 0,
                math.cos(coneAngle) * math.cos(faceAngle * f), math.cos(coneAngle) * math.sin(faceAngle * f), -math.sin(coneAngle)]) # normal
            vertices.extend([
                gr * math.cos(faceAngle * (f+1)),
                gr * math.sin(faceAngle * (f+1)),
                gh,
                math.cos(coneAngle) * math.cos(faceAngle * (f+1)), math.cos(coneAngle) * math.sin(faceAngle * (f+1)), -math.sin(coneAngle)])
            # Upper Disc
            vertices.extend([
                0, 0, gh, 
                0, 0, 1]) # Normal pointing upwards [0, 0, 1]
            vertices.extend([
                gr * math.cos(faceAngle * f),
                gr * math.sin(faceAngle * f),
                gh,
                0, 0, 1])
            vertices.extend([
                gr * math.cos(faceAngle * (f+1)),
                gr * math.sin(faceAngle * (f+1)),
                gh,
                0, 0, 1])
        
        gantryVertices = numpy.array(vertices, dtype=numpy.float32)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.gantryVBO)
        glBufferData(GL_ARRAY_BUFFER, gantryVertices.nbytes, gantryVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Create the vertices of the 4 lines going from the cone tip to the base
        gantryLinesVertices = numpy.array([
            0, 0, 0,
            gr, 0, gh,
            0, 0, 0,
            0, gr, gh,
            0, 0, 0,
            -gr, 0, gh,
            0, 0, 0,
            0, -gr, gh
        ], dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, self.gantryLinesVBO)
        glBufferData(GL_ARRAY_BUFFER, gantryLinesVertices.nbytes, gantryLinesVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)


    # ----------------------------------------------------------------------
    # Create system axes
    # ----------------------------------------------------------------------
    def createAxes(self, axisLength):        
        axesVertices = numpy.array([
            # X axis
            0, 0, 0, # Start Point
            0, # position. 0 for the first point of the line and length for the second. Used for dashed lines
            1, # Axis X
            axisLength, 0, 0, # End Point
            axisLength, # position. 0 for the first point of the line and length for the second. Used for dashed lines
            1, # Axis X
            # Y axis
            0, 0, 0, 0, 2, 0, axisLength, 0, axisLength, 2,
            # Z axis          
            0, 0, 0, 0, 3, 0, 0, axisLength, axisLength, 3
        ], dtype=numpy.float32)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.axesVBO)
        glBufferData(GL_ARRAY_BUFFER, axesVertices.nbytes, axesVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        # Text (x, y, z)
        self.axesText = {
            1: [vec3(axisLength * self.zoom, 0, 0), "X", self.rgb8(AXES_TEXT_COLOR)],
            2: [vec3(0, axisLength * self.zoom, 0), "Y", self.rgb8(AXES_TEXT_COLOR)],
            3: [vec3(0, 0, axisLength * self.zoom), "Z", self.rgb8(AXES_TEXT_COLOR)]
            }
        self.update_text_buffer(self.AxesTextVBO, self.axesText)
        
    # Update the selection rectangle
    def updateSelectionRect(self, x1, y1, x2, y2):
        glBindBuffer(GL_ARRAY_BUFFER, self.SelectionRectVBO)

        p1 = self.canvas2Unit(vec2(x1, y1))
        p2 = self.canvas2Unit(vec2(x2, y2))

        self.SelectionRectVertices = numpy.array(
            [p1.x, p1.y,
             p2.x, p1.y,
             p2.x, p2.y,
             p1.x, p1.y,
             p2.x, p2.y,
             p1.x, p2.y],
             dtype=numpy.float32)
        
        glBufferData(GL_ARRAY_BUFFER, self.SelectionRectVertices.nbytes, self.SelectionRectVertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    # ----------------------------------------------------------------------
    # Draw margins of selected blocks
    # ----------------------------------------------------------------------
    def updateMargin(self):
        if not self.draw_margin:
            self.queueDraw()
            return
        
        marginLines = {}

        if CNC.isMarginValid():
            xyz = [[CNC.vars["xmin"], CNC.vars["ymin"], 0.0],
                [CNC.vars["xmax"], CNC.vars["ymin"], 0.0],
                [CNC.vars["xmax"], CNC.vars["ymax"], 0.0],
                [CNC.vars["xmin"], CNC.vars["ymax"], 0.0],
                [CNC.vars["xmin"], CNC.vars["ymin"], 0.0]]
        
            self.create_line(marginLines, xyz, self.rgb8(MARGIN_COLOR), 1)
            self.update_lines_buffer(self.marginsVBO, marginLines)

        if not CNC.isAllMarginValid():
            self.queueDraw()
            return
        
        xyz = [[CNC.vars["axmin"], CNC.vars["aymin"], 0.0],
                [CNC.vars["axmax"], CNC.vars["aymin"], 0.0],
                [CNC.vars["axmax"], CNC.vars["aymax"], 0.0],
                [CNC.vars["axmin"], CNC.vars["aymax"], 0.0],
                [CNC.vars["axmin"], CNC.vars["aymin"], 0.0]]
    
        self.create_line(marginLines, xyz, self.rgb8(MARGIN_COLOR), 0.66)
        self.update_lines_buffer(self.marginsVBO, marginLines)
        
        self.queueDraw()

    # ----------------------------------------------------------------------
    # Draw a workspace rectangle
    # ----------------------------------------------------------------------
    def updateWorkArea(self):
        if not self.draw_workarea:
            self.queueDraw()
            return

        workAreaLines = {}

        xmin = self._dx - CNC.travel_x
        ymin = self._dy - CNC.travel_y
        xmax = self._dx
        ymax = self._dy

        xyz = [[xmin, ymin, 0.0],
            [xmax, ymin, 0.0],
            [xmax, ymax, 0.0],
            [xmin, ymax, 0.0],
            [xmin, ymin, 0.0]]
    
        self.create_line(workAreaLines, xyz, self.rgb8(WORK_COLOR), 0.661)
        self.update_lines_buffer(self.workAreaVBO, workAreaLines)
        
        self.queueDraw()

    # ----------------------------------------------------------------------
    # Draw coordinates grid
    # ----------------------------------------------------------------------
    def updateGrid(self):
        gridLines = {}
        
        xmin = (CNC.vars["axmin"] // 10) * 10
        xmax = (CNC.vars["axmax"] // 10 + 1) * 10
        ymin = (CNC.vars["aymin"] // 10) * 10
        ymax = (CNC.vars["aymax"] // 10 + 1) * 10
        
        for i in range(
            int(CNC.vars["aymin"] // 10), int(CNC.vars["aymax"] // 10) + 2
        ):
            y = i * 10.0
            self.create_line(gridLines,
                             [[xmin, y, 0], [xmax, y, 0]],
                             self.rgb8(GRID_COLOR),
                             0.25)

        for i in range(
            int(CNC.vars["axmin"] // 10), int(CNC.vars["axmax"] // 10) + 2
        ):
            x = i * 10.0
            self.create_line(gridLines,
                             [[x, ymin, 0], [x, ymax, 0]],
                             self.rgb8(GRID_COLOR),
                             0.25)
        
        self.update_lines_buffer(self.gridVBO, gridLines)
        
        self.queueDraw()

    # ----------------------------------------------------------------------
    # Display orientation markers
    # ----------------------------------------------------------------------
    def drawOrient(self, event=None):
        self.orientDict = {}

        # Draw orient markers
        if CNC.inch:
            w = 0.1
        else:
            w = 2.5

        self.gcode.orient.clearPaths()
        for i, (xm, ym, x, y) in enumerate(self.gcode.orient.markers):
            paths = []
            
            # Machine position (cross)
            item = self.create_line(self.orientDict,
                [(xm - w, ym, 0.0), (xm + w, ym, 0.0)],
                self.rgb8('Green'),
                1.)
            paths.append(item)

            item = self.create_line(self.orientDict,
                [(xm, ym - w, 0.0), (xm, ym + w, 0.0)],
                self.rgb8('Green'),
                1.)
            paths.append(item)

            # GCode position (cross)
            item = self.create_line(self.orientDict,
                [(x - w, y, 0.0), (x + w, y, 0.0)],
                self.rgb8('Red'),
                1.)
            paths.append(item)

            item = self.create_line(self.orientDict,
                [(x, y - w, 0.0), (x, y + w, 0.0)],
                self.rgb8('Red'),
                1.)
            paths.append(item)

            # Draw error if any
            try:
                err = self.gcode.orient.errors[i]
                item = self.create_oval(self.orientDict,
                    (xm - err, ym - err, 0.0),
                    (xm + err, ym + err, 0.0),
                    self.rgb8('Red'),
                    1.)
                paths.append(item)

                err = self.gcode.orient.errors[i]
                item = self.create_oval(self.orientDict,
                    (x - err, y - err, 0.0),
                    (x + err, y + err, 0.0),
                    self.rgb8('Red'),
                    1.)
                paths.append(item)
            except IndexError:
                pass

            # Connecting line
            item = self.create_line(self.orientDict,
                [(xm, ym, 0.0), (x, y, 0.0)],
                self.rgb8('Blue'),
                0.5)
            paths.append(item)

            self.gcode.orient.addPath(paths)

        if self._orientSelected is not None:
            try:
                for item in self.gcode.orient.paths[self._orientSelected]:
                    self.orientDict[item][3] = FLAG_ENABLED | FLAG_SELECTED

            except (IndexError, TclError):
                pass
        
        self.update_lines_buffer(self.orientVBO, self.orientDict)
        
        self.queueDraw()

    # ----------------------------------------------------------------------
    # Display probe
    # ----------------------------------------------------------------------
    def drawProbe(self):
        self.probeDict = {}
        self.update_lines_buffer(self.probeVBO, self.probeDict)
        self.probeText = {}
        self.update_text_buffer(self.ProbeTextVBO, self.probeText)
        # Clear image map if numpy exists
        if (numpy is not None):
            self.clear_probe_map_buffer()

        if not self.draw_probe:
            self.queueDraw()
            return

        # Draw probe grid
        probe = self.gcode.probe
        for x in bmath.frange(probe.xmin, probe.xmax + 0.00001, probe.xstep()):
            xyz = [(x, probe.ymin, 0.0), (x, probe.ymax, 0.0)]
            item = self.create_line(
                self.probeDict,
                xyz,
                self.rgb8('Yellow'),
                1.)

        for y in bmath.frange(probe.ymin, probe.ymax + 0.00001, probe.ystep()):
            xyz = [(probe.xmin, y, 0.0), (probe.xmax, y, 0.0)]
            item = self.create_line(
                self.probeDict,
                xyz,
                self.rgb8('Yellow'),
                1.)
        
        self.update_lines_buffer(self.probeVBO, self.probeDict)

        # Draw probe points text
        self.updateProbeText()

        # Draw image map if numpy exists
        if (numpy is not None and probe.matrix):
            self.update_probe_map_buffer()

        self.queueDraw()

    def updateProbeText(self):
        probe = self.gcode.probe

        if probe.matrix:
            self.probeText = {}
            for i, location in enumerate(probe.points):
                item = self.create_text(
                    self.probeText,
                    vec3(location[0], location[1], location[2] * self.probeMapHeightScale),
                    f"{probe.points[i][2]:.{CNC.digits}f}",
                    self.rgb8(PROBE_TEXT_COLOR))

            self.update_text_buffer(self.ProbeTextVBO, self.probeText)

    def drawProbeMap(self):
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glUseProgram(self.ProbeMapProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.ProbeMapVBO)
        PARAMETERS_PER_VERTEX = 4
        glVertexAttribPointer(glGetAttribLocation(self.ProbeMapProgram, "location"), 3, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, None)
        glVertexAttribPointer(glGetAttribLocation(self.ProbeMapProgram, "colorValue"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(3*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.ProbeMapProgram, "location"))
        glEnableVertexAttribArray(glGetAttribLocation(self.ProbeMapProgram, "colorValue"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.ProbeMapProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        heightScale_loc = glGetUniformLocation(program=self.ProbeMapProgram, name="heightScale")
        glUniform1f(heightScale_loc, self.probeMapHeightScale)

        alpha_loc = glGetUniformLocation(program=self.ProbeMapProgram, name="alpha")
        glUniform1f(alpha_loc, 0.5)

        size = glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawArrays(GL_TRIANGLES, 0, size // PARAMETERS_PER_VERTEX)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def clear_probe_map_buffer(self):
        probeMapVertices = numpy.array([], dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, self.ProbeMapVBO)
        glBufferData(GL_ARRAY_BUFFER, probeMapVertices.nbytes, probeMapVertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the VBO

    def update_probe_map_buffer(self):
        probe = self.gcode.probe

        probeMaxZ = numpy.max(probe.matrix)
        probeMinZ = numpy.min(probe.matrix)

        probeMapData = []

        # Get matrix size and steps (based on the matrix size, not on the last xn and yn input in the ProbePage widgets. 
        # The matrix size will match xn and yn when probe data is loaded or scan is performed)
        m = len(probe.matrix[0])
        n = len(probe.matrix)
        mstep = (probe.xmax - probe.xmin) / (m - 1)
        nstep = (probe.ymax - probe.ymin) / (n - 1)

        # Each quad of the map is drawn as two triangles (6 vertices)
        for j in range(n - 1):
            for i in range(m - 1):
                color1 = self.blue2red(probe.matrix[j][i], probeMinZ, probeMaxZ)
                color2 = self.blue2red(probe.matrix[j][i + 1], probeMinZ, probeMaxZ)
                color3 = self.blue2red(probe.matrix[j + 1][i + 1], probeMinZ, probeMaxZ)
                color4 = self.blue2red(probe.matrix[j + 1][i], probeMinZ, probeMaxZ)
                probeMapData.extend([
                    # Corner 1
                    probe.xmin + i * mstep,
                    probe.ymin + j * nstep,
                    probe.matrix[j][i],
                    (int(color1.x) << 16) + (int(color1.y) << 8) + int(color1.z),
                    # Corner 2
                    probe.xmin + (i + 1) * mstep,
                    probe.ymin + j * nstep,
                    probe.matrix[j][i + 1],
                    (int(color2.x) << 16) + (int(color2.y) << 8) + int(color2.z),
                    # Corner 3
                    probe.xmin + (i + 1) * mstep,
                    probe.ymin + (j + 1) * nstep,
                    probe.matrix[j + 1][i + 1],
                    (int(color3.x) << 16) + (int(color3.y) << 8) + int(color3.z),
                    # Corner 1
                    probe.xmin + i * mstep,
                    probe.ymin + j * nstep,
                    probe.matrix[j][i],
                    (int(color1.x) << 16) + (int(color1.y) << 8) + int(color1.z),
                    # Corner 3
                    probe.xmin + (i + 1) * mstep,
                    probe.ymin + (j + 1) * nstep,
                    probe.matrix[j + 1][i + 1],
                    (int(color3.x) << 16) + (int(color3.y) << 8) + int(color3.z),
                    # Corner 4
                    probe.xmin + i * mstep,
                    probe.ymin + (j + 1) * nstep,
                    probe.matrix[j + 1][i],
                    (int(color4.x) << 16) + (int(color4.y) << 8) + int(color4.z),
                ])

        probeMapVertices = numpy.array(probeMapData, dtype=numpy.float32)

        glBindBuffer(GL_ARRAY_BUFFER, self.ProbeMapVBO)
        glBufferData(GL_ARRAY_BUFFER, probeMapVertices.nbytes, probeMapVertices, GL_STATIC_DRAW)

        glBindBuffer(GL_ARRAY_BUFFER, 0)  # Unbind the VBO

        return probeMapVertices

    # ----------------------------------------------------------------------
    # Create paths for the whole gcode file
    # ----------------------------------------------------------------------
    def createPaths(self):
        self.pathDict = {}

        if not self.draw_paths:
            for block in self.gcode.blocks:
                block.resetPath()
            return

        try:
            n = 1
            startTime = before = time.time()
            self.cnc.resetAllMargins()
            drawG = self.draw_rapid or self.draw_paths or self.draw_margin
            for i, block in enumerate(self.gcode.blocks):
                start = True  # start location found
                block.resetPath()

                # Draw block
                for j, line in enumerate(block):
                    n -= 1
                    if n == 0:
                        if time.time() - startTime > DRAW_TIME:
                            raise AlarmException()
                        # Force a periodic update since this loop can take time
                        if time.time() - before > 1.0:
                            self.update()
                            before = time.time()
                        n = 1000
                    try:
                        cmd = self.gcode.evaluate(
                            CNC.compileLine(line), self.app)
                        if isinstance(cmd, tuple):
                            cmd = None
                        else:
                            cmd = CNC.breakLine(cmd)
                    except AlarmException:
                        raise
                    except Exception:
                        sys.stderr.write(
                            _(">>> ERROR: {}\n").format(str(sys.exc_info()[1]))
                        )
                        sys.stderr.write(_("     line: {}\n").format(line))
                        cmd = None
                    if cmd is None or not drawG:
                        block.addPath(None)
                    else:
                        path = self.drawPath(block, cmd)
                        self._items[path] = i, j
                        block.addPath(path)
                        if start and self.cnc.gcode in (1, 2, 3):
                            # Mark as start the first non-rapid motion
                            block.startPath(self.cnc.x, self.cnc.y, self.cnc.z)
                            start = False
                block.endPath(self.cnc.x, self.cnc.y, self.cnc.z)
        except AlarmException:
            self.status("Rendering takes TOO Long. Interrupted...")

    # ----------------------------------------------------------------------
    # Create path for one g command
    # ----------------------------------------------------------------------
    def drawPath(self, block, cmds):
        self.cnc.motionStart(cmds)
        xyz = self.cnc.motionPath()
        self.cnc.motionEnd()
        if xyz:
            self.cnc.pathLength(block, xyz)
            if self.cnc.gcode in (1, 2, 3):
                block.pathMargins(xyz)
                self.cnc.pathMargins(block)
            
            flags = 0

            if block.enable:
                flags |= FLAG_ENABLED

                if self.cnc.gcode == 0 and self.draw_rapid:
                    xyz[0] = self._last
                self._last = xyz[-1]

            else:
                if self.cnc.gcode == 0:
                    return None                

            if block.color:
                fill = block.color
                
            else:
                fill = ENABLE_COLOR

            if self.cnc.gcode == 0:
                if self.draw_rapid:
                    if RAPID_COLOR != "":
                        fill = RAPID_COLOR

                    return self.create_line(
                        self.pathDict,
                        xyz,
                        self.rgb8(fill),
                        0.6,
                        flags)
                
            elif self.draw_paths:
                return self.create_line(
                    self.pathDict,
                    xyz,
                    self.rgb8(fill),
                    1,
                    flags)
            
        return None
    
    def drawStockTop(self):
        glUseProgram(self.stockTopProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.stockTopVBO)
        PARAMETERS_PER_VERTEX = 2
        glVertexAttribPointer(glGetAttribLocation(self.stockTopProgram, "uv"), 2, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(0*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.stockTopProgram, "uv"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.stockTopProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_2D, self.textures[0])

        glUniform1i(glGetUniformLocation(self.stockTopProgram, "heightMap"), 0)

        glUniform3f(glGetUniformLocation(self.stockTopProgram, "stockMin"), STOCK_MIN_X, STOCK_MIN_Y, STOCK_MIN_Z)
        glUniform3f(glGetUniformLocation(self.stockTopProgram, "stockMax"), STOCK_MAX_X, STOCK_MAX_Y, STOCK_MAX_Z)
        glUniform1f(glGetUniformLocation(self.stockTopProgram, "meshResolution"), MESH_RES)
        glUniform1f(glGetUniformLocation(self.stockTopProgram, "opacity"), self.stockOpacity.get() / 100.)

        uvmin, uvmax = self.getStockVisibleArea()
        glUniform2f(glGetUniformLocation(self.stockTopProgram, "uvmin"), uvmin.x, uvmin.y)
        glUniform2f(glGetUniformLocation(self.stockTopProgram, "uvmax"), uvmax.x, uvmax.y)

        light1dir = normalize(inverse(MVP) * vec4(1.0, -0.25, -1.0, 0)).xyz
        light2dir = normalize(inverse(MVP) * vec4(-0.5, -0.125, -0.5, 0)).xyz
        
        glUniform3fv(glGetUniformLocation(program=self.stockTopProgram, name="light1dir"), 1, value_ptr(light1dir))
        glUniform3fv(glGetUniformLocation(program=self.stockTopProgram, name="light2dir"), 1, value_ptr(light2dir))

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.stockTopEBO)
        size = glGetBufferParameteriv(GL_ELEMENT_ARRAY_BUFFER, GL_BUFFER_SIZE) // 4
        glDrawElements(GL_TRIANGLES, size, GL_UNSIGNED_INT, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawStockBottom(self):
        glUseProgram(self.stockBottomProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.stockBottomVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(glGetAttribLocation(self.stockBottomProgram, "index"), 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(0*4))
        glEnableVertexAttribArray(glGetAttribLocation(self.stockBottomProgram, "index"))

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.stockBottomProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_2D, self.textures[0])

        glUniform1i(glGetUniformLocation(self.stockBottomProgram, "heightMap"), 0)

        glUniform3f(glGetUniformLocation(self.stockBottomProgram, "stockMin"), STOCK_MIN_X, STOCK_MIN_Y, STOCK_MIN_Z)
        glUniform3f(glGetUniformLocation(self.stockBottomProgram, "stockMax"), STOCK_MAX_X, STOCK_MAX_Y, STOCK_MAX_Z)
        glUniform1f(glGetUniformLocation(self.stockBottomProgram, "opacity"), self.stockOpacity.get() / 100.)

        light1dir = normalize(inverse(MVP) * vec4(1.0, -0.25, -1.0, 0)).xyz
        light2dir = normalize(inverse(MVP) * vec4(-0.5, -0.125, -0.5, 0)).xyz
        
        glUniform3fv(glGetUniformLocation(program=self.stockBottomProgram, name="light1dir"), 1, value_ptr(light1dir))
        glUniform3fv(glGetUniformLocation(program=self.stockBottomProgram, name="light2dir"), 1, value_ptr(light2dir))

        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def drawStockSide(self, side: int):
        # Side -> 1: up, 2: down, 3: left, 4: right
        # p1 and p2 -> vertices of the side surface
        glUseProgram(self.stockSideProgram)
        glBindBuffer(GL_ARRAY_BUFFER, self.stockSideVBO)
        PARAMETERS_PER_VERTEX = 1
        glVertexAttribPointer(self.stockSideProgram_index, 1, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(0*4))
        glEnableVertexAttribArray(self.stockSideProgram_index)

        MVP = self.PMatrix * self.MVMatrix
        mv_loc = glGetUniformLocation(program=self.stockSideProgram, name="MVP")
        glUniformMatrix4fv(mv_loc, 1, False, value_ptr(MVP))

        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_2D, self.textures[0])

        glUniform1i(self.stockSideProgram_heightMap, 0)
        glUniform1f(self.stockSideProgram_side, float(side))
        glUniform1f(self.stockSideProgram_zmin, STOCK_MIN_Z)
        glUniform1f(self.stockSideProgram_zmax, STOCK_MAX_Z)


        if side == 1:
            p1 = vec3(STOCK_MAX_X, STOCK_MAX_Y, STOCK_MIN_Z)
            p2 = vec3(STOCK_MIN_X, STOCK_MAX_Y, STOCK_MAX_Z)
        elif side == 2:
            p1 = vec3(STOCK_MIN_X, STOCK_MIN_Y, STOCK_MIN_Z)
            p2 = vec3(STOCK_MAX_X, STOCK_MIN_Y, STOCK_MAX_Z)
        elif side == 3:
            p1 = vec3(STOCK_MIN_X, STOCK_MAX_Y, STOCK_MIN_Z)
            p2 = vec3(STOCK_MIN_X, STOCK_MIN_Y, STOCK_MAX_Z)
        elif side == 4:
            p1 = vec3(STOCK_MAX_X, STOCK_MIN_Y, STOCK_MIN_Z)
            p2 = vec3(STOCK_MAX_X, STOCK_MAX_Y, STOCK_MAX_Z)
        else:
            return

        glUniform3f(self.stockSideProgram_p1, p1.x, p1.y, p1.z)
        glUniform3f(self.stockSideProgram_p2, p2.x, p2.y, p2.z)
        glUniform1f(self.stockSideProgram_opacity, self.stockOpacity.get() / 100.)

        light1dir = normalize(inverse(MVP) * vec4(1.0, -0.25, -1.0, 0)).xyz
        light2dir = normalize(inverse(MVP) * vec4(-0.5, -0.125, -0.5, 0)).xyz
        
        glUniform3fv(self.stockSideProgram_light1dir, 1, value_ptr(light1dir))
        glUniform3fv(self.stockSideProgram_light2dir, 1, value_ptr(light2dir))

        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
    
    def getStockVisibleArea(self):
        if self.viewAngle(vec3(0, 0, 1)) == 90:
            return vec2(0, 0), vec2(1, 1)
        
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Project the 4 corners of the canvas to the stock upper surface
        bl_up = self.canvas2WorldPlane(vec2(0, height), vec3(0, 0, 1), vec3(0, 0, STOCK_MAX_Z), 0)
        br_up = self.canvas2WorldPlane(vec2(width, height), vec3(0, 0, 1), vec3(0, 0, STOCK_MAX_Z), 0)
        ul_up = self.canvas2WorldPlane(vec2(0, 0), vec3(0, 0, 1), vec3(0, 0, STOCK_MAX_Z), 0)
        ur_up = self.canvas2WorldPlane(vec2(width, 0), vec3(0, 0, 1), vec3(0, 0, STOCK_MAX_Z), 0)

        # Project the 4 corners of the canvas to the stock lower surface
        bl_lo = self.canvas2WorldPlane(vec2(0, height), vec3(0, 0, 1), vec3(0, 0, STOCK_MIN_Z), 0)
        br_lo = self.canvas2WorldPlane(vec2(width, height), vec3(0, 0, 1), vec3(0, 0, STOCK_MIN_Z), 0)
        ul_lo = self.canvas2WorldPlane(vec2(0, 0), vec3(0, 0, 1), vec3(0, 0, STOCK_MIN_Z), 0)
        ur_lo = self.canvas2WorldPlane(vec2(width, 0), vec3(0, 0, 1), vec3(0, 0, STOCK_MIN_Z), 0)

        xmin = min(bl_up.x, br_up.x, ul_up.x, ur_up.x, bl_lo.x, br_lo.x, ul_lo.x, ur_lo.x)
        xmax = max(bl_up.x, br_up.x, ul_up.x, ur_up.x, bl_lo.x, br_lo.x, ul_lo.x, ur_lo.x)
        ymin = min(bl_up.y, br_up.y, ul_up.y, ur_up.y, bl_lo.y, br_lo.y, ul_lo.y, ur_lo.y)
        ymax = max(bl_up.y, br_up.y, ul_up.y, ur_up.y, bl_lo.y, br_lo.y, ul_lo.y, ur_lo.y)

        uvminx = max(0, (xmin - STOCK_MIN_X) / (STOCK_MAX_X - STOCK_MIN_X))
        uvmaxx = min(1, (xmax - STOCK_MIN_X) / (STOCK_MAX_X - STOCK_MIN_X))
        uvminy = max(0, (ymin - STOCK_MIN_Y) / (STOCK_MAX_Y - STOCK_MIN_Y))
        uvmaxy = min(1, (ymax - STOCK_MIN_Y) / (STOCK_MAX_Y - STOCK_MIN_Y))

        return vec2(uvminx, uvminy), vec2(uvmaxx, uvmaxy)

    def millSegment(self, p1: vec3, p2: vec3, toolType: int, toolRadius: float, updateParams: bool = True):
        """
        Single-pass, scissored milling update.

        The fragment shader reads the source height texture and writes
        the complete destination value for every pixel in the scissor
        rectangle. Pixels outside the actual cutter footprint simply
        write oldHeight unchanged.
        """

        glUseProgram(self.millProgram)

        # Source height map.
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.textures[0])

        if updateParams: # Use False if these parameters did not change from the last call to millSegment, to reduce gpu load
            glUniform1i(self.millProgram_heightMap, 0)
            glUniform1f(self.millProgram_toolRadius, toolRadius)
            glUniform1i(self.millProgram_toolType, toolType) # TODO: tool type as argument
            glUniform3f(self.millProgram_workMin, STOCK_MIN_X, STOCK_MIN_Y, STOCK_MIN_Z)
            glUniform3f(self.millProgram_workMax, STOCK_MAX_X, STOCK_MAX_Y, STOCK_MAX_Z)

        # Cutter bounding box in workpiece coordinates.
        min_x = max(STOCK_MIN_X, min(p1.x - toolRadius, p2.x - toolRadius))
        max_x = min(STOCK_MAX_X, max(p1.x + toolRadius, p2.x + toolRadius))
        min_y = max(STOCK_MIN_Y, min(p1.y - toolRadius, p2.y - toolRadius))
        max_y = min(STOCK_MAX_Y, max(p1.y + toolRadius, p2.y + toolRadius))

        if min_x >= max_x or min_y >= max_y:
            return

        work_w = STOCK_MAX_X - STOCK_MIN_X
        work_h = STOCK_MAX_Y - STOCK_MIN_Y

        # Convert physical XY to texture/framebuffer pixels.
        sx0 = int(math.floor((min_x - STOCK_MIN_X) / work_w * HEIGHTMAP_RES))
        sx1 = int(math.ceil((max_x - STOCK_MIN_X) / work_w * HEIGHTMAP_RES))

        sy0 = int(math.floor((min_y - STOCK_MIN_Y) / work_h * HEIGHTMAP_RES))
        sy1 = int(math.ceil((max_y - STOCK_MIN_Y) / work_h * HEIGHTMAP_RES))

        sx0 = max(0, min(HEIGHTMAP_RES - 1, sx0))
        sy0 = max(0, min(HEIGHTMAP_RES - 1, sy0))
        sx1 = max(sx0 + 1, min(HEIGHTMAP_RES, sx1))
        sy1 = max(sy0 + 1, min(HEIGHTMAP_RES, sy1))

        width = sx1 - sx0
        height = sy1 - sy0

        # Destination FBO.
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[1])

        glDrawBuffer(GL_COLOR_ATTACHMENT0)

        glViewport(0, 0, HEIGHTMAP_RES, HEIGHTMAP_RES)

        # Rasterization is restricted to the cutter's bounding box.
        glEnable(GL_SCISSOR_TEST)
        glScissor(sx0, sy0, width, height)

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)
        glDisable(GL_CULL_FACE)

        glBindBuffer(GL_ARRAY_BUFFER, self.millVBO)
        PARAMETERS_PER_VERTEX = 2
        glVertexAttribPointer(self.millProgram_pos, 2, GL_FLOAT, GL_FALSE, PARAMETERS_PER_VERTEX*4, c_void_p(0*4))
        glEnableVertexAttribArray(self.millProgram_pos)

        glUniform3f(self.millProgram_pA, p1.x, p1.y, p1.z)
        glUniform3f(self.millProgram_pB, p2.x, p2.y, p2.z)

        glDrawArrays(GL_TRIANGLES, 0, 3)

        glBindBuffer(GL_ARRAY_BUFFER, 0)

        glUseProgram(0)
        glDisable(GL_SCISSOR_TEST)

        # Copy the milled region to the source framebuffer
        glBindFramebuffer(GL_READ_FRAMEBUFFER, self.fbos[1])
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.fbos[0])

        glBlitFramebuffer(
            sx0, sy0,
            sx1, sy1,
            sx0, sy0,
            sx1, sy1,
            GL_COLOR_BUFFER_BIT,
            GL_NEAREST
        )

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def runSimulation(self):
        if self.millType.get() == '':
            return
        
        if self.millDiameter.get() == '':
            return

        lines16 = numpy.reshape(self.pathVertices, (-1, 16))

        millType = MILL_TYPES[self.millType.get()]

        toolRadius = self.millDiameter.get() / 2.

        firstSegment = True

        t = time.time()
        tr = t + 0.5 # Time when we refresh

        pd = tkDialogs.ProgressDialog(self.app, "Calculating final shape...")

        l = 0
        nl = len(lines16)

        for line in lines16:
            if time.time() >= tr:
                if pd.ended:
                    break
                
                pd.show(l / nl * 100)

                self.queueDraw()
                tr += 0.5

            flags = int(line[7])

            if flags & FLAG_ENABLED:
                if not self.millSelectedPathsOnly.get() or ((flags & FLAG_SELECTED) != 0):                
                    p1 = vec3(line[1:4])
                    p2 = vec3(line[9:12])
        
                    self.millSegment(p1, p2, millType, toolRadius, firstSegment)
                    
                    firstSegment = False
            
            l += 1
        
        pd.stop()

        self.queueDraw()

    def resetStock(self):
        glDisable(GL_SCISSOR_TEST)
        
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.fbos[0])

        glViewport(0, 0, HEIGHTMAP_RES, HEIGHTMAP_RES)

        # Reset the stock height (1.0 in the heightmap)
        glClearColor(1.0, 1.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        self.queueDraw()
    
    def is_raspberry_pi(self):
        """
        Detect if the app is running the app in a Pi, to disable Simulation
        """
        # 1. If it's not Linux, not a native Raspberry Pi
        if not sys.platform.startswith('linux'):
            return False
            
        # 2. If in Linux, find the model file
        try:
            model_path = '/sys/firmware/devicetree/base/model'
            if os.path.exists(model_path):
                with open(model_path, 'r', errors='ignore') as f:
                    if 'raspberry pi' in f.read().lower():
                        return True
        except Exception:
            pass # If not permission, go to Plan B
            
        # 3. Plan B: Check architecture and cpuinfo
        try:
            cpuinfo_path = '/proc/cpuinfo'
            if os.path.exists(cpuinfo_path):
                with open(cpuinfo_path, 'r') as f:
                    cpuinfo = f.read().lower()
                    if 'bcm2835' in cpuinfo or 'bcm2711' in cpuinfo or 'bcm2712' in cpuinfo:
                        return True
        except Exception:
            pass

        # 4. Plan C: Check Pi specific environment variables
        if os.getenv('XDG_CURRENT_DESKTOP') == 'LXDE' and platform.machine() in ('armv7l', 'aarch64'):
            return True

        return False

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
        self.draw_probe = BooleanVar()
        self.draw_paths = BooleanVar()
        self.draw_rapid = BooleanVar()
        self.draw_workarea = BooleanVar()
        self.draw_camera = BooleanVar()
        self.view = StringVar()
        self.show_sim = BooleanVar()
        self.first_time_sim_shown = True

        self.loadConfig()
        self.view.trace_add('write', self.viewChange)

        toolbar = Frame(self, relief=RAISED)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=EW)

        # Ensure the Frame exists at the OS level before OpenGL initializes
        self.pack(side='top', fill='both', expand=True)
        self.update()

        self.canvas = CNCCanvas(self, app, takefocus=True, background="White")
        # OpenGL context
        print(f"self.canvas.winfo_id(): {self.canvas.winfo_id()}")
        self.canvas.grid(row=1, column=1, sticky=NSEW)

        self.createCanvasToolbar(toolbar)

        # --- SIM Panel ---
        
        self.simPanel = Frame(self, padx=5, pady=10)

        lframe = LabelFrame(self.simPanel, text=_("Stock dimensions"), foreground="DarkBlue", padx=5, pady = 5)
        lframe.pack(side='top', fill='x')

        row, col = 0, 0
        # Empty
        col += 1
        Label(lframe, text=_("Min")).grid(row=row, column=col, sticky=EW)
        col += 1
        Label(lframe, text=_("Max")).grid(row=row, column=col, sticky=EW)

        # --- X ---
        row += 1
        col = 0
        Label(lframe, text=_("X:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.stockXmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockXmin.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockXmin, _("X minimum"))
        self.addWidget(self.stockXmin)

        col += 1
        self.stockXmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockXmax.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockXmax, _("X maximum"))
        self.addWidget(self.stockXmax)

        # --- Y ---
        row += 1
        col = 0
        Label(lframe, text=_("Y:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.stockYmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockYmin.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockYmin, _("Y minimum"))
        self.addWidget(self.stockYmin)

        col += 1
        self.stockYmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockYmax.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockYmax, _("Y maximum"))
        self.addWidget(self.stockYmax)

        # --- Z ---
        row += 1
        col = 0
        Label(lframe, text=_("Z:")).grid(row=row, column=col, sticky=E)
        col += 1
        self.stockZmin = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockZmin.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockZmin, _("Z minimum"))
        self.addWidget(self.stockZmin)

        col += 1
        self.stockZmax = tkExtra.FloatEntry(lframe, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=5)
        self.stockZmax.grid(row=row, column=col, sticky=EW)
        tkExtra.Balloon.set(self.stockZmax, _("Z maximum"))
        self.addWidget(self.stockZmax)

        # --- Update button ---
        row += 1
        col = 1
        bRefresh = Button(lframe, text=_("Update"), compound=LEFT, command=self.updateStockSize, image=Utils.icons["refresh"], padx=2, pady=1)
        bRefresh.grid(row=row, column=col, columnspan=2, sticky=EW)
        self.addWidget(bRefresh)

        lframe.grid_columnconfigure(1, weight=1)
        lframe.grid_columnconfigure(2, weight=1)

        # --- End Mill data ---

        lframe = LabelFrame(self.simPanel, text=_("End Mill"), foreground="DarkBlue", padx=5)
        lframe.pack(side='top', fill='x', pady=10)
        self.millType = tkinter.OptionMenu(lframe, self.canvas.millType, "Flat", "Ball")
        #self.millType = tkExtra.Combobox(lframe, True, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, textvariable=self.canvas.millType)
        #self.millType.fill(["Flat", "Ball"])
        #self.millType.set("Flat")
        self.millType.pack(side='top', fill='x')
        tkExtra.Balloon.set(self.millType, _("Type of End Mill"))

        lineFrame = Frame(lframe)
        lineFrame.pack(side='top', fill='x', pady=10)

        Label(lineFrame, text=_("Diameter:")).pack(side='left')
        self.millDiameter = tkExtra.FloatEntry(lineFrame, background=tkExtra.GLOBAL_CONTROL_BACKGROUND, width=10, textvariable=self.canvas.millDiameter)
        self.millDiameter.pack(side='left', fill='x', expand=True, padx=5)
        tkExtra.Balloon.set(self.millDiameter, _("Mill Diameter"))
        self.addWidget(self.millDiameter)

        Label(self.simPanel, text=_("Opacity:")).pack(side='top', fill='x')

        Scale(
            self.simPanel,
            from_=0,
            to=100,
            resolution=1,
            variable=self.canvas.stockOpacity,
            orient='horizontal',
            command=self.changeStockOpacity
        ).pack(side='top', fill='x')

        self.millSelectedPathsOnly = Checkbutton(self.simPanel, text=_("Mill selected paths only"), variable=self.canvas.millSelectedPathsOnly)
        self.millSelectedPathsOnly.pack(side='top', fill='x', pady=10)

        b = Button(self.simPanel, text=_("Run simulation"), compound=LEFT, command=self.canvas.runSimulation, image=Utils.icons["start"], padx=2, pady=1)
        b.pack(side='top', fill='x', pady=10)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def changeStockOpacity(self, value):
        self.canvas.queueDraw()
    # ----------------------------------------------------------------------
    def updateStockSize(self):
        try:
            xmin = float(self.stockXmin.get())
            xmax = float(self.stockXmax.get())
            ymin = float(self.stockYmin.get())
            ymax = float(self.stockYmax.get())
            zmin = float(self.stockZmin.get())
            zmax = float(self.stockZmax.get())
        except:
            messagebox.showinfo("Warning", "Please fill in all the stock dimensions")
            return
        
        if xmax <= xmin:
            messagebox.showinfo("Warning", "Xmax must be greater than Xmin")
            return
        
        if ymax <= ymin:
            messagebox.showinfo("Warning", "Ymax must be greater than Ymin")
            return
        
        if zmax <= zmin:
            messagebox.showinfo("Warning", "Zmax must be greater than Zmin")
            return
        
        global STOCK_MIN_X, STOCK_MAX_X, STOCK_MIN_Y, STOCK_MAX_Y, STOCK_MIN_Z, STOCK_MAX_Z

        STOCK_MIN_X = xmin
        STOCK_MAX_X = xmax
        STOCK_MIN_Y = ymin
        STOCK_MAX_Y = ymax
        STOCK_MIN_Z = zmin
        STOCK_MAX_Z = zmax

        self.canvas.resetStock()
        self.canvas.fit2Screen()
    # ----------------------------------------------------------------------
    def addWidget(self, widget):
        self.app.widgets.append(widget)

    # ----------------------------------------------------------------------
    def loadConfig(self):
        global INSERT_COLOR, GANTRY_COLOR, MARGIN_COLOR, GRID_COLOR
        global ENABLE_COLOR, DISABLE_COLOR, SELECT_COLOR
        global SELECT2_COLOR, PROCESS_COLOR, MOVE_COLOR, RULER_COLOR
        global CAMERA_COLOR, PROBE_TEXT_COLOR, CANVAS_COLOR_UP, CANVAS_COLOR_DOWN
        global DRAW_TIME, AXES_TEXT_COLOR, RAPID_COLOR

        self.draw_axes.set(bool(int(Utils.getBool("Canvas", "axes", True))))
        self.draw_grid.set(bool(int(Utils.getBool("Canvas", "grid", True))))
        self.draw_margin.set(bool(int(Utils.getBool("Canvas", "margin", True))))
        self.draw_paths.set(bool(int(Utils.getBool("Canvas", "paths", True))))
        self.draw_rapid.set(bool(int(Utils.getBool("Canvas", "rapid", True))))
        self.draw_workarea.set(
            bool(int(Utils.getBool("Canvas", "workarea", True))))

        self.view.set(Utils.getStr("Canvas", "view", VIEWS[0]))

        DRAW_TIME = Utils.getInt("Canvas", "drawtime", DRAW_TIME)

        INSERT_COLOR = Utils.getStr("Color", "canvas.insert", INSERT_COLOR)
        GANTRY_COLOR = Utils.getStr("Color", "canvas.gantry", DEFAULT_GANTRY_COLOR)
        MARGIN_COLOR = Utils.getStr("Color", "canvas.margin", DEFAULT_MARGIN_COLOR)
        GRID_COLOR = Utils.getStr("Color", "canvas.grid", DEFAULT_GRID_COLOR)
        ENABLE_COLOR = Utils.getStr("Color", "canvas.enable", DEFAULT_ENABLE_COLOR)
        DISABLE_COLOR = Utils.getStr("Color", "canvas.disable", DEFAULT_DISABLE_COLOR)
        SELECT_COLOR = Utils.getStr("Color", "canvas.select", DEFAULT_SELECT_COLOR)
        SELECT2_COLOR = Utils.getStr("Color", "canvas.select2", DEFAULT_SELECT2_COLOR)
        PROCESS_COLOR = Utils.getStr("Color", "canvas.process", DEFAULT_PROCESS_COLOR)
        MOVE_COLOR = Utils.getStr("Color", "canvas.move", DEFAULT_MOVE_COLOR)
        RULER_COLOR = Utils.getStr("Color", "canvas.ruler", DEFAULT_RULER_COLOR)
        CAMERA_COLOR = Utils.getStr("Color", "canvas.camera", DEFAULT_CAMERA_COLOR)
        PROBE_TEXT_COLOR = Utils.getStr("Color", "canvas.probetext", DEFAULT_PROBE_TEXT_COLOR)
        CANVAS_COLOR_UP = Utils.getStr("Color", "canvas.backgroundUp", DEFAULT_CANVAS_COLOR_UP)
        CANVAS_COLOR_DOWN = Utils.getStr("Color", "canvas.backgroundDown", DEFAULT_CANVAS_COLOR_DOWN)
        AXES_TEXT_COLOR = Utils.getStr("Color", "canvas.axestext", DEFAULT_AXES_TEXT_COLOR)
        RAPID_COLOR = Utils.getStr("Color", "canvas.rapid", DEFAULT_RAPID_COLOR)

    def loadMillConfig(self):
        global MILL_TYPE, MILL_DIAMETER

        self.stockXmin.set(Utils.getFloat("Simulation", "xmin", STOCK_MIN_X))
        self.stockXmax.set(Utils.getFloat("Simulation", "xmax", STOCK_MAX_X))
        self.stockYmin.set(Utils.getFloat("Simulation", "ymin", STOCK_MIN_Y))
        self.stockYmax.set(Utils.getFloat("Simulation", "ymax", STOCK_MAX_Y))
        self.stockZmin.set(Utils.getFloat("Simulation", "zmin", STOCK_MIN_Z))
        self.stockZmax.set(Utils.getFloat("Simulation", "zmax", STOCK_MAX_Z))

        self.canvas.millType.set(Utils.getStr("Simulation", "milltype", MILL_TYPE))
        if self.canvas.millType.get() == '':
            self.canvas.millType.set("Flat")

        self.canvas.millDiameter.set(Utils.getFloat("Simulation", "milldiameter", MILL_DIAMETER))
        if self.canvas.millDiameter.get() == 0:
            self.canvas.millDiameter.set(6.0)

        self.canvas.stockOpacity.set(Utils.getInt("Simulation", "stockopacity", 100))
        if self.canvas.stockOpacity.get() == 0:
            self.canvas.stockOpacity.set(100)

        self.updateStockSize()

    # ----------------------------------------------------------------------
    def saveConfig(self):
        Utils.setInt("Canvas", "drawtime", DRAW_TIME)
        Utils.setStr("Canvas", "view", self.view.get())
        Utils.setBool("Canvas", "axes", self.draw_axes.get())
        Utils.setBool("Canvas", "grid", self.draw_grid.get())
        Utils.setBool("Canvas", "margin", self.draw_margin.get())
        Utils.setBool("Canvas", "probe", self.draw_probe.get())
        Utils.setBool("Canvas", "paths", self.draw_paths.get())
        Utils.setBool("Canvas", "rapid", self.draw_rapid.get())
        Utils.setBool("Canvas", "workarea", self.draw_workarea.get())

        # Save Canvas Colors
        global customColors

        for c in customColors:
            Utils.setStr("Color", c, globals()[customColors[c]["color"]])

        if not self.first_time_sim_shown:
            Utils.addSection("Simulation")
            
            Utils.setFloat("Simulation", "xmin", self.stockXmin.get())
            Utils.setFloat("Simulation", "xmax", self.stockXmax.get())
            Utils.setFloat("Simulation", "ymin", self.stockYmin.get())
            Utils.setFloat("Simulation", "ymax", self.stockYmax.get())
            Utils.setFloat("Simulation", "zmin", self.stockZmin.get())
            Utils.setFloat("Simulation", "zmax", self.stockZmax.get())
            Utils.setStr("Simulation", "milltype", self.canvas.millType.get())
            Utils.setFloat("Simulation", "milldiameter", self.canvas.millDiameter.get())
            Utils.setInt("Simulation", "stockopacity", self.canvas.stockOpacity.get())

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
            command=self.toggleDrawFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle display of paths (G1,G2,G3)"))
        b.pack(side=LEFT)

        b = Checkbutton(
            toolbar,
            image=Utils.icons["rapid"],
            indicatoron=False,
            variable=self.draw_rapid,
            command=self.toggleDrawFlag,
        )
        tkExtra.Balloon.set(b, _("Toggle display of rapid motion (G0)"))
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

        b = Button(toolbar, image=Utils.icons["refresh"],
                   command=self.canvas.updateAll)
        tkExtra.Balloon.set(b, _("Redraw display [Ctrl-R]"))
        b.pack(side=LEFT)

        b = Button(toolbar, image=Utils.icons["color"],
                   command=self.canvas.setCustomColors)
        tkExtra.Balloon.set(b, _("Set Canvas colors"))
        b.pack(side=LEFT)

        if (self.canvas.glslVersion == "1.20") and (not self.canvas.is_raspberry_pi()):
            b = Checkbutton(
                toolbar,
                image=Utils.icons["sim"],
                indicatoron=False,
                variable=self.show_sim,
                command=self.showSim
            )
            tkExtra.Balloon.set(b, _("Show 3D simulation. --- REQUIRES ABOUT 500MB OF FREE GPU MEMORY ---"))
            b.pack(side=LEFT)

        # -----------
        self.drawTime = tkExtra.Combobox(
            toolbar, width=3, background="White", command=self.drawTimeChange
        )
        tkExtra.Balloon.set(self.drawTime, _("Draw timeout in seconds"))
        self.drawTime.fill(
            ["inf", "1", "2", "3", "5", "10", "20", "30", "60", "120"])
        self.drawTime.set(DRAW_TIME)
        self.drawTime.pack(side=RIGHT)
        Label(toolbar, text=_("Timeout:")).pack(side=RIGHT)

    def showSim(self, value = None):
        if value is not None:
            self.canvas.set_mode(value)
            return
        
        if self.show_sim.get() == True:
            self.canvas.set_mode(CNCCanvas.MODE_SIM)
            self.simPanel.grid(row=1, column=0, sticky=NSEW)

            if self.first_time_sim_shown:
                self.loadMillConfig()
                self.first_time_sim_shown = False

        else:
            self.canvas.set_mode(CNCCanvas.MODE_CNC)
            self.simPanel.grid_forget()

        self.canvas.queueDraw()
        
    # ----------------------------------------------------------------------
    def redraw(self, event=None):
        self.canvas.reset()
        self.event_generate("<<ViewChange>>")

    # ----------------------------------------------------------------------
    def viewChange(self, a=None, b=None, c=None):
        view = VIEWS.index(self.view.get())

        self.canvas.MVMatrix = mat4x4(self.canvas.MVMatrix)

        if view == 0:
            self.canvas.MVMatrix = lookAt(
                vec3(0, 0, 1),
                vec3(0, 0, 0),
                vec3(0, 1, 0))
        elif view == 1:
            self.canvas.MVMatrix = lookAt(
                vec3(0, -1, 0),
                vec3(0, 0, 0),
                vec3(0, 0, 1))
        elif view == 2:
            self.canvas.MVMatrix = lookAt(
                vec3(1, 0, 0),
                vec3(0, 0, 0),
                vec3(0, 0, 1))
        elif view == 3:
            self.canvas.MVMatrix = lookAt(
                vec3(1, -1, 1),
                vec3(0, 0, 0),
                vec3(0, 0, 1))
        elif view == 4:
            self.canvas.MVMatrix = lookAt(
                vec3(-1, -1, 1),
                vec3(0, 0, 0),
                vec3(0, 0, 1))
        elif view == 5:
            self.canvas.MVMatrix = lookAt(
                vec3(-1, 1, 1),
                vec3(0, 0, 0),
                vec3(0, 0, 1))
        
        #self.event_generate("<<ViewChange>>")
        self.canvas.fit2Screen()

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
    def toggleDrawFlag(self):
        self.canvas.draw_axes = self.draw_axes.get()
        self.canvas.draw_grid = self.draw_grid.get()
        self.canvas.draw_margin = self.draw_margin.get()
        self.canvas.draw_probe = self.draw_probe.get()
        self.canvas.draw_paths = self.draw_paths.get()
        self.canvas.draw_rapid = self.draw_rapid.get()
        self.canvas.draw_workarea = self.draw_workarea.get()
        self.event_generate("<<ViewChange>>")

    # ----------------------------------------------------------------------
    def drawAxes(self, value=None):
        if value is not None:
            self.draw_axes.set(value)
        self.canvas.draw_axes = self.draw_axes.get()
        self.canvas.queueDraw()

    # ----------------------------------------------------------------------
    def drawGrid(self, value=None):
        if value is not None:
            self.draw_grid.set(value)
        self.canvas.draw_grid = self.draw_grid.get()
        self.canvas.updateGrid()

    # ----------------------------------------------------------------------
    def drawMargin(self, value=None):
        if value is not None:
            self.draw_margin.set(value)
        self.canvas.draw_margin = self.draw_margin.get()
        self.canvas.updateMargin()

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
        self.canvas.updateWorkArea()

    # ----------------------------------------------------------------------
    def drawCamera(self, value=None):
        if value is not None:
            self.draw_camera.set(value)
        if self.draw_camera.get():
            self.canvas.cameraOn()
        else:
            self.canvas.cameraOff()
            self.canvas.queueDraw()

    # ----------------------------------------------------------------------
    def drawTimeChange(self):
        global DRAW_TIME
        try:
            DRAW_TIME = int(self.drawTime.get())
        except ValueError:
            DRAW_TIME = 5 * 60
        self.viewChange()

class CustomColorsDialog(Toplevel):
    def __init__(self, parent, canvas):
        super().__init__(parent)

        global customColors

        self.canvas = canvas
        self.title("Canvas Colors")

        # Make it modal
        self.transient(parent)     # keep on top of parent
        self.grab_set()            # block interaction with parent
        
        self.buttons = {}

        # List of customizable colors
        for c in customColors:
            item = Frame(self)
            item.pack(fill="x", padx=10, pady=2)
            labelText = customColors[c]["description"]
            if customColors[c]["canBeBlank"]:
                labelText = labelText + " - Right click to unset"
            Label(item, text=labelText).pack(side="left")
            buttonFrame = Frame(item, width=16, height=16)
            buttonFrame.pack_propagate(False)
            buttonFrame.pack(side="right")
            currentColor = globals()[customColors[c]["color"]]
            # We use labels as buttons. Buttons have some rendering issues when updating colors
            if currentColor != "":
                self.buttons[c] = Label(buttonFrame, bg=currentColor, height=16, width=16)
            else:
                self.buttons[c] = Label(buttonFrame, bg="White", text="x")
            self.buttons[c].pack(fill="both")
            self.buttons[c].bind("<Button-1>", lambda event, var=c: self.colorLeftClicked(var))
            if customColors[c]["canBeBlank"]:
                self.buttons[c].bind("<Button-3>", lambda event, var=c: self.colorRightClicked(var))

        Button(self, text="Set Default Colors", command=self.setDefaultColors).pack(pady=10)
        Button(self, text="Close", command=self.destroy).pack(pady=10)

        # Optional: center the window
        self.update_idletasks()
        x = parent.winfo_rootx() + 50
        y = parent.winfo_rooty() + 50
        self.geometry(f"+{x}+{y}")
    
    def colorLeftClicked(self, varName):
        global customColors

        currentColor = globals()[customColors[varName]["color"]]

        if currentColor != "":
            initialColor = currentColor
        else:
            initialColor = "Black"

        rgb, color = tkExtra.askcolor(title="Color",
            initialcolor=initialColor,
            parent = self
            )
    
        if color is not None:
            globals()[customColors[varName]["color"]] = color
            self.buttons[varName].config(bg=color)
            self.buttons[varName].config(text="")
            self.canvas.queueDraw()
    
    def colorRightClicked(self, varName):
        global customColors

        currentColor = globals()[customColors[varName]["color"]]
        globals()[customColors[varName]["color"]] = ""
        self.buttons[varName].config(bg="White")
        self.buttons[varName].config(text="x")

        self.canvas.queueDraw()

    def setDefaultColors(self):
        global customColors

        for c in customColors:
            defaultColor = globals()["DEFAULT_" + customColors[c]["color"]]
            globals()[customColors[c]["color"]] = defaultColor

            if defaultColor != "":
                self.buttons[c].config(bg=defaultColor)
            else:
                self.buttons[c].config(bg="White")
                self.buttons[c].config(text="x")
        
        self.canvas.queueDraw()
