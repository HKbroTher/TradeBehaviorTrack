import random
import unittest

from behavioral_guard import Baseline, Detector, Store, Window
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

    def test_local_storage_feedback_and_deletion(self):
        store = Store(":memory:")
        for index in range(60):
            store.add_window(f"2026-11-24T00:{index:02}:00", make_window(self.rng), True)
        restored = store.load_baseline()
        self.assertEqual(restored.count(("trading", "mouse_keyboard_a", "day")), 60)
        current = make_window(self.rng, 3)
        window_id = store.add_window("2026-11-24T01:00:00", current)
        alert_id = store.add_alert(window_id, 100, [{"metric": "mouse_speed"}])
        store.set_feedback(alert_id, "normal")
        self.assertEqual(store.connection.execute("SELECT feedback FROM alerts").fetchone()[0], "normal")
        sensitive = Window(current.context, current.device, current.hour_band,
                           current.activity_count, current.metrics, sensitive=True)
        with self.assertRaises(ValueError):
            store.add_window("2026-11-24T01:01:00", sensitive)
        store.delete_all()
        self.assertEqual(store.connection.execute("SELECT count(*) FROM windows").fetchone()[0], 0)
        self.assertEqual(store.connection.execute("SELECT count(*) FROM alerts").fetchone()[0], 0)
        store.close()


if __name__ == "__main__":
    unittest.main()
