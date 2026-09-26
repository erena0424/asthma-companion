"""Training and evaluation for tomorrow's flare-up classification model.

Production uses **strategy 2** (XGBoost native NaN): only ``tomorrow_flare_up`` is
required; feature NaNs are kept so partial sensor history still trains and scores.
Peak flow (PEF) is not used.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

from .feature_engineering import (
    CATEGORICAL_COLS,
    binary_valid_features,
    encode_categorical_features,
)
from .model import evaluate_classification, feature_importances_df, train_xgb_classifier


def chronological_user_split(
    df: pd.DataFrame,
    train_fraction: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split each user's timeline into chronological train/test portions."""
    train_parts = []
    test_parts = []
    for _, user_df in df.groupby("user_key"):
        user_df = user_df.sort_values("date")
        split_idx = int(len(user_df) * train_fraction)
        train_parts.append(user_df.iloc[:split_idx])
        test_parts.append(user_df.iloc[split_idx:])
    return pd.concat(train_parts, ignore_index=True), pd.concat(test_parts, ignore_index=True)


def per_user_holdout_metrics(
    test_data: pd.DataFrame,
    y_test: pd.Series,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> pd.DataFrame:
    """Compute accuracy, precision, recall, and AUC per user on chronological hold-out."""
    holdout_user_keys = []
    for user, user_df in test_data.groupby("user_key"):
        holdout_user_keys.extend([user] * len(user_df))

    eval_df = pd.DataFrame(
        {
            "user_key": holdout_user_keys,
            "y_true": np.asarray(y_test),
            "y_pred": np.asarray(y_pred),
            "y_proba": np.asarray(y_proba),
        }
    )

    rows = []
    for user, user_eval in eval_df.groupby("user_key"):
        y_true_u = user_eval["y_true"]
        y_pred_u = user_eval["y_pred"]
        row = {
            "user_key": user,
            "n_test_rows": len(user_eval),
            "n_flares": int(y_true_u.sum()),
            "accuracy": accuracy_score(y_true_u, y_pred_u),
            "precision": precision_score(y_true_u, y_pred_u, zero_division=0),
            "recall": recall_score(y_true_u, y_pred_u, zero_division=0),
        }
        if y_true_u.nunique() > 1:
            row["auc"] = roc_auc_score(user_eval["y_true"], user_eval["y_proba"])
        else:
            row["auc"] = np.nan
        rows.append(row)

    return pd.DataFrame(rows).sort_values("user_key").reset_index(drop=True)


def prepare_modeling_frame(
    data: pd.DataFrame,
    X_cols: List[str],
    y_col: str,
) -> pd.DataFrame:
    """Return a chronologically sorted frame ready for training.

    Only tomorrow's label is required. Feature NaNs are kept so XGBoost learns
    native missing-value splits (production strategy: no strict dropna).
    """
    return (
        data.drop_duplicates(subset=["user_key", "date"])
        .dropna(subset=[y_col])
        .sort_values(["user_key", "date"])
        .reset_index(drop=True)
    )


def evaluate_global_chronological(
    data: pd.DataFrame,
    X_cols: List[str],
    y_col: str,
    train_fraction: float = 0.8,
) -> Dict[str, object]:
    """Train a global classifier with per-user chronological hold-out.

    Mirrors Asthma_binary.ipynb cell 9 (~85% accuracy / ~82% recall on hold-out).
    """
    valid_features = binary_valid_features(X_cols)
    temporal_df = prepare_modeling_frame(data, X_cols, y_col)
    train_data, test_data = chronological_user_split(temporal_df, train_fraction)

    X_train = encode_categorical_features(train_data, valid_features, CATEGORICAL_COLS)
    feature_columns = X_train.columns.tolist()
    y_train = train_data[y_col].astype(int)
    X_test = encode_categorical_features(
        test_data,
        valid_features,
        CATEGORICAL_COLS,
        reference_columns=feature_columns,
    )
    y_test = test_data[y_col].astype(int)

    model = train_xgb_classifier(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)

    metrics = evaluate_classification(y_test, preds, probs)
    per_user_df = per_user_holdout_metrics(test_data, y_test, preds, probs)
    return {
        **metrics,
        "model": model,
        "feature_columns": feature_columns,
        "valid_features": valid_features,
        "train_rows": len(train_data),
        "test_rows": len(test_data),
        "y_test": y_test,
        "y_pred": preds,
        "y_proba": probs,
        "per_user_df": per_user_df,
        "importance_df": feature_importances_df(model, feature_columns),
    }


def train_final_model(
    data: pd.DataFrame,
    X_cols: List[str],
    y_col: str,
) -> tuple[object, pd.DataFrame, List[str]]:
    """Train a final global classifier on all labeled rows."""
    valid_features = binary_valid_features(X_cols)
    df = prepare_modeling_frame(data, X_cols, y_col)
    X = encode_categorical_features(df, valid_features, CATEGORICAL_COLS)
    y = df[y_col].astype(int)
    model = train_xgb_classifier(X, y)
    return model, df, X.columns.tolist()
