from __future__ import division
from __future__ import absolute_import
from math import sqrt, cos, sin, acos, degrees, radians, log
from collections import MutableSequence


# This file contains classes for the different types of SVG path segments as
# well as a Path object that contains a sequence of path segments.

MIN_DEPTH = 5
ERROR = 1e-12


def segment_length(curve, start, end, start_point, end_point, error, min_depth, depth):
    """Recursively approximates the length by straight lines"""
    mid = (start + end) / 2
    mid_point = curve.point(mid)
    length = abs(end_point - start_point)
    first_half = abs(mid_point - start_point)
    second_half = abs(end_point - mid_point)

    length2 = first_half + second_half
    if (length2 - length > error) or (depth < min_depth):
        # Calculate the length of each segment:
        depth += 1
        return (segment_length(curve, start, mid, start_point, mid_point,
                               error, min_depth, depth) +
                segment_length(curve, mid, end, mid_point, end_point,
                               error, min_depth, depth))
    # This is accurate enough.
    return length2


class Line(object):

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return 'Line(start=%s, end=%s)' % (self.start, self.end)

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __ne__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return not self == other

    def point(self, pos):
        distance = self.end - self.start
        return self.start + distance * pos

    def length(self, error=None, min_depth=None):
        distance = (self.end - self.start)
        return sqrt(distance.real ** 2 + distance.imag ** 2)


class CubicBezier(object):
    def __init__(self, start, control1, control2, end):
        self.start = start
        self.control1 = control1
        self.control2 = control2
        self.end = end

    def __repr__(self):
        return 'CubicBezier(start=%s, control1=%s, control2=%s, end=%s)' % (
               self.start, self.control1, self.control2, self.end)

    def __eq__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control1 == other.control1 and self.control2 == other.control2

    def __ne__(self, other):
        if not isinstance(other, CubicBezier):
            return NotImplemented
        return not self == other

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, CubicBezier):
            return (self.start == previous.end and
                    (self.control1 - self.start) == (previous.end - previous.control2))
        else:
            return self.control1 == self.start

    def point(self, pos):
        """Calculate the x,y position at a certain position of the path"""
        return ((1 - pos) ** 3 * self.start) + \
               (3 * (1 - pos) ** 2 * pos * self.control1) + \
               (3 * (1 - pos) * pos ** 2 * self.control2) + \
               (pos ** 3 * self.end)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """Calculate the length of the path up to a certain position"""
        start_point = self.point(0)
        end_point = self.point(1)
        return segment_length(self, 0, 1, start_point, end_point, error, min_depth, 0)


class QuadraticBezier(object):
    def __init__(self, start, control, end):
        self.start = start
        self.end = end
        self.control = control

    def __repr__(self):
        return 'QuadraticBezier(start=%s, control=%s, end=%s)' % (
               self.start, self.control, self.end)

    def __eq__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.control == other.control

    def __ne__(self, other):
        if not isinstance(other, QuadraticBezier):
            return NotImplemented
        return not self == other

    def is_smooth_from(self, previous):
        """Checks if this segment would be a smooth segment following the previous"""
        if isinstance(previous, QuadraticBezier):
            return (self.start == previous.end and
                    (self.control - self.start) == (previous.end - previous.control))
        else:
            return self.control == self.start

    def point(self, pos):
        return (1 - pos) ** 2 * self.start + 2 * (1 - pos) * pos * self.control + \
               pos ** 2 * self.end

    def length(self, error=None, min_depth=None):
        a = self.start - 2*self.control + self.end
        b = 2*(self.control - self.start)
        a_dot_b = a.real*b.real + a.imag*b.imag

        if abs(a) < 1e-12:
            s = abs(b)
        elif abs(a_dot_b + abs(a)*abs(b)) < 1e-12:
            k = abs(b)/abs(a)
            if k >= 2:
                s = abs(b) - abs(a)
            else:
                s = abs(a)*(k**2/2 - k + 1)
        else:
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
        return s


class Arc(object):

    def __init__(self, start, radius, rotation, arc, sweep, end):
        """radius is complex, rotation is in degrees,
           large and sweep are 1 or 0 (True/False also work)"""

        self.start = start
        self.radius = radius
        self.rotation = rotation
        self.arc = bool(arc)
        self.sweep = bool(sweep)
        self.end = end

        self._parameterize()

    def __repr__(self):
        return 'Arc(start=%s, radius=%s, rotation=%s, arc=%s, sweep=%s, end=%s)' % (
               self.start, self.radius, self.rotation, self.arc, self.sweep, self.end)

    def __eq__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return self.start == other.start and self.end == other.end and \
               self.radius == other.radius and self.rotation == other.rotation and \
               self.arc == other.arc and self.sweep == other.sweep

    def __ne__(self, other):
        if not isinstance(other, Arc):
            return NotImplemented
        return not self == other

    def _parameterize(self):
        # Conversion from endpoint to center parameterization
        # http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
        if self.start == self.end:
            # This is equivalent of omitting the segment, so do nothing
            return

        cosr = cos(radians(self.rotation))
        sinr = sin(radians(self.rotation))
        dx = (self.start.real - self.end.real) / 2
        dy = (self.start.imag - self.end.imag) / 2
        x1prim = cosr * dx + sinr * dy
        x1prim_sq = x1prim * x1prim
        y1prim = -sinr * dx + cosr * dy
        y1prim_sq = y1prim * y1prim

        rx = self.radius.real
        rx_sq = rx * rx
        ry = self.radius.imag
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

        if self.arc == self.sweep:
            c = -c
        cxprim = c * rx * y1prim / ry
        cyprim = -c * ry * x1prim / rx

        self.center = complex((cosr * cxprim - sinr * cyprim) +
                              ((self.start.real + self.end.real) / 2),
                              (sinr * cxprim + cosr * cyprim) +
                              ((self.start.imag + self.end.imag) / 2))

        ux = (x1prim - cxprim) / rx
        uy = (y1prim - cyprim) / ry
        vx = (-x1prim - cxprim) / rx
        vy = (-y1prim - cyprim) / ry
        n = sqrt(ux * ux + uy * uy)
        p = ux
        theta = degrees(acos(p / n))
        if uy < 0:
            theta = -theta
        self.theta = theta % 360

        n = sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
        p = ux * vx + uy * vy
        d = p/n
        # In certain cases the above calculation can through inaccuracies
        # become just slightly out of range, f ex -1.0000000000000002.
        if d > 1.0:
            d = 1.0
        elif d < -1.0:
            d = -1.0
        delta = degrees(acos(d))
        if (ux * vy - uy * vx) < 0:
            delta = -delta
        self.delta = delta % 360
        if not self.sweep:
            self.delta -= 360

    def point(self, pos):
        if self.start == self.end:
            # This is equivalent of omitting the segment
            return self.start
        angle = radians(self.theta + (self.delta * pos))
        cosr = cos(radians(self.rotation))
        sinr = sin(radians(self.rotation))

        x = (cosr * cos(angle) * self.radius.real - sinr * sin(angle) *
             self.radius.imag + self.center.real)
        y = (sinr * cos(angle) * self.radius.real + cosr * sin(angle) *
             self.radius.imag + self.center.imag)
        return complex(x, y)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        """The length of an elliptical arc segment requires numerical
        integration, and in that case it's simpler to just do a geometric
        approximation, as for cubic bezier curves.
        """
        if self.start == self.end:
            # This is equivalent of omitting the segment
            return 0
        start_point = self.point(0)
        end_point = self.point(1)
        return segment_length(self, 0, 1, start_point, end_point, error, min_depth, 0)


class Move(object):
    """Represents move commands. Does nothing, but is there to handle
    paths that consist of only move commands, which is valid, but pointless.
    """

    def __init__(self, to):
        self.start = self.end = to

    def __repr__(self):
        return 'Move(to=%s)' % self.start

    def __eq__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return self.start == other.start

    def __ne__(self, other):
        if not isinstance(other, Move):
            return NotImplemented
        return not self == other

    def point(self, pos):
        return self.start

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        return 0


class Path(MutableSequence):
    """A Path is a sequence of path segments"""

    # Put it here, so there is a default if unpickled.
    _closed = False

    def __init__(self, *segments, **kw):
        self._segments = list(segments)
        self._length = None
        self._lengths = None
        if 'closed' in kw:
            self.closed = kw['closed']

    def __getitem__(self, index):
        return self._segments[index]

    def __setitem__(self, index, value):
        self._segments[index] = value
        self._length = None

    def __delitem__(self, index):
        del self._segments[index]
        self._length = None

    def insert(self, index, value):
        self._segments.insert(index, value)
        self._length = None

    def reverse(self):
        # Reversing the order of a path would require reversing each element
        # as well. That's not implemented.
        raise NotImplementedError

    def __len__(self):
        return len(self._segments)

    def __repr__(self):
        return 'Path(%s, closed=%s)' % (
            ', '.join(repr(x) for x in self._segments), self.closed)

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        if len(self) != len(other):
            return False
        for s, o in zip(self._segments, other._segments):
            if not s == o:
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return not self == other

    def _calc_lengths(self, error=ERROR, min_depth=MIN_DEPTH):
        if self._length is not None:
            return

        lengths = [each.length(error=error, min_depth=min_depth) for each in self._segments]
        self._length = sum(lengths)
        self._lengths = [each / self._length for each in lengths]

    def point(self, pos, error=ERROR):

        # Shortcuts
        if pos == 0.0:
            return self._segments[0].point(pos)
        if pos == 1.0:
            return self._segments[-1].point(pos)

        self._calc_lengths(error=error)
        # Find which segment the point we search for is located on:
        segment_start = 0
        for index, segment in enumerate(self._segments):
            segment_end = segment_start + self._lengths[index]
            if segment_end >= pos:
                # This is the segment! How far in on the segment is the point?
                segment_pos = (pos - segment_start) / (segment_end - segment_start)
                break
            segment_start = segment_end

        return segment.point(segment_pos)

    def length(self, error=ERROR, min_depth=MIN_DEPTH):
        self._calc_lengths(error, min_depth)
        return self._length

    def _is_closable(self):
        """Returns true if the end is on the start of a segment"""
        end = self[-1].end
        for segment in self:
            if segment.start == end:
                return True
        return False

    @property
    def closed(self):
        """Checks that the path is closed"""
        return self._closed and self._is_closable()

    @closed.setter
    def closed(self, value):
        value = bool(value)
        if value and not self._is_closable():
            raise ValueError("End does not coincide with a segment start.")
        self._closed = value

    def d(self):
        if self.closed:
            segments = self[:-1]
        else:
            segments = self[:]

        current_pos = None
        parts = []
        previous_segment = None
        end = self[-1].end

        for segment in segments:
            start = segment.start
            # If the start of this segment does not coincide with the end of
            # the last segment or if this segment is actually the close point
            # of a closed path, then we should start a new subpath here.
            if isinstance(segment, Move) or (current_pos != start) or (
               start == end and not isinstance(previous_segment, Move)):
                parts.append('M {0:G},{1:G}'.format(start.real, start.imag))

            if isinstance(segment, Line):
                parts.append('L {0:G},{1:G}'.format(
                    segment.end.real, segment.end.imag)
                )
            elif isinstance(segment, CubicBezier):
                if segment.is_smooth_from(previous_segment):
                    parts.append('S {0:G},{1:G} {2:G},{3:G}'.format(
                        segment.control2.real, segment.control2.imag,
                        segment.end.real, segment.end.imag)
                    )
                else:
                    parts.append('C {0:G},{1:G} {2:G},{3:G} {4:G},{5:G}'.format(
                        segment.control1.real, segment.control1.imag,
                        segment.control2.real, segment.control2.imag,
                        segment.end.real, segment.end.imag)
                    )
            elif isinstance(segment, QuadraticBezier):
                if segment.is_smooth_from(previous_segment):
                    parts.append('T {0:G},{1:G}'.format(
                        segment.end.real, segment.end.imag)
                    )
                else:
                    parts.append('Q {0:G},{1:G} {2:G},{3:G}'.format(
                        segment.control.real, segment.control.imag,
                        segment.end.real, segment.end.imag)
                    )

            elif isinstance(segment, Arc):
                parts.append('A {0:G},{1:G} {2:G} {3:d},{4:d} {5:G},{6:G}'.format(
                    segment.radius.real, segment.radius.imag, segment.rotation,
                    int(segment.arc), int(segment.sweep),
                    segment.end.real, segment.end.imag)
                )
            current_pos = segment.end
            previous_segment = segment

        if self.closed:
            parts.append('Z')

        return ' '.join(parts)
