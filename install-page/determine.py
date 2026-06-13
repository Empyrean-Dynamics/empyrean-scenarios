"""Orbit determination: IOD + differential correction + outlier rejection.

Reproducer for the "Determine an Orbit" section of
https://empyrean-dynamics.com/install. Reads ADES PSV from a sample file in
this directory, fits an orbit, then inspects and refines that same fit —
each step hands its ``orbit`` to the next.
"""

from __future__ import annotations

from pathlib import Path

import empyrean

PSV = str(Path(__file__).parent / "observations.psv")


def main() -> None:
    empyrean.initialize()

    # spielberg:snippet:start
    # Read ADES PSV observations (file path or PSV string)
    obs = empyrean.read_ades(PSV)

    # Full pipeline: IOD + differential correction + outlier rejection
    fit = empyrean.determine(obs)
    print(
        f"converged={fit.converged}  "
        f'RMS RA·cos(d) {fit.summary.rms_ra_arcsec:.2f}" '
        f'Dec {fit.summary.rms_dec_arcsec:.2f}"'
    )

    # `fit.orbit` is a re-feedable orbit (state + covariance + non-grav).
    # Evaluate its own residuals against the arc — no fitting:
    ev = empyrean.evaluate(fit.orbit, obs)
    print(f"post-fit chi2 = {ev.summary.chi2:.1f}")

    # Refine the fit with a Bayesian prior (the fitted covariance is the
    # prior). The refined result is itself re-feedable into the next refine.
    refined = empyrean.refine(fit.orbit, obs)
    print(f"refined: converged={refined.converged}")
    # spielberg:snippet:end
    _ = refined


if __name__ == "__main__":
    main()
