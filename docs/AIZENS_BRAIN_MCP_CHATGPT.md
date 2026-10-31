# Aizens Brain — conexión de ChatGPT al MCP nativo de notebooklm-py

**Repositorio único:** `DiegoAizen/notebooklm-py` (rama `main`).  
**Servidor único:** proyecto Vercel `aizens-notebooklm`.  
**Dirección principal:** `https://aizens-notebooklm.vercel.app/mcp`.  
**Alias para clientes con esquema antiguo almacenado:** `https://aizens-notebooklm.vercel.app/mcp-v2`.  

## Arquitectura confirmada

El paquete original **YA dispone de un servidor FastMCP**:
`src/notebooklm/mcp/server.py` y sus módulos
`src/notebooklm/mcp/tools/`.

**No se implementan herramientas paralelas.** El archivo `app.py` monta
`notebooklm.mcp.create_server()` en Vercel, utilizando la misma cuenta de Google
que la API REST ya probada. `aizens_brain_oauth.py` proporciona solo el inicio
de sesión web ya configurado para ChatGPT y un control de permisos: hace falta
OAuth `brain:read brain:write` para entrar al servidor MCP con acciones de
creación o edición. El token maestro de Google nunca se entrega al agente.

Las rutas `/mcp` y `/mcp-v2` comparten **un único servidor nativo** y la misma
lista de herramientas, no representan dos proyectos de Vercel ni dos memorias.

## Cómo crear y consultar desde ChatGPT

El servidor original proporciona **38 herramientas nativas**. Las relevantes:

| Función nativa | Propósito |
|---|---|
| `notebook_list` | Descubrir todos los cuadernos existentes |
| `notebook_create` | Crear un cuaderno desde el chat |
| `source_add` | Guardar texto (`source_type="text"`) o una URL en un cuaderno |
| `source_list` | Comprobar las fuentes guardadas |
| `chat_ask` | Consultar un cuaderno con sus fuentes |
| `research_start` | Empezar investigación web (`fast` o `deep`) |
| `research_status` | Consultar la investigación por `poll_task_id` |
| `research_import` | Importar fuentes seleccionadas y verificarlas |

El flujo para Ruti es: comprobar primero GitHub y preparar contexto →
`notebook_list` para evitar duplicados → `notebook_create(title="Ruti Ecuador")`
→ `source_add(notebook=..., source_type="text", title=..., text=...)`
→ `source_list` para confirmar que el documento existe →
`chat_ask` para comprobar la recuperación.

La investigación es una operación independiente: `research_start`,
`research_status`, y `research_import` tras revisar los resultados.

**No afirmar que un proyecto está creado hasta que `notebook_list` lo
muestre y `source_list` compruebe la memoria inicial.**

## Complemento personalizado en ChatGPT web

La URL recomendada es
`https://aizens-notebooklm.vercel.app/mcp`. Si ChatGPT mantiene una lista
antigua de cinco o diez herramientas que incluya `brain_list_projects`,
**el conector conserva un contrato obsoleto**, aunque Vercel ya haya cambiado.
Actualiza los esquemas del conector o, si la interfaz no permite actualizarlos,
vuelve a conectar el mismo servidor. `/mcp-v2` es solo un alias de ese mismo
servidor para evitar la caché; no es otro proyecto.

Cuando autorices en la pantalla de Vercel, utiliza la clave privada del
servidor, nunca `NOTEBOOKLM_MASTER_TOKEN_JSON` ni información de Google.
Los permisos OAuth necesarios son `brain:read` y `brain:write`.

## Qué hace y qué no

- Usa la implementación del MCP existente, sin crear funciones de proyecto
  paralelas ni modificar la infraestructura de GitHub/Neon/Render.
- NotebookLM almacena el conocimiento **como fuentes dentro de cuadernos**.
  La memoria se puede crear desde el chat; el contexto no es una variable de Vercel.
- GitHub sigue siendo la verdad para HEAD, ramas, código, Issues y pruebas.
  Los cuadernos son memoria documental, no prueba de despliegues.
- **No existe sincronización automática continua con GitHub** solo por
  instalar el MCP. Requiere un mecanismo separado con permisos y pruebas.
- Algunas herramientas nativas son destructivas y exigen confirmación;
  no eliminarlas o modificarlas sin aprobación explícita.

## QA y estado

El adaptador nativo se ensayó con FastMCP 4.1.0 en sandbox del mismo proyecto
Vercel: MCP `initialize` y `tools/list` respondieron 200, se descubrieron
38 herramientas, se verificaron los alias `/mcp` y `/mcp-v2` y se rechazó
el acceso sin autenticar (401). La API de salud sigue respondiendo 200 tras
instalar el extra `mcp` en el comando de build real de Vercel.

**Aún debe comprobarse desde la conexión actualizada de ChatGPT una creación
REAL de cuaderno y una fuente real en Google NotebookLM.** No considerar ese
paso superado por pruebas con datos simulados.
