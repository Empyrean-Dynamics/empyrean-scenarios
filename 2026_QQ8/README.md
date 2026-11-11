# 2026 QQ8: seen after the pass: sunlight and a captured flyby

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2026_QQ8/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs, or open it in Colab with the
badge above.

## The story

2026 QQ8 is an Aten asteroid a few meters across. It was first observed on
2026-08-19 from Piszkéstető Observatory, Hungary (MPC station K88, the first
row of the Minor Planet Center record), 22 hours after it passed 537,055 km from Earth, 1.40 times the
distance to the Moon, at 1.15 km/s. By the engine's standard capture test
(negative geocentric energy within three Hill radii) Earth held it for 226
days, from 2026-04-26 to 2026-12-08 (TDB, to the day: the grid is one day),
but it never made a full revolution of Earth: it was a temporarily captured *flyby*, not a captured
orbiter (not a mini-moon, unlike 2020 CD3).

Thirty-nine observations from ten stations over nine nights are enough to
measure a radiation-pressure push at 3.0 sigma. The scenario fits that term
from scratch on the brand-new arc and compares it with JPL's solution without
borrowing it. The encounter was observed only afterward, so the dynamics
before the first observation are computed backward, with a stated
uncertainty.

## What the script does

1. **Queries the Minor Planet Center** for 2026 QQ8 and keeps the observations
   through 2026-11-07T23:59 UTC, the arc the published numbers use: 39 optical
   observations (24 of them carry a stated sigma). A fit of position and
   velocity alone, with the engine's default weighting (the VFCC2017 preset,
   station floors, with nightly de-weighting within 0.5 days; the Python and
   Rust programs both use that default and print the preset they run), leaves
   an RMS of 0.532 arcsecond in right ascension and 0.619 in declination, with
   a reduced chi-squared of 0.275: the default weights are looser than the
   actual scatter. A per-station table shows the weighting at work: for each of
   the ten stations the number of observations, the median stated sigma, the
   median sigma the fit applies (0.8 to 1.5 arcsecond, against stated values of
   0.06 to 1.11) and the median absolute right-ascension residual (0.12 to 1.05
   arcsecond). Stations that state nothing (K88, L01) are weighted from the
   preset alone, and the stated sigmas of the others are raised to the station
   floors.

2. **Fits the solar-radiation-pressure area-to-mass ratio together with the
   state**, from a wide prior (1e-2 au and 1e-4 au/d on the state; on the ratio a mean
   of the 1e-4 m^2/kg seed and a sigma of 1e-2 m^2/kg, which keeps 0.05% of the prior's information) and never from
   JPL's solution. The ratio is (6.608 +/- 2.178)e-4 m^2/kg, a 3.0 sigma
   detection, and chi-squared falls by 9.2 for the one added parameter. The
   same force is JPL's A1 under the inverse-square law: A1 = (1.504 +/- 0.496)e-10
   au/d^2 with K = 2.27545e-7 au/d^2 per m^2/kg (the engine's radiation-pressure
   constant, about 1367 W/m^2 divided by the speed of light), against JPL's
   1.174e-10 +/- 2.78e-11, a difference of +0.58 combined sigma.

   The sigma uses the default weights. With a reduced chi-squared of 0.149 the
   default weights are about 2.6 times looser than the residuals; scaled by the
   residuals the ratio sigma would be 0.84e-4 m^2/kg (A1 1.9e-11 au/d^2), tighter
   than JPL's. The script prints both and names the weighting.

3. **Turns the ratio into bulk-density lower bounds.** For H = 31.367 +/- 0.342
   a sphere is 3.2, 1.8 or 1.1 m across at albedo 0.05, 0.15 or 0.40. With
   area-to-mass = 1.5 / (rho D), and the ratio absorbing the reflectivity
   coefficient (so these are lower bounds), the bulk densities are at least
   717 +/- 262, 1242 +/- 454 and 2027 +/- 741 kg/m^3. The data fix a ratio, not
   an identity: for comparison, the natural object 2020 CD3 has 5.96e-4 m^2/kg
   (its A1 of 1.357e-10 au/d^2) and the Falcon 9 stage 2025-010D 2.9e-3 m^2/kg.

4. **Classifies the capture.** One capture start and one end are asserted,
   with or without the ratio fitted. The object never went beyond 1.29 Hill
   radii of Earth alone at 1 au (1,936,219 km against 1,496,557 km; the test
   allows 3), and it made 0.77 net revolutions of Earth in the Sun-Earth rotating
   frame, so N = 0. A temporarily captured orbiter makes at least one full
   revolution (Fedorets, Granvik and Jedicke 2017). The closest approach,
   2026-08-18T23:44 TDB (23:43 UTC) at 537,055 km, comes from a 0.001-day
   sampling refined by a parabola, because the engine emits no close-approach
   event for a pass made while captured: it suppresses Earth close-approach
   events during the capture.

5. **Reads how well the orbit is known** (first-order position uncertainty,
   1 sigma): 222 km when the capture begins, 115 days before the first
   observation; 2.5 km at the first observation and 2.9 km at closest approach;
   21 km at the last observation on 2026-11-07; 52 km when the capture ends; and
   427 km on 2027-10-22, 318 days later.

6. **Lists the Earth passes under 0.05 au from 1952 to 2090** on the nominal
   path, with the timing uncertainty along the path, ours beside JPL's:
   2058-12-19 at 0.0128 au, 9.96 minutes (JPL: 24.7); 2083-07-14 at 0.0310 au,
   16,022 minutes, 11 days (JPL: 12,900, 9 days); and, before the object was
   observed, 1965-04-17 at 0.0125 au, 3,803 minutes (JPL: 4,820) and
   1994-04-07 at 0.0413 au, 88 minutes (JPL: 8.3). Ours and JPL's timing
   sigmas differ by up to ten times in either direction (1994: 88 vs 8
   minutes); both are formal. The 2083 pass depends on the 2058 pass, so its timing is
   uncertain by days.
   Distances are daily-sampled minima.

## How the fit is posed

JPL's solved set is A1 only, which a Marsden solve cannot express in the
engine today. The scenario fits the same force through the area-to-mass axis:
the radiation-pressure axis and a Marsden inverse-square A1 propagate
identically (a design-time check outside these scripts, over 2026 to 2028).

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Orbit class, H | Aten, H = 31.367 +/- 0.342 | JPL SBDB, solution 2026-11-08 |
| A1 (r^-2 law) | 1.174e-10 +/- 2.777e-11 au/d^2 | JPL SBDB, solution 2026-11-08 |
| Closest approach | 2026-08-18T23:45 TDB, 0.00359 au, 1.15 km/s | JPL close-approach table |
| Capture test | negative geocentric energy within three Hill radii | Granvik, Vaubaillon and Jedicke 2012 |
| Captured orbiter test | at least one revolution of Earth in the Sun-Earth rotating frame | Fedorets, Granvik and Jedicke 2017 |
| Timing sigmas of the passes | 1965: 4,820 min; 1994: 8.3; 2058: 24.7; 2083: 12,900 | JPL close-approach table (formal) |
| Astrometry | 39 optical observations to 2026-11-07 | Minor Planet Center |

## Expected output

```
39 observations from 10 stations over 79.4 days
9 nights, 2026-08-19 to 2026-11-07; 33 observations in the first five nights, first station K88
Weighting: the engine default, preset VFCC2017 (station floors) with nightly de-weighting within 0.5 d
State-only fit: chi2/dof 0.275  RMS RA.cos(d) 0.532" Dec 0.619"  (39/39 obs)
Per station (observations, of which with a stated sigma, median stated sigma, median sigma the fit applies, median |RA residual|, arcsec):
  K88: 12 obs,  0 stated, stated  none, applied 1.500, |residual| 0.355
  204:  5 obs,  5 stated, stated 0.200, applied 1.000, |residual| 0.124
  G37:  4 obs,  4 stated, stated 0.369, applied 0.800, |residual| 0.275
  309:  3 obs,  3 stated, stated 0.180, applied 1.000, |residual| 1.047
  L01:  3 obs,  0 stated, stated  none, applied 1.000, |residual| 0.933
  M57:  3 obs,  3 stated, stated 1.110, applied 1.110, |residual| 0.333
  Z24:  3 obs,  3 stated, stated 0.300, applied 1.000, |residual| 0.182
  Z31:  3 obs,  3 stated, stated 0.219, applied 1.000, |residual| 0.228
  M21:  2 obs,  2 stated, stated 0.496, applied 1.000, |residual| 0.270
  T12:  1 obs,  1 stated, stated 0.062, applied 0.800, |residual| 0.210

Fit with the area-to-mass ratio: converged True  chi2/dof 0.149  RMS RA.cos(d) 0.376" Dec 0.510"  (39/39 obs)
Prior on the ratio: 1e-04 +/- 1e-02 m^2/kg; the fit keeps 0.05% of that prior's information
Area-to-mass ratio = 6.608e-04 +/- 2.178e-04 m^2/kg (3.0 sigma); chi2 falls by 9.2 for one parameter
  scaled by the residuals (x sqrt(chi2/dof)): +/- 8.422e-05 m^2/kg
A1 equivalent = 1.504e-10 +/- 4.96e-11 au/d^2, the same force as JPL's A1 under the r^-2 law (K = 2.27545e-07 au/d^2 per m^2/kg)
JPL A1        = 1.174e-10 +/- 2.78e-11 au/d^2 (SBDB solution 2026-11-08); difference +0.58 combined sigma

For H = 31.367 +/- 0.342, a sphere of albedo p has diameter 1329 km / sqrt(p) x 10^(-H/5). With area-to-mass = 1.5 / (rho D) and the ratio absorbing Cr, these densities are lower bounds:
  albedo 0.05:  3.2 m, bulk density   717 +/-  262 kg/m^3
  albedo 0.15:  1.8 m, bulk density  1242 +/-  454 kg/m^3
  albedo 0.40:  1.1 m, bulk density  2027 +/-  741 kg/m^3
Natural analogue 2020 CD3: A1 1.357e-10 au/d^2 = 5.96e-04 m^2/kg; the Falcon 9 stage 2025-010D: 2.9e-03 m^2/kg
Fit with the ratio: captured by Earth 2026-04-26T00:00 to 2026-12-08T00:00 TDB (226 days)
State-only (A1 = 0): captured by Earth 2026-04-26T00:00 to 2026-12-08T00:00 TDB (226 days)
Geocentric distance while captured: 537,056 to 1,936,219 km (at most 1.29 Hill radii of 1,496,557 km, Earth alone at 1 au; the capture test allows 3)
Revolutions of Earth in the Sun-Earth rotating frame: 0.77; complete revolutions N = 0
Closest approach: 2026-08-18T23:44 TDB (2026-08-18T23:43 UTC) at 537,055 km (1.40 lunar distances), speed 1.15 km/s, energy -0.085 km^2/s^2

1-sigma position uncertainty (daily samples, interpolated, first order):
  capture start                2026-04-26T00:00 TDB     222.4 km
  first observation            2026-08-19T22:09 TDB       2.5 km
  closest approach             2026-08-18T23:44 TDB       2.9 km
  last observation             2026-11-07T08:11 TDB      21.0 km
  capture end                  2026-12-08T00:00 TDB      51.5 km
  318 days after capture end   2027-10-22T00:00 TDB     427.0 km

Earth passes closer than 0.05 au (daily-sampled minima, nominal path), timing sigma along the path:
  1965-04-17 TDB  0.0125 au  +/-   3803.21 min
  1994-04-07 TDB  0.0413 au  +/-     88.28 min
  2026-05-02 TDB  0.0077 au  +/-      1.58 min
  2026-08-19 TDB  0.0036 au  +/-      0.02 min
  2026-12-14 TDB  0.0090 au  +/-      0.96 min
  2058-12-19 TDB  0.0128 au  +/-      9.96 min
  2083-07-14 TDB  0.0310 au  +/-  16021.98 min
```

The scripts query the MPC live and keep the observations through
2026-11-07T23:59 UTC, the arc the numbers are for, and the JPL constants carry
their solution date. A drift check after the snippet in `main.py` asserts that the filtered arc is
the 39 observations the numbers were computed from (by count and by a sha256 of
the sorted observation ids) and exits with an error if the MPC re-measures,
deletes or rewrites a row below the filter. The check is about the MPC record,
not the language, and the Rust program's output is byte-identical to the Python
program's, so the one check covers both.

## Data

The astrometry is the Minor Planet Center (MPC) record of 2026 QQ8, queried at
run time; the MPC holds the authoritative record. Nothing is committed beside
the scripts.

## See also

- Granvik, Vaubaillon and Jedicke 2012, "The population of natural Earth satellites": <https://ui.adsabs.harvard.edu/abs/2012Icar..218..262G/abstract>
- Fedorets, Granvik and Jedicke 2017, "Orbit and size distributions for asteroids temporarily captured by the Earth-Moon system": <https://doi.org/10.1016/j.icarus.2017.01.033>
- JPL Small-Body Database: <https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2026%20QQ8>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2026qq8>
