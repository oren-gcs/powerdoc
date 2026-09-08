"""Defensive upload scanning for form file/image fields.

Rejects dangerous or mismatched payloads before storage. Never executes uploads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

# Size caps (bytes)
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_IMAGES = 10
HARD_MAX_BYTES = 25 * 1024 * 1024

# Extension / MIME allowlists (lowercase, no dots on extensions)
IMAGE_EXTS = frozenset({"png", "jpg", "jpeg", "webp", "gif"})
DOC_EXTS = frozenset({"pdf", "txt", "docx", "png", "jpg", "jpeg", "webp", "gif"})

IMAGE_MIMES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/gif",
    }
)
DOC_MIMES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # only accepted when magic bytes match an allowlisted type
    }
) | IMAGE_MIMES

# Dangerous extensions always rejected
DANGEROUS_EXTS = frozenset(
    {
        "exe",
        "dll",
        "so",
        "dylib",
        "bat",
        "cmd",
        "com",
        "msi",
        "scr",
        "ps1",
        "vbs",
        "js",
        "jse",
        "wsf",
        "wsh",
        "hta",
        "cpl",
        "jar",
        "apk",
        "sh",
        "bash",
        "zsh",
        "php",
        "phtml",
        "asp",
        "aspx",
        "cgi",
        "pl",
        "py",
        "rb",
        "wasm",
        "html",
        "htm",
        "shtml",
        "svg",  # SVG rejected by default (scriptable); not in image allowlist
        "xml",
        "xhtml",
    }
)

_SCRIPTISH = re.compile(
    rb"(?i)<\s*script|javascript:|on(load|error|click|mouse\w+)\s*=|<\s*iframe|<\s*object|<\s*embed|<\s*foreignobject"
)


@dataclass(frozen=True)
class ScanResult:
    ok: bool
    reason: str
    sniffed_mime: str | None = None
    size: int = 0
    status: str = "rejected"  # clean | rejected

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "sniffed_mime": self.sniffed_mime,
            "size": self.size,
            "status": self.status,
        }


def _ext(filename: str) -> str:
    name = PurePosixPath((filename or "").replace("\\", "/").split("/")[-1]).name
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower().strip()


def _norm_mime(content_type: str | None) -> str:
    raw = (content_type or "").split(";", 1)[0].strip().lower()
    if raw == "image/jpg":
        return "image/jpeg"
    return raw


def sniff_mime(data: bytes) -> str | None:
    """Identify common formats from magic bytes. Returns None if unknown."""
    if not data:
        return None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"PK\x03\x04"):
        # OOXML / zip container — treat as docx when [Content_Types].xml present
        head = data[:8192]
        if b"[Content_Types].xml" in head or b"word/" in head:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/zip"
    # Plain text: printable + newlines only (small sample)
    sample = data[:4096]
    if sample and all(b in (9, 10, 13) or 32 <= b < 127 for b in sample):
        # Reject obvious HTML pretending to be text
        low = sample.lower().lstrip()
        if low.startswith((b"<!doctype html", b"<html", b"<svg", b"<?xml")):
            return "text/html"
        return "text/plain"
    return None


def _looks_executable(data: bytes) -> bool:
    if data.startswith(b"MZ"):  # PE / DOS
        return True
    if data.startswith(b"\x7fELF"):
        return True
    if data.startswith((b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe")):
        return True
    if data.startswith(b"#!"):
        return True
    return False


def _html_or_svg_payload(data: bytes) -> bool:
    head = data[:16384].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html", b"<svg", b"<?xml")):
        return True
    if b"<svg" in data[:65536].lower() and _SCRIPTISH.search(data[:65536]):
        return True
    if _SCRIPTISH.search(data[:65536]) and (b"<html" in head or b"<body" in head or b"<script" in head):
        return True
    return False


def _polyglot_image_reject(data: bytes, sniffed: str) -> str | None:
    """Basic polyglot checks when content sniffs as an image."""
    if sniffed not in IMAGE_MIMES:
        return None
    # Trailing / embedded HTML or script markers (common polyglot trick)
    tail = data[-8192:] if len(data) > 8192 else data
    if _SCRIPTISH.search(tail) or _SCRIPTISH.search(data[:4096]):
        return "image contains script-like content"
    if b"<!DOCTYPE html" in data or b"<html" in data[:65536].lower():
        return "image/html polyglot rejected"
    return None


def _pdf_active_content(data: bytes) -> str | None:
    """Reject PDFs with obvious active content markers (defensive heuristic)."""
    sample = data[:512_000]
    # Common active-content name tokens in PDF (case-sensitive per PDF conventions)
    for marker in (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile", b"/RichMedia"):
        if marker in sample:
            return f"pdf active content rejected ({marker.decode('ascii', errors='ignore')})"
    return None


def _parse_accept(accept: list[str] | None, kind: str) -> tuple[set[str], set[str]]:
    """Return (allowed_exts, allowed_mimes) from field accept list or defaults."""
    if kind == "images":
        default_exts, default_mimes = set(IMAGE_EXTS), set(IMAGE_MIMES)
    else:
        default_exts, default_mimes = set(DOC_EXTS), set(DOC_MIMES)

    if not accept:
        return default_exts, default_mimes

    exts: set[str] = set()
    mimes: set[str] = set()
    for item in accept:
        s = str(item or "").strip().lower()
        if not s:
            continue
        if s.startswith("."):
            s = s[1:]
        if "/" in s:
            if s == "image/jpg":
                s = "image/jpeg"
            if s == "image/*":
                mimes |= set(IMAGE_MIMES)
                exts |= set(IMAGE_EXTS)
            else:
                mimes.add(s)
                # map common mimes → ext
                for ext, mime in (
                    ("png", "image/png"),
                    ("jpg", "image/jpeg"),
                    ("jpeg", "image/jpeg"),
                    ("webp", "image/webp"),
                    ("gif", "image/gif"),
                    ("pdf", "application/pdf"),
                    ("txt", "text/plain"),
                    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                ):
                    if s == mime:
                        exts.add(ext)
        else:
            exts.add(s)
            for ext, mime in (
                ("png", "image/png"),
                ("jpg", "image/jpeg"),
                ("jpeg", "image/jpeg"),
                ("webp", "image/webp"),
                ("gif", "image/gif"),
                ("pdf", "application/pdf"),
                ("txt", "text/plain"),
                ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ):
                if s == ext:
                    mimes.add(mime)
    if not exts and not mimes:
        return default_exts, default_mimes
    if not mimes:
        mimes = set(default_mimes)
    return exts, mimes


def scan_upload(
    data: bytes,
    filename: str,
    content_type: str | None,
    *,
    kind: str = "file",
    accept: list[str] | None = None,
    max_bytes: int | None = None,
) -> dict:
    """Scan upload bytes. Returns {ok, reason, sniffed_mime, size, status}.

    kind: "file" (document) or "images" (image-only).
    """
    size = len(data or b"")
    if size == 0:
        return ScanResult(False, "empty file", size=0).as_dict()

    cap = max_bytes
    if cap is None:
        cap = MAX_IMAGE_BYTES if kind == "images" else MAX_FILE_BYTES
    cap = min(int(cap), HARD_MAX_BYTES)
    if size > cap:
        return ScanResult(False, f"file too large (max {cap} bytes)", size=size).as_dict()

    ext = _ext(filename)
    if ext in DANGEROUS_EXTS:
        return ScanResult(False, f"disallowed extension .{ext}", size=size).as_dict()

    if _looks_executable(data):
        return ScanResult(False, "executable or script payload rejected", size=size).as_dict()

    sniffed = sniff_mime(data)
    declared = _norm_mime(content_type)
    allowed_exts, allowed_mimes = _parse_accept(accept, kind)

    if kind == "images":
        # Images never accept SVG/HTML even if caller tries via accept
        allowed_exts -= {"svg", "html", "htm", "xml"}
        allowed_mimes -= {"image/svg+xml", "text/html", "application/xhtml+xml"}

    if ext and ext not in allowed_exts:
        return ScanResult(False, f"extension .{ext} not in allowlist", sniffed_mime=sniffed, size=size).as_dict()

    if not sniffed:
        return ScanResult(False, "unrecognized file content", sniffed_mime=None, size=size).as_dict()

    if sniffed == "application/zip":
        return ScanResult(False, "raw zip archives not allowed", sniffed_mime=sniffed, size=size).as_dict()

    if sniffed == "text/html" or (sniffed not in IMAGE_MIMES and _html_or_svg_payload(data)):
        return ScanResult(False, "HTML/SVG content rejected", sniffed_mime=sniffed or "text/html", size=size).as_dict()

    if kind == "images" and sniffed not in IMAGE_MIMES:
        return ScanResult(False, f"not an image (sniffed {sniffed})", sniffed_mime=sniffed, size=size).as_dict()

    if sniffed not in allowed_mimes and sniffed not in IMAGE_MIMES | {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return ScanResult(False, f"content type {sniffed} not allowed", sniffed_mime=sniffed, size=size).as_dict()

    # MIME allowlist: sniffed must be in field allowlist (octet-stream declared is ok if sniff matches)
    if sniffed not in allowed_mimes:
        # Allow jpeg alias / image kinds when ext allowlisted
        if not (ext and ext in allowed_exts and sniffed in (IMAGE_MIMES | {"application/pdf", "text/plain"})):
            return ScanResult(False, f"sniffed type {sniffed} not in accept list", sniffed_mime=sniffed, size=size).as_dict()

    # Declared Content-Type must not contradict sniff (when provided and not generic)
    if declared and declared not in ("application/octet-stream", "binary/octet-stream"):
        if declared != sniffed and not (
            declared == "image/jpg" and sniffed == "image/jpeg"
        ):
            # Allow text/plain declared for txt; otherwise mismatch = reject
            return ScanResult(
                False,
                f"content-type mismatch (declared {declared}, sniffed {sniffed})",
                sniffed_mime=sniffed,
                size=size,
            ).as_dict()

    if sniffed in IMAGE_MIMES:
        poly = _polyglot_image_reject(data, sniffed)
        if poly:
            return ScanResult(False, poly, sniffed_mime=sniffed, size=size).as_dict()

    if sniffed == "application/pdf":
        pdf_bad = _pdf_active_content(data)
        if pdf_bad:
            return ScanResult(False, pdf_bad, sniffed_mime=sniffed, size=size).as_dict()

    return ScanResult(True, "clean", sniffed_mime=sniffed, size=size, status="clean").as_dict()
