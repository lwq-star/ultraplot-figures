# UltraPlot recipes

Use these as small editable starting points. Replace synthetic arrays with real data
and keep paths/settings in a top config block. For publication-facing deliverables,
follow the target venue first and `references/scientific-figures.md` second. The
`nat2` + PDF + 600 dpi TIFF combination shown below is only a fallback when the
target venue, physical size, and explicit output requirements are all unknown.

Recipes are starting points, not copy-ready scientific decisions. Audit layout,
encoding, guide ownership, units, final physical size, and export settings before
reusing a recipe on a new dataset.

Start with UltraPlot defaults. Do not add `innerpad`, `outerpad`, `panelpad`, `wpad`,
`hpad`, `pad`, `hspace`, `wspace`, `space`, manual margins, global font-size rc
settings, gridline linewidths, or gridline colors in first-pass recipes. Do not add
subplot titles. Render once, then add the narrowest single override needed for real
overlap, clipping, poor contrast, or a target-style requirement, and record why.

## Common script header

```python
import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import numpy as np
import ultraplot as uplt

OUTPUT_DIR = Path("figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOURNAL = "nat2"  # only when venue, size, and output rules are all unknown
DPI = 600         # fallback raster resolution
```

For this fallback, copy the standalone `save_publication_fallback` function and
`FALLBACK_RC` settings from `references/scientific-figures.md` into the delivered
script. Do not import them from the installed skill. Keep production artists opaque;
the helper writes Type 42 PDF plus a white-background RGB LZW TIFF.

When adapting several recipes in one script, use figure-specific output names such as
`scatter.pdf` and `scatter.tif`. Save only formats required by the target. Do not add
PNG outputs unless the user explicitly requests PNG, preview images, quick drafts, or
check-only rasters.

## Line

```python
fig, ax = uplt.subplots(journal=JOURNAL)
ax.plot(x, y1, label="A", color="blue7")
ax.plot(x, y2, label="B", color="orange7")
ax.legend(loc="b", ncols=2, frame=False)
ax.format(xlabel="Time", ylabel="Value", grid=True)
save_publication_fallback(fig, OUTPUT_DIR / "line", dpi=DPI)
```

## Scatter with colorbar

```python
fig, ax = uplt.subplots(journal=JOURNAL)
ax.scatter(
    x,
    y,
    c=z,
    cmap="viridis",
    s=18,
    absolute_size=True,
    colorbar="r",
    colorbar_kw={"label": "z (units)"},
    rasterized=True,
)
ax.format(xlabel="x", ylabel="y", grid=True)
save_publication_fallback(fig, OUTPUT_DIR / "scatter", dpi=DPI)
```

A scalar `s` is an absolute marker area in points squared here. For a semantic
array-valued size encoding, pass original values with `smin`/`smax` and build a
`sizelegend` from the same values and area range; see `references/ultraplot-api.md`.

## Grouped or stacked bars

```python
fig, ax = uplt.subplots(journal=JOURNAL)
ax.bar(x - width / 2, control, width=width, label="Control", color="blue6")
ax.bar(x + width / 2, treatment, width=width, label="Treatment", color="orange6")
ax.legend(loc="t", ncols=2, frame=False)
ax.format(xlocator=x, xticklabels=groups, ylabel="Value", grid=True)
save_publication_fallback(fig, OUTPUT_DIR / "grouped_bar", dpi=DPI)
```

For stacked bars, accumulate `bottom` and call `ax.bar(..., bottom=bottom)`. Avoid
truncated bar baselines unless the axis break is explicit and justified.

## Distribution

```python
fig, axs = uplt.subplots(
    ncols=3, journal=JOURNAL, share=False, span=False
)
positions = list(range(1, len(labels) + 1))
axs[0].hist(values, bins=30, color="gray5", edgecolor="white")
axs[0].format(xlabel="Value", ylabel="Count", grid=True)
# Set category tick labels via format() instead of version-sensitive boxplot keywords.
axs[1].boxplot(grouped_values, fillcolor="blue3")
axs[1].format(xlabel="Group", ylabel="Value",
              xlocator=positions, xticklabels=labels, grid=True)
axs[2].violinplot(grouped_values, fillcolor="orange3")
axs[2].format(xlabel="Group", ylabel="Value",
              xlocator=positions, xticklabels=labels, grid=True)
axs.format(abc="a")
save_publication_fallback(fig, OUTPUT_DIR / "distribution", dpi=DPI)
```

For small samples, overlay raw jittered points when possible. For very large samples,
prefer density, hexbin, or rasterization. Use transparency only when the named target
allows it and the opaque fallback is not active.

## Heatmap

```python
SHOW_CELL_LABELS = False  # enable only after final-size render QA proves readability

fig, ax = uplt.subplots(journal=JOURNAL)
ax.heatmap(
    matrix,
    cmap="vik",
    vmin=-1,
    vmax=1,
    labels=SHOW_CELL_LABELS,
    precision=2,
    labels_kw={"fontsize": "small"},
    colorbar="r",
    colorbar_kw={"label": "Correlation"},
)
save_publication_fallback(fig, OUTPUT_DIR / "heatmap", dpi=DPI)
```

Use the built-in `labels`, `precision`, and `labels_kw` interface instead of a manual
nested `ax.text(...)` loop. There is no universal matrix-size cutoff. Enable labels
only when they remain legible and non-overlapping at the measured final physical
size; otherwise omit them or annotate only selected cells.

## Contour or raster map

```python
import cartopy.crs as ccrs

fig, ax = uplt.subplots(proj="robin", journal=JOURNAL)
ax.contourf(
    lon,
    lat,
    field,
    levels=uplt.arange(-1, 1, 0.2),
    cmap="vik",
    extend="both",
    transform=ccrs.PlateCarree(),
    colorbar="b",
    colorbar_kw={"label": "Anomaly (units)"},
)
ax.format(coast=True, lonlines=60, latlines=30)
save_publication_fallback(fig, OUTPUT_DIR / "map", dpi=DPI)
```

For `pcolormesh`, pass `discrete=False` for a continuous field and prefer
`shading="auto"`. For global data crossing the dateline, normalize longitudes or add
a cyclic column before plotting.

## Layout refinement after render check

Only add these after the first render demonstrates a real layout problem:

```python
fig, axs = uplt.subplots(layout, refwidth=2.4, innerpad=1.2)
# Reason: the first render showed [specific overlap or wasted-space defect].
# Use hspace/wspace only when the target explicitly requires a fixed physical gap.
```

After every artist and guide exists, call `fig.canvas.draw()` and run
`render_qa.audit_figure(...)`. Document the symptom each override fixes, such as
legend handle/text overlap, overlapping tick labels, or a clipped colorbar title.

## Error band

```python
fig, ax = uplt.subplots(journal=JOURNAL)
ax.plot(x, mean, color="blue7", label="Mean")
ax.fill_between(x, lo, hi, color="blue2", label="95% CI")
ax.legend(loc="b", frame=False)
ax.format(xlabel="Time", ylabel="Response", grid=True)
save_publication_fallback(fig, OUTPUT_DIR / "line_ci", dpi=DPI)
```

State whether the band is SD, SEM, CI, percentile interval, bootstrap interval, or
model uncertainty.
