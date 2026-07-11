//! Initialize empyrean: load SPICE kernels via the Context.
//!
//! Reproducer for the "Initialize & Data" section of
//! <https://empyrean-dynamics.com/install>. The marked region below is
//! the literal snippet shown in the install page; the surrounding
//! `fn main` is what makes the file runnable as a standalone binary.
//!
//! Run:
//! ```bash
//! cargo run --release --bin install-initialize
//! ```

fn main() -> empyrean::Result<()> {
    // empyrean:snippet:start
    use empyrean::{Context, Epoch, Frame, Origin};

    // Loads / downloads kernels on first run; reads cached files thereafter.
    // Override the data directory with the EMPYREAN_DATA_DIR env var.
    let ctx = Context::from_data_dir(None)?;
    // empyrean:snippet:end
    let _ = (&ctx, Epoch::from_mjd_tdb(60000.0), Frame::ICRF, Origin::SSB);
    println!("empyrean Context initialized OK");
    Ok(())
}
