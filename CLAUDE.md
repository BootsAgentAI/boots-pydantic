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
