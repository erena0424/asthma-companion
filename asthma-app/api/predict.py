"""Run classifier or GINA fallback predictions."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from api.schemas import ClassifierInput
from model.feature_engineering import compute_is_flare_up
from model.inference import (
    classifier_model_available,
    model_available,
    predict_app_gina_fallback,
    predict_classifier,
    predict_gina_fallback,
)


class PatientInput(BaseModel):
    """Simplified inputs for cold-start GINA rules (no full sensor history required)."""

    # App GINA fields (cold-start)
    sens_cold: float = Field(0.5, ge=0.0, le=1.0)
    sens_pollen: float = Field(0.5, ge=0.0, le=1.0)
    sens_dust: float = Field(0.5, ge=0.0, le=1.0)
    temp_change: float
    aqi: float = Field(..., ge=0)
    humidity: float = Field(..., ge=0, le=100)
    pollen_level: int = Field(0, ge=0, le=2)
    cough_today: int = Field(0, ge=0, le=1)
    inhaler_today: int = Field(0, ge=0, le=3)
    sleep_hours: float = Field(..., ge=0)
    steps: float = Field(..., ge=0)
    baseline_sleep_hours: Optional[float] = Field(None, ge=0)
    baseline_steps: Optional[float] = Field(None, ge=0)
    
    # Legacy GINA fields (full clinical)
    force_gina: bool = False
    night_symp: Optional[bool] = None
    day_symp: Optional[bool] = None
    limit_activity: Optional[bool] = None
    relief_inhaler_puffs: Optional[int] = None
    pef_am: Optional[float] = None
    pef_personal_best: Optional[float] = None
    pollen: Optional[float] = None
    temp: Optional[float] = None
    
    # Elena ML fields (BLOCKED on model export - see model/elena_features.py)
    # When Elena exports elena_global_model.joblib + feature_columns.json:
    # - Add watch lag fields: sleep_minutes_lag, sedentary_minutes_lag, running_minutes_lag, 
    #   total_steps_lag, avg_hr_lag
    # - Add env dict (19 columns from /env/daily) or lat/lon/date for auto-fetch
    # - Add user static fields: sex, age_range, severity (if in feature_columns.json)
    # - Wire build_elena_feature_row() → predict_elena_ml() in run_prediction()


def _legacy_gina_fields_complete(inputs: PatientInput) -> bool:
    return all(
        v is not None
        for v in (
            inputs.night_symp,
            inputs.day_symp,
            inputs.limit_activity,
            inputs.relief_inhaler_puffs,
            inputs.pef_am,
            inputs.pef_personal_best,
            inputs.pollen,
            inputs.temp,
        )
    )


def run_classifier_prediction(inputs: ClassifierInput) -> dict:
    """Predict tomorrow's flare-up with the trained XGBoost classifier."""
    if not classifier_model_available():
        raise FileNotFoundError(
            "Classifier artifact missing. Train the model and save to "
            "model/artifacts/flare_classifier.joblib (see moduler_workflow.ipynb)."
        )
    payload = inputs.model_dump()
    if payload.get("is_flare_up") is None:
        derived = compute_is_flare_up(
            payload.get("relief_inhaler"),
            payload.get("daily_day_symp"),
            payload.get("daily_night_symp"),
            payload.get("daily_limit_activity"),
        )
        if derived is not None:
            payload["is_flare_up"] = derived
    for key in ("relief_inhaler", "daily_day_symp", "daily_night_symp", "daily_limit_activity"):
        payload.pop(key, None)
    return predict_classifier(payload)


def run_prediction(inputs: PatientInput) -> dict:
    """
    Predict tomorrow flare risk using GINA cold-start rules.

    Use POST /predict/classifier for the trained ML model.
    """
    # Legacy GINA path (full clinical fields)
    if inputs.force_gina and _legacy_gina_fields_complete(inputs):
        return predict_gina_fallback(
            night_symp=inputs.night_symp,
            day_symp=inputs.day_symp,
            limit_activity=inputs.limit_activity,
            relief_inhaler_puffs=inputs.relief_inhaler_puffs,
            pef_am=inputs.pef_am,
            pef_personal_best=inputs.pef_personal_best,
            aqi=inputs.aqi,
            pollen=inputs.pollen,
            temp=inputs.temp,
        )

    return predict_app_gina_fallback(
        cough_today=inputs.cough_today,
        inhaler_today=inputs.inhaler_today,
        aqi=inputs.aqi,
        pollen_level=inputs.pollen_level,
        temp_change=inputs.temp_change,
        sens_cold=inputs.sens_cold,
        sens_pollen=inputs.sens_pollen,
    )


def health_status() -> dict:
    from db.health import check_db_status

    db_status = check_db_status()
    overall = "ok" if db_status.get("connected") else "degraded"
    return {
        "status": overall,
        "classifier_loaded": classifier_model_available(),
        "any_model_available": model_available(),
        "database": db_status,
        "training": {
            "missing_data_strategy": "xgb_native_nan",
            "peakflow": "not_used",
            "nullable_api_fields": [
                "sleep_minutes_lag",
                "sedentary_minutes_lag",
                "running_minutes_lag",
                "total_steps_lag",
                "avg_hr_lag",
                "temp_diff_tomorrow",
                "is_flare_up",
            ],
        },
    }
