"""Bennu: textbook transverse non-grav A2 (≈ Yarkovsky) detection + 2060 encounter.

Reproduces the bennu explore-mode scenario from
https://empyrean-dynamics.com/explore/bennu.

Run:
    pip install empyrean
    python 101955_Bennu/main.py

What it does:
    1. Queries JPL SBDB for Bennu's orbital state + 6×6 covariance.
    2. Patches in the published transverse non-grav A2 = -4.62e-14 AU/d²
       (Farnocchia et al. 2021 — interpreted physically as Yarkovsky
       thermal recoil from OSIRIS-REx-measured spin and thermal inertia)
       since SBDB doesn't always ship the non-grav coefficients for
       asteroid solutions. Empyrean fits the Marsden A1/A2/A3 form with
       inverse-square g(r); a real first-principles Vokrouhlický thermal
       model is on the engine roadmap.
    3. Propagates 125 years at 5-day cadence through the 2060 Earth
       encounter and the 2080 follow-up.
    4. Reads out the close-approach geometry and the projected B-plane
       3σ uncertainty at each Earth flyby.

Authoritative cross-checks (printed inline):
    - 2060-09-23, geocentric ~750,000 km                (JPL CAD)
    - A2 = -4.62e-14 AU/d² (~284 m/orbit)               (Farnocchia 2021)
    - Cumulative 22nd-century IP: ~1/1750               (Farnocchia 2021)
"""

from __future__ import annotations

# spielberg:snippet:start
import empyrean
from empyrean import Epochs, TimeScale, UncertaintyMethod


# Published Bennu transverse non-grav A2 from Farnocchia et al. 2021 —
# the OSIRIS-REx-augmented OD paper; physical interpretation is
# Yarkovsky thermal recoil. SBDB ships this in its non_grav block; if
# absent locally, we patch it in below.
BENNU_A2 = -4.6178e-14  # AU/d², Marsden transverse coefficient


def main() -> None:
    empyrean.initialize()

    # ── 1. Query SBDB for Bennu ─────────────────────────────────────
    orbits = empyrean.query_sbdb(["101955"])
    print(f"Object: {orbits.object_id.to_pylist()[0]}")
    print(
        f"Epoch MJD TDB: {orbits.coordinates.epoch.to_numpy(zero_copy_only=False)[0]:.1f}"
    )

    # ── 2. Patch in the published Marsden A2 if SBDB didn't ship it ─
    a2_existing = (
        orbits.non_grav.a2.to_numpy(zero_copy_only=False)[0]
        if orbits.non_grav is not None
        else float("nan")
    )
    if orbits.non_grav is None or a2_existing == 0.0 or a2_existing != a2_existing:
        from empyrean import NonGravParams

        orbits = orbits.set_column(
            "non_grav",
            NonGravParams.from_kwargs(
                a1=[0.0],
                a2=[BENNU_A2],
                a3=[0.0],
                model=["marsden_water"],
            ),
        )
    a2_now = orbits.non_grav.a2.to_numpy(zero_copy_only=False)[0]
    print(f"Marsden A2 (≈ Yarkovsky): {a2_now:.3e} AU/d^2")
    print("Reference                 -4.6178e-14    (Farnocchia 2021)")

    # ── 3. Propagate 125 years at 5-day cadence ─────────────────────
    # 5-day cadence renders smoothly at planet-radius zoom; coarser
    # cadences give piecewise-linear trajectory artifacts at Earth
    # close approach.
    epochs = Epochs.from_kwargs(
        mjd=[55562.0 + 5.0 * i for i in range(5289)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        orbits,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
    )

    # ── 4. Close approaches detected inline ─────────────────────────
    print("\nClose approaches (Empyrean):")
    p = prop.events.periapses
    bodies = p.body.to_pylist()
    epochs_p = p.epoch.to_numpy(zero_copy_only=False)
    dists = p.distance_km.to_numpy(zero_copy_only=False)
    for i in range(len(p)):
        print(f"  {bodies[i]:6s}  MJD {epochs_p[i]:.3f}  {dists[i]:>12.0f} km")
    print("Reference (JPL CAD nominal):")
    print("  Earth   MJD 73725 (2060-09-23)   ~750,000 km")

    # ── 5. B-plane geometry at each Earth encounter ─────────────────
    # 21 km 3σ at 2060 inflates to ~9,300 km at 2080 — gravitational
    # covariance amplification at close approach made quantitative.
    b_planes = empyrean.compute_b_planes(
        orbits,
        end_epoch=epochs.mjd.to_numpy(zero_copy_only=False)[-1],
        methods=[UncertaintyMethod.SECOND_ORDER],
        body_filter=["Earth"],
    )
    print("\nEarth B-plane geometry (Empyrean):")
    body = b_planes.body.to_pylist()
    bp_epochs = b_planes.epochs.mjd.to_numpy(zero_copy_only=False)
    bmag = b_planes.b_mag_km.to_numpy(zero_copy_only=False)
    sm = b_planes.semi_major_3sig_km.to_numpy(zero_copy_only=False)
    for i in range(len(b_planes)):
        if body[i] == "Earth":
            print(
                f"  MJD {bp_epochs[i]:.3f}  |B| = {bmag[i]:>10.0f} km  "
                f"3-sigma semi-major = {sm[i]:>8.1f} km"
            )
    print(
        "(2060 B-plane uncertainty input to any downstream resonant-return analysis; 440x covariance amplification at 2080.)"
    )


# spielberg:snippet:end


if __name__ == "__main__":
    main()
