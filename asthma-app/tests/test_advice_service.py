"""Unit tests for advice_service JSON parsing."""

import json

import pytest

from services.advice_service import _parse_json_response, _repair_json


def test_parse_json_response_plain():
    data = _parse_json_response('{"summary": "Hi", "sections": [], "disclaimer": "D"}')
    assert data["summary"] == "Hi"


def test_parse_json_response_code_fence():
    raw = '```json\n{"summary": "Hi", "sections": []}\n```'
    data = _parse_json_response(raw)
    assert data["summary"] == "Hi"
    assert "disclaimer" in data


def test_parse_json_response_trailing_comma():
    raw = '{"summary": "Hi", "sections": [{"title": "A", "body": "B",},],}'
    data = _parse_json_response(raw)
    assert data["summary"] == "Hi"
    assert len(data["sections"]) == 1


def test_repair_json_removes_trailing_commas():
    fixed = _repair_json('{"a": 1,}')
    json.loads(fixed)


def test_parse_json_response_raises_on_invalid():
    with pytest.raises(json.JSONDecodeError):
        _parse_json_response("not json at all")
