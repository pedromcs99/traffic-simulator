"""Constant green length per cycle; switches to yellow when `phase_elapsed` exceeds configured green."""

from __future__ import annotations

from dataclasses import dataclass

from traffic_sim.controllers.base import (
    ControllerAction,
    SimulationObservation,
    TrafficController,
)


@dataclass
class FixedTimeController(TrafficController):
    """Ignores queue lengths; timing-only baseline for benchmarks."""

    green_duration: float = 20.0
    min_green: float = 10.0

    def reset(self) -> None:
        return

    @property
    def name(self) -> str:
        return "fixed_time"

    def choose_action(self, obs: SimulationObservation) -> ControllerAction:
        if obs.is_yellow:
            return ControllerAction(switch_axis_after_yellow=True)
        if obs.phase_elapsed >= max(self.green_duration, self.min_green):
            return ControllerAction(switch_to_yellow=True)
        return ControllerAction()
