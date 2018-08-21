from __future__ import division
import unittest
from ..path import CubicBezier, QuadraticBezier, Line, Arc, Path, Move
from ..parser import parse_path


class TestParser(unittest.TestCase):

    def test_svg_examples(self):
        """Examples from the SVG spec"""
        path1 = parse_path('M 100 100 L 300 100 L 200 300 z')
        self.assertEqual(path1, Path(Move(100 + 100j),
                                     Line(100 + 100j, 300 + 100j),
                                     Line(300 + 100j, 200 + 300j),
                                     Line(200 + 300j, 100 + 100j)))
        self.assertTrue(path1.closed)

        # for Z command behavior when there is multiple subpaths
        path1 = parse_path('M 0 0 L 50 20 M 100 100 L 300 100 L 200 300 z')
        self.assertEqual(path1, Path(
            Move(0j),
            Line(0 + 0j, 50 + 20j),
            Move(100+100j),
            Line(100 + 100j, 300 + 100j),
            Line(300 + 100j, 200 + 300j),
            Line(200 + 300j, 100 + 100j)))

        path1 = parse_path('M 100 100 L 200 200')
        path2 = parse_path('M100 100L200 200')
        self.assertEqual(path1, path2)

        path1 = parse_path('M 100 200 L 200 100 L -100 -200')
        path2 = parse_path('M 100 200 L 200 100 -100 -200')
        self.assertEqual(path1, path2)

        path1 = parse_path("""M100,200 C100,100 250,100 250,200
                              S400,300 400,200""")
        self.assertEqual(path1,
                         Path(Move(100 + 200j),
                              CubicBezier(100 + 200j, 100 + 100j, 250 + 100j, 250 + 200j),
                              CubicBezier(250 + 200j, 250 + 300j, 400 + 300j, 400 + 200j)))

        path1 = parse_path('M100,200 C100,100 400,100 400,200')
        self.assertEqual(path1,
                         Path(Move(100 + 200j),
                              CubicBezier(100 + 200j, 100 + 100j, 400 + 100j, 400 + 200j)))

        path1 = parse_path('M100,500 C25,400 475,400 400,500')
        self.assertEqual(path1,
                         Path(Move(100 + 500j),
                              CubicBezier(100 + 500j, 25 + 400j, 475 + 400j, 400 + 500j)))

        path1 = parse_path('M100,800 C175,700 325,700 400,800')
        self.assertEqual(path1,
                         Path(Move(100+800j),
                              CubicBezier(100 + 800j, 175 + 700j, 325 + 700j, 400 + 800j)))

        path1 = parse_path('M600,200 C675,100 975,100 900,200')
        self.assertEqual(path1,
                         Path(Move(600 + 200j),
                              CubicBezier(600 + 200j, 675 + 100j, 975 + 100j, 900 + 200j)))

        path1 = parse_path('M600,500 C600,350 900,650 900,500')
        self.assertEqual(path1,
                         Path(Move(600 + 500j),
                              CubicBezier(600 + 500j, 600 + 350j, 900 + 650j, 900 + 500j)))

        path1 = parse_path("""M600,800 C625,700 725,700 750,800
                              S875,900 900,800""")
        self.assertEqual(path1,
                         Path(Move(600 + 800j),
                              CubicBezier(600 + 800j, 625 + 700j, 725 + 700j, 750 + 800j),
                              CubicBezier(750 + 800j, 775 + 900j, 875 + 900j, 900 + 800j)))

        path1 = parse_path('M200,300 Q400,50 600,300 T1000,300')
        self.assertEqual(path1,
                         Path(Move(200 + 300j),
                              QuadraticBezier(200 + 300j, 400 + 50j, 600 + 300j),
                              QuadraticBezier(600 + 300j, 800 + 550j, 1000 + 300j)))

        path1 = parse_path('M300,200 h-150 a150,150 0 1,0 150,-150 z')
        self.assertEqual(path1,
                         Path(Move(300 + 200j),
                              Line(300 + 200j, 150 + 200j),
                              Arc(150 + 200j, 150 + 150j, 0, 1, 0, 300 + 50j),
                              Line(300 + 50j, 300 + 200j)))

        path1 = parse_path('M275,175 v-150 a150,150 0 0,0 -150,150 z')
        self.assertEqual(path1,
                         Path(Move(275 + 175j),
                              Line(275 + 175j, 275 + 25j),
                              Arc(275 + 25j, 150 + 150j, 0, 0, 0, 125 + 175j),
                              Line(125 + 175j, 275 + 175j)))

        path1 = parse_path('M275,175 v-150 a150,150 0 0,0 -150,150 L 275,175 z')
        self.assertEqual(path1,
                         Path(Move(275 + 175j),
                              Line(275 + 175j, 275 + 25j),
                              Arc(275 + 25j, 150 + 150j, 0, 0, 0, 125 + 175j),
                              Line(125 + 175j, 275 + 175j)))

        path1 = parse_path("""M600,350 l 50,-25
                              a25,25 -30 0,1 50,-25 l 50,-25
                              a25,50 -30 0,1 50,-25 l 50,-25
                              a25,75 -30 0,1 50,-25 l 50,-25
                              a25,100 -30 0,1 50,-25 l 50,-25""")
        self.assertEqual(path1,
                         Path(Move(600 + 350j),
                              Line(600 + 350j, 650 + 325j),
                              Arc(650 + 325j, 25 + 25j, -30, 0, 1, 700 + 300j),
                              Line(700 + 300j, 750 + 275j),
                              Arc(750 + 275j, 25 + 50j, -30, 0, 1, 800 + 250j),
                              Line(800 + 250j, 850 + 225j),
                              Arc(850 + 225j, 25 + 75j, -30, 0, 1, 900 + 200j),
                              Line(900 + 200j, 950 + 175j),
                              Arc(950 + 175j, 25 + 100j, -30, 0, 1, 1000 + 150j),
                              Line(1000 + 150j, 1050 + 125j)))

    def test_others(self):
        # Other paths that need testing:

        # Relative moveto:
        path1 = parse_path('M 0 0 L 50 20 m 50 80 L 300 100 L 200 300 z')
        self.assertEqual(path1, Path(
            Move(0j),
            Line(0 + 0j, 50 + 20j),
            Move(100 + 100j),
            Line(100 + 100j, 300 + 100j),
            Line(300 + 100j, 200 + 300j),
            Line(200 + 300j, 100 + 100j)))

        # Initial smooth and relative CubicBezier
        path1 = parse_path("""M100,200 s 150,-100 150,0""")
        self.assertEqual(path1,
                         Path(Move(100 + 200j),
                              CubicBezier(100 + 200j, 100 + 200j, 250 + 100j, 250 + 200j)))

        # Initial smooth and relative QuadraticBezier
        path1 = parse_path("""M100,200 t 150,0""")
        self.assertEqual(path1,
                         Path(Move(100 + 200j),
                              QuadraticBezier(100 + 200j, 100 + 200j, 250 + 200j)))

        # Relative QuadraticBezier
        path1 = parse_path("""M100,200 q 0,0 150,0""")
        self.assertEqual(path1,
                         Path(Move(100 + 200j),
                              QuadraticBezier(100 + 200j, 100 + 200j, 250 + 200j)))

    def test_negative(self):
        """You don't need spaces before a minus-sign"""
        path1 = parse_path('M100,200c10-5,20-10,30-20')
        path2 = parse_path('M 100 200 c 10 -5 20 -10 30 -20')
        self.assertEqual(path1, path2)

    def test_numbers(self):
        """Exponents and other number format cases"""
        # It can be e or E, the plus is optional, and a minimum of +/-3.4e38 must be supported.
        path1 = parse_path('M-3.4e38 3.4E+38L-3.4E-38,3.4e-38')
        path2 = Path(Move(-3.4e+38 +  3.4e+38j), Line(-3.4e+38 + 3.4e+38j, -3.4e-38 + 3.4e-38j))
        self.assertEqual(path1, path2)

    def test_errors(self):
        self.assertRaises(ValueError, parse_path, 'M 100 100 L 200 200 Z 100 200')

    def test_non_path(self):
        # It's possible in SVG to create paths that has zero length,
        # we need to handle that.

        path = parse_path("M10.236,100.184")
        self.assertEqual(path.d(), 'M 10.236,100.184')
