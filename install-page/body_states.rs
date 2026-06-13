//! Body states: planetary / lunar / asteroid positions from SPK kernels.
//!
//! Reproducer for the "Body States" section of
//! <https://empyrean-dynamics.com/install>.

fn main() -> empyrean::Result<()> {
    use empyrean::Context;
    let ctx = Context::from_data_dir(None)?;

    // spielberg:snippet:start
    use empyrean::{Epoch, Frame, Origin};

    let states = ctx.get_states(
        Origin::Earth, // target
        Origin::SSB,   // center
        &[Epoch::from_mjd_tdb(60200.0), Epoch::from_mjd_tdb(60201.0)],
        Frame::EclipticJ2000,
    )?;
    // spielberg:snippet:end
    println!("states: {}", states.len());
    Ok(())
}
