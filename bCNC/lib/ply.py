import numpy as np


def load_ply(fileobj):
    """Same as load_ply, but takes a file-like object"""

    def nextline():
        """Read next line, skip comments"""
        while True:
            line = fileobj.readline()
            assert line != ""  # eof
            if not line.startswith("comment"):
                return line.strip()

    assert nextline() == "ply"
    assert nextline() == "format ascii 1.0"
    line = nextline()
    assert line.startswith("element vertex")
    nverts = int(line.split()[2])
    assert nextline() == "property float x"
    assert nextline() == "property float y"
    assert nextline() == "property float z"
    line = nextline()

    assert line.startswith("element face")
    nfaces = int(line.split()[2])
    assert nextline() == "property list uchar int vertex_indices"
    line = nextline()
    has_texcoords = line == "property list uchar float texcoord"
    if has_texcoords:
        assert nextline() == "end_header"
    else:
        assert line == "end_header"

    # Verts
    verts = np.zeros((nverts, 3))
    for i in range(nverts):
        vals = nextline().split()
        verts[i, :] = [float(v) for v in vals[:3]]
    # Faces
    faces = []
    faces_uv = []
    for i in range(nfaces):
        vals = nextline().split()
        assert int(vals[0]) == 3
        faces.append([int(v) for v in vals[1:4]])
        if has_texcoords:
            assert len(vals) == 11
            assert int(vals[4]) == 6
            faces_uv.append(
                [
                    (float(vals[5]), float(vals[6])),
                    (float(vals[7]), float(vals[8])),
                    (float(vals[9]), float(vals[10])),
                ]
            )
        else:
            assert len(vals) == 4
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
