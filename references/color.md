# Color in UltraPlot: choosing, building, modifying
The single most common way scientific figures mislead is bad color. Get the map *type* right first, then worry about which specific map.

## Match map type to data type

| Data | Map type | Good UltraPlot choices |
|------|----------|------------------------|
| Magnitude, 0→max, no meaningful zero split | **Sequential** | `batlow`, `fire`, `dusk`, `ice`, `boreal`, `marine`, `Blues`, `viridis`, `magma` |
| Signed / anomaly with a meaningful zero | **Diverging** | `Div`, `roma`, `vik`, `BuRd`, `RdBu` |
| Phase, angle, longitude, time-of-day | **Cyclic** | `romaO`, `vikO`, `twilight`, or build with `cyclic=True` |
| Distinct lines/bars/categories | **Qualitative cycle** | `538`, `ggplot`, `colorblind`, `qual1`, `Set3`, `bmh` |

Rules:
- **Never** `jet`, `rainbow`, `hsv`, `gist_rainbow` for magnitude — they add
  false boundaries and fail in grayscale/colorblind vision. UltraPlot still
  registers them but hides them from `show_cmaps()` for a reason.
- Diverging maps must be **centered on the real neutral value**. Use `values=` or
  symmetric `levels=` so the midpoint color sits at true zero, e.g.
  `levels=uplt.arange(-10, 10, 2)`.
- Prefer the perceptually uniform families (`PerceptualColormap`s and Fabio
  Crameri's scientific colour maps `batlow`/`roma`/`vik`/`vikO`/`romaO`), which
  are colorblind-safe and grayscale-safe by construction.

## Verify perceptual uniformity

```python
uplt.show_cmaps()                       # table of registered maps
uplt.show_channels("fire", "dusk", rgb=False)   # hue/chroma/luminance curves
uplt.show_colorspaces(luminance=50)     # cross-sections (black = impossible colors)
uplt.show_cycles()                      # registered discrete cycles
uplt.show_colors()                      # named colors (xkcd/open-color)
```
A good sequential map has a **monotonic luminance ramp** — check the luminance
curve in `show_channels`.

## Building colormaps — `uplt.Colormap(...)`
Every `cmap=` argument is passed through this constructor, so you can inline it.

```python
# Monochromatic from one color (progresses to white by default)
uplt.Colormap("prussian blue", l=100, space="hpl", name="Pacific")

# From a list of colors (interpolates; neutral colors make diverging maps)
uplt.Colormap(["blue", "white", "red"], name="BWR")

# From HSL/HCL channel values (numbers 0-100, colors, or lists)
uplt.Colormap(h=("red", "red-720"), s=(80, 20), l=(20, 100), space="hpl")

# Cyclic
uplt.Colormap(h=(0, 360), c=50, l=70, space="hcl", cyclic=True, name="Spectrum")

# Merge maps (e.g. build a diverging map from two sequential ones)
uplt.Colormap("Blues4_r", "Reds3", name="Diverging")
uplt.Colormap("Greens1_r", "Oranges1", "Blues1_r", "Blues6", ratios=(1, 3, 5, 10))
```
Colorspaces: `'hsl'` (default, full gamut), `'hpl'` (soft pastels, most uniform),
`'hcl'` (purely uniform but has impossible colors). Keep task-specific colormaps
inline. Use `save=True` only when the user explicitly requests persistent reuse;
do not create a saved colormap merely for the current figure.

## Modifying existing colormaps
Pass these to `uplt.Colormap(...)` or inline via `cmap_kw={...}`:

- `left=` / `right=` — truncate ends (drop near-white so lines pop).
- `cut=` — widen (`cut<0`) or sharpen (`cut>0`) a diverging map's neutral center.
- `shift=` — rotate a cyclic map (ends stay distinct).
- `alpha=(a0, a1)` — opacity gradation for layering fills.
- `gamma=` — emphasize high-luminance (`>1`) or high-saturation (`<1`) colors.
- Name suffixes: `_r` reverse, `_s` shift. Names are case-insensitive; diverging
  names can be given reversed (`BuRd` == `RdBu_r`).

```python
ax.contourf(data, cmap="Ice", cmap_kw={"left": 0.3})
ax.contourf(data, cmap="Div", cmap_kw={"cut": 0.2}, levels=uplt.arange(-10, 10, 2))
```

## Color cycles — `uplt.Cycle(...)`
Cycles are `DiscreteColormap`s turned into property cyclers for distinct elements (lines, bars).

```python
ax.plot(data, cycle="538")                   # per-call
ax.plot(data, cycle="Blues", cycle_kw={"left": 0.2})  # sample a continuous map

with uplt.rc.context(cycle="colorblind"):    # bounded figure series
    ax.plot(data)

# From colors / merged maps / a count
uplt.Cycle("blues", "reds", "oranges", 15, left=0.1)   # 15 colors
uplt.Cycle("plum")                            # monochromatic
uplt.Cycle(lw=3, dashes=[(1, 0.5), (3, 1.5)]) # cycle non-color props too
```
When you hand a 2D array to a 1D command, UltraPlot picks one color per column automatically. For categorical data, prefer a *qualitative* cycle (`colorblind`, `qual1`, `Set3`) — don't sample a sequential map, or categories will look ordered.

Get raw colors when you need them: `uplt.get_colors("grays", 5)`.

## Practical defaults

- Lines / few categories → `cycle="colorblind"` or `"538"`.
- Continuous field, positive → `cmap="batlow"` (or `viridis`).
- Anomaly / difference field → `cmap="roma"` or `"BuRd"`, symmetric levels.
- Correlation matrix / heatmap → diverging, centered at 0, `ax.heatmap(...)`.
- Phase / direction → `cmap="romaO"`.
