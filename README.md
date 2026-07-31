**English** | [简体中文](README_zh.md)

# UltraPlot Figures

> A Codex skill for reproducible, publication-size static figures with UltraPlot.

`ultraplot-figures` helps Codex create and revise static scientific figures. It
can also troubleshoot plotting problems, review figures, and validate outputs.
Provide the plotting data and describe the scientific question and purpose of the
figure. Include any required dimensions, output formats, or journal requirements.
The output includes a reproducible, editable Python plotting script and the
corresponding rendered figures.

This repository is a **Codex skill**, not the
[UltraPlot](https://github.com/ultraplot/ultraplot) Python package or a standalone
plotting application.

> [!CAUTION]
> **Figures generated or revised with this skill must be reviewed by the author
> before submission or formal release.** The skill provides reproducible,
> editable Python plotting code and rendered figures, reducing the need to build
> plotting scripts from scratch. The author remains responsible for the final
> review and refinement of the figure's scientific communication and details in
> light of the research and submission requirements.

## Quick start

Invoke `$ultraplot-figures` in Codex. Provide the plotting data when creating or
replotting a figure. When revising an existing figure, include the original
plotting script whenever possible. A PDF or PNG is sufficient when only the
visible output needs review. Describe the scientific question and purpose of the
figure, along with any known dimensions, output formats, or journal requirements.

```text
Use $ultraplot-figures.
Input: [plotting data, existing plotting script, PDF, or PNG]
Scientific question: [the question the figure should address]
Figure purpose: [what the figure should communicate]
Output requirements: [optional dimensions, formats, or journal requirements]
```

### Defaults

When no figure size is specified, the skill uses UltraPlot's `nat2` preset, which
is 183 mm wide. It produces PDF and PNG unless another format is requested.

If no journal or font is specified, UltraPlot defaults to 9 pt sans-serif TeX
Gyre Heros. It is an open-source Helvetica-style font that remains clear at
small figure sizes and is easy to reproduce across systems. It matches the
sans-serif style commonly required by many journals. For example,
[Nature requires sans-serif figure lettering and prefers Helvetica or Arial](https://www.nature.com/nature/for-authors/final-submission).

For Chinese text, the skill retains TeX Gyre Heros as the primary Latin font and
uses `Microsoft YaHei` (`微软雅黑`) as the default Chinese fallback. Microsoft
YaHei is a sans-serif Chinese font that covers common Simplified Chinese glyphs
and remains clear and legible at the small sizes used in scientific figures.

### Example request

```text
Use $ultraplot-figures with results.csv. Compare the treatment groups with the
control over time, including uncertainty. The figure should show the trends and
differences between groups. Return the maintainable plotting script, PDF, and
PNG, and summarize material verification issues in the response.
```

## Installation

### 1. Install the skill with Codex

Send this request to Codex:

```text
Please use $skill-installer to install ultraplot-figures from
https://github.com/lwq-star/ultraplot-figures. The skill is at the repository
root (path `.`); install it with the name `ultraplot-figures`.
```

The skill is available on the next turn after installation. If Codex has not
discovered it, start a new task and invoke `$ultraplot-figures` again.

### 2. Install UltraPlot

Install with pip:

```bash
pip install ultraplot
```

Or install it with conda:

```bash
conda install -c conda-forge ultraplot
```

Install Cartopy separately for geographic projections. Other data-reading and
processing libraries depend on the task. See the official
[installation guide](https://ultraplot.readthedocs.io/en/stable/install.html) for
details.

Installing this skill does not install UltraPlot or its dependencies.

At use time, the skill checks GitHub for the latest stable release at most once
per local calendar day. It never downloads, installs, or replaces files during
this check. Set `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` to disable it.

## Deliverables and limits

When data or plotting source is available, Codex retains only, as needed:

- concise, independently runnable, editable plotting code;
- preprocessing code and only the final processed data used by the figure when
  substantive preprocessing is required;
- the requested final figure files, defaulting to PDF and PNG when unspecified.

Codex performs verification internally. It does not retain verification code,
notes, manifests, diagnostic renders, logs, intermediate data, exclusion tables,
or other check-only files. Material assumptions and unresolved issues are
summarized in the final response.

When the only input is a PDF or raster image, the skill can inspect only visible
content and file information. It cannot reconstruct missing data, processing,
statistical methods, or reproducible code from a rendered figure.

The skill produces static Python figures, not interactive dashboards or web
applications, and does not support generating flowcharts.

## Examples

- [2025 global M5+ earthquake skill comparison](examples/earthquake/README.md):
  uses the same data and prompt to generate figures with and without
  `$ultraplot-figures`. The case includes input data, necessary editable scripts,
  processed data used by the plot, and final PDF and PNG outputs.
- [Observed-versus-predicted model comparison](examples/correlation-scatter-plot/README.md):
  uses the same Excel data and prompt to compare LR, SVR, GBRT, and DNN across
  four land types. The case includes input data, necessary editable scripts,
  processed data used by the plot, and final PDF and PNG outputs.

## Feedback and contact

Bug reports, usability feedback, and improvement suggestions are welcome. If you
encounter an error, unclear instructions, or unexpected output, please open a
[GitHub issue](https://github.com/lwq-star/ultraplot-figures/issues). When
possible, include your Python and UltraPlot versions, the relevant prompt or
script, a minimal reproducible example, and the complete error message.

For feedback you prefer not to post publicly, contact
[laiwenqinstar@gmail.com](mailto:laiwenqinstar@gmail.com). Do not include
passwords, API keys, confidential data, or other sensitive information in an
issue or email.

## Acknowledgements

This skill is built around the open-source
[UltraPlot](https://github.com/ultraplot/ultraplot) project. We thank its
maintainers and contributors for developing and sharing the plotting library on
which this workflow is based.

Following suggestions and feedback from the UltraPlot maintainer in
[cvanelteren/ultraplot-figures](https://github.com/cvanelteren/ultraplot-figures),
the skill was comprehensively rewritten and tested, further improving the
workflow. We are grateful for the maintainer's expert guidance and support.

We also thank the [LINUX DO](https://linux.do/) community and platform for its
technical exchange, feedback, and support.

## Links

- [UltraPlot documentation](https://ultraplot.readthedocs.io/en/stable/)
- [UltraPlot source code](https://github.com/ultraplot/ultraplot)
- [License for this skill](LICENSE)
