import unittest

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

import G2Core
from CNC import CNC
from mocks import MockSender


class TestG2Core(unittest.TestCase):
    def setUp(self):
        self.sender = MockSender()
        self.controller = G2Core.Controller(self.sender)
        CNC.vars["state"] = ""

    def test_map_state(self):
        self.assertEqual(self.controller.mapState(1), "Idle")
        self.assertEqual(self.controller.mapState(2), "Alarm")
        self.assertEqual(self.controller.mapState(5), "Run")
        self.assertEqual(self.controller.mapState(6), "Hold")
        self.assertEqual(self.controller.mapState(10), "Jog")

    def test_status_report(self):
        self.controller.processStatusReport(
            {
                "stat": 1,
                "posx": -40.0,
                "posy": 0.0,
                "posz": 2.042,
                "mpox": 0.0,
                "mpoy": -1.333,
                "mpoz": 2.001,
                "feed": 120.5,
                "tofz": 1.5,
                "tool": 3,
                "plan": 0,
                "dist": 0,
                "unit": 1,
                "coor": 1,
            }
        )

        self.assertEqual(CNC.vars["state"], "Idle")
        self.assertEqual(CNC.vars["wx"], -40.0)
        self.assertEqual(CNC.vars["wy"], 0.0)
        self.assertEqual(CNC.vars["wz"], 2.042)
        self.assertEqual(CNC.vars["mx"], 0.0)
        self.assertEqual(CNC.vars["my"], -1.333)
        self.assertEqual(CNC.vars["mz"], 2.001)
        self.assertEqual(CNC.vars["curfeed"], 120.5)
        self.assertEqual(CNC.vars["TLO"], 1.5)
        self.assertEqual(CNC.vars["tool"], 3)
        self.assertEqual(CNC.vars["plane"], "G17")
        self.assertEqual(CNC.vars["distance"], "G90")
        self.assertEqual(CNC.vars["units"], "G21")
        self.assertEqual(CNC.vars["WCS"], "G54")
        self.assertTrue(self.sender._posUpdate)

    def test_parse_values_g54(self):
        self.controller.parseValues(
            {"g54": {"x": 10.0, "y": -7.0, "z": -9.0}}
        )
        self.assertEqual(CNC.vars["G54X"], 10.0)
        self.assertEqual(CNC.vars["G54Y"], -7.0)
        self.assertEqual(CNC.vars["G54Z"], -9.0)

    def test_parse_line_json_status(self):
        line = (
            '{"r":{"sr":{"stat":5,"mpox":1.0,"mpoy":2.0,"mpoz":3.0,'
            '"posx":1.0,"posy":2.0,"posz":3.0}},"f":[1,0,9]}'
        )
        self.assertTrue(self.controller.parseLine(line, [], []))
        self.assertEqual(CNC.vars["state"], "Run")
        self.assertEqual(CNC.vars["mx"], 1.0)
        self.assertEqual(CNC.vars["my"], 2.0)
        self.assertEqual(CNC.vars["mz"], 3.0)
