//! 67P/Churyumov-Gerasimenko: cometary non-gravitational acceleration.
//!
//! Rust twin of `67P_Churyumov-Gerasimenko/main.py`. Reproduces the 67p explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/67p>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin comet67p
//! ```

// spielberg:snippet:start
use empyrean::{Context, Epoch, PropagationConfig, UncertaintyMethod, query_sbdb};

const KM_PER_AU: f64 = 149_597_870.7;

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. SBDB query — non-grav coefficients included ──────────────
    let batch = query_sbdb(&["67P"], None)?;
    let orbit = batch
        .orbits
        .into_iter()
        .next()
        .expect("SBDB returned no orbit for 67P");
    println!("non-grav coefficients (SBDB):");
    println!("  A1 = {:.3e} AU/d^2", orbit.a1);
    println!("  A2 = {:.3e} AU/d^2", orbit.a2);
    println!("  A3 = {:.3e} AU/d^2", orbit.a3);

    // ── 2. Propagate 16 years at 10-day cadence from the orbit epoch ─
    // Anchor the grid to the orbit's own epoch (as the Python twin does)
    // so both reproduce the same 16-year window from the SBDB solution.
    let base = orbit.state.epoch.mjd();
    let epochs: Vec<Epoch> = (0..601)
        .map(|i| Epoch::from_mjd_tdb(base + 10.0 * i as f64))
        .collect();
    let prop_config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::SecondOrder,
        ..Default::default()
    };

    let full = ctx.propagate(std::slice::from_ref(&orbit), &epochs, &prop_config)?;

    // ── 3. Control run — drop non-grav, propagate again ─────────────
    let grav_only = orbit.with_nongrav(0.0, 0.0, 0.0);
    let control = ctx.propagate(&[grav_only], &epochs, &prop_config)?;

    // ── 4. Cumulative position separation ───────────────────────────
    let mut max_delta_au: f64 = 0.0;
    for (a, b) in full.states.iter().zip(control.states.iter()) {
        let dx = a.position[0] - b.position[0];
        let dy = a.position[1] - b.position[1];
        let dz = a.position[2] - b.position[2];
        let d = (dx * dx + dy * dy + dz * dz).sqrt();
        if d > max_delta_au {
            max_delta_au = d;
        }
    }
    let max_delta_km = max_delta_au * KM_PER_AU;
    println!(
        "\nMax separation (non-grav vs gravity-only) over 16 years: {:.0} km",
        max_delta_km
    );
    println!(
        "(That's the cumulative effect of outgassing — what every cometary ephemeris pipeline has to model.)"
    );

    Ok(())
}
// spielberg:snippet:end
