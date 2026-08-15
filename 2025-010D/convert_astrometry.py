#!/usr/bin/env python3
"""
Convert Project Pluto find_orb-extended MPC 80-column astrometry for
2025-010D (Falcon 9 second stage, lunar impact 2026-08-05) into an ADES
PSV file readable by the empyrean `read_ades` reader.

Source pages (public domain, Project Pluto / B. Gray):
  https://www.projectpluto.com/pluto/mpecs/25010d.htm
  https://www.projectpluto.com/pluto/mpecs/25010d_new.htm
  https://projectpluto.com/temp/a11hsi1.htm

Format spec: https://www.projectpluto.com/mpec_xpl.htm#astrometry

Parsing is by FIXED COLUMN SLICES only -- never by whitespace splitting of
the whole record, because the 6-decimal date form abuts the RA field with
no separator (e.g. "2025 01 20.32129111 17 04.680").

All time arithmetic uses `decimal.Decimal` (exact) -- no binary floats
anywhere on the time path.
"""

from __future__ import annotations

import html
import itertools
import re
import sys
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path

getcontext().prec = 50

HERE = Path(__file__).parent

# The three public-domain Project Pluto pages holding the astrometry.
# Run with local file paths as arguments to convert saved copies
# instead of fetching:  convert_astrometry.py page1.htm page2.htm page3.htm
SOURCES = [
    "https://www.projectpluto.com/pluto/mpecs/25010d.htm",
    "https://www.projectpluto.com/pluto/mpecs/25010d_new.htm",
    "https://projectpluto.com/temp/a11hsi1.htm",
]

OUT_PSV = str(HERE / "astrometry.psv")


def fetch(url: str) -> str:
    """Fetch a source page (no caching — the run is the verification)."""
    import urllib.request

    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


# Uniform object identity. The source files carry seven different
# designation spellings for this one object plus the NEOCP tracklet
# designation; the OD keys identity off trkSub, so every row gets the
# same value.
TRKSUB = "25010D"

KNOWN_DESIGNATIONS = {
    "     25010D ",
    "     202510D",
    "     TR0000 ",
    "     TR0001 ",
    "     TR0002 ",
    "2025-010D   ",
    "     25-010D",
    "     A11hSI1",
}

TRACKLET_REMARK = "NEOCP discovery tracklet A11hSI1"

# note2 / mode (column 15) -> ADES mode enum
MODE_MAP = {"C": "CCD", "B": "CMO"}

# Observatory names and observer lists, transcribed from the station
# tables on the source pages themselves (the `<a name="stn_XXX">` blocks).
STATIONS = {
    "P13": ("Baihuashan Observatory, Beijing, China", ["Z. Wang", "B. Liu"]),
    "718": ("Tooele, Utah, USA", ["P. Wiggins"]),
    "970": ("Chelmsford, England, UK", ["N. James"]),
    "W05": ("Tree Gate Farm Observatory, Starkville, Mississippi, USA", ["J.-F. Gout"]),
    "Y82": ("LPMR Observatory, Broad Chalke, England, UK", ["G. Privett"]),
    "K19": ("PASTIS Observatory, Banon, France", ["C. Demeautis"]),
    "M21": (
        "Schiaparelli Southern Observatory, Hakos, Namibia",
        ["A. Aletti", "F. Bellini", "L. Buzzi", "G. Galli"],
    ),
    "Q62": ("iTelescope Observatory, Siding Spring, NSW, Australia", ["Z. Wang"]),
    "Y05": ("SONEAR Wykrota-CEAMIG, Serra da Piedade, Brazil", ["C. Jacques"]),
    "W68": (
        "ATLAS Chile, Rio Hurtado, Chile",
        ["L. Denneau", "R. Siverd", "J. Tonry", "H. Weiland"],
    ),
    # Private station, non-MPC code -- kept verbatim as it appears in the
    # source, since the OD needs to know this code is not an MPC site.
    "ScT": (
        "Roberts Creek 1, British Columbia, Canada (private station, non-MPC code)",
        ["S. Tilley"],
    ),
}

CENTURY = {"I": 1800, "J": 1900, "K": 2000}

TAG_RE = re.compile(r"<[^>]*>")
ANCHOR_RE = re.compile(r'<a name="o(\d+)"></a>(.*?)$')
PACKED_RE = re.compile(r"^([IJK])(\d{2})(\d{2})(\d{2}):(\d{2})(\d{2})(\d{2})(\d*)$")
STANDARD_RE = re.compile(r"^(\d{4}) (\d{2}) (\d{2})\.(\d+)$")

anomalies: list[str] = []


def note(msg: str) -> None:
    anomalies.append(msg)
    print(f"ANOMALY: {msg}", file=sys.stderr)


# ── Extraction ───────────────────────────────────────────────────────


def extract_lines(content: str) -> list[tuple[str, str]]:
    """Pull every `<a name="oNNN">` astrometry record out of a page.

    Strips HTML tags, unescapes entities, and asserts each record is
    exactly 80 characters.
    """
    out: list[tuple[str, str]] = []
    if True:
        for raw in content.splitlines():
            m = ANCHOR_RE.search(raw.rstrip("\r\n"))
            if not m:
                continue
            body = html.unescape(TAG_RE.sub("", m.group(2)))
            if len(body) != 80:
                note(f"o{m.group(1)}: length {len(body)} != 80: {body!r}")
                raise SystemExit(f"non-80-column record o{m.group(1)}")
            out.append((m.group(1), body))
    return out


# ── Time ─────────────────────────────────────────────────────────────


def format_seconds(sec: Decimal, ndp: int) -> str:
    """Render a seconds value as `SS` or `SS.ffff`, exactly, no rounding."""
    quant = Decimal(1).scaleb(-ndp) if ndp > 0 else Decimal(1)
    q = sec.quantize(quant)
    if q != sec:
        raise AssertionError(f"seconds {sec} not exact at {ndp} decimals")
    whole = int(q)
    if whole < 0 or whole > 59:
        raise AssertionError(f"seconds out of range: {q}")
    if ndp == 0:
        return f"{whole:02d}"
    frac_digits = str(abs(q)).split(".")[1].ljust(ndp, "0")
    return f"{whole:02d}.{frac_digits}"


def parse_time(field: str, ctx: str) -> str:
    """Convert columns 16-32 to an ISO-8601 UTC timestamp ending in 'Z'.

    Two encodings are accepted:
      (a) standard  'YYYY MM DD.dddddd'  (5 or 6 decimals of a day)
      (b) find_orb packed gray form 'KYYMMDD:HHMMSS[ff]'

    The day fraction is expanded with exact decimal arithmetic: a day
    fraction with `n` decimals maps to exactly `n - 2` decimals of a
    second (86400 / 10**n = 864 / 10**(n-2)), so nothing is ever rounded.
    """
    t = field.strip()

    m = PACKED_RE.match(t)
    if m:
        cent, yy, mo, dd, hh, mi, ss, frac = m.groups()
        year = CENTURY[cent] + int(yy)
        sec = f"{ss}.{frac}" if frac else ss
        return f"{year:04d}-{mo}-{dd}T{hh}:{mi}:{sec}Z"

    m = STANDARD_RE.match(t)
    if m:
        year, mon, day, frac = m.groups()
        ndp = len(frac) - 2
        if ndp < 0:
            note(f"{ctx}: day fraction with only {len(frac)} decimals: {t!r}")
            ndp = 0
        total = Decimal(f"0.{frac}") * Decimal(86400)
        hours = int(total // 3600)
        rem = total - hours * 3600
        mins = int(rem // 60)
        secs = rem - mins * 60
        return (
            f"{int(year):04d}-{mon}-{day}T"
            f"{hours:02d}:{mins:02d}:{format_seconds(secs, ndp)}Z"
        )

    raise ValueError(f"{ctx}: unparseable date field {t!r}")


# ── Coordinates ──────────────────────────────────────────────────────

SEVEN = Decimal("0.0000001")


def strip_plus(tok: str) -> str:
    """Drop a leading '+' from a decimal-degree token; digits untouched."""
    return tok.removeprefix("+")


def parse_ra(field: str, ctx: str) -> str:
    """Columns 33-44 -> decimal degrees.

    A single token with no internal spaces is already find_orb decimal
    degrees and is copied digit-for-digit. Otherwise it is sexagesimal
    'HH MM SS.dd' and is converted as (H*3600 + M*60 + S) / 240.
    """
    t = field.strip()
    if not t:
        raise ValueError(f"{ctx}: empty RA field")
    parts = t.split()
    if len(parts) == 1:
        return strip_plus(t)
    if len(parts) != 3:
        raise ValueError(f"{ctx}: unparseable RA field {t!r}")
    h, m, s = parts
    seconds_of_time = Decimal(h) * 3600 + Decimal(m) * 60 + Decimal(s)
    return str((seconds_of_time / Decimal(240)).quantize(SEVEN, rounding=ROUND_HALF_UP))


def parse_dec(field: str, ctx: str) -> str:
    """Columns 45-56 -> decimal degrees (sexagesimal or already decimal)."""
    t = field.strip()
    if not t:
        raise ValueError(f"{ctx}: empty Dec field")
    if " " not in t:
        return strip_plus(t)
    negative = t.startswith("-")
    parts = t.lstrip("+-").split()
    if len(parts) != 3:
        raise ValueError(f"{ctx}: unparseable Dec field {t!r}")
    d, m, s = parts
    arcsec = Decimal(d) * 3600 + Decimal(m) * 60 + Decimal(s)
    deg = arcsec / Decimal(3600)
    if negative:
        deg = -deg
    return str(deg.quantize(SEVEN, rounding=ROUND_HALF_UP))


# ── Record parsing ───────────────────────────────────────────────────


def parse_record(line: str, ctx: str, is_tracklet: bool) -> dict:
    if len(line) != 80:
        raise ValueError(f"{ctx}: length {len(line)} != 80")

    designation = line[0:12]
    if designation not in KNOWN_DESIGNATIONS:
        note(f"{ctx}: unexpected designation variant {designation!r}")

    discovery = line[12]
    note2 = line[14]
    date_f = line[15:32]
    ra_f = line[32:44]
    dec_f = line[44:56]
    # Columns 57-65 are ignored per the spec, except that find_orb parks
    # its "magnitude is not to be used" flag on column 65 (the character
    # immediately before the magnitude field), rendering as 'x16.6'.
    flag_col65 = line[64]
    mag_f = line[65:70].strip()
    band = line[70].strip()
    stn = line[77:80].strip()

    mode = MODE_MAP.get(note2, "")
    if not mode:
        note(f"{ctx}: unknown mode/note2 {note2!r}; emitting blank mode")

    mag_flagged = flag_col65 == "x" or mag_f.startswith("x")
    if mag_flagged:
        mag = ""
    else:
        mag = mag_f

    if stn not in STATIONS:
        note(f"{ctx}: station {stn!r} has no observatory metadata")

    return {
        "src_line": line,
        "ctx": ctx,
        "designation": designation,
        "discovery": discovery == "*",
        "trkSub": TRKSUB,
        "mode": mode,
        "stn": stn,
        "obsTime": parse_time(date_f, ctx),
        "ra": parse_ra(ra_f, ctx),
        "dec": parse_dec(dec_f, ctx),
        "mag": mag,
        "mag_flagged": mag_flagged,
        "band": band,
        "remarks": TRACKLET_REMARK if is_tracklet else "",
    }


# ── PSV emission ─────────────────────────────────────────────────────

COLUMNS = ["trkSub", "mode", "stn", "obsTime", "ra", "dec", "mag", "band", "remarks"]
WIDTHS = {
    "trkSub": 8,
    "mode": 4,
    "stn": 4,
    "obsTime": 23,
    "ra": 11,
    "dec": 11,
    "mag": 5,
    "band": 4,
    "remarks": 0,
}


def psv_row(values: list[str]) -> str:
    cells = []
    for name, val in zip(COLUMNS, values):
        if "|" in val:
            raise AssertionError(f"pipe character inside field {name}: {val!r}")
        w = WIDTHS[name]
        cells.append(val.ljust(w) if w else val)
    return "|".join(cells).rstrip()


def iso_sort_key(t: str) -> tuple:
    """Sort ISO timestamps correctly regardless of fractional-digit count."""
    date, rest = t.rstrip("Z").split("T")
    hh, mm, ss = rest.split(":")
    return (date, int(hh), int(mm), Decimal(ss))


def main() -> int:
    records: list[dict] = []
    per_source: dict[str, int] = {}

    local = sys.argv[1:]
    for i, url in enumerate(SOURCES):
        name = url.rsplit("/", 1)[-1]
        is_tracklet = name.startswith("a11hsi1")
        if local:
            content = Path(local[i]).read_text(encoding="utf-8", errors="replace")
        else:
            content = fetch(url)
        lines = extract_lines(content)
        per_source[url] = len(lines)
        for anchor, line in lines:
            records.append(parse_record(line, f"{name}:o{anchor}", is_tracklet))

    # ── Group into per-station obsBlocks, time-sorted ──
    by_stn: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_stn[r["stn"]].append(r)
    for rows in by_stn.values():
        rows.sort(key=lambda r: iso_sort_key(r["obsTime"]))

    # Blocks in chronological order of their first observation.
    block_order = sorted(by_stn, key=lambda s: iso_sort_key(by_stn[s][0]["obsTime"]))

    # ── Validation ──
    seen: set[tuple[str, str]] = set()
    for stn in block_order:
        rows = by_stn[stn]
        for r in rows:
            key = (stn, r["obsTime"])
            if key in seen:
                note(f"duplicate (stn, obsTime): {key} at {r['ctx']}")
            seen.add(key)
        for a, b in itertools.pairwise(rows):
            if iso_sort_key(a["obsTime"]) >= iso_sort_key(b["obsTime"]):
                note(
                    f"non-increasing time in {stn}: "
                    f"{a['obsTime']} -> {b['obsTime']} ({b['ctx']})"
                )

    # ── Write ──
    header = psv_row(COLUMNS)
    out: list[str] = ["# version=2022", "# comment"]
    out.append(
        "! line Astrometry of 2025-010D (Falcon 9 second stage; lunar impact 2026-08-05)."
    )
    out.append(
        "! line Converted from find_orb-extended MPC 80-column records published by"
    )
    out.append("! line Project Pluto (Bill Gray). Source pages, retrieved 2026-08-06:")
    for url, n in per_source.items():
        out.append(f"! line   {url} ({n} observations)")
    out.append(
        "! line These pseudo-MPEC pages are placed in the public domain by Project Pluto."
    )
    out.append(
        "! line Conversion: fixed-column parse of the 80-column records; times expanded"
    )
    out.append(
        "! line with exact decimal arithmetic to ISO-8601 UTC at the source precision;"
    )
    out.append(
        "! line sexagesimal RA/Dec converted to decimal degrees at 7 decimal places;"
    )
    out.append(
        "! line find_orb decimal-degree coordinates copied digit-for-digit. The seven"
    )
    out.append(
        f"! line source designation variants are unified to trkSub {TRKSUB}. Magnitudes"
    )
    out.append(
        "! line flagged unusable by find_orb (column 65 'x') are omitted. The astrometric"
    )
    out.append(
        "! line catalog code (column 72) is not carried over. Observatory and observer"
    )
    out.append(
        "! line names are transcribed from the station tables on the same pages."
    )

    total_rows = 0
    for stn in block_order:
        name, observers = STATIONS.get(stn, (None, []))
        out.append("# observatory")
        out.append(f"! mpcCode {stn}")
        if name:
            out.append(f"! name {name}")
        if observers:
            out.append("# observers")
            for who in observers:
                out.append(f"! name {who}")
        out.append(header)
        for r in by_stn[stn]:
            out.append(psv_row([r[c] for c in COLUMNS]))
            total_rows += 1

    with open(OUT_PSV, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")

    # ── Report ──
    counts = Counter(r["stn"] for r in records)
    print(f"records parsed : {len(records)}")
    print(f"rows written   : {total_rows}")
    print(f"per source     : {per_source}")
    print(f"per station    : {dict(sorted(counts.items()))}")
    print(f"blocks         : {len(block_order)} -> {block_order}")
    print(f"mag 'x'-flagged: {sum(1 for r in records if r['mag_flagged'])}")
    print(f"mag empty out  : {sum(1 for r in records if not r['mag'])}")
    print(f"band empty     : {sum(1 for r in records if not r['band'])}")
    print(f"mode blank     : {sum(1 for r in records if not r['mode'])}")
    print(f"designations   : {dict(Counter(r['designation'] for r in records))}")
    print(f"discovery '*'  : {sum(1 for r in records if r['discovery'])}")
    print(f"anomalies      : {len(anomalies)}")
    print(f"wrote          : {OUT_PSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
