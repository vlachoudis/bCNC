from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import io
import os
#import enum
import numpy
import struct
import logging
import datetime

from . import base
from . import __about__ as metadata
from .utils import b
from .utils import s

try:
    from . import _speedups
except ImportError:  # pragma: no cover
    _speedups = None


logger = logging.getLogger(__name__)


class Mode():
    #: Automatically detect whether the output is a TTY, if so, write ASCII
    #: otherwise write BINARY
    AUTOMATIC = 0
    #: Force writing ASCII
    ASCII = 1
    #: Force writing BINARY
    BINARY = 2


# For backwards compatibility, leave the original references
AUTOMATIC = Mode.AUTOMATIC
ASCII = Mode.ASCII
BINARY = Mode.BINARY


#: Amount of bytes to read while using buffered reading
BUFFER_SIZE = 4096
#: The amount of bytes in the header field
HEADER_SIZE = 80
#: The amount of bytes in the count field
COUNT_SIZE = 4
#: The maximum amount of triangles we can read from binary files
MAX_COUNT = 1e8


class BaseStl(base.BaseMesh):

    @classmethod
    def load(cls, fh, mode=AUTOMATIC, speedups=True):
        '''Load Mesh from STL file

        Automatically detects binary versus ascii STL files.

        :param file fh: The file handle to open
        :param int mode: Automatically detect the filetype or force binary
        '''
        header = fh.read(HEADER_SIZE).lower()
        if not header:
            return

        if isinstance(header, str):  # pragma: no branch
            header = b(header)

        name = ''

        if mode in (AUTOMATIC, ASCII) and header.startswith(b('solid')):
            try:
                name, data = cls._load_ascii(
                    fh, header, speedups=speedups)
            except RuntimeError as exception:
                # Disable fallbacks in ASCII mode
                if mode is ASCII:
                    raise

                (recoverable, e) = exception.args
                # If we didn't read beyond the header the stream is still
                # readable through the binary reader
                if recoverable:
                    name, data = cls._load_binary(fh, header, check_size=False)
                else:
                    # Apparently we've read beyond the header. Let's try
                    # seeking :)
                    # Note that this fails when reading from stdin, we can't
                    # recover from that.
                    fh.seek(HEADER_SIZE)

                    # Since we know this is a seekable file now and we're not
                    # 100% certain it's binary, check the size while reading
                    name, data = cls._load_binary(fh, header, check_size=True)
        else:
            name, data = cls._load_binary(fh, header)

        return name, data

    @classmethod
    def _load_binary(cls, fh, header, check_size=False):
        # Read the triangle count
        count_data = fh.read(COUNT_SIZE)
        if len(count_data) != COUNT_SIZE:
            count = 0
        else:
            count, = struct.unpack(s('<i'), b(count_data))
        # raise RuntimeError()
        assert count < MAX_COUNT, ('File too large, got %d triangles which '
                                   'exceeds the maximum of %d') % (
                                       count, MAX_COUNT)

        if check_size:
            try:
                # Check the size of the file
                fh.seek(0, os.SEEK_END)
                raw_size = fh.tell() - HEADER_SIZE - COUNT_SIZE
                expected_count = int(raw_size / cls.dtype.itemsize)
                assert expected_count == count, ('Expected %d vectors but '
                                                 'header indicates %d') % (
                                                     expected_count, count)
                fh.seek(HEADER_SIZE + COUNT_SIZE)
            except IOError:  # pragma: no cover
                pass

        name = header.strip()

        # Read the rest of the binary data
        return name, numpy.fromfile(fh, dtype=cls.dtype, count=count)

    @classmethod
    def _ascii_reader(cls, fh, header):
        if b'\n' in header:
            recoverable = [True]
        else:
            recoverable = [False]
            header += b(fh.read(BUFFER_SIZE))

        lines = b(header).split(b('\n'))

        def get(prefix=''):
            prefix = b(prefix)

            if lines:
                line = lines.pop(0)
            else:
                raise RuntimeError(recoverable[0], 'Unable to find more lines')
            if not lines:
                recoverable[0] = False

                # Read more lines and make sure we prepend any old data
                lines[:] = b(fh.read(BUFFER_SIZE)).split(b('\n'))
                line += lines.pop(0)

            line = line.lower().strip()
            if line == b(''):
                return get(prefix)

            if prefix:
                if line.startswith(prefix):
                    values = line.replace(prefix, b(''), 1).strip().split()
                elif line.startswith(b('endsolid')):
                    # go back to the beginning of new solid part
                    size_unprocessedlines = sum(len(l) + 1 for l in lines) - 1
                    if size_unprocessedlines > 0:
                        position = fh.tell()
                        fh.seek(position - size_unprocessedlines)
                    raise StopIteration()
                else:
                    raise RuntimeError(recoverable[0],
                                       '%r should start with %r' % (line,
                                                                    prefix))

                if len(values) == 3:
                    return [float(v) for v in values]
                else:  # pragma: no cover
                    raise RuntimeError(recoverable[0],
                                       'Incorrect value %r' % line)
            else:
                return b(line)

        line = get()
        if not line.startswith(b('solid ')) and line.startswith(b('solid')):
            cls.warning('ASCII STL files should start with solid <space>. '
                        'The application that produced this STL file may be '
                        'faulty, please report this error. The erroneous '
                        'line: %r', line)

        if not lines:
            raise RuntimeError(recoverable[0],
                               'No lines found, impossible to read')

        # Yield the name
        yield line[5:].strip()

        while True:
            # Read from the header lines first, until that point we can recover
            # and go to the binary option. After that we cannot due to
            # unseekable files such as sys.stdin
            #
            # Numpy doesn't support any non-file types so wrapping with a
            # buffer and/or StringIO does not work.
            try:
                normals = get('facet normal')
                assert get() == b('outer loop')
                v0 = get('vertex')
                v1 = get('vertex')
                v2 = get('vertex')
                assert get() == b('endloop')
                assert get() == b('endfacet')
                attrs = 0
                yield (normals, (v0, v1, v2), attrs)
            except AssertionError as e:  # pragma: no cover
                raise RuntimeError(recoverable[0], e)
            except StopIteration:
                return

    @classmethod
    def _load_ascii(cls, fh, header, speedups=True):
        # The speedups module is covered by travis but it can't be tested in
        # all environments, this makes coverage checks easier
        if _speedups and speedups:  # pragma: no cover
            return _speedups.ascii_read(fh, header)
        else:
            iterator = cls._ascii_reader(fh, header)
            name = next(iterator)
            return name, numpy.fromiter(iterator, dtype=cls.dtype)

    def save(self, filename, fh=None, mode=AUTOMATIC, update_normals=True):
        '''Save the STL to a (binary) file

        If mode is :py:data:`AUTOMATIC` an :py:data:`ASCII` file will be
        written if the output is a TTY and a :py:data:`BINARY` file otherwise.

        :param str filename: The file to load
        :param file fh: The file handle to open
        :param int mode: The mode to write, default is :py:data:`AUTOMATIC`.
        :param bool update_normals: Whether to update the normals
        '''
        assert filename, 'Filename is required for the STL headers'
        if update_normals:
            self.update_normals()

        if mode is AUTOMATIC:
            if fh and os.isatty(fh.fileno()):  # pragma: no cover
                write = self._write_ascii
            else:
                write = self._write_binary
        elif mode is BINARY:
            write = self._write_binary
        elif mode is ASCII:
            write = self._write_ascii
        else:
            raise ValueError('Mode %r is invalid' % mode)

        name = os.path.split(filename)[-1]
        try:
            if fh:
                write(fh, name)
            else:
                with open(filename, 'wb') as fh:
                    write(fh, filename)
        except IOError:  # pragma: no cover
            pass

    def _write_ascii(self, fh, name):
        if _speedups and self.speedups:  # pragma: no cover
            _speedups.ascii_write(fh, b(name), self.data)
        else:
            def p(s, file):
                file.write(b('%s\n' % s))

            p('solid %s' % name, file=fh)

            for row in self.data:
                vectors = row['vectors']
                p('facet normal %f %f %f' % tuple(row['normals']), file=fh)
                p('  outer loop', file=fh)
                p('    vertex %f %f %f' % tuple(vectors[0]), file=fh)
                p('    vertex %f %f %f' % tuple(vectors[1]), file=fh)
                p('    vertex %f %f %f' % tuple(vectors[2]), file=fh)
                p('  endloop', file=fh)
                p('endfacet', file=fh)

            p('endsolid %s' % name, file=fh)

    def _write_binary(self, fh, name):
        # Create the header
        header = '%s (%s) %s %s' % (
            metadata.__package_name__,
            metadata.__version__,
            datetime.datetime.now(),
            name,
        )

        # Make it exactly 80 characters
        header = header[:80].ljust(80, ' ')
        packed = struct.pack(s('<i'), self.data.size)

        if isinstance(fh, io.TextIOWrapper):  # pragma: no cover
            packed = str(packed)
        else:
            header = b(header)
            packed = b(packed)

        fh.write(header)
        fh.write(packed)
        self.data.tofile(fh)

        if self.data.size:  # pragma: no cover
            assert fh.tell() > 84, (
                'numpy silently refused to write our file. Note that writing '
                'to `StringIO` objects is not supported by `numpy`')

    @classmethod
    def from_file(cls, filename, calculate_normals=True, fh=None,
                  mode=Mode.AUTOMATIC, speedups=True, **kwargs):
        '''Load a mesh from a STL file

        :param str filename: The file to load
        :param bool calculate_normals: Whether to update the normals
        :param file fh: The file handle to open
        :param dict \**kwargs: The same as for :py:class:`stl.mesh.Mesh`

        '''
        if fh:
            name, data = cls.load(
                fh, mode=mode, speedups=speedups)
        else:
            try:
                with open(filename, 'rb') as fh:
                    name, data = cls.load(
                        fh, mode=mode, speedups=speedups)
            except AssertionError:  # pragma: no cover
                logger.warn('Unable to read the file with speedups, retrying')
                with open(filename, 'rb') as fh:
                    name, data = cls.load(
                        fh, mode=Mode.ASCII, speedups=False)

        return cls(data, calculate_normals, name=name,
                   speedups=speedups, **kwargs)

    @classmethod
    def from_multi_file(cls, filename, calculate_normals=True, fh=None,
                        mode=ASCII, speedups=True, **kwargs):
        '''Load multiple meshes from a STL file

        Note: mode is hardcoded to ascii since binary stl files do not support
        the multi format

        :param str filename: The file to load
        :param bool calculate_normals: Whether to update the normals
        :param file fh: The file handle to open
        :param dict \**kwargs: The same as for :py:class:`stl.mesh.Mesh`
        '''
        if fh:
            close = False
        else:
            fh = open(filename, 'rb')
            close = True

        try:
            raw_data = cls.load(fh, mode=mode, speedups=speedups)
            while raw_data:
                name, data = raw_data
                yield cls(data, calculate_normals, name=name,
                          speedups=speedups, **kwargs)
                raw_data = cls.load(fh, mode=ASCII,
                                    speedups=speedups)

        finally:
            if close:
                fh.close()


StlMesh = BaseStl.from_file
