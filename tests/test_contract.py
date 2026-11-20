"""Guard rails on the ingest contract and the trained model's behaviour."""
import hashlib

import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import COLUMN_GROUPS, LAG_WARMUP, RAW, RAW_FEATURE_COLS, RAW_SHA256, TARGET
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw
from src.train import MODELS, temporal_split


def test_raw_file_is_unchanged():
    """data/raw/bike_daily.csv is immutable; its hash must match the one
    recorded in src/config.py."""
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == RAW_SHA256


def test_raw_folder_holds_only_the_raw_file():
    """Nothing else may appear in data/raw/: a stray copy there is unreviewed
    data one path change away from being loaded. `.DS_Store` (macOS Finder
    metadata) is the one exception."""
    allowed = {RAW.name, ".DS_Store"}
    extra = sorted(p.name for p in RAW.parent.iterdir() if p.name not in allowed)
    assert not extra, f"unexpected files in data/raw/: {extra}"


def column_problems(columns) -> list[str]:
    """Raw columns in no group, or in more than one."""
    problems = []
    for col in columns:
        groups = [name for name, cols in COLUMN_GROUPS.items() if col in cols]
        if len(groups) != 1:
            problems.append(f"{col}: {groups or 'unclassified'}")
    return problems


def test_every_raw_column_is_classified():
    """Each column in data/raw/bike_daily.csv must be in exactly one group in
    src/config.py. An unclassified numeric column would otherwise pass through
    feature_columns() into the model without anyone deciding it should."""
    header = pd.read_csv(RAW, nrows=0).columns
    problems = column_problems(header)
    assert not problems, f"classify these in src/config.py: {problems}"


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_raw_features_are_only_the_classified_ones(raw, feats):
    """Every raw column that reaches the model is one we chose to use as-is."""
    used_raw = set(feature_columns(feats)) & set(raw.columns)
    assert used_raw == RAW_FEATURE_COLS, f"unexpected raw features: {used_raw ^ RAW_FEATURE_COLS}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result.

    Scored on validation, not test: `make test` runs on every edit, and a
    test-set check here would consult the test set hundreds of times."""
    cols = feature_columns(feats)
    train, valid, _ = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(valid[TARGET], ridge.predict(valid[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS
