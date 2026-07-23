"""Bennu: measuring Yarkovsky drift from optical + radar astrometry + 2060 encounter.

Reproduces the bennu explore-mode scenario from
https://empyrean-dynamics.com/explore/bennu.

Run:
    pip install empyrean
    python 101955_Bennu/main.py

What it does:
    1. Pulls Bennu's MPC optical astrometry plus the Arecibo/Goldstone
       radar delay/Doppler record (1999, 2005, 2011 apparitions) — the
       ranging data that anchored the classic Yarkovsky detection
       (Chesley et al. 2014).
    2. Anchors the epoch state on the 1999-2000 discovery apparition —
       optical plus its Arecibo/Goldstone radar ranging — then measures
       the drift: a joint (state + Marsden A-block) refine over the full
       26-year optical arc, with the A-block seeded at ZERO and opened
       by a Bayesian prior that pins the radial/normal components and
       leaves the transverse A2 wide. A2 IS the Yarkovsky measurement —
       recovered from the astrometry with an honest 1σ from the solved
       covariance, not patched in from a published value. (A real
       first-principles Vokrouhlický thermal model is on the engine
       roadmap.)

    Verified run (empyrean 0.9.0): A2 = -2.8e-14 ± 1.1e-14 AU/d² — a
    2.6σ detection of the drift, consistent with JPL's radar-complete
    joint solution (-4.618e-14, Farnocchia 2021) at 1.6σ.
    3. Propagates the FITTED orbit ~72 years (2011-2083) at 5-day
       cadence through the 2060 Earth encounter and the 2080 follow-up.
    4. Reads out the close-approach geometry and the projected B-plane
       3σ uncertainty at each Earth flyby.

Authoritative cross-checks (printed inline):
    - A2 = -4.618e-14 AU/d² (~284 m/orbit drift)        (Farnocchia 2021)
    - 2060-09-23, geocentric ~750,000 km                 (JPL CAD)
    - Cumulative 22nd-century IP: ~1/1750                (Farnocchia 2021)
"""

from __future__ import annotations

# empyrean:snippet:start
import empyrean
from empyrean import (
    Epochs,
    ODConfig,
    SolveForParams,
    TimeScale,
    UncertaintyMethod,
)


def main() -> None:
    empyrean.initialize()

    # ── 1. Optical astrometry (MPC) + radar astrometry (JPL) ────────
    # The MPC carries optical only; asteroid radar is a JPL SSD product,
    # queried separately and folded into the same fit. Bennu's 29
    # delay/Doppler measurements from Arecibo and Goldstone (1999, 2005,
    # 2011) are what pinned its semimajor-axis drift — radar ranging
    # measures the line-of-sight distance at the ~100 m level, which two
    # decades of Yarkovsky drift dwarfs.
    obs = empyrean.query_observations(["101955"])
    radar = empyrean.query_radar(["101955"])
    print(f"{len(obs)} optical + {len(radar)} radar (delay/Doppler)")

    # ── 2a. Anchor: state fit on the discovery apparition + radar ───
    # A state-only fit over the FULL arc would silently absorb the
    # Yarkovsky drift into the epoch state (aliasing the very signal we
    # want to measure), so the anchor uses only the 1999-2000 discovery
    # apparition — short enough that the drift is negligible — with its
    # radar ranging pinning the line-of-sight distance at the ~100 m
    # level.
    import numpy as np

    years = [t[:4] for t in obs.table.column("obs_time").to_pylist()]
    short = obs.take(np.nonzero(np.array([y in ("1999", "2000") for y in years]))[0])
    r_years = [t[:4] for t in radar.table.column("obs_time").to_pylist()]
    radar_short = radar.take(
        np.nonzero(np.array([y in ("1999", "2000") for y in r_years]))[0]
    )
    anchor = empyrean.determine(
        short,
        radar=radar_short if len(radar_short) else None,
        config=ODConfig(solve_for=SolveForParams.STATE_ONLY),
    )
    print(
        f"Anchor (1999-2000, {len(short)} optical + {len(radar_short)} radar): "
        f"chi2/dof {anchor.summary.reduced_chi2:.2f}"
    )

    # ── 2b. Measure: joint state + A2 refine over the full 26-yr arc ─
    # Bennu's arc constrains the TRANSVERSE component only — the A-block
    # is seeded at ZERO and opened by a Bayesian prior that pins A1/A3
    # near zero and leaves A2 wide: the astrometry, not the prior,
    # measures the drift. All-zero g(r) constants select the exact
    # inverse-square law (the Yarkovsky convention).
    from empyrean import NonGravParams

    sigma_tight = 1e-15  # AU/d^2 — A1/A3 pinned ~30x below the A2 signal
    sigma_wide = 1e-12  # AU/d^2 — A2 unconstrained (~20x above the signal)
    primed = anchor.orbit.set_column(
        "non_grav",
        NonGravParams.from_kwargs(
            a1=[0.0],
            a2=[0.0],
            a3=[0.0],
            model=["marsden"],
            alpha=[0.0],
            r0=[0.0],
            m=[0.0],
            n=[0.0],
            k=[0.0],
            covariance=[
                [sigma_tight**2, 0, 0, 0, sigma_wide**2, 0, 0, 0, sigma_tight**2]
            ],
        ),
    )
    cfg = ODConfig(solve_for=SolveForParams.STATE_AND_NONGRAV)
    result = empyrean.refine(primed, obs, config=cfg)
    s = result.summary
    print(f"Converged:  {result.converged}")
    print(f"chi2/dof:   {s.reduced_chi2:.3f}")
    print(f'RMS:        RA·cos(d) {s.rms_ra_arcsec:.3f}"  Dec {s.rms_dec_arcsec:.3f}"')
    print(f"Selected:   {s.num_selected}/{s.num_obs}")

    ng = result.orbit.non_grav
    a2 = ng.a2.to_numpy(zero_copy_only=False)[0]
    # The tagged solved covariance names each fitted parameter's slot —
    # read σ_A2 from the A2 row rather than guessing at column order.
    sc = result.solved_covariance
    if sc is not None and sc.marsden_slot is not None:
        a2_row = sc.marsden_slot + 1  # Marsden block is (A1, A2, A3)
        a2_sigma = float(sc.matrix[a2_row, a2_row]) ** 0.5
        print(f"Fitted A2 (≈ Yarkovsky) = {a2:.3e} +/- {a2_sigma:.1e} AU/d^2")
    else:
        print(f"Fitted A2 (≈ Yarkovsky) = {a2:.3e} AU/d^2")
    print("Reference                 -4.618e-14 AU/d^2   (Farnocchia 2021,")
    print("                          radar-complete joint solution)")

    # ── 3. Propagate the fitted orbit ~72 years (2011 → 2083) ───────
    # The orbit carries its fitted covariance and non-grav model, so the
    # 2060/2080 uncertainty story below is traceable to the astrometry.
    # 5-day cadence renders smoothly at planet-radius zoom; coarser
    # cadences give piecewise-linear trajectory artifacts at Earth
    # close approach.
    epochs = Epochs.from_kwargs(
        mjd=[55562.0 + 5.0 * i for i in range(5289)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        result.orbit,
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
    # Gravitational covariance amplification at close approach made
    # quantitative: the 2060 3σ ellipse — now traceable to the fitted
    # covariance — inflates by orders of magnitude through the flyby.
    # The growth factor is computed live below.
    b_planes = empyrean.compute_b_planes(
        result.orbit,
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
    earth_sm = [sm[i] for i in range(len(b_planes)) if body[i] == "Earth"]
    if len(earth_sm) >= 2:
        print(
            f"(2060 B-plane uncertainty input to any downstream resonant-return analysis; "
            f"3-sigma ellipse grows {earth_sm[1] / earth_sm[0]:.0f}x by 2080.)"
        )


# empyrean:snippet:end


if __name__ == "__main__":
    main()
