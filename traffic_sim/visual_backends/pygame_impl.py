"""Pygame implementations: linear crossing (simple) vs accel/brake (kinematic)."""

from __future__ import annotations
from dataclasses import dataclass
import math

import pygame

from traffic_sim.models import Approach, Axis, LaneId, LightState, Vehicle
from traffic_sim.motion_profiles import advance_trapezoid_speed, linear_advance
from traffic_sim.render_layout import (
    INTERSECTION_HALF_PX,
    crossing_endpoints,
    queue_center_xy,
)
from traffic_sim.simulation import IntersectionSimulation


def _load_ui_font(size: int = 20) -> pygame.font.Font:
    try:
        font = pygame.font.SysFont("Arial", size)
        if font is not None:
            return font
    except Exception:
        pass
    try:
        font = pygame.font.SysFont("Segoe UI", size)
        if font is not None:
            return font
    except Exception:
        pass
    return pygame.font.Font(pygame.font.get_default_font(), size)


def _car_color(vehicle_id: int) -> tuple[int, int, int]:
    r = (vehicle_id * 97) % 200 + 40
    g = (vehicle_id * 53) % 200 + 40
    b = (vehicle_id * 31) % 200 + 40
    return (r, g, b)


@dataclass
class RenderConfig:
    width: int = 900
    height: int = 700
    background_color: tuple[int, int, int] = (30, 30, 30)
    real_seconds_per_sim_second: float = 1.0
    max_sim_steps_per_frame: int = 10
    crossing_duration_seconds: float = 0.65
    approach_length_px: int = INTERSECTION_HALF_PX
    queue_spacing_px: int = 14
    backend: str = "simple"  # "simple" | "kinematic"


@dataclass
class AnimatedCarSimple:
    lane_id: LaneId
    vehicle_id: int
    progress: float = 0.0


@dataclass
class AnimatedCarKinematic:
    lane_id: LaneId
    vehicle: Vehicle
    s: float = 0.0
    v: float = 0.0


class _PygameViewBase:
    """Shared pygame loop, timescale, roads, lights, queues."""

    def __init__(
        self, sim: IntersectionSimulation, config: RenderConfig | None = None
    ) -> None:
        self.sim = sim
        self.config = config or RenderConfig()
        self._sim_time_accumulator: float = 0.0

        pygame.init()
        pygame.display.init()
        self.screen = pygame.display.set_mode((self.config.width, self.config.height))
        pygame.display.set_caption("Traffic Intersection Simulator")
        self.clock = pygame.time.Clock()
        self.font = _load_ui_font(20)

    def run(self, duration_seconds: int | None = None, fps: int = 30) -> None:
        running = True
        self._sim_time_accumulator = 0.0
        self._reset_animation_state()

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            real_dt_ms = self.clock.tick(fps)
            real_dt = real_dt_ms / 1000.0
            if self.config.real_seconds_per_sim_second > 0:
                self._sim_time_accumulator += (
                    real_dt / self.config.real_seconds_per_sim_second
                )
            else:
                self._sim_time_accumulator += real_dt

            steps = 0
            dt = self.sim.config.dt
            while (
                self._sim_time_accumulator >= dt
                and steps < self.config.max_sim_steps_per_frame
            ):
                self.sim.step()
                for lid, vehicle in self.sim.departed_this_step:
                    self._on_departure(lid, vehicle)
                self._sim_time_accumulator -= dt
                steps += 1

            self._tick_animations(real_dt)

            if duration_seconds is not None and self.sim.sim_time >= float(
                duration_seconds
            ):
                running = False

            self._draw_frame()

        pygame.quit()

    def _reset_animation_state(self) -> None:
        raise NotImplementedError

    def _on_departure(self, lid: LaneId, vehicle: Vehicle) -> None:
        raise NotImplementedError

    def _tick_animations(self, real_dt: float) -> None:
        raise NotImplementedError

    def _draw_frame(self) -> None:
        self.screen.fill(self.config.background_color)

        road_width = 0
        center_x = self.config.width // 2
        center_y = self.config.height // 2

        # draw lines
        self._draw_road(center_x, center_y)
        self._draw_road_lines(center_x, center_y)
        self._draw_lights(center_x, center_y, road_width)
        self._draw_queued_cars(center_x, center_y)
        self._draw_crossing_cars(center_x, center_y)
        self._draw_stats()
        pygame.display.flip()

    def _draw_road(self, center_x: int, center_y: int) -> None:
        road_color = (60, 60, 60)
        center_x = self.config.width // 2
        center_y = self.config.height // 2
        pygame.draw.rect(
            self.screen,
            road_color,
            (
                center_x - INTERSECTION_HALF_PX,
                0,
                2 * INTERSECTION_HALF_PX,
                self.config.height,
            ),
        )
        pygame.draw.rect(
            self.screen,
            road_color,
            (
                0,
                center_y - INTERSECTION_HALF_PX,
                self.config.width,
                2 * INTERSECTION_HALF_PX,
            ),
        )

    def _draw_road_lines(self, center_x: int, center_y: int) -> None:
        h = INTERSECTION_HALF_PX
        line_color = (255, 255, 255)
        line_length = 50
        line_height = 20

        horizontal_lane_counter = 0
        vertical_lane_counter = 0

        while vertical_lane_counter < self.config.height:
            pygame.draw.rect(
                self.screen,
                line_color,
                (
                    (self.config.width // 2) - (line_height // 2),
                    0 + vertical_lane_counter,
                    line_height,
                    line_length,
                ),
            )
            vertical_lane_counter += 100

        while horizontal_lane_counter < self.config.width:
            pygame.draw.rect(
                self.screen,
                line_color,
                (
                    0 + horizontal_lane_counter,
                    self.config.height // 2 - (line_height // 2),
                    line_length,
                    line_height,
                ),
            )
            horizontal_lane_counter += 100

    def _draw_lights(self, center_x: int, center_y: int, road_width: int) -> None:
        ns_state = self.sim.intersection.light.state_for_axis(Axis.NS)
        ew_state = self.sim.intersection.light.state_for_axis(Axis.EW)

        def color_for(state: LightState) -> tuple[int, int, int]:
            if state == LightState.GREEN:
                return (0, 180, 0)
            if state == LightState.YELLOW:
                return (240, 200, 0)
            return (180, 0, 0)

        circle_radius = 18
        half_road_plus_diameter = INTERSECTION_HALF_PX + circle_radius
        # vertical lane
        pygame.draw.circle(
            self.screen,
            color_for(ns_state),
            (center_x - half_road_plus_diameter, center_y - (half_road_plus_diameter -circle_radius)),
            circle_radius,0,True,True,False,False
        )
        pygame.draw.circle(
            self.screen,
            color_for(ns_state),
            (center_x + half_road_plus_diameter, center_y + (half_road_plus_diameter - circle_radius)),
            circle_radius,0,False,False,True,True
        )
        # horizontal lane
        pygame.draw.circle(
            self.screen,
            color_for(ew_state),
            (center_x - (half_road_plus_diameter -circle_radius), center_y + half_road_plus_diameter),
            circle_radius,0,False,True,True,False
        )
        pygame.draw.circle(
            self.screen,
            color_for(ew_state),
            (center_x + (half_road_plus_diameter -circle_radius), center_y - half_road_plus_diameter),
            circle_radius,0,True,False,False,True
        )

    def _num_lanes(self) -> int:
        return self.sim.config.num_lanes_per_approach

    def _draw_queued_cars(self, center_x: int, center_y: int) -> None:
        QUEUED_CARS_LANE_OFFSET = 50
        n = self._num_lanes()
        for lid, lane in self.sim.intersection.lanes.items():
            for index, vehicle in enumerate(lane.vehicles):
                cx, cy = queue_center_xy(
                    lid,
                    index,
                    center_x,
                    center_y,
                    n,
                    self.config.approach_length_px + QUEUED_CARS_LANE_OFFSET,
                    self.config.queue_spacing_px,
                )
                color = _car_color(vehicle.id)
                space_between_lanes = 70
                vehicle_type = vehicle.vehicle_type

                if lid.approach in (Approach.N, Approach.S):
                    pygame.draw.rect(
                        self.screen,
                        color,
                        (
                            int(cx - space_between_lanes),
                            int(cy - 5),
                            vehicle_type.length,
                            vehicle_type.width,
                        ),
                    )
                else:
                    pygame.draw.rect(
                        self.screen,
                        color,
                        (
                            int(cx - 5),
                            int(cy - space_between_lanes),
                            vehicle_type.width,
                            vehicle_type.length,
                        ),
                    )

    def _draw_stats(self) -> None:
        summary = self.sim.metrics.final_summary()
        ts = self.config.real_seconds_per_sim_second
        backend = getattr(self.config, "backend", "simple")
        lines = [
            f"Controller: {self.sim.controller.name}",
            f"Visual: {backend}",
            f"Sim time: {self.sim.sim_time:.1f}s  (1 sim s = {ts:g} real s)",
            f"Avg wait: {summary['avg_wait_time']:.2f}s",
            f"Max wait: {summary['max_wait_time']:.2f}s",
            f"Throughput/min: {summary['throughput_per_min']:.1f}",
            "Close window to exit",
        ]
        for idx, text in enumerate(lines):
            surface = self.font.render(text, True, (240, 240, 240))
            self.screen.blit(surface, (20, 20 + idx * 22))


class PygameSimpleVisualizer(_PygameViewBase):
    """Uniform-speed crossing (linear progress in real time)."""

    def __init__(
        self, sim: IntersectionSimulation, config: RenderConfig | None = None
    ) -> None:
        super().__init__(sim, config)
        self._animated: list[AnimatedCarSimple] = []

    def _reset_animation_state(self) -> None:
        self._animated = []

    def _on_departure(self, lid: LaneId, vehicle: Vehicle) -> None:
        self._animated.append(AnimatedCarSimple(lane_id=lid, vehicle_id=vehicle.id))

    def _tick_animations(self, real_dt: float) -> None:
        d = self.config.crossing_duration_seconds
        for car in self._animated:
            car.progress = linear_advance(car.progress, real_dt, d)
        self._animated = [c for c in self._animated if c.progress < 1.0]

    def _draw_crossing_cars(self, center_x: int, center_y: int) -> None:
        n = self._num_lanes()
        for ac in self._animated:
            start, end = crossing_endpoints(ac.lane_id, center_x, center_y, n)
            t = min(1.0, ac.progress)
            cx = start[0] + (end[0] - start[0]) * t
            cy = start[1] + (end[1] - start[1]) * t
            color = _car_color(ac.vehicle_id)
            vehicle_type = ac.vehicle.vehicle_type
            if ac.lane_id.approach in (Approach.N, Approach.S):
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        int(cx - 20),
                        int(cy - 5),
                        vehicle_type.length,
                        vehicle_type.width,
                    ),
                )
            else:
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        int(cx - 5),
                        int(cy - 20),
                        vehicle_type.width,
                        vehicle_type.length,
                    ),
                )


class PygameKinematicVisualizer(_PygameViewBase):
    """Accel / cruise / brake style motion along the crossing segment (visual only)."""

    def __init__(
        self, sim: IntersectionSimulation, config: RenderConfig | None = None
    ) -> None:
        super().__init__(sim, config)
        self._animated: list[AnimatedCarKinematic] = []

    def _reset_animation_state(self) -> None:
        self._animated = []

    def _on_departure(self, lid: LaneId, vehicle: Vehicle) -> None:
        self._animated.append(AnimatedCarKinematic(lane_id=lid, vehicle=vehicle))

    def _tick_animations(self, real_dt: float) -> None:
        next_list: list[AnimatedCarKinematic] = []
        for car in self._animated:
            s, v = advance_trapezoid_speed(car.s, car.v, real_dt)
            car.s = s
            car.v = v
            if car.s < 1.0:
                next_list.append(car)
        self._animated = next_list

    def _draw_crossing_cars(self, center_x: int, center_y: int) -> None:
        n = self._num_lanes()
        for ac in self._animated:
            start, end = crossing_endpoints(ac.lane_id, center_x, center_y, n)
            t = min(1.0, ac.s)
            cx = start[0] + (end[0] - start[0]) * t
            cy = start[1] + (end[1] - start[1]) * t
            color = _car_color(ac.vehicle.id)
            vehicle_type = ac.vehicle.vehicle_type
            space_between_lanes = 70

            if ac.lane_id.approach in (Approach.N, Approach.S):
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        int(cx - space_between_lanes),
                        int(cy - 5),
                        vehicle_type.length,
                        vehicle_type.width,
                    ),
                )
            else:
                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        int(cx - 5),
                        int(cy - space_between_lanes),
                        vehicle_type.width,
                        vehicle_type.length,
                    ),
                )


def create_pygame_visualizer(
    sim: IntersectionSimulation,
    config: RenderConfig | None = None,
    backend: str = "simple",
) -> PygameSimpleVisualizer | PygameKinematicVisualizer:
    cfg = config or RenderConfig()
    cfg.backend = backend
    if backend == "kinematic":
        return PygameKinematicVisualizer(sim, cfg)
    return PygameSimpleVisualizer(sim, cfg)
