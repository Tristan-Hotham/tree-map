"""Shared drawing helpers for the header, blog and paper figures and the Reddit collage (matplotlib).

Fonts: FONT_DIR holding Fraunces, Source Serif 4 and IBM Plex Mono (from github.com/google/fonts); otherwise
matplotlib's defaults are used. Maps are drawn from the project's own data files (no web tiles).
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import pandas as pd
from pyproj import Transformer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

FD = os.environ.get("FONT_DIR", "/root/.fonts")
DISP = None
if os.path.isdir(FD):
    for f in os.listdir(FD):
        if f.endswith(".ttf"): fm.fontManager.addfont(os.path.join(FD, f))
    fr = [f for f in os.listdir(FD) if f.startswith("Fraunces")]
    if fr: DISP = fm.FontProperties(fname=os.path.join(FD, fr[0]), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, RULE, CTX, SEA = "#F6F3EA", "#1B231F", "#5F6760", "#DCD6C6", "#E9E4D6", "#DCE5E6"
LEAF, CON, BARK = "#3E8E3A", "#1D5C5E", "#8A5A22"
plt.rcParams.update({"font.family": SER, "font.size": 13, "axes.edgecolor": MUT, "axes.labelcolor": FG, "xtick.color": MUT, "ytick.color": MUT,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.facecolor": BG, "figure.facecolor": BG, "axes.facecolor": BG})
R = json.load(open(os.path.join(DATA, "results.json")))
to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255
COMMON = R["common"]
gname = lambda g: COMMON[g] if g in COMMON.get(g, "") else (f"{COMMON[g]} ({g})" if g in COMMON else g)


def polys_of(g):
    if g["type"] == "Polygon": return [g["coordinates"]]
    if g["type"] == "MultiPolygon": return g["coordinates"]
    if g["type"] == "GeometryCollection": return [p for x in g["geometries"] for p in polys_of(x)]
    return []


def gb_outline():
    """County polygons projected to British National Grid (km), as lists of rings."""
    gj = json.load(open(os.path.join(DATA, "ctx", "gb_borders.json")))
    rings = []
    for f in gj["features"]:
        for p in polys_of(f["geometry"]):
            a = np.array(p[0]); e, n = to_bng.transform(a[:, 0], a[:, 1]); rings.append(np.c_[e, n] / 1000)
    return rings


def draw_land(ax, rings, fc=CTX, ec="none", lw=0, z=0):
    ax.add_collection(PatchCollection([Polygon(r) for r in rings], facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))


def gb_type_rgba(level=1, bg=None):
    """Woodland on a 1 km (level 1) or coarser grid: colour of the biggest group, opacity from cover. North up."""
    z = np.load(os.path.join(WORK, "grid1km.npz")); G1 = z["G1"]
    if level > 1:
        k = level; ny, nx = G1.shape[1] // k, G1.shape[2] // k
        G1 = G1[:, :ny * k, :nx * k].reshape(8, ny, k, nx, k).sum(axis=(2, 4)) / (k * k)
    wood = G1[1:].sum(0); dom = G1[1:].argmax(0)
    cols = np.array([hexrgb(c) for c in GROUP_COL[1:]])
    rgba = np.zeros(wood.shape + (4,)); rgba[..., :3] = cols[dom]
    rgba[..., 3] = np.clip(np.sqrt(wood / 100) * 1.25, 0, 1) * (wood > 0)
    return rgba[::-1], (0, wood.shape[1] * level, 0, wood.shape[0] * level)


def world_rings():
    gj = json.load(open(os.path.join(DATA, "ctx", "world.json")))
    rings = []
    for f in gj["features"]:
        for p in polys_of(f["geometry"]): rings.append(np.array(p[0]))
    return rings


def world_grid(mode="typ", genus=None):
    """RGBA image of the world grid (equirectangular, 0.35 degrees)."""
    wb = json.load(open(os.path.join(DATA, "gbif", "world_base.json")))
    W, H = wb["cols"], wb["rows"]; img = np.zeros((H * W, 4))
    idx = np.array(wb["idx"]); P = np.array(wb["plants"], float); mn = wb["min_records"]
    a = np.where(P < mn, 0, np.where(P < mn * 10, .45 + .5 * np.log10(np.maximum(P, 1) / mn), .95))
    if mode in ("typ", "dom"):
        g = np.array(wb["lq"]) if mode == "typ" else np.array([t[0] if t else -1 for t in wb["top"]])
        cols = np.array([hexrgb(R["genus_cols"][x]) for x in wb["genera"]])
        ok = g >= 0
        img[idx[ok], :3] = cols[g[ok]]; img[idx[ok], 3] = a[ok]
    elif mode == "effort":
        from matplotlib.colors import LinearSegmentedColormap
        cm = LinearSegmentedColormap.from_list("e", ["#F4E7D3", "#E8C98F", "#D69E52", "#B86E2E", "#8A4520", "#5A2A16"])
        img[idx] = cm(np.clip(np.log10(np.maximum(P, 1)) / 6, 0, 1)); img[idx, 3] = .95
    return img.reshape(H, W, 4), wb


def save(fig, path, **kw):
    fig.savefig(path, dpi=kw.pop("dpi", 200), facecolor=kw.pop("facecolor", BG), **kw)
    plt.close(fig)
