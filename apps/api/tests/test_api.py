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
    assert drafted.json()["reply"]
    assert any(f["type"] == "dropdown" for f in fields)
    created = client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": drafted.json()["name"],
            "description": "test",
            "language": "en",
            "fields": fields,
            "recipients": ["ops@example.com", "finance@example.com", "ops@example.com"],
        },
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    assert created.json()["recipients"] == ["ops@example.com", "finance@example.com"]
    assert created.json()["sends_to"] == [
        {"email": "ops@example.com", "name": None},
        {"email": "finance@example.com", "name": None},
    ]
    live = client.post(f"/api/v1/forms/{fid}/publish", headers=headers)
    assert live.status_code == 200, live.text
    # Listed recipients → personal links only (no shared open token).
    assert live.json()["share_token"] is None
    assert live.json()["share_url"] is None
    assert live.json()["open_link"] is False
    links = live.json()["recipient_links"]
    assert {x["email"] for x in links} == {"ops@example.com", "finance@example.com"}
    assert all(x["token"] and x["url"] and x["status"] == "pending" for x in links)
    assert live.json()["notified"] == ["ops@example.com", "finance@example.com"]
    assert live.json()["recipients"] == ["ops@example.com", "finance@example.com"]
    shared = client.post(
        f"/api/v1/forms/{fid}/share",
        headers=headers,
        json={"channel": "email", "recipients": ["counsel@example.com"]},
    )
    assert shared.status_code == 200, shared.text
    assert shared.json()["sent"] == ["counsel@example.com"]
    assert shared.json()["link"] is None
    counsel_links = shared.json()["recipient_links"]
    assert len(counsel_links) == 1
    token = counsel_links[0]["token"]
    assert counsel_links[0]["email"] == "counsel@example.com"
    refreshed = client.get(f"/api/v1/forms/{fid}", headers=headers)
    assert refreshed.json()["recipients"] == ["counsel@example.com"]
    assert refreshed.json()["share_token"] is None
    public = client.get(f"/api/v1/public/forms/{token}")
    assert public.status_code == 200
    assert "recipients" not in public.json()
    assert public.json()["personal"] is True
    assert public.json()["recipient_email"] == "counsel@example.com"
    assert public.json()["already_submitted"] is False
    assert public.json()["sends_to"] == [
        {"email": "counsel@example.com", "name": None},
    ]
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
    assert submitted.json()["locked"] is True
    assert submitted.json()["submission_id"]
    assert submitted.json()["answered_folder_id"]
    # Personal link closes after first submit.
    again = client.post(
        f"/api/v1/public/forms/{token}/submit",
        json={
            "name": "Vendor Lee",
            "email": "lee@example.com",
            "answers": answers,
            "signature": "data:image/png;base64,xxx",
        },
    )
    assert again.status_code == 409
    closed = client.get(f"/api/v1/public/forms/{token}")
    assert closed.status_code == 200
    assert closed.json()["already_submitted"] is True
    assert closed.json()["link_closed"] is True
    assert closed.json()["submission_id"] == submitted.json()["submission_id"]
    rows = client.get(f"/api/v1/forms/{fid}/submissions", headers=headers)
    assert rows.status_code == 200
    assert rows.json()[0]["submitter_email"] == "lee@example.com"
    assert rows.json()[0]["document_id"]
    assert rows.json()[0]["document_filename"]
    assert rows.json()[0]["id"] == submitted.json()["submission_id"]

    locked = client.get(f"/api/v1/forms/{fid}", headers=headers)
    assert locked.status_code == 200
    assert locked.json()["locked"] is True
    assert locked.json()["submission_count"] >= 1
    denied = client.put(
        f"/api/v1/forms/{fid}",
        headers=headers,
        json={"name": "Hacked", "fields": [], "recipients": ["x@example.com"]},
    )
    assert denied.status_code == 409
    deleted = client.delete(f"/api/v1/forms/{fid}", headers=headers)
    assert deleted.status_code == 409
    share_change = client.post(
        f"/api/v1/forms/{fid}/share",
        headers=headers,
        json={"channel": "email", "recipients": ["intruder@example.com"]},
    )
    assert share_change.status_code == 409

    sid = rows.json()[0]["id"]
    answered = client.get(f"/api/v1/forms/{fid}/answered", headers=headers)
    assert answered.status_code == 200
    assert answered.json()["folder"]["kind"] == "answered"
    assert answered.json()["submissions"][0]["id"] == sid

    digest = client.post(
        f"/api/v1/forms/{fid}/submissions/{sid}/digest",
        headers=headers,
        json={"action": "summarize"},
    )
    assert digest.status_code == 200, digest.text
    assert digest.json()["action"] == "summarize"
    assert digest.json()["entry"]["summary"]
    insights = client.post(
        f"/api/v1/forms/{fid}/submissions/{sid}/digest",
        headers=headers,
        json={"action": "insights"},
    )
    assert insights.status_code == 200, insights.text
    assert insights.json()["action"] == "insights"
    extract = client.post(
        f"/api/v1/forms/{fid}/submissions/{sid}/digest",
        headers=headers,
        json={"action": "extract"},
    )
    assert extract.status_code == 200, extract.text
    assert extract.json()["result"]["document_id"]

    # Locked form: copy → new unlocked draft with same definition, no submissions.
    copied = client.post(f"/api/v1/forms/{fid}/copy", headers=headers)
    assert copied.status_code == 200, copied.text
    assert copied.json()["copied_from"] == fid
    assert copied.json()["status"] == "draft"
    assert copied.json()["locked"] is False
    assert copied.json()["submission_count"] == 0
    assert copied.json()["name"].endswith("(copy)")
    assert len(copied.json()["fields"]) == len(locked.json()["fields"])
    assert copied.json()["recipients"] == locked.json()["recipients"]
    copy_id = copied.json()["id"]
    assert copy_id != fid
    copy_subs = client.get(f"/api/v1/forms/{copy_id}/submissions", headers=headers)
    assert copy_subs.status_code == 200
    assert copy_subs.json() == []

    # Archive with answered data kept under Archive package.
    archived = client.post(
        f"/api/v1/forms/{fid}/archive",
        headers=headers,
        json={"keep_answers": True},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived"] is True
    assert archived.json()["archive_keep_answers"] is True
    assert archived.json()["locked"] is True
    assert archived.json()["share_url"] is None
    # Public fill must stop.
    assert client.get(f"/api/v1/public/forms/{token}").status_code == 404
    # Still no edit/delete on archived locked form.
    assert (
        client.put(
            f"/api/v1/forms/{fid}",
            headers=headers,
            json={"name": "Nope", "fields": [], "recipients": []},
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/forms/{fid}", headers=headers).status_code == 409
    answered_arch = client.get(f"/api/v1/forms/{fid}/answered", headers=headers)
    assert answered_arch.status_code == 200
    assert answered_arch.json()["folder"]["kind"] == "archive"
    assert "Archive" in answered_arch.json()["folder"]["name"]

    # Unarchive restores draft; still locked while submissions exist.
    unarchived = client.post(f"/api/v1/forms/{fid}/unarchive", headers=headers)
    assert unarchived.status_code == 200, unarchived.text
    assert unarchived.json()["status"] == "draft"
    assert unarchived.json()["archived"] is False
    assert unarchived.json()["locked"] is True

    # Archive form-only: answers remain in answered folder / documents.
    archived_only = client.post(
        f"/api/v1/forms/{fid}/archive",
        headers=headers,
        json={"keep_answers": False},
    )
    assert archived_only.status_code == 200, archived_only.text
    assert archived_only.json()["archive_keep_answers"] is False
    answered_only = client.get(f"/api/v1/forms/{fid}/answered", headers=headers)
    assert answered_only.status_code == 200
    assert answered_only.json()["folder"]["kind"] == "answered"
    assert len(answered_only.json()["submissions"]) >= 1
    assert answered_only.json()["submissions"][0]["document_id"]


def test_personal_recipient_tokens_isolated(client):
    """Two recipients → two tokens; one submit doesn't close the other; second submit → 409."""
    headers = auth_headers(client)
    fields = [
        {"id": "q1", "type": "text", "label": "Note", "required": True, "options": []},
        {"id": "sig", "type": "signature", "label": "Sign", "required": True, "options": []},
    ]
    created = client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": "Personal shares",
            "description": "per-recipient",
            "language": "en",
            "fields": fields,
            "recipients": ["alice@example.com", "bob@example.com"],
        },
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    live = client.post(f"/api/v1/forms/{fid}/publish", headers=headers)
    assert live.status_code == 200, live.text
    assert live.json()["share_token"] is None
    links = {x["email"]: x for x in live.json()["recipient_links"]}
    assert set(links) == {"alice@example.com", "bob@example.com"}
    alice_tok = links["alice@example.com"]["token"]
    bob_tok = links["bob@example.com"]["token"]
    assert alice_tok != bob_tok

    alice_get = client.get(f"/api/v1/public/forms/{alice_tok}?email=alice@example.com")
    assert alice_get.status_code == 200
    assert alice_get.json()["email_match"] is True
    assert alice_get.json()["recipient_email"] == "alice@example.com"

    alice_sub = client.post(
        f"/api/v1/public/forms/{alice_tok}/submit",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "answers": {"q1": "from alice"},
            "signature": "data:image/png;base64,aaa",
        },
    )
    assert alice_sub.status_code == 200, alice_sub.text
    alice_sid = alice_sub.json()["submission_id"]
    assert alice_sid

    # Alice's link is closed; Bob's remains open.
    assert (
        client.post(
            f"/api/v1/public/forms/{alice_tok}/submit",
            json={
                "name": "Alice",
                "email": "alice@example.com",
                "answers": {"q1": "again"},
                "signature": "data:image/png;base64,aaa",
            },
        ).status_code
        == 409
    )
    bob_get = client.get(f"/api/v1/public/forms/{bob_tok}")
    assert bob_get.status_code == 200
    assert bob_get.json()["already_submitted"] is False
    assert bob_get.json()["link_closed"] is False

    bob_sub = client.post(
        f"/api/v1/public/forms/{bob_tok}/submit",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "answers": {"q1": "from bob"},
            "signature": "data:image/png;base64,bbb",
        },
    )
    assert bob_sub.status_code == 200, bob_sub.text
    bob_sid = bob_sub.json()["submission_id"]
    assert bob_sid
    assert bob_sid != alice_sid

    rows = client.get(f"/api/v1/forms/{fid}/submissions", headers=headers)
    assert rows.status_code == 200
    ids = {r["id"] for r in rows.json()}
    assert ids == {alice_sid, bob_sid}

    # Open form (no recipients) still gets a generic share token.
    open_form = client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": "Open form",
            "description": "anyone",
            "language": "en",
            "fields": fields,
            "recipients": [],
        },
    )
    oid = open_form.json()["id"]
    open_live = client.post(f"/api/v1/forms/{oid}/publish", headers=headers)
    assert open_live.status_code == 200
    assert open_live.json()["share_token"]
    assert open_live.json()["open_link"] is True
    assert open_live.json()["recipient_links"] == []


def test_n8n_export_and_connectors(client):
    headers = auth_headers(client)
    wf = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name": "n8n Invoice",
            "description": "export",
            "trigger": "on_upload",
            "steps": [
                {"key": "ocr", "type": "extract_text", "config": {}},
                {"key": "classify", "type": "classify", "config": {}},
                {"key": "notify", "type": "notify", "config": {}},
            ],
        },
    )
    assert wf.status_code == 200, wf.text
    listed = client.get("/api/v1/workflows", headers=headers)
    assert listed.json()[0]["canvas"][0]["type"] == "webhook"
    graph = client.get(f"/api/v1/workflows/{wf.json()['id']}/n8n", headers=headers)
    assert graph.status_code == 200, graph.text
    body = graph.json()
    assert body["name"] == "n8n Invoice"
    assert any(n["type"] == "n8n-nodes-base.webhook" for n in body["nodes"])
    linked = client.post("/api/v1/connectors", headers=headers, json={"kind": "google_drive", "name": "Drive"})
    assert linked.status_code == 200, linked.text
    cid = linked.json()["id"]
    roots = client.get(f"/api/v1/connectors/{cid}/browse", headers=headers)
    assert roots.status_code == 200, roots.text
    root = roots.json()
    assert root["demo"] is True
    assert root["sources"]
    source_path = root["sources"][0]["path"]
    folders = client.get(f"/api/v1/connectors/{cid}/browse", headers=headers, params={"path": source_path})
    assert folders.status_code == 200
    assert folders.json()["folders"]
    folder_path = folders.json()["folders"][0]["path"]
    files = client.get(f"/api/v1/connectors/{cid}/browse", headers=headers, params={"path": folder_path})
    assert files.status_code == 200
    file_paths = [f["path"] for f in files.json()["files"]]
    assert file_paths
    synced = client.post(
        f"/api/v1/connectors/{cid}/sync",
        headers=headers,
        json={"paths": file_paths[:1]},
    )
    assert synced.status_code == 200
    assert synced.json()["synced"] == 1
    rows = client.get("/api/v1/connectors", headers=headers)
    assert rows.json()[0]["files"]
    # empty body still syncs full catalog (compat)
    full = client.post(f"/api/v1/connectors/{cid}/sync", headers=headers)
    assert full.status_code == 200
    assert full.json()["synced"] >= 1

    local = client.post("/api/v1/connectors", headers=headers, json={"kind": "local_db", "name": "DB"})
    assert local.status_code == 200
    lid = local.json()["id"]
    lb = client.get(f"/api/v1/connectors/{lid}/browse", headers=headers)
    assert lb.status_code == 200
    assert lb.json()["sources"]
    sp = lb.json()["sources"][0]["path"]
    lf = client.get(f"/api/v1/connectors/{lid}/browse", headers=headers, params={"path": sp})
    assert lf.json()["folders"]
    fp = lf.json()["folders"][0]["path"]
    lfiles = client.get(f"/api/v1/connectors/{lid}/browse", headers=headers, params={"path": fp})
    assert lfiles.json()["files"]
    lsync = client.post(
        f"/api/v1/connectors/{lid}/sync",
        headers=headers,
        json={"paths": [lfiles.json()["files"][0]["path"]]},
    )
    assert lsync.status_code == 200
    assert lsync.json()["synced"] == 1


STUDENT_PROMPT = (
    "day summery to students , date automatic , rate today class, signature mandatory, "
    "email by user , did the student was in class, which topic was best explained"
)


def test_student_day_summary_compose_replies(client):
    from app.engine.formgen import compose_from_prompt, relevant_chunks

    built = compose_from_prompt(STUDENT_PROMPT, "en", use_llm=False)
    assert built["reply"]
    assert "I drafted" in built["reply"] or "understood" in built["reply"].lower()
    assert built["knowledge"]["applied"] is False
    assert built["knowledge"]["href"] == "/app/connectors"
    assert built["knowledge"]["also"] == "/app/manage"
    assert relevant_chunks(STUDENT_PROMPT, [{"title": "PBX manual", "text": "email date class of service user manual"}]) == []
    assert relevant_chunks(STUDENT_PROMPT, [{"title": "Roster", "text": "student roster for today's lesson"}])
    types = {f["type"] for f in built["fields"]}
    assert "date" in types
    assert "email" in types
    assert "signature" in types
    assert "yesno" in types
    assert "textarea" in types
    assert "radio" in types
    date = next(f for f in built["fields"] if f["type"] == "date")
    assert date["auto"] == "today"
    assert date["required"] is True
    sig = next(f for f in built["fields"] if f["type"] == "signature")
    assert sig["required"] is True
    assert any("in class" in f["label"].lower() for f in built["fields"] if f["type"] == "yesno")
    assert any("topic" in f["label"].lower() for f in built["fields"] if f["type"] == "textarea")
    assert any("rate" in f["label"].lower() for f in built["fields"] if f["type"] == "radio")

    headers = auth_headers(client)
    drafted = client.post(
        "/api/v1/forms/compose",
        headers=headers,
        json={"prompt": STUDENT_PROMPT, "language": "en"},
    )
    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert body["reply"]
    assert "Connectors" in body["reply"] or body["knowledge"]["href"] == "/app/connectors"
    assert any(f["type"] == "signature" and f["required"] for f in body["fields"])
    assert "up" in body["ollama"]
    assert "models" in body["ollama"]


def test_ollama_status_endpoint(client):
    headers = auth_headers(client)
    r = client.get("/api/v1/agent/ollama", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "up" in body
    assert "url" in body
    assert isinstance(body["models"], list)
    status = client.get("/api/v1/agent/status", headers=headers)
    assert status.status_code == 200
    assert "ollama" in status.json()
    health = client.get("/api/v1/admin/health", headers=headers)
    assert health.status_code == 200
    assert "ollama" in health.json()


HE_INVOICE = """חשבונית מס
מספר חשבונית: INV-HE-42
ספק: א.ב שיווק בע״מ
ח.פ. 512345678
מספר הקצאה: ALLOC-99881
סכום: ₪1,250.50
"""


def test_hebrew_invoice_classify_and_fields():
    from app.classify import classify_document, extract_fields

    classified = classify_document("he-invoice.txt", HE_INVOICE)
    assert classified["label"] == "invoice"
    assert classified["confidence"] >= 0.5
    fields = {f["name"]: f["value"] for f in extract_fields(HE_INVOICE, "invoice")}
    assert fields.get("amount") == "1,250.50"
    assert fields.get("company_id") == "512345678"
    assert fields.get("allocation_number") == "ALLOC-99881"
    assert fields.get("invoice_number") == "INV-HE-42"


def test_hebrew_invoice_form_compose(client):
    from app.engine.formgen import compose_from_prompt

    prompt = "טופס אישור חשבונית עם ספק, מספר חשבונית, סכום, ח.פ. ומספר הקצאה"
    built = compose_from_prompt(prompt, "he", use_llm=False)
    assert built["name"] == "אישור חשבונית"
    labels = [f["label"] for f in built["fields"]]
    assert "ספק" in labels
    assert "מספר חשבונית" in labels
    assert "סכום לתשלום" in labels
    assert "ח.פ." in labels
    assert "מספר הקצאה" in labels

    headers = auth_headers(client)
    drafted = client.post(
        "/api/v1/forms/compose",
        headers=headers,
        json={"prompt": prompt, "language": "he"},
    )
    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert body["language"] == "he"
    assert any(f["label"] == "ספק" for f in body["fields"])


def _mini_png() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_form_upload_scan_accept_and_reject(client):
    """Clean PNG/PDF accepted; exe / MIME mismatch / oversize rejected with 400."""
    headers = auth_headers(client)
    fields = [
        {
            "id": "doc1",
            "type": "file",
            "label": "Attach PDF",
            "required": True,
            "accept": ["pdf", "png"],
            "max_count": 1,
        },
        {
            "id": "pics",
            "type": "images",
            "label": "Photos",
            "required": False,
            "accept": ["png", "jpg", "jpeg"],
            "max_count": 3,
        },
    ]
    created = client.post(
        "/api/v1/forms",
        headers=headers,
        json={"name": "Upload scan form", "language": "en", "fields": fields, "recipients": []},
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    live = client.post(f"/api/v1/forms/{fid}/publish", headers=headers)
    assert live.status_code == 200, live.text
    token = live.json()["share_token"]
    assert token

    png = _mini_png()
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

    # Reject .exe
    bad_exe = client.post(
        f"/api/v1/public/forms/{token}/submit",
        data={"name": "A", "email": "a@example.com", "answers": "{}", "locale": "en"},
        files=[("file__doc1", ("malware.exe", b"MZ" + b"\x00" * 64, "application/octet-stream"))],
    )
    assert bad_exe.status_code == 400, bad_exe.text
    assert "reject" in bad_exe.text.lower() or "disallowed" in bad_exe.text.lower() or "executable" in bad_exe.text.lower()

    # Reject content-type mismatch (PNG bytes declared as PDF)
    bad_mismatch = client.post(
        f"/api/v1/public/forms/{token}/submit",
        data={"name": "A", "email": "a@example.com", "answers": "{}", "locale": "en"},
        files=[("file__doc1", ("photo.png", png, "application/pdf"))],
    )
    assert bad_mismatch.status_code == 400, bad_mismatch.text
    assert "mismatch" in bad_mismatch.text.lower()

    # Reject oversize via field max_bytes
    tiny = client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": "Tiny upload",
            "language": "en",
            "fields": [
                {
                    "id": "doc1",
                    "type": "file",
                    "label": "Tiny",
                    "required": True,
                    "accept": ["png"],
                    "max_count": 1,
                    "max_bytes": 10,
                }
            ],
            "recipients": [],
        },
    )
    assert tiny.status_code == 200, tiny.text
    tiny_live = client.post(f"/api/v1/forms/{tiny.json()['id']}/publish", headers=headers)
    tiny_token = tiny_live.json()["share_token"]
    bad_size = client.post(
        f"/api/v1/public/forms/{tiny_token}/submit",
        data={"name": "A", "email": "a@example.com", "answers": "{}", "locale": "en"},
        files=[("file__doc1", ("photo.png", png, "image/png"))],
    )
    assert bad_size.status_code == 400, bad_size.text
    assert "large" in bad_size.text.lower()

    # Accept clean PDF (+ optional PNG images)
    ok = client.post(
        f"/api/v1/public/forms/{token}/submit",
        data={"name": "Vendor", "email": "vendor@example.com", "answers": "{}", "locale": "en"},
        files=[
            ("file__doc1", ("invoice.pdf", pdf, "application/pdf")),
            ("file__pics", ("a.png", png, "image/png")),
        ],
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["status"] == "implemented"
    assert body["upload_scans"]
    assert all(s.get("status") == "clean" for s in body["upload_scans"])

    rows = client.get(f"/api/v1/forms/{fid}/submissions", headers=headers)
    assert rows.status_code == 200
    sub = rows.json()[0]
    assert sub["upload_scans"]
    assert isinstance(sub["answers"]["doc1"], dict)
    assert sub["answers"]["doc1"]["scan"] == "clean"
    assert sub["answers"]["doc1"]["filename"] == "invoice.pdf"
    assert isinstance(sub["answers"]["pics"], list)
    assert sub["answers"]["pics"][0]["scan"] == "clean"
    key = sub["answers"]["doc1"].get("storage_key") or ""
    assert key.startswith("t")
    assert "form" in key and "upload" in key.replace("-", "_")
    assert sub["answers"]["doc1"].get("document_id")


def test_desk_search_finds_forms_workflows_documents_connectors(client):
    headers = auth_headers(client)
    form = client.post(
        "/api/v1/forms",
        headers=headers,
        json={"name": "Alpha Invoice Gate", "topic": "AP", "description": "", "fields": [], "recipients": []},
    )
    assert form.status_code == 200, form.text
    fid = form.json()["id"]

    wf = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name": "Alpha Flow Process",
            "description": "search me",
            "trigger": "manual",
            "steps": [{"key": "ocr", "type": "extract_text", "config": {}}],
        },
    )
    assert wf.status_code == 200, wf.text

    up = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("alpha-invoice.txt", io.BytesIO(b"TAX INVOICE INV-1"), "text/plain")},
        params={"run_pipeline": "false"},
    )
    assert up.status_code == 200, up.text
    did = up.json()["id"]

    conn = client.post(
        "/api/v1/connectors",
        headers=headers,
        json={"kind": "google_drive", "name": "Alpha Drive Link"},
    )
    assert conn.status_code == 200, conn.text

    empty = client.get("/api/v1/search?q=", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["results"] == []

    r = client.get("/api/v1/search?q=alpha", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    kinds = {hit["kind"] for hit in body["results"]}
    assert "form" in kinds
    assert "workflow" in kinds
    assert "document" in kinds
    assert "connector" in kinds
    by_kind = {hit["kind"]: hit for hit in body["results"]}
    assert by_kind["form"]["href"] == f"/app/forms/{fid}"
    assert by_kind["document"]["href"] == f"/app/documents/{did}"
    assert by_kind["connector"]["href"] == "/app/connectors"
    assert by_kind["workflow"]["href"] == "/app/workflows"

    miss = client.get("/api/v1/search?q=zzznomatch", headers=headers)
    assert miss.status_code == 200
    assert miss.json()["results"] == []

def _promote_platform_admin(email: str = "demo@example.com") -> None:
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        assert u is not None
        u.role = "platform_admin"
        db.commit()
    finally:
        db.close()


def test_system_rag_requires_platform_admin(client):
    headers = auth_headers(client)
    denied = client.get("/api/v1/admin/rag/settings", headers=headers)
    assert denied.status_code == 403

    _promote_platform_admin()
    ok = client.get("/api/v1/admin/rag/settings", headers=headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["rag_enabled"] is True
    assert body["min_score"]["default"] == 1
    assert body["min_score"]["form_compose"] == 3
    assert any(f["key"] == "rag" for f in body["flags"])
    assert any(f["key"].startswith("rag_source_") for f in body["flags"])


def test_system_rag_chunks_tags_and_source_toggle(client):
    headers = auth_headers(client)
    _promote_platform_admin()

    conn = client.post(
        "/api/v1/connectors",
        headers=headers,
        json={"kind": "google_drive", "name": "RAG Drive"},
    )
    assert conn.status_code == 200, conn.text
    cid = conn.json()["id"]

    sync = client.post(f"/api/v1/connectors/{cid}/sync", headers=headers, json={})
    assert sync.status_code == 200, sync.text
    assert sync.json()["synced"] >= 1

    sources = client.get("/api/v1/admin/rag/sources", headers=headers)
    assert sources.status_code == 200, sources.text
    assert any(s.get("id") == cid for s in sources.json()["sources"])

    chunks = client.get("/api/v1/admin/rag/chunks", headers=headers)
    assert chunks.status_code == 200, chunks.text
    items = chunks.json()["chunks"]
    assert items
    chunk_id = items[0]["id"]

    tagged = client.patch(
        f"/api/v1/admin/rag/chunks/{chunk_id}/tags",
        headers=headers,
        json={"tags": ["finance", "invoice", "Finance"]},
    )
    assert tagged.status_code == 200, tagged.text
    assert tagged.json()["tags"] == ["finance", "invoice"]

    filtered = client.get("/api/v1/admin/rag/chunks?tag=finance", headers=headers)
    assert filtered.status_code == 200
    assert any(c["id"] == chunk_id for c in filtered.json()["chunks"])

    toggled = client.post(f"/api/v1/admin/rag/sources/{cid}/toggle", headers=headers)
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False

    blocked = client.post(f"/api/v1/connectors/{cid}/sync", headers=headers, json={})
    assert blocked.status_code == 403

    flag = client.post("/api/v1/admin/flags/rag_source_google_drive/toggle", headers=headers)
    assert flag.status_code == 200
    assert flag.json()["enabled"] is False


def test_rag_retrieves_form_chunks_and_scopes_field_fallback(client):
    from app.db import SessionLocal
    from app.engine.rag import retrieve, upsert_chunk
    from app.models import Document, ExtractedField

    headers = auth_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    tid = me["tenant_id"]

    db = SessionLocal()
    try:
        upsert_chunk(db, tid, "form_submission", "sub-1", "Class roster", "student roster for today's lesson attendance")
        db.commit()
        hits = retrieve(db, tid, "student roster lesson attendance", min_score=1, fallback_fields=False)
        assert any(h["source"] == "form_submission" for h in hits)
    finally:
        db.close()

    r2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "tenant-b@example.com",
            "password": "Password1!",
            "full_name": "Tenant B",
            "organization": "Other Co",
        },
    )
    assert r2.status_code == 200, r2.text
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    me2 = client.get("/api/v1/auth/me", headers=h2).json()

    db = SessionLocal()
    try:
        doc = Document(
            tenant_id=tid,
            user_id=me["id"],
            filename="secret.txt",
            content_type="text/plain",
            size_bytes=1,
            storage_key="t1/secret",
            checksum="abc",
            status="ready",
            tags=[],
        )
        db.add(doc)
        db.flush()
        db.add(ExtractedField(document_id=doc.id, name="secret_vendor", value="SHOULD_NOT_LEAK"))
        db.commit()

        leaked = retrieve(db, me2["tenant_id"], "zzzznonexistenttokenquery", min_score=99, fallback_fields=True)
        blob = " ".join(h.get("text", "") for h in leaked)
        assert "SHOULD_NOT_LEAK" not in blob
    finally:
        db.close()


def test_anonymous_replies_admin_only_and_open_submit(client):
    headers = auth_headers(client)  # register → owner (admin+)
    created = client.post(
        "/api/v1/forms",
        headers=headers,
        json={
            "name": "Group pulse",
            "language": "en",
            "fields": [{"id": "q1", "type": "text", "label": "Mood", "required": True}],
            "recipients": ["alice@example.com"],
        },
    )
    assert created.status_code == 200, created.text
    fid = created.json()["id"]
    assert created.json()["allow_anonymous_replies"] is False
    assert created.json()["share_token"] is None

    # Operator cannot enable.
    op = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"email": "ops-anon@example.com", "full_name": "Ops", "password": "Password1!", "role": "operator"},
    )
    assert op.status_code == 200, op.text
    op_login = client.post("/api/v1/auth/login", json={"email": "ops-anon@example.com", "password": "Password1!"})
    op_headers = {"Authorization": f"Bearer {op_login.json()['access_token']}"}
    denied = client.patch(
        f"/api/v1/forms/{fid}/anonymous-replies",
        headers=op_headers,
        json={"enabled": True},
    )
    assert denied.status_code == 403

    # Owner/admin can enable → open share token even with recipients.
    enabled = client.patch(
        f"/api/v1/forms/{fid}/anonymous-replies",
        headers=headers,
        json={"enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["allow_anonymous_replies"] is True
    assert enabled.json()["share_token"]

    live = client.post(f"/api/v1/forms/{fid}/publish", headers=headers)
    assert live.status_code == 200, live.text
    token = live.json()["share_token"]
    assert token
    assert live.json()["recipient_links"]

    pub = client.get(f"/api/v1/public/forms/{token}")
    assert pub.status_code == 200
    assert pub.json()["personal"] is False
    assert pub.json()["identity_mode"] == "anonymous"
    assert pub.json()["allow_anonymous_replies"] is True

    submitted = client.post(
        f"/api/v1/public/forms/{token}/submit",
        json={"name": "", "email": "", "answers": {"q1": "good"}, "locale": "en"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["submission_id"]

    rows = client.get(f"/api/v1/forms/{fid}/submissions", headers=headers)
    assert rows.status_code == 200
    assert len(rows.json()) >= 1
    assert rows.json()[0]["answers"]["q1"] == "good"
