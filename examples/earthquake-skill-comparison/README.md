**English** | [简体中文](README_zh.md)

# Scientific Figure Comparison with `ultraplot-figures`

This example uses the same earthquake data and the same scientific plotting prompt
under two conditions: allowing `$ultraplot-figures`, and allowing no skills. It
places the resulting figures and scripts side by side.

## Test setup

| Condition | With skill | Without skill |
|---|---|---|
| Skill policy | Only `$ultraplot-figures` allowed | No skills allowed |
| Standard Python plotting libraries | Allowed | Allowed, including direct use of UltraPlot |
| Input data | Same GeoJSON | Same GeoJSON |
| Scientific plotting prompt | Identical | Identical |
| Model and client | `GPT-5.6 sol`, Codex Desktop for Windows | `GPT-5.6 sol`, Codex Desktop for Windows |

Before the shared scientific plotting prompt, the two branches received different
condition instructions. The original instructions were in Chinese; the English
translations are:

- With skill: `For the next task, use only $ultraplot-figures and do not use any other skill.`
- Without skill: `For the next task, do not use any skill. You may directly use standard Python plotting libraries, including UltraPlot.`

- Data: [USGS 2025 M5+ earthquake catalog](data/usgs_earthquakes_2025_m5plus.geojson)
- Data source: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/search/)

The model determined the design, layout, and visual encodings for both figures. No
second-round visual redesign or data changes were made after figure generation. For
public use, local file paths were replaced with repository-relative paths and internal
QA scaffolding was removed from the delivered scripts; these code-only changes did not
alter the figure content.

## Shared prompt

The run used the original Chinese prompt shown in the
[Chinese version](README_zh.md#共同提示词). The following is an English translation:

> Create a figure suitable for a scientific paper using the data below.
>
> Data file: `data/usgs_earthquakes_2025_m5plus.geojson`
>
> The figure should show the spatial distribution, magnitude, and depth
> characteristics of global earthquakes with magnitude 5 or greater in 2025, so
> readers can directly understand their global distribution and main features.
>
> Inspect the data first, then choose appropriate plot types, layout, and visual
> expression based on the data. Keep the scientific interpretation cautious and do
> not make inferences beyond what the data support.
>
> Provide an editable Python plotting script, a PDF, and a high-resolution TIFF.

## Figure comparison

| With `$ultraplot-figures` | Without any skill |
|:---:|:---:|
| ![Scientific figure generated with ultraplot-figures](assets/with_skill.png) | ![Scientific figure generated without a skill](assets/without_skill.png) |

Each preview was generated from its final TIFF on a white background and resized to
the same width of 1,400 px. The previews preserve the original aspect ratios and were
not cropped, recolored, or rearranged.

## Output files

| File | With `$ultraplot-figures` | Without any skill |
|---|---|---|
| Python script | [plot_earthquakes_2025.py](with_skill/plot_earthquakes_2025.py) | [plot_earthquakes_2025.py](without_skill/plot_earthquakes_2025.py) |
| PDF | [earthquakes_2025_m5plus.pdf](with_skill/earthquakes_2025_m5plus.pdf) | [earthquakes_2025_m5plus.pdf](without_skill/earthquakes_2025_m5plus.pdf) |
| TIFF | [earthquakes_2025_m5plus.tif](with_skill/earthquakes_2025_m5plus.tif) | [earthquakes_2025_m5plus_600dpi.tif](without_skill/earthquakes_2025_m5plus_600dpi.tif) |

## Objective file information

| Item | With `$ultraplot-figures` | Without any skill |
|---|---:|---:|
| PDF pages | 1 | 1 |
| PDF page size | 183.0 × 180.6 mm | 183.0 × 132.0 mm |
| PDF fonts | Embedded; no Type 3 | Embedded; no Type 3 |
| Embedded PDF raster | None | One colorbar, 960 × 48 px, 600 dpi |
| TIFF pixel dimensions | 4322 × 4266 px | 4322 × 3118 px |
| TIFF resolution | 600 dpi | 600 dpi |
| TIFF color mode | RGB, no alpha | RGB, no alpha |
| TIFF compression | LZW | LZW |
| Script lines | 360 | 532 |

## Reading notes

Each condition independently selected its figure design, layout, and visual
encodings, so layout differences are part of the example results. Researchers should
still review the scientific figures and code against their research question, data
source, and submission requirements.
