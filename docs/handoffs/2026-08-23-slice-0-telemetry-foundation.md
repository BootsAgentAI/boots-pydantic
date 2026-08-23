# Handoff — Slice 0: Logfire telemetry foundation

**Date:** 2026-08-23
**Branch:** `slice-0-telemetry-foundation`
**PR:** https://github.com/BootsAgentAI/boots-pydantic/pull/1 (open)
**Outcome:** Complete. Telemetry confirmed arriving in `boots/starter-project`.

Written so the next session can start cold without re-deriving anything.

---

## Read these first, in this order

1. `docs/action-items.md` — what needs doing, who owns it, what "done" means
2. `docs/superpowers/specs/2026-08-23-logfire-observability-foundation-design.md` — Part 1 is the six-slice program map
3. `docs/pitfalls.md` — search by symptom when something breaks
4. This file

Do **not** re-read the slice 0 implementation plan unless changing slice 0. It is
executed and its tasks are closed.

---

## State

| | |
|---|---|
| Repo | `/Users/agentboots/projects/boots/pydantic` → `BootsAgentAI/boots-pydantic` (private) |
| Branch | `slice-0-telemetry-foundation`, synced with origin |
| `main` | 1 commit (the spec), pushed |
| Tests | `uv run pytest` — 4 passed |
| Logfire project | `boots/starter-project` on `https://logfire-us.pydantic.dev` |
| Service name | `logfire-sandbox` |
| Credentials | `.logfire/logfire_credentials.json`, gitignored, verified via `whoami` |
| Python | 3.14.3, managed by `uv` 0.10.8 |

## What shipped

```
app/telemetry.py     configure_telemetry() — the single telemetry policy
app/main.py          FastAPI app, GET /health and GET /boom
tests/test_telemetry.py   credential-independence + idempotency
tests/test_app.py    endpoint behavior
docs/pitfalls.md     running learnings log
docs/action-items.md prioritized action queue
.env.example         documents LOGFIRE_TOKEN for CI
```

Six commits. Notable: `5ade923` swaps the dev dependency `httpx` → `httpx2`
because starlette 1.6.0 deprecated the old TestClient transport.

## Design decisions that should not be silently reversed

**Logfire is the substrate for the evaluation harness, not a sixth competency.**
Spans are the eval data. The harness is built at slice 1 and extended every slice
after, rather than retrofitted at the end — a harness written last only confirms
assumptions already baked in.

**`send_to_logfire="if-token-present"` is a safety requirement.** Missing
credentials degrade to local-only instead of raising. Telemetry failure must
never become availability failure. `tests/test_telemetry.py` enforces it. If that
test fails, fix the code, not the test.

**All telemetry policy lives in `configure_telemetry()`.** Later slices extend
that one function. Do not scatter `logfire.configure()` calls into feature code.

**The logging bridge is additive.** `addHandler`, never `handlers = [...]`.

## Verified facts — do not re-derive

Checked against PyPI on 2026-08-23:

| Package | Version |
|---|---|
| `logfire` | 4.41.0 |
| `pydantic-ai` | 2.33.0 |
| `pydantic-evals` | 2.33.0 |
| `anthropic` | **1.0.0** |
| `fastapi` | 0.141.1 |
| `starlette` | 1.6.0 |
| `httpx2` | 2.12.0 |
| `pytest` | 9.1.1 |

API signatures introspected from the installed `logfire` 4.41.0:

- `logfire.configure(service_name=..., send_to_logfire='if-token-present', advanced=...)`
- `logfire.AdvancedOptions(base_url=...)` — `base_url` is the first parameter
- `logfire.LogfireLoggingHandler` exists
- `logfire.instrument_fastapi(app, *, capture_headers=False, ...)`
- `logfire.instrument_system_metrics(config=None, base='basic')`

`logfire[anthropic]`, `logfire[mcp]`, `logfire[pydantic-ai]` **do not exist.**

## Next: slice 1 — structured output + evaluation harness skeleton

The primary-focus competency. Adds the first real model call producing a
Pydantic-typed structured output, wrapped in `pydantic-evals`, with results
landing in Logfire.

**First three moves, in order:**

1. **Load the `claude-api` skill before writing any SDK code.** `anthropic` is at
   1.0.0 — a major version. Pre-1.0 API knowledge is not trustworthy.
2. **Resolve AI-004** (content-capture policy) — it changes what the spans
   contain.
3. **Write the slice 1 spec** at
   `docs/superpowers/specs/YYYY-MM-DD-slice-1-eval-harness-design.md`. Each slice
   gets its own spec; do not extend the slice 0 spec.

Then plan → branch → implement → verify, same cycle as slice 0.

**Prerequisite worth having first:** AI-001 (Logfire MCP server). Without it,
every "did the eval data land?" check is manual.

## Working agreements confirmed this session

- One logical change per branch and PR. Splice-0 spec sits on `main`; everything
  else came through PR #1.
- Verify every external claim — package version, API signature, extras list —
  with a command before it reaches Damara's screen.
- Never hand Damara a heredoc. Use single-line `printf '%s\n' ...`.
- Protected files (`.env*`, `supabase/migrations/*`, `.github/workflows/*`):
  surface the content and wait. Never route around the hook via Bash.
- Recommendations made in chat get logged in `docs/action-items.md` or they do
  not count.
