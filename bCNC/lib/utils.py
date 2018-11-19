import numpy as np
import numpy.linalg as la
#import mayavi.mlab as mlab


def points3d(verts, point_size=3, **kwargs):
    if 'mode' not in kwargs:
        kwargs['mode'] = 'point'
    p = mlab.points3d(verts[:, 0], verts[:, 1], verts[:, 2], **kwargs)
    p.actor.property.point_size = point_size


def trimesh3d(verts, faces, **kwargs):
    mlab.triangular_mesh(verts[:, 0], verts[:, 1], verts[:, 2], faces,
                         **kwargs)


def orthogonal_vector(v):
    """Return an arbitrary vector that is orthogonal to v"""
    if v[1] != 0 or v[2] != 0:
        c = (1, 0, 0)
    else:
        c = (0, 1, 0)
    return np.cross(v, c)


def show_plane(orig, n, scale=1.0, **kwargs):
    """
    Show the plane with the given origin and normal. scale give its size
    """
    b1 = orthogonal_vector(n)
    b1 /= la.norm(b1)
    b2 = np.cross(b1, n)
    b2 /= la.norm(b2)
    verts = [orig + scale*(-b1 - b2),
             orig + scale*(b1 - b2),
             orig + scale*(b1 + b2),
             orig + scale*(-b1 + b2)]
    faces = [(0, 1, 2), (0, 2, 3)]
    trimesh3d(np.array(verts), faces, **kwargs)
