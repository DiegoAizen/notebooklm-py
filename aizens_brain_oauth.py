"""Private single-owner OAuth 2.1/PKCE bridge for Aizens Brain on Vercel.

Tokens and codes are signed with a derivative of NOTEBOOKLM_SERVER_TOKEN.
A database-backed one-time code store is recommended before multi-user use.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import time
from urllib.parse import parse_qs, urlencode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

SCOPE = "brain:read"
BASE_DEFAULT = "https://aizens-notebooklm.vercel.app"
PKCE_RE = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
CLIENT_RE = re.compile(r"^https://chatgpt\.com/oauth/([A-Za-z0-9_-]{6,160})/client\.json$")

def _base():
    url = os.getenv("AIZENS_BRAIN_PUBLIC_URL", BASE_DEFAULT).rstrip("/")
    if not re.fullmatch(r"https://[a-zA-Z0-9.-]+(?::443)?", url):
        raise HTTPException(503, "OAuth public origin configuration invalid")
    return url

def _resource():
    return _base() + "/mcp"

def _key():
    secret = os.getenv("NOTEBOOKLM_SERVER_TOKEN", "").strip()
    if len(secret) < 32:
        raise HTTPException(503, "OAuth signing key not configured")
    return hmac.new(secret.encode(), b"aizens-brain-oauth-v1", hashlib.sha256).digest()

def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def _unb64(raw):
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))

def _sign(payload):
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    mac = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    return "ab1." + body + "." + mac

def _client_redirect_valid(client_id, redirect):
    if client_id == "https://chatgpt.com/oauth/client.json":
        return redirect == "https://chatgpt.com/connector_platform_oauth_redirect"
    if not isinstance(client_id, str) or not isinstance(redirect, str):
        return False
    match = CLIENT_RE.fullmatch(client_id)
    return bool(match and redirect == "https://chatgpt.com/connector/oauth/" + match.group(1))

def _verify(token, kind):
    try:
        if not isinstance(token, str) or len(token) > 6000:
            return None
        marker, body, mac = token.split(".")
        if marker != "ab1" or not hmac.compare_digest(
            hmac.new(_key(), body.encode(), hashlib.sha256).digest(), _unb64(mac)
        ):
            return None
        data = json.loads(_unb64(body))
        now = int(time.time())
        if (
            not isinstance(data, dict) or data.get("typ") != kind
            or not isinstance(data.get("iat"), int)
            or not isinstance(data.get("exp"), int)
            or data["iat"] > now + 30 or data["exp"] <= now
            or data.get("iss") != _base() or data.get("aud") != _resource()
            or data.get("scope") != SCOPE
            or not _client_redirect_valid(data.get("client_id"), data.get("redirect_uri"))
        ):
            return None
        return data
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, OverflowError):
        return None

def validate_oauth_access(token):
    return _verify(token, "access") is not None

def _error(msg, status=400):
    return JSONResponse({"error": msg}, status_code=status, headers={"Cache-Control": "no-store"})

def _csrf():
    now = int(time.time())
    return _sign({
        "typ": "csrf", "iat": now, "exp": now + 600, "iss": _base(),
        "aud": _resource(), "scope": SCOPE,
        "client_id": "https://chatgpt.com/oauth/client.json",
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "nonce": secrets.token_urlsafe(24),
    })

def _fields(params):
    client_id = params.get("client_id", "")
    redirect = params.get("redirect_uri", "")
    challenge = params.get("code_challenge", "")
    state = params.get("state", "")
    if (
        not _client_redirect_valid(client_id, redirect)
        or params.get("response_type") != "code"
        or params.get("code_challenge_method") != "S256"
        or not PKCE_RE.fullmatch(challenge)
        or len(state) > 1024 or params.get("resource", _resource()) != _resource()
        or params.get("scope", SCOPE) not in (SCOPE, "")
    ):
        return None
    return {
        "client_id": client_id, "redirect_uri": redirect, "code_challenge": challenge,
        "state": state, "resource": _resource(), "scope": SCOPE,
    }

def _page(fields, error=False):
    hidden = "\n".join(
        '<input type="hidden" name="%s" value="%s">' % (html.escape(k), html.escape(v, quote=True))
        for k, v in fields.items()
    )
    message = '<p role="alert">Clave incorrecta. Vuelve a intentarlo.</p>' if error else ""
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Aizens Brain · Autorizar</title>
<style>body{{font:16px system-ui,sans-serif;max-width:450px;margin:10vh auto;padding:24px;line-height:1.5}}
input[type=password]{{display:block;width:100%;box-sizing:border-box;padding:12px;margin:12px 0}}
button{{padding:12px 18px;cursor:pointer}}small{{color:#555}}</style></head>
<body><h1>🧠 Aizens Brain</h1>
<p>Autoriza a ChatGPT a consultar tu memoria privada de NotebookLM.</p>
<p>Acceso <strong>solo lectura</strong>, sin compartir tus credenciales de Google.</p>
{message}<form method="post" action="/oauth/authorize">{hidden}
<label for="password">Clave privada de Aizens Brain</label>
<input id="password" type="password" name="password" autocomplete="off" required autofocus>
<button type="submit">Autorizar ChatGPT</button></form>
<p><small>Utiliza tu NOTEBOOKLM_SERVER_TOKEN o, si la configuraste,
AIZENS_BRAIN_LOGIN_SECRET. No envíes esta clave en un chat.</small></p></body></html>'''

def _html(body, status=200):
    return HTMLResponse(body, status_code=status, headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
    })

def _params(raw):
    if len(raw) > 12000:
        return None
    try:
        values = parse_qs(raw.decode("utf-8"), keep_blank_values=True, max_num_fields=25)
        if any(len(v) != 1 for v in values.values()):
            return None
        return {k: v[0] for k, v in values.items()}
    except (ValueError, UnicodeDecodeError):
        return None

def _issue(kind, fields, ttl):
    now = int(time.time())
    payload = {
        "typ": kind, "iss": _base(), "aud": _resource(), "scope": SCOPE,
        "iat": now, "exp": now + ttl,
        "client_id": fields["client_id"], "redirect_uri": fields["redirect_uri"],
        "jti": secrets.token_urlsafe(20),
    }
    if kind == "code":
        payload["challenge"] = fields["code_challenge"]
    return _sign(payload)

def create_oauth_router():
    router = APIRouter()

    @router.get("/.well-known/oauth-protected-resource")
    @router.get("/.well-known/oauth-protected-resource/mcp")
    async def protected_resource():
        return JSONResponse({
            "resource": _resource(), "authorization_servers": [_base()],
            "scopes_supported": [SCOPE],
        }, headers={"Cache-Control": "no-store"})

    @router.get("/.well-known/oauth-authorization-server")
    async def metadata():
        return JSONResponse({
            "issuer": _base(),
            "authorization_endpoint": _base() + "/oauth/authorize",
            "token_endpoint": _base() + "/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "client_id_metadata_document_supported": True,
            "authorization_response_iss_parameter_supported": True,
            "scopes_supported": [SCOPE],
        }, headers={"Cache-Control": "no-store"})

    @router.get("/oauth/authorize")
    async def login(request: Request):
        fields = _fields(dict(request.query_params))
        if fields is None:
            return _html("Invalid OAuth authorization request", 400)
        form = {**fields, "response_type": "code", "code_challenge_method": "S256"}
        response = _html(_page(form))
        response.set_cookie("aizens_oauth_csrf", _csrf(), secure=True, httponly=True,
                            samesite="lax", max_age=600, path="/oauth/authorize")
        return response

    @router.post("/oauth/authorize")
    async def approve(request: Request):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            return _error("invalid_request", 415)
        params = _params(await request.body())
        fields = _fields(params) if params else None
        if fields is None:
            return _error("invalid_request")
        if _verify(request.cookies.get("aizens_oauth_csrf", ""), "csrf") is None:
            return _error("invalid_request", 403)
        secret = os.getenv("AIZENS_BRAIN_LOGIN_SECRET", "").strip()
        expected = secret or os.getenv("NOTEBOOKLM_SERVER_TOKEN", "").strip()
        password = params.get("password", "")
        if len(expected) < 32 or not hmac.compare_digest(password.encode(), expected.encode()):
            return _html(_page({**fields, "response_type": "code", "code_challenge_method": "S256"}, True), 401)
        code = _issue("code", fields, 90)
        url = fields["redirect_uri"] + "?" + urlencode({"code": code, "state": fields["state"], "iss": _base()})
        response = RedirectResponse(url, status_code=302, headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        })
        response.delete_cookie("aizens_oauth_csrf", path="/oauth/authorize")
        return response

    @router.post("/oauth/token")
    async def exchange(request: Request):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            return _error("invalid_request")
        params = _params(await request.body())
        if params is None or params.get("resource", _resource()) != _resource():
            return _error("invalid_request")
        grant = params.get("grant_type")
        if grant == "authorization_code":
            claims = _verify(params.get("code", ""), "code")
            verifier = params.get("code_verifier", "")
            if not claims or not PKCE_RE.fullmatch(verifier):
                return _error("invalid_grant")
            digest = _b64(hashlib.sha256(verifier.encode()).digest())
            if (
                claims.get("client_id") != params.get("client_id")
                or claims.get("redirect_uri") != params.get("redirect_uri")
                or not hmac.compare_digest(digest, claims.get("challenge", ""))
            ):
                return _error("invalid_grant")
        elif grant == "refresh_token":
            claims = _verify(params.get("refresh_token", ""), "refresh")
            if not claims or claims.get("client_id") != params.get("client_id"):
                return _error("invalid_grant")
        else:
            return _error("unsupported_grant_type")
        fields = {"client_id": claims["client_id"], "redirect_uri": claims["redirect_uri"]}
        return JSONResponse({
            "access_token": _issue("access", fields, 3600), "token_type": "Bearer",
            "expires_in": 3600, "refresh_token": _issue("refresh", fields, 30 * 86400),
            "scope": SCOPE,
        }, headers={"Cache-Control": "no-store"})

    return router
