"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from joshua7.api.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("J7_API_KEY", raising=False)
    app = create_app()
    return TestClient(app)

@pytest.fixture
def client_with_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("J7_API_KEY", "sekret")
    app = create_app()
    return TestClient(app)


class TestAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_list_validators(self, client):
        resp = client.get("/api/v1/validators")
        assert resp.status_code == 200
        data = resp.json()
        assert "validators" in data
        assert len(data["validators"]) == 5

    def test_validate_clean(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "We build professional solutions for our valued customers.",
            "validators": ["forbidden_phrases", "pii"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["validators_run"] == 2

    def test_validate_with_pii(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Email me at test@example.com right now.",
            "validators": ["pii"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is False

    def test_validate_all(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Our team is dedicated to quality and innovation in every product we deliver.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["validators_run"] == 5

    def test_validate_empty_text_rejected(self, client):
        resp = client.post("/api/v1/validate", json={"text": ""})
        assert resp.status_code == 422

    def test_response_contains_request_id(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Test content for ID check.",
            "validators": ["forbidden_phrases"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0

    def test_response_contains_timestamp(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Timestamp check.",
            "validators": ["forbidden_phrases"],
        })
        data = resp.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_response_contains_version(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Version check.",
            "validators": ["forbidden_phrases"],
        })
        data = resp.json()
        assert "version" in data
        assert data["version"] != ""

    def test_request_id_header_propagated(self, client):
        resp = client.post(
            "/api/v1/validate",
            json={"text": "Header test.", "validators": ["forbidden_phrases"]},
            headers={"X-Request-ID": "custom-rid-42"},
        )
        assert resp.headers.get("X-Request-ID") == "custom-rid-42"

    def test_response_time_header(self, client):
        resp = client.post("/api/v1/validate", json={
            "text": "Timing check.",
            "validators": ["forbidden_phrases"],
        })
        assert "X-Response-Time-Ms" in resp.headers

    def test_cors_headers(self, client):
        resp = client.options(
            "/api/v1/validate",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code == 200

    def test_pii_not_leaked_in_response(self, client):
        """SECURITY: Ensure raw PII values are never in the API response."""
        resp = client.post("/api/v1/validate", json={
            "text": "Call me at secret@evil.com or 123-45-6789.",
            "validators": ["pii"],
        })
        body = resp.text
        assert "secret@evil.com" not in body
        assert "123-45-6789" not in body

    def test_security_headers_present(self, client):
        """SECURITY: Key security headers must be set on every response."""
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Cache-Control") == "no-store"
        assert "strict-origin" in resp.headers.get("Referrer-Policy", "")

    def test_malformed_request_id_replaced(self, client):
        """SECURITY: Malformed X-Request-ID must be replaced, not echoed."""
        resp = client.post(
            "/api/v1/validate",
            json={"text": "Test.", "validators": ["forbidden_phrases"]},
            headers={"X-Request-ID": "bad\nheader\r\ninjection"},
        )
        rid = resp.headers.get("X-Request-ID", "")
        assert "\n" not in rid
        assert "\r" not in rid

    def test_body_too_large_rejected(self, client):
        """SECURITY: Oversized Content-Length must return 413."""
        resp = client.post(
            "/api/v1/validate",
            json={"text": "x"},
            headers={"Content-Length": "999999999"},
        )
        assert resp.status_code == 413

    def test_docs_disabled_by_default(self, client):
        """SECURITY: /docs should not be available when debug=false."""
        resp = client.get("/docs")
        assert resp.status_code == 404

    def test_api_key_timing_safe(self, client_with_api_key):
        """SECURITY: Missing API key returns 401."""
        resp = client_with_api_key.get("/api/v1/validators")
        assert resp.status_code == 401

    def test_api_key_valid_passes(self, client_with_api_key):
        resp = client_with_api_key.get(
            "/api/v1/validators",
            headers={"X-API-Key": "sekret"},
        )
        assert resp.status_code == 200

    def test_api_key_wrong_value_rejected(self, client_with_api_key):
        resp = client_with_api_key.get(
            "/api/v1/validators",
            headers={"X-API-Key": "wrong"},
        )
        assert resp.status_code == 401
