from __future__ import division
import unittest
from ..path import CubicBezier, QuadraticBezier, Line, Arc, Path
from ..parser import parse_path


class TestGeneration(unittest.TestCase):

    def test_svg_examples(self):
        """Examples from the SVG spec"""
        paths = [
            'M 100,100 L 300,100 L 200,300 Z',
            'M 0,0 L 50,20 M 100,100 L 300,100 L 200,300 Z',
            'M 100,100 L 200,200',
            'M 100,200 L 200,100 L -100,-200',
            'M 100,200 C 100,100 250,100 250,200 S 400,300 400,200',
            'M 100,200 C 100,100 400,100 400,200',
            'M 100,500 C 25,400 475,400 400,500',
            'M 100,800 C 175,700 325,700 400,800',
            'M 600,200 C 675,100 975,100 900,200',
            'M 600,500 C 600,350 900,650 900,500',
            'M 600,800 C 625,700 725,700 750,800 S 875,900 900,800',
            'M 200,300 Q 400,50 600,300 T 1000,300',
            'M -3.4E+38,3.4E+38 L -3.4E-38,3.4E-38',
            'M 0,0 L 50,20 M 50,20 L 200,100 Z',
            'M 600,350 L 650,325 A 25,25 -30 0,1 700,300 L 750,275',
        ]

        for path in paths:
            self.assertEqual(parse_path(path).d(), path)
