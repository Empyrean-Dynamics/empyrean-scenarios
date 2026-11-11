//! 2026 ED138: a large trans-Neptunian object, 49 years of astrometry.
//!
//! Rust twin of `2026_ED138/main.py`. Reproduces the 2026ed138 explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/2026ed138>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin ed138
//! ```
//!
//! Authoritative cross-checks (printed inline, labeled, never fitted to):
//!   - JPL SBDB solution of 2026-10-29: 115 observations, 1937-12-30 to
//!     2026-07-11; elements and 1 sigma at MJD 61200 TDB
//!   - Holman, Jurić, Napier et al. 2026, arXiv:2610.38693: H_V and Table 2
//!   - Souami and Souchay 2012 (the invariable plane); Khain et al. 2020 (the
//!     resonance criteria the paper applies)

// empyrean:snippet:start
use std::collections::BTreeMap;

use empyrean::{
    Context, Epoch, Frame, ODConfig, Observation, Observations, Orbit, Origin, OutputEpoch,
    PropagationConfig, Representation, UncertaintyMethod, query_observations,
};

// Two named filters on the MPC record, which is queried live below. Each keeps
// the observations at or after / at or before a UTC time.
// FIRST_USABLE: before 1960 empyrean 0.11 cannot convert UTC to TDB, so the
// 1937 and 1954 plates are in the record but held out here; the release that
// reads pre-1960 times lowers this to "1937".
const FIRST_USABLE: &str = "1960-01-01";
// LAST_NIGHT: the last night of JPL's solution (2026-10-29) and of the discovery
// paper's fit, so the three orbits are compared on the same end of the arc and
// observations the MPC adds later do not move the numbers.
const LAST_NIGHT: &str = "2026-07-11T23:59";
// JPL SBDB solution of 2026-10-29 (SBDB-published values, nothing derived by
// empyrean): 115 observations, 1937-12-30 to 2026-07-11 (an 89-year arc), ecliptic
// J2000, epoch MJD 61200 TDB (2026-06-09): a, e, i, node, argument of perihelion,
// mean anomaly (au, degrees) and their 1 sigma.
const JPL: [f64; 6] = [
    42.94869526572302,
    0.1417448328770402,
    24.47104038674766,
    322.5008984905298,
    167.9532328404424,
    128.3342024098231,
];
const JPL_SIGMA: [f64; 6] = [
    0.00052895, 2.3485e-6, 2.5475e-5, 8.2894e-5, 0.0041598, 0.0049194,
];
// Calibrated V-band absolute magnitude at zero phase, Holman et al. 2026
// (arXiv:2610.38693), Table 3; the MPC and SBDB H comes from redder bands.
const H_V: f64 = 3.19;
const H_V_SIGMA: f64 = 0.04;
// Holman et al. 2026, Table 2: adopted fit (74 observations, 2016-02-25 to
// 2026-07-11), barycentric ecliptic J2000 at MJD 59337.8171 TDB: a, e, i, node,
// argument of perihelion, mean anomaly, q, and their 1 sigma.
const PAPER_EPOCH: f64 = 59337.8171;
const PAPER: [f64; 7] = [
    43.090975, 0.1387280, 24.4338512, 322.606057, 168.6998, 121.0797, 37.11305,
];
// Uncertainties facing below / above (a, e, q, i are the paper's delta-chi^2 = 1
// profile ranges; node, argument of perihelion and mean anomaly are its 1 sigma).
const PAPER_SIGMA: [(f64, f64); 7] = [
    (6.0e-5, 5.6e-5),
    (7.4e-6, 7.4e-6),
    (1.8e-6, 1.8e-6),
    (2.9e-5, 2.9e-5),
    (2.8e-3, 2.8e-3),
    (4.0e-3, 4.0e-3),
    (2.7e-4, 2.7e-4),
];
const PAPER_PROPER_INCLINATION: f64 = 25.7; // deg, Holman et al. 2026 Table 2
// Masses in solar masses (the Sun with the inner planets added, and the giants'
// systems) for the invariable plane, as in the paper's integration.
const MASSES: [(Origin, f64); 5] = [
    (Origin::Sun, 1.000005977),
    (Origin::JupiterBarycenter, 9.54792e-4),
    (Origin::SaturnBarycenter, 2.85886e-4),
    (Origin::UranusBarycenter, 4.36625e-5),
    (Origin::NeptuneBarycenter, 5.15139e-5),
];
const GM_SUN: f64 = 2.959122082855911e-4; // au^3/d^2
// The Sun plus the planets, for barycentric osculating elements (the TNO
// convention, Elliot et al. 2005).
const GM_SYSTEM: f64 = GM_SUN * (1.0 + 1.341839e-3);
const AU_KM: f64 = 149_597_870.7;
const NAMES: [&str; 6] = [
    "a (au)",
    "e",
    "i (deg)",
    "node (deg)",
    "arg. perihelion (deg)",
    "mean anomaly (deg)",
];

type V3 = [f64; 3];

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

/// Seven significant digits, trailing zeros dropped, as Python's `:.7g`.
fn g7(x: f64) -> String {
    let exponent = x.abs().log10().floor() as i32;
    let s = format!("{x:.*}", (6 - exponent).max(0) as usize);
    if s.contains('.') {
        s.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        s
    }
}

/// Remainder with the sign of the divisor, as Python's `%` and numpy's `mod`.
fn pymod(a: f64, b: f64) -> f64 {
    let m = a % b;
    if m != 0.0 && ((m < 0.0) != (b < 0.0)) {
        m + b
    } else {
        m
    }
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

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

fn min(values: &[f64]) -> f64 {
    values.iter().cloned().fold(f64::INFINITY, f64::min)
}

fn max(values: &[f64]) -> f64 {
    values.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
}

fn dot(a: V3, b: V3) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

fn cross(a: V3, b: V3) -> V3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

fn norm(a: V3) -> f64 {
    dot(a, a).sqrt()
}

/// numpy's `unwrap` for angles in radians.
fn unwrap(phase: &[f64]) -> Vec<f64> {
    let pi = std::f64::consts::PI;
    let mut out = vec![phase[0]];
    let mut correction = 0.0;
    for w in phase.windows(2) {
        let dd = w[1] - w[0];
        let mut ddmod = pymod(dd + pi, 2.0 * pi) - pi;
        if ddmod == -pi && dd > 0.0 {
            ddmod = pi;
        }
        let ph_correct = if dd.abs() < pi { 0.0 } else { ddmod - dd };
        correction += ph_correct;
        out.push(w[1] + correction);
    }
    out
}

/// Smallest arc (degrees) that holds every sampled angle.
fn arc_containing(angle: &[f64]) -> f64 {
    let mut d: Vec<f64> = angle
        .iter()
        .map(|a| pymod(*a, 2.0 * std::f64::consts::PI).to_degrees())
        .collect();
    d.sort_by(f64::total_cmp);
    let mut widest = f64::NEG_INFINITY;
    for i in 0..d.len() {
        let next = if i + 1 < d.len() {
            d[i + 1]
        } else {
            d[0] + 360.0
        };
        widest = widest.max(next - d[i]);
    }
    360.0 - widest
}

/// The value to one digit beyond its sigma.
fn fmt(value: f64, sigma: f64) -> String {
    let places = (1 - sigma.log10().floor() as i32).max(0) as usize;
    format!("{value:.places$}")
}

/// Osculating elements about the barycenter from a barycentric state:
/// a, e, i, node, argument of perihelion, mean anomaly (radians).
fn elements(x: V3, v: V3) -> [f64; 6] {
    let r = norm(x);
    let h = cross(x, v);
    let hn = norm(h);
    let a = 1.0 / (2.0 / r - dot(v, v) / GM_SYSTEM);
    let vh = cross(v, h);
    let ev: V3 = std::array::from_fn(|i| vh[i] / GM_SYSTEM - x[i] / r);
    let e = norm(ev);
    let node: V3 = [-h[1], h[0], 0.0];
    let nn = norm(node);
    let raan = node[1].atan2(node[0]);
    let sum_h = |c: V3| (0..3).map(|i| c[i] * h[i] / hn).sum::<f64>();
    let w = (sum_h(cross(node, ev)) / (nn * e)).atan2(dot(node, ev) / (nn * e));
    let nu = (sum_h(cross(ev, x)) / (e * r)).atan2(dot(ev, x) / (e * r));
    let ecc =
        2.0 * ((1.0 - e).sqrt() * (nu / 2.0).sin()).atan2((1.0 + e).sqrt() * (nu / 2.0).cos());
    [a, e, (h[2] / hn).acos(), raan, w, ecc - e * ecc.sin()]
}

fn iso_epoch_tdb(iso: &str) -> empyrean::Result<f64> {
    Epoch::from_iso_utc(iso)?.mjd_tdb()
}

/// The observations from `first` through LAST_NIGHT (UTC).
fn window(record: &[Observation], first: &str) -> Vec<Observation> {
    record
        .iter()
        .filter(|o| first <= o.obs_time.as_str() && o.obs_time.as_str() <= LAST_NIGHT)
        .cloned()
        .collect()
}

/// Cold orbit determination on the observations from `first` onward.
fn fit(
    ctx: &Context,
    record: &[Observation],
    first: &str,
) -> empyrean::Result<(empyrean::DetermineResult, usize)> {
    let kept = window(record, first);
    let od_config = ODConfig {
        output_epoch: OutputEpoch::Epoch(Epoch::from_mjd_tdb(61200.0)),
        ..Default::default()
    };
    let result = ctx
        .determine(&Observations::from_array(&kept)?, None, &od_config)?
        .into_single()?;
    assert!((result.orbit.state.epoch.mjd_tdb()? - 61200.0).abs() < 1e-9);
    Ok((result, kept.len()))
}

/// Heliocentric ecliptic Keplerian elements of an orbit and their 1 sigma.
fn keplerian(ctx: &Context, orbit: &Orbit) -> empyrean::Result<([f64; 6], [f64; 6])> {
    let k = ctx.transform_orbits(
        std::slice::from_ref(orbit),
        Representation::Keplerian,
        Frame::EclipticJ2000,
        Origin::Sun,
    )?;
    let state = &k.orbits[0].state;
    let cov = state.covariance.expect("the orbit carries a covariance");
    Ok((state.elements, std::array::from_fn(|i| cov[i][i].sqrt())))
}

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // -- 1. The record -------------------------------------------------
    let all = query_observations(&["2026 ED138"], None)?;
    // Keep the observations through LAST_NIGHT (UTC): the frozen arc the numbers use.
    let record: Vec<Observation> = all
        .iter()
        .filter(|o| o.obs_time.as_str() <= LAST_NIGHT)
        .collect();
    let times: Vec<&str> = record.iter().map(|o| o.obs_time.as_str()).collect();
    let first_time = times.iter().min().expect("observations");
    let last_time = times.iter().max().expect("observations");
    println!(
        "{} observations of 2026 ED138 in the MPC record through {}, {} to {}",
        record.len(),
        &LAST_NIGHT[..10],
        &first_time[..10],
        &last_time[..10]
    );
    let mut decades: BTreeMap<String, usize> = BTreeMap::new();
    for t in &times {
        *decades.entry(format!("{}0s", &t[..3])).or_default() += 1;
    }
    let decade_text: Vec<String> = decades.iter().map(|(d, n)| format!("{d} {n}")).collect();
    println!("By decade: {}", decade_text.join(", "));
    let held = times.iter().filter(|t| **t < FIRST_USABLE).count();
    println!(
        "{held} observations before {} held out; observations after {} are not used",
        &FIRST_USABLE[..4],
        &LAST_NIGHT[..10]
    );
    let mut old: Vec<&Observation> = record
        .iter()
        .filter(|o| o.obs_time.as_str() < FIRST_USABLE)
        .collect();
    old.sort_by(|a, b| a.obs_time.cmp(&b.obs_time));
    for o in old {
        println!(
            "  {} station {}, stated {:.2} arcsec: {}",
            &o.obs_time[..10],
            o.obs_code,
            o.rms_ra_arcsec,
            o.remarks.as_deref().unwrap_or("")
        );
    }
    let mut stations: Vec<&str> = record.iter().map(|o| o.obs_code.as_str()).collect();
    stations.sort();
    stations.dedup();
    println!("{} stations", stations.len());

    // -- 2. The orbit from the modern arc ------------------------------
    let (result, n_used) = fit(&ctx, &record, FIRST_USABLE)?;
    let s = &result.summary;
    println!(
        "\nFit from {}: {}/{n_used} observations, chi2/dof {:.3}, RMS RA.cos(d) {:.3}\" Dec {:.3}\"",
        &FIRST_USABLE[..4],
        s.num_selected,
        s.reduced_chi2,
        s.rms_ra_arcsec,
        s.rms_dec_arcsec
    );
    println!(
        "Default weighting: stated sigma with station floors and nightly de-weighting. \
         Per station (stated sigma, sigma the fit applies, median |RA residual|, arcsec):"
    );
    let used_obs = window(&record, FIRST_USABLE);
    let mut used_codes: Vec<&str> = used_obs.iter().map(|o| o.obs_code.as_str()).collect();
    used_codes.sort();
    used_codes.dedup();
    let count = |c: &str| used_obs.iter().filter(|o| o.obs_code == c).count();
    used_codes.sort_by(|a, b| count(b).cmp(&count(a)).then(a.cmp(b)));
    for code in used_codes.iter().take(6) {
        let applied: Vec<f64> = result
            .residuals
            .iter()
            .filter(|r| r.obs_code == *code)
            .map(|r| r.residual_cov_ra.sqrt())
            .collect();
        let resid: Vec<f64> = result
            .residuals
            .iter()
            .filter(|r| r.obs_code == *code)
            .map(|r| r.ra_residual_arcsec.abs())
            .collect();
        let stated: Vec<f64> = used_obs
            .iter()
            .filter(|o| o.obs_code == *code && o.rms_ra_arcsec.is_finite())
            .map(|o| o.rms_ra_arcsec)
            .collect();
        let stated_med = if stated.is_empty() {
            f64::NAN
        } else {
            median(&stated)
        };
        println!(
            "  {code}: {:3} observations, stated {stated_med:.3}, applied {:.3}, |residual| {:.3}",
            applied.len(),
            median(&applied),
            median(&resid)
        );
    }
    let mut used_times: Vec<&str> = used_obs.iter().map(|o| o.obs_time.as_str()).collect();
    used_times.sort();
    let span_years =
        (iso_epoch_tdb(used_times[used_times.len() - 1])? - iso_epoch_tdb(used_times[0])?) / 365.25;
    println!(
        "Arc used: {} to {} ({span_years:.1} years)",
        &used_times[0][..10],
        &used_times[used_times.len() - 1][..10]
    );
    let (value, sigma) = keplerian(&ctx, &result.orbit)?;
    println!("Elements, ecliptic J2000 at 2026-06-09 (TDB), with 1 sigma, and JPL's difference:");
    for i in 0..6 {
        println!(
            "  {:22} {:>12} +/- {}   (ours - JPL) = {:+.2} JPL sigma; JPL sigma {}, ours/JPL {:.1}",
            NAMES[i],
            fmt(value[i], sigma[i]),
            sci(sigma[i], 1),
            (value[i] - JPL[i]) / JPL_SIGMA[i],
            sci(JPL_SIGMA[i], 1),
            sigma[i] / JPL_SIGMA[i]
        );
    }

    // -- 3. What the older plates add -----------------------------------
    println!("\n1 sigma by arc, under the default weights only:");
    println!(
        "  {:>10} {:>4}   a (au)     arg. perihelion   mean anomaly",
        "first year", "obs"
    );
    let mut rows: Vec<[f64; 6]> = Vec::new();
    for first in ["2010", FIRST_USABLE] {
        let (r, n) = fit(&ctx, &record, first)?;
        let (_, sg) = keplerian(&ctx, &r.orbit)?;
        rows.push(sg);
        println!(
            "  {:>10} {n:4}   {}   {} deg   {} deg   RMS {:.3}\" / {:.3}\"",
            &first[..4],
            sci(sg[0], 2),
            sci(sg[4], 2),
            sci(sg[5], 2),
            r.summary.rms_ra_arcsec,
            r.summary.rms_dec_arcsec
        );
    }
    let change: Vec<f64> = (0..6)
        .map(|i| 100.0 * (1.0 - rows[1][i] / rows[0][i]))
        .collect();
    println!(
        "  Adding the observations of {} to 2009 lowers sigma by {:.0}% (a), {:.0}% (arg. perihelion), {:.0}% (mean anomaly)",
        &FIRST_USABLE[..4],
        change[0],
        change[4],
        change[5]
    );

    // -- 4. Size from the absolute magnitude -----------------------------
    println!(
        "\nH_V = {H_V} +/- {H_V_SIGMA} (Holman et al. 2026); diameter 1329 km / sqrt(albedo) x 10^(-H_V/5):"
    );
    for albedo in [0.25_f64, 0.10, 0.04] {
        let d = 1329.0 / albedo.sqrt() * 10.0_f64.powf(-H_V / 5.0);
        println!(
            "  albedo {albedo:.2}: {d:6.0} +/- {:3.0} km",
            d * 10.0_f64.ln() / 5.0 * H_V_SIGMA
        );
    }

    // -- 5. Resonance with Neptune over the span the planets cover -------
    // Barycentric elements, as the TNO classification uses. DE440 covers 1550
    // to 2650; phi = p*lambda - q*lambda_N - (p - q)*varpi for resonances with a
    // period ratio P/P_N = p/q near this orbit.
    let grid: Vec<Epoch> = (0..548)
        .map(|i| Epoch::from_mjd_tdb(-112000.0 + 730.0 * i as f64))
        .collect();
    let config = PropagationConfig {
        uncertainty_method: UncertaintyMethod::FirstOrder,
        frame: Frame::EclipticJ2000,
        ..Default::default()
    };
    let path = ctx.propagate(std::slice::from_ref(&result.orbit), &grid, &config)?;
    let mut t = Vec::new();
    let mut x: Vec<V3> = Vec::new();
    let mut v: Vec<V3> = Vec::new();
    for s in &path.states {
        assert!(
            s.origin == Origin::SSB && s.frame == Frame::EclipticJ2000,
            "expected barycentric ecliptic states"
        );
        t.push(s.epoch.mjd_tdb()?);
        x.push(s.position);
        v.push(s.velocity);
    }
    let nearest = |target: f64| -> usize {
        let mut best = 0;
        for i in 1..t.len() {
            if (t[i] - target).abs() < (t[best] - target).abs() {
                best = i;
            }
        }
        best
    };
    let planet = |origin: Origin, epochs: &[f64]| -> empyrean::Result<Vec<(V3, V3)>> {
        let list: Vec<Epoch> = epochs.iter().map(|m| Epoch::from_mjd_tdb(*m)).collect();
        Ok(ctx
            .get_states(origin, Origin::SSB, &list, Frame::EclipticJ2000)?
            .iter()
            .map(|s| (s.position, s.velocity))
            .collect())
    };

    // The invariable plane: perpendicular to the system's angular momentum
    // (taken at the sample nearest 2026), the paper's reference plane.
    let k_now = nearest(61200.0);
    let mut momentum = [0.0_f64; 3];
    for (origin, mass) in MASSES {
        let (p, q) = planet(origin, &[t[k_now]])?[0];
        let c = cross(p, q);
        for i in 0..3 {
            momentum[i] += mass * c[i];
        }
    }
    let mn = norm(momentum);
    let z_axis: V3 = std::array::from_fn(|i| momentum[i] / mn);
    let x0 = cross([0.0, 0.0, 1.0], z_axis);
    let xn = norm(x0);
    let x_axis: V3 = std::array::from_fn(|i| x0[i] / xn);
    let rotation = [x_axis, cross(z_axis, x_axis), z_axis];
    let rotate = |a: V3| -> V3 { std::array::from_fn(|i| dot(rotation[i], a)) };
    println!(
        "Invariable plane: {:.3} deg from the ecliptic, node {:.2} deg",
        z_axis[2].acos().to_degrees(),
        pymod(z_axis[0].atan2(-z_axis[1]).to_degrees(), 360.0)
    );
    let x: Vec<V3> = x.iter().map(|a| rotate(*a)).collect();
    let v: Vec<V3> = v.iter().map(|a| rotate(*a)).collect();
    let el: Vec<[f64; 6]> = x.iter().zip(&v).map(|(a, b)| elements(*a, *b)).collect();
    let col = |n: usize| -> Vec<f64> { el.iter().map(|e| e[n]).collect() };
    let (a, e, inc, node, w, ma) = (col(0), col(1), col(2), col(3), col(4), col(5));
    let neptune = planet(Origin::NeptuneBarycenter, &t)?;
    let el_n: Vec<[f64; 6]> = neptune
        .iter()
        .map(|(p, q)| elements(rotate(*p), rotate(*q)))
        .collect();
    let a_n: Vec<f64> = el_n.iter().map(|e| e[0]).collect();
    let n_len = t.len();
    let lam: Vec<f64> = (0..n_len).map(|i| node[i] + w[i] + ma[i]).collect();
    let lam_n: Vec<f64> = (0..n_len)
        .map(|i| el_n[i][3] + el_n[i][4] + el_n[i][5])
        .collect();
    let varpi: Vec<f64> = (0..n_len).map(|i| node[i] + w[i]).collect();
    let peri: Vec<f64> = (0..n_len).map(|i| a[i] * (1.0 - e[i])).collect();

    let years = (t[n_len - 1] - t[0]) / 365.25;
    println!(
        "\nOver {} years (1552 to 2645), barycentric, invariable plane: a {:.2} to {:.2} au (mean {:.3}), e {:.3} to {:.3}, i {:.2} to {:.2} deg, perihelion {:.1} au at its closest",
        commas(years),
        min(&a),
        max(&a),
        mean(&a),
        min(&e),
        max(&e),
        min(&inc).to_degrees(),
        max(&inc).to_degrees(),
        min(&peri)
    );
    println!(
        "At the sample nearest 2026 (MJD {:.0}) a = {:.3} au.",
        t[k_now], a[k_now]
    );
    let inc_deg: Vec<f64> = inc.iter().map(|i| i.to_degrees()).collect();
    println!(
        "Mean inclination over the span, invariable plane: {:.2} deg (the paper's proper inclination: {PAPER_PROPER_INCLINATION} deg; a mean of osculating values against a proper element)",
        mean(&inc_deg)
    );
    println!(
        "Neptune: a = {:.2} au. Resonant argument (arc that holds every sample; 360 = circulates):",
        mean(&a_n)
    );
    for (p, q) in [(5, 3), (17, 10), (12, 7), (19, 11), (7, 4)] {
        let (pf, qf) = (p as f64, q as f64);
        let a_res = mean(&a_n) * (pf / qf).powf(2.0 / 3.0);
        let raw: Vec<f64> = (0..n_len)
            .map(|i| pf * lam[i] - qf * lam_n[i] - (pf - qf) * varpi[i])
            .collect();
        let phi = unwrap(&raw);
        let net = (phi[n_len - 1] - phi[0]).to_degrees();
        println!(
            "  {p}:{q} (order {}, exact at a = {a_res:.3} au, offset {:+.3}): {:5.0} deg; net change {net:+.0} deg, {:+.3} deg/yr",
            p - q,
            mean(&a) - a_res,
            arc_containing(&phi),
            net / years
        );
    }

    // The paper's argument for the same resonance (its 10-Myr integration finds it
    // librating about 180 degrees with 95 to 115 degrees amplitude).
    let raw: Vec<f64> = (0..n_len)
        .map(|i| 12.0 * lam[i] - 7.0 * lam_n[i] - 3.0 * varpi[i] - 2.0 * node[i])
        .collect();
    let mixed = unwrap(&raw);
    let net = (mixed[n_len - 1] - mixed[0]).to_degrees();
    let re = mean(&mixed.iter().map(|m| m.cos()).collect::<Vec<_>>());
    let im = mean(&mixed.iter().map(|m| m.sin()).collect::<Vec<_>>());
    println!(
        "12:7, the paper's argument 12 lambda - 7 lambda_N - 3 varpi - 2 node: {:.0} deg, net change {net:+.0} deg, {:+.3} deg/yr; mean {:.0} deg",
        arc_containing(&mixed),
        net / years,
        pymod(im.atan2(re).to_degrees(), 360.0)
    );

    // -- 6. Against the discovery paper, at its epoch, in its elements ----
    let at = ctx.propagate(
        std::slice::from_ref(&result.orbit),
        &[Epoch::from_mjd_tdb(PAPER_EPOCH)],
        &config,
    )?;
    let at = &at.states[0];
    assert!(at.origin == Origin::SSB && at.frame == Frame::EclipticJ2000);
    let state: [f64; 6] = std::array::from_fn(|i| {
        if i < 3 {
            at.position[i]
        } else {
            at.velocity[i - 3]
        }
    });
    let cov = at
        .joint
        .as_ref()
        .expect("the propagated state carries a joint")
        .state_block();

    let barycentric = |s6: [f64; 6]| -> [f64; 7] {
        let u = elements([s6[0], s6[1], s6[2]], [s6[3], s6[4], s6[5]]);
        [
            u[0],
            u[1],
            u[2].to_degrees(),
            pymod(u[3].to_degrees(), 360.0),
            pymod(u[4].to_degrees(), 360.0),
            pymod(u[5].to_degrees(), 360.0),
            u[0] * (1.0 - u[1]),
        ]
    };
    let mut jac = [[0.0_f64; 6]; 7];
    for n in 0..6 {
        let h = 1e-7 * state[n].abs().max(if n < 3 { 1e-3 } else { 1e-5 });
        let mut plus = state;
        let mut minus = state;
        plus[n] += h;
        minus[n] -= h;
        let (bp, bm) = (barycentric(plus), barycentric(minus));
        for k in 0..7 {
            let mut d = bp[k] - bm[k];
            if (3..6).contains(&k) {
                d = pymod(d + 180.0, 360.0) - 180.0;
            }
            jac[k][n] = d / (2.0 * h);
        }
    }
    let ours = barycentric(state);
    let ours_sigma: Vec<f64> = (0..7)
        .map(|k| {
            let mut quad = 0.0;
            for c in 0..6 {
                let mut jc = 0.0;
                for r in 0..6 {
                    jc += jac[k][r] * cov[r][c];
                }
                quad += jc * jac[k][c];
            }
            f64::sqrt(quad)
        })
        .collect();
    println!(
        "Barycentric ecliptic elements at MJD {PAPER_EPOCH} TDB (the paper's epoch), against its Table 2:"
    );
    println!("  (the paper's a, e, q, i uncertainties are delta-chi^2 = 1 profile ranges)");
    let labels = [
        "a",
        "e",
        "i",
        "node",
        "arg. perihelion",
        "mean anomaly",
        "q",
    ];
    for k in 0..7 {
        let (o, so, p) = (ours[k], ours_sigma[k], PAPER[k]);
        let (s_dn, s_up) = PAPER_SIGMA[k];
        let mut d = o - p;
        if (3..6).contains(&k) {
            d = pymod(d + 180.0, 360.0) - 180.0;
        }
        let sp = if d > 0.0 { s_up } else { s_dn };
        println!(
            "  {:16} {:>12} +/- {}  paper {} +{}/-{}  difference {:+.2} of our sigma, {:+.1} of the paper's",
            labels[k],
            fmt(o, so),
            sci(so, 1),
            g7(p),
            sci(s_up, 1),
            sci(s_dn, 1),
            d / so,
            d / sp
        );
    }

    // -- 7. How far the orbit can be followed -----------------------------
    let sig: Vec<f64> = path
        .states
        .iter()
        .map(|s| {
            let b = s
                .joint
                .as_ref()
                .expect("the propagated state carries a joint")
                .state_block();
            (b[0][0] + b[1][1] + b[2][2]).sqrt()
        })
        .collect();
    println!("\n1-sigma position uncertainty (first order, nearest 2-year sample):");
    for target in [
        t[0],
        -250.0 * 365.25 + 61200.0,
        -100.0 * 365.25 + 61200.0,
        61200.0,
        100.0 * 365.25 + 61200.0,
        250.0 * 365.25 + 61200.0,
        t[n_len - 1],
    ] {
        let k = nearest(target);
        let year = 2000.0 + (t[k] - 51544.5) / 365.25;
        println!(
            "  {year:7.1} (MJD {:8.0}): {:>12} km ({:.4} au) at {:.1} au",
            t[k],
            commas(sig[k] * AU_KM),
            sig[k],
            norm(x[k])
        );
    }
    Ok(())
}
// empyrean:snippet:end
