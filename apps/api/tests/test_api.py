import io
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///" + str(ROOT / "data" / "test-docflow.db")
os.environ["STORAGE_PATH"] = str(ROOT / "data" / "test-storage")
os.environ["SEED_DEMO"] = "false"

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def auth_headers(client: TestClient) -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "demo@example.com",
            "password": "Password1!",
            "full_name": "Demo User",
            "organization": "Harbor Labs",
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_register_creates_tenant_and_login(client):
    headers = auth_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "owner"
    assert body["email"] == "demo@example.com"


def test_document_pipeline_executes_steps(client):
    headers = auth_headers(client)
    wf = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name": "Invoice Intake",
            "description": "test",
            "trigger": "on_upload",
            "steps": [
                {"key": "ocr", "type": "extract_text", "config": {}},
                {"key": "classify", "type": "classify", "config": {}},
                {"key": "fields", "type": "extract_fields", "config": {}},
                {"key": "notify", "type": "notify", "config": {"subject": "done"}},
            ],
        },
    )
    assert wf.status_code == 200, wf.text
    invoice = b"TAX INVOICE\nInvoice No: INV-9\nAmount Due: USD 12.50\nBill To: Acme"
    up = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("inv.txt", io.BytesIO(invoice), "text/plain")},
    )
    assert up.status_code == 200, up.text
    doc = up.json()
    assert doc["classification"] == "invoice"
    assert doc["status"] == "ready"
    detail = client.get(f"/api/v1/documents/{doc['id']}/detail", headers=headers)
    assert "INV-9" in detail.json()["ocr"]["text"]
    runs = client.get("/api/v1/workflows/runs/recent", headers=headers)
    assert runs.status_code == 200
    assert runs.json()[0]["status"] == "completed"
    assert any(s["status"] == "completed" for s in runs.json()[0]["steps"])


def test_rbac_viewer_cannot_upload(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"email": "view@example.com", "full_name": "V", "password": "Password1!", "role": "viewer"},
    )
    assert created.status_code == 200, created.text
    login = client.post("/api/v1/auth/login", json={"email": "view@example.com", "password": "Password1!"})
    vheaders = {"Authorization": f"Bearer {login.json()['access_token']}"}
    up = client.post(
        "/api/v1/documents/upload",
        headers=vheaders,
        files={"file": ("a.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert up.status_code == 403


def test_block_and_suspend_endpoints_exist(client):
    headers = auth_headers(client)
    users = client.get("/api/v1/admin/users", headers=headers)
    uid = users.json()[0]["id"]
    blocked = client.post(f"/api/v1/admin/users/{uid}/block", headers=headers)
    assert blocked.status_code == 200


def test_analytics_summary_ok(client):
    headers = auth_headers(client)
    r = client.get("/api/v1/analytics/summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "documents" in body
    assert "success_rate" in body
