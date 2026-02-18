"""Tests for the FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from joshua7.api.main import create_app


@pytest.fixture
def client():
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
