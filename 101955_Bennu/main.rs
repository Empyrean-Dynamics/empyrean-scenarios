//! Bennu: textbook transverse non-grav A2 (≈ Yarkovsky) detection + 2060 encounter.
//!
//! Rust twin of `101955_Bennu/main.py`. Reproduces the bennu explore-mode scenario
//! from <https://empyrean-dynamics.com/explore/bennu>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin bennu
//! ```
//!
//! Authoritative cross-checks (printed inline):
//!   - 2060-09-23, geocentric ~750,000 km                (JPL CAD)
//!   - A2 = -4.62e-14 AU/d² (~284 m/orbit)               (Farnocchia 2021)

// spielberg:snippet:start
use empyrean::{
    Context, Epoch, EventConfig, Origin, PropagationConfig, UncertaintyMethod, query_sbdb,
};

/// Published Bennu transverse non-grav A2 from Farnocchia et al. 2021
/// (interpreted as Yarkovsky thermal recoil from OREx-measured spin
/// and thermal inertia). SBDB ships this in its non-grav block; if
/// absent locally we patch it in.
const BENNU_A2: f64 = -4.6178e-14; // AU/d², Marsden transverse coefficient

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. Query SBDB for Bennu ─────────────────────────────────────
    let batch = query_sbdb(&["101955"], None)?;
    let mut orbit = batch
        .orbits
        .into_iter()
        .next()
        .expect("SBDB returned no orbit for 101955");
    println!("Object: {}", orbit.object_id.as_deref().unwrap_or("101955"));
    println!("Epoch MJD TDB: {:.1}", orbit.state.epoch.mjd());

    // ── 2. Patch in the published Marsden A2 if SBDB didn't ship it ─
    if orbit.a2.abs() < 1e-20 {
        orbit = orbit.with_nongrav(0.0, BENNU_A2, 0.0);
    }
    println!("Marsden A2 (≈ Yarkovsky): {:.3e} AU/d^2", orbit.a2);
    println!("Reference                 -4.6178e-14    (Farnocchia 2021)");

    // ── 3. Propagate 125 years at 5-day cadence ─────────────────────
    let epochs: Vec<Epoch> = (0..5289)
        .map(|i| Epoch::from_mjd_tdb(55562.0 + 5.0 * i as f64))
        .collect();
    // FirstOrder is sufficient for the long propagation — the
    // headline numbers (CA distance, B-plane geometry, 3σ semi-major)
    // are linear-covariance quantities. SecondOrder would only buy
    // Edgeworth IP corrections, which the bennu scenario doesn't
    // exercise.
    let prop_config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::FirstOrder,
        events: EventConfig {
            close_approaches: true,
            ..Default::default()
        },
        ..Default::default()
    };

    let prop = ctx.propagate(&[orbit.clone()], &epochs, &prop_config)?;

    // ── 4. Close approaches ─────────────────────────────────────────
    println!("\nClose approaches (Empyrean):");
    for ev in prop.events.iter().filter(|e| e.event_type == "periapsis") {
        let body = ev
            .body
            .map(|b| format!("{b:?}"))
            .unwrap_or_else(|| "—".into());
        println!(
            "  {:6}  MJD {:.3}  {:>12.0} km",
            body,
            ev.epoch.mjd(),
            ev.distance_km
        );
    }
    println!("Reference (JPL CAD nominal):");
    println!("  Earth   MJD 73725 (2060-09-23)   ~750,000 km");

    // ── 5. B-plane geometry at each Earth encounter ─────────────────
    let b_planes = ctx.compute_b_planes(
        &[orbit],
        *epochs.last().unwrap(),
        &[UncertaintyMethod::SecondOrder],
        &[Origin::Earth],
    )?;
    println!("\nEarth B-plane geometry (Empyrean):");
    let earth_sm: Vec<f64> = b_planes
        .iter()
        .filter(|b| b.body == Origin::Earth)
        .map(|bp| {
            println!(
                "  MJD {:.3}  |B| = {:>10.0} km  3-sigma semi-major = {:>8.1} km",
                bp.epoch.mjd(),
                bp.b_mag_km,
                bp.semi_major_3sig_km
            );
            bp.semi_major_3sig_km
        })
        .collect();
    if earth_sm.len() >= 2 {
        println!(
            "(2060 B-plane uncertainty input to any downstream resonant-return analysis; \
             {:.0}x covariance amplification at 2080.)",
            earth_sm[1] / earth_sm[0]
        );
    }

    Ok(())
}
// spielberg:snippet:end
