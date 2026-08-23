"""Telemetry policy for the sandbox.

One module, one function. Every later slice extends `configure_telemetry()`
rather than calling `logfire.configure()` from its own code.
"""

from __future__ import annotations

import logging

import logfire

LOGFIRE_BASE_URL = "https://logfire-us.pydantic.dev"
SERVICE_NAME = "logfire-sandbox"
APP_LOGGER_NAME = "app"

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

    # A fresh root logger sits at WARNING, so this application's own INFO
    # records would be discarded before any handler saw them — making the
    # bridge below a bridge to nowhere. Raise the threshold for this app's
    # package only, leaving third-party loggers at their own defaults so
    # library chatter does not flood Logfire.
    logging.getLogger(APP_LOGGER_NAME).setLevel(logging.INFO)

    # addHandler, never `handlers = [...]`: stdlib logging reaches Logfire
    # in addition to whatever handlers the host application already installed.
    logging.getLogger().addHandler(logfire.LogfireLoggingHandler())

    _configured = True
