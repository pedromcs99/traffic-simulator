"""Pluggable traffic-light policies: observations in, actions out (Protocol = structural interface)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol

from traffic_sim.models import Axis


@dataclass
class SimulationObservation:
    """Everything a controller may read for one decision; built fresh each tick in `simulation`."""

    queue_lengths: Dict[str, int]
    ns_queue: int
    ew_queue: int
    active_axis: Axis
    is_yellow: bool
    phase_elapsed: float
    sim_time: float


@dataclass
class ControllerAction:
    """Instructions interpreted by `IntersectionSimulation._apply_controller`."""

    switch_to_yellow: bool = False
    switch_axis_after_yellow: bool = False
    target_green_duration: float | None = None


class TrafficController(Protocol):
    """Implement `reset` + `choose_action`; used wherever a policy is injected."""

    def reset(self) -> None: ...

    def choose_action(self, obs: SimulationObservation) -> ControllerAction: ...

    @property
    def name(self) -> str: ...
