import os
import time

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from app import main

HEADERS = {"X-API-Key": "test-key"}


def payload(**overrides):
    base = {
        "session_id": "s1",
        "student_id": "stu_1",
        "timestamp": time.time(),
        "attention_score": 80,
        "ear": 0.3,
        "yaw": 1.5,
        "pitch": 0.0,
        "roll": 0.0,
    }
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list(client):
    r = client.post("/attention", json=payload(), headers=HEADERS)
    assert r.status_code == 201
    rows = client.get("/attention?student_id=stu_1", headers=HEADERS).json()
    assert len(rows) == 1
    assert rows[0]["attention_score"] == 80


def test_requires_api_key(client):
    assert client.post("/attention", json=payload()).status_code == 401
    assert client.post("/attention", json=payload(), headers={"X-API-Key": "x"}).status_code == 401
    assert client.get("/attention").status_code == 401


@pytest.mark.parametrize(
    "bad", [{"attention_score": 101}, {"attention_score": -1}, {"ear": 2}, {"student_id": ""}]
)
def test_validation(client, bad):
    r = client.post("/attention", json=payload(**bad), headers=HEADERS)
    assert r.status_code == 422
