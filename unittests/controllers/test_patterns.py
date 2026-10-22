"""Regex match cases for GRBLv0 / Smoothie patterns in _GenericController.

POSPAT cases adapted from https://github.com/vlachoudis/bCNC/pull/1452
"""
import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix
from _GenericController import (
    DOLLARPAT,
    POSPAT,
    STATUSPAT,
    TLOPAT,
    VARPAT,
)


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


class TestSTATUSPAT(unittest.TestCase):
    def test_three_axis_status(self):
        line = "<Idle,MPos:0.000,-1.333,2.001,WPos:-40.000,0.000,2.042>"
        got = STATUSPAT.match(line)
        self.assertIsNotNone(got)
        self.assertEqual(
            got.groups(),
            ("Idle", "0.000", "-1.333", "2.001", "-40.000", "0.000", "2.042"),
        )

    def test_status_with_optional_extra_axes(self):
        line = (
            "<Idle,MPos:0.000,-1.333,2.001,1.0,"
            "WPos:-40.000,0.000,2.042,3.0>"
        )
        got = STATUSPAT.match(line)
        self.assertIsNotNone(got)
        self.assertEqual(got.group(1), "Idle")
        self.assertEqual(got.group(2), "0.000")
        self.assertEqual(got.group(5), "-40.000")


class TestTLOPAT(unittest.TestCase):
    def test_tlo(self):
        got = TLOPAT.match("[TLO:1.234]")
        self.assertIsNotNone(got)
        self.assertEqual(got.groups(), ("TLO", "1.234"))


class TestVARPAT(unittest.TestCase):
    def test_setting_value(self):
        got = VARPAT.match("$110=500.000")
        self.assertIsNotNone(got)
        self.assertEqual(got.groups(), ("110", "500.000"))

    def test_setting_with_comment(self):
        got = VARPAT.match("$132=200.0 (z max travel)")
        self.assertIsNotNone(got)
        self.assertEqual(got.groups(), ("132", "200.0"))


class TestDOLLARPAT(unittest.TestCase):
    def test_parser_state(self):
        line = "[G0 G54 G17 G21 G90 G94 M5 M9 T0 F0.0 S0]"
        self.assertIsNotNone(DOLLARPAT.match(line))

    def test_non_g_code_rejected(self):
        self.assertIsNone(DOLLARPAT.match("[PRB:1.0,2.0,3.0]"))
