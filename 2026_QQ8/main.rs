//! 2026 QQ8: seen after the pass: sunlight and a captured flyby.
//!
//! Rust twin of `2026_QQ8/main.py`. Reproduces the 2026qq8 explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/2026qq8>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin qq8
//! ```
//!
//! Authoritative cross-checks (printed inline, labeled, never fitted to):
//!   - JPL SBDB solution of 2026-11-08: H = 31.367 +/- 0.342,
//!     A1 = 1.174e-10 +/- 2.777e-11 au/d^2 (r^-2 law)
//!   - Capture test: Granvik, Vaubaillon and Jedicke 2012; mini-moon
//!     (captured orbiter) test: Fedorets, Granvik and Jedicke 2017

// empyrean:snippet:start
use empyrean::{
    AxisLayout, Context, Epoch, EventConfig, Frame, JointFunctional, JointProvenance, JointQuality,
    ODConfig, Observation, Observations, Origin, PackedJoint, ParamDisposition, PropagatedState,
    PropagationConfig, SolveFor, SolveForParams, TimeScale, UncertaintyMethod, WeightingLayer,
    query_observations,
};

const AU_KM: f64 = 149_597_870.7;
const MU_EARTH: f64 = 398600.4418; // km^3/s^2
const LUNAR_DISTANCE_KM: f64 = 384_400.0;
// The engine's radiation-pressure constant: 4.56e-6 N/m^2 at 1 au (about
// 1367 W/m^2 / c). One m^2/kg of area-to-mass ratio is this many au/d^2 of
// radial acceleration at 1 au under the r^-2 law, JPL's A1 convention.
const K_SRP: f64 = 4.56e-6 * 86400.0 * 86400.0 / 1.495978707e11; // au/d^2 per m^2/kg
// Priors, wide on every axis and not JPL's solution: 1e-2 au and 1e-4 au/d on
// the state, 1e-2 m^2/kg on the area-to-mass ratio (JPL's value is 5e-4).
const STATE_SIGMA: [f64; 6] = [1e-2, 1e-2, 1e-2, 1e-4, 1e-4, 1e-4];
const AMRAT_SEED: f64 = 1e-4; // m^2/kg, the prior mean (the fit starts here)
const AMRAT_SIGMA: f64 = 1e-2;
// JPL SBDB solution of 2026-11-08 (39 observations), the reference only.
const JPL_H: f64 = 31.367;
const JPL_H_SIGMA: f64 = 0.342;
const JPL_A1: f64 = 1.174e-10; // au/d^2, r^-2 law
const JPL_A1_SIGMA: f64 = 2.777e-11;
// Labeled comparison values from other scenarios.
const AMRAT_2025_010D: f64 = 0.0029; // m^2/kg, Falcon 9 stage (2025-010D scenario)
const A1_2020_CD3: f64 = 1.357e-10; // au/d^2, SBDB, natural analogue (2020 CD3 scenario)
// The observations are queried live from the MPC and filtered to this arc: the one
// JPL's solution of 2026-11-08 used, so later observations do not move the numbers.
const LAST_NIGHT: &str = "2026-11-07T23:59"; // UTC

/// Scientific notation with the exponent padded to two digits, as Python prints.
fn sci(x: f64, precision: usize) -> String {
    let s = format!("{x:.precision$e}");
    let (mantissa, exponent) = s.split_once('e').expect("scientific notation");
    let exponent: i32 = exponent.parse().expect("exponent");
    format!(
        "{mantissa}e{}{:02}",
        if exponent < 0 { '-' } else { '+' },
        exponent.abs()
    )
}

/// A whole number with thousands separators.
fn commas(x: f64) -> String {
    let digits = format!("{x:.0}");
    let mut out = String::new();
    for (i, c) in digits.chars().enumerate() {
        if i > 0 && (digits.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(c);
    }
    out
}

fn py_bool(b: bool) -> &'static str {
    if b { "True" } else { "False" }
}

/// Median, averaging the two middle values of an even count (as numpy does).
fn median(values: &[f64]) -> f64 {
    let mut v = values.to_vec();
    v.sort_by(f64::total_cmp);
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    }
}

fn norm(v: [f64; 3]) -> f64 {
    (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt()
}

fn iso_tdb(mjd_tdb: f64) -> empyrean::Result<String> {
    // The calendar date of a TDB MJD: label the number as UTC so that no
    // time-scale offset is applied when it is written as a date.
    Ok(empyrean::mjd_to_iso(mjd_tdb, TimeScale::UTC)?[..16].to_string())
}

fn iso_utc(mjd_tdb: f64) -> empyrean::Result<String> {
    let mjd_utc = Epoch::from_mjd_tdb(mjd_tdb).mjd_utc()?;
    Ok(empyrean::mjd_to_iso(mjd_utc, TimeScale::UTC)?[..16].to_string())
}

fn tdb_mjd_of_utc_iso(iso: &str) -> empyrean::Result<f64> {
    Epoch::from_iso_utc(iso)?.mjd_tdb()
}

/// Epochs (MJD), positions (km) and velocities (km/s) of a track.
type Track = (Vec<f64>, Vec<[f64; 3]>, Vec<[f64; 3]>);

/// Geocentric ecliptic position (km) and velocity (km/s) of propagated states.
fn geocentric(ctx: &Context, states: &[PropagatedState]) -> empyrean::Result<Track> {
    let epochs: Vec<Epoch> = states.iter().map(|s| s.epoch).collect();
    let earth = ctx.get_states(Origin::Earth, Origin::SSB, &epochs, Frame::EclipticJ2000)?;
    let mut mjd = Vec::new();
    let mut pos = Vec::new();
    let mut vel = Vec::new();
    for (s, e) in states.iter().zip(earth.iter()) {
        assert!(
            s.origin == Origin::SSB && s.frame == Frame::EclipticJ2000,
            "expected barycentric ecliptic states"
        );
        mjd.push(s.epoch.mjd());
        pos.push(std::array::from_fn(|i| {
            (s.position[i] - e.position[i]) * AU_KM
        }));
        vel.push(std::array::from_fn(|i| {
            (s.velocity[i] - e.velocity[i]) * AU_KM / 86400.0
        }));
    }
    Ok((mjd, pos, vel))
}

fn config(uncertainty_method: UncertaintyMethod, close_approaches: bool) -> PropagationConfig {
    PropagationConfig {
        uncertainty_method,
        frame: Frame::EclipticJ2000,
        events: EventConfig {
            close_approaches,
            ..Default::default()
        },
        ..Default::default()
    }
}

fn captured_span(
    ctx: &Context,
    orbit: &empyrean::Orbit,
    label: &str,
) -> empyrean::Result<(empyrean::PropagationResult, f64, f64)> {
    let grid: Vec<Epoch> = (0..1001)
        .map(|i| Epoch::from_mjd_tdb(61100.0 + i as f64))
        .collect();
    let prop = ctx.propagate(
        std::slice::from_ref(orbit),
        &grid,
        &config(UncertaintyMethod::FirstOrder, true),
    )?;
    let mut starts = Vec::new();
    let mut ends = Vec::new();
    for e in &prop.events {
        match e.event_type.as_str() {
            "capture_start" => starts.push(e.epoch.mjd_tdb()?),
            "capture_end" => ends.push(e.epoch.mjd_tdb()?),
            _ => {}
        }
    }
    assert!(starts.len() == 1 && ends.len() == 1, "expected one capture");
    println!(
        "{label}: captured by Earth {} to {} TDB ({:.0} days)",
        iso_tdb(starts[0])?,
        iso_tdb(ends[0])?,
        ends[0] - starts[0]
    );
    Ok((prop, starts[0], ends[0]))
}

/// Linear interpolation on an ascending grid, clamped at the ends.
fn interp(x: f64, xs: &[f64], ys: &[f64]) -> f64 {
    if x <= xs[0] {
        return ys[0];
    }
    if x >= xs[xs.len() - 1] {
        return ys[ys.len() - 1];
    }
    let j = xs.partition_point(|&v| v <= x);
    ys[j - 1] + (ys[j] - ys[j - 1]) * (x - xs[j - 1]) / (xs[j] - xs[j - 1])
}

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // -- 1. The observations and a state-only fit ----------------------
    let all = query_observations(&["2026 QQ8"], None)?;
    // Keep the observations through LAST_NIGHT (UTC): the arc the numbers use.
    let kept: Vec<Observation> = all
        .iter()
        .filter(|o| o.obs_time.as_str() <= LAST_NIGHT)
        .collect();
    let obs = Observations::from_array(&kept)?;
    let mut ot: Vec<String> = kept.iter().map(|o| o.obs_time.clone()).collect();
    ot.sort();
    let mut nights: Vec<String> = ot.iter().map(|t| t[..10].to_string()).collect();
    nights.dedup();
    let early = ot.iter().filter(|t| t[..10] <= *nights[4]).count();
    let first_obs = tdb_mjd_of_utc_iso(&ot[0])?;
    let last_obs = tdb_mjd_of_utc_iso(&ot[ot.len() - 1])?;
    let mut stations: Vec<&str> = kept.iter().map(|o| o.obs_code.as_str()).collect();
    stations.sort();
    stations.dedup();
    println!(
        "{} observations from {} stations over {:.1} days",
        obs.len(),
        stations.len(),
        last_obs - first_obs
    );
    println!(
        "{} nights, {} to {}; {} observations in the first five nights, first station {}",
        nights.len(),
        nights[0],
        nights[nights.len() - 1],
        early,
        kept[0].obs_code
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
    let chi2_0 = s0.reduced_chi2 * (2 * s0.num_selected - 6) as f64;
    println!(
        "State-only fit: chi2/dof {:.3}  RMS RA.cos(d) {:.3}\" Dec {:.3}\"  ({}/{} obs)",
        s0.reduced_chi2, s0.rms_ra_arcsec, s0.rms_dec_arcsec, s0.num_selected, s0.num_obs
    );
    println!(
        "Per station (observations, of which with a stated sigma, median stated sigma, median sigma the fit applies, median |RA residual|, arcsec):"
    );
    let all_codes: Vec<&str> = kept.iter().map(|o| o.obs_code.as_str()).collect();
    let mut codes = stations.clone();
    codes.sort_by(|a, b| {
        let count = |c: &str| all_codes.iter().filter(|s| **s == c).count();
        count(b).cmp(&count(a)).then(a.cmp(b))
    });
    for code in codes {
        let applied: Vec<f64> = base
            .residuals
            .iter()
            .filter(|r| r.obs_code == code)
            .map(|r| r.residual_cov_ra.sqrt())
            .collect();
        let resid: Vec<f64> = base
            .residuals
            .iter()
            .filter(|r| r.obs_code == code)
            .map(|r| r.ra_residual_arcsec.abs())
            .collect();
        let given: Vec<f64> = kept
            .iter()
            .filter(|o| o.obs_code == code && o.rms_ra_arcsec.is_finite())
            .map(|o| o.rms_ra_arcsec)
            .collect();
        let stated_text = if given.is_empty() {
            "none".to_string()
        } else {
            format!("{:.3}", median(&given))
        };
        println!(
            "  {code}: {:2} obs, {:2} stated, stated {stated_text:>5}, applied {:.3}, |residual| {:.3}",
            applied.len(),
            given.len(),
            median(&applied),
            median(&resid)
        );
    }

    // -- 2. Fit the radiation-pressure term with the state -------------
    let mut var = [[0.0_f64; 7]; 7];
    for (i, sigma) in STATE_SIGMA.iter().enumerate() {
        var[i][i] = sigma * sigma;
    }
    var[6][6] = AMRAT_SIGMA * AMRAT_SIGMA;
    let tri: Vec<f64> = (0..7).flat_map(|i| var[i][..=i].to_vec()).collect();
    let prior = PackedJoint {
        layout: AxisLayout {
            present: 1 << 4, // the AMRAT axis
            considered: 0,
            marginalized: 0,
        },
        width: 7,
        tri,
        kind: empyrean::CovarianceKind::Linear,
        quality: JointQuality::PositiveDefinite,
        functional: JointFunctional::State,
        provenance: JointProvenance::Derived,
        asserted_source: None,
    };
    let mut primed = base
        .orbit
        .clone()
        .with_srp(AMRAT_SEED, 1.0)
        .with_covariance(prior);
    // The orbit's flat state covariance must agree with the joint's state block:
    // replace the state-only fit's covariance with the prior's.
    primed.state.covariance = Some(std::array::from_fn(|i| std::array::from_fn(|j| var[i][j])));
    let fit = ctx.refine(
        &primed,
        &obs,
        &ODConfig {
            solve_for: SolveForParams::Explicit(SolveFor {
                amrat: ParamDisposition::Solved,
                ..Default::default()
            }),
            ..Default::default()
        },
    )?;
    let sc = fit
        .solved_covariance
        .as_ref()
        .expect("the fit carries a solved covariance");
    let slot = sc.amrat_slot.expect("the AMRAT axis was solved");
    let amrat = fit.orbit.srp.as_ref().expect("the fit carries SRP").amrat;
    let sigma = sc.matrix[slot][slot].sqrt();
    let s = &fit.summary;
    let chi2_1 = s.reduced_chi2 * (2 * s.num_selected - 7) as f64;
    println!(
        "\nFit with the area-to-mass ratio: converged {}  chi2/dof {:.3}  RMS RA.cos(d) {:.3}\" Dec {:.3}\"  ({}/{} obs)",
        py_bool(fit.converged),
        s.reduced_chi2,
        s.rms_ra_arcsec,
        s.rms_dec_arcsec,
        s.num_selected,
        s.num_obs
    );
    println!(
        "Prior on the ratio: {} +/- {} m^2/kg; the fit keeps {:.2}% of that prior's information",
        sci(AMRAT_SEED, 0),
        sci(AMRAT_SIGMA, 0),
        100.0 * (sigma / AMRAT_SIGMA).powi(2)
    );
    println!(
        "Area-to-mass ratio = {} +/- {} m^2/kg ({:.1} sigma); chi2 falls by {:.1} for one parameter",
        sci(amrat, 3),
        sci(sigma, 3),
        amrat / sigma,
        chi2_0 - chi2_1
    );
    println!(
        "  scaled by the residuals (x sqrt(chi2/dof)): +/- {} m^2/kg",
        sci(sigma * s.reduced_chi2.sqrt(), 3)
    );
    let (a1, a1_sigma) = (amrat * K_SRP, sigma * K_SRP);
    println!(
        "A1 equivalent = {} +/- {} au/d^2, the same force as JPL's A1 under the r^-2 law (K = {} au/d^2 per m^2/kg)",
        sci(a1, 3),
        sci(a1_sigma, 2),
        sci(K_SRP, 5)
    );
    let gap = (a1 - JPL_A1) / (a1_sigma.hypot(JPL_A1_SIGMA));
    println!(
        "JPL A1        = {} +/- {} au/d^2 (SBDB solution 2026-11-08); difference {gap:+.2} combined sigma",
        sci(JPL_A1, 3),
        sci(JPL_A1_SIGMA, 2)
    );

    // -- 3. What the ratio could mean -----------------------------------
    println!(
        "\nFor H = {JPL_H:.3} +/- {JPL_H_SIGMA:.3}, a sphere of albedo p has diameter 1329 km / sqrt(p) x 10^(-H/5). With area-to-mass = 1.5 / (rho D) and the ratio absorbing Cr, these densities are lower bounds:"
    );
    for albedo in [0.05_f64, 0.15, 0.40] {
        let diameter = 1329e3 / albedo.sqrt() * 10.0_f64.powf(-JPL_H / 5.0); // m
        let density = 1.5 / (amrat * diameter);
        let rel = (sigma / amrat).hypot(10.0_f64.ln() / 5.0 * JPL_H_SIGMA);
        println!(
            "  albedo {albedo:.2}: {diameter:4.1} m, bulk density {density:5.0} +/- {:4.0} kg/m^3",
            density * rel
        );
    }
    println!(
        "Natural analogue 2020 CD3: A1 {} au/d^2 = {} m^2/kg; the Falcon 9 stage 2025-010D: {} m^2/kg",
        sci(A1_2020_CD3, 3),
        sci(A1_2020_CD3 / K_SRP, 2),
        sci(AMRAT_2025_010D, 1)
    );

    // -- 4. Was it a mini-moon? -----------------------------------------
    // The engine's capture test is the standard one: negative geocentric
    // energy within three Hill radii. A temporarily captured orbiter, as
    // opposed to a captured flyby, makes at least one full revolution of Earth
    // in the Sun-Earth rotating frame (Fedorets et al. 2017).
    // Earth's Hill radius, Earth alone at 1 au: 1 au x (m_Earth / (3 m_Sun))^(1/3).
    let hill_radius_km = AU_KM * (3.00348e-6_f64 / 3.0).powf(1.0 / 3.0);
    let (prop, start, end) = captured_span(&ctx, &fit.orbit, "Fit with the ratio")?;
    captured_span(&ctx, &base.orbit, "State-only (A1 = 0)")?;
    let days: Vec<Epoch> = (0..=(end - start) as usize)
        .map(|i| Epoch::from_mjd_tdb(start + i as f64))
        .collect();
    let track = ctx.propagate(
        std::slice::from_ref(&fit.orbit),
        &days,
        &config(UncertaintyMethod::FirstOrder, false),
    )?;
    let (_, pos, _) = geocentric(&ctx, &track.states)?;
    let sun = ctx.get_states(Origin::SUN, Origin::Earth, &days, Frame::EclipticJ2000)?;
    let mut angle: Vec<f64> = pos
        .iter()
        .zip(sun.iter())
        .map(|(p, s)| p[1].atan2(p[0]) - s.position[1].atan2(s.position[0]))
        .collect();
    // np.unwrap: remove 2 pi jumps between consecutive samples.
    for i in 1..angle.len() {
        let d = angle[i] - angle[i - 1];
        let wrapped = (d + std::f64::consts::PI).rem_euclid(2.0 * std::f64::consts::PI)
            - std::f64::consts::PI;
        let wrapped = if wrapped == -std::f64::consts::PI && d > 0.0 {
            std::f64::consts::PI
        } else {
            wrapped
        };
        let shift = if d.abs() < std::f64::consts::PI {
            0.0
        } else {
            wrapped - d
        };
        // Later samples carry the accumulated correction.
        for a in angle[i..].iter_mut() {
            *a += shift;
        }
    }
    let turns = (angle[angle.len() - 1] - angle[0]).abs() / (2.0 * std::f64::consts::PI);
    let r_km: Vec<f64> = pos.iter().map(|p| norm(*p)).collect();
    let r_min = r_km.iter().cloned().fold(f64::INFINITY, f64::min);
    let r_max = r_km.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    println!(
        "Geocentric distance while captured: {} to {} km (at most {:.2} Hill radii of {} km, Earth alone at 1 au; the capture test allows 3)",
        commas(r_min),
        commas(r_max),
        r_max / hill_radius_km,
        commas(hill_radius_km)
    );
    println!(
        "Revolutions of Earth in the Sun-Earth rotating frame: {turns:.2}; complete revolutions N = {}",
        turns as i64
    );
    // Closest approach: the engine suppresses Earth close-approach events while
    // the object is captured by Earth, so take the minimum of a fine sampling,
    // refined by a parabola through its lowest three points.
    let fine: Vec<Epoch> = (0..201)
        .map(|i| Epoch::from_mjd_tdb(61270.9 + 0.001 * i as f64))
        .collect();
    let fine_prop = ctx.propagate(
        std::slice::from_ref(&fit.orbit),
        &fine,
        &config(UncertaintyMethod::FirstOrder, false),
    )?;
    let (tf, pf, vf) = geocentric(&ctx, &fine_prop.states)?;
    let rf: Vec<f64> = pf.iter().map(|p| norm(*p)).collect();
    let argmin = rf
        .iter()
        .enumerate()
        .min_by(|a, b| a.1.total_cmp(b.1))
        .map(|(i, _)| i)
        .expect("fine samples");
    let k = argmin.clamp(1, rf.len() - 2);
    // The parabola through three points, in time offset from the middle one.
    let (h0, h2) = (tf[k - 1] - tf[k], tf[k + 1] - tf[k]);
    let (y0, y1, y2) = (rf[k - 1], rf[k], rf[k + 1]);
    let (b0, b2) = (y0 - y1, y2 - y1);
    let det = h0 * h0 * h2 - h2 * h2 * h0;
    let c2 = (b0 * h2 - b2 * h0) / det;
    let c1 = (h0 * h0 * b2 - h2 * h2 * b0) / det;
    let c0 = y1;
    let t_ca = tf[k] - c1 / (2.0 * c2);
    let r_ca = c0 - c1 * c1 / (4.0 * c2);
    let v_ca = norm(vf[k]);
    println!(
        "Closest approach: {} TDB ({} UTC) at {} km ({:.2} lunar distances), speed {v_ca:.2} km/s, energy {:+.3} km^2/s^2",
        iso_tdb(t_ca)?,
        iso_utc(t_ca)?,
        commas(r_ca),
        r_ca / LUNAR_DISTANCE_KM,
        v_ca * v_ca / 2.0 - MU_EARTH / r_ca
    );

    // -- 5. How the uncertainty grows ---------------------------------------
    let grid_t: Vec<f64> = prop.states.iter().map(|s| s.epoch.mjd()).collect();
    let sig_km: Vec<f64> = prop
        .states
        .iter()
        .map(|s| {
            let b = s
                .joint
                .as_ref()
                .expect("the propagated state carries a joint")
                .state_block();
            (b[0][0] + b[1][1] + b[2][2]).sqrt() * AU_KM
        })
        .collect();
    println!("\n1-sigma position uncertainty (daily samples, interpolated, first order):");
    let after = 61700.0;
    let after_label = format!("{:.0} days after capture end", after - end);
    for (label, mjd) in [
        ("capture start", start),
        ("first observation", first_obs),
        ("closest approach", t_ca),
        ("last observation", last_obs),
        ("capture end", end),
        (after_label.as_str(), after),
    ] {
        let sig = interp(mjd, &grid_t, &sig_km);
        println!("  {label:<28} {} TDB  {sig:8.1} km", iso_tdb(mjd)?);
    }

    // -- 6. Where it goes next (first-order covariance on the long run) -----
    let long_grid: Vec<Epoch> = (0..50501)
        .map(|i| Epoch::from_mjd_tdb(34000.0 + i as f64)) // 1952 to 2090
        .collect();
    let path = ctx.propagate(
        std::slice::from_ref(&fit.orbit),
        &long_grid,
        &config(UncertaintyMethod::FirstOrder, false),
    )?;
    let (tl, pl, vl) = geocentric(&ctx, &path.states)?;
    let rl: Vec<f64> = pl.iter().map(|p| norm(*p)).collect();
    println!(
        "\nEarth passes closer than 0.05 au (daily-sampled minima, nominal path), timing sigma along the path:"
    );
    for i in 1..tl.len() - 1 {
        if rl[i] < rl[i - 1] && rl[i] <= rl[i + 1] && rl[i] < 0.05 * AU_KM {
            let speed = norm(vl[i]);
            let along = [vl[i][0] / speed, vl[i][1] / speed, vl[i][2] / speed];
            let block = path.states[i]
                .joint
                .as_ref()
                .expect("the propagated state carries a joint")
                .state_block();
            let mut quad = 0.0;
            for a in 0..3 {
                for b in 0..3 {
                    quad += along[a] * block[a][b] * AU_KM * AU_KM * along[b];
                }
            }
            let sigma_t_s = quad.sqrt() / speed;
            println!(
                "  {} TDB  {:.4} au  +/- {:9.2} min",
                &iso_tdb(tl[i])?[..10],
                rl[i] / AU_KM,
                sigma_t_s / 60.0
            );
        }
    }
    Ok(())
}
// empyrean:snippet:end
