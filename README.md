# Behavioral Guard detection prototype

This repository currently contains a platform-independent scoring prototype. Run `python simulate.py` from the repository root. It accepts only aggregate metrics per window; no raw input events or typed content are stored.

`behavioral_guard.store.Store` persists aggregate windows, alerts and feedback in a local SQLite database. Sensitive windows are rejected, baseline eligibility is explicit, and `delete_all()` removes personal records. A user marking an alert normal does not silently make its window part of the baseline. Applications embedding this core must provide consent checks before calling the store or detector.

`behavioral_guard.service.Service` connects consent, pause, learning progress, detection, feedback and deletion. It accepts an already aggregated `Window`; the embedding application remains responsible for Windows event capture and sensitive-field exclusion.

The detector uses a separate baseline for each application category, device and time band. Each metric is compared with its personal median and median absolute deviation. Correlated metrics are grouped; the largest deviation in a group represents that group. An alert requires at least two groups above a provisional robust-Z threshold of 2.5 in two of the last three windows, including the current window. Five-window cooldown limits repeat alerts. Insufficient baseline data, low activity, sensitive contexts and transitions suppress scoring.

These thresholds are engineering defaults for simulation and must be calibrated on real, consented data. The 0–100 display value is relative behavioral deviation, not a probability of stress or a diagnosis. Windows marked normal by user feedback may later be reviewed for baseline updates; this prototype does not update a baseline automatically.

Research inputs: Killourhy & Maxion (DSN 2009) studied fixed-password identity detection; Epp et al. (CHI 2011) studied typing rhythms and self-reported emotion; Naegelin et al. (Journal of Biomedical Informatics 2023, DOI 10.1016/j.jbi.2023.104299) studied mouse and keyboard features in a simulated office. None supplies a validated alert cutoff for this product.

Next implementation stage: Windows event collection with sensitive-field exclusion, local SQLite feature storage, consent controls, and a Tauri desktop shell. No Windows collection or desktop notification is implemented yet.
