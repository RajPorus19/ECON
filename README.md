# ECON

**ECON** (Execution & Cognitive Optimization Network) is a local automation runtime. It turns natural-language commands into deterministic, reusable flows so that Hermes (or another local LLM) is a teacher and fallback — not the hot path.

This repository is the Phase 1 foundation: Django + DRF, a Django-independent core, PostgreSQL, Redis, a host command agent, and an Ollama/Hermes adapter. The web UI (TanStack Start), voice client, and plugin marketplace come later. Until then, Django Admin is the knowledge editor.

Product spec: [SPECS.md](SPECS.md). Stack: [STACK.md](STACK.md).

## Architecture

```
Voice / CLI / HTTP
        │
        ▼
   ECON API (Django/DRF)
        │
        ▼
     ECON Core          ← matcher, security, compiler
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

Hermes never calls the shell. Proposed actions go through a security policy, then an executor that only accepts an argv list (`shell=False`).

## Requirements

- Python 3.12+
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

Apply migrations and seed default intents:

```bash
python manage.py migrate
python manage.py seed_defaults
python manage.py createsuperuser   # optional, for Django Admin
```

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
```

```bash
econom run "echo hello" --debug
# or
curl -s -X POST http://127.0.0.1:8000/api/v1/execute?debug=true \
  -H 'Content-Type: application/json' \
  -d '{"text":"echo hello"}'
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

`econom doctor` from a shell on the host still talks to local ports (8000, 5432, 11434, 8765).

## `econom doctor`

```bash
econom doctor
```

Checks PostgreSQL, Redis, Ollama/Hermes (`GET /api/tags`), and — when `ECON_EXECUTION_MODE=host_agent` — the host agent health endpoint.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Django settings |
| `POSTGRES_*` | `econ` / `127.0.0.1:5432` | Database |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Cache + Celery backend |
| `ECON_LLM_BASE_URL` | `http://127.0.0.1:11434` | Host Ollama. In Compose: `http://host.docker.internal:11434` |
| `ECON_LLM_MODEL` | `hermes` | Model tag already pulled in Ollama |
| `ECON_CONFIDENCE_THRESHOLD` | `0.90` | Below this, ECON calls Hermes |
| `ECON_EXECUTION_MODE` | `local` | `local` or `host_agent` |
| `ECON_HOST_AGENT_URL` | `http://127.0.0.1:8765` | In Compose: `http://host.docker.internal:8765` |
| `ECON_HOST_AGENT_TOKEN` | (required for the agent) | Shared bearer token |
| `ECON_API_URL` | `http://127.0.0.1:8000` | Used by `econom run` |

## Project layout

```
config/          Django project (split settings, ASGI, Celery)
apps/            Django apps: users, knowledge, flows, execution, llm, requests, plugins, analytics
core/            Django-free engine (normalize, match, security, executors, LLM protocol)
host_agent/      Host command daemon
econom/          CLI (`econom start|run|doctor|host-agent`)
tests/
```

## Tests and lint

```bash
pytest
ruff check .
ruff format .
```

## What this phase does not include

TanStack UI, voice/STT, embeddings, Steam/Jellyfin plugins, Redis phrase-cache layers, and Celery learning jobs. Those are later phases in the spec. Django Admin already CRUD-ed entities, intents, flows, actions, executions, and Hermes call logs.

## Security

- Executors pass an argv list to `subprocess.run(..., shell=False)`.
- Destructive patterns (`rm -rf /`, `mkfs`, `dd`, …) are denied.
- Filesystem and shutdown-style actions return `confirm_required` unless `"confirm": true`.
- The host agent requires a bearer token and binds loopback by default.
