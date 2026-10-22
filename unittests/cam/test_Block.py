import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

from GCode import Block


class TestBlockOperations(unittest.TestCase):
    def test_operation_name_adds_bracket(self):
        self.assertEqual(
            Block.operationName("contour", "pocket"),
            "contour [pocket]",
        )

    def test_operation_name_appends(self):
        self.assertEqual(
            Block.operationName("contour [out]", "pocket"),
            "contour [out,pocket]",
        )

    def test_operation_name_increments_counter(self):
        self.assertEqual(
            Block.operationName("part [out:2]", "out"),
            "part [out:3]",
        )

    def test_operation_test_and_get(self):
        block = Block("part [pocket,out:2]")
        self.assertTrue(block.operationTest("pocket"))
        self.assertTrue(block.operationTest("out"))
        self.assertFalse(block.operationTest("in"))
        self.assertEqual(block.operationGet("out"), "2")
        self.assertIsNone(block.operationGet("in"))

    def test_operation_side(self):
        self.assertEqual(Block("x [pocket]").operationSide(), -1)
        self.assertEqual(Block("x [in]").operationSide(), -1)
        self.assertEqual(Block("x [out]").operationSide(), 1)
        self.assertEqual(Block("x [in,out]").operationSide(), 0)
        self.assertEqual(Block("plain").operationSide(), 0)
