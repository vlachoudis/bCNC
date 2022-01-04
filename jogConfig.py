import tkinter 
import threading
import time
import sys
from functools import partial

#open Config file 
myConf = open("jogConf.txt",'w')

# define Window and canvas for status
wind = tkinter.Tk()
canv = tkinter.Canvas(wind,height=50,width=300)
canv.grid(row=2,column=0,columnspan=6)
#define Jog buttons
#routines to assign keycode to jogkey
mutex = threading.Lock()
lastKeyCode = 0
lastKeySym = ""
def release(ev=None):
    global lastKeyCode
    global lastKeySym
    print(ev)
    if mutex.locked():
        lastKeyCode = ev.keycode
        lastKeySym = ev.keysym
        mutex.release()

wind.bind("<KeyRelease>",release)

def addKey(keyName:str,file):
    def route():
        global canv
        global mutex
        global lastKeyCode
        global lastKeySym
        canv.create_text(150,25,text="Press Key ({})".format(keyName))
        if not mutex.locked():
            mutex.acquire()
        mutex.acquire(blocking=True)
        file.write(str(keyName)+" "+str(lastKeyCode)+" " +str(lastKeySym)+"\n")
        canv.delete("all")
        canv.create_text(150,25,text="Ok!")
        time.sleep(0.1)
        canv.delete("all")
    threading.Thread(target=route).start()


r,c = 0,0
for jogKey in "XYZABC":
    for direction in "+-":
        keyName = jogKey+direction
        tkinter.Button(wind,
                       text=jogKey+direction,
                       command=partial(addKey,jogKey+direction,myConf)).grid(row=r,column=c)
        c+=1
    if jogKey=='Z': 
        r += 1
        c  = 0

#Exit Button
tkinter.Button(wind,
                 text="Exit",
                 command=wind.destroy).grid(row=3,column=0)


wind.mainloop()
myConf.close()



