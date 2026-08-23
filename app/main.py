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
