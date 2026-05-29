"""Smoke tests for the transaction feature pipeline."""

import pandas as pd

from src.data.transaction_features import (
    CATEGORICAL_FEATURES,
    DATE,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET,
    chronological_split,
)


def test_feature_column_invariants():
    """The exported column lists are consistent — no overlap, no orphans."""
    assert set(CATEGORICAL_FEATURES).isdisjoint(NUMERIC_FEATURES)
    assert set(FEATURE_COLUMNS) == set(CATEGORICAL_FEATURES) | set(NUMERIC_FEATURES)
    assert TARGET not in FEATURE_COLUMNS
    assert DATE not in FEATURE_COLUMNS


def test_chronological_split_respects_cutoffs(synthetic_transactions, monkeypatch):
    """Train ≤ train_cutoff < val ≤ val_cutoff < test — no rows shuffled across."""
    from src.data import transaction_features as tf

    # Use cutoffs that actually live inside the synthetic date range.
    monkeypatch.setattr(tf, "TRAIN_END_DATE", "2020-06-30")
    monkeypatch.setattr(tf, "VALIDATION_END_DATE", "2022-06-30")

    train, val, test = chronological_split(synthetic_transactions)

    assert len(train) + len(val) + len(test) == len(synthetic_transactions)
    assert train[DATE].max() <= pd.Timestamp("2020-06-30")
    assert val[DATE].min() > pd.Timestamp("2020-06-30")
    assert val[DATE].max() <= pd.Timestamp("2022-06-30")
    assert test[DATE].min() > pd.Timestamp("2022-06-30")


def test_categorical_dtypes_preserved(synthetic_transactions):
    """The pipeline contract: town / property_type / residential_type are category dtype."""
    for col in CATEGORICAL_FEATURES:
        assert isinstance(synthetic_transactions[col].dtype, pd.CategoricalDtype), col
