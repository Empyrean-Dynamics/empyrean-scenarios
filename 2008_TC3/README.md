# 2008 TC3: 19-hour discovery arc → predicted Earth impact → meteorites

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)

## The story

2008 TC3 was the first asteroid for which an Earth impact was
predicted from the discovery arc itself. Discovered by Catalina Sky
Survey on 2008-10-06, it was tracked for ~19 hours by 27 observatories
worldwide before disappearing into the Earth's shadow. The impact
prediction — Nubian Desert, 02:45:40 UT on 2008-10-07 — was tight
enough to recover ~600 meteorite fragments on the desert floor several
months later, classified as a rare ureilite achondrite.

The TC3 event remains a benchmark for short-arc orbit determination:
19 hours of astrometry, a sub-day forward propagation, and a
predicted impact location that survived comparison with the actual
fireball-recovered fragments.

## What the script does

1. **Pulls all 883 MPC observations of 2008 TC3.** Catalina Sky
   Survey discovery + global follow-up.

2. **Runs `empyrean.determine` end-to-end.** The default pipeline
   does IOD (Gauss + Herget on observation triplets), 6-state
   differential correction, optional auto-escalation to 9-parameter
   solve if non-grav residuals warrant it, and outlier rejection.
   For TC3 the 6-state fit is more than sufficient.

3. **Propagates the determined orbit through atmospheric entry.**
   IAS15 step size adapts as Earth's gravity tightens; the event
   detector picks up the entry as an `Impact` event with surface
   coordinates and velocity at the entry interface.

4. **Reports the predicted impact lat/lon/epoch and compares.** The
   recovered-meteorites entry was 20.74° N, 32.16° E at 02:45:40 UT
   (Borovička et al. 2010); the script's predicted entry should agree
   to within the residual-driven covariance.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Discovery epoch | 2008-10-06 (~19 h pre-impact) | MPC / Catalina |
| Impact epoch | 2008-10-07 02:45:40 UT (MJD 54746.115) | Borovička+ 2010 |
| Impact location | 20.74° N, 32.16° E (Nubian Desert) | Borovička+ 2010 |
| Entry velocity | 12.4 km/s (geocentric) | Borovička+ 2010 |
| Energy | ~1 kt TNT-equivalent | Borovička+ 2010 |
| Recovered meteorites | ~600 fragments (ureilite) | Almahata Sitta |

## Expected output (rough)

```
883 observations spanning the discovery arc
chi2/dof:    0.582  (819/883 obs selected)
RMS:         RA·cos(d) 1.108"  Dec 0.590"

Predicted atmospheric entry (Empyrean):
  MJD 54746.11569  v_rel = 12.79 km/s  alt = 100 km
Reference (Borovička+ 2010):
  MJD 54746.115 (2008-10-07 02:45:40 UT) over 20.74°N 32.16°E  v = 12.4 km/s
```

A few-hundred-meter difference in predicted impact location is
consistent with the propagated covariance for a 19-hour arc, and is
genuinely impressive — it's the level of precision that lets a
meteorite-recovery expedition find fragments on the desert floor.

## See also

- [Borovička & Charvát 2010, "Meteoritic complex of asteroid 2008 TC3"](https://ui.adsabs.harvard.edu/abs/2010A%26A...507.1015B/abstract)
- [Jenniskens et al. 2009, "The impact and recovery of asteroid 2008 TC3"](https://ui.adsabs.harvard.edu/abs/2009Natur.458..485J/abstract)
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2008tc3>
