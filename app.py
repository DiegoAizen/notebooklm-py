"""Aizens NotebookLM: minimal, request-driven and read-only Vercel API.

All data endpoints require a bearer token. The Google master token is supplied
only through Vercel environment variables and materialized in /tmp at runtime.
No background tasks, cron jobs, or publicly writable NotebookLM operations.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
from pathlib import Path
from typing import Annotated
import sys

# The Vercel runtime does not preserve uv's editable-install .pth files.
# Include this fork's src-layout package on the function import path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from notebooklm import NotebookLMClient
from notebooklm._auth.master_token import bootstrap_missing_storage_from_master_token
from notebooklm._app.views import ask_result_view, notebook_view

_LOG = logging.getLogger("aizens.vercel")
_HOME = Path("/tmp/aizens-notebooklm")
_PROFILE = "vercel"
# Vercel's deploy filesystem is read-only; auth state/refresh must use /tmp.
os.environ["NOTEBOOKLM_HOME"] = str(_HOME)

app = FastAPI(title="Aizens NotebookLM", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


def require_bearer(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = os.environ.get("NOTEBOOKLM_SERVER_TOKEN", "").strip()
    prefix = "Bearer "
    if (
        not expected
        or not authorization
        or not authorization.startswith(prefix)
        or not hmac.compare_digest(authorization[len(prefix):], expected)
    ):
        raise HTTPException(401, "Invalid or missing bearer token")


def _prepare_auth() -> None:
    """Materialize a dedicated Google account token, never into source control."""
    raw = os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON")
    if not raw:
        raise HTTPException(503, "Google authentication not configured")
    try:
        payload = json.loads(raw)
        if (
            not isinstance(payload, dict)
            or payload.get("version") != 1
            or not all(
                isinstance(payload.get(key), str) and payload[key]
                for key in ("email", "android_id", "master_token")
            )
        ):
            raise ValueError("Invalid credential shape")
        profile_dir = _HOME / "profiles" / _PROFILE
        profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        profile_dir.chmod(0o700)
        destination = profile_dir / "master_token.json"
        # Immutable within a deployment; don't overwrite a live auth file.
        # Using an exclusive creation avoids readers seeing truncated JSON.
        if not destination.exists():
            try:
                fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, "w", encoding="utf-8") as out:
                    out.write(raw)
                destination.chmod(0o600)
    except (ValueError, OSError, TypeError):
        raise HTTPException(503, "Google authentication configuration invalid") from None


async def _ensure_session() -> None:
    """Mint Web cookies on a cold Vercel start from the stored master token.

    The master token alone is not a Playwright storage_state.json. The
    from_storage() loader still needs the cookie file before it can refresh
    and query Google. The upstream bootstrap handles cross-request locking.
    """
    storage_path = _HOME / "profiles" / _PROFILE / "storage_state.json"
    await bootstrap_missing_storage_from_master_token(storage_path)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = Field(default=None, max_length=256)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    # Liveness only. Does not claim that an account has been authenticated.
    return {"ok": True}


@app.get("/v1/notebooks", dependencies=[Depends(require_bearer)])
async def list_notebooks():
    _prepare_auth()
    try:
        await _ensure_session()
        async with NotebookLMClient.from_storage(profile=_PROFILE) as client:
            return {"notebooks": [notebook_view(nb) for nb in await client.notebooks.list()]}
    except Exception as exc:
        _LOG.warning("NotebookLM list failed: %s", type(exc).__name__)
        raise HTTPException(502, "NotebookLM query failed; inspect server logs") from None


@app.post("/v1/notebooks/{notebook_id}/chat", dependencies=[Depends(require_bearer)])
async def ask_notebook(notebook_id: str, body: AskRequest):
    if not notebook_id or len(notebook_id) > 256:
        raise HTTPException(422, "Invalid notebook ID")
    _prepare_auth()
    try:
        await _ensure_session()
        async with NotebookLMClient.from_storage(profile=_PROFILE) as client:
            result = await client.chat.ask(
                notebook_id, body.question, conversation_id=body.conversation_id
            )
            return ask_result_view(result)
    except Exception as exc:
        _LOG.warning("NotebookLM chat failed: %s", type(exc).__name__)
        raise HTTPException(502, "NotebookLM query failed; inspect server logs") from None


# Aizens Brain: private read-only MCP endpoint for scoped agent connections.
# Reuse the proven NotebookLM auth/session lifecycle, never a second master token.
from aizens_brain_mcp import create_router
from aizens_brain_oauth import create_oauth_router


async def _brain_ask_notebook(notebook_id: str, question: str) -> dict:
    _prepare_auth()
    await _ensure_session()
    async with NotebookLMClient.from_storage(profile=_PROFILE) as client:
        result = await client.chat.ask(notebook_id, question)
        return ask_result_view(result)


async def _brain_list_notebooks() -> list[dict]:
    _prepare_auth()
    await _ensure_session()
    async with NotebookLMClient.from_storage(profile=_PROFILE) as client:
        return [notebook_view(nb) for nb in await client.notebooks.list()]


app.include_router(create_oauth_router())
app.include_router(create_router(_brain_ask_notebook, _brain_list_notebooks), prefix="/mcp")
