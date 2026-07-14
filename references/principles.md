# Scientific figure principles

Use this file for publication-facing figures, reviewer-facing revisions, or any
plot where design choices could change interpretation. Keep citations and source
attribution in `README.md`; use this file for operational judgment.

## Core principles

1. Start from the claim. Define the comparison, trend, distribution, map pattern,
   or diagnostic before choosing the plot. In multi-panel figures, every panel
   must support the main message or a necessary method check.
2. Use accurate encodings. Prefer position and length for precise quantitative
   comparisons. Avoid area, angle, volume, and decorative effects when readers
   need to compare values.
3. Match the chart to the data structure. Use ordered charts for ordered data,
   scatter or density views for relationships, distribution plots for variation,
   gridded plots for matrices or fields, and map projections with explicit
   coordinate transforms for spatial data.
4. Show data granularity where feasible. For small samples, prefer raw points plus
   interval, box, or violin over mean-only bars. For large samples, control
   overplotting with transparency, density, hexbin, rasterization, or faceting.
5. Label uncertainty honestly. State whether intervals are SD, SEM, CI,
   percentile, bootstrap, model uncertainty, or prediction intervals. Report the
   sample size or comparison definition when it affects interpretation.
6. Avoid misleading summaries and axes. Do not silently truncate bar baselines,
   use unordered line charts, add gratuitous dual axes, over-smooth patterns, or
   use pie/donut charts for many-category comparison. For contour or colorbar
   limits with real under/over values, use `extend="both"` (or `"min"`/`"max"`)
   when appropriate. The triangular or rectangular shapes are colorbar extension
   caps that signal under/over ranges; the data themselves remain encoded by the
   under/over or endpoint colors and do not become triangles.
7. Use color for meaning, not decoration. Use colorblind-safe categorical
   palettes, perceptually ordered sequential maps, and diverging maps centered on
   a meaningful baseline. Avoid rainbow or `jet` unless a field convention
   explicitly requires it.
8. Do not rely on color alone. Add marker shape, line style, hatching, direct
   labels, facets, or annotation when categories or thresholds must survive
   grayscale printing or color-vision differences.
9. Design and verify at final physical size. Configure the target journal preset
   or explicit dimensions before plotting, add every artist and guide, call
   `fig.canvas.draw()`, then measure `fig.get_size_inches() * 25.4`. Constructor
   dimensions are provisional because UltraPlot auto-layout and guide panels can
   change the final canvas on draw.
10. Treat guide geometry as scientific readability, not decoration. Outer guide
    placement and inside-legend spacing are separate. Marker/title, marker/text,
    marker/marker, text/text, clipping, or frame-containment collisions are hard
    defects; fix and rerun geometry QA rather than assuming an outer legend panel
    solved the problem.
11. Preserve traceability and verify the artifact. Put thresholds, filters,
    transformations, statistics, and export settings in the script config. Inspect
    the actual saved PDF/TIFF/SVG dimensions and resources, plus PNG only when
    explicitly requested, and fix wrong physical size, DPI, fonts, clipping,
    hidden data, wrong units, or poor contrast before delivery.
12. Make the caption reproducible. Record critical processing choices: filtering,
    normalization, baseline period, coordinate reference system, test/correction,
    sample size, and any omitted uncertainty.
13. Check accessibility explicitly when color carries meaning. Use redundant
    encodings, grayscale-tolerant contrast, direct labels, or facets rather than
    relying on hue alone.

## Encoding audit

Before plotting, list each visual channel and the variable it encodes:

| Channel | Examples |
|---|---|
| x/y position | primary quantitative comparison |
| color | group, depth, anomaly, significance, density |
| marker size | magnitude, count, weight, uncertainty only when necessary |
| alpha/rasterization | overplotting control, not a primary scientific variable |
| line style/marker shape | redundant category encoding |

Avoid encoding the same variable twice in one panel unless the redundancy is
intentional and improves readability. If a variable is already on an axis, do not
also encode it by marker size by default.

Each legend must explain one active encoding. If an encoding is used only in one
panel, place its legend with that panel. If it is shared across panels, use a
figure-level legend or colorbar. For semantic marker size, the plotted scatter and
its legend must share the same original data domain and output marker-area range.
