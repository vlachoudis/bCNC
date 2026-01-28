#!/usr/bin/env python
"""
Test that DPI scaling is actually being applied
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bCNC'))

import DPI

# Create a root window
root = tk.Tk()
root.withdraw()

# Initialize DPI manager
dpi_mgr = DPI.init_dpi_manager(root)
detected = dpi_mgr.detect_system_dpi()

print("=" * 60)
print("DPI Scaling Verification")
print("=" * 60)
print(f"\nDetected scale: {detected}x")
print(f"Current scale: {dpi_mgr.get_scale_factor()}x")

print("\nScaling examples:")
print(f"  Font size -14 → {dpi_mgr.scale_font_size(-14)} (should be {-14 * detected})")
print(f"  Padding 5px → {dpi_mgr.scale(5)}px (should be {5 * detected})")
print(f"  Line width 2px → {dpi_mgr.scale_line_width(2)}px (should be {2 * detected})")
print(f"  Border 1px → {dpi_mgr.scale(1)}px (should be {1 * detected})")

if dpi_mgr.get_scale_factor() >= 3.0:
    print("\n✅ 3x scaling is active - UI should be properly sized!")
elif dpi_mgr.get_scale_factor() >= 2.0:
    print("\n⚠️  2x scaling is active - may still be small")
else:
    print("\n❌ 1x scaling - UI will be too small on HiDPI displays")

print("=" * 60)

root.destroy()
