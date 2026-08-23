# Pitfalls

Running log of things that cost time, surprised us, or would have been guessed
wrong. Append as they happen — each entry is symptom → cause → fix, so it can be
searched by the symptom you're actually staring at.

Newest slice at the bottom.

---

## Toolchain and environment

### `logfire: command not found`

**Symptom:** Running `logfire --base-url=... auth` returns `command not found`,
even though `uv` and `uvx` are on `PATH`.

**Cause:** `logfire` is never installed globally. `uvx` fetches and runs it on
demand, so the `uvx` prefix is the mechanism, not decoration.

**Fix:** Always `uvx logfire ...`. First run downloads ~23 packages, so expect a
few seconds of silence before anything happens.

### Heredocs stall when handed to a human to run

**Symptom:** A `cat > file <<'EOF' ... EOF` block pasted into the terminal leaves
you sitting at a `heredoc>` continuation prompt; the file is never written.

**Cause:** The shell invoked by the `!` prefix does not complete multi-line
heredocs.

**Fix:** Use a single-line `printf` instead:

```bash
printf '%s\n' 'first line' 'second line' > path
```

Heredocs are fine in commands the agent runs directly (git commit messages).
The restriction applies only to commands handed to a person to paste.

### `cat -A` fails on macOS

**Symptom:** `cat: illegal option -- A`.

**Cause:** `-A` is GNU coreutils. macOS ships BSD `cat`.

**Fix:** Use `cat -e` for line endings, or `od -c` when you genuinely need to see
non-printing characters.

### SIGINT to the wrapper does not stop the server

**Symptom:** `kill -INT $(pgrep -f "uvicorn app.main:app" | head -1)` reports
success, but the process keeps running and no shutdown lines appear in the log.

**Cause:** `pgrep -f` matches the zsh wrapper and the `uv run` parent before it
matches the actual server. Killing the wrapper leaves the Python process alive.

**Fix:** Match the real interpreter path:

```bash
pgrep -f "\.venv/bin/uvicorn app\.main:app"
```

This matters more than it looks: **an unclean shutdown means Logfire never
flushes**, so the last spans are silently lost and the telemetry check fails for
a reason that has nothing to do with telemetry. Always confirm
`Application shutdown complete` in the log before concluding data did not arrive.

---

## Dependencies and versions

### Never write a version number from memory

Every version in this repo came from `npm view`, `pip index`, or a PyPI JSON
lookup on the day it was written. Verified 2026-08-23:

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

`anthropic` being at 1.0.0 means pre-1.0 API knowledge is untrustworthy. Load the
`claude-api` skill before writing any Anthropic SDK code.

### Logfire extras that do **not** exist

`logfire[anthropic]`, `logfire[mcp]`, and `logfire[pydantic-ai]` are not real.
Assuming they exist produces a failing install.

The 28 real extras include: `fastapi`, `httpx`, `system-metrics`, `asyncpg`,
`psycopg`, `sqlalchemy`, `celery`, `redis`, `django`, `flask`, `litellm`,
`google-genai`, `dspy`, `aws-lambda`.

Check before installing:

```bash
curl -s https://pypi.org/pypi/logfire/json | \
  python3 -c "import json,sys; print(sorted(json.load(sys.stdin)['info']['provides_extra']))"
```

### starlette 1.6 deprecated the httpx test transport

**Symptom:** `StarletteDeprecationWarning: Using 'httpx' with
'starlette.testclient' is deprecated; install 'httpx2' instead.`

**Fix:** Dev dependency is `httpx2>=2.12.0`, not `httpx`. Only the TestClient
transport changes — the `logfire[httpx]` extra still instruments outbound httpx
clients, which later slices need.

---

## Observability

### Missing credentials must never break the app

`send_to_logfire="if-token-present"` in `app/telemetry.py` is a safety
requirement, not a convenience. Without it, a machine with no credentials raises
at configure time, which turns a telemetry problem into an availability problem.

Guarded by `tests/test_telemetry.py`, which runs `configure_telemetry()` in a
subprocess with a temp working directory and `LOGFIRE_TOKEN` stripped. If that
test ever fails, do not weaken it — it is the guard.

### `uv run pytest` sends real spans

Because `.logfire/` exists locally, the test suite exports to
`boots/starter-project`. Test-run spans appear in Live view alongside real
traffic.

This is acceptable noise in a sandbox and doubles as continuous proof the
pipeline works. If it ever needs suppressing, add a pytest fixture setting
`LOGFIRE_SEND_TO_LOGFIRE=false` — do not change `configure_telemetry()`.

### First request is slow; that is not a regression

Observed on identical `GET /health` calls: **15.0ms** first, **960µs** after.
Cold-path cost, not a performance problem. An evaluation harness has to
distinguish this from a real regression, which is a large part of why the harness
exists.

### "No exporter error" is not proof of delivery

A silent exporter and a green test suite prove nothing about whether data
arrived. Confirm in Live view filtered on `service_name`, or query the Logfire
MCP server. Compilation is not success.

---

## Repo guardrails

### Protected files cannot be written *or* read

`.env*`, `supabase/migrations/*`, and `.github/workflows/*` are blocked for
Write/Edit, and `.env*` is additionally blocked from being read or `cat`-ed.

The block is the design, not an obstacle. The correct response is to surface the
file content in chat with a `printf` one-liner for a human to run, then wait for
confirmation before continuing with dependent work. **Never** materialize it via
Bash to route around the hook.

You can still verify such a file safely without displaying it:

```bash
grep -c '^LOGFIRE_TOKEN=$' .env.example   # confirms the key exists and is empty
```

### The git guardrail hook has two regex gaps

The hook matches command text assuming adjacent tokens, so an intervening flag
defeats it:

| Blocked as intended | Slips through | Why |
|---|---|---|
| `git commit` on `main` | `git -c user.name=X commit` | `-c` flags break `git[[:space:]]+commit` adjacency |
| `git push origin main` | `git push -u origin main` | Regex allows exactly one token between `push` and `main` |

The first gap is not hypothetical — commit `2da462d` reached `main` through it
accidentally.

**Do not use these gaps.** Evading a guardrail on a technicality is equivalent to
disabling it. The durable fix is to match loosely on the command
(`git[[:space:]].*[[:space:]]commit`) and rely on the resolved-state check the
hook already performs.

### Compound commands defeat the branch check

`git checkout -b foo && git commit ...` is blocked, because the hook evaluates
`git branch --show-current` *before* the command runs and still sees `main`.
Split it into two calls.

---

## Process

### Decompose before designing

Five named competencies are five subsystems, not five features. Attempting one
spec across all of them produces a wish list. Each slice gets its own spec, plan,
branch, and PR.

### Verify claims before they reach a human

Package versions, API signatures, and extras all get a verification command and a
citation before being surfaced. `inspect.signature()` against the installed
package beats recalling an API. This is cheap and it is the difference between a
plan that works and a plan that wastes someone's afternoon.
