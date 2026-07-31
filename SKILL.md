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
4. **Define panel identifiers and text priority.** Classify every Axes as an independent main Axes or an auxiliary Axes. For two or more independent main Axes, require exactly one panel identifier per main Axes and use the skill default `abc="a.", abcloc="ul"` unless the user or target journal explicitly requests another style, location, or omission. Treat the rendered upper-left identifier region as reserved before placing ordinary annotations. Record every authorized deviation and its reason.
5. **Define the output size and export resolution.** Honor a user-specified journal preset or exact total physical figure width. If neither is specified, use `journal="nat2"` (Nature two-column, 183 mm). When the selected size authority constrains only one figure dimension, let UltraPlot derive the other from the reference subplot and GridSpec geometry. Do not infer another journal format or approximate `nat2` with a hand-written inch or millimetre value. Unless the user or journal explicitly specifies another resolution, define `EXPORT_DPI = 1000` and pass `dpi=EXPORT_DPI` to every final `fig.save(...)` call. Use the same export DPI for every output format and figure type; do not introduce format-specific DPI branches. The default must always be greater than 600 dpi.
6. **Inspect the data.** Confirm variables, units, observation level, groups, missing values, and whether the data are raw or already processed. Do not invent or silently alter scientific data.
7. **Inspect geospatial metadata when applicable.** Before plotting spatial data, confirm the source CRS, coordinate units, bounds, affine transform, resolution, grid orientation, and NoData definition. Never infer WGS84 from coordinate appearance or missing CRS metadata.
8. **Prepare the default WGS84 display data.** Use EPSG:4326 (WGS84 longitude/latitude) as the default plotting CRS for geospatial figures. When the source CRS differs, create an in-memory or temporary display-only EPSG:4326 representation before plotting. Do not overwrite the source dataset, use the display representation for area, distance, zonal statistics, or trend calculations, or obtain degree axes by relabeling projected coordinates. Use another display projection only when the user or required figure specification explicitly requests it.
9. **Decide whether preprocessing is required.** Cleaning, filtering, joining, reshaping, aggregation, normalization, derived variables, or statistical summaries count as data processing.
10. **Separate processing from plotting.** When preprocessing is required, create a dedicated processing script and a separate plotting script. The plotting script should read the processed data and should not hide substantive cleaning or analysis steps.
11. **Define plotting-script granularity.** Give each scientifically distinct figure an independently runnable plotting entry script. A single parameterized entry script may generate a homogeneous figure series only when the layout, scientific meaning, and processing logic are the same and the figures differ only by inputs, regions, years, or labels. Keep rendering code in the entry script by default. Add a helper module only when the delivered workflow imports it and it materially reduces necessary duplication.
12. **Apply the formal-deliverables policy.** Follow the mandatory allowlist below after preprocessing, rendering, and verification.

## Formal deliverables

Treat the formal deliverable set as a strict allowlist, whether or not it has a dedicated output directory. Unless the user or target journal explicitly requires otherwise, deliver only:

- the final vector and final PNG figure files;
- independently runnable plotting entry scripts and any local code or assets directly imported or read by the delivered scripts;
- when substantive preprocessing is required, the preprocessing scripts and only the final processed datasets directly read by the plotting scripts.

Treat a local file as a direct reproduction dependency only when removing it would prevent the delivered workflow from regenerating the final figure. Do not copy user-provided raw inputs or installed environment dependencies merely to make the output directory self-contained.

Do not deliver files used only for debugging, checking, experimentation, or explanation. This includes draft, test, check, and smoke-test renders; screenshots; diagnostic overlays or tables; logs; standalone verification notes; reports; manifests; README or instruction files; environment manifests; lock files; caches; backups; temporary reprojections; intermediate processing files; duplicate data representations; and unrequested figure formats.

Throughout this skill, "record" means encode reproduction-critical information in concise code comments, constants, or metadata embedded in an already required processed dataset, and summarize material assumptions or deviations in the final response. Do not create a separate notes, report, or manifest file unless the user explicitly requests it.

Prefer re-rendering corrected figures to the same final paths. If a separate diagnostic artifact is unavoidable, create it outside the formal deliverable set in a task-specific temporary location and remove only artifacts created by the current task after verification. Never remove pre-existing user files.

Before handoff, enumerate the formal deliverable set and confirm that every file is either a final figure or a direct reproduction dependency.

## Layout gate (before creating the figure)

Read `references/layout.md` before implementing a picture array, a spanning
subplot, a layout that mixes fixed- and auto-aspect axes, or a figure whose
width or height is intentionally left for UltraPlot to derive. Also read it
whenever the first render has unexplained whitespace, misalignment, clipping,
or overlap, including any panel-identifier and annotation conflict.

1. **Identify the layout topology.** Decide which panels occupy ordinary cells, which panels genuinely span rows or columns, and whether any empty slots are required.
2. **Plan and confirm subplot numbering.** Plan the expected identifier mapping from the layout, then confirm it against each main `Axes.number` after creation. Regular `nrows` and `ncols` layouts are row-major unless `order="F"` is used; picture-array integers determine subplot numbers. Explicit identifier sequences are assigned one by one to the Axes receiving `format()`. Do not infer identifier order from plotting-loop order alone.
3. **Reserve the inner upper-left identifier region.** Reserve the rendered `abc` bounding box plus clearance inside every main Axes. Do not place ordinary statistics, equations, sample sizes, callouts, legends, or insets in this region. For homogeneous small multiples, select one consistent non-upper-left annotation location across the figure whenever feasible.
4. **Check layout-topology feasibility.** At the intended physical output width, evaluate the number of panels, row-column arrangement, expected axis aspects, spanning panels, outer guides, and final typography. Identify axes whose data aspect is fixed, including GeoAxes, image axes, and equal-aspect CartesianAxes. Confirm that the proposed topology can provide readable visible axes frames and support the intended comparisons. If it cannot, revise the topology, spans, ratios, guide placement, or output format before writing plotting code. Do not use spacing parameters to rescue an infeasible topology.
5. **Use regular grids for regular layouts.** Use `nrows` and `ncols` whenever every subplot occupies one ordinary grid cell.
6. **Use ratios for unequal regular panels.** Add `wratios` or `hratios` when regular columns or rows require unequal sizes. Ratios control geometry, not spacing.
7. **Reserve picture arrays for genuine complex layouts.** Use a picture array only for real spans, holes, or non-rectangular arrangements. Never repeat a subplot number merely to approximate a width or height ratio. For example, use `ncols=2, wratios=(2, 1)` instead of `[[1, 1, 2]]` for two unequal side-by-side panels.
8. **Handle mixed axes deliberately.** Start from `share="auto"` in UltraPlot 2.5. Use `share=False, span=False` when GeoAxes and CartesianAxes show unrelated variables or units. Do not use `share=True` to force incompatible geographic and Cartesian axes to share limits or ticks.
9. **Select the sizing reference explicitly.** For every spanning or mixed-aspect layout with an unconstrained figure dimension, identify which subplot should govern that dimension. Treat `refaspect` as the width-to-height ratio of the subplot selected by `refnum`; the reference subplot may itself span cells. It is not the aspect of the complete figure or of an adjacent row or column composition. The first subplot is only the default, not a recommendation. When the intended reference subplot already has a fixed data aspect, normally omit `refaspect` and let UltraPlot use that aspect. Do not make `refnum=1` a universal rule.
10. **Stay within the supported layout model.** Use one UltraPlot `GridSpec` per figure. Do not propose `GridSpecFromSubplotSpec`, a nested `GridSpec`, or `SubFigure` as a layout repair. Use a valid picture array, `wratios`, `hratios`, panels or insets where semantically appropriate, or revise the topology.
11. **Preserve map geometry.** Keep the geographic projection aspect by default. Do not use `aspect="auto"` simply to fill a GridSpec slot because it distorts the map. Let fixed data aspects participate in UltraPlot's automatic figure-size calculation. After rendering, verify the visible axes frames rather than assuming they fill their GridSpec slots.
12. **Render without manual spacing first.** Do not pass `left`, `right`, `top`, `bottom`, `wspace`, or `hspace` on the first render. Resolve final text coverage and visible labels before evaluating automatic layout. Tight layout does not resolve collisions between inner panel identifiers and ordinary annotations.

### Layout geometry diagnosis

Before changing any spacing parameter, compare three geometries with the final renderer:

- The allocated GridSpec slot from `ax.get_subplotspec().get_position(fig)`.
- The visible axes frame from `ax.get_position()`.
- The decorated boundary from `ax.get_tightbbox(renderer)`.

Measure relevant dimensions and gaps in physical units. Classify apparent whitespace as a true gap between subplot slots, unused space inside a fixed-aspect slot, or clearance required by ticks, labels, titles, legends, and colorbars. `wspace` and `hspace` cannot remove unused space inside a fixed-aspect slot.

For every dominant fixed-aspect main axis, record directional slot utilization
for width and height. Measure outer guide space separately from main-axes slot
waste. Do not pass a figure when unexplained slot-internal whitespace forms a
composition-wide blank band or materially reduces the intended visible panel.
Numeric thresholds may trigger mandatory review, but they are skill heuristics,
not UltraPlot API guarantees or universal aesthetic pass criteria.

### Spacing escalation

Classify the defect before changing layout parameters. Revise topology, output
format, ratios, or the reference subplot for infeasible geometry, unreadable
frames, wrong proportions, or fixed-aspect slot waste. Use `wspace` or `hspace`
only for a required fixed distance between subplot frames, and use tight-layout
padding only for decorated-content clearance after the structure is correct.
Use outer-margin parameters only for figure-edge distances. For the complete
parameter decision table and the UltraPlot 2.5 picture-layout note, follow
`references/layout.md`.

## The non-negotiables (check every figure against these)
1. **Perceptually uniform, colorblind-safe colormaps.** Never `jet`/`rainbow`. Use sequential maps such as `batlow`, `fire`, `dusk`, or `viridis` for magnitude; diverging maps such as `roma` or `vik` for signed data with a meaningful zero; and cyclic maps such as `romaO` or `vikO` for phase or angle.
2. **Honest encodings.** Don't truncate a bar/area baseline away from a meaningful zero. Center diverging maps on the true neutral value (use `values=`/`levels=` so the midpoint is real, not implied). Preserve spatial geometry using a CRS-aware GeoAxes. Use `aspect="equal"` for projected Cartesian coordinates, but do not treat equal longitude and latitude increments as equal ground distances.
3. **Default WGS84 geospatial display.** Render geospatial distribution maps with `proj="pcarree"` from display-only EPSG:4326 coordinates and use degree-formatted longitude and latitude axes unless the user explicitly requests another display projection. Preserve the original CRS and use the original or scientifically appropriate projected data for calculations.
4. **Default-first, scoped styling.** Treat the effective UltraPlot configuration after import as the styling baseline. Override it only when required by the user, the scientific encoding, accessibility, or an explicit publication specification. Prefer `Axes.format()` or `Figure.format()` for figure-local changes and `uplt.rc.context()` for a bounded group of figures. Reserve session-global `uplt.rc` changes and persistent `ultraplotrc` changes for explicitly requested cross-figure themes. Treat rc aliases and meta-settings as coupled settings. Read `uplt.rc.changed` (a dictionary property) to audit values that differ from UltraPlot's built-in defaults; it does not audit figure-local visual effects, so verify those in the rendered output. For GeoAxes, make semantic choices such as grid visibility, label sides, locators, and formatters, but inherit the effective gridline and geographic-label appearance by default. Do not pass `gridcolor`, `gridalpha`, `gridlinewidth`, `gridlinestyle`, `labelcolor`, or `gridlabelcolor` unless required by the user, scientific encoding, accessibility, or an explicit publication specification. Do not hard-code UltraPlot's current visual defaults. The explicit `EXPORT_DPI = 1000` publication-output requirement and the multi-panel `abc="a.", abcloc="ul"` policy below are intentional semantic exceptions. Keep both figure-local; do not implement the panel-identifier policy with session-global or persistent rc changes. Preserve text, tick, coordinate-label, axes, and guide colors and opacity by default. Turn gridlines off when they do not aid interpretation (`grid=False`). No chartjunk, no 3D for 2D data, and no redundant legends when a colorbar already encodes the variable.
5. **Do not add figure-level or subplot-level titles by default.** Do not create or retain a visible figure-level or subplot-level title unless the user directly instructs you to display or retain one. Only such a direct instruction authorizes a title; all other wording is non-authorizing. This prohibition covers `suptitle` and its `figtitle` alias, `title`, every documented positional subplot-title variant, and equivalent figure or subplot title setters. Without direct authorization, omit these APIs and remove pre-existing figure-level and subplot-level titles when revising a figure. This prohibition does not apply to axis labels (`xlabel`, `ylabel`), tick labels, geographic coordinate labels, legend titles or labels, colorbar labels or titles, annotations, panel identifiers (`abc`), or figure-edge structural labels. Preserve these when needed to identify variables, units, categories, encodings, or figure structure. Use `abc` only for panel identifiers and use `toplabels`, `bottomlabels`, `leftlabels`, and `rightlabels` only for genuine grid-edge structure. Do not use structural-label APIs to carry descriptive title text. Do not use `autoformat=False` to enforce the no-title rule; `autoformat` controls automatically inferred axis, legend, and colorbar labels, not figure-level or subplot-level titles.
6. **Panel identifiers own the inner upper-left region.** For two or more independent main Axes, enable identifiers with `axs.format(abc="a.", abcloc="ul")`. Panel identifiers have higher text-layout priority than ordinary annotations. When a collision occurs, preserve the identifier and its upper-left location; move, reflow, shorten without losing scientific meaning, or relocate the lower-priority annotation first. Do not change `abcloc`, apply `abcpad`, disable `abc`, or hide the collision with z-order as a repair for an ordinary annotation. Relocate or omit an identifier only under a direct user or journal instruction and record the reason. Grid-edge labels do not replace panel identifiers.
7. **One consolidated `format()` per coherent group.** Use `ax.format(...)`, `axs.format(...)`, or `fig.format(...)` instead of scattered matplotlib setters. Mixed GeoAxes and CartesianAxes may require separate consolidated calls because they accept different formatting keywords. Apply `lonlabels` and `latlabels` only to GeoAxes.
8. **Structure-first automatic layout.** Follow the mandatory Layout gate. Use automatic layout, compatible axis sharing, spanning labels where scientifically appropriate, and outer colorbars or legends. Do not use `bbox_to_anchor`, `subplots_adjust()`, or `bbox_inches="tight"`.
9. **Exact physical sizing, vector output, and export resolution.** Use exactly one width authority: honor an explicitly requested `journal=` preset or total `figwidth`; otherwise use `journal="nat2"`, which resolves to 183 mm. When only one figure dimension is constrained, rely on UltraPlot's automatic size derivation. Do not approximate journal presets or combine `journal` with a competing `figwidth` or `refwidth`. Set `refaspect` only when the intended reference geometry differs from UltraPlot's default. Save vector output without post-render cropping so the requested physical width is preserved. Apply the single `EXPORT_DPI` selected in the Scientific plotting gate to every final save call. Use 1000 dpi by default and never silently reduce it to 600 dpi or less. Do not vary DPI according to the plot type or output extension.
10. **Render, diagnose, then override.** Inspect the automatic-layout render with effective typography and final labels. Distinguish panel geometry, frame spacing, decorated-content spacing, and outer margins before changing a parameter. Record every manual spacing override, the observed defect, and why structural correction plus automatic layout was insufficient. Also verify that insets do not overlap panel letters, titles, or annotations and are proportionate to the main axes. When a panel identifier conflicts with an ordinary annotation, keep the identifier in the upper-left and move the annotation first.

## Typography before layout

Preserve the effective UltraPlot font configuration by default. Do not replace `font.name`, `font.family`, the primary family order, font sizes, weights, styles, colors, or opacity merely to impose a house style or obtain missing glyphs.

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

The explicit `abcloc="ul"` is a skill policy, not the UltraPlot built-in
default. It reserves the inner upper-left region for panel identification.
Create ordinary annotations only after establishing this region and place them
outside it.

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

Steps every time:
0. **Plan the scientific message and data flow.** Apply the Scientific plotting gate in this file. Read a reference only when extra detail is needed. If preprocessing is required, write the processing script and save the processed data before writing the plotting script.
1. **Choose and preflight the layout structure.** Apply the Layout gate before creating the figure.
2. **Resolve text coverage and physical size.** Preserve UltraPlot's effective typography, register only the fallbacks required for missing glyph coverage before figure creation, select exactly one figure-width authority, and let UltraPlot derive any unconstrained dimension.
3. **Pick the plot commands.** Use axes-level UltraPlot commands and feed pandas or xarray objects directly when appropriate.
4. **Choose color.** Match the colormap or cycle type to the data type.
5. **Format identifiers, then add ordinary annotations.** Unless directly requested, keep figure-level and subplot-level title-producing arguments and methods out of the plotting code. Apply the consolidated main-Axes `format()` call, including `abc="a.", abcloc="ul"` when required, before placing ordinary annotations. Preserve scientifically necessary axis labels, guide labels, annotations, panel identifiers, and structural labels. Keep handles to statistics blocks, equations, sample sizes, and callouts. Start with a consistent non-upper-left location for homogeneous small multiples. If no fixed location is satisfactory, move only the lower-priority annotation with an explicit identifier obstacle. Interpret a `title` argument by the receiving API: legend and colorbar title aliases are guide labels, not figure-level or subplot-level titles.
6. **Render and verify.** Save every final output with the same explicit `EXPORT_DPI`, using 1000 dpi by default. Inspect the PDF and PNG, verify the actual output resolution, and measure any suspected layout defect before adding a spacing override. Verify expected and detected identifier counts, exact numbering, inner upper-left placement, canvas containment, legibility, and collision-free reserved regions. Treat a missing, relocated, duplicated, misordered, clipped, or annotation-obscured required identifier as a blocking failure. Re-render corrections to the same final paths whenever possible. Do not create separate draft, check, or test copies in the formal deliverable set.

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
- Treating UltraPlot's built-in `abc.loc="left"` as this skill's multi-panel policy; this skill deliberately uses figure-local `abcloc="ul"`.
- Placing ordinary `ax.text()` annotations in the upper-left region reserved for the panel identifier.
- Moving `abc`, changing `abcpad`, or disabling identifiers to accommodate a lower-priority annotation.
- Assuming `avoid_overlap=True` automatically avoids panel identifiers.
- Calling `auto_align_text()` without passing only the lower-priority annotation objects and without explicitly listing the identifier in `avoid=`.
- Treating `abcborder`, `abcbbox`, z-order, or tight layout as substitutes for geometric non-overlap.
- Treating a GeoAxes grid-style keyword as line-only or changing it by habit; preserve the effective defaults and verify gridlines and geographic labels separately after any justified override.
- Replacing the primary font family to solve missing-glyph coverage instead of extending the active fallback chain.
- Applying a stylesheet without auditing its typography, axes, tick, grid, and guide changes.
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
- Treating verification, diagnostic, report, or manifest artifacts as formal deliverables, or leaving task-created temporary files beside final artifacts.

## Verifying

Do not claim a figure "looks good" without rendering it. Save both the final vector output and the final PNG output, then inspect them with the effective typography and final labels. Confirm that labels, panel letters, annotations, insets, and outer guides are legible and do not overlap or clip. If the user did not directly request a figure-level or subplot-level title, treat any such title in the plotting code or rendered output as a blocking failure. Remove its producing argument, method, or pre-existing artist, render again, and reinspect both PDF and PNG. Audit calls by their receiving API; do not classify legend titles, colorbar labels, axis labels, panel identifiers, or grid-edge structural labels as figure-level or subplot-level titles. Encode reproduction-critical sizing and spacing decisions in the necessary plotting code and summarize material deviations in the final response. Do not create a standalone verification-notes artifact unless explicitly requested.

For figures requiring panel identifiers, count only independent main Axes and
exclude colorbars, legend-only Axes, helper Axes, and non-independent insets.
Use the documented `abc` rules and confirmed `Axes.number` values to derive the
expected labels. Treat every unrecorded relocation or omission as a blocking
failure.

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
- every required main Axes contains exactly one expected identifier and the expected and detected identifier counts agree;
- template identifiers follow `Axes.number`, explicit sequences follow the receiving Axes one by one, and identifiers beyond 26 follow UltraPlot's documented sequence;
- every required identifier is rendered inside the upper-left region of its visible axes frame and remains inside the figure canvas;
- each identifier bounding box plus clearance avoids ordinary annotations, insets, legends, and other lower-priority artists;
- every identifier collision repair preserved the identifier and moved or reflowed the lower-priority artist;
- every authorized identifier relocation or omission records the direct user or journal instruction;
- required fallback glyphs render correctly in both PDF and PNG output;
- adjacent decorated-content bounding boxes do not overlap;
- panel letters are positioned consistently in the upper-left relative to the visible axes frames;
- the physical width and height of every visible main axes frame are recorded and readable at the intended output size;
- GridSpec-slot and visible-frame dimensions are compared for fixed-aspect axes;
- directional slot utilization is recorded for every dominant fixed-aspect main axis;
- every material slot-to-frame discrepancy is structurally corrected or explicitly justified by the declared layout intent;
- apparent frame-to-frame gaps are measured rather than inferred from slot spacing;
- visible axes frames align as intended in mixed GeoAxes/Cartesian layouts;
- outer guides are measured and classified separately from fixed-aspect main-axes slot waste;
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
- the formal deliverable set contains only allowlisted files;
- every delivered helper, asset, and processed dataset is a direct reproduction dependency;
- no task-created diagnostic, temporary, cache, backup, report, or check file remains in the formal deliverable set.

Do not issue a publication-quality pass based only on canvas containment,
non-overlap, and successful file export. Unexplained fixed-aspect slot waste that
creates a composition-wide blank band or materially shrinks a dominant panel is
a blocking layout failure.

For `journal="nat2"`, verify that the saved PDF media box is 183 mm wide (about 7.2047 in or 518.74 pt; tolerance 0.2 mm). Do not rely only on the size requested in code.

## Optional reference files (load only when needed)

- Read `references/scientific-principles.md` only when the scientific question, preprocessing boundary, or deliverable contract needs more detail.
- Read `references/layout.md` for every picture array, spanning subplot, mixed fixed/auto-aspect layout, unconstrained figure dimension, unexplained whitespace, misalignment, clipping, or panel-identifier and annotation conflict.
- Read `references/geospatial.md` only for detailed CRS, raster, vector, or GeoAxes implementation guidance.
- Read `references/api.md` for unfamiliar commands, parameter details, or panel-identifier and annotation-priority semantics.
- Read `references/color.md` only for advanced colormap construction or perceptual diagnostics.
- Read `references/recipes.md` only when a matching starting pattern is useful.
