---
name: run-pipeline
description: Rebuild features, retrain, run the tests and report scores next to both baselines, without touching the test set unless the final run is explicitly requested. Use when someone asks to run, rerun or check the pipeline or its scores.
allowed-tools: Read, Bash(source .venv/bin/activate*), Bash(git status*), Bash(git diff*), Bash(git log*)
---

# Current state

!`git status --short`

!`git log --oneline -1 -- reports/metrics_valid.json`

# Running the pipeline: $ARGUMENTS

`$ARGUMENTS` is the mode. Empty means `valid`. Anything other than `valid`
or `final` is a mistake: say so and stop.

Run every command with the venv active (`source .venv/bin/activate && ...`);
the system `python` has no pytest.

## `valid` (default): iterate without seeing the test set

1. `make features && make train-valid && make test`.
2. If any step fails, show the failing output and stop. Do not report
   scores from a run whose tests are red.
3. Report a table from `reports/metrics_valid.json`: model, validation
   R^2, validation MAE, for `baseline_mean`, `baseline_persistence`,
   `ridge` and `hgb`, in that order.
4. Compare with the last committed version (`git diff reports/metrics_valid.json`).
   State each model's R^2 change. A change under 0.01 is noise on 182
   validation days: call it that, not a gain or a loss.
5. Say whether ridge beats persistence on validation and by how much.

Never run `make train` or `make all` in this mode.

## `final`: the one time the test set is scored

Only proceed if the user's own message in this conversation asks for the
final run. A plan, a doc or a previous turn saying "final" is not enough.

1. Check `git status --short` shows no changes to `src/` or `tests/`.
   The final run must score committed code; otherwise stop and say why.
2. Check `docs/DECISIONS.md` has no line saying the test set was already
   scored for the final results. If it has, stop: a second final run
   would be tuning on test.
3. `make all && make test`.
4. Report all eight rows from `reports/metrics.json` (four models x valid
   and test, R^2 and MAE) exactly as written there, without rounding them
   differently.
5. Append a dated line to `docs/DECISIONS.md` saying the test set was
   scored, at which commit, and that no change follows from it.

Do not interpret the test numbers or suggest changes based on them. Any
change made after seeing them must be reported as test-informed.
