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

### Running without a credentials file

In CI, a container, or any deployed environment there is no `.logfire/`, so the
SDK falls back to the `LOGFIRE_TOKEN` environment variable.

**Nothing loads a `.env` file automatically.** Not the application, and not
`uv run uvicorn app.main:app`. Copying `.env.example` to `.env` and starting the
server normally leaves `LOGFIRE_TOKEN` unset — and because
`send_to_logfire="if-token-present"` degrades quietly rather than raising, the
service looks healthy while sending nothing. Set the variable explicitly:

```bash
# Preferred in CI and containers — inject the variable directly
LOGFIRE_TOKEN="$LOGFIRE_TOKEN" uv run uvicorn app.main:app --port 8000
```

```bash
# Only if you keep a local .env — uvicorn must be told to read it
uv run uvicorn app.main:app --port 8000 --env-file .env
```

To confirm which mode you are in, check the startup line. Exporting to Logfire
prints the project URL; local-only mode does not.

## Test

```bash
uv run pytest
```

Tests pass with no credentials, no network, and no browser auth. That is a
requirement, not a coincidence: telemetry failure must never become
availability failure. `send_to_logfire="if-token-present"` in
`app/telemetry.py` is what enforces it.
