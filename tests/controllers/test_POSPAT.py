"""POSPAT match cases adapted from https://github.com/vlachoudis/bCNC/pull/1452

Extra axes are non-capturing in the current regex; we assert name + XYZ and that
optional axes / probe-success suffixes still match.
"""
import unittest

import pathfix
from _GenericController import POSPAT


class TestPOSPAT(unittest.TestCase):
    CASES = [
        # input, expected (name, x, y, z)
        ("[PRB:-356.0,-5.28,-118.3]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0,5.0]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0,5.0,6.0]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3:0]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3:1]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3:12]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0:1]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0,5.0:2]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[PRB:-356.0,-5.28,-118.3,4.0,5.0,6.0:3]", ("PRB", "-356.0", "-5.28", "-118.3")),
        ("[G54:10.000,-7.000,-9.000]", ("G54", "10.000", "-7.000", "-9.000")),
        ("[PRB:3.000,4.000,-0.500:0]", ("PRB", "3.000", "4.000", "-0.500")),
    ]

    def test_pospat_matches_name_and_xyz(self):
        for line, expected in self.CASES:
            with self.subTest(line=line):
                got = POSPAT.match(line)
                self.assertIsNotNone(got, f"should match: {line}")
                self.assertEqual(got.groups()[:4], expected)
