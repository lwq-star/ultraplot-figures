# UltraPlot API reference (for figure-making)
Everything below assumes `import ultraplot as uplt`. UltraPlot's axes are `PlotAxes`, a *superset* of matplotlib axes — every mpl method still works, plus the additions here. Feed pandas/xarray objects directly; UltraPlot reads their labels, coordinates, and units for you.

## Contents

- Creating figures and subplots
- `format()`
- Panel identifiers and annotation priority
- Plotting commands
- Colorbars and legends
- Panels and insets
- Maps
- rc and styling
- Saving

## Creating figures & subplots
```python
fig, ax  = uplt.subplot(journal="nat2")
fig, axs = uplt.subplots(ncols=3, nrows=2, journal="nat2")
fig      = uplt.figure(journal="nat2")
ax       = fig.subplot(121)
```

**Complex layouts** with a "picture" array (`0` = empty slot):
```python
fig, axs = uplt.subplots([[1, 1, 2],
                          [3, 4, 2]], journal="nat2")
```

Or create `fig = uplt.figure(journal="nat2")`, add an explicit gridspec with
`gs = uplt.GridSpec(nrows=2, ncols=2)`, then call `fig.subplot(gs[:, 0])`.

### Width selection

Use exactly one width authority, in this order:

1. If the user specifies a journal preset, use `journal=`.
2. If the user specifies an exact total physical width, use `figwidth=`.
3. Otherwise use `journal="nat2"`, the default for this skill.

UltraPlot defines `nat1` as 89 mm and `nat2` as 183 mm. Do not approximate
these values or combine `journal` with a competing `figwidth` or `refwidth`.
Numbers are interpreted as inches; unit strings include `'183mm'`, `'8em'`,
and `'2cm'`. Use `refwidth` or `refheight` only when the user explicitly asks
to size a reference subplot instead of the total figure.

### Geometry

`refnum` selects the reference subplot and `refaspect` is that subplot's
width-to-height ratio; the reference subplot may span multiple cells. It is not
the aspect of the complete figure or of an adjacent row or column composition.
Use `hratios` and `wratios` for intentional row and column proportions. When the
reference subplot has a fixed data aspect, normally omit `refaspect` and let
UltraPlot use its natural aspect. See `references/layout.md` for reference-axis
selection and renderer-based diagnostics.

### Advanced spacing overrides

Keep UltraPlot's own tight layout active. For complex layouts, pass `tight=True`
or confirm that the effective `rc["subplots.tight"]` is `True`. On the first
render with final content, do not pass `left`, `right`, `top`, `bottom`, `space`,
`wspace`, `hspace`, `outerpad`, `innerpad`, `panelpad`, `wpad`, or `hpad` to the
figure or GridSpec. When `journal=` or `figwidth=` fixes the total width, also
leave the height unconstrained unless an exact height is required.

UltraPlot's tight layout calculates margins and inter-subplot spacing from the
rendered artists. A manual value partially overrides the corresponding automatic
result. Add only the smallest necessary override after inspecting a failed
automatic render, document the defect and fix, and leave unaffected sequence
entries as `None`. Prefer `outerpad`, `innerpad`, `panelpad`, `wpad`, or `hpad`
for clearance; use `left`, `right`, `top`, `bottom`, `wspace`, or `hspace` only
when an exact axes-edge distance is required. Do not combine UltraPlot auto
layout with Matplotlib `tight_layout()`, `constrained_layout`, or
`subplots_adjust()`.

**SubplotGrid** (`axs`) is list- and array-indexable and broadcasts methods:
`axs[0]`, `axs[:, 0]` (first column), `axs[1, 1:]`, `axs.format(...)` applies to
all. Singleton grids act like a scalar.

**Axis sharing** is ON by default (shared limits/ticks/labels within rows/cols
plus *spanning* labels). Turn off with `share=False`, `span=False`. Levels:
`share=True|False|'labels'|'limits'|0|1|2|3`.

## `format()` — the one-stop formatter
Call on a figure, axes, or subplotgrid; or pass the same kwargs straight into `subplots(...)`. Grouped kwargs:

- **Figure-level titles - disabled by default:** `suptitle`/`figtitle`,
  `suptitlecolor`.
- **Figure-edge structural labels:** `toplabels`, `bottomlabels`, `leftlabels`,
  `rightlabels`.
- **Subplot-level titles - disabled by default:** `title`, `titleloc`
  (`'l'|'c'|'r'`), and all documented positional title variants.
- **Panel identifiers:** For two or more independent main Axes, this skill uses
  `abc="a.", abcloc="ul"` as its default figure-local policy unless a direct
  user or journal instruction requires another style, location, or omission.
  UltraPlot's built-in defaults remain `abc=False` and `abc.loc='left'`.
- **Axes/general:** `facecolor`/`fc`, `edgecolor`/`ec`, `linewidth`/`lw`, `grid`,
  `gridminor`.
- **Cartesian axis labels - preserve when needed:** `xlabel`/`ylabel`,
  `xlim`/`ylim`, `xscale='log'`, `xticks`,
  `yticks`, `xticklabels`, `xtickloc`/`ytickloc` (`'both'`), `xtickminor`,
  `xtickdir='inout'`, `xrotation`, `xgridminor`, `xbounds`, `xformatter`.
- **Polar:** `rlim`, `thetalim`, ... (`PolarAxes`).
- **Geographic:** `lonlim`/`latlim`, `lonlabels`/`latlabels`, `coast`, `land`,
  `ocean`, `borders`, `rivers` (`GeoAxes`, see Maps below).
- **rc settings:** any rc key works as a kwarg (dotted keys with dots removed,
  e.g. `abcloc` for `abc.loc`, or `rc_kw={'abc.loc': 'right'}`).

Shorthand aliases are pervasive: `fc`, `ec`, `lw`, `ls`, `c`. Use `uplt.arange(-3, 3)` (inclusive endpoint) for tick lists.

## Panel identifiers and annotation priority

UltraPlot accepts `abc=True`, a template containing `a` or `A`, or an explicit
sequence. `abc=True` uses the built-in `a` style, while this skill uses `a.`.
Template labels follow `Axes.number`; regular grids are row-major unless
`order="F"` is used, and picture-array integers determine the numbers. Beyond
26, UltraPlot repeats letters as `aa`, `bb`, ..., `zz`, `aaa`, and so on.
Explicit sequences are assigned one by one to the Axes receiving `format()`.
UltraPlot 2.5's stable `subplots(order=...)` parameter table reverses the prose
for `"C"` and `"F"`; its NumPy analogy, a-b-c guide, and installed behavior
agree that `"C"` is row-major and `"F"` is column-major. Confirm `Axes.number`
instead of relying on the reversed parameter-table wording.

For required multi-panel identifiers, reserve the inner upper-left region and
give `abc` higher text-layout priority than ordinary annotations. UltraPlot
automatically separates a title and `abc` that share a location, with
`abctitlepad` controlling their separation. It does not automatically separate
ordinary `Axes.text()` artists from `abc`. Inner identifiers use a white text
border by default; `abcbbox=True` uses a backing box instead. Borders, boxes,
and z-order improve contrast but do not repair geometric overlap. When
measuring decorated text, include both the Text extent and any public bbox-patch
extent, then add clearance for the configured border or path-effect stroke.

Place ordinary statistics, equations, sample sizes, and callouts in a
consistent non-upper-left location first. If fixed placement fails, pass only
the lower-priority annotation objects to `Axes.auto_align_text()` and pass the
public `abc` Text artist in `avoid=`. `avoid_overlap=True` alone does not make
the identifier an obstacle. Never pass the identifier as a movable object or
call `auto_align_text()` without an explicit object list for this repair.

Use `abcpad` only for an independently justified identifier alignment change,
not to make room for an ordinary annotation. UltraPlot 2.5.0 accepts the public
`abcpad` format argument, but the documented `rc['abc.pad']` key is absent from
the stable configuration table and local rc manager; do not depend on reading
that key.

## Plotting commands (axes-level)
**1D / relational:**
`plot`, `plotx`, `line`, `linex`, `scatter`, `scatterx`, `step`, `stem`,
`vlines`, `hlines`, `parametric` (color-encodes a third variable along a line),
`area`, `areax`, `fill_between`, `fill_betweenx`, `bar`, `barh`.

**Distributions / statistics:**
`hist`, `hist2d`, `hexbin`, `boxplot`/`box`, `violinplot`/`violin`. UltraPlot adds
support for shaded error/percentile ranges via `shadedata`/`fadedata` or
`mean=True`, `median=True`, `bars=True`, `boxes=True` keywords on 1D commands.

**2D fields:**
`pcolormesh`, `pcolor`, `pcolorfast`, `imshow`, `heatmap` (labeled cells), `contour`, `contourf`, `tricontour`. Key kwargs: `cmap`, `cmap_kw`, `levels` (int count or explicit edges via `uplt.arange`), `values` (level *centers* — use to pin a diverging midpoint), `norm`, `vmin`/`vmax`, `extend='both'|'min'|'max'`,`labels=True` (inline contour/cell labels), `discrete`.

**Vector fields:** `quiver`, `streamplot`, `barbs`.
All accept on-the-fly guides: `colorbar='r'`, `legend='b'`, plus `colorbar_kw`,`legend_kw`, `cycle`, `cycle_kw`, `labels`.

## Colorbars & legends

On legend calls, `title` and `label` name the legend. On colorbar calls,
`label` and `title` name the colorbar. These are guide labels, not figure-level
or subplot-level titles, and the default no-title rule does not disable them.

Use an axes-level guide when one Axes owns the encoding. Use a figure-level
guide only when the encoding is genuinely shared by multiple Axes. Do not choose
the figure-level form merely to standardize code structure.

**Locations** (`loc`/`location`): outer side = `'l'`, `'r'`, `'t'`, `'b'`; inset =`'ul'`, `'ur'`, `'ll'`, `'lr'`, or full words (`'upper right'`). Outer guides allocate a new gridspec row/column — they don't steal subplot space or distort aspect ratios. Multiple guides on one side stack.

```python
ax.colorbar(m, loc="r", label="...", length=0.8, extend="both", tickminor=True)
ax.legend(handles, loc="b", ncols=3, center=True, frame=False, order="C")
fig.colorbar(m, loc="b", col=1)          # figure-wide, aligned to column 1
fig.legend(hs, loc="r", rows=(1, 2))     # span specific rows/cols
```

Outer guides can increase total figure size even though they do not change main
subplot aspect ratios. For outer guides, `space` controls fixed separation from
the subplot-grid edge and `pad` controls tight-layout clearance; `panelpad`
supplies the axes-level and subsequently stacked figure-level guide default,
while the first figure-level guide uses `innerpad` by default.

- **On-the-fly:** pass `colorbar='b'` / `legend='ul'` straight to a plot command.
- **Colorbar from lines/artists or colors:** `ax.colorbar(lines, values=[...])` or `ax.colorbar('Blues', values=range(10))`.
- **Ticks:** `locator`/`ticks`, `minorlocator`/`minorticks`, `formatter`/ `ticklabels`, `tickloc`. Width/length are in physical units.
- **Legend extras:** auto-infer handles/labels; `labels=` for 2D-array columns; `center=True` for centered rows; `alphabetize=True`; restyle handles by passing `lw`, `color`, `markersize`, or `handle_kw`.
- **Decouple content/location:** `fig.legend(ax=axs[1, :], ref=axs[0, :],
  loc='b')` builds from one group's handles, places by another.

**Semantic legends** (describe an *encoding*, no exemplar artist needed):
`ax.catlegend(names, colors={...}, markers={...})`,
`ax.sizelegend([10, 50, 200], labels=[...])`,
`ax.numlegend(vmin=0, vmax=1, n=5, cmap='batlow')`,
`ax.entrylegend([{...}, {...}])`, `ax.geolegend([...])`. All exist on `fig` too
and accept `add=False` to return `(handles, labels)` for composition.

## Panels & insets
```python
px = ax.panel_axes("r", width="4em")     # marginal panel (share axis)
ix = ax.inset_axes([0.6, 0.6, 0.3, 0.3]) # inset; zoom indicators available
axt = ax.altx()   # twin x with independent scale;  ax.alty(), ax.dualx()
```
`panel_axes`/`inset_axes`/`altx`/`alty` also exist on the SubplotGrid.

## Maps (GeoAxes)
```python
import cartopy.crs as ccrs

fig, ax = uplt.subplots(proj="pcarree", journal="nat2")
ax.format(coast=True, land=True, ocean=True, borders=True,
          lonlim=(-60, 60), latlim=(0, 80),
          lonlabels="b", latlabels="l", grid=True)
ax.pcolormesh(lon, lat, data, transform=ccrs.PlateCarree(), cmap="batlow")
```
Backends: cartopy (default) or basemap via `backend=`. Pass projection kwargs with `proj_kw`. Requires cartopy in the env.

## rc / styling

`uplt.rc` spans both matplotlib rcParams and UltraPlot-only settings. Use the
narrowest configuration scope:

1. Pass settings to `Axes.format()` or `Figure.format()` for one figure.
2. Use `uplt.rc.context()` for a bounded group of figures.
3. Change session-global `uplt.rc` only for an explicitly requested shared theme.
4. Inspect `uplt.rc.changed` (a property, not a method) to audit current
   configuration differences from UltraPlot's built-in defaults. It does not
   report figure-local `format()` effects.

Do not replace the effective UltraPlot font family by default. For missing
glyphs, register a supported font and extend the active generic-family fallback
list. Treat stylesheets and rc aliases as multi-property changes and verify
their complete visual effect. If a stylesheet is required, apply it at the
narrowest practical scope with `ax.format(style="ggplot")` or a bounded rc
context.

## Saving
UltraPlot 2.5 sets `rc["savefig.dpi"]` to 1000, and `Figure.save()` forwards keyword arguments to matplotlib's `Figure.savefig()`. Skill-generated scripts must nevertheless make the publication export requirement explicit:

```python
EXPORT_DPI = 1000
fig.save("figure.pdf", dpi=EXPORT_DPI)
fig.save("figure.png", dpi=EXPORT_DPI)
```

Use the same `EXPORT_DPI` for every final output without branching by figure type or filename extension. Unless the user or journal explicitly specifies another value, keep the default at 1000 dpi and always above 600 dpi. Do not pass `bbox_inches="tight"` when the physical output size matters: it replaces the nominal canvas with the artists' post-render tight bounding box and can shrink or enlarge the saved page. For `journal="nat2"`, verify that the final PDF media box is 183 mm wide (about 7.2047 in or 518.74 pt), within 0.2 mm.
