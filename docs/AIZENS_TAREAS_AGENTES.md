# Aizens Cerebro IA — Tablero de encargos para agentes

**Fecha:** 2026-10-31 · **Estado global:** API de consulta autenticada **E2E validada** (9 cuadernos, POST con respuesta y 3 referencias); agentes, sincronización y seguridad integral pendientes.  
**Motivo de este tablero:** los Issues están desactivados en el fork `DiegoAizen/notebooklm-py`. Este documento sustituye temporalmente al tablero de Issues, sin crear ramas extra ni cambiar ajustes del repositorio.

**Lectura obligatoria:** [guía general](AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md) y [plantilla por proyecto](AIZENS_PLANTILLA_MEMORIA_PROYECTO.md).

## Estado de entregas

| Encargo | Estado inicial | Puede empezar sin credenciales | Bloqueo para completar |
| --- | --- | --- | --- |
| A — Backend y seguridad | SIN INICIAR (infraestructura E2E reparada previamente) | Sí, análisis + tests con mocks | Revisión de seguridad, robustez, pruebas automatizadas y fallos/renovación |
| B — Memoria y sincronización | SIN INICIAR | Sí, fixtures + diseño | Piloto autorizado con cuaderno y acceso segregado |
| C — Integración para agentes | SIN INICIAR | Sí, cliente con mocks | Integración con API ya validada y permisos por proyecto |
| O — Orquestador y QA | SIN INICIAR | Sí, organización y evaluación | Unir A+B+C y piloto E2E |

**No marcar EN CURSO sin agente asignado efectivamente.** Los commits de documentación no ejecutan agentes.

## Encargo A — Backend, seguridad y QA

**Área:** adaptador Python/FastAPI, dependencias y pruebas.  
**No tocar:** infraestructura de otros proyectos, cuadernos reales sin permiso, master token.

**Mensaje listo para asignar:**

> Eres el Agente A de Aizens Cerebro IA. Lee `AGENTS.md`, la guía general, `app.py`, `requirements.txt`, `VERCEL_SETUP.md`, `docs/android/README.md` y `scripts/aizens_vercel_smoke.py`. La API YA pasó E2E en Vercel el 2026-10-31 tras la corrección de bootstrap Web desde master token (`a84ba96`), con 9 cuadernos y 3 referencias en POST. No rehagas la autenticación ni cambies a Android sin evidencia. Revisa robustez, concurrencia, arranque frío, renovación y manejo de fallos; ejecuta tests en entorno controlado, protege secretos, entrega SHA, pruebas PASS/FAIL y riesgos. No necesitas volver a pedir al usuario el token maestro; no modificar producción sin revisión.

**Aceptación:** conservar los PASS E2E conocidos; comprobar 401 sin Bearer, 503 sin master, 502 saneado ante fallos de Google, pruebas automatizadas y protección de secretos. No afirmar tolerancia a reinicios o carga hasta medirla.

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

**Aceptación:** E2E ya demostrada; completar revisión de seguridad, memoria por proyecto, sincronización confirmada sin duplicados y recuperación de contexto por agente en otra sesión.

## Cómo actualizar este tablero

Al asignar: cambiar `SIN INICIAR` por `EN CURSO — rol — fecha`.  
Al entregar: registrar rama/PR/SHA, comandos y resultado de tests, evidencia real, riesgos y siguiente responsable.  
No actualizar una tarea por una descripción verbal de progreso: comprobar código y pruebas.  
Las tareas B y C pueden comenzar con fixtures **sin esperar por A**. La API real ya respondió E2E; cada agente debe verificar sus permisos y pruebas antes de integrarse.

## Puertas finales

- [x] Servidor remoto con consulta E2E autenticada y respuesta con referencias (2026-10-31, prueba manual de propietario).
- [ ] Contratos y tests de errores completos.
- [ ] Plantillas y manifest usados en proyecto piloto autorizado.
- [ ] Sync idempotente probada con fuente nueva y actualizada.
- [ ] Cliente de agente funcionando con citas y señal STALE.
- [ ] Relevo completo por un agente recién incorporado.
- [ ] Revisión de seguridad: sin secretos ni documentos privados en el fork público.
