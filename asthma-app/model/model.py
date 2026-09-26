"""Model utilities: create, train and evaluate XGBoost models.
"""
from __future__ import annotations

from typing import Dict, Any, Sequence
import numpy as np
import pandas as pd

import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)


def get_xgb_regressor(params: Dict[str, Any] = None) -> xgb.XGBRegressor:
    """Return an XGBRegressor with reasonable defaults; override with `params`."""
    default = dict(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        enable_categorical=True,
    )
    if params:
        default.update(params)
    return xgb.XGBRegressor(**default)


def train_xgb_model(X_train: pd.DataFrame, y_train: pd.Series, params: Dict[str, Any] = None) -> xgb.XGBRegressor:
    model = get_xgb_regressor(params)
    model.fit(X_train, y_train)
    return model


def evaluate_regression(model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    return {"mse": float(mse), "r2": float(r2)}


def feature_importances_df(model, feature_names) -> pd.DataFrame:
    fi = getattr(model, "feature_importances_", None)
    if fi is None:
        return pd.DataFrame()
    return pd.DataFrame({"feature": feature_names, "importance": fi}).sort_values("importance", ascending=False)


def get_xgb_classifier(params: Dict[str, Any] = None) -> xgb.XGBClassifier:
    """Return an XGBClassifier with defaults from Asthma_binary."""
    default = dict(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        eval_metric="logloss",
    )
    if params:
        default.update(params)
    return xgb.XGBClassifier(**default)


def scale_pos_weight(y: Sequence) -> float:
    """Compute class weight for imbalanced binary targets."""
    y_arr = np.asarray(y)
    positives = y_arr.sum()
    return float((len(y_arr) - positives) / max(1, positives))


def train_xgb_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    params: Dict[str, Any] = None,
    use_class_weight: bool = True,
) -> xgb.XGBClassifier:
    model_params = dict(params or {})
    if use_class_weight and "scale_pos_weight" not in model_params:
        model_params["scale_pos_weight"] = scale_pos_weight(y_train)
    model = get_xgb_classifier(model_params)
    model.fit(X_train, y_train)
    return model


def evaluate_classification(
    y_true: Sequence,
    y_pred: Sequence,
    y_proba: Sequence | None = None,
) -> Dict[str, float]:
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }
    if y_proba is not None and len(np.unique(y_true)) > 1:
        metrics["auc"] = float(roc_auc_score(y_true, y_proba))
    else:
        metrics["auc"] = float("nan")
    return metrics
