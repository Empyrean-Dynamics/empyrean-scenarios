//! Bennu: measuring Yarkovsky drift from optical + radar astrometry + 2060 encounter.
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
//!   - A2 = -4.618e-14 AU/d² (~284 m/orbit)              (Farnocchia 2021)
//!   - 2060-09-23, geocentric ~750,000 km                (JPL CAD)

// empyrean:snippet:start
use empyrean::{
    Context, Epoch, EventConfig, ODConfig, Observations, Origin, PropagationConfig, SolveForParams,
    UncertaintyMethod, query_observations, query_radar,
};

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. Optical astrometry (MPC) + radar astrometry (JPL) ────────
    // Bennu's 29 delay/Doppler measurements from Arecibo and Goldstone
    // (1999, 2005, 2011) pin the line-of-sight distance at the ~100 m
    // level — the ranging record behind the classic Yarkovsky
    // detection (Chesley et al. 2014).
    let optical = query_observations(&["101955"], None)?;
    let radar = query_radar(&["101955"], None)?;
    println!(
        "{} optical + {} radar (delay/Doppler)",
        optical.len(),
        radar.len()
    );

    // ── 2a. Anchor: state fit on the discovery apparition + radar ───
    // A state-only fit over the FULL arc would silently absorb the
    // Yarkovsky drift into the epoch state (aliasing the very signal we
    // want to measure), so the anchor uses only the 1999-2000 discovery
    // apparition — short enough that the drift is negligible — with its
    // radar ranging.
    let short = optical.filter_by_epoch(None, Some(Epoch::from_mjd_tdb(51910.0)))?;
    let radar_short: Vec<_> = radar
        .iter()
        .filter(|r| r.obs_time.starts_with("1999") || r.obs_time.starts_with("2000"))
        .cloned()
        .collect();
    let anchor_obs = Observations::from_arrays(&short.iter().collect::<Vec<_>>(), &radar_short)?;
    let anchor = ctx
        .determine(
            &anchor_obs,
            None,
            &ODConfig {
                solve_for: SolveForParams::StateOnly,
                ..Default::default()
            },
        )?
        .into_single()?;
    println!(
        "Anchor (1999-2000, {} optical + {} radar): chi2/dof {:.2}",
        short.len(),
        radar_short.len(),
        anchor.summary.reduced_chi2
    );

    // ── 2b. Measure: joint state + A2 refine over the full 26-yr arc ─
    // Bennu's arc constrains the TRANSVERSE component only — the A-block
    // is seeded at ZERO and opened by a Bayesian prior that pins A1/A3
    // near zero and leaves A2 wide: the astrometry, not the prior,
    // measures the drift. Zeroed g(r) constants select the exact
    // inverse-square law (the Yarkovsky convention).
    let sigma_tight = 1e-15_f64; // AU/d^2 — A1/A3 pinned ~30x below the A2 signal
    let sigma_wide = 1e-12_f64; // AU/d^2 — A2 unconstrained (~20x above the signal)
    let primed = anchor
        .orbit
        .clone()
        .with_orbit_id("101955")
        .with_nongrav(0.0, 0.0, 0.0)
        .with_nongrav_covariance(Some([
            [sigma_tight * sigma_tight, 0.0, 0.0],
            [0.0, sigma_wide * sigma_wide, 0.0],
            [0.0, 0.0, sigma_tight * sigma_tight],
        ]));
    let full_obs = Observations::from_arrays(&optical.iter().collect::<Vec<_>>(), &[])?;
    let result = ctx.refine(
        &primed,
        &full_obs,
        &ODConfig {
            solve_for: SolveForParams::StateAndNonGrav,
            ..Default::default()
        },
    )?;
    let s = &result.summary;
    println!("Converged:  {}", result.converged);
    println!("chi2/dof:   {:.3}", s.reduced_chi2);
    println!(
        "RMS:        RA·cos(d) {:.3}\"  Dec {:.3}\"",
        s.rms_ra_arcsec, s.rms_dec_arcsec
    );

    // The tagged solved covariance names each fitted parameter's slot —
    // read σ_A2 from the A2 row rather than guessing at column order.
    let a2 = result.orbit.a2;
    match &result.solved_covariance {
        Some(sc) if sc.marsden_slot.is_some() => {
            let row = sc.marsden_slot.unwrap() + 1; // Marsden block is (A1, A2, A3)
            let sigma = sc.matrix[row][row].sqrt();
            println!("Fitted A2 (≈ Yarkovsky) = {a2:.3e} +/- {sigma:.1e} AU/d^2");
        }
        _ => println!("Fitted A2 (≈ Yarkovsky) = {a2:.3e} AU/d^2"),
    }
    println!("Reference                 -4.618e-14 AU/d^2   (Farnocchia 2021,");
    println!("                          radar-complete joint solution)");

    // ── 3. Propagate the fitted orbit ~72 years (2011 → 2083) ───────
    // The orbit carries its fitted covariance and non-grav model, so the
    // 2060/2080 uncertainty story below is traceable to the astrometry.
    let orbit = result.orbit.clone().with_orbit_id("101955");
    let epochs: Vec<Epoch> = (0..5289)
        .map(|i| Epoch::from_mjd_tdb(55562.0 + 5.0 * i as f64))
        .collect();
    let prop_config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::SecondOrder,
        events: EventConfig {
            close_approaches: true,
            ..Default::default()
        },
        ..Default::default()
    };

    let prop = ctx.propagate(std::slice::from_ref(&orbit), &epochs, &prop_config)?;

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
    // Gravitational covariance amplification at close approach made
    // quantitative: the 2060 3σ ellipse — now traceable to the fitted
    // covariance — inflates by orders of magnitude through the flyby.
    // The growth factor is computed live below.
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
             3-sigma ellipse grows {:.0}x by 2080.)",
            earth_sm[1] / earth_sm[0]
        );
    }

    Ok(())
}
// empyrean:snippet:end
