"""Replace `choose_action` with a trained policy later; current logic is only so the type checks out."""

from __future__ import annotations

from dataclasses import dataclass

from traffic_sim.controllers.base import ControllerAction, SimulationObservation, TrafficController


@dataclass
class MLController(TrafficController):
    """Stub: not wired in CLI; swap body with model inference when you add RL."""

    min_green: float = 8.0

    def reset(self) -> None:
        return

    @property
    def name(self) -> str:
        return "ml_stub"

    def choose_action(self, obs: SimulationObservation) -> ControllerAction:
        # Stub policy: keep phase until minimum green, then switch every 2 seconds.
        if obs.is_yellow:
            return ControllerAction(switch_axis_after_yellow=True)
        if obs.phase_elapsed < self.min_green:
            return ControllerAction()
        if int(obs.phase_elapsed) % 2 == 0:
            return ControllerAction(switch_to_yellow=True)
        return ControllerAction()
