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
