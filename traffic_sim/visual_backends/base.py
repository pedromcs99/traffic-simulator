"""Pluggable visualization entry points (pygame now; other surfaces later)."""

from __future__ import annotations

from typing import Protocol


class TrafficVisualizer(Protocol):
    """Runs the interactive window until quit or duration."""

    def run(self, duration_seconds: int | None = None, fps: int = 30) -> None: ...
