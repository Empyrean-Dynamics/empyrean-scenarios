"""2026 ED138: a large trans-Neptunian object, 49 years of astrometry.

Reproduces the 2026ed138 explore-mode scenario from
https://empyrean-dynamics.com/explore/2026ed138.

Run:
    pip install empyrean
    python 2026_ED138/main.py

What it does:
    1. Queries the Minor Planet Center (MPC) for 2026 ED138's astrometry and
       prints the record; two named filters (FIRST_USABLE, LAST_NIGHT) pick the
       observations the fit uses.
    2. Fits the orbit from a cold start with the engine's default weighting and
       compares it with JPL's solution element by element.
    3. Shows what the observations from 1960 to 2009 add to the 2010-and-later arc.
    4. Gives the diameter for three albedos from the paper's calibrated H_V.
    5. Follows the barycentric orbit through 1,093 years of the planetary
       ephemeris and tests the 12:7 resonance with Neptune.
    6. Compares the orbit with the discovery paper's adopted fit at its epoch.
    7. Reads the position uncertainty across the span.

Authoritative cross-checks (printed inline, labeled, never fitted to):
    - JPL SBDB solution of 2026-10-29: 115 observations, 1937-12-30 to
      2026-07-11; elements and 1 sigma at MJD 61200 TDB
    - Holman, Jurić, Napier et al. 2026, arXiv:2610.38693: H_V and Table 2
    - Souami and Souchay 2012 (the invariable plane); Khain et al. 2020 (the
      resonance criteria the paper applies)
"""

from __future__ import annotations

import hashlib
import sys

# empyrean:snippet:start
import empyrean
import numpy as np
from empyrean import (
    Epochs,
    Frame,
    KeplerianOrbits,
    ODConfig,
    Origin,
    TimeScale,
    UncertaintyMethod,
    transform_orbits,
)
from empyrean.od.result import OutputEpoch, OutputEpochMode

# Two named filters on the MPC record, which is queried live below. Each keeps
# the observations at or after / at or before a UTC time.
# FIRST_USABLE: before 1960 empyrean 0.11 cannot convert UTC to TDB, so the
# 1937 and 1954 plates are in the record but held out here; the release that
# reads pre-1960 times lowers this to "1937".
FIRST_USABLE = "1960-01-01"
# LAST_NIGHT: the last night of JPL's solution (2026-10-29) and of the discovery
# paper's fit, so the three orbits are compared on the same end of the arc and
# observations the MPC adds later do not move the numbers.
LAST_NIGHT = "2026-07-11T23:59"
# JPL SBDB solution of 2026-10-29 (SBDB-published values, nothing derived by
# empyrean): 115 observations, 1937-12-30 to 2026-07-11 (an 89-year arc), ecliptic
# J2000, epoch MJD 61200 TDB (2026-06-09): a, e, i, node, argument of perihelion,
# mean anomaly (au, degrees) and their 1 sigma.
JPL = (
    42.94869526572302,
    0.1417448328770402,
    24.47104038674766,
    322.5008984905298,
    167.9532328404424,
    128.3342024098231,
)
JPL_SIGMA = (0.00052895, 2.3485e-6, 2.5475e-5, 8.2894e-5, 0.0041598, 0.0049194)
# Calibrated V-band absolute magnitude at zero phase, Holman et al. 2026
# (arXiv:2610.38693), Table 3; the MPC and SBDB H comes from redder bands.
H_V, H_V_SIGMA = 3.19, 0.04
# Holman et al. 2026, Table 2: adopted fit (74 observations, 2016-02-25 to
# 2026-07-11), barycentric ecliptic J2000 at MJD 59337.8171 TDB: a, e, i, node,
# argument of perihelion, mean anomaly, q, and their 1 sigma.
PAPER_EPOCH = 59337.8171
PAPER = (43.090975, 0.1387280, 24.4338512, 322.606057, 168.6998, 121.0797, 37.11305)
# Uncertainties facing below / above (a, e, q, i are the paper's delta-chi^2 = 1
# profile ranges; node, argument of perihelion and mean anomaly are its 1 sigma).
PAPER_SIGMA = (
    (6.0e-5, 5.6e-5),
    (7.4e-6, 7.4e-6),
    (1.8e-6, 1.8e-6),
    (2.9e-5, 2.9e-5),
    (2.8e-3, 2.8e-3),
    (4.0e-3, 4.0e-3),
    (2.7e-4, 2.7e-4),
)
PAPER_PROPER_INCLINATION = 25.7  # deg, Holman et al. 2026 Table 2
# Masses in solar masses (the Sun with the inner planets added, and the giants'
# systems) for the invariable plane, as in the paper's integration.
MASSES = {
    Origin.SUN: 1.000005977,
    Origin.JUPITER_BARYCENTER: 9.54792e-4,
    Origin.SATURN_BARYCENTER: 2.85886e-4,
    Origin.URANUS_BARYCENTER: 4.36625e-5,
    Origin.NEPTUNE_BARYCENTER: 5.15139e-5,
}
GM_SUN = 2.959122082855911e-4  # au^3/d^2
# The Sun plus the planets, for barycentric osculating elements (the TNO
# convention, Elliot et al. 2005).
GM_SYSTEM = GM_SUN * (1.0 + 1.341839e-3)
AU_KM = 149_597_870.7
NAMES = (
    "a (au)",
    "e",
    "i (deg)",
    "node (deg)",
    "arg. perihelion (deg)",
    "mean anomaly (deg)",
)


def fmt(value, sigma):
    """The value to one digit beyond its sigma."""
    return f"{value:.{max(0, 1 - int(np.floor(np.log10(sigma)))):d}f}"


def keplerian(orbit):
    k = transform_orbits(
        orbit, KeplerianOrbits, frame=Frame.ECLIPTICJ2000, origin=Origin.SUN
    )
    c = k.coordinates
    value = np.array(
        [c.table.column(n)[0].as_py() for n in ("a", "e", "i", "raan", "ap", "ma")]
    )
    sigma = np.sqrt(np.diag(np.asarray(k.covariance.joint(0).state_block())))
    return value, sigma


def elements(x, v):
    """Osculating elements about the barycenter from barycentric states (columns)."""
    r = np.linalg.norm(x, axis=0)
    h = np.cross(x.T, v.T).T
    hn = np.linalg.norm(h, axis=0)
    a = 1.0 / (2.0 / r - (v * v).sum(0) / GM_SYSTEM)
    ev = np.cross(v.T, h.T).T / GM_SYSTEM - x / r
    e = np.linalg.norm(ev, axis=0)
    node = np.array([-h[1], h[0], 0.0 * h[0]])
    nn = np.linalg.norm(node, axis=0)
    raan = np.arctan2(node[1], node[0])
    w = np.arctan2(
        (np.cross(node.T, ev.T).T * h / hn).sum(0) / (nn * e),
        (node * ev).sum(0) / (nn * e),
    )
    nu = np.arctan2(
        (np.cross(ev.T, x.T).T * h / hn).sum(0) / (e * r), (ev * x).sum(0) / (e * r)
    )
    ecc = 2.0 * np.arctan2(
        np.sqrt(1 - e) * np.sin(nu / 2), np.sqrt(1 + e) * np.cos(nu / 2)
    )
    return a, e, np.arccos(h[2] / hn), raan, w, ecc - e * np.sin(ecc)


def ssb_states(states):
    c = states.coordinates
    assert set(c.origin.to_pylist()) == {"SSB"}, "expected barycentric states"
    assert c.frame == Frame.ECLIPTICJ2000.value, "expected ecliptic J2000"
    x = np.array([getattr(c, n).to_numpy(zero_copy_only=False) for n in "xyz"])
    v = np.array(
        [getattr(c, n).to_numpy(zero_copy_only=False) for n in ("vx", "vy", "vz")]
    )
    return c.epochs.mjd.to_numpy(zero_copy_only=False), x, v


def window(obs, first):
    """The observations from `first` through LAST_NIGHT (UTC)."""
    return obs.apply_mask([first <= t <= LAST_NIGHT for t in obs.obs_time.to_pylist()])


def fit(obs, first):
    """Cold orbit determination on the observations from `first` onward."""
    epoch = Epochs.from_mjd([61200.0], scale=TimeScale.TDB.value)
    config = ODConfig(
        output_epoch=OutputEpoch(mode=OutputEpochMode.EXPLICIT, epoch=epoch)
    )
    result = empyrean.determine(window(obs, first), config=config).single()
    assert (
        abs(result.orbit.coordinates.epochs.mjd_tdb()[0] - 61200.0) < 1e-9
    )  # the epoch is stored as UTC
    return result, len(window(obs, first))


def main():
    empyrean.initialize()

    # -- 1. The record -------------------------------------------------
    obs = empyrean.query_observations(["2026 ED138"])
    # Keep the observations through LAST_NIGHT (UTC): the frozen arc the numbers use.
    obs = obs.apply_mask([t <= LAST_NIGHT for t in obs.obs_time.to_pylist()])
    times = obs.obs_time.to_pylist()
    print(
        f"{len(obs)} observations of 2026 ED138 in the MPC record through {LAST_NIGHT[:10]}, "
        f"{min(times)[:10]} to {max(times)[:10]}"
    )
    decades = {}
    for t in times:
        decades[t[:3] + "0s"] = decades.get(t[:3] + "0s", 0) + 1
    print("By decade: " + ", ".join(f"{d} {n}" for d, n in sorted(decades.items())))
    held = sum(t < FIRST_USABLE for t in times)
    print(
        f"{held} observations before {FIRST_USABLE[:4]} held out; "
        f"observations after {LAST_NIGHT[:10]} are not used"
    )
    for t, stn, rms, note in sorted(
        zip(times, obs.stn.to_pylist(), obs.rms_ra.to_pylist(), obs.remarks.to_pylist())
    ):
        if t < FIRST_USABLE:
            print(f"  {t[:10]} station {stn}, stated {rms:.2f} arcsec: {note}")
    print(f"{len(set(obs.stn.to_pylist()))} stations")

    # -- 2. The orbit from the modern arc ------------------------------
    result, n_used = fit(obs, FIRST_USABLE)
    s = result.summary
    print(
        f"\nFit from {FIRST_USABLE[:4]}: {s.num_selected}/{n_used} observations, "
        f'chi2/dof {s.reduced_chi2:.3f}, RMS RA.cos(d) {s.rms_ra_arcsec:.3f}" '
        f'Dec {s.rms_dec_arcsec:.3f}"'
    )
    print(
        "Default weighting: stated sigma with station floors and nightly de-weighting. "
        "Per station (stated sigma, sigma the fit applies, median |RA residual|, arcsec):"
    )
    res = result.observations
    codes = res.obs_code.to_pylist()
    applied = np.sqrt(res.residual_cov_ra.to_numpy(zero_copy_only=False))
    resid = np.abs(res.ra_residual.to_numpy(zero_copy_only=False))
    keep = [FIRST_USABLE <= t <= LAST_NIGHT for t in times]
    stated = obs.rms_ra.to_numpy(zero_copy_only=False)[keep]
    stations = obs.stn.to_pylist()
    stations = [c for c, k in zip(stations, keep) if k]
    for code in sorted(set(stations), key=lambda c: (-stations.count(c), c))[:6]:
        a_i = [i for i, c in enumerate(codes) if c == code]
        s_i = [i for i, c in enumerate(stations) if c == code]
        stated_med = (
            np.nanmedian(stated[s_i])
            if np.isfinite(stated[s_i]).any()
            else float("nan")
        )
        print(
            f"  {code}: {len(a_i):3d} observations, stated {stated_med:.3f}, applied "
            f"{np.median(applied[a_i]):.3f}, |residual| {np.median(resid[a_i]):.3f}"
        )
    used = sorted(t for t in times if FIRST_USABLE <= t <= LAST_NIGHT)
    span_years = (
        Epochs.from_iso([used[-1]], scale=TimeScale.UTC.value)
        .to_tdb()
        .mjd.to_numpy()[0]
        - Epochs.from_iso([used[0]], scale=TimeScale.UTC.value)
        .to_tdb()
        .mjd.to_numpy()[0]
    ) / 365.25
    print(f"Arc used: {used[0][:10]} to {used[-1][:10]} ({span_years:.1f} years)")
    value, sigma = keplerian(result.orbit)
    print(
        "Elements, ecliptic J2000 at 2026-06-09 (TDB), with 1 sigma, and JPL's difference:"
    )
    for name, v, sg, j, js in zip(NAMES, value, sigma, JPL, JPL_SIGMA):
        print(
            f"  {name:22s} {fmt(v, sg):>12s} +/- {sg:.1e}   (ours - JPL) = {(v - j) / js:+.2f} "
            f"JPL sigma; JPL sigma {js:.1e}, ours/JPL {sg / js:.1f}"
        )

    # -- 3. What the older plates add -----------------------------------
    print("\n1 sigma by arc, under the default weights only:")
    print(
        f"  {'first year':>10s} {'obs':>4s}   a (au)     arg. perihelion   mean anomaly"
    )
    rows = []
    for first in ("2010", FIRST_USABLE):
        r, n = fit(obs, first)
        _, sg = keplerian(r.orbit)
        rows.append(sg)
        print(
            f"  {first[:4]:>10s} {n:4d}   {sg[0]:.2e}   {sg[4]:.2e} deg   {sg[5]:.2e} deg"
            f'   RMS {r.summary.rms_ra_arcsec:.3f}" / {r.summary.rms_dec_arcsec:.3f}"'
        )
    change = 100.0 * (1.0 - rows[1] / rows[0])
    print(
        f"  Adding the observations of {FIRST_USABLE[:4]} to 2009 lowers sigma by {change[0]:.0f}% "
        f"(a), {change[4]:.0f}% (arg. perihelion), {change[5]:.0f}% (mean anomaly)"
    )

    # -- 4. Size from the absolute magnitude -----------------------------
    print(
        f"\nH_V = {H_V} +/- {H_V_SIGMA} (Holman et al. 2026); diameter 1329 km / sqrt(albedo) x 10^(-H_V/5):"
    )
    for albedo in (0.25, 0.10, 0.04):
        d = 1329.0 / np.sqrt(albedo) * 10.0 ** (-H_V / 5.0)
        print(
            f"  albedo {albedo:.2f}: {d:6.0f} +/- {d * np.log(10.0) / 5.0 * H_V_SIGMA:3.0f} km"
        )

    # -- 5. Resonance with Neptune over the span the planets cover -------
    # Barycentric elements, as the TNO classification uses. DE440 covers 1550
    # to 2650; phi = p*lambda - q*lambda_N - (p - q)*varpi for resonances with a
    # period ratio P/P_N = p/q near this orbit.
    grid = Epochs.from_kwargs(
        mjd=[-112000.0 + 730.0 * i for i in range(548)], scale=TimeScale.TDB.value
    )
    path = empyrean.propagate(
        result.orbit, grid, uncertainty_method=UncertaintyMethod.FIRST_ORDER
    )
    t, x, v = ssb_states(path.states)

    def planet(origin):
        st = empyrean.get_states(
            target=origin,
            center=Origin.SSB,
            epochs=Epochs.from_kwargs(mjd=t.tolist(), scale=TimeScale.TDB.value),
            frame=Frame.ECLIPTICJ2000,
        )
        return (
            np.array([getattr(st, n).to_numpy(zero_copy_only=False) for n in "xyz"]),
            np.array(
                [
                    getattr(st, n).to_numpy(zero_copy_only=False)
                    for n in ("vx", "vy", "vz")
                ]
            ),
        )

    # The invariable plane: perpendicular to the system's angular momentum
    # (taken at the sample nearest 2026), the paper's reference plane.
    k_now = int(np.argmin(np.abs(t - 61200.0)))
    momentum = sum(
        m * np.cross(planet(o)[0][:, k_now], planet(o)[1][:, k_now])
        for o, m in MASSES.items()
    )
    z_axis = momentum / np.linalg.norm(momentum)
    x_axis = np.cross([0.0, 0.0, 1.0], z_axis)
    x_axis /= np.linalg.norm(x_axis)
    rotation = np.array([x_axis, np.cross(z_axis, x_axis), z_axis])
    print(
        f"Invariable plane: {np.degrees(np.arccos(z_axis[2])):.3f} deg from the ecliptic, "
        f"node {np.degrees(np.arctan2(z_axis[0], -z_axis[1])) % 360:.2f} deg"
    )
    x, v = rotation @ x, rotation @ v
    a, e, inc, node, w, ma = elements(x, v)
    nx, nv = planet(Origin.NEPTUNE_BARYCENTER)
    a_n, _, _, node_n, w_n, ma_n = elements(rotation @ nx, rotation @ nv)
    lam, lam_n, varpi = node + w + ma, node_n + w_n + ma_n, node + w

    def arc_containing(angle):
        """Smallest arc (degrees) that holds every sampled angle."""
        d = np.sort(np.degrees(angle % (2 * np.pi)))
        return 360.0 - np.diff(np.concatenate([d, [d[0] + 360.0]])).max()

    years = (t[-1] - t[0]) / 365.25
    print(
        f"\nOver {years:,.0f} years (1552 to 2645), barycentric, invariable plane: a {a.min():.2f} to {a.max():.2f} au "
        f"(mean {a.mean():.3f}), e {e.min():.3f} to {e.max():.3f}, i {np.degrees(inc.min()):.2f} to "
        f"{np.degrees(inc.max()):.2f} deg, perihelion {(a * (1 - e)).min():.1f} au at its closest"
    )
    print(f"At the sample nearest 2026 (MJD {t[k_now]:.0f}) a = {a[k_now]:.3f} au.")
    print(
        f"Mean inclination over the span, invariable plane: {np.degrees(inc).mean():.2f} deg "
        f"(the paper's proper inclination: {PAPER_PROPER_INCLINATION} deg; a mean of osculating values against a proper element)"
    )
    print(
        f"Neptune: a = {a_n.mean():.2f} au. Resonant argument (arc that holds every sample; 360 = circulates):"
    )
    for p, q in ((5, 3), (17, 10), (12, 7), (19, 11), (7, 4)):
        a_res = a_n.mean() * (p / q) ** (2.0 / 3.0)
        phi = np.unwrap(p * lam - q * lam_n - (p - q) * varpi)
        print(
            f"  {p}:{q} (order {p - q}, exact at a = {a_res:.3f} au, offset {a.mean() - a_res:+.3f}): "
            f"{arc_containing(phi):5.0f} deg; net change {np.degrees(phi[-1] - phi[0]):+.0f} deg, "
            f"{np.degrees(phi[-1] - phi[0]) / years:+.3f} deg/yr"
        )

    # The paper's argument for the same resonance (its 10-Myr integration finds it
    # librating about 180 degrees with 95 to 115 degrees amplitude).
    mixed = np.unwrap(12 * lam - 7 * lam_n - 3 * varpi - 2 * node)
    print(
        f"12:7, the paper's argument 12 lambda - 7 lambda_N - 3 varpi - 2 node: "
        f"{arc_containing(mixed):.0f} deg, net change {np.degrees(mixed[-1] - mixed[0]):+.0f} deg, "
        f"{np.degrees(mixed[-1] - mixed[0]) / years:+.3f} deg/yr; mean {np.degrees(np.angle(np.exp(1j * mixed).mean())) % 360:.0f} deg"
    )

    # -- 6. Against the discovery paper, at its epoch, in its elements ----
    at = empyrean.propagate(
        result.orbit,
        Epochs.from_mjd([PAPER_EPOCH], scale=TimeScale.TDB.value),
        uncertainty_method=UncertaintyMethod.FIRST_ORDER,
    )
    _, bx, bv = ssb_states(at.states)
    state = np.concatenate([bx[:, 0], bv[:, 0]])
    cov = np.asarray(at.states.covariance.joint(0).state_block())

    def barycentric(s6):
        ea, ee, ei, en, ew, em = (u[0] for u in elements(s6[:3, None], s6[3:, None]))
        return np.array(
            [
                ea,
                ee,
                np.degrees(ei),
                np.degrees(en) % 360,
                np.degrees(ew) % 360,
                np.degrees(em) % 360,
                ea * (1 - ee),
            ]
        )

    jac = np.zeros((7, 6))
    for n in range(6):
        h = 1e-7 * max(abs(state[n]), 1e-3 if n < 3 else 1e-5)
        step = np.zeros(6)
        step[n] = h
        d = barycentric(state + step) - barycentric(state - step)
        d[3:6] = (d[3:6] + 180.0) % 360.0 - 180.0
        jac[:, n] = d / (2.0 * h)
    ours = barycentric(state)
    ours_sigma = np.sqrt(np.diag(jac @ cov @ jac.T))
    print(
        f"Barycentric ecliptic elements at MJD {PAPER_EPOCH} TDB (the paper's epoch), against its Table 2:"
    )
    print("  (the paper's a, e, q, i uncertainties are delta-chi^2 = 1 profile ranges)")
    for name, o, so, p, (s_dn, s_up) in zip(
        ("a", "e", "i", "node", "arg. perihelion", "mean anomaly", "q"),
        ours,
        ours_sigma,
        PAPER,
        PAPER_SIGMA,
    ):
        d = o - p
        if name in ("node", "arg. perihelion", "mean anomaly"):
            d = (d + 180.0) % 360.0 - 180.0
        sp = s_up if d > 0 else s_dn
        print(
            f"  {name:16s} {fmt(o, so):>12s} +/- {so:.1e}  paper {p:.7g} +{s_up:.1e}/-{s_dn:.1e}  "
            f"difference {d / so:+.2f} of our sigma, {d / sp:+.1f} of the paper's"
        )

    # -- 7. How far the orbit can be followed -----------------------------
    sig = np.array(
        [
            np.sqrt(
                np.trace(
                    np.asarray(path.states.covariance.joint(i).state_block())[:3, :3]
                )
            )
            for i in range(len(path.states))
        ]
    )
    print("\n1-sigma position uncertainty (first order, nearest 2-year sample):")
    for target in (
        t[0],
        -250 * 365.25 + 61200.0,
        -100 * 365.25 + 61200.0,
        61200.0,
        100 * 365.25 + 61200.0,
        250 * 365.25 + 61200.0,
        t[-1],
    ):
        k = int(np.argmin(np.abs(t - target)))
        year = 2000.0 + (t[k] - 51544.5) / 365.25
        print(
            f"  {year:7.1f} (MJD {t[k]:8.0f}): {sig[k] * AU_KM:12,.0f} km ({sig[k]:.4f} au) at {np.linalg.norm(x[:, k]):.1f} au"
        )

    return obs


obs = main()
# empyrean:snippet:end

# Drift check, outside the snippet: the published numbers are for exactly these
# observations: every row through LAST_NIGHT, the held-out ones and their
# remarks included. If the MPC re-measures, deletes or adds a row through
# LAST_NIGHT, stop instead of printing numbers for a different arc.
EXPECTED_COUNT = 129
EXPECTED_SHA256 = "c0607791935532a98086beaea7eac6e60b5f37465d7e726725fba803334f8162"
found_ids = "\n".join(sorted(obs.obs_id.to_pylist()))
found_sha256 = hashlib.sha256(found_ids.encode()).hexdigest()
if len(obs) != EXPECTED_COUNT or found_sha256 != EXPECTED_SHA256:
    sys.exit(
        f"The MPC record changed through LAST_NIGHT: expected {EXPECTED_COUNT} "
        f"observations with sha256 {EXPECTED_SHA256} of the sorted obsIDs, found "
        f"{len(obs)} with {found_sha256}. The numbers above are for a different arc."
    )
