# Logfire Observability Foundation

**Date:** 2026-08-23
**Status:** Approved for implementation (slice 0)
**Repo:** `boots/pydantic`

---

## Part 1 — Program context

### Purpose

Build one reference system that develops and demonstrates five competencies:

1. **Advanced prompt & context engineering** — prompt caching, system instructions, structured JSON output.
2. **MCP & tool use** — open-standard interfaces connecting Claude to external data and local environments.
3. **Production data architecture** — RAG over Postgres with pgvector, hybrid keyword-vector retrieval, streaming.
4. **Enterprise infrastructure** — Docker, Kubernetes, AWS, GCP, strict data boundaries.
5. **Evaluation harnesses** — proving AI metrics and safety over time. *Primary focus.*

### Organizing principle

Logfire is not a sixth competency. It is the substrate for competency 5.

An evaluation harness needs a durable, queryable record of every model call — tokens, cost, latency, model version, tool calls, retrieval hits, failures — captured in production rather than only in test runs. That record is Logfire spans. `pydantic-evals` and `logfire` are built by the same team to compose.

Observability therefore comes first, not because it is the most interesting slice, but because every later slice reports into it.

### Decomposition

One spine: a document-grounded agent over corporate records. Each slice adds one competency and one measurable dimension to the harness.

| # | Slice | Competency | New eval dimension |
|---|---|---|---|
| 0 | Telemetry foundation | substrate | spans exist at all |
| 1 | Structured output + eval harness skeleton | 1 (partial), **5 (core)** | correctness vs. typed expectation |
| 2 | Prompt caching, system instructions, cost metrics | **1** | cost and latency per case |
| 3 | Postgres + pgvector, hybrid retrieval | **3** | retrieval precision and recall |
| 4 | MCP server exposing tools and data | **2** | tool-selection accuracy |
| 5 | Docker → Kubernetes → AWS/GCP, data boundaries | **4** | behavior under real deployment |

Each slice gets its own spec, plan, branch, and PR.

### Why the harness is built early

Enterprise AI applications commonly fail when moving from demo to live production data. A harness written last, against a system already believed to work, confirms existing assumptions and has little power to surprise. A harness established at slice 1 and extended at every slice afterward means each new capability arrives with a measurement attached, and regressions have somewhere to appear.

---

## Part 2 — Slice 0 specification

### Goal

Logfire telemetry configured in a minimal Python service, with real spans confirmed to have arrived in `boots/starter-project` on `https://logfire-us.pydantic.dev`.

### Non-goals

No LLM calls. No retrieval. No MCP. No containers. No prompt-content capture. Those belong to later slices. Slice 0 introduces no external API cost and no sensitive data.

### Verified toolchain

Checked against PyPI and the local machine on 2026-08-23:

| Component | Version |
|---|---|
| `uv` | 0.10.8 (`~/.local/bin/uv`) |
| `python3` | 3.14.3 |
| `logfire` | 4.41.0 (requires-python `>=3.10`) |

Confirmed to exist: extras `fastapi`, `httpx`, `system-metrics`, `asyncpg`, `psycopg`, `sqlalchemy`.
Confirmed **not** to exist: `logfire[anthropic]`, `logfire[mcp]`, `logfire[pydantic-ai]`.

Exact resolved versions are pinned by `uv` into `uv.lock`. No version is written from memory.

### Architecture

The repository root is the application. There is no workspace or monorepo, so dependencies belong in the root `pyproject.toml`.

```
pyproject.toml       dependencies and tool config
app/__init__.py
app/telemetry.py     configure_telemetry() — the single telemetry policy
app/main.py          FastAPI app and endpoints
tests/test_app.py    proves the app runs with no credentials
.env.example         documents LOGFIRE_TOKEN
.gitignore           .logfire/, .env, .venv, __pycache__
README.md            run instructions and what to look for in Logfire
```

`telemetry.py` is a separate module with one exported function so the entire telemetry policy is readable on one screen, independent of framework code. Later slices extend this function rather than scattering `logfire.configure` calls.

### Component contracts

**`app/telemetry.py`**

`configure_telemetry() -> None`, made idempotent by a module-level `_configured` flag so repeated imports or an explicit second call cannot double-configure the exporter. It:

- calls `logfire.configure()` with `service_name="logfire-sandbox"`, `send_to_logfire="if-token-present"`, and `advanced=logfire.AdvancedOptions(base_url="https://logfire-us.pydantic.dev")`;
- calls `logfire.instrument_system_metrics()`;
- attaches `logfire.LogfireLoggingHandler()` to the root logger **additively**, leaving existing handlers in place.

The base URL is a module constant, not a literal repeated at call sites. Scrubbing and sampling stay at Logfire defaults.

**`app/main.py`**

Calls `configure_telemetry()` before the FastAPI app is constructed, then `logfire.instrument_fastapi(app)`.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Returns `{"status": "ok"}`. The representative auto-instrumented request span. |
| `GET /boom` | Raises `RuntimeError`. The representative error span with stack trace. |

Two endpoints, deliberately. Manual nested spans are deferred to slice 1, where the model call produces them from real work rather than from simulation.

### Data flow

Request → FastAPI auto-instrumentation opens a span → handler runs → span closes with status and attributes → OTLP export to `logfire-us` under `service.name=logfire-sandbox`. System metrics export on their own interval, independent of requests.

### Credentials

Local development reads `.logfire/logfire_credentials.json` directly. The procedure, in order:

1. `uvx logfire --base-url='https://logfire-us.pydantic.dev' auth` — opens a browser; must be run by the user.
2. `uvx logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'boots' 'starter-project'` — mints the project write token into `.logfire/logfire_credentials.json`.
3. `uvx logfire --base-url='https://logfire-us.pydantic.dev' whoami` — prints the project URL, not the token.

Step 3 is a gate. If the printed URL is not `boots/starter-project` on `logfire-us.pydantic.dev`, implementation stops and asks. If the CLI offers to select from all available projects, that offer is declined. No data is sent to any other project.

The write token is never printed, logged, pasted into chat, hard-coded, or committed. `.logfire/` is gitignored in the repository's first commit, before any credential can exist.

`.env.example` documents `LOGFIRE_TOKEN` for the future deployed and CI paths. Slice 0 does not read it; the SDK uses the credentials file. When CI or deployment is added in slice 5, `LOGFIRE_TOKEN` is the secret name to wire.

### Error handling

`/boom` is the intentional failure path, verifying that exceptions reach Logfire with stack traces.

Separately and more importantly: telemetry failure must never become availability failure. `send_to_logfire="if-token-present"` enforces this structurally — with no credentials present the app imports, serves, and tests cleanly rather than raising at configure time. This is a safety requirement, not a convenience.

### Testing

`tests/test_app.py` uses FastAPI's `TestClient` to exercise both endpoints:

- `/health` returns HTTP 200 with body `{"status": "ok"}`.
- `/boom` is asserted with `pytest.raises(RuntimeError)`, using `TestClient` at its default `raise_server_exceptions=True` so the exception propagates to the test rather than being flattened into a 500 response.

Tests must pass with `.logfire/` absent, with no network access, and with no browser authentication. A failure under those conditions means the safety requirement above was implemented incorrectly, so this test is the guard rather than a formality.

### Definition of done

Slice 0 is complete when all of the following hold:

1. `uv run pytest` passes with `.logfire/` absent.
2. `uv run pytest` passes with credentials present.
3. `uvx logfire ... whoami` reports `boots/starter-project` on `logfire-us.pydantic.dev`.
4. The server runs and `/health` and `/boom` have each been requested at least once.
5. Spans with `service.name=logfire-sandbox`, including the `/boom` exception, are confirmed present in `boots/starter-project` — queried via the Logfire MCP server at `https://logfire-us.pydantic.dev/mcp` if reachable, otherwise confirmed by the user in the Live view.

Successful compilation is not success. A silent exporter is not success. Success is telemetry arriving in the target project.

### Risks and dependencies

| Item | Impact | Handling |
|---|---|---|
| `logfire auth` requires an interactive browser | Blocks steps 2–5 | User runs step 1; agent does not attempt to automate browser auth |
| `anthropic` is at 1.0.0, a major version | Slice 1 only | Load the `claude-api` skill before writing any Anthropic SDK code; do not rely on training data for the 1.x API surface |
| Logfire MCP server may not be reachable or scoped | Verification step 5 | Fall back to user confirmation in the Live view; do not weaken the criterion |

### Out of scope for slice 0

Prompt-content capture, sampling configuration, custom metrics, distributed traces across services, database instrumentation, and containerization. Each arrives with the slice that needs it.
