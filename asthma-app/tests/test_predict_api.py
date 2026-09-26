"""Legacy POST /predict/classifier and POST /predict endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from model.inference import classifier_model_available

CLASSIFIER_PAYLOAD = {
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
    "sleep_minutes_lag": 420,
    "total_steps_lag": 6500,
    "is_flare_up": 0,
}

GINA_PAYLOAD = {
    "temp_change": -3.0,
    "aqi": 45.0,
    "humidity": 60.0,
    "pollen_level": 1,
    "cough_today": 0,
    "inhaler_today": 1,
    "sleep_hours": 7.0,
    "steps": 6000.0,
}


@pytest.mark.skipif(not classifier_model_available(), reason="Classifier artifact not on disk")
def test_predict_classifier(client: TestClient):
    response = client.post("/predict/classifier", json=CLASSIFIER_PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction_mode"] == "classifier"
    assert "flare_probability" in body
    assert body["risk_level"] in ("Low", "Medium", "High")


def test_predict_classifier_missing_artifact_returns_503(client: TestClient, monkeypatch):
    monkeypatch.setattr("api.predict.classifier_model_available", lambda: False)
    response = client.post("/predict/classifier", json=CLASSIFIER_PAYLOAD)
    assert response.status_code == 503


def test_predict_gina_cold_start(client: TestClient):
    response = client.post("/predict", json=GINA_PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["prediction_mode"] == "gina_app"
    assert "risk_level" in body
    assert body.get("cold_start") is True
