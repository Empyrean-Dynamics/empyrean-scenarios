"""2024 YR4: dual-OD-fit story (early-arc with IP → full-arc IP=0).

Reproduces the 2024yr4 explore-mode scenario from
https://empyrean-dynamics.com/explore/2024yr4.

Run:
    pip install empyrean
    python 2024_YR4/main.py

What it does:
    1. Pulls every available MPC astrometric observation of 2024 YR4.
    2. Filters to the discovery arc (≤ ~2025-01-05) and runs a
       short-arc OD; second pass uses the full arc.
    3. Propagates both fits to the 2032 Earth encounter and reads
       impact probabilities. Early arc surfaces ~0.14% Earth IP with a
       ~12-lunar-distance miss sigma; the full arc collapses it to
       zero. Sentry's published peak was 3.1%
       on 2025-02-18 — different arc cuts give different IPs, all
       legitimately within published uncertainty bounds.

Authoritative cross-checks (printed inline):
    - Discovery 2024-12-27 by ATLAS at Río Hurtado, Chile
    - Sentry peak IP = 3.1% on 2025-02-18 (55-day arc)
    - 2032-12-22 nominal Earth approach: ~278,000 km   (JPL CAD)
    - 2032-12-22 nominal Moon approach:  ~23,000 km    (JPL CAD)
"""

from __future__ import annotations

# spielberg:snippet:start
import numpy as np

import empyrean
from empyrean import Epochs, Origin, TimeScale, UncertaintyMethod


def main() -> None:
    empyrean.initialize()

    # ── 1. Astrometric observations from MPC ────────────────────────
    obs = empyrean.query_observations(["2024 YR4"])
    print(f"{len(obs)} observations from MPC (full arc)")

    # ── 2. Slice to the discovery arc ───────────────────────────────
    # ADESObservations carries obs_time as ISO-8601 UTC strings; convert
    # to MJD via Epochs to filter on time.
    iso_strings = obs.obs_time.to_pylist()
    obs_mjd = Epochs.from_iso(iso_strings, scale=TimeScale.UTC.value).mjd.to_numpy()
    discovery_arc = obs.apply_mask(obs_mjd < 60680.0)  # ~2025-01-05
    print(f"{len(discovery_arc)} observations in the discovery arc (~10 days)")

    # ── 3. Two OD fits ──────────────────────────────────────────────
    def _summary(label: str, r) -> None:
        s = r.summary
        print(
            f"{label}: chi2/dof = {s.reduced_chi2:.3f}  "
            f'RMS RA·cos(d) {s.rms_ra_arcsec:.3f}" Dec {s.rms_dec_arcsec:.3f}"  '
            f"({s.num_selected}/{s.num_obs} obs)"
        )

    early = empyrean.determine(discovery_arc)
    _summary("Discovery arc", early)

    full = empyrean.determine(obs)
    _summary("Full arc     ", full)

    # ── 4. Impact probabilities at the 2032 encounter for both fits ──
    # The covariance-aware IP comes from compute_impact_probabilities —
    # the fitted orbit carries its 6×6 covariance, which is mapped to
    # the encounter B-plane. (Reading sigma_d / IP off the propagation
    # event stream would not work: possible_impact events are purely
    # geometric — they carry the nominal miss distance only.)
    end_epoch = 63730.0  # ~2032-12-31, MJD TDB

    print("\n2032 encounter — impact probability + miss geometry:")
    for label, fit in [("early arc", early), ("full arc", full)]:
        ips = empyrean.compute_impact_probabilities(
            fit.orbit,
            end_epoch,
            [UncertaintyMethod.SECOND_ORDER],
            body_filter=[Origin.EARTH, Origin.MOON],
        )
        body = ips.body.to_pylist()
        miss_km = ips.miss_distance_km.to_numpy(zero_copy_only=False)
        sigma_km = ips.sigma_distance_km.to_numpy(zero_copy_only=False)
        ip_linear = ips.ip_linear.to_numpy(zero_copy_only=False)
        for i in range(len(ips)):
            print(
                f"  {label:9s}  {body[i]:6s}  "
                f"IP_linear = {ip_linear[i]:>7.3%}  "
                f"miss = {miss_km[i]:>10.1f} km  "
                f"sigma_d = {sigma_km[i]:>10.1f} km"
            )

    # Full-arc SecondOrder propagation across the 2032 encounter, used
    # for the tagged-covariance readback in section 5.
    epochs = Epochs.from_kwargs(
        mjd=[61000.0 + 10.0 * i for i in range(271)],
        scale=TimeScale.TDB.value,
    )
    full_prop = empyrean.propagate(
        full.orbit,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
        tagged_covariance=True,
    )

    # ── 5. Tagged-covariance readback through the 2032 flyby ─────────
    # The bare linear covariance carried on the propagated states is
    # Phi Sigma0 Phi^T — it ignores the curvature of the dynamics across
    # the encounter. Near a planetary close approach that curvature
    # matters, so we read the *resolved-kind* (Park–Scheeres second-order)
    # covariance back from the full-arc SecondOrder propagation and
    # contrast it with the linear one at perigee.
    peri = full_prop.events.periapses
    bodies = peri.body.to_pylist()
    peri_mjd = peri.epoch.to_numpy(zero_copy_only=False)
    ca_mjd = next(peri_mjd[i] for i in range(len(bodies)) if bodies[i] == "Earth")

    # Resolved-kind covariance, one tag per output epoch. The states
    # table is NOT request-ordered (encounter episodes are grouped by
    # origin), so each table is looked up by its own epoch column.
    series = full_prop.tagged_covariance_series(0)
    out_mjd = np.array([tc.epoch_mjd_tdb for tc in series])
    k = int(np.argmin(np.abs(out_mjd - ca_mjd)))
    state_mjd = full_prop.states.coordinates.epoch.to_numpy(zero_copy_only=False)
    k_state = int(np.argmin(np.abs(state_mjd - ca_mjd)))

    def _pos_sigma_km(m) -> float:
        m = np.asarray(m)
        return float(np.sqrt(m[0, 0] + m[1, 1] + m[2, 2])) * 149_597_870.7

    resolved = series[k]
    resolved_sigma = _pos_sigma_km(resolved.matrix)
    # The bare linear covariance lives on the propagated states.
    linear = full_prop.states.coordinates.covariance.to_matrix()
    linear_sigma = _pos_sigma_km(linear[k_state])

    print(f"\nTagged-covariance readback at 2032 Earth perigee (MJD {ca_mjd:.4f} TDB):")
    print(f"  resolved kind        = {resolved.kind}")
    print(
        f"  resolved pos sigma   = {resolved_sigma:>10.1f} km  (second-order ellipsoid)"
    )
    print(f"  linear   pos sigma   = {linear_sigma:>10.1f} km  (bare Phi Sigma0 Phi^T)")

    print("\nReference (JPL CAD, full-arc nominal):")
    print("  Earth   ~278,000 km   IP = 0")
    print("  Moon    ~23,000 km    IP = 0   (inside Moon's Hill sphere)")
    print("Reference (Sentry, peak):")
    print("  Earth   55-day arc, 2025-02-18 published    IP = 3.1%")


# spielberg:snippet:end


if __name__ == "__main__":
    main()
