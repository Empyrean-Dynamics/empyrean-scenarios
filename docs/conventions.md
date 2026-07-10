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
   to golden fixtures.

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

1. Match the corresponding explore-mode scenario on
   empyrean-dynamics.com — the numbers should agree with what the
   panel shows.
2. Create a per-object directory at the repo root, named for the
   object's full canonical designation: `<number>_<Name>` for named
   asteroids and comets (e.g. `99942_Apophis`,
   `67P_Churyumov-Gerasimenko`), or the provisional designation
   alone for unnamed objects (e.g. `2024_YR4`). Put three files
   inside:
   - `<dirname>/main.py` — Python implementation
   - `<dirname>/main.rs` — Rust twin
   - `<dirname>/README.md` — scientific background, data sources,
     expected output, comparison to authoritative reference values
3. Add a `[[bin]]` entry in the top-level `Cargo.toml` pointing at
   `<dirname>/main.rs` with a short, CLI-friendly `name` (e.g.
   `apophis`, `yr4`).
4. Add the new directory to the top-level `Cargo.toml`'s `include`
   list and to the top-level `README.md`'s Scripts table.
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

## Version pinning

Both manifests pin the published `empyrean` release **exactly** —
`empyrean==X.Y.Z` in `pyproject.toml` and `empyrean = "=X.Y.Z"` in
`Cargo.toml` (cargo's bare `"X.Y.Z"` is a caret range and would float
across patch releases).

The pin, every scenario's "Expected output (rough)" block, and any
version-coupled numbers in the READMEs form one atomic artifact:
they are updated together, in a single commit, per release. Bumping
the pin means re-running every scenario in both languages against the
new release and regenerating the blocks — that re-run is the upgrade
validation, and diffs in the blocks are the changelog of what the
release changed for these objects. Never bump the pin without
refreshing the blocks, and never use a version range: a fresh clone
must print the committed numbers (modulo live-astrometry drift, which
the blocks are marked "rough" for).
