"""Pack the PNG tiles into one JSON file per layer and zoom (data/tiles/<layer>_<z>.json,
{"x/y": base64 PNG}), so the site has a few dozen files instead of about 1,600."""
import base64, glob, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "data", "tiles")
for layer in sorted(os.listdir(T)):
    d = os.path.join(T, layer)
    if not os.path.isdir(d): continue
    for z in sorted(os.listdir(d)):
        pack = {}
        for f in glob.glob(os.path.join(d, z, "*", "*.png")):
            x = os.path.basename(os.path.dirname(f)); y = os.path.basename(f)[:-4]
            pack[f"{x}/{y}"] = base64.b64encode(open(f, "rb").read()).decode()
        out = os.path.join(T, f"{layer}_{z}.json")
        json.dump(pack, open(out, "w"), separators=(",", ":"))
        print(out, len(pack), os.path.getsize(out))
