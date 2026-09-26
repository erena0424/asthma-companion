"""GINA-based rule engine for asthma flare-up risk assessment."""

from __future__ import annotations


def compute_risk(
    night_symp: bool,
    day_symp: bool,
    limit_activity: bool,
    relief_inhaler_puffs: int,
    pef_am: float,
    pef_personal_best: float,
    aqi: float,
    pollen: float,
    temp: float,
) -> dict:
    """Evaluate GINA-style rules and return risk level with triggered rule names."""
    inputs = {
        "night_symp": night_symp,
        "day_symp": day_symp,
        "limit_activity": limit_activity,
        "relief_inhaler_puffs": relief_inhaler_puffs,
        "pef_am": pef_am,
        "pef_personal_best": pef_personal_best,
        "aqi": aqi,
        "pollen": pollen,
        "temp": temp,
    }

    high_rules: list[tuple[str, bool]] = [
        (
            "night_symp with frequent relief inhaler use (>=3 puffs)",
            night_symp and relief_inhaler_puffs >= 3,
        ),
        (
            "pef_am below 60% of personal best",
            _pef_ratio(pef_am, pef_personal_best) is not None
            and _pef_ratio(pef_am, pef_personal_best) < 0.6,
        ),
        (
            "activity limited with frequent relief inhaler use (>=3 puffs)",
            limit_activity and relief_inhaler_puffs >= 3,
        ),
    ]

    medium_rules: list[tuple[str, bool]] = [
        (
            "daytime symptoms with relief inhaler use (>=1 puff)",
            day_symp and relief_inhaler_puffs >= 1,
        ),
        (
            "pef_am between 60% and 80% of personal best",
            _pef_in_range(pef_am, pef_personal_best, 0.6, 0.8),
        ),
        (
            "nighttime symptoms",
            night_symp,
        ),
        (
            "aqi above 100",
            aqi > 100,
        ),
        (
            "high pollen with active symptoms",
            pollen > 50 and (day_symp or night_symp),
        ),
    ]

    triggered = [name for name, fired in high_rules if fired]
    if triggered:
        return {
            "risk_level": "High",
            "triggered_rules": triggered,
            "inputs": inputs,
        }

    triggered = [name for name, fired in medium_rules if fired]
    if triggered:
        return {
            "risk_level": "Medium",
            "triggered_rules": triggered,
            "inputs": inputs,
        }

    return {
        "risk_level": "Low",
        "triggered_rules": ["no high or medium rules triggered"],
        "inputs": inputs,
    }


def _pef_ratio(pef_am: float, pef_personal_best: float) -> float | None:
    if pef_personal_best <= 0:
        return None
    return pef_am / pef_personal_best


def _pef_in_range(
    pef_am: float, pef_personal_best: float, lower: float, upper: float
) -> bool:
    ratio = _pef_ratio(pef_am, pef_personal_best)
    if ratio is None:
        return False
    return lower <= ratio < upper


def compute_app_risk(
    *,
    cough_today: int,
    inhaler_today: int,
    aqi: float,
    pollen_level: int,
    temp_change: float,
    sens_cold: float = 0.5,
    sens_pollen: float = 0.5,
) -> dict:
    """GINA-style rules using App-realistic fields only (no PEF required)."""
    inputs = {
        "cough_today": cough_today,
        "inhaler_today": inhaler_today,
        "aqi": aqi,
        "pollen_level": pollen_level,
        "temp_change": temp_change,
        "sens_cold": sens_cold,
        "sens_pollen": sens_pollen,
    }

    high_rules: list[tuple[str, bool]] = [
        (
            "cough with frequent rescue inhaler use (>=3)",
            cough_today >= 1 and inhaler_today >= 3,
        ),
        (
            "frequent rescue inhaler use (>=3 puffs)",
            inhaler_today >= 3,
        ),
    ]

    medium_rules: list[tuple[str, bool]] = [
        (
            "cough with rescue inhaler use (>=1)",
            cough_today >= 1 and inhaler_today >= 1,
        ),
        (
            "aqi above 100",
            aqi > 100,
        ),
        (
            "high pollen with cough",
            pollen_level >= 2 and cough_today >= 1 and sens_pollen >= 0.5,
        ),
        (
            "cold air drop with cough",
            temp_change <= -5 and cough_today >= 1 and sens_cold >= 0.5,
        ),
    ]

    triggered = [name for name, fired in high_rules if fired]
    if triggered:
        return {"risk_level": "High", "triggered_rules": triggered, "inputs": inputs}

    triggered = [name for name, fired in medium_rules if fired]
    if triggered:
        return {"risk_level": "Medium", "triggered_rules": triggered, "inputs": inputs}

    return {
        "risk_level": "Low",
        "triggered_rules": ["no high or medium rules triggered"],
        "inputs": inputs,
    }


def _run_tests() -> None:
    base_inputs = {
        "night_symp": False,
        "day_symp": False,
        "limit_activity": False,
        "relief_inhaler_puffs": 0,
        "pef_am": 400.0,
        "pef_personal_best": 500.0,
        "aqi": 50.0,
        "pollen": 10.0,
        "temp": 20.0,
    }

    def call(**overrides):
        params = {**base_inputs, **overrides}
        return compute_risk(**params)

    # 1. High: nighttime symptoms with frequent relief inhaler use
    high_relief = call(night_symp=True, relief_inhaler_puffs=3)
    assert high_relief["risk_level"] == "High"
    assert "night_symp with frequent relief inhaler use (>=3 puffs)" in high_relief[
        "triggered_rules"
    ]

    # 2. High: PEF below 60% of personal best
    high_pef = call(pef_am=250.0, pef_personal_best=500.0)
    assert high_pef["risk_level"] == "High"
    assert "pef_am below 60% of personal best" in high_pef["triggered_rules"]

    # 3. Medium: daytime symptoms with any relief inhaler use
    medium_day = call(day_symp=True, relief_inhaler_puffs=1)
    assert medium_day["risk_level"] == "Medium"
    assert "daytime symptoms with relief inhaler use (>=1 puff)" in medium_day[
        "triggered_rules"
    ]

    # 4. Low: no qualifying high or medium rules
    low = call()
    assert low["risk_level"] == "Low"
    assert low["triggered_rules"] == ["no high or medium rules triggered"]

    # 5. Edge cases: 60% PEF boundary is medium; zero personal best skips PEF rules
    medium_boundary = call(pef_am=300.0, pef_personal_best=500.0)
    assert medium_boundary["risk_level"] == "Medium"
    assert "pef_am between 60% and 80% of personal best" in medium_boundary[
        "triggered_rules"
    ]

    zero_best = call(pef_am=100.0, pef_personal_best=0.0)
    assert zero_best["risk_level"] == "Low"
    assert "pef_am below 60% of personal best" not in zero_best["triggered_rules"]

    # 6. App GINA: high cough + frequent inhaler
    app_high = compute_app_risk(cough_today=1, inhaler_today=3, aqi=50, pollen_level=0, temp_change=0)
    assert app_high["risk_level"] == "High"

    # 7. App GINA: low baseline
    app_low = compute_app_risk(cough_today=0, inhaler_today=0, aqi=50, pollen_level=0, temp_change=0)
    assert app_low["risk_level"] == "Low"

    print("All 7 risk_engine tests passed.")


if __name__ == "__main__":
    _run_tests()
