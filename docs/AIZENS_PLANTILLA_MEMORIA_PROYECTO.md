# Plantilla de memoria — un proyecto por cuaderno

**Uso:** copiar al **repositorio propio** del proyecto, en ubicación aprobada por su propietario. NO copiar información privada a este fork público.

## Ficha `docs/estado/00_RESUMEN.md`

```md
# Proyecto: <slug / nombre>
Última revisión: <YYYY-MM-DDTHH:mmTZ>
Objetivo del producto:
Alcance / fuera de alcance:
Repositorios (visibilidad):
Ramas principales:
Responsables / roles:
Cuaderno NotebookLM: <ID guardado en configuración privada, NO en docs públicos>
Documentación canónica:
```

## Estado `docs/estado/02_ESTADO_ACTUAL.md`

```md
# Estado técnico
Última verificación real: <fecha>
Repositorio: <enlace>
Rama: <rama>
HEAD SHA: <SHA real>
Despliegue: <url de panel si autorizado> / <READY, ERROR, no comprobado>
Componentes terminados: <evidencia: PR, archivo, test>
Componentes en curso: <issue, responsable>
Bloqueos y riesgos: <issue / pasos de reproducción>
Diferencias respecto a la memoria NotebookLM: <ninguna / stale / por revisar>
Próximo cambio recomendado: <una tarea concreta>
```

## Relevo `docs/estado/06_RELEVO_AGENTES.md`

```md
# Relevo verificable
Fecha/hora y zona:
Agente / rol:
Tarea y issue:
Rama:
SHA inicial -> SHA final:
Archivos tocados:
Qué funciona (pruebas, logs redactados, PASS):
Qué no funciona (FAIL, pendientes):
Cambios en API/DB / compatibilidad:
Seguridad y secretos: <sin secretos> / <incidente escalado en privado>
PR / enlace:
Próximo responsable y siguiente paso:
Fuentes revisadas (GitHub, docs, NotebookLM):
Fecha de consulta de NotebookLM y sincronización conocida:
```

## Manifest de sincronización (ejemplo FICTICIO, formato recomendado)

```json
{
  "project_slug": "proyecto-demo",
  "repo": "owner/repo",
  "branch": "main",
  "head_sha": "<40-char-sha>",
  "sources": [
    {
      "path": "docs/estado/02_ESTADO_ACTUAL.md",
      "sha256": "<sha256-de-contenido>",
      "source_id": "<id-privado>",
      "synced_at": null,
      "status": "pending"
    }
  ],
  "last_successful_sync": null
}
```

**Almacenamiento:** el manifest real, especialmente `source_id` y `notebook_id`, reside bajo el control de acceso del proyecto; no en una web pública. Separar versión de GitHub de versión confirmada en NotebookLM. Actualizar `last_successful_sync` únicamente tras comprobar la operación.

## Flujo mínimo por agente

1. Leer el estado y relevo de su proyecto y la [guía general](AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md).
2. Verificar **en vivo** rama, HEAD, issues, PR y tests del proyecto.
3. Consultar el cuaderno asignado si es necesario; exigir citas.
4. Si el cuaderno contradice GitHub: anotar `STALE`, continuar con evidencia original, solicitar sincronización.
5. Aplicar cambio completo (backend + interfaz + pruebas cuando corresponda) dentro de sus permisos.
6. Registrar resultado, SHA, pruebas y siguiente tarea en el relevo.
7. Preparar la sincronización sin subir secretos o datos sensibles.

### Ejemplo de pregunta

> Sobre el proyecto <slug>, resume arquitectura, últimas decisiones, tareas pendientes por issue y problemas sin resolver. Da referencias de las fuentes y su fecha. Separa lo confirmado de lo desactualizado.

### Criterio de aceptación de una memoria

- Responde con citas concretas y puede señalar el SHA documentado.
- El SHA actual de GitHub se verifica por separado; si cambió, se detecta obsolescencia.
- No revela datos de otro proyecto ni credenciales.
- Un agente nuevo puede retomar una tarea con instrucciones reproducibles.
