"""PATCH /v1/users/me and full profile field tests."""

from fastapi.testclient import TestClient

FULL_PROFILE = {
    "name": "Elena M.",
    "date_of_birth": "1998-03-15",
    "emergency_contact": "Alex M. — 555-0100",
    "preferred_reminder": "08:00",
    "contact_method": "Email",
    "preferred_environment": "Low-pollen mornings",
    "care_goal": "Keep symptoms stable during exercise",
    "accessibility_needs": "Large text and clear contrast",
    "trigger_preferences": ["Pollen", "Exercise", "Cold air"],
    "trigger_sensitivities": {"pollen": 0.9, "cold_air": 0.4, "exercise": 0.7},
}


def test_patch_user_profile(client: TestClient, auth_headers: dict):
    response = client.patch("/v1/users/me", json=FULL_PROFILE, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == FULL_PROFILE["name"]
    assert body["date_of_birth"] == FULL_PROFILE["date_of_birth"]
    assert body["emergency_contact"] == FULL_PROFILE["emergency_contact"]
    assert body["care_goal"] == FULL_PROFILE["care_goal"]
    assert "Pollen" in body["trigger_preferences"]
    assert body["trigger_sensitivities"]["pollen"] == 0.9

    me = client.get("/v1/users/me", headers=auth_headers)
    assert me.json()["date_of_birth"] == "1998-03-15"


def test_register_accepts_full_profile(client: TestClient):
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "fullprofile@example.com",
            "password": "password12345",
            **FULL_PROFILE,
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["date_of_birth"] == "1998-03-15"
    assert me.json()["care_goal"] == FULL_PROFILE["care_goal"]


def test_patch_user_requires_auth(client: TestClient):
    response = client.patch("/v1/users/me", json={"name": "Nope"})
    assert response.status_code == 401


def test_patch_profile_image_url(client: TestClient, auth_headers: dict):
    url = "https://res.cloudinary.com/demo/image/upload/v1/avatar.jpg"
    response = client.patch(
        "/v1/users/me",
        json={"profile_image_url": url},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["profile_image_url"] == url

    me = client.get("/v1/users/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["profile_image_url"] == url


def test_patch_setup_wizard_fields(client: TestClient, auth_headers: dict):
    """Frontend SetupPage sends emergency_contacts + symptoms + tracking."""
    payload = {
        "name": "Alex Test",
        "date_of_birth": "1998-03-15",
        "emergency_contacts": [
            {
                "id": "c1",
                "firstName": "Jamie",
                "lastName": "Lee",
                "phone": "(555) 123-4567",
                "email": "jamie@example.com",
            }
        ],
        "trigger_preferences": ["Pollen", "Exercise", "Cold air"],
        "symptoms": ["Wheezing", "Cough", "Shortness of breath"],
        "tracking": ["Wheezing", "Cough"],
    }
    response = client.patch("/v1/users/me", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Alex Test"
    assert len(body["emergency_contacts"]) == 1
    assert body["emergency_contacts"][0]["firstName"] == "Jamie"
    assert "Jamie" in (body["emergency_contact"] or "")
    assert body["symptoms"] == payload["symptoms"]
    assert body["tracking"] == payload["tracking"]

    me = client.get("/v1/users/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["tracking"] == ["Wheezing", "Cough"]
