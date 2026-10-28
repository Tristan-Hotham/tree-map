"""Step 3. GBIF occurrence density grids: decode, check, and turn into shares of all vascular plant records.

Input (read in place): gbif_trees.json.gz (zoom 2 EPSG:4326 vector tiles, squareSize 8, for 90 tree genera) and
gbif_baseline.json.gz (the same grids for Tracheophyta, Pinopsida and Magnoliopsida).
Tiles are 45 by 45 degrees at zoom 2 (eight across, four down); each holds 512 by 512 bins of 45/512 = 0.0879 degrees.
The decoder returns y upwards, so bin row = 511 - y // 8. Checked below on known places.
Two genera (Cedrus, Washingtonia) were matched by GBIF only to Tracheophyta, so their tiles are the plant baseline,
not the genus; they are dropped. The 44 UK species grids at zoom 6 named in the download notes are not in the file.

Outputs: data/gbif/world_base.json (0.35 degree world grid: plant records, conifer records, top genera per cell),
data/gbif/world/<Genus>.json (record counts per cell, loaded by the page when a genus is picked),
data/gbif/gb.json (0.088 degree grid over Great Britain: plant records and every genus),
data/world_cells.csv, data/gb_gbif_cells.csv, data/genera.csv and _work/gbif.npz for the analysis.
"""
import gzip, json, os, sys, base64, shutil
import numpy as np, pandas as pd
import mapbox_vector_tile as mvt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

NB = 512                       # bins per tile side
NCOL, NROW = 8 * NB, 4 * NB    # 4096 by 2048 bins, 0.0879 degrees
DEG = 45 / NB
T = json.load(gzip.open(os.path.join(D17, "gbif_trees.json.gz")))
B = json.load(gzip.open(os.path.join(D17, "gbif_baseline.json.gz")))


def decode(tiles, taxon):
    idx, val = [], []
    for k, v in tiles.items():
        tx, zxy = k.split("|")
        if tx != taxon: continue
        z, x, y = map(int, zxy.split("/"))
        if z != 2: continue
        L = mvt.decode(base64.b64decode(v)).get("occurrence")
        if not L: continue
        assert L["extent"] == 4096
        for f in L["features"]:
            c = f["geometry"]["coordinates"][0]
            i = min(p[0] for p in c) // 8; j = min(p[1] for p in c) // 8
            assert max(p[0] for p in c) - min(p[0] for p in c) == 8
            idx.append((y * NB + (NB - 1 - j)) * NCOL + x * NB + i); val.append(f["properties"]["total"])
    idx = np.array(idx, np.int64); val = np.array(val, np.float64)
    out = np.zeros(NCOL * NROW, np.float64); np.add.at(out, idx, val)
    return out


def cell_of(lat, lon):
    return int((90 - lat) / DEG) * NCOL + int((lon + 180) / DEG)


plants = decode(B["tiles"], "Tracheophyta")
conif = decode(B["tiles"], "Pinopsida")
dicot = decode(B["tiles"], "Magnoliopsida")
keys = T["keys"]
dropped = [g for g, k in keys.items() if not k.get("uk") and k.get("match") != "EXACT"]
genera = [g for g, k in keys.items() if not k.get("uk") and k.get("match") == "EXACT"]
uk_species = [g for g, k in keys.items() if k.get("uk")]
have_uk = sorted({k.split("|")[0] for k in T["tiles"]} & set(uk_species))
print("genera", len(genera), "dropped", dropped, "UK species with tiles", have_uk)
GEN = np.zeros((len(genera), NCOL * NROW), np.float32)
for k, g in enumerate(genera):
    GEN[k] = decode(T["tiles"], g)
tot_gen = GEN.sum(1)
# sanity: a genus never has more records in a cell than all vascular plants
over = (GEN > plants[None, :] * 1.0001 + 1).sum()
print("cells where a genus exceeds all plants", int(over))

checks = {}
for nm, lat, lon in [("London", 51.51, -0.12), ("Canberra", -35.28, 149.13), ("Madrid", 40.42, -3.70), ("Kielder", 55.23, -2.58),
                     ("Aviemore", 57.19, -3.83), ("Morondava (baobabs)", -20.25, 44.42)]:
    c = cell_of(lat, lon)
    top = np.argsort(-GEN[:, c])[:3]
    checks[nm] = {"plants": int(plants[c]), "top": [[genera[t], int(GEN[t, c])] for t in top]}
print(json.dumps(checks, indent=0))
assert "Eucalyptus" in [t[0] for t in checks["Canberra"]["top"][:2]] and checks["Morondava (baobabs)"]["top"][0][0] == "Adansonia"
assert checks["London"]["top"][1][0] == "Platanus"  # the London plane
assert checks["London"]["plants"] > 1000

np.savez_compressed(os.path.join(WORK, "gbif.npz"), plants=plants.astype(np.float32), conif=conif.astype(np.float32),
                    dicot=dicot.astype(np.float32), GEN=GEN)

# ---------------------------------------------------------------- world grid at 0.35 degrees (4 by 4 bins)
F = 4
WC, WR = NCOL // F, NROW // F
agg = lambda a: a.reshape(WR, F, WC, F).sum(axis=(1, 3)).ravel()
P4 = agg(plants); C4 = agg(conif)
G4 = np.stack([agg(GEN[k]) for k in range(len(genera))])
MINREC = 200
cells = np.where(P4 > 0)[0]
order = np.argsort(-G4[:, cells], axis=0)[:5]          # top five genera per cell
base = {"deg": DEG * F, "cols": WC, "rows": WR, "lat_top": 90, "lon_left": -180, "min_records": MINREC,
        "genera": genera, "families": [keys[g]["family"] for g in genera],
        "idx": cells.tolist(), "plants": P4[cells].astype(int).tolist(), "conifers": C4[cells].astype(int).tolist(),
        "top": [[int(order[r, n]) if G4[order[r, n], c] > 0 else -1 for r in range(5)] for n, c in enumerate(cells)],
        "topn": [[int(G4[order[r, n], c]) for r in range(5) if G4[order[r, n], c] > 0] for n, c in enumerate(cells)]}
for n, t in enumerate(base["top"]):
    base["top"][n] = [x for x in t if x >= 0]
# "most typical" genus: the highest share of the cell's plant records relative to the genus's share of all records
# in the world (a location quotient), among genera with at least LQMIN records in the cell
LQMIN = 20
wshare = G4.sum(1) / P4.sum()
lq = np.where(G4[:, cells] >= LQMIN, G4[:, cells] / np.maximum(P4[cells], 1)[None, :] / wshare[:, None], 0)
best = lq.argmax(0)
base["lq"] = [int(b) if lq[b, n] > 0 else -1 for n, b in enumerate(best)]
base["lqv"] = [round(float(lq[b, n]), 1) for n, b in enumerate(best)]
base["lq_min"] = LQMIN
base["world_share"] = [float(f"{x:.3g}") for x in wshare]
os.makedirs(os.path.join(DATA, "gbif", "world"), exist_ok=True)
json.dump(base, open(os.path.join(DATA, "gbif", "world_base.json"), "w"), separators=(",", ":"))
for k, g in enumerate(genera):
    nz = np.where(G4[k] > 0)[0]
    d = np.diff(np.r_[0, nz])
    json.dump({"genus": g, "d": d.tolist(), "n": G4[k, nz].astype(int).tolist()},
              open(os.path.join(DATA, "gbif", "world", f"{g}.json"), "w"), separators=(",", ":"))
wc = pd.DataFrame({"lat": 90 - (cells // WC + .5) * DEG * F, "lon": -180 + (cells % WC + .5) * DEG * F,
                   "plant_records": P4[cells].astype(int), "conifer_records": C4[cells].astype(int)})
for r in range(3):
    wc[f"genus_{r + 1}"] = [genera[t[r]] if len(t) > r else "" for t in base["top"]]
    wc[f"genus_{r + 1}_records"] = [t[r] if len(t) > r else 0 for t in base["topn"]]
wc["typical_genus"] = [genera[b] if b >= 0 else "" for b in base["lq"]]
wc["typical_index"] = base["lqv"]
wc.round(4).to_csv(os.path.join(DATA, "world_cells.csv"), index=False)
print("world cells with plant records", len(cells), "with", MINREC, "or more", int((P4 >= MINREC).sum()))

# ---------------------------------------------------------------- Great Britain at the native 0.088 degrees
lon0, lat0, lon1, lat1 = -8.0, 49.8, 2.0, 61.0
c0 = int((lon0 + 180) / DEG); c1 = int((lon1 + 180) / DEG) + 1
r0 = int((90 - lat1) / DEG); r1 = int((90 - lat0) / DEG) + 1
sub = lambda a: a.reshape(NROW, NCOL)[r0:r1, c0:c1]
PG = sub(plants); nr, nc = PG.shape
gb = {"deg": DEG, "rows": nr, "cols": nc, "lat_top": 90 - r0 * DEG, "lon_left": -180 + c0 * DEG, "genera": genera,
      "plants": PG.astype(int).ravel().tolist(), "conifers": sub(conif).astype(int).ravel().tolist(), "g": {}}
for k, g in enumerate(genera):
    a = sub(GEN[k]).ravel(); nz = np.where(a > 0)[0]
    if len(nz) == 0: continue
    gb["g"][g] = [np.diff(np.r_[0, nz]).tolist(), a[nz].astype(int).tolist()]
json.dump(gb, open(os.path.join(DATA, "gbif", "gb.json"), "w"), separators=(",", ":"))
for f in ["world_base.json", "gb.json"]:
    print(f, os.path.getsize(os.path.join(DATA, "gbif", f)))
print("world genus files MB", round(sum(os.path.getsize(os.path.join(DATA, "gbif", "world", f)) for f in os.listdir(os.path.join(DATA, "gbif", "world"))) / 1e6, 2))
pd.DataFrame({"genus": genera, "family": [keys[g]["family"] for g in genera], "gbif_key": [keys[g]["key"] for g in genera],
              "gbif_name": [keys[g]["name"] for g in genera], "records_world": tot_gen.astype(int)}).to_csv(os.path.join(DATA, "genera.csv"), index=False)
json.dump({"checks": checks, "dropped": dropped, "uk_species_missing": len(uk_species) - len(have_uk), "uk_species_n": len(uk_species),
           "genera_n": len(genera), "plants_total": float(plants.sum()), "conifers_total": float(conif.sum()),
           "over": int(over), "gb_window": [lon0, lat0, lon1, lat1], "world_min_records": MINREC},
          open(os.path.join(WORK, "gbif_meta.json"), "w"), indent=1)
