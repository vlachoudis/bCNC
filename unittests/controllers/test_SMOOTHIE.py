import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

import SMOOTHIE
from CNC import CNC
from mocks import MockSender


class TestSMOOTHIE(unittest.TestCase):
    def setUp(self):
        self.sender = MockSender()
        self.controller = SMOOTHIE.Controller(self.sender)

    def test_status_parsing(self):
        status = (
            "<Idle|MPos:68.9980,-49.9240,40.0000,12.3456|"
            "WPos:68.9980,-49.9240,40.0000|F:12345.12|S:1.2>"
        )
        self.controller.parseBracketAngle(status, [])

        self.assertEqual(CNC.vars["state"], "Idle")
        self.assertEqual(CNC.vars["mx"], 68.9980)
        self.assertEqual(CNC.vars["my"], -49.9240)
        self.assertEqual(CNC.vars["mz"], 40.0000)
        self.assertEqual(CNC.vars["wx"], 68.9980)
        self.assertEqual(CNC.vars["wy"], -49.9240)
        self.assertEqual(CNC.vars["wz"], 40.0000)
        self.assertEqual(CNC.vars["wcox"], 0.0)
        self.assertEqual(CNC.vars["wcoy"], 0.0)
        self.assertEqual(CNC.vars["wcoz"], 0.0)
        self.assertEqual(CNC.vars["curfeed"], 12345.12)
        self.assertTrue(self.sender._posUpdate)

    def test_params_parsing(self):
        for line in (
            "[G54:10.000,-7.000,-9.000]",
            "[TLO:0.500]",
            "[PRB:3.000,4.000,-0.500:0]",
            "[G0 G54 G17 G21 G90 G94 M5 M9 T0 F0.0 S0]",
        ):
            self.assertTrue(self.controller.parseBracketSquare(line), line)

        self.assertEqual(CNC.vars["G54"], [10.0, -7.0, -9.0])
        self.assertEqual(CNC.vars["TLO"], "0.500")
        self.assertEqual(CNC.vars["prbx"], 3.0)
        self.assertEqual(CNC.vars["prby"], 4.0)
        self.assertEqual(CNC.vars["prbz"], -0.5)
        self.assertIn("G0", CNC.vars["G"])
        self.assertIn("G54", CNC.vars["G"])
