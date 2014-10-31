bCNC
====

GRBL CNC command sender, autoleveler and g-code editor

![bCNC screenshot](https://github.com/vlachoudis/bCNC/blob/master/screenshots/bCNC.png)

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
Please edit the on in the home directory

# Features
- g-code sender
- workspace configuration (dialog for G54..G59 commands)
- auto leveling, Z-probing and auto leveling by altering the g-code during
  sending
- g-code editor
- web pendant to be used via smart phones
- graphics display of the g-code, and workspace

# Editor functions
- syntax highlighting
- move/translate of g-code
- rounding digits
- inkscape gcodetools correction of annoying Z-lifting and lowering on every
  passage
- Graphical block selection for reordering the cut process.

# TODO list
- graphics setup (for the moment it has to be written in the ~/.bCNC.ini file)
- manual
- editor rotation of g-code
- move up/down blocks of gcode
- tkinter canvas that I use for display can a bit slow sometimes on very big
  g-code files.

# Disclaimer
  The software is made available "AS IS". It seems quite stable, but it is in
  early stage of development, hence there should be plenty of bugs not spotted
  yet. Please use/try it with care, i don't want to be liable if it causes any
  damage :)

