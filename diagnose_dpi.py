#!/usr/bin/env python
"""
Diagnose DPI detection issues
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bCNC'))

import DPI

# Create a root window
root = tk.Tk()
root.withdraw()  # Hide the window

print("=" * 60)
print("DPI Detection Diagnostics")
print("=" * 60)

# Try different DPI detection methods
print("\n1. winfo_fpixels('1i'):")
try:
    pixels_per_inch = root.winfo_fpixels('1i')
    print(f"   Pixels per inch: {pixels_per_inch}")
    print(f"   Scale factor: {pixels_per_inch / 96.0:.2f}x")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n2. winfo_screenwidth/height (physical):")
try:
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    screen_width_mm = root.winfo_screenmmwidth()
    screen_height_mm = root.winfo_screenmmheight()

    dpi_x = screen_width / (screen_width_mm / 25.4)
    dpi_y = screen_height / (screen_height_mm / 25.4)

    print(f"   Screen: {screen_width}x{screen_height} pixels")
    print(f"   Physical: {screen_width_mm}x{screen_height_mm} mm")
    print(f"   Calculated DPI X: {dpi_x:.1f}")
    print(f"   Calculated DPI Y: {dpi_y:.1f}")
    print(f"   Scale factor: {dpi_x / 96.0:.2f}x")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n3. tk scaling factor:")
try:
    scaling = root.tk.call('tk', 'scaling')
    print(f"   Tk scaling: {scaling}")
    print(f"   Scale factor: {scaling / 1.33:.2f}x")  # 1.33 is default
except Exception as e:
    print(f"   ERROR: {e}")

# Initialize DPI manager
print("\n4. DPI Manager detection:")
dpi_mgr = DPI.init_dpi_manager(root)
detected = dpi_mgr.detect_system_dpi()
print(f"   Detected scale: {detected}x")
print(f"   Current scale: {dpi_mgr.get_scale_factor()}x")

print("\n" + "=" * 60)
print("Recommendation:")
print("=" * 60)

if detected < 2.0:
    print("⚠️  DPI detection may not be working correctly for HiDPI displays")
    print("   Try manually setting scale in ~/.bCNC:")
    print("   [DPI]")
    print("   mode = manual")
    print("   scale = 3.0  # or 2.0, 2.5 depending on your display")
else:
    print(f"✓  DPI detection working: {detected}x scale")

root.destroy()
