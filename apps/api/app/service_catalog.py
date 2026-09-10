from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    title: str
    path_prefixes: tuple[str, ...]
    routers: tuple[str, ...]
    runs_seed: bool = False


SERVICES: dict[str, ServiceSpec] = {
    "identity": ServiceSpec(
        name="identity",
        title="DocFlow Identity",
        path_prefixes=("/api/v1/auth", "/api/v1/org", "/api/v1/admin"),
        routers=("auth", "org", "admin"),
        runs_seed=True,
    ),
    "documents": ServiceSpec(
        name="documents",
        title="DocFlow Documents",
        path_prefixes=(
            "/api/v1/documents",
            "/api/v1/search",
            "/api/v1/connectors",
            "/api/v1/agent",
            "/api/v1/mcp",
        ),
        routers=("documents", "search", "connectors", "agents", "mcp_http"),
    ),
    "forms": ServiceSpec(
        name="forms",
        title="DocFlow Forms",
        path_prefixes=("/api/v1/forms", "/api/v1/public/forms"),
        routers=("forms", "forms_public"),
    ),
    "workflow": ServiceSpec(
        name="workflow",
        title="DocFlow Workflow",
        path_prefixes=("/api/v1/workflows", "/api/v1/automations"),
        routers=("workflows", "automations"),
    ),
    "notify": ServiceSpec(
        name="notify",
        title="DocFlow Notify",
        path_prefixes=("/api/v1/notify",),
        routers=("notify",),
    ),
    "analytics": ServiceSpec(
        name="analytics",
        title="DocFlow Analytics",
        path_prefixes=("/api/v1/analytics",),
        routers=("analytics",),
    ),
}

SPECIAL = frozenset({"monolith", "gateway", "all"})

UPSTREAM_ENV: dict[str, str] = {
    "/api/v1/auth": "IDENTITY_URL",
    "/api/v1/org": "IDENTITY_URL",
    "/api/v1/admin": "IDENTITY_URL",
    "/api/v1/documents": "DOCUMENTS_URL",
    "/api/v1/search": "DOCUMENTS_URL",
    "/api/v1/connectors": "DOCUMENTS_URL",
    "/api/v1/agent": "DOCUMENTS_URL",
    "/api/v1/mcp": "DOCUMENTS_URL",
    "/api/v1/forms": "FORMS_URL",
    "/api/v1/public/forms": "FORMS_URL",
    "/api/v1/workflows": "WORKFLOW_URL",
    "/api/v1/automations": "WORKFLOW_URL",
    "/api/v1/notify": "NOTIFY_URL",
    "/api/v1/analytics": "ANALYTICS_URL",
}


def resolve_service_name(raw: str | None) -> str:
    name = (raw or "monolith").strip().lower()
    if name in ("all", ""):
        return "monolith"
    if name in SERVICES or name in SPECIAL:
        return name
    known = sorted(SERVICES) + ["monolith", "gateway"]
    raise ValueError(f"Unknown DOCFLOW_SERVICE={raw!r}; expected one of {known}")
