#!/bin/sh
set -eu

# El perfil se reconstruye con cada arranque: Render Free tiene disco efímero.
: "${NOTEBOOKLM_MASTER_TOKEN_JSON:?Configura NOTEBOOKLM_MASTER_TOKEN_JSON en Render}"
: "${NOTEBOOKLM_SERVER_TOKEN:?Configura NOTEBOOKLM_SERVER_TOKEN en Render}"

umask 077
python - <<'PY'
import json
import os
from pathlib import Path

raw = os.environ["NOTEBOOKLM_MASTER_TOKEN_JSON"]
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit("La credencial Google no contiene JSON valido") from None
if not isinstance(data, dict) or not data:
    raise SystemExit("Formato invalido para master_token.json")

home = Path(os.environ["NOTEBOOKLM_HOME"])
profile = home / "profiles" / "server"
profile.mkdir(parents=True, exist_ok=True, mode=0o700)
destination = profile / "master_token.json"
destination.write_text(raw, encoding="utf-8")
destination.chmod(0o600)
PY

# No heredar el master token como variable hacia el proceso del servidor.
unset NOTEBOOKLM_MASTER_TOKEN_JSON
export NOTEBOOKLM_SERVER_ALLOW_EXTERNAL_BIND=1

exec notebooklm-server \
  --backend android \
  --profile server \
  --host 0.0.0.0 \
  --port "${PORT:-10000}"
