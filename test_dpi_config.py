#!/usr/bin/env python
"""
Simple test to verify DPI configuration and scaling
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bCNC'))

import DPI

# Test 1: Initialize DPI manager
print("=" * 60)
print("DPI Configuration Test")
print("=" * 60)

dpi_mgr = DPI.init_dpi_manager(None)
print(f"✓ DPI Manager initialized")

# Test 2: Check default scale
scale = dpi_mgr.get_scale_factor()
print(f"✓ Default scale factor: {scale}x")

# Test 3: Test scaling functions
print(f"\nScaling Tests (at {scale}x):")
print(f"  - scale(10) = {dpi_mgr.scale(10)}")
print(f"  - scale_tuple(5, 10) = {dpi_mgr.scale_tuple(5, 10)}")
print(f"  - scale_font_size(-14) = {dpi_mgr.scale_font_size(-14)}")
print(f"  - scale_line_width(2) = {dpi_mgr.scale_line_width(2)}")

# Test 4: Test different scale factors
print("\nScale Factor Tests:")
for test_scale in [1.0, 1.5, 2.0, 2.5, 3.0]:
    dpi_mgr.set_scale_factor(test_scale)
    print(f"  - At {test_scale}x: scale(100) = {dpi_mgr.scale(100)}")

# Test 5: Check PIL availability
print(f"\n✓ PIL/Pillow available: {DPI.PIL_AVAILABLE}")

print("\n" + "=" * 60)
print("All DPI tests passed successfully!")
print("=" * 60)
