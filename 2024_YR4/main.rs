//! 2024 YR4: dual-fit OD story (early-arc IP vs full-arc ruled-out).
//!
//! Rust twin of `2024_YR4/main.py`. Reproduces the 2024yr4 explore-mode scenario
//! from <https://empyrean-dynamics.com/explore/2024yr4>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin yr4
//! ```

// empyrean:snippet:start
use empyrean::{
    Context, Epoch, ODConfig, Origin, PropagationConfig, UncertaintyMethod, query_observations,
};

const KM_PER_AU: f64 = 149_597_870.7;

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. Astrometric observations from MPC ────────────────────────
    let all_obs = query_observations(&["2024 YR4"], None)?;
    println!("{} observations from MPC (full arc)", all_obs.len());

    // ── 2. Strict 10-day discovery arc cut via filter_by_epoch ──────
    // YR4 was first listed on Sentry at 1.2% on 2024-12-27 with the
    // early-arc dataset. The published 3.1% Sentry peak corresponds to
    // the 55-day arc through 2025-02-18. The discovery arc here is
    // the conservative ≤10-day cut.
    let cut = Epoch::from_mjd_tdb(60680.0); // ~2024-12-27 + 10 days
    let early_arc = all_obs.filter_by_epoch(None, Some(cut))?;
    println!(
        "{} observations after 10-day discovery-arc cut (< MJD {:.2} TDB)",
        early_arc.len(),
        cut.mjd()
    );

    // ── 3. Dual OD: discovery-arc vs full-arc ───────────────────────
    let cfg = ODConfig::default();

    let print_summary = |label: &str, r: &empyrean::DetermineResult| {
        let s = &r.summary;
        println!(
            "{label}: chi2/dof = {:.3}  RMS RA·cos(d) {:.3}\" Dec {:.3}\"  ({}/{} obs)",
            s.reduced_chi2, s.rms_ra_arcsec, s.rms_dec_arcsec, s.num_selected, s.num_obs
        );
    };

    let early = ctx.determine(&early_arc, None, &cfg)?;
    print_summary("Discovery arc", &early);

    let full = ctx.determine(&all_obs, None, &cfg)?;
    print_summary("Full arc     ", &full);

    // ── 4. Compute impact probabilities to 2032 encounter for both fits ──
    let end_epoch = Epoch::from_mjd_tdb(63730.0); // ~2032-12-31

    // The fitted orbit is already re-feedable — it carries its covariance
    // and the fitted non-grav model. Pass it straight to the IP call.
    let early_orbit = early.orbit.clone().with_orbit_id("2024 YR4 (discovery)");
    let full_orbit = full.orbit.clone().with_orbit_id("2024 YR4 (full)");

    let print_ips = |label: &str, ips: &[empyrean::ImpactProbability]| {
        println!("\n{label} — 2032 encounter:");
        for ip in ips {
            let miss_km = ip.miss_distance_au * KM_PER_AU;
            let sigma_km = ip.sigma_distance_au * KM_PER_AU;
            println!(
                "  {:?}  IP_linear = {:>7.3}%  miss = {:>10.1} km  sigma_d = {:>10.1} km",
                ip.body,
                ip.ip_linear * 100.0,
                miss_km,
                sigma_km,
            );
        }
    };

    let early_ips = ctx.compute_impact_probabilities(
        &[early_orbit],
        end_epoch,
        &[UncertaintyMethod::SecondOrder],
        &[Origin::Earth, Origin::Moon],
    )?;
    print_ips("Discovery arc", &early_ips);

    let full_ips = ctx.compute_impact_probabilities(
        &[full_orbit],
        end_epoch,
        &[UncertaintyMethod::SecondOrder],
        &[Origin::Earth, Origin::Moon],
    )?;
    print_ips("Full arc", &full_ips);

    // ── 5. Tagged-covariance readback through the 2032 flyby ─────────
    // The bare linear covariance on a propagated state is Φ Σ₀ Φᵀ — it
    // ignores the curvature of the dynamics across the encounter. Near a
    // planetary close approach that curvature matters, so we propagate
    // the full-arc fit through the flyby under SecondOrder uncertainty
    // and read the *resolved-kind* (Park–Scheeres second-order)
    // covariance back, contrasting it with the linear one at perigee.
    let grid: Vec<Epoch> = (0..271)
        .map(|i| Epoch::from_mjd_tdb(61_000.0 + 10.0 * i as f64))
        .collect();

    let prop_cfg = PropagationConfig {
        uncertainty_method: UncertaintyMethod::SecondOrder,
        ..PropagationConfig::default()
    };

    let full_orbit = full.orbit.clone().with_orbit_id("2024 YR4 (full)");
    let prop = ctx.propagate(std::slice::from_ref(&full_orbit), &grid, &prop_cfg)?;

    // Earth periapsis epoch from the detected events.
    let earth_peri = prop
        .events
        .iter()
        .find(|e| e.event_type == "periapsis" && e.body == Some(Origin::Earth))
        .expect("Earth periapsis detected during the 2032 flyby");
    let ca_mjd = earth_peri.epoch.mjd_tdb()?;

    // Resolved-kind covariance series (one tag per output epoch),
    // aligned epoch-for-epoch with `prop.states`.
    let series = prop.covariance_series_cartesian(0)?;
    let k = series
        .iter()
        .enumerate()
        .min_by(|(_, a), (_, b)| {
            let da = (a.epoch.mjd_tdb().unwrap() - ca_mjd).abs();
            let db = (b.epoch.mjd_tdb().unwrap() - ca_mjd).abs();
            da.partial_cmp(&db).unwrap()
        })
        .map(|(i, _)| i)
        .expect("non-empty covariance series");

    let pos_sigma_km =
        |m: &[[f64; 6]; 6]| -> f64 { ((m[0][0] + m[1][1] + m[2][2]).sqrt()) * KM_PER_AU };

    let resolved = &series[k];
    let resolved_sigma = pos_sigma_km(&resolved.matrix);
    // The bare linear covariance lives on the propagated state itself.
    // States are NOT request-ordered (encounter episodes are grouped by
    // origin), so find the row by its own epoch.
    let k_state = prop
        .states
        .iter()
        .enumerate()
        .min_by(|(_, a), (_, b)| {
            (a.epoch.mjd() - ca_mjd)
                .abs()
                .total_cmp(&(b.epoch.mjd() - ca_mjd).abs())
        })
        .map(|(i, _)| i)
        .expect("non-empty states");
    let linear_sigma = prop.states[k_state]
        .covariance
        .as_ref()
        .map(pos_sigma_km)
        .expect("linear covariance present on the propagated state");

    println!("\nTagged-covariance readback at 2032 Earth perigee (MJD {ca_mjd:.4} TDB):");
    println!("  resolved kind        = {:?}", resolved.kind);
    println!("  resolved pos sigma   = {resolved_sigma:>10.1} km  (second-order ellipsoid)");
    println!("  linear   pos sigma   = {linear_sigma:>10.1} km  (bare Phi Sigma0 Phi^T)");

    println!("\nReference (JPL CAD, full-arc nominal):");
    println!("  Earth   ~278,000 km   IP = 0");
    println!("  Moon    ~23,000 km    IP = 0   (inside Moon's Hill sphere)");
    println!("Reference (Sentry, peak):");
    println!("  Earth   55-day arc, 2025-02-18 published    IP = 3.1%");

    Ok(())
}
// empyrean:snippet:end
