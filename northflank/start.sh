#!/bin/sh
set -eu

# Northflank almacena los secretos en su configuracion. Nunca subirlos a git.
: "${NOTEBOOKLM_MASTER_TOKEN_JSON:?Falta NOTEBOOKLM_MASTER_TOKEN_JSON en Secret / Environment}"
: "${NOTEBOOKLM_SERVER_TOKEN:?Falta NOTEBOOKLM_SERVER_TOKEN en Secret / Environment}"

umask 077
python - <<'PY'
import json
import os
from pathlib import Path

raw = os.environ["NOTEBOOKLM_MASTER_TOKEN_JSON"]
try:
    obj = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit("NOTEBOOKLM_MASTER_TOKEN_JSON no es JSON valido") from None
if not isinstance(obj, dict) or not obj:
    raise SystemExit("NOTEBOOKLM_MASTER_TOKEN_JSON requiere objeto JSON")

folder = Path(os.environ["NOTEBOOKLM_HOME"]) / "profiles" / "server"
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
file = folder / "master_token.json"
file.write_text(raw, encoding="utf-8")
file.chmod(0o600)
PY

# No exponer el token maestro en el entorno del proceso de la API.
unset NOTEBOOKLM_MASTER_TOKEN_JSON
export NOTEBOOKLM_SERVER_ALLOW_EXTERNAL_BIND=1

exec notebooklm-server \
  --backend android \
  --profile server \
  --host 0.0.0.0 \
  --port 10000
