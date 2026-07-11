//! Epochs: explicit time scales, ISO-8601 parsing, evenly spaced grids.
//!
//! Reproducer for the "Epochs" section of
//! <https://empyrean-dynamics.com/install>.

use empyrean::{Context, query_sbdb};

// The snippet below deliberately rebinds `epochs` three times to show
// the construction idioms side by side; the intermediate bindings are
// shadowed rather than consumed.
#[allow(unused_variables)]
fn main() -> empyrean::Result<()> {
    let _ctx = Context::from_data_dir(None)?;
    let batch = query_sbdb(&["Apophis"], None)?;
    let orbit = batch.orbits.into_iter().next().expect("not found");

    // empyrean:snippet:start
    use empyrean::Epoch;

    // Explicit scale at construction
    let epoch_utc = Epoch::from_mjd_utc(60200.0);
    let epoch_tdb = Epoch::from_mjd_tdb(epoch_utc.mjd_tdb()?);

    // Offsets from an orbit epoch
    let t0 = orbit.state.epoch.mjd();
    let epochs: Vec<Epoch> = [30.0, 60.0, 90.0]
        .iter()
        .map(|dt| Epoch::from_mjd_tdb(t0 + dt))
        .collect();

    // Evenly spaced grid
    let epochs: Vec<Epoch> = (0..100)
        .map(|i| Epoch::from_mjd_tdb(60200.0 + 3.65 * i as f64))
        .collect();

    // From an ISO-8601 string (UTC, trailing Z required)
    let epochs = vec![Epoch::from_iso_utc("2029-04-13T21:46:00Z")?];
    // empyrean:snippet:end
    let _ = (epoch_tdb, epochs);
    Ok(())
}
