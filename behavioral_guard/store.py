"""Local SQLite storage for aggregate features and alert feedback only."""

import json
import sqlite3
from pathlib import Path

from .detector import Baseline, Window


class Store:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS windows (
                id INTEGER PRIMARY KEY,
                observed_at TEXT NOT NULL,
                context TEXT NOT NULL,
                device TEXT NOT NULL,
                hour_band TEXT NOT NULL,
                activity_count INTEGER NOT NULL,
                metrics_json TEXT NOT NULL,
                baseline_eligible INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                window_id INTEGER NOT NULL REFERENCES windows(id) ON DELETE CASCADE,
                score INTEGER NOT NULL,
                reasons_json TEXT NOT NULL,
                feedback TEXT CHECK(feedback IN ('ignore', 'normal', 'fatigue_or_emotion', 'device_or_environment'))
            );
        """)

    def add_window(self, observed_at: str, window: Window, baseline_eligible: bool = False) -> int:
        if window.sensitive:
            raise ValueError("Sensitive windows must not be stored")
        if window.transition or window.activity_count < 5:
            baseline_eligible = False
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO windows (observed_at, context, device, hour_band, activity_count, metrics_json, baseline_eligible) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (observed_at, window.context, window.device, window.hour_band,
                 window.activity_count, json.dumps(dict(window.metrics)), int(baseline_eligible)))
        return cursor.lastrowid

    def add_alert(self, window_id: int, score: int, reasons: list[dict]) -> int:
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO alerts (window_id, score, reasons_json) VALUES (?, ?, ?)",
                (window_id, score, json.dumps(reasons)))
        return cursor.lastrowid

    def set_feedback(self, alert_id: int, feedback: str) -> None:
        if feedback not in {"ignore", "normal", "fatigue_or_emotion", "device_or_environment"}:
            raise ValueError("Unknown feedback")
        with self.connection:
            cursor = self.connection.execute("UPDATE alerts SET feedback = ? WHERE id = ?", (feedback, alert_id))
        if cursor.rowcount != 1:
            raise ValueError("Unknown alert")

    def load_baseline(self) -> Baseline:
        baseline = Baseline()
        rows = self.connection.execute(
            "SELECT context, device, hour_band, activity_count, metrics_json FROM windows WHERE baseline_eligible = 1")
        for context, device, hour_band, count, metrics in rows:
            baseline.add(Window(context, device, hour_band, count, json.loads(metrics)))
        return baseline

    def delete_all(self) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM alerts")
            self.connection.execute("DELETE FROM windows")

    def close(self) -> None:
        self.connection.close()
