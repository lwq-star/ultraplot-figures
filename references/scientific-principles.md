# Scientific plotting principles

Use this checklist before writing plotting code. The purpose is to keep the figure tied to the research question and to make every data transformation reproducible.

## 1. Clarify the figure's purpose

Before choosing a chart, state:

- **Scientific question:** What comparison, relationship, pattern, or mechanism is being investigated?
- **Intended message:** What should the reader be able to see or compare after viewing the figure?
- **Evidence:** Which variables, units, groups, observation units, and sample sizes support that message?
- **Output context:** Which journal or medium, column format, final file format, and physical width apply?

Do not begin from a preferred chart type. Begin from the scientific question and the comparison the reader must make.

A useful one-sentence brief is:

> Show **[variable or estimate]** across **[groups, time, or space]** so the reader can evaluate **[scientific comparison]**.

## 2. Define the output size

Use one width authority. Honor an explicitly requested journal preset first, or an explicitly requested total physical figure width second. If neither is supplied, use UltraPlot's `journal="nat2"` default for this skill (Nature two-column, 183 mm). Do not infer a different journal, approximate a preset with a nearby manual width, or combine `journal` with a competing `figwidth` or `refwidth`.

Record the sizing authority, expected physical width, final format, and whether exact saved dimensions are required. `refaspect` may still describe subplot geometry without competing with the total-width authority.

## 3. Inspect the data before plotting

Check the available files and confirm column meanings, units, missing values, duplicates, ranges, grouping, pairing or repeated measurements, and any transformations already applied. Do not silently remove observations, aggregate replicates, normalize values, or compute statistics merely to make plotting easier.

For geospatial figures, also confirm the source CRS, coordinate units, bounds, affine transform, resolution, grid orientation, and NoData definition. Never infer WGS84 from coordinate appearance or missing CRS metadata.

## 4. Decide whether data processing is required

Create a separate data-processing stage when the task requires substantive operations such as:

- cleaning invalid or missing records;
- filtering observations;
- joining multiple data sources;
- reshaping data for analysis;
- aggregating repeated measurements;
- normalization or transformation;
- deriving variables;
- computing statistics, estimates, or uncertainty intervals.

Simple display-only choices such as label wording, category order, marker style, or axis formatting can remain in the plotting script.

For geospatial figures, an EPSG:4326 transformation created only for final display may remain in the plotting script. It is a plotting-preparation artifact, not a processed scientific dataset. Any transformed grid used for measurement, comparison, or statistics must be created in the processing stage.

## 5. Keep processing and plotting separate

When processing is required, use two scripts:

- `process_data.py`: reads the raw input, validates and transforms it, and writes a processed data file. It should not create the final figure.
- `plot_figure.py`: reads the processed data file and creates the figure. It should not contain hidden cleaning, aggregation, normalization, or statistical analysis.

When multiple figures are requested, use one independently runnable plotting entry script for each scientifically distinct figure. A single parameterized entry script may generate several figures only when their layout, scientific meaning, and processing logic are the same and they differ only by inputs, regions, years, labels, or similarly simple parameters. Put genuinely shared rendering utilities in a small helper module instead of combining unrelated figures in one script.

Write the processed data to disk in an appropriate format such as CSV, Parquet, NetCDF, or another format suited to the data. Use explicit input and output paths, deterministic operations, and fixed random seeds where randomness is unavoidable.

A typical delivery structure is:

```text
process_data.py
plot_figure.py
processed_data.csv
figure.pdf
figure.png
```

Use names and formats appropriate to the task; the separation of responsibilities is the important requirement.

## 6. Required deliverables

When preprocessing is required, provide:

1. the data-processing script;
2. the plotting script;
3. the processed data file used by the plotting script;
4. the rendered figure in the requested final format, plus a preview when useful;
5. a brief note describing important assumptions, transformations, sizing authority, measured output dimensions, and any manual spacing overrides.

When preprocessing is not required, do not create an empty processing script. Provide the plotting script, rendered figure files, and identify the input data used.

For multiple figures, also provide a manifest mapping each figure to its plotting entry script, processed inputs, and rendered outputs.

## 7. Verify the scientific message

Before delivery, render and inspect both the vector output and a raster preview. Confirm that the chosen encoding supports the intended comparison, axes and units are clear, transformations and uncertainty are labeled, colors are consistent with the variable type, and the figure remains legible at its intended size. Check the saved PDF media box rather than trusting only the size requested in code. For `journal="nat2"`, the PDF must be 183 mm wide within 0.2 mm. Do not use `bbox_inches="tight"`, because post-render cropping can change the physical page size. The final figure should answer the stated scientific question without relying on undocumented processing or layout overrides.
