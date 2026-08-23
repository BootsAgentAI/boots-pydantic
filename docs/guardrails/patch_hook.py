"""Harden the git guardrail PreToolUse hook in ~/.claude/settings.json.

Byte-exact replacement of two regex literals inside the JSON file. Everything
else in the file is untouched -- no JSON round-trip, so formatting, key order,
and unrelated settings are preserved exactly.

Creates a timestamped backup before writing.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"
BACKUP = SETTINGS.with_suffix(".json.bak-2026-08-23-git-hook")

# --- gap 1: intervening flags (e.g. `git -c user.name=X commit`) defeated the
#     adjacency assumption of `git[[:space:]]+commit`.
OLD_COMMIT = r"(^|[[:space:];&|])git[[:space:]]+commit"
NEW_COMMIT = r"(^|[[:space:];&|])git[[:space:]]([^;&|]*[[:space:]])?commit([[:space:]]|$)"

# --- gap 2: `git push -u origin main` put two tokens where the regex allowed one.
# --- gap 3: `git push origin HEAD:main` separates the ref with ':' not a space.
OLD_PUSH = r"git[[:space:]]+push[[:space:]]+\S+[[:space:]]+(main|master)([[:space:];&|]|$)"
NEW_PUSH = r"git[[:space:]][^;&|]*push[^;&|]*[[:space:]:/](main|master)([[:space:];&|]|$)"


def escaped(s: str) -> str:
    """The literal as it appears inside the JSON file (without surrounding quotes)."""
    return json.dumps(s)[1:-1]


def main() -> int:
    raw = SETTINGS.read_text()

    for label, old in (("commit", OLD_COMMIT), ("push", OLD_PUSH)):
        n = raw.count(escaped(old))
        if n != 1:
            print(f"ABORT: expected exactly 1 occurrence of the {label} regex, found {n}.")
            print("The hook is not in the state this patch was written against.")
            return 1

    patched = raw.replace(escaped(OLD_COMMIT), escaped(NEW_COMMIT))
    patched = patched.replace(escaped(OLD_PUSH), escaped(NEW_PUSH))

    # Must still be valid JSON, and the hook must still be a non-empty string.
    parsed = json.loads(patched)
    cmd = parsed["hooks"]["PreToolUse"][1]["hooks"][0]["command"]
    assert isinstance(cmd, str) and len(cmd) > 500, "patched hook looks wrong"

    shutil.copy2(SETTINGS, BACKUP)
    SETTINGS.write_text(patched)

    print(f"backup : {BACKUP}")
    print(f"patched: {SETTINGS}")
    print(f"hook length {len(raw)} -> {len(patched)} bytes (file)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
