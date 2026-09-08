from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.rag import upsert_chunk
from app.models import Connector, Document, OCRResult, User

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# Demo catalogs (not live OAuth). Paths are Source / Folder / File.
DEMO_CATALOGS: dict[str, dict] = {
    "google_drive": {
        "demo": True,
        "label": "Demo catalog (not live OAuth)",
        "sources": [
            {
                "id": "Drive",
                "name": "My Drive",
                "folders": [
                    {
                        "id": "Finance",
                        "name": "Finance",
                        "files": [
                            {
                                "id": "q3-invoices",
                                "name": "Q3-invoices.pdf",
                                "text": "TAX INVOICE GCS Tech Invoice No: INV-2201 Amount Due: USD 910.00",
                            },
                            {
                                "id": "vendor-w9",
                                "name": "vendor-w9.pdf",
                                "text": "Form W-9 Request for Taxpayer Identification Number and Certification vendor Harbor LLC",
                            },
                        ],
                    },
                    {
                        "id": "Legal",
                        "name": "Legal",
                        "files": [
                            {
                                "id": "msa-harbor",
                                "name": "MSA-Harbor.docx",
                                "text": "SERVICES AGREEMENT governing law Delaware parties GCS Tech and Harbor",
                            },
                            {
                                "id": "nda-template",
                                "name": "NDA-template.docx",
                                "text": "Mutual non-disclosure agreement confidential information term two years",
                            },
                        ],
                    },
                ],
            },
            {
                "id": "Shared drives",
                "name": "Shared drives",
                "folders": [
                    {
                        "id": "AP",
                        "name": "AP",
                        "files": [
                            {
                                "id": "ap-aging",
                                "name": "AP-aging.xlsx",
                                "text": "Accounts payable aging by vendor 30 60 90 days past due",
                            },
                        ],
                    },
                ],
            },
        ],
    },
    "microsoft": {
        "demo": True,
        "label": "Demo catalog (not live OAuth)",
        "sources": [
            {
                "id": "SharePoint",
                "name": "SharePoint",
                "folders": [
                    {
                        "id": "AP",
                        "name": "AP",
                        "files": [
                            {
                                "id": "vendor-onboarding",
                                "name": "vendor-onboarding.xlsx",
                                "text": "Vendor legal name, tax id, billing email columns for onboarding",
                            },
                            {
                                "id": "po-register",
                                "name": "PO-register.xlsx",
                                "text": "Purchase order register open POs receiving status",
                            },
                        ],
                    },
                    {
                        "id": "HR",
                        "name": "HR",
                        "files": [
                            {
                                "id": "onboarding-checklist",
                                "name": "onboarding-checklist.docx",
                                "text": "New hire checklist badge laptop payroll enrollment",
                            },
                        ],
                    },
                ],
            },
            {
                "id": "OneDrive",
                "name": "OneDrive",
                "folders": [
                    {
                        "id": "Ops",
                        "name": "Ops",
                        "files": [
                            {
                                "id": "site-checklist",
                                "name": "site-checklist.docx",
                                "text": "Site visit condition findings inspector sign-off",
                            },
                            {
                                "id": "safety-walk",
                                "name": "safety-walk.pdf",
                                "text": "Safety walkthrough findings PPE hazards corrective actions",
                            },
                        ],
                    },
                ],
            },
        ],
    },
}


def _path_join(*parts: str) -> str:
    return " / ".join(p for p in parts if p)


def _flatten_demo(kind: str) -> dict[str, tuple[str, str]]:
    """Map display path → (file_id, text) for demo catalogs."""
    out: dict[str, tuple[str, str]] = {}
    catalog = DEMO_CATALOGS.get(kind) or {}
    for src in catalog.get("sources") or []:
        for folder in src.get("folders") or []:
            for f in folder.get("files") or []:
                path = _path_join(src["id"], folder["id"], f["name"])
                out[path] = (f["id"], f.get("text") or "")
    return out


# Legacy flat titles (used when listing synced files before browse).
SANDBOX = {
    kind: [(path, text) for path, (_fid, text) in _flatten_demo(kind).items()]
    for kind in DEMO_CATALOGS
}
SANDBOX["local_db"] = [
    ("local_db.extracted_fields", "invoice_number amount date vendor classification"),
    ("local_db.documents", "ingested files with OCR text available for form generation"),
]


class ConnectorIn(BaseModel):
    kind: str
    name: str
    config: dict = {}


class SyncIn(BaseModel):
    paths: list[str] = Field(default_factory=list)


def _files_for(c: Connector) -> list[str]:
    stored = (c.config or {}).get("files")
    if stored:
        return list(stored)
    return [title for title, _ in SANDBOX.get(c.kind, [])]


def _get_connector(db: Session, connector_id: int, user: User) -> Connector:
    c = db.get(Connector, connector_id)
    if not c or c.tenant_id != user.tenant_id:
        raise HTTPException(404, "Connector not found")
    return c


def _parse_path(path: str | None) -> list[str]:
    if not path or not path.strip():
        return []
    # Accept both "A / B" and "A/B"
    raw = path.replace(" / ", "/").strip().strip("/")
    if not raw:
        return []
    return [p.strip() for p in raw.split("/") if p.strip()]


def _browse_demo(kind: str, parts: list[str]) -> dict:
    catalog = DEMO_CATALOGS[kind]
    sources = catalog["sources"]
    crumbs = []
    if not parts:
        return {
            "demo": True,
            "label": catalog["label"],
            "path": "",
            "breadcrumbs": [],
            "sources": [{"id": s["id"], "name": s["name"], "path": s["id"]} for s in sources],
            "folders": [],
            "files": [],
        }
    src = next((s for s in sources if s["id"] == parts[0]), None)
    if not src:
        raise HTTPException(404, "Source not found")
    crumbs.append({"id": src["id"], "name": src["name"], "path": src["id"]})
    if len(parts) == 1:
        return {
            "demo": True,
            "label": catalog["label"],
            "path": parts[0],
            "breadcrumbs": crumbs,
            "sources": [],
            "folders": [
                {"id": f["id"], "name": f["name"], "path": _path_join(src["id"], f["id"])}
                for f in src.get("folders") or []
            ],
            "files": [],
        }
    folder = next((f for f in src.get("folders") or [] if f["id"] == parts[1]), None)
    if not folder:
        raise HTTPException(404, "Folder not found")
    folder_path = _path_join(src["id"], folder["id"])
    crumbs.append({"id": folder["id"], "name": folder["name"], "path": folder_path})
    if len(parts) > 2:
        raise HTTPException(400, "Path too deep — stop at folder to select files")
    return {
        "demo": True,
        "label": catalog["label"],
        "path": folder_path,
        "breadcrumbs": crumbs,
        "sources": [],
        "folders": [],
        "files": [
            {
                "id": f["id"],
                "name": f["name"],
                "path": _path_join(src["id"], folder["id"], f["name"]),
            }
            for f in folder.get("files") or []
        ],
    }


def _browse_local_db(db: Session, user: User, parts: list[str]) -> dict:
    """Browse tenant documents / OCR as Source → Folder → Files."""
    docs = (
        db.query(Document)
        .filter(Document.tenant_id == user.tenant_id)
        .order_by(Document.id.desc())
        .all()
    )
    ocrs = {
        o.document_id: o
        for o in db.query(OCRResult).filter(OCRResult.tenant_id == user.tenant_id).all()
    }
    sources = [
        {"id": "Library", "name": "Document library", "path": "Library"},
        {"id": "OCR", "name": "OCR results", "path": "OCR"},
    ]
    label = "Local database (tenant library)"
    if not parts:
        return {
            "demo": False,
            "label": label,
            "path": "",
            "breadcrumbs": [],
            "sources": sources,
            "folders": [],
            "files": [],
        }

    src_id = parts[0]
    if src_id not in ("Library", "OCR"):
        raise HTTPException(404, "Source not found")
    crumbs = [{"id": src_id, "name": next(s["name"] for s in sources if s["id"] == src_id), "path": src_id}]

    # Folders: by classification (or Unclassified), plus All
    classes: dict[str, list[Document]] = {}
    for d in docs:
        key = d.classification or "Unclassified"
        classes.setdefault(key, []).append(d)
    folder_ids = ["All", *sorted(classes.keys())]

    if len(parts) == 1:
        return {
            "demo": False,
            "label": label,
            "path": src_id,
            "breadcrumbs": crumbs,
            "sources": [],
            "folders": [{"id": fid, "name": fid, "path": _path_join(src_id, fid)} for fid in folder_ids],
            "files": [],
        }

    folder_id = parts[1]
    if folder_id not in folder_ids and folder_id != "All":
        # Allow folder even if empty classification set changed
        if folder_id not in classes and folder_id != "All":
            raise HTTPException(404, "Folder not found")
    folder_path = _path_join(src_id, folder_id)
    crumbs.append({"id": folder_id, "name": folder_id, "path": folder_path})
    if len(parts) > 2:
        raise HTTPException(400, "Path too deep — stop at folder to select files")

    selected = docs if folder_id == "All" else classes.get(folder_id, [])
    files = []
    for d in selected:
        if src_id == "OCR" and d.id not in ocrs:
            continue
        name = d.filename or f"document:{d.id}"
        files.append(
            {
                "id": f"document:{d.id}",
                "name": name,
                "path": _path_join(src_id, folder_id, f"document:{d.id}"),
            }
        )

    # Fallback demo rows when library empty
    if not files and not docs:
        if src_id == "Library":
            files = [
                {
                    "id": "local_db.documents",
                    "name": "documents (sample)",
                    "path": _path_join(src_id, folder_id, "documents (sample)"),
                }
            ]
        else:
            files = [
                {
                    "id": "local_db.extracted_fields",
                    "name": "extracted_fields (sample)",
                    "path": _path_join(src_id, folder_id, "extracted_fields (sample)"),
                }
            ]

    return {
        "demo": False,
        "label": label,
        "path": folder_path,
        "breadcrumbs": crumbs,
        "sources": [],
        "folders": [],
        "files": files,
    }


def _resolve_demo_files(kind: str, paths: list[str] | None) -> list[tuple[str, str, str]]:
    """Return list of (source_id, title, text)."""
    flat = _flatten_demo(kind)
    if not paths:
        return [(fid, path, text) for path, (fid, text) in flat.items()]
    out = []
    for path in paths:
        # Normalize display path
        key = path.replace("/", " / ").replace("  /  ", " / ")
        # Also try exact and slash-normalized variants
        candidates = [path, key, " / ".join(_parse_path(path))]
        hit = None
        for cand in candidates:
            if cand in flat:
                hit = (cand, flat[cand])
                break
            # case-sensitive match on joined parts
            joined = " / ".join(_parse_path(cand))
            if joined in flat:
                hit = (joined, flat[joined])
                break
        if not hit:
            raise HTTPException(400, f"Unknown path: {path}")
        title, (fid, text) = hit[0], hit[1]
        out.append((fid, title, text))
    return out


def _resolve_local_files(db: Session, user: User, paths: list[str] | None) -> list[tuple[str, str, str]]:
    ocrs = {
        o.document_id: o
        for o in db.query(OCRResult).filter(OCRResult.tenant_id == user.tenant_id).all()
    }
    docs = {d.id: d for d in db.query(Document).filter(Document.tenant_id == user.tenant_id).all()}

    if not paths:
        # Prefer real OCR; else sandbox samples
        if ocrs:
            return [
                (f"document:{doc_id}", f"document:{doc_id}", o.text or "")
                for doc_id, o in ocrs.items()
            ]
        return [(title, title, text) for title, text in SANDBOX["local_db"]]

    out = []
    for path in paths:
        parts = _parse_path(path)
        leaf = parts[-1] if parts else path
        if leaf.startswith("document:"):
            try:
                doc_id = int(leaf.split(":", 1)[1])
            except ValueError as exc:
                raise HTTPException(400, f"Bad document path: {path}") from exc
            doc = docs.get(doc_id)
            if not doc:
                raise HTTPException(404, f"Document not found: {leaf}")
            ocr = ocrs.get(doc_id)
            text = (ocr.text if ocr else "") or f"Document {doc.filename} (no OCR text yet)"
            title = doc.filename or leaf
            out.append((leaf, title, text))
        elif leaf in ("documents (sample)", "local_db.documents") or "documents" in leaf:
            out.append(("local_db.documents", "local_db.documents", SANDBOX["local_db"][1][1]))
        elif leaf in ("extracted_fields (sample)", "local_db.extracted_fields") or "extracted" in leaf:
            out.append(("local_db.extracted_fields", "local_db.extracted_fields", SANDBOX["local_db"][0][1]))
        else:
            raise HTTPException(400, f"Unknown path: {path}")
    return out


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
            "demo": c.kind in DEMO_CATALOGS,
        }
        for c in rows
    ]


@router.post("")
def connect(body: ConnectorIn, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    if body.kind not in ("google_drive", "microsoft", "local_db", "local_files"):
        raise HTTPException(400, "Unknown connector")
    mode = "local" if body.kind == "local_db" else "sandbox"
    row = Connector(
        tenant_id=user.tenant_id,
        kind=body.kind,
        name=body.name,
        status="connected",
        config=body.config or {"mode": mode},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "kind": row.kind, "status": row.status}


@router.get("/{connector_id}/browse")
def browse(
    connector_id: int,
    path: str = Query("", description="Source / Folder path; empty lists sources"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    c = _get_connector(db, connector_id, user)
    parts = _parse_path(path)
    if c.kind in DEMO_CATALOGS:
        payload = _browse_demo(c.kind, parts)
    elif c.kind == "local_db":
        payload = _browse_local_db(db, user, parts)
    else:
        raise HTTPException(400, "Browse not supported for this connector")
    return {
        "connector_id": c.id,
        "kind": c.kind,
        **payload,
    }


@router.post("/{connector_id}/sync")
def sync(
    connector_id: int,
    body: SyncIn | None = None,
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    c = _get_connector(db, connector_id, user)
    paths = list((body.paths if body else None) or [])

    if c.kind in DEMO_CATALOGS:
        resolved = _resolve_demo_files(c.kind, paths or None)
    elif c.kind == "local_db":
        resolved = _resolve_local_files(db, user, paths or None)
    else:
        raise HTTPException(400, "Sync not supported for this connector")

    n = 0
    titles = []
    for fid, title, text in resolved:
        upsert_chunk(db, user.tenant_id, c.kind, f"{c.id}:{fid}", title, text)
        titles.append(title)
        n += 1
    cfg = dict(c.config or {})
    cfg["files"] = titles
    if paths:
        cfg["last_selected_paths"] = paths
    c.config = cfg
    c.file_count = n
    c.last_sync_at = datetime.utcnow()
    db.commit()
    return {"synced": n, "kind": c.kind, "files": titles, "paths": paths}
