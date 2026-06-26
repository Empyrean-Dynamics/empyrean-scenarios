//! Apophis end-to-end: 21-year astrometric arc → Marsden A1/A2/A3 fit → 2029 flyby.
//!
//! Rust twin of `99942_Apophis/main.py`. Reproduces the apophis explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/apophis>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin apophis
//! ```
//!
//! What it does:
//! 1. Pulls every available MPC optical observation of Apophis plus the
//!    JPL Goldstone/Arecibo radar delay/Doppler astrometry, and folds
//!    both ADES tables into one fit.
//! 2. Runs the full IOD → DC pipeline with the 9-parameter
//!    `STATE_AND_NONGRAV` solve so the converged orbit carries the
//!    same Marsden A1/A2/A3 non-gravitational coefficients JPL fits
//!    jointly with the state. The transverse A2 is consistent with
//!    Yarkovsky thermal recoil and is fit empirically with
//!    inverse-square g(r); a real first-principles Vokrouhlický
//!    thermal model is on the engine roadmap.
//! 3. Forward-propagates that orbit through the 2029 Earth flyby
//!    with second-order STT uncertainty.
//! 4. Prints close approaches (from the propagation event stream),
//!    reads back the resolved-kind (second-order) covariance at the
//!    flyby and contrasts it with the bare linear covariance, and
//!    reports the 2029 B-plane geometry (computed separately via
//!    `Context::compute_b_planes`).
//!
//! Authoritative cross-checks (printed inline):
//!   - 2029-04-13 21:46 UT, geocentric 38,012 km    (JPL CAD)
//!   - A1 ≈  5e-13 AU/d²  (radial)                  (JPL SBDB)
//!   - A2 ≈ -2.9e-14 AU/d²  (transverse, ≈ Yarkovsky)  (JPL SBDB)
//!   - Removed from Sentry 2021-02-21               (NASA / CNEOS)

// spielberg:snippet:start
use empyrean::{
    Context, Epoch, EventConfig, ODConfig, Observations, Origin, PropagationConfig, SolveForParams,
    UncertaintyMethod, query_observations, query_radar,
};

fn main() -> empyrean::Result<()> {
    // Loads / downloads the full Standard-tier kernel set (DE440,
    // SB441-N16, Earth/Moon BPCs, GM, MPC observatory codes) into
    // the platform's XDG data directory on first run.
    let ctx = Context::from_data_dir(None)?;

    // ── 1. Optical astrometry (MPC) + radar astrometry (JPL) ────────
    // The MPC carries optical only; asteroid radar delay/Doppler is a
    // JPL SSD product, queried separately and folded into the same fit.
    // Apophis has an extensive Goldstone/Arecibo radar record set.
    let optical = query_observations(&["99942"], None)?;
    let radar = query_radar(&["99942"], None)?;
    println!(
        "{} optical + {} radar (delay/Doppler)",
        optical.len(),
        radar.len()
    );

    // Fold both ADES tables into a single observation set. When the
    // radar query comes back empty the fit is optical-only.
    let observations = Observations::from_arrays(&optical.iter().collect::<Vec<_>>(), &radar)?;

    // ── 2. 9-parameter OD with non-grav ─────────────────────────────
    // Forces the (state + A1, A2, A3) solve. The hyperdual integrator
    // computes the (O−C) Jacobian against all 9 parameters analytically
    // — no finite differencing of the 21-year arc.
    let od_config = ODConfig {
        solve_for: SolveForParams::StateAndNonGrav,
        ..Default::default()
    };

    let result = ctx.determine(&observations, None, &od_config)?;
    let s = &result.summary;
    println!("Converged:  {}", result.converged);
    println!("chi2/dof:   {:.3}", s.reduced_chi2);
    println!(
        "RMS:        RA·cos(d) {:.3}\"  Dec {:.3}\"",
        s.rms_ra_arcsec, s.rms_dec_arcsec
    );
    println!("Selected:   {}/{}", s.num_selected, s.num_obs);
    if let Some([a1, a2, _a3]) = result.non_grav_delta {
        println!("Fitted A1 = {:.3e}  A2 = {:.3e}", a1, a2);
    }
    println!("Reference  A1 = 5.000e-13     A2 = -2.902e-14   (JPL SBDB)");

    // ── 3. Forward propagation through the 2029 flyby ───────────────
    // The fitted orbit is already re-feedable: it carries the fitted 6×6
    // covariance (so `compute_b_planes` can project it onto the encounter
    // plane) and the fitted non-grav model — no reconstruction needed.
    let orbit = result.orbit.clone().with_orbit_id("99942");

    let epochs: Vec<Epoch> = (0..341)
        .map(|i| Epoch::from_mjd_tdb(61000.0 + 5.0 * i as f64))
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

    // ── 4. Headline numbers ─────────────────────────────────────────
    // The full encounter lifecycle is `close_approach_start → periapsis
    // → close_approach_end` — the periapsis event is the actual
    // closest geocentric distance. Filter for that, not the SOI-entry
    // event the start record represents.
    println!("\nClose approaches (Empyrean):");
    for ev in prop.events.iter().filter(|e| e.event_type == "periapsis") {
        let body = ev
            .body
            .map(|b| format!("{b:?}"))
            .unwrap_or_else(|| "—".into());
        println!(
            "  {:6}  MJD {:.5}  {:>12.0} km",
            body,
            ev.epoch.mjd(),
            ev.distance_km
        );
    }
    println!("Reference (JPL CAD):");
    println!("  Earth   MJD 62239.907    38,012 km    (2029-04-13 21:46 UT)");

    // ── 4b. Tagged-covariance readback at the 2029 flyby ────────────
    // The bare `PropagatedState::covariance` is always the linear
    // Φ Σ₀ Φᵀ mapping — it over-states the encounter ellipse because
    // the 2029 flyby bends the linear map hard. The resolved-kind
    // readback (`covariance_series_cartesian`) carries the *honest*
    // covariance: inside the Auto close-approach window it is the
    // Park–Scheeres second-order (Jet2 STT) ellipsoid we asked for
    // via `UncertaintyMethod::SecondOrder`. Compare them at the grid
    // epoch nearest the periapsis to see the nonlinear correction.
    let ca_mjd = prop
        .events
        .iter()
        .find(|e| e.event_type == "periapsis" && e.body == Some(Origin::Earth))
        .map(|e| e.epoch.mjd());
    if let Some(ca_mjd) = ca_mjd {
        // Grid epoch (orbit 0, orbit-major ⇒ states[k]) nearest the flyby.
        let k = epochs
            .iter()
            .enumerate()
            .min_by(|(_, a), (_, b)| {
                (a.mjd() - ca_mjd)
                    .abs()
                    .total_cmp(&(b.mjd() - ca_mjd).abs())
            })
            .map(|(i, _)| i)
            .unwrap();

        // σ_pos = sqrt(trace of the 3×3 position block), AU → km.
        let au_km = 1.495_978_707e8;
        let pos_sigma_km =
            |cov: &[[f64; 6]; 6]| -> f64 { (cov[0][0] + cov[1][1] + cov[2][2]).sqrt() * au_km };

        let series = prop.covariance_series_cartesian(0)?;
        let resolved = &series[k];

        println!(
            "\nFlyby covariance readback (Empyrean, grid MJD {:.3}):",
            epochs[k].mjd()
        );
        if let Some(linear) = prop.states[k].covariance {
            println!(
                "  bare linear        σ_pos = {:>10.0} km",
                pos_sigma_km(&linear)
            );
        }
        println!(
            "  resolved {:<12?} σ_pos = {:>10.0} km",
            resolved.kind,
            pos_sigma_km(&resolved.matrix)
        );
        if let Some(shift) = resolved.mean_shift_prop {
            let shift_km =
                (shift[0] * shift[0] + shift[1] * shift[1] + shift[2] * shift[2]).sqrt() * au_km;
            println!("  2nd-order mean shift |δμ_prop| = {:>8.0} km", shift_km);
        }
    }

    // B-plane geometry is computed by a separate Context method —
    // dedicated propagation with the requested uncertainty method.
    let b_planes = ctx.compute_b_planes(
        &[orbit],
        *epochs.last().unwrap(),
        &[UncertaintyMethod::SecondOrder],
        &[Origin::Earth],
    )?;
    println!("\n2029 Earth B-plane geometry (Empyrean):");
    for bp in b_planes.iter().filter(|b| b.body == Origin::Earth) {
        println!("  B*T = {:>10.0} km", bp.b_dot_t_km);
        println!("  B*R = {:>10.0} km", bp.b_dot_r_km);
        println!("  3-sigma semi-major = {:>8.1} km", bp.semi_major_3sig_km);
    }
    println!("(B-plane uncertainty input to any downstream resonant-return analysis.)");

    Ok(())
}
// spielberg:snippet:end
