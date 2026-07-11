//! Query JPL: SBDB elements, Horizons reference, MPC astrometry.
//!
//! Reproducer for the "Query JPL" section of
//! <https://empyrean-dynamics.com/install>.

use empyrean::Context;

fn main() -> empyrean::Result<()> {
    let _ctx = Context::from_data_dir(None)?;

    // empyrean:snippet:start
    use empyrean::{query_horizons, query_observations, query_sbdb};

    // SBDB: elements + covariance + non-grav + photometry
    let batch = query_sbdb(&["Apophis", "Eros"], None)?;

    // Horizons: reference ephemeris for validation (epochs in MJD TDB)
    let eph_ref = query_horizons(&["Apophis"], "W84", &[60200.0], None)?;

    // MPC: astrometric observations in ADES
    let obs = query_observations(&["Apophis"], None)?;
    // empyrean:snippet:end

    println!("SBDB:      {} orbits", batch.orbits.len());
    println!("Horizons:  {} ephemeris rows", eph_ref.len());
    println!("MPC:       {} observations", obs.len());
    Ok(())
}
