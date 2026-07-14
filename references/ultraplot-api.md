# UltraPlot API and style

Use this file for UltraPlot syntax, styling, colors, fonts, and common API issues.

## Setup

For scripts or headless execution, set the backend before importing UltraPlot:

```python
import matplotlib
matplotlib.use("Agg")

import ultraplot as uplt
```

UltraPlot is a Matplotlib-compatible wrapper. Use Matplotlib axes methods when
needed, but create and format figures through UltraPlot where practical.

## Version and capability validation

The validated primary path is UltraPlot 2.4.x. After a package upgrade or before a
figure relies on semantic scatter-size legends, run:

```bash
python scripts/ultraplot_compat.py --strict
```

The smoke check reports UltraPlot and Matplotlib versions and verifies:

- relative scatter-size mapping with `s=values`, `smin=...`, and `smax=...`;
- scatter-aware `sizelegend(values=..., smin=..., smax=...)` behavior;
- physical legend unit specs such as `"6pt"`;
- legend discovery through `fig.findobj(match=Legend)`;
- journal-preset dimensions after the final draw.

Successful reports are cached by interpreter, Python/UltraPlot/Matplotlib versions,
platform, and helper hash. A changed key reruns automatically; use
`--refresh-cache` after suspicious behavior or `--no-cache` for an isolated probe.
This environment cache never replaces per-figure QA.

Do not use `hasattr(ax, "sizelegend")` as the compatibility decision. A method name
can exist while its accepted keywords or mapping behavior differ. Use a manual-handle
fallback only after its values, marker areas, and rendered geometry are explicitly
validated.

Some Matplotlib keywords drift across versions. For `boxplot`/`violinplot`, set
category tick labels through `format(xlocator=..., xticklabels=...)` instead of a
`labels=`/`tick_labels=` keyword. Pin and record a known-good environment when exact
behavior matters.

## Figure construction

Common layouts:

```python
JOURNAL = "nat2"

fig, ax = uplt.subplots(refwidth=4)
fig, axs = uplt.subplots(ncols=2, nrows=2)
fig, axs = uplt.subplots([[1, 1, 2], [3, 4, 4]], journal=JOURNAL)
fig, axs = uplt.subplots(proj={1: "robin"}, journal=JOURNAL)
```

Useful sizing controls:

- `refwidth`, `refheight`, `refaspect`: reference subplot size;
- `figwidth`, `figheight`: total figure size, including unit strings such as `"89mm"`;
- `journal`: publication presets such as `nat1`, `nat2`, `aaas1`, `aaas2`,
  `pnas1`, `pnas2`, `agu1`, `agu2`;
- `share`, `span`: axis sharing and label spanning; defaults are usually best.

Use the target venue's named preset or physical dimensions first. Only when the
target venue, physical size, and explicit output requirements are all unknown should
`JOURNAL = "nat2"` act as the skill fallback. Use `refwidth`, `refheight`, and
`refaspect` as layout controls when panel geometry or render QA shows a preset is
unsuitable. Use explicit `figwidth` or `figheight` when the target supplies a
physical size not covered by a verified preset.

Let UltraPlot manage subplot spacing on the first render. UltraPlot 2.4 defaults to
`subplots.tight=True`; `wpad`, `hpad`, `wspace`, and `hspace` default to `None`, while
`innerpad`, `outerpad`, and `panelpad` already have rc defaults. Therefore do not
initially pass any of those arguments, `pad`/`space`, or fixed margin arguments.
This lets `auto_layout` account for labels, tick labels, guides, and shared axes.
After the final draw, if a concrete overlap, clipping, or wasted-space defect remains,
add the narrowest single override and record the symptom. An explicit target request
for a fixed physical gap is also a valid reason. Do not add several speculative
spacing controls at once.

Keep `share` and `span` at defaults in first-pass layouts. Set `share=False` or
`span=False` only when panels have incompatible variables, units, projections, or
shared labels would mislead readers.

`axs` is a `SubplotGrid`: iterate with `for ax in axs`, index with `axs[0]` or
`axs[row, col]`, and format subsets such as `axs[:, 0].format(...)`.

### Final physical size

Constructor dimensions are provisional. UltraPlot journal sizing and auto-layout
can change the canvas when legends, colorbars, labels, and panels are realized. Add
every artist and guide, then force the final draw before measuring:

```python
fig.canvas.draw()
width_mm, height_mm = fig.get_size_inches() * 25.4
```

Run `render_qa.audit_figure(...)` at this point. After saving, verify physical size
again from the PDF/TIFF/SVG artifact; do not assume the constructor request is the
saved result.

## Plotting commands

Use normal axes methods:

- 1-D: `plot`, `line`, `scatter`, `bar`, `barh`, `area`, `fill_between`, `step`,
  `vlines`, `hlines`;
- 2-D: `pcolormesh`, `pcolor`, `contour`, `contourf`, `imshow`, `heatmap`,
  `quiver`, `streamplot`;
- statistical: `hist`, `hist2d`, `kde`, `boxplot`/`box`, `violinplot`/`violin`;
- maps: create map axes with `proj=...` and pass data transforms such as
  `transform=ccrs.PlateCarree()` where Cartopy requires them.

For uncertainty, prefer explicit arrays or clearly named summaries. State whether
error bars are SD, SEM, CI, percentile intervals, or model uncertainty.

### Scatter marker-size semantics

Matplotlib/UltraPlot scatter marker area is measured in points squared. In
UltraPlot 2.4.x, a scalar `s` normally behaves as an absolute area
(`absolute_size=True`), while array-like `s` or an explicit `smin`/`smax` normally
uses semantic relative scaling (`absolute_size=False`). Make the intended mode
explicit whenever marker size carries scientific meaning.

For a semantic size encoding, pass original values to both scatter and sizelegend:

```python
values = magnitude.to_numpy()
levels = [5, 6, 7]
points = ax.scatter(x, y, s=values, smin=8, smax=80)
handles, labels = ax.sizelegend(
    levels, values=values, smin=8, smax=80, add=False
)
```

Do not pre-scale values into marker areas and then pass them to the default relative
scatter path, because UltraPlot will scale them again. If areas are deliberately
precomputed in points squared, use `absolute_size=True` and construct legend handles
from the exact same area function. Verify the scatter and legend mapping with
`render_qa.audit_figure(...)`.

### Continuous versus discrete pseudocolor

UltraPlot supports both continuous and discrete color normalization. For
`pcolor` and `pcolormesh`, the default behavior can apply
`ultraplot.colors.DiscreteNorm` depending on `rc["cmap.discrete"]` and the
command default. This is useful for real levels, thresholds, and classes, but it
is not appropriate for continuous scalar fields such as density, anomaly
magnitude, elevation, or model output.

For continuous fields, explicitly pass `discrete=False` and use a continuous
normalizer when needed:

```python
from matplotlib.colors import LogNorm

m = ax.pcolormesh(
    xedges,
    yedges,
    counts,
    cmap="viridis",
    norm=LogNorm(vmin=1, vmax=counts.max()),
    discrete=False,
    shading="auto",
)
ax.colorbar(m, loc="r", label="Pixels per bin")
```

For true classes, fixed bins, or documented thresholds, use discrete colors,
`levels` or `values`, and category labels or a clearly labeled discrete guide.
Do not infer that gridded data are discrete merely because they are plotted with
`pcolormesh`.

### Heatmap cell labels

Use UltraPlot's built-in heatmap label interface rather than a manual nested
`ax.text(...)` loop:

```python
ax.heatmap(
    matrix,
    cmap="vik",
    labels=SHOW_CELL_LABELS,
    precision=2,
    labels_kw={"fontsize": "small"},
)
```

There is no universal matrix-dimension cutoff. Enable labels only when they remain
legible and non-overlapping at the measured final physical size; otherwise omit
them or use selective annotation. Confirm the result with render QA.

## Formatting

Use `fig.format()`, `axs.format()`, and `ax.format()` for common layout and axis
settings instead of many setter calls:

```python
axs.format(
    abc="a",
    abcloc="ul",
    xlabel="x",
    ylabel="y",
    grid=True,
)
```

Leave axis limits automatic unless the scale has semantic meaning, panels must
share a common scale, or render QA shows clipping or hidden data.

For publication-style multi-panel figures, keep `abcloc="ul"` unless a concrete
data-coverage or journal requirement justifies another location. If panel letters
clash with statistics, legends, or annotation text, move the clashing item rather
than the panel letter.

Do not add per-subplot `title=` values by default. Prefer axis labels, guide labels,
panel letters, and the caption. Add subplot titles only when explicitly requested or
when otherwise ambiguous panels must stand alone; pass `allow_subplot_titles=True`
to semantic QA in that case. Apply the same restraint to `suptitle=`.

Use UltraPlot locations for legends and colorbars:

```python
m = ax.pcolormesh(z, cmap="viridis", colorbar="r", colorbar_kw={"label": "Value"})
ax.plot(x, y, label="Series")
ax.legend(loc="b", ncols=2, frame=False)
```

Prefer UltraPlot-managed outer placement (`loc`, `ref`, `span`, `pad`, `space`, and
panel allocation) over manual `bbox_to_anchor`. For guides that explain an encoding
rather than existing artists, prefer semantic helpers such as `sizelegend`,
`catlegend`, `numlegend`, `geolegend`, or `entrylegend`.

Outer guide spacing and internal legend spacing are different controls:

```python
legend = ax.legend(
    handles,
    labels,
    loc="r",                 # outer placement
    space="6pt",            # guide-to-axes/figure spacing
    frame=False,
    borderpad="4pt",        # internal frame padding
    handletextpad="6pt",    # handle-to-label gap
    labelspacing="6pt",     # row-to-row gap
    columnspacing="8pt",    # column-to-column gap
)
```

Use physical unit specs for publication-critical spacing. After the final draw,
discover every legend rather than assuming `ax.get_legend()` is complete:

```python
from matplotlib.legend import Legend
legends = fig.findobj(match=Legend)
```

Run geometry QA for title/entry, handle/text, handle/handle, text/text, clipping, and
frame containment. Fall back to manual handles only when the semantic guide API cannot
represent the encoding and the replacement mapping is validated.

For labels attached to plotted marks, prefer plotting-call parameters over manual
coordinate text. For ordinary bar labels, use the built-in bar-label interface:

```python
ax.barh(
    y,
    values,
    bar_labels=True,
    bar_labels_kw={"fmt": "%.1f%%", "padding": 3},
)
```

Use `ax.text(...)` only for freeform annotations that are not supported by the
plotting call, formatting method, or guide API.

For colorbars, first use UltraPlot/Matplotlib's ordinary guide behavior. After
render checks, adjust ticks only when automatic ticks are unclear, too dense,
normalized artifacts, or imply thresholds that are not part of the analysis. Use
the returned colorbar object's `set_ticks`, `set_ticklabels`, locator, or formatter
as a targeted fix. Keep ticks in the data quantity's units or named categories, and
explain nonlinear normalization outside the tick labels.

For in-panel annotations, use `ax.text(...)` or `ax.annotate(...)` with axes
coordinates. Add a subtle background only when needed for legibility. A single
annotation does not need a config wrapper; for repeated panel annotations, put text,
position, and optional background settings in the script config. Minimal pattern:

```python
ax.text(x_axes, y_axes, label_text, transform=ax.transAxes, bbox=bbox_or_none)
```

If the annotation is already legible in an empty region, omit `bbox`. Do not use an
annotation background as a decorative panel.

Save with explicit extensions and only the formats required by the target. When the
target venue, physical size, and explicit output requirements are all unknown, copy
the canonical standalone `save_publication_fallback(...)` template from
`references/scientific-figures.md` into the delivered script. It writes Type 42 PDF
plus a white-background 600 dpi RGB TIFF with lossless LZW. Do not import the helper
from the installed skill, and do not assume that a direct `fig.save(..., dpi=600)`
has produced the required TIFF mode or compression. Verify the saved artifacts with
`require_tiff_mode="RGB"` and `require_tiff_compression="lzw"` through
`check_figure.audit_files(...)`.

A named target's formats, compression, alpha, color mode, and file-size rules override
the fallback.

Do not save PNG by default. Add a separate `fig.save("figure.png", dpi=300)` only
when the user explicitly asks for PNG, a preview image, a quick draft, or a
check-only raster. The Python script and input data remain the editable authority;
PDF/SVG are vector-preserving production outputs. Follow
`references/scientific-figures.md` for publication deliverables.

## Colors and style

Use UltraPlot defaults first. Do not set global font-size rc values or font families
in ordinary first-pass scripts. Override typography only for message clarity,
accessibility, publication rules, CJK text, or a visible render problem.

For one-off style overrides, prefer scoped settings:

```python
with uplt.rc.context({"axes.grid": True}):
    fig, ax = uplt.subplots(refwidth=4)
```

Use global `uplt.rc.update(...)` only for deliberate script-wide or session-wide
defaults, and keep the scope clear in the final report.

Color rules:

- sequential data: `viridis`, `cividis`, `Blues`, `Reds`, `davos`, `turku`;
- signed anomalies or correlations: diverging palette centered on the meaningful
  zero or baseline;
- categories: colorblind-safe discrete colors, with shape or line style if color
  alone is insufficient;
- avoid `jet`/rainbow unless a field-specific convention justifies it.

UltraPlot named colors such as `blue7`, `gray6`, `red3`, and `sky blue` are useful
for scalar color arguments. For arrays of per-point colors, prefer hex codes or
standard Matplotlib color names to avoid backend-specific color parsing issues.
Use `uplt.Cycle(...)` for custom cycles and `norm=`/`levels=` for controlled color
scaling.

When choosing palettes interactively or for reusable scripts, prefer UltraPlot's
registered colormaps, cycles, and named colors over ad hoc hex values. Hex values
remain appropriate for journal, brand, or GIS standard colors.

Aspect heuristics:

- time series: wider than tall;
- distributions and category comparisons: moderate or vertical;
- maps and rasters: preserve geographic or pixel aspect when possible;
- multi-panel figures: use shared scales only when direct comparison is intended.

## CJK text

Follow the target journal or publisher's font policy. Do not impose a universal
SimSun/Times New Roman pairing: venue rules, operating-system availability, glyph
coverage, mathematical notation, and embedding requirements differ.

Check candidate fonts when exact typography matters:

```python
from matplotlib import font_manager

available_fonts = {font.name for font in font_manager.fontManager.ttflist}
missing = set(REQUIRED_FONTS) - available_fonts
if missing:
    raise RuntimeError(f"Missing required fonts: {sorted(missing)}")
```

Use a tested fallback stack that covers every required CJK and Latin glyph, and embed
fonts according to the target policy. Import UltraPlot first, then keep the delivery
settings scoped through figure creation and saving. UltraPlot initializes rc settings
at import time, so a Matplotlib `pdf.fonttype` value set before `import ultraplot` is
not a reliable final-delivery control:

```python
with uplt.rc.context({
    "font.family": REQUIRED_FONT_STACK,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}):
    fig, ax = uplt.subplots(journal=JOURNAL)
    # ... add all artists, draw, and run render QA ...
    fig.save(OUTPUT_PDF)
```

If mixed-script strings require different fonts, set them on the actual text artists
or split the text into controlled artists. Verify glyph rendering in the final PDF
and raster output. If the selected font lacks the Unicode minus sign, use
`axes.unicode_minus=False` only as a documented fallback rather than a global habit.

## Troubleshooting

- Import fails: install `ultraplot`; install optional packages only when used
  (`cartopy`, `geopandas`, `xarray`, `Pillow`, etc.).
- Missing labels in panels: check `share` and `span`.
- Figure saved as the wrong format: give an explicit extension.
- Legend overlaps: first identify whether the collision is external or internal.
  Use `loc`/`space`/`pad` for guide-to-axes spacing and
  `borderpad`/`handletextpad`/`labelspacing`/`columnspacing` for entry geometry,
  then force a final draw and run `render_qa`; moving the legend outside alone is
  not sufficient.
- Colorbar overlaps: prefer an UltraPlot outer panel and verify the final draw;
  change panel padding only after a rendered defect is observed.
- Continuous pseudocolor looks banded: first check whether the returned mappable
  uses `ultraplot.colors.DiscreteNorm`. For continuous fields, set
  `discrete=False` on `pcolor`/`pcolormesh`, then re-render. Bypass UltraPlot with
  lower-level Matplotlib calls only after checking the local API behavior with
  help/source or a minimal reproduction.
- Dense vector output is huge: rasterize heavy point/mesh layers while keeping text
  vector.
- Map data appear misplaced: check CRS/projection and `transform=...`.
- Windows geospatial imports warn that `GDAL_DATA is not defined`: load
  `references/domains/geospatial-setup.md` and diagnose the active environment.
- Color array fails or renders unexpectedly: replace UltraPlot named colors inside
  arrays with hex codes.
- API uncertainty: record the installed versions, inspect the local signature,
  docstring, or source, and run a minimal reproduction in the system temporary
  directory. For 2.4.x size guides run `ultraplot_compat.py --strict`; successful
  environment checks are cached, and `--refresh-cache` forces a rerun. Do not rely
  on `hasattr(...)` alone.
