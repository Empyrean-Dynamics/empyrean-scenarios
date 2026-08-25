"""Why the optical-only forecast missed by 2 km, and what would fix it.

Re-runs the scenario's final-arc fit with the solar-radiation-pressure
area-to-mass ratio held at a ladder of values, propagates each to the
Moon, and decomposes the miss against the LRO-located crater
(19.4759°N 266.7138°E) into along-track and cross-track components.
The optical arc leaves AMR nearly degenerate with the gravitational
signal (flat chi-square), and the impact site slides cross-track with
it — the axis that radar Doppler pins directly.

    python amr_sensitivity.py
"""

from __future__ import annotations

import math
from pathlib import Path

import empyrean
import numpy as np
from empyrean import (
    CartesianCoordinates,
    CartesianOrbits,
    Epochs,
    ODConfig,
    Origin,
    OriginPolicy,
    OriginPolicyMode,
    SolveFor,
    SRPParams,
    TimeScale,
    WeightingConfig,
    WeightingPreset,
)

HERE = Path(__file__).parent
CRATER = (19.4759, 266.7138)  # NASA LRO, imaged 2026-08-11/12
R_MOON = 1737.4


def main() -> None:
    empyrean.initialize()
    obs, _ = empyrean.read_ades(str(HERE / "astrometry.psv"))
    t = obs.obs_time.to_pylist()
    final_arc = obs.apply_mask(np.array([x >= "2026-07-23" for x in t]))
    od = ODConfig(
        origin=OriginPolicy(mode=OriginPolicyMode.EXPLICIT, origin=Origin.EARTH),
        weighting=WeightingConfig(
            preset=WeightingPreset.NONE, default_sigma_arcsec=0.3
        ),
    )
    fit = empyrean.determine(final_arc, config=od).single()
    end = Epochs.from_kwargs(mjd=[61258.0], scale=TimeScale.TDB.value)

    # Approach heading at the surface, from the nominal solved-AMR orbit.
    nominal = refine_fixed(fit, final_arc, od, 0.0029, solve=True)
    imp = empyrean.propagate(nominal.orbit, end).events.impacts
    t_imp = float(imp.epoch.to_numpy(zero_copy_only=False)[0])
    st = empyrean.propagate(
        nominal.orbit,
        Epochs.from_kwargs(mjd=[t_imp - 1 / 86400], scale=TimeScale.TDB.value),
    ).states.coordinates
    st = empyrean.transform_coordinates(st, CartesianCoordinates, origin=Origin.MOON)
    heading = approach_heading(st)
    print(f"approach heading at impact: {heading:.1f}° (direction of travel)\n")
    print(
        "AMR (m²/kg)  impact site           along-track  cross-track  total   chi²/dof"
    )
    for amr in (0.0029, 0.0040, 0.0050, 0.0060, 0.0079, 0.0100):
        ref = refine_fixed(fit, final_arc, od, amr, solve=False)
        imp = empyrean.propagate(ref.orbit, end).events.impacts
        lat = float(imp.latitude_deg.to_numpy(zero_copy_only=False)[0])
        lon = float(imp.longitude_deg.to_numpy(zero_copy_only=False)[0]) % 360
        along, cross, total = decompose(lat, lon, heading)
        print(
            f"  {amr:.4f}     {lat:.4f}°N {lon:.4f}°E  {along:+6.2f} km   {cross:+6.2f} km"
            f"  {total:5.2f} km  {ref.summary.reduced_chi2:.3f}"
        )
    print(
        "\nEvery +0.001 m²/kg moves the site ~0.8 km cross-track while the fit\n"
        "quality barely changes: the optical arc cannot separate SRP from\n"
        "gravity. JPL #GA1A2/21 (370 measurements to Aug 4, including 3 radar\n"
        "Doppler points) breaks that degeneracy; CNEOS's terrain-aware nominal\n"
        "lands 0.2 km from the crater."
    )


def refine_fixed(fit, arc, od, amr, *, solve):
    srp = SRPParams.from_kwargs(
        amrat=[amr], cr=[1.0], amrat_variance=[1e-4 if solve else 1e-8]
    )
    primed = CartesianOrbits.from_kwargs(
        orbit_id=fit.orbit.orbit_id.to_pylist(),
        object_id=fit.orbit.object_id.to_pylist(),
        coordinates=fit.orbit.coordinates,
        srp=srp,
    )
    cfg = ODConfig(
        solve_for_flags=SolveFor(amrat="solved" if solve else "fixed"),
        origin=od.origin,
        weighting=od.weighting,
    )
    return empyrean.refine(primed, arc, config=cfg)


def approach_heading(st) -> float:
    au = 149597870.7
    r = np.array([st.x[0].as_py(), st.y[0].as_py(), st.z[0].as_py()]) * au
    v = np.array([st.vx[0].as_py(), st.vy[0].as_py(), st.vz[0].as_py()]) * au / 86400.0
    up = r / np.linalg.norm(r)
    if "ecl" in str(st.frame[0]).lower():
        pole = np.array([0.0, 0.0, 1.0])
    else:
        e = math.radians(23.4392911)
        pole = np.array([0.0, -math.sin(e), math.cos(e)])
    north = pole - np.dot(pole, up) * up
    north /= np.linalg.norm(north)
    east = np.cross(up, north)
    vh = v - np.dot(v, up) * up
    return (math.degrees(math.atan2(np.dot(vh, east), np.dot(vh, north))) + 360) % 360


def decompose(lat, lon, heading):
    dn = math.radians(lat - CRATER[0]) * R_MOON
    de = math.radians(lon - CRATER[1]) * R_MOON * math.cos(math.radians(CRATER[0]))
    h = math.radians(heading)
    along = dn * math.cos(h) + de * math.sin(h)
    cross = -dn * math.sin(h) + de * math.cos(h)
    return along, cross, math.hypot(dn, de)


if __name__ == "__main__":
    main()
