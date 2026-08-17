# UltraPlot recipes — good-default figures

Copy, adapt, render. These recipes are scientific-encoding and API skeletons,
not style specifications. They use the skill default `journal="nat2"` and
`EXPORT_DPI = 1000`; otherwise they inherit UltraPlot's effective visual
defaults and leave spacing to its automatic layout. All assume
`import numpy as np; import ultraplot as uplt`.

## 1. Multi-line comparison with a legend
```python
fig, ax = uplt.subplots(journal="nat2")
ax.plot(x, Y, labels=["control", "treatment", "baseline"])
ax.legend()
ax.format(xlabel="time (s)", ylabel="signal (mV)")
fig.save("lines.pdf", dpi=EXPORT_DPI)
```

## 2. Small-multiples grid with shared axes + panel letters
```python
fig, axs = uplt.subplots(ncols=3, nrows=2, journal="nat2")
for ax, y in zip(axs, series):
    ax.plot(x, y)
axs.format(abc="a.", abcloc="ul",
           xlabel="x (units)", ylabel="y (units)",
           toplabels=("Low", "Mid", "High"), leftlabels=("Run 1", "Run 2"))
```

## 3. 2D field with a shared outer colorbar
```python
fig, axs = uplt.subplots(ncols=2, journal="nat2")
for ax, field in zip(axs, fields):
    m = ax.pcolormesh(lon, lat, field, levels=shared_levels, extend="both")
axs.format(abc="a.", abcloc="ul", xlabel="x", ylabel="y")
fig.colorbar(m, label="T (K)")  # one scientifically shared scale for the row
```

## 4. Signed / anomaly field (diverging, centered at zero)
```python
fig, ax = uplt.subplots(journal="nat2")
m = ax.contourf(anomaly, levels=uplt.arange(-6, 6, 1), extend="both")
ax.colorbar(m, label="anomaly (K)")
ax.format(xlabel="lon", ylabel="lat")
```

## 5. Correlation matrix as a labeled heatmap
```python
fig, ax = uplt.subplots(journal="nat2")
m = ax.heatmap(corr, vmin=-1, vmax=1, labels=True,
               labels_kw={"precision": 2})
ax.format(xticklabels=names, yticklabels=names)
ax.colorbar(m, label="Pearson r")
```

## 6. Scatter with a size legend + color legend (semantic keys)

```python
fig, ax = uplt.subplots(journal="nat2")
m = ax.scatter(df.x, df.y, c=df.value, s=df.pop)
ax.colorbar(m, label="value")
ax.sizelegend([10, 50, 200], labels=["S", "M", "L"], title="population")
ax.format(xlabel="x", ylabel="y")
```

## 7. Distribution: box/violin with shaded percentile bands on a line

```python
fig, axs = uplt.subplots(ncols=2, journal="nat2", share=False)
axs[0].violin(samples)
axs[0].format(xticklabels=groups)
# line with mean + shaded IQR straight from raw samples
axs[1].plot(x, runs, mean=True, shadedata=True)
axs.format(abc="a.", abcloc="ul")
```

## 8. Map (cartopy) with an anomaly field

```python
import cartopy.crs as ccrs

fig, ax = uplt.subplots(proj="pcarree", journal="nat2")
m = ax.pcolormesh(lon, lat, data, levels=uplt.arange(-4, 4, 0.5),
                  extend="both", transform=ccrs.PlateCarree())
ax.format(coast=True, borders=True, grid=True,
          lonlabels="b", latlabels="l")
ax.colorbar(m, label="anomaly")
```

## 9. Twin axes (two y-scales, honestly labeled)

```python
fig, ax = uplt.subplots(journal="nat2")
ax.plot(x, temp, color="rose")
ax.format(ylabel="temperature (°C)", ycolor="rose", xlabel="day")
axr = ax.alty(ylabel="precipitation (mm)", ycolor="denim")
axr.bar(x, precip, color="denim")
```

## Final render
Save and inspect every figure using its final filenames:

```python
EXPORT_DPI = 1000
fig.save("figure.pdf", dpi=EXPORT_DPI)
fig.save("figure.png", dpi=EXPORT_DPI)
```

Replace `figure` with the task's final basename and re-render corrections to the
same paths. Do not create separate check, draft, or test copies. Inspect both
final files internally. Keep output-file and geometry validation code out of the
delivered plotting script.
