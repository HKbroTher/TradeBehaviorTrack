"""Personal, context-aware deviation detector.

Inputs are aggregate window metrics only. No key codes, text, or raw events are accepted.
Thresholds are initial engineering choices, not clinical or research-derived cutoffs.
"""

from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Mapping

GROUPS = {
    "mouse_motion": ("mouse_speed", "mouse_turning", "mouse_pause_ratio"),
    "mouse_click": ("click_rate", "click_interval_cv"),
    "keyboard_rhythm": ("key_interval", "key_dwell", "typing_pause_ratio"),
}
MIN_WINDOWS = 30
MIN_ACTIVITY = 5
GROUP_THRESHOLD = 2.5


@dataclass(frozen=True)
class Window:
    context: str
    device: str
    hour_band: str
    activity_count: int
    metrics: Mapping[str, float]
    sensitive: bool = False
    transition: bool = False

    @property
    def key(self) -> tuple[str, str, str]:
        return self.context, self.device, self.hour_band


class Baseline:
    def __init__(self) -> None:
        self._samples: dict[tuple[str, str, str], list[Mapping[str, float]]] = {}

    def add(self, window: Window) -> None:
        if window.sensitive or window.transition or window.activity_count < MIN_ACTIVITY:
            return
        self._samples.setdefault(window.key, []).append(dict(window.metrics))

    def count(self, key: tuple[str, str, str]) -> int:
        return len(self._samples.get(key, ()))

    def deviation(self, key: tuple[str, str, str], metric: str, value: float) -> float | None:
        values = [sample[metric] for sample in self._samples.get(key, ()) if metric in sample]
        if len(values) < MIN_WINDOWS:
            return None
        center = median(values)
        mad = median(abs(x - center) for x in values)
        # A flat baseline gives no reliable scale. Require new varied observations.
        if mad == 0:
            return None
        return abs(value - center) / (1.4826 * mad)


class Detector:
    def __init__(self, baseline: Baseline, cooldown_windows: int = 5) -> None:
        self.baseline = baseline
        self.recent: deque[bool] = deque(maxlen=3)
        self.last_key: tuple[str, str, str] | None = None
        self.cooldown = 0
        self.cooldown_windows = cooldown_windows

    def score(self, window: Window) -> dict:
        if window.key != self.last_key:
            self.recent.clear()
            self.last_key = window.key
        if self.cooldown:
            self.cooldown -= 1
        if window.sensitive or window.transition or window.activity_count < MIN_ACTIVITY:
            self.recent.clear()
            return {"status": "insufficient_data", "score": None, "alert": False, "reasons": []}
        if self.baseline.count(window.key) < MIN_WINDOWS:
            self.recent.clear()
            return {"status": "learning", "score": None, "alert": False, "reasons": []}

        groups = []
        details = []
        for group, names in GROUPS.items():
            deviations = [(name, self.baseline.deviation(window.key, name, window.metrics[name]))
                          for name in names if name in window.metrics]
            deviations = [(name, value) for name, value in deviations if value is not None]
            if deviations:
                name, value = max(deviations, key=lambda item: item[1])
                groups.append((group, value))
                details.append({"group": group, "metric": name, "robust_z": round(value, 2),
                                "direction": "above" if window.metrics[name] > median(
                                    [s[name] for s in self.baseline._samples[window.key] if name in s]) else "below"})
        if len(groups) < 2:
            self.recent.clear()
            return {"status": "insufficient_data", "score": None, "alert": False, "reasons": []}

        active = sum(value >= GROUP_THRESHOLD for _, value in groups)
        candidate = active >= 2
        self.recent.append(candidate)
        # Two independent group deviations must recur in two of the last three windows.
        persistent = len(self.recent) == 3 and sum(self.recent) >= 2 and candidate
        alert = persistent and self.cooldown == 0
        if alert:
            self.cooldown = self.cooldown_windows
        # Display score is relative deviation, not a probability of a mental state.
        top = sorted((value for _, value in groups), reverse=True)[:2]
        display_score = min(100, round(100 * sum(min(v, 6) for v in top) / 12))
        return {"status": "anomaly" if candidate else "normal", "score": display_score,
                "alert": alert, "reasons": sorted(details, key=lambda d: d["robust_z"], reverse=True)[:3],
                "active_groups": active}
