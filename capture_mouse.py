"""Opt-in Windows mouse collection prototype for selected foreground executables.

No keyboard data is collected. Use only for controlled evaluation; custom
password-field exclusion and physical mouse-device identification are pending.
"""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import time

from behavioral_guard import Service, Store
from behavioral_guard.mouse import MouseWindow
from behavioral_guard.win_mouse import WindowsMouse


def hour_band(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 24:
        return "evening"
    return "night"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consent", action="store_true", required=True,
                        help="Confirm explicit consent to mouse feature collection")
    parser.add_argument("--allow-exe", action="append", required=True,
                        help="Foreground executable basename to monitor, e.g. trading.exe")
    parser.add_argument("--window-seconds", type=int, default=60)
    parser.add_argument("--sample-ms", type=int, default=50)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Live mouse collection requires Windows")
    if args.window_seconds < 10 or args.sample_ms < 20:
        parser.error("Window must be at least 10 seconds and sampling interval at least 20 ms")
    allowed = {name.lower() for name in args.allow_exe}
    data_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BehavioralGuard"
    data_root.mkdir(parents=True, exist_ok=True)
    stop_file = data_root / "stop-monitoring"
    stop_file.unlink(missing_ok=True)  # Explicit new consent starts a new session.
    store = Store(data_root / "behavior.sqlite3")
    store.prune_older_than((datetime.now().date() - timedelta(days=30)).isoformat())
    service = Service(store)
    service.set_consent(True)
    service.set_paused(False)
    source = WindowsMouse()
    window = MouseWindow(args.window_seconds)
    active_exe: str | None = None
    started = time.monotonic()
    print("Mouse-only prototype running. Press Ctrl+C to stop. No keyboard data is collected.")
    try:
        while True:
            if stop_file.exists():
                print("Monitoring stopped by the desktop application.")
                break
            now = time.monotonic()
            exe = source.foreground_exe()
            if exe not in allowed or source.sensitive_focus():
                if active_exe is not None:
                    print(f"Discarded partial window after {now - started:.1f}s: foreground changed or focus excluded")
                active_exe = None
                window.reset()
                started = now
            elif exe != active_exe:
                active_exe = exe
                window.reset()
                started = now
                print(f"Approved foreground: {active_exe}; collecting {args.window_seconds}s window")
            else:
                window.sample(now, *source.sample())
                if now - started >= args.window_seconds:
                    if stop_file.exists():
                        break
                    observed = datetime.now().astimezone()
                    result = service.process(observed.isoformat(timespec="seconds"),
                                             window.finish(f"{active_exe}:{args.window_seconds}s", "default_mouse", hour_band(observed.hour)))
                    print(f"{observed:%H:%M:%S} {active_exe}: {result['status']} score={result['score']} alert={result['alert']}")
                    window.reset()
                    started = now
            time.sleep(args.sample_ms / 1000)
    except KeyboardInterrupt:
        if active_exe is not None:
            print(f"Stopped with partial window after {time.monotonic() - started:.1f}s; no partial window saved")
        print("Stopped.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
