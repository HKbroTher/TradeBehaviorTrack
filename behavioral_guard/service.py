"""Consent-gated orchestration of baseline learning, scoring and local storage."""

from .detector import Detector, MIN_WINDOWS, Window
from .store import Store


class Service:
    def __init__(self, store: Store, min_learning_days: int = 7):
        if min_learning_days < 1:
            raise ValueError("min_learning_days must be positive")
        self.store = store
        self.min_learning_days = min_learning_days
        self.detector = Detector(store.load_baseline())
        self.consent = False
        self.paused = False

    def set_consent(self, enabled: bool) -> None:
        self.consent = enabled
        if not enabled:
            self.paused = True

    def set_paused(self, enabled: bool) -> None:
        self.paused = enabled

    def process(self, observed_at: str, window: Window) -> dict:
        if not self.consent or self.paused:
            return {"status": "paused", "score": None, "alert": False, "reasons": []}
        if window.sensitive:
            return {"status": "sensitive", "score": None, "alert": False, "reasons": []}
        count = self.detector.baseline.count(window.key)
        days = self.store.learning_days(window.key)
        if count < MIN_WINDOWS or days < self.min_learning_days:
            if not window.transition and window.activity_count >= 5:
                self.store.add_window(observed_at, window, baseline_eligible=True)
                self.detector.baseline.add(window)
                days = self.store.learning_days(window.key)
            window_progress = min(1.0, self.detector.baseline.count(window.key) / MIN_WINDOWS)
            day_progress = min(1.0, days / self.min_learning_days)
            return {"status": "learning", "progress": round(100 * min(window_progress, day_progress)),
                    "learning_days": days, "required_days": self.min_learning_days,
                    "score": None, "alert": False, "reasons": []}
        result = self.detector.score(window)
        if result["status"] != "insufficient_data":
            window_id = self.store.add_window(observed_at, window)
            if result["alert"]:
                result["alert_id"] = self.store.add_alert(window_id, result["score"], result["reasons"])
        return result

    def feedback(self, alert_id: int, choice: str) -> None:
        self.store.set_feedback(alert_id, choice)

    def delete_all(self) -> None:
        self.store.delete_all()
        self.detector = Detector(self.store.load_baseline())
