import sys

IS_PYTHON2 = sys.version_info[0] == 2


# TODO: Check if this methods are still required
def b(s, encoding="ascii", errors="replace"):  # pragma: no cover
    if IS_PYTHON2:
        return bytes(s)
    else:
        if isinstance(s, str):
            return bytes(s, encoding, errors)
        else:
            return s


def s(s):  # pragma: no cover
    if IS_PYTHON2:
        return bytes(s)
    else:
        return s
