# Spec: Learned Flows

ECON turns a natural-language request into a stored, executable flow. Local Hermes compiles **unknown** requests once. After a successful run, ECON remembers the commands and replays them with cheap local matching — no paid API, no LLM on the hot path.

This is the product source of truth. [SPECS.md](../SPECS.md) remains the long architecture note.

## Objective

**User:** a person talking to ECON in plain text (CLI, `POST /api/v1/execute`, or voice STT).

**Job:**

1. Unknown request → local Hermes (Ollama) compiles structured actions → ECON validates and executes.
2. On success → store **templated** steps as a flow and bind **trigger phrases** from the utterance.
3. Next similar phrase → exact / alias / prefix / fuzzy / local n-gram match → execute. `llm_used` is false.

**Examples:**

| First time (Hermes) | Stored flow | Later (no LLM) |
| --- | --- | --- |
| “hermes update the pc” → `topgrade` | intent-only flow, triggers `update` / `update pc` | “update the pc” |
| “find me Dune” → HTTP add to Radarr | one flow with `{query}` | “find me Inception” interpolates Inception |

**Success looks like:** the second request for the same *kind* of action hits a stored flow via matching. Redis cache expiry still works because Postgres knowledge is enough.

## Tech Stack

Unchanged: Django/DRF, PostgreSQL, Redis, local Ollama/Hermes, `subprocess` argv (`shell=False`), HTTP via httpx. Matching stays in-process: normalize, aliases, prefix, `difflib` fuzzy, hash n-gram embeddings. No OpenAI, no sentence-transformers requirement.

## Commands

```bash
python manage.py migrate
python manage.py seed_defaults
econom run "update the pc" --debug
econom run "find me Dune" --debug
pytest tests/test_compiler.py tests/test_normalize.py tests/test_flow_versioning.py tests/test_learned_flows.py tests/test_pipeline.py
ruff check .
```

## Project Structure

```
docs/LEARNED_FLOWS.md   → this spec
core/normalize.py       → wake-word strip + fillers
core/compiler.py        → Hermes proposal → FlowSteps (shell and http)
core/llm/               → proposal schema + Ollama prompt
core/engine.py          → match remainder as {query}; compile LLM steps
core/learning.py        → template helpers, trigger phrases
apps/knowledge/learning.py → persist triggers, reuse same-intent flow
apps/knowledge/tasks.py → learn after successful Hermes execution
```

## Code Style

Trigger phrases are normalized. Command graphs keep `{query}` in argv/extra, never a one-off title:

```python
FlowStep(
    executor="http",
    argv=["http"],
    extra={"url": "http://127.0.0.1:7878/api/v3/movie", "method": "POST",
           "body": {"title": "{query}", "addOptions": {"searchForMovie": True}}},
)
```

Secrets are env refs (`{"$env": "RADARR_API_KEY"}`), never literals in flows or prompts.

## Testing Strategy

- Unit: normalize wake words, `compile_proposal` shell/http, templating, trigger extraction.
- Django: persist reuses the same intent+steps; second `run_execute` skips the LLM; `{query}` interpolates a new title.
- No live Ollama. FakeLLM only.
- Coverage target: the two examples above plus “do not duplicate the flow on a third identical compile”.

## Boundaries

- **Always:** match before Hermes; persist only after success; version a flow when the command graph changes; argv list + `shell=False`; redact secrets.
- **Ask first:** paid/cloud LLM providers, new embedding models, dedicated Radarr/topgrade plugins.
- **Never:** Hermes → `os.system`; rewrite an existing flow body in place; store API keys in nodes, logs, or prompts.

## Success Criteria

- [ ] “update the pc” then “hermes update the pc” → second call `llm_used is false`, argv `["topgrade"]` (or whatever Hermes compiled).
- [ ] “find me Dune” then “find me Inception” → one flow, `{query}` swapped, no LLM on the second call.
- [ ] Learned flow confidence ≥ matching threshold so a cold cache still hits Postgres.
- [ ] Identical command graph does not create a new flow version; only aliases/triggers are attached.

## Open Questions

None for this slice. Plugins for specific apps stay optional accelerators; generic shell/HTTP learning is enough.
