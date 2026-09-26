"""Build Elena-compatible encoded feature row from API inputs.

This module transforms raw patient inputs into the exact feature format expected by
Elena's XGBClassifier from Asthma_binary.ipynb, including:
- Computing is_flare_up from today's symptoms
- Merging watch lags, env features, and user static fields
- Applying get_dummies() to match feature_columns.json

BLOCKED: Requires Elena to export:
  - saved_models/elena_global_model.joblib
  - saved_models/feature_columns.json
  - (optional) daily_merged.csv for validation

See docs/ELENA_HANDOFF.md for export instructions.
"""

from __future__ import annotations

import pandas as pd


def build_elena_feature_row(
    *,
    # Today's questionnaire (compute is_flare_up)
    night_symp: bool,
    day_symp: bool,
    limit_activity: bool,
    relief_inhaler_puffs: int,
    # Yesterday's watch lags (from HealthKit / device sync)
    sleep_minutes_lag: float,
    sedentary_minutes_lag: float,
    running_minutes_lag: float,
    total_steps_lag: float,
    avg_hr_lag: float,
    # Environment features (19 columns from /env/daily)
    env: dict,
    # User static fields (if needed by feature_columns.json)
    sex: str | None = None,
    age_range: str | None = None,
    severity: str | None = None,
) -> pd.DataFrame:
    """
    Build a single-row DataFrame matching Elena's encoded feature columns.

    Args:
        night_symp: Nighttime symptoms today
        day_symp: Daytime symptoms today
        limit_activity: Activity limited today
        relief_inhaler_puffs: Number of rescue inhaler puffs today
        sleep_minutes_lag: Yesterday's sleep minutes
        sedentary_minutes_lag: Yesterday's sedentary minutes
        running_minutes_lag: Yesterday's running minutes
        total_steps_lag: Yesterday's total steps
        avg_hr_lag: Yesterday's average heart rate
        env: Dict with 19 env columns (temperature, aqi, pollutants, pollen categories)
        sex: User sex (if categorical in model)
        age_range: User age range (if categorical in model)
        severity: Asthma severity (if categorical in model)

    Returns:
        pd.DataFrame with columns matching feature_columns.json, ready for model.predict()

    Raises:
        NotImplementedError: Until Elena exports model artifacts
    """
    raise NotImplementedError(
        "Elena feature encoding pipeline not yet implemented.\n"
        "Blocked on Elena's model export (see docs/ELENA_HANDOFF.md):\n"
        "  - saved_models/elena_global_model.joblib\n"
        "  - saved_models/feature_columns.json\n"
        "\n"
        "Once exported, implement:\n"
        "  1. Compute is_flare_up = (relief_inhaler_puffs >= 3) OR "
        "(night_symp AND day_symp AND limit_activity)\n"
        "  2. Merge watch lags + env dict + user static fields into single dict\n"
        "  3. Create DataFrame and apply pd.get_dummies() for categorical columns\n"
        "     (grass_pollen, tree_pollen, weed_pollen, sex, age_range, severity, etc.)\n"
        "  4. Align to feature_columns.json with .reindex(columns=..., fill_value=0)\n"
        "  5. Return single-row DataFrame\n"
        "\n"
        "Example implementation sketch:\n"
        "  is_flare_up = (relief_inhaler_puffs >= 3) or "
        "(night_symp and day_symp and limit_activity)\n"
        "  row = {\n"
        "      'is_flare_up': int(is_flare_up),\n"
        "      'sleep_minutes_lag': sleep_minutes_lag,\n"
        "      'sedentary_minutes_lag': sedentary_minutes_lag,\n"
        "      'running_minutes_lag': running_minutes_lag,\n"
        "      'total_steps_lag': total_steps_lag,\n"
        "      'avg_hr_lag': avg_hr_lag,\n"
        "      **env,  # 19 env columns\n"
        "  }\n"
        "  if sex: row['sex'] = sex\n"
        "  if age_range: row['age_range'] = age_range\n"
        "  if severity: row['severity'] = severity\n"
        "  df = pd.DataFrame([row])\n"
        "  df = pd.get_dummies(df, columns=['grass_pollen', 'tree_pollen', 'weed_pollen', ...], "
        "drop_first=True)\n"
        "  # Load feature_columns.json and align\n"
        "  return df.reindex(columns=feature_columns, fill_value=0)\n"
    )
