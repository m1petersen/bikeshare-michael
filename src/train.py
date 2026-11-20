"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features
  hgb_log_ratio         the same trees, fit on log(cnt / cnt_roll_7) (Exercise 4)

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train               (valid + test -> reports/metrics.json)
     python -m src.train --valid-only  (valid only -> reports/metrics_valid.json)
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import EXERCISE1_FEATURE, METRICS, METRICS_VALID, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


class LogRatioTarget(BaseEstimator, RegressorMixin):
    """Fit `estimator` on log(y / X[reference]) and predict
    X[reference] * exp(prediction).

    Exercise 4. A tree predicts within the range of its training targets, and
    71 of the 182 validation days exceed the 2011 maximum (6,043), so `hgb`
    on raw counts cannot reach them. The ratio of today to the past week's
    mean has no such ceiling. `reference` must be a lagged feature (known
    before the day), and must be positive.
    """

    def __init__(self, estimator=None, reference: str = "cnt_roll_7"):
        self.estimator = estimator
        self.reference = reference

    def fit(self, X, y):
        ref = X[self.reference].to_numpy(dtype=float)
        if (ref <= 0).any():
            raise ValueError(f"{self.reference} must be positive for a log ratio")
        self.estimator_ = clone(self.estimator).fit(X, np.log(np.asarray(y, dtype=float) / ref))
        return self

    def predict(self, X):
        return X[self.reference].to_numpy(dtype=float) * np.exp(self.estimator_.predict(X))


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
    # Exercise 4: same booster, target log(cnt / cnt_roll_7).
    "hgb_log_ratio": LogRatioTarget(
        HistGradientBoostingRegressor(random_state=0, max_iter=300), "cnt_roll_7"
    ),
}


# The four models in the starter; the report's eight-row table compares
# them with and without EXERCISE1_FEATURE.
STARTER_MODELS = ["baseline_mean", "baseline_persistence", "ridge", "hgb"]


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score(include_test: bool = True) -> dict:
    """Fit every model on train and score it.

    include_test=False scores validation only and never evaluates a model
    on the test rows: use it while iterating, so the test set is consulted
    once, by the final `make all`.
    """
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    parts = [("valid", valid)] + ([("test", test)] if include_test else [])

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
    }
    if include_test:
        results["n_test"] = len(test)

    def score(model, use_cols):
        model = clone(model).fit(train[use_cols], train[TARGET])
        return {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[use_cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[use_cols]))), 1),
            }
            for split, part in parts
        }

    for name, model in MODELS.items():
        results[name] = score(model, cols)

    # Exercise 1 comparison for the report's eight-row table: the four
    # starter models refit without the new feature. Only these four, so the
    # test set is not scored for any extra variant.
    without = [c for c in cols if c != EXERCISE1_FEATURE]
    results[f"without_{EXERCISE1_FEATURE}"] = {
        "features": without,
        **{name: score(MODELS[name], without) for name in STARTER_MODELS},
    }
    return results


if __name__ == "__main__":
    valid_only = "--valid-only" in sys.argv[1:]
    res = fit_and_score(include_test=not valid_only)
    out = METRICS_VALID if valid_only else METRICS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
