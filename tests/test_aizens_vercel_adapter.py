"""Pruebas del adaptador FastAPI de Vercel con cuentas y cuadernos falsos.

Ejecución en el fork: uv run pytest tests/test_aizens_vercel_adapter.py -q
No accede a Google ni necesita credenciales; NO sustituye al smoke test remoto.
"""
import asyncio
import json
import stat
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import app as target


@pytest.fixture()
def api(monkeypatch, tmp_path):
    monkeypatch.setattr(target, "_HOME", tmp_path)
    monkeypatch.setattr(target, "_PROFILE", "test")
    monkeypatch.setenv("NOTEBOOKLM_SERVER_TOKEN", "test-server-token-only")
    monkeypatch.delenv("NOTEBOOKLM_MASTER_TOKEN_JSON", raising=False)
    return TestClient(target.app)


def _master():
    return json.dumps({
        "version": 1,
        "email": "example@invalid.test",
        "android_id": "example-device",
        "master_token": "fictional-not-a-token",
    })


def _headers():
    return {"Authorization": "Bearer test-server-token-only"}


def test_health_does_not_require_credentials(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response.headers["cache-control"] == "no-store"


def test_api_rejects_missing_and_wrong_tokens(api):
    assert api.get("/v1/notebooks").status_code == 401
    assert api.get("/v1/notebooks", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert api.post("/v1/notebooks/notebook-1/chat", json={"question": "hola"}).status_code == 401


def test_missing_master_returns_503(api):
    response = api.get("/v1/notebooks", headers=_headers())
    assert response.status_code == 503
    assert "Google authentication not configured" in response.text


@pytest.mark.parametrize("raw", ["{broken-json", "{}", '{"version":2}'])
def test_invalid_master_returns_503(api, monkeypatch, raw):
    monkeypatch.setenv("NOTEBOOKLM_MASTER_TOKEN_JSON", raw)
    response = api.get("/v1/notebooks", headers=_headers())
    assert response.status_code == 503
    assert "master_token" not in response.text


def test_valid_master_is_materialized_privately(api, monkeypatch, tmp_path):
    monkeypatch.setenv("NOTEBOOKLM_MASTER_TOKEN_JSON", _master())
    target._prepare_auth()
    path = tmp_path / "profiles" / "test" / "master_token.json"
    assert json.loads(path.read_text())["email"] == "example@invalid.test"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


class MockBackend:
    def __init__(self, *, failing=False):
        self.failing = failing
        self.notebooks = SimpleNamespace(list=self.list_notebooks)
        self.chat = SimpleNamespace(ask=self.ask)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def list_notebooks(self):
        if self.failing:
            raise RuntimeError("FICTIONAL-SECRET-MUST-NOT-LEAK")
        return [{"id": "notebook-1", "title": "Fixture"}]

    async def ask(self, notebook_id, question, conversation_id=None):
        if self.failing:
            raise RuntimeError("FICTIONAL-SECRET-MUST-NOT-LEAK")
        return {"answer": "Respuesta simulada", "references": [{"source_id": "test-source"}]}


@pytest.fixture()
def fake_google(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_MASTER_TOKEN_JSON", _master())
    monkeypatch.setattr(target, "notebook_view", lambda item: item)
    monkeypatch.setattr(target, "ask_result_view", lambda result: result)
    async def fake_session():
        return None
    monkeypatch.setattr(target, "_ensure_session", fake_session)
    factory = lambda **kwargs: MockBackend()
    monkeypatch.setattr(target.NotebookLMClient, "from_storage", staticmethod(factory))


def test_authenticated_list_and_chat_with_fake_google(api, fake_google):
    response = api.get("/v1/notebooks", headers=_headers())
    assert response.status_code == 200
    assert response.json()["notebooks"][0]["id"] == "notebook-1"

    response = api.post(
        "/v1/notebooks/notebook-1/chat",
        headers=_headers(),
        json={"question": "¿Qué se está construyendo?"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Respuesta simulada"
    assert len(response.json()["references"]) == 1


def test_upstream_errors_do_not_leak_details(api, monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_MASTER_TOKEN_JSON", _master())
    async def fake_session():
        return None
    monkeypatch.setattr(target, "_ensure_session", fake_session)
    monkeypatch.setattr(target.NotebookLMClient, "from_storage", staticmethod(
        lambda **kwargs: MockBackend(failing=True)
    ))
    response = api.get("/v1/notebooks", headers=_headers())
    assert response.status_code == 502
    assert "FICTIONAL-SECRET" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_question_validation_and_id_length(api, fake_google):
    assert api.post(
        "/v1/notebooks/notebook-1/chat", headers=_headers(), json={"question": ""}
    ).status_code == 422
    assert api.post(
        "/v1/notebooks/" + "a" * 257 + "/chat",
        headers=_headers(),
        json={"question": "hola"},
    ).status_code == 422


def test_cold_start_bootstraps_cookie_storage_from_master(api, monkeypatch, tmp_path):
    calls = []

    async def bootstrap(path):
        calls.append(path)
        return True

    monkeypatch.setattr(target, "bootstrap_missing_storage_from_master_token", bootstrap)
    asyncio.run(target._ensure_session())
    assert calls == [tmp_path / "profiles" / "test" / "storage_state.json"]


def test_cold_start_bootstrap_failure_is_sanitized(api, monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_MASTER_TOKEN_JSON", _master())

    async def failing_session():
        raise RuntimeError("FICTIONAL-SECRET-MUST-NOT-LEAK")

    monkeypatch.setattr(target, "_ensure_session", failing_session)
    response = api.get("/v1/notebooks", headers=_headers())
    assert response.status_code == 502
    assert "FICTIONAL-SECRET-MUST-NOT-LEAK" not in response.text
