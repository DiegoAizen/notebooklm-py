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
WRITE_SCOPE = "brain:read brain:write"
ACCEPTED_SCOPES = (SCOPE, WRITE_SCOPE)
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
            or data.get("scope") not in ACCEPTED_SCOPES
            or not _client_redirect_valid(data.get("client_id"), data.get("redirect_uri"))
        ):
            return None
        return data
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, OverflowError):
        return None

def validate_oauth_access(token):
    return _verify(token, "access") is not None


def get_oauth_access(token):
    """Return scoped access claims or None. Do not accept access by boolean alone for writes."""
    return _verify(token, "access")

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
        or params.get("scope", SCOPE) not in (*ACCEPTED_SCOPES, "")
    ):
        return None
    return {
        "client_id": client_id, "redirect_uri": redirect, "code_challenge": challenge,
        "state": state, "resource": _resource(), "scope": params.get("scope") or SCOPE,
    }

def _form_ticket(fields):
    """Bind a signed 10-minute approval intent to this exact OAuth request."""
    now = int(time.time())
    return _sign({
        "typ": "form", "iat": now, "exp": now + 600, "iss": _base(),
        "aud": _resource(), "scope": SCOPE,
        "client_id": fields["client_id"], "redirect_uri": fields["redirect_uri"],
        "challenge": fields["code_challenge"], "state": fields["state"],
        "scope": fields["scope"],
        "nonce": secrets.token_urlsafe(20),
    })


def _page(fields, error=False):
    """Accessible, mobile-first authorization view with no external assets/JS."""
    safe_fields = {**fields, "form_ticket": _form_ticket(fields)}
    hidden = "\n".join(
        '<input type="hidden" name="%s" value="%s">' % (
            html.escape(k, quote=True), html.escape(v, quote=True),
        )
        for k, v in safe_fields.items()
    )
    message = (
        '<div class="alert" role="alert">La clave no es correcta. '
        'Compruébala e inténtalo de nuevo.</div>'
        if error is True else (
            '<div class="alert" role="alert">La sesión de autorización ha caducado '
            'o tu navegador la bloqueó. Vuelve a iniciar la conexión desde ChatGPT.</div>'
            if error == "session" else ""
        )
    )
    template = '''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#f6f8fc">
<meta name="robots" content="noindex,nofollow">
<title>Autorizar acceso · Aizens Brain</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}
html{min-height:100%;background:#f6f8fc}
body{margin:0;min-height:100vh;min-height:100dvh;color:#14213c;background:
 radial-gradient(ellipse 380px 310px at 10% 5%,#dceaffb5,transparent 95%),
 radial-gradient(ellipse 350px 260px at 90% 92%,#e7ddff80,transparent 95%),
 #f6f8fc;display:flex;flex-direction:column}
main{display:flex;flex:1;justify-content:center;align-items:center;padding:28px 18px}
.card{position:relative;width:min(100%,475px);padding:clamp(25px,5vw,43px);
 background:#fff;border:1px solid #e5eaf3;border-radius:24px;
 box-shadow:0 22px 75px #243b7015,0 4px 14px #243b7008}
.mark{width:64px;height:64px;border-radius:20px;display:grid;place-items:center;
 margin-bottom:26px;background:linear-gradient(145deg,#2b73e9,#7253e7);
 box-shadow:0 10px 24px #4164d739;color:#fff}
.mark svg{width:38px;height:38px}
.eyebrow{font-size:11px;font-weight:800;letter-spacing:2px;color:#5679c0;margin:0 0 9px}
h1{font-size:clamp(27px,5vw,33px);font-weight:760;letter-spacing:-1.2px;
 line-height:1.17;margin:0 0 13px;color:#14213c}
.intro{font-size:15px;line-height:1.65;color:#65728a;margin:0 0 27px}
label{display:block;font-size:13px;font-weight:700;color:#273753;margin-bottom:9px}
input[type=password]{display:block;width:100%;height:54px;border:1.5px solid #d9e1ee;
 border-radius:13px;background:#fff;color:#1d2b46;padding:0 16px;
 font:inherit;font-size:16px;outline:none;transition:border-color .15s,box-shadow .15s}
input[type=password]:focus{border-color:#426bdd;box-shadow:0 0 0 4px #426bdd19}
input[type=password]::placeholder{color:#a1abba}

button{width:100%;min-height:54px;margin-top:19px;border:none;border-radius:13px;
 display:flex;justify-content:center;align-items:center;gap:12px;
 background:#264fd3;color:white;font:inherit;font-size:15px;font-weight:730;
 cursor:pointer;transition:transform .15s,background .15s,box-shadow .15s;
 box-shadow:0 9px 20px #2c57db35}
button:hover{background:#1d43c1;box-shadow:0 12px 25px #2c57db40}
button:active{transform:translateY(1px)}
button:focus-visible{outline:3px solid #8dadff;outline-offset:3px}
.alert{padding:13px 15px;margin:0 0 18px;border-radius:12px;background:#fff3f2;
 color:#a03532;border:1px solid #f2d0cd;font-size:13px;line-height:1.5}
@media(max-width:480px){.card{border-radius:20px}.mark{margin-bottom:22px}main{align-items:center;padding:20px 15px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<main>
<section class="card" aria-labelledby="page-title">
<div class="mark" aria-hidden="true">
<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
<circle cx="24" cy="9.5" r="3.5" fill="currentColor" stroke="none"/>
<circle cx="10" cy="25" r="3.5" fill="currentColor" stroke="none"/>
<circle cx="38" cy="25" r="3.5" fill="currentColor" stroke="none"/>
<circle cx="24" cy="39" r="3.5" fill="currentColor" stroke="none"/>
<path d="M20.8 12.4 13 21.6m14.2-9.2 7.8 9.2M13 28.3l7.8 7.8m14.2-7.8-7.8 7.8M13.5 25h21M24 13v22"/>
</svg>
</div>
<p class="eyebrow">CONEXIÓN SEGURA</p>
<h1 id="page-title">Conecta tu memoria con ChatGPT</h1>
<p class="intro">__INTRO__</p>
__MESSAGE__
<form action="/oauth/authorize" method="post" autocomplete="off">
__FIELDS__
<label for="password">Clave de acceso privada</label>
<input id="password" type="password" name="password" autocomplete="off"
 placeholder="Introduce tu clave de Aizens Brain" required>
<button type="submit">Autorizar conexión</button>
</form>
</section>
</main>
</body>
</html>'''
    intro = (
        "Autoriza a ChatGPT a consultar, crear y actualizar los proyectos "
        "de tu Aizens Brain."
        if fields.get("scope") == WRITE_SCOPE else
        "Autoriza a ChatGPT a consultar los cuadernos de NotebookLM "
        "disponibles en tu Aizens Brain."
    )
    return template.replace("__FIELDS__", hidden).replace("__MESSAGE__", message).replace("__INTRO__", intro)


def _approval_page(redirect_url: str) -> str:
    """Explicit handoff to ChatGPT: automatic navigation plus manual fallback.

    The callback URL is already checked against ChatGPT-only allowlist before
    this is called. The authorization code is short-lived, so never cache.
    """
    safe_url = html.escape(redirect_url, quote=True)
    return """<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="1;url=""" + safe_url + """">
<title>Conexión autorizada · Aizens Brain</title>
<style>body{min-height:100vh;margin:0;display:grid;place-items:center;background:#f6f8fc;
font:16px system-ui,sans-serif;color:#17243a;padding:18px;box-sizing:border-box}
main{width:min(100%,390px);background:#fff;border:1px solid #e6ebf3;
border-radius:22px;padding:38px 28px;text-align:center;
box-shadow:0 20px 55px #1a3a6a18}
.mark{display:grid;place-items:center;margin:0 auto 16px;width:58px;height:58px;
border-radius:18px;background:#e4f8ec;color:#137b4f;font-size:29px}
h1{font-size:26px;letter-spacing:-.7px;margin:0 0 12px}
p{line-height:1.6;color:#66758d;margin:0 0 23px}
a{display:block;background:#264fd3;color:#fff;text-decoration:none;
border-radius:13px;padding:17px 16px;font-weight:700}
a:focus-visible{outline:3px solid #9bb7ff;outline-offset:3px}
</style></head>
<body><main><div class="mark" aria-hidden="true">✓</div>
<h1>Conexión autorizada</h1><p>Volviendo a ChatGPT…</p>
<a href='""" + safe_url + """'>Continuar en ChatGPT</a>
</main></body></html>"""


def _approval_response(redirect_url: str):
    if not (
        redirect_url.startswith("https://chatgpt.com/connector_platform_oauth_redirect?")
        or redirect_url.startswith("https://chatgpt.com/connector/oauth/")
    ):
        raise HTTPException(500, "Invalid trusted OAuth return URL")
    return HTMLResponse(
        _approval_page(redirect_url),
        headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
        },
    )

def _html(body, status=200):
    return HTMLResponse(body, status_code=status, headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin", "X-Frame-Options": "DENY",
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
        "typ": kind, "iss": _base(), "aud": _resource(), "scope": fields.get("scope", SCOPE),
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
            "scopes_supported": [SCOPE, "brain:write"],
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
            "scopes_supported": [SCOPE, "brain:write"],
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
        ticket = _verify(params.get("form_ticket", ""), "form")
        if (
            ticket is None
            or ticket.get("client_id") != fields["client_id"]
            or ticket.get("redirect_uri") != fields["redirect_uri"]
            or ticket.get("challenge") != fields["code_challenge"]
            or ticket.get("state") != fields["state"]
            or ticket.get("scope") != fields["scope"]
        ):
            return _html(_page({**fields, "response_type": "code",
                                "code_challenge_method": "S256"}, error="session"), 403)
        # The signed, short-lived form ticket binds this POST to the exact
        # OAuth challenge/state and is validated above. Brave may omit cookies,
        # Origin or Referer. Reject explicit cross-origin requests, but do not
        # make a privacy header mandatory for a valid signed form.
        origin = request.headers.get("origin", "").rstrip("/")
        if origin and origin != _base():
            return _html(_page({**fields, "response_type": "code",
                                "code_challenge_method": "S256"}, error="session"), 403)
        secret = os.getenv("AIZENS_BRAIN_LOGIN_SECRET", "").strip()
        expected = secret or os.getenv("NOTEBOOKLM_SERVER_TOKEN", "").strip()
        password = params.get("password", "")
        if len(expected) < 32 or not hmac.compare_digest(password.encode(), expected.encode()):
            return _html(_page({**fields, "response_type": "code", "code_challenge_method": "S256"}, True), 401)
        code = _issue("code", fields, 90)
        url = fields["redirect_uri"] + "?" + urlencode({"code": code, "state": fields["state"], "iss": _base()})
        response = _approval_response(url)
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
        fields = {"client_id": claims["client_id"], "redirect_uri": claims["redirect_uri"], "scope": claims["scope"]}
        return JSONResponse({
            "access_token": _issue("access", fields, 3600), "token_type": "Bearer",
            "expires_in": 3600, "refresh_token": _issue("refresh", fields, 30 * 86400),
            "scope": claims["scope"],
        }, headers={"Cache-Control": "no-store"})

    return router
