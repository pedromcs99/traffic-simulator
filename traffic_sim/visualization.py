"""Pygame visualization entry; implementation lives in `traffic_sim.visual_backends`."""

from traffic_sim.visual_backends.pygame_impl import (
    PygameKinematicVisualizer,
    PygameSimpleVisualizer,
    RenderConfig,
    create_pygame_visualizer,
)

# Backward-compatible name (simple/linear crossing).
PygameRenderer = PygameSimpleVisualizer

__all__ = [
    "RenderConfig",
    "PygameRenderer",
    "PygameSimpleVisualizer",
    "PygameKinematicVisualizer",
    "create_pygame_visualizer",
]
