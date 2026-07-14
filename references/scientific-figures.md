# Publication-quality scientific figures

Use this file for manuscripts, journal submissions, posters, revisions, significance
annotations, and publication-facing multi-panel figures. Check the target journal's
current author instructions when final submission rules matter.

This file is the authoritative export profile for publication-facing deliverables in
this skill.

## Publication requirements and fallback

Resolve publication settings in this order:

1. the target journal or publisher's current author instructions;
2. the user's explicit size, format, DPI, color, font, and transparency settings;
3. verified UltraPlot journal presets, auto-layout, unit specs, and export APIs;
4. a documented Skill fallback for each setting that remains unknown.

The target venue controls accepted formats, single/double-column dimensions, raster
DPI, color mode, fonts, transparency, and file-size limits. Do not replace a named
venue's rules with a generic Nature-style profile.

Resolve settings independently rather than enabling or disabling one monolithic
profile:

| Missing setting | Skill fallback |
|---|---|
| Venue and physical width | Current `nat2` width, 183 mm, stated as a size fallback |
| Height | Automatic after all artists and guides are added |
| Output formats | PDF plus TIFF only when formats are not requested |
| High-resolution TIFF DPI | 600 dpi when no numeric DPI is supplied |
| TIFF color mode and transparency | Opaque RGB |
| TIFF compression | Lossless LZW |

Preserve explicit formats even when another setting uses a fallback. `183 mm` is the
measured width of the current `nat2` preset, not a universal double-column width.

Put the resolved settings in the top config block:

```python
OUTPUT_PDF = "figure.pdf"   # include only if accepted/required
OUTPUT_TIF = "figure.tif"   # include only if accepted/required
OUTPUT_SVG = None           # optional vector production output
JOURNAL = "nat2"            # size fallback when venue and width are unknown
TARGET_WIDTH_MM = 183       # current nat2 fallback width; change for a named target
TARGET_HEIGHT_MM = None     # unconstrained unless specified
DPI = 600                   # fallback raster resolution, not a universal rule
ABC = "a"                  # follow target panel-label policy
```

Set the journal preset or requested physical size before plotting:

```python
fig, axs = uplt.subplots(ncols=2, nrows=2, journal=JOURNAL)
axs.format(abc=ABC, abcloc="ul")
```

Common UltraPlot journal presets include `nat1`, `nat2`, `aaas1`, `aaas2`,
`pnas1`, `pnas2`, `pnas3`, `agu1` to `agu4`, and `ams1` to `ams4`. A preset is an
implementation mechanism, not proof that the current target instructions are met.
Follow the target venue's font policy and verify glyph coverage and embedding; do not
hard-code one universal CJK/Latin font pair.

### Canonical PDF/TIFF fallback export template

Use this template when the resolved deliverables include the Skill-default PDF/TIFF
artifact settings. Explicit target requirements override individual constants and
formats. Copy the function and constants into the delivered plotting script; do not
import them from the installed skill. The temporary PNG exists only inside a temporary
directory and is not a deliverable.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
matplotlib.use("Agg")

from PIL import Image
import ultraplot as uplt

FALLBACK_JOURNAL = "nat2"
FALLBACK_DPI = 600
FALLBACK_RC = {
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.facecolor": "white",
    "savefig.transparent": False,
}


def save_publication_fallback(fig, output_stem, *, dpi=FALLBACK_DPI):
    """Save the resolved PDF/TIFF fallback without Skill imports."""
    output_stem = Path(output_stem)
    if output_stem.suffix:
        raise ValueError("output_stem must not include a file extension")
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = output_stem.with_suffix(".pdf")
    tiff_path = output_stem.with_suffix(".tif")

    with uplt.rc.context(FALLBACK_RC):
        fig.canvas.draw()
        fig.savefig(pdf_path, facecolor="white", transparent=False)
        with TemporaryDirectory() as tmp_dir:
            raster_path = Path(tmp_dir) / "render.png"
            fig.savefig(
                raster_path,
                dpi=dpi,
                facecolor="white",
                transparent=False,
            )
            with Image.open(raster_path) as rendered:
                rgba = rendered.convert("RGBA")
                white = Image.new("RGBA", rgba.size, "white")
                rgb = Image.alpha_composite(white, rgba).convert("RGB")
                rgb.save(
                    tiff_path,
                    format="TIFF",
                    dpi=(dpi, dpi),
                    compression="tiff_lzw",
                )

    return pdf_path, tiff_path
```

Do not set fallback production artists to `alpha < 1`. Create and save the figure
inside the same scoped settings:

```python
with uplt.rc.context(FALLBACK_RC):
    fig, axs = uplt.subplots(ncols=2, nrows=2, journal=FALLBACK_JOURNAL)
    # ... add opaque artists and guides, then run live QA ...
    save_publication_fallback(fig, Path("figures") / "figure")
```

The function enforces Type 42 PDF output settings and writes the TIFF as a white-
background, 600 dpi, RGB, lossless-LZW image. Artifact QA still verifies those
properties from the saved files.

## Final physical size and export rules

The Python plotting script and its input data are the editable authority. PDF and SVG
are vector-preserving production outputs, not authoritative editable sources. TIFF is
a raster production output.

UltraPlot journal presets and auto-layout may change figure dimensions when legends,
colorbars, labels, and panel guides are drawn. Therefore:

1. configure the target preset or physical dimensions before plotting;
2. add every artist and guide;
3. call `fig.canvas.draw()`;
4. measure `fig.get_size_inches() * 25.4` and run `render_qa.audit_figure(...)`;
5. save only after hard render defects are closed;
6. re-check physical size and resources from the saved files with
   `scripts/check_figure.py`.

For scientific-figure deliverables:

- save only formats accepted or required by the target venue;
- preserve explicit formats and fill only missing settings; when formats are unknown,
  use PDF plus TIFF, and when TIFF artifact settings are unknown, use 600 dpi opaque
  RGB with lossless LZW;
- save SVG only when requested or needed downstream;
- save PNG only for an explicitly requested preview, draft, or check-only raster;
- avoid JPEG unless explicitly required;
- always pass explicit raster `dpi=` instead of relying on UltraPlot defaults;
- for the resolved PDF/TIFF fallback, and whenever the target forbids Type 3 PDF fonts,
  apply `pdf.fonttype=42` and `ps.fonttype=42` in a scoped
  `uplt.rc.context(...)` after importing UltraPlot, and keep the context active
  through figure creation and saving;
- for the fallback TIFF, use the canonical exporter above so the saved file is
  flattened onto white and explicitly converted to RGB before lossless-LZW encoding;
  verify saved mode/compression metadata rather than inferring it from the save call;
  a named target's alpha, color-mode, or compression rules override the fallback;
- rasterize dense point/mesh/image layers when useful while keeping text and axes
  vector, subject to the target's policy.

Example in-memory check:

```python
fig.canvas.draw()
qa = audit_figure(
    fig,
    expected_size_mm={"width": TARGET_WIDTH_MM, "height": TARGET_HEIGHT_MM},
)
if not qa["ok"]:
    raise RuntimeError(qa["errors"])
```

Run the artifact API from the temporary Skill-side QA harness, not from the delivered
plotting script:

```python
artifact_report = check_figure.audit_files(
    [Path("figure.pdf"), Path("figure.tif")],
    allow_formats={"pdf", "tif"},
    require_formats={"pdf", "tif"},
    min_effective_dpi=600,
    require_embedded_fonts=True,
    forbid_type3_fonts=True,
    forbid_alpha=True,
    require_tiff_mode="RGB",
    require_tiff_compression="lzw",
    strict=True,
    fail_on_warning=True,
)
```

```bash
python scripts/check_figure.py figure.pdf figure.tif \
  --allow-formats pdf,tif --require-formats pdf,tif \
  --min-effective-dpi 600 \
  --require-embedded-fonts --forbid-type3-fonts \
  --forbid-alpha \
  --require-tiff-mode RGB --require-tiff-compression lzw \
  --strict --fail-on-warning
```

These are fallback checks. Add `expected_width_mm=183` to the API call or
`--expected-width-mm 183 --size-tolerance-mm 0.5` to the CLI only when `nat2` or an
explicit 183 mm target is genuinely intended. For a named target, replace the
fallback policy with the target's actual requirements.

## Color and accessibility

Use colorblind-safe palettes for categorical groups:

```python
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9"]
```

For continuous fields, use sequential palettes such as `viridis`, `cividis`,
`davos`, `turku`, `Blues`, or `Reds`. For signed anomalies or correlations, use a
diverging palette centered on the meaningful baseline. Avoid rainbow/`jet` unless a
field convention explicitly requires it.

Use redundant encodings when categories matter: marker shape, line style, hatching,
direct labels, or facets.

The Okabe-Ito set holds about eight distinguishable colors. Beyond that, colors stop
being separable: do not extend the palette with near-duplicate hues. Instead merge
minor categories into an "other" group, facet into small multiples, use direct
labels at cluster centroids, or add a second channel (shape or line style). Keep
color meaning identical across panels.

## Multi-panel figures

- Define each panel's role before coding.
- Keep axes, units, group order, and color meanings consistent.
- Share axes only for direct comparisons.
- Put common legends and colorbars outside the data area.
- Do not add panel titles by default. Prefer panel letters, axis/guide labels, and a
  caption. Add short panel titles only when the user requests them or when genuinely
  different tasks, datasets, or model outputs would otherwise be ambiguous; record
  that exception with `allow_subplot_titles=True` in semantic QA.
- Use `axs.format(abc="a", abcloc="ul")` for panel letters. Upper-left panel
  letters are the default priority anchor for publication-style multi-panel
  figures.
- Do not move panel letters to solve clashes with in-panel statistics, legends,
  colorbars, or annotations. Move or simplify the clashing item first. Move a panel
  letter only when the upper-left position would hide essential data or a target
  journal/example explicitly requires another location, and state that reason.
- Do not add decorative panels that do not support the figure message.

## Legend and colorbar ownership

Before rendering, decide whether each guide is panel-level or figure-level.

- Panel-level legend: explains an encoding used only in that panel.
- Figure-level legend/colorbar: explains a scale shared across panels.
- Do not place a legend inside a different panel from the one it primarily explains.
- If marker size encodes a variable on a map, place the size legend near the map or
  in a shared legend area and use the same source values and output marker-area range
  as the scatter.
- If color encodes the same continuous variable in multiple panels, use identical
  normalization, limits, label, and required ticks; use one shared colorbar when the
  layout supports it.

Guide placement has two independent spacing layers:

- outer placement: `loc`, `space`, `pad`, panel allocation, and auto-layout;
- inside the legend: `borderpad`, `handletextpad`, `labelspacing`, and
  `columnspacing`.

For publication-critical legends, use physical unit specs such as `"4pt"` or
`"6pt"` for internal spacing. After all guides exist, force a final draw and discover
all legend objects with `fig.findobj(match=matplotlib.legend.Legend)`. Treat
marker/title, marker/text, marker/marker, text/text, clipping, and frame-containment
collisions as hard defects. An outer legend location does not prove the entries are
internally separated.

## In-panel annotations

Place in-panel annotations where they do the least harm to the data:

- Prefer unused or low-density regions of the panel.
- Keep the annotation close to the feature or statistic it explains when practical.
- Do not cover the main data pattern, dense points, fitted lines, uncertainty bands,
  or important map/raster regions.
- Do not move panel letters out of the upper-left position merely to make room for
  annotation text.

Use an annotation background only for readability, not decoration. When text sits
on dense marks, image data, or variable-color backgrounds, use a small, neutral,
subtle aid such as a semi-transparent white box, a text halo, or a leader line.
Prefer borderless or very light borders, modest padding, and enough transparency
that the underlying data remain visible. If the text is already legible on an empty
or uniform area, omit the background.

## Colorbar ticks and normalization

For continuous variables, use a continuous colormap and colorbar. Use discrete
colors, boundaries, or legends only for real classes, bins, or thresholds.

Colorbar labels and ticks must describe the encoded data quantity, not just the
normalization:

- Label the colorbar with the encoded quantity and unit or scale. Use a descriptive
  variable name, not the normalization name.
- If using `LogNorm`, `PowerNorm`, transformed axes, or binned densities, keep the
  colorbar label tied to the data quantity and explain the normalization or binning
  in the caption/final note.
- Match tick strategy to the scale: use a small number of rounded ticks for ordinary
  continuous data; use major, human-readable ticks for logarithmic or transformed
  scales; include a real center value for centered diverging scales; and use
  category/bin labels only when the data are genuinely discrete or binned.
- Inspect automatic colorbar ticks before finalizing. Replace ticks that are
  difficult to interpret, normalized artifacts, or minor ticks masquerading as
  primary values.
- Do not show ticks that imply analytical thresholds unless those thresholds are
  real and documented in the config/caption.
- For shared colorbars, use identical limits, normalization, tick locations, and
  tick labels across the panels they explain.

## Statistical annotations

Show data where possible. For small samples, prefer raw points plus interval, box,
or violin instead of mean-only bars.

Always label uncertainty:

- SD: variability among observations;
- SEM: precision of the mean estimate;
- CI: confidence interval for mean/effect/model estimate;
- bootstrap interval: state method and resamples when known.

Use significance markers only when the test, comparison, correction, and sample size
are known or provided. Prefer reporting exact p values or adjusted p values and effect
sizes in the caption/final note when space permits.

Use established statistical notation. Use `r` for Pearson correlation and `ρ` for
Spearman rank correlation. Use clear standard labels for other quantities, such as
`R2`, `RMSE`, `n`, `95% CI`, `p`, and `adjusted p`. Avoid ad hoc abbreviations such
as `r(raw)`, `p_adj?`, or unexplained shorthand. If axes are transformed but a
statistic is computed on untransformed values, keep the in-panel notation standard
and explain the computation scale in the caption or final note. If the statistic
could be ambiguous, explain the test or model in the caption/final note rather than
inventing a new symbol. Do not add p values, stars, or significance wording unless
the test, sample unit, comparison, and correction are clear.

Keep thresholds in config:

```python
def p_to_stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"
```

Caption/final response should identify:

- test name or model;
- comparison definition;
- correction method for multiple testing, if any;
- sample size per group or analysis unit;
- effect size or plotted estimate;
- interval definition;
- exact threshold used for any stars or highlights.
