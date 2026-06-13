# Bennu: textbook transverse non-grav A2 (≈ Yarkovsky) + 2060 Earth encounter

Scripts: [`main.py`](./main.py) (Python) · [`main.rs`](./main.rs) (Rust)

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
Farnocchia et al. 2013. That A2 implies an along-track drift of ~284 m
per orbit, and over the 50-year propagation arc to 2060 it accumulates
into a sub-km offset.

The 2060 Earth encounter is the geometric event that any future-impact
analysis is anchored on. Bennu passes ~750,000 km geocentric (about
1.95 lunar distances), and the encounter B-plane geometry is the input
that downstream resonant-return analyses (Valsecchi-Rossi-Milani 2003
keyhole catalog; deferred capability) consume. Farnocchia 2021 showed
that with the A2 measured, every Bennu impact through the year 2300 is
constrained to better than 1-in-1750 cumulative probability.

## What the script does

1. **Queries JPL SBDB for Bennu's state + 6×6 covariance.** SBDB
   returns the orbital elements + the Cartesian covariance referenced
   to its solution epoch.

2. **Patches in the published Marsden A2 (Yarkovsky-driven).** SBDB's
   asteroid solutions don't always ship the (A1, A2, A3) non-grav
   coefficients in the public payload — the script falls back to the
   Farnocchia 2021 published value (A2 = −4.6178×10⁻¹⁴ AU/d²) if the
   query result is silent. This makes the script work standalone
   regardless of SBDB's per-day non-grav-availability state.

3. **Propagates 125 years at 5-day cadence.** 5-day cadence renders
   smoothly when the camera zooms in to planet-radius scale (the
   coarser 30-day cadence produces piecewise-linear segments that
   are visible in the 3D viewer). Window is 2010 → 2086, which
   captures both the 2060 Earth encounter and the 2080 follow-up
   where covariance amplification at the 2060 close pass becomes
   visible.

4. **Reads close approaches + per-encounter B-plane geometry.** The
   headline number is the 21 km 3σ semi-major of the projected
   uncertainty ellipse at the 2060 encounter — the precision result
   Farnocchia 2021 published.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Diameter | ~490 m | OSIRIS-REx in-situ |
| Marsden A2 (≈ Yarkovsky) | −4.6178×10⁻¹⁴ AU/d² | Farnocchia et al. 2021 |
| Implied along-track drift | 284 ± 1 m / orbit | Farnocchia et al. 2021 |
| 2060 Earth CA epoch | 2060-09-23 (MJD ~73725) | JPL CAD |
| 2060 Earth CA distance | ~750,000 km (~1.95 LD) | JPL CAD |
| 2080 Earth CA distance | ~1.7 M km | JPL CAD |
| Cumulative IP through 2300 | ≤ 1 in 1,750 | Farnocchia et al. 2021 |

## Expected output (rough)

```
Object: 101955
Epoch MJD TDB: 55562.0
Marsden A2 (≈ Yarkovsky): -4.618e-14 AU/d^2
Reference                 -4.6178e-14    (Farnocchia 2021)

Close approaches (Empyrean):
  Earth   MJD 73725.103      750576 km
  Moon    MJD 73725.555      662245 km
  Earth   MJD 81029.211     1738122 km
Reference (JPL CAD nominal):
  Earth   MJD 73725 (2060-09-23)   ~750,000 km

Earth B-plane geometry (Empyrean):
  MJD 73725.103  |B| =     750576 km  3-sigma semi-major =     21.0 km
  MJD 81029.211  |B| =    1738122 km  3-sigma semi-major =   9263.4 km
(2060 B-plane uncertainty input to any downstream resonant-return analysis; 440x covariance amplification at 2080.)
```

## The 21 km result, in context

A 21 km 3σ semi-major at a 750,000 km close approach is a
positional knowledge of ~3 parts in 10⁵. To put it differently: Bennu
is a 490 m object that we know the position of, 35 years from now, to
within a ~40-Bennu-radius ellipse. That precision comes from including
the measured transverse non-grav A2 in the OD; without it, the same
propagation produces an uncertainty ellipse hundreds of km wide.

The 9,263 km B-plane uncertainty at the 2080 follow-up is gravitational
covariance amplification at close approach made quantitative — a 440×
covariance inflation produced by the 2060 close pass. Where Bennu
actually threads the 2060 B-plane controls almost everything about its
22nd-century trajectory.

## See also

- [Farnocchia et al. 2021, "Ephemeris and hazard assessment for near-Earth asteroid (101955) Bennu based on OSIRIS-REx data"](https://ui.adsabs.harvard.edu/abs/2021Icar..36914594F/abstract)
- OSIRIS-REx mission: <https://www.nasa.gov/osiris-rex>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/bennu>
