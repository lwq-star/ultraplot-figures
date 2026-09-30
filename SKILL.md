---
name: ultraplot-figures
description: >-
  Create, revise, troubleshoot, review, and validate publication-quality static
  scientific figures with UltraPlot (import ultraplot as uplt). Use for
  UltraPlot or ProPlot-style tasks that require scientifically honest encodings,
  maintainable reproduction code, accessible layouts, or publication-ready
  exports. Also use when the user explicitly asks to configure or troubleshoot
  the official UltraPlot MCP server.
---

# UltraPlot Figures

Use UltraPlot's public axes-level APIs and automation to produce figures that are
scientifically honest, publication-ready, and easy for the user to maintain.
Treat concise reproduction code as part of figure quality.

## Release update checks

Before the normal workflow, resolve `scripts/update_skill.py` relative to this
`SKILL.md`. Unless the user has prohibited network access, run it with the Python
interpreter selected by the active environment rules and pass `--auto`.

- Automatic release checks are enabled by default and usually run at most once
  per local calendar day for the same installed skill version.
- Never download, install, or replace skill files during the check.
- For `update_available`, report the installed and latest versions, recommend
  updating, link the stable GitHub Release, and provide the returned copy-ready
  update request in the user's language. Continue the user's original task.
- Treat only published stable Releases as actionable updates. Ignore drafts and
  prereleases; if the helper cannot establish release metadata, continue with
  the user's task and report the check as inconclusive only when relevant.
- Do not perform an update unless the user explicitly requests it. For a later
  update request, preserve Git history and uncommitted changes for a Git worktree;
  back up an ordinary installation before replacement.
- Continue normally for `disabled`, `skipped_checked_today`, `no_release`,
  `up_to_date`, or `check_failed`.
- Respect `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` as an explicit local opt-out.

## UltraPlot MCP

### First-use bootstrap and preflight

A standalone skill install or update only copies files; it cannot run a
process-level `SessionStart` hook. On the first invocation after an install or
update, select the plotting interpreter and perform one read-only MCP
discovery/check pass. Repeat the inexpensive, idempotent preflight on later
figure tasks; do not claim that the skill has a persistent first-use marker.
Choose the interpreter in this order: an explicit user or project choice, the
host's environment rules, then the current task interpreter. Use that same
executable for plotting, checks, and MCP bootstrap.
Use the following state machine:

1. Discover the complete current-host tool registry and run the read-only
   `ensure_mcp.py --check` equivalent with the selected interpreter.
2. If a discovered server answers `ping` with `pong` and its source aligns with
   the selected interpreter, reuse it. A configured entry alone is not a health
   result.
3. For an ordinary figure creation or revision task, run bootstrap when the
   check explicitly returns `missing_ultraplot`, `missing_mcp_dependency`, or
   `needs_configuration`. A missing base package remains read-only unless the
   user has enabled the explicit package policy below. If the check returns
   `configured_without_docs`, a matching, version-marked documentation tree may
   be added as a docs-only enrichment when it is explicitly supplied or already
   present at the standard candidate path.
   Do not install or edit configuration merely because discovery is incomplete
   or callability is `unverified`.
4. After bootstrap reports a change and `restart_required`, start a new Codex
   session (or otherwise follow the host's restart procedure), then repeat
   discovery before labeling the server callable.
5. For review-only, status, or troubleshooting work, keep the preflight
   read-only unless the user explicitly requests repair. A task may use the
   selected runtime when UltraPlot is importable, but must disclose whether MCP
   callability is unverified or a direct health check actually failed.

When step 3 permits bootstrap, resolve `<skill-root>` from this `SKILL.md` and
run the script with that exact interpreter:

```text
<python> <skill-root>/scripts/ensure_mcp.py --bootstrap --python <python> --json
```

Leave the base-package policy at its default `manual` unless the user has
authorized package changes. For a missing package, add
`--package-policy install --ultraplot-version 2.7.0`; for an upgrade, add
`--package-policy upgrade --ultraplot-version <newer-2.7.x>`. A conda or mixed
environment also requires explicit `--allow-pip-in-conda` review before pip
mutation.

Use the host shell's quoting and path syntax as needed. By default the script
targets the active user-level `CODEX_HOME/config.toml`; use an explicitly
selected `--config` path only when the host confirms that project or alternate
configuration is the one Codex will load.

The command performs a read-only readiness check first. Do not silently
substitute a different interpreter or project environment than the one selected
by the user or host rules. A configured server that is not yet callable is not
a reason to create a duplicate entry; bootstrap is idempotent and only writes
the safe matching table.

When UltraPlot is present but its MCP extra is missing or incompatible, the
bootstrap requests the exact matching requirement
`ultraplot[mcp]==<installed UltraPlot version>` in that same interpreter,
rechecks the import, and then writes the matching user-level
`mcp_servers.ultraplot` entry when it is safe to do so. Pip may reinstall the
same distribution or resolve related dependencies; inspect `partial` when a
later configuration step fails. The operation is idempotent: a configured server
is reused, unrelated TOML settings are preserved, and a serial second task does
not reinstall the extra. A `configured`
result means that the local dependency and matching configuration table are
ready to be tested; it does not prove that the currently running Codex session
can call the server. `configured_without_docs` means that API/source calls may
be tested after restart, but no valid documentation tree is available for
`search_docs` or `read_doc`; when a matching tree is already available, the
bootstrap may add only its docs path.

Automatic MCP setup applies to the published stable UltraPlot 2.7.x series
starting at 2.7.0. Older, future-major, prerelease, local-build, or otherwise
unverifiable source versions are reported for manual repair by default. An
explicit `upgrade` or `install-and-upgrade` package policy may migrate an older
normal pip installation to an exact supported 2.7.x target after the package
manager and provenance checks pass. An
editable/development installation that is missing the MCP extra is also left
for manual installation instead of being replaced from PyPI; an already
MCP-enabled editable environment may still be reused when its configuration is
safe to edit.

Base-package installation and upgrades are a separate, opt-in policy. The
default is `manual`, so an ordinary first-use check never changes the base
UltraPlot distribution. Enable `install`, `upgrade`, or `install-and-upgrade`
with `--package-policy`, or set `ULTRAPLOT_FIGURES_PACKAGE_POLICY`; the
boolean aliases `ULTRAPLOT_FIGURES_AUTO_INSTALL_ULTRAPLOT=1` and
`ULTRAPLOT_FIGURES_AUTO_UPGRADE=1` are also supported. Installation uses the
exact stable target from `--ultraplot-version` or
`ULTRAPLOT_FIGURES_ULTRAPLOT_VERSION` (default `2.7.0` for a missing package),
and installs `ultraplot[mcp]` in one operation. An upgrade requires an exact
target version and only proceeds when it is newer than the current version;
the helper never downgrades or uses an unbounded `--upgrade`.

The package policy checks provenance and package-manager metadata first. It
does not replace editable, remote, unknown, or conda/mixed installations from
PyPI by default. A reviewed conda/mixed environment may explicitly opt in with
`--allow-pip-in-conda` or `ULTRAPLOT_FIGURES_ALLOW_PIP_IN_CONDA=1`. Conflicts,
invalid configuration, failed post-install verification, and package-manager
ambiguity remain manual. Package changes are reported with `package_action`,
`package_requirement`, `previous_version`, `target_version`, `partial`, and
`restart_required`; pip changes are not automatically rolled back.

Automatic setup never clones documentation, overwrites a conflicting or
non-standard existing server, changes unrelated settings, or restarts Codex.
Use `ULTRAPLOT_FIGURES_MCP_AUTO_SETUP=0` to opt out. On opt-out, missing MCP
extras, invalid configuration, conflicts (including invalid timeout or HTTP
transport fields), permission errors, unverified UltraPlot provenance, or
package installation failures are reported in the JSON result. If UltraPlot
itself is importable, an ordinary task may continue with the selected Python
runtime and must disclose the exact fallback reason. If the result is
`base_install_required` or `base_install_disabled`, do not claim that figure
work can fall back: the base package is not available in the selected
environment. Review-only work that does not execute plotting code may still
continue.

When the JSON boolean field `restart_required` is `true`, start a new task or
restart Codex before treating the newly configured server as callable; until then, continue with
the selected runtime only when UltraPlot is importable and the task permits a
fallback. A standalone skill installer only copies the skill files, so this
bootstrap runs when the installed or updated skill is first invoked, rather
than as a process-level SessionStart hook.

If configuration reports a conflict with an existing command, table shape,
timeout, HTTP/auth transport, or environment, stop and review that entry
manually. `ultraplot_provenance_unverified` means the imported package cannot be
matched safely to its distribution source, so do not let pip replace it
silently. Use `--force` only after the
user explicitly authorizes replacing the reviewed command; never use it as an
automatic retry. `config_invalid` is a read-only diagnostic failure: preserve
the file, report the exact reason, and use the selected runtime only when
UltraPlot itself is importable. `interpreter_error` means that the selected
interpreter could not be verified; stop figure execution until another valid
interpreter is selected.

A successful config write is not itself an MCP health or environment-alignment
result: rerun discovery and `ping` after the new Codex session starts. A
bootstrap failure is fail-open for tasks whose selected runtime can still
import UltraPlot, but it must be reported rather than silently ignored. If the
JSON result marks the operation `partial`, report that the environment may have
changed even though configuration did not complete, and do not retry blindly.

Before figure implementation or revision, perform the discovery pass above. For
review-only work, do so only when the review depends on API/version behavior or
MCP use was explicitly requested. Do not infer that MCP is unavailable merely
because no `mcp__ultraplot__*` tool appears in an initially expanded tool list;
inspect the current host's complete callable-tool registry, including deferred
or nested tools.

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
code. Use `get_api("ultraplot.subplots")` as a stable alignment probe when it is
available; otherwise use a task-relevant API probe when cross-environment
alignment must be established. `ping` and an alignment probe alone do not count
as MCP-assisted implementation. Use `get_api` for signatures and
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

For an ordinary figure task, use the selected runtime after the required
discovery/preflight attempt when the runtime can import UltraPlot and any of
these states applies: no matching tool was found by complete discovery; no
complete discovery mechanism exists; `ping` is absent, fails, or does not
return `pong`; the `get_api` alignment probe is absent or fails; alignment is
mismatched or unverified; or a task-relevant lookup is unavailable or fails.
Disclose the exact fallback reason in the final response. Never infer
"not configured" from tool absence; configuration and current-session
callability are separate facts. A `missing_ultraplot`, `base_install_required`,
`base_install_disabled`, `package_manager_requires_manual`,
`upgrade_requires_manual`, or `editable_ultraplot` result is a prerequisite
failure, not a runtime fallback state.

When MCP use is explicitly requested or defines an experimental arm, do not
present a fallback result as MCP-enabled. A run may be labelled MCP-enabled only
when `ping` succeeded, the environments matched, and at least one task-relevant
MCP lookup succeeded. Report the MCP tools actually used.

MCP lookup does not replace executing the delivered script or visually
verifying final exports. For ordinary first use, the bounded `--bootstrap`
operation may install the exact MCP extra matching an already installed
UltraPlot and edit the single safe MCP table. It may install or upgrade the
base package only when the explicit package policy and target rules above are
enabled. It never clones documentation, uses `--force`, or restarts Codex.
Those broader actions, and explicit repair of a conflicting entry, still
require a user request. For setup troubleshooting or repair, read
`references/mcp-setup.md`.

## Retained task artifacts

For figure creation and revision tasks, apply this allowlist to files created by
the current task. It is not permission to delete, rename, or overwrite a
user-provided input or an existing project file. Retain only what is needed to
reproduce and deliver the requested result:

- one independently runnable plotting entry script for each scientifically
  distinct figure, plus minimal local helper code only when it materially
  reduces real duplication;
- the requested final figure files; when the user, journal, or project does not
  specify formats, use PDF plus PNG for a publication-oriented static figure;
- only when substantive preprocessing is necessary, the preprocessing code and
  the final processed datasets semantically consumed by the plotting code.

A processed file is semantically consumed only when its values determine final
marks, labels, layout, or export behavior. Reading a file only for validation,
provenance reporting, logging, or an assertion does not make it a reproduction
dependency. Every persisted preprocessing result must have a real figure
consumer. Do not reread a validation-only file to make it appear necessary.

Do not create or retain copies of user-provided raw inputs, intermediate
datasets, validation-only or exclusion tables, diagnostic renders, screenshots,
logs, audit dictionaries, JSON reports, manifests, README files, environment
files, caches, backups, or temporary files merely for this task. Re-render
corrections to the same authorized final paths. Summarize material assumptions,
deviations, and unresolved issues in the final response instead of creating
another report. Remove only temporary artifacts created by the current task,
and leave pre-existing files untouched.

For review-only work, do not create retained files unless the user asks for a
revision or explicitly requests a report. For revisions, preserve the existing
workflow and authorized output paths where practical, and make the smallest
maintainable change that satisfies the request; do not prune unrelated files.

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
  after confirming that the server uses the same environment. UltraPlot 2.7.0,
  matplotlib 3.10.6, and cartopy 0.25.0 are a validated reference baseline,
  not a requirement when the selected project specifies another compatible
  version.
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
- For maps whose displayed coordinates are longitude/latitude, use EPSG:4326
  with `proj="pcarree"` and degree-formatted longitude and latitude when the
  user, journal, or figure specification does not choose another projection.
  Honor a requested or established project projection, and use the original or
  scientifically appropriate projected data for calculations.
- Do not add a new figure-level or subplot-level title merely by convention.
  Preserve an existing title and honor a user, journal, or figure-specification
  request. This does not restrict axis labels, guide labels, annotations, panel
  identifiers, or genuine grid-edge structural labels.
- For two or more independent main Axes, use figure-local panel identifiers such
  as `abc="a.", abcloc="ul"` when identifiers are needed and the user, journal,
  or established project convention does not specify another policy. Place them
  where they remain clear of ordinary annotations and plotted data.
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
- Use exactly one physical width authority. Honor a requested `journal=` preset,
  total `figwidth`, or established project width. For a new publication figure
  with no width guidance, `journal="nat2"` (183 mm) is a reasonable default;
  do not combine competing width authorities or approximate a journal preset.
- Unless the user, journal, output specification, or established project
  requires an exact figure height, leave the total height unconstrained. When
  `journal=` or `figwidth=` fixes the width, do not also pass `figheight=`,
  `figsize=`, or call `set_size_inches()` unless that explicit height is part of
  the requested specification. This preserves UltraPlot's ability to derive
  the height from the reference Axes, fixed data aspects, guides, and GridSpec
  geometry.
- Honor the user, journal, output specification, or established project for
  physical size, formats, and raster resolution. When none is specified, use a
  consistent publication-appropriate raster DPI (600 or higher when practical)
  for requested raster outputs, and use the same DPI across those outputs; do
  not force a DPI setting on vector-only output.
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
- For the first render with final data, labels, annotations, panel identifiers,
  and guides, leave `left`, `right`, `top`, `bottom`, `space`, `wspace`,
  `hspace`, `outerpad`, `innerpad`, `panelpad`, `wpad`, and `hpad` automatic when
  practical. Do not categorically prohibit explicit spacing: after a failed
  automatic render, classify the defect and retain only the smallest scoped
  override.
  Leave unaffected sequence entries as `None` so they remain automatic.
- Do not use fixed margins or spacing to repair ordinary-annotation collisions,
  incorrect limits, fixed-aspect slot waste, unsuitable ratios, a wrong
  `refnum`, or an infeasible topology.
- Never combine UltraPlot auto layout with Matplotlib `tight_layout()`,
  `constrained_layout`, or `subplots_adjust()`.
- Use an axes-level guide for one Axes and a figure-level guide only when the
  encoding is genuinely shared.

Preserve the effective UltraPlot font configuration by default. For Chinese
text, choose an installed local CJK fallback that matches the user, journal, or
project (for example, `Microsoft YaHei` when it is installed), without
downloading or globally installing fonts. Resolve the fallback before figure
creation and register a local `.ttf`, `.ttc`, or `.otf` file only when the
backend requires it. Verify required glyphs in delivered vector or raster
output when rendering is available.

## Implementation sequence

Select the plotting interpreter, then complete the MCP discovery, health, and
environment-alignment preflight above. Inspect the input or existing
implementation and choose the data flow. When the server is operational and
matched and a genuine API, concept, or version question exists, complete at
least one lookup relevant to the task as now understood before writing plotting
code. If substantive preprocessing is needed, implement and run it first. Load
only plot-ready data, perform minimal plotting-input checks, create and format
the figure, save directly to the authorized final paths, and verify internally
when the task produces a figure deliverable.
Use `references/recipes.md` for concise starting patterns; do not treat any
recipe as a mandatory function or project template.

## Internal verification

For a figure deliverable, render and inspect the final files before handoff when
the requested backend and output format are available. Verification is
agent-side work, not delivered reproduction code. For review-only or
code-only work with no renderable deliverable, inspect the relevant source and
inputs instead and state any unverified visual checks.

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
resolution when specified, applicable geospatial behavior, and the retained-file
allowlist. When `journal="nat2"` is actually used, verify internally that the
saved PDF is 183 mm wide within 0.2 mm and that PNG dimensions agree with the
selected DPI. Use `references/verification.md` for the detailed procedure and
do not retain a verification report.

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
- `references/mcp-setup.md`: when first-use bootstrap reports a missing or
  misaligned server, or for an explicit MCP configuration or troubleshooting
  request.
- `scripts/ensure_mcp.py`: first-use checks, safe automatic MCP bootstrap, and
  explicit repair configuration. Run it with the selected plotting interpreter;
  do not retain its JSON output as a task artifact.
- `references/color.md`: advanced colormap construction or perceptual checks.
- `references/recipes.md`: a concise starting pattern for a matching figure.

References inform implementation and internal verification. They do not expand
the retained figure-task artifact allowlist.
