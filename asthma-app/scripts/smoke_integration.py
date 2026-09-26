#!/usr/bin/env python3
"""Smoke-test auth + profile against a running local API."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
EMAIL = "smoke_test@example.com"
PASSWORD = "password12345"


def request(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read().decode()
            return resp.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {"detail": payload}


def main() -> int:
    print("1. GET /health")
    status, health = request("GET", "/health")
    print(f"   {status} classifier_loaded={health.get('classifier_loaded')} db={health.get('database', {}).get('connected')}")
    if status != 200:
        return 1

    print("2. POST /v1/auth/register (ignore 409 if already exists)")
    status, reg = request(
        "POST",
        "/v1/auth/register",
        {"email": EMAIL, "password": PASSWORD, "name": "Smoke Tester"},
    )
    token = reg.get("access_token")
    if status == 409:
        print("   user exists — logging in")
        status, login = request("POST", "/v1/auth/login", {"email": EMAIL, "password": PASSWORD})
        token = login.get("access_token")
    if status not in (200, 201) or not token:
        print(f"   FAIL {status} {reg}")
        return 1
    print("   OK")

    print("3. GET /v1/users/me")
    status, me = request("GET", "/v1/users/me", token=token)
    print(f"   {status} email={me.get('email')}")
    if status != 200:
        return 1

    print("4. PATCH /v1/users/me (setup-wizard fields)")
    status, patched = request(
        "PATCH",
        "/v1/users/me",
        {
            "emergency_contacts": [
                {
                    "id": "smoke-1",
                    "firstName": "Alex",
                    "lastName": "Helper",
                    "phone": "(555) 010-0200",
                    "email": "alex@example.com",
                }
            ],
            "trigger_preferences": ["Pollen"],
            "symptoms": ["Wheezing", "Cough"],
            "tracking": ["Wheezing"],
        },
        token=token,
    )
    contacts = patched.get("emergency_contacts") or []
    print(
        f"   {status} contacts={len(contacts)} "
        f"symptoms={patched.get('symptoms')} tracking={patched.get('tracking')}"
    )
    if status != 200:
        print(f"   FAIL {patched}")
        return 1
    if len(contacts) != 1 or not patched.get("emergency_contact"):
        print(f"   FAIL emergency_contacts not persisted: {patched}")
        return 1
    if patched.get("symptoms") != ["Wheezing", "Cough"]:
        print(f"   FAIL symptoms not persisted: {patched}")
        return 1
    if patched.get("tracking") != ["Wheezing"]:
        print(f"   FAIL tracking not persisted: {patched}")
        return 1

    print("5. GET /v1/forecasts (empty list OK)")
    status, forecasts = request("GET", "/v1/forecasts", token=token)
    print(f"   {status} items={len(forecasts.get('items', []))}")
    if status != 200:
        print(f"   FAIL {forecasts}")
        return 1

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
