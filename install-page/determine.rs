//! Orbit determination: IOD + differential correction + outlier rejection.
//!
//! Reproducer for the "Determine an Orbit" section of
//! <https://empyrean-dynamics.com/install>. Reads ADES PSV from a sample
//! file in this directory, fits an orbit, then inspects and refines that
//! same fit — each step hands its `orbit` to the next.

use empyrean::Context;

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    let psv_path = concat!(env!("CARGO_MANIFEST_DIR"), "/install-page/observations.psv");
    let psv = std::fs::read_to_string(psv_path).expect("sample observations.psv not found");

    // empyrean:snippet:start
    use empyrean::ODConfig;

    let cfg = ODConfig::default();

    // Read ADES PSV observations (file path or PSV string). The returned
    // set carries both ADES tables (optical + radar); the Python twin
    // unpacks the (optical, radar) tuple and folds the radar back in.
    let obs = ctx.read_ades(&psv)?;

    // Full pipeline: IOD + differential correction + outlier rejection.
    // Any <radar> block read above rides along inside `obs`.
    let fit = ctx.determine(&obs, None, &cfg)?.into_single()?;
    let s = &fit.summary;
    println!(
        "converged={}  RMS RA\u{00B7}cos(d) {:.2}\"  Dec {:.2}\"",
        fit.converged, s.rms_ra_arcsec, s.rms_dec_arcsec
    );

    // `fit.orbit` is a re-feedable Orbit (state + covariance + non-grav).
    // Evaluate its own residuals against the arc — no fitting:
    let eval = ctx.evaluate(&fit.orbit, &obs, &cfg)?;
    println!("post-fit chi2 = {:.1}", eval.summary.chi2);

    // Refine the fit with a Bayesian prior (the fitted covariance is the
    // prior). The refined result is itself re-feedable into the next refine.
    let refined = ctx.refine(&fit.orbit, &obs, &cfg)?;
    println!("refined: converged={}", refined.converged);
    // empyrean:snippet:end
    let _ = refined;
    Ok(())
}
