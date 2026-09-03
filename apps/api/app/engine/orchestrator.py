from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.engine.workflow import execute_workflow, _load_text, _log
from app.classify import classify_document
from app.models import Activity, Automation, Document, Notification, Workflow, WorkflowRun
from app.storage import storage


def match_automation(db: Session, tenant_id: int, trigger_type: str, payload: dict) -> Automation | None:
    autos = (
        db.query(Automation)
        .filter(Automation.tenant_id == tenant_id, Automation.is_active.is_(True), Automation.trigger_type == trigger_type)
        .all()
    )
    classification = (payload.get("classification") or "").lower()
    for auto in autos:
        cfg = auto.trigger_config or {}
        wanted = (cfg.get("classification") or "").lower()
        if wanted and wanted != classification:
            continue
        return auto
    return autos[0] if autos and trigger_type == "on_upload" else None


def process_document(
    db: Session,
    document: Document,
    *,
    enable_ocr: bool = True,
    enable_workflow: bool = True,
    enable_notification: bool = True,
    enable_analytics: bool = True,
    workflow_id: int | None = None,
) -> dict:
    result = {
        "status": "processing",
        "document": {"id": document.id, "filename": document.filename},
        "ocr": None,
        "classification": None,
        "workflow": None,
        "notification": None,
        "analytics": None,
        "errors": [],
    }
    try:
        if enable_ocr:
            text = _load_text(db, document)
            result["ocr"] = {"chars": len(text), "preview": text[:400]}
            classified = classify_document(document.filename, text)
            document.classification = classified["label"]
            result["classification"] = classified
            _log(db, "orchestrator", "ocr_classify", classified["label"], document.tenant_id, classified)

        if enable_workflow:
            workflow = None
            if workflow_id:
                workflow = db.get(Workflow, workflow_id)
            if not workflow:
                auto = match_automation(
                    db,
                    document.tenant_id,
                    "on_classify" if document.classification else "on_upload",
                    {"classification": document.classification},
                )
                if auto:
                    workflow = db.get(Workflow, auto.workflow_id)
                    auto.last_fired_at = datetime.utcnow()
                    auto.fire_count = (auto.fire_count or 0) + 1
            if not workflow:
                workflow = (
                    db.query(Workflow)
                    .filter(Workflow.tenant_id == document.tenant_id, Workflow.is_active.is_(True))
                    .order_by(Workflow.id.asc())
                    .first()
                )
            if workflow:
                run = execute_workflow(db, workflow, document)
                result["workflow"] = {
                    "workflow_id": workflow.id,
                    "name": workflow.name,
                    "run_id": run.id,
                    "status": run.status,
                    "decision": (run.output or {}).get("agent_decision"),
                }
            else:
                result["errors"].append("No active workflow for tenant")

        if enable_notification:
            n = Notification(
                tenant_id=document.tenant_id,
                user_id=document.user_id,
                channel="in_app",
                subject=f"Processed {document.filename}",
                body=f"Status {document.status}. Class: {document.classification or 'pending'}.",
                extra={"document_id": document.id},
            )
            db.add(n)
            db.flush()
            result["notification"] = {"id": n.id, "subject": n.subject}

        if enable_analytics:
            db.add(
                Activity(
                    tenant_id=document.tenant_id,
                    user_id=document.user_id,
                    activity_type="document_processed",
                    details={"document_id": document.id, "classification": document.classification},
                )
            )
            result["analytics"] = {"tracked": True}

        result["status"] = "completed" if not result["errors"] else "partial_success"
        if document.status != "failed":
            document.status = "ready"
        _log(db, "orchestrator", "process_document", result["status"], document.tenant_id, result)
        db.commit()
        db.refresh(document)
        result["document"]["status"] = document.status
        result["document"]["classification"] = document.classification
        return result
    except Exception as exc:
        db.rollback()
        result["status"] = "failed"
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        return result
