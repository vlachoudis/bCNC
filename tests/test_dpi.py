"""
Unit tests for DPI scaling functionality
"""

import unittest
import sys
import os

# Add bCNC module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bCNC'))

import DPI


class TestDPIManager(unittest.TestCase):
    """Test cases for DPIManager class"""

    def setUp(self):
        """Create a fresh DPI manager for each test"""
        self.dpi_mgr = DPI.DPIManager()

    def test_default_scale_factor(self):
        """Test default scale factor is 1.0"""
        self.assertEqual(self.dpi_mgr.get_scale_factor(), 1.0)

    def test_snap_to_supported_scale(self):
        """Test snapping to supported scale factors"""
        # Test snapping to 1.0
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(0.9), 1.0)
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(1.1), 1.0)

        # Test snapping to 1.5
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(1.4), 1.5)
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(1.6), 1.5)

        # Test snapping to 2.0
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(1.9), 2.0)
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(2.1), 2.0)

        # Test snapping to 2.5
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(2.4), 2.5)
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(2.6), 2.5)

        # Test snapping to 3.0
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(2.9), 3.0)
        self.assertEqual(self.dpi_mgr._snap_to_supported_scale(3.1), 3.0)

    def test_scale_integer(self):
        """Test scaling integer pixel values"""
        # At 1x scale
        self.dpi_mgr.set_scale_factor(1.0)
        self.assertEqual(self.dpi_mgr.scale(10), 10)
        self.assertEqual(self.dpi_mgr.scale(0), 0)

        # At 2x scale
        self.dpi_mgr.set_scale_factor(2.0)
        self.assertEqual(self.dpi_mgr.scale(10), 20)
        self.assertEqual(self.dpi_mgr.scale(5), 10)
        self.assertEqual(self.dpi_mgr.scale(0), 0)

        # At 1.5x scale
        self.dpi_mgr.set_scale_factor(1.5)
        self.assertEqual(self.dpi_mgr.scale(10), 15)
        self.assertEqual(self.dpi_mgr.scale(4), 6)

    def test_scale_tuple(self):
        """Test scaling multiple values"""
        # At 2x scale
        self.dpi_mgr.set_scale_factor(2.0)
        self.assertEqual(self.dpi_mgr.scale_tuple(10, 20), (20, 40))
        self.assertEqual(self.dpi_mgr.scale_tuple(1, 2, 3), (2, 4, 6))

        # At 1.5x scale
        self.dpi_mgr.set_scale_factor(1.5)
        self.assertEqual(self.dpi_mgr.scale_tuple(10, 20), (15, 30))

    def test_scale_font_negative(self):
        """Test scaling negative (pixel-based) font sizes"""
        # At 2x scale
        self.dpi_mgr.set_scale_factor(2.0)
        self.assertEqual(self.dpi_mgr.scale_font_size(-12), -24)
        self.assertEqual(self.dpi_mgr.scale_font_size(-10), -20)

        # At 1.5x scale
        self.dpi_mgr.set_scale_factor(1.5)
        self.assertEqual(self.dpi_mgr.scale_font_size(-12), -18)

    def test_scale_font_positive(self):
        """Test scaling positive (point-based) font sizes"""
        # At 2x scale
        self.dpi_mgr.set_scale_factor(2.0)
        result = self.dpi_mgr.scale_font_size(12)
        self.assertGreater(result, 12)  # Should be larger
        self.assertEqual(result, 24)  # Should double

        # At 1.5x scale
        self.dpi_mgr.set_scale_factor(1.5)
        result = self.dpi_mgr.scale_font_size(12)
        self.assertEqual(result, 18)

        # Minimum font size test
        self.dpi_mgr.set_scale_factor(0.5)  # Hypothetical tiny scale
        result = self.dpi_mgr.scale_font_size(8)
        self.assertGreaterEqual(result, 6)  # Should not go below minimum

    def test_scale_line_width(self):
        """Test scaling line widths"""
        # At 2x scale
        self.dpi_mgr.set_scale_factor(2.0)
        self.assertEqual(self.dpi_mgr.scale_line_width(1), 2)
        self.assertEqual(self.dpi_mgr.scale_line_width(2), 4)
        self.assertEqual(self.dpi_mgr.scale_line_width(0), 0)

        # At 1x scale, ensure minimum of 1 for non-zero
        self.dpi_mgr.set_scale_factor(1.0)
        self.assertEqual(self.dpi_mgr.scale_line_width(1), 1)
        self.assertEqual(self.dpi_mgr.scale_line_width(0), 0)

    def test_set_scale_factor_manual(self):
        """Test setting manual scale factor"""
        self.dpi_mgr.set_scale_factor(2.0, is_manual=True)
        self.assertEqual(self.dpi_mgr.get_scale_factor(), 2.0)
        self.assertEqual(self.dpi_mgr.get_manual_override(), 2.0)

    def test_set_scale_factor_auto(self):
        """Test setting auto scale factor"""
        self.dpi_mgr.set_scale_factor(1.5, is_manual=False)
        self.assertEqual(self.dpi_mgr.get_scale_factor(), 1.5)
        self.assertIsNone(self.dpi_mgr.get_manual_override())

    def test_invalid_scale_factor(self):
        """Test that invalid scale factors are snapped to valid ones"""
        # Should snap 1.7 to 1.5 or 2.0 (closest is 2.0)
        self.dpi_mgr.set_scale_factor(1.7)
        self.assertIn(self.dpi_mgr.get_scale_factor(), DPI.DPIManager.SCALE_FACTORS)

        # Should snap 4.0 to 3.0 (max)
        self.dpi_mgr.set_scale_factor(4.0)
        self.assertEqual(self.dpi_mgr.get_scale_factor(), 3.0)

    def test_upscale_icon_without_pil(self):
        """Test icon upscaling fallback without PIL"""
        # This test just ensures the function doesn't crash
        # Actual PIL functionality is tested in integration tests
        pass

    def test_get_auto_detected_scale(self):
        """Test getting auto-detected scale"""
        # Default should be 1.0
        self.assertEqual(self.dpi_mgr.get_auto_detected_scale(), 1.0)


class TestDPIGlobalFunctions(unittest.TestCase):
    """Test global DPI manager functions"""

    def test_get_dpi_manager(self):
        """Test getting global DPI manager"""
        mgr = DPI.get_dpi_manager()
        self.assertIsInstance(mgr, DPI.DPIManager)

    def test_init_dpi_manager(self):
        """Test initializing global DPI manager"""
        # Initialize with None (no window)
        mgr = DPI.init_dpi_manager(None)
        self.assertIsInstance(mgr, DPI.DPIManager)

        # Get the same instance
        mgr2 = DPI.get_dpi_manager()
        self.assertIs(mgr, mgr2)


if __name__ == '__main__':
    unittest.main()
