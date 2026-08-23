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
