"""Append-only per-step stats and CSV export; used by HUD, experiments, and summaries."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Dict, List


@dataclass
class StepSnapshot:
    sim_time: float
    avg_wait_time: float
    max_wait_time: float
    throughput_per_min: float
    queue_n: int
    queue_s: int
    queue_e: int
    queue_w: int


@dataclass
class MetricsCollector:
    """Grows one snapshot per `simulation.step()` when `record` is called."""

    snapshots: List[StepSnapshot] = field(default_factory=list)

    def record(
        self,
        sim_time: float,
        avg_wait_time: float,
        max_wait_time: float,
        throughput_per_min: float,
        queue_lengths: Dict[str, int],
    ) -> None:
        self.snapshots.append(
            StepSnapshot(
                sim_time=sim_time,
                avg_wait_time=avg_wait_time,
                max_wait_time=max_wait_time,
                throughput_per_min=throughput_per_min,
                queue_n=queue_lengths["N"],
                queue_s=queue_lengths["S"],
                queue_e=queue_lengths["E"],
                queue_w=queue_lengths["W"],
            )
        )

    def final_summary(self) -> Dict[str, float]:
        if not self.snapshots:
            return {
                "avg_wait_time": 0.0,
                "max_wait_time": 0.0,
                "throughput_per_min": 0.0,
                "avg_total_queue": 0.0,
            }
        total_queues = [s.queue_n + s.queue_s + s.queue_e + s.queue_w for s in self.snapshots]
        return {
            "avg_wait_time": mean(s.avg_wait_time for s in self.snapshots),
            "max_wait_time": max(s.max_wait_time for s in self.snapshots),
            "throughput_per_min": self.snapshots[-1].throughput_per_min,
            "avg_total_queue": mean(total_queues),
        }

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "sim_time",
                    "avg_wait_time",
                    "max_wait_time",
                    "throughput_per_min",
                    "queue_n",
                    "queue_s",
                    "queue_e",
                    "queue_w",
                ]
            )
            for row in self.snapshots:
                writer.writerow(
                    [
                        row.sim_time,
                        row.avg_wait_time,
                        row.max_wait_time,
                        row.throughput_per_min,
                        row.queue_n,
                        row.queue_s,
                        row.queue_e,
                        row.queue_w,
                    ]
                )
