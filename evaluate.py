"""Deterministic synthetic evaluation; not a real-world accuracy claim."""

import random
from behavioral_guard import Baseline, Detector
from simulate import make_window


def main() -> None:
    rng = random.Random(20261124)
    baseline = Baseline()
    for _ in range(60):
        baseline.add(make_window(rng))
    detector = Detector(baseline)
    normal_alerts = sum(detector.score(make_window(rng))["alert"] for _ in range(1000))
    detector = Detector(baseline)
    abnormal_results = [detector.score(make_window(rng, 3)) for _ in range(10)]
    first_alert = next((index + 1 for index, result in enumerate(abnormal_results) if result["alert"]), None)
    print(f"Normal simulation: {normal_alerts} alerts / 1000 windows")
    print(f"Sustained change: first alert in window {first_alert}")
    print("Synthetic data only; this does not measure real user false alarms or sensitivity.")


if __name__ == "__main__":
    main()
