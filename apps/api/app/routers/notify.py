from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.engine.mail import send_smtp, smtp_configured
from app.models import Notification, User

logger = logging.getLogger("docflow.notify")

router = APIRouter(prefix="/api/v1/notify", tags=["notify"])


class SendEmailRequest(BaseModel):
    to: list[EmailStr] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=50_000)
    html: str | None = None
    related_type: str | None = None
    related_id: int | None = None


class SendEmailResponse(BaseModel):
    status: str
    delivered: int
    channel: str
    detail: str | None = None


@router.get("/status")
def notify_status():
    return {"service": "notify", "smtp_configured": smtp_configured()}


@router.post("/email", response_model=SendEmailResponse)
def send_email(
    payload: SendEmailRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> SendEmailResponse:
    recipients = [str(a) for a in payload.to]
    status = "recorded"
    detail = "SMTP not configured; notification stored only"
    delivered = 0

    if smtp_configured():
        try:
            send_smtp(to=recipients, subject=payload.subject, body=payload.body, html=payload.html)
            status = "sent"
            detail = None
            delivered = len(recipients)
        except Exception:
            logger.exception("smtp send failed")
            status = "failed"
            detail = "smtp send failed"

    for addr in recipients:
        db.add(
            Notification(
                tenant_id=user.tenant_id,
                user_id=user.id,
                channel="email",
                subject=payload.subject,
                body=payload.body[:4000],
                status=status,
                extra={
                    "recipient": addr,
                    "related_type": payload.related_type,
                    "related_id": payload.related_id,
                    "detail": detail,
                },
            )
        )
    db.commit()
    return SendEmailResponse(status=status, delivered=delivered, channel="email", detail=detail)


@router.get("/recent")
def recent_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[dict[str, Any]]:
    rows = (
        db.query(Notification)
        .filter(Notification.tenant_id == user.tenant_id)
        .order_by(Notification.id.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
    return [
        {
            "id": n.id,
            "channel": n.channel,
            "recipient": (n.extra or {}).get("recipient"),
            "subject": n.subject,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]
