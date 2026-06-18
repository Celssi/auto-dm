"""Terminal progress reporting for long-running ingest/OCR steps."""

from __future__ import annotations

import sys
import time


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


class ProgressReporter:
    """In-place progress line for TTY; line-per-update when stdout is piped."""

    def __init__(self, *, min_interval: float = 2.0, prefix: str = "    ") -> None:
        self._min_interval = min_interval
        self._prefix = prefix
        self._label = ""
        self._total: int | None = None
        self._start: float | None = None
        self._last_emit = 0.0
        self._active = False

    def begin(self, label: str, *, total: int | None = None) -> None:
        self._label = label
        self._total = total
        self._start = time.monotonic()
        self._last_emit = 0.0
        self._active = True

    def update(
        self,
        current: int,
        total: int | None = None,
        *,
        detail: str | None = None,
        force: bool = False,
    ) -> None:
        if not self._active:
            return

        total = total or self._total
        if total is None:
            return

        now = time.monotonic()
        is_final = current >= total
        if not force and not is_final and now - self._last_emit < self._min_interval:
            return

        self._last_emit = now
        elapsed = now - (self._start or now)
        pct = 100.0 * current / total if total else 0.0

        parts = [f"{self._label}: {current}/{total} ({pct:.1f}%)"]
        if detail:
            parts.append(detail)
        parts.append(f"elapsed {format_duration(elapsed)}")
        if current > 0 and current < total:
            rate = elapsed / current
            parts.append(f"ETA {format_duration(rate * (total - current))}")

        line = self._prefix + " | ".join(parts)
        if sys.stdout.isatty():
            sys.stdout.write(f"\r{line:<100}")
            sys.stdout.flush()
        else:
            print(line, flush=True)

    def finish(self, *, message: str | None = None) -> None:
        if self._active and sys.stdout.isatty():
            sys.stdout.write("\n")
            sys.stdout.flush()
        self._active = False
        if message:
            print(f"{self._prefix}{message}", flush=True)


def ocr_progress_callback(label: str, *, min_interval: float = 2.0):
    """Build a (current, total) callback with automatic begin/finish."""
    reporter = ProgressReporter(min_interval=min_interval)
    started = False

    def _callback(current: int, total: int) -> None:
        nonlocal started
        if not started:
            reporter.begin(label, total=total)
            started = True
        reporter.update(current, total, detail=f"page {current}", force=current >= total)
        if current >= total:
            reporter.finish()

    return _callback
