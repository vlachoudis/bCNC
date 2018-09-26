import sys
import random
import argparse

from . import stl


def _get_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'),
                        default=sys.stdin, help='STL file to read')
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('wb'),
                        default=sys.stdout, help='STL file to write')
    parser.add_argument('--name', nargs='?', help='Name of the mesh')
    parser.add_argument(
        '-n', '--use-file-normals', action='store_true',
        help='Read the normals from the file instead of recalculating them')
    parser.add_argument(
        '-r', '--remove-empty-areas', action='store_true',
        help='Remove areas with 0 surface areas to prevent errors during '
        'normal calculation')
    parser.add_argument('-s', '--disable-speedups', action='store_true',
                        help='Disable Cython speedups')
    return parser


def _get_name(args):
    names = [
        args.name,
        getattr(args.outfile, 'name', None),
        getattr(args.infile, 'name', None),
        'numpy-stl-%06d' % random.randint(0, 1e6),
    ]

    for name in names:  # pragma: no branch
        if name and isinstance(name, str) and not name.startswith('<'):
            return name


def main():
    parser = _get_parser('Convert STL files from ascii to binary and back')
    parser.add_argument('-a', '--ascii', action='store_true',
                        help='Write ASCII file (default is binary)')
    parser.add_argument('-b', '--binary', action='store_true',
                        help='Force binary file (for TTYs)')

    args = parser.parse_args()
    name = _get_name(args)
    stl_file = stl.StlMesh(filename=name,
                           fh=args.infile,
                           calculate_normals=False,
                           remove_empty_areas=args.remove_empty_areas,
                           speedups=not args.disable_speedups)

    if args.binary:
        mode = stl.BINARY
    elif args.ascii:
        mode = stl.ASCII
    else:
        mode = stl.AUTOMATIC

    stl_file.save(name, args.outfile, mode=mode,
                  update_normals=not args.use_file_normals)


def to_ascii():
    parser = _get_parser('Convert STL files to ASCII (text) format')
    args = parser.parse_args()
    name = _get_name(args)
    stl_file = stl.StlMesh(filename=name, fh=args.infile,
                           calculate_normals=False,
                           remove_empty_areas=args.remove_empty_areas,
                           speedups=not args.disable_speedups)
    stl_file.save(name, args.outfile, mode=stl.ASCII,
                  update_normals=not args.use_file_normals)


def to_binary():
    parser = _get_parser('Convert STL files to ASCII (text) format')
    args = parser.parse_args()
    name = _get_name(args)
    stl_file = stl.StlMesh(filename=name, fh=args.infile,
                           calculate_normals=False,
                           remove_empty_areas=args.remove_empty_areas,
                           speedups=not args.disable_speedups)
    stl_file.save(name, args.outfile, mode=stl.BINARY,
                  update_normals=not args.use_file_normals)

