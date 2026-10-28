"""r/dataisbeautiful collage: reddit/what_grows_where.png (2400 x 3000) on warm paper.
Every number comes from ../data/results.json; maps are drawn from the project's data files.
Run from anywhere: FONT_DIR=/path/to/fonts python3 reddit/collage.py
"""
import os, sys
OUTDIR = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(OUTDIR, "..", "code"))
from figlib import *

BGC = "#F4EEE1"; INK = "#1B231F"; ACC = "#1D5C5E"; LEAFC = "#3E8E3A"
N, G, W, F = R["nations"], R["gb"], R["world"], R["fe"]
fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BGC)

fig.text(.045, .972, "What grows where?", fontproperties=DISP, fontsize=60, color=INK, va="top")
fig.text(.045, .9, f"Every mapped wood in Great Britain, coloured by type: {G['woodland_pct']:.1f}% of the land, from the National Forest\n"
         f"Inventory's {R['nfi']['polygons']:,} polygons. Below, the most typical tree genus in the world's plant records.",
         family=SER, fontsize=14.5, color=INK, va="top", linespacing=1.25)

# hero map
ax = fig.add_axes([.0, .265, .62, .6]); ax.set_facecolor(BGC)
draw_land(ax, gb_outline(), fc="#E7DFCD")
img, ext = gb_type_rgba(1)
ax.imshow(img, extent=ext, interpolation="nearest", zorder=2)
ax.set_xlim(20, 660); ax.set_ylim(0, 1000); ax.set_aspect("equal"); ax.axis("off")
for nm, e, n, dx, dy in [("Kielder Forest", 367, 592, 70, 30), ("Galloway", 245, 585, -95, -45), ("Thetford Forest", 585, 285, -110, 85),
                         ("Abernethy and\nStrathspey pinewoods", 300, 817, 120, 45), ("New Forest", 429, 106, 70, -25)]:
    ax.annotate(nm, (e, n), xytext=(e + dx, n + dy), ha="left" if dx > 0 else "right", va="center", fontsize=11, family=MONO, color=INK, zorder=6,
                arrowprops=dict(arrowstyle="-", color=INK, lw=.9), bbox=dict(boxstyle="round,pad=0.2", fc=BGC, ec="none", alpha=.85))
# legend
lx, ly = .63, .80
for i, (nm, c) in enumerate(zip(GROUPS[1:], GROUP_COL[1:])):
    fig.patches.append(plt.Rectangle((lx, ly - i * .022), .022, .016, fc=c, transform=fig.transFigure, figure=fig))
    fig.text(lx + .03, ly - i * .022 + .008, f"{nm}  {G['groups_pct_of_woodland'][GROUP_KEYS[i + 1]]:.0f}%", family=MONO, fontsize=11.5, va="center", color=INK)
fig.text(lx, ly + .028, "WOODLAND TYPE, SHARE OF ALL WOODLAND", family=MONO, fontsize=10.5, color=MUT)

# big numbers
nums = [(f"{N['Scotland']['woodland_pct']:.0f}% vs {N['England']['woodland_pct']:.0f}%", ACC,
         f"of the land is woodland in Scotland and in\nEngland. Wales: {N['Wales']['woodland_pct']:.0f}%."),
        (f"{N['Scotland']['conifer_share_pct']:.0f}%", ACC, f"of Scotland's broadleaf and conifer woodland\nis conifer. England: {N['England']['conifer_share_pct']:.0f}%."),
        (f"{R['squares10']['most_wooded'][0]['woodland_pct']:.0f}%", ACC, f"woodland in Britain's most wooded 10 km\nsquare, in Kielder Forest ({R['squares10']['most_wooded'][0]['conifer_share_pct']:.0f}% conifer)."),
        (f"{F['top_species'][0][2]:.0f}%", "#8A5A22", f"of England's public forests are Sitka spruce,\nthe biggest single species.")]
y = .615
for big, c, txt in nums:
    fig.text(lx, y, big, fontproperties=DISP, fontsize=40, color=c, va="top")
    fig.text(lx, y - .043, txt, family=SER, fontsize=13, color=INK, va="top", linespacing=1.2)
    y -= .093

# world map
fig.text(.045, .252, "THE WORLD: MOST TYPICAL TREE GENUS IN EACH PLACE'S PLANT RECORDS", family=MONO, fontsize=11, color=MUT)
wimg, wb = world_grid("typ")
ax2 = fig.add_axes([.03, .075, .64, .17]); ax2.set_facecolor(BGC)
draw_land(ax2, world_rings(), fc="#E7DFCD")
ax2.imshow(wimg, extent=(-180, 180, -90, 90), interpolation="nearest", zorder=2)
ax2.set_xlim(-170, 180); ax2.set_ylim(-56, 78); ax2.set_aspect(1.1); ax2.axis("off")
show = ["Acacia", "Eucalyptus", "Corymbia", "Ficus", "Vachellia", "Picea", "Betula", "Salix", "Quercus", "Pinus", "Juniperus", "Inga"]
for i, g in enumerate(show):
    cx, cy = .69 + (i % 2) * .15, .236 - (i // 2) * .019
    fig.patches.append(plt.Rectangle((cx, cy - .006), .016, .013, fc=R["genus_cols"][g], transform=fig.transFigure, figure=fig))
    fig.text(cx + .022, cy, COMMON[g].split(" (")[0], family=MONO, fontsize=11, va="center", color=INK)
fig.text(.69, .113, f"A map of recording as much as of trees:\nEurope and North America hold {W['europe_namerica_share_pct']:.0f}% of plant\nrecords on {W['europe_namerica_land_pct']:.0f}% of the land. Blank: under {W['min_records']} records.",
         family=SER, fontsize=11, color=INK, va="top", linespacing=1.2)

fig.text(.045, .044, "Data: National Forest Inventory GB 2024 and Forestry England, © Forestry Commission, contains OS data © Crown copyright (OGL v3);\n"
         "GBIF.org (28 October 2026) occurrence density maps (CC BY 4.0); ONS boundaries; Natural Earth. NFI polygons drawn on 1 km squares.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib. Interactive map: tristan-hotham.github.io/tree-map",
         family=MONO, fontsize=9.2, color=MUT, va="top", linespacing=1.3)
fig.savefig(os.path.join(OUTDIR, "what_grows_where.png"), dpi=200, facecolor=BGC)
print("saved")
