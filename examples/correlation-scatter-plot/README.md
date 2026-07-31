**English** | [简体中文](README_zh.md)

# UltraPlot Skill A/B Test: Correlation Scatter Plot

## Experiment provenance

- Each condition was generated in a fresh, projectless Codex task with no
  inherited conversation history.
- The four overall tests were run sequentially. Each task had its own directory
  and input copy and could not read completed sibling runs.
- The skill-disabled task could not read any skill. The skill-enabled task could
  read the skill instructions, while the skill `examples/` directory remained
  inaccessible during generation.
- Both correlation conditions received byte-identical workbook content. The
  artifacts were copied into this example only after the isolated runs finished.
- The controlled prompt factor was whether `$ultraplot-figures` was explicitly
  invoked.

## Input data

- Workbook: [multiple_data.xlsx](data/multiple_data.xlsx)
- Worksheet and shape: `Sheet1`, 4,305 rows × 32 numeric columns
- Structure: four land covers × four models × paired `_0` and `_1` fields
- Land covers: `cropland`, `forest`, `grassland`, `savanna`
- Models: `DNN`, `GBRT`, `LR`, `SVR`
- Complete pairs per land cover: 3,499, 3,965, 4,221, and 4,305;
  63,960 finite pairs across all 16 land-cover/model combinations

## Prompt control

The common request was to create a publication-ready UltraPlot correlation
scatter plot comparing `_0` with `_1` for the four models and four land covers,
and to provide runnable Python plus PDF and PNG. Only this instruction changed:

| Condition | Plotting instruction |
|---|---|
| Skill enabled | `Use [$ultraplot-figures](../../SKILL.md) to create the plot.` |
| Skill disabled | `Use UltraPlot to create the plot.` |

## Figure comparison

### Skill enabled

![Skill-enabled correlation figure](with_skill/correlation_scatter.png)

### Skill disabled

![Skill-disabled correlation figure](without_skill/correlation_scatter_ultraplot.png)

## Output files

| Artifact | Skill enabled | Skill disabled |
|---|---|---|
| Processing | [process_data.py](with_skill/process_data.py) | Included in the plotting script |
| Plotting | [plot_correlation.py](with_skill/plot_correlation.py) | [plot_correlation_ultraplot.py](without_skill/plot_correlation_ultraplot.py) |
| PDF | [correlation_scatter.pdf](with_skill/correlation_scatter.pdf) | [correlation_scatter_ultraplot.pdf](without_skill/correlation_scatter_ultraplot.pdf) |
| PNG | [correlation_scatter.png](with_skill/correlation_scatter.png) | [correlation_scatter_ultraplot.png](without_skill/correlation_scatter_ultraplot.png) |
| Processed pairs | [processed_pairs.csv](with_skill/processed_pairs.csv) | Not written separately |
| Statistics | [correlation_statistics.csv](with_skill/correlation_statistics.csv) | Computed in memory by the plotting script |

## Objective output information

| Item | Skill enabled | Skill disabled |
|---|---:|---:|
| PDF pages | 1 | 1 |
| PDF page size | 182.9996 × 189.8647 mm | 209.5500 × 218.4400 mm |
| PNG dimensions | 7,204 × 7,474 px | 3,300 × 3,440 px |
| PNG resolution metadata | 999.998 dpi | 399.999 dpi |
