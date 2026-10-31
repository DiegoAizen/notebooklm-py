"""Offline end-to-end project lifecycle tests with a fake persistent NotebookLM account.

No Google account, Vercel secrets or live project notebooks are touched.
"""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from aizens_brain_projects import title_for_project, discover_projects, validate_project_tool
from aizens_brain_mcp import create_router


class FakeAccount:
    def __init__(self):
        self.notebooks = []
        self.sources = {}
        self.research = {}

    async def list(self):
        return list(self.notebooks)

    async def ask(self, notebook_id, question):
        return {"answer": f"About {notebook_id}", "references": [{"source_id": "fake"}]}

    async def create(self, title):
        nb = {"id": f"nb-{len(self.notebooks)+1}", "title": title, "sources_count": 0}
        self.notebooks.append(nb)
        self.sources[nb["id"]] = []
        return nb

    async def add_text(self, notebook_id, title, content):
        item = {"id": f"s-{len(self.sources[notebook_id])+1}", "title": title, "status_label": "ready"}
        self.sources[notebook_id].append(item)
        return item

    async def research_start(self, notebook_id, query, mode):
        return {"task_id": "task-1", "query": query, "mode": mode}

    async def research_poll(self, notebook_id, task_id):
        return {"task_id": task_id, "status": "completed", "sources": [
            {"url": "https://example.org/report", "title": "Example report"}
        ]}

    async def research_import(self, notebook_id, task_id, sources):
        return [{"id": "research-1", "title": sources[0]["title"]}]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_SERVER_TOKEN", "super-private-test-owner-token-abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("AIZENS_PROJECTS_JSON", "{}")
    account = FakeAccount()
    app = FastAPI()
    app.include_router(create_router(
        account.ask, account.list,
        create_notebook=account.create,
        add_text=account.add_text,
        research_start=account.research_start,
        research_poll=account.research_poll,
        research_import=account.research_import,
    ), prefix="/mcp")
    return TestClient(app), account


def call(client, name, **arguments):
    response = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }, headers={"Authorization": "Bearer super-private-test-owner-token-abcdefghijklmnopqrstuvwxyz"})
    assert response.status_code == 200
    result = response.json()["result"]
    parsed = json.loads(result["content"][0]["text"])
    return result["isError"], parsed


def test_create_project_persists_without_vercel_environment_updates(client):
    api, fake = client
    error, initial = call(api, "brain_create_project",
        project="ruti", title="Ruti Ecuador",
        initial_context="Proyecto de transporte compartido, apps de conductor y pasajero, sin datos sensibles.",
        confirmed=True)
    assert not error
    assert initial["created"] is True
    assert initial["memory_saved"] is True
    assert fake.notebooks[0]["title"] == "Aizens · ruti · Ruti Ecuador"
    assert len(fake.sources["nb-1"]) == 1
    error, status = call(api, "brain_list_projects")
    assert not error
    assert status["needs_registry_configuration"] is False
    assert status["projects"][0]["project"] == "ruti"
    error, context = call(api, "brain_get_context", project="ruti")
    assert not error
    assert context["references"]


def test_duplicate_and_unconfirmed_creation_do_not_mutate(client):
    api, fake = client
    error, result = call(api, "brain_create_project", project="gym", title="Gym",
        initial_context="Preparando un proyecto de gimnasio con arquitectura documentada.",
        confirmed=False)
    assert error
    assert fake.notebooks == []
    call(api, "brain_create_project", project="gym", title="Gym",
         initial_context="Preparando un proyecto de gimnasio con arquitectura documentada.",
         confirmed=True)
    error, repeat = call(api, "brain_create_project", project="gym", title="Gym",
         initial_context="Una repetición no debe crear el mismo cuaderno por error.",
         confirmed=True)
    assert error
    assert len(fake.notebooks) == 1


def test_write_memory_then_research_and_import(client):
    api, fake = client
    call(api, "brain_create_project", project="postal", title="Postal",
        initial_context="Proyecto postal: clasificar cartas por calles, portales y código postal.",
        confirmed=True)
    err, saved = call(api, "brain_add_memory", project="postal",
        title="Estado GitHub 2026-10-31", content="Prueba de relevo con contrato de rama y tareas pendientes, confirmado en GitHub.",
        confirmed=True)
    assert not err and saved["source_id"] == "s-2"
    err, started = call(api, "brain_start_research", project="postal",
        query="Métodos de verificación de direcciones postales en España",
        mode="fast", confirmed=True)
    assert not err and started["research"]["task_id"] == "task-1"
    err, status = call(api, "brain_research_status", project="postal", task_id="task-1")
    assert not err and status["research"]["status"] == "completed"
    err, imported = call(api, "brain_import_research", project="postal",
        task_id="task-1", sources=[{"url": "https://example.org/report", "title": "Example report"}],
        confirmed=True)
    assert not err and imported["imported"][0]["id"] == "research-1"


def test_reject_private_or_insecure_research_sources(client):
    api, _ = client
    call(api, "brain_create_project", project="test", title="Testing",
         initial_context="Un proyecto aislado usado solo para pruebas de seguridad.",
         confirmed=True)
    for url in ("http://example.com/report", "https://127.0.0.1/private",
                "https://metadata.google.internal/token"):
        error, _ = call(api, "brain_import_research", project="test",
            task_id="task-1", sources=[{"url": url, "title": "Bad source"}],
            confirmed=True)
        assert error


def test_name_parsing_does_not_register_unrelated_notebooks():
    assert title_for_project("gym", "Mi Gimnasio") == "Aizens · gym · Mi Gimnasio"
    projects = discover_projects([
        {"id": "x", "title": "Manual de notyPost"},
        {"id": "y", "title": "Aizens · gym · Mi Gimnasio"},
    ])
    assert list(projects) == ["gym"]
    assert projects["gym"]["notebook_id"] == "y"
    assert validate_project_tool("brain_create_project", {
        "project": "gym", "title": "x", "initial_context": "a" * 20, "confirmed": False
    }) is None
