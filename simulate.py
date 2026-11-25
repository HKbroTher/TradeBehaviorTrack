"""Run a deterministic normal / short spike / persistent anomaly demonstration."""

import random
from behavioral_guard import Baseline, Detector, Window


def make_window(rng: random.Random, shift: float = 0) -> Window:
    return Window("trading", "mouse_keyboard_a", "day", 50, {
        "mouse_speed": 100 + rng.gauss(0, 6) + shift * 35,
        "mouse_turning": 1.5 + rng.gauss(0, .1),
        "click_rate": 12 + rng.gauss(0, 1) + shift * 7,
        "key_interval": 180 + rng.gauss(0, 10) - shift * 45,
    })


def main() -> None:
    rng = random.Random(2026)
    baseline = Baseline()
    for _ in range(60):
        baseline.add(make_window(rng))
    detector = Detector(baseline)
    sequence = [("normal", 0)] * 10 + [("single spike", 3)] + [("normal", 0)] * 3 + [("persistent", 3)] * 4
    for label, shift in sequence:
        result = detector.score(make_window(rng, shift))
        print(f"{label:14} score={result['score']:3} alert={result['alert']} reasons={result['reasons'][:2]}")


if __name__ == "__main__":
    main()
