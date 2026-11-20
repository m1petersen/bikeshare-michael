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
