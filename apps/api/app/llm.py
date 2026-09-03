from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.config import get_settings

_status_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def ollama_status(url: str | None = None) -> dict[str, Any]:
    """Probe local Ollama. Cached a few seconds so compose/status do not stack timeouts."""
    settings = get_settings()
    base = (url or settings.ollama_url).rstrip("/")
    now = time.monotonic()
    hit = _status_cache.get(base)
    if hit and now - hit[0] < 4.0:
        return dict(hit[1])
    try:
        r = httpx.get(f"{base}/api/tags", timeout=1.2)
        r.raise_for_status()
        models = [m.get("name") for m in (r.json().get("models") or []) if m.get("name")]
        preferred = settings.ollama_model.strip()
        default = preferred if preferred in models else (models[0] if models else preferred or "")
        out: dict[str, Any] = {"up": True, "url": base, "models": models, "default": default, "error": None}
    except Exception as exc:
        out = {"up": False, "url": base, "models": [], "default": settings.ollama_model, "error": str(exc)}
    _status_cache[base] = (now, out)
    return dict(out)


def generate(role: str, prompt: str, model: str | None = None) -> dict[str, Any]:
    """Local Ollama first, then OpenAI, then heuristic."""
    settings = get_settings()
    status = ollama_status(settings.ollama_url)
    pick = model or status.get("default") or "llama3.2"
    if status["up"] and status["models"]:
        try:
            chosen = pick if pick in status["models"] else status["models"][0]
            return _ollama(settings.ollama_url, chosen, prompt)
        except Exception as exc:
            fallback = _heuristic(role, prompt)
            return {"text": fallback, "model": "heuristic", "provider": "fallback", "error": str(exc)}
    if settings.openai_api_key:
        try:
            return _openai(prompt, model or settings.openai_model)
        except Exception as exc:
            return {"text": _heuristic(role, prompt), "model": "heuristic", "provider": "fallback", "error": str(exc)}
    note = ""
    if not status["up"]:
        note = f" Ollama is not reachable at {status['url']}. Start it with `ollama serve` and pull a model."
    elif not status["models"]:
        note = " Ollama is up but has no models. Run `ollama pull llama3.2`."
    return {"text": _heuristic(role, prompt) + note, "model": "heuristic", "provider": "heuristic", "ollama": status}


def _ollama(url: str, model: str, prompt: str) -> dict[str, Any]:
    r = httpx.post(
        f"{url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
        timeout=90.0,
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
    if role == "form_builder":
        return json.dumps({"ok": True, "note": "heuristic form builder"})
    if "invoice" in lowered:
        return "Invoice intake: extract vendor, amount, due date; route to AP if amount present."
    return json.dumps({"role": role, "decision": "continue", "note": "heuristic agent — bind Ollama for richer reasoning"})
