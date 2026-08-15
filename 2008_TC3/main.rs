//! 2008 TC3: 19-hour discovery arc → predicted Earth impact → meteorites.
//!
//! Rust twin of `2008_TC3/main.py`. Reproduces the 2008tc3 explore-mode scenario
//! from <https://empyrean-dynamics.com/explore/2008tc3>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin tc3
//! ```

// empyrean:snippet:start
use empyrean::{
    Context, Epoch, EventConfig, ODConfig, PropagationConfig, UncertaintyMethod, query_observations,
};

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. Astrometric observations from MPC ────────────────────────
    let observations = query_observations(&["2008 TC3"], None)?;
    println!(
        "{} observations spanning the discovery arc",
        observations.len()
    );

    // ── 2. Full pipeline OD ─────────────────────────────────────────
    let result = ctx
        .determine(&observations, None, &ODConfig::default())?
        .into_single()?;
    let s = &result.summary;
    println!(
        "chi2/dof:    {:.3}  ({}/{} obs selected)",
        s.reduced_chi2, s.num_selected, s.num_obs
    );
    println!(
        "RMS:         RA·cos(d) {:.3}\"  Dec {:.3}\"",
        s.rms_ra_arcsec, s.rms_dec_arcsec
    );

    // The fitted orbit is already re-feedable (state + covariance); just
    // tag it and re-propagate.
    let orbit = result.orbit.clone().with_orbit_id("2008 TC3");

    // ── 3. Propagate forward through atmospheric entry ──────────────
    let epochs: Vec<Epoch> = (0..170)
        .map(|i| Epoch::from_mjd_tdb(54745.7 + 0.005 * i as f64))
        .collect();
    let prop_config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::SecondOrder,
        events: EventConfig {
            impacts: true,
            atmospheric: true,
            ..Default::default()
        },
        ..Default::default()
    };

    let prop = ctx.propagate(&[orbit], &epochs, &prop_config)?;

    // ── 4. Predicted entry — atmospheric_entry is the ~100 km Karman-
    //       line crossing, the apples-to-apples comparator for the
    //       Borovička+ 2010 fireball timing (the surface-impact event
    //       lands ~150 km downrange because the fireball exploded at
    //       ~37 km altitude). ─────────────────────────────────────────
    println!("\nPredicted atmospheric entry (Empyrean):");
    for ev in prop
        .events
        .iter()
        .filter(|e| e.event_type == "atmospheric_entry")
    {
        // `impact_altitude_km` is the true altitude above the reference
        // ellipsoid from the planetodetic ground track (~100 km Karman
        // line); `distance_km` is the body-CENTER crossing distance.
        println!(
            "  MJD {:.5}  v_rel = {:.2} km/s  alt = {:.0} km",
            ev.epoch.mjd(),
            ev.relative_velocity_au_day * 149_597_870.7 / 86_400.0,
            ev.impact_altitude_km,
        );
        // The entry event carries its planetodetic ground point — the
        // 19-hour discovery arc pins WHERE over Sudan, not just when.
        println!(
            "  over {:.2}°N {:.2}°E",
            ev.impact_latitude_deg, ev.impact_longitude_deg
        );
    }
    println!("Reference (Borovička+ 2010):");
    println!("  MJD 54746.115 (2008-10-07 02:45:40 UT) over 20.74°N 32.16°E  v = 12.4 km/s");

    Ok(())
}
// empyrean:snippet:end
