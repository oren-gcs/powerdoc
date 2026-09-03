from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require
from app.engine.orchestrator import process_document
from app.models import Activity, Document, ExtractedField, OCRResult, User
from app.schemas import DocumentOut
from app.storage import storage

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _scope(db: Session, user: User):
    q = db.query(Document)
    if user.role != "platform_admin":
        q = q.filter(Document.tenant_id == user.tenant_id)
    return q


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _scope(db, user).order_by(Document.id.desc()).limit(200).all()


@router.post("", response_model=DocumentOut)
@router.post("/upload", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    run_pipeline: bool = True,
    user: User = Depends(require("operator")),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    import hashlib

    key = storage.put(user.tenant_id, file.filename or "untitled", data)
    doc = Document(
        tenant_id=user.tenant_id,
        user_id=user.id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        storage_key=key,
        checksum=hashlib.sha256(data).hexdigest(),
        status="uploaded",
        tags=[],
    )
    db.add(doc)
    db.add(
        Activity(
            tenant_id=user.tenant_id,
            user_id=user.id,
            activity_type="document_upload",
            details={"filename": doc.filename},
        )
    )
    db.commit()
    db.refresh(doc)
    if run_pipeline:
        process_document(db, doc)
        db.refresh(doc)
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _scope(db, user).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{document_id}/detail")
def document_detail(document_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _scope(db, user).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    ocr = db.query(OCRResult).filter(OCRResult.document_id == doc.id).order_by(OCRResult.id.desc()).first()
    fields = db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).all()
    return {
        "document": DocumentOut.model_validate(doc).model_dump(),
        "ocr": None
        if not ocr
        else {
            "engine": ocr.engine,
            "text": ocr.text,
            "confidence": ocr.confidence,
            "language": ocr.language,
            "page_count": ocr.page_count,
        },
        "fields": [{"name": f.name, "value": f.value, "confidence": f.confidence} for f in fields],
    }


@router.get("/{document_id}/download")
def download(document_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _scope(db, user).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    data = storage.get(doc.storage_key)
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/{document_id}")
def delete_document(document_id: int, user: User = Depends(require("admin")), db: Session = Depends(get_db)):
    doc = _scope(db, user).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    storage.delete(doc.storage_key)
    db.delete(doc)
    db.commit()
    return {"ok": True}
