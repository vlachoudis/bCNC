"""Headless tests for portable bcam strategies (no Tk / serial)."""
import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

import bcam
from bmath import Vector
from bpath import Path, Segment


def square_path(size=10.0, name="sq"):
    path = Path(name)
    pts = [
        Vector(0.0, 0.0),
        Vector(size, 0.0),
        Vector(size, size),
        Vector(0.0, size),
        Vector(0.0, 0.0),
    ]
    for start, end in zip(pts, pts[1:]):
        path.append(Segment(Segment.LINE, start, end))
    return path


class TestBcamProfile(unittest.TestCase):
    def test_profile_paths_insets_square(self):
        path = square_path(10.0)
        path.directionSet(1)
        result = bcam.profile_paths(path, offset=-1.0, overcut=False, name="in")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].isClosed())
        self.assertAlmostEqual(result[0].length(), 32.0, places=5)


class TestBcamPocket(unittest.TestCase):
    def test_pocket_paths_longer_than_outline(self):
        path = square_path(20.0)
        result = bcam.pocket_paths(path, diameter=3.0, stepover=0.4)
        self.assertGreater(len(result), 0)
        total = sum(p.length() for p in result)
        self.assertGreater(total, 80.0)


if __name__ == "__main__":
    unittest.main()
