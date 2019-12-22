# bCNC changelog

There are too much commits, so i've created this brief overview of new features in bCNC.

## 0.9.15

- New features
  - Python 3 is (mostly) supported now #228
  - Can load SVG files (~only paths without transformations~ improved by tatarize, see wiki) #902 #1312
  - Can slice 3D meshes in STL and PLY formats (with minor limitations) #901
  - Can export 3D scan (autolevel probe) data in XYZ format suitable for meshlab poisson surface reconstruction
  - Support for helical and ramp cutting #590
  - New style of tabs implemented using "islands" with support for arbitrary shapes and pockets #220
  - Interactive value entry is now possible in g-code scripting #1256
  - DRO entry can now handle math formulas like: `sqrt(safe)+1`, `sin(pi**2)` or `3.175/2` #789
  - Drag Knife postprocessor and simulator plugin #975
  - Jog digitizer to create drawing by recording points while jogging #929
  - ArcFit plugin can interpolate lots of small segments using one long line/arc #921
  - DrillMark plugin to laser engrave markers for manual drilling #1128
  - More plugins: find center of path, close path, flatten path, scaling, randomize...
  - Start cycle can now be triggered by hardware button connected to arduino #885
- Improvements
  - Restructured UI #1057 and more
  - Better autodetection of serial ports (with device names, ids and without restarting bCNC)
  - Disabled blocks are commented-out in exported g-code #767
  - Lots of small improvements and experimental/development features like "trochoidal" (see git)
  - Added button to activate GRBL sleep mode (= disable motors) #1099
  - Added button to trigger GRBL door alarm
  - Added button to scan autoleveling margins (to see what will be probed)
  - Added some usefull jog buttons
  - Added framework to show help text and images for each plugin #806
- Bug Fixes
  - Proper path direction detection and climb/conventional support #881
  - Proper handling of G91 when moving/rotating g-code #915
- Development and release engineering
  - Created PyPI package for bCNC #964
    - This means bCNC now installs as `pip install bCNC` and launches as `python -m bCNC` (see wiki!)
  - Added .bat script to build .exe package of bCNC #437
  - Support for individual motion controllers is now in form of separate plugins #1020
  - Added some basic Travis-CI tests #1117
- New bugs
  - We've hidden few secret bugs in our code as a challenge for you to find and report :-)

## 0.9.14

- Currently there is no changelog for 0.9.14 and older releases
- You can still find some info in github issues and history https://github.com/vlachoudis/bCNC/commits/master
