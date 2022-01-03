import tkinter 
import threading
import time
import sys

#open Config file 
myConf = open("jogConf.txt",'w')

# define Window and canvas for status
wind = tkinter.Tk()
canv = tkinter.Canvas(wind,height=50,width=300)
canv.grid(row=2,column=0,columnspan=6)
#define Jog buttons
tkinter.Button(
    wind,
    text="X+",
    command=lambda:addKey("X+",myConf)
).grid(row=0,column=0)
tkinter.Button(
    wind,
    text="X-",
    command=lambda:addKey("X-",myConf)
).grid(row=0,column=1)
tkinter.Button(
    wind,
    text="Y+",
    command=lambda:addKey("Y+",myConf)
).grid(row=0,column=2)
tkinter.Button(
    wind,
    text="Y-",
    command=lambda:addKey("Y-",myConf)
).grid(row=0,column=3)
tkinter.Button(
    wind,
    text="Z+",
    command=lambda:addKey("Z+",myConf)
).grid(row=0,column=4)
tkinter.Button(
    wind,
    text="Z-",
    command=lambda:addKey("Z-",myConf)
).grid(row=0,column=5)
tkinter.Button(
    wind,
    text="A+",
    command=lambda:addKey("A+",myConf)
).grid(row=1,column=0)
tkinter.Button(
    wind,
    text="A-",
    command=lambda:addKey("A-",myConf)
).grid(row=1,column=1)
tkinter.Button(
    wind,
    text="B+",
    command=lambda:addKey("B+",myConf)
).grid(row=1,column=2)
tkinter.Button(
    wind,
    text="B-",
    command=lambda:addKey("B-",myConf)
).grid(row=1,column=3)
tkinter.Button(
    wind,
    text="C+",
    command=lambda:addKey("C+",myConf)
).grid(row=1,column=4)
tkinter.Button(
    wind,
    text="C-",
    command=lambda:addKey("C-",myConf)
).grid(row=1,column=5)

#Exit Button
tkinter.Button(wind,
                 text="Exit",
                 command=wind.destroy).grid(row=3,column=0)

#routines to assign keycode to jogkey
mutex = threading.Lock()
lastKey = 0
def release(ev=None):
    global lastKey
    if mutex.locked():
        lastKey = ev.keycode
        mutex.release()

wind.bind("<KeyRelease>",release)

def addKey(keyName:str,file):
    def route():
        global canv
        global mutex
        global lastKey
        canv.create_text(150,25,text="Press Key ({})".format(keyName))
        if not mutex.locked():
            mutex.acquire()
        mutex.acquire(blocking=True)
        file.write(str(keyName)+":"+str(lastKey)+"\n")
        canv.delete("all")
        canv.create_text(150,25,text="Ok!")
        time.sleep(0.1)
        canv.delete("all")
    threading.Thread(target=route).start()

wind.mainloop()
myConf.close()



