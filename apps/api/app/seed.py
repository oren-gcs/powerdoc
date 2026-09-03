from app.models import FeatureFlag, ModelBinding, Tenant, User, Workflow, Automation, Document
from app.security import hash_password
from app.storage import storage
from app.engine.orchestrator import process_document

DEMO_PASSWORD = "DocFlow!2026"

INVOICE = """TAX INVOICE
GCS Tech Ltd
Invoice No: INV-10482
Date: 2026-08-12
Bill To: Northwind Analytics
Amount Due: USD 4,280.00
Subtotal: USD 4,000.00
VAT: USD 280.00
Total Due: USD 4,280.00
Please remit to ap@gcs-tech.org
"""

CONTRACT = """SERVICES AGREEMENT
This Agreement is entered into as of 2026-07-01 between GCS Tech ("Provider")
and Harbor Clinics ("Client").
WHEREAS the parties wish to define terms and conditions of document processing;
NOW, THEREFORE, the party of the first part and the party of the second part
agree that governing law shall be the State of Delaware.
Term: 24 months. Confidentiality survives termination.
"""

MEMO = """MEMORANDUM
From: Operations
To: Leadership
Re: Q3 document intake
Internal memo: inbound invoice volume rose 18%. Contract reviews remain on SLA.
"""


def seed_if_needed(db) -> None:
    if db.query(User).first():
        return
    tenant = Tenant(name="GCS Tech", slug="gcs-tech", plan="scale")
    db.add(tenant)
    db.flush()
    users = [
        User(email="oren@gcs-tech.org", full_name="Oren Gilboa", hashed_password=hash_password(DEMO_PASSWORD), role="owner", tenant_id=tenant.id),
        User(email="admin@docflow.example", full_name="Platform Admin", hashed_password=hash_password(DEMO_PASSWORD), role="platform_admin", tenant_id=tenant.id),
        User(email="operator@docflow.example", full_name="Maya Operator", hashed_password=hash_password(DEMO_PASSWORD), role="operator", tenant_id=tenant.id),
        User(email="viewer@docflow.example", full_name="Lee Viewer", hashed_password=hash_password(DEMO_PASSWORD), role="viewer", tenant_id=tenant.id),
    ]
    for u in users:
        db.add(u)
    db.flush()
    owner = users[0]

    invoice_wf = Workflow(
        tenant_id=tenant.id,
        name="Invoice Intake",
        description="Extract, classify, capture AP fields, notify finance.",
        trigger="on_classify",
        definition={
            "steps": [
                {"key": "ocr", "type": "extract_text", "config": {}},
                {"key": "classify", "type": "classify", "config": {}},
                {"key": "fields", "type": "extract_fields", "config": {}},
                {"key": "only_invoices", "type": "condition", "config": {"field": "classification", "equals": "invoice"}},
                {"key": "tag_ap", "type": "tag", "config": {"tags": ["accounts-payable", "finance"]}},
                {"key": "summarize", "type": "summarize", "config": {}},
                {"key": "notify", "type": "notify", "config": {"subject": "Invoice ready for review"}},
            ]
        },
    )
    contract_wf = Workflow(
        tenant_id=tenant.id,
        name="Contract Review",
        description="Legal review path for agreements.",
        trigger="on_classify",
        definition={
            "steps": [
                {"key": "ocr", "type": "extract_text", "config": {}},
                {"key": "classify", "type": "classify", "config": {}},
                {"key": "agent", "type": "agent", "config": {"role": "workflow", "prompt": "Highlight governing law, term, and parties."}},
                {"key": "tag", "type": "tag", "config": {"tags": ["legal"]}},
                {"key": "notify", "type": "notify", "config": {"subject": "Contract queued for counsel"}},
            ]
        },
    )
    general_wf = Workflow(
        tenant_id=tenant.id,
        name="General Ingest",
        description="Default document flow used when no specialist path matches.",
        trigger="on_upload",
        definition={
            "steps": [
                {"key": "ocr", "type": "extract_text", "config": {}},
                {"key": "classify", "type": "classify", "config": {}},
                {"key": "fields", "type": "extract_fields", "config": {}},
                {"key": "tag", "type": "tag", "config": {"tags": ["inbox"]}},
                {"key": "notify", "type": "notify", "config": {"subject": "New document in DocFlow"}},
            ]
        },
    )
    db.add_all([invoice_wf, contract_wf, general_wf])
    db.flush()
    db.add_all(
        [
            Automation(
                tenant_id=tenant.id,
                name="Route invoices to AP",
                trigger_type="on_classify",
                trigger_config={"classification": "invoice"},
                workflow_id=invoice_wf.id,
            ),
            Automation(
                tenant_id=tenant.id,
                name="Route contracts to legal",
                trigger_type="on_classify",
                trigger_config={"classification": "contract"},
                workflow_id=contract_wf.id,
            ),
            Automation(
                tenant_id=tenant.id,
                name="Catch-all ingest",
                trigger_type="on_upload",
                trigger_config={},
                workflow_id=general_wf.id,
                is_active=False,
            ),
        ]
    )
    db.add_all(
        [
            ModelBinding(agent_role="ocr", model_name="heuristic", provider="heuristic"),
            ModelBinding(agent_role="workflow", model_name="heuristic", provider="heuristic"),
            ModelBinding(agent_role="notification", model_name="heuristic", provider="heuristic"),
            ModelBinding(agent_role="analytics", model_name="heuristic", provider="heuristic"),
            ModelBinding(agent_role="orchestrator", model_name="heuristic", provider="heuristic"),
            FeatureFlag(key="pipeline", enabled=True, description="Document processing pipeline"),
            FeatureFlag(key="automations", enabled=True, description="Trigger matching"),
            FeatureFlag(key="llm_optional", enabled=True, description="Use Ollama/OpenAI when available"),
            FeatureFlag(key="customer_admin", enabled=True, description="Tenant admin console"),
        ]
    )
    db.commit()

    samples = [
        ("northwind-invoice-10482.txt", INVOICE),
        ("harbor-services-agreement.txt", CONTRACT),
        ("q3-ops-memo.txt", MEMO),
    ]
    for name, body in samples:
        data = body.encode()
        key = storage.put(tenant.id, name, data)
        import hashlib

        doc = Document(
            tenant_id=tenant.id,
            user_id=owner.id,
            filename=name,
            content_type="text/plain",
            size_bytes=len(data),
            storage_key=key,
            checksum=hashlib.sha256(data).hexdigest(),
            status="uploaded",
            tags=[],
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        process_document(db, doc)


def seed_extensions(db) -> None:
    from app.engine.formgen import compose_form
    from app.engine.rag import upsert_chunk
    from app.models import AccessGrant, Connector, Folder, Form, Layer, LayerMember, OCRResult, Workflow

    if db.query(Layer).first():
        return
    tenant = db.query(Tenant).first()
    if not tenant:
        return
    users = {u.email: u for u in db.query(User).filter(User.tenant_id == tenant.id).all()}
    owner = users.get("oren@gcs-tech.org") or db.query(User).filter(User.tenant_id == tenant.id).first()
    if not owner:
        return
    org = Layer(tenant_id=tenant.id, name="GCS Tech", kind="org", locale="en")
    db.add(org)
    db.flush()
    finance = Layer(tenant_id=tenant.id, parent_id=org.id, name="Finance", kind="department", locale="en")
    legal = Layer(tenant_id=tenant.id, parent_id=org.id, name="Legal", kind="department", locale="he")
    remote = Layer(tenant_id=tenant.id, parent_id=org.id, name="Remote vendors", kind="remote", locale="en")
    db.add_all([finance, legal, remote])
    db.flush()
    for email, layer, title, manage in (
        ("oren@gcs-tech.org", org, "owner", True),
        ("operator@docflow.example", finance, "AP operator", False),
        ("operator@docflow.local", finance, "AP operator", False),
        ("viewer@docflow.example", remote, "vendor", False),
        ("viewer@docflow.local", remote, "vendor", False),
    ):
        u = users.get(email)
        if u:
            db.add(LayerMember(layer_id=layer.id, user_id=u.id, title=title, can_manage=manage))
    files = Folder(tenant_id=tenant.id, layer_id=org.id, name="Library", kind="files")
    forms_folder = Folder(tenant_id=tenant.id, layer_id=finance.id, name="Draft forms", kind="forms")
    live = Folder(tenant_id=tenant.id, layer_id=org.id, name="Automation", kind="automation")
    db.add_all([files, forms_folder, live])
    db.flush()
    wf = db.query(Workflow).filter(Workflow.tenant_id == tenant.id).first()
    built = compose_form("invoice approval with department dropdown and signature", "en")
    form = Form(
        tenant_id=tenant.id,
        folder_id=forms_folder.id,
        layer_id=finance.id,
        created_by=owner.id,
        name=built["name"],
        topic=built["topic"],
        description="Seeded AP approval form",
        language="en",
        definition={"fields": built["fields"]},
        workflow_id=wf.id if wf else None,
        status="draft",
    )
    db.add(form)
    db.flush()
    he = compose_form("טופס אישור חשבונית", "he")
    db.add(
        Form(
            tenant_id=tenant.id,
            folder_id=forms_folder.id,
            layer_id=finance.id,
            created_by=owner.id,
            name=he["name"],
            topic=he["topic"],
            description="טופס בעברית",
            language="he",
            definition={"fields": he["fields"]},
            status="draft",
        )
    )
    from secrets import token_urlsafe
    from datetime import datetime as dt

    form.status = "live"
    form.share_token = token_urlsafe(12)
    form.published_at = dt.utcnow()
    db.add(AccessGrant(tenant_id=tenant.id, principal_type="layer", principal_id=finance.id, resource_type="form", resource_id=form.id, permission="edit"))
    db.add(AccessGrant(tenant_id=tenant.id, principal_type="layer", principal_id=remote.id, resource_type="form", resource_id=form.id, permission="fill"))
    db.add_all(
        [
            Connector(tenant_id=tenant.id, kind="google_drive", name="Google Drive (sandbox)", status="connected", config={"mode": "sandbox"}),
            Connector(tenant_id=tenant.id, kind="microsoft", name="Microsoft 365 (sandbox)", status="connected", config={"mode": "sandbox"}),
            Connector(tenant_id=tenant.id, kind="local_db", name="DocFlow database", status="connected", config={"mode": "local"}),
        ]
    )
    for o in db.query(OCRResult).filter(OCRResult.tenant_id == tenant.id).all():
        upsert_chunk(db, tenant.id, "ocr", str(o.document_id), f"doc {o.document_id}", o.text or "")
    db.commit()

