import random
import unittest

from behavioral_guard import Baseline, Detector, Window
from simulate import make_window


class DetectorTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(2026)
        self.baseline = Baseline()
        for _ in range(60):
            self.baseline.add(make_window(rng))
        self.rng = rng

    def test_short_spike_is_suppressed_but_persistent_change_alerts(self):
        detector = Detector(self.baseline)
        self.assertFalse(detector.score(make_window(self.rng, 3))["alert"])
        self.assertFalse(detector.score(make_window(self.rng))["alert"])
        self.assertFalse(detector.score(make_window(self.rng))["alert"])
        self.assertFalse(detector.score(make_window(self.rng, 3))["alert"])
        result = detector.score(make_window(self.rng, 3))
        self.assertTrue(result["alert"])
        self.assertGreaterEqual(result["active_groups"], 2)
        self.assertLessEqual(len(result["reasons"]), 3)
        self.assertFalse(detector.score(make_window(self.rng, 3))["alert"])

    def test_sensitive_and_new_context_are_not_scored(self):
        detector = Detector(self.baseline)
        source = make_window(self.rng, 3)
        sensitive = Window(source.context, source.device, source.hour_band,
                           source.activity_count, source.metrics, sensitive=True)
        self.assertEqual(detector.score(sensitive)["status"], "insufficient_data")
        new_context = Window("browser", source.device, source.hour_band,
                             source.activity_count, source.metrics)
        self.assertEqual(detector.score(new_context)["status"], "learning")


if __name__ == "__main__":
    unittest.main()
