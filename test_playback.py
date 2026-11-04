"""Deterministic playback checks with real Qt timers disabled."""
import random
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import ling_app as ling
from PySide6.QtCore import QPoint


class PlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = ling.QApplication.instance() or ling.QApplication([])
        cls.frames = {skin: ling.load_frames(ling.sheet_path(skin)) for skin in ling.SKINS}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with patch.object(ling, "settings_path", return_value=Path(self.tmp.name) / "settings.ini"):
            self.pet = ling.LingWindow(self.frames, "ling")
        for timer in (self.pet.frame_timer, self.pet.motion_timer, self.pet.perch_timer):
            timer.stop()
        self.pet.rng = random.Random(42)
        self.pet.hovering = False

    def tearDown(self):
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()
        self.tmp.cleanup()

    def finish(self):
        count = len(self.pet.frames[self.pet.state])
        for _ in range(count * self.pet.cycles_left - self.pet.frame_index):
            self.pet.next_frame()

    def test_durations_and_last_frame_for_both_skins(self):
        for skin in ling.SKINS:
            self.pet.change_skin(skin)
            for state, (_, count) in ling.ANIMATIONS.items():
                self.pet.start_reaction(state)
                self.assertLessEqual(abs(count * self.pet.frame_timer.interval() - 1600), 3)
                for _ in range(count - 1):
                    self.pet.next_frame()
                self.assertEqual(self.pet.state, state)
                self.assertEqual(self.pet.frame_index, count - 1)
                self.assertEqual(self.pet.playback_mode, "manual")
                self.pet.next_frame()
                self.assertEqual(self.pet.playback_mode, "auto")
                self.assertEqual(self.pet.frame_index, 0)

    def test_shuffle_coverage_and_two_complete_cycles(self):
        self.pet.animation_queue = []
        previous = None
        for _ in range(10):
            seen = []
            for i in range(9):
                self.pet.start_next_auto()
                state = self.pet.state
                if i == 0:
                    self.assertNotEqual(state, previous)
                seen.append(state)
                count = len(self.pet.frames[state])
                for _ in range(count):
                    self.pet.next_frame()
                self.assertEqual((self.pet.state, self.pet.frame_index, self.pet.cycles_left), (state, 0, 1))
                previous = state
            self.assertEqual(set(seen), set(ling.ANIMATIONS))
        # Completing the second cycle advances exactly one queued action.
        remaining = len(self.pet.animation_queue)
        self.finish()
        self.assertEqual(self.pet.cycles_left, 2)
        self.assertEqual(len(self.pet.animation_queue), 8 if remaining == 0 else remaining - 1)

    def test_manual_priority_and_queue(self):
        queue = self.pet.animation_queue.copy()
        self.pet.start_reaction("waving")
        self.assertEqual(self.pet.animation_queue, queue)
        with patch.object(ling.QCursor, "pos", return_value=self.pet.mapToGlobal(self.pet.input_region.boundingRect().center())):
            self.pet.refresh_hover()
        self.assertTrue(self.pet.hovering)
        self.assertEqual(self.pet.state, "waving")
        self.finish()
        self.assertEqual(self.pet.playback_mode, "auto")
        self.assertEqual(len(self.pet.animation_queue), len(queue) - 1)

    def test_pause_manual_and_resume(self):
        self.pet.toggle_pause()
        frame = self.pet.frame_index
        self.pet.next_frame()
        self.assertEqual(self.pet.frame_index, frame)
        self.pet.start_reaction("waving")
        self.finish()
        self.assertEqual((self.pet.state, self.pet.playback_mode), ("idle", "rest"))
        self.pet.next_frame()
        self.assertEqual(self.pet.frame_index, 0)
        self.pet.toggle_pause()
        self.assertEqual(self.pet.playback_mode, "auto")

    def test_boundary_bounce_preserves_cycle(self):
        self.pet.begin_animation("right", "auto", 2)
        self.pet.frame_index = 4
        self.pet.x_position = float(self.pet.bounds()[1])
        self.pet.last_tick = time.monotonic() - 0.05
        with patch.object(self.pet, "refresh_hover"):
            self.pet.advance_motion()
        self.assertEqual(self.pet.state, "left")
        self.assertEqual((self.pet.frame_index, self.pet.cycles_left), (4, 2))
        self.assertEqual(self.pet.x_position, self.pet.bounds()[1])

    def test_hover_and_interruptions(self):
        self.pet.hovering = True
        self.pet.start_reaction("jumping", mode="hover")
        for _ in range(10):
            self.pet.next_frame()
        self.assertEqual((self.pet.state, self.pet.frame_index), ("jumping", 0))
        self.pet.hovering = False
        for _ in range(5):
            self.pet.next_frame()
        self.assertEqual(self.pet.playback_mode, "auto")
        self.pet.start_reaction("waving")
        self.pet.change_skin("ling-heart")
        self.assertIsNone(self.pet.reaction)
        self.assertEqual((self.pet.playback_mode, self.pet.cycles_left), ("auto", 2))
        self.pet.drag_offset = QPoint(5, 5)
        frame = self.pet.frame_index
        self.pet.next_frame()
        self.assertEqual(self.pet.frame_index, frame)

    def test_all_menu_actions(self):
        menu = next(a.menu() for a in self.pet.menu.actions() if a.text() == "播放动作")
        self.assertEqual(len(menu.actions()), 9)
        for action, state in zip(menu.actions(), ("idle", "right", "left", "waving", "jumping", "waiting", "running", "review", "failed")):
            action.trigger()
            self.assertEqual((self.pet.state, self.pet.playback_mode), (state, "manual"))
            self.assertEqual(self.pet.frame_index, 0)


if __name__ == "__main__":
    unittest.main()
