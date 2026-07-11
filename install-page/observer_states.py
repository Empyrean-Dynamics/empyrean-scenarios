"""Observer states: ground-based MPC observatories by code.

Reproducer for the "Observer States" section of
https://empyrean-dynamics.com/install.
"""

from __future__ import annotations

import empyrean
from empyrean import Epochs, TimeScale


def main() -> None:
    empyrean.initialize()

    # empyrean:snippet:start
    observers = empyrean.Observers.from_codes(
        obs_codes=["W84", "F51"],
        epochs=Epochs.from_kwargs(mjd=[60200.0, 60201.0], scale=TimeScale.TDB),
    )
    # 4 rows: cross product of codes x epochs, ICRF/SSB positions + velocities
    # empyrean:snippet:end
    print(f"observers: {len(observers)} rows")


if __name__ == "__main__":
    main()
