bCNC
====

GRBL CNC command sender, autoleveler, g-code editor, digitizer, CAM
and swiss army knife for all your hobby CNC needs.

An advanced fully featured g-code sender for GRBL. bCNC is a cross platform program (Windows, Linux, Mac) written in python. The sender is robust and fast able to work nicely with old or slow hardware like [Rasperry PI](http://www.openbuilds.com/threads/bcnc-and-the-raspberry-pi.3038/) (As it was validated by the GRBL mainter on heavy testing).

![bCNC screenshot](https://raw.githubusercontent.com/vlachoudis/bCNC/doc/Screenshots/bCNC.png)

# Installation
You will need the following packages to run bCNC
- tkinter the graphical toolkit for python
  Depending your python/OS it can either be already installed,
  or under the names tkinter, python-tkinter, python-tk
- pyserial or under the name python-serial, python-pyserial
- numpy
- Optionally:
- python-imaging-tk: the PIL libraries for autolevel height map
- python-opencv: for webcam streaming on web pendant
- scipy: for 100 times faster 3D mesh slicing

Expand the directory or download it from github
and run the bCNC command

# Configuration
You can modify most of the parameters from the "Tools -> Machine"
page. Only the changes/differences from the default configuration
file will be saved in your home directory ${HOME}/.bCNC  or ~/.bCNC

The default configuration is stored on bCNC.ini in the
installation directory.

*PLEASE DO NOT CHANGE THIS ONE*

# Features:
- simple and intuitive interface for small screens
- import/export **g-code**, **dxf** and **svg** files
- fast g-code sender (works nicely on RPi and old hardware)
- workspace configuration (G54..G59 commands)
- user configurable buttons
- g-code **function evaluation** with run time expansion
- feed override during the running for fine tuning
- Easy probing:
  - simple probing
  - center finder with a probing ring
  - **auto leveling**, Z-probing and auto leveling by altering the g-code during
    sending (or permanently autoleveling the g-code file).
  - height color map display
  - create g-code by joging and recording points (can even use camera for this)
  - **manual tool change** expansion and automatic tool length probing
  - **canned cycles** expansion
- Various Tools:
  - user configurable database of materials, endmills, stock
  - properties database of materials, stock, end mills etc..
  - basic **CAM** features (profiling, pocketing, drilling, flat/helical/ramp cutting, thread milling, cutout tabs)
  - User g-code plugins:
    - bowl generator
    - finger joint box generator
    - simple spur gear generator
    - spirograph generator
    - surface flatten
    - ...
- G-Code editor and display
    - graphical display of the g-code, and workspace
    - graphically moving and editing g-code
    - reordering code and **rapid motion optimization**
    - moving, rotating, mirroring the g-code
- Web pendant to be used via smart phones

# Debuging
You can use following command to connect to debug serial traffic.
ttyUSB0 is real HW, ttyUSB23 is gonna be new fake device to which you'll connect the bCNC in order to intercept trafic:

    interceptty -l /dev/ttyUSB0 /dev/ttyUSB23 | interceptty-nicedump

# Disclaimer
  The software is made available "AS IS". It seems quite stable, but it is in
  an early stage of development.  Hence there should be plenty of bugs not yet
  spotted. Please use/try it with care, I don't want to be liable if it causes
  any damage :)
