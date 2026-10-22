import queue


class MockGCode:
    class Probe:
        def __init__(self):
            self.points = []

        def add(self, x, y, z):
            self.points.append((x, y, z))

    def __init__(self):
        self.probe = self.Probe()


class MockSender:
    MSG_OK = 0
    MSG_ERROR = 1
    MSG_RECEIVE = 2

    def __init__(self):
        self._alarm = False
        self._msg = None
        self.sio_wait = False
        self.sio_status = False
        self.log = queue.Queue()
        self.gcode = MockGCode()
        self.running = False
        self.runningPrev = False
        self._posUpdate = False
        self._probeUpdate = False
        self._gUpdate = False
        self._update = False
        self._gcount = 0
        self._cycleStartRun = False
        self.written = []


    def controllerStateChange(self, state):
        pass

    def serial_write(self, data):
        self.written.append(data)

    def sendGCode(self, cmd):
        self.written.append(cmd)
