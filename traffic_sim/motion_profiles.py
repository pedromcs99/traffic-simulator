"""Visual-only motion: advance normalized arc length with accel / brake (not simulation physics)."""


def advance_trapezoid_speed(
    s: float,
    v: float,
    dt: float,
    *,
    v_max: float = 2.0,
    accel: float = 1.0,
    brake: float = 2.0,
) -> tuple[float, float]:
    """Return new (s, v) with s in [0, 1]; v is speed along normalized path."""
    remaining = max(0.0, 1.0 - s)
    # Brake distance estimate ~ v^2 / (2*brake)
    stop_dist = (v * v) / (2.0 * brake) if brake > 0 else 0.0
    if remaining <= 1e-6:
        return 1.0, 0.0
    if stop_dist >= remaining * 0.98:
        v = max(0.0, v - brake * dt)
    elif v < v_max:
        v = min(v_max, v + accel * dt)
    ds = v * dt
    s = min(1.0, s + ds)
    return s, v


def linear_advance(progress: float, dt: float, duration: float) -> float:
    """Uniform motion (legacy simple backend)."""
    if duration <= 0:
        return 1.0
    return min(1.0, progress + dt / duration)
