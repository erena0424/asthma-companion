"""Tests for Elena env schema helpers."""

from model.elena_env_schema import grains_to_pollen_category, us_aqi_to_openweather_band, validate_env_features


def test_pollen_bucket_mapping():
    assert grains_to_pollen_category(5) == "Low"
    assert grains_to_pollen_category(50) == "Moderate"
    assert grains_to_pollen_category(150) == "High"
    assert grains_to_pollen_category(400) == "Very High"


def test_us_aqi_mapping():
    assert us_aqi_to_openweather_band(40) == 1
    assert us_aqi_to_openweather_band(80) == 2
    assert us_aqi_to_openweather_band(120) == 3
    assert us_aqi_to_openweather_band(180) == 4
    assert us_aqi_to_openweather_band(250) == 5


def test_validate_env_features_fills_pollen_and_nh3_fallback():
    features, missing = validate_env_features(
        {
            "temperature": 10.0,
            "temperature_min": 8.0,
            "temperature_max": 12.0,
            "pressure": 1010.0,
            "humidity": 60.0,
            "wind_speed": 2.0,
            "wind_deg": 90.0,
            "aqi": 2,
            "co": 1.0,
            "no2": 2.0,
            "o3": 3.0,
            "so2": 1.0,
            "pm2_5": 5.0,
            "pm10": 6.0,
        }
    )
    assert features["nh3"] == 1.28
    assert "nh3" not in missing
    assert features["grass_pollen"] in ("Low", "Moderate", "High", "Very High")
    assert "no" in missing
