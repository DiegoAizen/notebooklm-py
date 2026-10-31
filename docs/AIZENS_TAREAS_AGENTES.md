# Aizens Cerebro IA — Tablero de encargos para agentes

**Fecha:** 2026-10-31 · **Estado global:** preparación publicada; API de consultas autenticadas **sin validación E2E**.  
**Motivo de este tablero:** los Issues están desactivados en el fork `DiegoAizen/notebooklm-py`. Este documento sustituye temporalmente al tablero de Issues, sin crear ramas extra ni cambiar ajustes del repositorio.

**Lectura obligatoria:** [guía general](AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md) y [plantilla por proyecto](AIZENS_PLANTILLA_MEMORIA_PROYECTO.md).

## Estado de entregas

| Encargo | Estado inicial | Puede empezar sin credenciales | Bloqueo para completar |
| --- | --- | --- | --- |
| A — Backend y seguridad | SIN INICIAR | Sí, análisis + tests con mocks | Consulta real autenticada y revisión de seguridad |
| B — Memoria y sincronización | SIN INICIAR | Sí, fixtures + diseño | Piloto autorizado con cuaderno y acceso segregado |
| C — Integración para agentes | SIN INICIAR | Sí, cliente con mocks | API real operativa (A) |
| O — Orquestador y QA | SIN INICIAR | Sí, organización y evaluación | Unir A+B+C y piloto E2E |

**No marcar EN CURSO sin agente asignado efectivamente.** Los commits de documentación no ejecutan agentes.

## Encargo A — Backend, seguridad y QA

**Área:** adaptador Python/FastAPI, dependencias y pruebas.  
**No tocar:** infraestructura de otros proyectos, cuadernos reales sin permiso, master token.

**Mensaje listo para asignar:**

> Eres el Agente A de Aizens Cerebro IA. Lee `AGENTS.md`, `docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md`, `app.py`, `requirements.txt`, `VERCEL_SETUP.md` y `docs/android/README.md`. Investiga por qué el despliegue guarda `master_token.json` y utiliza `NotebookLMClient.from_storage(profile="vercel")` con Web predeterminado aunque el token corresponde al backend Android. Verifica extras/dependencias, cómo inicializa `from_storage`, si exige cookies Web y cómo evitar errores en arranque frío. Prepara solución mínima y pruebas con mocks primero; NO uses credenciales reales en código/chat, no des un deploy READY por prueba de consulta. Entrega PR, SHA, pruebas PASS/FAIL y pasos de validación autenticada desde Vercel con cuaderno de prueba. Si necesitas secretos o modificar producción, deja bloqueo explícito para el orquestador.

**Aceptación:** 401 sin Bearer; 503 si falta master; 502 saneado en error Google; tests de autenticación; finalmente GET de cuadernos y POST de pregunta reales con referencias.

## Encargo B — Memoria y sincronización por proyecto

**Área:** archivos canónicos, manifest, sincronización incremental.  
**No tocar:** `app.py` ni credenciales de producción.

**Mensaje listo para asignar:**

> Eres el Agente B de Aizens Cerebro IA. Lee `docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md` y `docs/AIZENS_PLANTILLA_MEMORIA_PROYECTO.md`. Diseña el sistema un cuaderno por proyecto sin mezclar fuentes ni permisos. Crea una implementación inicial con fixtures: detectar cambios por SHA/hash, subir o reemplazar fuentes una sola vez, registrar éxito, error y estado STALE, y preservar procedencia y fecha. GitHub sigue siendo fuente de verdad para estado de código. No conectes a cuadernos reales sin aprobación y no introduzcas nuevos cron/servicios. Entrega PR, pruebas idempotentes, guía de despliegue del sincronizador separada de la API read-only y SHA.

**Aceptación:** actualización repetida no duplica fuentes; fallo parcial no marca sincronización exitosa; cambios nuevos se detectan; cuadernos aislados.

## Encargo C — Cliente de NotebookLM reutilizable

**Área:** adaptador de consumo para agentes; sin cambios sobre API de servidor.

**Mensaje listo para asignar:**

> Eres el Agente C de Aizens Cerebro IA. Lee `docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md`. Construye un cliente de lectura para `GET /v1/notebooks` y `POST /v1/notebooks/{id}/chat` usando token de servidor desde almacén seguro, sin hardcodearlo ni imprimirlo. Configura proyecto/cuaderno de manera explícita; valida que no se crucen proyectos. Proporciona timeouts y errores manejados 401/429/502/503 y devuelve texto, citas, hora y estado ok/stale/unavailable. Empieza con mocks porque el backend real todavía no está validado. Entrega PR, SHA, tests y ejemplo de integración para un agente nuevo.

**Aceptación:** respuesta trazable o fallo transparente; nunca inventa consulta; token no aparece en logs ni interfaz.

## Encargo O — Orquestador, piloto y aceptación final

**Área:** revisar PR y pruebas, planificar integración, preparar piloto privado.

**Mensaje listo para asignar:**

> Eres el Orquestador de Aizens Cerebro IA. Lee `docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md`, `docs/AIZENS_PLANTILLA_MEMORIA_PROYECTO.md` y este tablero. Coordina agentes A/B/C sin solapar archivos ni dar tareas por terminadas sin evidencias. Primero audita que el Agente A pueda autenticar y consultar con referencias desde Vercel; revisa seguridad. Después prepara un piloto de memoria en un repositorio privado autorizado (Ruti Ecuador es una propuesta, no una publicación automática), y prueba el ciclo: commit en GitHub → sincronización verificada en cuaderno → consulta con referencias → nuevo agente recupera contexto. Reporta SHA, pruebas PASS/FAIL y cualquier aprobación pendiente; NO copies material privado a este repo público.

**Aceptación:** consulta real autenticada, memoria por proyecto, sync confirmada sin duplicados y recuperación de contexto por agente en otra sesión.

## Cómo actualizar este tablero

Al asignar: cambiar `SIN INICIAR` por `EN CURSO — rol — fecha`.  
Al entregar: registrar rama/PR/SHA, comandos y resultado de tests, evidencia real, riesgos y siguiente responsable.  
No actualizar una tarea por una descripción verbal de progreso: comprobar código y pruebas.  
Las tareas B y C pueden comenzar con fixtures **sin esperar por A**. La integración real depende de A.

## Puertas finales

- [ ] Servidor remoto protegido con consulta E2E autenticada a cuaderno de prueba.
- [ ] Contratos y tests de errores completos.
- [ ] Plantillas y manifest usados en proyecto piloto autorizado.
- [ ] Sync idempotente probada con fuente nueva y actualizada.
- [ ] Cliente de agente funcionando con citas y señal STALE.
- [ ] Relevo completo por un agente recién incorporado.
- [ ] Revisión de seguridad: sin secretos ni documentos privados en el fork público.
