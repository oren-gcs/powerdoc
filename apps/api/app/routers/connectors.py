from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.rag import upsert_chunk
from app.models import Connector, OCRResult, User

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

SANDBOX = {
    "google_drive": [
        ("Drive / Finance / Q3-invoices.pdf", "TAX INVOICE GCS Tech Invoice No: INV-2201 Amount Due: USD 910.00"),
        ("Drive / Legal / MSA-Harbor.docx", "SERVICES AGREEMENT governing law Delaware parties GCS Tech and Harbor"),
    ],
    "microsoft": [
        ("SharePoint / AP / vendor-onboarding.xlsx", "Vendor legal name, tax id, billing email columns for onboarding"),
        ("OneDrive / Ops / site-checklist.docx", "Site visit condition findings inspector sign-off"),
    ],
    "local_db": [
        ("local_db.extracted_fields", "invoice_number amount date vendor classification"),
        ("local_db.documents", "ingested files with OCR text available for form generation"),
    ],
}


class ConnectorIn(BaseModel):
    kind: str
    name: str
    config: dict = {}


def _files_for(c: Connector) -> list[str]:
    stored = (c.config or {}).get("files")
    if stored:
        return list(stored)
    return [title for title, _ in SANDBOX.get(c.kind, [])]


@router.get("")
def list_connectors(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Connector).filter(Connector.tenant_id == user.tenant_id).all()
    return [
        {
            "id": c.id,
            "kind": c.kind,
            "name": c.name,
            "status": c.status,
            "file_count": c.file_count,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "files": _files_for(c),
        }
        for c in rows
    ]


@router.post("")
def connect(body: ConnectorIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    if body.kind not in ("google_drive", "microsoft", "local_db", "local_files"):
        raise HTTPException(400, "Unknown connector")
    row = Connector(tenant_id=user.tenant_id, kind=body.kind, name=body.name, status="connected", config=body.config or {"mode": "sandbox"})
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "kind": row.kind, "status": row.status}


@router.post("/{connector_id}/sync")
def sync(connector_id: int, user: User = Depends(require("operator")), db: Session = Depends(get_db)):
    c = db.get(Connector, connector_id)
    if not c or c.tenant_id != user.tenant_id:
        raise HTTPException(404, "Connector not found")
    files = SANDBOX.get(c.kind, [])
    if c.kind == "local_db":
        ocrs = db.query(OCRResult).filter(OCRResult.tenant_id == user.tenant_id).all()
        files = [(f"document:{o.document_id}", o.text or "") for o in ocrs] or files
    n = 0
    titles = []
    for title, text in files:
        upsert_chunk(db, user.tenant_id, c.kind, f"{c.id}:{n}", title, text)
        titles.append(title)
        n += 1
    cfg = dict(c.config or {})
    cfg["files"] = titles
    c.config = cfg
    c.file_count = n
    c.last_sync_at = datetime.utcnow()
    db.commit()
    return {"synced": n, "kind": c.kind, "files": titles}
