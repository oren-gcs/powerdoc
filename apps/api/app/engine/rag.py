from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ExtractedField, KnowledgeChunk, OCRResult


def upsert_chunk(db: Session, tenant_id: int, source_type: str, source_id: str, title: str, text: str, locale: str = "en") -> None:
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
    else:
        db.add(
            KnowledgeChunk(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=str(source_id),
                title=title,
                text=text[:8000],
                locale=locale,
            )
        )


def retrieve(db: Session, tenant_id: int, query: str, limit: int = 8, *, min_score: int = 1, fallback_fields: bool = True) -> list[dict]:
    stop = {
        "the", "and", "for", "with", "was", "did", "which", "user", "from", "this", "that",
        "today", "were", "have", "been", "your", "their", "them", "then", "than", "into",
        "about", "after", "before", "over", "under", "also", "just", "only", "here", "there",
        "http", "https", "www",
    }
    tokens = [t.lower().strip(".,;:") for t in query.replace(",", " ").split() if len(t) > 3 and t.lower().strip(".,;:") not in stop]
    rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.tenant_id == tenant_id).all()
    scored = []
    for r in rows:
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
            out.append({"title": r.title, "text": r.text[:1200], "source": r.source_type, "score": score})
        else:
            out.append({"title": f"document:{r.document_id}", "text": (r.text or "")[:1200], "source": "ocr", "score": score})
    if not out and fallback_fields:
        fields = db.query(ExtractedField).limit(20).all()
        if fields:
            text = ", ".join(f"{f.name}={f.value}" for f in fields)
            out.append({"title": "extracted fields", "text": text, "source": "fields", "score": 1})
    return out
