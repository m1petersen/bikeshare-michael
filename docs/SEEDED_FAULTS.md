# Seeded faults

Each fault was made with Claude Code's Edit tool, so the PostToolUse hook
(`.claude/hooks/check_leakage.sh`, which runs `tests/test_leakage.py`) saw
it, and was committed on its own before the fix. "Turns to fix" counts the
agent's tool calls from seeing the failure to a green `make test`.

Agent: Claude Opus 5.5 via Claude Code (Claude Pro plan).

## Step 5 bugs (lesson), re-created before Exercise 2

### B1. Calendar gap: `reindex_to_calendar` not called

**Change** (`src/features.py`, `build_features`):

```diff
-    out = reindex_to_calendar(df.sort_values("dteday").reset_index(drop=True)).copy()
+    out = df.sort_values("dteday").reset_index(drop=True).copy()
```

**Effect.** 721 rows instead of 714. The 7 days after the missing
2011-03-10 survive with wrong lags: `cnt_lag_1` on 2011-03-11 is the count
from 2011-03-09 (a two-day lag), `cnt_lag_7` on 2011-03-11 to 2011-03-16 is
an eight-day lag, and `cnt_roll_7` mixes in an eighth day for a week.

| date | `cnt_lag_1` | true d-1 | `cnt_lag_7` | true d-7 |
|---|---|---|---|---|
| 2011-03-11 | 1891 | missing | 1685 | 1944 |
| 2011-03-12 | 1977 | 1977 | 1944 | 2077 |
| 2011-03-13 | 2132 | 2132 | 2077 | 605 |
| 2011-03-17 | 2192 | 2192 | 1891 | missing |

**Tests.** Green: `16 passed`. **Hook stderr:** none (exit 0).

**Why nothing caught it.** `test_lags_are_true_calendar_lags` skips any
date whose previous calendar day is absent, which is exactly the broken
row. `cnt_lag_7` has no test, and `test_rolling_mean_excludes_today`
checks one date (row 200) far from the gap. `test_calendar_is_complete_before_lagging`
tests `reindex_to_calendar` itself, not that `build_features` calls it.
The row-loss test sets an upper bound only, and losing fewer rows passes it.

**Fix** (commit after the bug). Added `test_every_row_has_a_complete_lag_window`
to `tests/test_leakage.py`: every surviving row must have all `LAG_WARMUP`
previous calendar days in the raw data. Run against the bug, it goes red
(output trimmed; pytest prints the dates as `datetime.date(2011, 3, 11)`):

```
FAILED tests/test_leakage.py::test_every_row_has_a_complete_lag_window
AssertionError: rows with an incomplete lag window: [2011-03-11, 2011-03-12,
2011-03-13, 2011-03-14, 2011-03-15, 2011-03-16, 2011-03-17]
1 failed, 16 passed
```

Then restored the `reindex_to_calendar` call: `17 passed`, 714 rows. The
hook stayed silent on the restoring edit (tests green). Because the new
test is in `tests/test_leakage.py`, the hook now catches this bug on any
future `src/` edit.

**Turns to fix:** 6 tool calls (add test and import, run twice to read
the failure, restore the call, verify).

### B2. Silent weather map: plain `.map()` without `BAD`

**Change** (`src/features.py`, `build_features`):

```diff
-    out["weather_severity"] = encode_weather(out.weather)
+    out["weather_severity"] = out.weather.map({"GOOD": 0, "MISTY": 1})
```

**Effect.** `BAD` maps to NaN, and the final `dropna()` deletes those rows
without any message: 694 rows instead of 714, and all 20 BAD-weather days
in the raw data are gone.

**Tests.** Red in `make test`:

```
FAILED tests/test_contract.py::test_only_expected_rows_are_dropped
AssertionError: lost 34 rows; expected at most 14
1 failed, 16 passed
```

**Hook stderr:** none (exit 0). The hook runs only `tests/test_leakage.py`,
and the row-loss test is in `tests/test_contract.py`, so the agent is not
told at edit time; only a full `make test` shows it.

**Fix** (commit after the bug). Restored `encode_weather(out.weather)`:
`17 passed`, 714 rows. **Turns to fix:** 2 tool calls (restore, verify).

The same commit closes the blind spot: the hook now runs `pytest tests/`
(the whole suite, ~1.3 s) instead of only `tests/test_leakage.py`. Run
against the B2 bug commit (in a temporary worktree), the hook now exits 2
with:

```
Tests failed after editing src/features.py:
FAILED tests/test_contract.py::test_only_expected_rows_are_dropped - Assertio...
1 failed, 16 passed
```
