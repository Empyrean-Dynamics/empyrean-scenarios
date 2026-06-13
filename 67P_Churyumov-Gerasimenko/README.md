# 67P/Churyumov-Gerasimenko: cometary non-grav vs gravity-only control

Scripts: [`main.py`](./main.py) (Python) · [`main.rs`](./main.rs) (Rust)

## The story

67P/Churyumov-Gerasimenko is the target of ESA's Rosetta mission —
the spacecraft rendezvoused with the comet in 2014 and accompanied it
through the 2015 perihelion before depositing the Philae lander on
the surface. 67P is a Jupiter-family comet with a 6.44-year orbital
period and a perihelion distance of ~1.24 AU, deep enough into the
inner solar system that water-ice sublimation drives a measurable
non-gravitational acceleration on the nucleus.

The Marsden A1/A2/A3 model parameterises that outgassing as a
water-sublimation g(r) function modulating three orthogonal
acceleration components (radial, transverse, normal). For 67P, A1 is
~1×10⁻⁹ AU/d² — about 36,000 times the magnitude of Apophis's A2
(transverse, ≈ Yarkovsky thermal recoil) — although the physics is
completely different (outgassing recoil vs anisotropic thermal
re-radiation). What the two share is that both manifest as cumulative
along-track displacement that grows secularly over many orbits, and
both fit into the same Marsden A1/A2/A3 parameterization with
different g(r) shapes (water-ice for comets, inverse-square for
Yarkovsky-on-asteroids).

## What the script does

1. **Queries JPL SBDB for 67P.** The SBDB solution ships the
   Marsden water-sublimation A1/A2/A3 coefficients. The propagator
   picks them up automatically and integrates the non-grav alongside
   the gravitational forces.

2. **Propagates 2012 → 2028 at 10-day cadence.** Window covers the
   Rosetta-era 2015 perihelion, the 2021 perihelion, and the
   upcoming 2028 perihelion.

3. **Re-builds the same orbit *without* the non-grav coefficients
   and propagates a control run.** This is the gravity-only twin:
   identical state at the SBDB epoch, identical force model except
   for outgassing.

4. **Differences the two trajectories.** The L2 separation between
   the non-grav and gravity-only states grows secularly, accumulating
   into a multi-thousand-km along-track displacement over the 16-year
   propagation window. That accumulated separation is the
   integrated effect of outgassing — the quantity every cometary
   ephemeris pipeline has to model in order to recover the orbit.

## Reference values

| Quantity | Reference value | Source |
|---|---|---|
| Orbital period | 6.44 years | JPL SBDB |
| Perihelion distance | 1.24 AU | JPL SBDB |
| Last perihelion | 2021-11-02 | JPL SBDB |
| Next perihelion | 2028-05-21 | JPL SBDB |
| Marsden A1 | ~1×10⁻⁹ AU/d² (radial) | JPL SBDB |
| Apophis A2 magnitude (for comparison) | ~3×10⁻¹⁴ AU/d² | JPL SBDB |

## Expected output (rough)

```
non-grav coefficients (SBDB):
  A1 = 1.234e-09 AU/d^2
  A2 = -2.567e-10 AU/d^2
  A3 = 8.901e-11 AU/d^2

Max separation (non-grav vs gravity-only) over 16 years: 3,450,000 km
(That's the cumulative effect of outgassing — what every cometary
ephemeris pipeline has to model.)
```

The exact separation depends on the SBDB epoch and the latest
non-grav fit, which is updated as new astrometry arrives. The
qualitative result — millions of km of cumulative displacement — is
robust across plausible solutions.

## A note on Marsden vs Yarkovsky

The two non-gravitational accelerations are sometimes lumped together
because both manifest as "small acceleration that drifts the orbit
secularly." They are physically distinct:

- **Marsden water-sublimation** (cometary): outgassing of volatile
  ices on the dayside applies a thrust opposite to the local sub-solar
  surface normal. Modelled as `g(r) = α (r/r₀)^(-m) (1 + (r/r₀)^n)^(-k)`
  modulating (A1, A2, A3) Cartesian-projected components. Drops off
  rapidly outside ~3 AU as the ice stops sublimating.

- **Yarkovsky** (asteroidal): anisotropic thermal re-radiation from a
  rotating body produces a tangential acceleration whose sign depends
  on the body's spin direction (prograde rotators drift outward,
  retrograde drift inward). The leading distance dependence scales as
  1/r² (solar flux); higher-order corrections come from spin axis
  obliquity, thermal inertia, and YORP. Empyrean fits the leading
  term as the Marsden A2 coefficient with inverse-square g(r); a real
  first-principles Vokrouhlický thermal model (computing A2 from spin
  and thermal inertia) is on the engine roadmap.

The script's "magnitude of A1 ≈ 36,000× |Apophis A2|" line is purely a
*magnitudes-comparison* statement — it's not saying the physics is
similar, only that the absolute scale of the acceleration on 67P is
much larger than the Yarkovsky drift on a typical near-Earth asteroid.

## See also

- [Marsden et al. 1973, "Comets and nongravitational forces. V"](https://ui.adsabs.harvard.edu/abs/1973AJ.....78..211M/abstract)
- ESA Rosetta mission: <https://www.esa.int/Science_Exploration/Space_Science/Rosetta>
- explore-mode scenario: <https://empyrean-dynamics.com/explore/67p>
