# Report: daily bikeshare demand, methodology 07

Forecasting daily Capital Bikeshare rides (`cnt`), 2011-2012. Train on
2011 (348 days), validate on H1 2012 (182), test on H2 2012 (184). All
numbers below come from `reports/metrics.json`, written by one `make all`
at commit `02a3192` (`make all` reproduces it: fixed seeds, pinned venv).
Features: 15, listed in `metrics.json`, including the Exercise 1 feature
`cnt_roll_3`.

## Results

| Model | Split | R^2 | MAE (rides/day) |
|---|---|---|---|
| baseline_mean | valid | -0.9318 | 2002.2 |
| baseline_mean | test | -2.1441 | 2847.7 |
| baseline_persistence | valid | 0.4507 | 900.6 |
| baseline_persistence | test | 0.5099 | 840.1 |
| ridge | valid | 0.6439 | 836.5 |
| ridge | test | 0.58 | 946.2 |
| hgb | valid | 0.1983 | 1311.6 |
| hgb | test | -0.5338 | 1998.7 |

Exercise 4's `hgb_log_ratio` is reported in its own section, so this table
compares the four models in the starter.

**When the test set was seen.** The test set was scored once for these
results, after all feature, fault and audit work
(`docs/DECISIONS.md`). Two exposures before that are disclosed there:
- The starter's DECISIONS.md quotes starter test numbers.
- At the start, the agent read a leftover `reports/metrics.json` from an
  earlier `make all`.

Neither informed a choice. After the final run, a few descriptive
analyses were run on test (below, marked *post-hoc*). They change no
model.

**Exercise 1 (`cnt_roll_3`, mean of the previous 3 days).** Validation R^2
fell for both models: ridge 0.6475 -> 0.6439 (-0.0036, noise), and hgb
0.2185 -> 0.1983 (-0.0202). It mostly repeats `cnt_lag_1` and
`cnt_roll_7`. It stays in the feature set because the exercise requires
one; we would drop it otherwise.

**Caveat on every score.** Same-day weather (`temp`, `atemp`, `hum`,
`windspeed`, `weather_severity`) is a feature. It is known on the day but
not in advance, so these are nowcasts with perfect weather knowledge. A
real forecast would use weather forecasts and score lower (see Exercise 5).

## Headline finding

**The gradient-boosted model is worse than predicting yesterday's count:
test R^2 -0.5338 against 0.5099 for persistence. The reason is that it
cannot predict above the highest count it saw in training.** Ridership grew
about 65% from 2011 to 2012.

- The 2011 maximum was 6,043 rides.
- 71 of 182 validation days and 104 of 184 test days are above it.
- hgb's highest test prediction is 5,625 (*post-hoc*); the highest actual
  test day is 8,714.

A tree predicts averages of its training targets, so on more than half of
the test days it cannot reach the right level. It is not overfitting; it
was trained on a different level of demand. Ridge has no ceiling, but it
also underestimates the level: its average error is -508 rides/day on
validation and -551 on test (*post-hoc*), against +16 for persistence.
**Only persistence tracks the level, because it just repeats yesterday.**
Every model in this repo has to be judged against that.

## Exercise 4: changing the target so the tree can extrapolate

We kept the booster's settings and changed what it predicts: instead of
`cnt`, it fits `log(cnt / cnt_roll_7)`, today relative to the past week's
mean. Predictions are `cnt_roll_7 * exp(prediction)`
(`LogRatioTarget` in `src/train.py`). A ratio has no ceiling: when demand is
high, `cnt_roll_7` is high and so is the forecast. The reference column is
a lag whose `.shift(1)` is tested, so nothing from day *d* is used.
`tests/test_contract.py` checks that, and that the inverse is exact.

Seven targets were compared on validation only, before the test set was
scored:

| hgb target | valid R^2 | valid MAE |
|---|---|---|
| `log(cnt / cnt_roll_7)` (chosen) | 0.7450 | 687.9 |
| `cnt - cnt_roll_7` | 0.7209 | 722.4 |
| `log(cnt / cnt_roll_3)` | 0.6886 | 751.2 |
| `log(cnt / cnt_lag_1)` | 0.6148 | 831.8 |
| `cnt - cnt_lag_1` | 0.6251 | 805.4 |
| `cnt` (plain hgb) | 0.1983 | 1311.6 |
| `log(cnt)` | 0.1617 | 1351.3 |

`log(cnt)` alone does not help: it is still a level, still capped by 2011.
What helps is predicting relative to recent demand.

**Test, scored once in the final run:** `hgb_log_ratio` R^2 **0.6169**,
MAE **850.2**. That compares with -0.5338 / 1998.7 for plain hgb.

It is the best test R^2 in the repo, ahead of ridge (0.58) and persistence
(0.5099). But its MAE is still 10 rides/day *worse* than persistence's
840.1. Validation-to-test drop: 0.745 -> 0.617. Part of that is expected,
because the best of seven on 182 days is optimistic.

The target change fixes the tree's extrapolation failure, but on mean
absolute error it does not beat "yesterday again".

## Exercise 5: should we deploy ridge instead of persistence?

**Against.** On test, ridge has the higher R^2 (0.58 vs 0.5099), but it is
**worse on the error that matters operationally**:
- MAE 946.2 vs 840.1, so 106 more rides/day off.
- It is closer than persistence on only 71 of 184 test days.

These two metrics disagree because persistence's few huge misses inflate
squared error. Its five worst test days (around Hurricane Sandy,
2012-10-28 to 10-31, plus two others) carry 30.5% of its squared error. R^2
punishes those days, and MAE does not.

Ridge's lead is also not reliable:
- Paired bootstrap 95% intervals on test (5,000 resamples, *post-hoc*): R^2
  difference -0.037 to +0.195; MAE difference -6.8 to +218.0 rides/day.
  So ridge is "not clearly better on R^2, probably worse on MAE".

Most of its advantage comes from same-day weather that a forecaster would
not have:
- Without the five same-day weather features, ridge's validation R^2 drops
  from 0.6439 to 0.4644 (persistence: 0.4507), and its MAE rises to 1035.5
  (persistence: 900.6).
- On test (*post-hoc*), the same model scores 0.4567 / 1098.0, below
  persistence on both.

**Recommendation:** deploy persistence as the baseline, and don't use ridge
until it beats persistence on MAE using weather *forecasts*, not observed
weather. Its constant underestimate of the level (-551 rides/day on test)
is the first thing to fix.

## Attribution

**Agent:** Claude Opus 5.5 (Anthropic; size not published), via Claude Code
on a Claude Pro plan. We didn't use the open-weight model the lesson
assumes, for three reasons:
- The laptop has 8 GB RAM, under the 16 GB minimum.
- `qwen3.5` had no Ollama cloud tag.
- Ollama cloud needed paid credits.

The README lists a paid Anthropic plan as a working setup.
`agent/audit.py` ran on the same model through the Agent SDK, using the
same login. Exercise 6 (another model size) was skipped: there is only one
model available.

**Written by the agent**, under review at each step:
- **Code:** validation-only training, `make train-valid`, the Makefile's
  venv Python, the `cnt_roll_3` feature, and `LogRatioTarget` /
  `hgb_log_ratio`.
- **Tests:** column classification, raw hash and folder, complete lag
  windows, every-row rolling means, the encoder's unknown label, and the
  log-ratio checks.
- **Agent setup:** the `/run-pipeline` skill, the Bash PreToolUse hook
  `protect_raw.sh`, widening the PostToolUse hook to the whole suite, and
  the hook's venv fix.
- **Fault work:** seeding and fixing the Step 5 bugs and the Exercise 2
  faults.
- **Audits:** running both, and the audit.py test-set guard.
- **Documents:** `docs/SEEDED_FAULTS.md`, `docs/AUDIT.md`, this report and
  CLAUDE.md edits.

**Decided by Michael:**
- Using Claude Opus 5.5 on Pro, and using the existing login for the SDK
  instead of paying for an API key.
- Changing the starter's test and `train.py` so the test set stays unseen.
- Committing the Step 5 bugs as bug/fix pairs.
- `cnt_roll_3` as the feature (to differ from the teammate's) and keeping
  it despite the result.
- Fault 4 as a separate new file, never touching `bike_daily.csv`. Michael
  ran that `cp` himself after the agent's attempt was blocked.
- Widening the hook to the whole suite.
- Strengthening the rolling-mean test.
- Guarding audit.py instead of running it after the final run.
- Which teammate repo to audit.
- When to run the final test evaluation, and that it ran once.
- Rewriting the commit history to remove the agent co-author trailer
  (contents unchanged).

The agent proposed most technical choices, and Michael approved or chose
each. Each decision is a dated line in `docs/DECISIONS.md`, made in the
commit that carries it.
