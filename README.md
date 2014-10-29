bCNC
====

GRBL CNC command sender, autoleveler and g-code editor

![bCNC screenshot](https://raw.github.com/vlachoudis/bCNC/trunk/bCNC.png)

Features:
=========
- g-code sender
- workspace configuration (dialog for G54..G59 commands)
- auto leveling, Z-probing and auto leveling by altering the g-code during
  sending
- g-code editor
- web pendant to be used via smart phones
- graphics display of the g-code, and workspace

Editor functions:
=================
- syntax highlighting
- move/translate of g-code
- rounding digits
- inkscape gcodetools correction of annoying Z-lifting and lowering on every
  passage
- Graphical block selection for reordering the cut process.

ToDo list:
==========
- graphics setup (for the moment it has to be written in the ~/.bCNC.ini file)
- manual
- editor rotation of g-code
- move up/down blocks of gcode
- tkinter canvas that I use for display can a bit slow sometimes on very big
  g-code files.

Disclaimer:
===========
  The software is made available "AS IS". It seems quite stable, but it is in
  early stage of development, hence there should be plenty of bugs not spotted
  yet. Please use/try it with care, i don't want to be liable if it causes any
  damage :)

