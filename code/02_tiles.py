"""Step 2. Map tiles for the Great Britain view (Web Mercator XYZ, 256 px, paletted PNG).

data/tiles/wood/{z}/{x}/{y}.png   NFI woodland by type, zooms 5 to 10 (100 m grid at zoom 10, coarser grids below).
                                  Colour = type group; opacity = share of the pixel that is woodland.
data/tiles/mix1/...  and mix5/... Woodland cover and broadleaf / conifer mix on 1 km and 5 km squares.
data/tiles/hill/...               Hill shading (dark where slopes face away from a light in the north west),
                                  from the Terrain Tiles elevation (zoom 10, about 100 m), zooms 5 to 9.
Run: python3 code/02_tiles.py
"""
import os, sys, json, math, shutil
import numpy as np
from PIL import Image
from pyproj import Transformer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

TD = os.path.join(DATA, "tiles")
tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
WHICH = sys.argv[1:] or ["wood", "mix", "hill"]


def tiles_for(z, bbox=GB_BBOX):
    x0, y0 = lonlat_to_tile(bbox[0], bbox[3], z); x1, y1 = lonlat_to_tile(bbox[2], bbox[1], z)
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def save_p(arr, pal, alpha, path):
    """arr: uint8 palette indices (0 = transparent)."""
    im = Image.fromarray(arr, "P")
    flat = []
    for c in pal: flat += list(c)
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.info["transparency"] = bytes(alpha + [0] * (256 - len(alpha)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True, transparency=bytes(alpha))


def bng_of_tile(z, x, y):
    LON, LAT = tile_pixel_lonlat(z, x, y)
    E, N = tr.transform(LON.ravel(), LAT.ravel())
    return np.asarray(E).reshape(256, 256), np.asarray(N).reshape(256, 256), LAT


stats = {}
# ------------------------------------------------------------------ woodland by type
if "wood" in WHICH:
    shutil.rmtree(os.path.join(TD, "wood"), ignore_errors=True)
    z = np.load(os.path.join(WORK, "nfi100.npz"))
    TYPE, COV = z["type"], z["cov"].astype(np.float32) / 200
    levels = [(TYPE, COV)]
    S = np.stack([np.where(TYPE == g, COV, 0).astype(np.float32) for g in range(1, 8)])
    for L in range(1, 6):
        ny, nx = S.shape[1] // 2, S.shape[2] // 2
        S = S[:, :ny * 2, :nx * 2].reshape(7, ny, 2, nx, 2).sum(axis=(2, 4))
        cov = S.sum(0) / (4 ** L)
        typ = (S.argmax(0) + 1).astype(np.uint8); typ[cov <= 0] = 0
        levels.append((typ, cov))
    del S
    # palette: 3 cover levels per group
    pal, alpha = [(0, 0, 0)], [0]
    for g in range(1, 8):
        for a in (120, 190, 255):
            pal.append(hexrgb(GROUP_COL[g])); alpha.append(a)
    n = 0; size = 0
    for zz in range(5, 11):
        for (x, y) in tiles_for(zz):
            E, N, LAT = bng_of_tile(zz, x, y)
            px = 156543.034 * math.cos(math.radians(float(LAT.mean()))) / 2 ** zz
            L = int(min(5, max(0, round(math.log2(max(px, 100) / 100)))))
            typ, cov = levels[L]
            c = CELL * 2 ** L
            i = np.floor(E / c).astype(int); j = np.floor(N / c).astype(int)
            ok = (i >= 0) & (j >= 0) & (i < typ.shape[1]) & (j < typ.shape[0])
            t = np.zeros((256, 256), np.uint8); cv = np.zeros((256, 256), np.float32)
            t[ok] = typ[j[ok], i[ok]]; cv[ok] = cov[j[ok], i[ok]]
            if not t.any(): continue
            lvl = np.where(cv < .3, 0, np.where(cv < .65, 1, 2))
            idx = np.where(t > 0, (t.astype(int) - 1) * 3 + lvl + 1, 0).astype(np.uint8)
            p = os.path.join(TD, "wood", str(zz), str(x), f"{y}.png")
            save_p(idx, pal, alpha, p); n += 1; size += os.path.getsize(p)
        print("wood z", zz, "tiles", n, "MB", round(size / 1e6, 1), flush=True)
    stats["wood"] = {"tiles": n, "bytes": size}
    del levels, TYPE, COV

# ------------------------------------------------------------------ cover and mix on 1 km and 5 km squares
COVER_BREAKS = [5, 15, 30, 50]          # % woodland
SHARE_BREAKS = [20, 40, 60, 80]         # conifer share of broadleaf + conifer, %
MIX_COLS = ["#3C8F35", "#5E9B47", "#6E9A7C", "#3A7A7E", "#1C4F66"]   # broadleaf to conifer
MIX_ALPHA = [70, 120, 170, 215, 255]
if "mix" in WHICH:
    g = np.load(os.path.join(WORK, "grid1km.npz"))
    G1, land = g["G1"], g["land"]
    pal, alpha = [(0, 0, 0)], [0]
    for s in range(5):
        for a in MIX_ALPHA:
            pal.append(hexrgb(MIX_COLS[s])); alpha.append(a)
    for k, name, zmax in ((1, "mix1", 9), (5, "mix5", 8)):
        shutil.rmtree(os.path.join(TD, name), ignore_errors=True)
        ny, nx = G1.shape[1] // k, G1.shape[2] // k
        B = G1[:, :ny * k, :nx * k].reshape(8, ny, k, nx, k).sum(axis=(2, 4))
        lnd = land[:ny * k, :nx * k].reshape(ny, k, nx, k).sum(axis=(1, 3)) * 100.0   # ha
        wood = B[1:].sum(0)
        pct = np.where(lnd > 0, 100 * wood / np.maximum(lnd, 1), np.where(wood > 0, 100, 0)).clip(0, 100)
        bl = B[1] + B[2]; cf = B[3] + B[4]
        share = np.where(bl + cf > 0, 100 * cf / np.maximum(bl + cf, 1e-9), -1)
        cc = np.digitize(pct, COVER_BREAKS); sc = np.digitize(share, SHARE_BREAKS)
        IDX = np.where((wood > 0) & (pct >= .5) & (share >= 0), sc * 5 + cc + 1, 0).astype(np.uint8)
        n = size = 0
        for zz in range(5, zmax + 1):
            for (x, y) in tiles_for(zz):
                E, N, _ = bng_of_tile(zz, x, y)
                i = np.floor(E / (1000 * k)).astype(int); j = np.floor(N / (1000 * k)).astype(int)
                ok = (i >= 0) & (j >= 0) & (i < nx) & (j < ny)
                t = np.zeros((256, 256), np.uint8); t[ok] = IDX[j[ok], i[ok]]
                if not t.any(): continue
                p = os.path.join(TD, name, str(zz), str(x), f"{y}.png")
                save_p(t, pal, alpha, p); n += 1; size += os.path.getsize(p)
        print(name, "tiles", n, "MB", round(size / 1e6, 1), flush=True)
        stats[name] = {"tiles": n, "bytes": size}
    json.dump({"cover_breaks": COVER_BREAKS, "share_breaks": SHARE_BREAKS, "cols": MIX_COLS, "alpha": MIX_ALPHA},
              open(os.path.join(WORK, "mix_key.json"), "w"))

# ------------------------------------------------------------------ hill shading from the zoom 10 terrain tiles
if "hill" in WHICH:
    shutil.rmtree(os.path.join(TD, "hill"), ignore_errors=True)
    sys.path.insert(0, "/home/claude/hist/within-sight/code")
    from dem import DEM
    dem = DEM()
    Z0 = 10
    tx0, ty0 = lonlat_to_tile(GB_BBOX[0] - 2.2, GB_BBOX[3] + .3, Z0); tx1, ty1 = lonlat_to_tile(GB_BBOX[2] + .3, GB_BBOX[1] - .3, Z0)
    gx = np.arange(tx0 * 256, (tx1 + 1) * 256); gy = np.arange(ty0 * 256, (ty1 + 1) * 256)
    E = np.zeros((len(gy), len(gx)), np.float32)
    for r0 in range(0, len(gy), 512):
        GX, GY = np.meshgrid(gx, gy[r0:r0 + 512])
        E[r0:r0 + 512] = dem.nearest(GX.ravel() + .5, GY.ravel() + .5).reshape(GX.shape)
    E = np.maximum(E, 0)
    print("dem window", E.shape, float(E.max()))
    # downsample once to zoom 9 (about 200 m) before shading, which is all the hill tiles need
    E9 = E[:E.shape[0] // 2 * 2, :E.shape[1] // 2 * 2].reshape(E.shape[0] // 2, 2, E.shape[1] // 2, 2).mean(axis=(1, 3))
    del E
    lat_c = 55.0
    cell = 156543.034 * 2 * math.cos(math.radians(lat_c)) / 2 ** Z0
    gyy, gxx = np.gradient(E9 * 3.0, cell)
    dzdx, dzdy = gxx, -gyy
    slope = np.arctan(np.hypot(dzdx, dzdy)); aspect = np.arctan2(-dzdx, -dzdy)
    alt = np.radians(45); shade = np.zeros_like(E9)
    for az, w in ((315, .6), (270, .2), (0, .2)):
        a = np.radians(az); shade += w * (np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(a - aspect))
    v = np.clip(shade / np.sin(alt), 0, 1.25)
    dark = np.clip(1 - v, 0, 1) ** .8                     # 0 flat or lit, 1 deep shadow
    light = np.clip(v - 1, 0, .25) / .25                  # slopes facing the light
    del slope, aspect, gyy, gxx, dzdx, dzdy, shade
    # 16 shadow levels (black, rising alpha) and 4 light levels (white, low alpha)
    q = np.where(dark > .04, 1 + np.minimum(15, (dark * 16).astype(int)), np.where(light > .1, 17 + np.minimum(3, (light * 4).astype(int)), 0)).astype(np.uint8)
    pal = [(0, 0, 0)] + [(20, 24, 22)] * 16 + [(255, 255, 255)] * 4
    alpha = [0] + [int(12 + 220 * (k / 16) ** .9) for k in range(1, 17)] + [40, 60, 80, 100]
    base_x, base_y = tx0 * 128, ty0 * 128          # zoom 9 global pixel of E9[0, 0]
    n = size = 0
    for zz in range(5, 10):
        f = 2 ** (9 - zz)
        for (x, y) in tiles_for(zz, (GB_BBOX[0] - 2.2, GB_BBOX[1] - .2, GB_BBOX[2] + .2, GB_BBOX[3] + .2)):
            px = (x * 256 + np.arange(256)) * f + f // 2 - base_x; py = (y * 256 + np.arange(256)) * f + f // 2 - base_y
            if px.max() < 0 or py.max() < 0 or px.min() >= q.shape[1] or py.min() >= q.shape[0]: continue
            pxc = np.clip(px, 0, q.shape[1] - 1); pyc = np.clip(py, 0, q.shape[0] - 1)
            if f == 1:
                t = q[np.ix_(pyc, pxc)]
            else:
                # average the darkness over the f by f block, then requantise
                d = np.zeros((256, 256), np.float32)
                for dy in range(f):
                    for dx in range(f):
                        d += dark[np.ix_(np.clip(py - f // 2 + dy, 0, q.shape[0] - 1), np.clip(px - f // 2 + dx, 0, q.shape[1] - 1))]
                d /= f * f
                t = np.where(d > .04, 1 + np.minimum(15, (d * 16).astype(int)), 0).astype(np.uint8)
            t[(px < 0) | (px >= q.shape[1])] = 0; t[:, :][(py < 0) | (py >= q.shape[0]), :] = 0
            if not t.any(): continue
            p = os.path.join(TD, "hill", str(zz), str(x), f"{y}.png")
            save_p(t, pal, alpha, p); n += 1; size += os.path.getsize(p)
        print("hill z", zz, "tiles", n, "MB", round(size / 1e6, 1), flush=True)
    stats["hill"] = {"tiles": n, "bytes": size}

old = {}
if os.path.exists(os.path.join(WORK, "tile_stats.json")): old = json.load(open(os.path.join(WORK, "tile_stats.json")))
old.update(stats); json.dump(old, open(os.path.join(WORK, "tile_stats.json"), "w"))
