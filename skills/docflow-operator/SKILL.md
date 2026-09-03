---
name: docflow-operator
description: How to operate the DocFlow desk — health, pipeline, demo account, and MCP tools.
---

# DocFlow operator

## Demo
- UI: http://localhost:5173
- API: http://localhost:8000/docs
- User: `oren@gcs-tech.org` / `DocFlow!2026`

## Health
`curl http://localhost:8000/health`

## Pipeline
Upload a `.txt` or `.pdf`. The orchestrator runs extract → classify → matching automation → workflow steps → notify → analytics.

## MCP
Run `python apps/mcp/server.py` as a stdio MCP server. Tools: health, list_documents, process_text, list_workflows, list_skills.
