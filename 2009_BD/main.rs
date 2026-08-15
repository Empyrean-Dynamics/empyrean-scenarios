//! 2009 BD: fitting the SRP area-to-mass ratio AMRAT.
//!
//! Rust twin of `2009_BD/main.py`. Reproduces the 2009-bd explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/2009-bd>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin bd2009
//! ```
//!
//! Authoritative cross-checks (printed inline):
//!   - SBDB A1-derived AMRAT reference (JPL's fitted radial non-grav,
//!     converted through P0 = S/c)
//!   - Micheli, Tholen & Elliott (2012), New Astronomy 17, 446:
//!     AMR = (2.97 +/- 0.33)e-4 m^2/kg — the original SRP detection.

// empyrean:snippet:start
use empyrean::{Context, ODConfig, SolveFor, SolveForParams, query_observations, query_sbdb};

/// Wide AMRAT prior (variance, (m^2/kg)^2): loose enough that the
/// astrometry, not the prior, drives the fitted AMRAT. ~ (1e-3 m^2/kg)^2.
const AMRAT_PRIOR_VAR: f64 = 1.0e-6;
/// Radiation-pressure coefficient. Fixed, never fitted — only Cr·AMRAT
/// enters the dynamics, so the fitted AMRAT absorbs Cr (the JPL AMR
/// convention). 1.0 = total absorption.
const CR: f64 = 1.0;
/// au in m / day in s / radiation pressure at 1 au (solar constant / c).
const AU_M: f64 = 1.495978707e11;
const DAY_S: f64 = 86400.0;
const P0: f64 = 1361.0 / 2.99792458e8;
/// The original detection: Micheli, Tholen & Elliott (2012).
const MICHELI_AMRAT: f64 = 2.97e-4;
const MICHELI_SIGMA: f64 = 0.33e-4;

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. SBDB query: fitted SRP as the Marsden radial A1 ──────────
    // The current JPL solution (JPL 46) ships 2009 BD's fitted SRP not
    // as an explicit AMRAT but as a Marsden radial non-grav A1 with an
    // r^-2 law — physically the same force. Convert A1 to the AMRAT
    // seed (m^2/kg) through the standard radiation-pressure constant
    // P0 = S/c at 1 au.
    let batch = query_sbdb(&["2009 BD"], None)?;
    let orbit = batch
        .orbits
        .into_iter()
        .next()
        .expect("SBDB returned no orbit for 2009 BD");
    // 0.10.0rc0 workaround: the Rust wrapper's query_sbdb populates the
    // state<->non-grav cross-covariance without the 3x3 it conditions
    // on, and the engine (correctly) refuses the half-attached joint.
    // Clear the cross terms — this scenario reads nominal-trajectory
    // numbers only. Remove once the wrapper attaches the full block.
    let mut orbit = orbit;
    orbit.state.non_grav_cross = None;
    let a1 = orbit.a1;
    // Loud, not silent: without JPL's fitted radial non-grav there is
    // no seed to fit from.
    assert!(
        a1.is_finite() && a1 != 0.0,
        "SBDB returned no radial non-grav A1 for 2009 BD — cannot \
         seed the AMRAT fit without a starting value"
    );
    let sbdb_amrat = a1 * AU_M / (DAY_S * DAY_S) / P0;
    println!("SRP parameters (SBDB):");
    println!("  A1    = {a1:.4e} au/d^2  (JPL's fitted radial non-grav, r^-2 law)");
    println!("  AMRAT = {sbdb_amrat:.4e} m^2/kg  (A1 converted through P0 = S/c)");
    println!("  Cr    = {CR:.2}  (fixed; only Cr*AMRAT enters the dynamics)");

    // ── 2. Prime the orbit with an AMRAT prior ──────────────────────
    // AMRAT fitting is a refine-path solve: the input orbit must carry
    // amrat_variance — both the trigger that opens the AMRAT column and
    // the Bayesian prior. Hand the radial slot to AMRAT (A1 zeroed so
    // the same force is never counted twice) while the transverse A2
    // (a 13-sigma detection in JPL 46) stays in the dynamics as
    // shipped, g(r) constants and all.
    // `refine` linearizes about a Cartesian state — carry the SBDB
    // elements (and their covariance, through the element→Cartesian
    // Jacobian) into Cartesian form before priming.
    orbit.state = ctx.transform_coordinates_single(
        &orbit.state,
        empyrean::Representation::Cartesian,
        orbit.state.frame,
        orbit.state.origin,
    )?;
    let (a2, a3) = (orbit.a2, orbit.a3);
    let (alpha, r0, m, n, k) = (
        orbit.ng_alpha,
        orbit.ng_r0,
        orbit.ng_m,
        orbit.ng_n,
        orbit.ng_k,
    );
    let primed = orbit
        .with_nongrav(0.0, a2, a3)
        .with_g_function(alpha, r0, m, n, k)
        .with_srp(sbdb_amrat, CR)
        .with_srp_amrat_variance(Some(AMRAT_PRIOR_VAR));

    // ── 3. 2009 BD optical astrometry + wide AMRAT refine ───────────
    let optical = query_observations(&["2009 BD"], None)?;
    println!("\n{} optical observations", optical.len());
    let observations = empyrean::Observations::from_array(&optical.iter().collect::<Vec<_>>())?;

    let od_config = ODConfig {
        solve_for: SolveForParams::Explicit(SolveFor {
            amrat: empyrean::ParamDisposition::Solved,
            ..Default::default()
        }),
        ..Default::default()
    };
    let result = ctx.refine(&primed, &observations, &od_config)?;

    let s = &result.summary;
    println!("Converged:  {}", result.converged);
    println!("chi2/dof:   {:.3}", s.reduced_chi2);
    println!(
        "RMS:        RA·cos(d) {:.3}\"  Dec {:.3}\"",
        s.rms_ra_arcsec, s.rms_dec_arcsec
    );

    // ── 4. Fitted AMRAT ± 1σ (the v0.9.0 measurement) ───────────────
    // The tagged solved covariance names the AMRAT slot — read the
    // variance from it rather than guessing at column order.
    match (&result.solved_covariance, &result.orbit.srp) {
        (Some(sc), Some(srp)) if sc.amrat_slot.is_some() => {
            let slot = sc.amrat_slot.unwrap();
            let sigma = sc.matrix[slot][slot].sqrt();
            println!("\nFitted AMRAT  = {:.4e} +/- {sigma:.4e} m^2/kg", srp.amrat);
            println!("SBDB (A1)     = {sbdb_amrat:.4e} m^2/kg  (JPL's fitted A1, converted)");
            println!(
                "Micheli 2012  = {MICHELI_AMRAT:.4e} +/- {MICHELI_SIGMA:.4e} m^2/kg  \
                 (the original detection)"
            );
            println!(
                "(The fit measures the area-to-mass ratio directly from the \
                 astrometry via solar radiation pressure, with an honest sigma \
                 from the solved covariance.)"
            );
        }
        _ => {
            // Loud failure, not a silent zero: the AMRAT column did not open.
            println!("\nAMRAT was not recovered (no AMRAT slot in the solved covariance).");
        }
    }

    Ok(())
}
// empyrean:snippet:end
