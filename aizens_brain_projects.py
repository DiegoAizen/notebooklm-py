"""Persistent Aizens project identity using NotebookLM notebook titles.

Each project owns one Google-hosted notebook, so Vercel needs no writable
filesystem, env-var registry edits, or external DB to discover new projects.
The conventional title is: "Aizens · {slug} · {human title}".
"""
from __future__ import annotations

import re
from typing import Any

PREFIX = "Aizens · "
SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,47}$")
MAX_TITLE = 100


def title_for_project(slug: str, title: str) -> str:
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("Project slug must be 2-48 lowercase characters, digits, dashes or underscores.")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE:
        raise ValueError("Project title must be 1-100 characters.")
    if any(ord(c) < 32 for c in title):
        raise ValueError("Project title cannot contain control characters.")
    return f"{PREFIX}{slug} · {title.strip()}"


def discover_projects(notebooks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Recognize only notebooks explicitly created using Aizens naming."""
    results: dict[str, dict[str, Any]] = {}
    for nb in notebooks:
        if not isinstance(nb, dict):
            continue
        identifier, name = nb.get("id"), nb.get("title")
        if not isinstance(identifier, str) or not identifier or not isinstance(name, str):
            continue
        if not name.startswith(PREFIX):
            continue
        parts = name[len(PREFIX):].split(" · ", 1)
        if len(parts) != 2 or not SLUG.fullmatch(parts[0]) or not parts[1].strip():
            continue
        slug = parts[0]
        # Duplicate names are not accepted as unambiguous project IDs.
        if slug in results:
            results[slug] = {"error": "duplicate_project_title"}
        else:
            results[slug] = {
                "project": slug,
                "notebook_id": identifier,
                "title": parts[1].strip(),
                "sources_count": nb.get("sources_count"),
                "repo": None,
                "verification": "documentary_only_not_live_git",
            }
    return results


PROJECT_WRITE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "brain_create_project",
        "description": (
            "CREATE a new persistent Aizens NotebookLM project from this chat. "
            "Requires explicit user confirmation. Creates a notebook and saves "
            "the provided initial context as its first text source. Never invent context."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "minLength": 2, "maxLength": 48},
                "title": {"type": "string", "minLength": 1, "maxLength": 100},
                "initial_context": {"type": "string", "minLength": 20, "maxLength": 30000},
                "confirmed": {"type": "boolean", "const": True},
            },
            "required": ["project", "title", "initial_context", "confirmed"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "brain_add_memory",
        "description": (
            "ADD a factual source/handoff to an existing Aizens project notebook. "
            "Must provide actual content, provenance and user confirmation; this "
            "does not update GitHub. Use versioned headings, SHAs, timestamps."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "minLength": 2, "maxLength": 48},
                "title": {"type": "string", "minLength": 1, "maxLength": 120},
                "content": {"type": "string", "minLength": 20, "maxLength": 30000},
                "confirmed": {"type": "boolean", "const": True},
            },
            "required": ["project", "title", "content", "confirmed"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "brain_start_research",
        "description": (
            "START a NotebookLM WEB research run for an Aizens project. "
            "Use brain_research_status later to review results, and "
            "brain_import_research to add specifically selected sources. "
            "Does not automatically schedule recurring investigations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "minLength": 2, "maxLength": 48},
                "query": {"type": "string", "minLength": 6, "maxLength": 1500},
                "mode": {"type": "string", "enum": ["fast", "deep"]},
                "confirmed": {"type": "boolean", "const": True},
            },
            "required": ["project", "query", "confirmed"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "brain_research_status",
        "description": (
            "READ current result candidates of a previously started NotebookLM "
            "research task, without importing any source. Include task_id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "minLength": 2, "maxLength": 48},
                "task_id": {"type": "string", "minLength": 1, "maxLength": 256},
            },
            "required": ["project", "task_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "brain_import_research",
        "description": (
            "IMPORT up to 8 selected URL sources returned by a NotebookLM "
            "research task into its project. Explicit confirmation required; "
            "check source reliability before importing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "minLength": 2, "maxLength": 48},
                "task_id": {"type": "string", "minLength": 1, "maxLength": 256},
                "sources": {"type": "array", "minItems": 1, "maxItems": 8, "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "minLength": 10, "maxLength": 2000},
                        "title": {"type": "string", "minLength": 1, "maxLength": 200},
                    },
                    "required": ["url", "title"],
                    "additionalProperties": False,
                }},
                "confirmed": {"type": "boolean", "const": True},
            },
            "required": ["project", "task_id", "sources", "confirmed"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
]

WRITE_NAMES = frozenset({
    "brain_create_project", "brain_add_memory", "brain_start_research", "brain_import_research"
})
PROJECT_NAMES = frozenset(t["name"] for t in PROJECT_WRITE_TOOLS)


def validate_project_tool(name: str, arguments: object) -> dict | None:
    if name not in PROJECT_NAMES or not isinstance(arguments, dict):
        return None
    tool = next(t for t in PROJECT_WRITE_TOOLS if t["name"] == name)
    schema = tool["inputSchema"]
    if set(arguments) != set(schema["required"]) and (
        set(arguments) - set(schema["properties"])
        or not set(schema["required"]).issubset(arguments)
    ):
        return None
    for key, rule in schema["properties"].items():
        if key not in arguments:
            continue
        value = arguments[key]
        if rule.get("const") is True and value is not True:
            return None
        if rule["type"] == "string" and (
            not isinstance(value, str) or not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", 99999)
        ):
            return None
        if rule["type"] == "string" and "enum" in rule and value not in rule["enum"]:
            return None
        if rule["type"] == "array" and (
            not isinstance(value, list) or not rule["minItems"] <= len(value) <= rule["maxItems"]
        ):
            return None
    if "project" in arguments and not SLUG.fullmatch(arguments["project"]):
        return None
    if name == "brain_import_research":
        from urllib.parse import urlsplit
        import ipaddress
        for item in arguments["sources"]:
            if not isinstance(item, dict) or set(item) != {"url", "title"}:
                return None
            title, url = item["title"], item["url"]
            if not isinstance(title, str) or not title.strip() or len(title) > 200:
                return None
            if not isinstance(url, str) or not 10 <= len(url) <= 2000:
                return None
            try:
                p = urlsplit(url)
                host = p.hostname or ""
                if p.scheme != "https" or not host or p.username or p.password or p.port not in (None, 443):
                    return None
                if host.lower() in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
                    return None
                try:
                    address = ipaddress.ip_address(host)
                except ValueError:
                    pass
                else:
                    if not address.is_global:
                        return None
            except ValueError:
                return None
    return arguments
