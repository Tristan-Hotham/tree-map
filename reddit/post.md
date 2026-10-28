# Reddit post (r/dataisbeautiful)

## Title

[OC] What grows where: every wood in Great Britain by type (13.7% of the land, 19% of Scotland vs 10% of England), and the most typical tree genus in the world's plant records

## Body

I mapped all 641,642 polygons of the National Forest Inventory's 2024 woodland map. Scotland is 19.1% woodland and 71% of its broadleaf and conifer woodland is conifer; England is 10.3% woodland and only 25% conifer. The most wooded 10 km square is in Kielder Forest (81%). For the world I used GBIF records of 88 tree genera, shown as the genus most typical of each place compared with the world as a whole: acacias and eucalypts in Australia, spruce and birch in Scandinavia. Caveat: GBIF counts records, not trees, and Europe and North America hold 86% of plant records on 32% of the land.

Interactive version: https://tristan-hotham.github.io/tree-map/

## Source comment

Source: National Forest Inventory Woodland GB 2024 and Forestry England Subcompartments (© Forestry Commission copyright, contains Ordnance Survey data © Crown copyright and database right 2025, Open Government Licence v3); GBIF.org (28 October 2026) GBIF occurrence density maps (records from many publishers; derived grids CC BY 4.0); ONS boundaries (Open Government Licence v3); Natural Earth (public domain).

Tools: Python (numpy, pandas, shapely, pyproj, mapbox-vector-tile, matplotlib), Leaflet for the interactive map.

Interactive map: https://tristan-hotham.github.io/tree-map/
Blog post: https://blog.tristanhotham.com/2026/10/28/tree-map/
Paper: https://doi.org/10.5281/zenodo.23739845
