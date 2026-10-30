# Aizens NotebookLM — Northflank

## Estado

Preparacion de codigo para Northflank completada. **No se ha creado ningun servicio ni hay conexion Google operativa todavia.** El conector Northflank de ChatGPT permite leer proyectos y gestionar servicios ya creados, pero no tiene la accion de crear un servicio. La creacion inicial necesita una operacion manual en el panel de Northflank.

GitHub: `DiegoAizen/notebooklm-py`, rama `main`. No se utilizan GitHub Actions ni cron-job.org.

## Configuracion exacta en Northflank

En el proyecto `Default` (region `europe-west`), crear un servicio:

| Campo | Valor |
| --- | --- |
| Tipo | **Combined** (build + deployment) |
| Nombre | `aizens-notebooklm` |
| Proveedor/repositorio | GitHub: `DiegoAizen/notebooklm-py` |
| Rama | `main` |
| Build mode | `Dockerfile` |
| Dockerfile path | `northflank/Dockerfile` |
| Build context | `/` (raiz del repositorio) |
| HTTP public port | `10000` |
| Instancias | `1` |
| Health check HTTP | `/healthz` en puerto `10000` |
| Auto-build | Desactivado inicialmente para controlar actualizaciones |
| Compute | La opcion mas pequena compatible con el plan Sandbox; observar RAM/CPU y logs |

La interfaz puede mostrar los campos con nombres ligeramente distintos. El contenedor escucha en `0.0.0.0:10000`; Northflank finaliza HTTPS en el dominio publico. `/healthz` solo confirma que el proceso responde, **no** que NotebookLM haya autenticado correctamente.

## Secretos obligatorios — NO subir a GitHub

Configurar en Environment / Secrets del servicio, en runtime:

- `NOTEBOOKLM_SERVER_TOKEN`: token largo aleatorio para proteger la API REST. Generar en local, por ejemplo `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `NOTEBOOKLM_MASTER_TOKEN_JSON`: contenido JSON completo de `master_token.json` de una cuenta de Google **dedicada**, obtenida con el inicio de sesion no oficial que documenta notebooklm-py.

**No copiar credenciales personales a un repo ni a un chat.** Este token maestro tiene privilegios amplios sobre la cuenta Google. La autenticacion requiere una inicializacion compatible (normalmente navegador desde PC). El inicio de sesion en Termux con Playwright no esta garantizado. Consulta `docs/installation.md` y `docs/android/README.md`.

El script `northflank/start.sh` valida las variables, copia el token a un archivo protegido `0600` dentro del contenedor, elimina la variable del entorno antes de ejecutar el proceso y lanza `notebooklm-server --backend android`. Si falta cualquier secreto, el arranque falla de forma segura.

## Comprobacion tras crear el servicio

En un equipo autorizado:

```bash
# Configurar BASE_URL y API_TOKEN de forma privada, nunca en un repo.
curl --fail-with-body --max-time 30 "$BASE_URL/healthz"

curl --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $API_TOKEN" \
  "$BASE_URL/v1/notebooks"
```

Solo la segunda peticion valida el acceso autenticado a NotebookLM.

Para consultar un cuaderno existente:

```bash
curl --fail-with-body --max-time 180 -X POST \
  "$BASE_URL/v1/notebooks/ID_DEL_CUADERNO/chat" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Resume los cambios pendientes y proporciona referencias a las fuentes."}'
```

No reintentar automaticamente POST no idempotentes cuando una respuesta no llegue: la operacion puede haber terminado en Google y duplicarse.

## Diferencias frente a Render

Northflank anuncia el plan Sandbox como **always on, no sleeping**. No heredar el procedimiento de despertar cada 10/16 minutos ni el timeout de arranque por suspension de Render. Un servicio pausado o escalado a 0 instancias **no** se reanuda automaticamente por una peticion HTTP; necesita activarse con el panel o API.

Segun los terminos del Sandbox, hay limites de recursos y presupuesto: confirmar en `Billing` antes de crear y no asumir que la cuota `Free` del complemento ChatGPT corresponde a la del hosting.

## Despues de crearlo

El complemento Northflank disponible permite consultar servicios, builds, reiniciar, pausar, reanudar y cambiar replicas. Con el ID de `aizens-notebooklm` creado en `Default`, podra comprobar el estado y desencadenar compilaciones. Los secretos se configuran en Northflank; nunca se imprimen en informes.

Referencias:
- [Northflank - build & deploy](https://northflank.com/docs/v1/application/getting-started/build-and-deploy-your-code)
- [Northflank - networking](https://northflank.com/docs/v1/application/network/configure-ports)
- [Northflank - pricing](https://northflank.com/pricing)
- [notebooklm-py - REST](https://github.com/teng-lin/notebooklm-py/blob/main/docs/installation.md#rest-api-server)
- [notebooklm-py - security](https://github.com/teng-lin/notebooklm-py/blob/main/SECURITY.md)

## Pruebas pendientes

Docker build real, conexion a Google, GET autentificado, consulta a un cuaderno y reinicio seguro. Ninguna de estas pruebas se declara superada antes de ejecutarla en Northflank.
