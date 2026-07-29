**English** | [简体中文](README_zh.md)

# UltraPlot Skill A/B Test: Correlation Scatter Plot

This example compares two independently generated UltraPlot solutions for the same
correlation-scatter task. The only prompt difference is whether
`$ultraplot-figures` is explicitly invoked.

## Input data

- Workbook: [multiple_data.xlsx](data/multiple_data.xlsx)
- Worksheet: `Sheet1`
- Shape: 4,305 rows × 32 numeric columns
- Structure: four land-cover classes × four models × paired `_0` and `_1` fields
- Land-cover classes: `cropland`, `forest`, `grassland`, `savanna`
- Models: `DNN`, `GBRT`, `LR`, `SVR`
- Valid pairs per panel: 3,499, 3,965, 4,221, and 4,305 by land-cover row
- Total finite pairs shown across the 16 panels: 63,960
- Units and descriptive variable names are absent from the source and were not invented.

## Prompt control

The common task was:

> Plotting data file: `data/multiple_data.xlsx`
>
> Create a publication-ready correlation scatter plot comparing `_0` and `_1` for
> DNN, GBRT, LR, and SVR across cropland, forest, grassland, and savanna.
>
> Provide directly runnable Python code and export PDF and PNG.

Only the plotting instruction changed:

| Condition | Instruction |
|---|---|
| With skill | `Use [$ultraplot-figures](../../SKILL.md) to create the plot.` |
| Without skill | `Use UltraPlot to create the plot.` |

## Figure comparison

| With `$ultraplot-figures` | Without skill |
|:---:|:---:|
| ![Correlation scatter plot generated with the skill](with_skill/correlation_scatter_with_skill.png) | ![Correlation scatter plot generated without the skill](without_skill/correlation_scatter.png) |

## Output files

| Type | With `$ultraplot-figures` | Without skill |
|---|---|---|
| Processing script | [prepare_correlation_with_skill.py](with_skill/prepare_correlation_with_skill.py) | Processing occurs in the plotting script |
| Plotting script | [plot_correlation_with_skill.py](with_skill/plot_correlation_with_skill.py) | [correlation_scatter_ultraplot.py](without_skill/correlation_scatter_ultraplot.py) |
| PDF | [correlation_scatter_with_skill.pdf](with_skill/correlation_scatter_with_skill.pdf) | [correlation_scatter.pdf](without_skill/correlation_scatter.pdf) |
| PNG | [correlation_scatter_with_skill.png](with_skill/correlation_scatter_with_skill.png) | [correlation_scatter.png](without_skill/correlation_scatter.png) |
| Processed paired data | [correlation_pairs_with_skill.csv](with_skill/correlation_pairs_with_skill.csv) | Not written separately |
| Panel statistics | [correlation_stats_with_skill.csv](with_skill/correlation_stats_with_skill.csv) | [correlation_statistics.csv](without_skill/correlation_statistics.csv) |
| Data audit | [data_audit_with_skill.json](with_skill/data_audit_with_skill.json) | Printed and asserted by the script |
| Figure verification | [verification_with_skill.json](with_skill/verification_with_skill.json) | Assertions and console report in the script |

## Objective output information

| Item | With `$ultraplot-figures` | Without skill |
|---|---:|---:|
| PDF pages | 1 | 1 |
| PDF page size | 183.000 × 187.977 mm | 191.385 × 185.148 mm |
| PNG dimensions | 7,204 × 7,400 px | 3,013 × 2,915 px |
| PNG resolution metadata | 999.998 dpi | 399.999 dpi |
