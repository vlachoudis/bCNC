# $Id$
#
# Author:    Filippo Rivato
# Date: December 2015

from CNC import CNC, Block
from ToolsPage import Plugin
from PIL.FontFile import FontFile
from shxparser.shxparser import ShxFont,ShxPath
from svgelements import Arc
__author__ = "Filippo Rivato"
__email__ = "f.rivato@gmail.com"

__name__ = "Text"
__version__ = "0.0.2" #0.0.2 on 2023 03 05 : SHX font import

# =============================================================================
# Text class
# =============================================================================
class Text:
    def __init__(self, name="Text"):
        self.name = name


# =============================================================================
# Create Text
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Create text using a ttf font")

    def __init__(self, master):
        Plugin.__init__(self, master, "Text")
        self.icon = "text"
        self.group = "Generator"

        self.variables = [
            ("name", "db", "", _("Name")),
            ("Text", "text", "Write this!", _("Text to generate"),"enter here text to generate"),
            ("Depth", "mm", 0.0, _("Working Depth"),"enter here depth (negative inside material)"),
            ("FontSize", "mm", 10.0, _("Font size"),"enter here font height"),
            ("FontFile", "file", "", _("Font file"),"pick the ttf or shx font"),
            ("Closed", "bool", True, _("Close Contours"),"only for ttf fonts"),
            ("ImageToAscii", "file", "", _("Image to Ascii")),
            ("CharsWidth", "int", 80, _("Image chars width"),"for ttf fonts only"),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):

        # Get inputs
        fontSize = self.fromMm("FontSize")
        depth = self.fromMm("Depth")
        textToWrite = self["Text"]
        fontFileName = self["FontFile"]
        closed = self["Closed"]
        imageFileName = self["ImageToAscii"]
        charsWidth = self["CharsWidth"]

        # Check parameters!!!
        if fontSize <= 0:
            app.setStatus(_("Text abort: please input a Font size > 0"))
            return
        if fontFileName == "":
            app.setStatus(_("Text abort: please select a font file"))
            return
        if imageFileName != "":
            try:
                textToWrite = self.asciiArt(imageFileName, charsWidth)
            except Exception:
                pass
        if textToWrite == "":
            textToWrite = "Nel mezzo del cammin di nostra vita..."
            return

        # Init blocks
        self.blocks = []
        n = self["name"]
        if not n or n == "default":
            n = "Text"
        block = Block(n)
        if "\n" in textToWrite:
            block.append("(Text:)")
            for line in textToWrite.splitlines():
                block.append(f"({line})")
        else:
            block.append(f"(Text: {textToWrite})")
        if fontFileName.upper().endswith(".SHX") :
            try :
                shx = ShxFont(fontFileName)
                paths = ShxPath()
                shx.render(paths, textToWrite, font_size=fontSize)
                self.shxtoGcode(paths.path,block,depth,app)
            except Exception as exc :
                app.setStatus(_("Text abort: That's embarrassing, "+ "I can't read this font file!"))
                return
        else :
            self.ttftoGcode(fontFileName,textToWrite,closed,fontSize,depth,block,app)

#     (x0,y0) -- Move to Position.
#     ((x0,y0), (x1, y1)) --- Straight Line start->end
#     ((x0,y0), (cx, cy), (x1, y1)) --- Arc start->control->end where control is a point on the arc that starts at start and ends at end.

    def shxtoGcode(self,path,block,depth,app):
        block.append(CNC.zsafe())
        block.append(CNC.gcode(1, [("f", CNC.vars["cutfeed"])]))
        for element in path:
            if element is None :
                break
            if len (element) == 2 :
                block.append("( ---------- cut-here ---------- )")
                block.append(CNC.zsafe())
                block.append(CNC.grapid(element[0] , element[1]))
                block.append(CNC.zenter(depth))
                block.append(CNC.gcode(1, [("f", CNC.vars["cutfeed"])]))
            elif len(element)==4 :
                block.append(CNC.gline(element[2],element[3]))
            elif len(element)==6 : 
                x0 = element[0]
                y0 = element[1]
                x1 = element[2]
                y1= element[3]
                x2 = element[4]
                y2 = element[5]
                arc = Arc(start=(x0, y0), control=(x1, y1), end=(x2, y2))
                step = 1./10.
                t = 0
                for i in range(10):
                    p1 = arc.point(t)
                    p2 = arc.point(t+step)
                    t += step
                    block.append(CNC.gline(p2[0],p2[1]))
        # Gcode Zsafe
        block.append(CNC.zsafe())
        self.blocks.append(block)
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, self.blocks, "Text")
        app.refresh()
        app.setStatus("Generated Text")
        
    def ttftoGcode(self,fontFileName,textToWrite,closed,fontSize,depth,block,app):
        try:
            import ttf

            font = ttf.TruetypeInfo(fontFileName)
        except ImportError:
            app.setStatus(
                _("Text abort: That's embarrassing, "
                  + "I can't read this font file!")
            )
            return
        cmap = font.get_character_map()

        adv = font.get_glyph_advances()

        xOffset = 0
        yOffset = 0
        for c in textToWrite:
            # New line
            if c == "\n":
                xOffset = 0.0
                yOffset -= 1  # offset for new line
                continue

            if c in cmap:
                glyphIndx = cmap[c]

                # Get glyph contours as line segments and draw them
                gc = font.get_glyph_contours(glyphIndx, closed)
                if not gc:
                    gc = font.get_glyph_contours(
                        0, closed
                    )  # standard glyph for missing glyphs (complex glyph)
                if (
                    gc and not c == " "
                ):  # FIXME: for some reason space is not mapped correctly!!!
                    self.writeGlyphContour(
                        block, font, gc, fontSize, depth, xOffset, yOffset
                    )

                if glyphIndx < len(adv):
                    xOffset += adv[glyphIndx]
                else:
                    xOffset += 1

        # Remember to close Font
        font.close()

        # Gcode Zsafe
        block.append(CNC.zsafe())

        self.blocks.append(block)
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, self.blocks, "Text")
        app.refresh()
        app.setStatus("Generated Text")

    # Write GCode from glyph contours
    def writeGlyphContour(
            self, block, font, contours, fontSize, depth, xO, yO):
        scale = fontSize / font.header.units_per_em
        xO = xO * fontSize
        yO = yO * fontSize
        for cont in contours:
            block.append("( ---------- cut-here ---------- )")
            block.append(CNC.zsafe())
            block.append(
                CNC.grapid(xO + cont[0].x * scale, yO + cont[0].y * scale))
            block.append(CNC.zenter(depth))
            block.append(CNC.gcode(1, [("f", CNC.vars["cutfeed"])]))
            for p in cont:
                block.append(CNC.gline(xO + p.x * scale, yO + p.y * scale))

    def image_to_ascii(self, image):
        ascii_chars = ["#", "A", "@", "%", "S", "+", "<", "*", ":", ",", "."]
        image_as_ascii = []
        all_pixels = list(image.getdata())
        for pixel_value in all_pixels:
            index = pixel_value / 25  # 0 - 10
            image_as_ascii.append(ascii_chars[index])
        return image_as_ascii

    def asciiArt(self, filePath, new_width=80):
        from PIL import Image

        img = Image.open(filePath)
        width, height = img.size
        new_height = int((height * new_width) / width)
        new_image = img.resize((new_width, new_height))
        new_image = new_image.convert("L")  # convert to grayscale

        # now that we have a grayscale image with some fixed width we have
        # to convert every pixel
        # to the appropriate ascii character from "ascii_chars"
        img_as_ascii = self.image_to_ascii(new_image)
        img_as_ascii = "".join(ch for ch in img_as_ascii)
        output = ""
        for c in range(0, len(img_as_ascii), new_width):
            output += img_as_ascii[c:c + new_width] + "\n"
        return output
