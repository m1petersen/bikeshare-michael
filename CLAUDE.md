# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make data` - download raw CSV and assert its shape
- `make features` - build `data/processed/features.parquet`
- `make train` - fit models, write `reports/metrics.json` (scores TEST)
- `make train-valid` - validation only, `reports/metrics_valid.json`.
  Use this (or `/run-pipeline`) while iterating.
- `make test` - pytest; run this before claiming anything works
- `make all` - the three pipeline stages in order

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `src/config.py` lists these and the
  other excluded columns (`cnt_2d_bfr`, raw time indexes) with the reason
  for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag or rolling feature must be built on a gap-free calendar
  index (`src.features.reindex_to_calendar`) and must `.shift(1)` before
  it aggregates. Add a test for it in `tests/test_leakage.py`.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.
- The test set is scored once, by `/run-pipeline final`, and only when
  Michael asks for it in his own message. Any change after it is reported
  as test-informed.
- `data/raw/` is immutable and a person changes it, never the agent. A new
  raw column must be put in a group in `src/config.py`.
- Log every decision as a dated line in `docs/DECISIONS.md`.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Modules are runnable: `python -m src.<module>` prints a one-line `OK ...`
  summary.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error;
  `hgb_log_ratio` (Exercise 4) is the fix, kept beside plain `hgb`.
- The Bash hook (`protect_raw.sh`) matches command text, so a heredoc that
  merely quotes a write to `data/raw` is blocked. Write docs with Edit.
- Agent here: Claude Opus 5.5 via Claude Code (Pro plan). The git-ignored
  `.claude/settings.local.json` overrides the repo's Ollama settings.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. Expect it in
  any residual plot.
