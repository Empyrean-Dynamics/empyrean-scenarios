//! 2025-010D: a Falcon 9 second stage → community-driven astrometry → lunar impact.
//!
//! Rust twin of `2025-010D/main.py`. Reproduces the 25010d explore-mode
//! scenario from <https://empyrean-dynamics.com/explore/25010d>.
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

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    // ── 1. The committed public astrometry ──────────────────────────
    // No MPC query: astrometry of recognized artificial satellites is
    // removed from public MPC holdings. These 402 observations are the
    // public-domain record compiled by Project Pluto (see README).
    let obs = ctx.read_ades("2025-010D/astrometry.psv")?;
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
    let primed = fit
        .orbit
        .clone()
        .with_orbit_id("2025-010D")
        .with_srp(0.008, 1.0)
        .with_srp_amrat_variance(Some(1.0e-4));
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
    println!("Gray (same 74-obs arc): 0.0079 ± 0.0017 m²/kg");

    // ── 3. Into the Moon ────────────────────────────────────────────
    let epochs: Vec<Epoch> = (0..120)
        .map(|i| Epoch::from_mjd_tdb(65610.0 + 0.05 * i as f64))
        .collect();
    let prop = ctx.propagate(
        std::slice::from_ref(&refined.orbit),
        &epochs,
        &empyrean::PropagationConfig::default(),
    )?;
    for ev in prop
        .events
        .iter()
        .filter(|e| e.event_type == "impact" && e.body == Some(Origin::Moon))
    {
        let iso = mjd_to_iso(ev.epoch.mjd_utc()?, TimeScale::UTC)?;
        let lon = ev.impact_longitude_deg.rem_euclid(360.0);
        println!("\nPredicted lunar impact (Empyrean): {iso}");
        println!(
            "  at {:.3}°N {:.3}°E (selenographic)",
            ev.impact_latitude_deg, lon
        );
    }
    println!("Gray (74-obs arc):  2026-08-05T06:35:42.45Z at 19.577°N 266.630°E");
    println!("JPL #GA1A2/21:      2026-08-05T06:35:40Z ± 9 s at 19.507°N 266.7°E");
    println!("Confirmed:          2026-08-05 ~06:35 UTC near crater Einstein");

    // ── 4. Why the record is fit per arc ────────────────────────────
    // Score the final-arc orbit against the WHOLE public record: the
    // residual RMS grows through two lunar encounters and a tumbling
    // body whose effective area changed between arcs (Gray 2026;
    // Campbell et al. 2026) — consistent with the per-arc solutions
    // Project Pluto published.
    let own = ctx.evaluate(&refined.orbit, &final_arc, &od_config)?;
    let full = ctx.evaluate(&refined.orbit, &obs, &od_config)?;
    println!(
        "\nFinal-arc orbit scored against its own arc:   RMS {:>12.2}\"",
        own.summary.rms_combined_arcsec
    );
    println!(
        "Final-arc orbit scored against all 402 obs:   RMS {:>12.2}\"",
        full.summary.rms_combined_arcsec
    );
    println!("(Consistent with the per-arc solutions Project Pluto published;");
    println!(" Gray 2026, Campbell et al. 2026.)");

    Ok(())
}
// empyrean:snippet:end
