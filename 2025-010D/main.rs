//! 2025-010D: a Falcon 9 second stage → community-driven astrometry → lunar impact.
//!
//! Rust twin of `2025-010D/main.py`. Reproduces the 2025010d explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/2025010d>.
//!
//! Run:
//! ```bash
//! cargo run --release --bin falcon9
//! ```

// empyrean:snippet:start
use empyrean::{
    Context, Epoch, ODConfig, Origin, ParamDisposition, SolveFor, SolveForParams, TimeScale,
    mjd_to_iso,
};
use empyrean::{OriginPolicy, WeightingConfig, WeightingPreset};

// The 402 public observations, in ADES PSV, from Bill Gray's Project Pluto pages
// (public domain; the MPC does not distribute this object's astrometry). Download
// https://raw.githubusercontent.com/Empyrean-Dynamics/empyrean-scenarios/main/2025-010D/astrometry.psv
// and save it as astrometry.psv in the directory you run from.
const ASTROMETRY: [&str; 2] = ["astrometry.psv", "2025-010D/astrometry.psv"];
// Gray's fit to the same 74 public observations (Project Pluto pseudo-MPEC 25010d_new).
const GRAY_AMR: f64 = 0.0079; // m^2/kg
const GRAY_AMR_SIGMA: f64 = 0.0017;
// The crater NASA's Lunar Reconnaissance Orbiter imaged on 2026-08-11/12 (NASA,
// "NASA's LRO Images Falcon 9 Crater on Moon", science.nasa.gov), and Gray's final
// prediction of 2026-08-01 from his full record, which is not public (Project Pluto,
// https://www.projectpluto.com/25010d.htm). Selenographic degrees north and east.
const CRATER: (f64, f64) = (19.4759, 266.7138);
const GRAY_FINAL: (f64, f64) = (19.461, 266.707);
const MOON_RADIUS_KM: f64 = 1737.4; // the Moon's mean radius

/// Great-circle distance between two (lat, lon) points in degrees, on the Moon.
fn separation_km(a: (f64, f64), b: (f64, f64)) -> f64 {
    let (p1, p2) = (a.0.to_radians(), b.0.to_radians());
    let dl = (b.1 - a.1).to_radians();
    let h = ((p2 - p1) / 2.0).sin().powi(2) + p1.cos() * p2.cos() * (dl / 2.0).sin().powi(2);
    2.0 * MOON_RADIUS_KM * h.sqrt().asin()
}

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. The committed public astrometry ──────────────────────────
    // No MPC query: these 402 observations are the
    // public-domain record compiled by Project Pluto (see README).
    let obs = ctx.read_ades(
        ASTROMETRY
            .iter()
            .find(|p| std::path::Path::new(p).exists())
            .expect("astrometry.psv not found"),
    )?;
    println!(
        "{} public observations (Project Pluto, public domain)",
        obs.len()
    );

    // Final pre-impact arc: nine nights, five stations, four continents.
    let final_arc = obs.filter_by_epoch(Some(Epoch::from_mjd_utc(61222.0)), None)?;
    println!("{} in the final arc (2026-07-23 → 08-01)", final_arc.len());

    // ── 2. Geocentric fit + AMR refine ──────────────────────────────
    // EXPLICIT/Earth: heliocentric Gauss IOD is unphysical for a
    // catalogued Earth-orbiting object. The PSV carries no
    // per-observation sigmas and these community stations have no
    // survey-weighting rules, so state the residual-matched 0.3"
    // explicitly instead of inheriting the ~1.5" catalog fallback.
    let weighting = WeightingConfig {
        preset: WeightingPreset::None,
        default_sigma_arcsec: 0.3,
        ..Default::default()
    };
    let od_config = ODConfig {
        origin: OriginPolicy::Explicit(Origin::Earth),
        weighting: weighting.clone(),
        ..Default::default()
    };
    let fit = ctx.determine(&final_arc, None, &od_config)?.into_single()?;
    let s = &fit.summary;
    println!(
        "fit: chi2/dof {:.3}  RMS RA·cos(d) {:.3}\" Dec {:.3}\"  ({}/{} obs)",
        s.reduced_chi2, s.rms_ra_arcsec, s.rms_dec_arcsec, s.num_selected, s.num_obs
    );

    // AMRAT is a refine-path solve: prime the fitted orbit with an SRP
    // prior wide enough for the artsat regime (~1e-2 m²/kg, 100× any
    // asteroid) so the astrometry, not the prior, drives the fit.
    // The AMRAT prior rides the fitted orbit's packed joint (its AMRAT axis,
    // bit 4), widening the state 6x6 to 7. The removed
    // `with_srp_amrat_variance` builder is gone.
    let state6 = fit
        .orbit
        .covariance
        .as_ref()
        .expect("fit carries a state covariance joint")
        .state_block();
    let amrat_prior = prior_joint(state6, &[1.0e-4], 1 << 4);
    let primed = fit
        .orbit
        .clone()
        .with_orbit_id("2025-010D")
        .with_srp(0.008, 1.0)
        .with_covariance(amrat_prior);
    let refine_config = ODConfig {
        solve_for: SolveForParams::Explicit(SolveFor {
            amrat: ParamDisposition::Solved,
            ..Default::default()
        }),
        origin: OriginPolicy::Explicit(Origin::Earth),
        weighting,
        ..Default::default()
    };
    let refined = ctx.refine(&primed, &final_arc, &refine_config)?;
    if let (Some(sc), Some(srp)) = (&refined.solved_covariance, &refined.orbit.srp) {
        let slot = sc.amrat_slot.expect("AMRAT slot opened by the solve");
        let sigma = sc.matrix[slot][slot].sqrt();
        println!("Fitted AMR = {:.4} ± {:.4} m²/kg", srp.amrat, sigma);
    }
    println!("Gray (same 74-obs arc): {GRAY_AMR} ± {GRAY_AMR_SIGMA} m²/kg");
    if let (Some(sc), Some(srp)) = (&refined.solved_covariance, &refined.orbit.srp) {
        let slot = sc.amrat_slot.expect("AMRAT slot opened by the solve");
        let sigma = sc.matrix[slot][slot].sqrt();
        let gap = srp.amrat - GRAY_AMR;
        println!(
            "Ours - Gray = {gap:+.4} m²/kg, {:.2} combined sigma",
            gap.abs() / sigma.hypot(GRAY_AMR_SIGMA)
        );
    }

    // ── 3. Into the Moon ────────────────────────────────────────────
    let epochs: Vec<Epoch> = (0..200)
        .map(|i| Epoch::from_mjd_tdb(61250.0 + 0.05 * i as f64))
        .collect();
    let prop = ctx.propagate(
        std::slice::from_ref(&refined.orbit),
        &epochs,
        &empyrean::PropagationConfig::default(),
    )?;
    let impacts: Vec<_> = prop
        .events
        .iter()
        .filter(|e| e.event_type == "impact" && e.body == Some(Origin::Moon))
        .collect();
    assert!(impacts.len() == 1, "expected one lunar impact");
    let mut ours = (0.0, 0.0);
    for ev in impacts {
        let iso = mjd_to_iso(ev.epoch.mjd_utc()?, TimeScale::UTC)?;
        // To 0.01 s: the fit's timing is no better than that.
        let (head, frac) = iso
            .trim_end_matches('Z')
            .split_once('.')
            .expect("fractional seconds");
        let centis = (format!("0.{frac}").parse::<f64>().expect("fraction") * 100.0).round() as u32;
        assert!(centis < 100);
        let iso = format!("{head}.{centis:02}Z");
        let lon = ev.impact_longitude_deg.rem_euclid(360.0);
        println!("\nPredicted lunar impact (empyrean): {iso}");
        println!(
            "  at {:.3}°N {:.3}°E (selenographic)",
            ev.impact_latitude_deg, lon
        );
        ours = (ev.impact_latitude_deg, lon);
    }
    println!("Gray (74-obs arc):  2026-08-05T06:35:42.45Z at 19.577°N 266.630°E");
    println!("JPL #GA1A2/21:      2026-08-05T06:35:40Z ± 9 s at 19.507°N 266.7°E");
    println!("Confirmed:          2026-08-05 ~06:35 UTC near crater Einstein");
    println!(
        "\nScored against the crater LRO imaged ({}°N {}°E), great circle on a {} km Moon:",
        CRATER.0, CRATER.1, MOON_RADIUS_KM
    );
    println!(
        "  empyrean (this fit, public 74-obs arc)  {:.2} km",
        separation_km(ours, CRATER)
    );
    println!(
        "  Gray's final prediction (all data)      {:.2} km",
        separation_km(GRAY_FINAL, CRATER)
    );

    // ── 4. Why the record is fit per arc ────────────────────────────
    // Score the final-arc orbit against the WHOLE public record: the
    // residual RMS grows through two lunar encounters and a tumbling
    // body whose effective area changed between arcs (Gray 2026;
    // Campbell et al. 2026), consistent with the per-arc solutions
    // Project Pluto published.
    // evaluate (unlike determine) runs no rejection pass, so it refuses an
    // observation whose station the engine cannot resolve (0.11.0 removed the
    // old silent fallback). Drop any such unregistered community station
    // explicitly (named by the engine's own refusal) before scoring.
    let mut scorable: Vec<_> = obs.iter().collect();
    let full = loop {
        let subset = empyrean::Observations::from_array(&scorable)?;
        match ctx.evaluate(&refined.orbit, &subset, &od_config) {
            Ok(ev) => break ev,
            Err(e) => {
                let code = e
                    .to_string()
                    .split_once("unknown observatory code \"")
                    .and_then(|(_, rest)| rest.split_once('"'))
                    .map(|(c, _)| c.to_string());
                match code {
                    Some(c) => {
                        scorable.retain(|o| o.obs_code != c);
                        println!("(dropped unregistered community station {c} from scoring)");
                    }
                    None => return Err(e),
                }
            }
        }
    };
    // Per-arc ladder, same statistic as the Python twin: total angular
    // RMS sqrt(mean(ra_res^2 + dec_res^2)) over each arc's rows,
    // NaN-skipped. (The engine summary's rms_combined is the per-axis
    // quadratic mean over evaluable rows, a different convention.)
    println!("\nFinal-arc orbit scored against the full 402-obs record:");
    for (label, lo, hi) in [
        ("own arc   (2026 Jul-Aug)", 61244.0, 61300.0),
        ("Apr-May 2026", 61135.0, 61190.0),
        ("Dec 2025", 61020.0, 61040.0),
        ("Jan 2025 discovery", 60680.0, 60700.0),
    ] {
        let mut ss = 0.0_f64;
        let mut n = 0_usize;
        for r in &full.residuals {
            let ti = r.epoch.mjd_tdb()?;
            let (ra, de) = (r.ra_residual_arcsec, r.dec_residual_arcsec);
            if ti >= lo && ti < hi && ra.is_finite() && de.is_finite() {
                ss += ra * ra + de * de;
                n += 1;
            }
        }
        if n > 0 {
            println!("  {label:26} RMS {:>12.2}\"", (ss / n as f64).sqrt());
        }
    }
    println!("(Five orders of magnitude across two lunar encounters and a");
    println!(" changing tumble, consistent with the per-arc solutions");
    println!(" Project Pluto published; Gray 2026, Campbell et al. 2026.)");

    Ok(())
}

/// A block-diagonal refine prior: the fit's state 6x6 plus one diagonal prior
/// variance per parameter axis (zero cross terms). The AMRAT prior rides the
/// orbit's one packed joint now (present bit 4 of the axis table). The removed
/// `with_srp_amrat_variance` builder is gone.
fn prior_joint(
    state6: [[f64; 6]; 6],
    param_vars: &[f64],
    present_bits: u32,
) -> empyrean::PackedJoint {
    let width = 6 + param_vars.len();
    let mut full = vec![vec![0.0_f64; width]; width];
    for (i, row) in state6.iter().enumerate() {
        full[i][..6].copy_from_slice(row);
    }
    for (k, &v) in param_vars.iter().enumerate() {
        full[6 + k][6 + k] = v;
    }
    let mut tri = Vec::with_capacity(width * (width + 1) / 2);
    for (i, row) in full.iter().enumerate() {
        tri.extend_from_slice(&row[..=i]);
    }
    empyrean::PackedJoint {
        layout: empyrean::AxisLayout {
            present: present_bits,
            considered: 0,
            marginalized: 0,
        },
        width: width as u8,
        tri,
        kind: empyrean::CovarianceKind::Linear,
        quality: empyrean::JointQuality::PositiveDefinite,
        functional: empyrean::JointFunctional::State,
        provenance: empyrean::JointProvenance::Derived,
        asserted_source: None,
    }
}
// empyrean:snippet:end
