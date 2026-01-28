# Installing bCNC with HiDPI Support

This guide provides detailed instructions for uninstalling the standard version of bCNC and installing this custom version with HiDPI (High Dots Per Inch) display support.

## IMPORTANT: Remove Previous bCNC Installations First

**Before proceeding with this installation, you MUST remove any existing installations of the upstream (original) bCNC software.** This custom HiDPI version is a fork of the original bCNC project, and having both installed simultaneously will cause conflicts and unexpected behavior.

### Why Remove the Upstream Version?

The upstream bCNC (from https://github.com/vlachoudis/bCNC) and this HiDPI-enhanced fork share the same module names and installation paths. Installing this version without removing the original will result in:
- Python import conflicts
- Unpredictable behavior as Python may load modules from either version
- Configuration file conflicts
- Command-line launcher conflicts

### Quick Check: Is bCNC Already Installed?

Run these commands to check if bCNC is already installed:

```bash
# Check if bCNC module exists
python -m bCNC --version 2>/dev/null && echo "bCNC is installed" || echo "bCNC not found"

# Check if bCNC command exists
which bCNC 2>/dev/null && echo "bCNC command found" || echo "bCNC command not found"

# Check with pip
pip show bCNC
```

If any of these commands indicate bCNC is installed, **proceed to Step 1 below to remove it completely** before installing this HiDPI version.

## Prerequisites

### System Requirements
- **Python**: Version 3.8 or newer (required)
- **Operating System**: Linux, Windows, or macOS
- **Display**: Works on both standard and HiDPI/4K displays

### Required Packages
The following packages will be installed automatically:
- `tkinter` - Python GUI toolkit (may need manual installation on some systems)
- `pyserial` - Serial communication for CNC controllers
- `numpy` - Numerical computing library
- `Pillow` - Image processing library
- `opencv-python` - Computer vision library (optional on ARM platforms)
- `svgelements` - SVG file support
- `shxparser` - SHX font parser
- `tkinter-gl` - OpenGL support for tkinter

## Step 1: Uninstall Existing bCNC

Before installing the custom HiDPI version, you need to remove any existing bCNC installation to avoid conflicts.

### Option A: If installed via pip

```bash
pip uninstall bCNC
```

If you're unsure which pip is being used, try:

```bash
pip3 uninstall bCNC
python -m pip uninstall bCNC
python3 -m pip uninstall bCNC
```

### Option B: If installed system-wide (Linux)

Check if bCNC is installed as a system package:

```bash
# For Debian/Ubuntu-based systems
dpkg -l | grep bcnc
sudo apt remove bcnc

# For Arch-based systems
pacman -Q | grep bcnc
sudo pacman -R bcnc

# For Fedora/RedHat-based systems
rpm -qa | grep bcnc
sudo dnf remove bcnc
```

### Option C: If installed manually

If bCNC was installed by copying files to a system directory, you'll need to remove:
- `/usr/lib/python3.x/site-packages/bCNC/` directory
- `/usr/bin/bCNC` or `/usr/bin/bCNC.sh` script

### Verify Uninstallation

Confirm bCNC is uninstalled:

```bash
python -m bCNC
# Should show: No module named 'bCNC'

which bCNC
# Should show: no bCNC in ($PATH)
```

## Step 2: Install Custom HiDPI Version

Navigate to the directory containing this README (where you cloned or extracted the custom bCNC):

```bash
cd /home/randy/projects/python-3/bCNC-master
```

### Install in Development Mode (Recommended for Testing)

This method allows you to make changes to the code and see them immediately without reinstalling:

```bash
pip install -e .
```

Or with pip3:

```bash
pip3 install -e .
```

### Install as a Regular Package

This method installs bCNC like any other Python package:

```bash
pip install .
```

Or with pip3:

```bash
pip3 install .
```

### Special Considerations

#### On Linux without tkinter:
If you get a "No module named 'tkinter'" error, install tkinter first:

```bash
# Debian/Ubuntu
sudo apt install python3-tk

# Fedora/RedHat
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

#### On ARM platforms (Raspberry Pi, etc.):
OpenCV may not install automatically. Install it separately if needed:

```bash
sudo apt install python3-opencv
```

#### On Windows:
Use `py` instead of `python`:

```bash
py -m pip install .
```

## Step 3: Verify Installation

Check that bCNC is installed correctly:

```bash
python -m bCNC --help
```

Or simply:

```bash
bCNC --help
```

Check the installed version:

```bash
pip show bCNC
```

You should see version 0.9.16 and the location where it's installed.

## Step 4: Launch bCNC

### From the Command Line

```bash
python -m bCNC
```

Or using the installed command:

```bash
bCNC
```

### HiDPI Features

The custom version includes automatic HiDPI detection and scaling:

1. **Automatic Detection**: On startup, bCNC detects if you're using a HiDPI display
2. **UI Scaling**: The interface automatically scales appropriately
3. **Manual Configuration**: You can adjust DPI settings in:
   - Menu: `CAM` → `Config/Controller` → `GUI` tab → `DPI Settings` section
   - Settings include:
     - Auto-detect DPI (recommended)
     - Manual DPI override
     - Widget size overrides
     - Font size adjustments

### Configuration File

Your configuration is stored in:
- **Linux/Mac**: `~/.bCNC` or `${HOME}/.bCNC`
- **Windows**: `%USERPROFILE%\.bCNC`

The HiDPI settings are automatically saved and restored between sessions.

## Step 5: Testing HiDPI Features

To verify HiDPI support is working:

1. **Check Auto-Detection**:
   - Launch bCNC
   - Check the console output for DPI detection messages
   - The UI should appear crisp and properly scaled on HiDPI displays

2. **Manual Testing**:
   - Go to `CAM` → `Config/Controller` → `GUI` tab
   - Find the `DPI Settings` section
   - Toggle "Auto-detect DPI" and observe changes
   - Try different manual DPI values (96, 144, 192)

3. **Compare**:
   - Standard displays: Should detect ~96 DPI
   - HiDPI displays: Should detect 144+ DPI
   - 4K displays: May detect 192+ DPI

## Troubleshooting

### Issue: "No module named 'bCNC'"

**Solution**: The installation didn't complete or Python can't find it.

```bash
# Try reinstalling
pip install --force-reinstall .

# Or check which Python is being used
which python
which pip
```

### Issue: "No module named 'tkinter'"

**Solution**: Install tkinter using your system package manager (see Step 2).

### Issue: UI appears tiny/huge on HiDPI display

**Solution**:

1. Check auto-detect is enabled in DPI settings
2. Restart bCNC after changing DPI settings
3. Manually override DPI if auto-detection fails:
   - `CAM` → `Config/Controller` → `GUI` tab → Set DPI manually to 144 or 192

### Issue: Permission errors during installation

**Solution**:

```bash
# Install for current user only
pip install --user .

# Or use sudo (not recommended)
sudo pip install .
```

### Issue: Old version still running

**Solution**:

```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall
pip install --force-reinstall --no-cache-dir .
```

### Issue: Serial port access denied (Linux)

**Solution**: Add your user to the dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and log back in for changes to take effect
```

## Development Mode

If you want to actively develop or modify bCNC:

1. **Install in editable mode**:
   ```bash
   pip install -e .
   ```

2. **Run directly from source**:
   ```bash
   cd /home/randy/projects/python-3/bCNC-master
   python -m bCNC
   ```

3. **Run tests**:
   ```bash
   pytest tests/
   ```

## Uninstalling the Custom Version

To uninstall this custom HiDPI version:

```bash
pip uninstall bCNC
```

Your configuration files in `~/.bCNC` will be preserved unless you manually delete them.

## Additional Resources

- **Original bCNC Project**: https://github.com/vlachoudis/bCNC
- **bCNC Wiki**: https://github.com/vlachoudis/bCNC/wiki
- **GRBL Configuration**: https://github.com/gnea/grbl/wiki/Grbl-v1.1-Configuration
- **FluidNC**: https://github.com/bdring/FluidNC

## What's New in the HiDPI Version

This custom version includes:

- **Automatic HiDPI Detection**: Detects display DPI on startup
- **Dynamic UI Scaling**: Automatically scales UI elements based on DPI
- **Manual DPI Override**: Configure DPI manually if auto-detection doesn't work
- **Per-Platform Support**: Works correctly on Linux, Windows, and macOS HiDPI displays
- **Settings Persistence**: DPI settings are saved and restored between sessions
- **Comprehensive Testing**: Includes unit tests for DPI detection and scaling

Key files modified:
- `bCNC/DPI.py` - Core DPI detection and scaling logic
- `bCNC/Utils.py` - Integration with DPI system
- `bCNC/bmain.py` - Early DPI initialization
- `bCNC/lib/tkExtra.py` - UI widget DPI scaling

## Support

If you encounter issues specific to the HiDPI implementation, check:
1. Console output for DPI detection messages
2. DPI settings in the GUI configuration panel
3. Your display's actual DPI (can vary by platform)

For general bCNC issues, refer to the official documentation and community resources.
