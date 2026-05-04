# Script conventions

Every script in this repo follows the same shape so a reader can move
between scenarios without re-orienting. This document is the spec.

## File layout

```python
"""<title>: <one-line subtitle>.

Reproduces the <id> explore-mode scenario from
https://empyrean-dynamics.com/explore/<id>.

Run:
    pip install empyrean
    python <name>.py

What it does:
    1. <step>
    2. <step>
    3. <step>

Authoritative cross-checks (printed inline):
    - <reference value> (<source>)
    - <reference value> (<source>)
"""
from __future__ import annotations

import empyrean
from empyrean import <minimal public-API surface>


def main() -> None:
    empyrean.initialize()

    # ── 1. <step heading> ────────────────────────────────────────
    ...

    # ── 2. <step heading> ────────────────────────────────────────
    ...


if __name__ == "__main__":
    main()
```

## Rules

1. **Public API only.** Every import is from `empyrean` or a stdlib /
   widely-used scientific dependency (`numpy`). No `_empyrean_rs` /
   `empyrean.internal.*` / private-module reaches.

2. **`empyrean.initialize()` at the top of `main()`.** This downloads
   SPICE kernels on first use into the XDG cache. Without it the
   propagator can't find DE440 and a fresh-machine run will trip on
   the first call.

3. **Inputs from public sources.** No hand-coded states. Use
   `empyrean.query_observations(...)` (MPC astrometry),
   `empyrean.query_sbdb(...)` (JPL SBDB elements + covariance), or
   manifest published values inline with a comment citing the source.

4. **Headline numbers print as a smoke test.** The script's
   final-section `print(...)` lines double as the manual test:
   eyeball the close-approach distance, IP, B-plane geometry against
   the inline `Reference (...)` lines. CI will eventually pin these
   to the spielberg fixtures (see issue empyrean-c368).

5. **Reference values cited inline.** Every quantitative reference
   value appears next to the corresponding script output, prefixed by
   `Reference (...)` plus the source — JPL CAD, JPL Sentry, JPL SBDB,
   or a paper citation (Borovička+ 2010, Farnocchia 2021, etc.).

6. **No platform / API references.** Scripts are reproducible from
   `pip install empyrean` against public data. Don't say "our API",
   "the platform", "this app." Say what the toolkit does:
   `empyrean.determine(...)`, `empyrean.propagate(...)`.

7. **Step-numbered comment dividers.** Use Unicode box-drawing
   `# ── 1. <heading> ─────────────────────` so the script reads as
   a guided walkthrough. The numbered step list in the docstring
   corresponds 1:1 with these dividers.

## Adding a new scenario

1. Mirror the spielberg `src/data/scenarios/<id>.ts` fixture — the
   numbers should match what the explore-mode panel shows.
2. Build the script following the layout above.
3. Add an entry to `README.md`'s Scripts table with both the script
   link and a `docs/scenarios/<id>.md` link.
4. Write `docs/scenarios/<id>.md` covering: scientific background,
   data sources, expected output, comparison to authoritative
   reference values.
5. Open a PR.

## Reference values: where they come from

| Source | What it gives | When to use |
|---|---|---|
| **JPL Horizons** | Reference ephemeris for a known object | Cross-check propagated states |
| **JPL CAD** (close-approach DB) | Nominal close-approach distance + epoch | Cross-check periapsis events |
| **JPL Sentry** | Published impact-probability tables | Cross-check possible-impact events |
| **JPL SBDB** | Orbital elements + 6×6 covariance + non-grav | Source of truth for propagation initial conditions |
| **MPC** | Astrometric observations | Source of truth for orbit-determination input |
| **Published papers** | Yarkovsky coefficients, capture-episode bounds, atmospheric-entry timing | Cited inline in the script's docstring + alongside corresponding `print(...)` |
