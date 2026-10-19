"""Transform coordinates between representations / frames / origins.

Reproducer for the "Transform Coordinates" section of
https://empyrean-dynamics.com/install.
"""

from __future__ import annotations

import empyrean
from empyrean import Frame, Origin


def main() -> None:
    empyrean.initialize()
    orbits = empyrean.query_sbdb(["Apophis"])

    # empyrean:snippet:start
    from empyrean import CartesianOrbits, KeplerianOrbits

    # Cometary -> Cartesian (same frame, same origin). transform_orbits moves
    # the state AND its packed-joint covariance through the Jacobian;
    # transform_coordinates handles bare states and refuses a
    # covariance-bearing input (a queried orbit carries one).
    cart = empyrean.transform_orbits(orbits, CartesianOrbits)

    # Full transform: representation + frame + origin
    kep = empyrean.transform_orbits(
        orbits,
        KeplerianOrbits,
        frame=Frame.ICRF,
        origin=Origin.EARTH,
    )
    # empyrean:snippet:end
    _ = (cart, kep)


if __name__ == "__main__":
    main()
