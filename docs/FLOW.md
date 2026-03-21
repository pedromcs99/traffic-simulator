# How the code runs

Read this top-to-bottom once; it matches the call order in the repo.

## Entry points

| You run | What starts | What happens next |
|---------|---------------|-------------------|
| `py -3 -m traffic_sim` | `traffic_sim/main.py` → `main()` | Builds controller + `IntersectionSimulation` + a pygame visualizer from `--visual-backend`; loop uses `--timescale` and may call `sim.step()` zero or more times per frame. |
| `py -3 experiments/compare_controllers.py` | That script’s `main()` | Two fresh sims (same `--seed`), each `run(N)` with **no** pygame; writes CSV under `experiments/results/`. |

`traffic_sim/__main__.py` only forwards to `main()` so `-m traffic_sim` works.

---

## Domain model (`models.py`)

- **`LaneId`**: `(Approach, lane_index)` — parallel lanes per approach (`SimulationConfig.num_lanes_per_approach`).
- **`Vehicle`**: `lane_id`, `movement` (`STRAIGHT` until turns exist), `wait_time`.
- **`Intersection.lanes`**: `dict[LaneId, Lane]` (FIFO queues).
- **`queue_lengths()`**: totals per **approach** `N,S,E,W` (sums parallel lanes) for metrics/controllers.
- **`aggregate_for_controller()`**: same observation shape as before (`ns_queue`, `ew_queue`).

---

## One simulation step (`IntersectionSimulation.step`)

Order is fixed:

1. **`_spawn_vehicles`** — Bernoulli per approach in `spawn_probabilities`; random lane index among `0..num_lanes-1`; new `Vehicle` enqueued.
2. **`_increment_wait_times`** — Every queued vehicle’s `wait_time` += `dt`.
3. **`_apply_controller`** — `SimulationObservation` → `choose_action` → lights.
4. **`_move_vehicles`** — If not yellow: for each `LaneId` on the green axis, pop up to `pass_rate_per_green_lane` vehicles; append `(LaneId, Vehicle)` to **`departed_this_step`**.
5. **Clock** — `sim_time`, `phase_elapsed`, optional `yellow_elapsed`.
6. **`_record_metrics`**.

---

## Controller contract (`controllers/base.py`)

- **`SimulationObservation`**: `queue_lengths` (N,S,E,W totals), `ns_queue`, `ew_queue`, light state, timers.
- **`ControllerAction`**: yellow / switch / optional `target_green_duration`.

---

## Traffic light (`models.TrafficLight`)

Axis-level green/yellow/red for `NS` vs `EW` (movement-specific phases are future work).

---

## Visualization (`visual_backends/pygame_impl.py`)

Does not change traffic rules.

1. Events, then wall-clock → sim accumulator → `sim.step()` in a loop (capped per frame).
2. After each step, for each `(LaneId, Vehicle)` in `departed_this_step`, spawn a visual crossing sprite.
3. Each frame: update animations — **`simple`** uses linear progress over `crossing_duration_seconds`; **`kinematic`** uses `motion_profiles.advance_trapezoid_speed` (visual only).
4. Draw roads, lights, queued cars (per lane + lateral offset), crossing cars. Geometry: `render_layout.py`.

---

## Metrics (`metrics.py`)

Per-step CSV rows use aggregated `queue_n`…`queue_w` (unchanged).

---

## File map

| File | Role |
|------|------|
| `simulation.py` | Loop, spawn, lights, dequeue. |
| `models.py` | Lanes, vehicles, intersection topology. |
| `render_layout.py` | Pixel math for queues and crossing segments. |
| `visual_backends/pygame_impl.py` | Pygame simple vs kinematic. |
| `controllers/*.py` | Policies. |
| `main.py` | CLI. |
| `experiments/compare_controllers.py` | Headless benchmark. |
