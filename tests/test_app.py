"""Endpoint behavior. Each endpoint exists to produce one representative span."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_boom_raises_the_deliberate_failure(client: TestClient):
    with pytest.raises(RuntimeError, match="deliberate sandbox failure"):
        client.get("/boom")
