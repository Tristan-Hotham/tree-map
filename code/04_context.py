"""Step 4. Context layers for the page: borders, land, place names and the search list.

data/ctx/gb_borders.json     counties and council areas (ONS boundaries, simplified), with nation.
data/ctx/world.json          Natural Earth 1:50m countries (simplified), with name and continent.
data/places/gb.json          OS Open Names cities, towns and villages: [name, county, lat, lon, rank, other name].
data/places/woods.json       OS Open Names named woods and forests: [name, lat, lon].
data/places/world.json       GeoNames places of 15,000 or more: [name, country code, lat, lon, population].
"""
import json, os, sys, zipfile, io
import numpy as np, pandas as pd
import shapely
from shapely.geometry import shape, mapping
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

os.makedirs(os.path.join(DATA, "ctx"), exist_ok=True); os.makedirs(os.path.join(DATA, "places"), exist_ok=True)


def rnd(geom, nd):
    return json.loads(json.dumps(mapping(geom)), parse_float=lambda s: round(float(s), nd))


def dump(obj, name):
    p = os.path.join(DATA, name)
    json.dump(obj, open(p, "w"), separators=(",", ":"), ensure_ascii=False)
    print(name, os.path.getsize(p))


gj = json.load(open(COUNTIES))
feats = []
for f in gj["features"]:
    g = shape(f["geometry"]).simplify(0.004, preserve_topology=True)
    feats.append({"type": "Feature", "properties": {"n": f["properties"]["county"], "c": f["properties"]["nation"]}, "geometry": rnd(g, 4)})
dump({"type": "FeatureCollection", "features": feats}, "ctx/gb_borders.json")

ne = json.load(open(os.path.join(NE, "ne_50m_admin_0_countries.geojson")))
feats = []; iso = {}
for f in ne["features"]:
    p = f["properties"]
    g = shape(f["geometry"]).simplify(0.06, preserve_topology=True)
    if g.is_empty: continue
    feats.append({"type": "Feature", "properties": {"n": p["NAME"], "c": p["CONTINENT"]}, "geometry": rnd(g, 2)})
    if p.get("ISO_A2") and p["ISO_A2"] != "-99": iso[p["ISO_A2"]] = p["NAME"]
    elif p.get("ISO_A2_EH") and p["ISO_A2_EH"] != "-99": iso[p["ISO_A2_EH"]] = p["NAME"]
dump({"type": "FeatureCollection", "features": feats}, "ctx/world.json")

osn = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False)
for c in ("lat", "lon"): osn[c] = osn[c].astype(float)
eng = (osn.lang2 == "eng") & osn.lang1.isin(["gla", "cym"])
osn["show"] = np.where(eng, osn.name2, osn.name1)
osn["alt"] = np.where(eng, osn.name1, osn.name2)
osn["cty"] = [(c or d).split(" - ")[-1] for c, d in zip(osn.county, osn.district)]
S = osn[(osn.type == "populatedPlace") & osn.local_type.isin(["City", "Town", "Village"])]
rank = {"City": 3, "Town": 2, "Village": 1}
dump([[r.show, r.cty, round(r.lat, 4), round(r.lon, 4), rank[r.local_type]] + ([r.alt] if r.alt else []) for r in S.itertuples()], "places/gb.json")
Wd = osn[(osn.local_type == "Woodland Or Forest") & osn.show.str.contains(r"(?:Forest|Wood|Woods|Chase)$", regex=True)]
dump([[r.show, round(r.lat, 4), round(r.lon, 4)] for r in Wd.itertuples()], "places/woods.json")

with zipfile.ZipFile(CITIES) as z:
    C = pd.read_csv(io.BytesIO(z.read("cities15000.txt")), sep="\t", header=None, quoting=3, dtype=str, keep_default_na=False)
C = C[[1, 4, 5, 7, 8, 14]]; C.columns = ["name", "lat", "lon", "fcode", "cc", "pop"]
C = C[~C.fcode.isin(["PPLX", "PPLH", "PPLQ", "PPLW"])]
C["pop"] = C["pop"].astype(int); C = C.sort_values("pop", ascending=False)
dump({"cc": iso, "rows": [[r.name, r.cc, round(float(r.lat), 3), round(float(r.lon), 3), int(r.pop)] for r in C.itertuples()]}, "places/world.json")
