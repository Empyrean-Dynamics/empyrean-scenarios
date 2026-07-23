"""2008 TC3: 19-hour discovery arc → predicted Earth impact → meteorites.

Reproduces the 2008tc3 explore-mode scenario from
https://empyrean-dynamics.com/explore/2008tc3.

Run:
    pip install empyrean
    python 2008_TC3/main.py

What it does:
    1. Pulls all 883 MPC astrometric observations of 2008 TC3 from the
       19-hour discovery arc (Catalina + 27 follow-up stations).
    2. Runs `empyrean.determine` to fit the orbit live.
    3. Propagates the determined orbit forward through the predicted
       atmospheric entry on 2008-10-07.
    4. Reports the predicted atmospheric-entry epoch + velocity and compares
       to the actual recovered-meteorites entry of 02:45:40 UT.

Authoritative cross-checks (printed inline):
    - Actual atmospheric entry: 2008-10-07 02:45:40 UT (Borovička 2010)
    - Energy: ~1 kt TNT-equivalent                     (Borovička 2010)
    - Observed entry: over ~20.7° N, 32.1° E (Nubian Desert)
    - 600+ meteorite fragments recovered (ureilite class)
"""

from __future__ import annotations

# empyrean:snippet:start
import empyrean
from empyrean import Epochs, ODConfig, PhotometryConfig, TimeScale, UncertaintyMethod


def main() -> None:
    empyrean.initialize()

    # ── 1. Astrometric observations from MPC ────────────────────────
    obs = empyrean.query_observations(["2008 TC3"])
    print(f"{len(obs)} observations spanning the discovery arc")

    # ── 2. Full pipeline OD, with a post-OD photometric fit ─────────
    # IOD (Gauss + Herget on triplets), 6-param state DC, optional
    # auto-escalation to 9-param if non-grav residuals are non-trivial,
    # outlier rejection. `photometry` adds the v0.9.0 H/G fit over the
    # observations' magnitudes once the orbit is solved.
    result = empyrean.determine(obs, config=ODConfig(photometry=PhotometryConfig()))
    s = result.summary
    print(
        f"chi2/dof:    {s.reduced_chi2:.3f}  "
        f"({s.num_selected}/{s.num_obs} obs selected)"
    )
    print(f'RMS:         RA·cos(d) {s.rms_ra_arcsec:.3f}"  Dec {s.rms_dec_arcsec:.3f}"')

    # ── 2b. Absolute magnitude from the discovery-arc photometry ────
    # The same observations carry V-band magnitudes; the post-OD H/G
    # fit recovers the absolute magnitude H with an honest 1-sigma from
    # its 3x3 parameter covariance. Over a 19-hour arc the phase-angle
    # coverage is thin, so the model ladder settles on HG12 (one shape
    # parameter) rather than the full three-parameter HG1G2.
    ph = result.photometry
    if ph is not None:
        h_sigma = (
            float(ph.covariance[0, 0] ** 0.5)
            if ph.covariance is not None
            else float("nan")
        )
        print(
            f"Photometry:  H = {ph.h:.2f} +/- {h_sigma:.2f}  "
            f"(model {ph.model_used}, chi2_r {ph.reduced_chi2:.2f}, "
            f"{ph.n_mags_used} mags)"
        )
        print("Reference (JPL SBDB): H = 30.9  (a ~4 m ureilite)")

    # ── 3. Propagate forward through atmospheric entry ──────────────
    # IAS15 step size auto-bottoms out as Earth's gravity tightens; the
    # event detector picks up the entry as an Impact event.
    epochs = Epochs.from_kwargs(
        mjd=[54745.7 + 0.005 * i for i in range(170)],
        scale=TimeScale.TDB.value,
    )
    prop = empyrean.propagate(
        result.orbit,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
    )

    # ── 4. Predicted entry — atmospheric_entry is the ~100 km
    # Karman-line crossing, the apples-to-apples comparator for the
    # Borovička+ 2010 fireball coordinates (the surface-impact event
    # lands ~150 km downrange because the fireball exploded at ~37 km
    # altitude). ────────────────────────────────────────────────────
    print("\nPredicted atmospheric entry (Empyrean):")
    ae = prop.events.atmospheric_entries
    au_per_day_to_km_per_s = 149_597_870.7 / 86_400.0
    for i in range(len(ae)):
        epoch = ae.epoch.to_numpy(zero_copy_only=False)[i]
        v_rel = ae.relative_velocity_au_day.to_numpy(zero_copy_only=False)[i]
        alt = ae.altitude_km.to_numpy(zero_copy_only=False)[i]
        print(
            f"  MJD {epoch:.5f}  v_rel = {v_rel * au_per_day_to_km_per_s:.2f} km/s  "
            f"alt = {alt:.0f} km"
        )
    print("Reference (Borovička+ 2010):")
    print(
        "  MJD 54746.115 (2008-10-07 02:45:40 UT) over 20.74°N 32.16°E  v = 12.4 km/s"
    )


# empyrean:snippet:end


if __name__ == "__main__":
    main()
