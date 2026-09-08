"""Map DocFlow executable workflows to n8n graphs (importable JSON)."""

from __future__ import annotations

N8N_TYPES = {
    "extract_text": ("n8n-nodes-base.httpRequest", "OCR"),
    "classify": ("n8n-nodes-base.switch", "Classify"),
    "extract_fields": ("n8n-nodes-base.set", "Extract fields"),
    "condition": ("n8n-nodes-base.if", "Condition"),
    "tag": ("n8n-nodes-base.set", "Tag"),
    "summarize": ("n8n-nodes-base.openAi", "Summarize"),
    "notify": ("n8n-nodes-base.emailSend", "Notify"),
    "agent": ("n8n-nodes-base.agent", "Agent"),
    "webhook": ("n8n-nodes-base.webhook", "Webhook"),
}


def canvas_nodes(steps: list[dict], trigger: str = "webhook") -> list[dict]:
    nodes = [{"key": "in", "type": "webhook", "label": "Webhook", "n8n": "n8n-nodes-base.webhook"}]
    for i, raw in enumerate(steps or []):
        t = raw.get("type") or "set"
        n8n, label = N8N_TYPES.get(t, ("n8n-nodes-base.set", t))
        nodes.append({"key": raw.get("key") or f"s{i}", "type": t, "label": label, "n8n": n8n})
    nodes.append({"key": "out", "type": "notify", "label": "Done", "n8n": "n8n-nodes-base.emailSend"})
    _ = trigger
    return nodes


def to_n8n(name: str, steps: list[dict], trigger: str = "webhook") -> dict:
    nodes = []
    connections: dict = {}
    chain = canvas_nodes(steps, trigger)
    prev = None
    for i, item in enumerate(chain):
        node_name = f"{item['label']} {i}" if i else item["label"]
        item["node_name"] = node_name
        nodes.append(
            {
                "parameters": {},
                "id": item["key"],
                "name": node_name,
                "type": item["n8n"],
                "typeVersion": 1,
                "position": [240 + i * 220, 300],
            }
        )
        if prev:
            connections.setdefault(prev, {"main": [[{"node": node_name, "type": "main", "index": 0}]]})
        prev = node_name
    return {
        "name": name,
        "active": True,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
        "meta": {"templateCredsSetupCompleted": True, "instanceId": "docflow"},
    }
