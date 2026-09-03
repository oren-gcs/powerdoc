from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings


def generate(role: str, prompt: str, model: str | None = None) -> dict[str, Any]:
    """Best available generator: OpenAI → Ollama → heuristic."""
    settings = get_settings()
    if settings.openai_api_key:
        try:
            return _openai(prompt, model or settings.openai_model)
        except Exception as exc:
            return {"text": _heuristic(role, prompt), "model": "heuristic", "provider": "fallback", "error": str(exc)}
    if _ollama_up(settings.ollama_url):
        try:
            return _ollama(settings.ollama_url, model or "qwen2.5:3b", prompt)
        except Exception as exc:
            return {"text": _heuristic(role, prompt), "model": "heuristic", "provider": "fallback", "error": str(exc)}
    return {"text": _heuristic(role, prompt), "model": "heuristic", "provider": "heuristic"}


def _ollama_up(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/api/tags", timeout=0.4)
        return r.status_code == 200
    except Exception:
        return False


def _ollama(url: str, model: str, prompt: str) -> dict[str, Any]:
    r = httpx.post(
        f"{url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    return {"text": data.get("response", ""), "model": model, "provider": "ollama"}


def _openai(prompt: str, model: str) -> dict[str, Any]:
    settings = get_settings()
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
        timeout=45.0,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return {"text": text, "model": model, "provider": "openai"}


def _heuristic(role: str, prompt: str) -> str:
    lowered = prompt.lower()
    if role == "ocr":
        return "Heuristic OCR complete. Use the extracted text layer; no vision model is bound."
    if role == "workflow":
        return (
            "Execute steps in declared order: extract text, classify, extract fields, "
            "apply conditions, notify operators, and record analytics. Skip notify if no recipient."
        )
    if role == "notification":
        return "A document finished processing. Open DocFlow to review OCR, classification, and the workflow run."
    if role == "analytics":
        return "Processing volume is healthy. Invoice and contract classes dominate inbound flow this period."
    if role == "summarize":
        snippet = prompt[-400:]
        return f"Summary: this document covers operational content. Key excerpt: {snippet[:240]}"
    if "invoice" in lowered:
        return "Invoice intake: extract vendor, amount, due date; route to AP if amount present."
    return json.dumps({"role": role, "decision": "continue", "note": "heuristic agent — bind Ollama or OpenAI for richer reasoning"})
