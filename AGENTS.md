# AGENTS.md

Guidance for coding agents working in this repository. The repository is
the set of worked examples for the public `empyrean` package; the
`empyrean` skill (install lines in the README) is what tells an agent how to
use the package itself.

## What this repository is

- Nine scenarios, one directory per object, each shipping three
  implementations that must agree: `main.py`, `main.rs` and the executed
  notebook `main.ipynb`. Any discrepancy in the headline numbers between the
  Python and Rust twins is a bug somewhere.
- Each scenario's `README.md` carries a reference-value table with its
  sources (mostly JPL CAD, SBDB and CNEOS) and a rough expected output.
  Those tables are what a result is checked against; do not change a
  reference value without naming its source.
- Inputs are public: fetched at run time from JPL SBDB, the MPC and JPL
  CAD, or checked in beside the scenario. Everything imports only the
  public `empyrean` surface; nothing here depends on private repositories.

## Run and check

- Python: `pip install empyrean`, then `python <dir>/main.py`. Rust:
  `cargo run --release --bin <name>`. The first run downloads the kernel set
  (about 740 MB); later runs reuse the cache.
- A change to one twin is a change to all three: keep the printed banners
  identical to the precision of the arithmetic, re-execute the notebook, and
  compare against the README's reference values before and after.
- Conventions are in `docs/conventions.md`; the README's *Conventions*
  section is the summary.

## Where things are documented

- Package docs: <https://docs.empyrean-dynamics.com> (plain text:
  `/llms.txt`).
- Validation of each release against JPL Horizons, ASSIST and the other
  channels: <https://validation.empyrean-dynamics.com/latest/validation_report.html>.
- Scenario problems or proposals: the issue templates in this repository.
