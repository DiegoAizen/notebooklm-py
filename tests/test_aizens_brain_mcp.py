"""Offline tests for private MCP transport, credentials and project isolation."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from aizens_brain_mcp import create_router


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_SERVER_TOKEN", "owner-key-123")
    monkeypatch.setenv("AIZENS_PROJECTS_JSON", json.dumps({
        "ruti": {"notebook_id": "nb-ruti", "repo": "owner/ruti", "branch": "develop"},
        "gym": {"notebook_id": "nb-gym", "repo": "owner/gym", "branch": "main"},
    }))
    monkeypatch.setenv("AIZENS_AGENT_TOKENS_JSON", json.dumps({
        "ruti-agent": {"token": "s" * 48, "projects": ["ruti"]}
    }))
    calls = []

    async def ask(notebook_id, question):
        calls.append((notebook_id, question))
        return {"answer": "fixture", "references": [{"source_id": "fake-ref"}]}

    app = FastAPI()
    app.include_router(create_router(ask), prefix="/mcp")
    return TestClient(app), calls


def rpc(method, *, params=None, ident=1):
    return {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}


def request(client, method, *, params=None, token="owner-key-123", headers=None):
    h = {"Authorization": "Bearer " + token}
    h.update(headers or {})
    return client.post("/mcp", json=rpc(method, params=params), headers=h)


def tool(client, name, args=None, token="owner-key-123"):
    response = request(client, "tools/call",
                       params={"name": name, "arguments": args or {}}, token=token)
    return response.status_code, response.json()["result"]


def data(result):
    return json.loads(result["content"][0]["text"])


def test_requires_auth(client):
    c, calls = client
    assert c.post("/mcp", json=rpc("tools/list")).status_code == 401
    assert request(c, "tools/list", token="invalid").status_code == 401
    assert calls == []


def test_initialize_and_list(client):
    c, _ = client
    response = request(c, "initialize", params={"protocolVersion": "2025-06-18"})
    assert response.json()["result"]["capabilities"]["tools"] == {"listChanged": False}
    names = [x["name"] for x in request(c, "tools/list").json()["result"]["tools"]]
    assert names == ["brain_list_notebooks", "brain_ask_notebook", "brain_list_projects", "brain_get_context", "brain_ask_project"]
    headers = {"Authorization": "Bearer owner-key-123"}
    assert c.post("/mcp",
                  json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                  headers=headers).status_code == 202


def test_scoped_listing(client):
    c, calls = client
    status, result = tool(c, "brain_list_projects", token="s" * 48)
    assert status == 200
    assert [p["project"] for p in data(result)["projects"]] == ["ruti"]
    assert calls == []


def test_scoped_cannot_read_another_project(client):
    c, calls = client
    _, result = tool(c, "brain_get_context", {"project": "gym"}, token="s" * 48)
    assert result["isError"] is True
    assert "Unknown or unauthorized" in data(result)["error"]
    assert calls == []


def test_get_context_uses_mapped_notebook_and_returns_citations(client):
    c, calls = client
    _, result = tool(c, "brain_get_context", {"project": "ruti"}, token="s" * 48)
    assert data(result)["answer"] == "fixture"
    assert len(data(result)["references"]) == 1
    assert calls and calls[0][0] == "nb-ruti"


def test_ask_project_and_reject_bad_input(client):
    c, calls = client
    _, result = tool(c, "brain_ask_project", {"project": "gym", "question": "¿Estado?"})
    assert data(result)["project"] == "gym"
    assert calls == [("nb-gym", "¿Estado?")]
    _, invalid = tool(c, "brain_ask_project", {"project": "gym", "question": ""})
    assert invalid["isError"] is True and len(calls) == 1


def test_invalid_registry_fails_closed(client, monkeypatch):
    c, calls = client
    monkeypatch.setenv("AIZENS_PROJECTS_JSON", "invalid-json")
    _, result = tool(c, "brain_list_projects")
    assert result["isError"] is True and calls == []


def test_bad_origin_and_content_type_rejected(client):
    c, _ = client
    assert request(c, "tools/list", headers={"Origin": "https://unknown.example"}).status_code == 403
    assert c.post("/mcp", content="x", headers={
        "Authorization": "Bearer owner-key-123", "Content-Type": "text/plain",
    }).status_code == 415


def test_upstream_error_is_sanitized(client):
    c, _ = client
    app = FastAPI()

    async def bad(_, __):
        raise RuntimeError("FICTIONAL-PRIVATE-CREDENTIAL")

    app.include_router(create_router(bad), prefix="/mcp")
    _, result = tool(TestClient(app), "brain_get_context", {"project": "ruti"})
    assert result["isError"] is True
    assert "FICTIONAL" not in json.dumps(data(result))


def test_unconfigured_registry_explains_next_step(client, monkeypatch):
    c, calls = client
    monkeypatch.delenv("AIZENS_PROJECTS_JSON")
    _, result = tool(c, "brain_list_projects")
    assert data(result)["needs_registry_configuration"] is True
    assert calls == []
