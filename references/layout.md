# UltraPlot layout and geometry diagnostics

Read this reference for picture arrays, spanning subplots, mixed fixed- and
auto-aspect axes, a figure with one unconstrained dimension, outer guides in a
complex layout, or any unexplained whitespace, misalignment, clipping, or
overlap.

## Contents

- Supported model and sizing semantics
- Reference-subplot preflight
- Renderer measurements
- Panel-identifier reserved regions
- Defect-to-parameter decisions

## Supported model and sizing semantics

- Use one UltraPlot `GridSpec` per figure. UltraPlot 2.5 does not officially
  support `GridSpecFromSubplotSpec`, nested gridspecs, or `SubFigure`.
- Use `nrows` and `ncols` for regular grids. Use a picture array only for real
  spans, holes, or non-rectangular topology; `0` denotes an empty slot.
- Treat `refnum` as the subplot number that controls reference sizing. The first
  subplot is the default, not a preferred universal choice.
- Treat `refaspect` as reference-subplot width divided by height. The reference
  subplot may span cells. Do not interpret it as the complete-figure aspect or
  the aspect of an adjacent row or column composition.
- When only one of `figwidth` and `figheight`, or one of `refwidth` and
  `refheight`, is specified, let UltraPlot derive the other dimension from the
  reference subplot and gridspec geometry. When both dimensions are fixed,
  `refaspect` does not control canvas sizing.
- Remember that `journal="nat2"` fixes the figure width at 183 mm but leaves
  height to automatic derivation.
- When the reference subplot has a fixed data aspect, as with GeoAxes or image
  axes, normally omit `refaspect` so UltraPlot can use that aspect. Set it only
  when a different reference geometry is intentional.
- Use the canonical names `refnum`, `refaspect`, `refwidth`, `refheight`,
  `figwidth`, and `figheight`. Avoid competing size authorities.

## Reference-subplot preflight

1. Declare the intended geometry: which visible-frame edges should align, which
   panel is dominant, the minimum readable physical frame sizes, and whether any
   blank slot or band is intentional.
2. Identify every fixed-aspect axis and its true row or column span after data
   limits or geographic extent are applied.
3. Choose the subplot whose intended visible geometry should govern the
   unconstrained canvas dimension. Do not choose by subplot order.
4. Omit `refaspect` when that reference subplot already has the intended fixed
   data aspect. If the reference is auto-aspect, set `refaspect` only from an
   explicit design requirement.
5. Render with the actual axes types, extents, typography, labels, and guides.
   Compare plausible `refnum` candidates when the correct authority is unclear.

For `[[1, 2], [1, 3]]`, subplot 1 spans both rows while subplots 2 and 3 each
occupy one row. If subplot 1 is a dominant fixed-aspect map, `refnum=2` with an
explicit `refaspect` sizes one right-hand subplot, not the combined right-hand
composition. Use subplot 1 as the reference when its complete span should govern
height, then tune `hratios` only if the two right-hand panels need unequal
heights. This is a contextual choice, not a universal `refnum=1` rule.

## Renderer measurements

Use only public APIs and the final renderer:

```python
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
fig_w, fig_h = map(float, fig.get_size_inches())

for name, ax in main_axes.items():
    slot = ax.get_subplotspec().get_position(fig)
    frame = ax.get_position()
    tight = ax.get_tightbbox(renderer).transformed(
        fig.dpi_scale_trans.inverted()
    )
    slot_w, slot_h = float(slot.width * fig_w), float(slot.height * fig_h)
    frame_w, frame_h = float(frame.width * fig_w), float(frame.height * fig_h)
    metrics = {
        "slot_in": (slot_w, slot_h),
        "frame_in": (frame_w, frame_h),
        "tight_in": (tight.width, tight.height),
        "unused_width_fraction": max(0.0, 1.0 - frame_w / slot_w),
        "unused_height_fraction": max(0.0, 1.0 - frame_h / slot_h),
    }
    print(name, metrics)
```

Keep outer-guide axes out of `main_axes` and measure them separately. Also check
pairwise decorated-bbox overlap, canvas containment, visible-frame alignment,
and the union of decorated content against the canvas edges. Treat numerical
thresholds only as configurable review triggers. Decide pass or failure from the
declared layout intent and physical readability.

For a subplot that spans rows or columns, its allocated `SubplotSpec` slot
includes the intervening gridspec spaces. Therefore the reported unused fraction
can include structurally required row or column separation; do not classify all
of it as fixed-aspect waste. Compare it with the intended alignment, the actual
inter-row or inter-column spaces, and the decorated-content geometry.

## Panel-identifier reserved regions

For two or more independent main Axes, the figure-local skill policy is
`abc="a.", abcloc="ul"`. Treat the identifier's rendered bounding box plus a
small physical clearance as a reserved region. Ordinary annotations have lower
priority and must move first. Use only public artists and the final renderer:

```python
from matplotlib.text import Text
from matplotlib.transforms import Bbox

fig.canvas.draw()
renderer = fig.canvas.get_renderer()

def visible_text_bbox(text, renderer):
    """Union the public Text and optional bbox-patch extents."""
    parts = [text.get_window_extent(renderer)]
    patch = text.get_bbox_patch()
    if patch is not None and patch.get_visible():
        parts.append(patch.get_window_extent(renderer))
    return Bbox.union(parts)


abc_matches = [
    text for text in ax.findobj(match=Text)
    if text.get_visible() and text.get_text() == expected_label
]
if len(abc_matches) != 1:
    raise RuntimeError(
        f"Expected exactly one {expected_label!r} identifier; "
        f"found {len(abc_matches)}"
    )
abc_text = abc_matches[0]
abc_bbox = visible_text_bbox(abc_text, renderer)

# Two points clears the default 1.5 pt border. Increase this after any
# explicit border-width or path-effect override.
clearance_px = 2.0 * fig.dpi / 72.0
reserved_bbox = Bbox.from_extents(
    abc_bbox.x0 - clearance_px,
    abc_bbox.y0 - clearance_px,
    abc_bbox.x1 + clearance_px,
    abc_bbox.y1 + clearance_px,
)
annotation_bbox = visible_text_bbox(annotation, renderer)
if reserved_bbox.overlaps(annotation_bbox):
    raise RuntimeError("Ordinary annotation overlaps the panel identifier")
```

Store handles to ordinary statistics blocks, equations, sample sizes, and
callouts so each can be checked directly. Match the expected identifier inside
each main Axes and require exactly one match. Do not inspect private `_abc_*`
attributes. Also confirm that the identifier lies inside the upper-left region
of the visible axes frame and that its bounding box remains inside the canvas.

Repair a collision in this order: choose a consistent non-upper-left location
for homogeneous small multiples; move or reflow the ordinary annotation without
losing scientific meaning; then, if fixed placement remains infeasible, use the
documented solver with the identifier as an explicit obstacle:

```python
abc_obstacles = [abc_text]
abc_patch = abc_text.get_bbox_patch()
if abc_patch is not None and abc_patch.get_visible():
    abc_obstacles.append(abc_patch)

ax.auto_align_text(
    annotation,
    avoid=abc_obstacles,
    # Exceed the 2 pt validation clearance used above.
    pad=4.0,
    avoid_points=False,
    only_move="x",
    clip=True,
)
fig.canvas.draw()
```

Pass only lower-priority annotations as movable objects. Never pass `abc_text`
as a movable object. Make the solver `pad` larger than the validation clearance;
the example uses 4 points around the movable annotation and verifies against a
2-point identifier clearance. Use `only_move="xy"` when horizontal movement
cannot find a valid location, and set `avoid_points=True` only when avoiding
plotted data is also scientifically required. Re-render and repeat the
bounding-box checks after every automatic adjustment. `avoid_overlap=True`,
text borders, backing boxes, z-order, and tight layout do not independently
protect the identifier. If a decorated movable annotation still overlaps after
the solver runs, move it explicitly and validate its full visible bbox again.

## Defect-to-parameter decisions

- For infeasible topology or unreadable frames, revise topology or output format.
- For fixed-aspect slot waste, revise topology, `wratios`, `hratios`, or the
  reference subplot. Do not use spacing or padding to hide it.
- For wrong panel proportions, revise ratios or the intended sizing reference.
- For a required fixed frame-to-frame distance, use `wspace` or `hspace`.
- For decorated-content clearance, use the smallest necessary `wpad`, `hpad`,
  or `innerpad` only after structural geometry is correct.
- For automatic figure-edge clearance, use `outerpad`; for an exact edge
  distance, use `left`, `right`, `top`, or `bottom`.
- For outer guides, use `space` for fixed separation from the subplot-grid edge
  and `pad` for tight-layout clearance. `panelpad` is the axes-level and stacked
  figure-level guide default; the first figure-level guide uses `innerpad`.
- For a panel-identifier and ordinary-annotation collision, preserve `abc` in
  the inner upper-left and move or reflow the ordinary annotation. Do not use
  `abcpad`, subplot spacing, or z-order to hide the collision.

Outer guides add gridspec rows or columns and do not change main-subplot aspect
ratios or spacing, but they can increase total figure size. They can amplify
visual imbalance without causing fixed-aspect slot waste.

In UltraPlot 2.5.0, replace a repeated-ID picture array used only to imitate an
unequal regular grid with `nrows`, `ncols`, and ratios. Do not use `group=False`,
`equal=True`, `ultra_layout=False`, repeated `auto_layout()`, or `aspect="auto"`
as generic repairs. Preserve a genuine picture array when a real span or hole is
required, and diagnose its rendered geometry directly.
