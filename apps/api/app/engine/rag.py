from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Document, ExtractedField, FeatureFlag, KnowledgeChunk, OCRResult

# Maps KnowledgeChunk.source_type → feature flag that gates inclusion in retrieve().
SOURCE_KIND_FLAGS = {
    "google_drive": "rag_source_google_drive",
    "microsoft": "rag_source_microsoft",
    "local_db": "rag_source_local_db",
    "local_files": "rag_source_local_files",
    "ocr": "rag_source_ocr",
    "form_submission": "rag_source_forms",
    "form_digest": "rag_source_forms",
    "form_summary": "rag_source_forms",
    "form_insights": "rag_source_forms",
}

# Documented retrieve defaults (form compose uses a stricter floor).
RAG_MIN_SCORE_DEFAULT = 1
RAG_MIN_SCORE_FORM_COMPOSE = 3


def rag_master_enabled(db: Session) -> bool:
    row = db.query(FeatureFlag).filter(FeatureFlag.key == "rag").first()
    return True if row is None else bool(row.enabled)


def enabled_source_kinds(db: Session) -> set[str]:
    flags = {f.key: f.enabled for f in db.query(FeatureFlag).filter(FeatureFlag.key.like("rag_source_%")).all()}
    out = set()
    for kind, key in SOURCE_KIND_FLAGS.items():
        if flags.get(key, True):
            out.add(kind)
    return out


def upsert_chunk(
    db: Session,
    tenant_id: int,
    source_type: str,
    source_id: str,
    title: str,
    text: str,
    locale: str = "en",
    tags: list | None = None,
) -> None:
    row = (
        db.query(KnowledgeChunk)
        .filter(
            KnowledgeChunk.tenant_id == tenant_id,
            KnowledgeChunk.source_type == source_type,
            KnowledgeChunk.source_id == str(source_id),
        )
        .first()
    )
    if row:
        row.title = title
        row.text = text[:8000]
        row.locale = locale
        if tags is not None:
            row.tags = list(tags)
    else:
        db.add(
            KnowledgeChunk(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=str(source_id),
                title=title,
                text=text[:8000],
                locale=locale,
                tags=list(tags or []),
            )
        )


def retrieve(
    db: Session,
    tenant_id: int,
    query: str,
    limit: int = 8,
    *,
    min_score: int = RAG_MIN_SCORE_DEFAULT,
    fallback_fields: bool = True,
) -> list[dict]:
    if not rag_master_enabled(db):
        return []
    stop = {
        "the", "and", "for", "with", "was", "did", "which", "user", "from", "this", "that",
        "today", "were", "have", "been", "your", "their", "them", "then", "than", "into",
        "about", "after", "before", "over", "under", "also", "just", "only", "here", "there",
        "http", "https", "www",
    }
    tokens = [t.lower().strip(".,;:") for t in query.replace(",", " ").split() if len(t) > 3 and t.lower().strip(".,;:") not in stop]
    allowed = enabled_source_kinds(db)
    rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.tenant_id == tenant_id).all()
    scored = []
    for r in rows:
        if r.source_type not in allowed:
            continue
        hay = f"{r.title} {r.text}".lower()
        score = sum(1 for t in tokens if t in hay)
        if score >= min_score:
            scored.append((score, r))
    if not scored:
        ocrs = db.query(OCRResult).filter(OCRResult.tenant_id == tenant_id).all()
        for o in ocrs:
            hay = (o.text or "").lower()
            score = sum(1 for t in tokens if t in hay)
            if score >= min_score:
                scored.append((score, o))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, r in scored[:limit]:
        if isinstance(r, KnowledgeChunk):
            out.append({"title": r.title, "text": r.text[:1200], "source": r.source_type, "score": score, "tags": list(r.tags or [])})
        else:
            out.append({"title": f"document:{r.document_id}", "text": (r.text or "")[:1200], "source": "ocr", "score": score, "tags": []})
    if not out and fallback_fields:
        fields = (
            db.query(ExtractedField)
            .join(Document, Document.id == ExtractedField.document_id)
            .filter(Document.tenant_id == tenant_id)
            .limit(20)
            .all()
        )
        if fields:
            text = ", ".join(f"{f.name}={f.value}" for f in fields)
            out.append({"title": "extracted fields", "text": text, "source": "fields", "score": 1, "tags": []})
    return out
