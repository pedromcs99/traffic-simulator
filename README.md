# Traffic intersection simulator

4-way intersection, queue-based cars, traffic lights. **Fixed** vs **dynamic** controllers; optional CSV benchmarks. Visualization uses **pygame** (`simple` or `kinematic` motion).

**Execution order:** [docs/FLOW.md](docs/FLOW.md)

---

### If you know Java or JavaScript

| Python idea | Rough analogue |
|-------------|----------------|
| `pip` + `requirements.txt` | npm + `package.json` dependencies |
| `traffic_sim/` package | a Java package / npm package folder |
| `py -3 -m traffic_sim` | run the app’s main module (like `java -cp …` or `node` on an entry file, but the `-m` target is the package name) |
| Virtual env | isolated `node_modules` / separate JDK project—optional here |

---

### Setup

Terminal **cwd must be this repo root** (the folder that contains `traffic_sim/`).

```bash
py -3 -m pip install -r requirements.txt
```

Use `python` instead of `py -3` if that’s what works on your machine. If `pip` is missing: `py -3 -m ensurepip --upgrade`, then the line above again.

---

### Run

| Goal | Command |
|------|---------|
| Visual sim, close window to stop | `py -3 -m traffic_sim` |
| Kinematic-style crossing animation | `py -3 -m traffic_sim --visual-backend kinematic` |
| Two lanes per approach | `py -3 -m traffic_sim --lanes 2` |
| Dynamic lights | `py -3 -m traffic_sim --controller dynamic` |
| Stop after N simulated seconds | `py -3 -m traffic_sim --duration 120` |
| Slower pace (2 real s per 1 sim s) | `py -3 -m traffic_sim --timescale 2` |
| Benchmark fixed vs dynamic → CSV | `py -3 experiments/compare_controllers.py --duration 300 --seed 42` |

Benchmark output: `experiments/results/` (`*_timeseries.csv`, `comparison_summary.csv`).

CLI: `--controller`, `--seed`, `--fps`, `--timescale`, `--visual-backend simple|kinematic`, `--lanes N` (visual + sim).

---

### Repo layout

```
traffic_sim/
  main.py                 # CLI
  simulation.py           # discrete-time loop
  models.py               # LaneId, approaches, vehicles (straight; turns TBD)
  render_layout.py        # shared screen geometry
  motion_profiles.py      # visual-only kinematic helpers
  visual_backends/        # pygame simple vs kinematic
  visualization.py        # re-exports visual backends
  controllers/
experiments/              # headless benchmarks
requirements.txt
```

One simulation step ≈ 1 s simulated time. Controllers still see aggregated N/S/E/W queues. `Movement` on `Vehicle` is for future turn routing.
