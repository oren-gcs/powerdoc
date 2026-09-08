#!/usr/bin/env python3
"""DocFlow MCP server — stdlib only, stdio JSON-RPC 2.0."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.getenv("DOCFLOW_API", "http://127.0.0.1:8000")
EMAIL = os.getenv("DOCFLOW_EMAIL", "oren@gcs-tech.org")
PASSWORD = os.getenv("DOCFLOW_PASSWORD", "DocFlow!2026")


def log(msg: str) -> None:
    print(f"[docflow-mcp] {msg}", file=sys.stderr, flush=True)


def http(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def token() -> str:
    r = http("POST", "/api/v1/auth/login", {"email": EMAIL, "password": PASSWORD})
    return r.get("access_token", "")


TOOLS = [
    {"name": "health", "description": "DocFlow API health", "inputSchema": {"type": "object", "properties": {}}},
    {
        "name": "list_documents",
        "description": "List tenant documents",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_workflows",
        "description": "List executable workflows",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_skills",
        "description": "List agent skills",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "analytics_summary",
        "description": "Platform analytics summary",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_skill",
        "description": "Run a named skill with a prompt",
        "inputSchema": {
            "type": "object",
            "properties": {"skill_id": {"type": "string"}, "prompt": {"type": "string"}},
            "required": ["skill_id", "prompt"],
        },
    },
]


def call_tool(name: str, args: dict) -> str:
    if name == "health":
        return json.dumps(http("GET", "/health"))
    t = token()
    if name == "list_documents":
        return json.dumps(http("GET", "/api/v1/documents", token=t))
    if name == "list_workflows":
        return json.dumps(http("GET", "/api/v1/workflows", token=t))
    if name == "list_skills":
        return json.dumps(http("GET", "/api/v1/agent/skills", token=t))
    if name == "analytics_summary":
        return json.dumps(http("GET", "/api/v1/analytics/summary", token=t))
    if name == "run_skill":
        sid = args.get("skill_id", "summarize")
        prompt = args.get("prompt", "")
        return json.dumps(http("POST", f"/api/v1/agent/skills/{sid}/run?prompt={urllib.request.quote(prompt)}", token=t))
    return json.dumps({"error": f"unknown tool {name}"})


def reply(msg_id, result=None, error=None):
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error:
        payload["error"] = error
    else:
        payload["result"] = result
    print(json.dumps(payload), flush=True)


def main():
    log(f"listening, API={API}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            reply(
                msg_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "docflow", "version": "2.0.0"},
                },
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params") or {}
            text = call_tool(params.get("name"), params.get("arguments") or {})
            reply(msg_id, {"content": [{"type": "text", "text": text}]})
        elif method == "ping":
            reply(msg_id, {})
        elif msg_id is not None:
            reply(msg_id, error={"code": -32601, "message": f"Unknown method {method}"})


if __name__ == "__main__":
    main()
