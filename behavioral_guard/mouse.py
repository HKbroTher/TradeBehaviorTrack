"""Aggregate sampled cursor movement without retaining coordinates or events."""

import math
from statistics import mean, pstdev

from .detector import Window


class MouseWindow:
    def __init__(self, seconds: float = 60.0):
        self.seconds = seconds
        self.reset()

    def reset(self) -> None:
        self.previous: tuple[float, int, int, bool] | None = None
        self.previous_move: tuple[int, int] | None = None
        self.distance = 0.0
        self.turn_weight = 0.0
        self.speeds: list[float] = []
        self.idle_seconds = 0.0
        self.click_times: list[float] = []
        self.motion_samples = 0

    def sample(self, at: float, x: int, y: int, left_down: bool) -> None:
        if self.previous is not None:
            previous_at, previous_x, previous_y, previous_down = self.previous
            elapsed = at - previous_at
            if elapsed <= 0:
                return
            dx, dy = x - previous_x, y - previous_y
            distance = math.hypot(dx, dy)
            self.distance += distance
            if distance < 2:
                self.idle_seconds += elapsed
            else:
                if self.previous_move is not None:
                    old_x, old_y = self.previous_move
                    angle = math.atan2(abs(old_x * dy - old_y * dx), old_x * dx + old_y * dy)
                    self.turn_weight += angle * min(math.hypot(old_x, old_y), distance)
                self.previous_move = (dx, dy)
                self.motion_samples += 1
                self.speeds.append(distance / elapsed)
            if left_down and not previous_down:
                self.click_times.append(at)
        self.previous = (at, x, y, left_down)

    def finish(self, context: str, device: str, hour_band: str) -> Window:
        intervals = [b - a for a, b in zip(self.click_times, self.click_times[1:])]
        metrics = {
            "mouse_speed": mean(self.speeds) if self.speeds else 0.0,
            "mouse_turning": 1 + self.turn_weight / self.distance if self.distance else 1.0,
            "mouse_pause_ratio": min(1.0, self.idle_seconds / self.seconds),
            "click_rate": len(self.click_times) * 60 / self.seconds,
        }
        if len(intervals) >= 2 and mean(intervals) > 0:
            metrics["click_interval_cv"] = pstdev(intervals) / mean(intervals)
        return Window(context, device, hour_band, self.motion_samples + len(self.click_times), metrics)
