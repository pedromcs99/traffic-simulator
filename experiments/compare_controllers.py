"""Headless benchmark: two sims, same seed/duration, CSV time series + summary (adds repo root to `sys.path`)."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from traffic_sim.controllers.dynamic import DynamicController
from traffic_sim.controllers.fixed_time import FixedTimeController
from traffic_sim.simulation import IntersectionSimulation, SimulationConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare fixed and dynamic traffic controllers"
    )
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/results"))
    return parser.parse_args()


def run_once(
    name: str, sim: IntersectionSimulation, duration: int, output_dir: Path
) -> dict[str, float]:
    metrics = sim.run(duration)
    metrics.write_csv(output_dir / f"{name}_timeseries.csv")
    return metrics.final_summary()


def improvement_pct(base: float, candidate: float, lower_is_better: bool) -> float:
    if base == 0:
        return 0.0
    if lower_is_better:
        return ((base - candidate) / base) * 100.0
    return ((candidate - base) / base) * 100.0


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    fixed_sim = IntersectionSimulation(
        controller=FixedTimeController(),
        config=SimulationConfig(seed=args.seed),
    )
    dynamic_sim = IntersectionSimulation(
        controller=DynamicController(),
        config=SimulationConfig(seed=args.seed),
    )

    fixed_summary = run_once("fixed", fixed_sim, args.duration, args.output_dir)
    dynamic_summary = run_once("dynamic", dynamic_sim, args.duration, args.output_dir)

    comparison_rows = [
        (
            "avg_wait_time",
            fixed_summary["avg_wait_time"],
            dynamic_summary["avg_wait_time"],
            True,
        ),
        (
            "max_wait_time",
            fixed_summary["max_wait_time"],
            dynamic_summary["max_wait_time"],
            True,
        ),
        (
            "throughput_per_min",
            fixed_summary["throughput_per_min"],
            dynamic_summary["throughput_per_min"],
            False,
        ),
        (
            "avg_total_queue",
            fixed_summary["avg_total_queue"],
            dynamic_summary["avg_total_queue"],
            True,
        ),
    ]

    summary_path = args.output_dir / "comparison_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["metric", "fixed", "dynamic", "improvement_pct_dynamic_vs_fixed"]
        )
        for metric, fixed_value, dynamic_value, lower_is_better in comparison_rows:
            writer.writerow(
                [
                    metric,
                    fixed_value,
                    dynamic_value,
                    improvement_pct(fixed_value, dynamic_value, lower_is_better),
                ]
            )

    print(f"Results saved in: {args.output_dir}")
    for metric, fixed_value, dynamic_value, lower_is_better in comparison_rows:
        improvement = improvement_pct(fixed_value, dynamic_value, lower_is_better)
        direction = "better" if improvement >= 0 else "worse"
        print(
            f"{metric}: fixed={fixed_value:.3f}, dynamic={dynamic_value:.3f}, "
            f"dynamic {abs(improvement):.2f}% {direction}"
        )


if __name__ == "__main__":
    main()
