"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import pandas as pd
import pytest

from src.config import FORBIDDEN, LAG_WARMUP, TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_every_row_has_a_complete_lag_window(feats):
    """Each surviving row needs all LAG_WARMUP previous calendar days in the
    raw data. test_lags_are_true_calendar_lags skips dates whose previous day
    is missing, so a row-based shift across the 2011-03-10 gap passes it;
    this catches the rows it skips."""
    present = set(load_raw().dteday)
    broken = [
        d.date() for d in feats.dteday
        if any(d - pd.Timedelta(days=k) not in present for k in range(1, LAG_WARMUP + 1))
    ]
    assert not broken, f"rows with an incomplete lag window: {broken}"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


@pytest.mark.parametrize("column, days", [("cnt_roll_7", 7), ("cnt_roll_3", 3)])
def test_rolling_mean_excludes_today(feats, column, days):
    """Every row's rolling mean must equal the mean of the `days` calendar
    days *before* it, taken from the raw counts. Checks all rows, not one
    date, and fails rather than skips if a window is incomplete."""
    by_date = load_raw().set_index("dteday")[TARGET]
    wrong = []
    for date, value in feats.set_index("dteday")[column].items():
        window = [date - pd.Timedelta(days=k) for k in range(1, days + 1)]
        missing = [d for d in window if d not in by_date.index]
        assert not missing, f"{column} on {date.date()}: window days {missing} absent"
        expected = sum(by_date[d] for d in window) / days
        if value != pytest.approx(expected):
            wrong.append((date.date(), value, expected))
    assert not wrong, f"{len(wrong)} rows wrong, first: {wrong[:3]}"


def test_roll_3_is_mean_of_three_previous_days(feats):
    """cnt_roll_3 on 2011-06-15, computed by hand from data/raw/bike_daily.csv:
    cnt on 06-12, 06-13, 06-14 = 4460, 5020, 4891 -> 14371 / 3 = 4790.333.
    Today's count (5180) must not be in it; with it, the mean would be
    (5020 + 4891 + 5180) / 3 = 5030.333."""
    value = feats.set_index("dteday").cnt_roll_3[pd.Timestamp("2011-06-15")]
    assert value == pytest.approx(14371 / 3)


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
