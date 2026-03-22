"""World state: lanes as FIFO queues, two-axis lights, vehicles with optional movement intent.

Routing graph for turns is future work; `Movement` is carried on `Vehicle` for extension.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

# Future: routing graph for turns (enter lane -> exit lane edges) — not modeled yet.


class Axis(str, Enum):
    NS = "NS"
    EW = "EW"


class Approach(str, Enum):
    N = "N"
    S = "S"
    E = "E"
    W = "W"


class Movement(str, Enum):
    STRAIGHT = "straight"
    LEFT = "left"
    RIGHT = "right"


class LightState(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True, order=True)
class LaneId:
    """Which approach and which parallel lane (0 = inner-left convention)."""

    approach: Approach
    lane_index: int = 0

@dataclass(frozen=True)
class VehicleType:
    length: int
    width: int


CAR = VehicleType(40, 10)
TRUCK = VehicleType(80, 10)


@dataclass
class Vehicle:
    id: int
    lane_id: LaneId
    movement: Movement = Movement.STRAIGHT
    wait_time: float = 0.0
    vehicle_type: VehicleType = CAR
    @property
    def approach(self) -> Approach:
        return self.lane_id.approach


@dataclass
class Lane:
    lane_id: LaneId
    vehicles: List[Vehicle] = field(default_factory=list)
    passed_count: int = 0

    def enqueue(self, vehicle: Vehicle) -> None:
        self.vehicles.append(vehicle)

    def pop_vehicle(self) -> Vehicle | None:
        if not self.vehicles:
            return None
        self.passed_count += 1
        return self.vehicles.pop(0)

    @property
    def queue_length(self) -> int:
        return len(self.vehicles)

    def increment_wait(self, dt: float) -> None:
        for vehicle in self.vehicles:
            vehicle.wait_time += dt


@dataclass
class TrafficLight:
    """Which axis has priority; yellow applies only to `active_axis` while others are red."""

    active_axis: Axis = Axis.NS
    is_yellow: bool = False

    def state_for_axis(self, axis: Axis) -> LightState:
        if self.is_yellow and axis == self.active_axis:
            return LightState.YELLOW
        if axis == self.active_axis and not self.is_yellow:
            return LightState.GREEN
        return LightState.RED


@dataclass
class Intersection:
    """Lanes keyed by `LaneId`; light state shared. Build via `Intersection.with_lanes`."""

    lanes: Dict[LaneId, Lane]
    light: TrafficLight = field(default_factory=TrafficLight)

    @staticmethod
    def with_lanes(num_lanes_per_approach: int) -> Intersection:
        if num_lanes_per_approach < 1:
            raise ValueError("num_lanes_per_approach must be >= 1")
        lanes: Dict[LaneId, Lane] = {}
        for approach in Approach:
            for lane_index in range(num_lanes_per_approach):
                lid = LaneId(approach, lane_index)
                lanes[lid] = Lane(lane_id=lid)
        return Intersection(lanes=lanes)

    def axis_queue_length(self, axis: Axis) -> int:
        if axis == Axis.NS:
            return sum(self.lanes[lid].queue_length for lid in self.lanes if lid.approach in (Approach.N, Approach.S))
        return sum(self.lanes[lid].queue_length for lid in self.lanes if lid.approach in (Approach.E, Approach.W))

    def queue_lengths(self) -> Dict[str, int]:
        """Per-approach totals (sums parallel lanes) — legacy keys N,S,E,W for metrics/controllers."""
        out: Dict[str, int] = {a.value: 0 for a in Approach}
        for lid, lane in self.lanes.items():
            out[lid.approach.value] += lane.queue_length
        return out

    def aggregate_for_controller(self) -> Tuple[Dict[str, int], int, int]:
        """Same observation shape as before: per-direction counts and axis totals."""
        ql = self.queue_lengths()
        ns_queue = ql["N"] + ql["S"]
        ew_queue = ql["E"] + ql["W"]
        return ql, ns_queue, ew_queue
