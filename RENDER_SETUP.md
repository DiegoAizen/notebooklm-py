# Aizens NotebookLM — preparación para Render

Este fork incorpora un servidor REST privado para consultar Google NotebookLM desde agentes y Termux. **El servicio aún no se ha creado en Render.** No exige GitHub Actions ni cron-job.org.

## Decisiones

- Docker utiliza el **código de este fork** (actualmente la versión 0.8.6 declarada en `pyproject.toml`), con Python 3.12 y los extras `server,android`.
- Servidor REST existente `notebooklm-server` sobre el backend Android/gRPC.
- Render Free, despliegues manuales (`autoDeployTrigger: off`), activación automática al recibir peticiones.
- Un único perfil `server`: **solo uso privado, no multiusuario**.
- Las fuentes y cuadernos se almacenan en Google; las credenciales locales se recrean desde secretos en cada arranque.

## 1. Credencial Google (pendiente)

**Crea una cuenta Google dedicada**, diferente de tu cuenta personal. El archivo `master_token.json` permite obtener acceso amplio a la cuenta: nunca lo subas a GitHub, lo pegues en un chat, lo envíes a un agente sin necesidad ni lo registres en logs.

La autenticación inicial requiere un equipo con navegador compatible. Por ejemplo, en PC/Linux:

```bash
python -m venv .venv
. .venv/bin/activate
pip install "notebooklm-py[browser,headless]"
notebooklm login --master-token --account CUENTA_DEDICADA@gmail.com
```

Consulta `~/.notebooklm/profiles/default/master_token.json` (o el perfil indicado por la CLI). **El login normal no genera este archivo**, y la autenticación con navegador desde Termux no está garantizada. No lo generes mediante servicios de terceros.

## 2. Cuando se libere espacio en Render

1. Render → **New → Blueprint** → elegir `DiegoAizen/notebooklm-py` y rama `main`.
2. Confirmar los valores de `render.yaml` y que se crea solo **un Web Service gratuito**.
3. Render solicita `NOTEBOOKLM_MASTER_TOKEN_JSON` (`sync: false`): introducir el JSON completo del archivo anterior en el panel seguro.
4. Render genera `NOTEBOOKLM_SERVER_TOKEN` automáticamente: leer su valor en Environment y conservarlo **solo** en los clientes autorizados.
5. Iniciar el despliegue manual. No activar despliegues automáticos.

No hay que ejecutar Docker en Termux: Render construye la imagen desde GitHub.

## 3. Acceso desde Termux / agentes

Configura en la terminal las variables privadas `BASE_URL` y `API_TOKEN` (nunca dentro de código versionado). Para pruebas manuales:

```bash
curl --max-time 120 "$BASE_URL/healthz"

curl --max-time 120 --fail-with-body \
  -H "Authorization: Bearer $API_TOKEN" \
  "$BASE_URL/v1/notebooks"
```

La segunda petición valida realmente la autenticación con Google. `/healthz` **solo verifica que el proceso está vivo**.

Ejemplo de consulta a un cuaderno, tras reemplazar su ID:

```bash
curl --max-time 180 --fail-with-body \
  -X POST "$BASE_URL/v1/notebooks/ID_DEL_CUADERNO/chat" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"Resume los requisitos técnicos y cita las fuentes."}'
```

## 4. Protocolo de despertar bajo demanda

Render Free suspende el servicio tras unos 15 minutos sin tráfico público. La siguiente petición despierta el servidor; Render indica que esto tarda aproximadamente un minuto. **No programar ping periódico**.

Instrucción a agentes:

1. Ejecutar GET `/healthz` cuando necesiten NotebookLM, con un tiempo máximo de 120 segundos.
2. Si la petición falla por arranque, repetir **solo GET** de forma acotada (por ejemplo, intervalos de 5 segundos, hasta 120 segundos en total).
3. Ejecutar GET autenticado `/v1/notebooks` para verificar acceso real a Google.
4. Consultar NotebookLM cuando responda; **no repetir automáticamente POST de escrituras o generaciones**, ya que pueden haberse ejecutado aunque haya habido timeout.
5. Ante 401, 429 o 503, informar el fallo y aplicar recuperación limitada. Si falla después del margen total, continuar otras tareas.

El tiempo necesario para **responder una pregunta** es adicional al arranque. Render Free tiene 750 horas de instancia compartidas por workspace al mes; estar suspendido no consume esas horas.

## 5. Advertencias técnicas

- API Google no oficial, susceptible a cambios y límites; el REST del proyecto es experimental.
- La versión en el fork se controla manualmente. Si se actualiza desde upstream, revisar compatibilidad antes de redesplegar.
- Al no haber almacenamiento persistente gratuito, el perfil se reconstituye del secreto de Render en cada inicio.
- El valor `NOTEBOOKLM_SERVER_TOKEN` protege todas las operaciones; compartirlo permite acceder a la información y funciones de la cuenta conectada.
- Probar login, consultas, reinicio, despertar en frío y errores de cuota **antes de depender de este servicio**.
- No publicar la URL como API abierta; no diseñar integraciones multiusuario sobre este servidor REST.

**Estado del proyecto:** archivos de despliegue preparados en GitHub; **Render aún no desplegado, autenticación real pendiente de prueba.**

Referencias: [README de notebooklm-py](https://github.com/teng-lin/notebooklm-py), [API REST](https://github.com/teng-lin/notebooklm-py/blob/main/docs/installation.md#rest-api-server), [Render Free](https://render.com/docs/free), [Blueprints](https://render.com/docs/blueprint-spec).
