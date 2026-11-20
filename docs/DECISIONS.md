# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-19: Agent is Claude Opus 5.5 via Claude Code on a Claude Pro plan, not an open-weight model. The laptop has 8 GB RAM (below the 16 GB minimum), qwen3.5 has no Ollama cloud tag, and Ollama cloud models require paid credits; the README lists a paid Anthropic plan as a working setup.
- 2026-11-19: Track `reports/` (removed from `.gitignore`) and anchor the ignore rule to `/audit.jsonl`, because the assignment requires committing `reports/metrics.json` and `reports/audit.jsonl`. Deleted a leftover, untracked `reports/metrics.json` from an earlier `make all`. It contained test scores, which were read while surveying the repo and not used for any decision.
- 2026-11-19: The leakage hook now uses `.venv/bin/python` when it exists. Hooks run in Claude Code's environment, where a bare `python` (miniforge) has no pytest, so the hook reported every `src/` edit as a failure (exit 2, "No module named pytest") even with green tests.
- 2026-11-19: Added `make train-valid` (`python -m src.train --valid-only`, writes `reports/metrics_valid.json`) and pointed the `new-feature` skill at it, because `make train` always scored the test set. Moved `test_beats_the_mean_baseline` from test to validation (same 0.4 bound), because `make test` runs after every change. `make train`/`make all` run once, at the end. `metrics_valid.json` is committed so validation changes can be traced to commits. Pre-feature validation R^2: ridge 0.6475, hgb 0.2185, persistence 0.4507, mean -0.9318.
