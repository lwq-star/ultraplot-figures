# UltraPlot layout decisions and diagnostics

This reference guides agent-side reasoning. Any renderer measurements or
diagnostic snippets used while applying it are temporary QA and must not be
copied into delivered plotting or preprocessing scripts.

Read it for picture arrays, spanning subplots, mixed fixed- and auto-aspect axes,
an unconstrained figure dimension, complex outer guides, or unexplained
whitespace, misalignment, clipping, or overlap.

## Contents

- Topology and supported model
- Default tight-layout contract
- Sizing reference
- Axis sharing and guides
- Geometry diagnosis
- Panel-identifier clearance
- Defect-to-parameter decisions

## Topology and supported model

- Use `nrows` and `ncols` when each subplot occupies one ordinary grid cell.
- Use `wratios` and `hratios` for unequal regular columns or rows. Ratios control
  geometry, not spacing.
- Use a picture array only for genuine spans, holes, or non-rectangular topology;
  `0` denotes an empty slot. Do not repeat an identifier merely to imitate a
  regular-grid ratio.
- Use one UltraPlot `GridSpec` per figure. UltraPlot 2.5 does not officially
  support nested gridspecs, `GridSpecFromSubplotSpec`, or `SubFigure`.
- Revise the topology when the intended comparison cannot remain readable at the
  required physical size. Spacing cannot repair an infeasible topology.

For two unequal side-by-side panels, prefer:

```python
fig, axs = uplt.subplots(ncols=2, wratios=(2, 1), journal="nat2")
```

For a subplot spanning two rows beside two stacked subplots, keep the genuine
row span and express the width difference with `wratios`:

```python
# Prefer
fig, axs = uplt.subplots(
    [[1, 2],
     [1, 3]],
    wratios=(2, 1.1),
)

# Avoid: the duplicate first two columns only imitate extra width
fig, axs = uplt.subplots(
    [[1, 1, 2],
     [1, 1, 3]],
    wratios=(1, 1, 1.1),
)
```

## Default tight-layout contract

- Keep UltraPlot's own tight layout active with `tight=True`, or confirm that
  the effective `rc["subplots.tight"]` is `True`.
- The first render must include final axes types, limits or extents, typography,
  labels, annotations, identifiers, and guides while leaving all subplot and
  GridSpec margin, spacing, and padding arguments unset.
- Do not use Matplotlib `tight_layout()`, `constrained_layout`, or
  `subplots_adjust()` alongside UltraPlot auto layout.
- Explicit spacing is a supported partial override, not a default design tool.
  Retain one only after the automatic render exposes a specific defect, and
  leave unaffected sequence entries as `None`.
- Fixed margins and spaces cannot repair an infeasible topology, a wrong sizing
  reference, unsuitable row or column ratios, fixed-aspect slot waste, or an
  ordinary-annotation collision.

## Sizing reference

- `refnum` selects the subplot that governs an unconstrained canvas dimension.
  The first subplot is the default, not a universal recommendation.
- `refaspect` is the selected subplot's width-to-height ratio, not the complete
  figure aspect or the aspect of a neighboring row or column composition.
- When a reference subplot has a fixed data aspect, normally omit `refaspect` so
  UltraPlot can use the actual aspect after limits or extent are known.
- When only one total figure dimension is fixed, let UltraPlot derive the other
  from the reference subplot and GridSpec geometry.
- `journal="nat2"` fixes total width at 183 mm and leaves height for automatic
  derivation. Do not combine it with a competing `figwidth` or `refwidth`.
- Unless an exact height is required, do not combine a width-fixing `journal=`
  or `figwidth=` with `figheight=`, `figsize=`, or `set_size_inches()`. Some
  journal presets may themselves constitute an explicit fixed-size requirement.

For `[[1, 2], [1, 3]]`, subplot 1 spans both rows. If it is the dominant fixed-
aspect map, use it as the sizing reference when its complete visible geometry
should govern height. Choosing subplot 2 instead sizes one right-hand panel, not
the combined right-hand composition.

## Axis sharing and guides

- Start from `share="auto"`. Use `share=False, span=False` when geographic and
  Cartesian axes, or any axes with unrelated variables or units, should not share
  limits, ticks, or spanning labels.
- Use `ax.colorbar()` or `ax.legend()` when one Axes owns the guide.
- Use `fig.colorbar()` or `fig.legend()` only for a guide genuinely shared by
  multiple Axes. Figure-level guides can span selected rows or columns.
- Outer guides allocate GridSpec rows or columns and may increase total figure
  size. They do not directly change a main Axes data aspect.
- Avoid `bbox_to_anchor`. Use UltraPlot guide locations and layout allocation.

## Diagnose rendered geometry

Use the complete first render defined by the default tight-layout contract.

When a defect appears, distinguish:

1. the allocated GridSpec slot from
   `ax.get_subplotspec().get_position(fig)`;
2. the visible axes frame from `ax.get_position()`;
3. the decorated boundary from `ax.get_tightbbox(renderer)`.

Inspect these geometries with the final renderer in temporary task code or an
internal validation tool. Do not return measurement functions, bbox records, or
diagnostic dictionaries as reproduction code.

Classify apparent whitespace as:

- a true gap between subplot slots;
- unused space inside a fixed-aspect slot;
- decorated-content clearance for ticks, labels, identifiers, or guides;
- an outer margin.

`wspace` and `hspace` cannot remove unused area created when a fixed-aspect axes
occupies only part of its slot. For spanning axes, remember that the allocated
slot includes intervening GridSpec spaces, so a slot-to-frame difference is not
automatically waste.

Use numerical thresholds only as review triggers. Judge the layout from the
declared comparison, physical readability, and composition rather than treating
a heuristic threshold as an UltraPlot guarantee.

## Panel-identifier clearance

For two or more independent main Axes, use `abc="a.", abcloc="ul"` unless the
user or journal specifies otherwise. Count only independent main Axes; exclude
colorbars, legend-only axes, helper axes, and non-independent insets.

Reserve the rendered identifier region plus modest clearance. Place ordinary
statistics, equations, sample sizes, callouts, legends, and insets elsewhere.
For homogeneous small multiples, prefer one consistent non-upper-left annotation
location.

If a collision occurs:

1. preserve the identifier and its upper-left location;
2. move, shorten, or reflow the ordinary annotation;
3. use `auto_align_text()` only when fixed placement remains infeasible, passing
   only lower-priority annotations as movable objects and the public identifier
   artist as an obstacle;
4. render again and inspect the result internally.

Do not use `abcpad`, z-order, a border, backing box, or tight layout to conceal a
geometric collision. Do not include identifier-discovery or bbox-overlap code in
the delivered plotting script.

## Defect-to-parameter decisions

Choose repairs in this order: correct topology, ratios, and `refnum`; correct
ordinary annotation placement; correct guide ownership or placement; then tune
automatic padding. Use a fixed axes-edge space only when an exact distance is
actually required, and use a fixed outer margin only when that exact physical
margin is itself a requirement.

| Observed defect | Correct response |
|---|---|
| Infeasible topology or unreadable frames | Revise topology or output format |
| Fixed-aspect slot waste | Revise topology, ratios, or sizing reference |
| Wrong panel proportions | Revise `wratios`, `hratios`, or `refnum` |
| Unnecessarily fixed width and height | Remove `figheight`, `figsize`, or manual resizing and let UltraPlot derive the open dimension |
| Required fixed frame-to-frame distance | Use the smallest local `wspace` or `hspace`; leave unaffected entries as `None` |
| Decorated-content clearance | Use minimal `wpad`, `hpad`, or `innerpad` after structure is correct |
| Figure-edge distance | Use `outerpad` for automatic clearance or an edge margin for an exact distance |
| Outer-guide separation | Use guide `space` or `pad` according to UltraPlot semantics |
| Identifier/annotation collision | Move or reflow the lower-priority annotation |

Do not use `group=False`, `equal=True`, `ultra_layout=False`, repeated
`auto_layout()`, or `aspect="auto"` as generic repairs. Keep only the final
layout choices and concise rationale required to reproduce the figure.
