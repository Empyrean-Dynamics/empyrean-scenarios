"""Query JPL: SBDB elements, Horizons reference, MPC astrometry.

Reproducer for the "Query JPL" section of
https://empyrean-dynamics.com/install.
"""

from __future__ import annotations

import empyrean


def main() -> None:
    empyrean.initialize()

    # spielberg:snippet:start
    # SBDB: elements + covariance + non-grav + photometry
    orbits = empyrean.query_sbdb(["Apophis", "Eros"])

    # Horizons: reference ephemeris for validation
    eph_ref = empyrean.query_horizons(["Apophis"], observer="W84", epochs=[60200.0])

    # MPC: astrometric observations in ADES
    obs = empyrean.query_observations(["Apophis"])
    # spielberg:snippet:end

    print(f"SBDB:      {len(orbits)} orbits")
    print(f"Horizons:  {len(eph_ref)} ephemeris rows")
    print(f"MPC:       {len(obs)} observations")


if __name__ == "__main__":
    main()
