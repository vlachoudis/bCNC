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
DO NOT CHANGE THIS ONE
The first time you run bCNC will make a copy in the home
directory typically ${HOME}/.bCNC  or ~/.bCNC
Please edit the one in the home directory

# Features
- g-code sender
- workspace configuration (dialog for G54..G59 commands)
- auto leveling, Z-probing and auto leveling by altering the g-code during
  sending
- basic CAM features (profiling, drilling)
- user configurable database of materials, endmills, stock
- graphically moving and arranging objects
- g-code editor
- web pendant to be used via smart phones
- graphical display of the g-code, and workspace
- Goodies:
  - finger joint box generator

# Editor functions
- move, rotate objects
- reorder cutting sequence, move up/down blocks of gcode
- rounding digits
- inkscape gcodetools correction of annoying Z-lifting and lowering on every
  passage
- graphical block selection for reordering the cut process.

# TODO list
- graphical setup (for the moment it has to be written in the ~/.bCNC.ini file)
- manual
- tkinter canvas that I use for display can be a bit slow sometimes on very
  big g-code files.

# Disclaimer
  The software is made available "AS IS". It seems quite stable, but it is in
  an early stage of development.  Hence there should be plenty of bugs not yet
  spotted. Please use/try it with care, I don't want to be liable if it causes
  any damage :)
