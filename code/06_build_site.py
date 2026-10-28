"""Step 6. Build index.html from code/page_template.html.

Every number in the text is a {{path|format}} token filled from data/results.json, so the page cannot drift from the
analysis. Facts the template states in words are checked against the data below. The results and the tile index are
embedded; tiles, grids, places and borders are fetched by the page from data/.
Run: python3 code/06_build_site.py
"""
import json, os, re, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(v):,}"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    raise ValueError(f)


def check():
    """Facts the page, paper and blog state in words."""
    N = R["nations"]
    assert N["Scotland"]["woodland_pct"] > N["Wales"]["woodland_pct"] > N["England"]["woodland_pct"]
    assert N["Scotland"]["conifer_share_pct"] > N["Wales"]["conifer_share_pct"] > N["England"]["conifer_share_pct"]
    assert 30 < N["Scotland"]["land_km2"] / R["gb"]["land_km2"] * 100 < 36           # "a third of its land"
    assert 15 < R["gb"]["groups_pct_of_woodland"]["felled"] < 25                      # "about a fifth"
    C = R["counties"]
    assert [c["county"] for c in C["most"][:4]] == ["Moray", "South Ayrshire", "Argyll and Bute", "Dumfries and Galloway"]
    assert all(27 < c["woodland_pct"] < 33 and c["conifer_share_pct"] > 60 for c in C["most"][:4])
    assert C["by_nation"]["England"]["most"]["county"] == "Surrey" and C["by_nation"]["Wales"]["most"]["county"] == "West Glamorgan"
    assert [c["county"] for c in C["least"][:3]] == ["Shetland Islands", "Orkney Islands", "Na h-Eileanan Siar"]
    eng_least = sorted([c for c in C["least"] + C["most"]], key=lambda c: c["woodland_pct"])
    assert C["by_nation"]["England"]["least"]["county"] == "Cambridgeshire"
    assert [c["county"] for c in C["least"] if c["nation"] == "England"][:2] == ["Cambridgeshire", "East Riding of Yorkshire"]
    S10 = R["squares10"]
    assert S10["most_wooded"][0]["forest"] == "Kielder Forest" and S10["most_wooded"][0]["county"] == "Northumberland"
    assert {"Kielder Forest", "Dornal Forest", "The Forest"} <= {s["forest"] for s in S10["most_conifer"][:3]}
    assert S10["most_conifer"][2]["place"] == "Thetford" and S10["most_conifer"][0]["place"] == "Glentrool Village"
    u = S10["under1_by_county"]
    assert u["Na h-Eileanan Siar"] + u["Shetland Islands"] + u["Orkney Islands"] + u["Highland"] + u["Lincolnshire"] + u["Cambridgeshire"] + u["Norfolk"] >= .85 * S10["under1pct"]
    G = R["gbif_gb"]["genera"]
    assert G["Pinus"]["top"][0]["place"] == "Nethy Bridge" and G["Juniperus"]["top"][0]["lat"] < G["Pinus"]["top"][0]["lat"] and G["Juniperus"]["top"][0]["lon"] < G["Pinus"]["top"][0]["lon"]
    assert G["Betula"]["top"][0]["place"] == "Braemar" and G["Betula"]["top"][0]["lat"] < G["Juniperus"]["top"][0]["lat"]
    assert G["Fagus"]["top"][0]["place"] == "Wootton Rivers" and G["Fraxinus"]["top"][0]["place"] == "Highworth" and G["Quercus"]["top"][0]["place"] == "Long Ditton"
    assert G["Picea"]["top"][0]["place"] == "Y Bala"
    assert R["gbif_gb"]["dominant_cells"][0][0] == "Salix" and R["gbif_gb"]["dominant_cells"][0][1] > R["gbif_gb"]["cells_ok"] / 2
    F = R["fe"]
    assert [s[0] for s in F["top_species"][:5]] == ["Sitka spruce", "Corsican pine", "Scots pine", "Oak (robur/petraea)", "Beech"]
    assert F["conifer_peak_decade"] == 1990 and F["periods"]["1980_1999"][0][0] == "Sitka spruce" and F["periods"]["2000_2029"][0][0] == "Sitka spruce"
    W = R["world"]
    assert [g for g, *_ in W["dominant_area"][:3]] == ["Ficus", "Salix", "Quercus"]
    T = W["typical_by_continent"]
    assert [g for g, _ in T["Oceania"][:3]] == ["Acacia", "Corymbia", "Eucalyptus"]
    assert [g for g, _ in T["Africa"][:3]] == ["Ficus", "Vachellia", "Combretum"]
    assert T["South America"][0][0] == "Inga" and [g for g, _ in T["Europe"][:3]] == ["Salix", "Picea", "Betula"]
    assert [g for g, _ in T["North America"][:4]] == ["Quercus", "Salix", "Pinus", "Juniperus"]
    gc = W["genus_countries"]
    assert gc["Pinus"][0][0] == "Spain" and [c for c, _ in gc["Pinus"][1:3]] == ["Poland", "United States of America"]
    assert [c for c, _ in gc["Quercus"][:2]] == ["Spain", "Mexico"] and gc["Eucalyptus"][0][0] == "Australia" and gc["Acacia"][0][0] == "Australia"
    assert W["gaps"]["Congo basin"]["ok_pct"] < 20 and W["gaps"]["central Siberia"]["ok_pct"] < 5


def sanitise(o):
    if isinstance(o, str): return o.replace("—", "-").replace("–", "-")
    if isinstance(o, list): return [sanitise(x) for x in o]
    if isinstance(o, dict): return {sanitise(k): sanitise(v) for k, v in o.items()}
    return o


if __name__ == "__main__":
    check()
    # no long dashes in any published data file (place names from GeoNames and OS can contain them)
    for p in glob.glob(os.path.join(DATA, "**", "*.json"), recursive=True):
        if "/tiles/" in p: continue
        t = open(p, encoding="utf-8").read()
        if "—" in t or "–" in t:
            json.dump(sanitise(json.loads(t)), open(p, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
            print("sanitised", os.path.relpath(p, ROOT))
    tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
    html = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(m.group(1)), m.group(3)), tpl)
    slim = {k: R[k] for k in ("gb", "nations", "counties", "squares10", "gbif_gb", "groups", "mix_key", "common", "genus_cols", "fe")}
    slim["world"] = {k: R["world"][k] for k in ("dominant_area", "typical_area", "by_continent", "continents", "min_records", "genus_records_top")}
    html = html.replace("/*RESULTS*/", json.dumps(sanitise(slim), ensure_ascii=False, separators=(",", ":")))
    idx = {}
    for lay in ("wood", "mix1", "mix5", "hill"):
        d = {}
        for p in glob.glob(os.path.join(DATA, "tiles", lay, "*", "*", "*.png")):
            z, x, y = p.split(os.sep)[-3:]
            d.setdefault(int(z), []).append(int(x) * 100000 + int(y[:-4]))
        idx[lay] = {z: sorted(v) for z, v in sorted(d.items())}
    html = html.replace("/*TILEIDX*/", json.dumps(idx, separators=(",", ":")))
    assert "{{" not in html
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--"):
        assert bad not in vis, bad
    js = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    for q in re.findall(r'"([^"\n]{12,})"|`([^`]{12,})`', js):
        for t in q:
            assert "—" not in t and "–" not in t, t
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()), "bytes")
