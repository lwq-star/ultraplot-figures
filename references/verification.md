# Internal figure verification

This reference is for agent-side QA. It does not expand the retained task
artifact allowlist. Never copy its diagnostic procedures into delivered plotting
or preprocessing scripts, and never retain a verification report by default.

## Verification workflow

1. Render to the final requested paths with final labels, typography, guides,
   limits, and geographic extent.
2. Inspect the vector and raster results visually.
3. Check saved-file dimensions and resolution with a skill-bundled tool or
   temporary task code.
4. For picture arrays, spanning Axes, mixed GeoAxes and CartesianAxes, fixed
   data aspects, outer guides, or panel identifiers, inspect geometry with the
   live final renderer even when visual inspection initially appears acceptable.
5. Correct the production code, overwrite the final outputs, and repeat.
6. Remove diagnostic artifacts created by the current task.
7. Confirm that every retained file is allowlisted and semantically necessary.

Use `scripts/validate_outputs.py` for deterministic PDF and PNG checks when its
dependencies are available. It prints results to stdout and writes no report.

## Scientific and text checks

Confirm that:

- the selected marks and encodings answer the intended scientific comparison;
- units, observation level, transformations, and uncertainty are represented
  honestly;
- bar and area baselines and diverging neutral values are scientifically valid;
- required axis labels, guide labels, tick labels, geographic coordinate labels,
  and annotations remain visible and correct;
- no figure-level or subplot-level title is present unless directly requested;
- panel identifiers and grid-edge labels serve structural rather than descriptive
  title roles;
- required glyphs, symbols, Unicode minus signs, and math text render correctly.

## Panel and layout checks

Count only independent main Axes when deriving expected panel identifiers. Use
the documented numbering semantics and public `Axes.number` values. Confirm one
expected identifier per main Axes, correct ordering, upper-left placement,
canvas containment, and clearance from ordinary annotations and insets.

For the complex layouts listed in the verification workflow, inspect with the
final renderer:

- GridSpec slot geometry;
- visible axes frame geometry;
- decorated tight boundaries;
- pairwise decorated-content overlap;
- canvas containment;
- fixed-aspect slot use;
- frame alignment;
- outer-guide size and separation.

Runtime bbox measurements are temporary diagnostics. Do not return their helper
functions, raw measurements, nested dictionaries, thresholds, or JSON output in
the user's plotting script.

A successful export and non-overlapping bounding boxes are not sufficient by
themselves. Reject a layout when fixed-aspect slot waste creates an unexplained
composition-wide blank band, a dominant panel is materially reduced, or the
intended comparison is unreadable at final physical size.

## Output-file checks

Confirm that:

- every requested final file exists and is non-empty;
- all final save calls use the selected explicit `EXPORT_DPI`;
- PDF physical dimensions preserve the chosen size authority;
- PNG pixel dimensions and resolution metadata agree with physical dimensions
  and export DPI within format rounding tolerance;
- no `bbox_inches="tight"` changed the nominal physical canvas;
- vector content remains vector except for intentionally rasterized dense marks
  or gradients;
- no draft, check, screenshot, report, cache, or temporary file remains in the
  retained set.

For `journal="nat2"`, require a saved PDF width of 183 mm within 0.2 mm. With the
default `EXPORT_DPI = 1000`, compare PNG dimensions against the PDF page size
rather than trusting only code-level sizing.

## Geospatial checks

When applicable, confirm that:

- source CRS was inspected and the display policy is explicit;
- the displayed extent matches the study area;
- north-south orientation is correct;
- raster and vector boundaries align;
- NoData regions do not receive scientific colors;
- geographic axes use degree-formatted longitude and latitude for the default
  EPSG:4326 display;
- display-only transformed data were not used for analytical calculations;
- no temporary reprojection remains in the retained set.

## Allowed runtime assertions

Delivered code may fail clearly for missing input files, missing required
columns, empty data, non-finite plotted values, invalid CRS or units at the stage
that owns them, and scientific invariants required for interpretation.

Do not retain assertions that merely re-prove an upstream calculation, enforce a
dataset-specific aesthetic result, inspect the renderer or output file, audit the
source text, or inventory the task directory. Those checks belong here or in a
skill-bundled tool.
