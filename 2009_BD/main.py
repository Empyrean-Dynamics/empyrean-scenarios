"""2009 BD: measuring solar radiation pressure on a few-meter asteroid.

2009 BD is a few-meter near-Earth asteroid on an Earth-like orbit (2.9 to 4 m
across, depending on the albedo solution; Mommert et al. 2014) and one of the
first asteroids for which solar radiation pressure (SRP) was detected directly
from ground-based astrometry (Micheli, Tholen & Elliott 2012, *New Astronomy*
17, 446). Because it is so small, sunlight pushes it measurably over a
multi-year arc -- the same physics a mission would exploit, run in reverse to
*weigh* the object as an area-to-mass ratio.

Run:
    pip install empyrean
    python 2009_BD/main.py

What it does:
    1. Queries the Minor Planet Center (MPC) for 2009 BD's optical
       astrometry and keeps the observations between two named filters,
       JPL's first and last night, so later or earlier rows cannot move
       the numbers. A cold state-only fit (no JPL solution) gives the seed
       orbit.
    2. Refines that orbit with the radial and transverse Marsden
       non-gravitational terms A1 and A2 as free parameters, the set JPL
       solves, from wide priors on the state and on A1 and A2 and not from
       JPL's solution. A3 is held at zero by a tight prior.
    3. Reports the fitted A1 in JPL's own units (au/d^2) beside the
       area-to-mass ratio it implies under the engine's radiation-pressure
       constant, with their sigmas, against JPL's published solution and
       the 2012 detection.

Authoritative cross-checks (printed inline, labeled, never fitted to):
    - JPL SBDB solution of 2022-12-20 (180 observations, 2009-01-16 to
      2011-06-20): A1 and A2 with their 1 sigma
    - Micheli, Tholen & Elliott (2012): AMR = (2.97 +/- 0.33)e-4 m^2/kg,
      from a radiation-pressure-only fit to 108 observations
"""

from __future__ import annotations

import hashlib
import sys

# empyrean:snippet:start
import empyrean
import numpy as np
from empyrean import (
    CartesianOrbits,
    CovarianceKind,
    JointFunctional,
    JointProvenance,
    JointQuality,
    NonGravParams,
    ODConfig,
    PackedJoint,
    PackedJoints,
    SolveFor,
    SolveForParams,
)

# Two named filters on the MPC record, which is queried live below. Each keeps
# the observations at or after / at or before a UTC time: JPL's first and last
# night, so a row the MPC adds outside the arc cannot move the numbers.
FIRST_NIGHT = "2009-01-16"
LAST_NIGHT = "2011-06-20T23:59"
# The engine's radiation-pressure constant: 4.56e-6 N/m^2 at 1 au (about 1367
# W/m^2 / c). One m^2/kg of area-to-mass ratio is this many au/d^2 of radial
# acceleration at 1 au under the r^-2 law, JPL's A1 convention.
K_SRP = 4.56e-6 * 86400.0**2 / 1.495978707e11  # au/d^2 per m^2/kg
# JPL SBDB solution of 2022-12-20 (SBDB-published values, nothing derived by
# empyrean; 180 observations, 2009-01-16 to 2011-06-20): the Marsden radial and
# transverse terms with their 1 sigma, au/d^2. The law is r^-2: ALN = 1,
# R0 = 1 au, m = 2, n = 0, k = 0.
JPL_A1, JPL_A1_SIGMA = 5.604736985528152e-11, 8.508e-12
JPL_A2, JPL_A2_SIGMA = -1.14638955920583e-12, 8.37e-14
# Micheli, Tholen and Elliott 2012 (108 observations, radiation pressure only).
MICHELI_AMR, MICHELI_SIGMA = 2.97e-4, 0.33e-4  # m^2/kg
# Priors, wide on every axis and not JPL's solution: 1e-2 au and 1e-4 au/d on the
# state, 1e-9 and 1e-11 au/d^2 on A1 and A2 (about 20 and 10 times JPL's values).
# A3 is held at zero by a tight prior, as in JPL's solved set (A1 and A2): the
# engine's refine has no per-axis fixed/solved switch today, so its posterior
# is the prior and contributes nothing.
STATE_SIGMA = (1e-2, 1e-2, 1e-2, 1e-4, 1e-4, 1e-4)
A_SIGMA = (1e-9, 1e-11, 1e-14)  # A1, A2, A3


def sci(x, digits):
    return f"{x:.{digits}e}"


def main():
    empyrean.initialize()

    # -- 1. The record and a cold state-only fit -----------------------
    obs = empyrean.query_observations(["2009 BD"])
    obs = obs.apply_mask(
        [FIRST_NIGHT <= t <= LAST_NIGHT for t in obs.obs_time.to_pylist()]
    )
    times = obs.obs_time.to_pylist()
    print(
        f"{len(obs)} optical observations from {len(set(obs.stn.to_pylist()))} "
        f"stations, {min(times)[:10]} to {max(times)[:10]}"
    )
    config = ODConfig(solve_for=SolveForParams.STATE_ONLY)
    weighting = config.weighting
    print(
        f"Weighting: the engine default, preset {weighting.preset.name} (station "
        f"floors) with nightly de-weighting within "
        f"{weighting.additional_layers[0].max_gap_days:.1f} d"
    )
    base = empyrean.determine(obs, config=config).single()
    s0 = base.summary
    print(
        f"State-only fit (the seed): rejected {s0.num_rejected} of the {s0.num_obs} "
        f"observations; chi2/dof {s0.reduced_chi2:.3f}  "
        f'RMS RA.cos(d) {s0.rms_ra_arcsec:.3f}" Dec {s0.rms_dec_arcsec:.3f}"  '
        f"on the {s0.num_selected} kept"
    )

    # -- 2. JPL's solution, in its own units and as an area-to-mass ratio
    print(
        f"\nRadiation-pressure constant: K = {K_SRP:.5e} au/d^2 per m^2/kg "
        "(4.56e-6 N/m^2 at 1 au, the engine's)"
    )
    print(
        f"JPL A1 = {sci(JPL_A1, 4)} +/- {sci(JPL_A1_SIGMA, 2)} au/d^2 "
        f"= {sci(JPL_A1 / K_SRP, 4)} +/- {sci(JPL_A1_SIGMA / K_SRP, 2)} m^2/kg "
        "(SBDB solution 2022-12-20)"
    )
    print(
        f"JPL A2 = {sci(JPL_A2, 4)} +/- {sci(JPL_A2_SIGMA, 2)} au/d^2 "
        "(transverse, the Yarkovsky drift)"
    )

    # -- 3. Fit A1 and A2 with the state --------------------------------
    var = np.zeros((9, 9))
    var[:6, :6] = np.diag(np.square(STATE_SIGMA))
    var[6:, 6:] = np.diag(np.square(A_SIGMA))
    tri = [var[i, j] for i in range(9) for j in range(i + 1)]
    prior = PackedJoint(
        layout_present=0b111,  # the Marsden A1, A2, A3 axes
        layout_considered=0,
        layout_marginalized=0,
        width=9,
        tri=np.asarray(tri, dtype=np.float64),
        kind=CovarianceKind.LINEAR,
        quality=JointQuality.POSITIVE_DEFINITE,
        cov_rank=0,
        cov_null_axes=0,
        cov_min_eig_corr=float("nan"),
        functional=JointFunctional.STATE,
        provenance=JointProvenance.DERIVED,
        asserted_source=None,
    )
    primed = CartesianOrbits.from_kwargs(
        orbit_id=base.orbit.orbit_id.to_pylist(),
        object_id=base.orbit.object_id.to_pylist(),
        coordinates=base.orbit.coordinates,
        non_grav=NonGravParams.from_kwargs(
            a1=[0.0],
            a2=[0.0],
            a3=[0.0],
            model=["marsden"],
            alpha=[1.0],
            r0=[1.0],
            m=[2.0],
            n=[0.0],
            k=[0.0],
        ),
        covariance=PackedJoints.from_joints([prior]),
    )
    fit = empyrean.refine(
        primed, obs, config=ODConfig(solve_for_flags=SolveFor(marsden="solved"))
    )
    sc = fit.solved_covariance
    ng = fit.orbit.non_grav
    a1 = float(ng.a1.to_numpy(zero_copy_only=False)[0])
    a2 = float(ng.a2.to_numpy(zero_copy_only=False)[0])
    a3 = float(ng.a3.to_numpy(zero_copy_only=False)[0])
    slot = sc.marsden_slot
    a1_sigma = float(np.sqrt(sc.matrix[slot, slot]))
    a2_sigma = float(np.sqrt(sc.matrix[slot + 1, slot + 1]))
    a3_sigma = float(np.sqrt(sc.matrix[slot + 2, slot + 2]))
    s = fit.summary
    print(
        f"\nFit with A1 and A2: converged {fit.converged}  "
        f"chi2/dof {s.reduced_chi2:.3f}  "
        f'RMS RA.cos(d) {s.rms_ra_arcsec:.3f}" Dec {s.rms_dec_arcsec:.3f}"  '
        f"({s.num_selected}/{s.num_obs} obs)"
    )
    print(
        f"Priors: A1 +/- {sci(A_SIGMA[0], 0)}, A2 +/- {sci(A_SIGMA[1], 0)}, "
        f"A3 +/- {sci(A_SIGMA[2], 0)} (the hold on A3) au/d^2; "
        f"the fit keeps {100 * (a1_sigma / A_SIGMA[0]) ** 2:.2f}% and "
        f"{100 * (a2_sigma / A_SIGMA[1]) ** 2:.2f}% of those priors' information"
    )
    amr, amr_sigma = a1 / K_SRP, a1_sigma / K_SRP
    print(f"A1 = {sci(a1, 4)} +/- {sci(a1_sigma, 2)} au/d^2")
    print(
        f"  = area-to-mass ratio {sci(amr, 4)} +/- {sci(amr_sigma, 2)} m^2/kg "
        f"({amr / amr_sigma:.1f} sigma), A1 / K"
    )
    print(f"A2 = {sci(a2, 4)} +/- {sci(a2_sigma, 2)} au/d^2")
    print(
        f"A3 = {sci(a3, 2)} +/- {sci(a3_sigma, 2)} au/d^2 (its prior, not a fit: the "
        "engine's refine has no per-axis fixed switch)"
    )
    scale = np.sqrt(s.reduced_chi2)
    print(
        f"  scaled by the residuals (x sqrt(chi2/dof)): A1 +/- {sci(a1_sigma * scale, 2)}"
        f", A2 +/- {sci(a2_sigma * scale, 2)} au/d^2"
    )

    # -- 4. Against JPL's solution and the 2012 detection ---------------
    for name, v, sg, j, js in (
        ("A1", a1, a1_sigma, JPL_A1, JPL_A1_SIGMA),
        ("A2", a2, a2_sigma, JPL_A2, JPL_A2_SIGMA),
    ):
        print(
            f"{name}: ours - JPL = {(v - j) / np.hypot(sg, js):+.2f} combined sigma; "
            f"JPL sigma {sci(js, 2)}, ours/JPL {sg / js:.1f}"
        )
    print(
        f"Area-to-mass ratio: ours - Micheli 2012 ({sci(MICHELI_AMR, 2)} +/- "
        f"{sci(MICHELI_SIGMA, 2)} m^2/kg, radiation pressure only) = "
        f"{(amr - MICHELI_AMR) / np.hypot(amr_sigma, MICHELI_SIGMA):+.2f} combined sigma"
    )
    return obs


obs = main()
# empyrean:snippet:end

# Drift check, outside the snippet: the published numbers are for exactly these
# observations. If the MPC re-measures, deletes or adds a row between the two
# filters, stop instead of printing numbers for a different arc.
EXPECTED_COUNT = 190
EXPECTED_SHA256 = "26e63fb96eb8b34e2fdb7afacb0ce8c260bfbfa5f1ef79d88bf45c535ee5e523"
found_ids = "\n".join(sorted(obs.obs_id.to_pylist()))
found_sha256 = hashlib.sha256(found_ids.encode()).hexdigest()
if len(obs) != EXPECTED_COUNT or found_sha256 != EXPECTED_SHA256:
    sys.exit(
        f"The MPC record changed between the filters: expected {EXPECTED_COUNT} "
        f"observations with sha256 {EXPECTED_SHA256} of the sorted obsIDs, found "
        f"{len(obs)} with {found_sha256}. The numbers above are for a different arc."
    )
