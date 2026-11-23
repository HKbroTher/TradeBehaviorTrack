"""Consent-gated orchestration of baseline learning, scoring and local storage."""

from .detector import Detector, MIN_WINDOWS, Window
from .store import Store


class Service:
    def __init__(self, store: Store):
        self.store = store
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
        if count < MIN_WINDOWS:
            if not window.transition and window.activity_count >= 5:
                self.store.add_window(observed_at, window, baseline_eligible=True)
                self.detector.baseline.add(window)
            return {"status": "learning", "progress": min(100, round(100 * self.detector.baseline.count(window.key) / MIN_WINDOWS)),
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
