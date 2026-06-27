"""Small latency logging helpers."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("uvicorn.error")


def now_ms() -> float:
    return time.perf_counter() * 1000


def elapsed_ms(start_ms: float) -> int:
    return round(now_ms() - start_ms)


def log_latency(event: str, **fields: object) -> None:
    details = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    logger.info("latency.%s %s", event, details)


@contextmanager
def latency_span(event: str, **fields: object) -> Iterator[None]:
    start_ms = now_ms()
    try:
        yield
    finally:
        log_latency(event, elapsed_ms=elapsed_ms(start_ms), **fields)
