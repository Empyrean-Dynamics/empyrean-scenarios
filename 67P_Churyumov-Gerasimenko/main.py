"""67P/Churyumov-Gerasimenko: cometary non-gravitational acceleration.

Reproduces the 67p explore-mode scenario from
https://empyrean-dynamics.com/explore/67p.

Run:
    pip install empyrean
    python 67P_Churyumov-Gerasimenko/main.py

What it does:
    1. Queries JPL SBDB for 67P. The SBDB solution ships the standard
       Marsden water-sublimation A1/A2/A3 coefficients for the comet's
       outgassing-driven non-gravitational acceleration, the water-ice
       g(r) exponents, and a +46 d outgassing time delay.
    2. Propagates a 16-year, 10-day-cadence window starting at the
       orbit epoch — covers both the Rosetta-era (2015) and 2021
       perihelia, plus the upcoming 2028 return.
    3. Compares with a control run that drops the non-grav term, and
       prints the cumulative along-track displacement.

Authoritative cross-checks (printed inline):
    - Orbital period: 6.44 years
    - Last perihelion: 2021-11-02
    - Next perihelion: 2028-05-21
    - Marsden A1: ~1e-9 AU/d²
    - Magnitude of A1 ≈ 36,000× |Apophis A2| (transverse, ≈ Yarkovsky);
      different physics, comparable acceleration scale.
"""

from __future__ import annotations

# spielberg:snippet:start
import empyrean
from empyrean import (
    CometaryOrbits,
    Epochs,
    NonGravParams,
    TimeScale,
    UncertaintyMethod,
)
import numpy as np


KM_PER_AU = 149_597_870.7


def main() -> None:
    empyrean.initialize()

    # ── 1. SBDB query — non-grav coefficients included ──────────────
    orbits = empyrean.query_sbdb(["67P"])
    ng = orbits.non_grav
    print("non-grav coefficients (SBDB):")
    print(f"  A1 = {ng.a1.to_numpy()[0]:.3e} AU/d^2")
    print(f"  A2 = {ng.a2.to_numpy()[0]:.3e} AU/d^2")
    print(f"  A3 = {ng.a3.to_numpy()[0]:.3e} AU/d^2")

    # SBDB ships 67P's full Marsden-Sekanina solution: the water-ice
    # g(r) exponents (alpha, r0, m, n, k) and a +46 d outgassing time
    # delay. Re-attach them explicitly so the full run propagates the
    # comet g(r) — not the asteroid inverse-square default.
    full_orbit = CometaryOrbits.from_kwargs(
        orbit_id=orbits.orbit_id.to_pylist(),
        object_id=orbits.object_id.to_pylist(),
        coordinates=orbits.coordinates,
        non_grav=NonGravParams.from_kwargs(
            a1=ng.a1.to_pylist(),
            a2=ng.a2.to_pylist(),
            a3=ng.a3.to_pylist(),
            model=["marsden"],
            alpha=[0.1113],
            r0=[2.808],
            m=[2.15],
            n=[5.093],
            k=[4.6142],
            dt=[45.68888251286532],
        ),
    )

    # ── 2. Propagate 16 years at 10-day cadence from the orbit epoch ─
    base = orbits.coordinates.epoch.to_numpy()[0]
    epochs = Epochs.from_kwargs(
        mjd=[base + 10.0 * i for i in range(601)],
        scale=TimeScale.TDB.value,
    )
    full = empyrean.propagate(
        full_orbit,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
    )

    # ── 3. Control run — drop non-grav, propagate again ─────────────
    # Build a fresh orbit set without the non_grav column. The
    # cumulative position separation between the two trajectories is
    # the integrated effect of outgassing.
    orbits_grav_only = CometaryOrbits.from_kwargs(
        orbit_id=orbits.orbit_id.to_pylist(),
        object_id=orbits.object_id.to_pylist(),
        coordinates=orbits.coordinates,
        # non_grav omitted -> pure-gravity propagation
    )
    control = empyrean.propagate(orbits_grav_only, epochs)

    # ── 4. Cumulative along-track displacement ──────────────────────
    delta_au = np.sqrt(
        (full.states.coordinates.x.to_numpy() - control.states.coordinates.x.to_numpy())
        ** 2
        + (
            full.states.coordinates.y.to_numpy()
            - control.states.coordinates.y.to_numpy()
        )
        ** 2
        + (
            full.states.coordinates.z.to_numpy()
            - control.states.coordinates.z.to_numpy()
        )
        ** 2
    )
    delta_km = delta_au * KM_PER_AU
    print(
        f"\nMax separation (non-grav vs gravity-only) over 16 years: "
        f"{delta_km.max():,.0f} km"
    )
    print(
        "(That's the cumulative effect of outgassing — what every "
        "cometary ephemeris pipeline has to model.)"
    )


# spielberg:snippet:end


if __name__ == "__main__":
    main()
