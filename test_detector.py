import random
import unittest

from behavioral_guard import Baseline, Detector, Service, Store, Window
from behavioral_guard.mouse import MouseWindow
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

    def test_retention_deletes_old_alerts_with_windows(self):
        store = Store(":memory:")
        old = store.add_window("2026-10-01T00:00:00", make_window(self.rng))
        store.add_alert(old, 90, [])
        store.add_window("2026-11-24T00:00:00", make_window(self.rng))
        self.assertEqual(store.prune_older_than("2026-11-01"), 1)
        self.assertEqual(store.connection.execute("SELECT count(*) FROM alerts").fetchone()[0], 0)
        self.assertEqual(store.connection.execute("SELECT count(*) FROM windows").fetchone()[0], 1)
        store.close()

    def test_service_consent_learning_alert_and_delete(self):
        store = Store(":memory:")
        service = Service(store, min_learning_days=1)
        first = make_window(self.rng)
        self.assertEqual(service.process("t0", first)["status"], "paused")
        self.assertEqual(store.connection.execute("SELECT count(*) FROM windows").fetchone()[0], 0)
        service.set_consent(True)
        service.set_paused(False)
        for index in range(30):
            result = service.process(f"t{index}", make_window(self.rng))
        self.assertEqual(result["progress"], 100)
        self.assertFalse(service.process("s1", make_window(self.rng, 3))["alert"])
        result = service.process("s2", make_window(self.rng, 3))
        self.assertFalse(result["alert"])
        result = service.process("s3", make_window(self.rng, 3))
        self.assertTrue(result["alert"])
        service.feedback(result["alert_id"], "normal")
        service.delete_all()
        self.assertEqual(store.connection.execute("SELECT count(*) FROM windows").fetchone()[0], 0)
        self.assertEqual(service.process("new", make_window(self.rng))["status"], "learning")
        store.close()

    def test_mouse_samples_produce_aggregate_metrics_only(self):
        collector = MouseWindow(seconds=10)
        collector.sample(0.0, 10, 10, False)
        collector.sample(0.1, 20, 10, True)
        collector.sample(0.2, 30, 10, False)
        collector.sample(0.3, 40, 10, True)
        result = collector.finish("app", "mouse", "day")
        self.assertEqual(result.metrics["click_rate"], 12)
        self.assertEqual(result.metrics["mouse_curvature"], 1)
        self.assertNotIn("x", result.metrics)
        self.assertNotIn("y", result.metrics)
        self.assertNotIn("key", result.metrics)

    def test_default_learning_requires_seven_distinct_days(self):
        store = Store(":memory:")
        service = Service(store)
        service.set_consent(True)
        for index in range(30):
            result = service.process(f"2026-11-01T00:{index:02}:00", make_window(self.rng))
        self.assertEqual(result["status"], "learning")
        self.assertEqual(result["learning_days"], 1)
        for day in range(2, 8):
            result = service.process(f"2026-11-{day:02}T00:00:00", make_window(self.rng))
        self.assertEqual(result["learning_days"], 7)
        self.assertNotEqual(service.process("2026-11-08T00:00:00", make_window(self.rng))["status"], "learning")
        store.close()


if __name__ == "__main__":
    unittest.main()
