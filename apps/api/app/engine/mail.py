from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("docflow.mail")


def smtp_configured() -> bool:
    return bool(get_settings().smtp_host.strip())


def send_smtp(*, to: list[str], subject: str, body: str, html: str | None = None) -> None:
    s = get_settings()
    if not s.smtp_host.strip():
        raise RuntimeError("SMTP not configured")
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body or "")
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as client:
        client.ehlo()
        try:
            client.starttls()
            client.ehlo()
        except smtplib.SMTPException:
            pass
        user = (s.smtp_user or "").strip()
        if user:
            client.login(user, s.smtp_password)
        client.send_message(msg)
