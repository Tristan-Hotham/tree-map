"""Step 5. All statistics: writes data/results.json (every number used on the page, in the paper, blog and collage),
plus the Forestry England tables and the page's small lookup files.

Run after steps 1 to 4: python3 code/05_analyse.py
"""
import json, os, sys, gzip, math, collections
import numpy as np, pandas as pd
from PIL import Image
from scipy.spatial import cKDTree
from pyproj import Transformer
import shapely
from shapely.geometry import shape
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = {}
to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
to_ll = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
r1 = lambda v: round(float(v), 1); r2 = lambda v: round(float(v), 2); r4 = lambda v: round(float(v), 4)


def gridref(e, n, digits=2):
    """OS grid reference letters plus digits for a point in metres, e.g. NY68 for a 10 km square."""
    e100, n100 = int(e // 100000), int(n // 100000)
    l1 = (19 - n100) - (19 - n100) % 5 + (e100 + 10) // 5
    l2 = (19 - n100) * 5 % 25 + e100 % 5
    if l1 > 7: l1 += 1
    if l2 > 7: l2 += 1
    a = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    k = 10 ** (5 - digits // 2) if digits else 1
    return a[l1] + a[l2] + (f"{int(e % 100000 // k):0{digits // 2}d}{int(n % 100000 // k):0{digits // 2}d}" if digits else "")


assert gridref(366959, 592420) == "NY69" and gridref(587163, 283062) == "TL88" and gridref(529000, 180000) == "TQ28"

# ---------------------------------------------------------------- places for naming things
osn = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False)
for c in ("x", "y", "lat", "lon"): osn[c] = osn[c].astype(float)
eng = (osn.lang2 == "eng") & osn.lang1.isin(["gla", "cym"])
osn["show"] = np.where(eng, osn.name2, osn.name1)
osn["cty"] = [(c or d).split(" - ")[-1] for c, d in zip(osn.county, osn.district)]
PP = osn[(osn.type == "populatedPlace") & osn.local_type.isin(["City", "Town", "Village"])].reset_index(drop=True)
FOREST = osn[(osn.local_type == "Woodland Or Forest") & osn.show.str.endswith("Forest")].reset_index(drop=True)
tPP = cKDTree(PP[["x", "y"]].values); tFO = cKDTree(FOREST[["x", "y"]].values)


def near_place(e, n):
    d, i = tPP.query([e, n]); r = PP.iloc[i]
    return {"place": r.show, "county": r.cty, "km": r1(d / 1000)}


def near_forest(e, n, maxkm=12):
    d, i = tFO.query([e, n])
    return FOREST.iloc[i].show if d <= maxkm * 1000 else ""


# ---------------------------------------------------------------- NFI
meta = json.load(open(os.path.join(WORK, "nfi_meta.json")))
types = pd.read_csv(os.path.join(DATA, "nfi_types.csv"))
N = pd.read_csv(os.path.join(DATA, "nations.csv")).set_index("nation")
C = pd.read_csv(os.path.join(DATA, "counties.csv"))
wood = types[types.category == "Woodland"]
R["nfi"] = {"polygons": meta["polygons"], "woodland_polygons": meta["woodland_polygons"], "nonwoodland_polygons": meta["nonwoodland_polygons"],
            "duplicates": meta["duplicates"], "main_file_rows": 525642, "missing_file_rows": 116000,
            "woodland_ha": r1(wood.area_ha.sum()), "nonwoodland_ha": r1(types[types.category != "Woodland"].area_ha.sum()),
            "types": [{"type": t, "group": g, "polygons": int(p), "area_ha": r1(a)} for t, g, p, a in zip(wood.type, wood.group, wood.polygons, wood.area_ha)]}
GBL = N.land_km2.sum()
grp = {GROUP_KEYS[g]: r1(N[GROUP_KEYS[g] + "_ha"].sum()) for g in range(1, 8)}
bl = grp["broadleaved"] + grp["mixed_broad"]; cf = grp["conifer"] + grp["mixed_conifer"]
R["gb"] = {"land_km2": r1(GBL), "woodland_ha": r1(N.woodland_ha.sum()), "woodland_pct": r2(N.woodland_ha.sum() / (GBL * 100) * 100),
           "groups_ha": grp, "groups_pct_of_woodland": {k: r2(v / N.woodland_ha.sum() * 100) for k, v in grp.items()},
           "conifer_share_pct": r1(cf / (bl + cf) * 100), "broadleaf_share_pct": r1(bl / (bl + cf) * 100),
           "woodland_kha": round(N.woodland_ha.sum() / 1000)}
R["nations"] = {}
for nm, r in N.iterrows():
    R["nations"][nm] = {"land_km2": r1(r.land_km2), "woodland_ha": r1(r.woodland_ha), "woodland_pct": r2(r.woodland_pct),
                        "conifer_share_pct": r1(r.conifer_share_pct), "broadleaf_share_pct": r1(100 - r.conifer_share_pct),
                        "share_of_gb_woodland_pct": r1(r.woodland_ha / N.woodland_ha.sum() * 100),
                        "groups_ha": {GROUP_KEYS[g]: r1(r[GROUP_KEYS[g] + "_ha"]) for g in range(1, 8)},
                        "felled_pct_of_woodland": r1(r.felled_ha / r.woodland_ha * 100)}
crow = lambda r: {"county": r.county, "nation": r.nation, "woodland_pct": r2(r.woodland_pct), "conifer_share_pct": r1(r.conifer_share_pct),
                  "land_km2": r1(r.land_km2), "woodland_ha": r1(r.woodland_ha),
                  "bl_land_pct": r2((r.broadleaved_ha + r.mixed_broad_ha) / (r.land_km2 * 100) * 100), "cf_land_pct": r2((r.conifer_ha + r.mixed_conifer_ha) / (r.land_km2 * 100) * 100)}
Cs = C.sort_values("woodland_pct", ascending=False)
R["counties"] = {"n": len(C), "most": [crow(r) for r in Cs.head(10).itertuples()], "least": [crow(r) for r in Cs.tail(6).iloc[::-1].itertuples()],
                 "by_nation": {nm: {"most": crow(Cs[Cs.nation == nm].iloc[0]), "least": crow(Cs[Cs.nation == nm].iloc[-1])} for nm in ["England", "Scotland", "Wales"]},
                 "most_conifer": [crow(r) for r in C[C.woodland_ha > 20000].sort_values("conifer_share_pct", ascending=False).head(5).itertuples()],
                 "most_broadleaf": [crow(r) for r in C[C.woodland_ha > 20000].sort_values("conifer_share_pct").head(5).itertuples()]}
ce = C[C.nation == "England"].sort_values("woodland_pct", ascending=False)
R["counties"]["england_top5"] = [crow(r) for r in ce.head(5).itertuples()]

T10 = pd.read_csv(os.path.join(DATA, "gb_10km.csv"))
T10 = T10[T10.land_km2 >= 50].copy()
T10["con_ha"] = T10.conifer_ha + T10.mixed_conifer_ha
T10["bl_ha"] = T10.broadleaved_ha + T10.mixed_broad_ha


def sq(r):
    e, n = r.e_km * 1000, r.n_km * 1000
    lon, lat = to_ll.transform(e + 5000, n + 5000)
    return {"ref": gridref(e + 1, n + 1), "county": r.county, "woodland_pct": r1(r.woodland_pct), "conifer_share_pct": r1(r.conifer_share_pct) if r.conifer_share_pct == r.conifer_share_pct else None,
            "conifer_ha": r1(r.con_ha), "broadleaf_ha": r1(r.bl_ha), "forest": near_forest(e + 5000, n + 5000), "lat": r4(lat), "lon": r4(lon), **near_place(e + 5000, n + 5000)}


R["squares10"] = {"n": len(T10), "most_wooded": [sq(r) for r in T10.sort_values("woodland_pct", ascending=False).head(10).itertuples()],
                  "most_conifer": [sq(r) for r in T10.sort_values("con_ha", ascending=False).head(10).itertuples()],
                  "most_broadleaf": [sq(r) for r in T10.sort_values("bl_ha", ascending=False).head(10).itertuples()],
                  "under1pct": int((T10.woodland_pct < 1).sum()), "over50pct": int((T10.woodland_pct >= 50).sum()),
                  "under1_by_county": T10[T10.woodland_pct < 1].county.value_counts().to_dict(),
                  "note": "10 km squares of the British National Grid with at least 50 km2 of land"}

# named forests: woodland within 10 km of a named point (1 km squares whose centre is within the circle)
g1 = np.load(os.path.join(WORK, "grid1km.npz")); G1 = g1["G1"]; land1 = g1["land"]
yy, xx = np.mgrid[0:G1.shape[1], 0:G1.shape[2]]


def circle(e, n, km=10):
    m = ((xx + .5) * 1000 - e) ** 2 + ((yy + .5) * 1000 - n) ** 2 <= (km * 1000) ** 2
    w = G1[1:, m].sum(); lnd = land1[m].sum()
    b = G1[1, m].sum() + G1[2, m].sum(); c = G1[3, m].sum() + G1[4, m].sum()
    return {"woodland_ha": r1(w), "land_km2": int(lnd), "woodland_pct": r1(w / max(lnd, 1)), "conifer_share_pct": r1(c / max(b + c, 1e-9) * 100),
            "felled_young_pct": r1((G1[5, m].sum() + G1[6, m].sum()) / max(w, 1e-9) * 100)}


def osn_point(name, local_type=None):
    s = osn[(osn.show == name) & ((osn.local_type == local_type) if local_type else True)]
    assert len(s) >= 1, name
    r = s.iloc[0]; return r.x, r.y, r.lat, r.lon


named = {}
for key, nm, lt in [("kielder", "Kielder Forest", "Woodland Or Forest"), ("thetford", "Thetford", "Town"), ("glentrool", "Glentrool Village", "Village"),
                    ("abernethy", "Abernethy Forest", "Woodland Or Forest"), ("new_forest", "Lyndhurst", "Village"), ("dean", "Cinderford", "Town"),
                    ("savernake", "Savernake Forest", None), ("chilterns", "High Wycombe", "Town")]:
    e, n, la, lo = osn_point(nm, lt)
    named[key] = {"name": nm, "lat": r4(la), "lon": r4(lo), **circle(e, n, 10)}
R["named"] = named
R["named_radius_km"] = 10

# ---------------------------------------------------------------- GBIF
gm = json.load(open(os.path.join(WORK, "gbif_meta.json")))
gb = json.load(open(os.path.join(DATA, "gbif", "gb.json")))
nr, nc = gb["rows"], gb["cols"]; P = np.array(gb["plants"], float); CON = np.array(gb["conifers"], float)
GG = {}
for g, (d, v) in gb["g"].items():
    a = np.zeros(nr * nc); a[np.cumsum(d)] = v; GG[g] = a
rr, cc = np.divmod(np.arange(nr * nc), nc)
lat = gb["lat_top"] - (rr + .5) * gb["deg"]; lon = gb["lon_left"] + (cc + .5) * gb["deg"]
E, Nn = map(np.asarray, to_bng.transform(lon, lat))
ii = (E // 1000).astype(int); jj = (Nn // 1000).astype(int); ok = (ii >= 0) & (jj >= 0) & (ii < land1.shape[1]) & (jj < land1.shape[0])
LND = np.zeros(nr * nc, bool); LND[ok] = land1[jj[ok], ii[ok]]
MINGB = 500
M = LND & (P >= MINGB)
gen_tot = {g: float(GG[g][LND].sum()) for g in GG}
order = sorted(gen_tot, key=lambda g: -gen_tot[g])
A = np.stack([GG[g] for g in order]); dom = A.argmax(0)
domc = collections.Counter(order[d] for d in dom[M])
COMMON = {"Quercus": "oak", "Fraxinus": "ash", "Fagus": "beech", "Betula": "birch", "Pinus": "pine", "Picea": "spruce", "Larix": "larch",
          "Taxus": "yew", "Ilex": "holly", "Sorbus": "rowan and whitebeam", "Alnus": "alder", "Castanea": "sweet chestnut", "Acer": "maple and sycamore",
          "Salix": "willow", "Prunus": "cherry and blackthorn", "Ulmus": "elm", "Populus": "poplar and aspen", "Tilia": "lime", "Carpinus": "hornbeam",
          "Juniperus": "juniper", "Aesculus": "horse chestnut", "Abies": "fir", "Pseudotsuga": "Douglas fir", "Eucalyptus": "eucalyptus",
          "Acacia": "acacia", "Ficus": "fig", "Adansonia": "baobab", "Cupressus": "cypress", "Platanus": "plane", "Juglans": "walnut",
          "Tsuga": "hemlock", "Thuja": "thuja (red cedar)", "Sequoia": "coast redwood", "Nothofagus": "southern beech", "Araucaria": "araucaria",
          "Podocarpus": "podocarp", "Ginkgo": "ginkgo", "Magnolia": "magnolia", "Liquidambar": "sweetgum", "Liriodendron": "tulip tree",
          "Carya": "hickory", "Olea": "olive", "Prosopis": "mesquite", "Vachellia": "thorn acacia (Vachellia)", "Senegalia": "Senegalia",
          "Casuarina": "she-oak", "Melaleuca": "paperbark", "Banksia": "banksia", "Callitris": "cypress pine", "Agathis": "kauri",
          "Shorea": "meranti (Shorea)", "Dipterocarpus": "keruing", "Tectona": "teak", "Swietenia": "mahogany", "Ceiba": "kapok",
          "Hevea": "rubber tree", "Cecropia": "cecropia", "Inga": "ice-cream bean (Inga)", "Rhizophora": "red mangrove", "Avicennia": "black mangrove",
          "Mangifera": "mango", "Syzygium": "Syzygium", "Brachystegia": "miombo (Brachystegia)", "Julbernardia": "Julbernardia",
          "Isoberlinia": "doka (Isoberlinia)", "Terminalia": "Terminalia", "Combretum": "bushwillow", "Colophospermum": "mopane",
          "Cryptomeria": "Japanese cedar", "Chamaecyparis": "false cypress", "Cinnamomum": "camphor and cinnamon", "Castanopsis": "chinquapin",
          "Lithocarpus": "stone oak", "Eschweilera": "Eschweilera", "Bertholletia": "Brazil nut", "Hymenaea": "jatoba", "Handroanthus": "ipe",
          "Dalbergia": "rosewood", "Pterocarpus": "padauk", "Khaya": "African mahogany", "Entandrophragma": "sapele", "Milicia": "iroko",
          "Sabal": "palmetto", "Phoenix": "date palm", "Nyssa": "tupelo", "Robinia": "black locust", "Dacrydium": "rimu (Dacrydium)", "Corymbia": "bloodwood (Corymbia)"}
missing_common = [g for g in json.load(open(os.path.join(DATA, "gbif", "world_base.json")))["genera"] if g not in COMMON]
assert not missing_common, missing_common
R["common"] = COMMON


def gbcell(t):
    e, n = E[t], Nn[t]
    return {"lat": r2(lat[t]), "lon": r2(lon[t]), "records": int(P[t]), **near_place(e, n)}


gbg = {}
for g in ["Quercus", "Fraxinus", "Fagus", "Betula", "Pinus", "Picea", "Larix", "Taxus", "Ilex", "Sorbus", "Alnus", "Castanea", "Acer", "Salix",
          "Juniperus", "Ulmus", "Carpinus", "Tilia", "Prunus", "Populus"]:
    s = np.where(M, GG[g] / np.maximum(P, 1), -1)
    top = np.argsort(-s)[:3]
    gbg[g] = {"records": int(gen_tot[g]), "share_pct": round(GG[g][M].sum() / P[M].sum() * 100, 3), "cells_dominant": int(domc.get(g, 0)),
              "top": [dict(gbcell(t), share_pct=r2(s[t] * 100)) for t in top]}
gbshare = {g: GG[g][M].sum() / P[M].sum() for g in GG}
LQ = np.stack([np.where(GG[g] >= 20, GG[g] / np.maximum(P, 1) / gbshare[g], 0) for g in order])
lqb = LQ.argmax(0); typc = collections.Counter(order[b] for b, c in zip(lqb[M], LQ.max(0)[M]) if c > 0)
R["gbif_gb_typical"] = typc.most_common(12)
R["gbif_gb"] = {"min_records": MINGB, "cells_land": int(LND.sum()), "cells_ok": int(M.sum()), "cell_deg": r4(gb["deg"]),
                "plant_records": int(P[LND].sum()), "median_records": int(np.median(P[LND])),
                "genus_records_rank": [[g, int(gen_tot[g])] for g in order[:12]], "dominant_cells": domc.most_common(12),
                "genera": gbg, "conifer_share_pct": r2(CON[M].sum() / P[M].sum() * 100)}

# world
wb = json.load(open(os.path.join(DATA, "gbif", "world_base.json")))
WC, WR, deg = wb["cols"], wb["rows"], wb["deg"]
gen = wb["genera"]
idx = np.array(wb["idx"]); Pw = np.array(wb["plants"], float); Cw = np.array(wb["conifers"], float)
wl = 90 - (idx // WC + .5) * deg; wlon = -180 + (idx % WC + .5) * deg
top1 = np.array([t[0] if t else -1 for t in wb["top"]]); top1n = np.array([n[0] if n else 0 for n in wb["topn"]], float)
# land, country and continent of every cell centre
ne = json.load(open(os.path.join(NE, "ne_50m_admin_0_countries.geojson")))
geoms = [shape(f["geometry"]) for f in ne["features"]]
cont = [f["properties"]["CONTINENT"] for f in ne["features"]]; cname = [f["properties"]["NAME"] for f in ne["features"]]
allr, allc = np.divmod(np.arange(WR * WC), WC)
alat = 90 - (allr + .5) * deg; alon = -180 + (allc + .5) * deg
owner = np.full(WR * WC, -1)
for k, g in enumerate(geoms):
    x0, y0, x1, y1 = g.bounds
    sel = np.where((alon >= x0) & (alon <= x1) & (alat >= y0) & (alat <= y1) & (owner < 0))[0]
    if len(sel): owner[sel[shapely.contains_xy(g, alon[sel], alat[sel])]] = k
area = np.cos(np.radians(alat)) * (deg * 111.32) ** 2      # km2 per cell
isl = owner >= 0
CONTS = ["Europe", "North America", "Asia", "Africa", "South America", "Oceania"]
PwAll = np.zeros(WR * WC); PwAll[idx] = Pw
cell_cont = np.array([cont[o] if o >= 0 else "" for o in owner])
R["world"] = {"cell_deg": r4(deg), "min_records": wb["min_records"], "genera_n": len(gen), "dropped": gm["dropped"],
              "plant_records": int(gm["plants_total"]), "conifer_records": int(gm["conifers_total"]),
              "land_cells": int(isl.sum())}
by = {}
for ct in CONTS:
    m = cell_cont == ct
    by[ct] = {"land_km2": round(area[m].sum()), "records": int(PwAll[m].sum()), "records_per_1000km2": round(PwAll[m].sum() / area[m].sum() * 1000),
              "cells_ok_pct": r1((area[m] * (PwAll[m] >= wb["min_records"])).sum() / area[m].sum() * 100)}
R["world"]["continents"] = by
tot_land_rec = PwAll[isl].sum()
R["world"]["europe_namerica_share_pct"] = r1((by["Europe"]["records"] + by["North America"]["records"]) / tot_land_rec * 100)
R["world"]["europe_namerica_land_pct"] = r1((by["Europe"]["land_km2"] + by["North America"]["land_km2"]) / area[isl].sum() * 100)
trop = isl & (np.abs(alat) < 23.44)
R["world"]["tropics_land_pct"] = r1(area[trop].sum() / area[isl].sum() * 100)
R["world"]["tropics_records_pct"] = r1(PwAll[trop].sum() / tot_land_rec * 100)
R["world"]["cells_ok_land_pct"] = r1((area[isl] * (PwAll[isl] >= wb["min_records"])).sum() / area[isl].sum() * 100)
R["world"]["tropics_cells_ok_pct"] = r1((area[trop] * (PwAll[trop] >= wb["min_records"])).sum() / area[trop].sum() * 100)
ntemp = isl & (alat >= 35) & (alat < 60)
R["world"]["north_temperate_cells_ok_pct"] = r1((area[ntemp] * (PwAll[ntemp] >= wb["min_records"])).sum() / area[ntemp].sum() * 100)
# dominant recorded genus, cells with enough records
okw = (Pw >= wb["min_records"]) & (top1 >= 0)
own_idx = owner[idx]
w_area = area[idx]
dom_area = collections.Counter()
for g, a in zip(top1[okw], w_area[okw]): dom_area[gen[g]] += a
tot_ok_area = w_area[okw].sum()
R["world"]["dominant_area"] = [[g, round(a), r1(a / tot_ok_area * 100)] for g, a in dom_area.most_common(15)]
R["world"]["dominant_genera_n"] = len(dom_area)
lqg = np.array(wb["lq"]); typ = collections.Counter()
for g, a in zip(lqg[okw], w_area[okw]):
    if g >= 0: typ[gen[g]] += a
R["world"]["typical_area"] = [[g, round(a), r1(a / tot_ok_area * 100)] for g, a in typ.most_common(15)]
R["world"]["typical_genera_n"] = len(typ)
R["world"]["lq_min"] = wb["lq_min"]
tcont = {}
for ct in CONTS:
    m = okw & (np.array([cont[o] if o >= 0 else "" for o in own_idx]) == ct) & (lqg >= 0)
    d = collections.Counter()
    for g, ar in zip(lqg[m], w_area[m]): d[gen[g]] += ar
    tcont[ct] = [[g, r1(v / w_area[m].sum() * 100)] for g, v in d.most_common(4)]
R["world"]["typical_by_continent"] = tcont
R["world"]["ok_area_km2"] = round(tot_ok_area)
# pines, oaks, eucalypts by continent: share of the qualifying area each dominates
pq = {}
for ct in CONTS:
    m = okw & (np.array([cont[o] if o >= 0 else "" for o in own_idx]) == ct)
    a = w_area[m].sum()
    d = collections.Counter()
    for g, ar in zip(top1[m], w_area[m]): d[gen[g]] += ar
    pq[ct] = {"ok_km2": round(a), "top": [[g, r1(v / a * 100)] for g, v in d.most_common(5)]}
R["world"]["by_continent"] = pq
# countries where a genus dominates most of the qualifying area
cty_dom = collections.defaultdict(collections.Counter); cty_area = collections.Counter()
for o, g, a in zip(own_idx[okw], top1[okw], w_area[okw]):
    if o < 0: continue
    cty_dom[cname[o]][gen[g]] += a; cty_area[cname[o]] += a
big = [c for c in cty_area if cty_area[c] > 150000]
R["world"]["country_top"] = {c: [cty_dom[c].most_common(1)[0][0], r1(cty_dom[c].most_common(1)[0][1] / cty_area[c] * 100)] for c in sorted(big)}
for g in ["Pinus", "Quercus", "Eucalyptus", "Acacia", "Picea", "Betula", "Salix", "Prunus", "Acer", "Ficus", "Adansonia"]:
    cs = sorted(((cty_dom[c][g] / cty_area[c], c) for c in big if cty_dom[c][g] > 0), reverse=True)[:5]
    R["world"].setdefault("genus_countries", {})[g] = [[c, r1(s * 100)] for s, c in cs]
# share of plant records that are tree genera overall, and the conifer share by continent
Gsum = np.zeros(WR * WC)
for g in gen:
    j = json.load(open(os.path.join(DATA, "gbif", "world", f"{g}.json")))
    Gsum[np.cumsum(j["d"])] += j["n"]
R["world"]["tree_genera_share_pct"] = r1(Gsum[isl].sum() / tot_land_rec * 100)
CwAll = np.zeros(WR * WC); CwAll[idx] = Cw
R["world"]["conifer_share_by_continent"] = {ct: r2(CwAll[cell_cont == ct].sum() / PwAll[cell_cont == ct].sum() * 100) for ct in CONTS}
R["world"]["checks"] = gm["checks"]
gaps = {}
for nm, la0, la1, lo0, lo1 in [("Congo basin", -4, 3, 15, 28), ("inner Amazon", -8, -1, -70, -58), ("Borneo interior", -1, 3, 112, 116), ("central Siberia", 60, 66, 90, 120), ("England", 51, 53, -2, 0)]:
    m = isl & (alat > la0) & (alat < la1) & (alon > lo0) & (alon < lo1)
    gaps[nm] = {"ok_pct": r1((PwAll[m] >= wb["min_records"]).mean() * 100), "median_records": int(np.median(PwAll[m])), "box": [la0, la1, lo0, lo1]}
R["world"]["gaps"] = gaps
genera_df = pd.read_csv(os.path.join(DATA, "genera.csv"))
R["world"]["genus_records_top"] = [[g, int(n)] for g, n in genera_df.sort_values("records_world", ascending=False)[["genus", "records_world"]].head(10).values]
R["world"]["uk_species_missing"] = gm["uk_species_missing"]
# example places for the text: dominant genus at a few cities
ex = {}
for nm, la, lo in [("Sydney", -33.87, 151.21), ("Madrid", 40.42, -3.70), ("Helsinki", 60.17, 24.94), ("Atlanta", 33.75, -84.39),
                   ("Cape Town", -33.92, 18.42), ("Mexico City", 19.43, -99.13), ("Tokyo", 35.68, 139.69), ("Manaus", -3.12, -60.02), ("London", 51.51, -0.13)]:
    c = int((90 - la) / deg) * WC + int((lo + 180) / deg)
    k = np.searchsorted(idx, c)
    if k < len(idx) and idx[k] == c:
        t = wb["top"][k]; n = wb["topn"][k]
        ex[nm] = {"records": int(Pw[k]), "top": [[gen[a], r2(b / Pw[k] * 100)] for a, b in zip(t[:3], n[:3])]}
R["world"]["examples"] = ex

# ---------------------------------------------------------------- Forestry England
fe = json.load(gzip.open(os.path.join(D17, "forestry_england_subcompartments.json.gz")))
F = pd.DataFrame(fe["rows"], columns=fe["columns"])
F["ha"] = F.area_m2 / 1e4
CONIF = {"Sitka spruce", "Corsican pine", "Scots pine", "Douglas fir", "Norway spruce", "Japanese larch", "Hybrid larch", "Lodgepole pine",
         "Western hemlock", "European larch", "Western red cedar", "Mixed conifers", "Grand Fir", "Lawsons cypress", "Serbian spruce",
         "Coast redwood", "Monterey pine", "Maritime pine", "Japanese cedar", "Macedonian pine", "Noble fir", "European silver fir",
         "other conifers", "Yew", "Leyland cypress", "Wellingtonia", "Bishop pine", "Oriental spruce", "Atlas cedar", "Austrian pine",
         "Juniper", "Loblolly pine", "Mountain pine", "Nordmann fir", "Ponderosa pine", "Red (pacific silver) fir", "Weymouth pine",
         "other Cedar", "other firs (Abies)", "other pines", "other spruces"}
F["kind"] = np.where(F.species.isna() | (F.species == ""), "", np.where(F.species.isin(CONIF), "conifer", "broadleaf"))
S = F[F.kind != ""]
sp = S.groupby("species").ha.sum().sort_values(ascending=False)
R["fe"] = {"subcompartments": len(F), "area_ha": r1(F.ha.sum()), "with_species": len(S), "species_ha": r1(S.ha.sum()), "species_n": int(S.species.nunique()),
           "conifer_pct": r1(S[S.kind == "conifer"].ha.sum() / S.ha.sum() * 100),
           "top_species": [[s, r1(a), r1(a / S.ha.sum() * 100), "conifer" if s in CONIF else "broadleaf"] for s, a in sp.head(12).items()],
           "land_use": F.groupby("land_use").ha.sum().sort_values(ascending=False).head(6).round(1).to_dict()}
Y = S[S.plant_year.notna()].copy(); Y["decade"] = (Y.plant_year // 10 * 10).astype(int)
R["fe"]["with_year"] = len(Y); R["fe"]["year_ha"] = r1(Y.ha.sum())
R["fe"]["before_1900_ha"] = r1(Y[Y.plant_year < 1900].ha.sum()); R["fe"]["year_1500_n"] = int((Y.plant_year == 1500).sum())
R["fe"]["year_round_decade_pct"] = r1((Y.plant_year % 10 == 0).mean() * 100)
dec = Y[(Y.decade >= 1900)].pivot_table(index="decade", columns="kind", values="ha", aggfunc="sum", fill_value=0)
dec["broadleaf_pct"] = dec.broadleaf / (dec.broadleaf + dec.conifer) * 100
dec.round(1).to_csv(os.path.join(DATA, "fe_planting_decades.csv"))
R["fe"]["decades"] = [[int(d), r1(r.conifer), r1(r.broadleaf), r1(r.broadleaf_pct)] for d, r in dec.iterrows()]
pk = dec.conifer.idxmax()
R["fe"]["conifer_peak_decade"] = int(pk); R["fe"]["conifer_peak_ha"] = r1(dec.conifer.max())
y5070 = Y[(Y.plant_year >= 1950) & (Y.plant_year < 1980)]
R["fe"]["share_1950_1979_conifer_pct"] = r1(y5070[y5070.kind == "conifer"].ha.sum() / Y[Y.kind == "conifer"].ha.sum() * 100)
R["fe"]["broadleaf_pct_1950s"] = r1(dec.loc[1950, "broadleaf_pct"]); R["fe"]["broadleaf_pct_1960s"] = r1(dec.loc[1960, "broadleaf_pct"])
R["fe"]["broadleaf_pct_1990s"] = r1(dec.loc[1990, "broadleaf_pct"]); R["fe"]["broadleaf_pct_2000s"] = r1(dec.loc[2000, "broadleaf_pct"])
R["fe"]["broadleaf_pct_2010s"] = r1(dec.loc[2010, "broadleaf_pct"])
R["fe"]["pre1920_ha"] = r1(Y[(Y.plant_year >= 1900) & (Y.plant_year < 1920)].ha.sum())
R["fe"]["after1919_conifer_pct"] = r1(Y[(Y.plant_year >= 1920) & (Y.plant_year < 1990) & (Y.kind == "conifer")].ha.sum() / Y[(Y.plant_year >= 1920) & (Y.plant_year < 1990)].ha.sum() * 100)
# what was planted when: top species per period
per = {}
for a, b in [(1920, 1950), (1950, 1980), (1980, 2000), (2000, 2030)]:
    s = Y[(Y.plant_year >= a) & (Y.plant_year < b)].groupby("species").ha.sum().sort_values(ascending=False)
    per[f"{a}_{b - 1}"] = [[k, r1(v / s.sum() * 100)] for k, v in s.head(4).items()]
R["fe"]["periods"] = per
spc = S.groupby(["species", "kind"]).agg(subcompartments=("ha", "size"), area_ha=("ha", "sum"), median_plant_year=("plant_year", "median")).reset_index().sort_values("area_ha", ascending=False)
spc.round(1).to_csv(os.path.join(DATA, "fe_species.csv"), index=False)
# districts
R["fe"]["districts"] = {d: r1(v) for d, v in S.groupby("district").ha.sum().sort_values(ascending=False).items()}
# page points: lat, lon, species index, plant year, area
spl = list(sp.index)
lo_, la_ = to_ll.transform(F.x.values.astype(float), F.y.values.astype(float))
pts = []
for r, a, b in zip(F.itertuples(), la_, lo_):
    pts.append([round(a, 5), round(b, 5), spl.index(r.species) if r.kind else -1, int(r.plant_year) if r.plant_year == r.plant_year and r.plant_year else 0,
                round(r.ha, 2), r.land_use or ""])
json.dump({"species": spl, "kind": ["conifer" if s in CONIF else "broadleaf" for s in spl], "rows": pts},
          open(os.path.join(DATA, "fe_points.json"), "w"), separators=(",", ":"))

# ---------------------------------------------------------------- page lookup grid: 1 km values as a PNG on the National Grid
NX1, NY1 = G1.shape[2], G1.shape[1]
wood1 = G1[1:].sum(0)
pct = np.where(land1, wood1 / 100 * 100 / 100, np.where(wood1 > 0, 100, 255))   # ha per km2 is % already
pct = np.where(land1 | (wood1 > 0), np.clip(np.round(wood1 / 100 * 100 / 100 * 1), 0, 100), 255)
pct = np.where(land1 | (wood1 > 0), np.clip(np.round(wood1), 0, 100), 255)       # woodland ha in a 100 ha square = %
b1 = G1[1] + G1[2]; c1 = G1[3] + G1[4]
shr = np.where(b1 + c1 > 0, np.round(c1 / np.maximum(b1 + c1, 1e-9) * 100), 255)
domg = np.where(wood1 > 0, G1[1:].argmax(0) + 1, 0)
img = np.dstack([pct, shr, domg]).astype(np.uint8)[::-1]        # north at the top
os.makedirs(os.path.join(DATA, "gb"), exist_ok=True)
Image.fromarray(img, "RGB").save(os.path.join(DATA, "gb", "km1.png"), optimize=True)
# 5 km breakdown for the click panel
T5 = pd.read_csv(os.path.join(DATA, "gb_5km.csv"))
T5 = T5[T5.woodland_ha > 0]
json.dump({"cols": ["e_km", "n_km", "land_km2"] + [k + "_ha" for k in GROUP_KEYS[1:]],
           "rows": [[int(r.e_km), int(r.n_km), r1(r.land_km2)] + [round(getattr(r, k + "_ha")) for k in GROUP_KEYS[1:]] for r in T5.itertuples()]},
          open(os.path.join(DATA, "gb", "cells5.json"), "w"), separators=(",", ":"))
R["groups"] = {"names": GROUPS[1:], "keys": GROUP_KEYS[1:], "cols": GROUP_COL[1:]}
R["mix_key"] = json.load(open(os.path.join(WORK, "mix_key.json")))
R["tiles"] = json.load(open(os.path.join(WORK, "tile_stats.json")))
R["retrieved"] = "28 October 2026"
R["genus_cols"] = {g: genus_colour(g, f) for g, f in zip(wb["genera"], wb["families"])}

json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: R[k] for k in ["gb", "nations"]}, indent=0)[:3000])
print("counties", [(c["county"], c["woodland_pct"]) for c in R["counties"]["most"][:6]])
print("squares", [(s["ref"], s["forest"], s["place"], s["woodland_pct"]) for s in R["squares10"]["most_conifer"]])
print("named", {k: (v["woodland_pct"], v["conifer_share_pct"]) for k, v in named.items()})
print("world", json.dumps({k: R["world"][k] for k in R["world"] if k not in ("country_top", "checks")}, indent=0)[:6000])
print("fe", json.dumps(R["fe"], indent=0)[:4000])
