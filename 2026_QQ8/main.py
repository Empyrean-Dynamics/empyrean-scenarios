"""2026 QQ8: seen after the pass: sunlight and a captured flyby.

Reproduces the 2026qq8 explore-mode scenario from
https://empyrean-dynamics.com/explore/2026qq8.

Run:
    pip install empyrean
    python 2026_QQ8/main.py

What it does:
    1. Queries the Minor Planet Center (MPC) for 2026 QQ8's astrometry, keeps
       the observations through 2026-11-07T23:59 UTC (39 optical observations,
       the arc the published numbers use) and fits position and velocity.
    2. Refits with the solar-radiation-pressure area-to-mass ratio as an
       extra unknown, from a wide prior and not from JPL's solution; reports
       the detection, the A1 equivalent and JPL's value beside it.
    3. Turns the ratio into bulk-density lower bounds for three albedos.
    4. Classifies the capture: the engine's standard test (negative
       geocentric energy within three Hill radii), the closest approach, and
       the revolutions of Earth in the Sun-Earth rotating frame that
       separate a captured flyby from a captured orbiter.
    5. Reads the position uncertainty at the capture edges, the observations
       and a year past the capture, then lists the Earth passes under 0.05 au
       from 1952 to 2090 with their timing uncertainty.

Authoritative cross-checks (printed inline, labeled, never fitted to):
    - JPL SBDB solution of 2026-11-08: H = 31.367 +/- 0.342,
      A1 = 1.174e-10 +/- 2.777e-11 au/d^2 (r^-2 law)
    - Capture test: Granvik, Vaubaillon and Jedicke 2012; mini-moon
      (captured orbiter) test: Fedorets, Granvik and Jedicke 2017
"""

from __future__ import annotations

import hashlib
import sys

# empyrean:snippet:start
import empyrean
import numpy as np
from empyrean import (
    CartesianOrbits,
    CovarianceKind,
    Epochs,
    EventConfig,
    Frame,
    JointFunctional,
    JointProvenance,
    JointQuality,
    ODConfig,
    Origin,
    PackedJoint,
    PackedJoints,
    SolveFor,
    SolveForParams,
    SRPParams,
    TimeScale,
    UncertaintyMethod,
    transform_orbits,
)

AU_KM = 149_597_870.7
MU_EARTH = 398_600.4418  # km^3/s^2
LUNAR_DISTANCE_KM = 384_400.0
# Earth's Hill radius, Earth alone at 1 au: 1 au x (m_Earth / (3 m_Sun))^(1/3).
HILL_RADIUS_KM = AU_KM * (3.00348e-6 / 3.0) ** (1.0 / 3.0)
# The engine's radiation-pressure constant: 4.56e-6 N/m^2 at 1 au (about
# 1367 W/m^2 / c). One m^2/kg of area-to-mass ratio is this many au/d^2 of
# radial acceleration at 1 au under the r^-2 law, JPL's A1 convention.
K_SRP = 4.56e-6 * 86400.0**2 / 1.495978707e11  # au/d^2 per m^2/kg
# Priors, wide on every axis and not JPL's solution: 1e-2 au and 1e-4 au/d on
# the state, 1e-2 m^2/kg on the area-to-mass ratio (JPL's value is 5e-4).
STATE_SIGMA = (1e-2, 1e-2, 1e-2, 1e-4, 1e-4, 1e-4)
AMRAT_SEED = 1e-4  # m^2/kg, the prior mean (the fit starts here)
AMRAT_SIGMA = 1e-2
# JPL SBDB solution of 2026-11-08 (39 observations), the reference only.
JPL_H, JPL_H_SIGMA = 31.367, 0.342
JPL_A1, JPL_A1_SIGMA = 1.174e-10, 2.777e-11  # au/d^2, r^-2 law
# Labeled comparison values from other scenarios.
AMRAT_2025_010D = 0.0029  # m^2/kg, Falcon 9 stage (2025-010D scenario)
A1_2020_CD3 = 1.357e-10  # au/d^2, SBDB, natural analogue (2020 CD3 scenario)
# The observations are queried live from the MPC and filtered to this arc: the one
# JPL's solution of 2026-11-08 used, so later observations do not move the numbers.
LAST_NIGHT = "2026-11-07T23:59"  # UTC


def iso_tdb(mjd_tdb: float) -> str:
    # The calendar date of a TDB MJD: label the number as UTC so that no
    # time-scale offset is applied when it is written as a date.
    return Epochs.from_mjd([mjd_tdb], scale=TimeScale.UTC.value).to_iso()[0][:16]


def iso_utc(mjd_tdb: float) -> str:
    epoch = Epochs.from_mjd([mjd_tdb], scale=TimeScale.TDB.value)
    return epoch.to_utc().to_iso()[0][:16]


def tdb_mjd_of_utc_iso(iso: str) -> float:
    epoch = Epochs.from_iso([iso], scale=TimeScale.UTC.value).to_tdb()
    return float(epoch.mjd.to_numpy()[0])


def geocentric(states):
    g = transform_orbits(
        states, CartesianOrbits, frame=Frame.ECLIPTICJ2000, origin=Origin.EARTH
    ).coordinates
    pos = np.array([getattr(g, c).to_numpy(zero_copy_only=False) for c in "xyz"])
    vel = np.array(
        [getattr(g, c).to_numpy(zero_copy_only=False) for c in ("vx", "vy", "vz")]
    )
    mjd = g.epochs.mjd.to_numpy(zero_copy_only=False)
    return mjd, pos * AU_KM, vel * AU_KM / 86400.0


def captured_span(orbit, label):
    grid = Epochs.from_kwargs(
        mjd=[61100.0 + float(i) for i in range(1001)], scale=TimeScale.TDB.value
    )
    prop = empyrean.propagate(
        orbit,
        grid,
        uncertainty_method=UncertaintyMethod.FIRST_ORDER,
        events=EventConfig(close_approaches=True),
    )
    starts = prop.events.capture_starts.epochs.mjd.to_numpy()
    ends = prop.events.capture_ends.epochs.mjd.to_numpy()
    assert len(starts) == 1 and len(ends) == 1, "expected one capture"
    print(
        f"{label}: captured by Earth {iso_tdb(starts[0])} to {iso_tdb(ends[0])} "
        f"TDB ({ends[0] - starts[0]:.0f} days)"
    )
    return prop, float(starts[0]), float(ends[0])


def main():
    empyrean.initialize()

    # -- 1. The observations and a state-only fit ----------------------
    obs = empyrean.query_observations(["2026 QQ8"])
    # Keep the observations through LAST_NIGHT (UTC): the arc the numbers use.
    obs = obs.apply_mask([t <= LAST_NIGHT for t in obs.obs_time.to_pylist()])
    ot = sorted(obs.obs_time.to_pylist())
    nights = sorted({t[:10] for t in ot})
    early = sum(1 for t in ot if t[:10] <= nights[4])
    first_obs, last_obs = tdb_mjd_of_utc_iso(ot[0]), tdb_mjd_of_utc_iso(ot[-1])
    print(
        f"{len(obs)} observations from {len(set(obs.stn.to_pylist()))} stations "
        f"over {obs.time_span_days:.1f} days"
    )
    print(
        f"{len(nights)} nights, {nights[0]} to {nights[-1]}; {early} observations "
        f"in the first five nights, first station {obs.stn.to_pylist()[0]}"
    )
    config = ODConfig(solve_for=SolveForParams.STATE_ONLY)
    weighting = config.weighting
    print(
        f"Weighting: the engine default, preset {weighting.preset.name} (station "
        f"floors) with nightly de-weighting within "
        f"{weighting.additional_layers[0].max_gap_days:.1f} d"
    )
    base = empyrean.determine(obs, config=config).single()
    s0 = base.summary
    chi2_0 = s0.reduced_chi2 * (2 * s0.num_selected - 6)
    print(
        f"State-only fit: chi2/dof {s0.reduced_chi2:.3f}  "
        f'RMS RA.cos(d) {s0.rms_ra_arcsec:.3f}" Dec {s0.rms_dec_arcsec:.3f}"  '
        f"({s0.num_selected}/{s0.num_obs} obs)"
    )
    print(
        "Per station (observations, of which with a stated sigma, median stated "
        "sigma, median sigma the fit applies, median |RA residual|, arcsec):"
    )
    res = base.observations
    codes = res.obs_code.to_pylist()
    applied = np.sqrt(res.residual_cov_ra.to_numpy(zero_copy_only=False))
    resid = np.abs(res.ra_residual.to_numpy(zero_copy_only=False))
    stated = obs.rms_ra.to_numpy(zero_copy_only=False)
    stations = obs.stn.to_pylist()
    for code in sorted(set(stations), key=lambda c: (-stations.count(c), c)):
        a_i = [i for i, c in enumerate(codes) if c == code]
        s_i = [i for i, c in enumerate(stations) if c == code]
        given = stated[s_i][np.isfinite(stated[s_i])]
        stated_text = f"{np.median(given):.3f}" if len(given) else "none"
        print(
            f"  {code}: {len(a_i):2d} obs, {len(given):2d} stated, stated "
            f"{stated_text:>5s}, applied {np.median(applied[a_i]):.3f}, "
            f"|residual| {np.median(resid[a_i]):.3f}"
        )

    # -- 2. Fit the radiation-pressure term with the state -------------
    var = np.zeros((7, 7))
    var[:6, :6] = np.diag(np.square(STATE_SIGMA))
    var[6, 6] = AMRAT_SIGMA**2
    tri = [var[i, j] for i in range(7) for j in range(i + 1)]
    prior = PackedJoint(
        layout_present=1 << 4,  # the AMRAT axis
        layout_considered=0,
        layout_marginalized=0,
        width=7,
        tri=np.asarray(tri, dtype=np.float64),
        kind=CovarianceKind.LINEAR,
        quality=JointQuality.POSITIVE_DEFINITE,
        cov_rank=0,
        cov_null_axes=0,
        cov_min_eig_corr=float("nan"),
        functional=JointFunctional.STATE,
        provenance=JointProvenance.DERIVED,
        asserted_source=None,
    )
    primed = CartesianOrbits.from_kwargs(
        orbit_id=base.orbit.orbit_id.to_pylist(),
        object_id=base.orbit.object_id.to_pylist(),
        coordinates=base.orbit.coordinates,
        srp=SRPParams.from_kwargs(amrat=[AMRAT_SEED], cr=[1.0]),
        covariance=PackedJoints.from_joints([prior]),
    )
    fit = empyrean.refine(
        primed, obs, config=ODConfig(solve_for_flags=SolveFor(amrat="solved"))
    )
    sc = fit.solved_covariance
    amrat = float(fit.orbit.srp.amrat.to_numpy(zero_copy_only=False)[0])
    sigma = float(np.sqrt(sc.matrix[sc.amrat_slot, sc.amrat_slot]))
    s = fit.summary
    chi2_1 = s.reduced_chi2 * (2 * s.num_selected - 7)
    print(
        f"\nFit with the area-to-mass ratio: converged {fit.converged}  "
        f"chi2/dof {s.reduced_chi2:.3f}  "
        f'RMS RA.cos(d) {s.rms_ra_arcsec:.3f}" Dec {s.rms_dec_arcsec:.3f}"  '
        f"({s.num_selected}/{s.num_obs} obs)"
    )
    print(
        f"Prior on the ratio: {AMRAT_SEED:.0e} +/- {AMRAT_SIGMA:.0e} m^2/kg; the fit keeps "
        f"{100 * (sigma / AMRAT_SIGMA) ** 2:.2f}% of that prior's information"
    )
    print(
        f"Area-to-mass ratio = {amrat:.3e} +/- {sigma:.3e} m^2/kg "
        f"({amrat / sigma:.1f} sigma); chi2 falls by {chi2_0 - chi2_1:.1f} "
        "for one parameter"
    )
    print(
        f"  scaled by the residuals (x sqrt(chi2/dof)): "
        f"+/- {sigma * np.sqrt(s.reduced_chi2):.3e} m^2/kg"
    )
    a1, a1_sigma = amrat * K_SRP, sigma * K_SRP
    print(
        f"A1 equivalent = {a1:.3e} +/- {a1_sigma:.2e} au/d^2, the same force as "
        f"JPL's A1 under the r^-2 law (K = {K_SRP:.5e} au/d^2 per m^2/kg)"
    )
    gap = (a1 - JPL_A1) / np.hypot(a1_sigma, JPL_A1_SIGMA)
    print(
        f"JPL A1        = {JPL_A1:.3e} +/- {JPL_A1_SIGMA:.2e} au/d^2 "
        f"(SBDB solution 2026-11-08); difference {gap:+.2f} combined sigma"
    )

    # -- 3. What the ratio could mean -----------------------------------
    print(
        f"\nFor H = {JPL_H:.3f} +/- {JPL_H_SIGMA:.3f}, a sphere of albedo p has "
        "diameter 1329 km / sqrt(p) x 10^(-H/5). With area-to-mass = 1.5 / "
        "(rho D) and the ratio absorbing Cr, these densities are lower bounds:"
    )
    for albedo in (0.05, 0.15, 0.40):
        diameter = 1329e3 / np.sqrt(albedo) * 10.0 ** (-JPL_H / 5.0)  # m
        density = 1.5 / (amrat * diameter)
        rel = np.hypot(sigma / amrat, np.log(10.0) / 5.0 * JPL_H_SIGMA)
        print(
            f"  albedo {albedo:.2f}: {diameter:4.1f} m, bulk density "
            f"{density:5.0f} +/- {density * rel:4.0f} kg/m^3"
        )
    print(
        f"Natural analogue 2020 CD3: A1 {A1_2020_CD3:.3e} au/d^2 = "
        f"{A1_2020_CD3 / K_SRP:.2e} m^2/kg; the Falcon 9 stage 2025-010D: "
        f"{AMRAT_2025_010D:.1e} m^2/kg"
    )

    # -- 4. Was it a mini-moon? -----------------------------------------
    # The engine's capture test is the standard one: negative geocentric
    # energy within three Hill radii. A temporarily captured orbiter, as
    # opposed to a captured flyby, makes at least one full revolution of Earth
    # in the Sun-Earth rotating frame (Fedorets et al. 2017).
    prop, start, end = captured_span(fit.orbit, "Fit with the ratio")
    captured_span(base.orbit, "State-only (A1 = 0)")
    days = Epochs.from_kwargs(
        mjd=[start + float(i) for i in range(int(end - start) + 1)],
        scale=TimeScale.TDB.value,
    )
    track = empyrean.propagate(fit.orbit, days)
    _, pos, _ = geocentric(track.states)
    sun = empyrean.get_states(
        target=Origin.SUN, center=Origin.EARTH, epochs=days, frame=Frame.ECLIPTICJ2000
    )
    sun_x = sun.x.to_numpy(zero_copy_only=False)
    sun_y = sun.y.to_numpy(zero_copy_only=False)
    angle = np.unwrap(np.arctan2(pos[1], pos[0]) - np.arctan2(sun_y, sun_x))
    turns = abs(angle[-1] - angle[0]) / (2.0 * np.pi)
    r_km = np.linalg.norm(pos, axis=0)
    print(
        f"Geocentric distance while captured: {r_km.min():,.0f} to "
        f"{r_km.max():,.0f} km (at most {r_km.max() / HILL_RADIUS_KM:.2f} Hill "
        f"radii of {HILL_RADIUS_KM:,.0f} km, Earth alone at 1 au; the capture "
        "test allows 3)"
    )
    print(
        f"Revolutions of Earth in the Sun-Earth rotating frame: {turns:.2f}; "
        f"complete revolutions N = {int(turns)}"
    )
    # Closest approach: the engine suppresses Earth close-approach events while
    # the object is captured by Earth, so take the minimum of a fine sampling,
    # refined by a parabola through its lowest three points.
    fine = Epochs.from_kwargs(
        mjd=[61270.9 + 0.001 * i for i in range(201)], scale=TimeScale.TDB.value
    )
    tf, pf, vf = geocentric(empyrean.propagate(fit.orbit, fine).states)
    rf = np.linalg.norm(pf, axis=0)
    k = int(np.clip(rf.argmin(), 1, len(rf) - 2))
    c2, c1, c0 = np.polyfit(tf[k - 1 : k + 2] - tf[k], rf[k - 1 : k + 2], 2)
    t_ca = tf[k] - c1 / (2 * c2)
    r_ca = c0 - c1**2 / (4 * c2)
    v_ca = float(np.linalg.norm(vf[:, k]))
    print(
        f"Closest approach: {iso_tdb(t_ca)} TDB ({iso_utc(t_ca)} UTC) at "
        f"{r_ca:,.0f} km ({r_ca / LUNAR_DISTANCE_KM:.2f} lunar distances), "
        f"speed {v_ca:.2f} km/s, energy {v_ca**2 / 2 - MU_EARTH / r_ca:+.3f} km^2/s^2"
    )

    # -- 5. How the uncertainty grows ---------------------------------------
    grid_t, _, _ = geocentric(prop.states)
    blocks = [
        np.asarray(prop.states.covariance.joint(i).state_block())
        for i in range(len(prop.states))
    ]
    sig_km = np.array([np.sqrt(np.trace(b[:3, :3])) * AU_KM for b in blocks])
    print("\n1-sigma position uncertainty (daily samples, interpolated, first order):")
    after = 61700.0
    for label, mjd in [
        ("capture start", start),
        ("first observation", first_obs),
        ("closest approach", t_ca),
        ("last observation", last_obs),
        ("capture end", end),
        (f"{after - end:.0f} days after capture end", after),
    ]:
        sig = np.interp(mjd, grid_t, sig_km)
        print(f"  {label:28s} {iso_tdb(mjd)} TDB  {sig:8.1f} km")

    # -- 6. Where it goes next (first-order covariance on the long run) -----
    long_grid = Epochs.from_kwargs(
        mjd=[34000.0 + float(i) for i in range(50501)],  # 1952 to 2090
        scale=TimeScale.TDB.value,
    )
    path = empyrean.propagate(
        fit.orbit, long_grid, uncertainty_method=UncertaintyMethod.FIRST_ORDER
    )
    tl, pl, vl = geocentric(path.states)
    rl = np.linalg.norm(pl, axis=0)
    print(
        "\nEarth passes closer than 0.05 au (daily-sampled minima, nominal path), "
        "timing sigma along the path:"
    )
    for i in range(1, len(tl) - 1):
        if rl[i] < rl[i - 1] and rl[i] <= rl[i + 1] and rl[i] < 0.05 * AU_KM:
            along = vl[:, i] / np.linalg.norm(vl[:, i])
            block = np.asarray(path.states.covariance.joint(i).state_block())
            cov = block[:3, :3] * AU_KM**2
            sigma_t_s = np.sqrt(along @ cov @ along) / np.linalg.norm(vl[:, i])
            print(
                f"  {iso_tdb(tl[i])[:10]} TDB  {rl[i] / AU_KM:.4f} au  "
                f"+/- {sigma_t_s / 60.0:9.2f} min"
            )
    return obs


obs = main()
# empyrean:snippet:end

# Drift check, outside the snippet: the published numbers are for exactly these
# observations. If the MPC re-measures, deletes or adds a row below the filter,
# stop instead of printing numbers for a different arc.
EXPECTED_COUNT = 39
EXPECTED_SHA256 = "24cfe8507e47ed60a0201aaea29ba57bea9a77a5abf7855c5e08439320e550eb"
found_ids = "\n".join(sorted(obs.obs_id.to_pylist()))
found_sha256 = hashlib.sha256(found_ids.encode()).hexdigest()
if len(obs) != EXPECTED_COUNT or found_sha256 != EXPECTED_SHA256:
    sys.exit(
        f"The MPC record changed below the filter: expected {EXPECTED_COUNT} "
        f"observations with sha256 {EXPECTED_SHA256} of the sorted obsIDs, found "
        f"{len(obs)} with {found_sha256}. The numbers above are for a different arc."
    )
