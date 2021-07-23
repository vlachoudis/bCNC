import CNCList
from numpy import sqrt
def findLine(app, currentX=0, currentY=0):
    if app.gcode.filename=="":
        return 0
    answer = 0
    minimumError = CNCList.MAXINT
    lines = []
    for block in app.gcode.blocks:
        for line in block:
            lines += [line]
    xValue = currentX-CNCList.MAXINT
    yValue = currentY-CNCList.MAXINT
    for (i,currentLine) in enumerate(lines):
        xValue,yValue = computeCoords(xValue,yValue, currentLine)
        
        dist = (xValue - currentX)**2 + (yValue - currentY)**2
        dist = sqrt(dist)
        print("{},{} -> {},{} found {}".format(currentX,currentY,xValue,yValue,dist))
        if dist < minimumError:
            minimumError = dist
            answer = i
    print("from file {} line {} = {}".format(app.gcode.filename,answer,lines[answer]))
    return answer

def computeCoords(currentX,currentY, line):
    def nextNumber(line,index):
        value = ""
        for w in line[index:]:
            if w.isdigit() or w=='.':
                value += w
            else:
                break
        try:
            return float(value)
        except:
            print("Error in Code")
            return -CNCList.MAXINT

    line = line.upper()
    indexX = line.find('X')
    indexY = line.find('Y')
    if indexX >= 0:
        currentX = nextNumber(line,indexX+1)
    if indexY >= 0:
        currentY = nextNumber(line,indexY+1)
    return currentX,currentY
