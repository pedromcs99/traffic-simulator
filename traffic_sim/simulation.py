"""Discrete-time engine: each `step()` is one tick of length `config.dt` (default 1 simulated second).

Flow per tick: spawn → accumulate wait → controller updates lights → dequeue on green axis → metrics.
See docs/FLOW.md for the full picture.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict

from traffic_sim.controllers.base import SimulationObservation, TrafficController
from traffic_sim.metrics import MetricsCollector
from traffic_sim.models import (
    Approach,
    Axis,
    Intersection,
    LaneId,
    Movement,
    Vehicle,
)


@dataclass
class SimulationConfig:
    """Tunable arrivals, yellow length, dequeue rate, RNG seed, lanes per approach."""

    dt: float = 1.0
    yellow_duration: float = 3.0
    spawn_probabilities: Dict[str, float] | None = None
    pass_rate_per_green_lane: int = 1
    seed: int = 42
    #: Parallel lanes per approach (1 = original single-lane behavior).
    num_lanes_per_approach: int = 1

    def __post_init__(self) -> None:
        if self.spawn_probabilities is None:
            self.spawn_probabilities = {"N": 0.35, "S": 0.35, "E": 0.3, "W": 0.3}
        if self.num_lanes_per_approach < 1:
            raise ValueError("num_lanes_per_approach must be >= 1")


class IntersectionSimulation:
    """Owns RNG, intersection state, metrics, and phase timers; delegates decisions to `controller`.

    `departed_this_step`: vehicles removed by `_move_vehicles` in the last `step()` only—
    for visualization/debugging; headless benchmarks can ignore it.
    """

    def __init__(
        self, controller: TrafficController, config: SimulationConfig | None = None
    ) -> None:
        self.controller = controller
        self.config = config or SimulationConfig()
        self.random = random.Random(self.config.seed)
        self.intersection = Intersection.with_lanes(self.config.num_lanes_per_approach)
        self.metrics = MetricsCollector()
        self.sim_time = 0.0
        self.phase_elapsed = 0.0
        self.yellow_elapsed = 0.0
        self.completed_vehicles = 0
        self._vehicle_counter = 0
        self._active_green_duration = 20.0
        self.departed_this_step: list[tuple[LaneId, Vehicle]] = []
        self.controller.reset()

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.config.seed = seed
        self.random = random.Random(self.config.seed)
        self.intersection = Intersection.with_lanes(self.config.num_lanes_per_approach)
        self.metrics = MetricsCollector()
        self.sim_time = 0.0
        self.phase_elapsed = 0.0
        self.yellow_elapsed = 0.0
        self.completed_vehicles = 0
        self._vehicle_counter = 0
        self._active_green_duration = 20.0
        self.departed_this_step = []
        self.controller.reset()

    def step(self) -> None:
        """Advance simulation by one `dt`. See module docstring for step order."""
        self.departed_this_step = []
        self._spawn_vehicles()
        self._increment_wait_times()
        self._apply_controller()
        self._move_vehicles()
        self.sim_time += self.config.dt
        self.phase_elapsed += self.config.dt
        if self.intersection.light.is_yellow:
            self.yellow_elapsed += self.config.dt
        self._record_metrics()

    def run(self, duration_seconds: int) -> MetricsCollector:
        """Headless-friendly: run `step()` repeatedly and return the same `metrics` instance."""
        ticks = int(duration_seconds / self.config.dt)
        for _ in range(ticks):
            self.step()
        return self.metrics

    def current_observation(self) -> SimulationObservation:
        """Snapshot passed to the controller before actions are applied this tick."""
        ql, ns_queue, ew_queue = self.intersection.aggregate_for_controller()
        return SimulationObservation(
            queue_lengths=ql,
            ns_queue=ns_queue,
            ew_queue=ew_queue,
            active_axis=self.intersection.light.active_axis,
            is_yellow=self.intersection.light.is_yellow,
            phase_elapsed=self.phase_elapsed,
            sim_time=self.sim_time,
        )

    def _spawn_vehicles(self) -> None:
        """Bernoulli trials per approach; lane index chosen uniformly among parallel lanes."""
        assert self.config.spawn_probabilities is not None
        for lane_name, probability in self.config.spawn_probabilities.items():
            if self.random.random() < probability:
                self._vehicle_counter += 1
                approach = Approach(lane_name)
                lane_idx = self.random.randint(
                    0, self.config.num_lanes_per_approach - 1
                )
                lid = LaneId(approach, lane_idx)
                self.intersection.lanes[lid].enqueue(
                    Vehicle(
                        id=self._vehicle_counter,
                        lane_id=lid,
                        movement=Movement.STRAIGHT,
                    )
                )

    def _increment_wait_times(self) -> None:
        for lane in self.intersection.lanes.values():
            lane.increment_wait(self.config.dt)

    def _apply_controller(self) -> None:
        """Apply yellow / axis switch rules from `ControllerAction` (see `controllers/base.py`)."""
        obs = self.current_observation()
        action = self.controller.choose_action(obs)
        if action.target_green_duration is not None:
            self._active_green_duration = action.target_green_duration

        if self.intersection.light.is_yellow:
            if (
                action.switch_axis_after_yellow
                or self.yellow_elapsed >= self.config.yellow_duration
            ):
                self._switch_axis()
            return

        if action.switch_to_yellow:
            self.intersection.light.is_yellow = True
            self.yellow_elapsed = 0.0

    def _switch_axis(self) -> None:
        current = self.intersection.light.active_axis
        self.intersection.light.active_axis = Axis.EW if current == Axis.NS else Axis.NS
        self.intersection.light.is_yellow = False
        self.phase_elapsed = 0.0
        self.yellow_elapsed = 0.0

    def _green_lane_ids(self) -> list[LaneId]:
        if self.intersection.light.active_axis == Axis.NS:
            approaches = (Approach.N, Approach.S)
        else:
            approaches = (Approach.E, Approach.W)
        lids: list[LaneId] = []
        for approach in approaches:
            for lane_index in range(self.config.num_lanes_per_approach):
                lids.append(LaneId(approach, lane_index))
        return lids

    def _move_vehicles(self) -> None:
        """Dequeue from each green lane up to pass_rate (no movement during yellow)."""
        if self.intersection.light.is_yellow:
            return

        for lid in self._green_lane_ids():
            lane = self.intersection.lanes[lid]
            for _ in range(self.config.pass_rate_per_green_lane):
                vehicle = lane.pop_vehicle()
                if vehicle is None:
                    break
                self.departed_this_step.append((lid, vehicle))
                self.completed_vehicles += 1

    def _record_metrics(self) -> None:
        """Store one snapshot for charts/CSV; uses post-move queue state."""
        waits = [
            v.wait_time
            for lane in self.intersection.lanes.values()
            for v in lane.vehicles
        ]
        avg_wait = sum(waits) / len(waits) if waits else 0.0
        max_wait = max(waits) if waits else 0.0
        throughput_per_min = (self.completed_vehicles / max(self.sim_time, 1.0)) * 60.0
        self.metrics.record(
            sim_time=self.sim_time,
            avg_wait_time=avg_wait,
            max_wait_time=max_wait,
            throughput_per_min=throughput_per_min,
            queue_lengths=self.intersection.queue_lengths(),
        )
