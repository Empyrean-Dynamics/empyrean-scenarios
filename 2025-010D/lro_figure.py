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
from matplotlib.patches import Circle, FancyArrowPatch
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
for name, url in IMAGES.items():
    if not (CACHE / name).exists():
        print(f"fetching {url}")
        urllib.request.urlretrieve(url, CACHE / name)
gif = Image.open(CACHE / "before_after.gif")
for i in range(2):
    gif.seek(i)
    gif.convert("L").save(CACHE / f"frame_{i}.png")
N = str(CACHE) + "/"
R_MOON = 1737.4
CRATER = (19.4759, 266.7138)  # NASA LRO, 2026-08-11/12
PRED = {
    "Empyrean (optical, 74-obs arc)": (19.514, 266.646, "#eb6834"),
    "Gray / Project Pluto (74-obs arc)": (19.577, 266.630, "#1baf7a"),
    "JPL #GA1A2/21 nominal": (19.507, 266.700, "#2a78d6"),
}


def offset_km(lat, lon):
    dn = math.radians(lat - CRATER[0]) * R_MOON
    de = math.radians(lon - CRATER[1]) * R_MOON * math.cos(math.radians(CRATER[0]))
    return dn, de


# ── georeference NASA's ellipse map from its own marked points ──
img = np.asarray(Image.open(N + "ellipses.jpg").convert("RGB")).astype(int)
r, g, b = img[..., 0], img[..., 1], img[..., 2]


def centroid(mask):
    ys, xs = np.nonzero(mask)
    return float(xs.mean()), float(ys.mean()), int(mask.sum())


blue_pt = centroid((b > 170) & (r < 50) & (g < 60))  # JPL nominal dot (saturated)
teal_pt = centroid((g > 120) & (b > 100) & (r < 60) & (g > r + 60))  # crater dot
print("blue dot px:", blue_pt, "| teal dot px:", teal_pt)
dn_jpl, de_jpl = offset_km(*PRED["JPL #GA1A2/21 nominal"][:2])
m_per_px = (dn_jpl * 1000) / (teal_pt[1] - blue_pt[1])  # north-up, from Δlat
print(
    f"scale {m_per_px:.1f} m/px; east-west check: JPL should be {de_jpl * 1000:+.0f} m "
    f"east, measured {(blue_pt[0] - teal_pt[0]) * m_per_px:+.0f} m (JPL lon rounded to 0.1°)"
)


def to_px(lat, lon):
    dn, de = offset_km(lat, lon)
    return teal_pt[0] + de * 1000 / m_per_px, teal_pt[1] - dn * 1000 / m_per_px


INK, MUTED, SURF = "#1a1a19", "#6b6a63", "#fcfcfb"
fig = plt.figure(figsize=(16, 7.4), dpi=150)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(
    1,
    3,
    width_ratios=[1.55, 1, 1],
    wspace=0.06,
    left=0.02,
    right=0.98,
    top=0.86,
    bottom=0.14,
)

# Panel A: wide field
ax = fig.add_subplot(gs[0])
x0, x1, y0, y1 = 330, 900, 120, 800  # crop around the ellipses
ax.imshow(img[y0:y1, x0:x1].astype(np.uint8), extent=[x0, x1, y1, y0])
cx, cy = teal_pt[:2]
ax.add_patch(Circle((cx, cy), 9, fill=False, color="#fcfcfb", lw=2.2))
ax.add_patch(Circle((cx, cy), 9, fill=False, color="#1a1a19", lw=1.1))
ax.annotate(
    "LRO crater\n19.4759°N 266.7138°E",
    (cx, cy),
    xytext=(36, -62),
    textcoords="offset points",
    fontsize=8.5,
    color="#fcfcfb",
    arrowprops={"arrowstyle": "-", "color": "#fcfcfb", "lw": 0.9},
    bbox={"boxstyle": "round,pad=0.25", "fc": "#1a1a19", "ec": "none", "alpha": 0.75},
)
for lab, (lat, lon, col) in PRED.items():
    dn, de = offset_km(lat, lon)
    d = math.hypot(dn, de)
    if lab.startswith("JPL"):
        px, py = blue_pt[:2]  # NASA's own marker for the JPL nominal
        ax.annotate(
            f"{lab} (NASA's marker)\n{d:.1f} km from crater",
            (px, py),
            xytext=(44, 26),
            textcoords="offset points",
            fontsize=8,
            color="#fcfcfb",
            ha="left",
            arrowprops={"arrowstyle": "-", "color": col, "lw": 1.2},
            bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.9},
        )
        continue
    px, py = to_px(lat, lon)
    ax.plot(px, py, "o", ms=8, mfc=col, mec="#fcfcfb", mew=1.4, zorder=5)
    ax.plot([cx, px], [cy, py], color=col, lw=1.1, alpha=0.8, zorder=4)
    ax.annotate(
        f"{lab}\n{d:.1f} km from crater",
        (px, py),
        xytext=(-14, 10),
        textcoords="offset points",
        fontsize=8,
        color="#fcfcfb",
        ha="right",
        bbox={"boxstyle": "round,pad=0.25", "fc": col, "ec": "none", "alpha": 0.85},
    )
# scale bar + north
bar_px = 5000 / m_per_px
ax.plot([x0 + 30, x0 + 30 + bar_px], [y1 - 40, y1 - 40], color="#fcfcfb", lw=3)
ax.text(x0 + 30 + bar_px / 2, y1 - 52, "5 km", ha="center", fontsize=9, color="#fcfcfb")
ax.annotate(
    "N",
    (x1 - 40, y0 + 70),
    (x1 - 40, y0 + 20),
    fontsize=10,
    color="#fcfcfb",
    ha="center",
    arrowprops={"arrowstyle": "<-", "color": "#fcfcfb", "lw": 1.5},
)
ax.set_title(
    "JPL impact-probability ellipses (NASA/JPL-Caltech) with predicted sites",
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
    axb = fig.add_subplot(gs[k + 1])
    fr = np.asarray(Image.open(N + fn))
    axb.imshow(fr, cmap="gray", extent=[0, FRAME_M, FRAME_M, 0])
    axb.set_title(ttl, fontsize=10.5, color=INK, loc="left")
    axb.set_axis_off()
    axb.plot([20, 120], [FRAME_M - 18, FRAME_M - 18], color="#fcfcfb", lw=3)
    axb.text(70, FRAME_M - 28, "100 m", ha="center", fontsize=9, color="#fcfcfb")
    if k == 1:
        ccx, ccy = 0.492 * FRAME_M, 0.497 * FRAME_M  # fresh crater in the frame
        axb.add_patch(Circle((ccx, ccy), 16, fill=False, color="#fcfcfb", lw=1.6))
        for j, (lab, (lat, lon, col)) in enumerate(PRED.items()):
            dn, de = offset_km(lat, lon)
            d = math.hypot(dn, de)
            ang = math.atan2(dn, de)
            L = (150, 205, 120)[j]
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
    "2025-010D — where the predictions landed: LRO ground truth vs the optical-only forecasts",
    x=0.02,
    ha="left",
    fontsize=13,
    color=INK,
)
fig.text(
    0.02,
    0.035,
    "Left: NASA/JPL-Caltech probability-ellipse map, georeferenced from its own marked points "
    "(crater at 19.4759°N 266.7138°E; JPL nominal 19.507°N 266.7°E) assuming north up — "
    f"{m_per_px:.0f} m/px; east–west placement inherits JPL's 0.1° longitude rounding (~1 km).  "
    "Center/right: LRO NAC frames, NASA Goddard/Intuitive Machines, enlarged 3×, ~400 m wide, north up. "
    "Crater 60 ft across. Predictions: this scenario's optical-only fit; Gray 2026 (Project Pluto); JPL Horizons #GA1A2/21.",
    fontsize=7.6,
    color=MUTED,
    wrap=True,
)
fig.savefig(HERE / "lro_impact_site.png", dpi=200, bbox_inches="tight", facecolor=SURF)
print("figure written")
