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


def test_locale_and_org_tree(client):
    headers = auth_headers(client)
    langs = client.get("/api/v1/auth/languages")
    assert langs.status_code == 200
    assert {x["code"] for x in langs.json()} >= {"en", "he", "ar", "es", "fr"}
    patched = client.patch("/api/v1/auth/me?locale=he", headers=headers)
    assert patched.status_code == 200, patched.text
    assert patched.json()["locale"] == "he"
    layer = client.post("/api/v1/org/layers", headers=headers, json={"name": "Finance", "kind": "department"})
    assert layer.status_code == 200, layer.text
    tree = client.get("/api/v1/org/tree", headers=headers)
    assert tree.status_code == 200
    assert any(x["name"] == "Finance" for x in tree.json()["layers"])


def test_form_compose_publish_and_public_submit(client):
    headers = auth_headers(client)
    drafted = client.post(
        "/api/v1/forms/compose",
        headers=headers,
        json={"prompt": "invoice approval with department dropdown and signature", "language": "en"},
    )
    assert drafted.status_code == 200, drafted.text
    fields = drafted.json()["fields"]
    assert any(f["type"] == "dropdown" for f in fields)
    created = client.post(
        "/api/v1/forms",
        headers=headers,
        json={"name": drafted.json()["name"], "description": "test", "language": "en", "fields": fields},
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    live = client.post(f"/api/v1/forms/{fid}/publish", headers=headers)
    assert live.status_code == 200, live.text
    token = live.json()["share_token"]
    assert token
    public = client.get(f"/api/v1/public/forms/{token}")
    assert public.status_code == 200
    answers = {
        f["id"]: (f.get("options") or ["yes"])[0] if f["type"] in ("dropdown", "radio", "yesno") else "Acme"
        for f in public.json()["fields"]
        if f.get("required") and f["type"] not in ("heading", "signature")
    }
    submitted = client.post(
        f"/api/v1/public/forms/{token}/submit",
        json={
            "name": "Vendor Lee",
            "email": "lee@example.com",
            "answers": answers,
            "signature": "data:image/png;base64,xxx",
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "implemented"
    rows = client.get(f"/api/v1/forms/{fid}/submissions", headers=headers)
    assert rows.status_code == 200
    assert rows.json()[0]["submitter_email"] == "lee@example.com"
