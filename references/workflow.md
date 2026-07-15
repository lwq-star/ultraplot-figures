# Workflow and deliverables

Use this file when a request is vague, multi-panel, publication-facing, or needs
data inspection before choosing a chart.

## Research figure contract

Before plotting, settle the contract in one or two sentences:

| Field | Decide |
|---|---|
| Research question | What scientific question does this figure serve? |
| Figure role | Data overview, main result, relationship/mechanism, method validation, sensitivity analysis, or diagnostic/supplement. |
| Reader judgment | What should readers understand, judge, or test from the figure? |
| Visual evidence | The comparison, trend, distribution, spatial pattern, uncertainty, model diagnostic, or statistical result that supports that judgment. |
| Audience | Manuscript, target journal, poster, supplement, reviewer revision, or submission figure. |
| Data source | Raw files, derived tables, model output, image/raster files, or user-provided example data. |
| Target records | Required subset, class/type/status filters, and retained/excluded counts. |
| Panel roles | Every required panel and the evidence it must show. |
| Visual encoding | Chart type, grouping, facets, scale, color meaning, and uncertainty. |
| Statistics | Raw observations, summary interval, fitted model, p value, effect size, or no inference. |
| Export | Target venue, required formats, raster DPI, intended physical size, measured final physical size, and editable script path. |

Write every requested judgment as an atomic `requested_judgments` entry with a
verbatim `request_span`, the relevant data `fields`, and an `evidence_kind`. Bind each
judgment to real panels and channels in `evidence_map`. For multi-panel figures, define
the role of each panel before coding. If one panel does not support a requested
judgment or necessary interpretation limit, omit it or move it to a supplement.

For an explicit chart, panel list, or single-panel request, treat panel scope as closed:
expected panels are exactly the requested panels. A request for several scientific
aspects with no chart specification is not closed; use the minimum panels needed to
provide strong evidence for each judgment. Do not promote optional diagnostics,
insets, or context plots into the main figure. Every supporting panel needs a requested
judgment, a documented data-first recommendation, or a concrete scientific-correctness
reason.

## User prompt contract

When the user asks for a scientific figure, map the prompt back to the research
figure contract above. Use this portable prompt order when teaching users how to
ask:

```text
research question -> figure role -> reader judgment -> visual evidence
-> data source -> interpretation limits -> export target
```

Do not treat "make a scatter plot", "make a map", or "plot this CSV" as a
complete scientific request. These are implementation hints unless they are tied to
a research question and reader judgment.

When fields are missing:

- Missing research question: inspect the data first and infer only exploratory or
  data-overview questions from the data structure.
- Missing figure role: default to data overview unless the user provides a claim,
  hypothesis, target comparison, validation task, or sensitivity question.
- Missing reader judgment: derive a concrete judgment from the research question;
  do not repeat chart names as judgments.
- Missing visual evidence: choose evidence from the strongest data affordances
  after inspection.
- Missing data semantics or units: inspect file metadata and names, but ask one
  focused question if interpretation would be materially ambiguous.
- Missing limits: explicitly state the strongest conclusions the figure cannot
  support.
- Missing export target: first determine whether a journal, publisher, poster, or
  supplement specification is implied. Resolve settings independently and record a
  source for each one. Preserve explicit formats; when venue and physical width are
  unknown, use the current `nat2` width (`183 mm`) as a stated size fallback with
  automatic height. If formats are also unknown, use PDF plus a 600 dpi opaque RGB
  lossless-LZW TIFF. Keep unrequested previews in temporary QA storage.

When the user asks how to formulate a plotting request, give a concise tutorial
based on this contract. Prefer concrete prompts over abstract advice.
Recommend that the user explicitly name the skill in the first line, using
`Please use $ultraplot-figures for this task.` or a local `SKILL.md` link when the
interface supports file links.

Good minimal prompt:

```text
Please use $ultraplot-figures for this task.

Please inspect this dataset and recommend a scientific figure goal.
Before plotting, summarize what the data contain, propose 1 to 3 figure goals,
state what each goal can and cannot support, recommend one default, then proceed.
Data path: [path]
```

Good complete prompt:

```text
Please use $ultraplot-figures for this task.

Please make a scientific figure from [data path].

Research question:
[What scientific question should the figure serve?]

Figure role:
[Data overview / main result / relationship-mechanism / method validation /
sensitivity analysis / diagnostic-supplement]

Reader judgment:
Readers should be able to judge [specific judgments].

Visual evidence:
Show [patterns, comparisons, distributions, spatial fields, uncertainty, or
diagnostics].

Data semantics:
[Key variables, units, filters, groups, CRS, model outputs, or derived tables.]

Limits:
Do not infer [causality, mechanism, trend, significance, or other unsupported
claims].

Output:
[PDF/TIFF/SVG/PNG, DPI, target venue, editable scripts, preprocessing split.]
```

## Scientific figure roles

Classify the figure's role before choosing a chart. The role controls the level of
inference the figure may support.

| Figure role | Question served | Good default direction |
|---|---|---|
| Data overview | What does the dataset contain, and what are its coverage, sample structure, or obvious limits? | Maps, distributions, time counts, missingness or sample-size summaries. |
| Main result | What is the core finding, difference, trend, or spatial pattern? | Group comparison, trend, spatial pattern, effect-size, or uncertainty-aware result panels. |
| Relationship or mechanism | How do variables relate, and is the pattern consistent with a proposed mechanism? | Scatter/density, faceting, response curves, gradients, or paired panels with caveats. |
| Method validation | Is the method, model, or measurement reliable enough for the stated use? | Observed-vs-predicted, residuals, calibration, Taylor diagram, or benchmark comparison. |
| Sensitivity analysis | Does the result depend on thresholds, assumptions, models, or preprocessing choices? | Multi-scenario comparison, sensitivity curves, or parameter-sweep panels. |
| Diagnostic or supplement | What anomalies, biases, limitations, or supporting checks should readers see? | Residuals, outliers, sampling distribution, error structure, or QC panels. |

## Data-driven figure-goal recommendation

Use this section when the user provides data but does not specify the figure type,
variables, message, or research question, or when the user says "you decide".

Do not use this section merely because an otherwise explicit chart request omits a
research question. "Make one global event map" is an explicit single-map request;
inspect and filter the data, but do not add distribution panels unless needed for
scientific correctness. "Show spatial distribution and numeric characteristics" is
an evidence goal, not an explicit single-map constraint.

Do not start with a generic "what plot do you want?" question. Inspect the data
first, then recommend figure goals. A figure goal is the scientific purpose of the
figure, not merely the chart type: "show the global distribution of earthquake
events and their magnitude/depth structure" is a goal; "make a map and histogram"
is only an implementation.

Use this order: research question -> figure role -> reader judgment -> visual
evidence -> chart implementation. When the research question is unknown, infer only
plausible exploratory questions from the data structure and label the output as
data overview or diagnostic rather than a conclusion figure.

Follow these principles:

- Recommend goals that use the dataset's strongest structure: spatial, temporal,
  ordered, grouped, multivariate, model-output, or statistical-result structure.
- Prefer high-information, low-inference figures when no research question is
  supplied: overview maps, distributions, time summaries, group comparisons,
  relationship diagnostics, or model diagnostics.
- Do not invent causal, mechanistic, trend, or significance claims that are not
  supported by the request and data.
- Label the default as exploratory or data-overview unless the user supplies a
  manuscript claim, hypothesis, statistical test, or target comparison.
- Ask at most one focused confirmation question when the top options represent
  materially different scientific messages. If the user says "you decide", proceed
  with the recommended exploratory figure and state the assumption.

Rank candidate goals with this order:

1. Use the data's primary structure and domain meaning.
2. Serve a clear research question or honest exploratory question.
3. Make the dataset understandable before adding modeling or inference.
4. Avoid extra assumptions, external baselines, or heavy preprocessing.
5. Produce a figure that can serve as a manuscript or analysis starting point.
6. Keep the visual encoding readable at the observed sample size.

Plan from evidence needs before chart types:

| Evidence need | Data structure | Figure goal | Typical implementation |
|---|---|---|---|
| Show where something occurs | Coordinates, geometries, rasters, regions | Reveal spatial distribution, coverage, hotspot, or regional contrast. | Map, spatial field, zonal summary, or map plus distribution panel. |
| Show how something changes | Time, ordered sequence, depth, rank, genomic position | Reveal trend, event frequency, ordered gradient, or transition. | Line/step plot, ordered scatter, profile, or small multiples. |
| Show how groups differ | Category plus measure | Reveal group differences with sample size and variability visible. | Dot/interval, box/violin plus raw points, grouped bar only when appropriate. |
| Show variable relationships | Two or more continuous measures | Reveal association, gradient, nonlinearity, or heterogeneity. | Scatter, density scatter, faceting, or fitted curve with caveats. |
| Show uncertainty | CI, SD, SEM, bootstrap, ensemble, or posterior summaries | Reveal precision, spread, or robustness of estimates. | Error bars, intervals, ribbons, uncertainty maps, or side panels. |
| Show model reliability | Observed, predicted, residual, benchmark, or validation fields | Reveal performance, bias, calibration, or method differences. | Observed-vs-predicted, residuals, calibration, Taylor diagram. |
| Show statistical evidence | p values, adjusted p values, effects, ranks, test labels | Reveal effect size, significance, or prioritized discoveries. | Volcano, Manhattan, forest, ranked dot plot, or annotated comparison. |

Use the data affordances to propose goals:

| Data affordance | Good figure goal | Typical implementation |
|---|---|---|
| Coordinates or geometries | Show spatial distribution, regional pattern, or study-area coverage. | Map with color/size encodings and light context layers. |
| Time or ordered sequence | Show temporal pattern, event frequency, seasonal structure, or ordered change. | Line/step plot, counts over time, or small multiples. |
| Continuous measures | Show distribution, outliers, gradients, or relationships. | Histogram/KDE/box/violin/scatter/density scatter. |
| Categorical groups | Compare groups, conditions, regions, treatments, or classes. | Dot/bar/box/violin/faceted panels with sample sizes. |
| Spatial plus numeric attributes | Show where values are high/low and how the numeric structure is distributed. | Map plus distribution or relationship diagnostic. |
| Raster or gridded fields | Show spatial field, anomaly, gradient, or mask/coverage. | Map, pcolormesh, contourf, or raster summary panels. |
| Model outputs | Show performance, residuals, calibration, or method comparison. | Observed-vs-predicted, residual plot, Taylor diagram. |
| Statistical result columns | Show effect size, significance, or ranked discoveries. | Volcano, Manhattan/GWAS, forest, or ranked dot plot. |
| Uncertainty columns | Show estimate plus uncertainty, not just point values. | Error bars, intervals, ribbons, or uncertainty panels. |

Return a short recommendation block before coding when the choice is not obvious:

```text
Data read: [file type, rows/features, key variables, relevant ranges, caveats].
Plausible research questions:
1. [Question] -> role [figure role]; evidence [variables/pattern]; limit [what it cannot prove].
2. [Question] -> role [figure role]; evidence [variables/pattern]; limit [what it cannot prove].
Recommended figure goal: [goal].
Recommended role: [data overview/main result/relationship/method validation/sensitivity/diagnostic].
Reason: [why it uses the data well and keeps inference honest].
Action: [proceed under stated assumption, or ask one concrete confirmation question].
```

For example, only when the user supplies a point-event GeoJSON and asks the skill to
choose the figure goal, a defensible option is an exploratory multi-panel figure with
a global event map and one requested/recommended distribution panel. If the user has
already asked for a map, keep the default to one map. This distinction prevents a
data-affordance example from silently expanding an explicit task.

Before coding, record a compact coverage table in transient planning state or the
temporary QA harness, never in the delivered plotting script:

| Requested judgment | Request span | Evidence kind | Panel | Channels | Limit |
|---|---|---|---|---|---|
| One atomic reader question | Verbatim text | Spatial pattern, distribution, comparison, trend, relationship, uncertainty, diagnostic, or other | One or more live panel roles | Active encoding keys | What the evidence cannot prove |

Position and length are the default evidence for precise comparison and distribution.
Area or color alone may support lookup or spatial gradients, but needs a
request-specific justification when used as the only evidence for a distribution,
comparison, or trend.

Use contract version 2 for new figures. Define this object only in the temporary QA
harness or transient working state:

```python
EXPECTED_CONTRACT = {
    "contract_version": 2,
    "figure_purpose": "...",
    "reader_judgment": "...",
    "requested_judgments": [
        {
            "id": "stable_id",
            "request_span": "verbatim text from the request",
            "question": "one atomic reader question",
            "evidence_kind": "distribution",
            "fields": ["source_or_derived_field"],
        }
    ],
    "target_filter": None,
    "panels": ["main"],
    "encodings": {"main.x": "source_or_derived_field"},
    "evidence_map": {
        "stable_id": [
            {
                "panel": "main",
                "channels": ["main.x"],
                "justification": "",  # non-empty only for a real task constraint
            }
        ]
    },
    "outputs": ["python", "pdf", "tiff"],
    "target_policy": {
        "formats": {"value": ["python", "pdf", "tiff"], "source": "user"},
        "width_mm": {"value": 183, "source": "size_fallback:nat2"},
        "height_mm": {"value": None, "source": "automatic"},
        "tiff_dpi": {"value": 600, "source": "raster_fallback"},
    },
}
```

The plotting module may expose this normalized contract for the temporary harness.
Do not include the verbatim full request in the delivered script.

## Layout audit for multi-panel figures

Before coding a multi-panel figure, classify each panel's natural aspect:

- wide/short: global maps, timelines, long heatmaps, stratigraphic sections;
- square/moderate: correlation matrices, PCA/UMAP, ordinary scatter plots;
- tall/narrow: profiles, depth plots, vertical distributions, bar charts with many groups.

Do not place panels with strongly incompatible natural aspect ratios in the same
row unless the final render is explicitly checked. Prefer stacked layouts when a
global map is paired with a Cartesian diagnostic, profile, or depth plot.

For map + diagnostic figures:

- global map + relationship plot: prefer stacked layout;
- regional map + compact inset/diagnostic: side-by-side may work;
- several comparable maps: grid layout is appropriate.

The first render must leave UltraPlot's adaptive spacing and margins untouched. Do
not pass `innerpad`, `outerpad`, `panelpad`, `wpad`, `hpad`, `pad`, `hspace`,
`wspace`, `space`, or fixed margins speculatively. Also keep `share` and `span` at
their defaults unless incompatible units, variables, or projections make sharing
misleading. Add one targeted override only after the final draw reveals a concrete
defect or the target explicitly requires it, and retain a short reason for semantic
QA. Do not add subplot titles by default.

## Data inspection

Profile first when the user says "visualize this", the data columns are unknown, or
several chart families are equally plausible.

Inspect:

- rows, columns, dtypes, missingness, duplicates, and suspicious ranges;
- numeric, categorical, datetime, text, coordinate, identifier, and uncertainty columns;
- group sizes, low-n groups, outliers, and whether the table is raw or summarized;
- whether units, transformations, thresholds, or baselines are explicit;
- whether any column names indicate ID/sample/gene/station/accession fields that
  should not be treated as numeric measures.

Use `scripts/profile_data.py` for CSV/TSV/Excel files when it saves time:

```bash
python scripts/profile_data.py data.csv --json profile.json
```

For geospatial vector files such as GeoJSON, shapefiles, and GeoPackage layers,
`profile_data.py` is not the right first tool. Inspect the file format directly:

- geometry type and feature count;
- CRS, coordinate bounds, and longitude/latitude validity;
- key attribute fields used for color, size, groups, filters, or labels;
- unexpected feature classes, empty geometries, invalid geometries, and mixed
  geometry types.

Use `geopandas`, a lightweight GeoJSON read, or the project's existing GIS helper
only as much as needed to choose the map, validate coordinates, and define the plot
contract. Do not convert spatial files to tables merely to satisfy the tabular
profiler unless the intended figure is non-spatial.

For event catalogs or mixed-record spatial files, class inspection is mandatory.
Enumerate likely type/class/category/status fields and their counts. If the requested
target is a subset, filter explicitly and report input, retained, and excluded counts;
do not infer that every feature is the target from the filename.

Ask only when the answer changes the figure materially. Prefer 1 to 3 focused
choices:

- What should be compared: groups, conditions, time, spatial pattern, or variables?
- Should groups be overlaid or separated into panels?
- Is the target a manuscript, target journal, poster, supplement, or reviewer revision?

## Column semantics

Before plotting, identify these roles when present:

- measure columns: continuous values to encode on axes, color, size, or panels;
- grouping columns: categories, conditions, treatments, batches, clusters, or regions;
- ordering columns: time, sequence, depth, genomic position, or ordered factors;
- coordinate columns: longitude/latitude, projected x/y, row/column indices, or raster grids;
- uncertainty columns: SD, SEM, CI bounds, percentile bounds, bootstrap bounds, or model intervals;
- statistical result columns: p value, adjusted p value, q value, effect size, rank, or score;
- identifier columns: sample IDs, gene IDs, subject IDs, station IDs, accession IDs, or row numbers.

Do not use identifier columns as numeric variables unless the user explicitly asks.

## Encoding audit

Before plotting, list each requested visual channel and the variable it must encode.
After plotting, record the implemented mapping and compare the two. Confirm no variable
is encoded twice by accident, every guide explains one active encoding, and every
explicit user mapping is preserved. The channel-by-channel table and rules are in
`references/principles.md` (Encoding audit); apply them during both contract setup and
final task-semantic QA.

## Fail-fast validation

Do not silently plot invalid scientific data. Raise or report a clear issue when:

- required columns are missing;
- p values or adjusted p values are outside `[0, 1]`;
- log-scale variables contain non-positive values;
- longitude/latitude values are outside valid ranges;
- group labels are empty or have unintended whitespace/case duplicates;
- all values are missing or constant for the intended measure;
- units, transformations, or baseline periods are required for interpretation but absent.

## Chart chooser

| Data/message | Good default |
|---|---|
| Ordered trend | line, step, area, or small multiples |
| Numeric relationship | scatter, density scatter, fitted line, or facets |
| Category comparison | dot/point, bar, grouped bar, paired/slope chart |
| Distribution | raw points plus box/violin, histogram, KDE, ridgeline |
| Matrix or gridded field | heatmap, pcolormesh, contour, contourf, imshow |
| Correlation matrix | diverging heatmap centered on 0 with labels if readable |
| Map or raster | Cartopy/UltraPlot map axes with projection and transform |
| Model diagnostics | residual, calibration, Taylor, observed-vs-predicted |

Intervene before coding for risky designs: mean-only bars for small samples,
truncated bar baselines, gratuitous dual axes, pie charts with many categories,
line charts for unordered categories, rainbow colormaps, color-only grouping, and
dense opaque scatter.

## Plot-prep vs preprocessing

Keep light figure-specific shaping in the plotting script:

- select/rename columns;
- sort for display;
- pivot wide/long for a chart;
- bin values for a histogram;
- compute simple plotted summaries such as mean, SEM, percentiles, or `-log10(p)`;
- create display labels, palette mappings, and panel order.

Split into two scripts when the work is real data processing:

- cleaning messy raw files;
- merging sources;
- QC filtering;
- heavy aggregation;
- normalization;
- model fitting;
- reusable intermediate tables.

In that case, write:

- `preprocess.py`: reads raw data, validates it, writes a checked intermediate, and
  prints a short data-quality summary.
- `plot.py`: reads the intermediate and only builds the figure.

## Script style

Write runnable top-to-bottom scripts, not fragments. Put every user-tunable value in
a top `CONFIG` block:

- input/output paths;
- column names and units;
- filters, thresholds, group order;
- palette/colormap/norm limits;
- marker sizes, line widths, alpha;
- target journal or explicit physical size, projection, DPI, and export formats;
- expected final width/height and QA tolerances when the target constrains them.

Keep production code linear: load, validate or prepare, create `uplt.subplots(...)`,
plot, format, add every artist and guide, force a final draw, and return only ordinary
objects useful to normal callers, such as the figure, axes, processed data, and
descriptive statistics. Do not make the delivered script import Skill helpers, declare
QA contracts, construct evidence registries, or emit QA reports. The temporary harness
adapts those ordinary return values for validation.

Use two execution stages. The temporary draft stage runs live semantic/render QA and
creates only a 150-200 dpi preview. After it passes, the production stage writes the
target-required files once and runs final live plus artifact QA.

## Semantic, render, and export QA

Use `scripts/figure_qa.py` as the stable public facade. It keeps four gates separate:
task semantics, in-memory render geometry, saved artifacts, and final-scale visual
inspection. Passing a later gate never closes an earlier defect.

Run `python scripts/figure_qa.py --example` for the canonical temporary-harness call.
The harness defines one distilled `EXPECTED_CONTRACT` that includes `figure_purpose`
and `reader_judgment` alongside panel roles, mappings, filters, counts, and outputs. It
also owns the user's verbatim `REQUEST_TEXT` and constructs live evidence from the
delivered module's ordinary plotting objects and actual data. Never place these QA
objects in the plotting module, reconstruct a second expected contract, or copy
expected fields into actual evidence.

### Output lifecycle

Separate persistent outputs from internal evidence:

```python
deliverables = {
    "python": script_path,
    "pdf": pdf_path,
    "tiff": tif_path,
}

with qa_workspace() as qa_dir:
    qa_artifacts = [qa_dir / "draft-preview.png"]
```

`deliverables` contains only requested scripts, production figures, data products,
and reports. `qa_artifacts` contains temporary previews, helper reports, probes, logs,
per-task caches, bytecode, and any materialized harness source. The facade rejects
overlap and can require every QA path to stay under `qa_root` and outside
`delivery_dir`. It also parses existing Python deliverables and rejects QA-only
contracts, evidence registries, Skill QA module imports, and Skill QA calls. Ordinary
data validation and scientific summaries remain valid production code. If the user
explicitly requests a QA report, place that report in `deliverables`. The version-keyed
environment capability cache is separate user-cache state and never a deliverable.

### Draft stage

Build the complete figure at its final physical size with every artist, legend,
colorbar, panel letter, and annotation. In the temporary harness, set `REQUEST_TEXT`
to the original user request, then call `audit_draft_figure(...)` with:

- the single expected contract and the harness-owned original request text;
- distinct live axes for every panel role;
- actual field constants, artists, and plotted source values;
- target-filter counts from the retained data;
- planned deliverable paths, even though production files do not exist yet;
- relevant size, shared-color, and continuous-color diagnostic specifications;
- an empty layout-override reason mapping unless a real override was retained.

Draft semantic QA does not require final files to exist. Render QA forces the draw,
measures the post-layout canvas, discovers every legend, and checks geometry and
semantic mappings. Its default report summarizes large arrays with counts, ranges,
maximum errors, and at most five mismatches; use `include_raw_arrays=True` only for a
targeted diagnosis and write detailed reports into the QA workspace.

For a continuous color variable whose distribution may affect readability, pass the
semantic values and live mappable without inventing a universal threshold:

```python
continuous_color_encodings = [
    {"name": "quantity", "values": source_values, "mappable": mappable}
]
```

Inspect the reported data quantiles, normalized quantiles, and middle-range spans. Add
an explicitly labeled diagnostic threshold only when the task or domain policy needs a
machine warning.

Create a 150-200 dpi PNG with `save_draft_preview(...)` in that workspace and inspect
it at the final physical proportion. Keep the same data, fonts, physical dimensions,
projection, guides, and layout as the final figure; only preview raster DPI is reduced.

### Final stage

After draft gates pass, save the target-required production formats once. Then call
`audit_submission_figure(...)` with the same contract and live evidence, real
deliverable paths, and an artifact policy assembled from the resolved setting sources.
When the resolved outputs use the Skill-default PDF/TIFF artifact settings, copy the
standalone exporter from `references/scientific-figures.md` into the delivered script
and use `publication_fallback_policy(expected_width_mm=TARGET_WIDTH_MM)` in the
temporary QA harness. The width argument is required and must match the intended
post-draw width. This policy requires PDF plus 600 dpi opaque RGB lossless-LZW TIFF,
embedded fonts, no Type 3 fonts, and no artifact warnings. For other requested format
sets, build the equivalent target-specific policy without adding unrequested formats.
Pass a requested preview format through `additional_formats`, but do not require it by
default.

The final facade call reruns semantic/render checks with required real files and uses
`check_figure.audit_files(...)` for page/image dimensions, effective DPI, PDF
fonts/resources/transparency, TIFF mode/compression, and SVG/EPS policy. The fallback
policy passes `require_tiff_mode="RGB"` and
`require_tiff_compression="lzw"`; the equivalent CLI flags are
`--require-tiff-mode RGB` and `--require-tiff-compression lzw`. A named target
overrides fallback format, color-mode, alpha, compression, and font rules. Use `183`
only when `nat2` or an explicit 183 mm target is actually intended.

Call `require_ok(report)` after each stage. It raises a compact error and prevents a
failed in-memory gate from appearing as a successful shell command. Use
`compact_summary(report)` for normal terminal output; full child reports remain
available for targeted debugging without printing every plotted value.

### Hard defects and stopping rules

Treat these as hard defects requiring fix -> draw -> QA again:

- missing requested judgments, request spans, evidence-map bindings, or setting sources;
- missing/extra/wrong panel roles, target filters, counts, variables, units, or outputs;
- an unrequested subplot title or unjustified adaptive-layout override;
- final physical size outside target tolerance;
- legend collision, clipping, or frame-containment failure;
- semantic scatter-size or shared-color mapping mismatch;
- hidden data, unreadable labels, misleading statistical semantics, or guides covering data;
- target format, DPI, font, transparency, color-mode, compression, or file-limit failure.

Inspect text, tick labels, panel letters, annotation placement, colorbar semantics,
accessibility, overplotting, visual balance, and excessive empty space. Hard defects
must close. Soft layout issues and benign warnings get one targeted refinement after
hard gates pass. A final `final_qa_passed` summary means: perform one final-scale
visual inspection, clean temporary artifacts, and deliver. Do not continue open-ended
library-source inspection or warning elimination.

### Capability checks and cache

`scripts/ultraplot_compat.py --strict` checks environment-level behavior such as
semantic scatter size, `sizelegend`, physical unit specs, legend discovery, and
post-draw journal size. Successful checks are cached by executable, package versions,
platform, and helper hash. Use `--refresh-cache` after suspicious API behavior. The
cache never replaces per-figure QA. Run `figure_qa.py --self-test` after helper or
environment changes, not as a per-figure gate.

Finally inspect the saved rendering visually at final physical scale. Repeat the
full-resolution export only when a final artifact or visual hard gate fails.

## Final response

Use the final successful implementation/artifact report as the source of truth. Read
counts, filters, mappings, panel roles, dimensions, formats, and DPI from that report
and the saved files; do not reuse numbers from an earlier render iteration.

Report concrete choices, not generic claims:

- what preprocessing or plot-prep was done;
- final table shape if data were processed;
- chart type and why it matches the message;
- target requirement or fallback profile, plus measured final width and height after draw and from saved artifacts;
- font/base size if changed;
- palette/colormap and scale;
- output paths, formats, and DPI;
- validation or export-check results;
- tradeoffs such as shared axes, log scale, omitted uncertainty, rasterized layers,
  or overplotting controls;
- a short caption-ready note with thresholds, uncertainty definition, sample size,
  baseline, coordinate reference system, or test/correction when relevant.
