"""OAuth 2.1 PKCE integration checks with no real Google account or tokens.

Use: pytest -q tests/test_aizens_brain_oauth.py
"""
import base64
import hashlib
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from aizens_brain_oauth import create_oauth_router, validate_oauth_access


def _challenge(value):
    return base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()).decode().rstrip("=")


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_SERVER_TOKEN", "a" * 48)
    monkeypatch.delenv("AIZENS_BRAIN_LOGIN_SECRET", raising=False)
    api = FastAPI()
    api.include_router(create_oauth_router())
    return TestClient(api, base_url="https://aizens-notebooklm.vercel.app")


def _fields():
    return {
        "response_type": "code", "code_challenge_method": "S256",
        "code_challenge": _challenge("x" * 64),
        "client_id": "https://chatgpt.com/oauth/client.json",
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "scope": "brain:read", "state": "test-request",
        "resource": "https://aizens-notebooklm.vercel.app/mcp",
    }


def test_metadata_and_discovery(app):
    auth = app.get("/.well-known/oauth-authorization-server").json()
    resource = app.get("/.well-known/oauth-protected-resource").json()
    assert "S256" in auth["code_challenge_methods_supported"]
    assert auth["authorization_response_iss_parameter_supported"] is True
    assert resource["resource"] == "https://aizens-notebooklm.vercel.app/mcp"


def test_auth_code_pkce_access_and_refresh(app):
    fields = _fields()
    page = app.get("/oauth/authorize", params=fields)
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    assert "aizens_oauth_csrf" in app.cookies
    res = app.post("/oauth/authorize", data={**fields, "password": "a" * 48},
                   follow_redirects=False)
    assert res.status_code == 302
    code = parse_qs(urlparse(res.headers["location"]).query)["code"][0]
    assert parse_qs(urlparse(res.headers["location"]).query)["state"] == ["test-request"]
    exchanged = app.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code,
        "code_verifier": "x" * 64, "client_id": fields["client_id"],
        "redirect_uri": fields["redirect_uri"], "resource": fields["resource"],
    })
    assert exchanged.status_code == 200
    assert validate_oauth_access(exchanged.json()["access_token"])
    renewed = app.post("/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": exchanged.json()["refresh_token"],
        "client_id": fields["client_id"],
    })
    assert renewed.status_code == 200
    assert validate_oauth_access(renewed.json()["access_token"])


def test_wrong_password_no_redirect(app):
    fields = _fields()
    assert app.get("/oauth/authorize", params=fields).status_code == 200
    assert app.post("/oauth/authorize", data={**fields, "password": "wrong"},
                    follow_redirects=False).status_code == 401


def test_wrong_pkce_verifier_rejected(app):
    fields = _fields()
    app.get("/oauth/authorize", params=fields)
    res = app.post("/oauth/authorize", data={**fields, "password": "a" * 48},
                   follow_redirects=False)
    code = parse_qs(urlparse(res.headers["location"]).query)["code"][0]
    bad = app.post("/oauth/token", data={
        "grant_type": "authorization_code", "code": code,
        "code_verifier": "z" * 64, "client_id": fields["client_id"],
        "redirect_uri": fields["redirect_uri"],
    })
    assert bad.status_code == 400


def test_untrusted_redirect_and_client_rejected(app):
    fields = _fields()
    fields["redirect_uri"] = "https://evil.example.com/steal"
    assert app.get("/oauth/authorize", params=fields).status_code == 400
    fields["client_id"] = "https://evil.example.com/oauth/client.json"
    assert app.get("/oauth/authorize", params=fields).status_code == 400


def test_csrf_prevents_direct_post(app):
    fields = _fields()
    res = app.post("/oauth/authorize", data={**fields, "password": "a" * 48},
                   follow_redirects=False)
    assert res.status_code == 403
