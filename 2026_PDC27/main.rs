//! 2026 PDC27: replaying a planetary-defense exercise, method by method.
//!
//! Rust twin of `2026_PDC27/main.py`. Reproduces the 2026pdc27
//! explore-mode scenario from
//! <https://empyrean-dynamics.com/explore/2026pdc27>.
//!
//! **2026 PDC27 is a fictional asteroid**: the hypothetical-impact
//! exercise object of the IAA 2027 Planetary Defense Conference.
//! "This is only an exercise." (JPL CNEOS)
//!
//! Run (five fits, each with a 1000-sample Monte Carlo):
//! ```bash
//! cargo run --release --bin pdc27
//! ```

// empyrean:snippet:start
use empyrean::{Context, Epoch, ODConfig, Origin, SigmaPolicy, UncertaintyMethod, WeightingConfig};

// The exercise's 52 synthetic observations, transcribed field for field from
// the ADES XML that NASA/JPL CNEOS released on 2026-08-01 (Epoch 1). Download
// https://raw.githubusercontent.com/Empyrean-Dynamics/empyrean-scenarios/main/2026_PDC27/astrometry.psv
// and save it as astrometry.psv in the directory you run from.
const ASTROMETRY: [&str; 2] = ["astrometry.psv", "2026_PDC27/astrometry.psv"];

// The exercise's published impact-probability checkpoints for 2038-07-10, from
// the NASA/JPL CNEOS PDC27 exercise timeline (https://cneos.jpl.nasa.gov/pd/cs/pdc27/)
// and the IAWN potential impact notifications of 2026-07-15 and 2026-08-01:
// 0.1% on July 8, 16% on July 12 (after the precoveries), 19% at Epoch 1.
// Reference values only; nothing here is fitted to them.
const PUBLISHED: [(&str, f64); 3] = [
    ("2026-07-08", 0.001),
    ("2026-07-12", 0.16),
    ("2026-07-31", 0.19),
];
// The six nights of Rubin Observatory precovery images in the exercise's
// timeline (CNEOS PDC27 Epoch-1 data). The exercise's astronomers found them
// in the Rubin archive on PRECOVERY_KNOWN, so they join the fit on that date
// and not on the nights they were taken.
const PRECOVERY_NIGHTS: [&str; 6] = [
    "2026-05-11",
    "2026-05-17",
    "2026-05-23",
    "2026-06-04",
    "2026-06-10",
    "2026-06-16",
];
const PRECOVERY_KNOWN: &str = "2026-07-12";
// The knowledge dates replayed: the arcs of July 8, 10, 11 and 12 and the
// last night of Epoch 1.
const KNOWLEDGE_DATES: [&str; 5] = [
    "2026-07-08",
    "2026-07-10",
    "2026-07-11",
    "2026-07-12",
    "2026-07-31",
];
const N_SAMPLES: usize = 1000;
const Z95: f64 = 1.96;

/// The 95% Wilson score interval for hits out of n samples.
fn wilson(hits: u64, n: u64) -> (f64, f64) {
    let n = n as f64;
    let p = hits as f64 / n;
    let denom = 1.0 + Z95 * Z95 / n;
    let centre = (p + Z95 * Z95 / (2.0 * n)) / denom;
    let half = Z95 * (p * (1.0 - p) / n + Z95 * Z95 / (4.0 * n * n)).sqrt() / denom;
    (centre - half, centre + half)
}

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;

    let path = ASTROMETRY
        .iter()
        .find(|p| std::path::Path::new(p).exists())
        .expect("astrometry.psv not found");
    let obs = ctx.read_ades(path)?;
    println!("{} synthetic observations (JPL CNEOS, Epoch 1)", obs.len());

    // The file states per-observation sigmas (0.1"/0.2") and these are
    // the exercise's truth model, so honor them instead of survey floors.
    let stated_sigmas = ODConfig {
        weighting: WeightingConfig {
            sigma_policy: Some(SigmaPolicy::DefaultOnly),
            additional_layers: Vec::new(),
            ..Default::default()
        },
        ..Default::default()
    };

    let all: Vec<empyrean::Observation> = obs.iter().collect();
    let mut nights: Vec<String> = all.iter().map(|o| o.obs_time[..10].to_string()).collect();
    nights.sort();
    nights.dedup();
    assert!(
        KNOWLEDGE_DATES
            .iter()
            .all(|d| nights.iter().any(|n| n == d)),
        "a knowledge date has no observations"
    );
    let end_epoch = Epoch::from_mjd_tdb(65625.0); // 2038-07-20

    println!(
        "\nknowledge date  n_obs     linear  2nd-order       auto  Monte Carlo hits/N  95% Wilson interval   published (CNEOS/IAWN)"
    );
    let mut last = None;
    for night in KNOWLEDGE_DATES {
        // Knowledge set: apparition nights through `night`, plus the
        // precovery nights once they were found (2026-07-12), exactly
        // as the exercise's astronomers received the data.
        let kept: Vec<empyrean::Observation> = all
            .iter()
            .filter(|o| {
                let n = &o.obs_time[..10];
                if PRECOVERY_NIGHTS.contains(&n) {
                    night >= PRECOVERY_KNOWN
                } else {
                    n <= night
                }
            })
            .cloned()
            .collect();
        let arc = empyrean::Observations::from_array(&kept)?;
        let fit = match ctx.determine(&arc, None, &stated_sigmas) {
            Ok(results) => match results.into_single() {
                Ok(fit) => fit,
                Err(_) => {
                    println!("{night}    {:3}   (no converged solution)", kept.len());
                    continue;
                }
            },
            Err(_) => {
                println!("{night}    {:3}   (no converged solution)", kept.len());
                continue;
            }
        };
        let ips = ctx.compute_impact_probabilities(
            std::slice::from_ref(&fit.orbit),
            end_epoch,
            &[
                UncertaintyMethod::FirstOrder,
                UncertaintyMethod::SecondOrder,
                UncertaintyMethod::auto(),
                UncertaintyMethod::MonteCarlo {
                    n_samples: N_SAMPLES,
                    seed: Some(42),
                },
            ],
            &[Origin::Earth],
        )?;
        let find = |pred: fn(&UncertaintyMethod) -> bool| ips.iter().find(|ip| pred(&ip.method));
        let lin = find(|m| matches!(m, UncertaintyMethod::FirstOrder));
        let snd = find(|m| matches!(m, UncertaintyMethod::SecondOrder));
        let auto = find(|m| matches!(m, UncertaintyMethod::Auto { .. }));
        let mc = find(|m| matches!(m, UncertaintyMethod::MonteCarlo { .. }));
        if let (Some(lin), Some(snd), Some(auto), Some(mc)) = (lin, snd, auto, mc) {
            // AUTO's answer is its resolved rung: AGM when it fired,
            // else second-order, else linear.
            let ip_auto = if auto.ip_agm.is_finite() {
                auto.ip_agm
            } else if auto.ip_second_order.is_finite() {
                auto.ip_second_order
            } else {
                auto.ip_linear
            };
            assert!(
                mc.mc_n_samples > 0,
                "the Monte Carlo row carries no samples"
            );
            assert!((mc.ip_mc - mc.mc_n_impacts as f64 / mc.mc_n_samples as f64).abs() < 1e-12);
            let (lo, hi) = wilson(mc.mc_n_impacts, mc.mc_n_samples);
            let pub_note = PUBLISHED
                .iter()
                .find(|(d, _)| *d == night)
                .map(|(_, p)| format!("   {p:.3}"))
                .unwrap_or_default();
            println!(
                "{night}    {:3}  {:9.5}  {:9.5}  {ip_auto:9.5}  {:5}/{}       [{lo:.4}, {hi:.4}]{pub_note}",
                kept.len(),
                lin.ip_linear,
                snd.ip_second_order,
                mc.mc_n_impacts,
                mc.mc_n_samples,
            );
            last = Some((
                night,
                kept.len(),
                lin.ip_linear,
                snd.ip_second_order,
                ip_auto,
                mc.mc_n_impacts,
                mc.mc_n_samples,
                lo,
                hi,
            ));
        }
    }

    let (night, n_obs, ip_lin, ip_2nd, ip_auto, hits, n_mc, lo, hi) =
        last.expect("at least one converged fit");
    println!(
        "\nEpoch 1 ({night}, {n_obs} observations), impact probability for 2038-07-10 by method:"
    );
    println!("  linear        {ip_lin:.5}");
    println!("  second order  {ip_2nd:.5}");
    println!("  auto          {ip_auto:.5}");
    println!(
        "  Monte Carlo   {hits}/{n_mc} = {:.4}, 95% Wilson interval [{lo:.4}, {hi:.4}]",
        hits as f64 / n_mc as f64
    );
    let published = PUBLISHED
        .iter()
        .find(|(d, _)| *d == night)
        .map(|(_, p)| *p)
        .expect("a published checkpoint");
    println!("  published     {published:.3} (CNEOS / IAWN 2026-08-01)");

    Ok(())
}
// empyrean:snippet:end
