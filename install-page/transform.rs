//! Transform coordinates between representations / frames / origins.
//!
//! Reproducer for the "Transform Coordinates" section of
//! <https://empyrean-dynamics.com/install>.

use empyrean::{Context, query_sbdb};

fn main() -> empyrean::Result<()> {
    let ctx = Context::from_data_dir(None)?;
    let batch = query_sbdb(&["Apophis"], None)?;
    let orbit = batch.orbits.into_iter().next().expect("not found");

    // empyrean:snippet:start
    use empyrean::{Frame, Origin, Representation};

    // Cometary -> Cartesian (same frame, same origin). transform_orbits moves
    // the state AND its packed-joint covariance through the Jacobian;
    // transform_coordinates_single handles bare states and refuses a
    // covariance-bearing input (a queried orbit carries one).
    let cart = ctx.transform_orbits(
        std::slice::from_ref(&orbit),
        Representation::Cartesian,
        orbit.state.frame,
        orbit.state.origin,
    )?;

    // Full transform: representation + frame + origin
    let kep = ctx.transform_orbits(
        std::slice::from_ref(&orbit),
        Representation::Keplerian,
        Frame::ICRF,
        Origin::Earth,
    )?;
    // empyrean:snippet:end
    let _ = (cart, kep);
    Ok(())
}
