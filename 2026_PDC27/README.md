# 2026 PDC27: a hypothetical impactor, 26 nights of astrometry, and a 19% question

> **This scenario describes a fictional asteroid.** 2026 PDC27 is the
> hypothetical-impact exercise object for the International Academy of
> Astronautics **2027 Planetary Defense Conference** (Montreal, 3–7 May
> 2027). Quoting the JPL CNEOS exercise page: *"This webpage does not
> describe a real potential asteroid impact. The information on this
> page is fictional and provided only to support an emergency response
> exercise […] This is only an exercise."*

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2026_PDC27/main.ipynb)

## The story (as scripted by the exercise)

On 2026-06-28 Pan-STARRS1 discovers a ~23rd-magnitude object whose
orbit crosses Earth's. By July 8 the impact probability for
**10 July 2038** creeps past 0.1%. Then the plot twist: on July 12,
precovery detections are found in Vera C. Rubin Observatory images
from May and June. The arc suddenly triples in length and the impact
probability **jumps to 16%**, triggering the first IAWN Potential
Impact Notification. JWST sizes the object at 80–85 m (S-type, rocky).
On July 31 the asteroid slips into the Sun's glare at 19%, where it
will sit, unobservable, until December 2026. Epoch 1 of the exercise
ends there: a one-in-five chance of a 10–50 Mt airburst somewhere
along a corridor that wraps more than halfway around the globe, and
nothing to do but wait for the next observing window.

This is the textbook planetary-astronomy decision problem: a short
arc, a long lever ahead (twelve years and ten orbits to the 2038
encounter), and a probability that will either collapse below the 1%
notification threshold or march toward certainty.

## What the scripts do

1. **Read the committed synthetic astrometry** (`empyrean.read_ades`): 52
   geocentric observations with per-observation uncertainties. The file is
   <https://raw.githubusercontent.com/Empyrean-Dynamics/empyrean-scenarios/main/2026_PDC27/astrometry.psv>;
   save it as `astrometry.psv` next to where you run the code.
2. **Replay the knowledge timeline at five dates**: July 8 and July 10 (22 and
   26 observations), July 11 (28), July 12 (42: the six Rubin precovery nights
   enter all at once, as they did in the exercise) and July 31 (all 52). Each
   date is a cold fit that honors the stated 0.1 and 0.2 arcsecond sigmas. On
   July 10 the arc of 26 observations gives no converged solution.
3. **At each date, compute the 2038 impact probability four ways**: linear,
   second-order, AUTO (as resolved), and Monte Carlo (1000 samples, seeded),
   reported as hits out of N with a 95% Wilson interval, beside the
   exercise's published checkpoints (0.1%, 16%, 19%; CNEOS and the IAWN
   notifications).
4. **Print Epoch 1, one line per method.**

The five fits and their Monte Carlo take about nine minutes (the Python and
Rust programs each took about 9 minutes, run side by side on one machine).


## What the numbers show

The analytic estimates are per-date fits. On July 8 the linear estimate is
0.00119 and the second-order 0.00011; the Monte Carlo has 1 hit in 1000 (95%
Wilson interval 0.0002 to 0.0056), against the published 0.1%. On July 11 the
linear and second-order estimates are 0.00191 and 0.00121, with 0 of 1000
hits (interval 0 to 0.0038). On July 8 the two analytic estimates are tail
extrapolations ten times apart; the linear one lies inside the Monte Carlo
interval and the second-order one just below it (0.00011 against a lower end
of 0.0002), and a thousand samples cannot narrow the interval (that needs about
a hundred thousand, or importance sampling). On July 11 the two analytic
estimates differ by a factor of 1.6 and both lie inside the Monte Carlo
interval, which a thousand samples cannot narrow. When the precoveries enter on July 12 the arc grows from 28 to 42
observations and the probability jumps to 0.16021 (linear), 0.16022 (second
order) and 0.16093 (AUTO), with 160 of 1000 Monte Carlo hits (0.1386 to
0.1840) against the published 16%. At Epoch 1 (all 52 observations) the
estimates are linear 0.18707, second order 0.18707 and AUTO 0.18779, with 190
of 1000 hits (0.1669 to 0.2155) against the published 19%. Every Monte Carlo
interval contains the published value, which on July 8 is nearly vacuous: an
interval that wide contains almost any probability near one in a thousand.

## The data

- [`2026pdc27.epoch1.xml`](./2026pdc27.epoch1.xml): the official
  Epoch-1 ADES XML released by JPL CNEOS (2026-08-01), byte-identical
  to the published file (SHA256 `4a1fccde…`).
- [`astrometry.psv`](./astrometry.psv): the same 52 records
  transcribed field-for-field into ADES PSV (the format
  `empyrean.read_ades` consumes) by
  [`convert_astrometry.py`](./convert_astrometry.py), which
  self-verifies the transcription on every run. Only the constant
  `subFmt` field is dropped; no value is altered.

The observations are **synthetic and geocentric** (station code 500, since
the exercise dispenses with topocentric sites), with stated
uncertainties of 0.1″ (Rubin precovery + dark-time nights) and 0.2″
(discovery and twilight nights). They are noiseless by construction:
they sit on the exercise's truth trajectory to ~0.004″, and within
0.11″ of the published Horizons reference trajectory (`-937025`)
across the entire arc, so fitted χ² is essentially zero and the
covariance (hence the IP) is driven by the stated weights, exactly as
the exercise designers intended.

Scenario design and all source data: **NASA/JPL Center for Near-Earth
Object Studies (CNEOS)**, <https://cneos.jpl.nasa.gov/pd/cs/pdc27/>.
Impact risk assessment: **NASA Ames Asteroid Threat Assessment
Project** (L. Wheeler, A. Coates, R. Bennett, J. Mirza, M. Aftosmis,
J. Dotson). IAWN notifications 2026-07-15 and 2026-08-01. The
exercise pages carry no explicit license; they are NASA/JPL-Caltech
web products, and this directory redistributes only the small
astrometry file, unmodified, with this attribution.

## Reference values (Epoch 1, as published)

| Quantity | Reference value | Source |
|---|---|---|
| Potential impact date | 2038-07-10 | CNEOS exercise page |
| Worst-case impact time | 2038-07-10 05:29:35.52 UTC | JPL Horizons `-937025` |
| Impact probability (2026-07-08) | ~0.1% | exercise timeline |
| Impact probability (2026-07-12, precoveries) | 16% | exercise timeline / IAWN #1 |
| Impact probability (Epoch 1, all 52 obs) | **19%** | CNEOS / NEOCC / NEODyS concur |
| Orbit | e ≈ 0.410, q ≈ 0.665 au, i ≈ 13.76°, P ≈ 437 d | Horizons `-937025`, epoch 2026-08-01 |
| Absolute magnitude | H = 23.071 (G = 0.15) | Horizons `-937025` |
| Diameter | most likely 80–85 m (range 75–90 m), S-type | JWST (in-exercise), IAWN #2 |
| Impact energy | 10–50 Mt, most likely ~18–32 Mt | IAWN #2 / ATAP |
| Palermo / Torino | +0.8 / 3 (yellow) | exercise page |
| Risk corridor | Pacific → N. America → Atlantic → S. Europe → Mediterranean | IAWN #2 |
| Uncertainty region | >10 Earth diameters long, a few km wide | exercise page |

## Expected output

```
52 synthetic observations (JPL CNEOS, Epoch 1)

knowledge date  n_obs     linear  2nd-order       auto  Monte Carlo hits/N  95% Wilson interval   published (CNEOS/IAWN)
2026-07-08     22    0.00119    0.00011    0.00010      1/1000       [0.0002, 0.0056]   0.001
2026-07-10     26   (no converged solution)
2026-07-11     28    0.00191    0.00121    0.00035      0/1000       [0.0000, 0.0038]
2026-07-12     42    0.16021    0.16022    0.16093    160/1000       [0.1386, 0.1840]   0.160
2026-07-31     52    0.18707    0.18707    0.18779    190/1000       [0.1669, 0.2155]   0.190

Epoch 1 (2026-07-31, 52 observations), impact probability for 2038-07-10 by method:
  linear        0.18707
  second order  0.18707
  auto          0.18779
  Monte Carlo   190/1000 = 0.1900, 95% Wilson interval [0.1669, 0.2155]
  published     0.190 (CNEOS / IAWN 2026-08-01)
```

## References

- Park, R. S. & Scheeres, D. J. 2006, "Nonlinear mapping of Gaussian statistics: theory and applications to spacecraft trajectory design", *JGCD* **29**(6): the second-order (STT) uncertainty mapping.
- DeMars, K. J., Bishop, R. H. & Jah, M. K. 2013, "Entropy-based approach for uncertainty propagation of nonlinear dynamical systems", *JGCD* **36**(4): the adaptive Gaussian-mixture splitting.
- Roa, J., Farnocchia, D. & Chesley, S. R. 2021, "A novel approach to asteroid impact monitoring", *AJ* **162**(6): impact-probability computation practice (Sentry-II).

## See also

- [The 2027 PDC Hypothetical Asteroid Impact Scenario — Epoch 1](https://cneos.jpl.nasa.gov/pd/cs/pdc27/) (CNEOS)
- [10th IAA Planetary Defense Conference, Montreal, 3–7 May 2027](https://iaaspace.org/)
- IAWN Potential Impact Notifications, 2026-07-15 and 2026-08-01 (linked from the CNEOS page)
- NASA Ames ATAP, *Impact Risk Assessment — 2026 PDC27 Epoch 1*
- JPL Horizons simulation body `-937025` (`2026 PDC27`)

*Future exercise epochs (the asteroid returns to view December 2026)
will extend this scenario as CNEOS releases them.*
