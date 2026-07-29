---
name: ultraplot-figures
description: >-
  Create, revise, troubleshoot, review, and validate publication-quality
  scientific figures with UltraPlot (import ultraplot as uplt). Use when a
  user needs an UltraPlot or ProPlot-style figure to be implemented, improved,
  debugged, or audited for scientific integrity, reproducibility,
  accessibility, layout quality, and publication-ready output.
---

# UltraPlot Figures

UltraPlot (`import ultraplot as uplt`) subclasses matplotlib's `Figure`, `Axes`,
and `GridSpec` to remove boilerplate and ship better defaults. Your job with this skill is to produce figures that are **scientifically honest first, beautiful second** — and to lean on UltraPlot's automation instead of hand-rolling matplotlib calls.

## Release update checks

Before the normal workflow, resolve `scripts/update_skill.py` relative to this
`SKILL.md`. Unless the user has prohibited network access, run it with the Python
interpreter selected by the active environment rules and pass `--auto`.

- Automatic release checks are enabled by default and run at most once per local
  calendar day.
- Never download, install, or replace skill files during the check.
- For `update_available`, report the installed and latest versions, recommend
  updating, link the stable GitHub Release, and provide the returned copy-ready
  update request in the user's language. Continue the user's original task.
- Treat only published stable Releases as available updates; ignore drafts and
  prereleases.
- Do not perform an update unless the user explicitly requests it. For a later
  update request, preserve Git history and uncommitted changes for a Git worktree;
  back up an ordinary installation before replacement.
- Continue normally for `disabled`, `skipped_checked_today`, `no_release`,
  `up_to_date`, or `check_failed`.
- Respect `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` as an explicit local opt-out.

After completing or skipping the release check, apply the mandatory workflow in this file before every UltraPlot implementation. The files under `references/` are optional supporting material: read only the reference relevant to a non-trivial decision, unfamiliar API, or unresolved implementation detail. The default WGS84 geospatial policy and layout rules in this file remain mandatory even when no reference file is opened.

## Scientific plotting gate (before writing code)

1. **Confirm the plotting environment.** Record the installed UltraPlot, matplotlib, and cartopy versions before using version-specific behavior. The validated baseline for this skill is UltraPlot 2.5.0 with matplotlib 3.10.6 and cartopy 0.25.0. Use public documented APIs and do not depend on private attributes.
2. **Define the scientific question.** State what comparison, relationship, pattern, or mechanism the figure is meant to examine.
3. **Define the intended message.** Write one sentence describing what the reader should be able to see or compare. Do not choose a plot type before this is clear.
4. **Define the output size and export resolution.** Honor a user-specified journal preset or exact total physical figure width. If neither is specified, use `journal="nat2"` (Nature two-column, 183 mm). When the selected size authority constrains only one figure dimension, let UltraPlot derive the other from the reference subplot and GridSpec geometry. Do not infer another journal format or approximate `nat2` with a hand-written inch or millimetre value. Unless the user or journal explicitly specifies another resolution, define `EXPORT_DPI = 1000` and pass `dpi=EXPORT_DPI` to every final `fig.save(...)` call. Use the same export DPI for every output format and figure type; do not introduce format-specific DPI branches. The default must always be greater than 600 dpi.
5. **Inspect the data.** Confirm variables, units, observation level, groups, missing values, and whether the data are raw or already processed. Do not invent or silently alter scientific data.
6. **Inspect geospatial metadata when applicable.** Before plotting spatial data, confirm the source CRS, coordinate units, bounds, affine transform, resolution, grid orientation, and NoData definition. Never infer WGS84 from coordinate appearance or missing CRS metadata.
7. **Prepare the default WGS84 display data.** Use EPSG:4326 (WGS84 longitude/latitude) as the default plotting CRS for geospatial figures. When the source CRS differs, create an in-memory or temporary display-only EPSG:4326 representation before plotting. Do not overwrite the source dataset, use the display representation for area, distance, zonal statistics, or trend calculations, or obtain degree axes by relabeling projected coordinates. Use another display projection only when the user or required figure specification explicitly requests it.
8. **Decide whether preprocessing is required.** Cleaning, filtering, joining, reshaping, aggregation, normalization, derived variables, or statistical summaries count as data processing.
9. **Separate processing from plotting.** When preprocessing is required, create a dedicated processing script and a separate plotting script. The plotting script should read the processed data and should not hide substantive cleaning or analysis steps.
10. **Define plotting-script granularity.** Give each scientifically distinct figure an independently runnable plotting entry script. A single parameterized entry script may generate a homogeneous figure series only when the layout, scientific meaning, and processing logic are the same and the figures differ only by inputs, regions, years, or labels. Put genuinely shared rendering utilities in a small helper module.
11. **Deliver reproducible artifacts.** When preprocessing is required, return both scripts, the processed data file, and the rendered figure files. When it is not required, return the plotting script and rendered figure files. Record important assumptions and transformations.

## Layout gate (before creating the figure)

1. **Identify the layout topology.** Decide which panels occupy ordinary cells, which panels genuinely span rows or columns, and whether any empty slots are required.
2. **Check layout-topology feasibility.** At the intended physical output width, evaluate the number of panels, row-column arrangement, expected axis aspects, spanning panels, outer guides, and final typography. Identify axes whose data aspect is fixed, including GeoAxes, image axes, and equal-aspect CartesianAxes. Confirm that the proposed topology can provide readable visible axes frames and support the intended comparisons. If it cannot, revise the topology, spans, ratios, guide placement, or output format before writing plotting code. Do not use spacing parameters to rescue an infeasible topology.
3. **Use regular grids for regular layouts.** Use `nrows` and `ncols` whenever every subplot occupies one ordinary grid cell.
4. **Use ratios for unequal regular panels.** Add `wratios` or `hratios` when regular columns or rows require unequal sizes. Ratios control geometry, not spacing.
5. **Reserve picture arrays for genuine complex layouts.** Use a picture array only for real spans, holes, or non-rectangular arrangements. Never repeat a subplot number merely to approximate a width or height ratio. For example, use `ncols=2, wratios=(2, 1)` instead of `[[1, 1, 2]]` for two unequal side-by-side panels.
6. **Handle mixed axes deliberately.** Start from `share="auto"` in UltraPlot 2.5. Use `share=False, span=False` when GeoAxes and CartesianAxes show unrelated variables or units. Do not use `share=True` to force incompatible geographic and Cartesian axes to share limits or ticks.
7. **Preserve map geometry.** Keep the geographic projection aspect by default. Do not use `aspect="auto"` simply to fill a GridSpec slot because it distorts the map. Let fixed data aspects participate in UltraPlot's automatic figure-size calculation. The first subplot is the default reference subplot; set `refnum` only when a different subplot should control the derived figure geometry. After rendering, verify the visible axes frames rather than assuming they fill their GridSpec slots.
8. **Render without manual spacing first.** Do not pass `left`, `right`, `top`, `bottom`, `wspace`, or `hspace` on the first render. Resolve final text coverage and visible labels before evaluating automatic layout.

### Layout geometry diagnosis

Before changing any spacing parameter, compare three geometries with the final renderer:

- The allocated GridSpec slot from `ax.get_subplotspec().get_position(fig)`.
- The visible axes frame from `ax.get_position()`.
- The decorated boundary from `ax.get_tightbbox(renderer)`.

Measure relevant dimensions and gaps in physical units. Classify apparent whitespace as a true gap between subplot slots, unused space inside a fixed-aspect slot, or clearance required by ticks, labels, titles, legends, and colorbars. `wspace` and `hspace` cannot remove unused space inside a fixed-aspect slot.

### Spacing escalation

Classify the defect before changing layout parameters:

- Infeasible topology or unreadable visible-frame size: revise the topology or output format before changing spacing.
- Unused space inside a fixed-aspect slot: revise the topology, ratios, or reference subplot; do not use `wspace`, `hspace`, `wpad`, or `hpad`.
- Misaligned visible frames in a mixed-axes row or column: revise structural geometry before adjusting decorated-content padding.
- Wrong panel proportions: revise `wratios`, `hratios`, or `refnum`.
- Overlap between labels, ticks, titles, and adjacent panels: first revise the subplot structure; if the structure is already correct, use the smallest necessary `wpad`, `hpad`, or `innerpad`.
- A required fixed distance between subplot frames: use `wspace` or `hspace`.
- Insufficient automatic clearance at the outside of the figure: adjust `outerpad`.
- An exact subplot-to-figure-edge distance: use `left`, `right`, `top`, or `bottom`.
- Spacing between an axes and an outer colorbar, legend, or panel: use `panelpad`.
- Spacing between figure-level row or column labels and a shared spanning axis label: use `leftlabelsharedpad`, `rightlabelsharedpad`, `toplabelsharedpad`, or `bottomlabelsharedpad`.

`left`, `right`, `top`, and `bottom` control outer margins only. They must never be used to repair overlap between neighboring panels. In particular, `left="3em"` can change the left outer margin but cannot prevent the y tick labels of panel b from overlapping the frame of panel a.

### UltraPlot 2.5 layout note

In UltraPlot 2.5.0, a repeated-ID picture layout such as `[[1, 1, 2]]` can underestimate decorated-content clearance on the first layout pass in mixed GeoAxes/Cartesian figures. If the intended structure is a regular unequal two-column layout, replace it with `ncols=2, wratios=(2, 1)`.

Do not use `group=False`, `equal=True`, `ultra_layout=False`, or repeated `fig.auto_layout()` calls as generic overlap repairs. A second explicit `auto_layout()` may be documented as a last-resort version workaround only when the layout genuinely requires a picture array and no correct structural alternative exists.

## The non-negotiables (check every figure against these)
1. **Perceptually uniform, colorblind-safe colormaps.** Never `jet`/`rainbow`. Use sequential maps such as `batlow`, `fire`, `dusk`, or `viridis` for magnitude; diverging maps such as `roma` or `vik` for signed data with a meaningful zero; and cyclic maps such as `romaO` or `vikO` for phase or angle.
2. **Honest encodings.** Don't truncate a bar/area baseline away from a meaningful zero. Center diverging maps on the true neutral value (use `values=`/`levels=` so the midpoint is real, not implied). Preserve spatial geometry using a CRS-aware GeoAxes. Use `aspect="equal"` for projected Cartesian coordinates, but do not treat equal longitude and latitude increments as equal ground distances.
3. **Default WGS84 geospatial display.** Render geospatial distribution maps with `proj="pcarree"` from display-only EPSG:4326 coordinates and use degree-formatted longitude and latitude axes unless the user explicitly requests another display projection. Preserve the original CRS and use the original or scientifically appropriate projected data for calculations.
4. **Default-first, scoped styling.** Treat the effective UltraPlot configuration after import as the styling baseline, subject to the typography precedence below. Override it only when required by the user, the scientific encoding, accessibility, or an explicit publication specification. Prefer `Axes.format()` or `Figure.format()` for figure-local changes and `uplt.rc.context()` for a bounded group of figures. Reserve session-global `uplt.rc` changes and persistent `ultraplotrc` changes for explicitly requested cross-figure themes. Treat rc aliases and meta-settings as coupled settings. Read `uplt.rc.changed` (a dictionary property) to audit values that differ from UltraPlot's built-in defaults; it does not audit figure-local visual effects, so verify those in the rendered output. For GeoAxes, make semantic choices such as grid visibility, label sides, locators, and formatters, but inherit the effective gridline and geographic-label appearance by default. Do not pass `gridcolor`, `gridalpha`, `gridlinewidth`, `gridlinestyle`, `labelcolor`, or `gridlabelcolor` unless required by the user, scientific encoding, accessibility, or an explicit publication specification. Do not hard-code UltraPlot's current visual defaults. The explicit `EXPORT_DPI = 1000` publication-output requirement is intentional and is not a visual-style override. Preserve text, tick, coordinate-label, axes, and guide colors and opacity by default. Turn gridlines off when they do not aid interpretation (`grid=False`). No chartjunk, no 3D for 2D data, and no redundant legends when a colorbar already encodes the variable.
5. **Do not add figure-level or subplot-level titles by default.** Do not create or retain a visible figure-level or subplot-level title unless the user directly instructs you to display or retain one. Only such a direct instruction authorizes a title; all other wording is non-authorizing. This prohibition covers `suptitle` and its `figtitle` alias, `title`, every documented positional subplot-title variant, and equivalent figure or subplot title setters. Without direct authorization, omit these APIs and remove pre-existing figure-level and subplot-level titles when revising a figure. This prohibition does not apply to axis labels (`xlabel`, `ylabel`), tick labels, geographic coordinate labels, legend titles or labels, colorbar labels or titles, annotations, panel identifiers (`abc`), or figure-edge structural labels. Preserve these when needed to identify variables, units, categories, encodings, or figure structure. Use `abc` only for panel identifiers and use `toplabels`, `bottomlabels`, `leftlabels`, and `rightlabels` only for genuine grid-edge structure. Do not use structural-label APIs to carry descriptive title text. Do not use `autoformat=False` to enforce the no-title rule; `autoformat` controls automatically inferred axis, legend, and colorbar labels, not figure-level or subplot-level titles.
6. **One consolidated `format()` per coherent group.** Use `ax.format(...)`, `axs.format(...)`, or `fig.format(...)` instead of scattered matplotlib setters. Mixed GeoAxes and CartesianAxes may require separate consolidated calls because they accept different formatting keywords. Apply `lonlabels` and `latlabels` only to GeoAxes.
7. **Structure-first automatic layout.** Follow the mandatory Layout gate. Use automatic layout, compatible axis sharing, spanning labels where scientifically appropriate, and outer colorbars or legends. Do not use `bbox_to_anchor`, `subplots_adjust()`, or `bbox_inches="tight"`.
8. **Exact physical sizing, vector output, and export resolution.** Use exactly one width authority: honor an explicitly requested `journal=` preset or total `figwidth`; otherwise use `journal="nat2"`, which resolves to 183 mm. When only one figure dimension is constrained, rely on UltraPlot's automatic size derivation. Do not approximate journal presets or combine `journal` with a competing `figwidth` or `refwidth`. Set `refaspect` only when the intended reference geometry differs from UltraPlot's default. Save vector output without post-render cropping so the requested physical width is preserved. Apply the single `EXPORT_DPI` selected in the Scientific plotting gate to every final save call. Use 1000 dpi by default and never silently reduce it to 600 dpi or less. Do not vary DPI according to the plot type or output extension.
9. **Render, diagnose, then override.** Inspect the automatic-layout render with effective typography and final labels. Distinguish panel geometry, frame spacing, decorated-content spacing, and outer margins before changing a parameter. Record every manual spacing override, the observed defect, and why structural correction plus automatic layout was insufficient. Also verify that insets do not overlap panel letters, titles, or annotations and are proportionate to the main axes.

## Typography before layout

Apply typography in this order: (1) explicit user instructions, (2) current journal or publication specifications, (3) active typography settings that differ from UltraPlot's built-in defaults, and (4) the skill default. Treat active typography entries in `uplt.rc.changed`, including settings loaded from `ultraplotrc`, as an existing font specification even when the prompt does not repeat them.

When none of the first three applies, use 9 pt sans-serif TeX Gyre Heros. UltraPlot 2.5.0 already provides this baseline: `font.name` is `sans-serif`, `font.sans-serif` begins with the bundled TeX Gyre Heros, and `font.size` is 9 pt. Do not add redundant rc overrides when the effective configuration already resolves to this baseline. If another UltraPlot version does not resolve to this baseline, apply the skill default with the narrowest appropriate scope before creating the figure.

After selecting the typography source, preserve its font-family order, sizes, weights, styles, colors, and opacity. Do not replace the primary font merely to impose a house style or obtain missing glyphs.

When the active font stack lacks required glyphs, register a font in a format supported by UltraPlot and extend the appropriate generic-family fallback list without reordering or replacing its existing primary entries. Select fallback fonts by writing system and output requirements; for Chinese text, use an available Song/Ming-style fallback when requested. Prefer `.ttf` or `.otf` files for publication output. Do not rely on `.ttc` collections, which UltraPlot intentionally ignores because they are unreliable for PDF export.

Resolve font availability and fallback order before creating the figure. Do not rebind individual `Text` artists after layout has measured them. Verify all required scripts, symbols, units, Unicode minus signs, and mathematical text in both vector and raster output.

## Minimal workflow

```python
import numpy as np
import ultraplot as uplt

EXPORT_DPI = 1000

fig, axs = uplt.subplots(ncols=2, journal="nat2")
axs[0].plot(x, y, lw=2, cycle="538", labels=["a", "b", "c"], legend="b")
m = axs[1].pcolormesh(field, cmap="batlow", levels=11, extend="both")
axs[1].colorbar(m, loc="r", label="value")
axs.format(
    abc="a.", abcloc="ul",
    xlabel="x (units)", ylabel="y (units)",
    grid=False,
)
fig.save("figure.pdf", dpi=EXPORT_DPI)
fig.save("figure.png", dpi=EXPORT_DPI)
```

For a regular unequal mixed geospatial layout, use the semantic grid directly:

```python
fig, axs = uplt.subplots(
    ncols=2,
    wratios=(2, 1),
    proj={1: "pcarree"},
    journal="nat2",
    share=False,
    span=False,
)
map_ax, chart_ax = axs
```

Select `refnum` explicitly only when the intended reference subplot is not the first subplot.

Steps every time:
0. **Plan the scientific message and data flow.** Apply the Scientific plotting gate in this file. Read a reference only when extra detail is needed. If preprocessing is required, write the processing script and save the processed data before writing the plotting script.
1. **Choose and preflight the layout structure.** Apply the Layout gate before creating the figure.
2. **Resolve typography and physical size.** Apply the typography precedence above, confirm the selected base size and resolved primary family before figure creation, register only the fallbacks required for missing glyph coverage, select exactly one figure-width authority, and let UltraPlot derive any unconstrained dimension.
3. **Pick the plot commands.** Use axes-level UltraPlot commands and feed pandas or xarray objects directly when appropriate.
4. **Choose color.** Match the colormap or cycle type to the data type.
5. **Annotate and format.** Unless directly requested, keep figure-level and subplot-level title-producing arguments and methods out of the plotting code. Preserve scientifically necessary axis labels, guide labels, annotations, panel identifiers, and structural labels. Interpret a `title` argument by the receiving API: legend and colorbar title aliases are guide labels, not figure-level or subplot-level titles. Use consolidated `format()` calls for coherent axes groups and outer guides where appropriate.
6. **Render and verify.** Save every final output with the same explicit `EXPORT_DPI`, using 1000 dpi by default. Inspect the PDF and PNG, verify the actual output resolution, and measure any suspected layout defect before adding a spacing override.

## Colormap & cycle quick reference

- **Sequential** (0→max magnitude): `batlow`, `fire`, `dusk`, `ice`, `boreal`, `marine`, `Blues`, mpl `viridis`/`magma`.
- **Diverging** (signed, meaningful zero): `Div`, `roma`, `vik`, `BuRd`,`RdBu`. Name reversal is flexible (`BuRd` == `RdBu_r`).
- **Cyclic** (phase/angle/longitude): `romaO`, `vikO`/`viko`, mpl `twilight`, or build one with `uplt.Colormap(h=(0,360), c=50, l=70, space='hcl', cyclic=True)`.
- **Categorical cycles** (distinct lines/bars): `538`, `ggplot`, `colorblind`, `qual1`, `Set3`, `bmh`. Prefer per-call `cycle=` for individual plots. Use `uplt.rc.context()` for a bounded figure series, and use session-global cycle changes only for an explicitly requested shared theme.
- Append `_r` to reverse, `_s` to shift any map/cycle. Names are case-insensitive.
- Explore interactively: `uplt.show_cmaps()`, `uplt.show_cycles()`, `uplt.show_channels('fire', 'dusk')` (check perceptual uniformity), `uplt.show_colors()`.

## Common mistakes to avoid

- Reaching for raw `matplotlib.pyplot` — stay in the axes-level `uplt` API.
- `jet`, `rainbow`, `hsv` for magnitude data (perceptually misleading).
- A cyclic map such as `vikO`/`viko` on ordinary sequential magnitude data.
- A diverging colormap on strictly-positive data, or a sequential one on signed data — the map type must match the data.
- Manual legend placement with `bbox_to_anchor` — use `loc='r'`/`'b'` for outer guides instead.
- Redundant encodings (colorbar *and* legend for the same variable).
- Inferring permission to add a figure-level or subplot-level title without a direct instruction to display one.
- Suppressing axis labels, legend titles, or colorbar labels merely because they are informally called titles or use a `title` keyword.
- Using structural-label APIs to carry descriptive title text.
- Treating `autoformat` as a figure-title or subplot-title mechanism; it controls inferred axis, legend, and colorbar labels.
- Using session-global rc changes for a figure-local requirement.
- Treating a GeoAxes grid-style keyword as line-only or changing it by habit; preserve the effective defaults and verify gridlines and geographic labels separately after any justified override.
- Replacing the primary font family to solve missing-glyph coverage instead of extending the active fallback chain.
- Applying a stylesheet without auditing its typography, axes, tick, grid, and guide changes.
- Using a repeated-ID picture array as a substitute for `wratios` or `hratios`.
- Using `left`, `right`, `top`, or `bottom` to repair overlap between panels.
- Treating `wratios` or `hratios` as spacing rather than panel geometry.
- Using `wspace` before determining whether the defect is decorated-content overlap.
- Using spacing parameters to repair an infeasible panel topology.
- Treating unused space inside a fixed-aspect slot as `wspace` or `hspace`.
- Evaluating alignment from GridSpec slots without inspecting visible axes frames.
- Increasing one canvas dimension when the relevant fixed-aspect panels are constrained by the other dimension.
- Sizing an outer guide from slots that are much larger than the associated visible axes frames.
- Using `aspect="auto"` to align a map without accepting geographic distortion.
- Using `group=False`, `equal=True`, or `ultra_layout=False` as generic overlap-repair switches.
- Calling a second `fig.auto_layout()` before testing the correct regular-grid structure.
- Registering or rebinding fonts after automatic layout has measured text.
- Fighting axis sharing: if shared limits/ticks are wrong for the data, pass `share=False`/`span=False` rather than overriding subplot-by-subplot.
- Approximating `journal="nat2"` with values such as `180mm` or `7.15in`; UltraPlot defines `nat2` as exactly 183 mm.
- Combining `journal` with a competing `figwidth` or `refwidth`.
- Using `bbox_inches="tight"` when exact journal dimensions must be preserved; it replaces the nominal canvas with the artists' tight bounding box.
- Using different DPI values for different figure types or output extensions.
- Explicitly overriding UltraPlot's 1000 dpi default with 300 dpi or 600 dpi without a direct user or journal requirement.
- Assuming the intended DPI was used without checking the exported file.
- Setting figure size in pixels after rendering, or assuming code-level sizing is correct without checking the saved PDF media box.
- Assuming data are WGS84 without inspecting their CRS metadata.
- Passing projected coordinates to a GeoAxes that expects longitude and latitude.
- Relabeling projected x/y coordinates with degree symbols without transforming them.
- Overwriting source data with a display-only EPSG:4326 representation.
- Using display-transformed data as input for statistics or spatial analysis.
- Combining scientifically different figures in one monolithic plotting script.

## Verifying

Do not claim a figure "looks good" without rendering it. Save both the final vector output and a PNG preview, then inspect them with the effective typography and final labels. Confirm that labels, panel letters, annotations, insets, and outer guides are legible and do not overlap or clip. If the user did not directly request a figure-level or subplot-level title, treat any such title in the plotting code or rendered output as a blocking failure. Remove its producing argument, method, or pre-existing artist, render again, and reinspect both PDF and PNG. Audit calls by their receiving API; do not classify legend titles, colorbar labels, axis labels, panel identifiers, or grid-edge structural labels as figure-level or subplot-level titles. Record the sizing authority and every manual spacing override in the verification notes.

Evaluate GridSpec slots, visible axes frames, and decorated content. A positive frame gap does not prove that tick labels or titles are clear of a neighboring panel, and a positive slot gap does not reveal unused space inside a fixed-aspect slot. Use the final renderer for all measurements. Confirm that:

- every main axes tight bounding box remains inside the figure canvas;
- all style overrides have the narrowest necessary scope;
- every entry in `uplt.rc.changed` is explained; the dictionary need not be empty when an intended user or project configuration defines the effective baseline;
- text, tick, coordinate-label, axes, and guide appearance matches the effective baseline except where an override was explicitly justified;
- GeoAxes gridline strokes and longitude and latitude labels have been checked separately against the effective baseline after any justified style override;
- temporary rc contexts do not leak into subsequent figures;
- no figure-level or subplot-level title-producing call or visible title is present unless directly requested;
- when directly requested, only the requested title scope is present;
- required axis labels, legend titles, colorbar labels, tick labels, and geographic coordinate labels remain visible and correct;
- panel identifiers and grid-edge labels have genuine structural roles and do not substitute for descriptive titles;
- required fallback glyphs render correctly in both PDF and PNG output;
- adjacent decorated-content bounding boxes do not overlap;
- panel letters are positioned consistently relative to the visible axes frames;
- the physical width and height of every visible main axes frame are recorded and readable at the intended output size;
- GridSpec-slot and visible-frame dimensions are compared for fixed-aspect axes;
- apparent frame-to-frame gaps are measured rather than inferred from slot spacing;
- visible axes frames align as intended in mixed GeoAxes/Cartesian layouts;
- outer guides are proportionate to the visible axes they describe;
- no layout parameter is being used for a different semantic purpose;
- the saved PDF retains the requested physical width;
- every final `fig.save(...)` call receives the same explicit `EXPORT_DPI`;
- the default `EXPORT_DPI` is 1000 and therefore greater than 600;
- no output silently falls back to 600 dpi or less;
- raster pixel dimensions agree with the physical figure size and export DPI;
- any explicit deviation from 1000 dpi is supported by a direct user or journal requirement;
- geospatial figures use EPSG:4326/WGS84 with degree-formatted longitude and latitude axes unless another projection was explicitly requested;
- the displayed extent matches the study area, north-south orientation is correct, boundaries align with the raster, and NoData regions are rendered as intended.

Do not issue a publication-quality pass based only on canvas containment, non-overlap, and successful file export.

For `journal="nat2"`, verify that the saved PDF media box is 183 mm wide (about 7.2047 in or 518.74 pt; tolerance 0.2 mm). Do not rely only on the size requested in code.

A quick smoke test:

```python
import ultraplot as uplt

EXPORT_DPI = 1000

fig, ax = uplt.subplots(journal="nat2")
ax.plot([0, 1, 2], [0, 1, 4])
fig.save("figure_check.pdf", dpi=EXPORT_DPI)
fig.save("figure_check.png", dpi=EXPORT_DPI)
```

## Optional reference files (load only when needed)

- Read `references/scientific-principles.md` only when the scientific question, preprocessing boundary, or deliverable contract needs more detail.
- Read `references/geospatial.md` only for detailed CRS, raster, vector, or GeoAxes implementation guidance.
- Read `references/api.md` only for unfamiliar commands or parameter details.
- Read `references/color.md` only for advanced colormap construction or perceptual diagnostics.
- Read `references/recipes.md` only when a matching starting pattern is useful.
