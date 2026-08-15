"""2025-010D: a Falcon 9 second stage → amateur astrometry → lunar impact.

Reproduces the 25010d explore-mode scenario from
https://empyrean-dynamics.com/explore/25010d.

Run:
    pip install empyrean
    python 2025-010D/main.py

What it does:
    1. Reads the committed public astrometry (402 obs, Project Pluto /
       Bill Gray, public domain — the MPC does not serve artificial
       objects) and slices the final nine-night tracking arc.
    2. Fits a geocentric orbit (heliocentric IOD is unphysical for an
       Earth-orbiting stage), then refines with the solar-radiation-
       pressure area-to-mass ratio as a solve-for parameter — for a
       hollow 4-tonne cylinder AMR is the dominant model term.
    3. Propagates into the Moon and reads the impact epoch and
       selenographic coordinates off the Impact event.
    4. Scores the final-arc orbit against all 402 observations — the
       residual ladder through two lunar encounters is why nobody
       (including Bill Gray) publishes one grand fit of this object.

Authoritative cross-checks (printed inline):
    - Gray, fit to this same 74-obs arc: impact 2026-08-05
      06:35:42.45 UTC at 19.577°N 266.630°E, AMR 0.0079 ± 0.0017 m²/kg
    - JPL #GA1A2/21 (radar-informed): 06:35:40 UTC ± 9 s, 19.507°N
      266.7°E, 3σ ellipse 3.4 × 0.6 km
    - Impact confirmed 2026-08-05 by VLT (Na/Li plume) and KASA Danuri
      before/after imaging near crater Einstein.
"""

from __future__ import annotations

from pathlib import Path

import empyrean

# empyrean:snippet:start
import numpy as np
from empyrean import (
    CartesianOrbits,
    Epochs,
    EventConfig,
    ODConfig,
    Origin,
    SolveFor,
    SRPParams,
    TimeScale,
)
from empyrean.od.result import (
    OriginPolicy,
    OriginPolicyMode,
    WeightingConfig,
    WeightingPreset,
)

HERE = Path(__file__).parent


def main() -> None:
    empyrean.initialize()

    # ── 1. The committed public astrometry ──────────────────────────
    # No MPC query: astrometry of recognized artificial satellites is
    # removed from public MPC holdings. These 402 observations are the
    # public-domain record compiled by Project Pluto (see README).
    obs, _ = empyrean.read_ades(str(HERE / "astrometry.psv"))
    print(f"{len(obs)} public observations (Project Pluto, public domain)")

    # Final pre-impact arc: nine nights, five stations, four continents.
    iso = obs.obs_time.to_pylist()
    final_arc = obs.apply_mask([t >= "2026-07-01" for t in iso])
    print(f"{len(final_arc)} in the final arc (2026-07-23 → 08-01)")

    # ── 2. Geocentric fit + AMR refine ──────────────────────────────
    # EXPLICIT/EARTH: heliocentric Gauss IOD is unphysical for a
    # catalogued Earth-orbiting object.
    geocentric = ODConfig(
        origin=OriginPolicy(mode=OriginPolicyMode.EXPLICIT, origin=Origin.EARTH),
        # The PSV carries no per-observation sigmas and these amateur
        # stations have no survey-weighting rules, so the catalog
        # fallback would assume ~1.5" for astrometry that fits at 0.3".
        # State the residual-matched sigma explicitly.
        weighting=WeightingConfig(
            preset=WeightingPreset.NONE, default_sigma_arcsec=0.3
        ),
    )
    fit = empyrean.determine(final_arc, config=geocentric).single()
    s = fit.summary
    print(
        f"fit: chi2/dof {s.reduced_chi2:.3f}  "
        f'RMS RA·cos(d) {s.rms_ra_arcsec:.3f}" Dec {s.rms_dec_arcsec:.3f}"  '
        f"({s.num_selected}/{s.num_obs} obs)"
    )

    # AMRAT is a refine-path solve: prime the fitted orbit with an SRP
    # prior wide enough for the artsat regime (~1e-2 m²/kg, 100× any
    # asteroid) so the astrometry, not the prior, drives the fit.
    srp = SRPParams.from_kwargs(amrat=[0.008], cr=[1.0], amrat_variance=[1.0e-4])
    primed = CartesianOrbits.from_kwargs(
        orbit_id=fit.orbit.orbit_id.to_pylist(),
        object_id=fit.orbit.object_id.to_pylist(),
        coordinates=fit.orbit.coordinates,
        srp=srp,
    )
    refined = empyrean.refine(
        primed,
        final_arc,
        config=ODConfig(
            solve_for_flags=SolveFor(amrat="solved"),
            origin=OriginPolicy(mode=OriginPolicyMode.EXPLICIT, origin=Origin.EARTH),
            weighting=WeightingConfig(
                preset=WeightingPreset.NONE, default_sigma_arcsec=0.3
            ),
        ),
    )
    sc = refined.solved_covariance
    amrat = refined.orbit.srp.amrat.to_numpy(zero_copy_only=False)[0]
    amrat_sigma = float(np.sqrt(sc.matrix[sc.amrat_slot, sc.amrat_slot]))
    print(f"Fitted AMR = {amrat:.4f} ± {amrat_sigma:.4f} m²/kg")
    print("Gray (same 74-obs arc): 0.0079 ± 0.0017 m²/kg")

    # ── 3. Into the Moon ────────────────────────────────────────────
    epochs = Epochs.from_kwargs(
        mjd=[65610.0 + 0.05 * i for i in range(120)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        refined.orbit, epochs, events=EventConfig(body_filter=[Origin.MOON])
    )
    imp = prop.events.impacts
    for i in range(len(imp)):
        epoch_utc = (
            Epochs.from_mjd(
                [imp.epoch.to_numpy(zero_copy_only=False)[i]],
                scale=TimeScale.TDB.value,
            )
            .to_utc()
            .to_iso()[0]
        )
        lat = imp.latitude_deg.to_numpy(zero_copy_only=False)[i]
        lon = imp.longitude_deg.to_numpy(zero_copy_only=False)[i] % 360.0
        print(f"\nPredicted lunar impact (Empyrean): {epoch_utc}")
        print(f"  at {lat:.3f}°N {lon:.3f}°E (selenographic)")
    print("Gray (74-obs arc):  2026-08-05T06:35:42.45Z at 19.577°N 266.630°E")
    print("JPL #GA1A2/21:      2026-08-05T06:35:40Z ± 9 s at 19.507°N 266.7°E")
    print("Confirmed:          2026-08-05 ~06:35 UTC near crater Einstein")

    # ── 4. Why there is no grand unified fit ────────────────────────
    # Score the final-arc orbit against the WHOLE public record. The
    # residuals climb five orders of magnitude through two lunar
    # encounters and a tumbling body whose effective area changed —
    # each arc earns its own fit, which is exactly how Project Pluto
    # published them.
    ev = empyrean.evaluate(refined.orbit, obs)
    r = ev.observations
    t_mjd = r.epoch_mjd_tdb.to_numpy(zero_copy_only=False)
    res_ra = r.ra_residual.to_numpy(zero_copy_only=False)
    res_dec = r.dec_residual.to_numpy(zero_copy_only=False)
    windows = [
        ("own arc   (2026 Jul-Aug)", 61244.0, 61300.0),
        ("Apr-May 2026", 61135.0, 61190.0),
        ("Dec 2025", 61020.0, 61040.0),
        ("Jan 2025 discovery", 60680.0, 60700.0),
    ]
    print("\nFinal-arc orbit scored against the full 402-obs record:")
    for label, lo, hi in windows:
        m = (t_mjd >= lo) & (t_mjd < hi)
        if m.any():
            rms = float(np.sqrt(np.nanmean(res_ra[m] ** 2 + res_dec[m] ** 2)))
            print(f'  {label:26s} RMS {rms:>12.2f}"')
    print("(Five orders of magnitude: tumbling-body SRP + two lunar")
    print(" encounters make every arc its own fit — as published.)")


# empyrean:snippet:end


if __name__ == "__main__":
    main()
