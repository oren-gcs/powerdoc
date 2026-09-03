from __future__ import annotations

import io
import re
from pathlib import Path

from pypdf import PdfReader


def extract_text(filename: str, data: bytes) -> dict:
    name = filename.lower()
    if name.endswith(".txt") or name.endswith(".md") or name.endswith(".csv"):
        text = data.decode("utf-8", errors="ignore")
        return {"engine": "text", "text": text, "confidence": 0.99, "page_count": 1}
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages).strip()
            conf = 0.92 if text else 0.2
            return {"engine": "pypdf", "text": text or "[scanned PDF — no embedded text]", "confidence": conf, "page_count": len(pages)}
        except Exception as exc:
            return {"engine": "pypdf", "text": f"[pdf parse error: {exc}]", "confidence": 0.0, "page_count": 0}
    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")):
        tess = _tesseract(data)
        if tess:
            return tess
        return {
            "engine": "image-fallback",
            "text": f"[image {filename} — install tesseract for visual OCR; filename used as hint]",
            "confidence": 0.15,
            "page_count": 1,
        }
    # Office-ish or unknown: best-effort utf-8
    text = data.decode("utf-8", errors="ignore")
    if len(re.sub(r"\s+", "", text)) > 20:
        return {"engine": "utf8", "text": text, "confidence": 0.6, "page_count": 1}
    return {
        "engine": "binary-fallback",
        "text": f"Binary file {filename} ({len(data)} bytes). No text layer found.",
        "confidence": 0.1,
        "page_count": 1,
    }


def _tesseract(data: bytes) -> dict | None:
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)
        return {"engine": "tesseract", "text": text, "confidence": 0.85 if text.strip() else 0.3, "page_count": 1}
    except Exception:
        return None


def guess_language(text: str) -> str:
    sample = text.lower()
    if any(w in sample for w in ("the ", "invoice", "agreement", "and ")):
        return "en"
    if any(w in sample for w in ("der ", "die ", "rechnung")):
        return "de"
    if any(w in sample for w in ("le ", "la ", "facture")):
        return "fr"
    return "en"
