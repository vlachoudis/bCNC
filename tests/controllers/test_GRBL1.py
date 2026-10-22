import unittest

import pathfix

import GRBL1
from CNC import CNC
from mocks import MockSender


class TestGRBL1(unittest.TestCase):
    def setUp(self):
        self.sender = MockSender()
        self.controller = GRBL1.Controller(self.sender)
        # Typical work offset so wx = mx - wcox
        CNC.vars["wcox"] = 40.0
        CNC.vars["wcoy"] = -1.333
        CNC.vars["wcoz"] = -0.041
        CNC.vars["state"] = ""

    def test_status_parsing(self):
        status = (
            "<Idle|MPos:0.000,-1.333,2.001|WCO:40.000,-1.333,-0.041|"
            "FS:120.5,8000|Ov:100,100,100|Bf:15,128>"
        )
        self.controller.parseBracketAngle(status, [])

        self.assertEqual(CNC.vars["state"], "Idle")
        self.assertEqual(CNC.vars["mx"], 0.000)
        self.assertEqual(CNC.vars["my"], -1.333)
        self.assertEqual(CNC.vars["mz"], 2.001)
        self.assertEqual(CNC.vars["wcox"], 40.000)
        self.assertEqual(CNC.vars["wcoy"], -1.333)
        self.assertEqual(CNC.vars["wcoz"], -0.041)
        self.assertEqual(CNC.vars["wx"], round(0.000 - 40.000, CNC.digits))
        self.assertEqual(CNC.vars["wy"], round(-1.333 - (-1.333), CNC.digits))
        self.assertEqual(CNC.vars["wz"], round(2.001 - (-0.041), CNC.digits))
        self.assertEqual(CNC.vars["curfeed"], 120.5)
        self.assertEqual(CNC.vars["curspindle"], 8000.0)
        self.assertEqual(CNC.vars["OvFeed"], 100)
        self.assertEqual(CNC.vars["OvRapid"], 100)
        self.assertEqual(CNC.vars["OvSpindle"], 100)
        self.assertEqual(CNC.vars["planner"], 15)
        self.assertEqual(CNC.vars["rxbytes"], 128)
        self.assertTrue(self.sender._posUpdate)

    def test_status_hold_and_pins(self):
        status = "<Hold:1|MPos:1.000,2.000,3.000|Pn:XYZ>"
        self.controller.parseBracketAngle(status, [])

        self.assertEqual(CNC.vars["state"], "Hold:1")
        self.assertEqual(CNC.vars["mx"], 1.0)
        self.assertEqual(CNC.vars["my"], 2.0)
        self.assertEqual(CNC.vars["mz"], 3.0)
        self.assertEqual(CNC.vars["pins"], "XYZ")

    def test_params_parsing(self):
        params_lines = [
            "[G54:10.000,-7.000,-9.000]",
            "[G92:1.000,2.000,3.000]",
            "[G28:0.000,0.000,0.000]",
            "[G30:4.000,5.000,6.000]",
            "[TLO:1.234]",
            "[PRB:3.000,4.000,-0.500:0]",
            "[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]",
        ]
        for line in params_lines:
            self.assertTrue(self.controller.parseBracketSquare(line), line)

        self.assertEqual(CNC.vars["G54"], ["10.000", "-7.000", "-9.000"])
        self.assertEqual(CNC.vars["G92X"], 1.0)
        self.assertEqual(CNC.vars["G92Y"], 2.0)
        self.assertEqual(CNC.vars["G92Z"], 3.0)
        self.assertEqual(CNC.vars["G28X"], 0.0)
        self.assertEqual(CNC.vars["G28Y"], 0.0)
        self.assertEqual(CNC.vars["G28Z"], 0.0)
        self.assertEqual(CNC.vars["G30X"], 4.0)
        self.assertEqual(CNC.vars["G30Y"], 5.0)
        self.assertEqual(CNC.vars["G30Z"], 6.0)
        self.assertEqual(CNC.vars["TLO"], "1.234")
        self.assertEqual(CNC.vars["prbx"], 3.0)
        self.assertEqual(CNC.vars["prby"], 4.0)
        self.assertEqual(CNC.vars["prbz"], -0.5)
        self.assertEqual(
            CNC.vars["PRB"], ["3.000", "4.000", "-0.500", "0"]
        )
        self.assertIn("G0", CNC.vars["G"])
        self.assertIn("G54", CNC.vars["G"])

    def test_override_set_feed_100(self):
        CNC.vars["_OvFeed"] = 100
        CNC.vars["OvFeed"] = 90
        CNC.vars["_OvRapid"] = 100
        CNC.vars["OvRapid"] = 100
        CNC.vars["_OvSpindle"] = 100
        CNC.vars["OvSpindle"] = 100

        self.controller.overrideSet()

        self.assertEqual(self.sender.written, [GRBL1.OV_FEED_100])

    def test_jog(self):
        self.controller.jog("X10")
        self.assertEqual(self.sender.written, ["$J=G91 X10 F100000"])
