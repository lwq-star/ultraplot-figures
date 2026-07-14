# Vector maps and event catalogs

Read this file for GeoJSON, shapefile, GeoPackage, point-event, station, trajectory,
or other vector-map tasks. It owns vector inspection, target filtering, CRS,
projection, dateline handling, context layers, and semantic point encodings.

## Inspect before plotting

Inspect spatial files directly rather than passing them to the tabular profiler:

- feature count, geometry type, empty geometries, mixed geometry classes, and validity;
- declared CRS, coordinate bounds, and plausible longitude/latitude ranges;
- attributes used for target filtering, color, size, categories, labels, or time;
- likely type/class/category/status fields and their value counts.

For event catalogs, class inspection is mandatory. When the requested target is a
subset, filter explicitly and report input, retained, excluded, and
excluded-by-class counts. Never infer event identity from the filename alone.
Filtering a few unrelated classes is plot preparation; reusable spatial joins,
reprojection, clipping, or aggregation belongs in preprocessing.

Separate an explicit chart constraint from an evidence goal. "Make one event map" is
a closed single-map request. "Show spatial distribution and the characteristics of
numeric event attributes" leaves the layout open: map position can answer where, while
requested marginal distributions usually need position/length or density evidence in
one or more supporting panels. Record this distinction in `requested_judgments` and
`evidence_map`; do not add panels that serve no requested judgment.

## CRS, projection, and longitude

Keep display projection separate from source CRS:

- axes projection: for example `"robin"`, `"moll"`, `"cyl"`, `"npstere"`, or
  `"spstere"`;
- data transform: commonly `ccrs.PlateCarree()` for longitude/latitude arrays.

Pass `transform=` explicitly when code may be ported, mixed with projected data, or
reviewed by collaborators. Validate latitude in `[-90, 90]`; normalize longitude to
either `[-180, 180]` or `[0, 360]`. For global event maps, inspect density near the
map seam before selecting the central longitude. Regional maps need a meaningful
extent and enough context to identify the study area.

| Task | Starting projection |
|---|---|
| Global overview | Robinson or Mollweide |
| Simple longitude/latitude diagnostic | Cylindrical/PlateCarree |
| Polar region | North/south polar stereographic |
| Regional study | Known local projection, otherwise a clear lon/lat extent |

## Map axes and context

Create geographic axes with UltraPlot and Cartopy, then let UltraPlot perform the
first layout:

```python
import cartopy.crs as ccrs
import ultraplot as uplt

fig, ax = uplt.subplots(proj="robin", journal=JOURNAL)
ax.format(coast=True, lonlines=60, latlines=30, lonlabels="b", latlabels="l")
```

Start with GeoAxes `format()` options. Do not manually style gridlines, boundaries,
spacing, or margins in the first render unless the target venue requires it.

Use context layers only when they support interpretation:

- coastlines are useful natural reference for global or continental processes;
- borders belong on national, policy, population, exposure, or country-comparison maps;
- rivers and lakes belong on hydrology, water, riparian, wetland, or station-context maps;
- local study boundaries, basins, protected areas, faults, roads, and transects require
  authoritative user-provided vectors when they materially affect interpretation.

Do not fill land or ocean by default. Keep reference vectors thin, muted, below the
primary data, and unfilled unless polygon fill encodes a variable.

## Semantic point size and color

Pass original semantic values to both the scatter and size legend. Reuse the same
source domain and output area range:

```python
DATA_CRS = ccrs.PlateCarree()
values = data["magnitude"].to_numpy()
levels = [5, 6, 7]

points = ax.scatter(
    data["lon"],
    data["lat"],
    s=values,
    smin=8,
    smax=80,
    c=data["depth_km"],
    cmap="viridis",
    transform=DATA_CRS,
    rasterized=True,
    colorbar="b",
    colorbar_kw={"label": "Depth (km)"},
)
handles, labels = ax.sizelegend(
    levels,
    values=values,
    smin=8,
    smax=80,
    add=False,
)
legend = ax.legend(
    handles,
    labels,
    title="Magnitude",
    loc="r",
    frame=False,
    borderpad="4pt",
    handletextpad="6pt",
    labelspacing="6pt",
    columnspacing="8pt",
)
```

Do not pre-scale values and then let UltraPlot scale them again. For deliberately
precomputed point areas, use `absolute_size=True` consistently and construct legend
handles from the same area function. A mapping mismatch, internal legend collision,
or frame-containment failure is a hard defect. Run the stable draft/final QA entry in
`scripts/figure_qa.py`; detailed size semantics live in `references/ultraplot-api.md`.

Before assigning a continuous attribute to color, inspect its finite range and
quantiles, then inspect those quantiles after applying the live normalization. A
technically valid colorbar can still provide weak evidence when most observations
occupy a narrow part of the scale. Pass values plus the live norm or mappable through
`continuous_color_encodings` so render QA records data and normalized quantiles. If
compression weakens a requested judgment, use a documented transform with data-unit
ticks, defensible domain bins, complementary position/length evidence, or a concise
request-specific justification. Do not use quantile normalization by default because
it changes the visual meaning of numeric distance.

## Submission QA

- source CRS and display projection are explicit;
- coordinate ranges and dateline behavior are correct;
- target and non-target classes are counted and the requested filter is applied;
- panel roles and position/color/size mappings match the task contract;
- every requested judgment is bound to evidence strong enough for the intended reading;
- guides include quantities and units and do not cover the data;
- context vectors support interpretation without dominating the primary data;
- dense scatter may be rasterized while text, axes, coastlines, and guides stay vector;
- post-draw size and saved-artifact dimensions satisfy the target profile.
