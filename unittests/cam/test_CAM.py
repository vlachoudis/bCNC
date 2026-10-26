"""Basic headless CAM tests for bcam + document apply_* (no Tk / serial)."""
import unittest

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

# Stub ToolsPage so plugin modules can be imported without Tk GUI
if "ToolsPage" not in sys.modules:
    _tp = types.ModuleType("ToolsPage")

    class _Plugin:
        def __init__(self, *a, **k):
            pass

    def _run_on_selection(app, apply_fn, *args, **kwargs):
        return apply_fn(app.gcode, app.editor.getSelectedBlocks(), *args, **kwargs)

    _tp.Plugin = _Plugin
    _tp.run_on_selection = _run_on_selection
    sys.modules["ToolsPage"] = _tp

from GCode import Block, GCode
from bmath import Vector
from bpath import Path, Segment
from camProfile import apply_profile
from cut import apply_cut
from drill import apply_drill
from pocket import apply_pocket


def rect_block(name="rect", width=20.0, height=10.0):
    block = Block(name)
    block.extend(
        [
            "G0 X0 Y0",
            f"G1 X{width:g} Y0",
            f"G1 X{width:g} Y{height:g}",
            f"G1 X0 Y{height:g}",
            "G1 X0 Y0",
        ]
    )
    return block


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


class TestPathOffset(unittest.TestCase):
    def test_offset_clean_insets_closed_square(self):
        path = square_path(10.0)
        self.assertTrue(path.isClosed())
        self.assertAlmostEqual(path.length(), 40.0)

        result = path.offsetClean(-1.0)
        self.assertEqual(len(result), 1)
        inset = result[0]
        self.assertTrue(inset.isClosed())
        # 8x8 square perimeter
        self.assertAlmostEqual(inset.length(), 32.0, places=5)


class TestGCodeCAM(unittest.TestCase):
    def setUp(self):
        self.gcode = GCode()
        self.gcode.blocks = [rect_block()]

    def test_profile_inside_offset(self):
        blocks = [0]
        apply_profile(self.gcode, blocks, offset=-1.5)

        self.assertEqual(blocks, [1])
        self.assertFalse(self.gcode.blocks[0].enable)
        self.assertTrue(self.gcode.blocks[1].enable)
        self.assertIn("in", self.gcode.blocks[1].name())

        paths = self.gcode.toPath(1)
        self.assertEqual(len(paths), 1)
        # 20x10 inset by 1.5 → 17x7 → perimeter 48
        self.assertAlmostEqual(paths[0].length(), 48.0, places=5)

    def test_pocket_generates_longer_toolpath(self):
        blocks = [0]
        apply_pocket(self.gcode, blocks, diameter=3.0, stepover=0.4)

        self.assertEqual(len(blocks), 1)
        pocket = self.gcode.blocks[blocks[0]]
        self.assertTrue(pocket.enable)
        self.assertTrue(pocket.operationTest("pocket"))

        paths = self.gcode.toPath(blocks[0])
        total = sum(p.length() for p in paths)
        # Nested offsets should exceed the original 60-unit outline
        self.assertGreater(total, 60.0)
        self.assertGreater(len(pocket), len(self.gcode.blocks[0]))

    def test_drill_center(self):
        err = apply_drill(self.gcode, [0], depth=-2.0, center=True)
        self.assertIsNone(err)

        block = self.gcode.blocks[0]
        self.assertIn("drill", block.name())
        lines = [line.lower() for line in block]
        self.assertTrue(any("x10" in line and "y5" in line for line in lines))
        self.assertTrue(any("z-2" in line for line in lines))
        self.assertTrue(any(line.startswith("g0 z") for line in lines))

    def test_cut_multiple_depth_passes(self):
        err = apply_cut(self.gcode, [0], depth=-2.0, stepz=1.0)
        self.assertIsNone(err)

        block = self.gcode.blocks[0]
        self.assertIn("cut:-2", block.name())
        text = "\n".join(block)
        self.assertIn("(pass -1.000000)", text)
        self.assertIn("(pass -2.000000)", text)
        self.assertGreaterEqual(text.lower().count("z-1"), 1)
        self.assertGreaterEqual(text.lower().count("z-2"), 1)


if __name__ == "__main__":
    unittest.main()
