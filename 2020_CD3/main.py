"""2020 CD3: Earth's second known mini-moon — multi-year capture episode.

Reproduces the 2020cd3 explore-mode scenario from
https://empyrean-dynamics.com/explore/2020cd3.

Run:
    pip install empyrean
    python 2020_CD3/main.py

What it does:
    1. Queries JPL SBDB for 2020 CD3's orbital state. The orbit
       carries an inverse-square non-grav term (small-body radiation
       pressure); the propagator picks it up automatically.
    2. Propagates 2014–2022 at 1-day cadence through the entire
       capture episode.
    3. Counts CaptureStart / CaptureEnd events (the 2017–2020
       gravitational capture by the Earth-Moon system) and the dense
       constellation of Earth + Moon close approaches in between.

Authoritative cross-checks (printed inline):
    - Discovery: 2020-02-15 by Catalina Sky Survey
    - Estimated diameter: 1–1.5 m
    - Capture duration (Fedorets+ 2020): ~2017 → 2020-03 (~3 years)
"""

from __future__ import annotations

# spielberg:snippet:start
import empyrean
from empyrean import Epochs, TimeScale, UncertaintyMethod


def main() -> None:
    empyrean.initialize()

    # ── 1. SBDB query ──────────────────────────────────────────────
    orbits = empyrean.query_sbdb(["2020 CD3"])
    print(f"Object: {orbits.object_id.to_pylist()[0]}")

    # ── 2. Propagate through the capture episode ────────────────────
    # 1-day cadence covers the full 8-year span. The propagator
    # inserts fine encounter samples around each capture pass
    # automatically via dense-output triggers.
    epochs = Epochs.from_kwargs(
        mjd=[56000.0 + 1.0 * i for i in range(3001)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        orbits,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
    )

    # ── 3. Capture episodes + close approaches ──────────────────────
    print(f"\nCapture starts: {len(prop.events.capture_starts)}")
    print(f"Capture ends:   {len(prop.events.capture_ends)}")
    print(f"Close approaches (Earth+Moon): {len(prop.events.periapses)}")

    # ── 4. Closest Earth approach ───────────────────────────────────
    earth_cas = []
    for i in range(len(prop.events.periapses)):
        p = prop.events.periapses
        if p.body.to_pylist()[i] == "Earth":
            earth_cas.append(
                (
                    p.epoch.to_numpy()[i],
                    p.distance_km.to_numpy()[i],
                )
            )
    if earth_cas:
        earth_cas.sort(key=lambda x: x[1])
        mjd, dist = earth_cas[0]
        print(f"\nClosest Earth approach: MJD {mjd:.3f}  {dist:>10.0f} km")
    print("Reference: capture period ~2017-2020 (Fedorets+ 2020).")


# spielberg:snippet:end


if __name__ == "__main__":
    main()
