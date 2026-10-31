#!/usr/bin/env python3
"""Aizens NotebookLM: comprobación remota sin imprimir credenciales ni contenido privado.

Uso (Debian/Termux): python scripts/aizens_vercel_smoke.py
Requiere un token de servidor válido introducido de forma privada.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://aizens-notebooklm.vercel.app"


def request(base: str, method: str, path: str, *, token: str | None = None,
            payload: dict | None = None, timeout: int = 90) -> tuple[int, dict]:
    headers = {"Accept": "application/json", "Cache-Control": "no-store"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw, status = res.read(4_000_000), res.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(32_000), exc.code
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = {}
    return status, body if isinstance(body, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba E2E segura de Aizens NotebookLM.")
    parser.add_argument("--base", default=DEFAULT_BASE, help="URL HTTPS de la API")
    parser.add_argument("--notebook-id", default=None, help="ID opcional de cuaderno de prueba")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    parts = urllib.parse.urlparse(base)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query:
        print("FAIL: URL base HTTPS inválida.")
        return 2

    try:
        status, body = request(base, "GET", "/healthz", timeout=30)
        if status != 200 or body.get("ok") is not True:
            print(f"FAIL: /healthz HTTP {status} (se esperaba 200 y ok=true)")
            return 1
        print("PASS: /healthz devuelve 200 y ok=true")

        fake = "smoke-invalid-" + secrets.token_urlsafe(16)
        status, _ = request(base, "GET", "/v1/notebooks", token=fake, timeout=40)
        if status != 401:
            print(f"FAIL: token deliberadamente inválido devuelve {status}, no 401")
            return 1
        print("PASS: credencial inválida rechazada con HTTP 401")
    except (OSError, TimeoutError) as exc:
        print(f"FAIL: red/protección Vercel ({type(exc).__name__}); revise acceso al dominio.")
        return 1

    token = os.getenv("AIZENS_SERVER_TOKEN") or getpass.getpass(
        "Introduce NOTEBOOKLM_SERVER_TOKEN (no se muestra ni se guarda): "
    )
    if not token:
        print("FAIL: sin token de servidor. No se ha hecho ninguna consulta autenticada.")
        return 2
    try:
        status, body = request(base, "GET", "/v1/notebooks", token=token, timeout=120)
        if status != 200:
            print(f"FAIL: GET /v1/notebooks -> HTTP {status}")
            if status == 401:
                print("Comprueba el token y si Vercel Authentication bloquea el dominio.")
            elif status == 503:
                print("Comprueba la configuración privada del token maestro.")
            elif status == 502:
                print("La conexión con Google/NotebookLM falló. Revisa logs del servidor.")
            return 1
        items = body.get("notebooks")
        if not isinstance(items, list):
            print("FAIL: la respuesta de notebooks no contiene una lista válida.")
            return 1
        print(f"PASS: GET /v1/notebooks autenticado; cuadernos accesibles: {len(items)}")

        notebook_id = args.notebook_id or next(
            (x.get("id") for x in items if isinstance(x, dict) and isinstance(x.get("id"), str)),
            None,
        )
        if not notebook_id:
            print("INCOMPLETO: no hay cuaderno de prueba; no se realizó POST /chat.")
            return 2
        if not any(isinstance(x, dict) and x.get("id") == notebook_id for x in items):
            print("FAIL: el ID elegido no corresponde a un cuaderno de esta cuenta.")
            return 1

        status, body = request(
            base, "POST", "/v1/notebooks/" + urllib.parse.quote(notebook_id, safe="") + "/chat",
            token=token,
            payload={"question": "Resume en una frase el tema principal de las fuentes y cita una fuente si existe."},
            timeout=240,
        )
        if status != 200:
            print(f"FAIL: POST /chat -> HTTP {status}. No se imprimen respuestas privadas.")
            return 1
        answer = body.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            print("FAIL: HTTP 200 pero respuesta vacía o sin campo answer.")
            return 1
        references = body.get("references")
        refs = len(references) if isinstance(references, list) else 0
        print("PASS: POST /chat devuelve respuesta no vacía. Contenido redactado.")
        if refs > 0:
            print(f"PASS: referencias documentales presentes ({refs}).")
        else:
            print("AVISO: sin referencias explícitas; confirma que el cuaderno de prueba tiene fuentes.")
        print("RESULTADO: consulta E2E autenticada aprobada; no se expusieron secretos ni contenido.")
        return 0
    except (OSError, TimeoutError) as exc:
        print(f"FAIL: comunicación remota ({type(exc).__name__}); revisa red, Vercel y timeout.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
