import math
import os
import struct

import numpy as np

ASCII_FACET = """facet normal {normal[0]:.4f} {normal[1]:.4f} {normal[2]:.4f}
outer loop
vertex {face[0][0]:.4f} {face[0][1]:.4f} {face[0][2]:.4f}
vertex {face[1][0]:.4f} {face[1][1]:.4f} {face[1][2]:.4f}
vertex {face[2][0]:.4f} {face[2][1]:.4f} {face[2][2]:.4f}
endloop
endfacet
"""

BINARY_HEADER = "80sI"
BINARY_FACET = "12fH"


def crossproduct(u, v):
    s1 = u[1] * v[2] - u[2] * v[1]
    s2 = u[2] * v[0] - u[0] * v[2]
    s3 = u[0] * v[1] - u[1] * v[0]
    return [s1, s2, s3]


def norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def normalize(v):
    m = norm(v)
    return [v[0] / m, v[1] / m, v[2] / m]


def normalto(u, v):
    return normalize(crossproduct(u, v))


# functions for calculation of the normal vector (right-thumb-rule)
def crossProduct(a, b):
    # calculate cross product of two threedimensional vectors
    if (len(a) != 3) or (len(b) != 3):
        raise ValueError("invalid value")
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def diff(v1, v2):
    # subtracting one list from another
    if (len(v1) != 3) or (len(v2) != 3):
        raise ValueError("invalid value")
    return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]]


def normal(v1, v2, v3):
    # calculate normal vector on triangle spanned by the three vertices
    # tells in which direction the plane looks "right-thumb-rule"
    if (len(v1) != 3) or (len(v2) != 3) or (len(v2) != 3):
        raise ValueError("invalid value")
    n = crossProduct(diff(v2, v1), diff(v3, v1))
    absolut = 0
    for i in n:
        if i >= 0:
            absolut += i
        else:
            absolut -= i
    if absolut == 0:
        return n
    else:
        return [n[0] / absolut, n[1] / absolut, n[2] / absolut]


class ASCII_STL_Writer:
    """Export 3D objects build of 3 or 4 vertices as ASCII STL file."""

    def __init__(self, stream):
        self.fp = stream
        self._write_header()

    def _write_header(self):
        self.fp.write("solid python\n")

    def close(self):
        self.fp.write("endsolid python\n")

    def _write(self, face):
        n = normalto(diff(face[0], face[1]), diff(face[1], face[2]))
        self.fp.write(ASCII_FACET.format(normal=n, face=face))

    def _split(self, face):
        p1, p2, p3, p4 = face
        return (p1, p2, p3), (p3, p4, p1)

    def add_face(self, face):
        """Add one face with 3 or 4 vertices."""
        if len(face) == 4:
            face1, face2 = self._split(face)
            self._write(face1)
            self._write(face2)
        elif len(face) == 3:
            self._write(face)
        else:
            raise ValueError("only 3 or 4 vertices for each face")

    def add_faces(self, faces):
        """Add many faces."""
        for face in faces:
            self.add_face(face)


class Binary_STL_Writer(ASCII_STL_Writer):
    """Export 3D objects build of 3 or 4 vertices as binary STL file."""

    def __init__(self, stream):
        self.counter = 0
        ASCII_STL_Writer.__init__(self, stream)

    def close(self):
        self._write_header()

    def _write_header(self):
        self.fp.seek(0)
        self.fp.write(
            struct.pack(
                BINARY_HEADER, b"Python Binary STL Writer", self.counter)
        )

    def _write(self, face):
        self.counter += 1
        n = normalto(diff(face[0], face[1]), diff(face[1], face[2]))
        data = [
            n[0],
            n[1],
            n[2],
            face[0][0],
            face[0][1],
            face[0][2],
            face[1][0],
            face[1][1],
            face[1][2],
            face[2][0],
            face[2][1],
            face[2][2],
            0,
        ]
        self.fp.write(struct.pack(BINARY_FACET, *data))


# Binary STL: 80-byte header, uint32 triangle count, then 50 bytes per facet
_HEADER = 80
_COUNT = 4
_FACET = 50  # 12 float32 + uint16 attribute


def load_stl(fileobj):
    """Load an STL mesh (ASCII or binary) from a path or file-like object.

    Returns verts (Nx3) and faces (Mx3). Each triangle contributes three
    vertices; callers may merge duplicates.
    """
    if isinstance(fileobj, (str, bytes, os.PathLike)):
        with open(fileobj, "rb") as f:
            data = f.read()
    else:
        data = fileobj.read()
        if isinstance(data, str):
            data = data.encode("latin1")

    if _is_ascii(data):
        return _load_ascii(data)
    return _load_binary(data)


def _is_ascii(data):
    """Detect ASCII STL. Some binary files start with b'solid'."""
    if len(data) < _HEADER + _COUNT:
        return True
    if not data.lstrip().lower().startswith(b"solid"):
        return False
    (ntris,) = struct.unpack_from("<I", data, _HEADER)
    return _HEADER + _COUNT + ntris * _FACET != len(data)


def _load_ascii(data):
    text = data.decode("ascii", errors="ignore")
    verts = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].lower() == "vertex":
            verts.append(
                (float(parts[1]), float(parts[2]), float(parts[3]))
            )
    if not verts or len(verts) % 3 != 0:
        raise ValueError("invalid ASCII STL: expected vertex triplets")
    verts = np.asarray(verts, dtype=np.float64)
    faces = np.arange(len(verts), dtype=np.int_).reshape(-1, 3)
    return verts, faces


def _load_binary(data):
    if len(data) < _HEADER + _COUNT:
        raise ValueError("invalid binary STL: file too short")
    (ntris,) = struct.unpack_from("<I", data, _HEADER)
    expected = _HEADER + _COUNT + ntris * _FACET
    if len(data) < expected:
        raise ValueError(
            f"invalid binary STL: expected {expected} bytes, got {len(data)}"
        )
    verts = np.empty((ntris * 3, 3), dtype=np.float64)
    offset = _HEADER + _COUNT
    for i in range(ntris):
        # normal(3) + v0(3) + v1(3) + v2(3) + attribute(1 uint16)
        vals = struct.unpack_from("<12fH", data, offset)
        offset += _FACET
        base = i * 3
        verts[base] = vals[3:6]
        verts[base + 1] = vals[6:9]
        verts[base + 2] = vals[9:12]
    faces = np.arange(ntris * 3, dtype=np.int_).reshape(-1, 3)
    return verts, faces
