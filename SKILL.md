---
name: ultraplot-figures
description: >-
  Create, revise, troubleshoot, review, and validate publication-quality static
  scientific figures with UltraPlot (import ultraplot as uplt). Use for
  UltraPlot or ProPlot-style figure tasks requiring scientifically honest
  encodings, concise and maintainable reproducible code, accessible layouts,
  and publication-ready exports. Retain only the minimal plotting code, any
  necessary preprocessing code and final processed data, and the requested
  final figures; keep verification internal. Also use when the user explicitly
  asks to configure or troubleshoot the official UltraPlot MCP server.
---

# UltraPlot Figures

Use UltraPlot's public axes-level APIs and automation to produce figures that are
scientifically honest, publication-ready, and easy for the user to maintain.
Treat concise reproduction code as part of figure quality.

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

## UltraPlot MCP

Before any figure implementation or revision, perform one UltraPlot MCP
discovery pass. For review-only work, perform the same preflight when the review
depends on API or version behavior, or when MCP use or a skill comparison is
explicitly requested. Do not infer that the MCP is unavailable merely because
no `mcp__ultraplot__*` tool appears in the initially expanded tool list. Inspect
the current host's complete callable-tool registry, including deferred or nested
tools.

When `functions.exec` exposes `ALL_TOOLS`, search it for exact tool names
beginning with `mcp__ultraplot__` and invoke discovered tools through the
matching `tools.mcp__ultraplot__...` methods. Otherwise, use the host's
equivalent complete or deferred-tool discovery mechanism. If no complete
discovery mechanism exists, classify discovery as unverified; do not report
the MCP as unavailable or unconfigured.

Treat discovery, health, and environment alignment as separate checks:

1. If `mcp__ultraplot__ping` is discovered, call it once before implementation.
   Registry presence means discovered; only a `pong` response means operational.
   If other matching tools are present but `ping` is absent, classify health as
   unverified.
2. For an operational server, call `get_api("ultraplot.subplots")`. If this tool
   is absent or the call fails, classify alignment as unverified.
3. With the selected plotting interpreter, resolve
   `inspect.getsourcefile(ultraplot.subplots)` and compare the normalized path
   with the MCP `source_file`. If either path cannot be established, classify
   alignment as unverified rather than mismatched.
4. Canonicalize paths before comparison, resolving links where possible and
   applying the platform's case normalization. Prefer an exact source-file
   match. If host path mapping makes exact files incomparable, compare package
   or environment roots only when both can be established; otherwise classify
   alignment as unverified.
5. Treat the selected plotting interpreter as authoritative whenever the paths
   differ or alignment cannot be verified.

For an operational, environment-matched server, inspect the input or existing
implementation and identify any genuine API, concept, or version question. When
one exists, perform at least one task-relevant MCP lookup before writing plotting
code. `ping` and the fixed `get_api("ultraplot.subplots")` alignment probe alone
do not count as MCP-assisted implementation. Use `get_api` for signatures and
docstrings, `search_docs` followed by `read_doc` for concepts and examples,
`search_release_notes` for version history, and `get_source` only when the
preceding sources are insufficient.

If inspection establishes that no such question exists, as with a literal-only
label revision, do not invent an MCP lookup. Record the task-relevant lookup as
not applicable and do not label the run MCP-assisted or MCP-enabled.

API environment alignment does not prove that a separately configured
documentation checkout has the same version. For version-sensitive decisions,
verify the documentation version against the selected runtime or cross-check the
claim with the matched live API or source. Otherwise treat documentation
provenance as unverified and use it only for non-version-specific guidance.

For an ordinary figure task, fallback to the selected runtime after making the
required discovery and preflight attempt when any of these states applies: no
matching tool was found by complete discovery; no complete discovery mechanism
exists and a required tool is not directly discoverable; `ping` is absent,
fails, or does not return `pong`; the `get_api` alignment probe is absent or
fails; alignment is mismatched or unverified; or a task-relevant lookup is
unavailable or fails. Disclose the fallback and its exact reason in the final
response. Never infer "not configured" from tool absence; configuration and
current-session callability are separate facts.

When MCP use is explicitly requested or defines an experimental arm, do not
present a fallback result as MCP-enabled. A run may be labelled MCP-enabled only
when `ping` succeeded, the environments matched, and at least one task-relevant
MCP lookup succeeded. Report the MCP tools actually used.

MCP lookup does not replace executing the delivered script or visually
verifying final exports. For MCP troubleshooting, begin with read-only
diagnostics. Do not install packages, clone documentation, edit Codex
configuration, or restart Codex unless the user explicitly requests the
corresponding configuration or repair action. For an explicit setup,
troubleshooting, or repair request, read `references/mcp-setup.md`.

## Retained task artifacts

For figure creation and revision tasks, treat retained task files as a strict
allowlist. Retain only:

- one independently runnable plotting entry script for each scientifically
  distinct figure, plus minimal local helper code only when it materially
  reduces real duplication;
- the requested final figure files; when formats are unspecified, retain PDF and
  PNG;
- only when substantive preprocessing is necessary, the preprocessing code and
  the final processed datasets semantically consumed by the plotting code.

A processed file is semantically consumed only when its values determine final
marks, labels, layout, or export behavior. Reading a file only for validation,
provenance reporting, logging, or an assertion does not make it a reproduction
dependency. Every persisted preprocessing result must have a real figure
consumer. Do not reread a validation-only file to make it appear necessary.

Do not retain copies of user-provided raw inputs, intermediate datasets,
validation-only or exclusion tables, diagnostic renders, screenshots, logs,
audit dictionaries, JSON reports, manifests, README files, environment files,
caches, backups, or temporary files. Re-render corrections to the same final
paths. Summarize material assumptions, deviations, and unresolved issues in the
final response instead of creating another file.

For review-only work, do not create retained files unless the user asks for a
revision. For revisions, preserve the existing workflow where practical and make
the smallest maintainable change that satisfies the request.

User-authorized MCP setup or repair is infrastructure work, not a figure
deliverable. The figure-task allowlist does not prohibit the specific dependency,
documentation checkout, or configuration changes required by that request;
preserve unrelated infrastructure and settings.

## Choose the workflow

1. Clarify the scientific comparison and intended message.
2. Inspect variables, units, observation level, groups, missing values, and
   whether the input is raw, processed, or already plot-ready.
3. Use a plot-only workflow when the input is scientifically plot-ready.
4. Add a preprocessing stage only when operations materially change the sample,
   observation unit, scientific values, or analytical result.
5. For geospatial data, also inspect source CRS, coordinate units, bounds,
   transform, resolution, orientation, and NoData metadata as applicable.

Substantive preprocessing includes sample-changing cleaning or filtering, joins,
aggregation to a new observation level, normalization, derived scientific
variables, model fitting, inferential statistics, uncertainty estimation, and
analytical spatial transformations. Put these operations and their scientific
input checks in the preprocessing script.

Display-only operations may remain in the plotting script when concise and
transparent. These include an explicitly requested display subset, category and
draw order, a reshape required only by the plotting API, bar positions, label
formatting, axis limits, and simple descriptive values computed from the exact
plotted rows. Do not create a preprocessing script merely because a pandas or
xarray operation is used.

An EPSG:4326 transformation created only for final display may remain in the
plotting script. Any transformed data used for measurement, comparison,
statistics, or classification belong in preprocessing. Never overwrite source
data with a display representation.

When preprocessing is necessary, write its final outputs before implementing the
plotting script. Prefer the smallest number of coherent output datasets. Keep
different observation grains separate when combining them would make the result
harder to understand.

## Maintainable code

Write delivered code for reproduction and maintenance, not to prove that QA ran.

- Keep the execution path straightforward: imports, meaningful constants, data
  loading, minimal validation, plotting, formatting, saving, and entry point.
- Validate each scientific assumption once at the stage that owns it.
- In plotting code, validate only the fields and invariants required to render
  and interpret the figure. Do not recompute preprocessing results merely to
  confirm a processed table.
- Keep only processed columns and statistics used by the figure.
- Create a helper only when reused or when it isolates a genuinely non-trivial
  operation. Avoid one-line wrappers, pass-through abstractions, unused metadata,
  and configuration objects that merely rename local constants.
- Do not require a universal `build_figure()` function, dataclass, project
  structure, or helper module.
- Expose command-line arguments only for inputs, outputs, and parameters users
  are reasonably expected to change.
- Write comments for scientific rationale or non-obvious constraints, not to
  narrate ordinary code.
- Prefer pandas or xarray objects directly when they make data flow clearer.
- Keep rendering code in the plotting entry script by default. A parameterized
  entry script may generate a homogeneous series only when scientific meaning,
  layout, and processing logic are the same.

## Scientific and output requirements

- Use public documented APIs. Treat versions imported by the selected plotting
  interpreter as authoritative. Treat MCP results as current for the task only
  after confirming that the server uses the same environment. The validated
  baseline is UltraPlot 2.7.0, matplotlib 3.10.6, and cartopy 0.25.0.
- For routine values attached to bars, use the `bar_labels` and
  `bar_labels_kw` parameters of `Axes.bar()` or `Axes.barh()` instead of
  positioning `Axes.text()` labels manually.
- Let UltraPlot supply the default visual color styling. Explicitly select or
  override a colormap, normalization, color cycle, or category color only when
  required by scientific meaning, such as a real neutral value, cyclic data,
  stable category identity across related figures, or a shared comparison
  domain. Never use `jet` or `rainbow` for magnitude data.
- Preserve honest baselines, observation units, spatial geometry, and uncertainty
  meaning. Do not silently discard observations or alter scientific values.
- Display geospatial distributions in EPSG:4326 with `proj="pcarree"` and
  degree-formatted longitude and latitude by default. Use another display
  projection only when the user or figure specification requests it. Use the
  original or scientifically appropriate projected data for calculations.
- Do not add or retain a figure-level or subplot-level title unless the user
  directly requests it. This restriction does not apply to axis labels, guide
  labels, annotations, panel identifiers, or genuine grid-edge structural labels.
- For two or more independent main Axes, use figure-local
  `abc="a.", abcloc="ul"` unless the user or journal requests another policy.
  Reserve the inner upper-left region and move ordinary annotations first.
- Use one consolidated `format()` call per coherent axes group. Mixed GeoAxes and
  CartesianAxes may require separate calls because they accept different keys.
- Treat the effective UltraPlot configuration as the default authority for
  visual appearance. Preserve the explicit policies defined by this skill, but
  otherwise do not restate or override UltraPlot's effective defaults.
- In each figure, explicitly set only parameters required for scientific
  meaning, publication size or output specifications, or the smallest local
  correction to a concrete defect observed in the final-data render. Omit
  parameters used only to restyle an already acceptable UltraPlot default.
- When the same scientific categories recur across related figures, reuse their
  established color mapping so that color identity remains consistent. Do not
  create a shared color mapping for categories confined to one figure.
- Apply necessary overrides at the narrowest scope: a plotting call or
  `format()` first, then a bounded `uplt.rc.context()` only for settings genuinely
  shared by several figures. Do not use session-global or persistent rc changes
  for a single figure.
- Use exactly one physical width authority. Honor a requested `journal=` preset
  or total `figwidth`; otherwise use `journal="nat2"` (183 mm). Do not combine
  competing width authorities or approximate a journal preset.
- Unless the user, journal, or output specification requires an exact figure
  height, leave the total height unconstrained. When `journal=` or `figwidth=`
  fixes the width, do not also pass `figheight=`, `figsize=`, or call
  `set_size_inches()`. This preserves UltraPlot's ability to derive the height
  from the reference Axes, fixed data aspects, guides, and GridSpec geometry.
- Unless the user or journal specifies another value, define
  `EXPORT_DPI = 1000` and pass it to every final `fig.save(...)` call. Use the
  same DPI for all requested formats and keep the default above 600 dpi.
- Do not use `bbox_inches="tight"` when exact physical size matters; it changes
  the saved canvas.

## Layout and typography

Read `references/layout.md` before implementing a picture array, spanning
subplot, mixed fixed- and auto-aspect layout, or unconstrained figure dimension,
and whenever the first render has unexplained whitespace, misalignment,
clipping, or overlap.

- Use the smallest grid that represents the intended topology. Use picture
  arrays only for genuine spans, holes, or non-rectangular topology, and use
  `wratios` and `hratios` for relative column and row sizes. Do not add duplicate
  grid rows or columns solely to make a subplot wider or taller.
- Use one UltraPlot `GridSpec`, compatible axis sharing, and the subplot that
  should genuinely govern automatic sizing. Preserve fixed data aspects.
- Keep UltraPlot's own tight layout active. For complex layouts, pass
  `tight=True` or confirm that the effective `rc["subplots.tight"]` is `True`.
- The first render with final data, labels, annotations, panel identifiers, and
  guides must omit `left`, `right`, `top`, `bottom`, `space`, `wspace`,
  `hspace`, `outerpad`, `innerpad`, `panelpad`, `wpad`, and `hpad`.
- Do not categorically prohibit explicit spacing. After a failed automatic
  render, classify the defect and retain only the smallest scoped override.
  Leave unaffected sequence entries as `None` so they remain automatic.
- Do not use fixed margins or spacing to repair ordinary-annotation collisions,
  incorrect limits, fixed-aspect slot waste, unsuitable ratios, a wrong
  `refnum`, or an infeasible topology.
- Never combine UltraPlot auto layout with Matplotlib `tight_layout()`,
  `constrained_layout`, or `subplots_adjust()`.
- Use an axes-level guide for one Axes and a figure-level guide only when the
  encoding is genuinely shared.

Preserve the effective UltraPlot font configuration by default. For Chinese
text, append `Microsoft YaHei` to the ordered `font.family` fallback list unless
the user or journal specifies another font. Resolve it before figure creation
and register its `.ttf`, `.ttc`, or `.otf` file if necessary. Verify required
glyphs in vector and raster output.

## Implementation sequence

Select the plotting interpreter, then complete the MCP discovery, health, and
environment-alignment preflight above. Inspect the input or existing
implementation and choose the data flow. When the server is operational and
matched and a genuine API, concept, or version question exists, complete at
least one lookup relevant to the task as now understood before writing plotting
code. If substantive preprocessing is needed, implement and run it first. Load
only plot-ready data, perform minimal plotting-input checks, create and format
the figure, save directly to the final requested paths, and verify internally.
Use `references/recipes.md` for concise starting patterns; do not treat any
recipe as a mandatory function or project template.

## Internal verification

Render and inspect the final files before handoff. Verification is agent-side
work, not delivered reproduction code.

Do not place renderer measurements, bounding-box inspection, identifier
discovery, PDF or PNG inspection, source audits, directory audits, QA report
writers, or verification-result dictionaries in delivered plotting or
preprocessing scripts. Use temporary task code or skill-bundled validation tools,
write diagnostic artifacts outside the retained set only when necessary, and
remove artifacts created by the current task after verification.

Delivered scripts may retain concise checks for missing inputs, required
columns, empty data, non-finite plotted values, and scientific invariants needed
to interpret the result. Keep all other checks internal.

Before handoff, confirm scientific meaning, labels and units, authorized text,
panel identifiers, layout and guide clearance, glyph coverage, output size and
resolution, applicable geospatial behavior, and the retained-file allowlist. For
`journal="nat2"`, verify internally that the saved PDF is 183 mm wide within
0.2 mm and that PNG dimensions agree with the selected DPI. Use
`references/verification.md` for the detailed procedure and do not retain a
verification report.

Whenever the MCP preflight ran, or for an explicit MCP request or skill
comparison, also confirm that the final response states the discovery result,
health result, environment-alignment result, and task-relevant MCP tools actually
called. State clearly when a review-only task skipped the preflight. Keep this
audit in the response; do not retain an MCP log file.

## Optional references

Load only the reference needed for a non-trivial decision:

- `references/scientific-principles.md`: ambiguous scientific question,
  preprocessing boundary, or processed-data design.
- `references/layout.md`: complex topology, fixed-aspect geometry, whitespace,
  alignment, clipping, or panel-identifier conflicts.
- `references/verification.md`: detailed internal QA procedures. Never copy its
  diagnostic implementation into delivered scripts.
- `references/geospatial.md`: CRS, raster, vector, or GeoAxes details.
- `references/mcp-setup.md`: only for an explicit request to configure or
  troubleshoot the official UltraPlot MCP server.
- `references/color.md`: advanced colormap construction or perceptual checks.
- `references/recipes.md`: a concise starting pattern for a matching figure.

References inform implementation and internal verification. They do not expand
the retained figure-task artifact allowlist.
