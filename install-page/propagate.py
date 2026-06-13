"""Propagate an orbit forward with full uncertainty + event detection.

Reproducer for the "Propagate an Orbit" section of
https://empyrean-dynamics.com/install. The marked region is what the
install page shows; the rest is just the entry point that makes this
runnable as `python install-page/propagate.py`.
"""

from __future__ import annotations


def main() -> None:
    # spielberg:snippet:start
    import empyrean
    from empyrean import Epochs, TimeScale, UncertaintyMethod

    empyrean.download_data()
    empyrean.initialize()

    orbits = empyrean.query_sbdb(["Apophis"])
    epochs = Epochs.from_kwargs(mjd=[65000.0], scale=TimeScale.TDB)

    result = empyrean.propagate(
        orbits,
        epochs,
        uncertainty_method=UncertaintyMethod.SECOND_ORDER,
    )

    for i in range(len(result.events.summary)):
        ev = result.events.summary
        print(
            f"{ev.event_type.to_pylist()[i]:25s} "
            f"{ev.body.to_pylist()[i]:8s} "
            f"MJD {ev.epoch.to_numpy()[i]:.2f}"
        )

    # Typed event tables for specific categories
    print(f"Earth CA: {result.events.periapses.distance_km.to_numpy()[0]:.0f} km")

    # Save everything to a directory of Parquet files
    result.to_dir("apophis_2029/")
    # spielberg:snippet:end


if __name__ == "__main__":
    main()
