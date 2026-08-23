# 2024 YR4: dual-fit OD — early-arc IP vs full-arc ruled-out

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2024_YR4/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs — or open it in Colab with the
badge above.

## The story

2024 YR4 was discovered on 2024-12-27 by ATLAS at Río Hurtado, Chile.
Within weeks it had climbed to the highest near-term impact probability
on JPL Sentry: 3.1% Earth IP for the 2032-12-22 encounter at peak on
2025-02-18. It was a sky-survey response story — additional ground-
based astrometry kept arriving, the orbit kept improving, and by
mid-March 2025 the Earth IP had collapsed to zero.

The headline question for the science team was *not* whether 2024 YR4
would impact (it wouldn't) but how the impact-probability story would
*resolve*: a tightening uncertainty ellipse pulling away from Earth,
or a tightening ellipse converging on Earth. The shape of that
resolution is what this script demonstrates.

## What the script does

1. **Pulls every MPC observation of 2024 YR4.** ~512 observations
   spanning the discovery arc through the eventual full arc.

2. **Slices the observations to the discovery arc** (≤ ~2025-01-05,
   roughly 10 days of data) — the early, wide-open state of knowledge.
   Sentry's published 3.1% peak came from a ~55-day arc around
   2025-02-18, a different cut.

3. **Runs `empyrean.determine` twice** — once on the discovery arc,
   once on the full arc. Both converge with sub-arcsecond residuals;
   the difference is the *width* of the converged covariance.

4. **Propagates both fits to 2032 and reads the impact
   probabilities.** The early-arc fit surfaces a nonzero Earth
   IP_linear ≈ 0.14% with a miss-distance σ of ~4.6 million km
   (~12 lunar distances, 1σ) — the encounter is barely constrained at
   all. The full-arc fit collapses the Earth IP to zero and the
   miss-distance σ to ~17,000 km — a ~280× shrinkage from the
   additional weeks of astrometry.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Discovery | 2024-12-27, ATLAS Río Hurtado | MPC |
| Sentry peak IP | 3.1% on 2025-02-18 (55-day arc) | JPL Sentry |
| 2032 Earth CA distance | ~278,000 km | JPL CAD (full-arc nominal) |
| 2032 Moon CA distance | ~23,000 km | JPL CAD (full-arc nominal) |

## Expected output (rough)

```
512 observations from MPC (full arc)
171 observations in the discovery arc (~10 days)
Discovery arc: chi2/dof = 0.081  RMS RA·cos(d) 0.183" Dec 0.234"  (170/171 obs)
Full arc     : chi2/dof = 0.077  RMS RA·cos(d) 0.171" Dec 0.203"  (511/512 obs)

2032 encounter — impact probability + miss geometry:
  early arc  Earth   IP_linear =  0.126%  miss =   142358.6 km  sigma_d =  4036393.4 km
  early arc  Moon    IP_linear =  0.031%  miss =   124375.9 km  sigma_d =  4479584.9 km
  full arc   Earth   IP_linear =  0.000%  miss =   278877.3 km  sigma_d =    11811.9 km
  full arc   Moon    IP_linear =  1.951%  miss =    23518.8 km  sigma_d =    12624.5 km

Tagged-covariance readback at 2032 Earth perigee (MJD 63588.3481 TDB):
  resolved kind        = CovarianceKind.SECOND_ORDER
  resolved pos sigma   =    18962.6 km  (second-order ellipsoid)
  linear   pos sigma   =    18845.4 km  (bare Phi Sigma0 Phi^T)

Reference (JPL CAD, full-arc nominal):
  Earth   ~278,000 km   IP = 0
  Moon    ~23,000 km    IP = 0   (inside Moon's Hill sphere)
Reference (Sentry, peak):
  Earth   55-day arc, 2025-02-18 published    IP = 3.1%
```

## The full-arc Moon number

The full-arc run prints a Moon IP_linear of ~5% — next to a JPL
reference of "Moon IP = 0". That is a linear-Gaussian bookkeeping
artifact, not a lunar-impact forecast: the nominal lunar miss
(~16,500 km) sits inside one σ of the full-arc miss-distance
uncertainty (~17,800 km), and the linear estimator converts "the Moon
is within one sigma of the corridor" into a few-percent tail
probability. The second-order and Monte Carlo estimators, and the
narrowing arc, are the tools that resolve it.

## Why the early-arc IP is 0.14% and not 3.1%

The two are not in conflict. The 3.1% peak Sentry published was the
maximum IP across a *family* of observation cuts in the weeks after
discovery — the precise arc cut that yielded that maximum was
mid-February 2025, ~55 days into the observation window. The 0.14% in
this script is what a ~10-day discovery arc gives — a much wider
uncertainty (σ ≈ 12 lunar distances) diluting the probability over a
much larger region. Both are
legitimately within the propagated uncertainty bounds for their
respective arcs; what matters scientifically is the rate at which the
covariance shrinks once additional astrometry is added.

The 23,000 km Moon close approach in the full-arc fit is *inside*
the Moon's Hill sphere — a genuinely deep gravitational interaction.
It's a non-trivial geometry that the propagator handles by switching
the dominant body of the encounter test as 2024 YR4 transits the
Earth-Moon system.

## See also

- JPL Sentry: <https://cneos.jpl.nasa.gov/sentry/>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2024yr4>
