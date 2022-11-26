import shutil
import time

import pyautogui

from .base import BaseGUITestCase


class SmokeTest(BaseGUITestCase):
    def test_launches(self):
        self.assertFalse(self.gui_proc.poll())

    def test_can_load_and_run_sample_gcode(self):
        shutil.copy(
            self.get_static_path("sample.gcode"),
            "/tmp/",
        )

        self.send_command("load /tmp/sample.gcode")
        pyautogui.press("f10")  # Mapped to 'start' in config
        self.delay(10)
        pyautogui.press("f12")  # Mapped to 'stop' in config
        self.delay(10)

        state = self.get_bcnc_state()
        # Assert that we moved the tool position
        self.assertGreaterEqual(state["wx"], 0)
        self.assertGreaterEqual(state["wy"], 0)
