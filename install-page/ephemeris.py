"""Generate ephemeris: RA/Dec + photometry + local horizon for an MPC site.

Reproducer for the "Generate Ephemeris" section of
https://empyrean-dynamics.com/install. The fragment shown in the
install page assumes `orbits` is already in scope; this harness
queries SBDB first (outside the marker) so the file is runnable
end-to-end.
"""

from __future__ import annotations

import empyrean
from empyrean import Epochs, TimeScale


def main() -> None:
    empyrean.initialize()
    orbits = empyrean.query_sbdb(["Apophis"])

    # empyrean:snippet:start
    observers = empyrean.Observers.from_codes(
        obs_codes=["W84", "F51"],
        epochs=Epochs.from_kwargs(mjd=[60200.0, 60201.0], scale=TimeScale.TDB),
    )

    result = empyrean.generate_ephemeris(orbits, observers)
    eph = result.ephemeris

    print(eph.coordinates.lon.to_numpy())  # RA (degrees)
    print(eph.coordinates.lat.to_numpy())  # Dec (degrees)
    print(eph.coordinates.rho.to_numpy())  # range (AU)

    # Photometry
    print(eph.mag.to_numpy())  # apparent V-band magnitude
    print(eph.mag_sigma.to_numpy())  # 1-sigma uncertainty

    # Local horizon
    print(eph.zenith_angle.to_numpy())  # degrees from zenith
    print(eph.azimuth.to_numpy())  # degrees East of North
    # empyrean:snippet:end


if __name__ == "__main__":
    main()
