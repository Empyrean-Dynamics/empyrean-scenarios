//! 2009 BD: measuring solar radiation pressure on a few-meter asteroid.
//!
//! Rust twin of `2009_BD/main.py`. Reproduces the 2009bd explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/2009bd>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin bd2009
//! ```
//!
//! Authoritative cross-checks (printed inline, labeled, never fitted to):
//!   - JPL SBDB solution of 2022-12-20 (180 observations, 2009-01-16 to
//!     2011-06-20): A1 and A2 with their 1 sigma
//!   - Micheli, Tholen & Elliott (2012): AMR = (2.97 +/- 0.33)e-4 m^2/kg,
//!     from a radiation-pressure-only fit to 108 observations

// empyrean:snippet:start
use empyrean::{
    AxisLayout, Context, ODConfig, Observation, Observations, PackedJoint, ParamDisposition,
    SolveFor, SolveForParams, WeightingLayer, query_observations,
};

// Two named filters on the MPC record, which is queried live below. Each keeps
// the observations at or after / at or before a UTC time: JPL's first and last
// night, so a row the MPC adds outside the arc cannot move the numbers.
const FIRST_NIGHT: &str = "2009-01-16";
const LAST_NIGHT: &str = "2011-06-20T23:59";
// The engine's radiation-pressure constant: 4.56e-6 N/m^2 at 1 au (about 1367
// W/m^2 / c). One m^2/kg of area-to-mass ratio is this many au/d^2 of radial
// acceleration at 1 au under the r^-2 law, JPL's A1 convention.
const K_SRP: f64 = 4.56e-6 * 86400.0 * 86400.0 / 1.495978707e11; // au/d^2 per m^2/kg
// JPL SBDB solution of 2022-12-20 (SBDB-published values, nothing derived by
// empyrean; 180 observations, 2009-01-16 to 2011-06-20): the Marsden radial and
// transverse terms with their 1 sigma, au/d^2. The law is r^-2: ALN = 1,
// R0 = 1 au, m = 2, n = 0, k = 0.
const JPL_A1: f64 = 5.604736985528152e-11;
const JPL_A1_SIGMA: f64 = 8.508e-12;
const JPL_A2: f64 = -1.14638955920583e-12;
const JPL_A2_SIGMA: f64 = 8.37e-14;
// Micheli, Tholen and Elliott 2012 (108 observations, radiation pressure only).
const MICHELI_AMR: f64 = 2.97e-4; // m^2/kg
const MICHELI_SIGMA: f64 = 0.33e-4;
// Priors, wide on every axis and not JPL's solution: 1e-2 au and 1e-4 au/d on the
// state, 1e-9 and 1e-11 au/d^2 on A1 and A2 (about 20 and 10 times JPL's values).
// A3 is held at zero by a tight prior, as in JPL's solved set (A1 and A2): the
// engine's refine has no per-axis fixed/solved switch today, so its posterior
// is the prior and contributes nothing.
const STATE_SIGMA: [f64; 6] = [1e-2, 1e-2, 1e-2, 1e-4, 1e-4, 1e-4];
const A_SIGMA: [f64; 3] = [1e-9, 1e-11, 1e-14]; // A1, A2, A3

/// Scientific notation with the exponent padded to two digits, as Python prints.
fn sci(x: f64, digits: usize) -> String {
    let s = format!("{x:.digits$e}");
    let (mantissa, exponent) = s.split_once('e').expect("scientific notation");
    let exponent: i32 = exponent.parse().expect("exponent");
    format!(
        "{mantissa}e{}{:02}",
        if exponent < 0 { '-' } else { '+' },
        exponent.abs()
    )
}

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // -- 1. The record and a cold state-only fit -----------------------
    let all = query_observations(&["2009 BD"], None)?;
    let kept: Vec<Observation> = all
        .iter()
        .filter(|o| FIRST_NIGHT <= o.obs_time.as_str() && o.obs_time.as_str() <= LAST_NIGHT)
        .collect();
    let obs = Observations::from_array(&kept)?;
    let mut stations: Vec<&str> = kept.iter().map(|o| o.obs_code.as_str()).collect();
    stations.sort();
    stations.dedup();
    let first = kept
        .iter()
        .map(|o| o.obs_time.as_str())
        .min()
        .expect("observations");
    let last = kept
        .iter()
        .map(|o| o.obs_time.as_str())
        .max()
        .expect("observations");
    println!(
        "{} optical observations from {} stations, {} to {}",
        obs.len(),
        stations.len(),
        &first[..10],
        &last[..10]
    );
    let od_config = ODConfig {
        solve_for: SolveForParams::StateOnly,
        ..Default::default()
    };
    let WeightingLayer::NightlyDeweighting { max_gap_days } =
        &od_config.weighting.additional_layers[0]
    else {
        panic!("expected the default nightly de-weighting layer");
    };
    println!(
        "Weighting: the engine default, preset {:?} (station floors) with nightly de-weighting within {max_gap_days:.1} d",
        od_config.weighting.preset
    );
    let base = ctx.determine(&obs, None, &od_config)?.into_single()?;
    let s0 = &base.summary;
    println!(
        "State-only fit (the seed): rejected {} of the {} observations; chi2/dof {:.3}  RMS RA.cos(d) {:.3}\" Dec {:.3}\"  on the {} kept",
        s0.num_rejected,
        s0.num_obs,
        s0.reduced_chi2,
        s0.rms_ra_arcsec,
        s0.rms_dec_arcsec,
        s0.num_selected
    );

    // -- 2. JPL's solution, in its own units and as an area-to-mass ratio
    println!(
        "\nRadiation-pressure constant: K = {} au/d^2 per m^2/kg (4.56e-6 N/m^2 at 1 au, the engine's)",
        sci(K_SRP, 5)
    );
    println!(
        "JPL A1 = {} +/- {} au/d^2 = {} +/- {} m^2/kg (SBDB solution 2022-12-20)",
        sci(JPL_A1, 4),
        sci(JPL_A1_SIGMA, 2),
        sci(JPL_A1 / K_SRP, 4),
        sci(JPL_A1_SIGMA / K_SRP, 2)
    );
    println!(
        "JPL A2 = {} +/- {} au/d^2 (transverse, the Yarkovsky drift)",
        sci(JPL_A2, 4),
        sci(JPL_A2_SIGMA, 2)
    );

    // -- 3. Fit A1 and A2 with the state --------------------------------
    let mut var = [[0.0_f64; 9]; 9];
    for (i, sigma) in STATE_SIGMA.iter().enumerate() {
        var[i][i] = sigma * sigma;
    }
    for (k, sigma) in A_SIGMA.iter().enumerate() {
        var[6 + k][6 + k] = sigma * sigma;
    }
    let tri: Vec<f64> = (0..9).flat_map(|i| var[i][..=i].to_vec()).collect();
    let prior = PackedJoint {
        layout: AxisLayout {
            present: 0b111, // the Marsden A1, A2, A3 axes
            considered: 0,
            marginalized: 0,
        },
        width: 9,
        tri,
        kind: empyrean::CovarianceKind::Linear,
        quality: empyrean::JointQuality::PositiveDefinite,
        functional: empyrean::JointFunctional::State,
        provenance: empyrean::JointProvenance::Derived,
        asserted_source: None,
    };
    let mut primed = base
        .orbit
        .clone()
        .with_nongrav(0.0, 0.0, 0.0)
        .with_g_function(1.0, 1.0, 2.0, 0.0, 0.0)
        .with_covariance(prior);
    // The orbit's flat state covariance must agree with the joint's state block:
    // replace the state-only fit's covariance with the prior's.
    primed.state.covariance = Some(std::array::from_fn(|i| std::array::from_fn(|j| var[i][j])));
    let fit = ctx.refine(
        &primed,
        &obs,
        &ODConfig {
            solve_for: SolveForParams::Explicit(SolveFor {
                marsden: ParamDisposition::Solved,
                ..Default::default()
            }),
            ..Default::default()
        },
    )?;
    let sc = fit
        .solved_covariance
        .as_ref()
        .expect("the fit carries a solved covariance");
    let slot = sc.marsden_slot.expect("Marsden slot opened by the solve");
    let (a1, a2, a3) = (fit.orbit.a1, fit.orbit.a2, fit.orbit.a3);
    let a1_sigma = sc.matrix[slot][slot].sqrt();
    let a2_sigma = sc.matrix[slot + 1][slot + 1].sqrt();
    let a3_sigma = sc.matrix[slot + 2][slot + 2].sqrt();
    let s = &fit.summary;
    println!(
        "\nFit with A1 and A2: converged {}  chi2/dof {:.3}  RMS RA.cos(d) {:.3}\" Dec {:.3}\"  ({}/{} obs)",
        py_bool(fit.converged),
        s.reduced_chi2,
        s.rms_ra_arcsec,
        s.rms_dec_arcsec,
        s.num_selected,
        s.num_obs
    );
    println!(
        "Priors: A1 +/- {}, A2 +/- {}, A3 +/- {} (the hold on A3) au/d^2; the fit keeps {:.2}% and {:.2}% of those priors' information",
        sci(A_SIGMA[0], 0),
        sci(A_SIGMA[1], 0),
        sci(A_SIGMA[2], 0),
        100.0 * (a1_sigma / A_SIGMA[0]).powi(2),
        100.0 * (a2_sigma / A_SIGMA[1]).powi(2)
    );
    let (amr, amr_sigma) = (a1 / K_SRP, a1_sigma / K_SRP);
    println!("A1 = {} +/- {} au/d^2", sci(a1, 4), sci(a1_sigma, 2));
    println!(
        "  = area-to-mass ratio {} +/- {} m^2/kg ({:.1} sigma), A1 / K",
        sci(amr, 4),
        sci(amr_sigma, 2),
        amr / amr_sigma
    );
    println!("A2 = {} +/- {} au/d^2", sci(a2, 4), sci(a2_sigma, 2));
    println!(
        "A3 = {} +/- {} au/d^2 (its prior, not a fit: the engine's refine has no per-axis fixed switch)",
        sci(a3, 2),
        sci(a3_sigma, 2)
    );
    let scale = s.reduced_chi2.sqrt();
    println!(
        "  scaled by the residuals (x sqrt(chi2/dof)): A1 +/- {}, A2 +/- {} au/d^2",
        sci(a1_sigma * scale, 2),
        sci(a2_sigma * scale, 2)
    );

    // -- 4. Against JPL's solution and the 2012 detection ---------------
    for (name, v, sg, j, js) in [
        ("A1", a1, a1_sigma, JPL_A1, JPL_A1_SIGMA),
        ("A2", a2, a2_sigma, JPL_A2, JPL_A2_SIGMA),
    ] {
        println!(
            "{name}: ours - JPL = {:+.2} combined sigma; JPL sigma {}, ours/JPL {:.1}",
            (v - j) / sg.hypot(js),
            sci(js, 2),
            sg / js
        );
    }
    println!(
        "Area-to-mass ratio: ours - Micheli 2012 ({} +/- {} m^2/kg, radiation pressure only) = {:+.2} combined sigma",
        sci(MICHELI_AMR, 2),
        sci(MICHELI_SIGMA, 2),
        (amr - MICHELI_AMR) / amr_sigma.hypot(MICHELI_SIGMA)
    );
    Ok(())
}

fn py_bool(b: bool) -> &'static str {
    if b { "True" } else { "False" }
}
// empyrean:snippet:end
