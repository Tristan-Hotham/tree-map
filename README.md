# What grows where: the trees of Britain and the world

An explorable map of which trees grow where, with two views. **Great Britain**: every National Forest Inventory (NFI) 2024 woodland polygon by interpreted type, a 1 km and 5 km summary of woodland cover and broadleaf/conifer mix, the share of plant records for any of 88 tree genera from GBIF, and the species and planting year of every Forestry England compartment. **The world**: the most recorded and the most typical tree genus in each 0.35 degree cell, any genus on its own, and a map of recording effort. Click anywhere to see what grows there, or search a town, wood, postcode or world city. A "Map layers" panel sets the base map, hills, place names, borders and colour strength.

**Interactive version:** https://tristan-hotham.github.io/tree-map/

**Paper and archived release:** https://doi.org/10.5281/zenodo.23739845

A data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- Woodland of 0.5 ha and over covers 13.7% of Great Britain's land (3,153 thousand hectares): 19.1% of Scotland, 15.0% of Wales and 10.3% of England.
- Conifers are 71.0% of Scotland's broadleaf and conifer woodland, 40.7% of Wales's and 25.1% of England's.
- Moray is the most wooded county or council area (30.8%), Shetland the least (0.04%); England's most wooded county is Surrey (25.2%). The most wooded 10 km square is NY68 in Kielder Forest (81.1% woodland, 98% conifer).
- In England's public forests 67.1% of the area with a species is conifer; Sitka spruce alone is 25.8%. The broadleaf share of the trees standing today is 47.0% for 1950s plantings, 18.0% for the 1990s and 25.6% for the 2000s.
- GBIF records show pines taking their biggest share of plant records in Strathspey (7.5% in one cell), the home of the native Caledonian pinewoods; willows are the most recorded tree genus in 2,863 of 4,089 well recorded British cells, a sign of recording habits rather than abundance.
- Worldwide, the most typical recorded genus gives each continent a signature (acacias, bloodwoods and eucalypts in Oceania; figs, thorn acacias and bushwillows in Africa; Inga in South America), but Europe and North America hold 86.3% of land plant records on 32.1% of the land, and the tropics 6.6% on 34.1%.

Every number is in `data/results.json`, which the page, paper, blog and collage are built from.

## Files

| Path | What it is |
|---|---|
| `index.html` | The interactive page. Results and the tile index are embedded; tiles, grids, places and borders load from `data/`. |
| `header.png` | Social card (1200 by 630). |
| `data/tiles/wood_<z>.json` | NFI woodland by type, Web Mercator tiles, zooms 5 to 10 (paletted PNG, packed as base64 in one JSON file per zoom). |
| `data/tiles/mix1_<z>.json`, `data/tiles/mix5_<z>.json` | Woodland cover and broadleaf/conifer mix on 1 km and 5 km squares. |
| `data/tiles/hill_<z>.json` | Hill shading for Great Britain, zooms 5 to 9. |
| `data/gb/km1.png`, `data/gb/cells5.json` | 1 km lookup grid (woodland %, conifer share, main type) and 5 km type breakdowns for the click panel. |
| `data/gbif/world_base.json`, `data/gbif/world/*.json`, `data/gbif/gb.json` | Derived GBIF grids: plant and conifer records and top genera per 0.35 degree cell; record counts per cell for each genus; the 0.088 degree grid over Britain. |
| `data/fe_points.json` | Forestry England compartments (centroid, species, planting year, area, land use) for the map. |
| `data/nations.csv`, `data/counties.csv` | Woodland by country and by county or council area, by type group, with land area. |
| `data/nfi_types.csv` | NFI polygons and area by interpreted type and country. |
| `data/gb_1km.csv.gz`, `data/gb_5km.csv`, `data/gb_10km.csv` | Woodland by type group on National Grid squares (south west corner in km). |
| `data/world_cells.csv` | World 0.35 degree cells: plant and conifer records, top three genera, most typical genus. |
| `data/genera.csv` | The 88 genera with GBIF keys and world record counts. |
| `data/fe_species.csv`, `data/fe_planting_decades.csv` | Forestry England area by species, and by decade planted. |
| `data/ctx/`, `data/places/` | Simplified borders (ONS counties, Natural Earth countries) and place names (OS Open Names, GeoNames). |
| `data/results.json` | Every number used anywhere. |
| `code/` | The pipeline (below). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `release/` | Paper PDF and source, blog post and figures, Zenodo files. |

## Method in brief

- **Woodland.** NFI GB 2024 (layer NFI_GB_IFT_Data_20250826), 641,642 polygons as centroids with type, category, country and area, from two extracts that together give the full count with no duplicates. Fourteen woodland types are grouped into seven. Each polygon is drawn as a disc of its own area at its centroid on a 100 m grid for the maps and grid summaries; county and country totals use exact polygon areas assigned by centroid. Land area from ONS boundaries (ceremonial counties, preserved counties of Wales, Scottish council areas).
- **Public forests.** Forestry England subcompartments (73,109) with main species, planting year (of the current crop) and area; species classed as conifer or broadleaf.
- **Records.** GBIF occurrence density grids (EPSG:4326, zoom 2, square size 8, so 0.0879 degree bins) for 88 tree genera and for Tracheophyta, Pinopsida and Magnoliopsida, decoded and checked on known places. Cedrus and Washingtonia were dropped (matched by GBIF only to Tracheophyta). Each genus is mapped as its share of all vascular plant records, with a minimum of 200 records (world, 0.35 degree cells) or 500 (Britain, 0.088 degree cells). "Most typical" is the highest location quotient among genera with at least 20 records in the cell.

## Known limits

- The NFI covers woodland of 0.5 ha and over in Great Britain only, interpreted from imagery; hedgerows and lone trees are missing. Drawing polygons as discs places area correctly but not shape.
- Forestry England covers only the public estate in England; planting years are of the current crop and often rounded.
- GBIF counts records, not trees; recording effort varies hugely (Europe has 16,081 plant records per 1,000 km², Africa 289). The planned British species grids were not in the download, so the British records layer is at genus level.

## How to rerun

Inputs are read in place from the paths in `code/common.py` (environment variables `TREE_DATA`, `OSNAMES`, `NE_DIR`, `CITIES15000`, `COUNTIES`): the NFI, Forestry England and GBIF downloads, OS Open Names, Natural Earth, GeoNames `cities15000.zip`, ONS-derived counties, and the Terrain Tiles elevation used by the within-sight project (`dem.py`).

```
python3 code/01_nfi.py
python3 code/02_tiles.py
python3 code/10_pack_tiles.py   # packs the tile folders into data/tiles/<layer>_<z>.json
python3 code/03_gbif.py
python3 code/04_context.py
python3 code/05_analyse.py
python3 code/06_build_site.py
FONT_DIR=path/to/fonts python3 code/07_figures.py
python3 code/08_paper.py
python3 code/09_release.py
FONT_DIR=path/to/fonts python3 reddit/collage.py
```

Needs Python 3 with numpy, pandas, scipy, shapely 2, pyproj, Pillow, matplotlib and mapbox-vector-tile, and xelatex with TeX Gyre Pagella and Inter for the paper. Steps 1 to 3 write temporary files to `_work/`, which can be deleted afterwards.

## Sources and licences

- National Forest Inventory Woodland GB 2024 and Forestry England Subcompartments: © Forestry Commission copyright. Contains Ordnance Survey data © Crown copyright and database right 2025. Open Government Licence v3.
- GBIF.org (28 October 2026) GBIF occurrence density maps, https://www.gbif.org. Records are published by many institutions under CC0, CC BY 4.0 and CC BY-NC 4.0; only derived grids are shared here, under CC BY 4.0.
- Boundaries: Office for National Statistics, contains OS data © Crown copyright and database right (Open Government Licence v3).
- OS Open Names: contains OS data © Crown copyright and database right 2026 (Open Government Licence v3). GeoNames: CC BY 4.0. Natural Earth: public domain.
- Hill shading: Terrain Tiles (Mapzen/Tilezen), from SRTM and other public sources. Base map tiles on the page © Esri. Postcode lookups: postcodes.io.

Licences for this repository: code MIT; text and figures CC BY 4.0; data files Open Government Licence v3 where derived from Forestry Commission, ONS or OS data, CC BY 4.0 for the GBIF grids (see `LICENSE`).

## Citation

Hotham, T. (2026) What grows where: mapping the woodland of Great Britain and the recorded trees of the world. Zenodo. https://doi.org/10.5281/zenodo.23739845

## AI statement

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.

Related: [Ancient trees](https://tristan-hotham.github.io/ancient-trees/) · [blog](https://blog.tristanhotham.com/)
