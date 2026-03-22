"""CLI entry: optional pygame check, then `IntersectionSimulation` + visualizer loop."""

from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Traffic intersection simulator")
    parser.add_argument("--controller", choices=["fixed", "dynamic"], default="fixed")
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Stop after this many simulated seconds (default: run until you close the window)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--fps", type=int, default=30, help="Max frames per second (default: 30)"
    )
    parser.add_argument(
        "--timescale",
        type=float,
        default=1.0,
        metavar="T",
        help="Wall-clock seconds per 1 simulated second (e.g. 2.0 = slower pace; default 1.0)",
    )
    parser.add_argument(
        "--visual-backend",
        choices=["simple", "kinematic"],
        default="simple",
        help="simple=linear crossing; kinematic=accel/brake style motion (visual only)",
    )
    parser.add_argument(
        "--lanes",
        type=int,
        default=1,
        metavar="N",
        help="Parallel lanes per approach (>=1; default 1)",
    )
    return parser.parse_args()


def main() -> None:
    """Parse args, construct controller/sim, run pygame until quit or `--duration`."""
    args = parse_args()

    try:
        import pygame  # noqa: F401
    except ImportError:
        print(
            "pygame is not installed. From the project folder run:\n"
            "  py -3 -m pip install -r requirements.txt\n"
            "or:\n"
            "  pip install pygame",
            file=sys.stderr,
        )
        sys.exit(1)

    from traffic_sim.controllers.dynamic import DynamicController
    from traffic_sim.controllers.fixed_time import FixedTimeController
    from traffic_sim.simulation import IntersectionSimulation, SimulationConfig
    from traffic_sim.visual_backends.pygame_impl import (
        RenderConfig,
        create_pygame_visualizer,
    )

    controller = (
        FixedTimeController() if args.controller == "fixed" else DynamicController()
    )
    lanes = max(1, args.lanes)
    config = SimulationConfig(seed=args.seed, num_lanes_per_approach=lanes)
    simulation = IntersectionSimulation(controller=controller, config=config)
    ts = args.timescale if args.timescale > 0 else 1.0
    render_config = RenderConfig(real_seconds_per_sim_second=ts)
    renderer = create_pygame_visualizer(simulation, render_config, args.visual_backend)
    renderer.run(duration_seconds=args.duration, fps=args.fps)


if __name__ == "__main__":
    main()
