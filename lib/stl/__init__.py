
import stl.ascii
import stl.binary

from stl.types import Solid, Facet, Vector3d


def read_ascii_file(file):
    """
    Read an STL file in the *ASCII* format.

    Takes a :py:class:`file`-like object (supporting a ``read`` method)
    and returns a :py:class:`stl.Solid` object representing the data
    from the file.

    If the file is invalid in any way, raises
    :py:class:`stl.ascii.SyntaxError`.
    """
    return stl.ascii.parse(file)


def read_binary_file(file):
    """
    Read an STL file in the *binary* format.

    Takes a :py:class:`file`-like object (supporting a ``read`` method)
    and returns a :py:class:`stl.Solid` object representing the data
    from the file.

    If the file is invalid in any way, raises
    :py:class:`stl.binary.FormatError`.
    """
    return stl.binary.parse(file)


def read_ascii_string(data):
    """
    Read geometry from a :py:class:`str` containing data in the STL *ASCII*
    format.

    This is just a wrapper around :py:func:`read_ascii_file` that first wraps
    the provided string in a :py:class:`StringIO.StringIO` object.
    """
    from StringIO import StringIO
    return parse_ascii_file(StringIO(data))


def read_binary_string(data):
    """
    Read geometry from a :py:class:`str` containing data in the STL *binary*
    format.

    This is just a wrapper around :py:func:`read_binary_file` that first wraps
    the provided string in a :py:class:`StringIO.StringIO` object.
    """
    from StringIO import StringIO
    return parse_binary_file(StringIO(data))
