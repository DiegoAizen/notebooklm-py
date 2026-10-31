# Repository Guidelines

**Status:** Active
**Last Updated:** 2026-09-07

## Structure & Modules

`src/notebooklm/` contains the async client (`client.py`) and typed exports (`__init__.py`).
- **Internal:** `_*.py` and `_*/` (`_app/`, `_auth/`, `_runtime/`, `_sources.py`, `_artifacts.py`).
- **Adapters & Wire:** `cli/` (Click), `mcp/` (FastMCP), `server/` (FastAPI), `rpc/` (batchexecute RPC facade), `_android/` (gRPC session & codecs).
- **Tests & Data:** `tests/unit/`, `tests/integration/` (VCR), `tests/server/`, `tests/e2e/`, `tests/_guardrails/`, `tests/_fault_server/`, `tests/cassettes/` (`web/`, `android/`). Examples in `examples/`, tools in `scripts/`.

## Development Commands

Canonical contributor install (full guide: [docs/installation.md](docs/installation.md)):

```bash
uv sync --frozen --extra browser --extra dev --extra markdown \
        --extra mcp --extra server --extra impersonate
source .venv/bin/activate
uv run playwright install chromium

uv run pytest
uv run pytest -n auto --dist loadgroup  # faster parallel run
uv run ruff check .
uv run ruff format --check .
uv run mypy src/notebooklm
```

## Conventions & Testing

- **Style:** Python 3.10+, 4 spaces, double quotes, 100-char line limit (Ruff enforced).
- **Naming:** `snake_case` modules and tests (`test_<behavior>.py`). Preserve public/internal split (`_*.py`).
- **Testing:** Unit logic in `tests/unit/`, REST in `tests/server/`, VCR replay in `tests/integration/` (record: `NOTEBOOKLM_VCR_RECORD=1 uv run pytest tests/integration/ -v`), e2e in `tests/e2e/`. 90% coverage gate.
- **Commits/PRs:** Conventional commits (`feat(cli):`, `fix:`, `refactor:`, `style:`). Link issues and report test runs.

## Parallel & Autonomous Agents

- Prefer `--json` output and pass explicit notebook IDs instead of relying on stateful `notebooklm use`.
- Isolate concurrent runs with `NOTEBOOKLM_PROFILE=agent-<id>` (`~/.notebooklm/profiles/<name>/`) or `NOTEBOOKLM_HOME=/tmp/agent-<id>`.
- In headless environments, authenticate with `notebooklm login --browser-cookies <browser>` (requires `pip install "notebooklm-py[cookies]"`).


## Aizens Cerebro IA (fork-specific tasks)

When the request concerns **Aizens Cerebro IA** or its shared NotebookLM memory for agents, **also read** these fork-specific documents before starting:

- [Common guide](docs/AIZENS_CEREBRO_IA_GUIA_MAESTRA_AGENTES_2026-10-31.md): architecture, source of truth, security, read-only API, acceptance gates.
- [Agent assignment board](docs/AIZENS_TAREAS_AGENTES.md): roles A/B/C and orchestrator, exact deliverables, initial status.
- [Per-project memory template](docs/AIZENS_PLANTILLA_MEMORIA_PROYECTO.md): versioned status, handoff and sync manifest.
- [Private MCP for ChatGPT](docs/AIZENS_BRAIN_MCP_CHATGPT.md): remote URL, OAuth connection, tools and security limitations.

**Important:** Vercel deployment READY is not evidence of authenticated NotebookLM access. Consult current GitHub HEAD and actual tests. Never place Google master tokens, API tokens, personal notebook IDs or confidential project material in this public repository. The fork has GitHub Issues disabled; use the assignment document until a supported private tracker is explicitly chosen. The roles listed are tasks to assign, not agents already running.
