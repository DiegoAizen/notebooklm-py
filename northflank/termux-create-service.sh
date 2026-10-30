#!/usr/bin/env bash
# Crea el servicio Northflank desde un GitHub PUBLICO, sin vincular GitHub en la interfaz.
# Ejecutar desde Termux: bash northflank/termux-create-service.sh
# Solo registra el servicio inicialmente con 0 replicas, sin secretos y sin CI.
# Antes de hacer cambios pide confirmacion.
set -euo pipefail

for cmd in curl python; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Falta $cmd. En Termux: pkg install curl python"
    exit 1
  fi
done

PROJECT_ID="default"
SERVICE_NAME="aizens-notebooklm"
REPO_URL="https://github.com/DiegoAizen/notebooklm-py"
API="https://api.northflank.com/v1"
if [[ -n "${NORTHFLANK_API_TOKEN:-}" ]]; then
  TOKEN="${NORTHFLANK_API_TOKEN}"
else
  read -r -s -p "Token API de Northflank (no se guarda): " TOKEN
  printf '\n'
fi
if [[ -z "$TOKEN" ]]; then
  echo "No se introdujo token."
  exit 1
fi
trap 'unset TOKEN' EXIT

echo "[1/3] Comprobando acceso PUBLICO al repositorio..."
CHECK=$(curl -fsS --connect-timeout 15 --max-time 40 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"projectUrl":"https://github.com/DiegoAizen/notebooklm-py","projectType":"github","projectBranch":"main"}' \
  "$API/projects/$PROJECT_ID/services/repo-access")
ACCESS=$(printf '%s' "$CHECK" | python -c 'import json,sys; d=json.load(sys.stdin).get("data",{}); print(str(d.get("accessible",False)).lower()); print(d.get("reason","desconocido"),file=sys.stderr)')
if [[ "$ACCESS" != "true" ]]; then
  echo "Northflank no puede leer el repo directamente. No se ha creado nada."
  echo "Revisar Integrations > Git > GitHub App o permisos del token API."
  exit 2
fi
echo "Correcto: Northflank puede leer el repositorio."

echo "[2/3] Comprobando servicios existentes..."
SERVICES=$(curl -fsS --connect-timeout 15 --max-time 40 -H "Authorization: Bearer $TOKEN" "$API/projects/$PROJECT_ID/services")
EXISTS=$(printf '%s' "$SERVICES" | python -c 'import json,sys; o=json.load(sys.stdin); x=o.get("data",{}).get("services",[]); print("yes" if any(s.get("name")=="aizens-notebooklm" or s.get("id")=="aizens-notebooklm" for s in x) else "no")')
if [[ "$EXISTS" == "yes" ]]; then
  echo "Ya existe aizens-notebooklm. No se crea duplicado."
  exit 0
fi

echo
echo "Se creara UN servicio en Default, con:"
echo "  Repositorio publico: $REPO_URL (main)"
echo "  Dockerfile: /northflank/Dockerfile"
echo "  Plan de recursos: nf-compute-20 (0.2 vCPU, 512 MiB)"
echo "  Puerto HTTP publico: 10000"
echo "  Replicas iniciales: 0 (SIN consumir computo hasta activarlo)"
echo "  CI desactivada: compilacion manual posterior"
echo "Confirma en Billing que tu cuenta sigue en Sandbox y dentro de la cuota."
read -r -p "¿Quieres crear SOLO la definicion del servicio? [s/N]: " ANSWER
case "$ANSWER" in
  s|S|si|SI|Si) ;;
  *) echo "Cancelado sin cambios."; exit 0 ;;
esac

echo "[3/3] Creando servicio..."
# IMPORTANTE: -f oculta el cuerpo de las respuestas HTTP 4xx.
# Capturar y mostrar el detalle del error sin mostrar el token de autorizacion.
RESULT=$(curl -sS --connect-timeout 15 --max-time 80 \
  -w '\nNF_HTTP_STATUS:%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "name":"aizens-notebooklm",
    "description":"API privada de NotebookLM para agentes Aizens",
    "billing":{"deploymentPlan":"nf-compute-20"},
    "deployment":{
      "instances":0,
      "docker":{"configType":"default"},
      "storage":{"ephemeralStorage":{"storageSize":1024}}
    },
    "ports":[{"name":"http","internalPort":10000,"public":true,"protocol":"HTTP"}],
    "disabledCI":true,
    "buildSource":"git",
    "vcsData":{
      "projectUrl":"https://github.com/DiegoAizen/notebooklm-py",
      "projectType":"github",
      "projectBranch":"main"
    },
    "buildSettings":{
      "dockerfile":{
        "buildEngine":"buildkit",
        "dockerFilePath":"/northflank/Dockerfile",
        "dockerWorkDir":"/"
      }
    },
    "healthChecks":[
      {
        "protocol":"HTTP",
        "type":"readinessProbe",
        "path":"/healthz",
        "port":10000,
        "initialDelaySeconds":10,
        "periodSeconds":30,
        "timeoutSeconds":5,
        "failureThreshold":3,
        "successThreshold":1
      }
    ]
  }' "$API/projects/$PROJECT_ID/services/combined")
HTTP_CODE=$(printf '%s' "$RESULT" | tail -n 1 | sed 's/^NF_HTTP_STATUS://')
RESULT=$(printf '%s' "$RESULT" | sed '$d')
if [[ "$HTTP_CODE" != "200" && "$HTTP_CODE" != "201" ]]; then
  echo "Northflank respondió HTTP $HTTP_CODE. No se ha confirmado la creación."
  # Mostrar únicamente campos de diagnostico: nunca tokens ni cabeceras.
  printf '%s' "$RESULT" | python -c 'import json,sys
try:
    obj=json.load(sys.stdin)
except (ValueError,TypeError):
    print("Respuesta no JSON; revisar desde el panel de Northflank.")
    sys.exit(0)
for key in ("message","error","code","details","errors","status"):
    value=obj.get(key) if isinstance(obj,dict) else None
    if value is not None:
        if isinstance(value,dict):
            value={k:v for k,v in value.items() if k in ("message","code","type","details","status","errors","reason")}
        print(f"{key}: {str(value)[:1200]}")
' || true
  echo "Si ves HTTP 409, copia aqui SOLO el mensaje de error, nunca el token."
  exit 4
fi
printf '%s' "$RESULT" | python -c 'import json,sys; o=json.load(sys.stdin); d=o.get("data",{}); print("Servicio creado:",d.get("name",""),"ID:",d.get("id","no devuelto")); print("Pendiente: secretos, build, replicas=1 y prueba real.")'
