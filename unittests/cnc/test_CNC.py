import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

from CNC import CNC, MSG, UPDATE, WAIT


class TestCNCParseLine(unittest.TestCase):
    def test_strips_comments_and_splits_commands(self):
        self.assertEqual(
            CNC.parseLine("G0 X10 Y20 (rapid move)"),
            ["G0", "X10", "Y20"],
        )

    def test_semicolon_comment(self):
        self.assertEqual(CNC.parseLine("G1 X1 ; feed"), ["G1", "X1"])

    def test_empty_and_comment_only(self):
        self.assertIsNone(CNC.parseLine(""))
        self.assertIsNone(CNC.parseLine("(comment only)"))
        self.assertIsNone(CNC.parseLine("; comment"))
        self.assertIsNone(CNC.parseLine("%"))


class TestCNCCompileLine(unittest.TestCase):
    def test_plain_gcode(self):
        self.assertEqual(CNC.compileLine("G0 X10 Y20"), "G0X10Y20")

    def test_special_commands(self):
        self.assertEqual(CNC.compileLine("%wait"), (WAIT,))
        self.assertEqual(CNC.compileLine("%msg hello"), (MSG, "hello"))
        self.assertEqual(CNC.compileLine("%update dro"), (UPDATE, "dro"))

    def test_semicolon_sets_comment(self):
        CNC.comment = ""
        self.assertIsNone(CNC.compileLine("; tool change"))
        self.assertEqual(CNC.comment, "tool change")

    def test_expression_compiles(self):
        result = CNC.compileLine("G0 X[1+2]")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "G0X")
        self.assertEqual(eval(result[1]), 3)

    def test_assignment_compiles(self):
        code = CNC.compileLine("#100=1+2")
        self.assertIsNotNone(code)
        namespace = {"_100": 0}
        exec(code, {}, namespace)
        self.assertEqual(namespace["_100"], 3)


class TestCNCFmt(unittest.TestCase):
    def test_fmt_trims_zeros(self):
        self.assertEqual(CNC.fmt("X", 10.0), "X10")
        self.assertEqual(CNC.fmt("Y", 1.25, 2), "Y1.25")
