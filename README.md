bCNC-HiDPI
==========

## HiDPI-Enhanced Fork

This is a fork of the excellent [bCNC project by Vasilis Vlachoudis](https://github.com/vlachoudis/bCNC) with comprehensive HiDPI/4K display support added. All credit for the original bCNC application goes to Vasilis Vlachoudis and the bCNC community.

**Upstream Project**: https://github.com/vlachoudis/bCNC

### What's New in bCNC-HiDPI

This fork adds comprehensive high-resolution display support:

- **Automatic HiDPI Detection**: Detects display DPI on startup across Linux, Windows, and macOS
- **Dynamic UI Scaling**: All UI elements, fonts, and widgets automatically scale based on DPI
- **Manual DPI Override**: Configure DPI manually in settings if auto-detection doesn't work perfectly
- **Settings Persistence**: DPI preferences are saved and restored between sessions
- **4K Display Support**: Properly handles 4K and other high-resolution displays
- **Comprehensive Testing**: Includes unit tests for DPI detection and scaling functionality

The HiDPI implementation is designed to be non-invasive and maintains full compatibility with standard displays while providing crisp, properly-scaled interfaces on high-resolution displays.

### About bCNC

GrblHAL (formerly GRBL) CNC command sender, autoleveler, g-code editor, digitizer, CAM
and swiss army knife for all your CNC needs.

An advanced fully featured g-code sender for grblHAL (formerly GRBL). bCNC is a cross platform program (Windows, Linux, Mac) written in python. The sender is robust and fast able to work nicely with old or slow hardware like [Raspberry Pi](http://www.openbuilds.com/threads/bcnc-and-the-raspberry-pi.3038/) (As it was validated by the GRBL maintainer on heavy testing).

All pull requests that do change GUI should have attached screenshots of GUI before and after the changes.
Please note that all pull requests should pass the Travis-CI build in order to get merged.https://github.com/Harvie/cnc-simulator
Most pull requests should also pass CodeFactor checks if there is not good reason for failure.
Before making pull request, please test your code on ~~both python2 and~~ python3.

![bCNC screenshot](https://raw.githubusercontent.com/vlachoudis/bCNC/doc/Screenshots/bCNC.png)

# Installation (HiDPI Fork)

## IMPORTANT: Remove Previous bCNC Installation First

If you have the upstream bCNC installed, you **must uninstall it first** to avoid conflicts:

    pip uninstall bCNC

For detailed installation instructions including troubleshooting, see [installing-bCNC-HiDPI.md](installing-bCNC-HiDPI.md).

## Quick Install

Clone this repository and install:

    git clone https://github.com/Monotoba/bCNC-HiDPI.git
    cd bCNC-HiDPI
    pip install .

Or install directly from GitHub:

    pip install git+https://github.com/Monotoba/bCNC-HiDPI.git

## Launch bCNC

    python -m bCNC

or simply:

    bCNC

## HiDPI Configuration

The application will automatically detect your display DPI. To manually adjust:

1. Launch bCNC
2. Go to `CAM` → `Config/Controller` → `GUI` tab
3. Find the `DPI Settings` section
4. Toggle "Auto-detect DPI" or set manual DPI value (96 for standard, 144/192 for HiDPI/4K)

## System Requirements

- Python 3.8 or newer (Python 2 is no longer supported)
- Tkinter (usually included with Python, see manual installation below if needed)
- Works on Linux, Windows, and macOS
- Optimized for both standard and HiDPI displays

## Upstream Project

For general bCNC documentation, tutorials, and community support, please visit:
- **Original bCNC**: https://github.com/vlachoudis/bCNC
- **bCNC Wiki**: https://github.com/vlachoudis/bCNC/wiki
- **PyPI** (upstream): https://pypi.org/project/bCNC/

# Installation (manual)
You will need the following packages to run bCNC
- tkinter the graphical toolkit for python
  Depending your python/OS it can either be already installed,
  or under the names tkinter, python3-tkinter, python-tk
- pyserial or under the name python-serial, python-pyserial
- numpy
- Optionally:
- python-imaging-tk: the PIL libraries for autolevel height map
- python-opencv: for webcam streaming on web pendant
- scipy: for 100 times faster 3D mesh slicing

Expand the directory or download it from github
and run the bCNC command

# Installation (Linux package maintainers)
- Copy `bCNC` subdirectory of this repo to `/usr/lib/python3.x/site-packages/`
- Launch using `python -m bCNC` or install bCNC.sh to /usr/bin
- Alternatively you can fetch the bCNC Python package using pip when building Linux package
  - refer to your distro, eg.: https://wiki.archlinux.org/index.php/Python_package_guidelines
  - Py2deb to build Debian package from Python package: https://pypi.org/project/py2deb/

# Installation (Compile to Windows .exe)

Note that you might probably find some precompiled .exe files on github "releases" page:
https://github.com/vlachoudis/bCNC/releases
But they might not be up to date.

This is basic example of how to compile bCNC to .exe file.
(given that you have working bCNC in the first place, eg. using `pip install bCNC`).
Go to the directory where is your bCNC installed and do the following:

    pip install pyinstaller
    pyinstaller --onefile --distpath . --hidden-import tkinter --paths lib;plugins;controllers --icon bCNC.ico --name bCNC __main__.py

This will take a minute or two. But in the end it should create `bCNC.exe`.
Also note that there is `make-exe.bat` file which will do just that for you.
This will also create rather large "build" subdirectory.
That is solely for caching purposes and you should delete it before redistributing!

If you are going to report bugs in .exe version of bCNC,
please check first if that bug occurs even when running directly in python (without .exe build).

# IMPORTANT! Motion controller configuration
- We strongly recommend you to use 32b microcontroller with FluidNC https://github.com/bdring/FluidNC http://wiki.fluidnc.com firmware for the new machine builds.
- In case you are using grblHAL https://github.com/grblHAL (Original GRBL firmware is still supported, but it is currently reaching the end-of-life due to limitations of 8b microcontrollers)
- GRBL should be configured to use **MPos** rather than **Wpos**. This means that `$10=` should be set to odd number. As of GRBL 1.1 we recommend setting `$10=3`. If you have troubles communicating with your machine, you can try to set failsafe value `$10=1`.
- CADs, bCNC and GRBL all work in millimeters by default. Make sure that `$13=0` is set in GRBL, if you experience strange behavior. (unless you've configured your CAD and bCNC to use inches)
- Before filing bug please make sure you use latest stable official release of GRBL. Older and unofficial releases might work, but we frequently see cases where they don't. So please upgrade firmware in your Arduinos to reasonably recent version if you can.
- Also read about all possible GRBL settings and make sure your setup is correct: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Configuration
- GrblHAL also has "Compatibility level" settings which have to be correctly configured during firmware compilation: https://github.com/grblHAL/core/wiki/Compatibility-level

# Configuration
You can modify most of the parameters from the "CAM -> Config/Controller" page.
You can also enable (up to) 6-axis mode in Config section,
but bCNC restart is required for changes to take place.
Only the changes/differences from the default configuration
file will be saved in your home directory ${HOME}/.bCNC  or ~/.bCNC

The default configuration is stored on bCNC.ini in the
installation directory.

*PLEASE DO NOT CHANGE THIS FILE, IT'S GOING TO BE OVERWRITTEN ON EACH UPGRADE OF BCNC*

# Features:
- simple and intuitive interface for small screens
- 3-axis and 6-axis GUI modes
- import/export **g-code**, **dxf** and **svg** files
- 3D mesh slicing **stl** and **ply** files
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
  - create g-code by jogging and recording points (can even use camera for this)
  - **manual tool change** expansion and automatic tool length probing
  - **canned cycles** expansion
- Various Tools:
  - user configurable database of materials, endmills, stock
  - properties database of materials, stock, end mills etc..
  - basic **CAM** features (profiling, pocketing, drilling, flat/helical/ramp cutting, thread milling, cutout tabs, drag knife)
  - User g-code plugins:
    - bowl generator
    - finger joint box generator
    - simple spur gear generator
    - spirograph generator
    - surface flatten
    - play melody from MIDI file using stepper motor frequency
    - ...
- G-Code editor and display
    - graphical display of the g-code, and workspace
    - graphically moving and editing g-code
    - reordering code and **rapid motion optimization**
    - moving, rotating, mirroring the g-code
- Web pendant to be used via smart phones

# Contributing Back to Upstream

This fork's HiDPI improvements are designed to be contributed back to the upstream bCNC project. If you'd like to help get these changes merged:

1. Test the HiDPI features on your system and report any issues
2. Provide feedback on the implementation
3. Help with additional testing on different platforms and display configurations

The changes are structured to be non-invasive and maintain backward compatibility with existing installations.

# Acknowledgements

**Huge thanks to Vasilis Vlachoudis and all bCNC contributors** for creating and maintaining this excellent CNC control software. This fork simply adds HiDPI support on top of their outstanding work.

All core functionality, features, and the overall design of bCNC are courtesy of the upstream project and its community.

# Debugging
You can log serial communication by changing the port to something like:

    spy:///dev/ttyUSB0?file=serial_log.txt&raw
    spy://COM1?file=serial_log.txt&raw

If a file isn't specified, the log is written to stderr.
The 'raw' option outputs the data directly, instead of creating a hex dump.
Further documentation is available at: https://pyserial.readthedocs.io/en/latest/url_handlers.html#spy

# Technical Details: HiDPI Implementation

The HiDPI support is implemented through a centralized DPI management system:

## Modified Files

### Core DPI System
- `bCNC/DPI.py` - Core DPI detection and scaling logic with platform-specific detection
- `bCNC/Utils.py` - Integration of DPI system with configuration management
- `bCNC/bmain.py` - Early DPI initialization during application startup

### UI Components
- `bCNC/lib/tkExtra.py` - DPI-aware widget scaling
- `bCNC/CNCCanvas.py` - Canvas scaling for proper rendering
- `bCNC/CNCRibbon.py` - Ribbon UI scaling
- All page files in `bCNC/` - Individual page widgets updated for DPI awareness

### Configuration & Testing
- Configuration UI in the GUI tab for manual DPI adjustment
- Comprehensive unit tests in `tests/test_dpi.py`
- Test configuration UI in `tests/test_dpi_config.py`

## How It Works

1. **Platform Detection**: Detects display DPI using platform-specific APIs (X11 on Linux, Windows API, macOS)
2. **Scaling Factor**: Calculates scaling factor relative to standard 96 DPI
3. **Widget Scaling**: Applies scaling to fonts, button sizes, paddings, and all UI elements
4. **Configuration**: Saves DPI preferences to `~/.bCNC` configuration file
5. **Override Capability**: Users can manually set DPI if auto-detection is incorrect

The implementation is designed to be non-invasive and easily maintainable for future updates.

# Disclaimer
  The software is made available "AS IS". It seems quite stable, but it is in
  an early stage of development.  Hence there should be plenty of bugs not yet
  spotted. Please use/try it with care, I don't want to be liable if it causes
  any damage :)

# See also
  - G-code simulators that you can use to independently cross-check g-code generated by bCNC or verify any g-code files in case you have troubles running them.
    - https://harvie.github.io/cnc-simulator ([github](https://github.com/Harvie/cnc-simulator))
    - https://camotics.org
    - https://freecad.org
