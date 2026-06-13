//! Propagate an orbit forward with full uncertainty + event detection.
//!
//! Reproducer for the "Propagate an Orbit" section of
//! <https://empyrean-dynamics.com/install>.

fn main() -> empyrean::Result<()> {
    // spielberg:snippet:start
    use empyrean::{
        Context, Epoch, EventConfig, Origin, PropagationConfig, UncertaintyMethod, query_sbdb,
        write_events_parquet,
    };

    // Loads / downloads kernels on first run.
    let ctx = Context::from_data_dir(None)?;

    let batch = query_sbdb(&["Apophis"], None)?;
    let orbit = batch.orbits.into_iter().next().expect("not found");

    let epochs = vec![Epoch::from_mjd_tdb(65000.0)];
    let prop = PropagationConfig {
        uncertainty_method: UncertaintyMethod::SecondOrder,
        events: EventConfig {
            close_approaches: true,
            ..Default::default()
        },
        ..Default::default()
    };

    let result = ctx.propagate(&[orbit], &epochs, &prop)?;

    for ev in result.events.iter() {
        let body = ev
            .body
            .map(|b| format!("{b:?}"))
            .unwrap_or_else(|| "\u{2014}".into());
        println!(
            "{:25}  {:8}  MJD {:.2}",
            ev.event_type,
            body,
            ev.epoch.mjd()
        );
    }

    // Typed event accessors per category
    if let Some(ev) = result
        .events
        .iter()
        .find(|e| e.event_type == "periapsis" && e.body == Some(Origin::Earth))
    {
        println!("Earth CA: {:.0} km", ev.distance_km);
    }

    // Save the detected events to a Parquet file
    write_events_parquet("apophis_2029_events.parquet", &result.events)?;
    // spielberg:snippet:end
    Ok(())
}
