"""2009 BD: fitting the SRP area-to-mass ratio AMRAT.

2009 BD is a ~4 m near-Earth asteroid on an Earth-like orbit and one of
the first asteroids for which solar radiation pressure (SRP) was
detected directly from ground-based astrometry (Micheli, Tholen &
Elliott 2012, *New Astronomy* 17, 446). Because it is so small, the
Sun's radiation pressure produces a measurable transverse drift over a
multi-year arc -- the same physics that a mission would exploit, run in
reverse to *weigh* the object as an area-to-mass ratio.

Run:
    pip install "empyrean>=0.9"
    python 2009_BD/main.py

What it does:
    1. Queries JPL SBDB for 2009 BD. The current JPL solution (JPL 46)
       ships the fitted SRP not as an explicit AMRAT but as a Marsden
       radial non-grav A1 with an r^-2 law -- physically the same force.
       We convert A1 to the AMRAT seed (m^2/kg) through the standard
       radiation-pressure constant P0 = S/c at 1 au.
    2. Attaches an AMRAT prior (a wide variance) to the SBDB orbit and
       converts it to the Cartesian state ``refine`` solves in, carrying
       the SBDB covariance through the element->Cartesian Jacobian as the
       Bayesian prior. The radial slot is handed to AMRAT (A1 zeroed so
       the same force is never counted twice); the transverse A2 stays
       in the dynamics exactly as shipped -- nothing is dropped.
    3. Refines against 2009 BD's optical astrometry with the wide
       ``SolveFor(amrat)`` solve, so AMRAT is fit as a free parameter
       jointly with the state, with an honest 1-sigma from the solved
       covariance. This is the v0.9.0 fitting surface: the area-to-mass
       ratio is a *measured* quantity, not a fixed input.
    4. Reports the fitted AMRAT +/- sigma against the SBDB A1-derived
       reference and the published Micheli et al. measurement.

Authoritative cross-checks (printed inline):
    - SBDB A1-derived AMRAT reference: read from the query (JPL's fitted
      radial non-grav, converted through P0 = S/c)
    - Micheli, Tholen & Elliott (2012), *New Astronomy* 17, 446: the
      original SRP detection, AMR = (2.97 +/- 0.33)e-4 m^2/kg.
    - The fitted AMRAT should land within a few sigma of both; the point
      of the scenario is the *measured uncertainty*, not a bare point
      estimate.

NOTE: AMRAT fitting is a refine-path solve -- it needs an AMRAT-primed
orbit (``amrat_variance`` set), NOT a cold determine-from-scratch, which
the engine refuses loudly.
"""

from __future__ import annotations

# empyrean:snippet:start
import empyrean
import numpy as np
from empyrean import (
    CartesianCoordinates,
    CartesianOrbits,
    NonGravParams,
    ODConfig,
    SolveFor,
    SRPParams,
    transform_coordinates,
)

# Wide AMRAT prior (variance, (m^2/kg)^2): loose enough that the
# astrometry, not the prior, drives the fitted AMRAT. ~ (1e-3 m^2/kg)^2.
AMRAT_PRIOR_VAR = 1.0e-6
# Radiation-pressure coefficient. Fixed, never fitted -- only Cr*AMRAT
# enters the dynamics, so the fitted AMRAT absorbs Cr (the JPL AMR
# convention). 1.0 = total absorption.
CR = 1.0
# JPL ships 2009 BD's SRP as a Marsden radial A1 (au/d^2) with an r^-2
# law (ALN=1, k=0, m=2, R0=1 au) -- the same physics as SRP. Converting
# to an area-to-mass ratio: a = Cr*(A/m)*P0/r^2 with P0 = S/c the
# radiation pressure at 1 au.
AU_M = 1.495978707e11  # au in m
DAY_S = 86400.0  # day in s
P0 = 1361.0 / 2.99792458e8  # N/m^2: solar constant / c at 1 au
# The original detection: Micheli, Tholen & Elliott (2012).
MICHELI_AMRAT = 2.97e-4  # m^2/kg
MICHELI_SIGMA = 0.33e-4  # m^2/kg


def main() -> None:
    empyrean.initialize()

    # -- 1. SBDB query: fitted SRP as the Marsden radial A1 -----------
    orbits = empyrean.query_sbdb(["2009 BD"])
    ng = orbits.non_grav
    a1 = None if ng is None else float(ng.a1.to_numpy(zero_copy_only=False)[0])
    if a1 is None or not np.isfinite(a1) or a1 == 0.0:
        # Loud, not silent: without JPL's fitted radial non-grav there is
        # no seed to fit from. (JPL currently ships 2009 BD's SRP as the
        # Marsden A1; if this changes, seed AMRAT explicitly rather than
        # fabricating a value.)
        raise SystemExit(
            "SBDB returned no radial non-grav A1 for 2009 BD -- cannot "
            "seed the AMRAT fit without a starting value."
        )
    sbdb_amrat = a1 * AU_M / DAY_S**2 / P0
    print("SRP parameters (SBDB):")
    print(f"  A1    = {a1:.4e} au/d^2  (JPL's fitted radial non-grav, r^-2 law)")
    print(f"  AMRAT = {sbdb_amrat:.4e} m^2/kg  (A1 converted through P0 = S/c)")
    print(f"  Cr    = {CR:.2f}  (fixed; only Cr*AMRAT enters the dynamics)")

    # -- 2. Prime the orbit with an AMRAT prior + go Cartesian --------
    # AMRAT fitting is a refine-path solve: the input orbit must carry
    # amrat_variance -- both the trigger that opens the AMRAT column and
    # the Bayesian prior. SBDB ships the A1-derived *value*; we attach a
    # wide variance so the fit is data-driven. ``refine`` works in the
    # Cartesian state and needs the covariance as its prior, so we
    # transform the SBDB elements to Cartesian, carrying the 6x6
    # covariance through the element->Cartesian Jacobian; the force
    # params are representation invariant and re-attached unchanged.
    srp = SRPParams.from_kwargs(
        amrat=[sbdb_amrat],
        cr=[CR],
        amrat_variance=[AMRAT_PRIOR_VAR],  # v0.9.0: opens + priors the AMRAT column
    )
    # Hand the radial slot to AMRAT: A1 zeroed so the same force is never
    # counted twice, while the transverse A2 (Yarkovsky-like drift, a
    # 13-sigma detection in JPL 46) stays in the dynamics as shipped.
    non_grav = NonGravParams.from_kwargs(
        a1=[0.0],
        a2=ng.a2.to_pylist(),
        a3=ng.a3.to_pylist(),
        model=["marsden"],
        alpha=ng.alpha.to_pylist(),
        r0=ng.r0.to_pylist(),
        m=ng.m.to_pylist(),
        n=ng.n.to_pylist(),
        k=ng.k.to_pylist(),
    )
    cartesian_coords = transform_coordinates(orbits.coordinates, CartesianCoordinates)
    primed = CartesianOrbits.from_kwargs(
        orbit_id=orbits.orbit_id.to_pylist(),
        object_id=orbits.object_id.to_pylist(),
        coordinates=cartesian_coords,
        non_grav=non_grav,
        srp=srp,
    )

    # -- 3. 2009 BD optical astrometry + wide AMRAT refine -----------
    obs = empyrean.query_observations(["2009 BD"])
    print(f"\n{len(obs)} optical observations")

    cfg = ODConfig(solve_for_flags=SolveFor(amrat="solved"))
    result = empyrean.refine(primed, obs, config=cfg)

    s = result.summary
    print(f"Converged:  {result.converged}")
    print(f"chi2/dof:   {s.reduced_chi2:.3f}")
    print(f'RMS:        RA.cos(d) {s.rms_ra_arcsec:.3f}"  Dec {s.rms_dec_arcsec:.3f}"')

    # -- 4. Fitted AMRAT +/- 1 sigma (the v0.9.0 measurement) --------
    sc = result.solved_covariance
    if sc is None or sc.amrat_slot is None:
        # Loud failure, not a silent zero: the AMRAT column did not open.
        print("\nAMRAT was not recovered (no AMRAT slot in the solved covariance).")
        return
    fitted_amrat = result.orbit.srp.amrat.to_numpy(zero_copy_only=False)[0]
    amrat_sigma = float(np.sqrt(sc.matrix[sc.amrat_slot, sc.amrat_slot]))
    print(f"\nFitted AMRAT  = {fitted_amrat:.4e} +/- {amrat_sigma:.4e} m^2/kg")
    print(f"SBDB (A1)     = {sbdb_amrat:.4e} m^2/kg  (JPL's fitted A1, converted)")
    print(
        f"Micheli 2012  = {MICHELI_AMRAT:.4e} +/- {MICHELI_SIGMA:.4e} m^2/kg"
        "  (the original detection)"
    )
    print(
        "(The fit measures the area-to-mass ratio directly from the "
        "astrometry via solar radiation pressure, with an honest sigma "
        "from the solved covariance.)"
    )


# empyrean:snippet:end


if __name__ == "__main__":
    main()
