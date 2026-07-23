# Bennu: measuring Yarkovsky drift from optical + radar astrometry + the 2060 Earth encounter

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/101955_Bennu/main.ipynb)

Notebook twin: [`main.ipynb`](./main.ipynb) — rendered on GitHub with
executed outputs, or open it in Colab with the badge above.

## The story

101955 Bennu is a ~490 m near-Earth asteroid and the target of NASA's
OSIRIS-REx sample-return mission, which deposited its sample capsule
in Utah on 2023-09-24. Bennu is the textbook transverse non-grav A2
detection — radar astrometry from 1999, 2005, and 2011 plus OSIRIS-REx
spacecraft-tracking residuals constrained A2 = −4.62×10⁻¹⁴ AU/d² with
sub-1% precision (Farnocchia et al. 2021). The physical interpretation
is Yarkovsky thermal recoil from anisotropic re-radiation of absorbed
sunlight; Empyrean fits the empirical Marsden A1/A2/A3 form with
inverse-square g(r), capturing Yarkovsky's leading 1/r² scaling per
Farnocchia et al. 2013 — and this scenario MEASURES A2 from the
astrometry rather than quoting it. That A2 implies an along-track drift of ~285 m
per year (−284.6 ± 0.2 m/yr, Farnocchia et al. 2021), and over the
50-year propagation arc to 2060 it accumulates into a ~14 km offset.

The 2060 Earth encounter is the geometric event that any future-impact
analysis is anchored on. Bennu passes ~750,000 km geocentric (about
1.95 lunar distances), and the encounter B-plane geometry is the input
that downstream resonant-return analyses (Valsecchi-Rossi-Milani 2003
keyhole catalog; deferred capability) consume. Farnocchia 2021 showed
that with the A2 measured, every Bennu impact through the year 2300 is
constrained to better than 1-in-1750 cumulative probability.

## What the script does

1. **Pulls the astrometry: MPC optical + JPL radar.** ~600 optical
   observations spanning 1999–2025, plus the 29 Arecibo/Goldstone
   delay/Doppler measurements from the 1999, 2005, and 2011
   apparitions — radar ranging pins the line-of-sight distance at the
   ~100 m level.

2. **Measures A2 with a two-stage fit.** A state-only fit over the full
   arc would silently absorb the drift into the epoch state — aliasing
   the very signal being measured — so the epoch state is first
   anchored on the 1999–2000 discovery apparition (optical + its radar
   ranging), then a joint state + Marsden refine runs over the full
   26-year optical arc with the A-block seeded at zero and opened by a
   Bayesian prior: radial/normal components pinned, transverse A2 wide.
   The astrometry, not the prior, measures the drift, and the solved
   covariance delivers an honest 1σ on it.

3. **Propagates ~72 years (2011 → 2083) at 5-day cadence.** 5-day cadence renders
   smoothly when the camera zooms in to planet-radius scale (the
   coarser 30-day cadence produces piecewise-linear segments that
   are visible in the 3D viewer). Window is 2010 → 2086, which
   captures both the 2060 Earth encounter and the 2080 follow-up
   where covariance amplification at the 2060 close pass becomes
   visible.

4. **Reads close approaches + per-encounter B-plane geometry.** The
   3σ semi-major of the projected uncertainty ellipse at the 2060
   encounter is now traceable end-to-end to the fit in step 2 — the
   ellipse is exactly what this scenario's own astrometry supports,
   not a quoted catalog covariance.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Diameter | ~490 m | OSIRIS-REx in-situ |
| Marsden A2 (≈ Yarkovsky) | −4.6178×10⁻¹⁴ AU/d² | Farnocchia et al. 2021 |
| Implied along-track drift | −284.6 ± 0.2 m / year | Farnocchia et al. 2021 |
| 2060 Earth CA epoch | 2060-09-23 (MJD ~73725) | JPL CAD |
| 2060 Earth CA distance | ~750,000 km (~1.95 LD) | JPL CAD |
| 2080 Earth CA distance | ~2.34 M km (2080-09-22) | JPL CAD |
| Cumulative IP through 2300 | ≤ 1 in 1,750 | Farnocchia et al. 2021 |

## Expected output (rough)

```
603 optical + 29 radar (delay/Doppler)
Anchor (1999-2000, 217 optical + 10 radar): chi2/dof 0.22
Converged:  True
chi2/dof:   0.200
RMS:        RA·cos(d) 0.748"  Dec 0.351"
Fitted A2 (≈ Yarkovsky) = -2.837e-14 +/- 1.1e-14 AU/d^2
Reference                 -4.618e-14 AU/d^2   (Farnocchia 2021,
                          radar-complete joint solution)

Close approaches (Empyrean):
  Earth   MJD 73725.025        749738 km
  Earth   MJD 81029.197       2054181 km
Reference (JPL CAD nominal):
  Earth   MJD 73725 (2060-09-23)   ~750,000 km

Earth B-plane geometry (Empyrean):
  MJD 73725.025  |B| =     749738 km  3-sigma semi-major =    294.7 km
  MJD 81029.197  |B| =    2054181 km  3-sigma semi-major = 134233.2 km
(2060 B-plane uncertainty input to any downstream resonant-return analysis; 3-sigma ellipse grows 455x by 2080.)
```

## The measurement, in context

The fitted A2 = −2.8 ± 1.1 ×10⁻¹⁴ AU/d² is a 2.6σ detection of the
Yarkovsky drift, consistent (1.6σ) with Farnocchia 2021's
−4.618×10⁻¹⁴. The published value's sub-1% precision comes from a
radar-complete joint solution plus OSIRIS-REx spacecraft tracking —
data this scenario's two-stage ladder doesn't fold into the joint
solve — so the honest comparison is sign, magnitude, and consistency,
not equality.

The ~295 km 3σ semi-major at the 2060 encounter is what THIS fit's
covariance supports: positional knowledge of ~4 parts in 10⁴, 35 years
out, from ground-based astrometry alone. (JPL's OSIRIS-REx-era
solution reaches ~20 km on the same encounter.) The ~134,000 km
uncertainty at the 2080 follow-up is gravitational covariance
amplification at close approach made quantitative — the 3σ ellipse
grows ~455× through the 2060 close pass (the script prints the exact
ratio). Where Bennu actually threads the 2060 B-plane controls almost
everything about its 22nd-century trajectory.

## See also

- [Chesley et al. 2014, "Orbit and bulk density of the OSIRIS-REx target asteroid (101955) Bennu"](https://ui.adsabs.harvard.edu/abs/2014Icar..235....5C/abstract) — the radar-anchored Yarkovsky detection this scenario retraces
- [Farnocchia et al. 2021, "Ephemeris and hazard assessment for near-Earth asteroid (101955) Bennu based on OSIRIS-REx data"](https://ui.adsabs.harvard.edu/abs/2021Icar..36914594F/abstract)
- OSIRIS-REx mission: <https://www.nasa.gov/osiris-rex>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/bennu>
