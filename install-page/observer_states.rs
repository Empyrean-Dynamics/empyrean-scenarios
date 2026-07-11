//! Observer states: ground-based MPC observatories by code.
//!
//! Reproducer for the "Observer States" section of
//! <https://empyrean-dynamics.com/install>.

fn main() -> empyrean::Result<()> {
    use empyrean::Context;
    let ctx = Context::from_data_dir(None)?;

    // empyrean:snippet:start
    use empyrean::Epoch;

    let observers = ctx.get_observers(
        &["W84", "F51"],
        &[Epoch::from_mjd_tdb(60200.0), Epoch::from_mjd_tdb(60201.0)],
    )?;
    // 4 rows: cross product of codes x epochs, ICRF/SSB positions + velocities
    // empyrean:snippet:end
    println!("observers: {} rows", observers.len());
    Ok(())
}
