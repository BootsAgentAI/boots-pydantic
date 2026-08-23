# Action Items

Prioritized, persistent queue. Every open item has an owner, exact steps, and a
definition of done, so the answer is always **"done"**, **"stuck at step N"**, or
**"not started"** — never "what did that mean again?"

`docs/pitfalls.md` is reference material. **This file is the action queue.**
Recommendations made in chat get logged here or they do not count.

## Status vocabulary

| Status | Meaning |
|---|---|
| `TODO` | Not started |
| `DOING` | In progress |
| `BLOCKED` | Waiting on something named in the item |
| `DONE` | Complete, with evidence recorded |
| `WONTDO` | Deliberately declined, with the reason recorded |

## Priority

| Level | Meaning |
|---|---|
| `P0` | Blocks work happening right now |
| `P1` | Blocks the next slice |
| `P2` | Should happen, not blocking |
| `P3` | Nice to have |

---

## Open

| ID | Pri | Owner | Status | Item |
|---|---|---|---|---|
| [AI-001](#ai-001--add-the-logfire-mcp-server) | P1 | Damara | TODO | Add the Logfire MCP server |
| [AI-002](#ai-002--merge-pr-1) | P1 | Damara | TODO | Merge PR #1 |
| [AI-003](#ai-003--close-the-two-git-hook-regex-gaps) | P1 | Agent | BLOCKED | Close the two git-hook regex gaps — needs your approval |
| [AI-004](#ai-004--decide-llm-content-capture-policy) | P1 | Damara | TODO | Decide LLM content-capture policy — gate for slice 1 |
| [AI-005](#ai-005--wire-logfire_token-as-a-github-actions-secret) | P2 | Damara | TODO | Wire `LOGFIRE_TOKEN` as a GitHub Actions secret |
| [AI-006](#ai-006--suppress-test-run-spans-if-they-become-noise) | P3 | Agent | TODO | Suppress test-run spans if they become noise |

---

### AI-001 · Add the Logfire MCP server

**Priority** P1 · **Owner** Damara · **Status** TODO
**Blocks:** programmatic verification in slice 1. Without it, every "did the data
arrive?" check is you looking at the Live view by hand.

**Why:** The evaluation harness in slice 1 needs to query traces directly —
token counts, latencies, error rates — rather than screenshotting them. That is
the difference between an eval harness and a dashboard.

**Steps**

1. In a terminal **outside this Claude session** (config is only read at session
   start, so running it here changes nothing until you restart):

   ```bash
   claude mcp add logfire --transport http https://logfire-us.pydantic.dev/mcp
   ```

2. Start a new Claude Code session in this repo.
3. Run `/mcp` and complete the OAuth flow in the browser.

**Ignore** the "API KEY AUTHENTICATION" JSON block on the Logfire MCP page. That
path is for sandboxed environments with no browser. You have a browser, and it
would mean minting and storing another credential for no benefit.

**Done when:** `/mcp` lists `logfire` as connected, and a query against
`boots/starter-project` returns the `logfire-sandbox` spans.

**If stuck:** If OAuth fails, confirm you are signed into the same Logfire
account (`boots`) that `uvx logfire whoami` reports.

---

### AI-002 · Merge PR #1

**Priority** P1 · **Owner** Damara · **Status** TODO

**Why:** Slice 1 branches from `main`. Leaving slice 0 unmerged means slice 1
either branches from a feature branch or duplicates its work.

**Steps**

1. Review https://github.com/BootsAgentAI/boots-pydantic/pull/1
2. Merge it.

Self-approval here is not peer review and should not be treated as one. The PR's
value is the durable record and the place CI attaches at slice 5.

**Done when:** PR #1 is merged and `main` contains `app/telemetry.py`.

---

### AI-003 · Close the two git-hook regex gaps

**Priority** P1 · **Owner** Agent · **Status** BLOCKED — awaiting your approval

**Why:** The hook matches command *text* assuming adjacent tokens, so an
intervening flag defeats it. This is not theoretical: commit `2da462d` reached
`main` through gap 1 accidentally during this session.

| Blocked as intended | Slips through | Cause |
|---|---|---|
| `git commit` on `main` | `git -c user.name=X commit` | `-c` flags break `git[[:space:]]+commit` adjacency |
| `git push origin main` | `git push -u origin main` | Regex allows exactly one token between `push` and `main` |

**What needs changing:** `~/.claude/settings.json`,
`hooks.PreToolUse[1].hooks[0].command` — the ~1014-character Bash guardrail.

Two regexes get loosened so any number of intervening flags still match:

- commit: `git[[:space:]]+commit` → `git[[:space:]]([^;&|]*[[:space:]])?commit([[:space:]]|$)`
- push: `git[[:space:]]+push[[:space:]]+\S+[[:space:]]+(main|master)` → `git[[:space:]][^;&|]*push[^;&|]*[[:space:]](main|master)`

Loosening is safe because the hook already resolves real state with
`git branch --show-current`. A false positive just tells you to branch first,
which is nearly always the right advice anyway.

**Steps**

1. You reply "approved" (or edit the proposal above).
2. Agent patches `~/.claude/settings.json` surgically via a script — you do not
   hand-edit a 1000-character shell string.
3. Agent verifies by attempting `git -c user.name=X commit` on `main` and
   confirming it is now blocked.

**Blast radius:** this is your **global** config, affecting every project, not
just this repo. That is exactly why it needs your explicit yes.

**Done when:** both gap commands are blocked on `main`, and normal commits on a
feature branch still succeed.

---

### AI-004 · Decide LLM content-capture policy

**Priority** P1 · **Owner** Damara · **Status** TODO — decision due before slice 1 code

**Why:** Slice 1 introduces real model calls. Logfire can capture prompts,
responses, and tool arguments, which is enormously useful for evaluation and is
also the exact place sensitive data leaks into telemetry.

**Not asking for approval yet, deliberately.** Slice 0 makes no model calls, so
there is nothing to capture and an approval now would be approval of nothing. The
original setup brief says to offer this once first data arrives — first data has
arrived, but it is HTTP spans, not prompts.

**The choice, when we get there:**

| Option | Trade-off |
|---|---|
| Content off | Timing, token counts, error rates, cost — all still visible. Cannot see *what* the model was asked or said. |
| Content on | Full prompt/response/tool-argument visibility, which is what makes evals debuggable. Anything sensitive in a prompt lands in Logfire. |

**Default if you say nothing:** content **off**, per the setup brief. Slice 1
proceeds either way; only the span attributes differ.

**Done when:** you have recorded a decision here and it is reflected in
`app/telemetry.py`.

---

### AI-005 · Wire `LOGFIRE_TOKEN` as a GitHub Actions secret

**Priority** P2 · **Owner** Damara · **Status** TODO — not needed until CI exists

**Why:** In CI there is no `.logfire/logfire_credentials.json`, so the SDK falls
back to the `LOGFIRE_TOKEN` environment variable. Documented in `.env.example`.

**Steps**

1. Read the token value out of `.logfire/logfire_credentials.json` yourself. Do
   not paste it into chat.
2. Add it at
   https://github.com/BootsAgentAI/boots-pydantic/settings/secrets/actions
   under the name `LOGFIRE_TOKEN`.

**Done when:** the secret exists. Actually consuming it happens in slice 5.

---

### AI-006 · Suppress test-run spans if they become noise

**Priority** P3 · **Owner** Agent · **Status** TODO — only if it starts bothering you

**Why:** `uv run pytest` exports real spans, because `.logfire/` exists locally.
Right now that is a feature: continuous proof the pipeline works.

**If it becomes noise:** add a pytest fixture setting
`LOGFIRE_SEND_TO_LOGFIRE=false`. **Do not** weaken `configure_telemetry()` — the
production behavior is not the thing that should change to make tests quieter.

**Done when:** either the fixture exists, or this is marked `WONTDO`.

---

## Settled — no action needed

Recorded so the answer to "is this pending or actually configured?" is one lookup
away, with evidence.

| Item | Status | Evidence |
|---|---|---|
| `send_to_logfire="if-token-present"` | **DONE — configured, not pending** | `app/telemetry.py:29`. Enforced by `tests/test_telemetry.py::test_configures_without_credentials_and_preserves_log_handlers`, which runs configure in a temp cwd with `LOGFIRE_TOKEN` stripped and asserts it does not raise. |
| Logfire credentials scoped to the right project | **DONE** | `uvx logfire whoami` → `https://logfire-us.pydantic.dev/boots/starter-project` |
| Write token cannot be committed | **DONE** | `.gitignore:2` covers `.logfire/`, added in the repo's first commit *before* the token was minted. `git check-ignore` confirms. No token string exists anywhere outside `.logfire/`. |
| `.env.example` documents `LOGFIRE_TOKEN` | **DONE** | File exists, 9 lines, `grep -c '^LOGFIRE_TOKEN=$'` returns 1 — key present, value empty |
| Telemetry reaches Logfire | **DONE** | Live view, filtered `service_name = 'logfire-sandbox'`: `GET /health → 200`, `GET /boom → 500` with exception, `fastapi` instrumentation badge |
| System metrics enabled | **DONE** | `logfire.instrument_system_metrics()` in `configure_telemetry()` |
| stdlib logging bridged to Logfire | **DONE** | `LogfireLoggingHandler` attached additively (`addHandler`, never `handlers = [...]`) |
| Slice 0 test suite | **DONE** | `uv run pytest` — 4 passed |
