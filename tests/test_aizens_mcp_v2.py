"""Contract test: brand-new ChatGPT MCP identity with OAuth write scope.

Uses a fake NotebookLM account; no real Google notebooks are modified.
"""
import base64
import hashlib
import html
import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aizens_brain_mcp import create_router
from aizens_brain_oauth import create_oauth_router


BASE = "https://aizens-notebooklm.vercel.app"
CLIENT = "https://chatgpt.com/oauth/client.json"
CALLBACK = "https://chatgpt.com/connector_platform_oauth_redirect"
VERIFIER = "v" * 64


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_SERVER_TOKEN", "s" * 48)
    monkeypatch.setenv("AIZENS_PROJECTS_JSON", "{}")
    created = []

    async def notebooks():
        return list(created)

    async def make_notebook(title):
        item = {"id": "test-notebook-123", "title": title, "sources_count": 0}
        created.append(item)
        return item

    async def add_text(notebook_id, title, content):
        return {"id": "source-1", "status_label": "ready"}

    async def ask(notebook_id, question):
        return {"answer": "Fake NotebookLM reply", "references": [{"source_id": "source-1"}]}

    app = FastAPI()
    app.include_router(create_oauth_router())
    app.include_router(
        create_router(ask, notebooks, create_notebook=make_notebook, add_text=add_text,
                      resource_path="/mcp-v2"),
        prefix="/mcp-v2",
    )
    return TestClient(app, base_url=BASE), created


def _authorization(api, resource, scope):
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(VERIFIER.encode()).digest()
    ).decode().rstrip("=")
    fields = {
        "client_id": CLIENT, "redirect_uri": CALLBACK, "response_type": "code",
        "code_challenge": challenge, "code_challenge_method": "S256",
        "resource": resource, "scope": scope, "state": "test-state-123",
    }
    page = api.get("/oauth/authorize", params=fields)
    assert page.status_code == 200, page.text[:300]
    ticket = re.search(r'name="form_ticket" value="([^"]+)"', page.text)
    assert ticket, "Signed consent form missing"
    response = api.post(
        "/oauth/authorize",
        data={**fields, "form_ticket": ticket.group(1), "password": "s" * 48},
        follow_redirects=False,
    )
    assert response.status_code == 200
    redirect = re.search(r"href='([^']+)'", response.text)
    assert redirect
    code = parse_qs(urlsplit(html.unescape(redirect.group(1))).query)["code"][0]
    exchanged = api.post("/oauth/token", data={
        "grant_type": "authorization_code",
        "code": code, "code_verifier": VERIFIER,
        "client_id": CLIENT, "redirect_uri": CALLBACK, "resource": resource,
    })
    assert exchanged.status_code == 200, exchanged.text
    return exchanged.json()["access_token"]


def _rpc(api, token, method, params=None):
    response = api.post(
        "/mcp-v2",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["result"]


def _tool(api, token, name, args):
    r = _rpc(api, token, "tools/call", {"name": name, "arguments": args})
    return r["isError"], json.loads(r["content"][0]["text"])


def test_new_mcp_identity_oauth_tools_and_persistent_creation(api):
    client, created = api
    resource = BASE + "/mcp-v2"
    meta = client.get("/.well-known/oauth-protected-resource/mcp-v2")
    assert meta.status_code == 200
    assert meta.json()["resource"] == resource

    forbidden = client.post("/mcp-v2", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/list"
    })
    assert forbidden.status_code == 401
    assert "mcp-v2" in forbidden.headers["www-authenticate"]

    token = _authorization(client, resource, "brain:write brain:read")
    available = _rpc(client, token, "tools/list")["tools"]
    names = {t["name"] for t in available}
    assert len(available) == 10
    assert {"brain_create_project", "brain_add_memory", "brain_start_research"} <= names

    is_error, result = _tool(client, token, "brain_create_project", {
        "project": "ruti", "title": "Ruti Ecuador",
        "initial_context": "Información de pruebas, no es un proyecto real ni datos privados.",
        "confirmed": True,
    })
    assert not is_error, result
    assert result["created"] is True and result["memory_saved"] is True
    assert len(created) == 1
    assert created[0]["title"] == "Aizens · ruti · Ruti Ecuador"

    is_error, projects = _tool(client, token, "brain_list_projects", {})
    assert not is_error
    assert projects["projects"][0]["project"] == "ruti"
    assert projects["project_creation_available"] is True


def test_read_only_cannot_create_even_on_mcp_v2(api):
    client, created = api
    token = _authorization(client, BASE + "/mcp-v2", "brain:read")
    is_error, response = _tool(client, token, "brain_create_project", {
        "project": "ruti", "title": "Ruti",
        "initial_context": "This text has enough characters for a test.",
        "confirmed": True,
    })
    assert is_error and "Write permission required" in response["error"]
    assert created == []


def test_old_mcp_resource_token_cannot_access_v2(api):
    client, created = api
    token = _authorization(client, BASE + "/mcp", "brain:read brain:write")
    response = client.post("/mcp-v2", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/list"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert created == []
