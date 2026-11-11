# 2009 BD: weighing an asteroid with sunlight (fitting the radiation-pressure push)

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2009_BD/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs, or run it in Colab with the
badge above.

## The story

2009 BD is a few-meter near-Earth asteroid (2.9 to 4 m across, depending on
the albedo solution; Mommert et al. 2014) on an Earth-like orbit. It is one
of the first asteroids for which **solar radiation pressure (SRP) was
detected directly from ground-based astrometry** (Micheli, Tholen & Elliott
2012). Because the body is so small, the momentum carried by sunlight
produces a drift large enough to measure over a multi-year arc: the
trajectory does not close under gravity alone.

That push scales with the object's **area-to-mass ratio**: a bigger
cross-section per unit mass catches more photons per kilogram and drifts
faster. Measuring it is a way to *weigh* the object, to constrain its bulk
density and, with a size estimate, to tell a solid rock from a rubble pile.
The same physics underwrites solar-sail navigation and the SRP budget every
precise NEO ephemeris has to carry.

## What the script does

1. **Queries the Minor Planet Center (MPC)** for 2009 BD's optical
   astrometry and keeps the observations between two named filters,
   `FIRST_NIGHT = "2009-01-16"` and `LAST_NIGHT = "2011-06-20T23:59"`, JPL's
   first and last night, so rows the MPC adds outside that arc cannot move
   the numbers. A cold fit of position and velocity alone, with the engine's
   default weighting (the VFCC2017 preset, station floors, with nightly
   de-weighting within 0.5 days), is the seed only: it rejected 68 of the 190
   observations (the 2011 apparition misfits without radiation pressure), so
   its RMS and chi-squared are not comparable with the fit below, which uses
   all 190.

2. **Writes JPL's solution in its own units.** JPL ships the push as the
   Marsden radial and transverse terms A1 and A2 with an r⁻² law (SBDB,
   solution of 2022-12-20, 180 observations): A1 = 5.6047e-11 ± 8.51e-12
   au/d², A2 = -1.1464e-12 ± 8.37e-14 au/d². With the engine's own
   radiation-pressure constant (4.56e-6 N/m² at 1 au, about 1367 W/m²
   divided by the speed of light), K = 2.27545e-7 au/d² per m²/kg, JPL's A1
   is an area-to-mass ratio of 2.4631e-4 ± 3.74e-5 m²/kg. The constant
   matters: the same A1 under a 1361 W/m² constant reads 2.4741e-4, a
   0.44% difference.

3. **Fits A1 and A2 with the state**, the set JPL solves, from wide priors
   and not from JPL's solution (1e-2 au and 1e-4 au/d on the state, 1e-9 and
   1e-11 au/d² on A1 and A2, about 20 and 10 times JPL's values; the fit
   keeps 0.01% and 0.02% of those priors' information). A3 is held at zero by
   a 1e-14 au/d² prior because the engine's refine has no per-axis
   fixed/solved switch today; its posterior is the prior (A3 = -1.4e-17 ± 1.0e-14
   au/d², printed beside A1 and A2) and contributes nothing, as JPL's A3 = 0.
   Two parameters are fitted, A1 and A2. All 190 observations are used, with a reduced chi-squared
   of 0.174 and an RMS of 0.408 arcsecond in right ascension and 0.553 in
   declination. The fit gives A1 = 5.3508e-11 ± 9.23e-12 au/d², which is an
   area-to-mass ratio of 2.3515e-4 ± 4.05e-5 m²/kg (A1 divided by K), and
   A2 = -1.1598e-12 ± 1.41e-13 au/d². The sigmas are formal under the default
   weights (reduced chi-squared 0.17); scaled to the residuals they are
   3.85e-12 and 5.90e-14 au/d² (the default weights are about 2.4 times looser
   than the scatter).

4. **Compares.** Our A1 differs from JPL's by -0.20 combined sigma and our
   A2 by -0.08; our sigmas are 1.1 and 1.7 times JPL's. The area-to-mass
   ratio differs from the 2012 detection ((2.97 ± 0.33)e-4 m²/kg, from a fit
   with radiation pressure only) by -1.18 combined sigma.

## How the fit is posed

The area-to-mass ratio and the radial Marsden A1 are the same force for an
r⁻² law, and the engine treats Cr x AMRAT as the A1 axis scaled by K, so the
script fits A1 and prints the ratio as A1 divided by K, never mixing a
pressure constant of its own. JPL's solved set is A1 and A2; the engine's
Marsden solve carries a third axis, A3, which a 1e-14 au/d² prior holds at
zero (the refine has no per-axis fixed/solved switch today), so it is never
counted among the fitted parameters.
The A1 axis also absorbs the radial component of the Yarkovsky effect, and
the reflectivity coefficient Cr, so the ratio is an equivalent, not a mass.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Diameter | 2.9 ± 0.3 m or 4 ± 1 m (two solutions, not separable) | Mommert et al. 2014 (Spitzer non-detection at 4.5 µm, thermophysical and non-gravitational model) |
| A1 (radial, r⁻²) | 5.6047e-11 ± 8.51e-12 au/d² | JPL SBDB, solution 2022-12-20 |
| A2 (transverse) | -1.1464e-12 ± 8.37e-14 au/d² | JPL SBDB, solution 2022-12-20 |
| Radiation-pressure constant | 4.56e-6 N/m² at 1 au, K = 2.27545e-7 au/d² per m²/kg | empyrean engine |
| Area-to-mass ratio | (2.97 ± 0.33)e-4 m²/kg (9 sigma; 108 observations, radiation pressure only) | Micheli, Tholen & Elliott 2012 |
| Observations | 190 optical, 2009-01-16 to 2011-06-20 | Minor Planet Center |

## Expected output

```
190 optical observations from 24 stations, 2009-01-16 to 2011-06-20
Weighting: the engine default, preset VFCC2017 (station floors) with nightly de-weighting within 0.5 d
State-only fit (the seed): rejected 68 of the 190 observations; chi2/dof 0.184  RMS RA.cos(d) 0.377" Dec 0.715"  on the 122 kept

Radiation-pressure constant: K = 2.27545e-07 au/d^2 per m^2/kg (4.56e-6 N/m^2 at 1 au, the engine's)
JPL A1 = 5.6047e-11 +/- 8.51e-12 au/d^2 = 2.4631e-04 +/- 3.74e-05 m^2/kg (SBDB solution 2022-12-20)
JPL A2 = -1.1464e-12 +/- 8.37e-14 au/d^2 (transverse, the Yarkovsky drift)

Fit with A1 and A2: converged True  chi2/dof 0.174  RMS RA.cos(d) 0.408" Dec 0.553"  (190/190 obs)
Priors: A1 +/- 1e-09, A2 +/- 1e-11, A3 +/- 1e-14 (the hold on A3) au/d^2; the fit keeps 0.01% and 0.02% of those priors' information
A1 = 5.3508e-11 +/- 9.23e-12 au/d^2
  = area-to-mass ratio 2.3515e-04 +/- 4.05e-05 m^2/kg (5.8 sigma), A1 / K
A2 = -1.1598e-12 +/- 1.41e-13 au/d^2
A3 = -1.42e-17 +/- 1.00e-14 au/d^2 (its prior, not a fit: the engine's refine has no per-axis fixed switch)
  scaled by the residuals (x sqrt(chi2/dof)): A1 +/- 3.85e-12, A2 +/- 5.90e-14 au/d^2
A1: ours - JPL = -0.20 combined sigma; JPL sigma 8.51e-12, ours/JPL 1.1
A2: ours - JPL = -0.08 combined sigma; JPL sigma 8.37e-14, ours/JPL 1.7
Area-to-mass ratio: ours - Micheli 2012 (2.97e-04 +/- 3.30e-05 m^2/kg, radiation pressure only) = -1.18 combined sigma
```

The scripts query the MPC live and keep the observations between
`FIRST_NIGHT` and `LAST_NIGHT`, the arc the numbers are for; the JPL
constants carry their solution date. A drift check after the snippet in
`main.py` asserts that the filtered arc is the 190 observations the numbers
were computed from (by count and by a sha256 of the sorted observation ids)
and exits with an error if the MPC re-measures, deletes or adds a row
between the filters. The check is about the MPC record, not the language,
and the Rust program's output is byte-identical to the Python program's, so
the one check covers both.

## Why a refine, not a cold determine

The Marsden terms are only identifiable when the orbit already carries a
state and covariance to update. The non-gravitational signal is a small
perturbation on top of the two-body motion. The workflow is therefore: get a
converged state (here, a cold state-only fit of the astrometry), attach the
priors, and refine.

## Data

The astrometry is the Minor Planet Center record of 2009 BD, queried at run
time; the MPC holds the authoritative record. Nothing is committed beside
the scripts.

## See also

- Micheli, M., Tholen, D. J. and Elliott, G. T. 2012, "Detection of radiation pressure acting on 2009 BD", New Astronomy 17, 446: <https://arxiv.org/abs/1106.0564>
- Mommert, M., Hora, J. L., Farnocchia, D., et al. 2014, "Constraining the physical properties of near-Earth object 2009 BD", ApJ 786, 148: <https://arxiv.org/abs/1403.7699>
- JPL Small-Body Database: <https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2009%20BD>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2009bd>
