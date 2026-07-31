**English** | [Simplified Chinese](README_zh.md)

# UltraPlot Skill A/B Test: Global M5+ Earthquakes in 2025

## Input data

- GeoJSON: [usgs_earthquakes_2025_m5plus.geojson](data/usgs_earthquakes_2025_m5plus.geojson)
- Source features: 2,129
- Retained earthquakes: 2,128
- Explicitly excluded: one feature with `properties.type == "landslide"`
- Magnitude range: M5.0-M8.8; depth range: 3.0-648.298 km

## Prompt control

The prompt text below is restored from repository history. The input file is
shown using its repository-relative path to avoid exposing machine-specific
information. The full effective prompt for each condition consists of its
condition-specific instruction plus the common task below.

The common task was:

> Plotting data file: `data/usgs_earthquakes_2025_m5plus.geojson`
>
> Use UltraPlot to show the spatial distribution, magnitude, and depth
> characteristics of global M5+ earthquakes in 2025, so readers can understand
> their global pattern and major characteristics directly.
>
> Provide directly runnable Python code and export PDF and PNG.

Only the plotting instruction changed:

| Condition | Plotting instruction |
|---|---|
| With skill | `Use [$ultraplot-figures](../../SKILL.md) for plotting.` |
| Without skill | `Use UltraPlot for plotting.` |

## Figure comparison

### With `ultraplot-figures`

![Skill-enabled earthquake figure](with_skill/global_earthquakes_2025_m5plus.png)

### Without skill

![Skill-disabled earthquake figure](without_skill/global_earthquakes_2025_m5plus.png)

## Retained files

| Type | With skill | Without skill |
|---|---|---|
| Analysis and plotting | [plot_global_earthquakes.py](with_skill/plot_global_earthquakes.py) | [plot_global_earthquakes_2025.py](without_skill/plot_global_earthquakes_2025.py) |
| PDF | [global_earthquakes_2025_m5plus.pdf](with_skill/global_earthquakes_2025_m5plus.pdf) | [global_earthquakes_2025_m5plus.pdf](without_skill/global_earthquakes_2025_m5plus.pdf) |
| PNG | [global_earthquakes_2025_m5plus.png](with_skill/global_earthquakes_2025_m5plus.png) | [global_earthquakes_2025_m5plus.png](without_skill/global_earthquakes_2025_m5plus.png) |

## Objective output information

| Item | With skill | Without skill |
|---|---:|---:|
| PDF pages | 1 | 1 |
| PDF page size | 182.9996 x 116.6052 mm | 348.3003 x 194.2059 mm |
| PNG dimensions | 7,204 x 4,590 px | 4,113 x 2,293 px |
| PNG resolution metadata | 999.998 dpi | 299.999 dpi |
| Display projection | Plate Carree, central longitude 0 | Robinson, central longitude 0 |
