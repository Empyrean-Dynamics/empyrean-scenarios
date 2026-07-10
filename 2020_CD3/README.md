# 2020 CD3: Earth's second known mini-moon

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)

## The story

2020 CD3 is a 1–1.5 m natural object discovered by Catalina Sky
Survey on 2020-02-15. Backwards-propagation showed it had been
gravitationally captured by the Earth-Moon system since around 2017
— making it Earth's second known temporarily-captured mini-moon
after 2006 RH120 (Fedorets et al. 2020). It escaped the Earth-Moon
system in March 2020.

The CD3 event tests a propagator's ability to handle:

- **Non-Keplerian gravitational capture** — the orbit transitions in
  and out of the Earth-Moon system multiple times during the capture
  episode.
- **Dense close-approach detection** — over the ~3-year capture, the
  object made hundreds of close passes by both Earth and the Moon.
- **Inverse-square non-gravitational acceleration** — for a small
  object, solar-radiation pressure is non-trivial and the propagator
  must include it explicitly.

## What the script does

1. **Queries JPL SBDB for 2020 CD3.** The orbit ships an
   inverse-square non-grav coefficient (radiation-pressure analogue of
   the cometary A1 model) which the propagator picks up automatically.

2. **Propagates 2014 → 2022 at 1-day cadence.** Window covers the
   pre-capture cruise, the full capture episode, and post-capture
   escape. Dense-output triggers refine the trajectory automatically
   during each capture pass.

3. **Counts capture events + close approaches.** The headline numbers
   are the number of `CaptureStart` / `CaptureEnd` events (the
   transitions in and out of the Earth-Moon Hill sphere) and the total
   number of detected Earth + Moon close approaches during the
   capture episode (~116 in our fixture).

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Discovery | 2020-02-15, Catalina Sky Survey | MPC |
| Estimated diameter | 1–1.5 m | Fedorets et al. 2020 |
| Capture window | ~2017 → 2020-03 (~3 years) | Fedorets et al. 2020 |
| Mini-moon classification | Temporarily-Captured Object (TCO) | Granvik et al. 2012 |

## Expected output (rough)

```
Object: (2020 CD3)
Epoch MJD TDB: 61200.0
non-grav coefficients (SBDB):  A1 = 1.357e-10  A2 = 0.000e+00  A3 = 0.000e+00 AU/d^2

── With SBDB non-grav (A1 = 1.357e-10) ──
Capture starts: 0
Capture ends:   1
Close approaches (Earth+Moon): 264
Closest Earth approach: MJD 58577.393       13147 km

── Gravity-only control (A1 = A2 = A3 = 0) ──
Capture starts: 1
Capture ends:   0
Close approaches (Earth+Moon): 5
Closest Earth approach: MJD 58181.339       24491 km

Reference: capture period ~2017-2020 (Fedorets+ 2020).
```

The exact number of close approaches depends on the detection
threshold and the cadence; this fixture uses 1-day samples plus
encounter dense-output, which produces ~116 detected periapses across
the Earth + Moon stack.

## See also

- [Fedorets et al. 2020, "Establishing Earth's minimoon population through characterization of asteroid 2020 CD3"](https://ui.adsabs.harvard.edu/abs/2020AJ....160..277F/abstract)
- [Granvik et al. 2012, "The population of natural Earth satellites"](https://ui.adsabs.harvard.edu/abs/2012Icar..218..262G/abstract)
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2020cd3>
