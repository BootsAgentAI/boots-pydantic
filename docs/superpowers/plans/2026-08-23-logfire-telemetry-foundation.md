# Logfire Telemetry Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Logfire into a minimal FastAPI service and confirm real spans arrive in `boots/starter-project` on logfire-us.

**Architecture:** The repository root is the application. All telemetry policy lives in one module, `app/telemetry.py`, exposing a single idempotent `configure_telemetry()` that runs before the FastAPI app is constructed. Two endpoints exist solely to produce one representative success span and one representative error span. Later slices extend `configure_telemetry()` rather than calling `logfire.configure()` elsewhere.

**Tech Stack:** Python ≥3.10 (local 3.14.3), `uv` 0.10.8, `logfire` 4.41.0, `fastapi` 0.141.1, `uvicorn` 0.52.4, `pytest` 9.1.1, `httpx` 0.28.1.

**Spec:** `docs/superpowers/specs/2026-08-23-logfire-observability-foundation-design.md` (Part 2).

## Global Constraints

Every task's requirements implicitly include this section.

- Target project is `boots/starter-project` on `https://logfire-us.pydantic.dev`. No other project ever receives data.
- Service name is exactly `logfire-sandbox`.
- Base URL is set via `logfire.AdvancedOptions(base_url=...)`. Never hard-code an endpoint anywhere else.
- `send_to_logfire="if-token-present"` is mandatory. Missing credentials must never break imports, tests, or local development.
- The write token is never printed, logged, hard-coded, committed, or pasted into chat. `.logfire/` is already gitignored.
- Tests must pass with no network access, no `.logfire/` directory, and no browser authentication.
- Scrubbing and sampling stay at Logfire defaults. No PII is captured.
- Slice 0 makes no LLM calls and adds no LLM dependency.
- Every version floor below was verified on PyPI on 2026-08-23. Do not substitute remembered versions.

**Deliberate deviation from the spec:** the spec puts every test in `tests/test_app.py`. This plan splits them — `tests/test_telemetry.py` for the credential-independence and idempotency properties, `tests/test_app.py` for endpoint behavior. Both spec requirements are still covered; the split keeps each file to one responsibility, and the telemetry tests outlive slice 0 while the endpoint tests do not.

**Expect test runs to emit spans.** Because `.logfire/` exists in this repo, `uv run pytest` configures a live exporter and sends a small number of spans to `boots/starter-project`. That is acceptable noise in a sandbox and doubles as continuous proof the pipeline works. If it ever becomes unwanted, the fix is a pytest fixture setting `LOGFIRE_SEND_TO_LOGFIRE=false` — do not weaken `configure_telemetry()` itself to achieve it.

**Already done — do not redo:** `git init` on `main`, `.gitignore`, the committed spec, and all three credential steps. `uvx logfire --non-interactive --base-url='https://logfire-us.pydantic.dev' whoami` already reports `https://logfire-us.pydantic.dev/boots/starter-project`.

---

### Task 1: Project scaffold and telemetry module

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/telemetry.py`
- Test: `tests/test_telemetry.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app.telemetry.configure_telemetry() -> None` (idempotent), and module constants `app.telemetry.SERVICE_NAME: str = "logfire-sandbox"` and `app.telemetry.LOGFIRE_BASE_URL: str = "https://logfire-us.pydantic.dev"`. Task 2 imports `configure_telemetry`.

- [ ] **Step 1: Create `pyproject.toml`**

`package = false` tells uv this is an application, not a distributable library, so no build backend is needed. `pythonpath = ["."]` makes `import app` work under pytest without installing anything.

```toml
[project]
name = "logfire-sandbox"
version = "0.1.0"
description = "Reference system for AI observability, evaluation, and retrieval competencies."
requires-python = ">=3.10"
dependencies = [
    "logfire[fastapi,httpx,system-metrics]>=4.41.0",
    "fastapi>=0.141.1",
    "uvicorn[standard]>=0.52.4",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
    "httpx>=0.28.1",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Install dependencies and confirm the lockfile**

```bash
uv sync
```

Expected: creates `.venv/` and `uv.lock`, prints a list of installed packages including `logfire`, `fastapi`, `uvicorn`, `pytest`, `httpx`. Confirm `uv.lock` exists — it is committed; `.venv/` is not.

- [ ] **Step 3: Create the empty package marker**

```bash
mkdir -p app tests && touch app/__init__.py
```

- [ ] **Step 4: Write the failing test**

Both properties are checked in one subprocess because the no-credentials condition cannot be simulated in-process — `configure_telemetry()` sets global state, and the repo's own `.logfire/` directory is discovered relative to the working directory. Running in a temp cwd with `LOGFIRE_TOKEN` stripped is a genuine fresh-clone simulation.

Create `tests/test_telemetry.py`:

```python
"""Telemetry must never be able to break the application."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRESH_CLONE_SCRIPT = """
import logging

sentinel = logging.StreamHandler()
sentinel.name = "sentinel"
logging.getLogger().addHandler(sentinel)

from app.telemetry import configure_telemetry

configure_telemetry()

root = logging.getLogger()
assert sentinel in root.handlers, "configure_telemetry replaced existing log handlers"
print("OK")
"""


def test_configures_without_credentials_and_preserves_log_handlers(tmp_path):
    """A fresh clone has no .logfire/ and no LOGFIRE_TOKEN. That must still work."""
    env = {k: v for k, v in os.environ.items() if k != "LOGFIRE_TOKEN"}
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", FRESH_CLONE_SCRIPT],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "OK" in result.stdout


def test_configure_telemetry_is_idempotent():
    """Repeated calls must not stack duplicate Logfire log handlers."""
    import logfire

    from app.telemetry import configure_telemetry

    def logfire_handler_count() -> int:
        return sum(
            isinstance(h, logfire.LogfireLoggingHandler)
            for h in logging.getLogger().handlers
        )

    configure_telemetry()
    after_first = logfire_handler_count()
    configure_telemetry()
    after_second = logfire_handler_count()

    assert after_first == 1
    assert after_second == 1
```

- [ ] **Step 5: Run the tests to verify they fail**

```bash
uv run pytest tests/test_telemetry.py -v
```

Expected: FAIL. `test_configure_telemetry_is_idempotent` errors with `ModuleNotFoundError: No module named 'app.telemetry'`, and the subprocess test fails its `returncode == 0` assertion with the same error in `stderr`.

- [ ] **Step 6: Write the implementation**

Create `app/telemetry.py`:

```python
"""Telemetry policy for the sandbox.

One module, one function. Every later slice extends `configure_telemetry()`
rather than calling `logfire.configure()` from its own code.
"""

from __future__ import annotations

import logging

import logfire

LOGFIRE_BASE_URL = "https://logfire-us.pydantic.dev"
SERVICE_NAME = "logfire-sandbox"

_configured = False


def configure_telemetry() -> None:
    """Configure Logfire once.

    Safe to call repeatedly. Safe to call with no credentials present:
    `send_to_logfire="if-token-present"` degrades to local-only rather than
    raising, so a missing token can never take the application down.
    """
    global _configured
    if _configured:
        return

    logfire.configure(
        service_name=SERVICE_NAME,
        send_to_logfire="if-token-present",
        advanced=logfire.AdvancedOptions(base_url=LOGFIRE_BASE_URL),
    )
    logfire.instrument_system_metrics()

    # addHandler, never `handlers = [...]`: stdlib logging reaches Logfire
    # in addition to whatever handlers the host application already installed.
    logging.getLogger().addHandler(logfire.LogfireLoggingHandler())

    _configured = True
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
uv run pytest tests/test_telemetry.py -v
```

Expected: PASS, 2 passed.

- [ ] **Step 8: Confirm the token is still unstaged**

```bash
git status --short && git check-ignore -v .logfire/logfire_credentials.json
```

Expected: `.logfire/` appears nowhere in `git status`. `check-ignore` prints `.gitignore:2:.logfire/`.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock app/__init__.py app/telemetry.py tests/test_telemetry.py
git commit -m "$(cat <<'EOF'
feat: add Logfire telemetry configuration module

Single idempotent configure_telemetry() holding all telemetry policy:
service name, logfire-us base URL, system metrics, and an additive
stdlib logging bridge.

send_to_logfire="if-token-present" ensures a missing token degrades to
local-only rather than raising, so telemetry failure can never become
availability failure. Tested by running configure in a temp cwd with
LOGFIRE_TOKEN stripped.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: FastAPI application and endpoints

**Files:**
- Create: `app/main.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `app.telemetry.configure_telemetry()` from Task 1.
- Produces: `app.main.app: FastAPI`. Task 3 runs it via `uvicorn app.main:app`.

- [ ] **Step 1: Write the failing test**

`TestClient` defaults to `raise_server_exceptions=True`, so `/boom` propagates the exception into the test rather than flattening it into a 500. That is deliberate — the test asserts the exception type, which is what Logfire records.

Create `tests/test_app.py`:

```python
"""Endpoint behavior. Each endpoint exists to produce one representative span."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_boom_raises_the_deliberate_failure(client: TestClient):
    with pytest.raises(RuntimeError, match="deliberate sandbox failure"):
        client.get("/boom")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_app.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Write the implementation**

`configure_telemetry()` is called at module import, before `FastAPI()` is constructed and before `instrument_fastapi()` runs. Order matters: instrumentation attaches to an already-configured SDK.

Create `app/main.py`:

```python
"""Sandbox endpoints.

Each endpoint exists to produce exactly one kind of Logfire span, so the
trace in the UI can be traced back to the line that made it.
"""

from __future__ import annotations

import logging

import logfire
from fastapi import FastAPI

from app.telemetry import configure_telemetry

# Must run before the app is constructed and instrumented.
configure_telemetry()

logger = logging.getLogger(__name__)

app = FastAPI(title="logfire-sandbox")
logfire.instrument_fastapi(app)


@app.get("/health")
def health() -> dict[str, str]:
    """The representative success span, plus a stdlib log record."""
    logger.info("health check served")
    return {"status": "ok"}


@app.get("/boom")
def boom() -> dict[str, str]:
    """The representative error span, with stack trace."""
    raise RuntimeError("deliberate sandbox failure")
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_app.py -v
```

Expected: PASS, 2 passed.

- [ ] **Step 5: Run the whole suite**

```bash
uv run pytest -v
```

Expected: PASS, 4 passed. If `test_configures_without_credentials_and_preserves_log_handlers` now fails, the cause is `app/main.py` being imported by the subprocess — it is not; the subprocess imports only `app.telemetry`. Investigate rather than weakening the test.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: add sandbox endpoints for representative Logfire spans

GET /health produces an auto-instrumented success span plus a stdlib log
record exercising the logging bridge. GET /boom produces an error span
with stack trace.

Telemetry is configured at import, before the app is constructed and
instrumented, because instrumentation attaches to a configured SDK.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Documentation and live verification

This task is where the definition of done is actually met. Compilation and green tests are not success; telemetry arriving in `boots/starter-project` is.

**Files:**
- Create: `.env.example`
- Create: `README.md`

**Interfaces:**
- Consumes: `app.main:app` from Task 2.
- Produces: nothing consumed by later tasks in this slice.

- [ ] **Step 1: Create `.env.example`**

Slice 0 does not read this file — the SDK reads `.logfire/logfire_credentials.json` directly for local development. It documents the deployed and CI path, where `LOGFIRE_TOKEN` is the secret to wire.

```bash
# Logfire project write token.
#
# NOT needed for local development: the Logfire SDK reads
# .logfire/logfire_credentials.json automatically, created by
#   uvx logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'boots' 'starter-project'
#
# Needed for CI, containers, and any deployed environment, where no
# credentials file exists. Copy this file to .env and fill it in.
# .env is gitignored. Never commit a real token.
LOGFIRE_TOKEN=
```

- [ ] **Step 2: Create `README.md`**

````markdown
# logfire-sandbox

Reference system for AI observability, evaluation, retrieval, and deployment
competencies. Telemetry goes to `boots/starter-project` on
[logfire-us.pydantic.dev](https://logfire-us.pydantic.dev/boots/starter-project).

Built in slices. See `docs/superpowers/specs/` for the design and the
six-slice decomposition. This is slice 0: the telemetry foundation.

## Setup

```bash
uv sync
```

First-time telemetry credentials (opens a browser):

```bash
uvx logfire --base-url='https://logfire-us.pydantic.dev' auth
uvx logfire --base-url='https://logfire-us.pydantic.dev' projects use --org 'boots' 'starter-project'
uvx logfire --base-url='https://logfire-us.pydantic.dev' whoami
```

`whoami` must print `https://logfire-us.pydantic.dev/boots/starter-project`.
If it prints anything else, stop — do not send data.

This writes a project write token to `.logfire/logfire_credentials.json`,
which is gitignored. Never commit it.

## Run

```bash
uv run uvicorn app.main:app --port 8000
```

| Endpoint | What it demonstrates |
|---|---|
| `GET /health` | An auto-instrumented success span, plus a stdlib log record arriving via `LogfireLoggingHandler` |
| `GET /boom` | An error span with a stack trace |

System metrics export continuously in the background, independent of requests.

## Test

```bash
uv run pytest
```

Tests pass with no credentials, no network, and no browser auth. That is a
requirement, not a coincidence: telemetry failure must never become
availability failure. `send_to_logfire="if-token-present"` in
`app/telemetry.py` is what enforces it.
````

- [ ] **Step 3: Start the server**

```bash
uv run uvicorn app.main:app --port 8000
```

Expected: Logfire prints the project URL it is sending to on startup, then uvicorn prints `Uvicorn running on http://127.0.0.1:8000`. Confirm the printed project URL is `boots/starter-project` before continuing. Leave it running.

- [ ] **Step 4: Trigger both representative operations**

In a second shell:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/boom
```

Expected: `{"status":"ok"}` then `500`. The server log shows the `RuntimeError` traceback. A traceback here is the test passing, not a failure.

- [ ] **Step 5: Stop the server and flush**

Press Ctrl+C. Logfire flushes pending spans on shutdown. Wait for the process to exit cleanly rather than killing it, or the final spans may be lost.

- [ ] **Step 6: Confirm the data arrived**

Open https://logfire-us.pydantic.dev/boots/starter-project and filter the Live view on:

```
service_name = 'logfire-sandbox'
```

Required to be present:
- a span for `GET /health` with status OK
- a log record with the message `health check served`
- a span for `GET /boom` carrying the `RuntimeError` and its stack trace
- system metrics in the Metrics tab

**Note:** no Logfire MCP server is configured in this session, so this check is
visual rather than programmatic. To make it programmatic for later slices, the
MCP server at `https://logfire-us.pydantic.dev/mcp` can be added — worth doing
before slice 1, where the eval harness will want to query traces directly.

If nothing appears: check that `whoami` still resolves to the right project,
that the server printed a project URL at startup rather than a local-only
message, and that the server was stopped cleanly so spans flushed.

- [ ] **Step 7: Commit**

```bash
git add .env.example README.md
git commit -m "$(cat <<'EOF'
docs: add README and LOGFIRE_TOKEN example for the telemetry foundation

Documents the credential flow including the whoami gate that must resolve
to boots/starter-project before any data is sent, and records why tests
must pass without credentials.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Definition of done

Slice 0 is complete when every one of these holds. Item 5 is the one that counts.

1. `uv run pytest` passes — 4 tests.
2. The fresh-clone subprocess test passes with `.logfire/` absent from its working directory.
3. `uvx logfire --non-interactive --base-url='https://logfire-us.pydantic.dev' whoami` reports `boots/starter-project`. *(Already verified 2026-08-23.)*
4. `/health` and `/boom` have each been requested against a running server.
5. Spans with `service_name = 'logfire-sandbox'` — including the `/boom` exception and the `health check served` log record — are confirmed present in `boots/starter-project`.
6. `git status` shows a clean tree and `.logfire/` has never been staged.

A green test suite and a silent exporter are not success.
