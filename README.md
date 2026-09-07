# ECON

**ECON** (Execution & Cognitive Optimization Network) is a local automation runtime. It turns natural-language commands into deterministic, reusable flows so that Hermes (or another local LLM) is a teacher and fallback — not the hot path.

Product spec: [SPECS.md](SPECS.md). Stack: [STACK.md](STACK.md).

Matching uses Redis cache layers L1–L4, then the database, then Hermes. Learning (confidence, aliases, metrics) runs on Celery, not on the voice/execute hot path. The TanStack Start UI lives in `web/`. Voice capture is a separate `econom-voice` client.

## Architecture

```
Voice / CLI / Web UI
        │
        ▼
   ECON API (Django/DRF + SSE)
        │
        ▼
     ECON Core          ← cache L1–L4, matcher, security, compiler
        │
   ┌────┴─────┐
   ▼          ▼
 Known     Hermes (Ollama on the host)
 flow         │
   │          ▼
   └────► Validator ──► Executor
                            │
                    local subprocess
                            or
                    host agent (when API is in Docker)
```

Hermes never calls the shell. Proposed actions go through a security policy (`AUTO` / `CONFIRM` / `DENY`), then an executor that only accepts an argv list (`shell=False`). Secrets stay in environment variables — never in flows, logs, or LLM prompts. Token savings are **estimated**.

## Requirements

- Python 3.12+
- Node.js 22+ and [pnpm](https://pnpm.io) (web UI)
- Docker (for Postgres/Redis, and optionally the API)
- [Ollama](https://ollama.com) on the **host**, with a Hermes (or compatible) model already pulled
- macOS or Linux

## Setup

```bash
cp .env.example .env
# Python 3.12+ required (Django 6.1)
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Start Postgres and Redis:

```bash
docker compose up postgres redis
```

Apply migrations and seed default intents plus Steam/Jellyfin plugin manifests:

```bash
python manage.py migrate
python manage.py seed_defaults
python manage.py createsuperuser   # optional, for Django Admin
```

YAML defaults live in `econom.yaml`. Environment variables always win.

## Run modes

### Native API (recommended on a Mac desktop)

The API process can launch apps with `subprocess` directly:

```bash
# .env
ECON_EXECUTION_MODE=local
ECON_LLM_BASE_URL=http://127.0.0.1:11434
ECON_LLM_MODEL=hermes

econom start
# Django Admin: http://127.0.0.1:8000/admin/
# Health:       http://127.0.0.1:8000/health
# API:          POST /api/v1/execute
```

```bash
econom run "echo hello" --debug
econom test "Lance Firefox"
econom flows list
econom entities list
econom graph Firefox
econom learn
```

### Frontend (TanStack Start)

```bash
cd web
pnpm install
pnpm dev          # http://localhost:3000  (VITE_ECON_API_URL defaults to http://127.0.0.1:8000)
```

Dashboard, Requests, Knowledge, Graph, Flow editor, Hermes activity, and Optimizations. Live events: `GET /api/v1/events`.

### Voice client (not inside Django)

```bash
uv pip install -e "./voice[voice]"
econom-voice --text "Lance Firefox"
econom-voice                         # VAD → STT → POST /api/v1/execute
```

### Dockerized API + host commands

Docker Desktop runs Linux containers in a VM. Mounting `/` or using `pid: host` cannot launch macOS apps. A small **host agent** runs on the Mac and executes argv over HTTP.

1. Keep Ollama/Hermes running on the host (`http://127.0.0.1:11434`).
2. Start the host agent on the host (not in Docker):

```bash
# .env
ECON_HOST_AGENT_TOKEN=change-me-host-agent-token

econom host-agent
# listens on 127.0.0.1:8765
```

3. Start the stack. Compose points the API at `host.docker.internal` for both Hermes and the agent:

```bash
docker compose up --build
```

`econom doctor` from a shell on the host still talks to local ports (8000, 5432, 11434, 8765). Run the frontend and voice client on the host against `http://127.0.0.1:8000`.

## `econom doctor`

```bash
econom doctor
```

Checks PostgreSQL, Redis, Ollama/Hermes (`GET /api/tags`), STT if present, the shell executor, and the host agent.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Django settings |
| `POSTGRES_*` | `econ` / `127.0.0.1:5432` | Database |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Cache + Celery backend |
| `ECON_LLM_BASE_URL` | `http://127.0.0.1:11434` | Host Ollama. In Compose: `http://host.docker.internal:11434` |
| `ECON_LLM_MODEL` | `hermes` | Model tag already pulled in Ollama |
| `ECON_CONFIDENCE_THRESHOLD` | `0.90` | Below this, ECON calls Hermes |
| `ECON_ALIAS_CONFIRMATIONS` | `3` | Confirmations before automatic aliases |
| `ECON_EXECUTION_MODE` | `local` | `local` or `host_agent` |
| `ECON_HOST_AGENT_URL` | `http://127.0.0.1:8765` | In Compose: `http://host.docker.internal:8765` |
| `ECON_HOST_AGENT_TOKEN` | (required for the agent) | Shared bearer token |
| `ECON_API_URL` | `http://127.0.0.1:8000` | Used by `econom run` and `econom-voice` |
| `ECON_ESTIMATED_BASELINE_TOKENS` | `1200` | Estimated Hermes cost when ECON skips the LLM |
| `JELLYFIN_URL` / `JELLYFIN_API_KEY` | | Jellyfin plugin secrets (env only) |

## Project layout

```
config/          Django project (split settings, ASGI, Celery)
apps/            Django apps: users, knowledge, flows, execution, llm, requests, plugins, analytics
core/            Django-free engine (normalize, match, security, executors, LLM protocol)
host_agent/      Host command daemon
econom/          CLI (`econom start|run|doctor|host-agent|flows|entities|graph|learn|test`)
plugins/         Steam + Jellyfin example plugins
web/             TanStack Start UI
voice/           econom-voice client
tests/
econom.yaml      Defaults (env overrides)
```

## Tests and lint

```bash
pytest
ruff check .
ruff format .
cd web && pnpm test && pnpm build
```

## Security

- Executors pass an argv list to `subprocess.run(..., shell=False)`.
- Destructive patterns (`rm -rf /`, `mkfs`, `dd`, …) are denied.
- Filesystem and shutdown-style actions return `confirm_required` unless `"confirm": true`.
- Learned flows are versioned; definitions are never silently rewritten.
- Plugin credentials are env refs, never stored on flow nodes.
- The host agent requires a bearer token and binds loopback by default.
