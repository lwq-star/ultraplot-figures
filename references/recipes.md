# UltraPlot recipes — good-default figures

Copy, adapt, render. Each is deliberately minimal, uses the skill default `journal="nat2"`, and leaves spacing to UltraPlot's automatic layout. All assume `import numpy as np; import ultraplot as uplt` and `EXPORT_DPI = 1000`.

## 1. Multi-line comparison with a legend
```python
fig, ax = uplt.subplots(journal="nat2")
ax.plot(x, Y, lw=2, cycle="colorblind", labels=["control", "treatment", "baseline"],
        legend="b", legend_kw={"ncols": 3, "frame": False})
ax.format(xlabel="time (s)", ylabel="signal (mV)", grid=False)
fig.save("lines.pdf", dpi=EXPORT_DPI)
```

## 2. Small-multiples grid with shared axes + panel letters
```python
fig, axs = uplt.subplots(ncols=3, nrows=2, journal="nat2")
for ax, y in zip(axs, series):
    ax.plot(x, y, lw=1.5, color="denim")
axs.format(abc="a.", abcloc="ul",
           xlabel="x (units)", ylabel="y (units)",
           toplabels=("Low", "Mid", "High"), leftlabels=("Run 1", "Run 2"))
```

## 3. 2D field with a shared outer colorbar
```python
fig, axs = uplt.subplots(ncols=2, journal="nat2")
for ax, field in zip(axs, fields):
    m = ax.pcolormesh(lon, lat, field, cmap="batlow", levels=11, extend="both")
axs.format(abc="a.", abcloc="ul", xlabel="x", ylabel="y")
fig.colorbar(m, loc="b", label="T (K)", length=0.7)   # one bar for the row
```

## 4. Signed / anomaly field (diverging, centered at zero)
```python
fig, ax = uplt.subplots(journal="nat2")
m = ax.contourf(anomaly, cmap="roma", levels=uplt.arange(-6, 6, 1), extend="both")
ax.colorbar(m, loc="r", label="anomaly (K)")
ax.format(xlabel="lon", ylabel="lat")
```

## 5. Correlation matrix as a labeled heatmap
```python
fig, ax = uplt.subplots(journal="nat2")
m = ax.heatmap(corr, cmap="BuRd", vmin=-1, vmax=1, labels=True,
               labels_kw={"precision": 2})
ax.format(xticklabels=names, yticklabels=names, xrotation=45)
ax.colorbar(m, loc="r", label="Pearson r")
```

## 6. Scatter with a size legend + color legend (semantic keys)

```python
fig, ax = uplt.subplots(journal="nat2")
ax.scatter(df.x, df.y, c=df.value, s=df.pop, cmap="batlow", alpha=0.8)
ax.numlegend(vmin=df.value.min(), vmax=df.value.max(), n=5, cmap="batlow",
             loc="ur", title="value", frameon=False)
ax.sizelegend([10, 50, 200], labels=["S", "M", "L"], loc="lr",
              title="population", frameon=False)
ax.format(xlabel="x", ylabel="y", grid=False)
```

## 7. Distribution: box/violin with shaded percentile bands on a line

```python
fig, axs = uplt.subplots(ncols=2, journal="nat2", share=False)
axs[0].violin(samples, cycle="colorblind")
axs[0].format(xticklabels=groups)
# line with mean + shaded IQR straight from raw samples
axs[1].plot(x, runs, mean=True, shadedata=True, color="rose", lw=2)
axs.format(abc="a.", abcloc="ul")
```

## 8. Map (cartopy) with an anomaly field

```python
import cartopy.crs as ccrs

fig, ax = uplt.subplots(proj="pcarree", journal="nat2")
m = ax.pcolormesh(lon, lat, data, cmap="roma", levels=uplt.arange(-4, 4, 0.5),
                  extend="both", transform=ccrs.PlateCarree())
ax.format(coast=True, borders=True, grid=True,
          lonlabels="b", latlabels="l")
ax.colorbar(m, loc="b", label="anomaly", length=0.6)
```

## 9. Twin axes (two y-scales, honestly labeled)

```python
fig, ax = uplt.subplots(journal="nat2")
ax.plot(x, temp, color="rose", lw=2)
ax.format(ylabel="temperature (°C)", ycolor="rose", xlabel="day")
axr = ax.alty(ylabel="precipitation (mm)", ycolor="denim")
axr.bar(x, precip, color="denim", alpha=0.5)
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
