"""Queue-aware green extension and early handoff; sets `target_green_duration` for the *next* axis after yellow."""

from __future__ import annotations

from dataclasses import dataclass

from traffic_sim.controllers.base import (
    ControllerAction,
    SimulationObservation,
    TrafficController,
)
from traffic_sim.models import Axis


@dataclass
class DynamicController(TrafficController):
    """Rule-based adaptive timing between `min_green` and `max_green`."""

    base_green: float = 16.0
    min_green: float = 8.0
    max_green: float = 35.0
    queue_advantage_threshold: int = 4
    max_extension: float = 8.0

    _target_green_duration: float = 16.0

    def reset(self) -> None:
        self._target_green_duration = self.base_green

    @property
    def name(self) -> str:
        return "dynamic"

    def choose_action(self, obs: SimulationObservation) -> ControllerAction:
        if obs.is_yellow:
            self._retarget_green_for_next_axis(obs)
            return ControllerAction(
                switch_axis_after_yellow=True,
                target_green_duration=self._target_green_duration,
            )

        current_queue, opposite_queue = self._current_and_opposite(obs)

        if obs.phase_elapsed < self.min_green:
            return ControllerAction(target_green_duration=self._target_green_duration)

        if opposite_queue - current_queue >= self.queue_advantage_threshold:
            return ControllerAction(
                switch_to_yellow=True, target_green_duration=self._target_green_duration
            )

        if obs.phase_elapsed >= self._target_green_duration:
            return ControllerAction(
                switch_to_yellow=True, target_green_duration=self._target_green_duration
            )

        return ControllerAction(target_green_duration=self._target_green_duration)

    def _retarget_green_for_next_axis(self, obs: SimulationObservation) -> None:
        next_axis = Axis.EW if obs.active_axis == Axis.NS else Axis.NS
        next_queue = obs.ew_queue if next_axis == Axis.EW else obs.ns_queue
        other_queue = obs.ns_queue if next_axis == Axis.EW else obs.ew_queue
        queue_delta = max(0, next_queue - other_queue)
        raw_extension = min(self.max_extension, float(queue_delta))
        self._target_green_duration = min(
            self.max_green, max(self.min_green, self.base_green + raw_extension)
        )

    @staticmethod
    def _current_and_opposite(obs: SimulationObservation) -> tuple[int, int]:
        if obs.active_axis == Axis.NS:
            return obs.ns_queue, obs.ew_queue
        return obs.ew_queue, obs.ns_queue
