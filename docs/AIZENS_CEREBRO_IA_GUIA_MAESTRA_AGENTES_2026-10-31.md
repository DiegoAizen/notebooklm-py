# Aizens Cerebro IA — Guía maestra común para todos los agentes

**Versión:** 1.0 · **Fecha:** 2026-10-31  
**Alcance:** sistema de memoria documental consultable por agentes, aplicable a cualquier proyecto.  
**Repositorio del adaptador:** [DiegoAizen/notebooklm-py](https://github.com/DiegoAizen/notebooklm-py)  
**Servicio Vercel:** `aizens-notebooklm` · **Estado de integración:** API de lectura **validada E2E el 2026-10-31**; sincronización de proyectos y agentes aún pendientes.

> Este documento es una guía general. NO contiene contraseñas, datos privados de proyectos, credenciales ni identificadores de cuadernos reales. Los agentes deben leerlo al incorporarse.

## 1. Objetivo y límites

Mantener **un cuaderno de NotebookLM/Gemini Notebook por proyecto** con fuentes trazables que permitan responder preguntas como:
- ¿Qué producto estamos construyendo y cuáles son sus límites?
- ¿Cuál es la rama, el commit, la arquitectura y el contrato API más reciente?
- ¿Qué decisiones se tomaron, por qué, qué quedó hecho, qué falló y qué sigue?
- ¿Dónde están las pruebas y qué agente tiene la responsabilidad de cada tarea?
- Si un chat desaparece, ¿cómo retomar el trabajo sin inventar contexto?

NotebookLM **no sustituye a GitHub, al código, a los tests ni al orquestador**. La verdad operativa sobre código y tareas es la rama/HEAD real, PR/issues y pruebas; el cuaderno sirve de índice y memoria explicativa **con citas**. Ninguna respuesta debe tomarse como confirmación de un despliegue o estado actual sin verificar la fuente.

## 2. Estado conocido al 31 de octubre de 2026

| Componente | Confirmación | Lo que NO está demostrado |
| --- | --- | --- |
| Termux → Debian → `notebooklm-py` | En la sesión local previa se consultó un cuaderno con respuesta y referencias; el usuario conserva instalación y perfil. | Funcionamiento permanente, reautenticación futura o acceso a todos los cuadernos. |
| GitHub | Fork `DiegoAizen/notebooklm-py` conectado al proyecto Vercel. | Sincronización automática de cada repositorio de producto. |
| Vercel | Producción `READY`, `GET /healthz` 200 y consulta E2E autenticada verificada mediante `scripts/aizens_vercel_smoke.py` el 2026-10-31. | Carga concurrente, tolerancia a fallos de Google, renovación a largo plazo y reintentos. |
| API | `GET /healthz` 200, token inválido 401, `GET /v1/notebooks` autenticado 200 (9 cuadernos), `POST /v1/notebooks/{id}/chat` 200 con respuesta no vacía y 3 referencias (prueba reportada por el propietario el 2026-10-31). | `/healthz` por sí solo NO valida Google; falta revisión de seguridad y test periódico. |
| Memoria compartida | Diseño propuesto en esta guía. | Cuadernos creados por proyecto, cargas y actualizaciones automatizadas. |

**Corrección E2E aplicada:** `app.py` inicializa `storage_state.json` de manera controlada a partir de `master_token.json` antes de llamar al backend Web (`a84ba96`); pruebas adicionales en `f5e2deb`. Tras desplegar, el propietario ejecutó `scripts/aizens_vercel_smoke.py` con resultados PASS en salud, rechazo 401, listado de 9 cuadernos y `POST /chat` con 3 referencias. **Quedan sin validar** resiliencia a largo plazo, concurrencia, límites y revisión completa de seguridad.

**Ubicaciones útiles:** `app.py`, `requirements.txt`, `vercel.json`, `VERCEL_SETUP.md`, `docs/android/README.md`, `src/notebooklm/`.

## 3. Arquitectura aprobada y propuesta

```text
Agente de cualquier proyecto
  ├─ primero: GitHub (HEAD, issues, PR, tests, artefactos) = estado operativo
  ├─ después: API Aizens / NotebookLM = memoria documental con citas
  └─ respuesta: hechos + fuentes + fecha + incertidumbres + siguiente acción

Repositorio de proyecto
  └─ docs/estado/ (archivos Markdown canónicos, sin secretos)
         ↓ proceso de sincronización CONTROLADO (todavía pendiente)
    cuaderno NotebookLM por proyecto
         ↓ consultas de solo lectura
    API Vercel bajo demanda  ←→  Termux como respaldo local
```

- **Vercel** es una puerta de consulta **solo lectura**: no crear, borrar o cargar fuentes mediante los endpoints actuales.
- **Termux** es entorno alternativo local; no depende del uptime de Vercel.
- **La actualización de fuentes** deberá implementarse como proceso separado y autorizado (local o servicio con credenciales segregadas). Nunca afirmar que GitHub ya se sincroniza.
- **No** usar cron, ping para mantener despierto, GitHub Actions, tareas perpetuas ni nuevos servicios de pago sin autorización del propietario.
- La librería opera con APIs **no oficiales**: pueden cambiar, aplicar cuotas o fallar.

## 4. Contrato de memoria por proyecto

Cada proyecto mantendrá archivos versionados en su **propio repositorio privado o público según su política**, por ejemplo:

```text
docs/estado/
  00_RESUMEN.md          # propósito, alcance, producto, enlaces
  01_ARQUITECTURA.md     # componentes, interfaces, decisiones
  02_ESTADO_ACTUAL.md    # ramas, HEAD, módulos, fecha de verificación
  03_PENDIENTES.md       # tareas, bloqueo, prioridades, responsables, issues
  04_DECISIONES.md       # ADR cortos, causas y consecuencias
  05_PRUEBAS.md          # comandos reproducibles, resultados, fecha
  06_RELEVO_AGENTES.md   # instrucciones al nuevo agente
```

No es obligatorio crear todo el primer día: comenzar con `RESUMEN`, `ESTADO_ACTUAL` y `RELEVO_AGENTES` y añadir el resto por necesidad. La plantilla mínima se entregará en un archivo aparte.

**Cada afirmación sobre estado** incluye fecha, repositorio, rama, SHA y enlace al issue/PR/test correspondiente. Diferenciar `confirmado`, `pendiente de prueba`, `propuesta`, `bloqueado`. Los cambios de conversación por sí solos NO actualizan el estado.

Para cada proyecto se registrará un mapeo **privado**, fuera de GitHub público: `project_slug → notebook_id → conjunto de fuentes → última sincronización exitosa`. No mezclar proyectos en un mismo cuaderno por comodidad ni permitir que un agente vea proyectos para los que carece de autorización.

## 5. Cómo consulta un agente

### 5.1 Protocolo obligatorio antes de trabajar

1. Identificar proyecto, rol, tarea y permisos; leer `AGENTS.md`, guías y últimas instrucciones del proyecto.
2. Consultar GitHub para HEAD de la rama, issues/PR abiertos, tests y estado de despliegue si es relevante.
3. Consultar NotebookLM **solo sobre ese proyecto** cuando falte contexto histórico o documental.
4. Exigir respuesta con fuente y fecha; comparar lo recibido con GitHub. Si hay desacuerdo, prevalece la evidencia actual y se marca la memoria como desactualizada.
5. Ejecutar solo trabajo autorizado en el repositorio y rama propios; probar cambios completos, no solo el botón o UI.
6. Al terminar, producir relevo: resumen, cambios, SHA, pruebas PASS/FAIL, riesgos y siguiente tarea; preparar actualización documental.

### 5.2 Consulta remota: contrato previsto (no afirmar que está validado)

`GET /healthz` — salud del proceso; **no** autentica con Google.  
`GET /v1/notebooks` — lista de cuadernos, encabezado `Authorization: Bearer <TOKEN_DE_SERVIDOR>`.  
`POST /v1/notebooks/{notebook_id}/chat` — JSON: `{"question":"..."}`, autenticado con el mismo Bearer.

Ejemplo con placeholders (no insertar token real en el repositorio):

```bash
API_BASE="https://aizens-notebooklm.vercel.app"
# API_TOKEN llega de un almacén secreto del agente; nunca se imprime
curl --fail-with-body -sS "$API_BASE/healthz"
curl --fail-with-body -sS -H "Authorization: Bearer $API_TOKEN" "$API_BASE/v1/notebooks"
curl --fail-with-body -sS -X POST \
  -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"¿Qué decisiones están documentadas y qué queda pendiente? Incluye fuentes."}' \
  "$API_BASE/v1/notebooks/ID_PRIVADO/chat"
```

**Antes de operar** confirmar que el dominio es accesible para el cliente autorizado; Vercel puede proteger despliegues con autenticación de plataforma. Las llamadas pueden devolver `401` por Bearer inválido, `503` por credenciales Google no configuradas, `502` si falla NotebookLM, además de errores de protección, tiempo y cuotas.

No introducir token en prompts, logs, issues, capturas, URL query string, frontend, GitHub ni conversaciones. El **master token** solo existe del lado del servidor y no debe distribuirse a los agentes; los clientes solo necesitan su propio acceso protegido a la API.

### 5.3 Respaldo local

En Termux, según la instalación probada previamente:
```bash
proot-distro login debian
source ~/aizens-venv/bin/activate
notebooklm auth check --test
notebooklm list
notebooklm ask -n ID_DEL_CUADERNO "Resume estado, bloqueos y próximos pasos con referencias"
deactivate
exit
```
**Ojo:** si el cuaderno se autentica solo con token maestro Android, comprobar que el CLI usa `--backend android` (o `NOTEBOOKLM_BACKEND=android`); Web sigue siendo el valor predeterminado. Las variantes disponibles dependen de la versión instalada.

No borrar Debian ni el perfil de autenticación hasta validar un reemplazo real.

## 6. Integridad y actualización de memoria (pendiente de implementar)

Al cierre de un PR o hito:
1. Registrar cambio en archivos canónicos con SHA, fecha y test.
2. Validar que no haya secretos, PII, credenciales, logs sensibles ni documentos con acceso restringido fuera de su perímetro.
3. Generar un manifiesto por fuente (`path`, `source_url`, `commit_sha`, `sha256`, `updated_at`, `sync_status`).
4. Actualizar/reemplazar la fuente del cuaderno correspondiente **sin duplicar**. Documentar operación exitosa/fallida.
5. Hacer pregunta de control y cotejar al menos dos hechos con sus fuentes originales.
6. Registrar fecha de sincronización real; si falló, marcar `STALE`. **Nunca confundir actualización de GitHub con actualización de NotebookLM.**

Evitar cargar archivos completos del repositorio indiscriminadamente: priorizar contratos, documentación curada y resúmenes de cambios. Si una fuente no puede citarse o se contradice, el agente la trata como pista, no como hecho.

## 7. Reparto de trabajo entre agentes

**Agente A — Backend y seguridad (primero).**  
Analizar el adaptador Vercel y la compatibilidad del token maestro con el backend Android. Preparar parche mínimo, dependencias y tests automatizados: 401 sin token, `/healthz` sin secretos, 503 sin master, respuesta 502 saneada, sesión válida con cuaderno de prueba, arranque frío, logs sin secretos. No exponer credenciales ni modificar producción a ciegas. Entregar PR, SHA y evidencia.

**Agente B — Memoria y sincronización.**  
Diseñar plantillas `docs/estado`, manifiesto por proyecto, importación incremental y pruebas idempotentes con **fixtures**, sin conectar todavía tokens reales. Añadir criterios de obsolescencia y procedencia. No editar código del Agente A. Entregar PR y demostración de actualización sin duplicados.

**Agente C — Integración para agentes.**  
Construir un cliente seguro reutilizable para lectura de `/v1/notebooks` y `/chat`: configuración por proyecto, timeouts, 401/429/502/503, protección contra mezcla de proyectos, respuestas con citas y modo `unavailable/stale`. Comenzar con mocks, sin copiar tokens a código. Entregar PR y ejemplo reproducible.

**Orquestador — integración y QA final.**  
Mantener issues, asignación de archivos, conflictos y dependencias. Revisar entregas con SHA y pruebas reales antes del merge. Aislar cambios incompatibles y evitar trabajo paralelo sobre mismos archivos. El primer piloto puede ser Ruti Ecuador, pero **sin publicar su documentación privada en este fork público**.

## 8. Definición de listo (gates, no promesas)

- [x] G1: API responde `/healthz` desde el dominio definitivo (`200` comprobado).
- [ ] G2: La API deniega peticiones sin Bearer; no filtra contenido o credenciales.
- [x] G3: Una consulta autenticada a un cuaderno accesible devuelve respuesta con 3 referencias desde Vercel (E2E reportada el 2026-10-31).
- [ ] G4: El backend de credenciales y su renovación sobreviven arranque frío/reinicio.
- [ ] G5: Al menos un proyecto piloto tiene `docs/estado` versionado y cuaderno separado.
- [ ] G6: Prueba de sincronización: GitHub commit nuevo → fuente actualizada → pregunta verificable, sin duplicados.
- [ ] G7: Un agente recién incorporado puede reconstruir el estado, detectar desactualización y producir un relevo probado.
- [ ] G8: Revisión de seguridad completa, sin datos reales ni tokens en repositorios públicos.

**Regla:** el despliegue `READY` solo satisface el estado del build. Ninguna casilla se marca por suposición.

## 9. Mensaje de inicio para cualquier agente (copiar)

> Actúas como agente del proyecto que se te asigne. Lee primero `docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md` del repositorio de infraestructura y el `AGENTS.md` de tu proyecto. Verifica repo/branch/HEAD/issues antes de decidir. Usa NotebookLM solo como memoria documental con citas, nunca como prueba de estado actual. No solicites ni reveles el token maestro; usa un acceso protegido y segregado de la API cuando esté validado. Trabaja únicamente en tu área, deja cambios probados con SHA y documenta bloqueos y pendientes. No declares completo nada que no tenga evidencia.

## 10. Arranque recomendado

**En paralelo desde ahora:** A revisa seguridad, robustez y tests de la API E2E ya funcional; B diseña memoria con fixtures; C integra cliente con mocks y después contra la API validada. El orquestador revisa.  
**Secuencia de integración:** consulta real ya validada; completar seguridad y fiabilidad (A), piloto de memoria y sincronización (B), cliente real y relevo integral (C + QA).

No hay agentes trabajando automáticamente por el hecho de crear este documento o issues; hay que asignarles los encargos en sus sesiones/agentes.
