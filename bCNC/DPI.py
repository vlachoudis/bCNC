"""
DPI Management Module for bCNC

Provides centralized DPI scaling support for HiDPI displays.
Handles auto-detection, manual override, and scaling of all UI elements.
"""

import sys
import logging

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL/Pillow not available. Icon scaling quality will be reduced.")


class DPIManager:
    """Centralized DPI scaling management for bCNC"""

    # Supported scaling factors
    SCALE_FACTORS = [1.0, 1.5, 2.0, 2.5, 3.0]

    # Standard DPI baseline (96 DPI is standard for most systems)
    STANDARD_DPI = 96.0

    def __init__(self, root_window=None):
        """Initialize DPI manager

        Args:
            root_window: Tkinter root window for DPI detection
        """
        self._scale_factor = 1.0
        self._auto_detected = 1.0
        self._manual_override = None
        self._root = root_window
        self._dpi = self.STANDARD_DPI

    def detect_system_dpi(self):
        """Auto-detect system DPI using Tkinter methods and environment variables

        Returns:
            float: Detected scale factor
        """
        if not self._root:
            logging.warning("No root window available for DPI detection, defaulting to 1x")
            self._auto_detected = 1.0
            return 1.0

        try:
            # Method 1: Use screen resolution heuristics (most reliable for HiDPI)
            scale_from_resolution = self._detect_from_resolution()

            # Method 2: Check environment variables
            scale_from_env = self._detect_from_environment()

            # Use the higher of the two methods for HiDPI displays
            detected_scale = max(scale_from_resolution, scale_from_env)

            if detected_scale > 1.0:
                logging.info(f"Detected scale: {detected_scale}x (resolution={scale_from_resolution}x, env={scale_from_env}x)")
                self._auto_detected = detected_scale
                self._scale_factor = detected_scale  # Apply it immediately
                return detected_scale

            # Method 3: Try to get DPI from Tkinter
            # winfo_fpixels('1i') returns the number of pixels in 1 inch
            pixels_per_inch = self._root.winfo_fpixels('1i')
            self._dpi = float(pixels_per_inch)

            # Calculate scale factor relative to standard 96 DPI
            scale = self._dpi / self.STANDARD_DPI

            # Snap to nearest supported scale factor
            scale = self._snap_to_supported_scale(scale)

            self._auto_detected = scale
            logging.info(f"Detected DPI: {self._dpi:.1f}, scale factor: {scale}x")

            return scale

        except Exception as e:
            logging.warning(f"DPI detection failed: {e}, defaulting to 1x")
            self._auto_detected = 1.0
            return 1.0

    def _detect_from_environment(self):
        """Detect scale from environment variables

        Returns:
            float: Scale factor from environment, or 1.0 if not found
        """
        import os

        # Check common environment variables
        env_vars = [
            'GDK_SCALE',        # GTK/GNOME
            'GDK_DPI_SCALE',    # GTK/GNOME
            'QT_SCALE_FACTOR',  # Qt
            'ELM_SCALE',        # Elementary
        ]

        for var in env_vars:
            value = os.environ.get(var)
            if value:
                try:
                    scale = float(value)
                    if scale >= 1.0:
                        return self._snap_to_supported_scale(scale)
                except ValueError:
                    continue

        return 1.0

    def _detect_from_resolution(self):
        """Detect scale from screen resolution heuristics

        Returns:
            float: Estimated scale factor based on resolution
        """
        try:
            screen_width = self._root.winfo_screenwidth()
            screen_height = self._root.winfo_screenheight()

            # HiDPI display heuristics based on common resolutions
            # 4K displays (3840x2160, 3840x2400, 4096x2304)
            if screen_width >= 3840 or screen_height >= 2160:
                return 3.0  # 4K typically needs 3x or higher

            # QHD/WQHD displays (2560x1440, 3440x1440)
            elif screen_width >= 2560 or screen_height >= 1440:
                return 2.0  # QHD typically needs 2x

            # Full HD+ displays (1920x1200, 2560x1080)
            elif screen_width >= 1920 or screen_height >= 1200:
                return 1.5  # Some Full HD displays benefit from 1.5x

            return 1.0

        except Exception as e:
            logging.warning(f"Resolution detection failed: {e}")
            return 1.0

    def _snap_to_supported_scale(self, scale):
        """Snap a scale value to the nearest supported scale factor

        Args:
            scale: Raw scale value

        Returns:
            float: Nearest supported scale factor
        """
        # Find the closest supported scale factor
        closest = min(self.SCALE_FACTORS, key=lambda x: abs(x - scale))
        return closest

    def set_scale_factor(self, scale, is_manual=False):
        """Set scaling factor

        Args:
            scale: Scale factor (1.0, 1.5, 2.0, 2.5, 3.0)
            is_manual: If True, this is a manual override
        """
        # Validate scale factor
        if scale not in self.SCALE_FACTORS:
            logging.warning(f"Invalid scale factor {scale}, snapping to nearest supported value")
            scale = self._snap_to_supported_scale(scale)

        if is_manual:
            self._manual_override = scale
            self._scale_factor = scale
            logging.info(f"Manual scale factor set to {scale}x")
        else:
            self._scale_factor = scale
            logging.info(f"Scale factor set to {scale}x")

    def get_scale_factor(self):
        """Get current active scale factor

        Returns:
            float: Current scale factor
        """
        return self._scale_factor

    def get_auto_detected_scale(self):
        """Get auto-detected scale factor

        Returns:
            float: Auto-detected scale factor
        """
        return self._auto_detected

    def get_manual_override(self):
        """Get manual override scale factor

        Returns:
            float or None: Manual override if set, None otherwise
        """
        return self._manual_override

    def scale(self, value):
        """Scale a single integer pixel value

        Args:
            value: Integer pixel value to scale

        Returns:
            int: Scaled pixel value
        """
        if value == 0:
            return 0
        return int(round(value * self._scale_factor))

    def scale_tuple(self, *values):
        """Scale multiple values (for padding, dimensions, etc)

        Args:
            *values: Variable number of integer values

        Returns:
            tuple: Tuple of scaled values
        """
        return tuple(self.scale(v) for v in values)

    def scale_font_size(self, size):
        """Scale font size (handles both positive point sizes and negative pixel sizes)

        Args:
            size: Font size (negative for pixels, positive for points)

        Returns:
            int: Scaled font size
        """
        if size == 0:
            return 0

        # Negative sizes are pixel-based and scale linearly
        if size < 0:
            return -self.scale(-size)

        # Positive sizes are point-based
        # Scale points but ensure minimum readability
        scaled = int(round(size * self._scale_factor))
        return max(scaled, 6)  # Minimum 6pt font

    def scale_line_width(self, width):
        """Scale line width with minimum of appropriate value

        Args:
            width: Line width in pixels

        Returns:
            int: Scaled line width
        """
        if width == 0:
            return 0

        scaled = int(round(width * self._scale_factor))
        # Ensure at least 1 pixel for visible lines
        return max(scaled, 1)

    def upscale_icon(self, pil_image, factor=None):
        """Upscale icon using PIL with high-quality interpolation

        Args:
            pil_image: PIL Image object
            factor: Scale factor (uses current if None)

        Returns:
            PIL Image: Upscaled image
        """
        if not PIL_AVAILABLE:
            logging.warning("PIL not available, returning original image")
            return pil_image

        if factor is None:
            factor = self._scale_factor

        # Don't upscale if factor is 1.0 or less
        if factor <= 1.0:
            return pil_image

        # Calculate new size
        width, height = pil_image.size
        new_width = int(width * factor)
        new_height = int(height * factor)

        # Use LANCZOS for high-quality upscaling
        # Try modern Pillow API first, fall back to old API
        try:
            # Modern Pillow (>=10.0.0)
            resampling = Image.Resampling.LANCZOS
        except AttributeError:
            # Older Pillow
            resampling = Image.LANCZOS

        return pil_image.resize((new_width, new_height), resampling)

    def load_from_config(self):
        """Load DPI settings from configuration

        Returns:
            bool: True if loaded successfully
        """
        try:
            # Import Utils here to avoid circular imports
            import Utils

            # Check for legacy doublesizeicon setting
            if Utils.getBool("CNC", "doublesizeicon", False):
                logging.info("Migrating legacy doublesizeicon setting to new DPI system")
                self._manual_override = 2.0
                self._scale_factor = 2.0
                # Disable old setting
                Utils.setBool("CNC", "doublesizeicon", False)
                self.save_to_config()
                return True

            # Load modern DPI settings
            mode = Utils.getStr("DPI", "mode", "auto")
            manual_scale = Utils.getFloat("DPI", "scale", 1.0)

            # Validate manual scale
            if manual_scale not in self.SCALE_FACTORS:
                logging.warning(f"Invalid manual scale {manual_scale}, snapping to supported value")
                manual_scale = self._snap_to_supported_scale(manual_scale)

            if mode == "manual":
                self._manual_override = manual_scale
                self._scale_factor = manual_scale
                logging.info(f"Loaded manual DPI scale: {manual_scale}x")
            else:
                # Use auto-detected scale
                self._scale_factor = self._auto_detected
                logging.info(f"Using auto-detected DPI scale: {self._auto_detected}x")

            return True

        except Exception as e:
            logging.error(f"Failed to load DPI config: {e}")
            return False

    def save_to_config(self):
        """Save DPI settings to configuration

        Returns:
            bool: True if saved successfully
        """
        try:
            # Import Utils here to avoid circular imports
            import Utils

            # Determine mode
            mode = "manual" if self._manual_override is not None else "auto"

            # Save settings
            Utils.setStr("DPI", "mode", mode)
            if self._manual_override is not None:
                Utils.setFloat("DPI", "scale", self._manual_override)
            else:
                Utils.setFloat("DPI", "scale", 1.0)

            # Save detected scale for informational purposes
            Utils.setFloat("DPI", "detected", self._auto_detected)

            logging.info(f"Saved DPI config: mode={mode}, scale={self._scale_factor}x")
            return True

        except Exception as e:
            logging.error(f"Failed to save DPI config: {e}")
            return False


# Global DPI manager instance
_dpi_manager = None


def get_dpi_manager():
    """Get global DPI manager instance

    Returns:
        DPIManager: Global DPI manager instance
    """
    global _dpi_manager
    if _dpi_manager is None:
        logging.warning("DPI manager not initialized, creating default instance")
        _dpi_manager = DPIManager()
    return _dpi_manager


def init_dpi_manager(root_window):
    """Initialize global DPI manager

    Args:
        root_window: Tkinter root window

    Returns:
        DPIManager: Initialized DPI manager
    """
    global _dpi_manager
    _dpi_manager = DPIManager(root_window)
    logging.info("DPI manager initialized")
    return _dpi_manager
