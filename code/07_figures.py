"""Step 7. Static figures: header.png (1200 by 630), blog figures (release/blog/b_*.png, 1520 px wide) and the same
figures for the paper (release/paper/fig_*.png). All drawn with matplotlib from the project's data files.
Run: FONT_DIR=/path/to/fonts python3 code/07_figures.py
"""
import os, json, shutil
from figlib import *
from matplotlib.colors import LinearSegmentedColormap

BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
RINGS = gb_outline()
NAT = ["England", "Scotland", "Wales"]


def out(fig, name, paper):
    fig.savefig(os.path.join(BL, f"b_{name}.png"), dpi=200, facecolor=BG)
    fig.savefig(os.path.join(PA, f"fig_{paper}.png"), dpi=130, facecolor=BG)
    plt.close(fig)


def gb_types_axes(ax, level=1, legend=True, fs=11):
    draw_land(ax, RINGS, fc=CTX)
    img, ext = gb_type_rgba(level)
    ax.imshow(img, extent=ext, interpolation="nearest", zorder=2)
    ax.set_xlim(0, 670); ax.set_ylim(0, 1045); ax.set_aspect("equal"); ax.axis("off")
    if legend:
        for i, (nm, c) in enumerate(zip(GROUPS[1:], GROUP_COL[1:])):
            y = 1000 - i * 34
            ax.add_patch(plt.Rectangle((420, y - 10), 22, 20, fc=c, ec="none", zorder=5))
            ax.text(452, y, nm, va="center", fontsize=fs, family=MONO, color=FG, zorder=5)


# ---------------- 1. the GB woodland map
fig = plt.figure(figsize=(7.6, 10.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
gb_types_axes(ax)
for nm, e, n, ha in [("Kielder", 367, 592, "left"), ("Galloway", 245, 585, "right"), ("Thetford", 587, 283, "right"), ("Abernethy", 300, 817, "right"),
                     ("New Forest", 429, 106, "left"), ("Strathyre", 255, 717, "right")][:5]:
    ax.annotate(nm, (e, n), xytext=(e + (40 if ha == "left" else -40), n + 18), ha=ha, fontsize=11, family=MONO, color=FG, zorder=6,
                arrowprops=dict(arrowstyle="-", color=FG, lw=.8))
ax.text(10, 540, f"Woodland, {R['gb']['woodland_pct']:.1f}% of land\nNFI 2024, 1 km squares;\npaler where less of\nthe square is wooded.\nShetland not shown.", fontsize=10.5, family=MONO, color=MUT, va="top")
out(fig, "gb_woodland", "gb_woodland")

# ---------------- 2. nations stacked bars
fig, ax = plt.subplots(figsize=(7.6, 3.6)); fig.subplots_adjust(left=.14, right=.9, top=.95, bottom=.18)
for i, nm in enumerate(NAT[::-1]):
    N = R["nations"][nm]; x = 0
    for g, k in enumerate(GROUP_KEYS[1:]):
        v = N["groups_ha"][k] / (N["land_km2"] * 100) * 100
        ax.barh(i, v, left=x, color=GROUP_COL[g + 1], height=.62, label=GROUPS[g + 1] if i == 0 else None); x += v
    ax.text(x + .3, i, f"{N['woodland_pct']:.1f}%", va="center", fontsize=13, family=MONO, color=FG, fontweight="bold")
ax.set_yticks(range(3)); ax.set_yticklabels(NAT[::-1], fontsize=14); ax.set_xlim(0, 22)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}%"))
ax.set_xticks(range(0, 25, 5))
ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(.45, -.13), prop={"family": MONO, "size": 10})
fig.subplots_adjust(bottom=.36, left=.15)
out(fig, "nations", "nations")

# ---------------- 3. counties
C = pd.read_csv(os.path.join(DATA, "counties.csv")).sort_values("woodland_pct", ascending=False)
rows = pd.concat([C.head(10), C.tail(6)])
fig, ax = plt.subplots(figsize=(7.6, 7.4)); fig.subplots_adjust(left=.37, right=.92, top=.98, bottom=.1)
for i, r in enumerate(rows.itertuples()):
    y = len(rows) - i - (0 if i < 10 else 1)
    bl = (r.broadleaved_ha + r.mixed_broad_ha) / (r.land_km2 * 100) * 100; cf = (r.conifer_ha + r.mixed_conifer_ha) / (r.land_km2 * 100) * 100
    ax.barh(y, r.woodland_pct, color=RULE, height=.7); ax.barh(y, bl, color=GROUP_COL[1], height=.7); ax.barh(y, cf, left=bl, color=GROUP_COL[4], height=.7)
    ax.text(r.woodland_pct + .4, y, f"{r.woodland_pct:.1f}%" if r.woodland_pct >= 1 else f"{r.woodland_pct:.2f}%", va="center", fontsize=11, family=MONO)
    ax.text(-0.6, y, f"{r.county}", ha="right", va="center", fontsize=12)
ax.text(-.6, 6, "...", ha="right", va="center", fontsize=12, color=MUT)
ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.set_xlim(0, 34); ax.set_ylim(-.4, 17.6)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:.0f}%"))
ax.set_xlabel("broadleaf (green), conifer (teal), other woodland (grey)", fontsize=10.5, family=MONO, color=MUT)
out(fig, "counties", "counties")

# ---------------- 4. Forestry England planting decades
D = R["fe"]["decades"]
fig, ax = plt.subplots(figsize=(7.6, 4.4)); fig.subplots_adjust(left=.12, right=.98, top=.92, bottom=.14)
x = np.arange(len(D))
ax.bar(x, [d[1] for d in D], color=GROUP_COL[4], width=.8, label="conifer")
ax.bar(x, [d[2] for d in D], bottom=[d[1] for d in D], color=GROUP_COL[1], width=.8, label="broadleaf")
ax.set_xticks(x); ax.set_xticklabels([f"{d[0]}s" if i % 2 == 0 else "" for i, d in enumerate(D)], fontsize=11, family=MONO)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.set_ylabel("hectares standing today", fontsize=12, family=MONO, color=MUT)
ax.legend(frameon=False, prop={"family": MONO, "size": 11}, loc="upper left")
ax.grid(axis="y", color=RULE, lw=.8); ax.set_axisbelow(True)
out(fig, "planting", "planting")

# ---------------- 5. GBIF in Britain: pine, beech, spruce shares
gb = json.load(open(os.path.join(DATA, "gbif", "gb.json")))
nr, nc = gb["rows"], gb["cols"]; P = np.array(gb["plants"], float)
gj = json.load(open(os.path.join(DATA, "ctx", "gb_borders.json")))
llr = []
for f in gj["features"]:
    llr += [np.array(p[0]) for p in polys_of(f["geometry"])]
ramp = LinearSegmentedColormap.from_list("r", ["#F3EFC8", "#D7E3A0", "#A9CC7A", "#6FAE5B", "#3E8E4A", "#1E6A44", "#0F4636"])
fig, axs = plt.subplots(1, 3, figsize=(7.6, 5.0)); fig.subplots_adjust(left=.01, right=.99, top=.9, bottom=.02, wspace=.02)
for ax, g in zip(axs, ["Pinus", "Fagus", "Quercus"]):
    a = np.zeros(nr * nc); d, v = gb["g"][g]; a[np.cumsum(d)] = v
    s = np.where(P >= 500, a / np.maximum(P, 1), np.nan)
    sc = np.nanpercentile(s, 99)
    draw_land(ax, llr, fc=CTX)
    ax.imshow(np.clip(s / sc, 0, 1).reshape(nr, nc), cmap=ramp, extent=(gb["lon_left"], gb["lon_left"] + nc * gb["deg"], gb["lat_top"] - nr * gb["deg"], gb["lat_top"]), interpolation="nearest", zorder=2, vmin=0, vmax=1)
    ax.set_xlim(-6.5, 2); ax.set_ylim(49.9, 59); ax.set_aspect(1 / np.cos(np.radians(55))); ax.axis("off")
    ax.set_title(f"{gname(g)}\ndarkest {sc * 100:.1f}%+", fontsize=12, family=MONO, color=FG)
out(fig, "records_gb", "records_gb")

# ---------------- 6. the world: most typical genus
img, wb = world_grid("typ")
fig = plt.figure(figsize=(7.6, 5.2)); ax = fig.add_axes([0, .2, 1, .8])
draw_land(ax, world_rings(), fc=CTX)
ax.imshow(img, extent=(-180, 180, -90, 90), interpolation="nearest", zorder=2)
ax.set_xlim(-170, 180); ax.set_ylim(-56, 78); ax.set_aspect(1.15); ax.axis("off")
lg = fig.add_axes([0, 0, 1, .2]); lg.axis("off"); lg.set_xlim(0, 3); lg.set_ylim(0, 4)
for i, (g, _, s) in enumerate(R["world"]["typical_area"][:12]):
    cx, cy = i % 3, 3.5 - i // 3 * .95
    lg.add_patch(plt.Rectangle((cx + .06, cy - .22), .1, .44, fc=R["genus_cols"][g], ec="none"))
    lg.text(cx + .21, cy, gname(g), va="center", fontsize=9.5, family=MONO)
out(fig, "world_typical", "world_typical")

# ---------------- 7. recording effort
img, wb = world_grid("effort")
Cn = R["world"]["continents"]; order = sorted(Cn, key=lambda c: -Cn[c]["records_per_1000km2"])
fig = plt.figure(figsize=(7.6, 6.6))
ax = fig.add_axes([0, .36, 1, .64]); draw_land(ax, world_rings(), fc=CTX)
ax.imshow(img, extent=(-180, 180, -90, 90), interpolation="nearest", zorder=2)
ax.set_xlim(-170, 180); ax.set_ylim(-56, 78); ax.set_aspect(1.15); ax.axis("off")
b = fig.add_axes([.2, .06, .7, .26])
b.barh(range(len(order))[::-1], [Cn[c]["records_per_1000km2"] for c in order], color="#B86E2E", height=.65); b.set_xscale("log")
b.set_yticks(range(len(order))[::-1]); b.set_yticklabels(order, fontsize=12)
for i, c in enumerate(order): b.text(Cn[c]["records_per_1000km2"] * 1.12, len(order) - 1 - i, f"{Cn[c]['records_per_1000km2']:,}", va="center", fontsize=11, family=MONO)
b.set_xlim(100, 100000); b.set_xlabel("plant records per 1,000 km² of land (log scale)", fontsize=11, family=MONO, color=MUT)
b.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
out(fig, "effort", "effort")

# ---------------- header
fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([.02, .02, .38, .96]); ax.set_facecolor(BG); gb_types_axes(ax, legend=False); ax.set_xlim(60, 660); ax.set_ylim(0, 980)
fig.text(.42, .80, "What grows where", fontproperties=DISP, fontsize=50, color=FG)
fig.text(.42, .70, "the trees of Britain and the world", family=SER, fontsize=26, color=CON)
fig.text(.42, .56, f"{R['gb']['woodland_pct']:.1f}% of Great Britain is woodland: {R['nations']['Scotland']['woodland_pct']:.1f}% of Scotland,\n"
         f"{R['nations']['Wales']['woodland_pct']:.1f}% of Wales, {R['nations']['England']['woodland_pct']:.1f}% of England. Every wood by type,\n"
         f"England's public forests by species and year, and 88 tree\ngenera in the world's plant records.", family=SER, fontsize=17, color=FG, va="top", linespacing=1.35)
for i, (nm, c) in enumerate(zip(GROUPS[1:5], GROUP_COL[1:5])):
    fig.patches.append(plt.Rectangle((.42 + i * .145, .17), .018, .035, fc=c, transform=fig.transFigure, figure=fig))
    fig.text(.442 + i * .145, .187, ["Broadleaf", "Mixed, broad.", "Mixed, conifer", "Conifer"][i], family=MONO, fontsize=11, va="center")
fig.text(.42, .07, "Dr Tristan Hotham · tristan-hotham.github.io/tree-map", family=MONO, fontsize=13, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG); plt.close(fig)
for f in sorted(os.listdir(BL)): print(f, os.path.getsize(os.path.join(BL, f)))
