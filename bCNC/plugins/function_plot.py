from CNC import CNC, Block
from ToolsPage import Plugin

__author__ = "kswiorek"
__email__ = "ks@baskijski.net"

__name__ = _("Function")
__version__ = "2.5.1"


# I'm not commenting these lines, I just copied them from https://github.com/vlachoudis/bCNC/wiki/Tutorials:-How-to-create-a-plugin
class Tool(Plugin):
    __doc__ = _("""Generates gcode from a formula""")

    def __init__(self, master):
        Plugin.__init__(self, master, "Function")

        self.icon = "parabola"
        self.group = "Artistic"

        self.variables = [
            ("name", "db", "Function", _("Name")),
            ("form", "text", "x**2", _("Formula")),
            ("res", "float", 0.005, _("Resolution")),
            ("ranX", "float", 10, _("Range of X")),
            ("ranY", "float", 10, _("Range of Y")),
            ("centX", "float", 5, _("Center X coordinate")),
            ("centY", "float", 0, _("Center Y coordinate")),
            ("dimX", "mm", 100.0, _("X dimension")),
            ("dimY", "mm", 100.0, _("Y dimension")),
            ("spacX", "float", 1, _("X number line xpacing")),
            ("spacY", "float", 1, _("Y number line xpacing")),
            ("lin", "float", 1, _("Small line length")),
            ("draw", "bool", True, _("Draw coordinate system?")),
        ]
        self.buttons.append("exe")

        self.help = """
This plugin plots graph of a function.
There are some examples of function formulas that can be plotted:

- x**2
- sin(x)
TODO
"""

    def execute(self, app):
        name = self["name"]

        if not name or name == "default":
            name = "Function"

        # Initialize blocks that will contain our gCode
        blocks = []
        block = Block(name)

        # Variable definitions
        formula = self["form"]
        res = self["res"]  # X resolution
        # Range of X,Y, from -10, to 10 range is 20
        ran = [self["ranX"], self["ranY"]]
        cent = [
            self["centX"],
            self["centY"],
        ]  # Coordinates X,Y of the center from bottom left of the coordinate system
        dim = [self["dimX"], self["dimY"]]  # Real dimensions in gcode units
        spacX = self["spacX"]  # Spacing of X axis lines
        spacY = self["spacY"]  # Spacing of Y axis lines
        lin = self["lin"]  # Small value - length of a line in gcode units
        draw = self["draw"]  # Draw the coordinate system

        block.append("(Generated with a script by kswiorek)\n")
        block.append("(Equation: " + formula + ")\n")
        block.append("(Resolution: " + str(res) + ")\n")
        block.append("(Range: " + str(ran) + ")\n")
        block.append("(Center: " + str(cent) + ")\n")
        block.append("(Dimensions: " + str(dim) + ")\n")
        block.append("(SpacingXY: " + str(spacX) + ", " + str(spacY) + ")\n")

        def mapc(var, axis):  # Map coordinate systems
            return var * (dim[axis] / ran[axis])

        # Define coordinate system mins and maxes
        minX = -cent[0]

        minY = -cent[1]
        maxY = ran[1] - cent[1]

        # Define domain and codomain
        X = []
        Y = []

        e_old = ""  # Store old exception to compare

        # Calculate values for arguments with a resolution
        for i in range(
            0, int(ran[0] / res + 1)
        ):  # Complaints about values being floats
            x = i * res + minX  # Iterate x
            X.append(x)
            try:
                Y.append(eval(formula))

            except Exception as exc:  # Append None, not to loose sync with X
                Y.append(None)
                e = str(exc)
                if e != e_old:  # If there is a different exception - display it
                    print("Warning: " + str(e))
                    app.setStatus(_("Warning: " + str(e)))
                    e_old = e

        raised = True  # Z axis is raised at start

        # Clip values out of bounds, replace with None, not to loose sync with X
        for i, item in enumerate(Y):
            y = Y[i]
            if y is not None and (y < minY or y > maxY):
                Y[i] = None

        # Y without "None", min() and max() can't compare them
        Ynn = []  # Y no Nones
        for i, item in enumerate(Y):
            if not Y[i] is None:
                Ynn.append(Y[i])

        block.append(CNC.gcode(1, [("f", CNC.vars["cutfeed"])]))  # Set feedrate

        if draw:  # If the user selected to draw the coordinate system
            # X axis
            block.append(CNC.grapid(z=3))
            # 1st point of X axis line
            block.append(CNC.grapid(0, mapc(cent[1], 1)))
            block.append(CNC.grapid(z=0))

            block.append(
                CNC.gline(dim[0] + lin * 1.2, mapc(cent[1], 1))
            )  # End of X axis line + a bit more for the arrow

            block.append(
                CNC.gline(dim[0] - lin / 2, mapc(cent[1], 1) - lin / 2)
            )  # bottom part of the arrow

            block.append(CNC.grapid(z=3))
            block.append(
                CNC.grapid(dim[0] + lin * 1.2, mapc(cent[1], 1), 0)
            )  # End of X axis line
            block.append(CNC.grapid(z=0))

            block.append(
                CNC.gline(dim[0] - lin / 2, mapc(cent[1], 1) + lin / 2)
            )  # top part of the arrow
            block.append(CNC.grapid(z=3))

            # Y axis, just inverted x with y
            block.append(CNC.grapid(z=3))
            # 1st point of Y axis line
            block.append(CNC.grapid(mapc(cent[0], 0), 0))
            block.append(CNC.grapid(z=0))

            block.append(
                CNC.gline(mapc(cent[0], 0), dim[1] + lin * 1.2)
            )  # End of Y axis line + a bit more for the arrow

            block.append(
                CNC.gline(mapc(cent[0], 0) - lin / 2, dim[1] - lin / 2)
            )  # left part of the arrow

            block.append(CNC.grapid(z=3))
            block.append(
                CNC.grapid(mapc(cent[0], 0), dim[1] + lin * 1.2)
            )  # End of Y axis line
            block.append(CNC.grapid(z=0))

            block.append(
                CNC.gline(mapc(cent[0], 0) + lin / 2, dim[1] - lin / 2)
            )  # right part of the arrow
            block.append(CNC.grapid(z=3))

            # X axis number lines
            i = 0
            while i < ran[0] - cent[0]:  # While i is on the left of the arrow
                i += spacX  # Add line spacing

                # Draw lines right of the center
                block.append(
                    CNC.grapid(mapc(i + cent[0], 0), mapc(cent[1], 1) + lin / 2)
                )
                block.append(CNC.grapid(z=0))
                block.append(
                    CNC.gline(mapc(i + cent[0], 0), mapc(cent[1], 1) - lin / 2)
                )
                block.append(CNC.grapid(z=3))

            i = 0
            while (
                i > -cent[0]
            ):  # While i is lower than center coordinate, inverted for easier math
                i -= spacX  # Add line spacing

                # Draw lines left of the center
                block.append(
                    CNC.grapid(mapc(i + cent[0], 0), mapc(cent[1], 1) + lin / 2)
                )
                block.append(CNC.grapid(z=0))
                block.append(
                    CNC.gline(mapc(i + cent[0], 0), mapc(cent[1], 1) - lin / 2)
                )
                block.append(CNC.grapid(z=3))

            # Y axis number lines
            i = 0
            while i < ran[1] - cent[1]:  # While i is between the center and the arrow
                i += spacX  # Add line spacing

                # Draw lines top of the center (everything just inverted)
                block.append(
                    CNC.grapid(mapc(cent[0], 0) + lin / 2, mapc(i + cent[1], 1))
                )
                block.append(CNC.grapid(z=0))
                block.append(
                    CNC.gline(mapc(cent[0], 0) - lin / 2, mapc(i + cent[1], 1))
                )
                block.append(CNC.grapid(z=3))

            i = 0
            while i > -1 * cent[1]:
                i -= spacX  # Add line spacing

                # Draw lines bottom of the center
                block.append(
                    CNC.grapid(mapc(cent[0], 0) + lin / 2, mapc(i + cent[1], 1))
                )
                block.append(CNC.grapid(z=0))
                block.append(
                    CNC.gline(mapc(cent[0], 0) - lin / 2, mapc(i + cent[1], 1))
                )
                block.append(CNC.grapid(z=3))

            raised = True  # Z was raised

        # Draw graph
        for i, item in enumerate(Y):
            if not Y[i] is None:
                x = mapc(X[i] + cent[0], 0)  # Take an argument
                y = mapc(Y[i] + cent[1], 1)  # Take a value
            else:
                y = Y[i]  # only for the None checks next

            # If a None "period" just started raise Z
            if y is None and not raised:
                raised = True
                block.append(CNC.grapid(z=3))
            # If Z was raised and the None "period" ended move to new
            # coordinates
            elif (y is not None and raised):

                block.append(CNC.grapid(round(x, 2), round(y, 2)))
                block.append(CNC.grapid(z=0))  # Lower Z
                raised = False
            # Nothing to do with Nones? Just draw
            elif y is not None and not raised:
                block.append(CNC.gline(round(x, 2), round(y, 2)))

        block.append(CNC.grapid(z=3))  # Raise on the end

        blocks.append(block)
        active = app.activeBlock()
        app.gcode.insBlocks(
            active, blocks, "Function inserted"
        )  # insert blocks over active block in the editor
        app.refresh()  # refresh editor
        app.setStatus(_("Generated function graph"))  # feed back result
        print()
