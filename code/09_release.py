"""Step 9. Blog post (release/blog/post.html and meta.json) and Zenodo files (release/zenodo/).
Run after steps 1 to 8: python3 code/09_release.py
"""
import json, os, re, shutil, zipfile, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json")))
REL = os.path.join(ROOT, "release"); BL = os.path.join(REL, "blog"); ZD = os.path.join(REL, "zenodo")


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{round(v):,}"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    return str(v)


fill = lambda s: re.sub(r"\{\{(?!IMG\|)([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(m.group(1)), m.group(3)), s)
post = fill(open(os.path.join(HERE, "blog_template.html"), encoding="utf-8").read())
assert "{{" not in post.replace("{{IMG|", "")
for name in re.findall(r"\{\{IMG\|([^|]+)\|", post):
    assert os.path.exists(os.path.join(BL, name)), name
vis = re.sub(r"<!--.*?-->|<[^>]+>", " ", post, flags=re.S)
assert not any(b in vis for b in ("\u2014", "\u2013", "--"))
open(os.path.join(BL, "post.html"), "w", encoding="utf-8").write(post)
words = len(re.sub(r"\{\{IMG\|[^}]*\}\}", " ", vis).split())
print("post words", words)

N = R["nations"]
meta = {"title": "What grows where: the trees of Britain and the world", "slug": "tree-map",
        "excerpt": f"An explorable map of every wood in Great Britain by type, England's public forests by species and planting year, and 88 tree genera in the world's plant records. Woodland covers {R['gb']['woodland_pct']:.1f}% of Great Britain: {N['Scotland']['woodland_pct']:.1f}% of Scotland but {N['England']['woodland_pct']:.1f}% of England.",
        "seo_description": f"Map of Britain's woods by type and the world's recorded trees: {R['gb']['woodland_pct']:.1f}% of Great Britain is woodland, {N['Scotland']['conifer_share_pct']:.0f}% of Scotland's is conifer.",
        "tags": ["trees", "woodland", "forestry", "National Forest Inventory", "GBIF", "maps", "biodiversity", "data"],
        "header_alt": f"Title card reading 'What grows where: the trees of Britain and the world' on pale paper, beside a map of Great Britain with woodland coloured by type, dark teal conifer plantations in Scotland and green broadleaved woods across England. Text: {R['gb']['woodland_pct']:.1f}% of Great Britain is woodland, {N['Scotland']['woodland_pct']:.1f}% of Scotland, {N['Wales']['woodland_pct']:.1f}% of Wales and {N['England']['woodland_pct']:.1f}% of England."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
json.dump(meta, open(os.path.join(BL, "meta.json"), "w"), indent=2, ensure_ascii=False)

# ---------------- Zenodo
shutil.rmtree(ZD, ignore_errors=True); os.makedirs(ZD)
pdf = "Hotham_What_Grows_Where.pdf"
shutil.copy(os.path.join(REL, pdf), ZD)
for f in ["nations.csv", "counties.csv", "nfi_types.csv", "gb_5km.csv", "gb_10km.csv", "gb_1km.csv.gz", "world_cells.csv", "genera.csv",
          "fe_species.csv", "fe_planting_decades.csv", "results.json"]:
    shutil.copy(os.path.join(DATA, f), ZD)
zp = os.path.join(ZD, "tree-map_code_and_data.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(glob.glob(os.path.join(ROOT, "code", "*")) + glob.glob(os.path.join(DATA, "**", "*"), recursive=True)):
        if os.path.isdir(p) or "__pycache__" in p or "/tiles/" in p: continue
        z.write(p, os.path.relpath(p, ROOT))
    for f in ["README.md", "LICENSE"]:
        z.write(os.path.join(ROOT, f), f)
tex = open(os.path.join(REL, "paper", "Hotham_What_Grows_Where.tex"), encoding="utf-8").read()
ab = re.search(r"\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\textit{", "").replace("}", "").replace("\\", "")
title = "What Grows Where: Mapping the Woodland of Great Britain and the Recorded Trees of the World"
zm = {"title": title,
      "description_html": f"<p>{ab}</p><p>Interactive version: https://tristan-hotham.github.io/tree-map/. Data and code: https://github.com/Tristan-Hotham/tree-map. Blog post: to follow.</p>",
      "keywords": ["woodland", "trees", "National Forest Inventory", "Forestry England", "GBIF", "occurrence records", "sampling bias", "Great Britain", "interactive map", "open data"],
      "licence": "cc-by-4.0",
      "related": [{"identifier": "https://github.com/Tristan-Hotham/tree-map", "relation": "issupplementedby", "resource_type": "software"},
                  {"identifier": "https://tristan-hotham.github.io/tree-map/", "relation": "issupplementedby", "resource_type": "other"},
                  {"identifier": "https://data-forestry.opendata.arcgis.com/", "relation": "isderivedfrom", "resource_type": "dataset"},
                  {"identifier": "https://www.gbif.org", "relation": "isderivedfrom", "resource_type": "dataset"},
                  {"identifier": "https://www.ordnancesurvey.co.uk/products/os-open-names", "relation": "isderivedfrom", "resource_type": "dataset"},
                  {"identifier": "https://www.geonames.org", "relation": "isderivedfrom", "resource_type": "dataset"},
                  {"identifier": "https://www.naturalearthdata.com", "relation": "isderivedfrom", "resource_type": "dataset"}]}
assert not any(b in json.dumps(zm, ensure_ascii=False) for b in ("\u2014", "\u2013", "--"))
json.dump(zm, open(os.path.join(ZD, "meta.json"), "w"), indent=2, ensure_ascii=False)
for f in sorted(os.listdir(ZD)): print(f, os.path.getsize(os.path.join(ZD, f)))
