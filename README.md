<img src="docs/empyrean-scenarios-icon.png" width="140" alt="empyrean-scenarios">

# empyrean-scenarios
Runnable Rust + Python walkthroughs of the explore-mode scenarios on empyrean-dynamics.com

<a href="https://github.com/Empyrean-Dynamics/empyrean-scenarios/actions/workflows/ci.yml"><img src="https://github.com/Empyrean-Dynamics/empyrean-scenarios/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<a href="https://pypi.org/project/empyrean/"><img src="https://img.shields.io/badge/empyrean-0.10.0-1a1a2e?style=flat-square" alt="empyrean version"></a>
<br>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-BSD--3--Clause-blue.svg?style=flat-square" alt="License"></a>
<a href="https://doi.org/10.5281/zenodo.21315115"><img src="https://zenodo.org/badge/1228940802.svg" alt="DOI"></a>
<br>
<a href="https://claude.ai"><img src="https://img.shields.io/badge/Built%20with-Claude%20Code-D97757?logo=anthropic&logoColor=white&style=flat-square" alt="Built with Claude Code"></a>
<a href="https://www.empyrean-dynamics.com"><img src="https://img.shields.io/badge/Website-empyrean--dynamics.com-1a1a2e?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iMTAiLz48bGluZSB4MT0iMiIgeTE9IjEyIiB4Mj0iMjIiIHkyPSIxMiIvPjxwYXRoIGQ9Ik0xMiAyYTE1LjMgMTUuMyAwIDAgMSA0IDEwIDE1LjMgMTUuMyAwIDAgMS00IDEwIDE1LjMgMTUuMyAwIDAgMS00LTEwIDE1LjMgMTUuMyAwIDAgMSA0LTEweiIvPjwvc3ZnPg==&logoColor=white&style=flat-square" alt="Website"></a>
<a href="https://github.com/Empyrean-Dynamics"><img src="https://img.shields.io/badge/GitHub-Empyrean--Dynamics-1a1a2e?logo=github&logoColor=white&style=flat-square" alt="GitHub"></a>

---

`empyrean-scenarios` is a collection of runnable Rust binaries,
Python scripts, and executed Jupyter notebooks that reproduce the
planetary-science narratives from
[empyrean-dynamics.com/explore](https://empyrean-dynamics.com/explore)
end-to-end against the public `empyrean` toolkit. Each scenario tells
one near-Earth-object or comet story in **both** languages — same
propagator, same orbit-determination, same event-detection engine.
The two implementations cross-check each other: any divergence in
headline numbers between `cargo run --bin apophis` and
`python apophis.py` is a bug somewhere.

No hosted endpoint, no proprietary data — just `cargo add empyrean`
or `pip install empyrean` against the publicly-available astrometry
catalogues.

## Scenarios

| Scenario | What it shows | Scripts |
|---|---|---|
| [99942 Apophis](99942_Apophis/) | Optical + radar orbit determination with non-gravitational parameters, the 2029 Earth flyby, provenance-tagged covariance readback, and B-plane geometry | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](99942_Apophis/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](99942_Apophis/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](99942_Apophis/main.ipynb) |
| [2024 YR4](2024_YR4/) | Discovery-arc vs full-arc fits and how the 2032 impact probability collapses as astrometry accumulates | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2024_YR4/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2024_YR4/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2024_YR4/main.ipynb) |
| [101955 Bennu](101955_Bennu/) | Yarkovsky drift measured from optical + radar astrometry, a fitted-covariance 72-year propagation to the 2060 encounter, and covariance amplification between close approaches | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](101955_Bennu/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](101955_Bennu/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](101955_Bennu/main.ipynb) |
| [2008 TC3](2008_TC3/) | A 19-hour discovery arc fit forward to the observed atmospheric entry over Sudan | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2008_TC3/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2008_TC3/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2008_TC3/main.ipynb) |
| [2020 CD3](2020_CD3/) | Temporary lunar-distance capture ("mini-moon") event detection, with and without non-gravitational forces | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2020_CD3/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2020_CD3/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2020_CD3/main.ipynb) |
| [2009 BD](2009_BD/) | Solar-radiation-pressure area-to-mass ratio measured directly from the astrometry of a metre-scale asteroid | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2009_BD/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2009_BD/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2009_BD/main.ipynb) |
| [67P/Churyumov–Gerasimenko](67P_Churyumov-Gerasimenko/) | Cometary water-sublimation outgassing and its cumulative along-track displacement | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](67P_Churyumov-Gerasimenko/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](67P_Churyumov-Gerasimenko/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](67P_Churyumov-Gerasimenko/main.ipynb) |
| [2025-010D](2025-010D/) | A Falcon 9 second stage fit from public-domain community-driven astrometry — geocentric OD, a rocket-body area-to-mass ratio, and the 2026 lunar impact predicted to seconds | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2025-010D/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2025-010D/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2025-010D/main.ipynb) |
| [2026 PDC27](2026_PDC27/) | The (fictional) IAA PDC 2027 exercise asteroid — the knowledge-timeline replay of its impact probability under four uncertainty methods | [![py](https://img.shields.io/badge/py-3776AB?logo=python&logoColor=white&style=flat-square)](2026_PDC27/main.py) [![rs](https://img.shields.io/badge/rs-B7410E?logo=rust&logoColor=white&style=flat-square)](2026_PDC27/main.rs) [![ipynb](https://img.shields.io/badge/ipynb-F37626?logo=jupyter&logoColor=white&style=flat-square)](2026_PDC27/main.ipynb) |

## Layout

Each scenario lives in its own per-object directory at the top level,
named for the object's full canonical designation (number + name when
named, provisional designation otherwise). The Python script, the
Rust binary, the notebook, and the science writeup are colocated:

```
empyrean-scenarios/
├── 99942_Apophis/
│   ├── main.py                   ← python 99942_Apophis/main.py
│   ├── main.rs                   ← cargo run --release --bin apophis
│   ├── main.ipynb                ← the notebook twin, committed with executed outputs
│   └── README.md                 ← science context + reference-number table
├── 101955_Bennu/
├── 2008_TC3/
├── 2020_CD3/
├── 2024_YR4/
└── 67P_Churyumov-Gerasimenko/
```

The directory name carries the full provenance; the script files
inside are named `main.py` / `main.rs` for clarity. Rust binary
names stay short (`apophis`, `bd2009`, `bennu`, `cd3`, `comet67p`,
`falcon9`, `pdc27`, `tc3`, `yr4`) so they're cheap to type at the CLI.

## Quick start

Pick a runtime — both reproduce the same headline numbers.

**Rust:**
```bash
git clone https://github.com/Empyrean-Dynamics/empyrean-scenarios.git
cd empyrean-scenarios
cargo run --release --bin <scenario>     # apophis | bd2009 | bennu | cd3 | comet67p | falcon9 | pdc27 | tc3 | yr4
```

**Python:**
```bash
pip install empyrean
git clone https://github.com/Empyrean-Dynamics/empyrean-scenarios.git
cd empyrean-scenarios
python 99942_Apophis/main.py             # or 101955_Bennu/main.py, 2008_TC3/main.py, ...
```

**Notebooks:** every scenario's `main.ipynb` renders on GitHub with its
executed outputs — no install needed to read the numbers — and carries
an Open-in-Colab badge to run it in the browser (first run downloads
the ~740 MB kernel set).
```bash
jupyter lab 99942_Apophis/main.ipynb     # or any other scenario
```

The first run of any scenario downloads SPICE kernels (DE440, MPC
observatory codes, Earth orientation BPCs) into the platform's XDG
data directory; later runs reuse the cache.

## Conventions

Each scenario ships **three implementations** — `<dirname>/main.py`
(Python), `<dirname>/main.rs` (Rust), and `<dirname>/main.ipynb` (the
notebook twin, rendered on GitHub with executed outputs and runnable
in Colab) — and each implementation:

- Imports only from the public `empyrean` package / crate surface.
- Initializes once at the top (`empyrean.initialize()` in Python, `Context::default_data_dir()?` in Rust).
- Pulls inputs from authoritative public sources — JPL SBDB, MPC, JPL CAD.
- Prints a small banner of headline numbers (close-approach distances, IP, B-plane geometry) so the binary doubles as a smoke test.
- Cites authoritative reference values inline in comments where they exist, so a reader can sanity-check what the toolkit produced against what JPL publishes.

The numbers each implementation prints are the same numbers that
appear in the narrative panel of
`https://empyrean-dynamics.com/explore/{id}` — and the Rust and
Python prints should match each other to the precision of the
underlying float arithmetic. Any discrepancy is a bug somewhere.

See [`docs/conventions.md`](docs/conventions.md) for the full spec.

## License

[BSD-3-Clause](LICENSE) — permissive, attribution-required.
Compatible with the rest of the Empyrean Dynamics public-distribution
chain.
