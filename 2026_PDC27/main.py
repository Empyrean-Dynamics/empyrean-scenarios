"""2026 PDC27: replaying a planetary-defense exercise, method by method.

Reproduces the 2026pdc27 explore-mode scenario from
https://empyrean-dynamics.com/explore/2026pdc27.

**2026 PDC27 is a fictional asteroid** — the hypothetical-impact
exercise object of the IAA 2027 Planetary Defense Conference
(Montreal, May 2027). "This is only an exercise." (JPL CNEOS)

Run:
    pip install empyrean
    python 2026_PDC27/main.py     # ~20 min: per-step Monte Carlo

What it does:
    1. Reads the committed Epoch-1 synthetic astrometry (52 geocentric
       observations released by JPL CNEOS, transcribed to ADES PSV).
    2. Replays the exercise's knowledge timeline: cumulative fits
       night by night, with the six Rubin/LSST precovery nights
       entering all at once on 2026-07-12 — exactly as the exercise's
       astronomers received them.
    3. At every step, computes the 2038-07-10 impact probability four
       ways — linear, second-order, AUTO (κ-laddered), Monte Carlo —
       against the exercise's published checkpoints: 0.1% (Jul 8),
       16% (Jul 12, the precovery jump), 19% (Epoch 1).
    4. Prints the per-step method table; the notebook twin renders it
       as the IP-evolution figure.

The point: at a twelve-year horizon the encounter mapping is deeply
nonlinear (κ ≈ 13–50), the analytic methods disagree with each other
by up to two orders of magnitude, and only the sampling method tracks
the published values at every step. κ — which AUTO computes for free —
is the number that tells you when to stop trusting analytics.
"""

from __future__ import annotations

from pathlib import Path

import empyrean

# empyrean:snippet:start
import numpy as np
from empyrean import Epochs, ODConfig, Origin, TimeScale, UncertaintyMethod
from empyrean.od.result import SigmaPolicy, WeightingConfig
from empyrean.propagation.config import MonteCarlo

HERE = Path(__file__).parent

# The exercise's published IP checkpoints (CNEOS / IAWN).
PUBLISHED = {"2026-07-08": 0.001, "2026-07-12": 0.16, "2026-07-31": 0.19}
PRECOVERY_NIGHTS = {
    "2026-05-11",
    "2026-05-17",
    "2026-05-23",
    "2026-06-04",
    "2026-06-10",
    "2026-06-16",
}
PRECOVERY_KNOWN = "2026-07-12"  # found in Rubin archives on this date


def main() -> None:
    empyrean.initialize()

    obs, _ = empyrean.read_ades(str(HERE / "astrometry.psv"))
    print(f"{len(obs)} synthetic observations (JPL CNEOS, Epoch 1)")

    # The file states per-observation sigmas (0.1"/0.2") and these are
    # the exercise's truth model — honor them instead of survey floors.
    stated_sigmas = ODConfig(
        weighting=WeightingConfig(
            sigma_policy=SigmaPolicy.DEFAULT_ONLY, additional_layers=[]
        )
    )

    nights = sorted({t[:10] for t in obs.obs_time.to_pylist()})
    apparition = [n for n in nights if n not in PRECOVERY_NIGHTS]
    end_epoch = Epochs.from_mjd([65625.0], scale=TimeScale.TDB.value)  # 2038-07-20

    def knowledge_set(through_night: str):
        keep = [
            (through_night >= PRECOVERY_KNOWN)
            if t[:10] in PRECOVERY_NIGHTS
            else t[:10] <= through_night
            for t in obs.obs_time.to_pylist()
        ]
        return obs.apply_mask(keep)

    print(
        "\nknowledge date  n_obs  kappa      linear   2nd-order      auto"
        "        MC (95% CI)     published"
    )
    rows = []
    for night in apparition[3:]:  # need a few nights before IOD is stable
        arc = knowledge_set(night)
        try:
            fit = empyrean.determine(arc, config=stated_sigmas).single()
        except ValueError:
            print(f"{night}     {len(arc):3d}   (no converged solution yet)")
            continue
        ips = empyrean.compute_impact_probabilities(
            fit.orbit,
            end_epoch,
            [
                UncertaintyMethod.FIRST_ORDER,
                UncertaintyMethod.SECOND_ORDER,
                UncertaintyMethod.AUTO,
                MonteCarlo(n_samples=1000, seed=42),
            ],
            body_filter=[Origin.EARTH],
        )
        by_method = {ips.method[i].as_py(): i for i in range(len(ips))}
        ip_lin = ips.ip_linear[by_method["first_order"]].as_py()
        ip_2nd = ips.ip_second_order[by_method["second_order"]].as_py()
        kappa = ips.nonlinearity[by_method["second_order"]].as_py()
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
        ip_mc = ips.ip_mc[m].as_py()
        ci = ips.mc_confidence_interval[m].as_py()
        pub = PUBLISHED.get(night)
        rows.append((night, len(arc), kappa, ip_lin, ip_2nd, ip_auto, ip_mc, ci, pub))
        print(
            f"{night}    {len(arc):3d}  {kappa:6.1f}  "
            f"{ip_lin:9.5f}  {ip_2nd:9.5f}  {ip_auto:9.5f}  "
            f"{ip_mc:6.3f} ±{ci:5.3f}  "
            + (f"  ← {pub:.3f} published" if pub is not None else "")
        )

    # Machine-readable dump for the notebook's figure.
    np.save(
        HERE / "ip_evolution.npy",
        np.array(
            [
                (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8] or np.nan)
                for r in rows
            ],
            dtype=object,
        ),
        allow_pickle=True,
    )

    final = rows[-1]
    print(
        f"\nEpoch-1 verdict: MC {final[6]:.3f} ± {final[7]:.3f} vs published 0.19 — "
        f"linear {final[3]:.3f}, second-order {final[4]:.5f}, auto {final[5]:.3f}"
    )
    print(
        "Only the sampling method tracks the published values; κ ≈ "
        f"{final[2]:.0f} is the warning label on every analytic number."
    )


# empyrean:snippet:end


if __name__ == "__main__":
    main()
