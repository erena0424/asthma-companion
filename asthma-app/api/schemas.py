"""Request/response schemas for the prediction API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

PollenLevel = Literal["Low", "Moderate", "High", "Very High"]


class ClassifierInput(BaseModel):
    """Raw features for tomorrow's flare-up classification (strategy 2, no PEF).

    Production training keeps feature NaNs (only tomorrow's label is required).
    Environment and pollen fields are required. Sensor lags, ``is_flare_up``, and
    ``temp_diff_tomorrow`` may be omitted — send JSON ``null`` when unknown.
    The API maps ``null`` → NaN for XGBoost; do **not** send ``0`` as a stand-in
    for missing wearable data.
    """

    temperature: float
    temperature_min: float
    temperature_max: float
    pressure: float
    humidity: float = Field(..., ge=0, le=100)
    wind_speed: float = Field(..., ge=0)
    wind_deg: float
    aqi: float = Field(..., ge=0)
    co: float = Field(..., ge=0)
    no: float = Field(..., ge=0)
    no2: float = Field(..., ge=0)
    o3: float = Field(..., ge=0)
    so2: float = Field(..., ge=0)
    pm2_5: float = Field(..., ge=0)
    pm10: float = Field(..., ge=0)
    nh3: float = Field(..., ge=0)
    grass_pollen: PollenLevel = "Low"
    tree_pollen: PollenLevel = "Low"
    weed_pollen: PollenLevel = "Low"
    sleep_minutes_lag: Optional[float] = Field(
        None,
        ge=0,
        description="Sleep minutes yesterday; omit or null if unknown",
    )
    sedentary_minutes_lag: Optional[float] = Field(None, ge=0)
    running_minutes_lag: Optional[float] = Field(None, ge=0)
    total_steps_lag: Optional[float] = Field(None, ge=0)
    avg_hr_lag: Optional[float] = Field(None, ge=0)
    temp_diff_tomorrow: Optional[float] = Field(
        None,
        description="Forecast temperature change tomorrow minus today; null if unknown",
    )
    is_flare_up: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="Whether the patient had a flare-up today; null if unknown",
    )
    relief_inhaler: Optional[int] = Field(
        None,
        ge=0,
        description="Relief inhaler use today (questionnaire code); used to derive is_flare_up if omitted",
    )
    daily_day_symp: Optional[bool] = None
    daily_night_symp: Optional[bool] = None
    daily_limit_activity: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "temperature": 12.5,
                    "temperature_min": 8.0,
                    "temperature_max": 15.0,
                    "pressure": 1012.0,
                    "humidity": 72.0,
                    "wind_speed": 3.5,
                    "wind_deg": 210.0,
                    "aqi": 45.0,
                    "co": 0.2,
                    "no": 5.0,
                    "no2": 12.0,
                    "o3": 30.0,
                    "so2": 2.0,
                    "pm2_5": 18.0,
                    "pm10": 25.0,
                    "nh3": 0.5,
                    "grass_pollen": "Low",
                    "tree_pollen": "Moderate",
                    "weed_pollen": "Low",
                    "sleep_minutes_lag": None,
                    "total_steps_lag": None,
                    "is_flare_up": None,
                }
            ]
        }
    }
