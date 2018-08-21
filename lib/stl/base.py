from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
#import enum
import math
import numpy
import logging
import collections

from python_utils import logger

from .utils import s

#: When removing empty areas, remove areas that are smaller than this
AREA_SIZE_THRESHOLD = 0
#: Vectors in a point
VECTORS = 3
#: Dimensions used in a vector
DIMENSIONS = 3


class Dimension():
    #: X index (for example, `mesh.v0[0][X]`)
    X = 0
    #: Y index (for example, `mesh.v0[0][Y]`)
    Y = 1
    #: Z index (for example, `mesh.v0[0][Z]`)
    Z = 2


# For backwards compatibility, leave the original references
X = Dimension.X
Y = Dimension.Y
Z = Dimension.Z


class RemoveDuplicates():
    '''
    Choose whether to remove no duplicates, leave only a single of the
    duplicates or remove all duplicates (leaving holes).
    '''
    NONE = 0
    SINGLE = 1
    ALL = 2

    @classmethod
    def map(cls, value):
        if value and value in cls:
            pass
        elif value:
            value = cls.SINGLE
        else:
            value = cls.NONE

        return value


def logged(class_):
    # For some reason the Logged baseclass is not properly initiated on Linux
    # systems while this works on OS X. Please let me know if you can tell me
    # what silly mistake I made here

    logger_name = logger.Logged._Logged__get_name(
        __name__,
        class_.__name__,
    )

    class_.logger = logging.getLogger(logger_name)

    for key in dir(logger.Logged):
        if not key.startswith('__'):
            setattr(class_, key, getattr(class_, key))

    return class_


@logged
class BaseMesh(logger.Logged, collections.Mapping):
    '''
    Mesh object with easy access to the vectors through v0, v1 and v2.
    The normals, areas, min, max and units are calculated automatically.

    :param numpy.array data: The data for this mesh
    :param bool calculate_normals: Whether to calculate the normals
    :param bool remove_empty_areas: Whether to remove triangles with 0 area
            (due to rounding errors for example)

    :ivar str name: Name of the solid, only exists in ASCII files
    :ivar numpy.array data: Data as :func:`BaseMesh.dtype`
    :ivar numpy.array points: All points (Nx9)
    :ivar numpy.array normals: Normals for this mesh, calculated automatically
        by default (Nx3)
    :ivar numpy.array vectors: Vectors in the mesh (Nx3x3)
    :ivar numpy.array attr: Attributes per vector (used by binary STL)
    :ivar numpy.array x: Points on the X axis by vertex (Nx3)
    :ivar numpy.array y: Points on the Y axis by vertex (Nx3)
    :ivar numpy.array z: Points on the Z axis by vertex (Nx3)
    :ivar numpy.array v0: Points in vector 0 (Nx3)
    :ivar numpy.array v1: Points in vector 1 (Nx3)
    :ivar numpy.array v2: Points in vector 2 (Nx3)

    >>> data = numpy.zeros(10, dtype=BaseMesh.dtype)
    >>> mesh = BaseMesh(data, remove_empty_areas=False)
    >>> # Increment vector 0 item 0
    >>> mesh.v0[0] += 1
    >>> mesh.v1[0] += 2

    >>> # Check item 0 (contains v0, v1 and v2)
    >>> assert numpy.array_equal(
    ...     mesh[0],
    ...     numpy.array([1., 1., 1., 2., 2., 2., 0., 0., 0.]))
    >>> assert numpy.array_equal(
    ... mesh.vectors[0],
    ... numpy.array([[1., 1., 1.],
    ...     [2., 2., 2.],
    ...     [0., 0., 0.]]))
    >>> assert numpy.array_equal(
    ...     mesh.v0[0],
    ...     numpy.array([1., 1., 1.]))
    >>> assert numpy.array_equal(
    ...     mesh.points[0],
    ...     numpy.array([1., 1., 1., 2., 2., 2., 0., 0., 0.]))
    >>> assert numpy.array_equal(
    ...     mesh.data[0],
    ...     numpy.array((
    ...             [0., 0., 0.],
    ...             [[1., 1., 1.], [2., 2., 2.], [0., 0., 0.]],
    ...             [0]),
    ...         dtype=BaseMesh.dtype))
    >>> assert numpy.array_equal(mesh.x[0], numpy.array([1., 2., 0.]))

    >>> mesh[0] = 3
    >>> assert numpy.array_equal(
    ...     mesh[0],
    ...     numpy.array([3., 3., 3., 3., 3., 3., 3., 3., 3.]))

    >>> len(mesh) == len(list(mesh))
    True
    >>> (mesh.min_ < mesh.max_).all()
    True
    >>> mesh.update_normals()
    >>> mesh.units.sum()
    0.0
    >>> mesh.v0[:] = mesh.v1[:] = mesh.v2[:] = 0
    >>> mesh.points.sum()
    0.0

    >>> mesh.v0 = mesh.v1 = mesh.v2 = 0
    >>> mesh.x = mesh.y = mesh.z = 0

    >>> mesh.attr = 1
    >>> (mesh.attr == 1).all()
    True

    >>> mesh.normals = 2
    >>> (mesh.normals == 2).all()
    True

    >>> mesh.vectors = 3
    >>> (mesh.vectors == 3).all()
    True

    >>> mesh.points = 4
    >>> (mesh.points == 4).all()
    True
    '''
    #: - normals: :func:`numpy.float32`, `(3, )`
    #: - vectors: :func:`numpy.float32`, `(3, 3)`
    #: - attr: :func:`numpy.uint16`, `(1, )`
    dtype = numpy.dtype([
        (s('normals'), numpy.float32, (3, )),
        (s('vectors'), numpy.float32, (3, 3)),
        (s('attr'), numpy.uint16, (1, )),
    ])
    dtype = dtype.newbyteorder('<')  # Even on big endian arches, use little e.

    def __init__(self, data, calculate_normals=True,
                 remove_empty_areas=False,
                 remove_duplicate_polygons=RemoveDuplicates.NONE,
                 name='', speedups=True, **kwargs):
        super(BaseMesh, self).__init__(**kwargs)
        self.speedups = speedups
        if remove_empty_areas:
            data = self.remove_empty_areas(data)

        if RemoveDuplicates.map(remove_duplicate_polygons):
            data = self.remove_duplicate_polygons(data,
                                                  remove_duplicate_polygons)

        self.name = name
        self.data = data

        if calculate_normals:
            self.update_normals()

    @property
    def attr(self):
        return self.data['attr']

    @attr.setter
    def attr(self, value):
        self.data['attr'] = value

    @property
    def normals(self):
        return self.data['normals']

    @normals.setter
    def normals(self, value):
        self.data['normals'] = value

    @property
    def vectors(self):
        return self.data['vectors']

    @vectors.setter
    def vectors(self, value):
        self.data['vectors'] = value

    @property
    def points(self):
        return self.vectors.reshape(self.data.size, 9)

    @points.setter
    def points(self, value):
        self.points[:] = value

    @property
    def v0(self):
        return self.vectors[:, 0]

    @v0.setter
    def v0(self, value):
        self.vectors[:, 0] = value

    @property
    def v1(self):
        return self.vectors[:, 1]

    @v1.setter
    def v1(self, value):
        self.vectors[:, 1] = value

    @property
    def v2(self):
        return self.vectors[:, 2]

    @v2.setter
    def v2(self, value):
        self.vectors[:, 2] = value

    @property
    def x(self):
        return self.points[:, Dimension.X::3]

    @x.setter
    def x(self, value):
        self.points[:, Dimension.X::3] = value

    @property
    def y(self):
        return self.points[:, Dimension.Y::3]

    @y.setter
    def y(self, value):
        self.points[:, Dimension.Y::3] = value

    @property
    def z(self):
        return self.points[:, Dimension.Z::3]

    @z.setter
    def z(self, value):
        self.points[:, Dimension.Z::3] = value

    @classmethod
    def remove_duplicate_polygons(cls, data, value=RemoveDuplicates.SINGLE):
        value = RemoveDuplicates.map(value)
        polygons = data['vectors'].sum(axis=1)
        # Get a sorted list of indices
        idx = numpy.lexsort(polygons.T)
        # Get the indices of all different indices
        diff = numpy.any(polygons[idx[1:]] != polygons[idx[:-1]], axis=1)

        if value is RemoveDuplicates.SINGLE:
            # Only return the unique data, the True is so we always get at
            # least the originals
            return data[numpy.sort(idx[numpy.concatenate(([True], diff))])]
        elif value is RemoveDuplicates.ALL:
            # We need to return both items of the shifted diff
            diff_a = numpy.concatenate(([True], diff))
            diff_b = numpy.concatenate((diff, [True]))
            diff = numpy.concatenate((diff, [False]))

            # Combine both unique lists
            filtered_data = data[numpy.sort(idx[diff_a & diff_b])]
            if len(filtered_data) <= len(data) / 2:
                return data[numpy.sort(idx[diff_a])]
            else:
                return data[numpy.sort(idx[diff])]
        else:
            return data

    @classmethod
    def remove_empty_areas(cls, data):
        vectors = data['vectors']
        v0 = vectors[:, 0]
        v1 = vectors[:, 1]
        v2 = vectors[:, 2]
        normals = numpy.cross(v1 - v0, v2 - v0)
        squared_areas = (normals ** 2).sum(axis=1)
        return data[squared_areas > AREA_SIZE_THRESHOLD ** 2]

    def update_normals(self):
        '''Update the normals for all points'''
        self.normals[:] = numpy.cross(self.v1 - self.v0, self.v2 - self.v0)

    def update_min(self):
        self._min = self.vectors.min(axis=(0, 1))

    def update_max(self):
        self._max = self.vectors.max(axis=(0, 1))

    def update_areas(self):
        areas = .5 * numpy.sqrt((self.normals ** 2).sum(axis=1))
        self.areas = areas.reshape((areas.size, 1))

    def check(self):
        if (self.normals.sum(axis=0) >= 1e-4).any():
            self.warning('''
            Your mesh is not closed, the mass methods will not function
            correctly on this mesh.  For more info:
            https://github.com/WoLpH/numpy-stl/issues/69
            '''.strip())
            return False
        else:
            return True

    def get_mass_properties(self):
        '''
        Evaluate and return a tuple with the following elements:
          - the volume
          - the position of the center of gravity (COG)
          - the inertia matrix expressed at the COG

        Documentation can be found here:
        http://www.geometrictools.com/Documentation/PolyhedralMassProperties.pdf
        '''
        self.check()

        def subexpression(x):
            w0, w1, w2 = x[:, 0], x[:, 1], x[:, 2]
            temp0 = w0 + w1
            f1 = temp0 + w2
            temp1 = w0 * w0
            temp2 = temp1 + w1 * temp0
            f2 = temp2 + w2 * f1
            f3 = w0 * temp1 + w1 * temp2 + w2 * f2
            g0 = f2 + w0 * (f1 + w0)
            g1 = f2 + w1 * (f1 + w1)
            g2 = f2 + w2 * (f1 + w2)
            return f1, f2, f3, g0, g1, g2

        x0, x1, x2 = self.x[:, 0], self.x[:, 1], self.x[:, 2]
        y0, y1, y2 = self.y[:, 0], self.y[:, 1], self.y[:, 2]
        z0, z1, z2 = self.z[:, 0], self.z[:, 1], self.z[:, 2]
        a1, b1, c1 = x1 - x0, y1 - y0, z1 - z0
        a2, b2, c2 = x2 - x0, y2 - y0, z2 - z0
        d0, d1, d2 = b1 * c2 - b2 * c1, a2 * c1 - a1 * c2, a1 * b2 - a2 * b1

        f1x, f2x, f3x, g0x, g1x, g2x = subexpression(self.x)
        f1y, f2y, f3y, g0y, g1y, g2y = subexpression(self.y)
        f1z, f2z, f3z, g0z, g1z, g2z = subexpression(self.z)

        intg = numpy.zeros((10))
        intg[0] = sum(d0 * f1x)
        intg[1:4] = sum(d0 * f2x), sum(d1 * f2y), sum(d2 * f2z)
        intg[4:7] = sum(d0 * f3x), sum(d1 * f3y), sum(d2 * f3z)
        intg[7] = sum(d0 * (y0 * g0x + y1 * g1x + y2 * g2x))
        intg[8] = sum(d1 * (z0 * g0y + z1 * g1y + z2 * g2y))
        intg[9] = sum(d2 * (x0 * g0z + x1 * g1z + x2 * g2z))
        intg /= numpy.array([6, 24, 24, 24, 60, 60, 60, 120, 120, 120])
        volume = intg[0]
        cog = intg[1:4] / volume
        cogsq = cog ** 2
        inertia = numpy.zeros((3, 3))
        inertia[0, 0] = intg[5] + intg[6] - volume * (cogsq[1] + cogsq[2])
        inertia[1, 1] = intg[4] + intg[6] - volume * (cogsq[2] + cogsq[0])
        inertia[2, 2] = intg[4] + intg[5] - volume * (cogsq[0] + cogsq[1])
        inertia[0, 1] = inertia[1, 0] = -(intg[7] - volume * cog[0] * cog[1])
        inertia[1, 2] = inertia[2, 1] = -(intg[8] - volume * cog[1] * cog[2])
        inertia[0, 2] = inertia[2, 0] = -(intg[9] - volume * cog[2] * cog[0])
        return volume, cog, inertia

    def update_units(self):
        units = self.normals.copy()
        non_zero_areas = self.areas > 0
        areas = self.areas

        if non_zero_areas.shape[0] != areas.shape[0]:  # pragma: no cover
            self.warning('Zero sized areas found, '
                         'units calculation will be partially incorrect')

        if non_zero_areas.any():
            non_zero_areas.shape = non_zero_areas.shape[0]
            areas = numpy.hstack((2 * areas[non_zero_areas],) * DIMENSIONS)
            units[non_zero_areas] /= areas

        self.units = units

    @classmethod
    def rotation_matrix(cls, axis, theta):
        '''
        Generate a rotation matrix to Rotate the matrix over the given axis by
        the given theta (angle)

        Uses the `Euler-Rodrigues
        <https://en.wikipedia.org/wiki/Euler%E2%80%93Rodrigues_formula>`_
        formula for fast rotations.

        :param numpy.array axis: Axis to rotate over (x, y, z)
        :param float theta: Rotation angle in radians, use `math.radians` to
                     convert degrees to radians if needed.
        '''
        axis = numpy.asarray(axis)
        # No need to rotate if there is no actual rotation
        if not axis.any():
            return numpy.zeros((3, 3))

        theta = 0.5 * numpy.asarray(theta)

        axis = axis / numpy.linalg.norm(axis)

        a = math.cos(theta)
        b, c, d = - axis * math.sin(theta)
        angles = a, b, c, d
        powers = [x * y for x in angles for y in angles]
        aa, ab, ac, ad = powers[0:4]
        ba, bb, bc, bd = powers[4:8]
        ca, cb, cc, cd = powers[8:12]
        da, db, dc, dd = powers[12:16]

        return numpy.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                            [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                            [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

    def rotate(self, axis, theta=0, point=None):
        '''
        Rotate the matrix over the given axis by the given theta (angle)

        Uses the :py:func:`rotation_matrix` in the background.

        .. note:: Note that the `point` was accidentaly inverted with the
           old version of the code. To get the old and incorrect behaviour
           simply pass `-point` instead of `point` or `-numpy.array(point)` if
           you're passing along an array.

        :param numpy.array axis: Axis to rotate over (x, y, z)
        :param float theta: Rotation angle in radians, use `math.radians` to
                            convert degrees to radians if needed.
        :param numpy.array point: Rotation point so manual translation is not
                                  required
        '''
        # No need to rotate if there is no actual rotation
        if not theta:
            return

        self.rotate_using_matrix(self.rotation_matrix(axis, theta), point)

    def rotate_using_matrix(self, rotation_matrix, point=None):
        # No need to rotate if there is no actual rotation
        if not rotation_matrix.any():
            return

        if isinstance(point, (numpy.ndarray, list, tuple)) and len(point) == 3:
            point = numpy.asarray(point)
        elif point is None:
            point = numpy.array([0, 0, 0])
        elif isinstance(point, (int, float)):
            point = numpy.asarray([point] * 3)
        else:
            raise TypeError('Incorrect type for point', point)

        def _rotate(matrix):
            if point.any():
                # Translate while rotating
                return (matrix - point).dot(rotation_matrix) + point
            else:
                # Simply apply the rotation
                return matrix.dot(rotation_matrix)

        for i in range(3):
            self.vectors[:, i] = _rotate(self.vectors[:, i])

    def translate(self, translation):
        '''
        Translate the mesh in the three directions

        :param numpy.array translation: Translation vector (x, y, z)
        '''
        assert len(translation) == 3, "Translation vector must be of length 3"
        self.x += translation[0]
        self.y += translation[1]
        self.z += translation[2]

    def transform(self, matrix):
        '''
        Transform the mesh with a rotation and a translation stored in a
        single 4x4 matrix

        :param numpy.array matrix: Transform matrix with shape (4, 4), where
                                   matrix[0:3, 0:3] represents the rotation
                                   part of the transformation
                                   matrix[0:3, 3] represents the translation
                                   part of the transformation
        '''
        is_a_4x4_matrix = matrix.shape == (4, 4)
        assert is_a_4x4_matrix, "Transformation matrix must be of shape (4, 4)"
        rotation = matrix[0:3, 0:3]
        unit_det_rotation = numpy.allclose(numpy.linalg.det(rotation), 1.0)
        assert unit_det_rotation, "Rotation matrix has not a unit determinant"
        for i in range(3):
            self.vectors[:, i] = numpy.dot(rotation, self.vectors[:, i].T).T
        self.x += matrix[0, 3]
        self.y += matrix[1, 3]
        self.z += matrix[2, 3]

    def _get_or_update(key):
        def _get(self):
            if not hasattr(self, '_%s' % key):
                getattr(self, 'update_%s' % key)()
            return getattr(self, '_%s' % key)

        return _get

    def _set(key):
        def _set(self, value):
            setattr(self, '_%s' % key, value)

        return _set

    min_ = property(_get_or_update('min'), _set('min'),
                    doc='Mesh minimum value')
    max_ = property(_get_or_update('max'), _set('max'),
                    doc='Mesh maximum value')
    areas = property(_get_or_update('areas'), _set('areas'),
                     doc='Mesh areas')
    units = property(_get_or_update('units'), _set('units'),
                     doc='Mesh unit vectors')

    def __getitem__(self, k):
        return self.points[k]

    def __setitem__(self, k, v):
        self.points[k] = v

    def __len__(self):
        return self.points.shape[0]

    def __iter__(self):
        for point in self.points:
            yield point


