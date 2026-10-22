"""Minimal PLY loader/saver (ASCII and binary).

Supports triangle meshes with at least x/y/z vertex properties and a
list-valued face index property. Extra vertex/face properties are skipped.
Optional face texcoord lists are returned when present (ASCII or binary).
"""

import struct

import numpy as np

_TYPE_FORMAT = {
    "char": "b",
    "int8": "b",
    "uchar": "B",
    "uint8": "B",
    "short": "h",
    "int16": "h",
    "ushort": "H",
    "uint16": "H",
    "int": "i",
    "int32": "i",
    "uint": "I",
    "uint32": "I",
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}

_TYPE_SIZE = {name: struct.calcsize(fmt) for name, fmt in _TYPE_FORMAT.items()}


def _as_text(line):
    if isinstance(line, bytes):
        return line.decode("ascii", errors="replace")
    return line


def load_ply(fileobj):
    """Load a PLY mesh from a file-like object (text or binary).

    Returns (verts, faces, faces_uv) where faces_uv is a list of per-face
    UV triplets when a texcoord list property is present, else [].
    """
    header, fmt, endian = _read_header(fileobj)
    if fmt == "ascii":
        return _load_ascii(fileobj, header)
    return _load_binary(fileobj, header, endian)


def _read_header(fileobj):
    lines = []
    while True:
        raw = fileobj.readline()
        if raw == b"" or raw == "":
            raise ValueError("unexpected EOF in PLY header")
        line = _as_text(raw).strip()
        if line.startswith("comment") or line.startswith("obj_info"):
            continue
        lines.append(line)
        if line == "end_header":
            break

    if not lines or lines[0] != "ply":
        raise ValueError("not a PLY file")

    fmt = None
    endian = "<"
    elements = []
    current = None

    for line in lines[1:]:
        if line.startswith("format "):
            parts = line.split()
            name = parts[1]
            if name == "ascii":
                fmt = "ascii"
            elif name == "binary_little_endian":
                fmt = "binary"
                endian = "<"
            elif name == "binary_big_endian":
                fmt = "binary"
                endian = ">"
            else:
                raise ValueError(f"unsupported PLY format: {name}")
        elif line.startswith("element "):
            _name, count = line.split()[1], int(line.split()[2])
            current = {"name": _name, "count": count, "properties": []}
            elements.append(current)
        elif line.startswith("property ") and current is not None:
            parts = line.split()
            if parts[1] == "list":
                current["properties"].append(
                    {
                        "list": True,
                        "count_type": parts[2],
                        "value_type": parts[3],
                        "name": parts[4],
                    }
                )
            else:
                current["properties"].append(
                    {
                        "list": False,
                        "type": parts[1],
                        "name": parts[2],
                    }
                )
        elif line == "end_header":
            break

    if fmt is None:
        raise ValueError("PLY header missing format")
    return elements, fmt, endian


def _vertex_xyz_indices(props):
    names = [p["name"] for p in props if not p.get("list")]
    try:
        return names.index("x"), names.index("y"), names.index("z")
    except ValueError as exc:
        raise ValueError("PLY vertex element needs x, y, z properties") from exc


def _face_list_props(props):
    indices = None
    texcoords = None
    for prop in props:
        if not prop.get("list"):
            continue
        if prop["name"] in ("vertex_indices", "vertex_index"):
            indices = prop
        elif prop["name"] == "texcoord":
            texcoords = prop
    if indices is None:
        raise ValueError("PLY face element needs a vertex index list property")
    return indices, texcoords


def _load_ascii(fileobj, elements):
    def nextline():
        while True:
            raw = fileobj.readline()
            if raw == b"" or raw == "":
                raise ValueError("unexpected EOF in PLY body")
            line = _as_text(raw).strip()
            if line and not line.startswith("comment"):
                return line

    verts = None
    faces = []
    faces_uv = []

    for element in elements:
        name, count, props = element["name"], element["count"], element["properties"]
        if name == "vertex":
            ix, iy, iz = _vertex_xyz_indices(props)
            verts = np.zeros((count, 3), dtype=np.float64)
            nprop = len([p for p in props if not p.get("list")])
            # list props on vertices are rare; unsupported in ASCII path beyond skip
            for i in range(count):
                vals = nextline().split()
                floats = [float(v) for v in vals[:nprop]]
                verts[i, 0] = floats[ix]
                verts[i, 1] = floats[iy]
                verts[i, 2] = floats[iz]
        elif name == "face":
            indices_prop, tex_prop = _face_list_props(props)
            for _ in range(count):
                vals = nextline().split()
                pos = 0
                # properties in order
                face = None
                uvs = None
                for prop in props:
                    if prop.get("list"):
                        n = int(vals[pos])
                        pos += 1
                        items = vals[pos: pos + n]
                        pos += n
                        if prop is indices_prop:
                            if n != 3:
                                raise ValueError(
                                    "only triangular PLY faces are supported"
                                )
                            face = [int(v) for v in items]
                        elif prop is tex_prop:
                            if n != 6:
                                raise ValueError(
                                    "expected 6 texcoord values per triangle"
                                )
                            uvs = [
                                (float(items[0]), float(items[1])),
                                (float(items[2]), float(items[3])),
                                (float(items[4]), float(items[5])),
                            ]
                    else:
                        pos += 1
                faces.append(face)
                if tex_prop is not None:
                    faces_uv.append(uvs if uvs is not None else None)
        else:
            # skip unknown elements (ascii lines)
            for _ in range(count):
                nextline()

    if verts is None:
        raise ValueError("PLY file has no vertex element")
    return verts, faces, faces_uv


def _load_binary(fileobj, elements, endian):
    verts = None
    faces = []
    faces_uv = []

    def read_value(typename):
        fmt = endian + _TYPE_FORMAT[typename]
        raw = fileobj.read(struct.calcsize(fmt))
        if len(raw) != struct.calcsize(fmt):
            raise ValueError("unexpected EOF in binary PLY body")
        return struct.unpack(fmt, raw)[0]

    def skip_value(typename):
        size = _TYPE_SIZE[typename]
        if len(fileobj.read(size)) != size:
            raise ValueError("unexpected EOF in binary PLY body")

    for element in elements:
        name, count, props = element["name"], element["count"], element["properties"]
        if name == "vertex":
            ix, iy, iz = _vertex_xyz_indices(props)
            verts = np.zeros((count, 3), dtype=np.float64)
            scalar_props = [p for p in props if not p.get("list")]
            list_props = [p for p in props if p.get("list")]
            for i in range(count):
                scalars = []
                for prop in scalar_props:
                    scalars.append(float(read_value(prop["type"])))
                for prop in list_props:
                    n = int(read_value(prop["count_type"]))
                    for _ in range(n):
                        skip_value(prop["value_type"])
                verts[i, 0] = scalars[ix]
                verts[i, 1] = scalars[iy]
                verts[i, 2] = scalars[iz]
        elif name == "face":
            indices_prop, tex_prop = _face_list_props(props)
            for _ in range(count):
                face = None
                uvs = None
                for prop in props:
                    if prop.get("list"):
                        n = int(read_value(prop["count_type"]))
                        values = [
                            read_value(prop["value_type"]) for _ in range(n)
                        ]
                        if prop is indices_prop:
                            if n != 3:
                                raise ValueError(
                                    "only triangular PLY faces are supported"
                                )
                            face = [int(v) for v in values]
                        elif prop is tex_prop:
                            if n != 6:
                                raise ValueError(
                                    "expected 6 texcoord values per triangle"
                                )
                            uvs = [
                                (float(values[0]), float(values[1])),
                                (float(values[2]), float(values[3])),
                                (float(values[4]), float(values[5])),
                            ]
                    else:
                        skip_value(prop["type"])
                faces.append(face)
                if tex_prop is not None:
                    faces_uv.append(uvs if uvs is not None else None)
        else:
            for _ in range(count):
                for prop in props:
                    if prop.get("list"):
                        n = int(read_value(prop["count_type"]))
                        for _ in range(n):
                            skip_value(prop["value_type"])
                    else:
                        skip_value(prop["type"])

    if verts is None:
        raise ValueError("PLY file has no vertex element")
    return verts, faces, faces_uv


def save_ply(filename, verts, faces):
    with open(filename, "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write("element vertex %d\n" % verts.shape[0])
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")
        for i in range(verts.shape[0]):
            f.write(f"{verts[i, 0]:f} {verts[i, 1]:f} {verts[i, 2]:f}\n")
        for i in range(len(faces)):
            f.write("3 %d %d %d\n" % (faces[i][0], faces[i][1], faces[i][2]))
