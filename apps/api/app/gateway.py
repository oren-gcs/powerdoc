from __future__ import annotations

import os
from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.service_catalog import SERVICES, UPSTREAM_ENV

router = APIRouter(tags=["gateway"])

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _upstream_base(path: str) -> str | None:
    matches = [prefix for prefix in UPSTREAM_ENV if path == prefix or path.startswith(prefix + "/")]
    if not matches:
        return None
    prefix = max(matches, key=len)
    return os.environ.get(UPSTREAM_ENV[prefix], "").rstrip("/") or None


def _filter_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    return {k: v for k, v in headers if k.lower() not in HOP_BY_HOP}


@router.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_api(full_path: str, request: Request) -> Response:
    path = f"/api/{full_path}"
    base = _upstream_base(path)
    if not base:
        return JSONResponse({"detail": f"No upstream for {path}"}, status_code=404)

    url = f"{base}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    body = await request.body()
    async with httpx.AsyncClient(timeout=60.0) as client:
        upstream = await client.request(
            request.method,
            url,
            content=body,
            headers=_filter_headers(request.headers.items()),
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_filter_headers(upstream.headers.items()),
        media_type=upstream.headers.get("content-type"),
    )


@router.get("/gateway/services")
def list_services():
    return {
        "mode": "gateway",
        "services": [
            {
                "name": s.name,
                "title": s.title,
                "prefixes": list(s.path_prefixes),
                "url_env": UPSTREAM_ENV.get(s.path_prefixes[0]),
            }
            for s in SERVICES.values()
        ],
    }
