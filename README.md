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

If no journal or font is specified, the default is 9 pt sans-serif TeX Gyre
Heros. It is an open-source Helvetica-style font that remains clear at small
figure sizes and is easy to reproduce across systems. It matches the sans-serif
style commonly required by many journals. For example,
[Nature requires sans-serif figure lettering and prefers Helvetica or Arial](https://www.nature.com/nature/for-authors/final-submission).

Existing typography settings in `ultraplotrc`, session-level `uplt.rc`, or an
active rc context count as a font specification. Explicit user requirements and
current target-journal instructions take precedence over this default.

### Example request

```text
Use $ultraplot-figures with results.csv. Compare the treatment groups with the
control over time, including uncertainty. The figure should show the trends and
differences between groups. Return the plotting script, PDF, PNG, and verification
notes.
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

When data or plotting source is available, Codex returns, as needed:

- an independently runnable, editable Python plotting script;
- a separate processing script and processed data when substantive processing is
  required;
- PDF and PNG files at the requested dimensions;
- verification notes covering key assumptions, data processing, output dimensions,
  and unresolved issues.

When the only input is a PDF or raster image, the skill can inspect only visible
content and file information. It cannot reconstruct missing data, processing,
statistical methods, or reproducible code from a rendered figure.

The skill produces static Python figures, not interactive dashboards or web
applications. Some UltraPlot features require additional dependencies. Explicit
user requirements and current journal instructions take precedence over defaults.

## Examples

- [2025 global M5+ earthquake skill comparison](examples/earthquake/README.md):
  uses the same data and prompt to generate figures with and without
  `$ultraplot-figures`. The case includes input data, editable scripts, PDF and
  PNG outputs, preview images, and file information.
- [Observed-versus-predicted model comparison](examples/correlation-scatter-plot/README.md):
  uses the same Excel data and prompt to compare LR, SVR, GBRT, and DNN across
  four land types. The case includes input data, editable scripts, PDF and PNG
  outputs, preview images, and verification information.

These cases illustrate the workflow and are not performance benchmarks.

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

Version 1.0 was comprehensively rewritten and tested in response to suggestions
and feedback from the UltraPlot maintainer, reflected in
[cvanelteren/ultraplot-figures](https://github.com/cvanelteren/ultraplot-figures).
We are grateful for this expert guidance and support.

We also thank the [LINUX DO](https://linux.do/) community and platform for its
technical exchange, feedback, and support.

## Links

- [UltraPlot documentation](https://ultraplot.readthedocs.io/en/stable/)
- [UltraPlot source code](https://github.com/ultraplot/ultraplot)
- [License for this skill](LICENSE)
