"""2026 PDC27: replaying a planetary-defense exercise, method by method.

Reproduces the 2026pdc27 explore-mode scenario from
https://empyrean-dynamics.com/explore/2026pdc27.

**2026 PDC27 is a fictional asteroid**: the hypothetical-impact
exercise object of the IAA 2027 Planetary Defense Conference
(Montreal, May 2027). "This is only an exercise." (JPL CNEOS)

Run:
    pip install empyrean
    python 2026_PDC27/main.py     # five fits, each with a 1000-sample Monte Carlo

What it does:
    1. Reads the committed Epoch-1 synthetic astrometry (52 geocentric
       observations released by JPL CNEOS, transcribed to ADES PSV).
    2. Replays the exercise's knowledge timeline at five dates: July 8
       and July 10 (22 and 26 observations), July 11 (28), July 12 (42,
       the six Rubin/LSST precovery nights entering all at once, exactly
       as the exercise's astronomers received them) and July 31 (all 52).
    3. At each date, computes the 2038-07-10 impact probability four ways
       (linear, second-order, AUTO, and Monte Carlo as hits out of N with
       a 95% Wilson interval) against the exercise's published
       checkpoints: 0.1% (Jul 8), 16% (Jul 12, the precovery jump), 19%
       (Epoch 1, Jul 31).
    4. Prints the per-date table and, for Epoch 1, one line per method.

Published comparison values: CNEOS PDC27 Epoch-1 page and the IAWN
notifications of 2026-07-15 and 2026-08-01.
"""

from __future__ import annotations

# empyrean:snippet:start
from pathlib import Path

import empyrean
import numpy as np
from empyrean import Epochs, ODConfig, Origin, TimeScale, UncertaintyMethod
from empyrean.od.result import SigmaPolicy, WeightingConfig
from empyrean.propagation.config import MonteCarlo

# The exercise's 52 synthetic observations, transcribed field for field from
# the ADES XML that NASA/JPL CNEOS released on 2026-08-01 (Epoch 1). Download
# https://raw.githubusercontent.com/Empyrean-Dynamics/empyrean-scenarios/main/2026_PDC27/astrometry.psv
# and save it as astrometry.psv in the directory you run from.
ASTROMETRY = next(
    p for p in (Path("astrometry.psv"), Path("2026_PDC27/astrometry.psv")) if p.exists()
)

# The exercise's published impact-probability checkpoints for 2038-07-10, from
# the NASA/JPL CNEOS PDC27 exercise timeline (https://cneos.jpl.nasa.gov/pd/cs/pdc27/)
# and the IAWN potential impact notifications of 2026-07-15 and 2026-08-01:
# 0.1% on July 8, 16% on July 12 (after the precoveries), 19% at Epoch 1.
# Reference values only; nothing here is fitted to them.
PUBLISHED = {"2026-07-08": 0.001, "2026-07-12": 0.16, "2026-07-31": 0.19}
# The six nights of Rubin Observatory precovery images in the exercise's
# timeline (CNEOS PDC27 Epoch-1 data). The exercise's astronomers found them
# in the Rubin archive on PRECOVERY_KNOWN, so they join the fit on that date
# and not on the nights they were taken.
PRECOVERY_NIGHTS = {
    "2026-05-11",
    "2026-05-17",
    "2026-05-23",
    "2026-06-04",
    "2026-06-10",
    "2026-06-16",
}
PRECOVERY_KNOWN = "2026-07-12"
# The knowledge dates replayed: the arcs of July 8, 10, 11 and 12 and the
# last night of Epoch 1.
KNOWLEDGE_DATES = ("2026-07-08", "2026-07-10", "2026-07-11", "2026-07-12", "2026-07-31")
N_SAMPLES = 1000
Z95 = 1.96


def wilson(hits, n):
    """The 95% Wilson score interval for hits out of n samples."""
    n = float(n)
    p = hits / n
    denom = 1.0 + Z95 * Z95 / n
    centre = (p + Z95 * Z95 / (2.0 * n)) / denom
    half = Z95 * np.sqrt(p * (1.0 - p) / n + Z95 * Z95 / (4.0 * n * n)) / denom
    return centre - half, centre + half


def main():
    empyrean.initialize()

    # -- 1. The observations and the knowledge sets ---------------------
    obs, _ = empyrean.read_ades(str(ASTROMETRY))
    print(f"{len(obs)} synthetic observations (JPL CNEOS, Epoch 1)")

    # The file states per-observation sigmas (0.1"/0.2") and these are
    # the exercise's truth model, so honor them instead of survey floors.
    stated_sigmas = ODConfig(
        weighting=WeightingConfig(
            sigma_policy=SigmaPolicy.DEFAULT_ONLY, additional_layers=[]
        )
    )

    nights = sorted({t[:10] for t in obs.obs_time.to_pylist()})
    assert all(d in nights for d in KNOWLEDGE_DATES), (
        "a knowledge date has no observations"
    )
    end_epoch = Epochs.from_mjd([65625.0], scale=TimeScale.TDB.value)  # 2038-07-20

    def knowledge_set(through_night: str):
        keep = [
            (through_night >= PRECOVERY_KNOWN)
            if t[:10] in PRECOVERY_NIGHTS
            else t[:10] <= through_night
            for t in obs.obs_time.to_pylist()
        ]
        return obs.apply_mask(keep)

    # -- 2. Replay the five knowledge dates ------------------------------
    print(
        "\nknowledge date  n_obs     linear  2nd-order       auto  "
        "Monte Carlo hits/N  95% Wilson interval   published (CNEOS/IAWN)"
    )
    rows = []
    for night in KNOWLEDGE_DATES:
        arc = knowledge_set(night)
        try:
            fit = empyrean.determine(arc, config=stated_sigmas).single()
        except ValueError:
            print(f"{night}    {len(arc):3d}   (no converged solution)")
            continue
        ips = empyrean.compute_impact_probabilities(
            fit.orbit,
            end_epoch,
            [
                UncertaintyMethod.FIRST_ORDER,
                UncertaintyMethod.SECOND_ORDER,
                UncertaintyMethod.AUTO,
                MonteCarlo(n_samples=N_SAMPLES, seed=42),
            ],
            body_filter=[Origin.EARTH],
        )
        by_method = {ips.method[i].as_py(): i for i in range(len(ips))}
        ip_lin = ips.ip_linear[by_method["first_order"]].as_py()
        ip_2nd = ips.ip_second_order[by_method["second_order"]].as_py()
        a = by_method["auto"]
        ip_auto = next(
            v
            for v in (
                ips.ip_agm[a].as_py(),
                ips.ip_second_order[a].as_py(),
                ips.ip_linear[a].as_py(),
            )
            if v is not None
        )
        m = by_method["monte_carlo"]
        n_mc = ips.mc_n_samples[m].as_py()
        assert n_mc, "the Monte Carlo row carries no samples"
        # The wrapper stores zero impacts as null; the row's own fraction tells a
        # measured 0 from an absent count.
        hits = ips.mc_n_impacts[m].as_py() or 0
        assert abs(ips.ip_mc[m].as_py() - hits / n_mc) < 1e-12
        lo, hi = wilson(hits, n_mc)
        rows.append((night, len(arc), ip_lin, ip_2nd, ip_auto, hits, n_mc, lo, hi))
        pub = PUBLISHED.get(night)
        print(
            f"{night}    {len(arc):3d}  "
            f"{ip_lin:9.5f}  {ip_2nd:9.5f}  {ip_auto:9.5f}  "
            f"{hits:5d}/{n_mc}       [{lo:.4f}, {hi:.4f}]"
            + (f"   {pub:.3f}" if pub is not None else "")
        )

    # -- 3. Epoch 1, one line per method ----------------------------------
    night, n_obs, ip_lin, ip_2nd, ip_auto, hits, n_mc, lo, hi = rows[-1]
    print(
        f"\nEpoch 1 ({night}, {n_obs} observations), impact probability "
        f"for 2038-07-10 by method:"
    )
    print(f"  linear        {ip_lin:.5f}")
    print(f"  second order  {ip_2nd:.5f}")
    print(f"  auto          {ip_auto:.5f}")
    print(
        f"  Monte Carlo   {hits}/{n_mc} = {hits / n_mc:.4f}, 95% Wilson interval [{lo:.4f}, {hi:.4f}]"
    )
    print(f"  published     {PUBLISHED[night]:.3f} (CNEOS / IAWN 2026-08-01)")


main()
# empyrean:snippet:end
