"""Step 8. Build the paper PDF: fill code/paper_template.tex from data/results.json, add tables, compile with xelatex.
Figures come from step 7 (release/paper/fig_*.png). Run: python3 code/08_paper.py
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = json.load(open(os.path.join(DATA, "results.json")))
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_What_Grows_Where"
tex = lambda s: str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    return tex(str(v))


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


rows = ""
for nm in ["England", "Scotland", "Wales"]:
    N = R["nations"][nm]; g = N["groups_ha"]
    rows += f"{nm} & {N['land_km2']:,.0f} & {N['woodland_ha'] / 1000:,.0f} & {N['woodland_pct']:.1f} & {g['broadleaved'] / 1000 + g['mixed_broad'] / 1000:,.0f} & {g['conifer'] / 1000 + g['mixed_conifer'] / 1000:,.0f} & {g['young'] / 1000:,.0f} & {g['felled'] / 1000:,.0f} & {g['other'] / 1000:,.0f} & {N['conifer_share_pct']:.1f}\\\\\n"
G = R["gb"]; g = G["groups_ha"]
rows += f"\\midrule Great Britain & {G['land_km2']:,.0f} & {G['woodland_ha'] / 1000:,.0f} & {G['woodland_pct']:.1f} & {(g['broadleaved'] + g['mixed_broad']) / 1000:,.0f} & {(g['conifer'] + g['mixed_conifer']) / 1000:,.0f} & {g['young'] / 1000:,.0f} & {g['felled'] / 1000:,.0f} & {g['other'] / 1000:,.0f} & {G['conifer_share_pct']:.1f}\\\\\n"
TN = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{Woodland by country, NFI 2024. Areas of woodland groups in thousand hectares. "
      "Broadleaf includes mixed mainly broadleaved; conifer includes mixed mainly conifer. Conifer share is conifer over broadleaf plus conifer.}\\label{tab:nations}"
      "\\setlength{\\tabcolsep}{4pt}\\begin{tabular}{lrrrrrrrrr}\\toprule & Land & Woodland & \\% of & Broad- & Conifer & Young & Felled, & Other & Conifer\\\\"
      " & km\\textsuperscript{2} & kha & land & leaf & & & restock & & share \\%\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(s)} & {k} & {a:,.0f} & {p:.1f}\\\\\n" for s, a, p, k in R["fe"]["top_species"][:10])
TF = ("\\begin{table}[tbp]\\centering\\small\\caption{The ten largest species of the Forestry England estate by area, with share of the area that carries a species.}\\label{tab:fe}"
      "\\begin{tabular}{llrr}\\toprule Species & Kind & Hectares & \\%\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
CM = R["common"]
rows = ""
for c in ["Europe", "North America", "Asia", "Africa", "South America", "Oceania"]:
    a = ", ".join(f"\\textit{{{gg}}} {s:.0f}" for gg, s in R["world"]["by_continent"][c]["top"][:3])
    b = ", ".join(f"\\textit{{{gg}}} {s:.0f}" for gg, s in R["world"]["typical_by_continent"][c][:3])
    rows += f"{c} & {a} & {b}\\\\\n"
TW = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{Most recorded and most typical tree genera by continent: percentage of each continent's qualifying land (cells with at least "
      f"{R['world']['min_records']} plant records) on which each genus leads.}}\\label{{tab:world}}"
      "\\begin{tabular}{lll}\\toprule Continent & Most recorded genus (\\%) & Most typical genus (\\%)\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
t = open(os.path.join(HERE, "paper_template.tex"), encoding="utf-8").read()
t = re.sub(r"\{\{(?!TABLE_)(.+?)\}\}", sub, t).replace("{{TABLE_NATIONS}}", TN).replace("{{TABLE_FE}}", TF).replace("{{TABLE_WORLD}}", TW)
assert "{{" not in t and "--" not in t and "—" not in t and "–" not in t
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
print("\n".join(l for l in open(os.path.join(OUT, NAME + ".log"), errors="ignore") if l.startswith("!") or "Overfull" in l)[:2000])
for ext in (".aux", ".log", ".out"):
    p = os.path.join(OUT, NAME + ext)
    if os.path.exists(p): os.remove(p)
shutil.move(os.path.join(OUT, NAME + ".pdf"), os.path.join(ROOT, "release", NAME + ".pdf"))
print("paper written", r.returncode)
