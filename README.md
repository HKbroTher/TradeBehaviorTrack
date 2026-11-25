# Behavioral Guard detection prototype

This repository currently contains a platform-independent scoring prototype. Run `python simulate.py` from the repository root. It accepts only aggregate metrics per window; no raw input events or typed content are stored.

`behavioral_guard.store.Store` persists aggregate windows, alerts and feedback in a local SQLite database. Sensitive windows are rejected, baseline eligibility is explicit, and `delete_all()` removes personal records. A user marking an alert normal does not silently make its window part of the baseline. Applications embedding this core must provide consent checks before calling the store or detector.

`behavioral_guard.service.Service` connects consent, pause, learning progress, detection, feedback and deletion. It accepts an already aggregated `Window`; the embedding application remains responsible for Windows event capture and sensitive-field exclusion.

The detector uses a separate baseline for each application category, device and time band. Each metric is compared with its personal median and median absolute deviation. Correlated metrics are grouped; the largest deviation in a group represents that group. An alert requires at least two groups above a provisional robust-Z threshold of 2.5 in two of the last three windows, including the current window. Five-window cooldown limits repeat alerts. Insufficient baseline data, low activity, sensitive contexts and transitions suppress scoring.

Mouse turning is calculated from local changes in direction, weighted by movement distance. Its value is bounded between 1 and 1 + π. The earlier whole-window path-to-endpoint ratio could grow arbitrarily when the cursor returned near its start; the old `mouse_curvature` field is no longer used for scoring.

These thresholds are engineering defaults for simulation and must be calibrated on real, consented data. The 0–100 display value is relative behavioral deviation, not a probability of stress or a diagnosis. Windows marked normal by user feedback may later be reviewed for baseline updates; this prototype does not update a baseline automatically.

Research inputs: Killourhy & Maxion (DSN 2009) studied fixed-password identity detection; Epp et al. (CHI 2011) studied typing rhythms and self-reported emotion; Naegelin et al. (Journal of Biomedical Informatics 2023, DOI 10.1016/j.jbi.2023.104299) studied mouse and keyboard features in a simulated office. None supplies a validated alert cutoff for this product.

Next implementation stage: Windows event collection with sensitive-field exclusion, local SQLite feature storage, consent controls, and a Tauri desktop shell. No Windows collection or desktop notification is implemented yet.

The `desktop/` directory now contains a Tauri 2 + React + TypeScript shell with a Windows-compatible tray menu and an explicit privacy authorization screen. It does not collect input yet; authorization is currently held in memory and resets on restart. Run `cd desktop && npm ci && npm run build` to build the frontend. A native Tauri build additionally needs Rust and platform WebView development libraries; this Linux workspace currently lacks GLib/GObject development files. Windows collection, durable consent, and integration with the Python detection core are still pending.

`capture_mouse.py` is a separate Windows-only mouse collection prototype. Example: `python capture_mouse.py --consent --allow-exe trading.exe`. It polls cursor position and left-button state through Windows APIs, aggregates movement/click statistics into 60-second windows, and writes only window features to `%LOCALAPPDATA%/BehavioralGuard/behavior.sqlite3`. It monitors only explicitly allowed foreground executables and stops a window on focus changes. Classic Win32 password edit controls are skipped; custom password fields cannot yet be identified reliably. It does not collect keyboard data. Physical device identification and actual Windows runtime validation are still pending; use this collector only in controlled evaluation with non-sensitive applications. Each launch deletes aggregate windows and alert records older than 30 days.

The desktop dashboard reads this same local database and shows learning days and recent alerts. Feedback can be recorded, and the delete action signals the standalone collector to stop before removing its data. A Windows GitHub Actions workflow runs Python checks, builds the frontend and checks the Tauri Rust project. It is a build check, not a substitute for an interactive Windows privacy and performance test.

Run `python evaluate.py` for a deterministic synthetic false-alert and persistent-change check. These numbers do not estimate performance in actual trading sessions.

See `WINDOWS_VALIDATION.md` for the standard-user Windows smoke procedure and privacy checks. The short `smoke_windows.py` check keeps samples in memory and writes no database.
