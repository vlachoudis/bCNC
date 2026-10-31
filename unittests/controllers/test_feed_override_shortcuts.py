import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pathfix

from CNC import CNC
from ControlPage import StateFrame


class TestFeedOverrideShortcuts(unittest.TestCase):
    def setUp(self):
        self.old_feed = CNC.vars["_OvFeed"]
        self.old_changed = CNC.vars["_OvChanged"]

        CNC.vars["_OvFeed"] = 100
        CNC.vars["_OvChanged"] = False

        self.frame = SimpleNamespace(
            overrideCombo=Mock(),
            override=Mock(),
        )
        self.frame.overrideCombo.get.return_value = "Feed"

    def tearDown(self):
        CNC.vars["_OvFeed"] = self.old_feed
        CNC.vars["_OvChanged"] = self.old_changed

    def test_increase_feed_override(self):
        StateFrame.adjustFeedOverride(self.frame, 10)

        self.assertEqual(CNC.vars["_OvFeed"], 110)
        self.assertTrue(CNC.vars["_OvChanged"])
        self.frame.override.set.assert_called_once_with(110)

    def test_decrease_feed_override(self):
        StateFrame.adjustFeedOverride(self.frame, -10)

        self.assertEqual(CNC.vars["_OvFeed"], 90)
        self.assertTrue(CNC.vars["_OvChanged"])

    def test_does_not_change_spindle_display(self):
        self.frame.overrideCombo.get.return_value = "Spindle"

        StateFrame.adjustFeedOverride(self.frame, 10)

        self.assertEqual(CNC.vars["_OvFeed"], 110)
        self.frame.override.set.assert_not_called()

    def test_upper_limit(self):
        CNC.vars["_OvFeed"] = 195

        StateFrame.adjustFeedOverride(self.frame, 10)

        self.assertEqual(CNC.vars["_OvFeed"], 200)

    def test_lower_limit(self):
        CNC.vars["_OvFeed"] = 15

        StateFrame.adjustFeedOverride(self.frame, -10)

        self.assertEqual(CNC.vars["_OvFeed"], 10)

    def test_no_change_at_upper_limit(self):
        CNC.vars["_OvFeed"] = 200

        StateFrame.adjustFeedOverride(self.frame, 10)

        self.assertEqual(CNC.vars["_OvFeed"], 200)
        self.assertFalse(CNC.vars["_OvChanged"])
        self.frame.override.set.assert_not_called()

    def test_shortcut_command_dispatch(self):
        from bmain import Application
        from Sender import Sender

        app = Mock()
        app.commands = {}
        app.tools.pluginList.return_value = []

        app.registerCommand.side_effect = (
            lambda name, handler, minlen=None:
            Sender.registerCommand(app, name, handler, minlen)
        )
        app.matchCommand.side_effect = (
            lambda name: Sender.matchCommand(app, name)
        )
        app.executeCommand.side_effect = (
            lambda line: Sender.executeCommand(app, line)
        )
        app.executeGcode.side_effect = (
            lambda line: Sender.executeGcode(app, line)
        )
        app.evaluate.side_effect = lambda line: line

        app.gstate.adjustFeedOverride.side_effect = (
            lambda delta: StateFrame.adjustFeedOverride(
                self.frame, delta
            )
        )

        Application.registerCommands(app)

        self.assertIn("FEED+10", app.commands)
        self.assertIn("FEED-10", app.commands)

        Application.execute(app, "FEED+10")
        self.assertEqual(CNC.vars["_OvFeed"], 110)

        Application.execute(app, "FEED-10")
        self.assertEqual(CNC.vars["_OvFeed"], 100)

        app.sendGCode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
