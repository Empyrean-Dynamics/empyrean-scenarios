# Apophis: end-to-end orbit determination + 2029 Earth flyby

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Jupyter](https://img.shields.io/badge/Jupyter-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/99942_Apophis/main.ipynb)

The notebook twin [`main.ipynb`](./main.ipynb) is rendered on GitHub with
executed outputs, or opens directly in Colab via the badge above.

## The story

99942 Apophis is a ~340 m near-Earth asteroid discovered in 2004. It
briefly held the highest impact probability ever recorded for an
asteroid (~2.7% for 2029, before tracking pinned it down) and remains
the most-observed potentially-hazardous asteroid in the catalogue. Its
trajectory carries it inside the geosynchronous belt on 2029-04-13 —
about 38,000 km geocentric, naked-eye visible from parts of Europe and
Africa.

The 2029 flyby is also a textbook resonant-return / keyhole problem:
where Apophis threads the 2029 B-plane sets up (or rules out) every
follow-on Earth approach for the rest of the century. The "2068
keyhole" was a 600 m wide region of the 2029 B-plane that would have
deflected Apophis onto a 2068 impact trajectory; radar astrometry
through 2021 ruled it out, and Apophis was removed from the JPL Sentry
risk list on 2021-02-21.

## What the script does

1. **Pulls all available MPC astrometric observations.** Goldstone
   radar delay/Doppler from 2005, 2013, and 2021 plus tens of thousands
   of optical CCD measurements going back to discovery. Roughly 9,500
   observations spanning a 21-year arc.

2. **Runs `empyrean.determine` with 9-parameter solve.**
   `solve_for=STATE_AND_NONGRAV` forces the converged orbit to carry
   not just the 6-state Cartesian but the (A1, A2, A3) Marsden
   non-gravitational coefficients. For Apophis the transverse A2 is
   consistent with Yarkovsky thermal recoil and is fit empirically with
   inverse-square g(r); a real first-principles Vokrouhlický thermal
   model is on the engine roadmap. (The radial A1 is weakly
   constrained by astrometry and drifts with the arc — expect it to
   disagree with SBDB's value by tens of percent; the transverse A2,
   which carries the Yarkovsky signal, is the one that should and
   does match.) The hyperdual integrator computes
   the (O−C) Jacobian against all 9 parameters analytically — no
   finite-differencing of the 21-year arc.

3. **Forward-propagates with second-order STT.** State Transition
   Tensors carry the second-order term so the projected covariance at
   the 2029 encounter is accurate even where linear propagation
   breaks down (and around a deep planetary flyby, it does).

4. **Reads close approaches + B-plane geometry.** Headline numbers:
   geocentric distance + epoch of the 2029 flyby, B·R / B·T components,
   and the 3σ semi-major of the projected uncertainty ellipse on the
   B-plane.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| 2029 Earth CA epoch | 2029-04-13 21:46 UT (MJD 62239.907) | JPL CAD |
| 2029 Earth CA distance | 38,012 km (≈6 R⊕) | JPL CAD |
| Marsden A1 | ≈ 5×10⁻¹³ AU/d² (radial) | JPL SBDB |
| Marsden A2 (≈ Yarkovsky) | ≈ −2.9×10⁻¹⁴ AU/d² (transverse) | JPL SBDB |
| Sentry removal | 2021-02-21 | NASA / CNEOS |
| Cleared through | 2121 (100-year horizon at removal) | NASA / CNEOS |

The 2029 flyby is the geometric event that any future-impact analysis
is anchored on. The script's printed B-plane uncertainty (3σ semi-major
~5,300 km for the 9-parameter state + non-grav solve — the extra
non-gravitational degrees of freedom carry most of that width) is the
input geometry that downstream resonant-return / keyhole analyses
(Valsecchi-Rossi-Milani 2003) consume — Empyrean produces the input;
the keyhole catalog itself is a separate roadmap item.

## Expected output (rough)

```
9527 optical + 50 radar (delay/Doppler)
Converged:  True
chi2/dof:   0.080
RMS:        RA·cos(d) 0.514"  Dec 0.473"
Selected:   9569/9577
Fitted A1 = -4.108e-12  A2 = -2.849e-14
Reference  A1 = 5.000e-13     A2 = -2.902e-14   (JPL SBDB)
Fitted H  = 18.42 +/- 0.20  (model PhotometryModel.HG12, chi2_r 1.83)
Reference  H = 19.09   (JPL SBDB)

Close approaches (Empyrean):
  Earth   MJD 62239.90709         38016 km
  Moon    MJD 62240.60579         95942 km
Reference (JPL CAD):
  Earth   MJD 62239.907    38,012 km    (2029-04-13 21:46 UT)

Flyby covariance readback (Empyrean, grid MJD 62240.000):
  bare linear        sigma_pos =         25 km
  resolved second_order sigma_pos =       2582 km
  2nd-order mean shift |dmu_prop| =       39 km

2029 Earth B-plane geometry (Empyrean):
  B*T =     -37502 km
  B*R =      -6232 km
  3-sigma semi-major =     46.8 km
(B-plane uncertainty input to any downstream resonant-return analysis.)
```

(Exact numbers will drift with new astrometry.)

## See also

- [Farnocchia et al. 2013, "Yarkovsky-driven impact risk analysis for asteroid (99942) Apophis"](https://ui.adsabs.harvard.edu/abs/2013Icar..224..192F/abstract)
- JPL Sentry: <https://cneos.jpl.nasa.gov/sentry/details.html#?des=99942>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/apophis>
