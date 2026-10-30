# Aizens NotebookLM — Vercel Hobby (bajo demanda)

## Objetivo
Ejecutar el fork `DiegoAizen/notebooklm-py` con una API **solo lectura**
en Python/FastAPI. Cada solicitud crea una conexión a NotebookLM, consulta y
termina. Sin procesos permanentes, cron ni GitHub Actions.

## Archivos
- `app.py`: entrada ASGI de Vercel, rutas públicas de salud y privadas de consultas
- `requirements.txt`: instala este fork con el extra headless + FastAPI
- `vercel.json`: duración máxima 300 s (Fluid Compute / Hobby)

## Configuración privada (Vercel → Project → Settings → Environment Variables)
Crear como **Sensitive/Encrypted**, para production y preview:
- `NOTEBOOKLM_SERVER_TOKEN`: clave aleatoria larga creada localmente
  con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `NOTEBOOKLM_MASTER_TOKEN_JSON`: JSON completo de
  `~/.notebooklm/profiles/default/master_token.json` de una cuenta de
  Google **dedicada**. NO es lo mismo que `storage_state.json`.

Para generar la autenticación una sola vez en un equipo de confianza, consultar
`docs/installation.md`: instalar `notebooklm-py[browser,headless]` y ejecutar
`notebooklm login --master-token --account <correo-de-cuenta-dedicada>`.
Conservar el archivo estrictamente fuera de GitHub y de cualquier chat.
Nunca enviar credenciales de la cuenta personal. El token maestro concede
acceso amplio a la cuenta y debe tratarse como una contraseña.

## Pruebas (tras configurar secretos y desplegar otra vez)
```bash
curl -sS https://TU_PROYECTO.vercel.app/healthz
curl --fail-with-body -H "Authorization: Bearer $API_TOKEN" \
  https://TU_PROYECTO.vercel.app/v1/notebooks
curl --fail-with-body -X POST \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Resume las fuentes de este cuaderno"}' \
  https://TU_PROYECTO.vercel.app/v1/notebooks/ID/chat
```

No reintentar automáticamente la ruta POST al superar el tiempo máximo.
La salud `/healthz` no prueba que Google esté autenticado. Las rutas de datos
responden 401 sin token API y 503 sin cuenta Google configurada.

## Limitaciones
- Hobby: restricciones de uso, tiempo de función y tamaño de archivos. Solo
  uso personal/no comercial según las condiciones del plan.
- El backend usa APIs no oficiales de Google; pueden cambiar y bloquearse.
- El almacenamiento es efímero: las cookies se regeneran desde el token maestro
  en una nueva instancia, aumentando la latencia de arranque.
- No exponer `NOTEBOOKLM_MASTER_TOKEN_JSON`, logs sensibles ni cuentas personales.
- Las sesiones simultáneas y múltiples instancias Vercel necesitan pruebas
  reales; el endpoint está destinado a consultas personales poco frecuentes.
- La primera consulta autenticada real requiere configurar los dos secretos
  desde Vercel y verificar funcionamiento con un cuaderno de prueba.

## Estado inicial
Repositorio adaptado. Hasta completar la configuración de secretos y las
pruebas reales, NO declarar operativo el acceso a NotebookLM.
