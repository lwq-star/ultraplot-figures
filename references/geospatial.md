# Geospatial figure workflow

Use this reference whenever a figure contains rasters, vector boundaries,
geographic coordinates, map projections, or spatial distributions.

## 1. Inspect the source

Before plotting, confirm:

- source CRS and datum;
- coordinate units;
- raster bounds and affine transform;
- spatial resolution and grid orientation;
- NoData value or mask;
- whether coordinates describe pixel centers or pixel edges.

Do not assume that missing CRS metadata represent EPSG:4326.

## 2. Prepare the display coordinates

Use EPSG:4326 as the default plotting CRS. If the source CRS is not EPSG:4326,
create an in-memory or temporary display-only representation in EPSG:4326.

Do not overwrite the source data. Do not use the display representation for
area, distance, zonal statistics, trend analysis, or other scientific
calculations.

A display-only CRS conversion may remain in the plotting script. A CRS
transformation used by scientific analysis belongs in the processing script.

## 3. Plot with UltraPlot

Create a geographic axes using `proj="pcarree"`. Plot EPSG:4326 coordinates
and format longitude and latitude labels in degrees.

```python
import cartopy.crs as ccrs
import ultraplot as uplt

fig, ax = uplt.subplots(proj="pcarree", journal="nat2")
m = ax.pcolormesh(
    lon,
    lat,
    data,
    transform=ccrs.PlateCarree(),
    cmap="batlow",
)
ax.format(lonlabels="b", latlabels="l", grid=True)
fig.colorbar(m, loc="r", label="value")
```

`grid=True` or `grid=False` controls whether geographic gridlines are shown.
Select label sides, locators, and formatters for the scientific message, but
inherit the effective UltraPlot gridline and geographic-label appearance by
default. Omit `gridcolor`, `gridalpha`, `gridlinewidth`, `gridlinestyle`,
`labelcolor`, and `gridlabelcolor` unless an override is explicitly justified.
Do not hard-code UltraPlot's current default values. Because rc aliases and
meta-settings can couple line and label properties, inspect gridline strokes
and longitude and latitude labels separately after any justified override.

Do not specify a universal interpolation or raster-resampling method in this
skill. Let the plotting implementation choose an appropriate behavior for the
particular figure.

## 4. Verify the map

Confirm that:

- longitude and latitude labels use degree notation;
- the displayed extent matches the source study area;
- raster orientation is correct;
- administrative boundaries and rasters align;
- NoData areas are not assigned scientific colors;
- no source or analytical dataset was overwritten;
- the rendered output was visually inspected.
