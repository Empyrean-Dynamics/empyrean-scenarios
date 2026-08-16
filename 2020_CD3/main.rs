//! 2020 CD3: Earth's second known mini-moon — multi-year capture episode.
//!
//! Rust twin of `2020_CD3/main.py`. Reproduces the 2020cd3 explore-mode scenario
//! from <https://empyrean-dynamics.com/explore/2020cd3>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin cd3
//! ```

// empyrean:snippet:start
use empyrean::{
    Context, Epoch, EventConfig, Origin, PropagationConfig, UncertaintyMethod, query_sbdb,
};

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. SBDB query ──────────────────────────────────────────────
    let batch = query_sbdb(&["2020 CD3"], None)?;
    let orbit = batch
        .orbits
        .into_iter()
        .next()
        .expect("SBDB returned no orbit for 2020 CD3");
    // 0.10.0rc workaround (rc1 rebuilds the same engine, so it still applies): the Rust wrapper's query_sbdb populates the
    // state<->non-grav cross-covariance without the 3x3 it conditions
    // on, and the engine (correctly) refuses the half-attached joint.
    // Clear the cross terms — this scenario reads nominal-trajectory
    // numbers only. Remove once the wrapper attaches the full block.
    let mut orbit = orbit;
    orbit.state.non_grav_cross = None;
    println!(
        "Object: {}",
        orbit.object_id.as_deref().unwrap_or("(2020 CD3)")
    );
    println!("Epoch MJD TDB: {:.1}", orbit.state.epoch.mjd());
    println!(
        "non-grav coefficients (SBDB):  A1 = {:.3e}  A2 = {:.3e}  A3 = {:.3e} AU/d^2",
        orbit.a1, orbit.a2, orbit.a3
    );

    // ── 2. Propagate through the capture episode ────────────────────
    // 1-day cadence covers the full ~19-year span. The propagator
    // inserts fine encounter samples around each capture pass
    // automatically via dense-output triggers.
    let epochs: Vec<Epoch> = (0..7001)
        .map(|i| Epoch::from_mjd_tdb(52000.0 + 1.0 * i as f64))
        .collect();
    // FirstOrder is fast enough for this scenario — the headline
    // numbers (capture starts/ends, periapsis distances) are
    // covariance-free.
    let prop_config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::FirstOrder,
        events: EventConfig {
            close_approaches: true,
            ..Default::default()
        },
        ..Default::default()
    };

    let grav_only = orbit.clone().with_nongrav(0.0, 0.0, 0.0);
    let prop = ctx.propagate(&[orbit], &epochs, &prop_config)?;
    let prop_grav_only = ctx.propagate(&[grav_only], &epochs, &prop_config)?;

    // ── 3. Capture episodes + close approaches ──────────────────────
    // Capture is the energy-criterion event (two-body specific energy
    // crossing zero relative to Earth) — emitted as `capture_start` /
    // `capture_end`. SOI crossings (`soi_entry` / `soi_exit`) are a
    // different concept: they fire when the integrator switches
    // central body via the Laplace-SOI dominance test.
    let summarize = |label: &str, events: &[empyrean::Event]| -> empyrean::Result<()> {
        let captures: Vec<_> = events
            .iter()
            .filter(|e| matches!(e.event_type.as_str(), "capture_start" | "capture_end"))
            .filter(|e| e.body == Some(Origin::Earth))
            .collect();
        let starts: Vec<_> = captures
            .iter()
            .filter(|e| e.event_type == "capture_start")
            .collect();
        let ends: Vec<_> = captures
            .iter()
            .filter(|e| e.event_type == "capture_end")
            .collect();
        let periapses: Vec<_> = events
            .iter()
            .filter(|e| e.event_type == "periapsis")
            .filter(|e| matches!(e.body, Some(Origin::Earth) | Some(Origin::Moon)))
            .collect();
        let closest = periapses
            .iter()
            .filter(|e| e.body == Some(Origin::Earth))
            .min_by(|a, b| a.distance_km.partial_cmp(&b.distance_km).unwrap());
        println!("\n── {label} ──");
        println!("Capture starts: {}", starts.len());
        println!("Capture ends:   {}", ends.len());
        if let (Some(s), Some(e)) = (starts.first(), ends.first()) {
            let t_start = s.epoch.mjd();
            let t_end = e.epoch.mjd();
            let duration_days = t_end - t_start;
            println!(
                "Capture window: MJD {:.3} → MJD {:.3}  ({:.1} days, {:.2} years)",
                t_start,
                t_end,
                duration_days,
                duration_days / 365.25
            );
        }
        let n_earth = periapses
            .iter()
            .filter(|e| e.body == Some(Origin::Earth))
            .count();
        let n_moon = periapses.len() - n_earth;
        println!(
            "Close-approach periapses: Earth {n_earth}, Moon {n_moon}  \
             (in-capture geocentric passes are orbital structure around \
             the central body, not close approaches — no events emitted)"
        );
        if let Some(ev) = closest {
            println!(
                "Closest Earth CA periapsis: MJD {:.3}  {:>10.0} km",
                ev.epoch.mjd(),
                ev.distance_km
            );
        }
        Ok(())
    };

    summarize("With SBDB non-grav (A1 = 1.357e-10)", &prop.events)?;
    geocentric_minimum(&ctx, &prop)?;
    summarize(
        "Gravity-only control (A1 = A2 = A3 = 0)",
        &prop_grav_only.events,
    )?;
    geocentric_minimum(&ctx, &prop_grav_only)?;

    println!("\nReference: capture period ~2017-2020 (Fedorets+ 2020).");

    Ok(())
}
// empyrean:snippet:end

/// The geocentric minimum through the capture, from the propagated
/// states: the daily samples minus Earth's position at the same epochs.
/// (Coarser than an event — the grid is 1-day — but the honest headline
/// for a body that spends the episode *orbiting* Earth.)
fn geocentric_minimum(
    ctx: &empyrean::Context,
    prop: &empyrean::PropagationResult,
) -> empyrean::Result<()> {
    use empyrean::{Frame, Origin};
    const AU_KM: f64 = 149_597_870.7;
    let epochs: Vec<empyrean::Epoch> = prop.states.iter().map(|s| s.epoch).collect();
    let frame = prop.states.first().map(|s| s.frame).unwrap_or(Frame::ICRF);
    let earth = ctx.get_states(Origin::Earth, Origin::SSB, &epochs, frame)?;
    let mut best: Option<(f64, f64)> = None;
    for (s, e) in prop.states.iter().zip(earth.iter()) {
        let dx = s.position[0] - e.position[0];
        let dy = s.position[1] - e.position[1];
        let dz = s.position[2] - e.position[2];
        let r_km = (dx * dx + dy * dy + dz * dz).sqrt() * AU_KM;
        if best.is_none() || r_km < best.unwrap().1 {
            best = Some((s.epoch.mjd(), r_km));
        }
    }
    if let Some((mjd, r)) = best {
        println!("Closest geocentric distance (daily-sampled states): MJD {mjd:.3}  {r:>10.0} km");
    }
    Ok(())
}
