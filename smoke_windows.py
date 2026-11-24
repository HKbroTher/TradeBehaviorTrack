"""Short in-memory Windows mouse API smoke check for an approved application."""

import argparse
import os
import time

from behavioral_guard.mouse import MouseWindow
from behavioral_guard.win_mouse import WindowsMouse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consent", action="store_true", required=True)
    parser.add_argument("--allow-exe", required=True, help="Executable basename of a non-sensitive test app")
    parser.add_argument("--seconds", type=int, default=5)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows is required")
    if not 3 <= args.seconds <= 30:
        parser.error("Use 3 to 30 seconds")
    source = WindowsMouse()
    collector = MouseWindow(args.seconds)
    active_samples = 0
    excluded_samples = 0
    started = time.monotonic()
    while time.monotonic() - started < args.seconds:
        if source.foreground_exe() == args.allow_exe.lower() and not source.sensitive_focus():
            collector.sample(time.monotonic(), *source.sample())
            active_samples += 1
        else:
            collector.reset()
            excluded_samples += 1
        time.sleep(0.05)
    print(f"Approved samples: {active_samples}; excluded samples: {excluded_samples}")
    if active_samples:
        window = collector.finish(args.allow_exe.lower(), "test_mouse", "test")
        print(f"Aggregate metrics: {dict(window.metrics)}")
    print("No event coordinates, keyboard data or database records were saved.")


if __name__ == "__main__":
    main()
