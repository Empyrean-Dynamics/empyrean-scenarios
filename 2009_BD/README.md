# 2009 BD: weighing an asteroid with sunlight (fitting the SRP area-to-mass ratio)

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2009_BD/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs — or run it in Colab with the
badge above.

## The story

2009 BD is a tiny (~4 m) near-Earth asteroid on an Earth-like orbit. It
is one of the first asteroids for which **solar radiation pressure (SRP)
was detected directly from ground-based astrometry** (Micheli, Tholen &
Elliott 2012). Because the body is so small, the momentum carried by
sunlight produces a transverse drift large enough to measure over a
multi-year arc — the trajectory literally does not close under gravity
alone.

That drift is a direct readout of the object's **area-to-mass ratio
(AMRAT)**: a bigger cross-section per unit mass catches more photons per
kilogram and drifts faster. Fitting AMRAT from the astrometry is
therefore a way to *weigh* the object — to constrain its bulk density
and, with a size estimate, tell a solid rock from a rubble pile. The
same physics underwrites solar-sail navigation and the SRP budget every
precise NEO ephemeris has to carry.

## What the script does

1. **Queries JPL SBDB for 2009 BD.** The current JPL solution (JPL 46)
   ships the fitted SRP not as an explicit AMRAT but as a **Marsden
   radial non-grav A1** with an r⁻² law — physically the same force. The
   script converts A1 to the AMRAT seed (m²/kg) through the standard
   radiation-pressure constant P₀ = S/c at 1 au.

2. **Attaches an AMRAT prior and converts to Cartesian.** AMRAT fitting
   is a *refine-path* solve: the input orbit must carry an
   `amrat_variance` — both the trigger that opens the AMRAT column and
   the Bayesian prior. SBDB ships the A1-derived *value*; the script
   attaches a wide variance so the fit is data-driven. `refine` works in
   the Cartesian state, so the SBDB elements are transformed to Cartesian
   **carrying the covariance** through the element→Cartesian Jacobian.
   The radial slot is handed to AMRAT (A1 zeroed so the same force is
   never counted twice) while the transverse A2 stays in the dynamics
   exactly as shipped, so nothing is dropped.

3. **Refines against 2009 BD's optical astrometry** with the wide
   `SolveFor(amrat)` solve, fitting AMRAT as a free parameter jointly
   with the state, with an honest 1σ from the solved covariance.

4. **Reports the fitted AMRAT ± σ** against the SBDB A1-derived
   reference and the Micheli, Tholen & Elliott (2012) measurement. The
   point of the scenario is the *measured uncertainty*, not a bare point
   estimate: the area-to-mass ratio is a measured quantity in v0.9.0,
   not a fixed input.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Diameter | ~4 m | Micheli, Tholen & Elliott 2012 |
| SRP AMRAT (seed) | A1 from the query, converted through P₀ = S/c | JPL SBDB (JPL 46) |
| SRP AMRAT | (2.97 ± 0.33)e-4 m²/kg | Micheli, Tholen & Elliott 2012 |
| SRP detection | first ground-based asteroid SRP measurement | Micheli, Tholen & Elliott 2012 |

## Why a refine, not a cold determine

AMRAT (like the cometary time delay DT) is only identifiable when the
orbit already carries a state and covariance to update — the SRP signal
is a small perturbation on top of the gravitational two-body motion. A
cold determine-from-scratch has no AMRAT prior to open the column and
the engine refuses it loudly rather than fitting an unconstrained
area-to-mass. The workflow is therefore: get a converged state (here,
from SBDB), attach the AMRAT prior, and refine.

## See also

- [Micheli, Tholen & Elliott 2012, "Detection of radiation pressure acting on 2009 BD", *New Astronomy* 17, 446](https://ui.adsabs.harvard.edu/abs/2012NewA...17..446M/abstract)
