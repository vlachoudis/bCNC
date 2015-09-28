bCNC
====

GRBL CNC command sender, autoleveler and g-code editor

![bCNC screenshot](https://raw.githubusercontent.com/vlachoudis/bCNC/doc/Screenshots/bCNC.png)

# Installation
You will need the following packages to run bCNC
- tkinter the graphical toolkit for python
  Depending your python/OS it can either be already installed,
  or under the names tkinter, python-tkinter, python-tk
- pyserial or under the name python-serial, python-pyserial

Expand the directory or download it from github
and run the bCNC command

# Configuration
Currently the configuration is only via the bCNC.ini file.
There is a global ini file in the installation directory.

*DO NOT CHANGE THIS ONE*

The first time you run bCNC will make a copy in the home
directory typically ${HOME}/.bCNC  or ~/.bCNC
Please edit the one in the home directory

# Features
- simple interface for small screens
- fast g-code sender (works nicely on RPi and old hardware)
- workspace configuration (dialog for G54..G59 commands)
- user configurable buttons
- g-code function evaluation with run time expansion
- Easy probing:
  - simple probing
  - center finder with a probing ring
  - auto leveling, Z-probing and auto leveling by altering the g-code during
    sending.
  - height color map display
  - manual tool change expansion and automatic tool length probing
- Various Tools:
  - user configurable database of materials, endmills, stock
  - properties database of materials, stock, end mills etc..
  - basic CAM features (profiling, drilling)
  - User g-code plugins:
    - bowl generator
    - finger joint box generator
    - simple spur gear generator
    - spirograph generator
    - ...
- G-Code editor and display
    - graphical display of the g-code, and workspace
    - graphically moving
    - reordering code and rapid motion optimization
    - moving, rotating, mirroring the g-code
- web pendant to be used via smart phones

# Disclaimer
  The software is made available "AS IS". It seems quite stable, but it is in
  an early stage of development.  Hence there should be plenty of bugs not yet
  spotted. Please use/try it with care, I don't want to be liable if it causes
  any damage :)
