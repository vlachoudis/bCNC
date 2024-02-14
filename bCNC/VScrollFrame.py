from tkinter import (
    VERTICAL,
    NW,
    E,
    SE,
    Y,
    TOP,
    BOTH,
    LEFT,
    RIGHT,
    UNITS,
    ALL,
    Frame,
    Scrollbar,
    Canvas,
)

class VScrollFrame(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.bg="red"
        self.canvas = Canvas(self, borderwidth=0, highlightthickness=0)
        self.frame = Frame(self.canvas)
        self.vsb = Scrollbar(self, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side=RIGHT, fill=Y)        
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self._frame_window = self.canvas.create_window((0, 0), window=self.frame, anchor=NW)

        self.frame.bind("<Configure>", self.onFrameConfigure)
        self.canvas.bind("<Configure>", self.onCanvasConfigure)

    def onFrameConfigure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox(ALL))

    def onCanvasConfigure(self, event):
        self.canvas.itemconfig(self._frame_window, width=event.width)