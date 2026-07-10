"""Apophis end-to-end: 21-year astrometric arc → Marsden A1/A2/A3 fit → 2029 flyby.

Reproduces the apophis explore-mode scenario from
https://empyrean-dynamics.com/explore/apophis.

Run:
    pip install empyrean
    python 99942_Apophis/main.py

What it does:
    1. Pulls every available MPC optical observation of Apophis plus the
       JPL Goldstone/Arecibo radar delay/Doppler astrometry, and folds
       both ADES tables into one fit.
    2. Runs `empyrean.determine` with the 9-parameter (state + Marsden
       A1/A2/A3) solve_for so the converged orbit carries the same
       non-gravitational coefficients JPL fits jointly with the state.
       The transverse A2 is consistent with Yarkovsky thermal recoil
       and is fit empirically with inverse-square g(r); a real
       first-principles Vokrouhlický thermal model is roadmap.
    3. Forward-propagates that orbit through the 2029 Earth flyby with
       second-order STT uncertainty.
    4. Prints close approaches, reads back the resolved-kind
       (second-order) covariance at the flyby and contrasts it with
       the bare linear covariance, and reports the 2029 B-plane
       geometry.

Authoritative cross-checks (printed inline):
    - 2029-04-13 21:46 UT, geocentric 38,012 km    (JPL CAD)
    - A1 ≈  5e-13 AU/d²  (radial)                  (JPL SBDB)
    - A2 ≈ -2.9e-14 AU/d²  (transverse, ≈ Yarkovsky)  (JPL SBDB)
    - Removed from Sentry 2021-02-21               (NASA / CNEOS)
"""

from __future__ import annotations

# spielberg:snippet:start
import numpy as np

import empyrean
from empyrean import Epochs, ODConfig, SolveForParams, TimeScale, UncertaintyMethod


def main() -> None:
    empyrean.initialize()  # downloads SPICE kernels on first run

    # ── 1. Optical astrometry (MPC) + radar astrometry (JPL) ────────
    # ~9,500 optical observations from 2004 onward (Gaia-grade CCD), plus
    # Apophis's extensive Goldstone/Arecibo radar delay/Doppler record set.
    # The MPC carries optical only; asteroid radar is a JPL SSD product,
    # queried separately and folded into the same fit.
    obs = empyrean.query_observations(["99942"])
    radar = empyrean.query_radar(["99942"])
    print(f"{len(obs)} optical + {len(radar)} radar (delay/Doppler)")

    # ── 2. 9-parameter OD with non-grav ─────────────────────────────
    # Forces the (state + A1, A2, A3) solve. The hyperdual integrator
    # computes the (O-C) Jacobian against all 9 parameters analytically
    # — no finite differencing of the 21-year arc.
    cfg = ODConfig(solve_for=SolveForParams.STATE_AND_NONGRAV)
    result = empyrean.determine(obs, radar=radar if len(radar) else None, config=cfg)
    s = result.summary
    print(f"Converged:  {result.converged}")
    print(f"chi2/dof:   {s.reduced_chi2:.3f}")
    print(f'RMS:        RA·cos(d) {s.rms_ra_arcsec:.3f}"  Dec {s.rms_dec_arcsec:.3f}"')
    print(f"Selected:   {s.num_selected}/{s.num_obs}")

    ng = result.orbit.non_grav
    a1 = ng.a1.to_numpy(zero_copy_only=False)[0]
    a2 = ng.a2.to_numpy(zero_copy_only=False)[0]
    print(f"Fitted A1 = {a1:.3e}  A2 = {a2:.3e}")
    print("Reference  A1 = 5.000e-13     A2 = -2.902e-14   (JPL SBDB)")

    # ── 3. Forward propagation through the 2029 flyby ───────────────
    epochs = Epochs.from_kwargs(
        mjd=[61000.0 + 5.0 * i for i in range(341)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        result.orbit,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
        tagged_covariance=True,  # enable the resolved-kind readback
    )

    # ── 4. Headline numbers ─────────────────────────────────────────
    print("\nClose approaches (Empyrean):")
    p = prop.events.periapses
    bodies = p.body.to_pylist()
    epochs_p = p.epoch.to_numpy(zero_copy_only=False)
    dists = p.distance_km.to_numpy(zero_copy_only=False)
    for i in range(len(p)):
        print(f"  {bodies[i]:6s}  MJD {epochs_p[i]:.5f}  {dists[i]:>12.0f} km")
    print("Reference (JPL CAD):")
    print("  Earth   MJD 62239.907    38,012 km    (2029-04-13 21:46 UT)")

    # ── 4b. Tagged-covariance readback at the 2029 flyby ────────────
    # The bare per-state covariance is always the linear Φ Σ₀ Φᵀ map —
    # it over-states the encounter ellipse because the 2029 flyby bends
    # the linear map hard. The resolved-kind readback carries the
    # *honest* covariance: inside the close-approach window it is the
    # Park-Scheeres second-order (Jet2 STT) ellipsoid we asked for via
    # SECOND_ORDER. Compare them at the grid epoch nearest the periapsis.
    au_km = 1.495_978_707e8
    earth = [i for i in range(len(p)) if bodies[i] == "Earth"]
    if earth:
        ca_mjd = epochs_p[earth[0]]
        grid_mjd = epochs.mjd.to_numpy(zero_copy_only=False)
        # Output rows are NOT request-ordered (encounter episodes are
        # grouped by origin), so look every table up by ITS OWN epoch
        # column — never by request-grid position.
        out_mjd = prop.states.coordinates.epoch.to_numpy(zero_copy_only=False)
        k_state = int(np.argmin(np.abs(out_mjd - ca_mjd)))

        # σ_pos = sqrt(trace of the 3×3 position block), AU → km.
        def pos_sigma_km(cov6x6: np.ndarray) -> float:
            return float(np.sqrt(cov6x6[:3, :3].trace())) * au_km

        print(
            f"\nFlyby covariance readback (Empyrean, grid MJD {out_mjd[k_state]:.3f}):"
        )
        linear = prop.states.coordinates.covariance.to_matrix()[k_state]
        print(f"  bare linear        sigma_pos = {pos_sigma_km(linear):>10.0f} km")

        series = prop.tagged_covariance_series(0)
        series_mjd = np.array([tc.epoch_mjd_tdb for tc in series])
        resolved = series[int(np.argmin(np.abs(series_mjd - ca_mjd)))]
        print(
            f"  resolved {resolved.kind.value:<12s} sigma_pos = "
            f"{pos_sigma_km(np.asarray(resolved.matrix)):>10.0f} km"
        )
        if resolved.mean_shift_prop is not None:
            shift = np.asarray(resolved.mean_shift_prop)
            shift_km = float(np.linalg.norm(shift[:3])) * au_km
            print(f"  2nd-order mean shift |dmu_prop| = {shift_km:>8.0f} km")

    # B-plane geometry is computed by a separate call — dedicated
    # propagation with the requested uncertainty method per body.
    b_planes = empyrean.compute_b_planes(
        result.orbit,
        end_epoch=epochs.mjd.to_numpy(zero_copy_only=False)[-1],
        methods=[UncertaintyMethod.SECOND_ORDER],
        body_filter=["Earth"],
    )
    print("\n2029 Earth B-plane geometry (Empyrean):")
    body = b_planes.body.to_pylist()
    bt = b_planes.b_dot_t_km.to_numpy(zero_copy_only=False)
    br = b_planes.b_dot_r_km.to_numpy(zero_copy_only=False)
    sm = b_planes.semi_major_3sig_km.to_numpy(zero_copy_only=False)
    # (Apophis fixture has just the Earth row, but the filter matches the Bennu pattern.)
    for i in range(len(b_planes)):
        if body[i] == "Earth":
            print(f"  B*T = {bt[i]:>10.0f} km")
            print(f"  B*R = {br[i]:>10.0f} km")
            print(f"  3-sigma semi-major = {sm[i]:>8.1f} km")
    print("(B-plane uncertainty input to any downstream resonant-return analysis.)")


# spielberg:snippet:end


if __name__ == "__main__":
    main()
