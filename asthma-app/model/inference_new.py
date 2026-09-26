"""Inference utilities for flare-up classification models."""
from __future__ import annotations

from typing import List

import joblib
import pandas as pd

from .feature_engineering import CATEGORICAL_COLS, binary_valid_features, encode_categorical_features


def predict_dataframe(
    model,
    df: pd.DataFrame,
    X_cols: List[str],
    feature_columns: List[str],
    y_col: str = "tomorrow_flare_up",
    proba_col: str = "flare_probability",
) -> pd.DataFrame:
    """Predict tomorrow's flare-up on a raw feature dataframe."""
    valid_features = binary_valid_features(X_cols)
    X = encode_categorical_features(
        df,
        valid_features,
        CATEGORICAL_COLS,
        reference_columns=feature_columns,
    )
    probs = model.predict_proba(X)[:, 1]
    out = df.copy()
    out[proba_col] = probs
    out["predicted"] = model.predict(X)
    if y_col in out.columns:
        out["actual"] = out[y_col]
    return out


def predict_proba_dataframe(
    model,
    df: pd.DataFrame,
    X: pd.DataFrame,
    proba_col: str = "flare_probability",
) -> pd.DataFrame:
    """Return probabilities from an already-encoded feature matrix."""
    probs = model.predict_proba(X)[:, 1]
    out = df.copy()
    out[proba_col] = probs
    out["predicted"] = (probs >= 0.5).astype(int)
    return out


def save_model(model, path: str, feature_columns: List[str] | None = None) -> None:
    """Persist the classifier and encoded feature column names."""
    payload = {"model": model, "feature_columns": feature_columns}
    joblib.dump(payload, path)


def load_model(path: str):
    """Load a classifier bundle saved with `save_model`."""
    payload = joblib.load(path)
    if isinstance(payload, dict) and "model" in payload:
        return payload
    return {"model": payload, "feature_columns": None}
