//! Generate ephemeris: RA/Dec + photometry for an MPC site.
//!
//! Reproducer for the "Generate Ephemeris" section of
//! <https://empyrean-dynamics.com/install>. The fragment shown in the
//! install page assumes the `orbit` and `ctx` bindings are already in
//! scope; this harness queries SBDB first so the file is runnable
//! end-to-end.

use empyrean::{Context, query_sbdb};

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;
    let batch = query_sbdb(&["Apophis"], None)?;
    let orbit = batch.orbits.into_iter().next().expect("not found");

    // spielberg:snippet:start
    use empyrean::{EphemerisConfig, Epoch};

    let observers = ctx.get_observers(
        &["W84", "F51"],
        &[Epoch::from_mjd_tdb(60200.0), Epoch::from_mjd_tdb(60201.0)],
    )?;

    let eph = ctx.generate_ephemeris(&[orbit], &observers, &EphemerisConfig::default())?;

    for row in eph.iter() {
        println!(
            "RA = {:.6}\u{00B0}  Dec = {:.6}\u{00B0}  range = {:.6} AU",
            row.ra_deg, row.dec_deg, row.rho_au
        );
    }

    // Photometry — V-band magnitude with 1-sigma uncertainty
    for row in eph.iter() {
        let (m, s) = (row.mag, row.mag_sigma);
        println!("V = {m:.2} \u{00B1} {s:.2}");
    }
    // spielberg:snippet:end
    Ok(())
}
