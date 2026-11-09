"""LRO ground truth vs the predicted impact sites for 2025-010D.

Downloads NASA's public-domain release images (credits: NASA/JPL-Caltech
for the probability-ellipse map; NASA Goddard/Intuitive Machines for the
LRO NAC before/after frames), georeferences the ellipse map from its own
marked points, and overlays this scenario's prediction, Gray's, and JPL's
against the crater LRO located at 19.4759°N 266.7138°E.

    pip install matplotlib pillow numpy
    python lro_figure.py          # writes lro_impact_site.png next to it

Source: https://science.nasa.gov/solar-system/moon/nasas-lro-images-falcon-9-crater-on-moon-learns-new-details/
"""

import math
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Rectangle
from PIL import Image

HERE = Path(__file__).parent
CACHE = HERE / ".nasa_lro_cache"
CACHE.mkdir(exist_ok=True)
NASA = "https://assets.science.nasa.gov/"
IMAGES = {
    "ellipses.jpg": NASA
    + "dynamicimage/assets/science/missions/lro/probability-elipses.jpg",
    "before_after.gif": NASA
    + "content/dam/science/missions/lro/NASA_LRO_Falcon9impact_2026_GIF.gif",
}
# Wide-field base: Kaguya Terrain Camera ortho-mosaic (JAXA/SELENE) served by
# the USGS Astrogeology lunar WMS at ~10 m/px, simple-cylindrical, exact bbox.
TC_BBOX = (-93.60, 19.28, -92.97, 19.74)  # lon0, lat0, lon1, lat1 (deg)
TC_W, TC_H = 1800, 1400
IMAGES["tc_window.png"] = (
    "https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl.map"
    "&service=WMS&request=GetMap&version=1.1.1&layers=KaguyaTC_Ortho&styles="
    f"&srs=EPSG:4326&bbox={TC_BBOX[0]},{TC_BBOX[1]},{TC_BBOX[2]},{TC_BBOX[3]}"
    f"&width={TC_W}&height={TC_H}&format=image/png"
)
for name, url in IMAGES.items():
    if not (CACHE / name).exists():
        print(f"fetching {url[:80]}...")
        urllib.request.urlretrieve(url, CACHE / name)
gif = Image.open(CACHE / "before_after.gif")
for i in range(2):
    gif.seek(i)
    gif.convert("L").save(CACHE / f"frame_{i}.png")
N = str(CACHE) + "/"
R_MOON = 1737.4
CRATER = (19.4759, 266.7138)  # NASA LRO, 2026-08-11/12
PRED = {
    "empyrean (optical, 74-obs arc)": (19.514, 266.646, "#eb6834"),
    "Gray / Project Pluto (74-obs arc)": (19.577, 266.630, "#1baf7a"),
    "Gray final (all data, non-public)": (19.461, 266.707, "#eda100"),
}
CNEOS_COLOR = {"terrain-aware": "#2a78d6", "no terrain": "#c0392b"}


def offset_km(lat, lon):
    dn = math.radians(lat - CRATER[0]) * R_MOON
    de = math.radians(lon - CRATER[1]) * R_MOON * math.cos(math.radians(CRATER[0]))
    return dn, de


# ── georeference NASA's ellipse map ──
# The caption states both ellipses are 2.1 miles (3.4 km) long (JPL's
# published 3-sigma ellipse), so the map scale comes from the blue
# ellipse's own major axis. (The Horizons nominal is published to 0.1°
# of longitude, ~1.4 km, far too coarse to anchor a sub-km scale.)
img = np.asarray(Image.open(N + "ellipses.jpg").convert("RGB")).astype(int)
r, g, b = img[..., 0], img[..., 1], img[..., 2]


def centroid(mask):
    ys, xs = np.nonzero(mask)
    return float(xs.mean()), float(ys.mean()), int(mask.sum())


def major_axis_px(mask):
    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xs, ys]).astype(float)
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    proj = (pts - c) @ vt[0]
    return float(proj.max() - proj.min())


blue_pt = centroid((b > 170) & (r < 50) & (g < 60))  # CNEOS terrain-aware nominal
red_pt = centroid((r > 150) & (g < 40) & (b < 40))  # CNEOS nominal without terrain
teal_pt = centroid((g > 120) & (b > 100) & (r < 60) & (g > r + 60))  # LRO crater
ELLIPSE_LONG_M = 2.1 * 1609.344
m_per_px = ELLIPSE_LONG_M / major_axis_px((b - r > 45) & (b - g > 45) & (b < 170))
print(
    f"scale {m_per_px:.2f} m/px from the 3.4 km ellipse; map {1280 * m_per_px / 1000:.1f} km wide"
)


def map_offset_km(pt):
    """North/east offset of a marked map point from the crater, in km."""
    de = (pt[0] - teal_pt[0]) * m_per_px / 1000
    dn = -(pt[1] - teal_pt[1]) * m_per_px / 1000
    return dn, de


INK, MUTED, SURF = "#1a1a19", "#6b6a63", "#fcfcfb"
fig = plt.figure(figsize=(16, 14.2), dpi=150)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(
    2,
    2,
    width_ratios=[1.3, 1],
    height_ratios=[1, 1.05],
    wspace=0.05,
    hspace=0.12,
    left=0.02,
    right=0.98,
    top=0.93,
    bottom=0.075,
)

# ── Panel W: wide field on the Kaguya TC mosaic, terrain-anchored ──
tc = np.asarray(Image.open(N + "tc_window.png").convert("L")).astype(float)
tc_mpp = (TC_BBOX[2] - TC_BBOX[0]) * 28.58e3 / TC_W  # ~10 m/px at this latitude


def tc_px_from_lonlat(lat, lon):
    lon = ((lon + 180) % 360) - 180  # 0..360 (selenographic) -> -180..180 (WMS)
    return (
        (lon - TC_BBOX[0]) / (TC_BBOX[2] - TC_BBOX[0]) * TC_W,
        (TC_BBOX[3] - lat) / (TC_BBOX[3] - TC_BBOX[1]) * TC_H,
    )


# Anchor on terrain: locate NASA's map inside the mosaic by normalized
# cross-correlation, so the crater marker sits on the right craters even
# where the two missions' geodetic ties differ by a few hundred metres.
nasa_gray = Image.open(N + "ellipses.jpg").convert("L")
sc = m_per_px / tc_mpp
tmpl = np.asarray(
    nasa_gray.resize((int(1280 * sc), int(997 * sc)), Image.LANCZOS)
).astype(float)
cx_geo, cy_geo = tc_px_from_lonlat(*CRATER)
tx0, ty0 = cx_geo - teal_pt[0] * sc, cy_geo - teal_pt[1] * sc


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else 0.0


best = (-1.0, 0, 0)
th, tw = tmpl.shape
for dy in range(-60, 61, 3):
    for dx in range(-60, 61, 3):
        x0, y0 = int(np.rint(tx0 + dx)), int(np.rint(ty0 + dy))
        patch = tc[y0 : y0 + th, x0 : x0 + tw]
        if patch.shape == tmpl.shape:
            v = _ncc(patch, tmpl)
            if v > best[0]:
                best = (v, dx, dy)
shift_px = (best[1], best[2])
reg_m = math.hypot(*shift_px) * tc_mpp
print(
    f"NASA map located in the Kaguya mosaic: NCC {best[0]:.2f}, tie offset {reg_m:.0f} m"
)
wcx, wcy = cx_geo + shift_px[0], cy_geo + shift_px[1]  # crater, terrain-anchored


def wide_px(dn_km, de_km):
    return wcx + de_km * 1000 / tc_mpp, wcy - dn_km * 1000 / tc_mpp


axw = fig.add_subplot(gs[0, 0])
axw.imshow(
    tc.astype(np.uint8), cmap="gray", vmin=40, vmax=120, extent=[0, TC_W, TC_H, 0]
)
axw.set_xlim(300, 1700)
axw.set_ylim(1250, 150)
axw.add_patch(
    Rectangle(
        (tx0 + shift_px[0], ty0 + shift_px[1]),
        tw,
        th,
        fill=False,
        color="#fcfcfb",
        lw=1.0,
        ls=(0, (4, 3)),
    )
)
axw.text(
    tx0 + shift_px[0] + 6,
    ty0 + shift_px[1] + 16,
    "NASA/JPL map (right)",
    fontsize=7.5,
    color="#fcfcfb",
)
bdn, bde = map_offset_km(blue_pt)
ex, ey = wide_px(bdn, bde)
axw.add_patch(
    Ellipse(
        (ex, ey),
        640 / tc_mpp,
        ELLIPSE_LONG_M / tc_mpp,
        angle=90 - 81.7,
        fill=False,
        color=CNEOS_COLOR["terrain-aware"],
        lw=1.6,
    )
)
for lab, pt, col, dxy in (
    ("CNEOS terrain-aware nominal", blue_pt, CNEOS_COLOR["terrain-aware"], (14, -22)),
    ("CNEOS nominal, no terrain", red_pt, CNEOS_COLOR["no terrain"], (10, 40)),
):
    dn, de = map_offset_km(pt)
    px, py = wide_px(dn, de)
    axw.plot(px, py, "o", ms=6, mfc=col, mec="#fcfcfb", mew=1.2, zorder=5)
    axw.annotate(
        f"{lab} · {math.hypot(dn, de):.1f} km",
        (px, py),
        xytext=dxy,
        textcoords="offset points",
        fontsize=8,
        color="#fcfcfb",
        ha="left" if dxy[0] > 0 else "right",
        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.9},
    )
axw.add_patch(Circle((wcx, wcy), 9, fill=False, color="#fcfcfb", lw=2.0))
axw.annotate(
    "LRO crater",
    (wcx, wcy),
    xytext=(18, 26),
    textcoords="offset points",
    fontsize=8.5,
    color="#fcfcfb",
    bbox={"boxstyle": "round,pad=0.25", "fc": "#1a1a19", "ec": "none", "alpha": 0.8},
)
for lab, (lat, lon, col) in PRED.items():
    dn, de = offset_km(lat, lon)
    px, py = wide_px(dn, de)
    axw.plot(px, py, "o", ms=9, mfc=col, mec="#fcfcfb", mew=1.4, zorder=5)
    axw.plot([wcx, px], [wcy, py], color=col, lw=1.1, alpha=0.8, zorder=4)
    axw.annotate(
        f"{lab}\n{math.hypot(dn, de):.1f} km from crater",
        (px, py),
        xytext=(-14, 10),
        textcoords="offset points",
        fontsize=8,
        color="#fcfcfb",
        ha="right",
        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.9},
    )
bar = 2000 / tc_mpp
axw.plot([330, 330 + bar], [1225, 1225], color="#fcfcfb", lw=3)
axw.text(330 + bar / 2, 1210, "2 km", ha="center", fontsize=9, color="#fcfcfb")
axw.annotate(
    "N",
    (1660, 240),
    (1660, 175),
    fontsize=10,
    color="#fcfcfb",
    ha="center",
    arrowprops={"arrowstyle": "<-", "color": "#fcfcfb", "lw": 1.5},
)
axw.set_title(
    "Wide field: Kaguya TC ortho-mosaic (JAXA/SELENE via USGS Astrogeology WMS), 14 × 11 km",
    fontsize=10.5,
    color=INK,
    loc="left",
)
axw.set_axis_off()


# Panel A: NASA's map at its true scale, with a margin above for Gray's point
ax = fig.add_subplot(gs[0, 1])
H_IMG, W_IMG = img.shape[:2]
MARGIN = 190
ax.imshow(img.astype(np.uint8), extent=[0, W_IMG, H_IMG, 0])
ax.set_xlim(0, W_IMG)
ax.set_ylim(H_IMG, -MARGIN)
ax.axhspan(-MARGIN, 0, color="#e9e7e1", zorder=0)
ax.text(
    W_IMG / 2,
    -MARGIN + 18,
    "beyond the top edge of NASA's map",
    ha="center",
    fontsize=7.5,
    color=MUTED,
)
cx, cy = teal_pt[:2]
ax.add_patch(Circle((cx, cy), 12, fill=False, color="#fcfcfb", lw=2.2))
ax.add_patch(Circle((cx, cy), 12, fill=False, color="#1a1a19", lw=1.1))
ax.annotate(
    "LRO crater\n19.4759°N 266.7138°E",
    (cx, cy),
    xytext=(60, -70),
    textcoords="offset points",
    fontsize=8.5,
    color="#fcfcfb",
    arrowprops={"arrowstyle": "-", "color": "#fcfcfb", "lw": 0.9},
    bbox={"boxstyle": "round,pad=0.25", "fc": "#1a1a19", "ec": "none", "alpha": 0.8},
)
MAP_PTS = {}
for lab, pt, dxy in (
    ("CNEOS terrain-aware nominal", blue_pt, (40, 30)),
    ("CNEOS nominal, no terrain", red_pt, (-46, 62)),
):
    dn, de = map_offset_km(pt)
    MAP_PTS[lab] = (dn, de)
    col = CNEOS_COLOR["terrain-aware" if "aware" in lab else "no terrain"]
    ax.annotate(
        f"{lab}\n{math.hypot(dn, de):.1f} km from crater",
        pt[:2],
        xytext=dxy,
        textcoords="offset points",
        fontsize=8,
        color="#fcfcfb",
        ha="left" if dxy[0] > 0 else "right",
        arrowprops={"arrowstyle": "-", "color": col, "lw": 1.2},
        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.9},
    )


def to_px(lat, lon):
    dn, de = offset_km(lat, lon)
    return cx + de * 1000 / m_per_px, cy - dn * 1000 / m_per_px


for lab, (lat, lon, col) in PRED.items():
    dn, de = offset_km(lat, lon)
    d = math.hypot(dn, de)
    px, py = to_px(lat, lon)
    ax.plot(px, py, "o", ms=9, mfc=col, mec="#fcfcfb", mew=1.4, zorder=5, clip_on=False)
    ax.plot([cx, px], [cy, py], color=col, lw=1.1, alpha=0.8, zorder=4, clip_on=False)
    ax.annotate(
        f"{lab}\n{d:.1f} km from crater",
        (px, py),
        xytext=(14, -6),
        textcoords="offset points",
        fontsize=8,
        color="#fcfcfb",
        ha="left",
        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.9},
    )
bar_px = 1000 / m_per_px
ax.plot([30, 30 + bar_px], [H_IMG - 40, H_IMG - 40], color="#fcfcfb", lw=3)
ax.text(30 + bar_px / 2, H_IMG - 54, "1 km", ha="center", fontsize=9, color="#fcfcfb")
ax.annotate(
    "N",
    (W_IMG - 40, 80),
    (W_IMG - 40, 25),
    fontsize=10,
    color="#fcfcfb",
    ha="center",
    arrowprops={"arrowstyle": "<-", "color": "#fcfcfb", "lw": 1.5},
)
ax.set_title(
    "NASA/JPL-Caltech impact-probability ellipses (3σ, 3.4 × 0.6 km) with the predicted sites",
    fontsize=10.5,
    color=INK,
    loc="left",
)
ax.set_axis_off()

# Panels B/C: before / after NAC frames (north up, ~400 m wide)
FRAME_M = 402.0  # "about a quarter of a mile"
for k, (ttl, fn) in enumerate(
    [
        ("LRO NAC before impact", "frame_0.png"),
        ("LRO NAC after impact (Aug 11–12, 2026)", "frame_1.png"),
    ]
):
    axb = fig.add_subplot(gs[1, k])
    fr = np.asarray(Image.open(N + fn))
    axb.imshow(fr, cmap="gray", extent=[0, FRAME_M, FRAME_M, 0])
    axb.set_title(ttl, fontsize=10.5, color=INK, loc="left")
    axb.set_axis_off()
    axb.plot([20, 120], [FRAME_M - 18, FRAME_M - 18], color="#fcfcfb", lw=3)
    axb.text(70, FRAME_M - 28, "100 m", ha="center", fontsize=9, color="#fcfcfb")
    if k == 1:
        ccx, ccy = 0.492 * FRAME_M, 0.497 * FRAME_M  # fresh crater in the frame
        axb.add_patch(Circle((ccx, ccy), 16, fill=False, color="#fcfcfb", lw=1.6))
        arrows = [
            (lab, offset_km(lat, lon), col) for lab, (lat, lon, col) in PRED.items()
        ]
        arrows.append(
            (
                "CNEOS",
                MAP_PTS["CNEOS terrain-aware nominal"],
                CNEOS_COLOR["terrain-aware"],
            )
        )
        for j, (lab, (dn, de), col) in enumerate(arrows):
            d = math.hypot(dn, de)
            ang = math.atan2(dn, de)
            L = (150, 205, 120, 175, 235)[j]
            ex, ey = ccx + L * math.cos(ang), ccy - L * math.sin(ang)
            axb.add_patch(
                FancyArrowPatch(
                    (ccx + 30 * math.cos(ang), ccy - 30 * math.sin(ang)),
                    (ex, ey),
                    color=col,
                    lw=2,
                    arrowstyle="-|>",
                    mutation_scale=14,
                )
            )
            axb.text(
                ex + 6 * math.cos(ang),
                ey - 6 * math.sin(ang),
                f"{lab.split(' (')[0].split(' #')[0]} {d:.1f} km",
                fontsize=8,
                color="#fcfcfb",
                ha="center",
                va="center",
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "fc": col,
                    "ec": "none",
                    "alpha": 0.9,
                },
            )

fig.suptitle(
    "2025-010D, where the predictions landed: LRO ground truth vs the optical-only forecasts",
    x=0.02,
    ha="left",
    fontsize=13,
    color=INK,
)
fig.text(
    0.02,
    0.012,
    "Top left: Kaguya Terrain Camera ortho-mosaic wide field (~10 m/px), terrain-anchored by locating "
    f"NASA's map inside it (tie offset {reg_m:.0f} m between the two missions' geodetic frames). "
    "Top right: NASA/JPL-Caltech impact-probability ellipses, both 2.1 mi × 0.4 mi per NASA's caption "
    "(JPL's 3σ ellipse; blue accounts for lunar terrain, red does not), georeferenced from the ellipse's "
    f"own 3.4 km length ({m_per_px:.1f} m/px, north up) and anchored on NASA's crater marker. "
    "CNEOS offsets are measured from NASA's markers (the Horizons nominal is published only to 0.1° of "
    "longitude, ~1.4 km). Bottom left and bottom right: LRO NAC frames before and after impact, "
    "NASA Goddard/Intuitive Machines, ~400 m wide, north up; crater 60 ft across. "
    "Predictions: this scenario's optical-only fit; Gray 2026 (Project Pluto).",
    fontsize=7.6,
    color=MUTED,
    wrap=True,
)
fig.savefig(HERE / "lro_impact_site.png", dpi=200, bbox_inches="tight", facecolor=SURF)
print("figure written")
