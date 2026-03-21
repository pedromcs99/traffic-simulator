"""Screen-space geometry for the intersection (shared by pygame backends)."""

from __future__ import annotations

from traffic_sim.models import Approach, LaneId


# Half-width/height of the paved intersection box in pixels (must match road rects).
INTERSECTION_HALF_PX: int = 120

# Default pixels from center to stop line along an approach (front of queue).
APPROACH_LENGTH_PX: int = INTERSECTION_HALF_PX

LANE_WIDTH_PX: float = 28.0


def lateral_offset_px(lane_index: int, num_lanes_per_approach: int) -> float:
    """Spread parallel lanes around the road centerline (index 0 = west/left of direction)."""
    if num_lanes_per_approach <= 1:
        return 0.0
    mid = (num_lanes_per_approach - 1) / 2.0
    return (lane_index - mid) * LANE_WIDTH_PX


def queue_center_xy(
    lid: LaneId,
    index: int,
    center_x: int,
    center_y: int,
    num_lanes_per_approach: int,
    approach_length_px: int,
    queue_spacing_px: int,
) -> tuple[float, float]:
    """Center of queued vehicle at queue index (0 = at stop line)."""
    gap = float(queue_spacing_px)
    dist = float(approach_length_px) + index * gap
    off = lateral_offset_px(lid.lane_index, num_lanes_per_approach)
    a = lid.approach
    if a == Approach.N:
        return (float(center_x) + off, float(center_y - dist))
    if a == Approach.S:
        return (float(center_x) + off, float(center_y + dist))
    if a == Approach.E:
        return (float(center_x + dist), float(center_y) + off)
    if a == Approach.W:
        return (float(center_x - dist), float(center_y) + off)
    return (float(center_x), float(center_y))


def crossing_endpoints(
    lid: LaneId,
    center_x: int,
    center_y: int,
    num_lanes_per_approach: int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Straight segment across the box, offset by lane (visual only)."""
    h = float(INTERSECTION_HALF_PX)
    off = lateral_offset_px(lid.lane_index, num_lanes_per_approach)
    a = lid.approach
    if a == Approach.N:
        x = float(center_x) + off
        return ((x, float(center_y - h)), (x, float(center_y + h)))
    if a == Approach.S:
        x = float(center_x) + off
        return ((x, float(center_y + h)), (x, float(center_y - h)))
    if a == Approach.E:
        y = float(center_y) + off
        return ((float(center_x + h), y), (float(center_x - h), y))
    if a == Approach.W:
        y = float(center_y) + off
        return ((float(center_x - h), y), (float(center_x + h), y))
    return ((float(center_x), float(center_y)), (float(center_x), float(center_y)))
