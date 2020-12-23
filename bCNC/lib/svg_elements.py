# -*- coding: ISO-8859-1 -*-

import re

try:
    from collections.abc import MutableSequence  # noqa
except ImportError:
    from collections import MutableSequence  # noqa
from copy import copy
from math import *

from xml.etree.ElementTree import iterparse

try:
    from math import tau
except ImportError:
    tau = pi * 2

"""
The path elements are derived from regebro's svg.path project ( https://github.com/regebro/svg.path ) with
some of the math from mathandy's svgpathtools project ( https://github.com/mathandy/svgpathtools ).

The goal is to provide svg like path objects and structures. The svg standard 1.1 and elements of 2.0 will
be used to provide much of the decisions within path objects. Such that if there is a question on
implementation if the SVG documentation has a methodology it should be used.

Though not required the SVGImage class acquires new functionality if provided with PIL/Pillow as an import
and the Arc can do exact arc calculations if scipy is installed.
"""

SVGELEMENTS_VERSION = "1.4.1"

MIN_DEPTH = 5
ERROR = 1e-12

max_depth = 0

# SVG STATIC VALUES
DEFAULT_PPI = 96.0
SVG_NAME_TAG = 'svg'
SVG_ATTR_VERSION = 'version'
SVG_VALUE_VERSION = '1.1'
SVG_ATTR_XMLNS = 'xmlns'
SVG_VALUE_XMLNS = 'http://www.w3.org/2000/svg'
SVG_ATTR_XMLNS_LINK = 'xmlns:xlink'
SVG_VALUE_XLINK = 'http://www.w3.org/1999/xlink'
SVG_ATTR_XMLNS_EV = 'xmlns:ev'
SVG_VALUE_XMLNS_EV = 'http://www.w3.org/2001/xml-events'

XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
SVG_HREF = "href"
SVG_ATTR_WIDTH = 'width'
SVG_ATTR_HEIGHT = 'height'
SVG_ATTR_VIEWBOX = 'viewBox'
SVG_VIEWBOX_TRANSFORM = 'viewbox_transform'
SVG_TAG_PATH = 'path'
SVG_TAG_GROUP = 'g'
SVG_TAG_RECT = 'rect'
SVG_TAG_CIRCLE = 'circle'
SVG_TAG_ELLIPSE = 'ellipse'
SVG_TAG_LINE = 'line'
SVG_TAG_POLYLINE = 'polyline'
SVG_TAG_POLYGON = 'polygon'
SVG_TAG_TEXT = 'text'
SVG_TAG_TSPAN = 'tspan'
SVG_TAG_IMAGE = 'image'
SVG_TAG_DESC = 'desc'
SVG_TAG_TITLE = 'title'
SVG_TAG_METADATA = 'metadata'
SVG_TAG_STYLE = 'style'
SVG_TAG_DEFS = 'defs'
SVG_TAG_USE = 'use'
SVG_TAG_CLIPPATH = 'clipPath'
SVG_TAG_PATTERN = 'pattern'

SVG_STRUCT_ATTRIB = 'attributes'
SVG_ATTR_ID = 'id'
SVG_ATTR_DATA = 'd'
SVG_ATTR_DISPLAY = 'display'
SVG_ATTR_COLOR = 'color'
SVG_ATTR_FILL = 'fill'
SVG_ATTR_FILL_OPACITY = 'fill-opacity'
SVG_ATTR_STROKE = 'stroke'
SVG_ATTR_STROKE_OPACITY = 'stroke-opacity'
SVG_ATTR_STROKE_WIDTH = 'stroke-width'
SVG_ATTR_TRANSFORM = 'transform'
SVG_ATTR_STYLE = 'style'
SVG_ATTR_CLASS = 'class'
SVG_ATTR_CLIP_PATH = 'clip-path'
SVG_ATTR_CLIP_RULE = 'clip-rule'
SVG_ATTR_CLIP_UNIT_TYPE = 'clipPathUnits'
SVG_ATTR_CENTER_X = 'cx'
SVG_ATTR_CENTER_Y = 'cy'
SVG_ATTR_RADIUS_X = 'rx'
SVG_ATTR_RADIUS_Y = 'ry'
SVG_ATTR_RADIUS = 'r'
SVG_ATTR_POINTS = 'points'
SVG_ATTR_PRESERVEASPECTRATIO = 'preserveAspectRatio'
SVG_ATTR_X = 'x'
SVG_ATTR_Y = 'y'
SVG_ATTR_X0 = 'x0'
SVG_ATTR_Y0 = 'y0'
SVG_ATTR_X1 = 'x1'
SVG_ATTR_Y1 = 'y1'
SVG_ATTR_X2 = 'x2'
SVG_ATTR_Y2 = 'y2'
SVG_ATTR_DX = 'dx'
SVG_ATTR_DY = 'dy'
SVG_ATTR_TAG = 'tag'
SVG_ATTR_FONT = 'font'
SVG_ATTR_FONT_FAMILY = 'font-family'  # Serif, sans-serif, cursive, fantasy, monospace
SVG_ATTR_FONT_FACE = 'font-face'
SVG_ATTR_FONT_SIZE = 'font-size'
SVG_ATTR_FONT_WEIGHT = 'font-weight'  # normal, bold, bolder, lighter, 100-900
SVG_ATTR_TEXT_ANCHOR = 'text-anchor'
SVG_ATTR_PATTERN_CONTENT_UNITS = "patternContentUnits"
SVG_ATTR_PATTERN_TRANSFORM = "patternTransform"
SVG_ATTR_PATTERN_UNITS = "patternUnits"

SVG_ATTR_VECTOR_EFFECT = 'vector-effect'

SVG_UNIT_TYPE_USERSPACEONUSE = 'userSpaceOnUse'
SVG_UNIT_TYPE_OBJECTBOUNDINGBOX = 'objectBoundingBox'

SVG_RULE_NONZERO = 'nonzero'
SVG_RULE_EVENODD = 'evenodd'

SVG_TRANSFORM_MATRIX = 'matrix'
SVG_TRANSFORM_TRANSLATE = 'translate'
SVG_TRANSFORM_SCALE = 'scale'
SVG_TRANSFORM_ROTATE = 'rotate'
SVG_TRANSFORM_SKEW_X = 'skewx'
SVG_TRANSFORM_SKEW_Y = 'skewy'
SVG_TRANSFORM_SKEW = 'skew'
SVG_TRANSFORM_TRANSLATE_X = 'translatex'
SVG_TRANSFORM_TRANSLATE_Y = 'translatey'
SVG_TRANSFORM_SCALE_X = 'scalex'
SVG_TRANSFORM_SCALE_Y = 'scaley'

SVG_VALUE_NONE = 'none'
SVG_VALUE_CURRENT_COLOR = 'currentColor'

SVG_VALUE_NON_SCALING_STROKE = 'non-scaling-stroke'

PATTERN_WS = r'[\s\t\n]*'
PATTERN_COMMA = r'(?:\s*,\s*|\s+|(?=-))'
PATTERN_COMMAWSP = r'[ ,\t\n\x09\x0A\x0C\x0D]+'
PATTERN_FLOAT = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'
PATTERN_LENGTH_UNITS = 'cm|mm|Q|in|pt|pc|px|em|cx|ch|rem|vw|vh|vmin|vmax'
PATTERN_ANGLE_UNITS = 'deg|grad|rad|turn'
PATTERN_TIME_UNITS = 's|ms'
PATTERN_FREQUENCY_UNITS = 'Hz|kHz'
PATTERN_RESOLUTION_UNITS = 'dpi|dpcm|dppx'
PATTERN_PERCENT = '%'
PATTERN_TRANSFORM = SVG_TRANSFORM_MATRIX + '|' \
                    + SVG_TRANSFORM_TRANSLATE + '|' \
                    + SVG_TRANSFORM_TRANSLATE_X + '|' \
                    + SVG_TRANSFORM_TRANSLATE_Y + '|' \
                    + SVG_TRANSFORM_SCALE + '|' \
                    + SVG_TRANSFORM_SCALE_X + '|' \
                    + SVG_TRANSFORM_SCALE_Y + '|' \
                    + SVG_TRANSFORM_ROTATE + '|' \
                    + SVG_TRANSFORM_SKEW + '|' \
                    + SVG_TRANSFORM_SKEW_X + '|' \
                    + SVG_TRANSFORM_SKEW_Y
PATTERN_TRANSFORM_UNITS = PATTERN_LENGTH_UNITS + '|' \
                          + PATTERN_ANGLE_UNITS + '|' \
                          + PATTERN_PERCENT

REGEX_IRI = re.compile('url\(#?(.*)\)')
REGEX_FLOAT = re.compile(PATTERN_FLOAT)
REGEX_COORD_PAIR = re.compile('(%s)%s(%s)' % (PATTERN_FLOAT, PATTERN_COMMA, PATTERN_FLOAT))
REGEX_TRANSFORM_TEMPLATE = re.compile('(?u)(%s)%s\(([^)]+)\)' % (PATTERN_TRANSFORM, PATTERN_WS))
REGEX_TRANSFORM_PARAMETER = re.compile('(%s)%s(%s)?' % (PATTERN_FLOAT, PATTERN_WS, PATTERN_TRANSFORM_UNITS))
REGEX_COLOR_HEX = re.compile(r'^#?([0-9A-Fa-f]{3,8})$')
REGEX_COLOR_RGB = re.compile(
    r'rgba?\(\s*(%s)\s*,\s*(%s)\s*,\s*(%s)\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_COLOR_RGB_PERCENT = re.compile(
    r'rgba?\(\s*(%s)%%\s*,\s*(%s)%%\s*,\s*(%s)%%\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_COLOR_HSL = re.compile(
    r'hsla?\(\s*(%s)\s*,\s*(%s)%%\s*,\s*(%s)%%\s*(?:,\s*(%s)\s*)?\)' % (
        PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT, PATTERN_FLOAT))
REGEX_LENGTH = re.compile('(%s)([A-Za-z%%]*)' % PATTERN_FLOAT)
REGEX_CSS_STYLE = re.compile(r'([^{]+)\s*\{\s*([^}]+)\s*\}')
REGEX_CSS_FONT = re.compile(
    r'(?:(normal|italic|oblique)\s|(normal|small-caps)\s|(normal|bold|bolder|lighter|\d{3})\s|(normal|ultra-condensed|extra-condensed|condensed|semi-condensed|semi-expanded|expanded|extra-expanded|ultra-expanded)\s)*\s*(xx-small|x-small|small|medium|large|x-large|xx-large|larger|smaller|\d+(?:em|pt|pc|px|%))(?:/(xx-small|x-small|small|medium|large|x-large|xx-large|larger|smaller|\d+(?:em|pt|pc|px|%)))?\s*(.*),?\s+(serif|sans-serif|cursive|fantasy|monospace);?')

svg_parse = [
    ('COMMAND', r'[MmZzLlHhVvCcSsQqTtAa]'),
    ('SKIP', PATTERN_COMMAWSP)
]
svg_re = re.compile('|'.join('(?P<%s>%s)' % pair for pair in svg_parse))
num_parse = [
    ('FLOAT', PATTERN_FLOAT),
    ('CLOSE', r'[Zz]'),
    ('SKIP', PATTERN_COMMAWSP)
]
num_re = re.compile('|'.join('(?P<%s>%s)' % pair for pair in num_parse))
flag_parse = [
    ('FLAG', r'[01]'),
    ('SKIP', PATTERN_COMMAWSP)
]
flag_re = re.compile('|'.join('(?P<%s>%s)' % pair for pair in flag_parse))


class SVGLexicalParser:
    def __init__(self):
        self.parser = None
        self.pathd = None
        self.pos = 0
        self.limit = 0
        self.inline_close = None

    def _command(self):
        while self.pos < self.limit:
            match = svg_re.match(self.pathd, self.pos)
            if match is None:
                return None  # Did not match at command sequence.
            self.pos = match.end()
            kind = match.lastgroup
            if kind == 'SKIP':
                continue
            return match.group()
        return None

    def _more(self):
        while self.pos < self.limit:
            match = num_re.match(self.pathd, self.pos)
            if match is None:
                return False
            kind = match.lastgroup
            if kind == 'CLOSE':
                self.inline_close = match.group()
                return False
            if kind == 'SKIP':
                # move skipped elements forward.
                self.pos = match.end()
                continue
            return True
        return None

    def _number(self):
        while self.pos < self.limit:
            match = num_re.match(self.pathd, self.pos)
            if match is None:
                break  # No more matches.
            kind = match.lastgroup
            if kind == 'CLOSE':
                # Inline Close
                self.inline_close = match.group()
                return None
            self.pos = match.end()
            if kind == 'SKIP':
                continue
            return float(match.group())
        return None

    def _flag(self):
        while self.pos < self.limit:
            match = flag_re.match(self.pathd, self.pos)
            if match is None:
                break  # No more matches.
            self.pos = match.end()
            kind = match.lastgroup
            if kind == 'SKIP':
                continue
            return bool(int(match.group()))
        return None

    def _coord(self):
        x = self._number()
        if x is None:
            return None
        y = self._number()
        if y is None:
            raise ValueError
        return x, y

    def _rcoord(self):
        position = self._coord()
        if position is None:
            return None
        current_pos = self.parser.current_point
        if current_pos is None:
            return position
        return position[0] + current_pos.x, position[1] + current_pos.y

    def parse(self, parser, pathd):
        self.parser = parser
        self.parser.start()
        self.pathd = pathd
        self.pos = 0
        self.limit = len(pathd)
        while True:
            cmd = self._command()
            if cmd is None:
                return
            elif cmd == 'z' or cmd == 'Z':
                if self._more():
                    raise ValueError
                self.parser.closed(relative=cmd.islower())
                self.inline_close = None
                continue
            elif cmd == 'm':
                if not self._more():
                    raise ValueError
                coord = self._rcoord()
                self.parser.move(coord, relative=True)
                while self._more():
                    coord = self._rcoord()
                    self.parser.line(coord, relative=True)
            elif cmd == 'M':
                if not self._more():
                    raise ValueError
                coord = self._coord()
                self.parser.move(coord, relative=False)
                while self._more():
                    coord = self._coord()
                    self.parser.line(coord, relative=False)
            elif cmd == 'l':
                while True:
                    coord = self._rcoord()
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.line(coord, relative=True)
                    if not self._more():
                        break
            elif cmd == 'L':
                while True:
                    coord = self._coord()
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.line(coord, relative=False)
                    if not self._more():
                        break
            elif cmd == 't':
                while True:
                    coord = self._rcoord()
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.smooth_quad(coord, relative=True)
                    if not self._more():
                        break
            elif cmd == 'T':
                while True:
                    coord = self._coord()
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.smooth_quad(coord, relative=False)
                    if not self._more():
                        break
            elif cmd == 'h':
                while True:
                    value = self._number()
                    self.parser.horizontal(value, relative=True)
                    if not self._more():
                        break
            elif cmd == 'H':
                while True:
                    value = self._number()
                    self.parser.horizontal(value, relative=False)
                    if not self._more():
                        break
            elif cmd == 'v':
                while True:
                    value = self._number()
                    self.parser.vertical(value, relative=True)
                    if not self._more():
                        break
            elif cmd == 'V':
                while self._more():
                    value = self._number()
                    self.parser.vertical(value, relative=False)
            elif cmd == 'c':
                while True:
                    coord1, coord2, coord3 = self._rcoord(), self._rcoord(), self._rcoord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    if coord3 is None:
                        coord3 = self.inline_close
                        if coord3 is None:
                            raise ValueError
                    self.parser.cubic(coord1, coord2, coord3, relative=True)
                    if not self._more():
                        break
            elif cmd == 'C':
                while True:
                    coord1, coord2, coord3 = self._coord(), self._coord(), self._coord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    if coord3 is None:
                        coord3 = self.inline_close
                        if coord3 is None:
                            raise ValueError
                    self.parser.cubic(coord1, coord2, coord3, relative=False)
                    if not self._more():
                        break
            elif cmd == 'q':
                while True:
                    coord1, coord2 = self._rcoord(), self._rcoord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    self.parser.quad(coord1, coord2, relative=True)
                    if not self._more():
                        break
            elif cmd == 'Q':
                while True:
                    coord1, coord2 = self._coord(), self._coord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    self.parser.quad(coord1, coord2, relative=False)
                    if not self._more():
                        break
            elif cmd == 's':
                while True:
                    coord1, coord2 = self._rcoord(), self._rcoord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    self.parser.smooth_cubic(coord1, coord2, relative=True)
                    if not self._more():
                        break
            elif cmd == 'S':
                while True:
                    coord1, coord2 = self._coord(), self._coord()
                    if coord1 is None:
                        coord1 = self.inline_close
                        if coord1 is None:
                            raise ValueError
                    if coord2 is None:
                        coord2 = self.inline_close
                        if coord2 is None:
                            raise ValueError
                    self.parser.smooth_cubic(coord1, coord2, relative=False)
                    if not self._more():
                        break
            elif cmd == 'a':
                while self._more():
                    rx, ry, rotation, arc, sweep, coord = \
                        self._number(), self._number(), self._number(), self._flag(), self._flag(), self._rcoord()
                    if sweep is None:
                        raise ValueError
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.arc(rx, ry, rotation, arc, sweep, coord, relative=True)
            elif cmd == 'A':
                while self._more():
                    rx, ry, rotation, arc, sweep, coord = \
                        self._number(), self._number(), self._number(), self._flag(), self._flag(), self._coord()
                    if coord is None:
                        coord = self.inline_close
                        if coord is None:
                            raise ValueError
                    self.parser.arc(rx, ry, rotation, arc, sweep, coord, relative=False)
        self.parser.end()


class Length(object):
    """
    SVGLength as used in SVG

    Length are lazy solving values. Several conversion values are typically unknown by default and length simply
    stores that ambiguity. So we can have a length of 50% and without calling .value(relative_length=3000) it will
    simply store as 50%. Likewise you can have discrete values like 30cm or 20in which have knowable discrete values
    but are not knowable in pixels unless a PPI value is supplied. We can say .value(relative_length=30cm, PPI=96) and
    solve this for a value like 12%. We can also convert values between knowable lengths. So 30cm in 300mm regardless
    whether we know how to convert this to pixels. 0% is 0 in any units or relative values. We can convert pixels to
    pc and pt without issue. We can convert vh, vw, vmax, vmin values if we know viewbox values. We can convert em
    values if we know the font_size. We can add values together if they are convertible units. Length("20in") + "3cm".

    If .value() cannot solve for the value with the given information then it will return a Length value. If it can
    be solved it will return a float.
    """

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            value = args[0]
            if value is None:
                self.amount = None
                self.units = None
                return
            s = str(value)
            for m in REGEX_LENGTH.findall(s):
                self.amount = float(m[0])
                self.units = m[1]
                return
        elif len(args) == 2:
            self.amount = args[0]
            self.units = args[1]
            return
        self.amount = 0.0
        self.units = ''

    def __float__(self):
        if self.amount is None:
            return None
        if self.units == 'pt':
            return self.amount * 1.3333
        elif self.units == 'pc':
            return self.amount * 16.0
        return self.amount

    def __imul__(self, other):
        if isinstance(other, (int, float)):
            self.amount *= other
            return self
        if self.amount == 0.0:
            return 0.0
        if isinstance(other, str):
            other = Length(other)
        if isinstance(other, Length):
            if other.amount == 0.0:
                self.amount = 0.0
                return self
            if self.units == other.units:
                self.amount *= other.amount
                return self
            if self.units == '%':
                self.units = other.units
                self.amount = self.amount * other.amount / 100.0
                return self
            elif other.units == '%':
                self.amount = self.amount * other.amount / 100.0
                return self
        raise ValueError

    def __iadd__(self, other):
        if not isinstance(other, Length):
            other = Length(other)
        if self.units == other.units:
            self.amount += other.amount
            return self
        if self.amount == 0:
            self.amount = other.amount
            self.units = other.units
            return self
        if other.amount == 0:
            return self
        if self.units == 'px' or self.units == '':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount
            elif other.units == 'pt':
                self.amount += other.amount * 1.3333
            elif other.units == 'pc':
                self.amount += other.amount * 16.0
            else:
                raise ValueError
            return self
        if self.units == 'pt':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount / 1.3333
            elif other.units == 'pc':
                self.amount += other.amount * 12.0
            else:
                raise ValueError
            return self
        elif self.units == 'pc':
            if other.units == 'px' or other.units == '':
                self.amount += other.amount / 16.0
            elif other.units == 'pt':
                self.amount += other.amount / 12.0
            else:
                raise ValueError
            return self
        elif self.units == 'cm':
            if other.units == 'mm':
                self.amount += other.amount / 10.0
            elif other.units == 'in':
                self.amount += other.amount / 0.393701
            else:
                raise ValueError
            return self
        elif self.units == 'mm':
            if other.units == 'cm':
                self.amount += other.amount * 10.0
            elif other.units == 'in':
                self.amount += other.amount / 0.0393701
            else:
                raise ValueError
            return self
        elif self.units == 'in':
            if other.units == 'cm':
                self.amount += other.amount * 0.393701
            elif other.units == 'mm':
                self.amount += other.amount * 0.0393701
            else:
                raise ValueError
            return self
        raise ValueError('%s units were not determined.' % self.units)

    def __abs__(self):
        c = self.__copy__()
        c.amount = abs(c.amount)
        return c

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            c = self.__copy__()
            c.amount /= other
            return c
        if self.amount == 0.0:
            return 0.0
        if isinstance(other, str):
            other = Length(other)
        if isinstance(other, Length):
            if self.units == other.units:
                q = self.amount / other.amount
                return q  # no units
        if self.units == 'px' or self.units == '':
            if other.units == 'px' or other.units == '':
                return self.amount / other.amount
            elif other.units == 'pt':
                return self.amount / (other.amount * 1.3333)
            elif other.units == 'pc':
                return self.amount / (other.amount * 16.0)
            else:
                raise ValueError
        if self.units == 'pt':
            if other.units == 'px' or other.units == '':
                return self.amount / (other.amount / 1.3333)
            elif other.units == 'pc':
                return self.amount / (other.amount * 12.0)
            else:
                raise ValueError
        if self.units == 'pc':
            if other.units == 'px' or other.units == '':
                return self.amount / (other.amount / 16.0)
            elif other.units == 'pt':
                return self.amount / (other.amount / 12.0)
            else:
                raise ValueError
        if self.units == 'cm':
            if other.units == 'mm':
                return self.amount / (other.amount / 10.0)
            elif other.units == 'in':
                return self.amount / (other.amount / 0.393701)
            else:
                raise ValueError
        if self.units == 'mm':
            if other.units == 'cm':
                return self.amount / (other.amount * 10.0)
            elif other.units == 'in':
                return self.amount / (other.amount / 0.0393701)
            else:
                raise ValueError
        if self.units == 'in':
            if other.units == 'cm':
                return self.amount / (other.amount * 0.393701)
            elif other.units == 'mm':
                return self.amount / (other.amount * 0.0393701)
            else:
                raise ValueError
        raise ValueError

    __floordiv__ = __truediv__
    __div__ = __truediv__

    def __lt__(self, other):
        return (self - other).amount < 0.0

    def __le__(self, other):
        return (self - other).amount <= 0.0

    def __gt__(self, other):
        return (self - other).amount > 0.0

    def __ge__(self, other):
        return (self - other).amount >= 0.0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __add__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        c = self.__copy__()
        c += other
        return c

    __radd__ = __add__

    def __mul__(self, other):
        c = copy(self)
        c *= other
        return c

    def __rdiv__(self, other):
        c = copy(self)
        c *= 1.0 / other.amount
        return c

    def __neg__(self):
        s = self.__copy__()
        s.amount = -s.amount
        return s

    def __isub__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        self += -other
        return self

    def __sub__(self, other):
        s = self.__copy__()
        s -= other
        return s

    def __rsub__(self, other):
        if isinstance(other, (str, float, int)):
            other = Length(other)
        return (-self) + other

    def __copy__(self):
        return Length(self.amount, self.units)

    __rmul__ = __mul__

    def __repr__(self):
        return 'Length(\'%s\')' % (str(self))

    def __str__(self):
        if self.amount is None:
            return SVG_VALUE_NONE
        return '%s%s' % (Length.str(self.amount), self.units)

    def __eq__(self, other):
        if other is None:
            return False
        s = self.in_pixels()
        if isinstance(other, (float, int)):
            if s is not None:
                return abs(s - other) <= ERROR
            else:
                return other == 0 and self.amount == 0
        if isinstance(other, str):
            other = Length(other)
        if self.amount == other.amount and self.units == other.units:
            return True
        if s is not None:
            o = self.in_pixels()
            if abs(s - o) <= ERROR:
                return True
        s = self.in_inches()
        if s is not None:
            o = self.in_inches()
            if abs(s - o) <= ERROR:
                return True
        return False

    @property
    def value_in_units(self):
        return self.amount

    def in_pixels(self):
        if self.units == 'px' or self.units == '':
            return self.amount
        if self.units == 'pt':
            return self.amount / 1.3333
        if self.units == 'pc':
            return self.amount / 16.0
        return None

    def in_inches(self):
        if self.units == 'mm':
            return self.amount * 0.0393701
        if self.units == 'cm':
            return self.amount * 0.393701
        if self.units == 'in':
            return self.amount
        return None

    def to_mm(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length, font_size=font_size,
                           font_height=font_height, viewbox=viewbox)
        v = value / (ppi * 0.0393701)
        return Length("%smm" % (Length.str(v)))

    def to_cm(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length,
                           font_size=font_size, font_height=font_height, viewbox=viewbox)
        v = value / (ppi * 0.393701)
        return Length("%scm" % (Length.str(v)))

    def to_inch(self, ppi=DEFAULT_PPI, relative_length=None, font_size=None, font_height=None, viewbox=None):
        value = self.value(ppi=ppi, relative_length=relative_length,
                           font_size=font_size, font_height=font_height, viewbox=viewbox)
        v = value / ppi
        return Length("%sin" % (Length.str(v)))

    def value(self, ppi=None, relative_length=None, font_size=None, font_height=None, viewbox=None, **kwargs):
        if self.amount is None:
            return None
        if self.units == '%':
            if relative_length is None:
                return self
            fraction = self.amount / 100.0
            if isinstance(relative_length, (float, int)):
                return fraction * relative_length
            elif isinstance(relative_length, (str, Length)):
                length = relative_length * self
                if isinstance(length, Length):
                    return length.value(ppi=ppi, font_size=font_size, font_height=font_height, viewbox=viewbox)
                return length
            return self
        if self.units == 'mm':
            if ppi is None:
                return self
            return self.amount * ppi * 0.0393701
        if self.units == 'cm':
            if ppi is None:
                return self
            return self.amount * ppi * 0.393701
        if self.units == 'in':
            if ppi is None:
                return self
            return self.amount * ppi
        if self.units == 'px' or self.units == '':
            return self.amount
        if self.units == 'pt':
            return self.amount * 1.3333
        if self.units == 'pc':
            return self.amount * 16.0
        if self.units == 'em':
            if font_size is None:
                return self
            return self.amount * float(font_size)
        if self.units == 'ex':
            if font_height is None:
                return self
            return self.amount * float(font_height)
        if self.units == 'vw':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            return self.amount * v.width / 100.0
        if self.units == 'vh':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            return self.amount * v.height / 100.0
        if self.units == 'vmin':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            m = min(v.height, v.height)
            return self.amount * m / 100.0
        if self.units == 'vmax':
            if viewbox is None:
                return self
            v = Viewbox(viewbox)
            m = max(v.height, v.height)
            return self.amount * m / 100.0
        try:
            return float(self)
        except ValueError:
            return self

    @staticmethod
    def str(s):
        if s is None:
            return "n/a"
        if isinstance(s, Length):
            if s.units == '':
                s = s.amount
            else:
                a = '%.12f' % (s.amount)
                if '.' in a:
                    a = a.rstrip('0').rstrip('.')
                return '\'%s%s\'' % (a, s.units)
        try:
            s = '%.12f' % (s)
        except TypeError:
            return str(s)
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s


class Color(object):
    """
    SVG Color Parsing
    Parses different forms of defining colors.

    Including keyword: https://www.w3.org/TR/SVG11/types.html#ColorKeywords
    """

    def __init__(self, *args, **kwargs):
        self.value = 0
        if len(args) == 0:
            r = 0
            g = 0
            b = 0
            if 'red' in kwargs:
                r = kwargs['red']
            if 'green' in kwargs:
                g = kwargs['green']
            if 'blue' in kwargs:
                b = kwargs['blue']
            if 'r' in kwargs:
                r = kwargs['r']
            if 'g' in kwargs:
                g = kwargs['g']
            if 'b' in kwargs:
                b = kwargs['b']
            self.value = Color.rgb_to_int(r, g, b)
        if 1 <= len(args) <= 2:
            v = args[0]
            if isinstance(v, Color):
                self.value = v.value
            elif isinstance(v, int):
                self.value = v
            else:
                self.value = Color.parse(v)
            if len(args) == 2:
                self.opacity = float(args[1])
        elif len(args) == 3:
            r = args[0]
            g = args[1]
            b = args[2]
            self.value = Color.rgb_to_int(r, g, b)
        elif len(args) == 4:
            r = args[0]
            g = args[1]
            b = args[2]
            opacity = args[3] / 255.0
            self.value = Color.rgb_to_int(r, g, b, opacity)

    def __int__(self):
        return self.value

    def __str__(self):
        if self.value is None:
            return str(self.value)
        return self.hex

    def __repr__(self):
        if self.value is None:
            return 'Color(\'%s\')' % (self.value)
        return 'Color(\'%s\')' % (self.hex)

    def __eq__(self, other):
        if self is other:
            return True
        first = self.value
        second = other
        if isinstance(second, str):
            second = Color(second)
        if isinstance(second, Color):
            second = second.value
        return first == second

    def __ne__(self, other):
        return not self == other

    @staticmethod
    def rgb_to_int(r, g, b, opacity=1.0):
        if opacity > 1:
            opacity = 1.0
        if opacity < 0:
            opacity = 0
        r = Color.crimp(r)
        g = Color.crimp(g)
        b = Color.crimp(b)
        a = Color.crimp(opacity * 255.0)
        if a & 0x80 != 0:
            a ^= 0x80
            a <<= 24
            a = ~a
            a ^= 0x7FFFFFFF
        else:
            a <<= 24
        r <<= 16
        g <<= 8
        c = r | g | b | a
        return c

    @staticmethod
    def hsl_to_int(h, s, l, opacity=1.0):
        c = Color()
        c.opacity = opacity
        c.hsl = h, s, l
        return c.value

    @staticmethod
    def parse(color_string):
        """Parse SVG color, will return a set value."""
        if color_string is None or color_string == SVG_VALUE_NONE:
            return None
        match = REGEX_COLOR_HEX.match(color_string)
        if match:
            return Color.parse_color_hex(color_string)
        match = REGEX_COLOR_RGB.match(color_string)
        if match:
            return Color.parse_color_rgb(match.groups())
        match = REGEX_COLOR_RGB_PERCENT.match(color_string)
        if match:
            return Color.parse_color_rgbp(match.groups())
        match = REGEX_COLOR_HSL.match(color_string)
        if match:
            return Color.parse_color_hsl(match.groups())
        return Color.parse_color_lookup(color_string)

    @staticmethod
    def parse_color_lookup(v):
        """Parse SVG Color by Keyword on dictionary lookup"""
        if not isinstance(v, str):
            return Color.rgb_to_int(0, 0, 0)
        else:
            v = v.replace(' ', '').lower()
        if v == "transparent":
            return Color.rgb_to_int(0, 0, 0, 0.0)
        if v == "aliceblue":
            return Color.rgb_to_int(250, 248, 255)
        if v == "aliceblue":
            return Color.rgb_to_int(240, 248, 255)
        if v == "antiquewhite":
            return Color.rgb_to_int(250, 235, 215)
        if v == "aqua":
            return Color.rgb_to_int(0, 255, 255)
        if v == "aquamarine":
            return Color.rgb_to_int(127, 255, 212)
        if v == "azure":
            return Color.rgb_to_int(240, 255, 255)
        if v == "beige":
            return Color.rgb_to_int(245, 245, 220)
        if v == "bisque":
            return Color.rgb_to_int(255, 228, 196)
        if v == "black":
            return Color.rgb_to_int(0, 0, 0)
        if v == "blanchedalmond":
            return Color.rgb_to_int(255, 235, 205)
        if v == "blue":
            return Color.rgb_to_int(0, 0, 255)
        if v == "blueviolet":
            return Color.rgb_to_int(138, 43, 226)
        if v == "brown":
            return Color.rgb_to_int(165, 42, 42)
        if v == "burlywood":
            return Color.rgb_to_int(222, 184, 135)
        if v == "cadetblue":
            return Color.rgb_to_int(95, 158, 160)
        if v == "chartreuse":
            return Color.rgb_to_int(127, 255, 0)
        if v == "chocolate":
            return Color.rgb_to_int(210, 105, 30)
        if v == "coral":
            return Color.rgb_to_int(255, 127, 80)
        if v == "cornflowerblue":
            return Color.rgb_to_int(100, 149, 237)
        if v == "cornsilk":
            return Color.rgb_to_int(255, 248, 220)
        if v == "crimson":
            return Color.rgb_to_int(220, 20, 60)
        if v == "cyan":
            return Color.rgb_to_int(0, 255, 255)
        if v == "darkblue":
            return Color.rgb_to_int(0, 0, 139)
        if v == "darkcyan":
            return Color.rgb_to_int(0, 139, 139)
        if v == "darkgoldenrod":
            return Color.rgb_to_int(184, 134, 11)
        if v == "darkgray":
            return Color.rgb_to_int(169, 169, 169)
        if v == "darkgreen":
            return Color.rgb_to_int(0, 100, 0)
        if v == "darkgrey":
            return Color.rgb_to_int(169, 169, 169)
        if v == "darkkhaki":
            return Color.rgb_to_int(189, 183, 107)
        if v == "darkmagenta":
            return Color.rgb_to_int(139, 0, 139)
        if v == "darkolivegreen":
            return Color.rgb_to_int(85, 107, 47)
        if v == "darkorange":
            return Color.rgb_to_int(255, 140, 0)
        if v == "darkorchid":
            return Color.rgb_to_int(153, 50, 204)
        if v == "darkred":
            return Color.rgb_to_int(139, 0, 0)
        if v == "darksalmon":
            return Color.rgb_to_int(233, 150, 122)
        if v == "darkseagreen":
            return Color.rgb_to_int(143, 188, 143)
        if v == "darkslateblue":
            return Color.rgb_to_int(72, 61, 139)
        if v == "darkslategray":
            return Color.rgb_to_int(47, 79, 79)
        if v == "darkslategrey":
            return Color.rgb_to_int(47, 79, 79)
        if v == "darkturquoise":
            return Color.rgb_to_int(0, 206, 209)
        if v == "darkviolet":
            return Color.rgb_to_int(148, 0, 211)
        if v == "deeppink":
            return Color.rgb_to_int(255, 20, 147)
        if v == "deepskyblue":
            return Color.rgb_to_int(0, 191, 255)
        if v == "dimgray":
            return Color.rgb_to_int(105, 105, 105)
        if v == "dimgrey":
            return Color.rgb_to_int(105, 105, 105)
        if v == "dodgerblue":
            return Color.rgb_to_int(30, 144, 255)
        if v == "firebrick":
            return Color.rgb_to_int(178, 34, 34)
        if v == "floralwhite":
            return Color.rgb_to_int(255, 250, 240)
        if v == "forestgreen":
            return Color.rgb_to_int(34, 139, 34)
        if v == "fuchsia":
            return Color.rgb_to_int(255, 0, 255)
        if v == "gainsboro":
            return Color.rgb_to_int(220, 220, 220)
        if v == "ghostwhite":
            return Color.rgb_to_int(248, 248, 255)
        if v == "gold":
            return Color.rgb_to_int(255, 215, 0)
        if v == "goldenrod":
            return Color.rgb_to_int(218, 165, 32)
        if v == "gray":
            return Color.rgb_to_int(128, 128, 128)
        if v == "grey":
            return Color.rgb_to_int(128, 128, 128)
        if v == "green":
            return Color.rgb_to_int(0, 128, 0)
        if v == "greenyellow":
            return Color.rgb_to_int(173, 255, 47)
        if v == "honeydew":
            return Color.rgb_to_int(240, 255, 240)
        if v == "hotpink":
            return Color.rgb_to_int(255, 105, 180)
        if v == "indianred":
            return Color.rgb_to_int(205, 92, 92)
        if v == "indigo":
            return Color.rgb_to_int(75, 0, 130)
        if v == "ivory":
            return Color.rgb_to_int(255, 255, 240)
        if v == "khaki":
            return Color.rgb_to_int(240, 230, 140)
        if v == "lavender":
            return Color.rgb_to_int(230, 230, 250)
        if v == "lavenderblush":
            return Color.rgb_to_int(255, 240, 245)
        if v == "lawngreen":
            return Color.rgb_to_int(124, 252, 0)
        if v == "lemonchiffon":
            return Color.rgb_to_int(255, 250, 205)
        if v == "lightblue":
            return Color.rgb_to_int(173, 216, 230)
        if v == "lightcoral":
            return Color.rgb_to_int(240, 128, 128)
        if v == "lightcyan":
            return Color.rgb_to_int(224, 255, 255)
        if v == "lightgoldenrodyellow":
            return Color.rgb_to_int(250, 250, 210)
        if v == "lightgray":
            return Color.rgb_to_int(211, 211, 211)
        if v == "lightgreen":
            return Color.rgb_to_int(144, 238, 144)
        if v == "lightgrey":
            return Color.rgb_to_int(211, 211, 211)
        if v == "lightpink":
            return Color.rgb_to_int(255, 182, 193)
        if v == "lightsalmon":
            return Color.rgb_to_int(255, 160, 122)
        if v == "lightseagreen":
            return Color.rgb_to_int(32, 178, 170)
        if v == "lightskyblue":
            return Color.rgb_to_int(135, 206, 250)
        if v == "lightslategray":
            return Color.rgb_to_int(119, 136, 153)
        if v == "lightslategrey":
            return Color.rgb_to_int(119, 136, 153)
        if v == "lightsteelblue":
            return Color.rgb_to_int(176, 196, 222)
        if v == "lightyellow":
            return Color.rgb_to_int(255, 255, 224)
        if v == "lime":
            return Color.rgb_to_int(0, 255, 0)
        if v == "limegreen":
            return Color.rgb_to_int(50, 205, 50)
        if v == "linen":
            return Color.rgb_to_int(250, 240, 230)
        if v == "magenta":
            return Color.rgb_to_int(255, 0, 255)
        if v == "maroon":
            return Color.rgb_to_int(128, 0, 0)
        if v == "mediumaquamarine":
            return Color.rgb_to_int(102, 205, 170)
        if v == "mediumblue":
            return Color.rgb_to_int(0, 0, 205)
        if v == "mediumorchid":
            return Color.rgb_to_int(186, 85, 211)
        if v == "mediumpurple":
            return Color.rgb_to_int(147, 112, 219)
        if v == "mediumseagreen":
            return Color.rgb_to_int(60, 179, 113)
        if v == "mediumslateblue":
            return Color.rgb_to_int(123, 104, 238)
        if v == "mediumspringgreen":
            return Color.rgb_to_int(0, 250, 154)
        if v == "mediumturquoise":
            return Color.rgb_to_int(72, 209, 204)
        if v == "mediumvioletred":
            return Color.rgb_to_int(199, 21, 133)
        if v == "midnightblue":
            return Color.rgb_to_int(25, 25, 112)
        if v == "mintcream":
            return Color.rgb_to_int(245, 255, 250)
        if v == "mistyrose":
            return Color.rgb_to_int(255, 228, 225)
        if v == "moccasin":
            return Color.rgb_to_int(255, 228, 181)
        if v == "navajowhite":
            return Color.rgb_to_int(255, 222, 173)
        if v == "navy":
            return Color.rgb_to_int(0, 0, 128)
        if v == "oldlace":
            return Color.rgb_to_int(253, 245, 230)
        if v == "olive":
            return Color.rgb_to_int(128, 128, 0)
        if v == "olivedrab":
            return Color.rgb_to_int(107, 142, 35)
        if v == "orange":
            return Color.rgb_to_int(255, 165, 0)
        if v == "orangered":
            return Color.rgb_to_int(255, 69, 0)
        if v == "orchid":
            return Color.rgb_to_int(218, 112, 214)
        if v == "palegoldenrod":
            return Color.rgb_to_int(238, 232, 170)
        if v == "palegreen":
            return Color.rgb_to_int(152, 251, 152)
        if v == "paleturquoise":
            return Color.rgb_to_int(175, 238, 238)
        if v == "palevioletred":
            return Color.rgb_to_int(219, 112, 147)
        if v == "papayawhip":
            return Color.rgb_to_int(255, 239, 213)
        if v == "peachpuff":
            return Color.rgb_to_int(255, 218, 185)
        if v == "peru":
            return Color.rgb_to_int(205, 133, 63)
        if v == "pink":
            return Color.rgb_to_int(255, 192, 203)
        if v == "plum":
            return Color.rgb_to_int(221, 160, 221)
        if v == "powderblue":
            return Color.rgb_to_int(176, 224, 230)
        if v == "purple":
            return Color.rgb_to_int(128, 0, 128)
        if v == "red":
            return Color.rgb_to_int(255, 0, 0)
        if v == "rosybrown":
            return Color.rgb_to_int(188, 143, 143)
        if v == "royalblue":
            return Color.rgb_to_int(65, 105, 225)
        if v == "saddlebrown":
            return Color.rgb_to_int(139, 69, 19)
        if v == "salmon":
            return Color.rgb_to_int(250, 128, 114)
        if v == "sandybrown":
            return Color.rgb_to_int(244, 164, 96)
        if v == "seagreen":
            return Color.rgb_to_int(46, 139, 87)
        if v == "seashell":
            return Color.rgb_to_int(255, 245, 238)
        if v == "sienna":
            return Color.rgb_to_int(160, 82, 45)
        if v == "silver":
            return Color.rgb_to_int(192, 192, 192)
        if v == "skyblue":
            return Color.rgb_to_int(135, 206, 235)
        if v == "slateblue":
            return Color.rgb_to_int(106, 90, 205)
        if v == "slategray":
            return Color.rgb_to_int(112, 128, 144)
        if v == "slategrey":
            return Color.rgb_to_int(112, 128, 144)
        if v == "snow":
            return Color.rgb_to_int(255, 250, 250)
        if v == "springgreen":
            return Color.rgb_to_int(0, 255, 127)
        if v == "steelblue":
            return Color.rgb_to_int(70, 130, 180)
        if v == "tan":
            return Color.rgb_to_int(210, 180, 140)
        if v == "teal":
            return Color.rgb_to_int(0, 128, 128)
        if v == "thistle":
            return Color.rgb_to_int(216, 191, 216)
        if v == "tomato":
            return Color.rgb_to_int(255, 99, 71)
        if v == "turquoise":
            return Color.rgb_to_int(64, 224, 208)
        if v == "violet":
            return Color.rgb_to_int(238, 130, 238)
        if v == "wheat":
            return Color.rgb_to_int(245, 222, 179)
        if v == "white":
            return Color.rgb_to_int(255, 255, 255)
        if v == "whitesmoke":
            return Color.rgb_to_int(245, 245, 245)
        if v == "yellow":
            return Color.rgb_to_int(255, 255, 0)
        if v == "yellowgreen":
            return Color.rgb_to_int(154, 205, 50)
        return Color.rgb_to_int(0, 0, 0)

    @staticmethod
    def parse_color_hex(hex_string):
        """Parse SVG Color by Hex String"""
        h = hex_string.lstrip('#')
        size = len(h)
        if size == 8:
            return int(h[:8], 16)
        elif size == 6:
            s = '{0}'.format(h[:6])
            q = (~int(s, 16) & 0xFFFFFF)
            v = -1 ^ q
            return v
        elif size == 4:
            s = h[0] + h[0] + h[1] + h[1] + h[2] + h[2] + h[3] + h[3]
            return int(s, 16)
        elif size == 3:
            s = '{0}{0}{1}{1}{2}{2}'.format(h[0], h[1], h[2])
            q = (~int(s, 16) & 0xFFFFFF)
            v = -1 ^ q
            return v
        return Color.rgb_to_int(0, 0, 0)

    @staticmethod
    def parse_color_rgb(values):
        """Parse SVG Color, RGB value declarations """
        r = int(values[0])
        g = int(values[1])
        b = int(values[2])
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.rgb_to_int(r, g, b, opacity)

    @staticmethod
    def parse_color_rgbp(values):
        """Parse SVG color, RGB percent value declarations"""
        ratio = 255.0 / 100.0
        r = round(float(values[0]) * ratio)
        g = round(float(values[1]) * ratio)
        b = round(float(values[2]) * ratio)
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.rgb_to_int(r, g, b, opacity)

    @staticmethod
    def parse_color_hsl(values):
        """Parse SVG color, HSL value declarations"""
        h = Angle.parse(values[0])
        h = h.as_turns
        s = float(values[1]) / 100.0
        if s > 1:
            s = 1.0
        if s < 0:
            s = 0.0
        l = float(values[2]) / 100.0
        if l > 1:
            l = 1.0
        if l < 0:
            l = 0.0
        if values[3] is not None:
            opacity = float(values[3])
        else:
            opacity = 1
        return Color.hsl_to_int(h, s, l, opacity)

    @property
    def opacity(self):
        return self.alpha / 255.0

    @opacity.setter
    def opacity(self, opacity):
        a = int(round(opacity * 255.0))
        a = Color.crimp(a)
        self.alpha = a

    @property
    def alpha(self):
        return (self.value >> 24) & 0xFF

    @alpha.setter
    def alpha(self, a):
        a = Color.crimp(a)
        self.value &= 0xFFFFFF
        self.value = int(self.value)
        if a & 0x80 != 0:
            a ^= 0x80
            a <<= 24
            a = ~a
            a ^= 0x7FFFFFFF
        else:
            a <<= 24
        self.value |= a

    @property
    def red(self):
        return (self.value >> 16) & 0xFF

    @red.setter
    def red(self, r):
        r = int(r & 0xFF)
        self.value &= ~0xFF0000
        r <<= 16
        self.value |= r

    @property
    def green(self):
        return (self.value >> 8) & 0xFF

    @green.setter
    def green(self, g):
        g = int(g & 0xFF)
        self.value &= ~0xFF00
        g <<= 8
        self.value |= g

    @property
    def blue(self):
        return self.value & 0xFF

    @blue.setter
    def blue(self, b):
        b = int(b & 0xFF)
        self.value &= ~0xFF
        self.value |= b

    @property
    def hexa(self):
        return '#%02x%02x%02x%02x' % (self.alpha, self.red, self.green, self.blue)

    @property
    def hex(self):
        if self.alpha == 0xFF:
            return '#%02x%02x%02x' % (self.red, self.green, self.blue)
        else:
            return '#%02x%02x%02x%02x' % (self.alpha, self.red, self.green, self.blue)

    @property
    def hue(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        var_min = min(r, g, b)
        var_max = max(r, g, b)
        delta_max = var_max - var_min
        if delta_max == 0:
            return 0
        dr = (((var_max - r) / 6.0) + delta_max / 2.0) / delta_max
        dg = (((var_max - g) / 6.0) + delta_max / 2.0) / delta_max
        db = (((var_max - b) / 6.0) + delta_max / 2.0) / delta_max
        if r == var_max:
            h = db - dg
        elif g == var_max:
            h = (1.0 / 3.0) + dr - db
        else:  # db == max_v
            h = (2.0 / 3.0) + dg - dr
        if h < 0:
            h += 1
        if h > 1:
            h -= 1
        return h

    @hue.setter
    def hue(self, v):
        h, s, l = self.hsl
        self.hsl = v, s, l

    @property
    def saturation(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        min_v = min(r, g, b)
        max_v = max(r, g, b)
        delta = max_v - min_v
        if max_v == min_v:
            return 0.0
        if (max_v + min_v) < 1:
            return delta / (max_v + min_v)
        else:
            return delta / (2.0 - max_v - min_v)

    @saturation.setter
    def saturation(self, v):
        h, s, l = self.hsl
        self.hsl = h, v, l

    @property
    def lightness(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        min_v = min(r, g, b)
        max_v = max(r, g, b)
        return (max_v + min_v) / 2.0

    @lightness.setter
    def lightness(self, v):
        h, s, l = self.hsl
        self.hsl = h, s, v

    @property
    def intensity(self):
        r = self.red
        g = self.green
        b = self.blue
        return (r + b + g) / 768.0

    @property
    def brightness(self):
        r = self.red
        g = self.green
        b = self.blue
        cmax = max(r, g, b)
        return cmax / 255.0

    @property
    def blackness(self):
        return 1.0 - self.brightness

    @property
    def luminance(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        return r * 0.3 + g * 0.59 + b * 0.11

    @property
    def luma(self):
        r = self.red / 255.0
        g = self.green / 255.0
        b = self.blue / 255.0
        return r * 0.2126 + g * 0.7152 + b * 0.0722

    @staticmethod
    def over(c1, c2):
        """
        Porter Duff Alpha compositing operation over.
        Returns c1 over c2. This is the standard painter algorithm.
        """
        if isinstance(c1, str):
            c1 = Color.parse(c1)
        elif isinstance(c1, int):
            c1 = Color(c1)
        if isinstance(c2, str):
            c2 = Color.parse(c2)
        elif isinstance(c2, int):
            c2 = Color(c2)
        r1 = c1.red
        g1 = c1.green
        b1 = c1.blue
        a1 = c1.alpha
        if a1 == 255:
            return c1.value
        if a1 == 0:
            return c2.value
        r2 = c2.red
        g2 = c2.green
        b2 = c2.blue
        a2 = c2.alpha

        q = 255.0 - a1

        sr = r1 * a1 * 255.0 + r2 * a2 * q
        sg = g1 * a1 * 255.0 + g2 * a2 * q
        sb = b1 * a1 * 255.0 + b2 * a2 * q
        sa = a1 * 255.0 + a2 * q
        sr /= sa
        sg /= sa
        sb /= sa
        sa /= (255.0 * 255.0)
        return Color.rgb_to_int(sr, sg, sb, sa)

    @staticmethod
    def distance(c1, c2):
        return sqrt(Color.distance_sq(c1, c2))

    @staticmethod
    def distance_sq(c1, c2):
        """
        Function returns the square of colordistance. The square of the color distance will always be closer than the
        square of another color distance.

        Rather than naive Euclidean distance we use Compuphase's Redmean color distance.
        https://www.compuphase.com/cmetric.htm

        It's computationally simple, and empirical tests finds it to be on par with LabDE2000.

        :param c1: first color
        :param c2: second color
        :return: square of color distance
        """
        if isinstance(c1, str):
            c1 = Color(c1)
        elif isinstance(c1, int):
            c1 = Color(c1)
        if isinstance(c2, str):
            c2 = Color(c2)
        elif isinstance(c2, int):
            c2 = Color(c2)
        red_mean = int((c1.red + c2.red) / 2.0)
        r = c1.red - c2.red
        g = c1.green - c2.green
        b = c1.blue - c2.blue
        return (((512 + red_mean) * r * r) >> 8) + 4 * g * g + ((767 - red_mean) * b * b) >> 8

    @staticmethod
    def crimp(v):
        if v > 255:
            return 255
        if v < 0:
            return 0
        return int(v)

    @property
    def hsl(self):
        return self.hue, self.saturation, self.lightness

    @hsl.setter
    def hsl(self, value):
        if not isinstance(value, tuple):
            return
        h, s, l = value

        def hue_2_rgb(v1, v2, vh):
            if vh < 0:
                vh += 1
            if vh > 1:
                vh -= 1
            if 6.0 * vh < 1.0:
                return v1 + (v2 - v1) * 6.0 * vh
            if 2.0 * vh < 1:
                return v2
            if 3 * vh < 2.0:
                return v1 + (v2 - v1) * ((2.0 / 3.0) - vh) * 6.0
            return v1

        if s == 0.0:
            r = 255.0 * l
            g = 255.0 * l
            b = 255.0 * l
        else:
            if l < 0.5:
                v2 = l * (1.0 + s)
            else:
                v2 = (l + s) - (s * l)
            v1 = 2 * l - v2
            r = 255.0 * hue_2_rgb(v1, v2, h + (1.0 / 3.0))
            g = 255.0 * hue_2_rgb(v1, v2, h)
            b = 255.0 * hue_2_rgb(v1, v2, h - (1.0 / 3.0))
        self.value = self.rgb_to_int(r, g, b)

    def distance_to(self, other):
        return Color.distance(self, other)

    def blend(self, other, opacity=None):
        """
        Blends the given color with the current color.
        """
        if opacity is None:
            self.value = Color.over(other, self)
        else:
            color = Color(other)
            color.opacity = opacity
            self.value = Color.over(color, self)


class Point:
    """Point is a general subscriptable point class with .x and .y as well as [0] and [1]

    For compatibility with regebro svg.path we accept complex numbers as points x + yj,
    and provide .real and .imag as properties. As well as float and integer values as (v,0) elements.

    With regard to SVG 7.15.1 defining SVGPoint this class provides for matrix transformations.

    Points are only positions in real Euclidean space. This class is not intended to interact with
    the Length class.
    """

    def __init__(self, x, y=None):
        if x is not None and y is None:
            if isinstance(x, str):
                string_x, string_y = REGEX_COORD_PAIR.findall(x)[0]
                self.x = float(string_x)
                self.y = float(string_y)
                return
            try:  # Try .x .y
                self.y = x.y
                self.x = x.x
                return
            except AttributeError:
                pass
            try:  # try subscription.
                self.y = x[1]
                self.x = x[0]
                return
            except TypeError:
                pass
            try:  # try .imag .real complex values.
                self.y = x.imag
                self.x = x.real
                return
            except AttributeError:
                # Unknown.
                raise TypeError
        self.x = x
        self.y = y

    def __key(self):
        return (self.x, self.y)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if other is None:
            return False
        try:
            if not isinstance(other, Point):
                other = Point(other)
        except Exception:
            return NotImplemented

        return abs(self.x - other.x) <= ERROR and abs(self.y - other.y) <= ERROR

    def __ne__(self, other):
        return not self == other

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError

    def __setitem__(self, key, value):
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        else:
            raise IndexError

    def __repr__(self):
        x_str = Length.str(self.x)
        y_str = Length.str(self.y)
        return 'Point(%s,%s)' % (x_str, y_str)

    def __copy__(self):
        return Point(self.x, self.y)

    def __str__(self):
        try:
            x_str = ('%.12G' % (self.x))
        except TypeError:
            return self.__repr__()
        if '.' in x_str:
            x_str = x_str.rstrip('0').rstrip('.')
        y_str = ('%.12G' % (self.y))
        if '.' in y_str:
            y_str = y_str.rstrip('0').rstrip('.')
        return "%s,%s" % (x_str, y_str)

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            v = other.point_in_matrix_space(self)
            self.x = v.x
            self.y = v.y
            return self
        try:
            c = complex(self) * complex(other.x, other.y)
            self.x = c.real
            self.y = c.imag
            return self
        except AttributeError:
            pass
        try:
            c = complex(self) * complex(other[0], other[1])
            self.x = c.real
            self.y = c.imag
            return self
        except (TypeError, IndexError):
            pass
        try:
            c = complex(self) * complex(other.real, other.imag)
            self.x = c.real
            self.y = c.imag
            return self
        except AttributeError:
            pass
        try:
            self.x *= other
            self.y *= other
            return self
        except Exception:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            return other.point_in_matrix_space(self)
        try:
            return Point(complex(self) * complex(other.x,other.y))
        except AttributeError:
            pass
        try:
            return Point(complex(self) * complex(other[0], other[1]))
        except (TypeError, IndexError):
            pass
        try:
            return Point(complex(self) * complex(other.real, other.imag))
        except AttributeError:
            pass
        try:
            return Point(self.x * other, self.y * other)
        except Exception:
            return NotImplemented

    __rmul__ = __mul__

    def __iadd__(self, other):
        try:
            self.x += other.x
            self.y += other.y
            return self
        except AttributeError:
            pass
        try:
            self.y += other[1]
            self.x += other[0]
            return self
        except (TypeError, IndexError):
            pass
        try:
            self.x += other.real
            self.y += other.imag
            return self
        except AttributeError:
            pass
        try:
            self.x += other
            return self
        except Exception:
            return NotImplemented

    def __add__(self, other):
        try:
            x = self.x + other.x
            y = self.y + other.y
            return Point(x, y)
        except AttributeError:
            pass
        try:
            y = self.y + other[1]
            x = self.x + other[0]
            return Point(x, y)
        except (TypeError, IndexError):
            pass
        try:
            x = self.x + other.real
            y = self.y + other.imag
            return Point(x, y)
        except AttributeError:
            pass
        if isinstance(other, (float, int)):
            x = self.x + other
            return Point(x, self.y)
        return NotImplemented

    __radd__ = __add__

    def __isub__(self, other):
        try:
            self.x -= other.x
            self.y -= other.y
            return self
        except AttributeError:
            pass
        try:
            self.y -= other[1]
            self.x -= other[0]
            return self
        except (TypeError, IndexError):
            pass
        try:
            self.x -= other.real
            self.y -= other.imag
            return self
        except AttributeError:
            pass
        try:
            self.x -= other
            return self
        except Exception:
            return NotImplemented

    def __sub__(self, other):
        try:
            x = self.x - other.x
            y = self.y - other.y
            return Point(x, y)
        except AttributeError:
            pass
        try:
            y = self.y - other[1]
            x = self.x - other[0]
            return Point(x, y)
        except (TypeError, IndexError):
            pass
        try:
            x = self.x - other.real
            y = self.y - other.imag
            return Point(x, y)
        except AttributeError:
            pass
        if isinstance(other, (float, int)):
            x = self.x - other
            return Point(x, self.y)
        return NotImplemented

    def __rsub__(self, other):
        try:
            x = other.x - self.x
            y = other.y - self.y
            return Point(x, y)
        except AttributeError:
            pass
        try:
            y = other[1] - self.y
            x = other[0] - self.x
            return Point(x, y)
        except (TypeError, IndexError):
            pass
        try:
            x = other.real - self.x
            y = other.imag - self.y
            return Point(x, y)
        except AttributeError:
            pass
        if isinstance(other, (float, int)):
            x = other - self.x
            return Point(x, self.y)
        return NotImplemented

    def __complex__(self):
        return self.x + self.y * 1j

    def __abs__(self):
        return hypot(self.x, self.y)

    def __pow__(self, other):
        r_raised = abs(self) ** other
        argz_multiplied = self.argz() * other

        real_part = round(r_raised * cos(argz_multiplied))
        imag_part = round(r_raised * sin(argz_multiplied))
        return self.__class__(real_part, imag_part)

    def conjugate(self):
        return self.__class__(self.real, -self.imag)

    def argz(self):
        return atan(self.imag / self.real)

    @property
    def real(self):
        """Emulate svg.path use of complex numbers"""
        return self.x

    @property
    def imag(self):
        """Emulate svg.path use of complex numbers"""
        return self.y

    def matrix_transform(self, matrix):
        self *= matrix
        return self

    def move_towards(self, p2, amount=1):
        if not isinstance(p2, Point):
            p2 = Point(p2)
        self += amount * (p2 - self)

    def distance_to(self, p2):
        return abs(self - p2)

    def angle_to(self, p2):
        p = p2 - self
        return Angle.radians(atan2(p.y, p.x))

    def polar_to(self, angle, distance):
        q =  Point.polar(self, angle, distance)
        self.x = q.x
        self.y = q.y
        return self

    def reflected_across(self, p):
        return (p + (p - self))

    @staticmethod
    def orientation(p, q, r):
        """Determine the clockwise, linear, or counterclockwise orientation of the given points"""
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if val == 0:
            return 0
        elif val > 0:
            return 1
        else:
            return 2

    @staticmethod
    def convex_hull(pts):
        if len(pts) == 0:
            return
        points = sorted(set(pts), key=lambda p: p[0])
        first_point_on_hull = points[0]
        point_on_hull = first_point_on_hull
        while True:
            yield point_on_hull
            endpoint = point_on_hull
            for t in points:
                if point_on_hull is endpoint \
                        or Point.orientation(point_on_hull, t, endpoint) == 2:
                    endpoint = t
            point_on_hull = endpoint
            if first_point_on_hull is point_on_hull:
                break

    @staticmethod
    def distance(p1, p2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dx *= dx
        dy *= dy
        return sqrt(dx + dy)

    @staticmethod
    def polar(p1, angle, r):
        dx = cos(angle) * r
        dy = sin(angle) * r
        return Point(p1[0] + dx, p1[1] + dy)

    @staticmethod
    def angle(p1, p2):
        return Angle.radians(atan2(p2[1] - p1[1], p2[0] - p1[0]))

    @staticmethod
    def towards(p1, p2, amount):
        tx = amount * (p2[0] - p1[0]) + p1[0]
        ty = amount * (p2[1] - p1[1]) + p1[1]
        return Point(tx, ty)


class Angle(float):
    """CSS Angle defines as used in SVG/CSS"""

    def __repr__(self):
        return 'Angle(%.12f)' % self

    def __copy__(self):
        return Angle(self)

    def __eq__(self, other):
        # Python 2
        c1 = abs((self % tau) - (other % tau)) <= 1e-11
        return c1

    def normalized(self):
        return Angle(self % tau)

    @classmethod
    def parse(cls, angle_string):
        if not isinstance(angle_string, str):
            return
        angle_string = angle_string.lower()
        if angle_string.endswith('deg'):
            return Angle.degrees(float(angle_string[:-3]))
        if angle_string.endswith('grad'):
            return Angle.gradians(float(angle_string[:-4]))
        if angle_string.endswith('rad'):  # Must be after 'grad' since 'grad' ends with 'rad' too.
            return Angle.radians(float(angle_string[:-3]))
        if angle_string.endswith('turn'):
            return Angle.turns(float(angle_string[:-4]))
        if angle_string.endswith('%'):
            return Angle.turns(float(angle_string[:-1]) / 100.0)
        return Angle.degrees(float(angle_string))

    @classmethod
    def radians(cls, radians):
        return cls(radians)

    @classmethod
    def degrees(cls, degrees):
        return cls(tau * degrees / 360.0)

    @classmethod
    def gradians(cls, gradians):
        return cls(tau * gradians / 400.0)

    @classmethod
    def turns(cls, turns):
        return cls(tau * turns)

    @property
    def as_radians(self):
        return self

    @property
    def as_degrees(self):
        return self * 360.0 / tau

    @property
    def as_positive_degrees(self):
        v = self.as_degrees
        while v < 0:
            v += 360.0
        return v

    @property
    def as_gradians(self):
        return self * 400.0 / tau

    @property
    def as_turns(self):
        return self / tau

    def is_orthogonal(self):
        return (self % (tau / 4)) == 0


class Matrix:
    """"
    Provides svg matrix interfacing.

    SVG 7.15.3 defines the matrix form as:
    [a c  e]
    [b d  f]

    While e and f are defined as floats, they can be for limited periods defined as a Length.
    With regard to CSS, it's reasonable to perform operations like 'transform(20cm, 20cm)' and
    expect these to be treated consistently. Performing other matrix operations in a consistent
    way. However, render must be called to change these parameters into float locations prior to
    any operation which might be used to transform a point or polyline or path object.
    """

    def __init__(self, *components, **kwargs):
        self.a = 1.0
        self.b = 0.0
        self.c = 0.0
        self.d = 1.0
        self.e = 0.0
        self.f = 0.0
        len_args = len(components)
        if len_args == 0:
            pass
        elif len_args == 1:
            m = components[0]
            if isinstance(m, str):
                self.parse(m)
                self.render(**kwargs)
            else:
                self.a = m[0]
                self.b = m[1]
                self.c = m[2]
                self.d = m[3]
                self.e = m[4]
                self.f = m[5]
        else:
            self.a = components[0]
            self.b = components[1]
            self.c = components[2]
            self.d = components[3]
            self.e = components[4]
            self.f = components[5]
            self.render(**kwargs)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, str):
            other = Matrix(other)
        if not isinstance(other, Matrix):
            return False
        if abs(self.a - other.a) > 1e-12:
            return False
        if abs(self.b - other.b) > 1e-12:
            return False
        if abs(self.c - other.c) > 1e-12:
            return False
        if abs(self.d - other.d) > 1e-12:
            return False
        if self.e != other.e and abs(self.e - other.e) > 1e-12:
            return False
        if self.f != other.f and abs(self.f - other.f) > 1e-12:
            return False
        return True

    def __len__(self):
        return 6

    def __invert__(self):
        m = self.__copy__()
        return m.inverse()

    def __matmul__(self, other):
        m = copy(self)
        m.__imatmul__(other)
        return m

    def __rmatmul__(self, other):
        m = copy(other)
        m.__imatmul__(self)
        return m

    def __imatmul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(self, other)
        return self

    __mul__ = __matmul__
    __rmul__ = __rmatmul__
    __imul__ = __imatmul__

    def __getitem__(self, item):
        if item == 0:
            return float(self.a)
        elif item == 1:
            return float(self.b)
        elif item == 2:
            return float(self.c)
        elif item == 3:
            return float(self.d)
        elif item == 4:
            return self.e
        elif item == 5:
            return self.f

    def __setitem__(self, key, value):
        if key == 0:
            self.a = value
        elif key == 1:
            self.b = value
        elif key == 2:
            self.c = value
        elif key == 3:
            self.d = value
        elif key == 4:
            self.e = value
        elif key == 5:
            self.f = value

    def __repr__(self):
        return 'Matrix(%s, %s, %s, %s, %s, %s)' % \
               (Length.str(self.a), Length.str(self.b),
                Length.str(self.c), Length.str(self.d),
                Length.str(self.e), Length.str(self.f))

    def __copy__(self):
        return Matrix(self.a, self.b, self.c, self.d, self.e, self.f)

    def __str__(self):
        """
        Many of SVG's graphics operations utilize 2x3:

        :returns string representation of matrix.
        """
        return "[%3f, %3f,\n %3f, %3f,   %s, %s]" % \
               (self.a, self.c, self.b, self.d, self.e, self.f)

    def parse(self, transform_str):
        """Parses the svg transform string.

        Transforms from SVG 1.1 have a smaller complete set of operations. Whereas in SVG 2.0 they gain
        the CSS transforms and the additional functions and parsing that go with that. This parse is
        compatible with SVG 1.1 and the SVG 2.0 which includes the CSS 2d superset.

        CSS transforms have scalex() scaley() translatex(), translatey(), and skew() (deprecated).
        2D CSS angles haves units: "deg" tau / 360, "rad" tau/tau, "grad" tau/400, "turn" tau.
        2D CSS distances have length/percentages: "px", "cm", "mm", "in", "pt", etc. (+|-)?d+%

        In the case of percentages there must be a known height and width to properly create a matrix out of that.

        """
        if not transform_str:
            return
        if not isinstance(transform_str, str):
            raise TypeError('Must provide a string to parse')

        for sub_element in REGEX_TRANSFORM_TEMPLATE.findall(transform_str.lower()):
            name = sub_element[0]
            params = tuple(REGEX_TRANSFORM_PARAMETER.findall(sub_element[1]))
            params = [mag + units for mag, units in params]
            if SVG_TRANSFORM_MATRIX == name:
                params = map(float, params)
                self.pre_cat(*params)
            elif SVG_TRANSFORM_TRANSLATE == name:
                try:
                    x_param = Length(params[0]).value()
                except IndexError:
                    continue
                try:
                    y_param = Length(params[1]).value()
                    self.pre_translate(x_param, y_param)
                except IndexError:
                    self.pre_translate(x_param)
            elif SVG_TRANSFORM_TRANSLATE_X == name:
                self.pre_translate(Length(params[0]).value(), 0)
            elif SVG_TRANSFORM_TRANSLATE_Y == name:
                self.pre_translate(0, Length(params[0]).value())
            elif SVG_TRANSFORM_SCALE == name:
                params = map(float, params)
                self.pre_scale(*params)
            elif SVG_TRANSFORM_SCALE_X == name:
                self.pre_scale(float(params[0]), 1)
            elif SVG_TRANSFORM_SCALE_Y == name:
                self.pre_scale(1, float(params[0]))
            elif SVG_TRANSFORM_ROTATE == name:
                angle = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_rotate(angle)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_rotate(angle, x_param, y_param)
                except IndexError:
                    self.pre_rotate(angle, x_param)
            elif SVG_TRANSFORM_SKEW == name:
                angle_a = Angle.parse(params[0])
                try:
                    angle_b = Angle.parse(params[1])
                except IndexError:  # this isn't valid.
                    continue
                try:
                    x_param = Length(params[2]).value()
                except IndexError:
                    self.pre_skew(angle_a, angle_b)
                    continue
                try:
                    y_param = Length(params[3]).value()
                    self.pre_skew(angle_a, angle_b, x_param, y_param)
                except IndexError:
                    self.pre_skew(angle_a, angle_b, x_param)
            elif SVG_TRANSFORM_SKEW_X == name:
                angle_a = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_skew_x(angle_a)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_skew_x(angle_a, x_param, y_param)
                except IndexError:
                    self.pre_skew_x(angle_a, x_param)
            elif SVG_TRANSFORM_SKEW_Y == name:
                angle_b = Angle.parse(params[0])
                try:
                    x_param = Length(params[1]).value()
                except IndexError:
                    self.pre_skew_y(angle_b)
                    continue
                try:
                    y_param = Length(params[2]).value()
                    self.pre_skew_y(angle_b, x_param, y_param)
                except IndexError:
                    self.pre_skew_y(angle_b, x_param)
        return self

    def render(self, ppi=None, relative_length=None, width=None, height=None,
               font_size=None, font_height=None, viewbox=None, **kwargs):
        """
        Provides values to turn trans_x and trans_y values into user units floats rather
        than Lengths by giving the required information to perform the conversions.
        """
        if isinstance(self.e, Length):
            if width is None and relative_length is not None:
                width = relative_length
            self.e = self.e.value(ppi=ppi, relative_length=width, font_size=font_size,
                                  font_height=font_height, viewbox=viewbox)

        if isinstance(self.f, Length):
            if height is None and relative_length is not None:
                height = relative_length
            self.f = self.f.value(ppi=ppi, relative_length=height, font_size=font_size,
                                  font_height=font_height, viewbox=viewbox)
        return self

    @property
    def determinant(self):
        return self.a * self.d - self.c * self.b

    def value_trans_x(self):
        return self.e

    def value_trans_y(self):
        return self.f

    def value_scale_x(self):
        return float(self.a)

    def value_scale_y(self):
        return float(self.d)

    def value_skew_x(self):
        return float(self.b)

    def value_skew_y(self):
        return float(self.c)

    def reset(self):
        """Resets matrix to identity."""
        self.a = 1.0
        self.b = 0.0
        self.c = 0.0
        self.d = 1.0

        self.e = 0.0
        self.f = 0.0

    def inverse(self):
        """
        SVG Matrix:
        [a c e]
        [b d f]
        """
        m00 = self.a
        m01 = self.c
        m02 = self.e
        m10 = self.b
        m11 = self.d
        m12 = self.f
        determinant = m00 * m11 - m01 * m10
        inverse_determinant = 1.0 / determinant
        self.a = m11 * inverse_determinant
        self.c = -m01 * inverse_determinant
        self.b = -m10 * inverse_determinant
        self.d = m00 * inverse_determinant

        self.e = (m01 * m12 - m02 * m11) * inverse_determinant
        self.f = (m10 * m02 - m00 * m12) * inverse_determinant
        return self

    def vector(self):
        """
        provide the matrix suitable for multiplying vectors. This will be the matrix with the same rotation and scale
        aspects but with no translation. This matrix is for multiplying vector elements where the position doesn't
        matter but the scaling and rotation do.
        :return:
        """
        return Matrix(self.a, self.b, self.c, self.d, 0.0, 0.0)

    def is_identity(self):
        return self.a == 1 and self.b == 0 and self.c == 0 and self.d == 1 and self.e == 0 and self.f == 0

    def post_cat(self, *components):
        mx = Matrix(*components)
        self.__imatmul__(mx)

    def post_scale(self, sx=1.0, sy=None, x=0.0, y=0.0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.post_cat(Matrix.scale(sx, sy))
        else:
            self.post_translate(-x, -y)
            self.post_scale(sx, sy)
            self.post_translate(x, y)

    def post_scale_x(self, sx=1.0, x=0.0, y=0.0):
        self.post_scale(sx, 1, x, y)

    def post_scale_y(self, sy=1.0, x=0.0, y=0.0):
        self.post_scale(1, sy, x, y)

    def post_translate(self, tx=0.0, ty=0.0):
        self.post_cat(Matrix.translate(tx, ty))

    def post_translate_x(self, tx=0.0):
        self.post_translate(tx, 0.0)

    def post_translate_y(self, ty=0.0):
        self.post_translate(0.0, ty)

    def post_rotate(self, angle, x=0.0, y=0.0):
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.post_cat(Matrix.rotate(angle))  # self %= self.get_rotate(theta)
        else:
            matrix = Matrix()
            matrix.post_translate(-x, -y)
            matrix.post_cat(Matrix.rotate(angle))
            matrix.post_translate(x, y)
            self.post_cat(matrix)

    def post_skew(self, angle_a=0.0, angle_b=0.0, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.post_cat(Matrix.skew(angle_a, angle_b))
        else:
            self.post_translate(-x, -y)
            self.post_skew(angle_a, angle_b)
            self.post_translate(x, y)

    def post_skew_x(self, angle_a=0.0, x=0.0, y=0.0):
        self.post_skew(angle_a, 0.0, x, y)

    def post_skew_y(self, angle_b=0.0, x=0.0, y=0.0):
        self.post_skew(0.0, angle_b, x, y)

    def pre_cat(self, *components):
        mx = Matrix(*components)
        self.a, self.b, self.c, self.d, self.e, self.f = Matrix.matrix_multiply(mx, self)

    def pre_scale(self, sx=1.0, sy=None, x=0.0, y=0.0):
        if sy is None:
            sy = sx
        if x is None:
            x = 0.0
        if y is None:
            y = 0.0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.scale(sx, sy))
        else:
            self.pre_translate(x, y)
            self.pre_scale(sx, sy)
            self.pre_translate(-x, -y)

    def pre_scale_x(self, sx=1.0, x=0.0, y=0.0):
        self.pre_scale(sx, 1, x, y)

    def pre_scale_y(self, sy=1.0, x=0.0, y=0.0):
        self.pre_scale(1, sy, x, y)

    def pre_translate(self, tx=0.0, ty=0.0):
        self.pre_cat(Matrix.translate(tx, ty))

    def pre_translate_x(self, tx=0.0):
        self.pre_translate(tx, 0.0)

    def pre_translate_y(self, ty=0.0):
        self.pre_translate(0.0, ty)

    def pre_rotate(self, angle, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.rotate(angle))
        else:
            self.pre_translate(x, y)
            self.pre_rotate(angle)
            self.pre_translate(-x, -y)

    def pre_skew(self, angle_a=0.0, angle_b=0.0, x=0.0, y=0.0):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if x == 0 and y == 0:
            self.pre_cat(Matrix.skew(angle_a, angle_b))
        else:
            self.pre_translate(x, y)
            self.pre_skew(angle_a, angle_b)
            self.pre_translate(-x, -y)

    def pre_skew_x(self, angle_a=0.0, x=0.0, y=0.0):
        self.pre_skew(angle_a, 0, x, y)

    def pre_skew_y(self, angle_b=0.0, x=0.0, y=0.0):
        self.pre_skew(0.0, angle_b, x, y)

    def point_in_inverse_space(self, v0):
        inverse = Matrix(self)
        inverse.inverse()
        return inverse.point_in_matrix_space(v0)

    def point_in_matrix_space(self, v0):
        return Point(v0[0] * self.a + v0[1] * self.c + 1 * self.e,
                     v0[0] * self.b + v0[1] * self.d + 1 * self.f)

    def transform_point(self, v):
        nx = v[0] * self.a + v[1] * self.c + 1 * self.e
        ny = v[0] * self.b + v[1] * self.d + 1 * self.f
        v[0] = nx
        v[1] = ny
        return v

    def transform_vector(self, v):
        """
        Applies the transformation without the translation.
        """
        nx = v[0] * self.a + v[1] * self.c
        ny = v[0] * self.b + v[1] * self.d
        v[0] = nx
        v[1] = ny
        return v

    @classmethod
    def scale(cls, sx=1.0, sy=None):
        if sy is None:
            sy = sx
        return cls(sx, 0,
                   0, sy, 0, 0)

    @classmethod
    def scale_x(cls, sx=1.0):
        return cls.scale(sx, 1.0)

    @classmethod
    def scale_y(cls, sy=1.0):
        return cls.scale(1.0, sy)

    @classmethod
    def translate(cls, tx=0.0, ty=0.0):
        """SVG Matrix:
                [a c e]
                [b d f]
                """
        return cls(1.0, 0.0,
                   0.0, 1.0, tx, ty)

    @classmethod
    def translate_x(cls, tx=0.0):
        return cls.translate(tx, 0)

    @classmethod
    def translate_y(cls, ty=0.0):
        return cls.translate(0.0, ty)

    @classmethod
    def rotate(cls, angle=0.0):
        ct = cos(angle)
        st = sin(angle)
        return cls(ct, st,
                   -st, ct, 0.0, 0.0)

    @classmethod
    def skew(cls, angle_a=0.0, angle_b=0.0):
        aa = tan(angle_a)
        bb = tan(angle_b)
        return cls(1.0, bb,
                   aa, 1.0, 0.0, 0.0)

    @classmethod
    def skew_x(cls, angle=0.0):
        return cls.skew(angle, 0.0)

    @classmethod
    def skew_y(cls, angle=0.0):
        return cls.skew(0.0, angle)

    @classmethod
    def identity(cls):
        """
        1, 0, 0,
        0, 1, 0,
        """
        return cls()

    @staticmethod
    def matrix_multiply(m, s):
        """
        [a c e]      [a c e]   [a b 0]
        [b d f]   %  [b d f] = [c d 0]
        [0 0 1]      [0 0 1]   [e f 1]

        :param m0: matrix operand
        :param m1: matrix operand
        :return: muliplied matrix.
        """
        r0 = s.a * m.a + s.c * m.b + s.e * 0, \
             s.a * m.c + s.c * m.d + s.e * 0, \
             s.a * m.e + s.c * m.f + s.e * 1

        r1 = s.b * m.a + s.d * m.b + s.f * 0, \
             s.b * m.c + s.d * m.d + s.f * 0, \
             s.b * m.e + s.d * m.f + s.f * 1
        return float(r0[0]), float(r1[0]), float(r0[1]), float(r1[1]), r0[2], r1[2]


class Viewbox:

    def __init__(self, viewbox, preserve_aspect_ratio=None):
        """
        Viewbox controls the scaling between the drawing size view that is observing that drawing.

        :param viewbox: either values or viewbox attribute or a Viewbox object
        :param preserve_aspect_ratio: preserveAspectRatio
        """
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.preserve_aspect_ratio = preserve_aspect_ratio
        if isinstance(viewbox, dict):
            self.property_by_values(viewbox)
        elif isinstance(viewbox, Viewbox):
            self.property_by_object(viewbox)
        else:
            self.set_viewbox(viewbox)

    def __str__(self):
        return '%s %s %s %s' % (
            Length.str(self.x),
            Length.str(self.y),
            Length.str(self.width),
            Length.str(self.height),
        )

    def property_by_object(self, obj):
        self.x = obj.x
        self.y = obj.y
        self.width = obj.width
        self.height = obj.height
        self.preserve_aspect_ratio = obj.preserve_aspect_ratio

    def property_by_values(self, values):
        viewbox = values.get(SVG_ATTR_VIEWBOX)
        if viewbox is not None:
            self.set_viewbox(viewbox)
        if SVG_ATTR_PRESERVEASPECTRATIO in values:
            self.preserve_aspect_ratio = values[SVG_ATTR_PRESERVEASPECTRATIO]

    def set_viewbox(self, viewbox):
        if viewbox is not None:
            dims = list(REGEX_FLOAT.findall(viewbox))
            try:
                self.x = float(dims[0])
                self.y = float(dims[1])
                self.width = float(dims[2])
                self.height = float(dims[3])
            except IndexError:
                pass

    def transform(self, element):
        return Viewbox.viewbox_transform(
            element.x, element.y, element.width, element.height,
            self.x, self.y, self.width, self.height,
            self.preserve_aspect_ratio)

    @staticmethod
    def viewbox_transform(e_x, e_y, e_width, e_height, vb_x, vb_y, vb_width, vb_height, aspect):
        """
        SVG 1.1 7.2, SVG 2.0 8.2 equivalent transform of an SVG viewport.
        With regards to https://github.com/w3c/svgwg/issues/215 use 8.2 version.

        It creates transform commands equal to that viewport expected.

        :param svg_node: dict containing the relevant svg entries.
        :return: string of the SVG transform commands to account for the viewbox.
        """

        # Let e-x, e-y, e-width, e-height be the position and size of the element respectively.

        # Let vb-x, vb-y, vb-width, vb-height be the min-x, min-y,
        # width and height values of the viewBox attribute respectively.

        # Let align be the align value of preserveAspectRatio, or 'xMidYMid' if preserveAspectRatio is not defined.
        # Let meetOrSlice be the meetOrSlice value of preserveAspectRatio, or 'meet' if preserveAspectRatio is not defined
        # or if meetOrSlice is missing from this value.
        if e_x is None or e_y is None or e_width is None or e_height is None or \
                vb_x is None or vb_y is None or vb_width is None or vb_height is None:
            return ''
        if aspect is not None:
            aspect_slice = aspect.split(' ')
            try:
                align = aspect_slice[0]
            except IndexError:
                align = 'xMidyMid'
            try:
                meet_or_slice = aspect_slice[1]
            except IndexError:
                meet_or_slice = 'meet'
        else:
            align = 'xMidyMid'
            meet_or_slice = 'meet'
        # Initialize scale-x to e-width/vb-width.
        scale_x = e_width / vb_width
        # Initialize scale-y to e-height/vb-height.
        scale_y = e_height / vb_height

        # If align is not 'none' and meetOrSlice is 'meet', set the larger of scale-x and scale-y to the smaller.
        if align != SVG_VALUE_NONE and meet_or_slice == 'meet':
            scale_x = scale_y = min(scale_x, scale_y)
        # Otherwise, if align is not 'none' and meetOrSlice is 'slice', set the smaller of scale-x and scale-y to the larger
        elif align != SVG_VALUE_NONE and meet_or_slice == 'slice':
            scale_x = scale_y = max(scale_x, scale_y)
        # Initialize translate-x to e-x - (vb-x * scale-x).
        translate_x = e_x - (vb_x * scale_x)
        # Initialize translate-y to e-y - (vb-y * scale-y)
        translate_y = e_y - (vb_y * scale_y)
        # If align contains 'xMid', add (e-width - vb-width * scale-x) / 2 to translate-x.
        align = align.lower()
        if 'xmid' in align:
            translate_x += (e_width - vb_width * scale_x) / 2.0
        # If align contains 'xMax', add (e-width - vb-width * scale-x) to translate-x.
        if 'xmax' in align:
            translate_x += e_width - vb_width * scale_x
        # If align contains 'yMid', add (e-height - vb-height * scale-y) / 2 to translate-y.
        if 'ymid' in align:
            translate_y += (e_height - vb_height * scale_y) / 2.0
        # If align contains 'yMax', add (e-height - vb-height * scale-y) to translate-y.
        if 'ymax' in align:
            translate_y += (e_height - vb_height * scale_y)
        # The transform applied to content contained by the element is given by:
        # translate(translate-x, translate-y) scale(scale-x, scale-y)
        if isinstance(scale_x, Length) or isinstance(scale_y, Length):
            raise ValueError
        if translate_x == 0 and translate_y == 0:
            if scale_x == 1 and scale_y == 1:
                return ""  # Nothing happens.
            else:
                return "scale(%s, %s)" % (Length.str(scale_x), Length.str(scale_y))
        else:
            if scale_x == 1 and scale_y == 1:
                return "translate(%s, %s)" % (Length.str(translate_x), Length.str(translate_y))
            else:
                return "translate(%s, %s) scale(%s, %s)" % \
                       (Length.str(translate_x), Length.str(translate_y),
                        Length.str(scale_x), Length.str(scale_y))


class SVGElement(object):
    """
    Any element within the SVG namespace.

    if args[0] is a dict or SVGElement class the value is used to seed the values.
    Else, the values consist of the kwargs used. The priority is such that kwargs
    will overwrite any previously set value.

    If additional args exist these will be passed to property_by_args

    """

    def __init__(self, *args, **kwargs):
        self.id = None
        self.values = None
        if len(args) >= 1:
            s = args[0]
            if isinstance(s, dict):
                args = args[1:]
                self.values = dict(s)
                self.values.update(kwargs)
            elif isinstance(s, SVGElement):
                args = args[1:]
                self.property_by_object(s)
                self.property_by_args(*args)
                return
        if self.values is None:
            self.values = dict(kwargs)
        self.property_by_values(self.values)
        if len(args) != 0:
            self.property_by_args(*args)

    def property_by_args(self, *args):
        pass

    def property_by_object(self, obj):
        self.id = obj.id
        self.values = dict(obj.values)

    def property_by_values(self, values):
        self.id = values.get(SVG_ATTR_ID)

    def render(self, **kwargs):
        """
        Render changes any length/percent values or attributes into real usable limits if
        given the information required to change such parameters.

        :param kwargs: various other properties to be rendered with.
        :return:
        """
        pass

    def set(self, key, value):
        self.values[key] = value
        return self


class Transformable:
    """Any element that is transformable and has a transform property."""

    def __init__(self, *args, **kwargs):
        self._length = None
        self._lengths = None
        self.transform = None
        self.apply = None

    def property_by_object(self, s):
        self.transform = Matrix(s.transform)
        self.apply = s.apply

    def property_by_values(self, values):
        self.transform = Matrix(values.get(SVG_ATTR_TRANSFORM, ''))
        self.apply = bool(values.get('apply', True))

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n
        return NotImplemented

    __rmul__ = __mul__

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            self.transform *= other
        return self

    def __abs__(self):
        """
        The absolute value is taken to be the actual shape transformed.
        :return: transformed version of the given shape.
        """
        m = copy(self)
        m.reify()
        return m

    def reify(self):
        """
        Realizes the transform to the attributes. Such that the attributes become actualized and the transform
        simplifies towards the identity matrix. In many cases it will become the identity matrix. In other cases the
        transformed shape cannot be represented through the properties alone. And shall keep those parts of the
        transform required preserve equivalency.

        The default method will be called by submethods but will only scale properties like stroke_width which should
        scale with the transform.
        """
        self._lengths = None
        self._length = None

    def render(self, **kwargs):
        """
        Renders the transformable by performing any required length conversion operations into pixels. The element
        will be the pixel-length form.
        """
        if self.transform is not None:
            self.transform.render(**kwargs)
        return self

    def bbox(self, transformed=True):
        """
        Returns the bounding box of the given object.

        :param transformed: whether this is the transformed bounds or default.
        :return:
        """
        raise NotImplementedError

    @property
    def rotation(self):
        if not self.apply:
            return Angle.degrees(0)
        prx = Point(1, 0)
        prx *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.angle_to(prx)


class GraphicObject:
    """Any drawn element."""

    def __init__(self, *args, **kwargs):
        self.stroke = None
        self.fill = None
        self.stroke_width = None

    def property_by_object(self, s):
        self.fill = Color(s.fill) if s.fill is not None else None
        self.stroke = Color(s.stroke) if s.stroke is not None else None
        self.stroke_width = Length(s.stroke_width).value() if s.stroke_width is not None else None

    def property_by_values(self, values):
        stroke = values.get(SVG_ATTR_STROKE)
        self.stroke = Color(stroke) if stroke is not None else None
        stroke_opacity = values.get(SVG_ATTR_STROKE_OPACITY)
        if stroke_opacity is not None and self.stroke is not None and self.stroke.value is not None:
            try:
                self.stroke.opacity = float(stroke_opacity)
            except ValueError:
                pass
        fill = values.get(SVG_ATTR_FILL)
        self.fill = Color(fill) if fill is not None else None
        fill_opacity = values.get(SVG_ATTR_FILL_OPACITY)
        if fill_opacity is not None and self.fill is not None and self.fill.value is not None:
            try:
                self.fill.opacity = float(fill_opacity)
            except ValueError:
                pass
        self.stroke_width = Length(values.get(SVG_ATTR_STROKE_WIDTH, 1.0)).value()

    def render(self, **kwargs):
        if isinstance(self.stroke_width, Length):
            width = kwargs.get('width', kwargs.get('relative_length'))
            height = kwargs.get('height', kwargs.get('relative_length'))
            try:
                del kwargs['relative_length']
            except KeyError:
                pass
            self.stroke_width = self.stroke_width.value(relative_length=sqrt(width * width + height * height), **kwargs)
            # A percentage stroke_width is always computed as a percentage of the normalized viewBox diagonal length.

    def reify(self):
        """
        Realizes the transform to the attributes. Such that the attributes become actualized and the transform
        simplifies towards the identity matrix. In many cases it will become the identity matrix. In other cases the
        transformed shape cannot be represented through the properties alone. And shall keep those parts of the
        transform required preserve equivalency.
        """
        self.stroke_width = self.implicit_stroke_width
        return self

    @property
    def implicit_stroke_width(self):
        try:
            if not self.apply:
                return self.stroke_width
            if self.stroke_width is not None:
                if hasattr(self, 'values') and \
                        SVG_ATTR_VECTOR_EFFECT in self.values and \
                        SVG_VALUE_NON_SCALING_STROKE in self.values[SVG_ATTR_VECTOR_EFFECT]:
                    return self.stroke_width  # we are not to scale the stroke.
                width = self.stroke_width
                det = self.transform.determinant
                return width * sqrt(abs(det))
        except AttributeError:
            return self.stroke_width


class Shape(SVGElement, GraphicObject, Transformable):
    """
    SVG Shapes are several SVG items defined in SVG 1.1 9.1
    https://www.w3.org/TR/SVG11/shapes.html

    These shapes are circle, ellipse, line, polyline, polygon, and path.

    All shapes have methods:
    d(relative, transform): provides path_d string for the shape.
    reify(): Applies transform of the shape to modify the shape attributes.
    render(): Ensure that the shape properties have real space values.
    bbox(transformed): Provides the bounding box for the given shape.

    All shapes must implement:
    __repr__(), with a call to _repr_shape()
    __copy__()

    All shapes have attributes:
    id: SVG ID attributes. (SVGElement)
    transform: SVG Matrix to apply to this shape. (Transformable)
    apply: Determine whether transform should be applied. (Transformable)
    fill: SVG color of the shape fill. (GraphicObject)
    stroke: SVG color of the shape stroke. (GraphicObject)
    stroke_width: Stroke width of the stroke. (GraphicObject)
    """

    def __init__(self, *args, **kwargs):
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)
        SVGElement.__init__(self, *args, **kwargs)  # Must go last, triggers, by_object, by_value, by_arg functions.

    def property_by_object(self, s):
        SVGElement.property_by_object(self, s)
        Transformable.property_by_object(self, s)
        GraphicObject.property_by_object(self, s)

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        Transformable.property_by_values(self, values)
        GraphicObject.property_by_values(self, values)

    def render(self, **kwargs):
        SVGElement.render(self, **kwargs)
        Transformable.render(self, **kwargs)
        GraphicObject.render(self, **kwargs)

    def __eq__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        if self.fill != other.fill or self.stroke != other.stroke:
            return False
        first = self
        if not isinstance(first, Path):
            first = Path(first)
        second = other
        if not isinstance(second, Path):
            second = Path(second)
        return first == second

    def __ne__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        return not self == other

    def __iadd__(self, other):
        if isinstance(other, Shape):
            return Path(self) + Path(other)
        return NotImplemented

    __add__ = __iadd__

    def __matmul__(self, other):
        m = copy(self)
        m.__imatmul__(other)
        return m

    def __rmatmul__(self, other):
        m = copy(other)
        m.__imatmul__(self)
        return m

    def __imatmul__(self, other):
        """
        The % operation with a matrix works much like multiplication except that it automatically reifies the shape.
        """
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            self.transform *= other
        self.reify()
        return self

    def _calc_lengths(self, error=ERROR, min_depth=MIN_DEPTH, segments=None):
        """
        Calculate the length values for the segments of the Shape.

        :param error: error permitted for length calculations.
        :param min_depth: minimum depth for the length calculation.
        :param segments: optional segments to use.
        :return:
        """
        if segments is None:
            segments = self.segments(False)
        if self._length is not None:
            return
        lengths = [each.length(error=error, min_depth=min_depth) for each in segments]
        self._length = sum(lengths)
        if self._length == 0:
            self._lengths = lengths
        else:
            self._lengths = [each / self._length for each in lengths]

    def npoint(self, positions, error=ERROR):
        """
        Find a points between 0 and 1 within the shape. Numpy acceleration allows points to be an array of floats.
        """
        try:
            import numpy as np
        except ImportError:
            return [self.point(pos) for pos in positions]

        segments = self.segments(False)
        if len(segments) == 0:
            return None
        # Shortcuts
        if self._length is None:
            self._calc_lengths(error=error, segments=segments)
        xy = np.empty((len(positions), 2), dtype=float)
        if self._length == 0:
            i = int(round(positions * (len(segments) - 1)))
            point = segments[i].point(0.0)
            xy[:] = point
            return xy

        # Find which segment the point we search for is located on:
        segment_start = 0
        for index, segment in enumerate(segments):
            segment_end = segment_start + self._lengths[index]
            position_subset = ((segment_start <= positions) & (positions < segment_end))
            v0 = positions[position_subset]
            if not len(v0):
                continue  # Nothing matched.
            d = segment_end - segment_start
            if d == 0:  # This segment is 0 length.
                segment_pos = 0.0
            else:
                segment_pos = (v0 - segment_start) / d
            c = segment.npoint(segment_pos)
            xy[position_subset] = c[:]
            segment_start = segment_end

        # the loop above will miss position == 1
        xy[positions == 1] = np.array(list(segments[-1].end))
        return xy

    def point(self, position, error=ERROR):
        """
        Find a point between 0 and 1 within the Shape, going through the shape with regard to position.

        :param position: value between 0 and 1 within the shape.
        :param error: Length error permitted.
        :return: Point at the given location.
        """
        segments = self.segments(False)
        if len(segments) == 0:
            return None
        # Shortcuts
        try:
            if position <= 0.0:
                return segments[0].point(position)
            if position >= 1.0:
                return segments[-1].point(position)
        except ValueError:
            return self.npoint([position], error=error)[0]

        if self._length is None:
            self._calc_lengths(error=error, segments=segments)

        if self._length == 0:
            i = int(round(position * (len(segments) - 1)))
            return segments[i].point(0.0)
        # Find which segment the point we search for is located on:
        segment_start = 0
        segment_pos = 0
        segment = segments[0]
        for index, segment in enumerate(segments):
            segment_end = segment_start + self._lengths[index]
            if segment_end >= position:
                # This is the segment! How far in on the segment is the point?
                segment_pos = (position - segment_start) / (segment_end - segment_start)
                break
            segment_start = segment_end
        return segment.point(segment_pos)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        self._calc_lengths(error, min_depth)
        return self._length

    def segments(self, transformed=True):
        """
        Returns PathSegments which correctly produce this shape.

        This should be implemented by subclasses.
        """
        raise NotImplementedError

    def d(self, relative=False, transformed=True):
        """
        Returns the path_d string of the shape.

        :param relative: Returns path_d in relative form.
        :param transformed: Return path_d, with applied transform.
        :return: path_d string
        """
        return Path(self.segments(transformed=transformed)).d(relative=relative)

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given shape.
        """
        bbs = [seg.bbox() for seg in self.segments(transformed=False) if not isinstance(Close, Move)]
        try:
            xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        except ValueError:
            return None  # No bounding box items existed. So no bounding box.
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        if transformed:
            p0 = self.transform.transform_point([xmin, ymin])
            p1 = self.transform.transform_point([xmin, ymax])
            p2 = self.transform.transform_point([xmax, ymin])
            p3 = self.transform.transform_point([xmax, ymax])
            xmin = min(p0[0], p1[0], p2[0], p3[0])
            ymin = min(p0[1], p1[1], p2[1], p3[1])
            xmax = max(p0[0], p1[0], p2[0], p3[0])
            ymax = max(p0[1], p1[1], p2[1], p3[1])
        return xmin, ymin, xmax, ymax

    def _init_shape(self, *args):
        """
        Generic SVG parsing of args. In those cases where the shape accepts finite elements we can process the last
        four elements of the shape with this code. This will happen in simpleline, roundshape, and rect. It will not
        happen in polyshape or paths since these can accept infinite arguments.
        """

        arg_length = len(args)

        if arg_length >= 1:
            if args[0] is not None:
                self.transform = Matrix(args[0])
        if arg_length >= 2:
            if args[1] is not None:
                self.stroke = Color(args[1])
        if arg_length >= 3:
            if args[2] is not None:
                self.fill = Color(args[2])
        if arg_length >= 4:
            if args[3] is not None:
                self.apply = bool(args[3])

    def _repr_shape(self, values):
        """
        Generic pieces of repr shape.
        """
        if not self.transform.is_identity():
            values.append('transform=%s' % repr(self.transform))
        if self.stroke is not None:
            values.append('stroke=\'%s\'' % self.stroke)
        if self.fill is not None:
            values.append('fill=\'%s\'' % self.fill)
        if self.stroke_width is not None and self.stroke_width != 1.0:
            values.append('stroke_width=\'%s\'' % str(self.stroke_width))
        if self.apply is not None and not self.apply:
            values.append('apply=%s' % self.apply)
        if self.id is not None:
            values.append('id=\'%s\'' % self.id)

    def _name(self):
        return self.__class__.__name__


class PathSegment:
    """
    Path Segments are the base class for all the segment within a Path.
    These are defined in SVG 1.1 8.3 and SVG 2.0 9.3
    https://www.w3.org/TR/SVG11/paths.html#PathData
    https://www.w3.org/TR/SVG2/paths.html#PathElement

    These segments define a 1:1 relationship with the path_d or path data attribute, denoted in
    SVG by the 'd' attribute. These are moveto, closepath, lineto, and the curves which are cubic
    bezier curves, quadratic bezier curves, and elliptical arc. These are classed as Move, Close,
    Line, CubicBezier, QuadraticBezier, and Arc. And in path_d are denoted as M, Z, L, C, Q, A.

    There are lowercase versions of these commands. And for C, and Q there are S and T which are
    smooth versions. For lines there are also V and H commands which denote vertical and horizontal
    versions of the line command.

    The major difference between paths in 1.1 and 2.0 is the use of Z to truncate a command to close.
    "M0,0C 0,100 100,0 z is valid in 2.0 since the last z replaces the 0,0. These are read by
    svg.elements but they are not written.
    """

    def __init__(self, **kwargs):
        try:
            self.relative = bool(kwargs['relative'])
        except (KeyError, ValueError):
            self.relative = False
        try:
            self.smooth = bool(kwargs['smooth'])
        except (KeyError, ValueError):
            self.smooth = True
        self.start = None
        self.end = None

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n
        return NotImplemented

    __rmul__ = __mul__

    def __iadd__(self, other):
        if isinstance(other, PathSegment):
            path = Path(self, other)
            return path
        elif isinstance(other, str):
            path = Path(self) + other
            return path
        return NotImplemented

    __add__ = __iadd__

    def __str__(self):
        """
        This defines an individual path segment string. Since this isn't part of a Path it appends a pseudo-Move
        command to correctly provide the starting position.
        :return: string representation of the object.
        """
        d = self.d()
        if self.start is not None:
            if self.relative:
                return 'm %s %s' % (self.start, d)
            else:
                return 'M %s %s' % (self.start, d)
        return d

    def __iter__(self):
        self.n = -1
        return self

    def __next__(self):
        self.n += 1
        try:
            val = self[self.n]
            if val is None:
                self.n += 1
                val = self[self.n]
            return val
        except IndexError:
            raise StopIteration

    next = __next__

    @staticmethod
    def segment_length(curve, start=0.0, end=1.0, start_point=None, end_point=None, error=ERROR, min_depth=MIN_DEPTH,
                       depth=0):
        """Recursively approximates the length by straight lines"""
        if start_point is None:
            start_point = curve.point(start)
        if end_point is None:
            end_point = curve.point(end)
        mid = (start + end) / 2
        mid_point = curve.point(mid)
        length = abs(end_point - start_point)
        first_half = abs(mid_point - start_point)
        second_half = abs(end_point - mid_point)

        length2 = first_half + second_half
        if (length2 - length > error) or (depth < min_depth):
            # Calculate the length of each segment:
            depth += 1
            return (PathSegment.segment_length(curve, start, mid, start_point, mid_point,
                                               error, min_depth, depth) +
                    PathSegment.segment_length(curve, mid, end, mid_point, end_point,
                                               error, min_depth, depth))
        # This is accurate enough.
        return length2

    def _line_length(self, start=0.0, end=1.0, error=ERROR, min_depth=MIN_DEPTH):
        return PathSegment.segment_length(self, start, end, error=error, min_depth=min_depth)

    def bbox(self):
        """returns the bounding box for the segment.
        xmin, ymin, xmax, ymax
        """
        xs = [p.x for p in self if p is not None]
        ys = [p.y for p in self if p is not None]
        xmin = min(xs)
        xmax = max(xs)
        ymin = min(ys)
        ymax = max(ys)
        return xmin, ymin, xmax, ymax

    def reverse(self):
        """
        Reverses the current path segment.
        """
        end = self.end
        self.end = self.start
        self.start = end

    def point(self, position):
        """
        Returns the point at a given amount through the path segment.
        :param position:  t value between 0 and 1
        :return: Point instance
        """
        return Point(self.npoint([position])[0])

    def npoint(self, positions):
        """
        Returns the points at given positions along the path segment
        :param positions: N-sized sequence of t value between 0 and 1
        :return: N-sized sequence of 2-sized sequence of float
        """
        return [self.end] * len(positions)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """
        Returns the length of this path segment.

        :param error:
        :param min_depth:
        :return:
        """
        return 0

    def d(self, current_point=None, relative=None, smooth=None):
        """Returns the fragment path_d value for the current path segment.

        For a relative segment the current_point must be provided. If it is omitted then only an absolute segment
        can be returned."""
        raise NotImplementedError


class Move(PathSegment):
    """Represents move commands. Moves to a new location without any path distance.
    Paths that consist of only move commands, are valid.

    Move serve to make discontinuous paths into continuous linked paths segments
    with non-drawn sections.
    """

    def __init__(self, *args, **kwargs):
        """
        Move commands most importantly go to a place. So if one location is given, that's the end point.
        If two locations are given then first is the start location.

        For many Move commands it is not necessary to have an original start location. The start point provides a
        linked locations for some elements that may require it. If known it can be provided.

        Move(p) where p is the End point.
        Move(s,e) where s is the Start point, e is the End point.
        Move(p, start=s) where p is End point, s is the Start point.
        Move(p, end=e) where p is the Start point, e is the End point.
        Move(start=s, end=e) where s is the Start point, e is the End point.
        """
        PathSegment.__init__(self, **kwargs)
        self.end = None
        self.start = None
        if len(args) == 0:
            if 'end' in kwargs:
                self.end = kwargs['end']
            if 'start' in kwargs:
                self.start = kwargs['start']
        elif len(args) == 1:
            if len(kwargs) == 0:
                self.end = args[0]
            else:
                if 'end' in kwargs:
                    self.start = args[0]
                    self.end = kwargs['end']
                elif 'start' in kwargs:
                    self.start = kwargs['start']
                    self.end = args[0]
        elif len(args) == 2:
            self.start = args[0]
            self.end = args[1]
        if self.start is not None:
            self.start = Point(self.start)
        if self.end is not None:
            self.end = Point(self.end)

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __repr__(self):
        if self.start is None:
            return 'Move(end=%s)' % repr(self.end)
        else:
            return 'Move(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def __copy__(self):
        return Move(self.start, self.end, relative=self.relative)

    def __eq__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return not self == other

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def d(self, current_point=None, relative=None, smooth=None):
        if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
            return 'M %s' % self.end
        return 'm %s' % (self.end - current_point)


class Curve(PathSegment):
    """Represents curve commands"""

    def __init__(self, start=None, end=None, **kwargs):
        PathSegment.__init__(self, **kwargs)
        self.start = Point(start) if start is not None else None
        self.end = Point(end) if end is not None else None


class Linear(PathSegment):
    """Represents line commands."""

    def __init__(self, start=None, end=None, **kwargs):
        PathSegment.__init__(self, **kwargs)
        self.start = Point(start) if start is not None else None
        self.end = Point(end) if end is not None else None

    def __copy__(self):
        return self.__class__(self.start, self.end, relative=self.relative)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        else:
            raise IndexError

    def npoint(self, positions):
        try:
            import numpy as np
            xy = np.empty(shape=(len(positions), 2), dtype=float)
            xy[:, 0] = np.interp(positions, [0, 1], [self.start.x, self.end.x])
            xy[:, 1] = np.interp(positions, [0, 1], [self.start.y, self.end.y])
            return xy
        except ImportError:
            return [Point.towards(self.start, self.end, pos) for pos in positions]

    def length(self, error=None, min_depth=None):
        if self.start is not None and self.end is not None:
            return Point.distance(self.end, self.start)
        else:
            return 0

    def closest_segment_point(self, p, respect_bounds=True):
        """ Gives the point on the line closest to the given point. """
        a = self.start
        b = self.end
        vAPx = p[0] - a.x
        vAPy = p[1] - a.y
        vABx = b.x - a.x
        vABy = b.y - a.y
        sqDistanceAB = vABx * vABx + vABy * vABy
        ABAPproduct = vABx * vAPx + vABy * vAPy
        if sqDistanceAB == 0:
            return 0  # Line is point.
        amount = ABAPproduct / sqDistanceAB
        if respect_bounds:
            if amount > 1:
                amount = 1
            if amount < 0:
                amount = 0
        return self.point(amount)

    def d(self, current_point=None, relative=None, smooth=None):
        raise NotImplementedError


class Close(Linear):
    """Represents close commands. If this exists at the end of the shape then the shape is closed.
    the methodology of a single flag close fails in a couple ways. You can have multi-part shapes
    which can close or not close several times.
    """

    def __repr__(self):
        if self.start is None and self.end is None:
            return 'Close()'
        s = self.start
        if s is not None:
            s = repr(s)
        e = self.end
        if e is not None:
            e = repr(e)
        return 'Close(start=%s, end=%s)' % (s, e)

    def d(self, current_point=None, relative=None, smooth=None):
        if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
            return 'Z'
        else:
            return 'z'


class Line(Linear):
    """Represents line commands."""

    def __repr__(self):
        if self.start is None:
            return 'Line(end=%s)' % (repr(self.end))
        return 'Line(start=%s, end=%s)' % (repr(self.start), repr(self.end))

    def d(self, current_point=None, relative=None, smooth=None):
        if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
            return 'L %s' % self.end
        else:
            return 'l %s' % (self.end - current_point)


class QuadraticBezier(Curve):
    """Represents Quadratic Bezier commands."""

    def __init__(self, start, control, end, **kwargs):
        Curve.__init__(self, start, end, **kwargs)
        self.control = Point(control) if control is not None else None

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
            repr(self.start), repr(self.control), repr(self.end))

    def __copy__(self):
        return QuadraticBezier(self.start, self.control, self.end, relative=self.relative, smooth=self.smooth)

    def __eq__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control == other.control

    def __ne__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.control is not None:
                self.control *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 3

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.control
        elif item == 2:
            return self.end
        raise IndexError

    def npoint(self, positions):
        """Calculate the x,y position at a certain position of the path. `pos` may be a
        float or a NumPy array."""
        x0, y0 = self.start
        x1, y1 = self.control
        x2, y2 = self.end

        def _compute_point(position):
            # compute factors
            n_pos = 1 - position
            pos_2 = position ** 2
            n_pos_2 = n_pos ** 2
            n_pos_pos = n_pos * position

            return (n_pos_2 * x0 + 2 * n_pos_pos * x1 + pos_2 * x2,
                    n_pos_2 * y0 + 2 * n_pos_pos * y1 + pos_2 * y2)

        try:
            import numpy as np
            xy = np.empty(shape=(len(positions), 2))
            xy[:, 0], xy[:, 1] = _compute_point(np.array(positions))
            return xy
        except ImportError:
            return [Point(*_compute_point(position)) for position in positions]

    def bbox(self):
        """
        Returns the bounding box for the quadratic bezier curve.
        """
        n = self.start.x - self.control.x
        d = self.start.x - 2 * self.control.x + self.end.x
        if d != 0:
            t = n / d
        else:
            t = 0.5
        if 0 < t < 1:
            x_values = [self.start.x, self.end.x, self.point(t).x]
        else:
            x_values = [self.start.x, self.end.x]
        n = self.start.y - self.control.y
        d = self.start.y - 2 * self.control.y + self.end.y
        if d != 0:
            t = n / d
        else:
            t = 0.5
        if 0 < t < 1:
            y_values = [self.start.y, self.end.y, self.point(t).y]
        else:
            y_values = [self.start.y, self.end.y]
        return min(x_values), min(y_values), max(x_values), max(y_values)

    def length(self, error=None, min_depth=None):
        """Calculate the length of the path up to a certain position"""
        a = self.start - 2 * self.control + self.end
        b = 2 * (self.control - self.start)
        try:
            # For an explanation of this case, see
            # http://www.malczak.info/blog/quadratic-bezier-curve-length/
            A = 4 * (a.real ** 2 + a.imag ** 2)
            B = 4 * (a.real * b.real + a.imag * b.imag)
            C = b.real ** 2 + b.imag ** 2

            Sabc = 2 * sqrt(A + B + C)
            A2 = sqrt(A)
            A32 = 2 * A * A2
            C2 = 2 * sqrt(C)
            BA = B / A2

            s = (A32 * Sabc + A2 * B * (Sabc - C2) + (4 * C * A - B ** 2) *
                 log((2 * A2 + BA + Sabc) / (BA + C2))) / (4 * A32)
        except (ZeroDivisionError, ValueError):
            # a_dot_b = a.real * b.real + a.imag * b.imag
            if abs(a) < 1e-10:
                s = abs(b)
            else:
                k = abs(b) / abs(a)
                if k >= 2:
                    s = abs(b) - abs(a)
                else:
                    s = abs(a) * (k ** 2 / 2 - k + 1)
        return s

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, QuadraticBezier):
            return (self.start == previous.end and
                    (self.control - self.start) == (previous.end - previous.control))
        else:
            return self.control == self.start

    def d(self, current_point=None, relative=None, smooth=None):
        if (smooth is None and self.smooth) or (smooth is not None and smooth):
            if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
                return 'T %s' % self.end
            else:
                return 't %s' % (self.end - current_point)
        else:
            if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
                return 'Q %s %s' % (self.control, self.end)
            else:
                return 'q %s %s' % (self.control - current_point, self.end - current_point)


class CubicBezier(Curve):
    """Represents Cubic Bezier commands."""

    def __init__(self, start, control1, control2, end, **kwargs):
        Curve.__init__(self, start, end, **kwargs)
        self.control1 = Point(control1) if control1 is not None else None
        self.control2 = Point(control2) if control1 is not None else None

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
            repr(self.start), repr(self.control1), repr(self.control2), repr(self.end))

    def __copy__(self):
        return CubicBezier(self.start, self.control1, self.control2, self.end, relative=self.relative,
                           smooth=self.smooth)

    def __eq__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control1 == other.control1 and self.control2 == other.control2

    def __ne__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.control1 is not None:
                self.control1 *= other
            if self.control2 is not None:
                self.control2 *= other
            if self.end is not None:
                self.end *= other
        return self

    def __len__(self):
        return 4

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.control1
        elif item == 2:
            return self.control2
        elif item == 3:
            return self.end
        else:
            raise IndexError

    def reverse(self):
        PathSegment.reverse(self)
        c2 = self.control2
        self.control2 = self.control1
        self.control1 = c2

    def npoint(self, positions):
        """Calculate the x,y position at a certain position of the path. `pos` may be a
        float or a NumPy array."""
        x0, y0 = self.start
        x1, y1 = self.control1
        x2, y2 = self.control2
        x3, y3 = self.end

        def _compute_point(position):
            # compute factors
            pos_3 = position ** 3
            n_pos = 1 - position
            n_pos_3 = n_pos ** 3
            pos_2_n_pos = position * position * n_pos
            n_pos_2_pos = n_pos * n_pos * position
            return (n_pos_3 * x0 + 3 * (n_pos_2_pos * x1 + pos_2_n_pos * x2) + pos_3 * x3,
                    n_pos_3 * y0 + 3 * (n_pos_2_pos * y1 + pos_2_n_pos * y2) + pos_3 * y3)

        try:
            import numpy as np
            xy = np.empty(shape=(len(positions), 2))
            xy[:, 0], xy[:, 1] = _compute_point(np.array(positions))
            return xy
        except ImportError:
            return [Point(*_compute_point(position)) for position in positions]

    def bbox(self):
        """returns the tight fitting bounding box of the bezier curve.
        Code by:
        https://github.com/mathandy/svgpathtools
        """
        xmin, xmax = self._real_minmax(0)
        ymin, ymax = self._real_minmax(1)
        return xmin, ymin, xmax, ymax

    def _real_minmax(self, v):
        """returns the minimum and maximum for a real cubic bezier, with a non-zero denom
        Code by:
        https://github.com/mathandy/svgpathtools
        """
        local_extremizers = [0, 1]
        a = [c[v] for c in self]
        denom = a[0] - 3 * a[1] + 3 * a[2] - a[3]
        if abs(denom) >= 1e-12:
            delta = a[1] ** 2 - \
                    (a[0] + a[1]) * a[2] + \
                    a[2] ** 2 + \
                    (a[0] - a[1]) * a[3]
            if delta >= 0:  # otherwise no local extrema
                sqdelta = sqrt(delta)
                tau = a[0] - 2 * a[1] + a[2]
                r1 = (tau + sqdelta) / denom
                r2 = (tau - sqdelta) / denom
                if 0 < r1 < 1:
                    local_extremizers.append(r1)
                if 0 < r2 < 1:
                    local_extremizers.append(r2)
        else:
            local_extremizers.append(0.5)
        local_extrema = [self.point(t)[v] for t in local_extremizers]
        return min(local_extrema), max(local_extrema)

    def _length_scipy(self, error=ERROR):
        from scipy.integrate import quad

        p0 = complex(*self.start)
        p1 = complex(*self.control1)
        p2 = complex(*self.control2)
        p3 = complex(*self.end)

        def _abs_derivative(t):
            return abs(3 * (p1 - p0) * (1 - t) ** 2 + 6 * (p2 - p1) * (1 - t) * t + 3 \
                       * (p3 - p2) * t ** 2)

        return quad(_abs_derivative, 0., 1., epsabs=error, limit=1000)[0]

    def _length_default(self, error=ERROR, min_depth=MIN_DEPTH):
        return self._line_length(0, 1, error, min_depth)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """Calculate the length of the path up to a certain position"""
        try:
            return self._length_scipy(error)
        except ImportError:
            return self._length_default(error, min_depth)

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, CubicBezier):
            return (self.start == previous.end and
                    (self.control1 - self.start) == (previous.end - previous.control2))
        else:
            return self.control1 == self.start

    def d(self, current_point=None, relative=None, smooth=None):
        if (smooth is None and self.smooth) or (smooth is not None and smooth):
            if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
                return 'S %s %s' % (self.control2, self.end)
            else:
                return 's %s %s' % (self.control2 - current_point, self.end - current_point)
        else:
            if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
                return 'C %s %s %s' % (self.control1, self.control2, self.end)
            else:
                return 'c %s %s %s' % (
                    self.control1 - current_point, self.control2 - current_point, self.end - current_point)


class Arc(Curve):
    def __init__(self, *args, **kwargs):
        """
        Represents Arc commands.

        Arc objects can take different parameters to create arcs.
        Since we expect taking in SVG parameters. We accept SVG parameterization which is:
        start, rx, ry, rotation, arc_flag, sweep_flag, end.

        To do matrix transitions, the native parameterization is start, end, center, prx, pry, sweep

        'start, end, center, prx, pry' are points and sweep amount is a t value in tau radians.
        If points are modified by an affine transformation, the arc is transformed.
        There is a special case for when the scale factor inverts, it inverts the sweep.

        Note: t-values are not angles from center in elliptical arcs. These are the same thing in
        circular arcs. But, here t is a parameterization around the ellipse, as if it were a circle.
        The position on the arc is (a * cos(t), b * sin(t)). If r-major was 0 for example. The
        positions would all fall on the x-axis. And the angle from center would all be either 0 or
        tau/2. However, since t is the parameterization we can conceptualize it as a position on a
        circle which is then scaled and rotated by a matrix.

        prx is the point at t 0 in the ellipse.
        pry is the point at t tau/4 in the ellipse.
        prx -> center -> pry should form a right triangle.

        The rotation can be defined as the angle from center to prx. Since prx is located at
        t(0) its deviation can only be the result of a rotation.

        Sweep is a value in t.
        The sweep angle can be a value greater than tau and less than -tau.
        However if this is the case, conversion back to Path.d() is expected to fail.
        We can denote these arc events but not as a single command.

        start_t + sweep = end_t
        """
        Curve.__init__(self, **kwargs)
        self.center = None
        self.prx = None
        self.pry = None
        self.sweep = None
        if len(args) == 6 and isinstance(args[1], complex):
            self._svg_complex_parameterize(*args)
            return
        elif len(kwargs) == 6 and 'rotation' in kwargs:
            self._svg_complex_parameterize(**kwargs)
            return
        elif len(args) == 7:
            # This is an svg parameterized call.
            # A: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            self._svg_parameterize(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
            return
        if 'left' in kwargs and 'right' in kwargs and 'top' in kwargs and 'bottom' in kwargs:
            left = kwargs['left']
            right = kwargs['right']
            top = kwargs['top']
            bottom = kwargs['bottom']
            self.center = Point((left + right) / 2.0, (top + bottom) / 2.0)
            rx = (right - left) / 2.0
            ry = (bottom - top) / 2.0
            self.prx = Point(self.center.x + rx, self.center.y)
            self.pry = Point(self.center.x, self.center.y + ry)
        len_args = len(args)
        if len_args > 0:
            if args[0] is not None:
                self.start = Point(args[0])
        if len_args > 1:
            if args[1] is not None:
                self.end = Point(args[1])
        if len_args > 2:
            if args[2] is not None:
                self.center = Point(args[2])
        if len_args > 3:
            if args[3] is not None:
                self.prx = Point(args[3])
        if len_args > 4:
            if args[4] is not None:
                self.pry = Point(args[4])
        if len_args > 5:
            self.sweep = args[5]
            return  # The args gave us everything.
        if 'start' in kwargs:
            self.start = Point(kwargs['start'])
        if 'end' in kwargs:
            self.end = Point(kwargs['end'])
        if 'center' in kwargs:
            self.center = Point(kwargs['center'])
        if 'prx' in kwargs:
            self.prx = Point(kwargs['prx'])
        if 'pry' in kwargs:
            self.pry = Point(kwargs['pry'])
        if 'sweep' in kwargs:
            self.sweep = kwargs['sweep']
        cw = True  # Clockwise default. (sometimes needed)
        if self.start is not None and self.end is not None and self.center is None:
            # Start and end, but no center.
            # Solutions require a radius, a control point, or a bulge
            control = None
            sagitta = None
            if 'bulge' in kwargs:
                bulge = float(kwargs['bulge'])
                sagitta = bulge * self.start.distance_to(self.end) / 2.0
            elif 'sagitta' in kwargs:
                sagitta = float(kwargs['sagitta'])
            if sagitta is not None:
                control = Point.towards(self.start, self.end, 0.5)
                angle = self.start.angle_to(self.end)
                control = control.polar_to(angle - tau / 4, sagitta)
            if 'control' in kwargs:  # Control is any additional point on the arc.
                control = Point(kwargs['control'])
            if control is not None:
                delta_a = control - self.start
                delta_b = self.end - control
                try:
                    slope_a = delta_a.y / delta_a.x
                except ZeroDivisionError:
                    slope_a = float('inf')
                try:
                    slope_b = delta_b.y / delta_b.x
                except ZeroDivisionError:
                    slope_b = float('inf')
                ab_mid = Point.towards(self.start, control, 0.5)
                bc_mid = Point.towards(control, self.end, 0.5)
                if delta_a.y == 0:  # slope_a == 0
                    cx = ab_mid.x
                    if delta_b.x == 0:  # slope_b == inf
                        cy = bc_mid.y
                    else:
                        cy = bc_mid.y + (bc_mid.x - cx) / slope_b
                elif delta_b.y == 0:  # slope_b == 0
                    cx = bc_mid.x
                    if delta_a.y == 0:  # slope_a == inf
                        cy = ab_mid.y
                    else:
                        cy = ab_mid.y + (ab_mid.x - cx) / slope_a
                elif delta_a.x == 0:  # slope_a == inf
                    cy = ab_mid.y
                    cx = slope_b * (bc_mid.y - cy) + bc_mid.x
                elif delta_b.x == 0:  # slope_b == inf
                    cy = bc_mid.y
                    cx = slope_a * (ab_mid.y - cy) + ab_mid.x
                elif slope_a == slope_b:
                    cx = ab_mid.x
                    cy = ab_mid.y
                else:
                    cx = (slope_a * slope_b * (ab_mid.y - bc_mid.y)
                          - slope_a * bc_mid.x
                          + slope_b * ab_mid.x) / (slope_b - slope_a)
                    cy = ab_mid.y - (cx - ab_mid.x) / slope_a
                self.center = Point(cx, cy)
                cw = bool(Point.orientation(self.start, control, self.end) == 2)
            elif 'r' in kwargs:
                r = kwargs['r']
                mid = Point((self.start.x + self.end.x) / 2.0, (self.start.y + self.end.y) / 2.0)
                q = Point.distance(self.start, self.end)
                hq = q / 2.0
                if r < hq:
                    kwargs['r'] = r = hq  # Correct potential math domain error.
                self.center = Point(
                    mid.x + sqrt(r ** 2 - hq ** 2) * (self.start.y - self.end.y) / q,
                    mid.y + sqrt(r ** 2 - hq ** 2) * (self.end.x - self.start.x) / q
                )
                cw = bool(Point.orientation(self.start, self.center, self.end) == 1)
                if 'ccw' in kwargs and kwargs['ccw'] and cw or not cw:
                    # ccw arg exists, is true, and we found the cw center, or we didn't find the cw center.
                    self.center = Point(
                        mid.x - sqrt(r ** 2 - hq ** 2) * (self.start.y - self.end.y) / q,
                        mid.y - sqrt(r ** 2 - hq ** 2) * (self.end.x - self.start.x) / q
                    )
            elif 'rx' in kwargs and 'ry' in kwargs:
                # This formulation will assume p1 and p2 are both axis aligned.
                rx = kwargs['rx']
                ry = kwargs['ry']
                # We will assume rx == abs(self.start.x - self.end.x)
                self.center = Point(self.start.x, self.end.y)
                cw = bool(Point.orientation(self.start, self.center, self.end) == 1)
                if 'ccw' in kwargs and kwargs['ccw'] and cw or not cw:
                    self.center = Point(self.end.x, self.start.y)
                self.sweep = tau / 4.0

        if self.center is None:
            raise ValueError("Not enough values to solve for center.")
        if 'r' in kwargs:
            r = kwargs['r']
            if self.prx is None:
                self.prx = Point(self.center.x + r, self.center.y)
            if self.pry is None:
                self.pry = Point(self.center.x, self.center.y + r)
        if 'rx' in kwargs:
            rx = kwargs['rx']
            if self.prx is None:
                if 'rotation' in kwargs:
                    theta = kwargs['rotation']
                    self.prx = Point.polar(self.center, theta, rx)
                else:
                    self.prx = Point(self.center.x + rx, self.center.y)
        if 'ry' in kwargs:
            ry = kwargs['ry']
            if self.pry is None:
                if 'rotation' in kwargs:
                    theta = kwargs['rotation']
                    theta += tau / 4.0
                    self.pry = Point.polar(self.center, theta, ry)
                else:
                    self.pry = Point(self.center.x, self.center.y + ry)
        if self.start is not None and (self.prx is None or self.pry is None):
            radius_s = Point.distance(self.center, self.start)
            self.prx = Point(self.center.x + radius_s, self.center.y)
            self.pry = Point(self.center.x, self.center.y + radius_s)
        if self.end is not None and (self.prx is None or self.pry is None):
            radius_e = Point.distance(self.center, self.end)
            self.prx = Point(self.center.x + radius_e, self.center.y)
            self.pry = Point(self.center.x, self.center.y + radius_e)
        if self.sweep is None and self.start is not None and self.end is not None:
            start_t = self.get_start_t()
            end_t = self.get_end_t()
            self.sweep = end_t - start_t
            if 'ccw' in kwargs:
                cw = not bool(kwargs['ccw'])
            if cw and self.sweep < 0:
                self.sweep += tau
            if not cw and self.sweep > 0:
                self.sweep -= tau
        if self.sweep is not None and self.start is not None and self.end is None:
            start_t = self.get_start_t()
            end_t = start_t + self.sweep
            self.end = self.point_at_t(end_t)
        if self.sweep is not None and self.start is None and self.end is not None:
            end_t = self.get_end_t()
            start_t = end_t - self.sweep
            self.end = self.point_at_t(start_t)

    def __repr__(self):
        return 'Arc(%s, %s, %s, %s, %s, %s)' % (
            repr(self.start), repr(self.end), repr(self.center), repr(self.prx), repr(self.pry), self.sweep)

    def __copy__(self):
        return Arc(self.start, self.end, self.center, self.prx, self.pry, self.sweep, relative=self.relative)

    def __eq__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.prx == other.prx and self.pry == other.pry and \
               self.center == other.center and self.sweep == other.sweep

    def __ne__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return not self == other

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            if self.start is not None:
                self.start *= other
            if self.center is not None:
                self.center *= other
            if self.end is not None:
                self.end *= other
            if self.prx is not None:
                self.prx *= other
            if self.pry is not None:
                self.pry *= other
            if other.value_scale_x() < 0:
                self.sweep = -self.sweep
            if other.value_scale_y() < 0:
                self.sweep = -self.sweep
        return self

    def __len__(self):
        return 5

    def __getitem__(self, item):
        if item == 0:
            return self.start
        elif item == 1:
            return self.end
        elif item == 2:
            return self.center
        elif item == 3:
            return self.prx
        elif item == 4:
            return self.pry
        raise IndexError

    @property
    def theta(self):
        """legacy property"""
        return Angle.radians(self.get_start_t()).as_positive_degrees

    @property
    def delta(self):
        """legacy property"""
        return Angle.radians(self.sweep).as_degrees

    def reverse(self):
        PathSegment.reverse(self)
        self.sweep = -self.sweep

    def npoint(self, positions):
        try:
            import numpy as np
            return self._points_numpy(np.array(positions))
        except ImportError:
            if self.start == self.end and self.sweep == 0:
                # This is equivalent of omitting the segment
                return [self.start] * len(positions)

            start_t = self.get_start_t()
            return [self.start if pos == 0 else self.end if pos == 1 else
            self.point_at_t(start_t + self.sweep * pos) for pos in positions]

    def _points_numpy(self, positions):
        """Vectorized version of `point()`.

        :param positions: 1D numpy array of float in [0, 1]
        :return: 1D numpy array of complex
        """
        import numpy as np
        xy = np.empty((len(positions), 2), dtype=float)

        if self.start == self.end and self.sweep == 0:
            xy[:, 0], xy[:, 1] = self.start
        else:
            t = self.get_start_t() + self.sweep * positions

            rotation = self.get_rotation()
            a = self.rx
            b = self.ry
            cx = self.center.x
            cy = self.center.y
            cos_rot = cos(rotation)
            sin_rot = sin(rotation)
            cos_t = np.cos(t)
            sin_t = np.sin(t)
            xy[:, 0] = cx + a * cos_t * cos_rot - b * sin_t * sin_rot
            xy[:, 1] = cy + a * cos_t * sin_rot + b * sin_t * cos_rot

            # ensure clean endings
            xy[positions == 0, :] = list(self.start)
            xy[positions == 1, :] = list(self.end)

        return xy

    def _integral_length(self):
        def ellipse_part_integral(t1, t2, a, b, n=100000):
            # function to integrate
            def f(t):
                return sqrt(1 - (1 - a ** 2 / b ** 2) * sin(t) ** 2)

            start = min(t1, t2)
            seg_len = abs(t1 - t2) / n
            return b * sum(f(start + seg_len * i) * seg_len for i in range(1, n + 1))

        start_angle = self.get_start_t()
        end_angle = start_angle + self.sweep
        return ellipse_part_integral(start_angle, end_angle, self.rx, self.ry)

    def _exact_length(self):
        """scipy is not a dependency. However, if scipy exists this function will find the
        exact arc length. By default .length() delegates to here and on failure uses the
        fallback method."""
        from scipy.special import ellipeinc
        a = self.rx
        b = self.ry
        phi = self.get_start_t()
        m = 1 - (a / b) ** 2
        d1 = ellipeinc(phi, m)
        phi = phi + self.sweep
        m = 1 - (a / b) ** 2
        d2 = ellipeinc(phi, m)
        return b * abs(d2 - d1)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """The length of an elliptical arc segment requires numerical
        integration, and in that case it's simpler to just do a geometric
        approximation, as for cubic bezier curves.
        """
        if self.sweep == 0:
            return 0
        if self.start == self.end and self.sweep == 0:
            # This is equivalent of omitting the segment
            return 0
        a = self.rx
        b = self.ry
        d = abs(a - b)

        if d < ERROR:  # This is a circle.
            return abs(self.rx * self.sweep)
        try:
            return self._exact_length()
        except ImportError:
            return self._line_length(error=error, min_depth=min_depth)

    def _svg_complex_parameterize(self, start, radius, rotation, arc_flag, sweep_flag, end):
        """Parameterization with complex radius and having rotation factors."""
        self._svg_parameterize(Point(start), radius.real, radius.imag, rotation, arc_flag, sweep_flag, Point(end))

    def _svg_parameterize(self, start, rx, ry, rotation, large_arc_flag, sweep_flag, end):
        """Conversion from svg parameterization, our chosen native native form.
        http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes """

        large_arc_flag = bool(large_arc_flag)
        sweep_flag = bool(sweep_flag)
        start = Point(start)
        self.start = start
        end = Point(end)
        self.end = end
        if start == end or rx == 0 or ry == 0:
            # If start is equal to end, there are infinite number of circles so these void out.
            # We still permit this kind of arc, but SVG parameterization cannot be used to achieve it.
            self.sweep = 0
            self.prx = Point(start)
            self.pry = Point(start)
            self.center = Point(start)
            return
        cosr = cos(radians(rotation))
        sinr = sin(radians(rotation))
        dx = (start.real - end.real) / 2
        dy = (start.imag - end.imag) / 2
        x1prim = cosr * dx + sinr * dy
        x1prim_sq = x1prim * x1prim
        y1prim = -sinr * dx + cosr * dy
        y1prim_sq = y1prim * y1prim

        rx_sq = rx * rx
        ry_sq = ry * ry

        # Correct out of range radii
        radius_check = (x1prim_sq / rx_sq) + (y1prim_sq / ry_sq)
        if radius_check > 1:
            rx *= sqrt(radius_check)
            ry *= sqrt(radius_check)
            rx_sq = rx * rx
            ry_sq = ry * ry

        t1 = rx_sq * y1prim_sq
        t2 = ry_sq * x1prim_sq
        c = sqrt(abs((rx_sq * ry_sq - t1 - t2) / (t1 + t2)))

        if large_arc_flag == sweep_flag:
            c = -c
        cxprim = c * rx * y1prim / ry
        cyprim = -c * ry * x1prim / rx

        center = Point((cosr * cxprim - sinr * cyprim) +
                       ((start.real + end.real) / 2),
                       (sinr * cxprim + cosr * cyprim) +
                       ((start.imag + end.imag) / 2))

        ux = (x1prim - cxprim) / rx
        uy = (y1prim - cyprim) / ry
        vx = (-x1prim - cxprim) / rx
        vy = (-y1prim - cyprim) / ry
        n = sqrt(ux * ux + uy * uy)
        p = ux
        theta = degrees(acos(p / n))
        if uy < 0:
            theta = -theta
        theta = theta % 360

        n = sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
        p = ux * vx + uy * vy
        d = p / n
        # In certain cases the above calculation can through inaccuracies
        # become just slightly out of range, f ex -1.0000000000000002.
        if d > 1.0:
            d = 1.0
        elif d < -1.0:
            d = -1.0
        delta = degrees(acos(d))
        if (ux * vy - uy * vx) < 0:
            delta = -delta
        delta = delta % 360
        if not sweep_flag:
            delta -= 360
        # built parameters, delta, theta, center

        rotate_matrix = Matrix()
        rotate_matrix.post_rotate(Angle.degrees(rotation).as_radians, center.x, center.y)

        self.center = center
        self.prx = Point(center.x + rx, center.y)
        self.pry = Point(center.x, center.y + ry)

        self.prx.matrix_transform(rotate_matrix)
        self.pry.matrix_transform(rotate_matrix)
        self.sweep = Angle.degrees(delta).as_radians

    def as_quad_curves(self, arc_required):
        if arc_required is None:
            sweep_limit = tau / 12
            arc_required = int(ceil(abs(self.sweep) / sweep_limit))
            if arc_required == 0:
                return
        t_slice = self.sweep / float(arc_required)

        current_t = self.get_start_t()
        p_start = self.start

        theta = self.get_rotation()
        cos_theta = cos(theta)
        sin_theta = sin(theta)

        a = self.rx
        b = self.ry
        cx = self.center.x
        cy = self.center.y

        for i in range(0, arc_required):
            next_t = current_t + t_slice
            mid_t = (next_t + current_t) / 2
            p_end = self.point_at_t(next_t)
            if i == arc_required - 1:
                p_end = self.end
            cos_mid_t = cos(mid_t)
            sin_mid_t = sin(mid_t)
            alpha = (4.0 - cos(t_slice)) / 3.0
            px = cx + alpha * (a * cos_mid_t * cos_theta - b * sin_mid_t * sin_theta)
            py = cy + alpha * (a * cos_mid_t * sin_theta + b * sin_mid_t * cos_theta)
            yield QuadraticBezier(p_start, (px, py), p_end)
            p_start = p_end
            current_t = next_t

    def as_cubic_curves(self, arc_required=None):
        if arc_required is None:
            sweep_limit = tau / 12
            arc_required = int(ceil(abs(self.sweep) / sweep_limit))
            if arc_required == 0:
                return
        t_slice = self.sweep / float(arc_required)

        theta = self.get_rotation()
        rx = self.rx
        ry = self.ry
        p_start = self.start
        current_t = self.get_start_t()
        x0 = self.center.x
        y0 = self.center.y
        cos_theta = cos(theta)
        sin_theta = sin(theta)

        for i in range(0, arc_required):
            next_t = current_t + t_slice

            alpha = sin(t_slice) * (sqrt(4 + 3 * pow(tan((t_slice) / 2.0), 2)) - 1) / 3.0

            cos_start_t = cos(current_t)
            sin_start_t = sin(current_t)

            ePrimen1x = -rx * cos_theta * sin_start_t - ry * sin_theta * cos_start_t
            ePrimen1y = -rx * sin_theta * sin_start_t + ry * cos_theta * cos_start_t

            cos_end_t = cos(next_t)
            sin_end_t = sin(next_t)

            p2En2x = x0 + rx * cos_end_t * cos_theta - ry * sin_end_t * sin_theta
            p2En2y = y0 + rx * cos_end_t * sin_theta + ry * sin_end_t * cos_theta
            p_end = (p2En2x, p2En2y)
            if i == arc_required - 1:
                p_end = self.end

            ePrimen2x = -rx * cos_theta * sin_end_t - ry * sin_theta * cos_end_t
            ePrimen2y = -rx * sin_theta * sin_end_t + ry * cos_theta * cos_end_t

            p_c1 = (p_start[0] + alpha * ePrimen1x, p_start[1] + alpha * ePrimen1y)
            p_c2 = (p_end[0] - alpha * ePrimen2x, p_end[1] - alpha * ePrimen2y)

            yield CubicBezier(p_start, p_c1, p_c2, p_end)
            p_start = Point(p_end)
            current_t = next_t

    def is_circular(self):
        a = self.rx
        b = self.ry
        return a == b

    @property
    def radius(self):
        """Legacy complex radius property

        Point will work like a complex for legacy reasons.
        """
        return Point(self.rx, self.ry)

    @property
    def rx(self):
        return Point.distance(self.center, self.prx)

    @property
    def ry(self):
        return Point.distance(self.center, self.pry)

    def get_rotation(self):
        return Point.angle(self.center, self.prx)

    def get_start_angle(self):
        """
        :return: Angle from the center point to start point.
        """
        return self.angle_at_point(self.start)

    def get_end_angle(self):
        """
        :return: Angle from the center point to end point.
        """
        return self.angle_at_point(self.end)

    def get_start_t(self):
        """
        start t value in the ellipse.

        :return: t parameter of start point.
        """
        return self.t_at_point(self.point_at_angle(self.get_start_angle()))

    def get_end_t(self):
        """
        end t value in the ellipse.

        :return: t parameter of start point.
        """
        return self.t_at_point(self.point_at_angle(self.get_end_angle()))

    def point_at_angle(self, angle):
        """
        find the point on the ellipse from the center at the given angle.
        Note: For non-circular arcs this is different than point(t).

        :param angle: angle from center to find point
        :return: point found
        """
        angle -= self.get_rotation()
        a = self.rx
        b = self.ry
        if a == b:
            return self.point_at_t(angle)
        t = atan2(a * tan(angle), b)
        tau_1_4 = tau / 4.0
        tau_3_4 = 3 * tau_1_4
        if tau_3_4 >= abs(angle) % tau > tau_1_4:
            t += tau / 2
        return self.point_at_t(t)

    def angle_at_point(self, p):
        """
        find the angle to the point.

        :param p: point
        :return: angle to given point.
        """
        return self.center.angle_to(p)

    def t_at_point(self, p):
        """
        find the t parameter to at the point.

        :param p: point
        :return: t parameter to the given point.
        """
        angle = self.angle_at_point(p)
        angle -= self.get_rotation()
        a = self.rx
        b = self.ry
        t = atan2(a * tan(angle), b)
        tau_1_4 = tau / 4.0
        tau_3_4 = 3 * tau_1_4
        if tau_3_4 >= abs(angle) % tau > tau_1_4:
            t += tau / 2
        return t

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        rotation = self.get_rotation()
        a = self.rx
        b = self.ry
        cx = self.center.x
        cy = self.center.y
        cos_rot = cos(rotation)
        sin_rot = sin(rotation)
        cos_t = cos(t)
        sin_t = sin(t)
        px = cx + a * cos_t * cos_rot - b * sin_t * sin_rot
        py = cy + a * cos_t * sin_rot + b * sin_t * cos_rot
        return Point(px, py)

    def get_ellipse(self):
        return Ellipse(self.center, self.rx, self.ry, self.get_rotation())

    def bbox(self):
        """Find the bounding box of a arc.
        Code from: https://github.com/mathandy/svgpathtools
        """
        phi = self.get_rotation().as_radians
        if cos(phi) == 0:
            atan_x = pi / 2
            atan_y = 0
        elif sin(phi) == 0:
            atan_x = 0
            atan_y = pi / 2
        else:
            rx, ry = self.rx, self.ry
            atan_x = atan(-(ry / rx) * tan(phi))
            atan_y = atan((ry / rx) / tan(phi))

        def angle_inv(ang, k):  # inverse of angle from Arc.derivative()
            return ((ang + pi * k) * (360 / (2 * pi)) - self.theta) / self.delta

        xtrema = [self.start.x, self.end.x]
        ytrema = [self.start.y, self.end.y]

        for k in range(-4, 5):
            tx = angle_inv(atan_x, k)
            ty = angle_inv(atan_y, k)
            if 0 <= tx <= 1:
                xtrema.append(self.point(tx).x)
            if 0 <= ty <= 1:
                ytrema.append(self.point(ty).y)

        return min(xtrema), min(ytrema), max(xtrema), max(ytrema)

    def d(self, current_point=None, relative=None, smooth=None):
        if current_point is None or (relative is None and self.relative) or (relative is not None and not relative):
            return 'A %G,%G %G %d,%d %s' % (
                self.rx,
                self.ry,
                self.get_rotation().as_degrees,
                int(abs(self.sweep) > (tau / 2.0)),
                int(self.sweep >= 0),
                self.end)
        else:
            return 'a %G,%G %G %d,%d %s' % (
                self.rx,
                self.ry,
                self.get_rotation().as_degrees,
                int(abs(self.sweep) > (tau / 2.0)),
                int(self.sweep >= 0),
                self.end - current_point)


class Path(Shape, MutableSequence):
    """
    A Path is a Mutable sequence of path segments

    It is a generalized shape which can map out all the other shapes.

    Each PathSegment object maps a particular command. Each one exists only once in each path and every point contained
    within the object is also unique. We attempt to internally maintain some validity. Each end point should link
    to the following segments start point. And each close point should connect from the preceding segments endpoint to
    the last Move command.

    These are soft checks made only at the time of addition and some manipulations. Modifying the points of the segments
    can and will cause path invalidity. Some SVG invalid operations are permitted such as arcs longer than tau radians
    or beginning sequences without a move. The expectation is that these will eventually be used as part of a valid path
    so these fragment paths are permitted. In some cases these invalid paths will still have consistent path_d values,
    in other cases, there will be no valid methods to reproduce these.
    """

    def __init__(self, *args, **kwargs):
        Shape.__init__(self, *args, **kwargs)
        self._length = None
        self._lengths = None
        self._segments = list()
        if len(args) != 1:
            self._segments.extend(args)
        else:
            s = args[0]
            if isinstance(s, Subpath):
                self._segments.extend(s.segments(transformed=False))
                Shape.__init__(self, s._path)
            elif isinstance(s, Shape):
                self._segments.extend(s.segments(transformed=False))
            elif isinstance(s, str):
                self._segments = list()
                self.parse(s)
            elif isinstance(s, tuple):
                # We have no guarantee of the validity of the source data
                self._segments.extend(s)
                self.validate_connections()
            elif isinstance(s, list):
                # We have no guarantee of the validity of the source data
                self._segments.extend(s)
                self.validate_connections()
            elif isinstance(s, PathSegment):
                self._segments.append(s)
        if SVG_ATTR_DATA in self.values:
            if not self.values.get('pathd_loaded', False):
                self.parse(self.values[SVG_ATTR_DATA])
                self.values['pathd_loaded'] = True

    def __copy__(self):
        path = Path(self)
        segs = path._segments
        for i in range(0, len(segs)):
            segs[i] = copy(segs[i])
        return path

    def __getitem__(self, index):
        return self._segments[index]

    def _validate_subpath(self, index):
        """ensure the subpath containing this index is valid."""
        if index < 0 or index + 1 >= len(self._segments):
            return  # This connection doesn't exist.
        for j in range(index, len(self._segments)):
            close_search = self._segments[j]
            if isinstance(close_search, Move):
                return  # Not a closed path, subpath is valid.
            if isinstance(close_search, Close):
                for k in range(index, -1, -1):
                    move_search = self._segments[k]
                    if isinstance(move_search, Move):
                        self._segments[j].end = Point(move_search.end)
                        return
                self._segments[j].end = Point(self._segments[0].end)
                return

    def _validate_move(self, index):
        """ensure the next closed point from this index points to a valid location."""
        for i in range(index + 1, len(self._segments)):
            segment = self._segments[i]
            if isinstance(segment, Move):
                return  # Not a closed path, the move is valid.
            if isinstance(segment, Close):
                segment.end = Point(self._segments[index].end)
                return

    def _validate_close(self, index):
        """ensure the close element at this position correctly links to the previous move"""
        for i in range(index, -1, -1):
            segment = self._segments[i]
            if isinstance(segment, Move):
                self._segments[index].end = Point(segment.end)
                return
        self._segments[index].end = Point(self._segments[0].end) if self._segments[0].end is not None else None
        # If move is never found, just the end point of the first element. Unless that's not a thing.

    def _validate_connection(self, index, prefer_second=False):
        """
        Validates the connection at the index.
        Connection 0 is the connection between getitem(0) and getitem(1)

        prefer_second is for those cases where failing the connection requires replacing
        a existing value. It will prefer the authority of right side, second value.
        """
        if index < 0 or index + 1 >= len(self._segments):
            return  # This connection doesn't exist.
        first = self._segments[index]
        second = self._segments[index + 1]
        if first.end is not None and second.start is None:
            second.start = Point(first.end)
        elif first.end is None and second.start is not None:
            first.end = Point(second.start)
        elif first.end != second.start:
            # The two values exist but are not equal. One must replace the other.
            if prefer_second:
                first.end = Point(second.start)
            else:
                second.start = Point(first.end)

    def __setitem__(self, index, new_element):
        if isinstance(new_element, str):
            new_element = Path(new_element)
            if len(new_element) == 0:
                return
            new_element = new_element.segments()
            if isinstance(index, int):
                if len(new_element) > 1:
                    raise ValueError  # Cannot insert multiple items into a single space. Requires slice.
                new_element = new_element[0]
        self._segments[index] = new_element
        self._length = None
        self._lengths = None
        if isinstance(index, slice):
            self.validate_connections()
        else:
            self._validate_connection(index - 1)
            self._validate_connection(index)
            if isinstance(new_element, Move):
                self._validate_move(index)
            if isinstance(new_element, Close):
                self._validate_close(index)

    def __delitem__(self, index):
        original_element = self._segments[index]
        del self._segments[index]
        self._length = None
        if isinstance(index, slice):
            self.validate_connections()
        else:
            self._validate_connection(index - 1)
            if isinstance(original_element, (Close, Move)):
                self._validate_subpath(index)

    def __iadd__(self, other):
        if isinstance(other, str):
            self.parse(other)
        elif isinstance(other, (Path, Subpath)):
            self.extend(map(copy, list(other)))
        elif isinstance(other, Shape):
            self.parse(other.d())
        elif isinstance(other, PathSegment):
            self.append(other)
        else:
            return NotImplemented
        return self

    def __add__(self, other):
        if isinstance(other, (str, Path, Subpath, Shape, PathSegment)):
            n = copy(self)
            n += other
            return n
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            path = Path(other)
            path.extend(map(copy, self._segments))
            return path
        elif isinstance(other, PathSegment):
            path = copy(self)
            path.insert(0, other)
            return path
        else:
            return NotImplemented

    def __len__(self):
        return len(self._segments)

    def __str__(self):
        return self.d()

    def __repr__(self):
        values = []
        if len(self) > 0:
            values.append(', '.join(repr(x) for x in self._segments))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(Path(other))
        if not isinstance(other, Path):
            return NotImplemented
        if len(self) != len(other):
            return False
        p = abs(self)
        q = abs(other)
        for s, o in zip(q._segments, p._segments):
            if not s == o:
                return False
        if p.stroke_width != q.stroke_width:
            return False
        return True

    def __ne__(self, other):
        if not isinstance(other, (Path, str)):
            return NotImplemented
        return not self == other

    def parse(self, pathdef):
        """Parses the SVG path."""
        tokens = SVGLexicalParser()
        tokens.parse(self, pathdef)

    def validate_connections(self):
        """
        Force validate all connections.

        This will scan path connections and link any adjacent elements together by replacing any None points or causing
        the start position of the next element to equal the end position of the previous. This should only be needed
        when combining paths and elements together. Close elements are always connected to the last Move element or to
        the end position of the first element in the list. The start element of the first segment may or may not be
        None.
        """
        zpoint = None
        last_segment = None
        for segment in self._segments:
            if zpoint is None or isinstance(segment, Move):
                zpoint = segment.end
            if last_segment is not None:
                if segment.start is None and last_segment.end is not None:
                    segment.start = Point(last_segment.end)
                elif last_segment.end is None and segment.start is not None:
                    last_segment.end = Point(segment.start)
                elif last_segment.end != segment.start:
                    segment.start = Point(last_segment.end)
            if isinstance(segment, Close) and zpoint is not None and segment.end != zpoint:
                segment.end = Point(zpoint)
            last_segment = segment

    def _is_valid(self):
        """
        Checks validation of all connections.

        Paths are valid if all end points match the start of the next point and all close
        commands return to the last valid move command.

        This does not check for incongruent path validity. Path fragments without initial moves
        double closed paths, may all pass this check.
        """
        zpoint = None
        last_segment = None
        for segment in self._segments:
            if zpoint is None or isinstance(segment, Move):
                zpoint = segment.end
            if last_segment is not None:
                if segment.start is None:
                    return False
                elif last_segment.end is None:
                    return False
                elif last_segment.end != segment.start:
                    return False
            if isinstance(segment, Close) and zpoint is not None and segment.end != zpoint:
                return False
            last_segment = segment
        return True

    @property
    def first_point(self):
        """First point along the Path. This is the start point of the first segment unless it starts
        with a Move command with a None start in which case first point is that Move's destination."""
        if len(self._segments) == 0:
            return None
        if self._segments[0].start is not None:
            return Point(self._segments[0].start)
        return Point(self._segments[0].end) if self._segments[0].end is not None else None

    @property
    def current_point(self):
        if len(self._segments) == 0:
            return None
        return Point(self._segments[-1].end) if self._segments[-1].end is not None else None

    @property
    def z_point(self):
        """
        Z is the destination of the last Move. It can mean, but doesn't necessarily mean the first_point in the path.
        This behavior of Z is defined in svg spec:
        http://www.w3.org/TR/SVG/paths.html#PathDataClosePathCommand
        """
        end_pos = None
        for segment in reversed(self._segments):
            if isinstance(segment, Move):
                end_pos = segment.end
                break
        if end_pos is None:
            try:
                end_pos = self._segments[0].end
            except IndexError:
                pass  # entire path is "z".
        return end_pos

    @property
    def smooth_point(self):
        """Returns the smoothing control point for the smooth commands.
        With regards to the SVG standard if the last command was a curve the smooth
        control point is the reflection of the previous control point.

        If the last command was not a curve, the smooth_point is coincident with the current.
        https://www.w3.org/TR/SVG/paths.html#PathDataCubicBezierCommands
        """

        if len(self._segments) == 0:
            return None
        start_pos = self.current_point
        last_segment = self._segments[-1]
        if isinstance(last_segment, QuadraticBezier):
            previous_control = last_segment.control
            return previous_control.reflected_across(start_pos)
        elif isinstance(last_segment, CubicBezier):
            previous_control = last_segment.control2
            return previous_control.reflected_across(start_pos)
        return start_pos

    def start(self):
        pass

    def end(self):
        pass

    def move(self, *points, relative=False):
        start_pos = self.current_point
        end_pos = points[0]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = Move(start_pos, end_pos)
        segment.relative = relative
        self.append(segment)
        if len(points) > 1:
            self.line(*points[1:], relative=relative)
        return self

    def line(self, *points, relative=False):
        start_pos = self.current_point
        end_pos = points[0]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = Line(start_pos, end_pos)
        segment.relative = relative
        self.append(segment)
        if len(points) > 1:
            self.line(*points[1:])
        return self

    def vertical(self, *y_points, relative=False):
        start_pos = self.current_point
        if relative:
            segment = Line(start_pos, Point(start_pos.x, start_pos.y + y_points[0]))
        else:
            segment = Line(start_pos, Point(start_pos.x, y_points[0]))
        segment.relative = relative
        self.append(segment)
        if len(y_points) > 1:
            self.vertical(*y_points[1:], relative=relative)
        return self

    def horizontal(self, *x_points, relative=False):
        start_pos = self.current_point
        if relative:
            segment = Line(start_pos, Point(start_pos.x + x_points[0], start_pos.y))
            segment.relative = relative
        else:
            segment = Line(start_pos, Point(x_points[0], start_pos.y))
            segment.relative = relative
        self.append(segment)
        if len(x_points) > 1:
            self.horizontal(*x_points[1:], relative=relative)
        return self

    def smooth_quad(self, *points, relative=False):
        """Smooth curve. First control point is the "reflection" of
           the second control point in the previous path."""
        start_pos = self.current_point
        control1 = self.smooth_point
        end_pos = points[0]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = QuadraticBezier(start_pos, control1, end_pos)
        segment.relative = relative
        segment.smooth = True
        self.append(segment)
        if len(points) > 1:
            self.smooth_quad(*points[1:])
        return self

    def quad(self, *points, relative=False):
        start_pos = self.current_point
        control = points[0]
        if control in ('z', 'Z'):
            control = self.z_point
        end_pos = points[1]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = QuadraticBezier(start_pos, control, end_pos)
        segment.relative = relative
        segment.smooth = False
        self.append(segment)
        if len(points) > 2:
            self.quad(*points[2:])
        return self

    def smooth_cubic(self, *points, relative=False):
        """Smooth curve. First control point is the "reflection" of
        the second control point in the previous path."""
        start_pos = self.current_point
        control1 = self.smooth_point
        control2 = points[0]

        if control2 in ('z', 'Z'):
            control2 = self.z_point
        end_pos = points[1]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = CubicBezier(start_pos, control1, control2, end_pos)
        segment.relative = relative
        segment.smooth = True
        self.append(segment)
        if len(points) > 2:
            self.smooth_cubic(*points[2:])
        return self

    def cubic(self, *points, relative=False):
        start_pos = self.current_point
        control1 = points[0]
        if control1 in ('z', 'Z'):
            control1 = self.z_point
        control2 = points[1]
        if control2 in ('z', 'Z'):
            control2 = self.z_point
        end_pos = points[2]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = CubicBezier(start_pos, control1, control2, end_pos)
        segment.relative = relative
        segment.smooth = False
        self.append(segment)
        if len(points) > 3:
            self.cubic(*points[3:])
        return self

    def arc(self, *arc_args, relative=False):
        start_pos = self.current_point
        rx = arc_args[0]
        ry = arc_args[1]
        rotation = arc_args[2]
        arc = arc_args[3]
        sweep = arc_args[4]
        end_pos = arc_args[5]
        if end_pos in ('z', 'Z'):
            end_pos = self.z_point
        segment = Arc(start_pos, rx, ry, rotation, arc, sweep, end_pos)
        segment.relative = relative
        self.append(segment)
        if len(arc_args) > 6:
            self.arc(*arc_args[6:])
        return self

    def closed(self, relative=False):
        start_pos = self.current_point
        end_pos = self.z_point
        segment = Close(start_pos, end_pos)
        segment.relative = relative
        self.append(segment)
        return self

    def append(self, value):
        if isinstance(value, str):
            value = Path(value)
            if len(value) == 0:
                return
            if len(value) > 1:
                self.extend(value)
                return
            value = value[0]
        self._length = None
        index = len(self._segments) - 1
        self._segments.append(value)
        self._validate_connection(index)
        if isinstance(value, Close):
            self._validate_close(index + 1)

    def insert(self, index, value):
        if isinstance(value, str):
            value = Path(value)
            if len(value) == 0:
                return
            value = value[0]
        self._length = None
        self._segments.insert(index, value)
        self._validate_connection(index - 1)
        self._validate_connection(index)
        if isinstance(value, Move):
            self._validate_move(index)
        if isinstance(value, Close):
            self._validate_close(index)

    def extend(self, iterable):
        if isinstance(iterable, str):
            iterable = Path(iterable)
        self._length = None
        index = len(self._segments) - 1
        self._segments.extend(iterable)
        self._validate_connection(index)
        self._validate_subpath(index)

    def direct_close(self):
        """Forces close operations to be zero length by introducing a direct
        line to operation just before any non-zero length close.

        This is helpful because for some operations like reverse() because the
        close must located at the very end of the path sequence. But, if it's
        in effect a line-to and close, the line-to would need to start the sequence.

        But, for some operations this won't matter since it will still result in
        a closed shape with reversed ordering. But, if the final point in the
        sequence must exactly switch with the first point in the sequence. The
        close segments must be direct and zero length.
        """
        if len(self._segments) == 0:
            return
        for i in range(len(self._segments) - 1, -1, -1):
            segment = self._segments[i]
            if isinstance(segment, Close):
                if segment.length() != 0:
                    line = Line(segment.start, segment.end)
                    segment.start = Point(segment.end)
                    self.insert(i, line)
        return self

    def reverse(self):
        if len(self._segments) == 0:
            return
        prepoint = self._segments[0].start
        self._segments[0].start = None
        p = Path()
        subpaths = list(self.as_subpaths())
        for subpath in subpaths:
            subpath.reverse()
        for subpath in reversed(subpaths):
            p += subpath
        self._segments = p._segments
        self._segments[0].start = prepoint
        return self

    def subpath(self, index):
        subpaths = list(self.as_subpaths())
        return subpaths[index]

    def count_subpaths(self):
        subpaths = list(self.as_subpaths())
        return len(subpaths)

    def as_subpaths(self):
        last = 0
        for current, seg in enumerate(self):
            if current != last and isinstance(seg, Move):
                yield Subpath(self, last, current - 1)
                last = current
        yield Subpath(self, last, len(self) - 1)

    def as_points(self):
        """Returns the list of defining points within path"""
        for seg in self:
            for p in seg:
                if not isinstance(p, Point):
                    yield Point(p)
                else:
                    yield p

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Path objects reify perfectly.
        """
        GraphicObject.reify(self)
        Transformable.reify(self)
        if isinstance(self.transform, Matrix):
            for e in self._segments:
                e *= self.transform
        self.transform.reset()
        return self

    @staticmethod
    def svg_d(segments, relative=None, smooth=None):
        if len(segments) == 0:
            return ''
        parts = []
        previous_segment = None
        p = Point(0)
        if smooth is None:
            override_smooth = False
            smooth_set_value = True
        else:
            override_smooth = True
            smooth_set_value = bool(smooth)
        if relative is not None:
            for segment in segments:
                if isinstance(segment, (Move, Line, Arc, Close)):
                    parts.append(segment.d(p, relative=relative))
                elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                    if (override_smooth and smooth_set_value) or (not override_smooth and segment.smooth):
                        parts.append(segment.d(p, relative=relative, smooth=segment.is_smooth_from(previous_segment)))
                    else:
                        parts.append(segment.d(p, relative=relative, smooth=False))
                previous_segment = segment
                p = previous_segment.end
        else:
            for segment in segments:
                if isinstance(segment, (Move, Line, Arc, Close)):
                    parts.append(segment.d(p, relative=segment.relative))
                elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                    if (override_smooth and smooth_set_value) or (not override_smooth and segment.smooth):
                        parts.append(
                            segment.d(p, relative=segment.relative, smooth=segment.is_smooth_from(previous_segment)))
                    else:
                        parts.append(segment.d(p, relative=segment.relative, smooth=False))
                previous_segment = segment
                p = previous_segment.end
        return ' '.join(parts)

    def d(self, relative=None, transformed=True, smooth=None):
        path = self
        if transformed:
            path = abs(path)
        return Path.svg_d(path._segments, relative=relative, smooth=smooth)

    def segments(self, transformed=True):
        if transformed and not self.transform.is_identity():
            return [s * self.transform for s in self._segments]
        return self._segments

    def approximate_arcs_with_cubics(self, error=0.1):
        """
        Iterates through this path and replaces any Arcs with cubic bezier curves.
        """
        sweep_limit = tau * error
        for s in range(len(self) - 1, -1, -1):
            segment = self[s]
            if isinstance(segment, Arc):
                arc_required = int(ceil(abs(segment.sweep) / sweep_limit))
                self[s:s + 1] = list(segment.as_cubic_curves(arc_required))

    def approximate_arcs_with_quads(self, error=0.1):
        """
        Iterates through this path and replaces any Arcs with quadratic bezier curves.
        """
        sweep_limit = tau * error
        for s in range(len(self) - 1, -1, -1):
            segment = self[s]
            if isinstance(segment, Arc):
                arc_required = int(ceil(abs(segment.sweep) / sweep_limit))
                self[s:s + 1] = list(segment.as_quad_curves(arc_required))


class Rect(Shape):
    """
    SVG Rect shapes are defined in SVG2 10.2
    https://www.w3.org/TR/SVG2/shapes.html#RectElement

    These have geometric properties x, y, width, height, rx, ry
    Geometric properties can be Length values.

    Rect(x, y, width, height)
    Rect(x, y, width, height, rx, ry)
    Rect(x, y, width, height, rx, ry, matrix)
    Rect(x, y, width, height, rx, ry, matrix, stroke, fill)

    Rect(dict): dictionary values read from svg.

    """

    def __init__(self, *args, **kwargs):
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.rx = None
        self.ry = None
        Shape.__init__(self, *args, **kwargs)
        self._validate_rect()

    def property_by_object(self, s):
        Shape.property_by_object(self, s)
        self.x = s.x
        self.y = s.y
        self.width = s.width
        self.height = s.height
        self.rx = s.rx
        self.ry = s.ry
        self._validate_rect()

    def property_by_values(self, values):
        Shape.property_by_values(self, values)
        self.x = Length(values.get(SVG_ATTR_X, 0)).value()
        self.y = Length(values.get(SVG_ATTR_Y, 0)).value()
        self.width = Length(values.get(SVG_ATTR_WIDTH, 1)).value()
        self.height = Length(values.get(SVG_ATTR_HEIGHT, 1)).value()
        self.rx = Length(values.get(SVG_ATTR_RADIUS_X, None)).value()
        self.ry = Length(values.get(SVG_ATTR_RADIUS_Y, None)).value()

    def property_by_args(self, *args):
        arg_length = len(args)
        if arg_length >= 1:
            self.x = Length(args[0]).value()
        if arg_length >= 2:
            self.y = Length(args[1]).value()
        if arg_length >= 3:
            self.width = Length(args[2]).value()
        if arg_length >= 4:
            self.height = Length(args[3]).value()
        if arg_length >= 5:
            self.rx = Length(args[4]).value()
        if arg_length >= 6:
            self.ry = Length(args[5]).value()
        if arg_length >= 7:
            self._init_shape(*args[6:])

    def _validate_rect(self):
        """None is 'auto' for values."""
        rx = self.rx
        ry = self.ry
        if rx is None and ry is None:
            rx = ry = 0
        if rx is not None and ry is None:
            rx = Length(rx).value(relative_length=self.width)
            ry = rx
        elif ry is not None and rx is None:
            ry = Length(ry).value(relative_length=self.height)
            rx = ry
        elif rx is not None and ry is not None:
            rx = Length(rx).value(relative_length=self.width)
            ry = Length(ry).value(relative_length=self.height)
        if rx == 0 or ry == 0:
            rx = ry = 0
        else:
            rx = min(rx, self.width / 2.0)
            ry = min(ry, self.height / 2.0)
        self.rx = rx
        self.ry = ry

    def __repr__(self):
        values = []
        if self.x != 0:
            values.append('x=%s' % Length.str(self.x))
        if self.y != 0:
            values.append('y=%s' % Length.str(self.y))
        if self.width != 0:
            values.append('width=%s' % Length.str(self.width))
        if self.height != 0:
            values.append('height=%s' % Length.str(self.height))
        if self.rx != 0:
            values.append('rx=%s' % Length.str(self.rx))
        if self.ry != 0:
            values.append('ry=%s' % Length.str(self.ry))
        self._repr_shape(values)
        params = ", ".join(values)
        return "Rect(%s)" % params

    def __copy__(self):
        return Rect(self)

    @property
    def implicit_position(self):
        if not self.apply:
            return Point(self.x, self.y)
        point = Point(self.x, self.y)
        point *= self.transform
        return point

    @property
    def implicit_x(self):
        if not self.apply:
            return self.x
        return self.implicit_position[0]

    @property
    def implicit_y(self):
        if not self.apply:
            return self.y
        return self.implicit_position[1]

    @property
    def implicit_width(self):
        if not self.apply:
            return self.width
        p = Point(self.width, 0)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_height(self):
        if not self.apply:
            return self.height
        p = Point(0, self.height)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_rx(self):
        if not self.apply:
            return self.rx
        p = Point(self.rx, 0)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    @property
    def implicit_ry(self):
        if not self.apply:
            return self.ry
        p = Point(0, self.ry)
        p *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(p)

    def segments(self, transformed=True):
        """
        Rect decomposition is given in SVG 2.0 10.2

        Rect:
        * perform an absolute moveto operation to location (x,y);
        * perform an absolute horizontal lineto with parameter x+width;
        * perform an absolute vertical lineto parameter y+height;
        * perform an absolute horizontal lineto parameter x;
        * ( close the path)

        Rounded Rect:
        rx and ry are used as the equivalent parameters to the elliptical arc command,
        the x-axis-rotation and large-arc-flag are set to zero, the sweep-flag is set to one

        * perform an absolute moveto operation to location (x+rx,y);
        * perform an absolute horizontal lineto with parameter x+width-rx;
        * perform an absolute elliptical arc operation to coordinate (x+width,y+ry)
        * perform an absolute vertical lineto parameter y+height-ry;
        * perform an absolute elliptical arc operation to coordinate (x+width-rx,y+height)
        * perform an absolute horizontal lineto parameter x+rx;
        * perform an absolute elliptical arc operation to coordinate (x,y+height-ry)
        * perform an absolute vertical lineto parameter y+ry
        * perform an absolute elliptical arc operation with a segment-completing close path operation

        :param transformed: provide the reified version.
        :return: path_d of shape.
        """
        x = self.x
        y = self.y
        width = self.width
        height = self.height
        if width == 0 or height == 0:
            return ()  # a computed value of zero for either dimension disables rendering.
        rx = self.rx
        ry = self.ry
        if rx == ry == 0:
            segments = (Move(None, (x, y)),
                        Line((x, y), (x + width, y)),
                        Line((x + width, y), (x + width, y + height)),
                        Line((x + width, y + height), (x, y + height)),
                        Close((x, y + height), (x, y)))
        else:
            segments = (Move(None, (x + rx, y)),
                        Line((x + rx, y), (x + width - rx, y)),
                        Arc((x + width - rx, y), (x + width, y + ry), rx=rx, ry=ry),
                        Line((x + width, y + ry), (x + width, y + height - ry)),
                        Arc((x + width, y + height - ry), (x + width - rx, y + height), rx=rx, ry=ry),
                        Line((x + width - rx, y + height), (x + rx, y + height)),
                        Arc((x + rx, y + height), (x, y + height - ry), rx=rx, ry=ry),
                        Line((x, y + height - ry), (x, y + ry)),
                        Arc((x, y + ry), (x + rx, y), rx=rx, ry=ry),
                        Close((x + rx, y), (x + rx, y)))
        if not transformed or self.transform.is_identity():
            return segments
        else:
            return [s * self.transform for s in segments]

    def reify(self):
        """
        Realizes the transform to the shape properties.

        If the realized shape can be properly represented as a rectangle with an identity matrix
        it will be, otherwise the properties will approximate the implied values.

        Skewed and Rotated rectangles cannot be reified.
        """
        GraphicObject.reify(self)
        Transformable.reify(self)
        scale_x = self.transform.value_scale_x()
        scale_y = self.transform.value_scale_y()
        translate_x = self.transform.value_trans_x()
        translate_y = self.transform.value_trans_y()
        if self.transform.value_skew_x() == 0 and self.transform.value_skew_y() == 0 \
                and scale_x != 0 and scale_y != 0:
            self.x *= scale_x
            self.y *= scale_y
            self.x += translate_x
            self.y += translate_y
            self.transform *= Matrix.translate(-translate_x, -translate_y)
            self.rx = scale_x * self.rx
            self.ry = scale_y * self.ry
            self.width = scale_x * self.width
            self.height = scale_y * self.height
            self.transform *= Matrix.scale(1.0 / scale_x, 1.0 / scale_y)
        return self

    def render(self, **kwargs):
        Shape.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.width, Length):
            self.width = self.width.value(relative_length=width, **kwargs)
        if isinstance(self.height, Length):
            self.height = self.height.value(relative_length=height, **kwargs)
        if isinstance(self.rx, Length):
            self.rx = self.rx.value(relative_length=width, **kwargs)
        if isinstance(self.ry, Length):
            self.ry = self.ry.value(relative_length=height, **kwargs)
        return self


class _RoundShape(Shape):

    def __init__(self, *args, **kwargs):
        self.cx = None
        self.cy = None
        self.rx = None
        self.ry = None
        Shape.__init__(self, *args, **kwargs)

    def property_by_object(self, s):
        Shape.property_by_object(self, s)
        self.cx = s.cx
        self.cy = s.cy
        self.rx = s.rx
        self.ry = s.ry

    def property_by_values(self, values):
        Shape.property_by_values(self, values)
        self.cx = Length(values.get(SVG_ATTR_CENTER_X)).value()
        self.cy = Length(values.get(SVG_ATTR_CENTER_Y)).value()
        self.rx = Length(values.get(SVG_ATTR_RADIUS_X)).value()
        self.ry = Length(values.get(SVG_ATTR_RADIUS_Y)).value()
        r = Length(values.get(SVG_ATTR_RADIUS, None)).value()
        if r is not None:
            self.rx = r
            self.ry = r
        else:
            if self.rx is None:
                self.rx = 1
            if self.ry is None:
                self.ry = 1
        center = values.get('center', None)
        if center is not None:
            self.cx, self.cy = Point(center)

        if self.cx is None:
            self.cx = 0
        if self.cy is None:
            self.cy = 0

    def property_by_args(self, *args):
        arg_length = len(args)
        if arg_length >= 1:
            self.cx = Length(args[0]).value()
        if arg_length >= 2:
            self.cy = Length(args[1]).value()
        if arg_length >= 3:
            self.rx = Length(args[2]).value()
            if arg_length >= 4:
                self.ry = Length(args[3]).value()
            else:
                self.ry = self.rx
        if arg_length >= 5:
            self._init_shape(*args[4:])

    def __repr__(self):
        values = []
        if self.cx is not None:
            values.append('cx=%s' % Length.str(self.cx))
        if self.cy is not None:
            values.append('cy=%s' % Length.str(self.cy))
        if self.rx == self.ry or self.ry is None:
            values.append('r=%s' % Length.str(self.rx))
        else:
            values.append('rx=%s' % Length.str(self.rx))
            values.append('ry=%s' % Length.str(self.ry))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    @property
    def implicit_rx(self):
        if not self.apply:
            return self.rx
        prx = Point(self.rx, 0)
        prx *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(prx)

    @property
    def implicit_ry(self):
        if not self.apply:
            return self.ry
        pry = Point(0, self.ry)
        pry *= self.transform
        origin = Point(0, 0)
        origin *= self.transform
        return origin.distance_to(pry)

    implicit_r = implicit_rx

    @property
    def implicit_center(self):
        center = Point(self.cx, self.cy)
        if not self.apply:
            return center
        center *= self.transform
        return center

    def segments(self, transformed=True):
        """
        SVG path decomposition is given in SVG 2.0 10.3, 10.4.

        A move-to command to the point cx+rx,cy;
        arc to cx,cy+ry;
        arc to cx-rx,cy;
        arc to cx,cy-ry;
        arc with a segment-completing close path operation.

        Converts the parameters from an ellipse or a circle to a string for a
        Path object d-attribute"""
        original = self.apply
        self.apply = transformed
        path = Path()
        steps = 4
        step_size = tau / steps
        if transformed and self.transform.value_scale_x() * self.transform.value_scale_y() < 0:
            step_size = -step_size
        t_start = 0
        t_end = step_size
        # zero for either dimension, or a computed value of auto for both dimensions, disables rendering of the element.
        rx = self.implicit_rx
        ry = self.implicit_ry
        if rx == 0 or ry == 0:
            return ()
        center = self.implicit_center
        path.move((self.point_at_t(0)))
        for i in range(steps):
            path += Arc(
                self.point_at_t(t_start),
                self.point_at_t(t_end),
                center,
                rx=rx, ry=ry, rotation=self.rotation, sweep=step_size)
            t_start = t_end
            t_end += step_size
        path.closed()
        self.apply = original
        return path.segments(transformed)

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Skewed and Rotated roundshapes cannot be reified.
        """
        GraphicObject.reify(self)
        Transformable.reify(self)
        scale_x = abs(self.transform.value_scale_x())
        scale_y = abs(self.transform.value_scale_y())
        translate_x = self.transform.value_trans_x()
        translate_y = self.transform.value_trans_y()
        if self.transform.value_skew_x() == 0 and self.transform.value_skew_y() == 0 \
                and scale_x != 0 and scale_y != 0:
            self.cx *= scale_x
            self.cy *= scale_y
            self.cx += translate_x
            self.cy += translate_y
            self.transform *= Matrix.translate(-translate_x, -translate_y)
            self.rx = scale_x * self.rx
            self.ry = scale_y * self.ry
            self.transform *= Matrix.scale(1.0 / scale_x, 1.0 / scale_y)
        return self

    def render(self, **kwargs):
        Shape.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.cx, Length):
            self.cx = self.cx.value(relative_length=width, **kwargs)
        if isinstance(self.cy, Length):
            self.cy = self.cy.value(relative_length=height, **kwargs)
        if isinstance(self.rx, Length):
            self.rx = self.rx.value(relative_length=width, **kwargs)
        if isinstance(self.ry, Length):
            self.ry = self.ry.value(relative_length=height, **kwargs)
        return self

    def unit_matrix(self):
        """
        return the unit matrix which could would transform the unit circle into this ellipse.

        One of the valid parameterizations for ellipses is that they are all affine transforms of the unit circle.
        This provides exactly such a matrix.

        :return: matrix
        """
        m = Matrix()
        m.post_scale(self.implicit_rx, self.implicit_ry)
        m.post_rotate(self.rotation)
        center = self.implicit_center
        m.post_translate(center.x, center.y)
        return m

    def arc_t(self, t0, t1):
        """
        return the arc found between the given values of t on the ellipse.

        :param t0: t start
        :param t1: t end
        :return: arc
        """
        return Arc(self.point_at_t(t0),
                   self.point_at_t(t1),
                   self.implicit_center,
                   rx=self.implicit_rx, ry=self.implicit_ry, rotation=self.rotation, sweep=t1 - t0)

    def arc_angle(self, a0, a1, ccw=None):
        """
        return the arc found between the given angles on the ellipse.

        :param a0: start angle
        :param a1: end angle
        :return: arc
        """
        if ccw is None:
            ccw = a0 > a1
        return Arc(self.point_at_angle(a0),
                   self.point_at_angle(a1),
                   self.implicit_center,
                   rx=self.implicit_rx, ry=self.implicit_ry,
                   rotation=self.rotation, ccw=ccw)

    def point_at_angle(self, angle):
        """
        find the point on the ellipse from the center at the given angle.
        Note: For non-circular arcs this is different than point(t).

        :param angle: angle from center to find point
        :return: point found
        """
        a = self.implicit_rx
        b = self.implicit_ry
        if a == b:
            return self.point_at_t(angle)
        angle -= self.rotation
        t = atan2(a * tan(angle), b)
        tau_1_4 = tau / 4.0
        tau_3_4 = 3 * tau_1_4
        if tau_3_4 >= abs(angle) % tau > tau_1_4:
            t += tau / 2
        return self.point_at_t(t)

    def angle_at_point(self, p):
        """
        find the angle to the point.

        :param p: point
        :return: angle to given point.
        """
        if self.apply and not self.transform.is_identity():
            return self.implicit_center.angle_to(p)
        else:
            center = Point(self.cx, self.cy)
            return center.angle_to(p)

    def t_at_point(self, p):
        """
        find the t parameter to at the point.

        :param p: point
        :return: t parameter to the given point.
        """
        angle = self.angle_at_point(p)
        angle -= self.rotation
        a = self.implicit_rx
        b = self.implicit_ry
        t = atan2(a * tan(angle), b)
        tau_1_4 = tau / 4.0
        tau_3_4 = 3 * tau_1_4
        if tau_3_4 >= abs(angle) % tau > tau_1_4:
            t += tau / 2
        return t

    def point_at_t(self, t):
        """
        find the point that corresponds to given value t.
        Where t=0 is the first point and t=tau is the final point.

        In the case of a circle: t = angle.

        :param t:
        :return:
        """
        rotation = self.rotation
        a = self.implicit_rx
        b = self.implicit_ry
        center = self.implicit_center
        cx = center.x
        cy = center.y
        cosTheta = cos(rotation)
        sinTheta = sin(rotation)
        cosT = cos(t)
        sinT = sin(t)
        px = cx + a * cosT * cosTheta - b * sinT * sinTheta
        py = cy + a * cosT * sinTheta + b * sinT * cosTheta
        return Point(px, py)

    def point(self, position, error=ERROR):
        """
        find the point that corresponds to given value [0,1].
        Where t=0 is the first point and t=1 is the final point.

        :param position:
        :return: point at t
        """
        return self.point_at_t(tau * position)

    def _ramanujan_length(self):
        a = self.implicit_rx
        b = self.implicit_ry
        if b > a:
            a, b = b, a
        h = (a - b) ** 2 / (a + b) ** 2
        return pi * (a + b) * (1 + (3 * h / (10 + sqrt(4 - 3 * h))))


class Ellipse(_RoundShape):
    """
    SVG Ellipse shapes are defined in SVG2 10.4
    https://www.w3.org/TR/SVG2/shapes.html#EllipseElement

    These have geometric properties cx, cy, rx, ry
    """

    def __init__(self, *args, **kwargs):
        _RoundShape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Ellipse(self)

    def _name(self):
        return self.__class__.__name__


class Circle(_RoundShape):
    """
    SVG Circle shapes are defined in SVG2 10.3
    https://www.w3.org/TR/SVG2/shapes.html#CircleElement

    These have geometric properties cx, cy, r
    """

    def __init__(self, *args, **kwargs):
        _RoundShape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Circle(self)

    def _name(self):
        return self.__class__.__name__


class SimpleLine(Shape):
    """
    SVG Line shapes are defined in SVG2 10.5
    https://www.w3.org/TR/SVG2/shapes.html#LineElement

    These have geometric properties x1, y1, x2, y2

    These are called Line in SVG but that name is already used for Line(PathSegment)
    """

    def __init__(self, *args, **kwargs):
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None
        Shape.__init__(self, *args, **kwargs)

    def property_by_object(self, s):
        Shape.property_by_object(self, s)
        self.x1 = s.x1
        self.y1 = s.y1
        self.x2 = s.x2
        self.y2 = s.y2

    def property_by_values(self, values):
        Shape.property_by_values(self, values)
        self.x1 = Length(values.get(SVG_ATTR_X1, 0)).value()
        self.y1 = Length(values.get(SVG_ATTR_Y1, 0)).value()
        self.x2 = Length(values.get(SVG_ATTR_X2, 0)).value()
        self.y2 = Length(values.get(SVG_ATTR_Y2, 0)).value()

    def property_by_args(self, *args):
        arg_length = len(args)
        if arg_length >= 1:
            self.x1 = Length(args[0]).value()
        if arg_length >= 2:
            self.y1 = Length(args[1]).value()
        if arg_length >= 3:
            self.x2 = Length(args[2]).value()
        if arg_length >= 4:
            self.y2 = Length(args[3]).value()
        self._init_shape(*args[4:])

    def __repr__(self):
        values = []
        if self.x1 is not None:
            values.append('x1=%s' % repr(self.x1))
        if self.y1 is not None:
            values.append('y1=%s' % repr(self.y1))
        if self.x2 is not None:
            values.append('x2=%s' % repr(self.x2))
        if self.y2 is not None:
            values.append('y2=%s' % repr(self.y2))
        self._repr_shape(values)
        params = ", ".join(values)
        return "SimpleLine(%s)" % params

    def __copy__(self):
        return SimpleLine(self)

    @property
    def implicit_x1(self):
        point = Point(self.x1, self.y1)
        point *= self.transform
        return point.x

    @property
    def implicit_y1(self):
        point = Point(self.x1, self.y1)
        point *= self.transform
        return point.y

    @property
    def implicit_x2(self):
        point = Point(self.x2, self.y2)
        point *= self.transform
        return point.x

    @property
    def implicit_y2(self):
        point = Point(self.x2, self.y2)
        point *= self.transform
        return point.y

    def segments(self, transformed=True):
        """
        SVG path decomposition is given in SVG 2.0 10.5.

        perform an absolute moveto operation to absolute location (x1,y1)
        perform an absolute lineto operation to absolute location (x2,y2)

        :returns Path_d path for line.
        """

        start = Point(self.x1, self.y1)
        end = Point(self.x2, self.y2)
        if transformed:
            start *= self.transform
            end *= self.transform
        return (Move(None, start), Line(start, end))

    def reify(self):
        """
        Realizes the transform to the shape properties.

        SimpleLines are perfectly reified.
        """
        GraphicObject.reify(self)
        Transformable.reify(self)
        matrix = self.transform
        p = Point(self.x1, self.y1)
        p *= matrix
        self.x1 = p.x
        self.y1 = p.y

        p = Point(self.x2, self.y2)
        p *= matrix
        self.x2 = p.x
        self.y2 = p.y

        matrix.reset()
        return self

    def render(self, **kwargs):
        Shape.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.x1, Length):
            self.x1 = self.x1.value(relative_length=width, **kwargs)
        if isinstance(self.y1, Length):
            self.y1 = self.y1.value(relative_length=height, **kwargs)
        if isinstance(self.x2, Length):
            self.x2 = self.x2.value(relative_length=width, **kwargs)
        if isinstance(self.y2, Length):
            self.y2 = self.y2.value(relative_length=height, **kwargs)
        return self


class _Polyshape(Shape):
    """Base form of Polygon and Polyline since the objects are nearly the same."""

    def __init__(self, *args, **kwargs):
        self.points = list()
        Shape.__init__(self, *args, **kwargs)

    def property_by_object(self, s):
        Shape.property_by_object(self, s)
        self._init_points(s.points)

    def property_by_values(self, values):
        Shape.property_by_values(self, values)
        self._init_points(values)

    def property_by_args(self, *args):
        self._init_points(args)

    def _init_points(self, points):
        if len(self.points) != 0:
            return
        if points is None:
            self.points = list()
            return
        if isinstance(points, dict):
            if SVG_ATTR_POINTS in points:
                points = points[SVG_ATTR_POINTS]
            else:
                self.points = list()
                return
        try:
            if len(points) == 1:
                points = points[0]
        except TypeError:
            pass
        if isinstance(points, str):
            findall = REGEX_COORD_PAIR.findall(points)
            self.points = [Point(float(j), float(k)) for j, k in findall]
        elif isinstance(points, (list, tuple)):
            if len(points) == 0:
                self.points = list()
            else:
                first_point = points[0]
                if isinstance(first_point, (float, int)):
                    self.points = list(map(Point, zip(*[iter(points)] * 2)))
                elif isinstance(first_point, (list, tuple, complex, str, Point)):
                    self.points = list(map(Point, points))
        else:
            self.points = list()

    def __repr__(self):
        values = []
        if self.points is not None:
            s = ", ".join(map(str, self.points))
            values.append('points=(%s)' % repr(s))
        self._repr_shape(values)
        params = ", ".join(values)
        name = self._name()
        return "%s(%s)" % (name, params)

    def __len__(self):
        return len(self.points)

    def __getitem__(self, item):
        return self.points[item]

    def segments(self, transformed=True):
        """
        Polyline and Polygon decomposition is given in SVG2. 10.6 and 10.7

        * perform an absolute moveto operation to the first coordinate pair in the list of points
        * for each subsequent coordinate pair, perform an absolute lineto operation to that coordinate pair.
        * (Polygon-only) perform a closepath command

        Note:  For a polygon/polyline made from n points, the resulting path will
        be composed of n lines (even if some of these lines have length zero).
        """
        if self.transform.is_identity() or not transformed:
            points = self.points
        else:
            points = list(map(self.transform.point_in_matrix_space, self.points))
        if len(points) == 0:
            return []
        segments = [Move(None, points[0])]
        last = points[0]
        for i in range(1, len(points)):
            current = points[i]
            segments.append(Line(last, current))
            last = current
        if isinstance(self, Polygon):
            segments.append(Close(last, points[0]))
        return segments

    def reify(self):
        """
        Realizes the transform to the shape properties.

        Polyshapes are perfectly reified.
        """
        GraphicObject.reify(self)
        Transformable.reify(self)
        matrix = self.transform
        for p in self:
            p *= matrix
        matrix.reset()
        return self


class Polyline(_Polyshape):
    """
    SVG Polyline shapes are defined in SVG2 10.6
    https://www.w3.org/TR/SVG2/shapes.html#PolylineElement

    These have geometric properties points
    """

    def __init__(self, *args, **kwargs):
        _Polyshape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Polyline(self)

    def _name(self):
        return self.__class__.__name__


class Polygon(_Polyshape):
    """
    SVG Polygon shapes are defined in SVG2 10.7
    https://www.w3.org/TR/SVG2/shapes.html#PolygonElement

    These have geometric properties points
    """

    def __init__(self, *args, **kwargs):
        _Polyshape.__init__(self, *args, **kwargs)

    def __copy__(self):
        return Polygon(self)

    def _name(self):
        return self.__class__.__name__


class Subpath:
    """
    Subpath is a Path-backed window implementation. It does not store a list of segments but rather
    stores a Path, start position, end position. When a function is called on a subpath, the result of
    those events is performed on the backing Path. When the backing Path is modified the behavior is
    undefined."""

    def __init__(self, path, start, end):
        self._path = path
        self._start = start
        self._end = end

    def __copy__(self):
        return Subpath(Path(self._path), self._start, self._end)

    def __getitem__(self, index):
        return self._path[self.index_to_path_index(index)]

    def __setitem__(self, index, value):
        self._path[self.index_to_path_index(index)] = value

    def __delitem__(self, index):
        del self._path[self.index_to_path_index(index)]
        self._end -= 1

    def __iadd__(self, other):
        if isinstance(other, str):
            p = Path(other)
            self._path[self._end:self._end] = p
        elif isinstance(other, Path):
            p = copy(other)
            self._path[self._end:self._end] = p
        elif isinstance(other, PathSegment):
            self._path.insert(self._end, other)
        else:
            return NotImplemented
        return self

    def __add__(self, other):
        if isinstance(other, (str, Path, PathSegment)):
            n = copy(self)
            n += other
            return n
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            path = Path(other)
            path.extend(map(copy, self._path))
            return path
        elif isinstance(other, PathSegment):
            path = Path(self)
            path.insert(0, other)
            return path
        else:
            return NotImplemented

    def __imul__(self, other):
        if isinstance(other, str):
            other = Matrix(other)
        if isinstance(other, Matrix):
            for e in self:
                e *= other
        return self

    def __mul__(self, other):
        if isinstance(other, (Matrix, str)):
            n = copy(self)
            n *= other
            return n
        return NotImplemented

    __rmul__ = __mul__

    def __iter__(self):
        class Iterator:
            def __init__(self, subpath):
                self.n = subpath._start - 1
                self.subpath = subpath

            def __next__(self):
                self.n += 1
                try:
                    if self.n > self.subpath._end:
                        raise StopIteration
                    return self.subpath._path[self.n]
                except IndexError:
                    raise StopIteration

            next = __next__

        return Iterator(self)

    def __len__(self):
        return self._end - self._start + 1

    def __str__(self):
        return self.d()

    def __repr__(self):
        return 'Path(%s)' % (', '.join(repr(x) for x in self))

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(Path(other))
        if not isinstance(other, (Path, Subpath)):
            return NotImplemented
        if len(self) != len(other):
            return False
        for s, o in zip(self, other):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, (Path, Subpath, str)):
            return NotImplemented
        return not self == other

    def segments(self, transformed=True):
        path = self._path
        if transformed:
            return [s * path.transform for s in path._segments[self._start:self._end + 1]]
        return path._segments[self._start:self._end + 1]

    def _numeric_index(self, index):
        if index < 0:
            return self._end + index + 1
        else:
            return self._start + index

    def index_to_path_index(self, index):
        if isinstance(index, slice):
            start = index.start
            stop = index.stop
            step = index.step
            if start is None:
                start = 0
            start = self._numeric_index(start)
            if stop is None:
                stop = len(self)
            stop = self._numeric_index(stop)
            return slice(start, stop, step)
        return self._numeric_index(index)

    def bbox(self):
        """returns a bounding box for the input Path"""
        segments = self._path._segments[self._start:self._end + 1]
        bbs = [seg.bbox() for seg in segments if not isinstance(Close, Move)]
        try:
            xmins, ymins, xmaxs, ymaxs = list(zip(*bbs))
        except ValueError:
            return None  # No bounding box items existed. So no bounding box.
        xmin = min(xmins)
        xmax = max(xmaxs)
        ymin = min(ymins)
        ymax = max(ymaxs)
        return xmin, ymin, xmax, ymax

    def d(self, relative=None, smooth=None):
        segments = self._path._segments[self._start:self._end + 1]
        return Path.svg_d(segments, relative=relative, smooth=None)

    def _reverse_segments(self, start, end):
        """Reverses segments between the given indexes in the subpath space."""
        segments = self._path._segments  # must avoid path validation.
        s = self.index_to_path_index(start)
        e = self.index_to_path_index(end)
        while s <= e:
            start_segment = segments[s]
            end_segment = segments[e]
            start_segment.reverse()
            if start_segment is not end_segment:
                end_segment.reverse()
                segments[s] = end_segment
                segments[e] = start_segment
            s += 1
            e -= 1
        start = self.index_to_path_index(start)
        end = self.index_to_path_index(end)
        self._path._validate_connection(start - 1, prefer_second=True)
        self._path._validate_connection(end)

    def reverse(self):
        size = len(self)
        if size == 0:
            return
        start = 0
        end = size - 1
        if isinstance(self[-1], Close):
            end -= 1
        if isinstance(self[0], Move):  # Move remains in place but references next element.
            start += 1
        self._reverse_segments(start, end)
        if size > 1:
            if isinstance(self[0], Move):
                self[0].end = Point(self[1].start)
        last = self[-1]
        if isinstance(last, Close):
            last.reverse()
            if last.start != self[-2].end:
                last.start = Point(self[-2].end)
            if last.end != self[0].end:
                last.end = Point(self[0].end)
        return self


class Group(SVGElement, Transformable, list):
    """
    Group Container element can have children.
    SVG 2.0 <g> are defined in:
    5.2. Grouping: the g element
    """
    # TODO: This should override the Transformable math and propagate to children.
    def __init__(self, *args, **kwargs):
        Transformable.__init__(self, *args, **kwargs)
        list.__init__(self)
        if len(args) >= 1:
            s = args[0]
            if isinstance(s, Group):
                self.extend(list(map(copy, s)))
                return
        SVGElement.__init__(self, *args, **kwargs)

    def render(self, **kwargs):
        Transformable.render(self, **kwargs)

    def __copy__(self):
        return Group(self)

    def select(self, conditional=None):
        """
        Finds all flattened subobjects of this group for which the conditional returns
        true.

        :param conditional: function taking element and returns True or False if matching
        """
        if conditional is None:
            def conditional(item):
                return True
        for subitem in self:
            if not conditional(subitem):
                continue
            yield subitem
            if isinstance(subitem, Group):
                for s in subitem.select(conditional):
                    yield s

    def reify(self):
        pass


class ClipPath(SVGElement, list):
    """
    clipPath elements are defined in svg 14.3.5
    https://www.w3.org/TR/SVG11/masking.html#ClipPathElement

    Clip paths conceptually define a 1 bit mask for images these are usually defined within
    def blocks and do not render themselves but rather are attached by IRI references to the
    """

    def __init__(self, *args, **kwargs):
        list.__init__(self)
        self.unit_type = SVG_UNIT_TYPE_USERSPACEONUSE
        SVGElement.__init__(self, *args, **kwargs)

    def property_by_object(self, s):
        SVGElement.property_by_object(self, s)
        self.unit_type = s.unit_type

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        self.unit_type = self.values.get(SVG_ATTR_CLIP_UNIT_TYPE, SVG_UNIT_TYPE_USERSPACEONUSE)


class Pattern(SVGElement, list):
    def __init__(self, *args, **kwargs):
        self.viewbox = None
        self.preserve_aspect_ratio = None
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.href = None
        self.pattern_content_units = None  # UserSpaceOnUse default
        self.pattern_transform = None
        self.pattern_units = None
        SVGElement.__init__(self, *args, **kwargs)

    def __int__(self):
        return 0

    @property
    def viewbox_transform(self):
        if self.viewbox is None:
            return ''
        return self.viewbox.transform(self)

    def property_by_object(self, s):
        SVGElement.property_by_object(self, s)
        self.viewbox = s.viewbox
        self.preserve_aspect_ratio = s.preserve_aspect_ratio

        self.x = s.x
        self.y = s.y
        self.width = s.width
        self.height = s.height
        self.href = s.href
        self.pattern_content_units = s.pattern_contents_units
        self.pattern_transform = Matrix(s.pattern_transform) if s.pattern_transform is not None else None
        self.pattern_units = s.pattern_units

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        if XLINK_HREF in values:
            self.href = values[XLINK_HREF]
        elif SVG_HREF in values:
            self.href = values[SVG_HREF]
        viewbox = values.get(SVG_ATTR_VIEWBOX)
        if viewbox is not None:
            self.viewbox = Viewbox(viewbox)
        if SVG_ATTR_PRESERVEASPECTRATIO in values:
            self.preserve_aspect_ratio = values[SVG_ATTR_PRESERVEASPECTRATIO]
        self.x = Length(values.get(SVG_ATTR_X, 0)).value()
        self.y = Length(values.get(SVG_ATTR_Y, 0)).value()
        self.width = Length(values.get(SVG_ATTR_WIDTH, '100%')).value()
        self.height = Length(values.get(SVG_ATTR_HEIGHT, '100%')).value()
        if SVG_ATTR_PATTERN_CONTENT_UNITS in values:
            self.pattern_content_units = values[SVG_ATTR_PATTERN_CONTENT_UNITS]
        if SVG_ATTR_PATTERN_TRANSFORM in values:
            self.pattern_transform = Matrix(values[SVG_ATTR_PATTERN_TRANSFORM])
        if SVG_ATTR_PATTERN_UNITS in values:
            self.pattern_units = values[SVG_ATTR_PATTERN_UNITS]

    def render(self, **kwargs):
        if self.pattern_transform is not None:
            self.pattern_transform.render(**kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.width, Length):
            self.width = self.width.value(relative_length=width, **kwargs)
        if isinstance(self.height, Length):
            self.height = self.height.value(relative_length=height, **kwargs)
        return self


class SVGText(SVGElement, GraphicObject, Transformable):
    """
    SVG Text are defined in SVG 2.0 Chapter 11

    No methods are implemented to perform a text to path conversion.

    However, if such a method exists the assumption is that the results will be
    placed in the .path attribute, and functions like bbox() will check if such
    a value exists.
    """

    def __init__(self, *args, **kwargs):
        if len(args) >= 1:
            self.text = args[0]
        else:
            self.text = ''
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0
        self.anchor = 'start'  # start, middle, end.
        self.font_family = 'san-serif'
        self.font_size = 16.0  # 16 point font 'normal'
        self.font_weight = 400.0  # Thin=100, Normal=400, Bold=700
        self.font_face = ''

        self.path = None
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)
        SVGElement.__init__(self, *args, **kwargs)

    def __str__(self):
        parts = list()
        parts.append("'%s'" % self.text)
        parts.append('font_family=%s' % self.font_family)
        parts.append('anchor=%s' % self.anchor)
        parts.append('font_size=%d' % self.font_size)
        parts.append('font_weight=%s' % str(self.font_weight))
        return 'Text(%s)' % (', '.join(parts))

    def __repr__(self):
        parts = list()
        parts.append('%s' % self.text)
        parts.append('font_family=%s' % self.font_family)
        parts.append('anchor=%s' % self.anchor)
        parts.append('font_size=%d' % self.font_size)
        parts.append('font_weight=%s' % str(self.font_weight))
        return 'Text(%s)' % (', '.join(parts))

    def property_by_object(self, s):
        Transformable.property_by_object(self, s)
        GraphicObject.property_by_object(self, s)
        self.text = s.text
        self.x = s.x
        self.y = s.y
        self.width = s.width
        self.height = s.height
        self.dx = s.dx
        self.dy = s.dy
        self.anchor = s.anchor
        self.font_family = s.font_family
        self.font_size = s.font_size
        self.font_weight = s.font_weight
        self.font_face = s.font_face

    def parse_font(self, font):
        """
        CSS Fonts 3 has a shorthand font property which serves to provide a single location to define:
        ‘font-style’, ‘font-variant’, ‘font-weight’, ‘font-stretch’, ‘font-size’, ‘line-height’, and ‘font-family’

        font-style: normal | italic | oblique
        font-variant: normal | small-caps
        font-weight: normal | bold | bolder | lighter | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900
        font-stretch: normal | ultra-condensed | extra-condensed | condensed | semi-condensed | semi-expanded | expanded | extra-expanded | ultra-expanded
        font-size: <absolute-size> | <relative-size> | <length-percentage>
        line-height: '/' <‘line-height’>
        font-family: [ <family-name> | <generic-family> ] #
        generic-family:  ‘serif’, ‘sans-serif’, ‘cursive’, ‘fantasy’, and ‘monospace’
         """
        # https://www.w3.org/TR/css-fonts-3/#font-prop
        font_elements = list(*re.findall(REGEX_CSS_FONT, font))

        font_style = font_elements[0]
        font_variant = font_elements[1]
        font_weight = font_elements[2]
        font_stretch = font_elements[3]
        font_size = font_elements[4]
        line_height = font_elements[5]
        font_face = font_elements[6]
        font_family = font_elements[7]
        if len(font_weight) > 0:
            self.font_weight = self.parse_font_weight(font_weight)
        if len(font_size) > 0:
            self.font_size = Length(font_size).value()
        if len(font_face) > 0:
            if font_face.endswith(','):
                font_face = font_face[:-1]
            self.font_face = font_face

        if len(font_family) > 0:
            self.font_family = font_family

    def parse_font_weight(self, weight):
        if weight == 'bold':
            return 700
        if weight == 'normal':
            return 400
        try:
            return int(weight)
        except KeyError:
            return 400

    def property_by_values(self, values):
        Transformable.property_by_values(self, values)
        GraphicObject.property_by_values(self, values)
        self.anchor = values.get(SVG_ATTR_TEXT_ANCHOR, self.anchor)
        self.font_face = values.get(SVG_ATTR_FONT_FACE)
        self.font_family = values.get(SVG_ATTR_FONT_FAMILY, self.font_family)
        self.font_size = Length(values.get(SVG_ATTR_FONT_SIZE, self.font_size)).value()
        self.font_weight = values.get(SVG_ATTR_FONT_WEIGHT, self.font_weight)
        font = values.get(SVG_ATTR_FONT, None)
        if font is not None:
            self.parse_font(font)
        self.text = values.get(SVG_TAG_TEXT, self.text)
        self.x = Length(values.get(SVG_ATTR_X, self.x)).value()
        self.y = Length(values.get(SVG_ATTR_Y, self.y)).value()
        self.dx = Length(values.get(SVG_ATTR_DX, self.dx)).value()
        self.dy = Length(values.get(SVG_ATTR_DY, self.dy)).value()

    def reify(self):
        GraphicObject.reify(self)
        Transformable.reify(self)

    def render(self, **kwargs):
        GraphicObject.render(self, **kwargs)
        Transformable.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.dx, Length):
            self.dx = self.dx.value(relative_length=width, **kwargs)
        if isinstance(self.dy, Length):
            self.dy = self.dy.value(relative_length=height, **kwargs)
        return self

    def __copy__(self):
        return SVGText(self)

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given text object.
        """
        if self.path is not None:
            return (self.path * self.transform).bbox(transformed=True)
        width = self.width
        height = self.height
        xmin = self.x
        ymin = self.y - height
        xmax = self.x + width
        ymax = self.y
        if not hasattr(self, 'anchor') or self.anchor == 'start':
            pass
        elif self.anchor == 'middle':
            xmin -= (width / 2)
            xmax -= (width / 2)
        elif self.anchor == 'end':
            xmin -= width
            xmax -= width
        if transformed:
            p0 = self.transform.transform_point([xmin, ymin])
            p1 = self.transform.transform_point([xmin, ymax])
            p2 = self.transform.transform_point([xmax, ymin])
            p3 = self.transform.transform_point([xmax, ymax])
            xmin = min(p0[0], p1[0], p2[0], p3[0])
            ymin = min(p0[1], p1[1], p2[1], p3[1])
            xmax = max(p0[0], p1[0], p2[0], p3[0])
            ymax = max(p0[1], p1[1], p2[1], p3[1])
        return xmin, ymin, xmax, ymax


class SVGImage(SVGElement, GraphicObject, Transformable):
    """
    SVG Images are defined in SVG 2.0 12.3

    This class is called SVG Image rather than image as a guard against many Image objects
    which are quite useful and would be ideal for reading the linked or contained data.
    """

    def __init__(self, *args, **kwargs):
        self.url = None
        self.data = None
        self.viewbox = None
        self.preserve_aspect_ratio = None
        self.x = None
        self.y = None
        self.width = None
        self.height = None

        self.image = None
        self.image_width = None
        self.image_height = None
        Transformable.__init__(self, *args, **kwargs)
        GraphicObject.__init__(self, *args, **kwargs)
        SVGElement.__init__(self, *args, **kwargs)  # Dataurl requires this be processed first.

        if self.url is not None:
            if self.url.startswith("data:image/"):
                # Data URL
                from base64 import b64decode
                if self.url.startswith("data:image/png;base64,"):
                    self.data = b64decode(self.url[22:])
                elif self.url.startswith("data:image/jpg;base64,"):
                    self.data = b64decode(self.url[22:])
                elif self.url.startswith("data:image/jpeg;base64,"):
                    self.data = b64decode(self.url[23:])
                elif self.url.startswith("data:image/svg+xml;base64,"):
                    self.data = b64decode(self.url[26:])

    def property_by_object(self, s):
        SVGElement.property_by_object(self, s)
        Transformable.property_by_object(self, s)
        GraphicObject.property_by_object(self, s)
        self.url = s.url
        self.data = s.data
        self.viewbox = s.viewbox
        self.preserve_aspect_ratio = s.preserve_aspect_ratio

        self.x = s.x
        self.y = s.y
        self.width = s.width
        self.height = s.height

        self.image = s.image
        self.image_width = s.image_width
        self.image_height = s.image_height

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        Transformable.property_by_values(self, values)
        GraphicObject.property_by_values(self, values)
        if XLINK_HREF in values:
            self.url = values[XLINK_HREF]
        elif SVG_HREF in values:
            self.url = values[SVG_HREF]
        viewbox = values.get(SVG_ATTR_VIEWBOX)
        if viewbox is not None:
            self.viewbox = Viewbox(viewbox)
        if SVG_ATTR_PRESERVEASPECTRATIO in values:
            self.preserve_aspect_ratio = values[SVG_ATTR_PRESERVEASPECTRATIO]
        self.x = Length(values.get(SVG_ATTR_X, 0)).value()
        self.y = Length(values.get(SVG_ATTR_Y, 0)).value()
        self.width = Length(values.get(SVG_ATTR_WIDTH, '100%')).value()
        self.height = Length(values.get(SVG_ATTR_HEIGHT, '100%')).value()
        if 'image' in values:
            self.image = values['image']
            self.image_width, self.image_height = self.image.size

    def render(self, **kwargs):
        GraphicObject.render(self, **kwargs)
        Transformable.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        if isinstance(self.x, Length):
            self.x = self.x.value(relative_length=width, **kwargs)
        if isinstance(self.y, Length):
            self.y = self.y.value(relative_length=height, **kwargs)
        if isinstance(self.width, Length):
            self.width = self.width.value(relative_length=width, **kwargs)
        if isinstance(self.height, Length):
            self.height = self.height.value(relative_length=height, **kwargs)
        return self

    def __copy__(self):
        """
        Copy of SVGImage. This will not copy the .image subobject in a deep manner
        since it's optional that that object will exist or not. As such if using PIL it would
        be required to either say self.image = self.image.copy() or call .load() again.
        """
        return SVGImage(self)

    @property
    def viewbox_transform(self):
        if self.viewbox is None:
            return ''
        return self.viewbox.transform(self)

    def load(self, directory=None):
        try:
            from PIL import Image
            if self.data is not None:
                self.load_data()
            elif self.url is not None:
                self.load_file(directory)
            self.set_values_by_image()
        except ImportError:
            pass

    def load_data(self):
        try:
            # This code will not activate without PIL/Pillow installed.
            from PIL import Image
            if self.data is not None:
                from io import BytesIO
                self.image = Image.open(BytesIO(self.data))
            else:
                return
        except ImportError:
            # PIL/Pillow not found, decoding data is most we can do.
            pass

    def load_file(self, directory):
        try:
            # This code will not activate without PIL/Pillow installed.
            from PIL import Image
            if self.url is not None:
                try:
                    self.image = Image.open(self.url)
                except IOError:
                    try:
                        if directory is not None:
                            from os.path import join
                            relpath = join(directory, self.url)
                            self.image = Image.open(relpath)
                    except IOError:
                        return
        except ImportError:
            # PIL/Pillow not found, decoding data is most we can do.
            pass

    def set_values_by_image(self):
        if self.image is not None:
            self.image_width = self.image.width
            self.image_height = self.image.height
        else:
            return
        self.viewbox = Viewbox("0 0 %d %d" % (self.image_width, self.image_height), self.preserve_aspect_ratio)
        self.transform = Matrix(self.viewbox_transform) * self.transform

    def bbox(self, transformed=True):
        """
        Get the bounding box for the given image object
        """
        if self.image_width is None or self.image_height is None:
            p = Point(0, 0)
            p *= self.transform
            return p.x, p.y, p.x, p.y
        width = self.image_width
        height = self.image_height
        if transformed:
            p = (Point(0, 0) * self.transform,
                 Point(width, 0) * self.transform,
                 Point(width, height) * self.transform,
                 Point(0, height) * self.transform)
        else:
            p = (Point(0, 0),
                 Point(width, 0),
                 Point(width, height),
                 Point(0, height))
        x_vals = list(s.x for s in p)
        y_vals = list(s.y for s in p)
        min_x = min(x_vals)
        min_y = min(y_vals)
        max_x = max(x_vals)
        max_y = max(y_vals)
        return min_x, min_y, max_x, max_y


class Desc(SVGElement):
    def __init__(self, values, desc=None):
        self.desc = desc
        SVGElement.__init__(self, **values)

    def property_by_object(self, obj):
        SVGElement.property_by_object(self, obj)
        self.desc = obj.desc

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        if SVG_TAG_DESC in values:
            self.desc = values[SVG_TAG_DESC]


SVGDesc = Desc


class Title(SVGElement):
    def __init__(self, values, title=None):
        self.title = title
        SVGElement.__init__(self,**values)

    def property_by_object(self, obj):
        SVGElement.property_by_object(self, obj)
        self.title = obj.title

    def property_by_values(self, values):
        SVGElement.property_by_values(self, values)
        if SVG_TAG_TITLE in values:
            self.title = values[SVG_TAG_TITLE]


class SVG(Group):
    """
    SVG Document and Parsing.

    SVG is the SVG main object and also the embedded SVGs within it. It's a subtype of Group. The SVG has a viewbox,
    and parsing methods which can be used if given a stream, path, or svg string.
    """
    def __init__(self, *args, **kwargs):
        self.objects = {}
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.viewbox = None
        Group.__init__(self, *args, **kwargs)

    def property_by_object(self, s):
        Group.property_by_object(self, s)
        self.x = s.x
        self.y = s.y
        self.width = s.width
        self.height = s.height
        self.viewbox = Viewbox(s.viewbox) if s.viewbox is not None else None

    def property_by_values(self, values):
        Group.property_by_values(self, values)
        self.x = Length(values.get(SVG_ATTR_X, 0)).value()
        self.y = Length(values.get(SVG_ATTR_Y, 0)).value()
        self.width = Length(values.get(SVG_ATTR_WIDTH, '100%')).value()
        self.height = Length(values.get(SVG_ATTR_HEIGHT, '100%')).value()
        viewbox = values.get(SVG_ATTR_VIEWBOX)
        par = values.get(SVG_ATTR_PRESERVEASPECTRATIO)
        self.viewbox = Viewbox(viewbox, par) if viewbox is not None else None

    def get_element_by_id(self, id):
        return self.objects.get(id)

    def get_element_by_url(self, url):
        for _id in REGEX_IRI.findall(url):
            return self.get_element_by_id(_id)

    def render(self, **kwargs):
        Group.render(self, **kwargs)
        width = kwargs.get('width', kwargs.get('relative_length'))
        height = kwargs.get('height', kwargs.get('relative_length'))
        try:
            del kwargs['relative_length']
        except KeyError:
            pass
        self.width = Length(self.width).value(relative_length=width, **kwargs)
        self.height = Length(self.height).value(relative_length=height, **kwargs)
        self.x = Length(self.x).value(relative_length=width, **kwargs)
        self.y = Length(self.y).value(relative_length=height, **kwargs)

    def elements(self, conditional=None):
        yield self
        for q in self.select(conditional):
            yield q

    @property
    def viewbox_transform(self):
        if self.viewbox is None:
            return ''
        return self.viewbox.transform(self)

    @staticmethod
    def _shadow_iter(elem, children):
        yield 'start', elem
        try:
            for e, c in children:
                for shadow_event, shadow_elem in SVG._shadow_iter(e, c):
                    yield shadow_event, shadow_elem
        except RecursionError:
            """
            Strictly speaking it is possible to reference use from other use objects. If this is an infinite loop
            we should not block the rendering. Just say we finished. See: W3C, struct-use-12-f
            """
            pass
        yield 'end', elem

    @staticmethod
    def _use_structure_parse(source):
        """
        SVG structure pass: parses the svg file such that it creates the structure implied by reused objects in a
        generalized context. Objects ids are read and put into an unparsed shadow tree. <use> objects seamlessly contain
        their definitions.
        """
        defs = {}
        parent = None  # Define Root Node.
        children = list()

        for event, elem in iterparse(source, events=('start', 'end', 'start-ns')):
            try:
                tag = elem.tag
                if tag.startswith('{http://www.w3.org/2000/svg'):
                    tag = tag[28:]  # Removing namespace. http://www.w3.org/2000/svg:
                    elem.tag = tag
            except AttributeError:
                yield event, elem
                continue

            if event == 'start':
                attributes = elem.attrib
                # Create new node.
                siblings = children  # Parent's children are now my siblings.
                parent = (parent, children)  # parent is now previous node context
                children = list()  # new node has no children.
                node = (elem, children)  # define this node.
                siblings.append(node)  # siblings now includes this node.

                if SVG_TAG_USE == tag:
                    url = None
                    if XLINK_HREF in attributes:
                        url = attributes[XLINK_HREF]
                    if SVG_HREF in attributes:
                        url = attributes[SVG_HREF]
                    if url is not None:
                        transform = False
                        try:
                            x = attributes[SVG_ATTR_X]
                            del attributes[SVG_ATTR_X]
                            transform = True
                        except KeyError:
                            x = '0'
                        try:
                            y = attributes[SVG_ATTR_Y]
                            del attributes[SVG_ATTR_Y]
                            transform = True
                        except KeyError:
                            y = '0'
                        if transform:
                            try:
                                attributes[SVG_ATTR_TRANSFORM] = '%s translate(%s, %s)' % \
                                                                 (attributes[SVG_ATTR_TRANSFORM], x, y)
                            except KeyError:
                                attributes[SVG_ATTR_TRANSFORM] = 'translate(%s, %s)' % (x, y)
                        yield event, elem
                        try:
                            shadow_node = defs[url[1:]]
                            children.append(shadow_node)  # Shadow children are children of the use.
                            for n in SVG._shadow_iter(*shadow_node):
                                yield n
                        except KeyError:
                            pass  # Failed to find link.
                else:
                    yield event, elem
                if SVG_ATTR_ID in attributes:  # If we have an ID, we save the node.
                    defs[attributes[SVG_ATTR_ID]] = node  # store node value in defs.
            elif event == 'end':
                yield event, elem
                # event is 'end', pop values.
                parent, children = parent  # Parent is now node.

    @staticmethod
    def parse(source,
              reify=True,
              ppi=DEFAULT_PPI,
              width=1000,
              height=1000,
              color="black",
              transform=None,
              context=None):
        """
        Parses the SVG file. All attributes are things which the SVG document itself could not be aware of, such as
        the real size of pixels and the size of the viewport (as opposed to the viewbox).

        :param source: Source svg file or stream.
        :param reify: Should the Geometry sized or have lazy matrices.
        :param ppi: How many physical pixels per inch are there in this view.
        :param width: The physical width of the viewport
        :param height: The physical height of the viewport
        :param color: the `currentColor` value from outside the current scope.
        :param transform: Any required transformations to be pre-applied to this document
        :param context: Any existing document context.
        :return:
        """
        clip = 0
        root = context
        styles = {}
        stack = []

        values = {SVG_ATTR_COLOR: color, SVG_ATTR_FILL: "black", SVG_ATTR_STROKE: "none"}

        if transform is not None:
            values[SVG_ATTR_TRANSFORM] = transform

        for event, elem in SVG._use_structure_parse(source):
            """
            SVG element parsing parses the job compiling any parsed elements into their compiled object forms. 
            """
            # print(event, elem)
            if event == 'start':
                stack.append((context, values))
                if SVG_ATTR_DISPLAY in values and values[SVG_ATTR_DISPLAY] == SVG_VALUE_NONE:
                    continue  # Values has a display=none. Do not render anything. No Shadow Dom.
                current_values = values
                values = {}
                values.update(current_values)  # copy of dictionary
                tag = elem.tag

                # Non-propagating values.
                if SVG_ATTR_PRESERVEASPECTRATIO in values:
                    del values[SVG_ATTR_PRESERVEASPECTRATIO]
                if SVG_ATTR_VIEWBOX in values:
                    del values[SVG_ATTR_VIEWBOX]
                if SVG_ATTR_ID in values:
                    del values[SVG_ATTR_ID]
                if SVG_ATTR_CLIP_PATH in values:
                    del values[SVG_ATTR_CLIP_PATH]

                attributes = elem.attrib  # priority; lowest
                attributes[SVG_ATTR_TAG] = tag

                # Split any Style block elements into parts; priority medium
                style = ''
                if '*' in styles:  # Select all.
                    style += styles['*']
                if tag in styles:  # selector type
                    style += styles[tag]
                if SVG_ATTR_ID in attributes:  # Selector id #id
                    svg_id = attributes[SVG_ATTR_ID]
                    css_tag = '#%s' % svg_id
                    if css_tag in styles:
                        if len(style) != 0:
                            style += ';'
                        style += styles[css_tag]
                if SVG_ATTR_CLASS in attributes:  # Selector class .class
                    for svg_class in attributes[SVG_ATTR_CLASS].split(' '):
                        css_tag = '.%s' % svg_class
                        if css_tag in styles:
                            if len(style) != 0:
                                style += ';'
                            style += styles[css_tag]
                        css_tag = '%s.%s' % (tag, svg_class)  # Selector type/class type.class
                        if css_tag in styles:
                            if len(style) != 0:
                                style += ';'
                            style += styles[css_tag]
                # Split style element into parts; priority highest
                if SVG_ATTR_STYLE in attributes:
                    style += attributes[SVG_ATTR_STYLE]

                # Process style tag left to right.
                for equate in style.split(";"):
                    equal_item = equate.split(":")
                    if len(equal_item) == 2:
                        key = str(equal_item[0]).strip()
                        value = str(equal_item[1]).strip()
                        attributes[key] = value
                if SVG_ATTR_FILL in attributes and attributes[SVG_ATTR_FILL] == SVG_VALUE_CURRENT_COLOR:
                    if SVG_ATTR_COLOR in attributes:
                        attributes[SVG_ATTR_FILL] = attributes[SVG_ATTR_COLOR]
                    else:
                        attributes[SVG_ATTR_FILL] = values[SVG_ATTR_COLOR]

                if SVG_ATTR_STROKE in attributes and attributes[SVG_ATTR_STROKE] == SVG_VALUE_CURRENT_COLOR:
                    if SVG_ATTR_COLOR in attributes:
                        attributes[SVG_ATTR_STROKE] = attributes[SVG_ATTR_COLOR]
                    else:
                        attributes[SVG_ATTR_STROKE] = values[SVG_ATTR_COLOR]

                if SVG_ATTR_TRANSFORM in attributes:
                    # If transform is already in values, append the new value.
                    if SVG_ATTR_TRANSFORM in values:
                        attributes[SVG_ATTR_TRANSFORM] = values[SVG_ATTR_TRANSFORM] + \
                                                         " " + \
                                                         attributes[SVG_ATTR_TRANSFORM]
                    else:
                        attributes[SVG_ATTR_TRANSFORM] = attributes[SVG_ATTR_TRANSFORM]

                # All class and attribute properties are compiled.

                values.update(attributes)
                if SVG_ATTR_DISPLAY in values and values[SVG_ATTR_DISPLAY] == SVG_VALUE_NONE:
                    continue  # If the attributes flags our values to display=none, stop rendering.
                if SVG_NAME_TAG == tag:
                    # The ordering for transformations on the SVG object are:
                    # explicit transform, parent transforms, attribute transforms, viewport transforms
                    s = SVG(values)
                    s.render(ppi=ppi, width=width, height=height)
                    height, width = s.width, s.height
                    if s.viewbox is not None:
                        try:
                            if s.height == 0 or s.width == 0:
                                return s
                            viewport_transform = s.viewbox_transform
                        except ZeroDivisionError:
                            # The width or height was zero.
                            # https://www.w3.org/TR/SVG11/struct.html#SVGElementWidthAttribute
                            # "A value of zero disables rendering of the element."
                            return s  # No more parsing will be done.

                        if SVG_ATTR_TRANSFORM in values:
                            # transform on SVG element applied as if svg had parent with transform.
                            values[SVG_ATTR_TRANSFORM] += " " + viewport_transform
                        else:
                            values[SVG_ATTR_TRANSFORM] = viewport_transform
                        width, height = s.viewbox.width, s.viewbox.height
                    if context is None:
                        stack[-1] = (context, values)
                    if context is not None:
                        context.append(s)
                    context = s
                    if root is None:
                        root = s
                elif SVG_TAG_GROUP == tag:
                    s = Group(values)
                    context.append(s)
                    context = s
                    s.render(ppi=ppi, width=width, height=height)
                elif SVG_TAG_DEFS == tag:
                    s = Group(values)
                    context = s  # Non-Rendered
                    s.render(ppi=ppi, width=width, height=height)
                elif SVG_TAG_CLIPPATH == tag:
                    s = ClipPath(values)
                    context = s  # Non-Rendered
                    s.render(ppi=ppi, width=width, height=height)
                    clip += 1
                elif SVG_TAG_PATTERN == tag:
                    s = Pattern(values)
                    context = s  # Non-rendered
                    s.render(ppi=ppi, width=width, height=height)
                elif tag in (SVG_TAG_PATH, SVG_TAG_CIRCLE, SVG_TAG_ELLIPSE, SVG_TAG_LINE,  # Shapes
                             SVG_TAG_POLYLINE, SVG_TAG_POLYGON, SVG_TAG_RECT, SVG_TAG_IMAGE):
                    try:
                        if SVG_TAG_PATH == tag:
                            s = Path(values)
                        elif SVG_TAG_CIRCLE == tag:
                            s = Circle(values)
                        elif SVG_TAG_ELLIPSE == tag:
                            s = Ellipse(values)
                        elif SVG_TAG_LINE == tag:
                            s = SimpleLine(values)
                        elif SVG_TAG_POLYLINE == tag:
                            s = Polyline(values)
                        elif SVG_TAG_POLYGON == tag:
                            s = Polygon(values)
                        elif SVG_TAG_RECT == tag:
                            s = Rect(values)
                        else:  # SVG_TAG_IMAGE == tag:
                            s = SVGImage(values)
                    except ValueError:
                        continue
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    context.append(s)
                elif tag in (SVG_TAG_STYLE, SVG_TAG_TEXT, SVG_TAG_DESC, SVG_TAG_TITLE, SVG_TAG_TSPAN):
                    # <style>, <text>, <desc>, <title>
                    continue
                else:
                    s = SVGElement(values)  # SVG Unknown object return as element.
                    context.append(s)

                # Assign optional linked properties.
                try:
                    clip_path_url = s.values.get(SVG_ATTR_CLIP_PATH, None)
                    if clip_path_url is not None:
                        clip_path = root.get_element_by_url(clip_path_url)
                        s.clip_path = clip_path
                except AttributeError:
                    pass
                if clip != 0:
                    try:
                        clip_rule = s.values.get(SVG_ATTR_CLIP_RULE, SVG_RULE_NONZERO)
                        if clip_rule is not None:
                            s.clip_rule = clip_rule
                    except AttributeError:
                        pass
                if SVG_ATTR_ID in values and root is not None:
                    root.objects[attributes[SVG_ATTR_ID]] = s
            elif event == 'end':  # End event.
                # The iterparse spec makes it clear that internal text data is undefined except at the end.
                s = None
                tag = elem.tag
                if tag in (SVG_TAG_TEXT, SVG_TAG_TSPAN, SVG_TAG_DESC, SVG_TAG_TITLE, SVG_TAG_STYLE):
                    attributes = elem.attrib
                    if SVG_ATTR_ID in values and root is not None:
                        root.objects[attributes[SVG_ATTR_ID]] = s
                if tag in (SVG_TAG_TEXT, SVG_TAG_TSPAN):
                    s = SVGText(values, text=elem.text)
                    s.render(ppi=ppi, width=width, height=height)
                    if reify:
                        s.reify()
                    context.append(s)
                elif SVG_TAG_DESC == tag:
                    s = Desc(values, desc=elem.text)
                    context.append(s)
                elif SVG_TAG_TITLE == tag:
                    s = Title(values, title=elem.text)
                    context.append(s)
                elif SVG_TAG_STYLE == tag:
                    assignments = list(re.findall(REGEX_CSS_STYLE, elem.text))
                    for key, value in assignments:
                        key = key.strip()
                        value = value.strip()
                        for selector in key.split(','):  # Can comma select subitems.
                            styles[selector.strip()] = value
                elif SVG_TAG_CLIPPATH == tag:
                    clip -= 1
                if s is not None:
                    # Assign optional linked properties.
                    try:
                        clip_path_url = s.values.get(SVG_ATTR_CLIP_PATH, None)
                        if clip_path_url is not None:
                            clip_path = root.get_element_by_url(clip_path_url)
                            s.clip_path = clip_path
                    except AttributeError:
                        pass
                    if clip != 0:
                        try:
                            clip_rule = s.values.get(SVG_ATTR_CLIP_RULE, SVG_RULE_NONZERO)
                            if clip_rule is not None:
                                s.clip_rule = clip_rule
                        except AttributeError:
                            pass

                context, values = stack.pop()
            elif event == 'start-ns':
                if elem[0] != SVG_ATTR_DATA:
                    values[elem[0]] = elem[1]
        return root
