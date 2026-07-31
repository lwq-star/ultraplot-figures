# Scientific question and data-flow boundaries

Read this reference only when the scientific question, preprocessing boundary,
or design of the final processed data is unclear. The retained-file allowlist in
`SKILL.md` remains authoritative.

## Clarify the figure

Before choosing a chart, establish:

- the comparison, relationship, pattern, or mechanism being examined;
- the observation unit and the variables, units, groups, and sample supporting
  the comparison;
- the one message the reader should be able to see;
- the requested output context and physical size.

A useful brief is:

> Show **[variable or estimate]** across **[groups, time, or space]** so the
> reader can evaluate **[scientific comparison]**.

Keep this brief in working context. Do not create a report, manifest, or audit
object merely to record it.

## Inspect the input

Confirm column meanings, units, observation level, missing values, duplicates,
ranges, grouping, pairing or repeated measurements, and transformations already
applied. Do not silently remove observations, aggregate replicates, normalize
values, or calculate inferential results for plotting convenience.

For geospatial inputs, also confirm source CRS, coordinate units, bounds,
transform, resolution, orientation, and NoData metadata as applicable. Never
infer WGS84 from coordinate appearance or absent metadata.

## Decide whether preprocessing is substantive

Use a preprocessing script when an operation changes the analytical sample,
observation unit, scientific value, or result. Typical examples are:

- removing or imputing invalid observations;
- applying analytical inclusion or exclusion criteria;
- joining multiple sources;
- aggregating to a new observation level;
- normalization, calibration, or scientific unit transformation;
- deriving scientific variables or classifications;
- model fitting, hypothesis tests, uncertainty, confidence intervals, or other
  inferential results;
- spatial transformations used by measurements, comparison, or statistics.

Keep a transformation in the plotting script when it is transparent,
display-only, and easiest to understand beside the plot call. Examples include:

- selecting a display range or group explicitly requested by the user;
- category and draw order;
- a small reshape required only by the plotting API;
- label formatting, bar positions, axis limits, and marker sizes;
- simple counts, minima, maxima, medians, or quantiles calculated from the exact
  rows being plotted and used only as display annotations;
- an in-memory EPSG:4326 representation used only for display.

The presence of a pandas, xarray, NumPy, or GeoPandas operation does not by itself
require a preprocessing script. Separate the stage when the operation needs
methodological explanation, changes scientific interpretation, or should be
reused by multiple figures.

## Assign validation ownership

Validate an assumption once at the stage that owns it:

| Stage | Owns |
|---|---|
| Preprocessing | Raw schema, units, CRS, sample-changing filters, joins, analytical transformations, fitted results, and uncertainty |
| Plotting | Required final columns, non-empty inputs, finite plotted values, keys or ordering needed to map values to marks and labels |
| Internal QA | Renderer geometry, overlaps, identifiers, font rendering, PDF/PNG size and resolution, and retained-file inspection |

The plotting script should not recompute a regression, summary table, class
assignment, or exclusion audit merely to confirm the preprocessing output.
Conversely, the preprocessing script should not contain figure geometry or file
export checks.

## Design final processed outputs

Write only final processed datasets semantically consumed by the figure. Prefer
one coherent dataset when values share an observation grain. Keep separate
datasets when they represent genuinely different grains and combining them would
obscure meaning.

Every persisted field should affect the figure. Keep validation-only tables and
rejected-row details in memory. Report concise counts through stdout when useful;
do not retain another file.

Use explicit paths, deterministic operations, and a fixed random seed when
randomness is scientifically unavoidable. The final plotting script must read
the final processed results rather than repeat their substantive processing.
