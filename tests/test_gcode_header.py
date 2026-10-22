"""Inferred Header keeps initial spindle startup when a cut block is disabled."""

import os
import shutil
import tempfile
import unittest

from GCode import GCode


class TestGCodeHeader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def load_lines(self, gcode, lines, name="in.nc"):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        self.assertTrue(gcode.load(path))
        return gcode

    def assertBlocks(self, lines, blocks):
        gcode = self.load_lines(GCode(), lines)
        self.assertEqual([list(block) for block in gcode.blocks], blocks)
        self.assertEqual(list(gcode.lines()), lines)
        self.assertFalse(any(len(block) == 0 for block in gcode.blocks))
        return gcode


class TestStartupPrefix(TestGCodeHeader):
    def test_flatcam_disabling_first_cut_keeps_startup(self):
        lines = [
            "G21",
            "G90",
            "G0 Z3",
            "M03 S500",
            "G4 P1",
            "G0 X1 Y1",
            "G1 Z-0.1 F100",
            "G1 X2",
            "G0 Z3",
            "G0 X4 Y4",
            "G1 Z-0.2 F100",
            "G1 X5",
        ]
        gcode = self.assertBlocks(lines, [
            ["G21", "G90", "G0 Z3", "M03 S500", "G4 P1"],
            ["G0 X1 Y1", "G1 Z-0.1 F100", "G1 X2", "G0 Z3"],
            ["G0 X4 Y4", "G1 Z-0.2 F100", "G1 X5"],
        ])
        self.assertEqual(gcode.blocks[0].name(), "Header")
        gcode.blocks[1].enable = False

        out = os.path.join(self.tmp, "out.txt")
        self.assertTrue(gcode.saveTXT(out))
        with open(out) as fh:
            saved = fh.read().splitlines()
        self.assertEqual(saved, [
            "G21",
            "G90",
            "G0 Z3",
            "M03 S500",
            "G4 P1",
            "G0 X4 Y4",
            "G1 Z-0.2 F100",
            "G1 X5",
        ])

    def test_prefix_shapes_keep_order(self):
        cases = {
            "startup before any rapid": (
                [
                    "G21",
                    "M03 S500",
                    "G4 P1",
                    "G0 X1 Y1",
                    "G1 Z-0.1 F100",
                    "G1 X2",
                    "G0 Z3",
                ],
                [
                    ["G21", "M03 S500", "G4 P1"],
                    ["G0 X1 Y1", "G1 Z-0.1 F100", "G1 X2", "G0 Z3"],
                ],
            ),
            "startup after an XY rapid": (
                [
                    "G21",
                    "G0 X1 Y1",
                    "M03 S500",
                    "(dwell)",
                    "G4 P1",
                    "G1 Z-0.1 F100",
                    "G0 Z3",
                    "G0 X2 Y2",
                    "G1 Z-0.1",
                ],
                [
                    ["G21", "G0 X1 Y1", "M03 S500", "(dwell)", "G4 P1"],
                    ["G1 Z-0.1 F100", "G0 Z3"],
                    ["G0 X2 Y2", "G1 Z-0.1"],
                ],
            ),
            "several preliminary upward rapids": (
                [
                    "G0 Z1",
                    "G0 Z2",
                    "G0 Z3",
                    "M03 S500",
                    "G4 P1",
                    "G0 X1",
                    "G1 Z-1 F10",
                ],
                [
                    ["G0 Z1", "G0 Z2", "G0 Z3", "M03 S500", "G4 P1"],
                    ["G0 X1", "G1 Z-1 F10"],
                ],
            ),
            "lowercase padded commands and inline comment": (
                [
                    "g21",
                    "g00 z3",
                    "m03 s500 (spindle)",
                    "(warmup)",
                    "g04 p1",
                    "g00 x1 y1",
                    "g01 z-0.1 f100",
                ],
                [
                    [
                        "g21",
                        "g00 z3",
                        "m03 s500 (spindle)",
                        "(warmup)",
                        "g04 p1",
                    ],
                    ["g00 x1 y1", "g01 z-0.1 f100"],
                ],
            ),
            "packed spindle word": (
                ["G0 Z3", "M03S500", "G04 P1", "G0 X1 Y1", "G1 Z-1 F20"],
                [
                    ["G0 Z3", "M03S500", "G04 P1"],
                    ["G0 X1 Y1", "G1 Z-1 F20"],
                ],
            ),
            "separate S before spindle on": (
                ["G0 Z3", "S500", "M3", "G4 P1", "G0 X1", "G1 X2 F100"],
                [
                    ["G0 Z3", "S500", "M3", "G4 P1"],
                    ["G0 X1", "G1 X2 F100"],
                ],
            ),
            "separate S after spindle on": (
                ["M3", "S500", "G4 P1", "G0 X1", "G1 X2 F50"],
                [
                    ["M3", "S500", "G4 P1"],
                    ["G0 X1", "G1 X2 F50"],
                ],
            ),
            "M4 startup": (
                [
                    "g0 z3",
                    "m04 s250",
                    "g4 p1",
                    "g0 x2 y2",
                    "g1 z-0.2 f80",
                    "g0 z3",
                    "m03 s100",
                    "g1 x3",
                ],
                [
                    ["g0 z3", "m04 s250", "g4 p1"],
                    ["g0 x2 y2", "g1 z-0.2 f80", "g0 z3"],
                    ["m03 s100", "g1 x3"],
                ],
            ),
        }
        for name, (lines, blocks) in cases.items():
            with self.subTest(name=name):
                self.assertBlocks(lines, blocks)

    def test_startup_without_cut_has_no_empty_block(self):
        cases = {
            "startup only": (
                ["G21", "M03 S500", "G4 P1"],
                [["G21", "M03 S500", "G4 P1"]],
            ),
            "upward rapid then startup": (
                ["G0 Z3", "M03 S500", "G4 P1"],
                [["G0 Z3", "M03 S500", "G4 P1"]],
            ),
            "startup then upward rapid": (
                ["M03 S500", "G4 P1", "G0 Z3"],
                [["M03 S500", "G4 P1", "G0 Z3"]],
            ),
            "non-motion under modal G0": (
                [
                    "G0 Z3",
                    "M03 S500",
                    "F100",
                    "S500",
                    "M8",
                    "(note)",
                    "",
                    "T2",
                    "G4 P1",
                ],
                [[
                    "G0 Z3",
                    "M03 S500",
                    "F100",
                    "S500",
                    "M8",
                    "(note)",
                    "",
                    "T2",
                    "G4 P1",
                ]],
            ),
        }
        for name, (lines, blocks) in cases.items():
            with self.subTest(name=name):
                gcode = self.assertBlocks(lines, blocks)
                self.assertEqual(len(gcode.blocks), 1)

    def test_without_startup_keeps_inferred_boundaries(self):
        cases = {
            "upward then cuts": (
                [
                    "G21",
                    "G90",
                    "G0 Z3",
                    "G0 X1 Y1",
                    "G1 Z-0.1 F100",
                    "G1 X2",
                    "G0 Z3",
                    "G0 X5 Y5",
                    "G1 Z-0.1",
                    "G1 X6",
                ],
                [
                    ["G21", "G90", "G0 Z3"],
                    ["G0 X1 Y1", "G1 Z-0.1 F100", "G1 X2", "G0 Z3"],
                    ["G0 X5 Y5", "G1 Z-0.1", "G1 X6"],
                ],
            ),
            "several upward rapids": (
                ["G0 Z1", "G0 Z2", "G0 Z3"],
                [["G0 Z1"], ["G0 Z2"], ["G0 Z3"]],
            ),
            "XY rapid first": (
                ["G21", "G0 X1 Y1", "G1 Z-0.1 F100", "G1 X2", "G0 Z3"],
                [
                    ["G21"],
                    ["G0 X1 Y1", "G1 Z-0.1 F100", "G1 X2", "G0 Z3"],
                ],
            ),
            "cutting with no rapid": (
                ["G21", "G1 X1 F100", "G1 X2", "X3"],
                [["G21", "G1 X1 F100", "G1 X2", "X3"]],
            ),
            "upward rapid only": (
                ["G0 Z3"],
                [["G0 Z3"]],
            ),
            "combined cut stays out of header": (
                ["G0 Z3", "G1 X1 F100 M03 S500", "X2"],
                [["G0 Z3"], ["G1 X1 F100 M03 S500", "X2"]],
            ),
            "combined cut with no rapid stays put": (
                ["G1 X1 F100 M03 S500", "X2"],
                [["G1 X1 F100 M03 S500", "X2"]],
            ),
        }
        for name, (lines, blocks) in cases.items():
            with self.subTest(name=name):
                self.assertBlocks(lines, blocks)


class TestStartupNotHoistedAfterCut(TestGCodeHeader):
    def test_linear_modal_and_combined_lines(self):
        lines = [
            "G21",
            "G90",
            "G0 Z3",
            "M03 S500",
            "G4 P1",
            "G0 X1 Y1",
            "G1 Z-0.1 F100",
            "X2",
            "X3 M03 S800",
            "G4 P2",
            "G0 Z3",
            "M04 S100",
            "G4 P3",
            "G1 X4",
        ]
        self.assertBlocks(lines, [
            ["G21", "G90", "G0 Z3", "M03 S500", "G4 P1"],
            [
                "G0 X1 Y1",
                "G1 Z-0.1 F100",
                "X2",
                "X3 M03 S800",
                "G4 P2",
                "G0 Z3",
            ],
            ["M04 S100", "G4 P3", "G1 X4"],
        ])

    def test_dwell_then_combined_cut_is_not_header(self):
        self.assertBlocks(
            ["G0 Z3", "G4 P1", "G1 X1 M03 S500"],
            [["G0 Z3", "G4 P1"], ["G1 X1 M03 S500"]],
        )

    def test_arc_then_later_spindle_stays_in_block(self):
        for arc, later in (("G2", "G3"), ("G3", "G2")):
            with self.subTest(arc=arc):
                lines = [
                    "G21",
                    "G0 Z3",
                    "M03 S500",
                    "G4 P1",
                    "G0 X0 Y0",
                    f"{arc} X2 Y0 I1 J0 F100",
                    "G4 P4",
                    "G0 Z6",
                    "M3 S100",
                    f"{later} X4 Y0 I1 J0",
                ]
                self.assertBlocks(lines, [
                    ["G21", "G0 Z3", "M03 S500", "G4 P1"],
                    [
                        "G0 X0 Y0",
                        f"{arc} X2 Y0 I1 J0 F100",
                        "G4 P4",
                        "G0 Z6",
                    ],
                    ["M3 S100", f"{later} X4 Y0 I1 J0"],
                ])

    def test_canned_cycles_end_precut(self):
        for cycle in ("G81", "G82", "G83", "G85", "G86", "G89"):
            with self.subTest(cycle=cycle):
                lines = [
                    "G21",
                    "G0 Z5",
                    "M03 S1000",
                    "G4 P1",
                    f"{cycle} X1 Y1 Z-1 R1 F80",
                    "X2 Y2",
                    "G0 Z8",
                    "G4 P2",
                    f"{cycle} X3 Y3 Z-1 R1 F80",
                ]
                self.assertBlocks(lines, [
                    ["G21", "G0 Z5", "M03 S1000", "G4 P1"],
                    [
                        f"{cycle} X1 Y1 Z-1 R1 F80",
                        "X2 Y2",
                        "G0 Z8",
                    ],
                    ["G4 P2", f"{cycle} X3 Y3 Z-1 R1 F80"],
                ])

    def test_incremental_motion(self):
        lines = [
            "G91",
            "G0 Z1",
            "G0 Z1",
            "M04 S300",
            "G4 P1",
            "G1 X1 F100",
            "G1 X1",
            "G0 Z1",
            "G1 X1",
        ]
        self.assertBlocks(lines, [
            ["G91", "G0 Z1", "G0 Z1", "M04 S300", "G4 P1"],
            ["G1 X1 F100", "G1 X1", "G0 Z1"],
            ["G1 X1"],
        ])

    def test_repeated_loads_do_not_keep_phase(self):
        gcode = GCode()
        absolute = [
            "G21",
            "G90",
            "G0 Z3",
            "M03 S500",
            "G4 P1",
            "G0 X1 Y1",
            "G1 Z-0.1 F100",
            "G0 Z3",
            "G0 X4 Y4",
            "G1 Z-0.2",
        ]
        incremental = [
            "G91",
            "G0 Z1",
            "G0 Z1",
            "M04 S300",
            "G4 P1",
            "G1 X1 F100",
            "G1 X1",
            "G0 Z1",
            "G1 X1",
        ]
        no_startup = ["G21", "G1 X1 F100", "G1 X2", "X3"]
        startup_only = ["M03 S500", "G4 P1"]

        self.load_lines(gcode, absolute, "absolute.nc")
        loaded = self.load_lines(gcode, incremental, "incremental.nc")
        fresh = self.load_lines(GCode(), incremental, "incremental-fresh.nc")
        self.assertEqual(
            [list(block) for block in loaded.blocks],
            [list(block) for block in fresh.blocks],
        )

        self.load_lines(gcode, startup_only, "startup.nc")
        loaded = self.load_lines(gcode, no_startup, "plain.nc")
        fresh = self.load_lines(GCode(), no_startup, "plain-fresh.nc")
        self.assertEqual(list(loaded.lines()), no_startup)
        self.assertEqual(
            [list(block) for block in loaded.blocks],
            [list(block) for block in fresh.blocks],
        )
        self.assertEqual(len(loaded.blocks), 1)


class TestExplicitBlocks(TestGCodeHeader):
    def test_named_blocks_keep_local_spindle_across_save(self):
        lines = [
            "(Block-name: Header)",
            "(Block-expand: 0)",
            "(Block-enable: 1)",
            "G21",
            "G90",
            "G0 Z3",
            "(Block-name: Pocket)",
            "(Block-expand: 0)",
            "(Block-enable: 1)",
            "M03 S500",
            "G4 P1",
            "G0 X1 Y1",
            "G1 Z-0.1 F100",
            "(Block-name: Profile)",
            "(Block-expand: 1)",
            "(Block-enable: 0)",
            "M04 S250",
            "G1 X2 F100",
        ]
        gcode = self.load_lines(GCode(), lines)

        def snapshot(program):
            return [
                (block.name(), block.enable, block.expand, list(block))
                for block in program.blocks
            ]

        expected = [
            ("Header", True, False, ["G21", "G90", "G0 Z3"]),
            (
                "Pocket",
                True,
                False,
                ["M03 S500", "G4 P1", "G0 X1 Y1", "G1 Z-0.1 F100"],
            ),
            ("Profile", False, True, ["M04 S250", "G1 X2 F100"]),
        ]
        self.assertEqual(snapshot(gcode), expected)

        path = os.path.join(self.tmp, "saved.nc")
        self.assertTrue(gcode.save(path))
        again = GCode()
        self.assertTrue(again.load(path))
        self.assertEqual(snapshot(again), expected)
        self.load_lines(gcode, lines, "original.nc")
        self.assertTrue(gcode.save(path))
        self.assertTrue(again.load(path))
        self.assertEqual(snapshot(again), expected)


class TestLoadErrors(TestGCodeHeader):
    def test_empty_and_missing_file(self):
        gcode = GCode()
        missing = os.path.join(self.tmp, "missing.nc")
        self.assertFalse(gcode.load(missing))
        self.assertEqual(gcode.blocks, [])

        empty = os.path.join(self.tmp, "empty.nc")
        with open(empty, "w") as fh:
            fh.write("")
        self.assertTrue(gcode.load(empty))
        self.assertEqual(gcode.blocks, [])

        self.load_lines(gcode, ["G21", "M03 S500", "G4 P1"])
        self.assertEqual(len(gcode.blocks), 1)
        self.assertFalse(gcode.load(missing))
        self.assertEqual(gcode.blocks, [])


if __name__ == "__main__":
    unittest.main()
