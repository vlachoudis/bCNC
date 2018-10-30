svg.path
========

svg.path is a collection of objects that implement the different path
commands in SVG, and a parser for SVG path definitions.


Usage
-----

There are four path segment objects, ``Line``, ``Arc``, ``CubicBezier`` and
``QuadraticBezier``.`There is also a ``Path`` object that acts as a
collection of the path segment objects.

All coordinate values for these classes are given as ``complex`` values,
where the ``.real`` part represents the X coordinate, and the ``.imag`` part
representes the Y coordinate.

    >>> from svg.path import Path, Line, Arc, CubicBezier, QuadraticBezier

All of these objects have a ``.point()`` function which will return the
coordinates of a point on the path, where the point is given as a floating
point value where ``0.0`` is the start of the path and ``1.0`` is end end.

You can calculate the length of a Path or it's segments with the
``.length()`` function. For CubicBezier and Arc segments this is done by
geometric approximation and for this reason **may be very slow**. You can
make it faster by passing in an ``error`` option to the method. If you
don't pass in error, it defaults to ``1e-12``.

    >>> CubicBezier(300+100j, 100+100j, 200+200j, 200+300j).length(error=1e-5)
    297.2208145656899

CubicBezier and Arc also has a ``min_depth`` option that specifies the
minimum recursion depth. This is set to 5 by default, resulting in using a
minimum of 32 segments for the calculation. Setting it to 0 is a bad idea for
CubicBeziers, as they may become approximated to a straight line.

``Line.length()`` and ``QuadraticBezier.length()`` also takes these
parameters, but they are ignored.

CubicBezier and QuadraticBezier also has ``is_smooth_from(previous)``
methods, that check if the segment is a "smooth" segment compared to the
given segment.

There is also a ``parse_path()`` function that will take an SVG path definition
and return a ``Path`` object.

    >>> from svg.path import parse_path
    >>> parse_path('M 100 100 L 300 100')
    Path(Move(to=(100+100j)), Line(start=(100+100j), end=(300+100j)), closed=False)


Classes
.......

These are the SVG path segment classes. See the `SVG specifications
<http://www.w3.org/TR/SVG/paths.html>`_ for more information on what each
parameter means.

* ``Line(start, end)``

* ``Arc(start, radius, rotation, arc, sweep, end)``

* ``QuadraticBezier(start, control, end)``

* ``CubicBezier(start, control1, control2, end)``

In addition to that, there is the ``Path`` class, which is instantiated
with a sequence of path segments:

* ``Path(*segments)``

The ``Path`` class is a mutable sequence, so it behaves like a list.
You can add to it and replace path segments etc.

    >>> path = Path(Line(100+100j,300+100j), Line(100+100j,300+100j))
    >>> path.append(QuadraticBezier(300+100j, 200+200j, 200+300j))
    >>> path[0] = Line(200+100j,300+100j)
    >>> del path[1]

The path object also has a ``d()`` method that will return the
SVG representation of the Path segments.

    >>> path.d()
    'M 200,100 L 300,100 Q 200,200 200,300'


Examples
........

This SVG path example draws a triangle:


    >>> path1 = parse_path('M 100 100 L 300 100 L 200 300 z')

You can format SVG paths in many different ways, all valid paths should be
accepted:

    >>> path2 = parse_path('M100,100L300,100L200,300z')

And these paths should be equal:

    >>> path1 == path2
    True

You can also build a path from objects:

    >>> path3 = Path(Line(100+100j,300+100j), Line(300+100j, 200+300j), Line(200+300j, 100+100j))

And it should again be equal to the first path:

    >>> path1 == path2
    True

Paths are mutable sequences, you can slice and append:

    >>> path1.append(QuadraticBezier(300+100j, 200+200j, 200+300j))
    >>> len(path1[2:]) == 3
    True

Paths also have a ``closed`` property, which defines if the path should be
seen as a closed path or not.

    >>> path = parse_path('M100,100L300,100L200,300z')
    >>> path.closed
    True

If you modify the path in such a way that it is no longer closeable, it will
not be closed.

    >>> path[0].start = (100+105j)
    >>> path[1].start = (100+105j)
    >>> path.closed
    False

However, a path previously set as closed will automatically close if it it
further modified to that it can be closed.

    >>> path[-1].end = (300+100j)
    >>> path.closed
    True

Trying to set a Path to be closed if the end does not coincide with the start
of any segment will raise an error.

    >>> path = parse_path('M100,100L300,100L200,300')
    >>> path.closed = True
    Traceback (most recent call last):
    ...
    ValueError: End does not coincide with a segment start.


Future features
---------------

* Reversing paths. They should then reasonably be drawn "backwards" meaning each
  path segment also needs to be reversed.

* Mathematical transformations might make sense.


Licence
-------

This module is under a MIT License.
