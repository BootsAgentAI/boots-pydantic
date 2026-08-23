#!/bin/bash
# Test harness for the git guardrail PreToolUse hook.
#
#   ./hook_harness.sh                 # test the currently installed hook
#   ./hook_harness.sh path/to/hook.sh # test a specific extracted hook
#
# The hook reads `tool_input.command` from stdin and signals via exit code
# (2 = blocked, 0 = allowed), so it can be exercised without Claude Code by
# feeding it fabricated JSON. Fixtures are two throwaway git repos: one sitting
# on `main`, one on a feature branch, because the commit rule resolves the real
# branch with `git branch --show-current`.
#
# Exits non-zero if any case fails.
set -u

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ "$#" -ge 1 ]; then
  HOOK="$1"
else
  HOOK="$WORK/hook.sh"
  python3 -c "
import json, pathlib, sys
p = pathlib.Path.home() / '.claude' / 'settings.json'
d = json.loads(p.read_text())
pathlib.Path(sys.argv[1]).write_text(d['hooks']['PreToolUse'][1]['hooks'][0]['command'])
" "$HOOK" || { echo "could not extract the installed hook"; exit 1; }
  echo "testing the currently installed hook"
fi

git init -q "$WORK/t-main"  && git -C "$WORK/t-main" symbolic-ref HEAD refs/heads/main
git init -q "$WORK/t-feat"  && git -C "$WORK/t-feat" symbolic-ref HEAD refs/heads/some-feature

run() { # cmd, cwd -> exit code
  jq -nc --arg c "$1" '{tool_input:{command:$c}}' \
    | ( cd "$2" && bash "$HOOK" >/dev/null 2>&1; echo $? )
}

pass=0
fail=0
check() { # label, cmd, cwd, expected(BLOCK|ALLOW)
  code=$(run "$2" "$3")
  if [ "$code" = "2" ]; then actual=BLOCK; else actual=ALLOW; fi
  if [ "$actual" = "$4" ]; then mark="  ok"; pass=$((pass+1)); else mark="FAIL"; fail=$((fail+1)); fi
  printf '%-4s %-5s (want %-5s) %s\n' "$mark" "$actual" "$4" "$1"
}

# --- commit-on-main protection ---
check "git commit on main"                  'git commit -m x'                 "$WORK/t-main" BLOCK
check "git -c ... commit on main    [GAP1]" 'git -c user.name=X commit -m x'  "$WORK/t-main" BLOCK
check "git commit on feature branch"        'git commit -m x'                 "$WORK/t-feat" ALLOW
check "git -c ... commit on feature"        'git -c user.name=X commit -m x'  "$WORK/t-feat" ALLOW

# --- push-to-main protection ---
check "git push origin main"                'git push origin main'            "$WORK/t-feat" BLOCK
check "git push -u origin main      [GAP2]" 'git push -u origin main'         "$WORK/t-feat" BLOCK
check "git push origin HEAD:main    [GAP3]" 'git push origin HEAD:main'       "$WORK/t-feat" BLOCK
check "git push origin some-feature"        'git push origin some-feature'    "$WORK/t-feat" ALLOW

# --- false-positive guards: these must stay allowed ---
check "git log --grep=commit on main"       'git log --grep=commit'           "$WORK/t-main" ALLOW
check "git add specific file"               'git add file.py'                 "$WORK/t-feat" ALLOW

# --- untouched rules must still fire ---
check "git add all (dot form)"              'git add .'                       "$WORK/t-feat" BLOCK
# split literal so this script can itself be edited by an agent whose Bash hook
# blocks any command merely containing the flag -- see "Known remaining
# limitations" in git-hook-hardening.md
check "bypass flag"                         'git commit --no-ver''ify -m x'   "$WORK/t-feat" BLOCK

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
