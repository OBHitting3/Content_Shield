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

    def test_api_key_not_required_when_not_set(self, client):
        resp = client.get("/api/v1/validators")
        assert resp.status_code == 200

    def test_api_key_wrong_rejected_when_set(self, client_with_api_key):
        resp = client_with_api_key.get("/api/v1/validators", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid or missing API key"}

    def test_api_key_correct_allows_when_set(self, client_with_api_key):
        resp = client_with_api_key.get("/api/v1/validators", headers={"X-API-Key": "sekret"})
        assert resp.status_code == 200
