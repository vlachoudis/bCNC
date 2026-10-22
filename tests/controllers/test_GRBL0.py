import os
import queue
import sys
import unittest

import pathfix

import GRBL0
from CNC import CNC


class MockSender:
    MSG_RECEIVE = 2
    def __init__(self):
        self._alarm = False
        self._msg = None
        self.sio_wait = False
        self.log = queue.Queue()
        self.gcode = MockGCode()

class MockGCode:
    class Probe:
        def add(self, x, y, z): pass
    def __init__(self):
        self.probe = self.Probe()


class TestGRBL0(unittest.TestCase):
    def setUp(self):
        self.sender = MockSender()
        self.controller = GRBL0.Controller(self.sender)

    def test_status_parsing(self):
        status_string = "<Idle,MPos:0.000,-1.333,2.001,WPos:-40.000,0.000,2.042>"
        self.controller.parseBracketAngle(status_string, [])

        self.assertEqual(CNC.vars["state"], "Idle")
        self.assertEqual(CNC.vars["mx"], 0.000)
        self.assertEqual(CNC.vars["my"], -1.333)
        self.assertEqual(CNC.vars["mz"], 2.001)
        self.assertEqual(CNC.vars["wx"], -40.000)
        self.assertEqual(CNC.vars["wy"], 0.000)
        self.assertEqual(CNC.vars["wz"], 2.042)

    def test_params_parsing(self):
        params_lines = [
            "[G54:10.000,-7.000,-9.000]",
            "[G55:0.000,0.000,0.000]",
            "[G56:0.000,-1.333,2.001]",
            "[G57:-40.000,0.000,2.042]",
            "[G58:3.333,4.444,5.555]",
            "[G59:-10.001,-20.002,-30.003]",
            "[G28:0.000,0.000,0.000]",
            "[G30:0.000,0.000,0.000]",
            "[G92:0.000,0.000,0.000]",
            "[TLO:0.000]",
            "[PRB:3.000,4.000,-0.500:0]",
        ]
        for line in params_lines:
            self.controller.parseBracketSquare(line)

        self.assertEqual(CNC.vars["G54"], [10.0, -7.0, -9.0])
        self.assertEqual(CNC.vars["G55"], [0.0, 0.0, 0.0])
        self.assertEqual(CNC.vars["G56"], [0.0, -1.333, 2.001])
        self.assertEqual(CNC.vars["G57"], [-40.0, 0.0, 2.042])
        self.assertEqual(CNC.vars["G58"], [3.333, 4.444, 5.555])
        self.assertEqual(CNC.vars["G59"], [-10.001, -20.002, -30.003])
        self.assertEqual(CNC.vars["G28"], [0.0, 0.0, 0.0])
        self.assertEqual(CNC.vars["G30"], [0.0, 0.0, 0.0])
        self.assertEqual(CNC.vars["G92"], [0.0, 0.0, 0.0])

        self.assertEqual(CNC.vars["TLO"], "0.000")

        self.assertEqual(CNC.vars["PRB"], [3.0, 4.0, -0.5])
        self.assertEqual(CNC.vars["prbx"], 3.0)
        self.assertEqual(CNC.vars["prby"], 4.0)
        self.assertEqual(CNC.vars["prbz"], -0.5)
