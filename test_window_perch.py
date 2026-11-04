"""Run with python -m unittest test_window_perch."""
import unittest

from window_perch import WindowInfo, choose_attachment, ledge_position, logical_rect


class PerchGeometryTests(unittest.TestCase):
    def setUp(self):
        self.window = WindowInfo(1, (100, 400, 900, 800))
        self.screens = [(0, 0, 1920, 1080)]
        self.anchor = (96, 188)
        self.size = (192, 208)

    def choose(self, windows=None, sprite=(350, 300, 450, 500)):
        return choose_attachment(windows or [self.window], sprite,
                                 {"top": self.anchor, "bottom": (96, 10)},
                                 {"top": self.size, "bottom": self.size}, self.screens)

    def test_threshold_and_outside_edge(self):
        self.assertIsNotNone(self.choose(sprite=(350, 428, 450, 628)))
        self.assertIsNone(self.choose(sprite=(350, 429, 450, 629)))
        self.assertIsNone(self.choose(sprite=(901, 300, 1001, 500)))

    def test_topmost_and_occlusion(self):
        front = WindowInfo(2, (200, 390, 800, 700))
        self.assertEqual(self.choose([front, self.window])[0].handle, 2)
        blocker = WindowInfo(3, (300, 300, 500, 600), False)
        self.assertIsNone(self.choose([blocker, self.window]))
        self.assertIsNotNone(self.choose([self.window, blocker]))

    def test_move_and_resize_clamp(self):
        moved = WindowInfo(1, (200, 500, 600, 900))
        self.assertEqual(ledge_position(moved, 700, self.anchor, self.size, self.screens, [moved]), (408, 312))

    def test_insufficient_space_and_narrow_window(self):
        for bounds in [(100, 100, 900, 800), (100, 400, 250, 800)]:
            w = WindowInfo(1, bounds)
            self.assertIsNone(ledge_position(w, 100, self.anchor, self.size, self.screens, [w]))

    def test_negative_monitor_origin_and_scale(self):
        self.assertEqual(logical_rect((-1800, 600, -600, 1200), (-1920, 0), (-1920, 0), 1.5),
                         (-1840, 400, -1040, 800))

    def test_non_candidate_and_disappeared_window(self):
        self.assertIsNone(self.choose([WindowInfo(2, self.window.rect, False)]))
        self.assertIsNone(ledge_position(self.window, 300, self.anchor, self.size, self.screens, []))

    def test_head_body_or_feet_can_overlap_ledge(self):
        for top in (200, 280, 390):
            self.assertIsNotNone(self.choose(sprite=(350, top, 450, top+200)))
        self.assertIsNone(self.choose(sprite=(350, 450, 450, 650)))

    def test_partial_horizontal_overlap_is_sufficient(self):
        self.assertIsNotNone(self.choose(sprite=(50, 300, 110, 500)))

    def test_trimmed_transparent_padding_allows_lower_top_margin(self):
        window = WindowInfo(1, (100, 120, 900, 700))
        result = choose_attachment([window], (350, 50, 450, 250),
                                   {"top": (96, 104), "bottom": (96, 10)},
                                   {"top": self.size, "bottom": self.size}, self.screens)
        self.assertEqual(result[2], (304, 16))

    def test_lower_edge_is_selected(self):
        self.assertEqual(self.choose(sprite=(350, 700, 450, 900))[3], "bottom")

    def test_both_edges_choose_nearest_then_top_on_tie(self):
        short = WindowInfo(1, (100, 400, 900, 500))
        self.assertEqual(self.choose([short], (350, 350, 450, 550))[3], "top")
        self.assertEqual(self.choose([short], (350, 390, 450, 590))[3], "bottom")

    def test_lower_edge_allows_clipping_below_screen(self):
        low = WindowInfo(1, (100, 400, 900, 1070))
        result = ledge_position(low, 300, (96, 10), self.size, self.screens, [low], "bottom")
        self.assertEqual(result, (304, 1060))
        moved = WindowInfo(1, (100, 400, 900, 1150))
        self.assertEqual(ledge_position(moved, 300, (96, 10), self.size, self.screens, [moved], "bottom"), (304, 1140))

    def test_lower_edge_checks_contact_inside_window(self):
        blocker = WindowInfo(2, (300, 700, 600, 810), False)
        self.assertIsNone(self.choose([blocker, self.window], (350, 700, 450, 900)))

    def test_covering_either_hand_detaches(self):
        for left, right in ((375, 385), (417, 427)):
            blocker = WindowInfo(2, (left, 700, right, 810), False)
            self.assertIsNone(self.choose([blocker, self.window], (350, 700, 450, 900)))

    def test_heart_grips_use_natural_narrower_spacing(self):
        for left, right in ((382, 385), (415, 418)):
            blocker = WindowInfo(2, (left, 700, right, 810), False)
            self.assertIsNone(ledge_position(self.window, 300, (96, 10), self.size,
                                            self.screens, [blocker, self.window], "bottom", (-16.56, 16.56)))


if __name__ == "__main__":
    unittest.main()
