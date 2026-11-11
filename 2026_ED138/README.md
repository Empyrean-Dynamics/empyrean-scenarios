# 2026 ED138: a large trans-Neptunian object, 49 years of astrometry

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2026_ED138/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs, or open it in Colab with the
badge above.

## The story

2026 ED138 is a trans-Neptunian object on a 43 au orbit, inclined 24.5 degrees
to the ecliptic, that never comes closer to the Sun than 37.1 au (barycentric). It was found
in early Rubin Observatory data by the linking code pointdexter, and archival
DECam images extended its arc to 3,789 days (Holman et al. 2026). From its
brightness it is 612 +/- 11 km across for a geometric albedo of 0.25 and
1,529 +/- 28 km for 0.04; the discovery paper calls it a dwarf-planet candidate,
pending an albedo measurement.

The Minor Planet Center (MPC) record is longer than the paper's fit: 129
observations through 2026-07-11 from 11 stations, among them a Harvard plate of 1937 and two
Palomar plates of 1954. empyrean 0.11 cannot yet read times before 1960, so
those three are held out by a named filter, and the orbit is fitted from the
126 observations from 1977-03-20 to 2026-07-11, a span of 49.3 years. That fit
agrees with JPL's solution of 2026-10-29, which uses 115 observations over 89
years, to within 0.91 of JPL's sigma on every element, and with the discovery
paper's orbit to within 0.65 of our sigma (and up to 5.6 of the paper's much
smaller uncertainties), and it puts the orbit at the edge of
the 12:7 resonance with Neptune.

## What the script does

1. **Queries the MPC** for 2026 ED138 and prints the record through
   `LAST_NIGHT`: 129 observations, 1937-12-30 to 2026-07-11, by decade (the 2010s
   and 2020s hold 116 of them), with the remarks of the three observations
   before 1960. Two named filters
   choose the arc. `FIRST_USABLE = "1960-01-01"` holds out those three (the
   release that reads pre-1960 times lowers it to "1937"); `LAST_NIGHT =
   "2026-07-11T23:59"` is the last night of JPL's solution and of the paper's
   fit, so the three orbits are compared on the same end of the arc and
   observations the MPC adds later do not move the numbers: later observations are
   not used, and no printed line depends on them.

2. **Fits the orbit** from a cold start with the engine's default weighting
   (the stated sigma, raised to station floors, with nightly de-weighting).
   The 126 observations fit with a reduced chi-squared of 0.055 and an RMS of
   0.117 arcsecond in right ascension and 0.121 in declination. A per-station
   table shows the weighting at work: the applied sigmas (0.2 to 1.4 arcsecond)
   are 10 to 110 times the median residuals at the three busiest stations, which
   is why the reduced chi-squared is below one and the sigmas below are
   conservative. At
   2026-06-09 (TDB) the elements (ecliptic J2000, 1 sigma) are a = 42.9488 +/-
   0.0014 au, e = 0.141743 +/- 0.000012, i = 24.471052 +/- 0.000061 degrees,
   node = 322.50087 +/- 0.00027 degrees, argument of perihelion = 167.9539 +/-
   0.0098 degrees and mean anomaly = 128.334 +/- 0.011 degrees.

   **Compared with JPL's solution:** our elements differ from JPL's published
   ones (SBDB, solution of 2026-10-29, never fetched by the script) by +0.27,
   -0.91, +0.46, -0.38, +0.15 and -0.11 of JPL's sigma (a, e, i, node, argument
   of perihelion, mean anomaly). JPL's sigmas are 2.2 to 5.1 times smaller than
   ours: JPL has 40 more years of arc and different weights.

3. **Shows what the older observations add**, under the default weights only:
   from the 2010-and-later arc (116 observations, RMS 0.069 and 0.061
   arcsecond) to the 1960-and-later arc (126, RMS 0.117 and 0.121), the sigma
   of the semi-major axis falls by 13 percent, of the argument of perihelion by
   32 percent and of the mean anomaly by 39 percent. The 1937 and 1954 plates,
   a 72-year lever beyond 1977, join this table when the engine reads
   pre-1960 times.

4. **Gives the size.** The diameter formula needs a V-band absolute magnitude.
   SBDB's H (2.8533) comes from redder bands, so the script uses the paper's
   calibrated zero-phase H_V = 3.19 +/- 0.04: 612 +/- 11 km at albedo 0.25,
   967 +/- 18 km at 0.10 and 1,529 +/- 28 km at 0.04. The paper finds the
   largest trans-Neptunian objects tend to have higher albedos (Lellouch et al.
   2013), so the large end is less likely; the brightness alone does not say
   which.

5. **Tests the 12:7 resonance** over the 1,093 years the planetary ephemeris
   covers (1552 to 2645; the ephemeris ends in 2650 and the script stays inside
   it). The
   elements are barycentric, in the invariable plane that the script derives
   from the planets' angular momentum (1.579 degrees from the ecliptic, node
   107.63 degrees, from the script's five-body angular momentum; Souami and
   Souchay 2012 give 1.5787 degrees and 107.58 degrees, the node difference
   coming from the inner planets being lumped into the Sun). The semi-major axis
   ranges from 43.05 to 43.10 au, its mean sitting 0.011 au above the 12:7
   commensurability with Neptune (43.070 au), the inclination between 25.74 and 25.75 degrees (the
   paper's proper inclination is 25.7 degrees; ours is a span mean of
   osculating values, so the agreement is a check, not an identity), and the
   perihelion no closer than 37.1 au. The 12:7 resonant argument stays within a
   6 degree arc and changes by -4 degrees; the 5:3, 17:10, 19:11 and 7:4
   arguments sweep 193 to 204 degrees, about 0.18 degrees per year, and so
   circulate. The paper's own argument for the 12:7 resonance (12 lambda - 7
   lambda_N - 3 varpi - 2 node) also stays within a 6 degree arc. One
   libration cycle takes tens of thousands of years, so **this span cannot
   decide whether the orbit is locked**. The paper integrated 201 orbits drawn
   from its covariance for 10 million years: 93 of them (46 percent) are
   resonant by the criteria of Khain et al. (2020), librating about 180 degrees
   with an amplitude of 95 to 115 degrees, and the rest circulate, an orbit at
   the edge of the resonance. The paper also finds it too red (g - r = 0.63 +/-
   0.07, against the Sun's 0.41) to belong to the collisional family of Haumea,
   which is in the same resonance.

6. **Compares with the discovery paper's adopted fit** (74 observations,
   2016-02-25 to 2026-07-11), whose Table 2 gives barycentric ecliptic elements
   at MJD 59337.8171 TDB. The script propagates our fit to that epoch and forms
   the same elements with first-order sigmas from a numerical Jacobian. The
   differences are at most 0.65 of our sigma. Against the paper's own
   uncertainties, which are much smaller (its a, e, q and i uncertainties are
   delta-chi-squared = 1 profile ranges, and its DECam and Rubin positions are
   weighted at their stated 0.01 to 0.05 arcsecond), they are up to 5.6: the
   data, weights and arcs differ, and no better or worse claim is made.

7. **Reads how far the orbit can be followed** (first-order position
   uncertainty, 1 sigma): 0.0221 au in 1552, 0.0030 au in 1926, 68,877 km in
   2026 (the sample nearest), 0.0047 au in 2126 and 0.0246 au in 2645. Against
   an orbit 43 au across, the position is known across the whole 1,093 years;
   the phase along the orbit is what grows.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Orbit | a = 42.94870 +/- 0.00053 au, e = 0.1417448 +/- 0.0000023, i = 24.47104 +/- 0.000025 degrees (MJD 61200 TDB) | JPL SBDB, solution 2026-10-29 (115 observations, 1937-12-30 to 2026-07-11) |
| Barycentric elements at MJD 59337.8171 TDB | a = 43.090975 au, e = 0.1387280, i = 24.4338512 degrees, q = 37.11305 au | Holman et al. 2026, Table 2 |
| Absolute magnitude | H_V = 3.19 +/- 0.04 (calibrated, zero phase) | Holman et al. 2026, Table 3 |
| Diameter | 612 to 1,529 km for geometric albedo 0.25 to 0.04 | Holman et al. 2026; measured albedos of large trans-Neptunian objects: Lellouch et al. 2013 |
| 12:7 resonance | 93 of 201 orbits (46 percent) resonant over 10 Myr; the orbit is at the edge of the resonance | Holman et al. 2026, using the criteria of Khain et al. 2020 |
| Invariable plane | 1.579 degrees from the ecliptic J2000, node 107.63 degrees (the script's five-body angular momentum) | Souami and Souchay 2012 give 1.5787 degrees, 107.58 degrees |
| Barycentric elements for classification | integrate barycentric elements and test resonant arguments for libration | Elliot et al. 2005 |
| Astrometry | 129 observations, 1937-12-30 to 2026-07-11, 11 stations | Minor Planet Center |

## Expected output

```
129 observations of 2026 ED138 in the MPC record through 2026-07-11, 1937-12-30 to 2026-07-11
By decade: 1930s 1, 1950s 2, 1970s 1, 1980s 2, 1990s 6, 2000s 1, 2010s 83, 2020s 33
3 observations before 1960 held out; observations after 2026-07-11 are not used
  1937-12-30 station 074, stated 2.00 arcsec: Harvard A plate 19892 (blue), DASCH scan; marginal detection, S/N 3.4
  1954-04-03 station 261, stated 0.30 arcsec: POSS-I E plate 1029 (103a-E red), SuperCOSMOS scan
  1954-04-03 station 261, stated 0.30 arcsec: POSS-I O plate 1029 (103a-O blue), STScI DSS scan
11 stations

Fit from 1960: 126/126 observations, chi2/dof 0.055, RMS RA.cos(d) 0.117" Dec 0.121"
Default weighting: stated sigma with station floors and nightly de-weighting. Per station (stated sigma, sigma the fit applies, median |RA residual|, arcsec):
  W84:  44 observations, stated 0.052, applied 0.250, |residual| 0.025
  X05:  30 observations, stated 0.011, applied 1.000, |residual| 0.009
  W91:  21 observations, stated 0.082, applied 1.414, |residual| 0.020
  F51:  13 observations, stated 0.079, applied 0.200, |residual| 0.108
  809:   5 observations, stated 0.570, applied 1.000, |residual| 0.278
  Q55:   5 observations, stated 0.250, applied 1.000, |residual| 0.032
Arc used: 1977-03-20 to 2026-07-11 (49.3 years)
Elements, ecliptic J2000 at 2026-06-09 (TDB), with 1 sigma, and JPL's difference:
  a (au)                      42.9488 +/- 1.4e-03   (ours - JPL) = +0.27 JPL sigma; JPL sigma 5.3e-04, ours/JPL 2.7
  e                          0.141743 +/- 1.2e-05   (ours - JPL) = -0.91 JPL sigma; JPL sigma 2.3e-06, ours/JPL 5.1
  i (deg)                   24.471052 +/- 6.1e-05   (ours - JPL) = +0.46 JPL sigma; JPL sigma 2.5e-05, ours/JPL 2.4
  node (deg)                322.50087 +/- 2.7e-04   (ours - JPL) = -0.38 JPL sigma; JPL sigma 8.3e-05, ours/JPL 3.3
  arg. perihelion (deg)      167.9539 +/- 9.8e-03   (ours - JPL) = +0.15 JPL sigma; JPL sigma 4.2e-03, ours/JPL 2.3
  mean anomaly (deg)          128.334 +/- 1.1e-02   (ours - JPL) = -0.11 JPL sigma; JPL sigma 4.9e-03, ours/JPL 2.2

1 sigma by arc, under the default weights only:
  first year  obs   a (au)     arg. perihelion   mean anomaly
        2010  116   1.65e-03   1.43e-02 deg   1.82e-02 deg   RMS 0.069" / 0.061"
        1960  126   1.43e-03   9.78e-03 deg   1.10e-02 deg   RMS 0.117" / 0.121"
  Adding the observations of 1960 to 2009 lowers sigma by 13% (a), 32% (arg. perihelion), 39% (mean anomaly)

H_V = 3.19 +/- 0.04 (Holman et al. 2026); diameter 1329 km / sqrt(albedo) x 10^(-H_V/5):
  albedo 0.25:    612 +/-  11 km
  albedo 0.10:    967 +/-  18 km
  albedo 0.04:   1529 +/-  28 km
Invariable plane: 1.579 deg from the ecliptic, node 107.63 deg

Over 1,093 years (1552 to 2645), barycentric, invariable plane: a 43.05 to 43.10 au (mean 43.081), e 0.138 to 0.139, i 25.74 to 25.75 deg, perihelion 37.1 au at its closest
At the sample nearest 2026 (MJD 61010) a = 43.091 au.
Mean inclination over the span, invariable plane: 25.74 deg (the paper's proper inclination: 25.7 deg; a mean of osculating values against a proper element)
Neptune: a = 30.07 au. Resonant argument (arc that holds every sample; 360 = circulates):
  5:3 (order 2, exact at a = 42.269 au, offset +0.812):   201 deg; net change -201 deg, -0.183 deg/yr
  17:10 (order 7, exact at a = 42.830 au, offset +0.251):   204 deg; net change -204 deg, -0.187 deg/yr
  12:7 (order 5, exact at a = 43.070 au, offset +0.011):     6 deg; net change -4 deg, -0.003 deg/yr
  19:11 (order 8, exact at a = 43.287 au, offset -0.206):   193 deg; net change +193 deg, +0.177 deg/yr
  7:4 (order 3, exact at a = 43.666 au, offset -0.585):   197 deg; net change +197 deg, +0.180 deg/yr
12:7, the paper's argument 12 lambda - 7 lambda_N - 3 varpi - 2 node: 6 deg, net change -3 deg, -0.003 deg/yr; mean 253 deg
Barycentric ecliptic elements at MJD 59337.8171 TDB (the paper's epoch), against its Table 2:
  (the paper's a, e, q, i uncertainties are delta-chi^2 = 1 profile ranges)
  a                     43.0913 +/- 1.4e-03  paper 43.09098 +5.6e-05/-6.0e-05  difference +0.22 of our sigma, +5.6 of the paper's
  e                    0.138736 +/- 1.2e-05  paper 0.138728 +7.4e-06/-7.4e-06  difference +0.65 of our sigma, +1.0 of the paper's
  i                   24.433858 +/- 6.1e-05  paper 24.43385 +1.8e-06/-1.8e-06  difference +0.12 of our sigma, +4.0 of the paper's
  node                322.60604 +/- 2.7e-04  paper 322.6061 +2.9e-05/-2.9e-05  difference -0.05 of our sigma, -0.5 of the paper's
  arg. perihelion       168.705 +/- 1.0e-02  paper 168.6998 +2.8e-03/-2.8e-03  difference +0.50 of our sigma, +1.8 of the paper's
  mean anomaly          121.073 +/- 1.1e-02  paper 121.0797 +4.0e-03/-4.0e-03  difference -0.60 of our sigma, -1.7 of the paper's
  q                     37.1130 +/- 1.7e-03  paper 37.11305 +2.7e-04/-2.7e-04  difference -0.04 of our sigma, -0.2 of the paper's

1-sigma position uncertainty (first order, nearest 2-year sample):
   1552.2 (MJD  -112000):    3,312,208 km (0.0221 au) at 46.3 au
   1776.1 (MJD   -30240):    1,741,657 km (0.0116 au) at 48.9 au
   1926.0 (MJD    24510):      446,603 km (0.0030 au) at 37.1 au
   2025.9 (MJD    61010):       68,877 km (0.0005 au) at 47.1 au
   2125.8 (MJD    97510):      705,403 km (0.0047 au) at 45.4 au
   2275.7 (MJD   152260):    2,009,745 km (0.0134 au) at 43.4 au
   2645.5 (MJD   287310):    3,679,348 km (0.0246 au) at 48.9 au
```

The scripts query the MPC live and keep the observations from `FIRST_USABLE`
through `LAST_NIGHT`, the arc the numbers are for; the JPL and paper constants
carry their source and date. A drift check after the
snippet in `main.py` asserts that the record through `LAST_NIGHT` is the 129
observations the numbers were computed from (the 3 held-out rows and their
remarks included, and the 126 fitted ones), by count and by a sha256 of the
sorted observation ids, and exits with an error if the MPC re-measures, deletes
or adds a row through `LAST_NIGHT`. The check is about the MPC record, not the
language, and the Rust program's output is byte-identical to the Python
program's, so the one check covers both.

## Data

The astrometry is the Minor Planet Center record of 2026 ED138, queried at run
time; the MPC holds the authoritative record. Nothing is committed beside the
scripts. The ten observations from 1977 to 2000 and the three before 1960 come
from digitized photographic plates and film, named in the `remarks` of their
rows: Harvard (DASCH), POSS-I (SuperCOSMOS and STScI DSS scans), SERC, ESO and
the APPLAUSE archive. The modern observations come from survey and follow-up
stations, among them W84 (Cerro Tololo-DECam), X05 (Simonyi Survey Telescope,
Rubin Observatory), F51 (Pan-STARRS 1, Haleakala), W91 (VHS-VISTA, Cerro
Paranal), 309 (Cerro Paranal), Q55 (SkyMapper, Siding Spring) and 809 (European
Southern Observatory, La Silla); station names are from the MPC observatory
codes.

## See also

- Holman, M. J., Jurić, M., Napier, K. J., et al. 2026, "2026 ED138: A Large Trans-Neptunian Object in Early Rubin Observatory Data, and How Many More May Remain", arXiv:2610.38693: <https://arxiv.org/abs/2610.38693>
- Khain, T., Becker, J. C., Lin, H. W., et al. 2020, "Dynamical Classification of Trans-Neptunian Objects Detected by the Dark Energy Survey", AJ 159, 133: <https://doi.org/10.3847/1538-3881/ab7002>
- Lellouch, E., Santos-Sanz, P., Lacerda, P., et al. 2013, "'TNOs are Cool': A survey of the trans-Neptunian region. IX. Thermal properties of Kuiper belt objects and Centaurs from combined Herschel and Spitzer observations", A&A 557, A60: <https://doi.org/10.1051/0004-6361/201322047>
- Souami, D. and Souchay, J. 2012, "The solar system's invariable plane", A&A 543, A133: <https://doi.org/10.1051/0004-6361/201219011>
- Elliot, J. L., Kern, S. D., Clancy, K. B., et al. 2005, "The Deep Ecliptic Survey: A Search for Kuiper Belt Objects and Centaurs. II. Dynamical Classification, the Kuiper Belt Plane, and the Core Population", AJ 129, 1117: <https://doi.org/10.1086/427395>
- JPL Small-Body Database: <https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2026%20ED138>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/2026ed138>
