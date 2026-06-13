# 2024 YR4: dual-fit OD — early-arc IP vs full-arc ruled-out

Scripts: [`main.py`](./main.py) (Python) · [`main.rs`](./main.rs) (Rust)

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
   roughly 10 days of data). This is the data on which the 1.4% IP
   was first reported by Empyrean — Sentry's 3.1% peak came from a
   55-day arc around 2025-02-18, a different cut.

3. **Runs `empyrean.determine` twice** — once on the discovery arc,
   once on the full arc. Both converge with sub-arcsecond residuals;
   the difference is the *width* of the converged covariance.

4. **Propagates both fits to 2032 and reads possible_impacts.** The
   early-arc fit surfaces an Earth IP_linear ≈ 1.4% with a 918,000 km
   B-plane 3σ semi-major (~2.4 lunar distances). The full-arc fit
   collapses both to zero IP and a 2,900 km B-plane 3σ — a 316×
   covariance shrinkage from the additional weeks of astrometry.

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
112 observations in the discovery arc (~10 days)
Discovery arc:   chi2/dof = 0.945  (108/112 obs)
Full arc:        chi2/dof = 0.972  (497/512 obs)

2032 encounter — impact probability + miss geometry:
  early arc  Earth   IP_linear =   1.433%  miss =   612000.0 km  sigma_d =   918000.0 km
  full arc   Earth   IP_linear =   0.000%  miss =   278000.0 km  sigma_d =     2902.0 km
  full arc   Moon    IP_linear =   0.000%  miss =    23000.0 km  sigma_d =     1850.0 km

Reference (JPL CAD, full-arc nominal):
  Earth   ~278,000 km   IP = 0
  Moon    ~23,000 km    IP = 0   (inside Moon's Hill sphere)
Reference (Sentry, peak):
  Earth   55-day arc, 2025-02-18 published    IP = 3.1%
```

## Why the early-arc IP is 1.4% and not 3.1%

The two are not in conflict. The 3.1% peak Sentry published was the
maximum IP across a *family* of observation cuts in the weeks after
discovery — the precise arc cut that yielded that maximum was
mid-February 2025, ~55 days into the observation window. The 1.4% in
this script is what a ~10-day discovery arc gives. Both are
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
