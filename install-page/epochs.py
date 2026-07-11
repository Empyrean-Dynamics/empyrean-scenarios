"""Epochs: explicit time scales, Astropy interop, evenly spaced grids.

Reproducer for the "Epochs" section of
https://empyrean-dynamics.com/install.
"""

from __future__ import annotations

import empyrean
from empyrean import Epochs, TimeScale


def main() -> None:
    empyrean.initialize()
    orbits = empyrean.query_sbdb(["Apophis"])

    # empyrean:snippet:start
    from astropy.time import Time

    # Explicit scale at construction
    epoch_utc = Epochs.from_kwargs(mjd=[60200.0], scale=TimeScale.UTC)
    epoch_tdb = epoch_utc.to_tdb()

    # Offsets from orbit epochs
    epochs = Epochs.from_orbits(orbits, dt=[30, 60, 90])

    # Evenly spaced grid
    epochs = Epochs.linspace(60200.0, 60565.0, num=100)

    # From Astropy
    epochs = Epochs.from_astropy(Time(["2029-04-13T21:46:00"], scale="utc"))
    # empyrean:snippet:end
    _ = (epoch_tdb, epochs)


if __name__ == "__main__":
    main()
