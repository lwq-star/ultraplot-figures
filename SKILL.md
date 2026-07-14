---
name: ultraplot-figures
description: Use when creating, revising, or validating reproducible static scientific figures with UltraPlot. Also use when selecting a defensible figure design from data, writing a standalone Python plotting script, or checking a finished scientific figure for publication quality.
---

# UltraPlot Figures

Create reproducible static scientific figures and standalone Python plotting scripts.
Treat the plotting script and input data as the editable source of truth; treat
PDF/SVG/TIFF/PNG as outputs. Load only the references needed for the current task.

## Release update checks

Before the normal workflow, resolve `scripts/update_skill.py` relative to this
`SKILL.md`, then run the non-blocking release check unless the user has prohibited
network access:

```bash
python "<skill-directory>/scripts/update_skill.py" --auto
```

- Check at most once per local calendar day. Never download, install, or replace skill
  files as part of this check.
- For `update_available`, tell the user the current and latest versions, recommend
  updating, link the Release, and provide the returned copy-ready update request in
  the user's language. Do not perform the update unless the user explicitly asks.
- Treat only published stable Releases as available updates; ignore drafts and
  prereleases. Keep this implementation detail out of routine user notifications.
- If the user later asks to update, inspect the installation type internally. Preserve
  Git history and uncommitted changes for a Git worktree; back up an ordinary
  installation before replacement. Do not put these execution details in the
  copy-ready user request.
- Continue normally for `disabled`, `skipped_checked_today`, `no_release`,
  `up_to_date`, or `check_failed`.
- Respect `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` as an explicit opt-out.

## Decision priority

Apply requirements in this order:

1. **Task contract.** Preserve requested records, panels, mappings, deliverables, and
   explicit size, format, font, and target requirements. Report conflicts between an
   explicit setting and a named venue before choosing one.
2. **Current target instructions.** Use the journal or publisher's official guidance
   for physical size, format, raster DPI, color mode, fonts, transparency, compression,
   and file limits. Record the source URL and access date; mark anything not verified.
3. **Verified UltraPlot mechanisms.** Prefer journal presets, automatic layout,
   physical units, guide APIs, and behavior confirmed in the current runtime.
4. **Missing-setting fallback.** Resolve target settings independently. Preserve every
   explicit format, size, font, and venue requirement; fill only missing settings. When
   venue and physical width are unknown, use the current `nat2` width (`183mm`) as a
   stated size fallback with automatic height. When formats are also unknown, use PDF
   plus a 600 dpi opaque RGB lossless-LZW TIFF. These are Skill fallbacks, not universal
   journal rules.

## Input modes

- **Data or plotting source available:** run the full planning, generation, semantic,
  render, artifact, and visual workflow that the available inputs support.
- **Exported figure only:** inspect saved-file properties and visible defects. Do not
  claim checks that require source data, analysis steps, plotting code, or live artists.
  Report those unavailable checks explicitly.

## Task contract

Before coding, define one compact `EXPECTED_CONTRACT` containing:

- figure purpose and the judgment the reader should be able to make;
- `contract_version=2`, atomic requested judgments, and verbatim request spans;
- target records and filters;
- complete panel roles;
- channel-to-variable mappings, including units, statistics, and uncertainty where relevant;
- an evidence map from every requested judgment to panels and active channels;
- persistent deliverable roles and target settings with a source for every setting.

Explicit requirements are binding. Panel scope is closed only when the user explicitly
specifies a chart type, panel list, or single-panel constraint. A request that names
several reader judgments or scientific aspects but leaves layout open requires the
minimum evidence needed for every judgment. Area or color can show where high and low
values occur, but does not by itself establish a marginal distribution, concentration,
range, or group composition. State the reason for every supporting panel or for a
request-specific decision to use lower-precision evidence alone.

Keep the verbatim `REQUEST_TEXT` in the temporary QA harness, not in the delivered
plotting script. The plotting module may expose the normalized `EXPECTED_CONTRACT` and
live evidence for the harness to import. Reuse that single contract; do not reconstruct
a second expected contract or populate actual evidence by copying expected values.

## Core workflow

1. Parse the request into the task contract and applicable target policy.
2. Inspect data structure, target classes, units, ranges, missingness, and domain risks.
3. Build an evidence-coverage table: requested judgment -> reader question -> strongest
   evidence -> panel -> visual channel -> interpretation limit.
4. If the figure goal is unclear, recommend 1-3 defensible low-inference options and
   explain what each can show. Proceed directly when the request is already specific.
5. Split heavy cleaning, merging, modeling, reprojection, or QC into preprocessing.
6. Run the capability check only after an environment/helper change or before relying
   on version-sensitive behavior:

   ```bash
   python scripts/ultraplot_compat.py --strict
   ```

7. Build the minimal complete figure with every requested artist and guide. Keep the
   delivered plotting script runnable without the installed Skill.
8. **Draft stage:** run `audit_draft_figure(...)`, save a temporary 150-200 dpi preview
   through `qa_workspace()`, and fix semantic/render defects before production export.
9. **Final stage:** save only the resolved formats, pass the expected post-draw width,
   then run `audit_submission_figure(...)` on the real files.
10. Inspect the final artifact at its final physical size. Repeat full-resolution export
   only when an artifact or visual hard gate fails.
11. Deliver persistent outputs and a concise evidence-based summary.

Use `scripts/figure_qa.py` as the stable QA facade. Run `figure_qa.py --example` for
the canonical draft/final call. Run `--self-test` only after a QA-helper or environment
change, not for every ordinary figure.

## Mandatory QA

Every generated figure receives the checks supported by its inputs:

1. **Task-semantic QA:** verbatim request spans, reader judgments, evidence coverage,
   filters, counts, panels, mappings, units, guides, deliverables, and setting sources
   match the contract and live evidence.
2. **Render QA:** post-draw physical size, legend geometry, clipping, containment,
   semantic size mapping, and shared color scales are correct.
3. **Artifact QA:** saved format, page/image size, effective DPI, exposed font
   resources, transparency, color mode, compression, and target policy pass.
4. **Final-scale visual inspection:** text, guides, data, and annotations remain clear
   and free of defects that mechanical checks cannot judge.

For exported-only inputs, run artifact QA and final-scale visual inspection, then list
the semantic and live-render checks that could not be performed. Font identity and
embedding can be inspected only in formats that expose font resources; raster images
support visual text checks, not font-resource verification.

A later gate never closes an earlier defect. Fix hard defects, rerender, and recheck
until resolved or genuinely blocked. After hard gates pass, make at most one targeted,
evidence-based refinement for a soft layout issue or benign warning. When final QA and
one final-scale visual inspection pass, clean temporary artifacts and deliver; do not
continue open-ended warning elimination.

## Core rules

- **Static scope.** Do not add an interactive or browser companion unless requested.
- **Deliverables versus QA.** Keep requested scripts, figures, data products, and
  reports separate from temporary previews, logs, probes, caches, `__pycache__/`, and
  `.pyc` files. Use `qa_workspace()` or the system temporary directory for QA files.
- **Environment.** For headless scripts, run `import matplotlib; matplotlib.use("Agg")`
  before `import ultraplot as uplt`.
- **Scoped rc.** Import UltraPlot before target-specific overrides. Keep font and
  export rc settings in a scoped `uplt.rc.context(...)` covering creation and saving.
- **Purpose before chart.** Select the chart from the figure purpose, reader judgment,
  visual evidence, uncertainty, audience, and target.
- **Target records.** Inspect likely type/class/category/status fields, apply filters
  explicitly, and report input, retained, excluded, and excluded-by-class counts.
- **UltraPlot first.** Use UltraPlot for Matplotlib-compatible static figures. Change
  libraries only when requested or materially better, and state why.
- **Final size.** Configure the target preset or physical size before plotting, add
  every artist and guide, call `fig.canvas.draw()`, then measure
  `fig.get_size_inches() * 25.4`. Constructor values are not final evidence.
- **Automatic layout.** Start with UltraPlot defaults. Retain only the minimum targeted
  spacing or margin overrides needed for a visible defect or target requirement, and
  record each reason.
- **Typography.** When no font is specified, keep UltraPlot's default 9 pt TeX Gyre
  Heros sans-serif setting. Target requirements and glyph coverage take priority.
- **Panels.** Use panel letters when required. Avoid subplot titles unless requested or
  needed to remove genuine ambiguity.
- **Encoding honesty.** Prefer position/length for quantitative comparison, use
  accessible palettes and redundant channels, avoid rainbow/`jet`, keep continuous
  fields continuous, and identify uncertainty, statistics, and units.
- **Guides.** Prefer plotting, `format()`, colorbar, and semantic legend APIs over
  free-form text. Discover every legend through `fig.findobj(...)` during QA.
- **Final source of truth.** Report counts, mappings, dimensions, formats, DPI, and
  validation results from the final successful report and saved files.

## Conditional specialist gates

Add only the checks relevant to the figure:

- **Semantic marker size:** pass original values to `scatter(s=...)`; reuse the same
  source and area ranges in `sizelegend`. Precomputed areas require consistent
  `absolute_size=True`.
- **Continuous color:** verify normalization, data-unit ticks, quantity plus units, and
  `discrete=False` for continuous `pcolor`/`pcolormesh`. Inspect source and normalized
  quantiles so a valid scale does not compress most observations into a narrow color
  interval. Use transformation, documented bins, complementary evidence, or an explicit
  justification when compression weakens the requested judgment.
- **Multi-panel/shared guides:** bind each role to a distinct live axes and verify
  shared quantities use the same units, normalization, limits, and guide ownership.
- **Maps/rasters:** verify CRS, transform, coordinate ranges, target classes, extent,
  masks/nodata, longitude convention, and rasterization policy.
- **Statistics/CJK/named targets:** load the owning reference and apply its sample,
  correction, glyph, font, or publisher-specific policy.

## Reference routing

Load a reference only for a concrete unresolved decision. Search headings first and
read one bounded section. Use script `--help`, `--example`, or `--self-test` before
inspecting source.

| Read only when | File |
|---|---|
| Chart choice or encoding remains scientifically ambiguous | `references/principles.md` |
| Data are underspecified/complex, multi-panel, or need preprocessing/report detail | `references/workflow.md` |
| A specific UltraPlot call, sizing, guide, color, CJK, or API behavior is uncertain | `references/ultraplot-api.md` |
| A named venue or accessibility/statistical/output policy needs detail | `references/scientific-figures.md` |
| A concise editable chart pattern is needed | `references/recipes.md` |
| GeoJSON/vector/point-event map, CRS, projection, dateline, or context layer | `references/domains/maps-event-catalogs.md` |
| GeoTIFF/NetCDF/xarray/raster/gridded/climate/anomaly map | `references/domains/raster-maps.md` |
| Taylor diagram or Taylor suitability decision | `references/domains/taylor-diagrams.md` |
| Cartopy/GDAL/Rasterio/Fiona/GeoPandas import or environment failure | `references/domains/geospatial-setup.md` |
| Omics/genomics conventions | `references/domains/bioinformatics.md` |

## Bundled scripts

- `scripts/figure_qa.py`: draft/final facade, compact reports, temporary QA workspace,
  deliverable separation, and resolved PDF/TIFF fallback artifact policy.
- `scripts/render_qa.py`: in-memory size, legend geometry, semantic size, shared-color
  consistency, and continuous-color quantile diagnostics.
- `scripts/semantic_qa.py`: contract plus live axes, artists, values, filters, and outputs.
- `scripts/check_figure.py`: saved PDF/TIFF/SVG/PNG/EPS dimensions, DPI, fonts,
  transparency, raster mode, compression, and metadata.
- `scripts/ultraplot_compat.py`: cached runtime capability checks.
- `scripts/profile_data.py`: conservative tabular structure profiler.
- `scripts/update_skill.py`: once-daily stable-Release checks and copy-ready update
  notifications; it never installs updates.

Installation and dependencies are summarized in `README.md`. Implementation patterns
live in `references/recipes.md`, `references/scientific-figures.md`, and
`scripts/figure_qa.py --example`. Install only what the requested figure needs.
