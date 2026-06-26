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
    2. Propagates 2001–2020 at 1-day cadence through the entire
       capture episode, both with the SBDB non-grav term and as a
       gravity-only control.
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
from empyrean import CometaryOrbits, Epochs, EventConfig, TimeScale, UncertaintyMethod


def main() -> None:
    empyrean.initialize()

    # ── 1. SBDB query ──────────────────────────────────────────────
    orbits = empyrean.query_sbdb(["2020 CD3"])
    print(f"Object: {orbits.object_id.to_pylist()[0]}")
    print(f"Epoch MJD TDB: {orbits.coordinates.epoch.to_numpy()[0]:.1f}")
    ng = orbits.non_grav
    print(
        f"non-grav coefficients (SBDB):  A1 = {ng.a1.to_numpy()[0]:.3e}  "
        f"A2 = {ng.a2.to_numpy()[0]:.3e}  A3 = {ng.a3.to_numpy()[0]:.3e} AU/d^2"
    )

    # ── 2. Propagate through the capture episode ────────────────────
    # 1-day cadence covers the full 8-year span. The propagator
    # inserts fine encounter samples around each capture pass
    # automatically via dense-output triggers.
    epochs = Epochs.from_kwargs(
        mjd=[52000.0 + 1.0 * i for i in range(7001)],
        scale=TimeScale.TDB.value,
    )
    # FirstOrder is fast enough for this scenario — the headline
    # numbers (capture starts/ends, periapsis distances) are
    # covariance-free.
    events = EventConfig(close_approaches=True)

    # Gravity-only control: drop the non_grav column so the orbit
    # propagates under pure gravity (A1 = A2 = A3 = 0).
    grav_only = CometaryOrbits.from_kwargs(
        orbit_id=orbits.orbit_id.to_pylist(),
        object_id=orbits.object_id.to_pylist(),
        coordinates=orbits.coordinates,
    )
    prop = empyrean.propagate(
        orbits,
        epochs,
        uncertainty_method=UncertaintyMethod.FIRST_ORDER,
        events=events,
    )
    prop_grav_only = empyrean.propagate(
        grav_only,
        epochs,
        uncertainty_method=UncertaintyMethod.FIRST_ORDER,
        events=events,
    )

    # ── 3. Capture episodes + close approaches ──────────────────────
    # Capture is the energy-criterion event (two-body specific energy
    # crossing zero relative to Earth) — emitted as `capture_start` /
    # `capture_end`. SOI crossings (`soi_entry` / `soi_exit`) are a
    # different concept: they fire when the integrator switches
    # central body via the Laplace-SOI dominance test.
    def summarize(label: str, prop: empyrean.PropagationResult) -> None:
        starts = [
            b for b in prop.events.capture_starts.body.to_pylist() if b == "Earth"
        ]
        ends = [b for b in prop.events.capture_ends.body.to_pylist() if b == "Earth"]
        p = prop.events.periapses
        bodies = p.body.to_pylist()
        periapses = [b for b in bodies if b in ("Earth", "Moon")]
        dist = p.distance_km.to_numpy()
        ep = p.epoch.to_numpy()
        earth_cas = sorted(
            ((ep[i], dist[i]) for i in range(len(bodies)) if bodies[i] == "Earth"),
            key=lambda x: x[1],
        )
        print(f"\n── {label} ──")
        print(f"Capture starts: {len(starts)}")
        print(f"Capture ends:   {len(ends)}")
        print(f"Close approaches (Earth+Moon): {len(periapses)}")
        if earth_cas:
            mjd, d = earth_cas[0]
            print(f"Closest Earth approach: MJD {mjd:.3f}  {d:>10.0f} km")
        else:
            print("Closest Earth approach: none in window")

    summarize("With SBDB non-grav (A1 = 1.357e-10)", prop)
    summarize("Gravity-only control (A1 = A2 = A3 = 0)", prop_grav_only)

    print("\nReference: capture period ~2017-2020 (Fedorets+ 2020).")


# spielberg:snippet:end


if __name__ == "__main__":
    main()
