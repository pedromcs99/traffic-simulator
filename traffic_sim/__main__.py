"""Shim so `py -3 -m traffic_sim` runs the same `main()` as `traffic_sim/main.py`."""

from traffic_sim.main import main

if __name__ == "__main__":
    main()
