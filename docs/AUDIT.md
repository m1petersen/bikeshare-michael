# Audit (Exercise 3)

Two audits, each with the auditor's findings first and the verdict in its
own section. The findings are the auditor's words, shortened. The verdicts
are ours, and each one was checked against the source before writing it.

Agent for both: Claude Opus 5.5 via Claude Code (Claude Pro plan).
Neither audit scored the test set (H2 2012): the teammate auditor was told
not to, and `agent/audit.py` blocks it (see `docs/DECISIONS.md`). After the
run, `reports/metrics.json` still did not exist.

---

## 1. Teammate's repo, with `/leakage-auditor`

**Repo:** `github.com/ishaantibdewal/bikeshare-open`, cloned outside this
repo. **Diff reviewed:** `07b276d..HEAD` (11 commits): Exercise 1 feature
`weather_severity_lag_1`, faults 1-3 seeded and fixed, and a hash check on
the raw CSV.

**How it ran:** the `leakage-auditor` subagent (`.claude/agents/leakage-auditor.md`),
read-only. It ran their suite with our venv, excluding the one test that
scores test (`16 passed, 1 deselected`), plus one validation-only script.

### Auditor's findings

**Finding 1 (check 2, temporal ordering): the test split is scored on every
iteration.**
- **Where:** `tests/test_contract.py:59-65` (`test_beats_the_mean_baseline`,
  unchanged from the starter), `src/train.py:84`, and
  `.claude/skills/new-feature/SKILL.md:29`.
- **Scenario:** the skill runs `make features && make test && make train`.
  - `make test` fits ridge on 2011 and asserts test R^2 > 0.4.
  - `make train` computes and prints test R^2 and MAE for every model.
  
  So every red/green cycle in the diff (the feature, each fault and fix)
  scored H2 2012. A test-set pass/fail also gated which features were kept.
  This contradicts `docs/DECISIONS.md:10` ("Test set touched once, after all
  feature work"). How many times it happened is not recorded.
- **Fix:** score that test on validation; make `fit_and_score` validation-only
  unless a final flag is given; correct the DECISIONS entry.

**Finding 2 (check 5, baselines): the keep decision for the feature has no
baselines next to it.**
- **Where:** `docs/DECISIONS.md:11`. The feature is kept on validation R^2
  ridge 0.6475 -> 0.6670 and hgb 0.2185 -> 0.2437.
- **Scenario:** on validation, persistence scores 0.4507 (mean baseline
  -0.9318). Even after its gain, hgb is 0.21 below "yesterday again", yet its
  gain is cited as support. Ridge's gain is real, and ridge beats persistence.
- **Fix:** add both baselines to the entry, and say hgb remains below
  persistence.

**Checks:**

| Check | Result | Evidence |
|---|---|---|
| 1. Target leakage | pass | 15 features, none in FORBIDDEN, none restating `casual + registered` |
| 2. Temporal ordering | **fail** | Finding 1. Otherwise fine: `.shift(1)` restored, new lag shifted, split by date, scaler fit on train only |
| 3. Calendar gaps | pass | New lag built after `reindex_to_calendar`; 0 mismatches on 714 rows against the raw previous day |
| 4. Silent row loss | pass | 728 -> 714 rows, exactly the bound of 14; fault 3 has a direct test |
| 5. Unreported baseline | **fail** (write-up only) | Finding 2. `src/train.py` still reports both baselines |

It reproduced their validation numbers exactly (ridge 0.6670, MAE 803.9;
hgb 0.2437).

### Verdict

**Both findings confirmed; neither is target leakage.** We checked Finding 1
in their source: `test_beats_the_mean_baseline` uses
`train, _, test = temporal_split(feats)` and asserts on `test`,
`fit_and_score` loops over `("valid", valid), ("test", test)`, and the skill's
step 4 runs `make train`.

The feature itself is sound. Its validation gain for ridge (+0.0195) is
above the 0.01 noise threshold, and ridge beats persistence on validation.
But the repo cannot claim the test set was touched once. Their H2 2012 score
is no longer a clean held-out estimate, even though no test number appears
to have been used deliberately.

Finding 2 is a reporting gap, fixed by editing one line. **Recommended to
the teammate:** the Finding 1 fix (we made the same change in our repo, at
commit `168b628`), and a DECISIONS line saying the test split was scored
during iteration. We opened no PR and changed nothing in their repo.

---

## 2. Our own repo, with `agent/audit.py`

**Run:**
```
AUDIT_MODEL=claude-opus-5-5 .venv/bin/python agent/audit.py <this repo> --out reports/audit.jsonl
```
It ran with `ANTHROPIC_BASE_URL/AUTH_TOKEN/API_KEY` unset, so it used the
existing Claude login. Output: `audited 1 repos; 0 flagged`. Raw result:
`reports/audit.jsonl`.

### Auditor's findings

Summary: `leakage: none`, `temporal_ok: true`, `baseline_reported: true`,
`reproducible: true`, `confidence: high`.

1. **`Makefile:7`:** targets call bare `python`. Without the venv active,
   `make test` fails (no pytest), and `make train-valid` runs on the system
   sklearn 1.8.0 instead of the pinned 1.9.1. That gives different scores:
   hgb validation R^2 0.2564 instead of 0.1983, and hgb_log_ratio 0.7482
   instead of 0.7450. Reproducing the results depends on activating the
   venv by hand.
2. **`README.md:25`:** says `make test` runs 14 tests; there are 24.
3. **`src/features.py:69`:** same-day weather (temp, atemp, hum, windspeed,
   weather_severity) is used as a feature. `check_identity` confirms it is
   not leakage. But the scores assume perfect knowledge of the day's weather,
   which a real forecaster would only have as a forecast.

### Verdict

- **Finding 1: confirmed, and it matters for the "reproducible from a clean
  checkout" requirement.** It is the same problem the hook had in S1. Fixed
  in the commit after this one: the Makefile now uses `.venv/bin/python` when
  it exists.
- **Finding 2: confirmed, documentation only.** The README count is updated
  in the same commit.
- **Finding 3: agreed as a disclosure, not an error.** Same-day weather is
  how the starter frames the task (`src/config.py` calls it "known to a
  forecaster on the day"). `REPORT.md` will state that the scores assume
  observed same-day weather, so they are an upper bound on real forecasting
  skill.
