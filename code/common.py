"""Shared paths, groups and colours for the tree-map project."""
import os, json, gzip, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
D17 = os.environ.get("TREE_DATA", "/home/claude/hist/_data17")
OSN = os.environ.get("OSNAMES", "/home/claude/hist/osnames_gb.tsv")
NE = os.environ.get("NE_DIR", "/home/claude/hist/_data3/ne/geojson")
CITIES = os.environ.get("CITIES15000", "/home/claude/hist/_data13/cities15000.zip")
COUNTIES = os.environ.get("COUNTIES", "/home/claude/hist/how-roman-is-your-road/data/counties.geojson")
WORK = os.environ.get("WORK", os.path.join(ROOT, "_work"))  # temporary, deleted after the build
os.makedirs(WORK, exist_ok=True)

# NFI interpreted forest types grouped for the map. 0 = nothing.
GROUPS = ["", "Broadleaved", "Mixed, mainly broadleaved", "Mixed, mainly conifer", "Conifer", "Young trees",
          "Felled and restocking", "Other and assumed woodland"]
GROUP_KEYS = ["", "broadleaved", "mixed_broad", "mixed_conifer", "conifer", "young", "felled", "other"]
TYPE2GROUP = {"Broadleaved": 1, "Mixed mainly broadleaved": 2, "Mixed mainly conifer": 3, "Conifer": 4, "Young trees": 5,
              "Felled": 6, "Ground prep": 6, "Windblow": 6, "Failed": 6,
              "Low density": 7, "Shrub": 7, "Coppice": 7, "Coppice with standards": 7, "Assumed woodland": 7}
GROUP_COL = ["#000000", "#3E8E3A", "#86A845", "#4E8F7A", "#1D5C5E", "#BFD47E", "#CDB78C", "#A9B7A0"]

# 100 m raster on the British National Grid
CELL = 100
NX, NY = 7000, 12500   # 0 to 700 km east, 0 to 1250 km north


def load_nfi():
    """The full NFI GB 2024: the main file plus the offsets the first pass missed. Returns a list of tuples."""
    d = json.load(gzip.open(os.path.join(D17, "nfi_gb_2024_centroids.json.gz")))
    m = json.load(gzip.open(os.path.join(D17, "nfi_missing.json.gz")))
    T, C, K = d["types"], d["cats"], d["countries"]
    rows = [(r[0], r[1], T[r[2]], C[r[3]], K[r[4]], float(r[5])) for r in d["rows"]]
    rows += [(r[0], r[1], r[2], r[3], r[4], float(r[5])) for r in m["rows"]]
    return rows


def mercator_tile_bounds(z, x, y):
    n = 2 ** z
    lon0 = x / n * 360 - 180; lon1 = (x + 1) / n * 360 - 180
    lat0 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    lat1 = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon0, lat0, lon1, lat1


def tile_pixel_lonlat(z, x, y, size=256):
    n = 2 ** z
    px = (x * size + np.arange(size) + .5) / (n * size)
    py = (y * size + np.arange(size) + .5) / (n * size)
    lon = px * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * py))))
    LON, LAT = np.meshgrid(lon, lat)
    return LON, LAT


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


GB_BBOX = (-8.75, 49.8, 2.0, 60.9)   # lon0, lat0, lon1, lat1

# Colours for genera on the world and GBIF maps: by broad family group, with the most common genera picked out.
FAMILY_COL = {"Pinaceae": "#2E6E73", "Cupressaceae": "#4F6B3A", "Taxaceae": "#3B5A33", "Araucariaceae": "#56794E", "Podocarpaceae": "#56794E",
              "Ginkgoaceae": "#9C9A3C", "Fagaceae": "#9A6A2E", "Nothofagaceae": "#B0844A", "Betulaceae": "#8DB255", "Salicaceae": "#B8C64A",
              "Sapindaceae": "#C5562F", "Oleaceae": "#7C9A6A", "Malvaceae": "#C98E3B", "Ulmaceae": "#6F8F4E", "Rosaceae": "#D27C93",
              "Myrtaceae": "#7F95A8", "Fabaceae": "#D9A520", "Moraceae": "#7E4A86", "Arecaceae": "#C46FA0", "Rhizophoraceae": "#3E9AB0",
              "Acanthaceae": "#3E9AB0", "Dipterocarpaceae": "#A3423A", "Meliaceae": "#A3423A", "Lecythidaceae": "#A3423A",
              "Combretaceae": "#B9893F", "Casuarinaceae": "#6E8A80", "Proteaceae": "#C47A52"}
GENUS_COL = {"Quercus": "#8A5A22", "Fagus": "#B9803A", "Castanea": "#A86B3C", "Pinus": "#1F6F78", "Picea": "#2C4F6B", "Abies": "#3E6F96",
             "Larix": "#6FA3A0", "Betula": "#A9C46A", "Salix": "#C4C948", "Populus": "#9DB04A", "Alnus": "#6E9E52", "Acer": "#C5562F",
             "Fraxinus": "#6F9A7A", "Prunus": "#D27C93", "Sorbus": "#B4495A", "Ilex": "#2F7D4E", "Taxus": "#24502F", "Juniperus": "#5B7F45",
             "Eucalyptus": "#6F8FB0", "Corymbia": "#8BA6C0", "Acacia": "#E2B323", "Vachellia": "#C9902A", "Senegalia": "#D8B04E",
             "Prosopis": "#B87C2E", "Inga": "#E09A3E", "Ficus": "#7E4A86", "Combretum": "#B9893F", "Terminalia": "#9C7A3A",
             "Adansonia": "#C2412D", "Ulmus": "#6F8F4E", "Tilia": "#C98E3B", "Carpinus": "#86A35E", "Platanus": "#8F8A55",
             "Aesculus": "#B5673A", "Robinia": "#C6A44A", "Cupressus": "#4F6B3A", "Nothofagus": "#B0844A", "Melaleuca": "#93A3B5",
             "Callitris": "#5E7F70", "Avicennia": "#3E9AB0", "Rhizophora": "#2D7F9A", "Juglans": "#7B5B3A", "Liquidambar": "#C7633F"}


def genus_colour(genus, family):
    return GENUS_COL.get(genus) or FAMILY_COL.get(family, "#8E8A80")
