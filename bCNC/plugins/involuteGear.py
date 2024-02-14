# $Id$
#
# Author: @LittlePierre Pierre KLein
# https://github.com/LittlePierre/
# Date:      13 Mar 2023


# from bmath import Vector
from CNC import CNC, CW, Block
from ToolsPage import Plugin
from builtins import isinstance

__author__ = "LittlePierre"

__name__ = _("involuteGear")



from math import acos,sqrt,atan2,pi,cos,sin
from operator import sub

import involute
from involute import rotate as rotate


def involutePolyLigne(baseRadius, limitRadius, order, fstart, fstop):
    """Approximates an involute using a Polyline-curve
    This function overrides involute.BezCoeffs since gcode does not implement Beziers curves neither splines
    Instead, this function generates an involute interpolated by a polyline
    Parameters:
    baseRadius - the radius of base circle of the involute.
        This is where the involute starts, too.
    limitRadius - the radius of an outer circle, where the involute ends.
    order - dummy variable here ( used for compatibilty with involute.BezCoeffs here)
    fstart - fraction of distance along the involute to start the approximation.
    fstop - fraction of distance along the involute to stop the approximation.
    """
    Rb = baseRadius
    Ra = limitRadius
    ta = sqrt(Ra * Ra - Rb * Rb) / Rb   # involute angle at the limit radius
    te = sqrt(fstop) * ta          # involute angle, theta, at end of approx
    ts = sqrt(fstart) * ta         # involute angle, theta, at start of approx

    def involuteXPolyLigne(theta):
        return Rb * (cos(theta) + theta * sin(theta))
    def involuteYPolyLigne(theta):
        return Rb * (sin(theta) - theta * cos(theta))
    nb = 10
    step = (te - ts)/nb
    current = ts
    result = []
    for index in range(nb+1):
        bx = involuteXPolyLigne(current)
        by = involuteYPolyLigne(current)
        result.append((bx, by))
        current += step
    return result

'''override involute.bzCoeffs here'''
involute.BezCoeffs = involutePolyLigne

class Move():
    def __init__(self,end):
        self.end = end
    def __str__(self):
        result = "Move : \n"
        result += "end :" + str(self.end)+"\n"
        return result
class LineSegment():
    def __init__(self,start,end):
        self.start = start
        self.end = end
    def __str__(self):
        result = "LineSegment : \n"
        result += "start : "+str(self.start)+"\n"
        result += "end :" + str(self.end)+"\n"
        return result
class Curve():
    def __init__(self,start,points):
        self.start = start
        self.points = points
    def __str__(self):
        result = "Curve : \n"
        result += "start : "+str(self.start)+"\n"
        result += "points :" + str(self.points)+"\n"
        return result
class Arc():#sweep = True => antiClockWise
    def __init__(self,start, end,r,sweep):
        self.start = start
        self.end = end
        self.r = r
        self.sweep = sweep
        self.c = self.center()
        self.startangle = self.angle(self.start)
        self.endangle = self.angle(self.end)
        self.extend = self.endangle - self.startangle
    def __str__(self):
        result = "Arc : \n"
        result += "start : "+str(self.start)+"\n"
        result += "end :" + str(self.end)+"\n"
        result += "r" + str(self.r)+"\n"
        result += "sweep" + str(self.sweep)+"\n"
        return result
    def center(self):
        start_end_vector = tuple( map(sub, self.end, self.start) )
        lg = sqrt(sum(elt*elt for elt in start_end_vector))
        if lg/2. > self.r:
            raise Exception("Arc error : radius is smaller than distance between points")
        unit = tuple(elt/lg for elt in start_end_vector)
        norm = (-unit[1],unit[0])
        middlePoint = tuple(elt/2. for elt in tuple(sum(x) for x in zip(self.start, self.end)))
        h = sqrt(self.r**2-lg**2/4.)

        if self.sweep :#anticlockwise
            y = tuple(elt*h for elt in norm)
        else :#clockwise
            y = tuple(-elt*h for elt in norm)
        c = tuple(sum(x) for x in zip(middlePoint, y))
        return c
    def angle(self,point):
        (x,y) = tuple(map(sub,point,self.c))
        theta = atan2(y,x)*180./pi
        if theta < 0. :
            theta += 360.
        return theta



class PathBuilder(object):
    """A helper class to prepare a wire object, used for gcode generation"""
    def __init__(self):
        self.pos = None
        self.theta = 0.0
        self.wire = []

    def move(self, p):
        """set current position"""
        self.pos = p
        self.wire.append(Move(self.pos))

    def line(self, p):
        """Add a segment between self.pos and p"""
        p = rotate(p, self.theta)
        start = self.pos
        end = p
        self.wire.append(LineSegment(self.pos, end))
        self.pos = end

    def arc(self, p, r, sweep):
        """"Add an arc from self.pos to p which radius is r
        sweep (0 or 1) determine the orientation of the arc
        """
        p = rotate(p, self.theta)
        start = self.pos
        end = p
        self.wire.append(Arc(start, end,r,sweep))
        self.pos = end

    def curve(self, *points):
        """Add a polyline curve from self.pos to points[-1]
        """
        points = [rotate(p,self.theta) for p in points]
        self.wire.append(Curve(self.pos,points))
        self.pos = points[-1]

    def close(self):
        pass


class involuteGearControler():
    def __init__(self):
        pass 
    def makeGear(self,Z,m,phi,addCoeff,dedCoeff,filletCoeff,shiftCoeff,external,useDefault):
        self.w = PathBuilder()
        if external :
            if useDefault :
                addCoeff = 1.0
                dedCoeff = 1.25
                filletCoeff = 0.38
                shiftCoeff = 0.0
                phi = 20.
            involute.CreateExternalGear(self.w, m, Z, phi, split=False,addCoeff=addCoeff,dedCoeff=dedCoeff,filletCoeff=filletCoeff,shiftCoeff=shiftCoeff)

        else :
            if useDefault :
                addCoeff = 0.6
                dedCoeff = 1.25
                filletCoeff = 0.38
                shiftCoeff = 0.
                phi = 20.
            involute.CreateInternalGear(self.w, m, Z, phi, split=False,addCoeff=addCoeff,dedCoeff=dedCoeff,filletCoeff=filletCoeff,shiftCoeff=shiftCoeff)

    def calcGcode(self):
        blocks = []
        elt = self.w.wire[0]

        block = Block("involute")
        for elt in self.w.wire :
            if isinstance(elt,LineSegment):
                block.append(CNC.gline(elt.end[0],elt.end[1]))
            elif isinstance(elt,Arc):
                start = elt.start
                end = elt.end
                center = elt.c
                x = end[0]
                y = end[1]
                i = center[0]-start[0]
                j= center[1]-start[1]
                if elt.sweep :
                    g = 3
                else :
                    g = 2
                block.append(CNC.garc(g,x=x,y=y,i=i,j=j))
            elif isinstance(elt,Curve):
                for point in elt.points:
                    block.append(CNC.gline(point[0],point[1]))
            elif isinstance(elt,Move):
                block.append(CNC.grapid(elt.end[0],elt.end[1]))
                block.append(CNC.zenter(0.0))
        blocks.append(block)
        return blocks
# =============================================================================
# Create a simple Gear
# =============================================================================
class Tool(Plugin):
    __doc__ = _("Generate involute gears")

    def __init__(self, master):
        Plugin.__init__(self, master, "involuteGear")
        self.icon = "gear"
        self.group = "Generator"
        self.variables = [
            ("name", "db", "", _("Name")),
            ("Z", "int", 10, _("No of teeth"),"This is the number of teeth"),
            ("m", "mm", 1.0, _("Module"),"This is the module of the Gear; d = m*Z"),
            ("external", "bool", True, _("x External Gear"), "x for external gear / None for internal gears"),
            ("useDefault","bool",True,_("use default parameters"),"x will use default parameters, None will use parameters specified below"),
            ("phi", "float", 20.0, _("Pressure angle"),"This is the pressure angle, default is 20 deg"),
            ("addCoeff", "float", 1.0, _("Addendum coeff"),"this is the addendum coeff, default is 1.0*m in external gears, 0.6 for internal"),
            ("dedCoeff", "float", 1.25, _("Dedendum coeff"),"This is the deddendum coef, default is 1.25*m"),
            ("filletCoeff", "float", 0.38, _("fillet coeff"),"This is the fillet coef, default is 0.38 in ISO Rack specifications"),
            ("shiftCoeff", "float", 0.0, _("shiftCoeff"),"shiftCoeff is the profile shift coefficient (profile shift normalized by module)"),
        ]
        self.buttons.append("exe")

    # ----------------------------------------------------------------------
    def execute(self, app):
        n = self["name"]
        if not n or n == "default":
            n = "involuteGear"
        Z=self["Z"]
        m=self ["m"]
        phi = self["phi"]
        external=self["external"]
        useDefault=self["useDefault"]
        addCoeff =self["addCoeff"]
        dedCoeff=self["dedCoeff"]
        filletCoeff=self["filletCoeff"]
        shiftCoeff = self["shiftCoeff"]
        try : 
            controler = involuteGearControler()
            controler.makeGear(Z,m,phi,addCoeff,dedCoeff,filletCoeff,shiftCoeff,external,useDefault)
            blocks = controler.calcGcode()
        except Exception as exc :
            print(exc)
            blocks = []
        active = app.activeBlock()
        if active == 0:
            active = 1
        app.gcode.insBlocks(active, blocks, _("Create involute GEAR"))
        app.refresh()
        app.setStatus(_("Generated: involute GEAR"))


if __name__ == "__main__":
    pass
