# 2025-010D: a Falcon 9 stage → community-driven astrometry → predicted lunar impact

[![Python](https://img.shields.io/badge/Python-main.py-3776AB?logo=python&logoColor=white&style=flat-square)](./main.py)
[![Rust](https://img.shields.io/badge/Rust-main.rs-B7410E?logo=rust&logoColor=white&style=flat-square)](./main.rs)
[![Notebook](https://img.shields.io/badge/Notebook-main.ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](./main.ipynb)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Empyrean-Dynamics/empyrean-scenarios/blob/main/2025-010D/main.ipynb)

Prefer a notebook? [`main.ipynb`](./main.ipynb) is the same walkthrough,
rendered on GitHub with executed outputs — or open it in Colab with the
badge above.

## The story

On 2025-01-15 a Falcon 9 launched two lunar landers at once — Firefly's
Blue Ghost Mission 1 and ispace's HAKUTO-R Resilience. The expendable
second stage that performed the trans-lunar injection, catalogued as
**2025-010D** (NORAD 62719), was left in a ~26-day, Moon-crossing high
Earth orbit. Four days later the ATLAS survey picked it up as an unknown
object; it spent a day on the NEO Confirmation Page as **A11hSI1**
before Bill Gray (Project Pluto) identified it as the just-launched
stage.

In September 2025, Gray's orbit solutions began showing a lunar impact
in August 2026. There was no radar tracking to lean on — at lunar
distance, radar returns are ~10¹⁰ times fainter than for LEO objects —
so the trajectory came almost entirely from telescopic astrometry: NEO
surveys plus a hand-raised network of community observers on four continents who
answered Gray's call for measurements. The final pre-impact prediction
put the stage on the Moon at **2026-08-05 06:35:37.5 UTC**, near the
crater Einstein at the Moon's western limb — terrain just past the
90° W line that favorable libration happened to tilt into view from
Earth that morning.

The stage hit on time. The VLT saw a sodium–lithium vapor plume in the
minutes after impact, and KASA's Danuri orbiter — which had imaged the
site 33 minutes *before* impact — caught the fresh scar on its next
passes: the first before/after documentation of an artificial lunar
crater. 2025-010D is the first lunar impactor whose provenance, mass,
and dimensions were all known in advance, making it a genuine
ground-truth calibration object for cislunar orbit determination.

For an orbit-determination engine this object is a stress test that no
asteroid provides: a ~4-tonne hollow tumbling cylinder whose
solar-radiation-pressure area-to-mass ratio (~0.008 m²/kg) is one to
two orders of magnitude above any natural body's, fitted from a public
arc of community-driven astrometry, propagated through the Earth–Moon system
into a hyperbolic selenocentric encounter.

## The data (read this — it's not the usual MPC query)

Every other scenario in this collection pulls its astrometry live from
the Minor Planet Center. That cannot work here: MPC policy removes
observations of recognized artificial satellites from its public
holdings, so the ~1,000-observation survey dataset for 2025-010D is not
publicly available. What *is* public — and explicitly placed in the
public domain — is the astrometry on Bill Gray's Project Pluto pages,
contributed by the observers named below. This directory therefore
ships the observations as a committed ADES PSV file:

- [`astrometry.psv`](./astrometry.psv) — all 402 public observations of
  2025-010D, normalized from the find_orb-extended MPC 80-column format
  of the source pages by [`convert_astrometry.py`](./convert_astrometry.py).
  Normalization means exactly: packed sub-second timestamps and decimal
  day fractions expanded to ISO-8601 UTC at the source's own precision;
  sexagesimal coordinates converted to decimal degrees (find_orb
  decimal-degree lines are copied digit-for-digit); the source's seven
  designation spellings unified to one tracklet ID; magnitudes carrying
  find_orb's exclusion flag omitted; star-catalog codes not carried.
  Nothing else is altered, and no observation is dropped.

Sources, all released to the public domain by Project Pluto (retrieved
2026-08-06):

| Source | Arc | Obs | URL |
|---|---|---|---|
| Pseudo-MPEC for 2025-010D | 2025-12-21 → 2026-05-22 | 323 | <https://www.projectpluto.com/pluto/mpecs/25010d.htm> |
| Pseudo-MPEC, final pre-impact arc | 2026-07-23 → 2026-08-01 | 74 | <https://www.projectpluto.com/pluto/mpecs/25010d_new.htm> |
| NEOCP discovery tracklet A11hSI1 | 2025-01-19/20 | 5 | <https://projectpluto.com/temp/a11hsi1.htm> |

**Observers.** This scenario exists because of the people who took the
measurements — several of them specifically in response to Gray's
request for tracking of this object:

| Code | Station | Observers |
|---|---|---|
| Y82 | LPMR Observatory, Broad Chalke, UK | G. Privett |
| Q62 | iTelescope Observatory, Siding Spring, Australia | Z. Wang |
| P13 | Baihuashan Observatory, Beijing, China | Z. Wang, B. Liu |
| Y05 | SONEAR Wykrota-CEAMIG, Serra da Piedade, Brazil | C. Jacques |
| 718 | Tooele, Utah, USA | P. Wiggins |
| W05 | Tree Gate Farm Observatory, Starkville, Mississippi, USA | J.-F. Gout |
| 970 | Chelmsford, UK | N. James |
| K19 | PASTIS Observatory, Banon, France | C. Demeautis |
| M21 | Schiaparelli Southern Observatory, Hakos, Namibia | A. Aletti, F. Bellini, L. Buzzi, G. Galli |
| W68 | ATLAS Chile, Río Hurtado, Chile | L. Denneau, R. Siverd, J. Tonry, H. Weiland |
| ScT | Roberts Creek 1, British Columbia, Canada (private station) | S. Tilley |

The same attribution is embedded in `astrometry.psv` itself as ADES
observatory/observer context blocks, so the credits travel with the
data.

Orbit solutions, impact predictions, and the astrometry compilation are
the work of **Bill Gray (Project Pluto)** — if you reuse this data,
credit him and the observers above, and see his page
<https://www.projectpluto.com/25010d.htm> (he asks for a link if you
use it).

## What the script does

1. **Reads the committed public astrometry** with `empyrean.read_ades`
   — no network fetch; the MPC has nothing to serve for this object.

2. **Fits the final nine-night arc as a geocentric orbit.** IOD is told
   this is an Earth-orbiting object (`OriginPolicy` `EXPLICIT`/`EARTH` —
   heliocentric Gauss is unphysical for a catalogued satellite), then
   the differential correction runs with solar radiation pressure's
   area-to-mass ratio as a solve-for parameter. For a hollow rocket
   stage the AMR is not a small correction — it is the dominant model
   term, and Gray's fit recovers it at ~5σ from nine nights of data.

3. **Propagates into the Moon.** The trajectory is hyperbolic with
   respect to the Moon (e ≈ 1.055); the event detector reports the
   surface impact with selenographic coordinates.

4. **Compares against the published record**: Gray's fit to this same
   public arc, JPL's radar-informed solution #GA1A2/21, and the
   confirmed impact.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Launch | 2025-01-15 06:11 UTC, KSC LC-39A | Blue Ghost 1 / HAKUTO-R 2 mission |
| Impact epoch | 2026-08-05 06:35:40 UTC ± 9 s | JPL Horizons #GA1A2/21 |
| Impact epoch (Gray, all data) | 2026-08-05 06:35:37.5 UTC | Project Pluto, 2026-08-01 |
| Impact epoch (Gray, this public 74-obs arc) | 2026-08-05 06:35:42.45 UTC | Pseudo-MPEC 25010d_new |
| Impact site | 19.46° N, 266.71° E (near crater Einstein) | Project Pluto |
| Impact site (public 74-obs arc) | 19.58° N, 266.63° E | Pseudo-MPEC 25010d_new |
| 3σ surface ellipse | 3.4 × 0.6 km | JPL Horizons #GA1A2/21 |
| Impact speed | 2.43 km/s | Project Pluto / Campbell+ 2026 |
| Area-to-mass ratio (74-obs arc) | 0.0079 ± 0.0017 m²/kg | Pseudo-MPEC 25010d_new |
| Stage mass / size | ~4,000–4,900 kg, ~13 m × 3.7 m | JPL Horizons; Sky & Telescope |
| Selenocentric e, q | 1.0549, 1303 km | Pseudo-MPEC 25010d_new |
| Confirmation | Na/Li impact plume (VLT); before/after imaging (KASA Danuri) | ESO; KASA, 2026-08-06 |

Notes for the careful reader: the two independent full-arc solutions
(Gray; Campbell et al. 2026) differ by ~2 minutes in impact time with
overlapping stated uncertainties — solar radiation pressure on a
tumbling hollow body is the dominant error term in both. The single
`ScT` observation is from a private, non-MPC station code the engine
cannot resolve to a site, so evaluation skips it — it appears as the
one rejected row in the residual summary, and both language twins skip
it identically in the ladder (its site coordinates are on the source
page if you want to model it yourself).

## Expected output (rough)

```
402 public observations (Project Pluto, public domain)
74 in the final arc (2026-07-23 → 08-01)
fit: chi2/dof 0.540  RMS RA·cos(d) 0.323" Dec 0.279"  (74/74 obs)
Fitted AMR = 0.0029 ± 0.0011 m²/kg
Gray (same 74-obs arc): 0.0079 ± 0.0017 m²/kg

Predicted lunar impact (Empyrean): 2026-08-05T06:35:40.169028682Z
  at 19.514°N 266.646°E (selenographic)
Gray (74-obs arc):  2026-08-05T06:35:42.45Z at 19.577°N 266.630°E
JPL #GA1A2/21:      2026-08-05T06:35:40Z ± 9 s at 19.507°N 266.7°E
Confirmed:          2026-08-05 ~06:35 UTC near crater Einstein

Final-arc orbit scored against the full 402-obs record:
  own arc   (2026 Jul-Aug)   RMS         0.41"
  Apr-May 2026               RMS       165.29"
  Dec 2025                   RMS      1679.21"
  Jan 2025 discovery         RMS    470211.04"
(Five orders of magnitude across two lunar encounters and a
 changing tumble — consistent with the per-arc solutions
 Project Pluto published; Gray 2026, Campbell et al. 2026.)
```

An impact epoch 0.2 s from JPL's radar-informed solution, from
optical-only public astrometry — and a residual ladder spanning five
orders of magnitude that shows exactly why every arc of a tumbling
rocket body earns its own fit.

## References

- Gray, B. 2026, "A Falcon 9 second stage will hit the moon", Project Pluto — <https://www.projectpluto.com/25010d.htm>; pseudo-MPECs 25010d and 25010d_new (the astrometry, orbit solutions, and impact predictions compared above).
- Campbell, T., Battle, A., Gray, B., Sanchez, J. A., Cantillo, D., LeCorre, L. & Reddy, V. 2026, "Physical Characterization of Moon Impactor 2025-010D", arXiv:2608.00360 — independent optical-only orbit solutions and physical characterization.
- Fernando, B., Heldmann, J., Gray, B., et al. 2026, "Observational planning for the 2026 August 5 Falcon 9 Upper Stage lunar impact", arXiv:2607.14625.
- JPL Horizons, target `-162719`, solution #GA1A2/21 (S. Naidu) — the radar-informed reference solution and 3σ ellipse quoted above.

## See also

- [Project Pluto: the 2025-010D lunar-impact page](https://www.projectpluto.com/25010d.htm) — Gray's running account
- [Campbell et al. 2026, "Physical Characterization of Moon Impactor 2025-010D"](https://arxiv.org/abs/2608.00360)
- [Fernando et al. 2026, "Observational planning for the 2026 August 5 Falcon 9 Upper Stage lunar impact"](https://arxiv.org/abs/2607.14625)
- [Sky & Telescope: "SpaceX booster will hit the Moon this August"](https://skyandtelescope.org/astronomy-news/spacex-booster-will-hit-the-moon-this-august/)
- JPL Horizons target `-162719` (`2025-010D`), solution #GA1A2/21
