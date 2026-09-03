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
