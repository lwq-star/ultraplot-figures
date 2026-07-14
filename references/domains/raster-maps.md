# Raster, gridded, and climate maps

Read this file for GeoTIFF, NetCDF, xarray, DEM, land-cover, remote-sensing,
climate/ocean/atmosphere fields, masks, anomalies, and other gridded spatial data.

## Inspect the grid

Before plotting, record:

- array dimensions, coordinate names/order, units, missing/nodata values, and masks;
- CRS, transform, bounds, resolution, pixel orientation, and longitude convention;
- regular image geometry versus coordinate-defined, nonuniform, or curvilinear cells;
- whether values are continuous magnitudes, signed anomalies, or real classes;
- time, season, ensemble, scenario, and anomaly-baseline semantics when present.

Put heavy clipping, reprojection, resampling, masking, merging, and reusable
aggregation in preprocessing. Preserve the method and interpolation/resampling choice.

## Choose the plotting method from grid geometry

Use `imshow` for regular image-like rasters represented by a 2-D array plus an
`extent`. Pass the source CRS with `transform=...`, keep `origin` consistent with the
raster orientation, and use `interpolation="nearest"` for categorical rasters.

Use `pcolormesh` when each cell needs explicit coordinates: nonuniform lon/lat,
curvilinear grids, xarray/NetCDF model output, cell-edge coordinates, or projected
cell geometry. Use `shading="auto"` unless edges are managed explicitly. Do not
choose `pcolormesh` merely because the data are a raster.

Use `contour` or `contourf` when isolines or filled intervals are scientifically
meaningful. Do not convert a continuous field into arbitrary classes merely to make
the colorbar look simpler.

```python
mesh = ax.pcolormesh(
    lon,
    lat,
    field,
    cmap="viridis",
    discrete=False,
    shading="auto",
    transform=ccrs.PlateCarree(),
    colorbar="r",
    colorbar_kw={"label": "Variable (units)"},
)
```

For a signed anomaly, use a defensible baseline and symmetric limits when the
scientific comparison requires equal visual weight around zero:

```python
vmax = np.nanmax(np.abs(anomaly))
levels = uplt.arange(-vmax, vmax, 0.5)
ax.contourf(
    lon,
    lat,
    anomaly,
    levels=levels,
    cmap="vik",
    extend="both",
    transform=ccrs.PlateCarree(),
    colorbar="b",
    colorbar_kw={"label": "Anomaly (units)"},
)
```

## Longitude, color, and climate semantics

- normalize longitude to `[-180, 180]` or `[0, 360]` before plotting;
- add a cyclic column or use a wrapping method for global grids crossing the dateline;
- pass `discrete=False` for continuous `pcolor`/`pcolormesh` fields;
- use sequential palettes for magnitudes and diverging palettes for signed anomalies;
- reserve discrete bins for real categories, thresholds, or explicitly justified classes;
- share a colorbar only when panels represent the same quantity, units, norm, and range;
- include quantity and units in every colorbar label;
- state anomaly baseline, season, scenario, ensemble, and uncertainty definitions in
  the caption or final response when relevant.

Use map context rules from `maps-event-catalogs.md` only when vector context is needed.
Load `geospatial-setup.md` only after a geospatial import or environment failure.

## Submission QA

- CRS, transform, extent, orientation, and longitude convention are explicit and valid;
- nodata/masks are not plotted as observations;
- plotting method matches the grid geometry;
- continuous/discrete normalization matches the data semantics;
- shared panels use identical normalization and data-unit colorbar ticks;
- dense meshes are rasterized in vector exports when needed, while text and axes stay vector;
- baseline periods, units, thresholds, and uncertainty semantics are stated;
- final physical size and effective raster DPI satisfy the target profile.
