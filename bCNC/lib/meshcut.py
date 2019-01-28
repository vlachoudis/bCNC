"""
Functions to slice a mesh. For now, computes planar cross-section
"""
from __future__ import absolute_import
import numpy as np
import numpy.linalg as la
try:
    import scipy.spatial.distance as spdist
    USE_SCIPY = True
except ImportError:
    USE_SCIPY = False
import collections

# ---- Geometry datastructures


def make_edge(v1, v2):
    """
    We store edges as tuple where the vertex indices are sorted (so
    the edge going from v1 to v2 and v2 to v1 is the same)
    """
    return tuple(sorted((v1, v2)))


class TriangleMesh(object):
    def __init__(self, verts, tris):
        """
        Args:
            verts: The 3D vertex positions
            tris: A list of triplet containing vertex indices for each triangle
        """
        self.verts = np.array(verts)
        # For each edge, contains the list of triangles it belongs to
        # If the mesh is closed, each edge belongs to 2 triangles
        self.edges_to_tris = collections.defaultdict(lambda: [])
        # For each triangle, contains the edges it contains
        self.tris_to_edges = {}
        # For each vertex, the list of triangles it belongs to
        self.verts_to_tris = collections.defaultdict(lambda: [])

        self.tris = tris

        # Fill data structures
        for tid, f in enumerate(tris):
            tri_edges = []
            for i in range(3):
                v1 = f[i]
                v2 = f[(i + 1) % 3]
                e = make_edge(v1, v2)
                self.edges_to_tris[e].append(tid)
                tri_edges.append(e)
                self.verts_to_tris[f[i]].append(tid)
            self.tris_to_edges[tid] = tri_edges

        # Sanity check : max 2 faces per edge
        for e, tris in self.edges_to_tris.items():
            assert len(tris) <= 2

    def edges_for_triangle(self, tidx):
        """Returns the edges forming triangle with given index"""
        return self.tris_to_edges[tidx]

    def triangles_for_edge(self, edge):
        return self.edges_to_tris[edge]

    def triangles_for_vert(self, vidx):
        """Returns the triangles `vidx` belongs to"""
        return self.verts_to_tris[vidx]


class Plane(object):
    def __init__(self, orig, normal):
        self.orig = orig
        self.n = normal / la.norm(normal)

    def __str__(self):
        return 'plane(o=%s, n=%s)' % (self.orig, self.n)


def point_to_plane_dist(p, plane):
    return np.dot((p - plane.orig), plane.n)


def triangle_intersects_plane(mesh, tid, plane):
    """
    Returns true if the given triangle is cut by the plane. This will return
    false if a single vertex of the triangle lies on the plane
    """
    dists = [point_to_plane_dist(mesh.verts[vid], plane)
             for vid in mesh.tris[tid]]
    side = np.sign(dists)
    return not (side[0] == side[1] == side[2])


# ---- Planar cross-section

INTERSECT_EDGE = 0
INTERSECT_VERTEX = 1


def compute_triangle_plane_intersections(mesh, tid, plane, dist_tol=1e-8):
    """
    Compute the intersection between a triangle and a plane

    Returns a list of intersections in the form
        (INTERSECT_EDGE, <intersection point>, <edge>) for edges intersection
        (INTERSECT_VERTEX, <intersection point>, <vertex index>) for vertices


    This return between 0 and 2 intersections :
    - 0 : the plane does not intersect the plane
    - 1 : one of the triangle's vertices lies on the plane (so it just
          "touches" the plane without really intersecting)
    - 2 : the plane slice the triangle in two parts (either vertex-edge,
          vertex-vertex or edge-edge)
    """
    # TODO: Use a distance cache
    dists = {vid: point_to_plane_dist(mesh.verts[vid], plane)
             for vid in mesh.tris[tid]}
    # TODO: Use an edge intersection cache (we currently compute each edge
    # intersection twice : once for each tri)

    # This is to avoid registering the same vertex intersection twice
    # from two different edges
    vert_intersect = {vid: False for vid in dists.keys()}

    # Iterate through the edges, cutting the ones that intersect
    intersections = []
    for e in mesh.edges_for_triangle(tid):
        v1 = mesh.verts[e[0]]
        d1 = dists[e[0]]
        v2 = mesh.verts[e[1]]
        d2 = dists[e[1]]

        if np.fabs(d1) < dist_tol:
            # Avoid creating the vertex intersection twice
            if not vert_intersect[e[0]]:
                # point on plane
                intersections.append((INTERSECT_VERTEX, v1, e[0]))
                vert_intersect[e[0]] = True
        if np.fabs(d2) < dist_tol:
            if not vert_intersect[e[1]]:
                # point on plane
                intersections.append((INTERSECT_VERTEX, v2, e[1]))
                vert_intersect[e[1]] = True

        # If vertices are on opposite sides of the plane, we have an edge
        # intersection
        if d1 * d2 < 0:
            # Due to numerical accuracy, we could have both a vertex intersect
            # and an edge intersect on the same vertex, which is impossible
            if not vert_intersect[e[0]] and not vert_intersect[e[1]]:
                # intersection factor (between 0 and 1)
                # here is a nice drawing :
                # https://ravehgonen.files.wordpress.com/2013/02/slide8.png
                # keep in mind d1, d2 are *signed* distances (=> d1 - d2)
                s = d1 / (d1 - d2)
                vdir = v2 - v1
                ipos = v1 + vdir * s
                intersections.append((INTERSECT_EDGE, ipos, e))

    return intersections


def get_next_triangle(mesh, T, plane, intersection, dist_tol):
    """
    Returns the next triangle to visit given the intersection and
    the list of unvisited triangles (T)

    We look for a triangle that is cut by the plane (2 intersections) as
    opposed to one that only touch the plane (1 vertex intersection)
    """
    if intersection[0] == INTERSECT_EDGE:
        tris = mesh.triangles_for_edge(intersection[2])
    elif intersection[0] == INTERSECT_VERTEX:
        tris = mesh.triangles_for_vert(intersection[2])
    else:
        assert False, 'Invalid intersection[0] value : %d' % intersection[0]

    # Knowing where we come from is not enough. If an edge of the triangle
    # lies exactly on the plane, i.e. :
    #
    #   /t1\
    # -v1---v2-
    #   \t2/
    #
    # With v1, v2 being the vertices and t1, t2 being the triangles, then
    # if you just try to go to the next connected triangle that intersect,
    # you can visit v1 -> t1 -> v2 -> t2 -> v1 .
    # Therefore, we need to limit the new candidates to the set of unvisited
    # triangles and once we've visited a triangle and decided on a next one,
    # remove all the neighbors of the visited triangle so we don't come
    # back to it

    T = set(T)
    for tid in tris:
        if tid in T:
            intersections = compute_triangle_plane_intersections(
                    mesh, tid, plane, dist_tol)
            if len(intersections) == 2:
                T = T.difference(tris)
                return tid, intersections, T
    return None, [], T


def _walk_polyline(tid, intersect, T, mesh, plane, dist_tol):
    """
    Given an intersection, walk through the mesh triangles, computing
    intersection with the cut plane for each visited triangle and adding
    those intersection to a polyline.
    """
    T = set(T)
    p = []
    # Loop until we have explored all the triangles for the current
    # polyline
    while True:
        p.append(intersect[1])

        tid, intersections, T = get_next_triangle(mesh, T, plane,
                                                  intersect, dist_tol)
        if tid is None:
            break

        # get_next_triangle returns triangles that our plane actually
        # intersects (as opposed to touching only a single vertex),
        # hence the assert
        assert len(intersections) == 2

        # Of the two returned intersections, one should have the
        # intersection point equal to p[-1]
        if la.norm(intersections[0][1] - p[-1]) < dist_tol:
            intersect = intersections[1]
        else:
            assert la.norm(intersections[1][1] - p[-1]) < dist_tol, \
                '%s not close to %s' % (str(p[-1]), str(intersections))
            intersect = intersections[0]

    return p, T


def cross_section_mesh(mesh, plane, dist_tol=1e-8):
    """
    Args:
        mesh: A geom.TriangleMesh instance
        plane: The cut plane : geom.Plane instance
        dist_tol: If two points are closer than dist_tol, they are considered
                  the same
    """
    # Set of all triangles
    T = set(range(len(mesh.tris)))
    # List of all cross-section polylines
    P = []

    while len(T) > 0:
        tid = T.pop()

        intersections = compute_triangle_plane_intersections(
                mesh, tid, plane, dist_tol)

        if len(intersections) == 2:
            for intersection in intersections:
                p, T = _walk_polyline(tid, intersection, T, mesh, plane,
                                      dist_tol)
                if len(p) > 1:
                    P.append(np.array(p))
    return P


def cross_section(verts, tris, plane_orig, plane_normal, **kwargs):
    """
    Compute the planar cross section of a mesh. This returns a set of
    polylines.

    Args:
        verts: Nx3 array of the vertices position
        faces: Nx3 array of the faces, containing vertex indices
        plane_orig: 3-vector indicating the plane origin
        plane_normal: 3-vector indicating the plane normal

    Returns:
        A list of Nx3 arrays, each representing a disconnected portion
        of the cross section as a polyline
    """
    mesh = TriangleMesh(verts, tris)
    plane = Plane(plane_orig, plane_normal)
    return cross_section_mesh(mesh, plane, **kwargs)


def pdist_squareformed_numpy(a):
    """
    Compute spatial distance using pure numpy
    (similar to scipy.spatial.distance.cdist())

    Thanks to Divakar Roy (@droyed) at stackoverflow.com

    Note this needs at least np.float64 precision!

    Returns: dist
    """
    a = np.array(a, dtype=np.float64)
    a_sumrows = np.einsum('ij,ij->i', a, a)
    dist = a_sumrows[:, None] + a_sumrows - 2 * np.dot(a, a.T)
    np.fill_diagonal(dist, 0)
    return dist


def merge_close_vertices(verts, faces, close_epsilon=1e-5):
    """
    Will merge vertices that are closer than close_epsilon.

    Warning, this has a O(n^2) memory usage because we compute the full
    vert-to-vert distance matrix. If you have a large mesh, might want
    to use some kind of spatial search structure like an octree or some fancy
    hashing scheme

    Returns: new_verts, new_faces
    """
    # Pairwise distance between verts
    if USE_SCIPY:
        D = spdist.cdist(verts, verts)
    else:
        D = np.sqrt(np.abs(pdist_squareformed_numpy(verts)))

    # Compute a mapping from old to new : for each input vert, store the index
    # of the new vert it will be merged into
    old2new = np.zeros(D.shape[0], dtype=np.int)
    # A mask indicating if a vertex has already been merged into another
    merged_verts = np.zeros(D.shape[0], dtype=np.bool)
    new_verts = []
    for i in range(D.shape[0]):
        if merged_verts[i]:
            continue
        else:
            # The vertices that will be merged into this one
            merged = np.flatnonzero(D[i, :] < close_epsilon)
            old2new[merged] = len(new_verts)
            new_verts.append(verts[i])
            merged_verts[merged] = True

    new_verts = np.array(new_verts)

    # Recompute face indices to index in new_verts
    new_faces = np.zeros((len(faces), 3), dtype=np.int)
    for i, f in enumerate(faces):
        new_faces[i] = (old2new[f[0]], old2new[f[1]], old2new[f[2]])

    # again, plot with utils.trimesh3d(new_verts, new_faces)
    return new_verts, new_faces
