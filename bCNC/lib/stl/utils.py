from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys


IS_PYTHON2 = (sys.version_info[0] == 2)


def b(s, encoding='ascii', errors='replace'):  # pragma: no cover
    if IS_PYTHON2:
        return bytes(s)
    else:
        if isinstance(s, str):
            return bytes(s, encoding, errors)
        else:
            return s
        # return bytes(s, encoding, errors)


def s(s):  # pragma: no cover
    if IS_PYTHON2:
        return bytes(s)
    else:
        return s
