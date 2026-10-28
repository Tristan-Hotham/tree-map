"""Step 1. National Forest Inventory GB 2024: merge, spread each polygon over a 100 m grid, summarise by 1 km, 5 km,
10 km, county and nation.

Input (read in place): nfi_gb_2024_centroids.json.gz and nfi_missing.json.gz (641,642 polygon centroids with
interpreted type, category, country and area), and ceremonial counties / council areas (ONS boundaries, as built for
the how-roman-is-your-road project).

The NFI file gives each polygon's centroid and area, not its outline. I draw each polygon as a disc of the same area
centred on its centroid on a 100 m grid (polygons under 1 ha fill part of one cell). Where discs overlap, the smaller
polygon is drawn on top. Area totals use the polygon areas exactly; only where the area lands is approximate.
Outputs: data/nfi_types.csv, data/gb_1km.csv.gz, data/gb_5km.csv, data/gb_10km.csv, data/counties.csv, data/nations.csv,
and _work/nfi100.npz (temporary, for the map tiles).
"""
import json, os, sys, collections
import numpy as np, pandas as pd
import shapely
from shapely.geometry import shape
from pyproj import Transformer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

rows = load_nfi()
print("polygons", len(rows))
assert len(rows) == 641642
keys = collections.Counter((r[0], r[1], round(r[5], 3)) for r in rows)
dups = sum(v - 1 for v in keys.values() if v > 1)
print("duplicates on position and area", dups)

df = pd.DataFrame(rows, columns=["x", "y", "type", "category", "country", "area_ha"])
types = df.groupby(["category", "type"]).agg(polygons=("area_ha", "size"), area_ha=("area_ha", "sum")).reset_index()
types["group"] = [GROUPS[TYPE2GROUP[t]] if c == "Woodland" else "Not woodland" for c, t in zip(types.category, types.type)]
for c in ["England", "Scotland", "Wales"]:
    types[f"area_ha_{c.lower()}"] = [df[(df.type == t) & (df.category == k) & (df.country == c)].area_ha.sum() for k, t in zip(types.category, types.type)]
types = types.sort_values(["category", "area_ha"], ascending=[False, False])
types.round(1).to_csv(os.path.join(DATA, "nfi_types.csv"), index=False)
assert set(df[df.category == "Woodland"].type) <= set(TYPE2GROUP), set(df[df.category == "Woodland"].type) - set(TYPE2GROUP)

W = df[df.category == "Woodland"].copy()
W["g"] = W.type.map(TYPE2GROUP).astype(np.int8)
print("woodland polygons", len(W), "area", W.area_ha.sum())

# ---------- counties on a 1 km grid (cell centre inside the polygon) ----------
NX1, NY1 = NX // 10, NY // 10
tr = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
gj = json.load(open(COUNTIES))
cnames, cnation, cgeom = [], [], []
for f in gj["features"]:
    g = shape(f["geometry"])
    g = shapely.transform(g, lambda xy: np.c_[tr.transform(xy[:, 0], xy[:, 1])])
    cnames.append(f["properties"]["county"]); cnation.append(f["properties"]["nation"]); cgeom.append(g)
CTY = np.zeros((NY1, NX1), np.int16)   # 1-based county index, 0 = not land
xs = (np.arange(NX1) + .5) * 1000; ys = (np.arange(NY1) + .5) * 1000
for k, g in enumerate(cgeom):
    x0, y0, x1, y1 = g.bounds
    i0, i1 = max(0, int(x0 // 1000)), min(NX1, int(x1 // 1000) + 1)
    j0, j1 = max(0, int(y0 // 1000)), min(NY1, int(y1 // 1000) + 1)
    X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
    inside = shapely.contains_xy(g, X, Y)
    sub = CTY[j0:j1, i0:i1]; sub[inside & (sub == 0)] = k + 1
county_area = {cnames[k]: g.area / 1e6 for k, g in enumerate(cgeom)}
print("land cells", int((CTY > 0).sum()), "polygon land km2", round(sum(county_area.values())))

# ---------- spread polygons over the 100 m grid ----------
x = W.x.values.astype(np.float64); y = W.y.values.astype(np.float64); A = W.area_ha.values; G = W.g.values
ix = np.clip((x // CELL).astype(np.int64), 0, NX - 1); iy = np.clip((y // CELL).astype(np.int64), 0, NY - 1)
r = np.sqrt(A / np.pi)                     # radius in 100 m cells (1 cell = 1 ha)
rb = np.where(r < .5642, 0, np.round(r * 4) / 4)
I, V, GG, AA = [], [], [], []
for rad in np.unique(rb):
    sel = np.where(rb == rad)[0]
    if rad == 0:
        offs = np.array([[0, 0]])
    else:
        R_ = int(np.ceil(rad)) + 1
        dx, dy = np.meshgrid(np.arange(-R_, R_ + 1), np.arange(-R_, R_ + 1))
        m = dx ** 2 + dy ** 2 <= rad ** 2
        offs = np.c_[dx[m], dy[m]]
    n = len(offs)
    cx = (ix[sel][:, None] + offs[None, :, 0]).ravel(); cy = (iy[sel][:, None] + offs[None, :, 1]).ravel()
    ok = (cx >= 0) & (cx < NX) & (cy >= 0) & (cy < NY)
    I.append((cy * NX + cx)[ok]); V.append(np.repeat(A[sel] / n, n)[ok]); GG.append(np.repeat(G[sel], n)[ok]); AA.append(np.repeat(A[sel], n)[ok])
I = np.concatenate(I); V = np.concatenate(V); GG = np.concatenate(GG); AA = np.concatenate(AA)
print("stamp cells", len(I), "area kept", V.sum())
order = np.argsort(-AA, kind="stable")      # big first, so small polygons end up on top
TYPE = np.zeros(NX * NY, np.uint8); TYPE[I[order]] = GG[order]
COV = np.zeros(NX * NY, np.float32); np.add.at(COV, I, V.astype(np.float32))
COVq = np.clip(np.round(np.minimum(COV, 1) * 200), 0, 200).astype(np.uint8)
np.savez_compressed(os.path.join(WORK, "nfi100.npz"), type=TYPE.reshape(NY, NX), cov=COVq.reshape(NY, NX))
del TYPE, COV, COVq

# ---------- 1 km summaries ----------
cyx = I // NX; cxx = I % NX
i1 = (cyx // 10) * NX1 + (cxx // 10)
G1 = np.zeros((8, NY1 * NX1))
for g in range(1, 8):
    s = GG == g
    G1[g] = np.bincount(i1[s], weights=V[s], minlength=NY1 * NX1)
G1 = G1.reshape(8, NY1, NX1)
WOOD = G1[1:].sum(0)
# give every wooded cell outside the generalised coastline the county of its nearest land cell
from scipy import ndimage
_, (nj, ni) = ndimage.distance_transform_edt(CTY == 0, return_indices=True)
CTY2 = CTY[nj, ni]
cell_cty = np.where(CTY > 0, CTY, np.where(WOOD > 0, CTY2, 0))
np.savez_compressed(os.path.join(WORK, "grid1km.npz"), G1=G1.astype(np.float32), cty=cell_cty, land=(CTY > 0))
NAT = np.array([""] + cnation)


def table(k):
    """Summaries on k km squares (k = 1, 5, 10), keyed by the square's south-west corner in km."""
    ny, nx = NY1 // k, NX1 // k
    blk = lambda a: a[:ny * k, :nx * k].reshape(ny, k, nx, k).sum(axis=(1, 3))
    land = blk((CTY > 0).astype(float))
    gs = [blk(G1[g]) for g in range(1, 8)]
    wood = sum(gs)
    jj, ii = np.where((land > 0) | (wood > 0))
    out = pd.DataFrame({"e_km": ii * k, "n_km": jj * k, "land_km2": land[jj, ii]})
    cb = cell_cty[:ny * k, :nx * k].reshape(ny, k, nx, k).transpose(0, 2, 1, 3).reshape(ny, nx, k * k)
    cc = []
    for j, i in zip(jj, ii):
        v = cb[j, i]; v = v[v > 0]; cc.append(np.bincount(v).argmax() if len(v) else 0)
    cc = np.array(cc)
    out["county"] = [cnames[c - 1] if c else "" for c in cc]
    out["nation"] = [cnation[c - 1] if c else "" for c in cc]
    out["woodland_ha"] = wood[jj, ii]
    for g in range(1, 8):
        out[GROUP_KEYS[g] + "_ha"] = gs[g - 1][jj, ii]
    out["woodland_pct"] = np.where(out.land_km2 > 0, 100 * out.woodland_ha / (out.land_km2 * 100).clip(lower=1), np.nan).clip(max=100)
    bc = out.broadleaved_ha + out.mixed_broad_ha + out.conifer_ha + out.mixed_conifer_ha
    out["conifer_share_pct"] = np.where(bc > 0, 100 * (out.conifer_ha + out.mixed_conifer_ha) / bc.clip(lower=1e-9), np.nan)
    return out.round(2)


T1 = table(1); T5 = table(5); T10 = table(10)
T1[T1.woodland_ha > 0].to_csv(os.path.join(DATA, "gb_1km.csv.gz"), index=False)
T5.to_csv(os.path.join(DATA, "gb_5km.csv"), index=False)
T10.to_csv(os.path.join(DATA, "gb_10km.csv"), index=False)
print("1 km wooded cells", int((T1.woodland_ha > 0).sum()), "5 km cells", len(T5), "10 km", len(T10))

# ---------- counties and nations: exact polygon areas assigned by centroid ----------
cx1 = np.clip((x // 1000).astype(int), 0, NX1 - 1); cy1 = np.clip((y // 1000).astype(int), 0, NY1 - 1)
W["county"] = [cnames[c - 1] if c else "" for c in cell_cty[cy1, cx1]]
assert (W.county != "").all()
rowsC = []
for k, nm in enumerate(cnames):
    s = W[W.county == nm]
    d = {"county": nm, "nation": cnation[k], "land_km2": round(county_area[nm], 1), "woodland_ha": round(s.area_ha.sum(), 1)}
    for g in range(1, 8): d[GROUP_KEYS[g] + "_ha"] = round(s[s.g == g].area_ha.sum(), 1)
    rowsC.append(d)
C = pd.DataFrame(rowsC)
C["woodland_pct"] = (C.woodland_ha / (C.land_km2 * 100) * 100).round(2)
bc = C.broadleaved_ha + C.mixed_broad_ha + C.conifer_ha + C.mixed_conifer_ha
C["conifer_share_pct"] = (100 * (C.conifer_ha + C.mixed_conifer_ha) / bc).round(1)
C.sort_values("woodland_pct", ascending=False).to_csv(os.path.join(DATA, "counties.csv"), index=False)
N = C.groupby("nation").sum(numeric_only=True).reset_index()
N["woodland_pct"] = (N.woodland_ha / (N.land_km2 * 100) * 100).round(2)
bc = N.broadleaved_ha + N.mixed_broad_ha + N.conifer_ha + N.mixed_conifer_ha
N["conifer_share_pct"] = (100 * (N.conifer_ha + N.mixed_conifer_ha) / bc).round(1)
# woodland by the NFI's own country field, as a check on the county assignment
N["woodland_ha_nfi_country"] = [round(W[W.country == n].area_ha.sum(), 1) for n in N.nation]
N.to_csv(os.path.join(DATA, "nations.csv"), index=False)
print(N.to_string())
json.dump({"duplicates": int(dups), "polygons": len(rows), "woodland_polygons": int(len(W)),
           "nonwoodland_polygons": int((df.category != "Woodland").sum()), "county_names": cnames},
          open(os.path.join(WORK, "nfi_meta.json"), "w"))
