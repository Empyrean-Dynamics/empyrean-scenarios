"""Body states: planetary / lunar / asteroid positions from SPK kernels.

Reproducer for the "Body States" section of
https://empyrean-dynamics.com/install.
"""

from __future__ import annotations

import empyrean
from empyrean import Epochs, Frame, Origin, TimeScale


def main() -> None:
    empyrean.initialize()

    # empyrean:snippet:start
    states = empyrean.get_states(
        target=Origin.EARTH,
        center=Origin.SSB,
        epochs=Epochs.from_kwargs(mjd=[60200.0, 60201.0], scale=TimeScale.TDB),
        frame=Frame.ECLIPTICJ2000,
    )
    # empyrean:snippet:end
    print(f"states: {len(states)}")


if __name__ == "__main__":
    main()
