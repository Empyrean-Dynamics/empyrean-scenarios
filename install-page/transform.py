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

    # spielberg:snippet:start
    from empyrean import CartesianCoordinates, KeplerianCoordinates

    # Cometary -> Cartesian (same frame, same origin)
    cart = empyrean.transform_coordinates(orbits.coordinates, CartesianCoordinates)

    # Full transform: representation + frame + origin
    kep = empyrean.transform_coordinates(
        orbits.coordinates,
        KeplerianCoordinates,
        frame=Frame.ICRF,
        origin=Origin.EARTH,
    )
    # spielberg:snippet:end
    _ = (cart, kep)


if __name__ == "__main__":
    main()
