**English** | [简体中文](README_zh.md)

# UltraPlot Figures Skill

> Make, revise, and check static scientific figures with UltraPlot.

[GitHub repository](https://github.com/lwq-star/ultraplot-figures)

`ultraplot-figures` is a Codex skill. Give it your data and explain what the figure should show; Codex will write an editable Python script, make the figure, and check the output files. It can also revise an existing plotting script or inspect a PDF, TIFF, SVG, or PNG.

> [!CAUTION]
> **Do not submit a figure produced or revised by this skill without author review.** Generated code, figures, and check results can contain errors. The skill can check data filters, variable mappings, layout, and exported files, but it cannot decide whether the data, methods, statistics, or conclusions are sound. Before submission, review the data and code, make sure the manuscript, figure, and caption agree, and check the journal's latest official instructions.

## Where to use it

Use this skill in a Codex Desktop or Codex CLI conversation that can load local skills. It is not a standalone plotting program and is not imported as a Python package.

It is useful when you want Codex to:

- make a figure from a dataset;
- suggest a suitable figure when you are not sure what to plot;
- revise an existing script or figure;
- prepare files for a journal or publisher;
- check an exported figure's size, resolution, fonts, and other file settings.

## Why this project

This project helps AI write reproducible code for scientific figures. The workflow covers understanding the data and figure goal, producing an editable script, exporting final figures, and reviewing the result.

General AI can quickly produce plotting code, but a script that runs is not necessarily reproducible, scientifically clear, or ready for submission. This skill adds a focused UltraPlot workflow that:

- selects a suitable figure from the data structure, scientific question, and intended reader, offering several clear options when the goal is uncertain;
- produces runnable Python code from input data to final figure, separating heavy preprocessing from plotting when needed;
- handles common scientific-figure needs such as multi-panel layouts, journal sizing, accessible color, legends, maps, rasters, Taylor diagrams, and omics figures;
- keeps internal contracts, QA helpers, temporary checks, and final deliverables separate so the delivered script stays standalone, then checks the result against the request before author review.

The project will be maintained while AI models still need extra guidance to produce reproducible scientific figures reliably, with updates following UltraPlot and journal requirements. It can be simplified when these capabilities become reliable model defaults.

## Installation

### Install from GitHub with Codex

Ask Codex to install the skill from the repository root:

```text
Please use $skill-installer to install ultraplot-figures from https://github.com/lwq-star/ultraplot-figures. The skill is at the repository root (path `.`); install it with the name `ultraplot-figures`.
```

After installation, call the skill on the next turn. If Codex has not discovered the
new skill yet, start a new task and call it by name.

### Install manually

1. Download or clone the [GitHub repository](https://github.com/lwq-star/ultraplot-figures).
2. Copy it to `$CODEX_HOME/skills/ultraplot-figures`. If `CODEX_HOME` is not set, the usual locations are:
   - Windows: `%USERPROFILE%\.codex\skills\ultraplot-figures`
   - macOS/Linux: `~/.codex/skills/ultraplot-figures`
3. Confirm that `SKILL.md`, `VERSION`, `agents/`, `references/`, and `scripts/` are directly inside that folder. The README files and `examples/` are project documentation.
4. Call `$ultraplot-figures` on the next turn. If it is not discovered, start a new Codex task and try again.

Installing the skill folder does not install its Python libraries.

## Release update checks

The installed version is recorded in `VERSION`. When the skill is used, it checks the
latest stable [GitHub Release](https://github.com/lwq-star/ultraplot-figures/releases)
at most once per local calendar day. This is a use-time check, not a background
service.

- The check never downloads, installs, or replaces skill files.
- When a newer stable Release is available, Codex reports the current and latest
  versions, recommends updating, links the Release, and gives you a copy-ready request
  to send to Codex.
- Set `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` to disable automatic checks.

Copy-ready update request:

```text
Please update my installed ultraplot-figures skill to the latest stable release: https://github.com/lwq-star/ultraplot-figures/releases/latest
```

Manual commands:

```bash
python scripts/update_skill.py --check
python scripts/update_skill.py --auto
python scripts/update_skill.py --self-test
```

## Before you start

You need:

- Codex Desktop or Codex CLI with local skill support;
- Python 3.10 or newer in an environment that Codex can run;
- UltraPlot, Matplotlib, and NumPy in that environment;
- readable paths to the data, script, or figure you want to use.

The skill has been checked with UltraPlot 2.4.x. Pandas is used for tabular data, Pillow and `pypdf` for file checks, `openpyxl` for Excel files, and `pyarrow` is commonly needed for Parquet. Maps, statistics, and omics figures may need additional packages. Install only what your task needs. If you are preparing a submission, also have the journal's current figure instructions available when possible.

## Quick start

Mention the skill name, the input file, what you want readers to see, and the files you need:

```text
Please use $ultraplot-figures.
Data: [file or folder path]
Show: [variables, comparison, trend, or map]
Purpose: [what readers should understand from the figure]
Output: [Python script and PDF/TIFF/SVG/PNG]
```

If you do not know what to plot, say: “Please inspect the data first, suggest 1–3 suitable figures, explain what each one would show, and recommend one.”

## Contents

- [Where to use it](#where-to-use-it)
- [Why this project](#why-this-project)
- [Installation](#installation)
- [Release update checks](#release-update-checks)
- [Before you start](#before-you-start)
- [Quick start](#quick-start)
- [Examples](#examples)
- [How it works](#how-it-works)
- [What you receive](#what-you-receive)
- [Journal requirements and final checks](#journal-requirements-and-final-checks)
- [Default font settings](#default-font-settings)
- [Supported figure types](#supported-figure-types)
- [Limits](#limits)
- [Feedback and contact](#feedback-and-contact)
- [Software and projects referenced](#software-and-projects-referenced)
- [Acknowledgements](#acknowledgements)
- [Scientific references](#scientific-references)

## Examples

- [2025 global M5+ earthquake skill comparison](examples/earthquake-skill-comparison/README.md):
  uses the same data and prompt with and without `$ultraplot-figures`. It includes
  the input data, editable scripts, PDF and TIFF
  outputs, preview images, and file information.
- [Observed-versus-predicted model comparison](examples/correlation-scatter-plot/README.md):
  compares LR, SVR, GBRT, and DNN across four land types using the same Excel data
  and prompt. It includes the input data, editable scripts, PDF and TIFF outputs,
  preview images, and file information.

## How it works

1. Codex reads the files and checks what you want to show, which records to use, and which files to return.
2. It maps each requested reader judgment to suitable visual evidence. An explicit request for one chart stays one chart; a request for several scientific aspects may need the minimum set of panels that makes each aspect readable.
3. If the figure is not yet clear, it looks at the data and suggests 1–3 suitable options. It asks a question only when the choice would change the meaning of the figure.
4. Large cleaning, merging, modeling, or reprojection work is kept separate from the plotting script.
5. Codex makes a draft, checks the content and layout, writes the final files, and checks those files again.

Internal task contracts and Skill QA calls remain in temporary validation code; they
are not included in the delivered plotting script.

Journal, map, statistical, and multi-panel tasks receive the extra checks they need. The skill does not add panels or scientific claims that you did not request and the data do not support.

## What you receive

- a runnable Python plotting script;
- a separate preprocessing script and checked intermediate data when needed;
- the requested PDF, TIFF, SVG, or PNG files;
- a short note listing important filters, record counts, final dimensions, checks, and anything that still needs author review.

Use the script and input data when making later changes. Exported figures are outputs, not a replacement for the source files.

## Journal requirements and final checks

Journal requirements vary, so the skill handles the target as follows:

- **When you name a journal or publisher:** its latest official instructions become the target for size, format, resolution, fonts, transparency, and file limits.
- **When some settings are missing:** explicit settings are preserved and only missing settings receive defaults. If venue and width are unknown, the size fallback uses the current `nat2` width of 183 mm with automatic height. If formats are unknown, the default is PDF plus TIFF; a TIFF with otherwise unspecified artifact settings uses 600 dpi, opaque RGB, and lossless LZW. These are Skill fallbacks, not universal journal rules.

Before handing over a figure, the skill checks:

1. whether every requested reader judgment has suitable evidence and the correct records, filters, panels, variables, units, and labels were used;
2. whether text, legends, color bars, and plotted data are readable and do not overlap or get cut off;
3. whether the exported file has the requested format, size, resolution, transparency, and other file settings; PDF/SVG font resources can be inspected, while raster text is checked visually;
4. whether the delivered Python plotting script is standalone and free of internal contracts, evidence registries, and Skill QA calls;
5. whether the final figure is understandable at the size at which it will be used.

## Default font settings

If no journal or font is specified, the default is 9 pt sans-serif TeX Gyre Heros. It is an open Helvetica-style font that stays clear at small figure sizes and is easy to reproduce across systems. It follows the sans-serif style common in many journals. For example, [Nature asks for sans-serif figure lettering and prefers Helvetica or Arial](https://www.nature.com/nature/for-authors/final-submission).

## Supported figure types

The skill supports line and scatter plots, bars and interval plots, distributions, heatmaps, contours, maps, raster and climate fields, Taylor diagrams, model diagnostics, volcano and Manhattan plots, PCA/UMAP, and other static multi-panel figures.

## Limits

- The normal output is a static Python figure, not an interactive dashboard or web app.
- Checks that depend on the source data, analysis, or plotting code cannot be completed from an exported figure alone.

## Feedback and contact

Bug reports, usability feedback, and improvement suggestions are welcome. If you encounter an error, unclear instructions, unexpected output, or anything that does not meet your needs, please open a [GitHub issue](https://github.com/lwq-star/ultraplot-figures/issues). When possible, include your Python and UltraPlot versions, the relevant prompt or script, a minimal reproducible example, and the complete error message.

For feedback you prefer not to post publicly, contact [laiwenqinstar@gmail.com](mailto:laiwenqinstar@gmail.com). Please do not include passwords, API keys, confidential data, or other sensitive information.

## Software and projects referenced

The skill uses or directly refers to these GitHub projects:

- [UltraPlot](https://github.com/ultraplot/ultraplot)
- [Matplotlib](https://github.com/matplotlib/matplotlib)
- [NumPy](https://github.com/numpy/numpy)
- [pandas](https://github.com/pandas-dev/pandas)
- [Pillow](https://github.com/python-pillow/Pillow)
- [pypdf](https://github.com/py-pdf/pypdf)
- [Cartopy](https://github.com/SciTools/cartopy)

The workflow was also compared with these open-source plotting skills:

- [K-Dense scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills/tree/main/skills/scientific-visualization)
- [scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill)
- [nature-skills](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-figure)
- [pythesis-plot](https://github.com/stephenlzc/pythesis-plot)
- [scientific-plotting-skill](https://github.com/dazhiyang/scientific-plotting-skill)

## Acknowledgements

This skill is built around the open-source [UltraPlot](https://github.com/ultraplot/ultraplot) project. We sincerely thank its maintainers and contributors for developing and sharing the plotting library that makes this workflow possible.

We also thank the [LINUX DO](https://linux.do/) community and platform for the technical exchange, feedback, and support that have helped this project grow.

## Scientific references

The figure-planning, visual-encoding, uncertainty, readability, and color rules also draw on these publications:

- Cleveland, W. S., & McGill, R. (1984). Graphical perception: Theory, experimentation, and application to the development of graphical methods. *Journal of the American Statistical Association*. [DOI](https://doi.org/10.2307/2288400)
- Cleveland, W. S., & McGill, R. (1985). Graphical perception and graphical methods for analyzing scientific data. *Science*. [DOI](https://doi.org/10.1126/science.229.4716.828)
- Kelleher, C., & Wagener, T. (2011). Ten guidelines for effective data visualization in scientific publications. *Environmental Modelling & Software*. [DOI](https://doi.org/10.1016/j.envsoft.2010.12.006)
- Rougier, N. P., Droettboom, M., & Bourne, P. E. (2014). Ten simple rules for better figures. *PLOS Computational Biology*. [DOI](https://doi.org/10.1371/journal.pcbi.1003833)
- Weissgerber, T. L., Milic, N. M., Winham, S. J., & Garovic, V. D. (2015). Beyond bar and line graphs: Time for a new data presentation paradigm. *PLOS Biology*. [DOI](https://doi.org/10.1371/journal.pbio.1002128)
- Midway, S. R. (2020). Principles of effective data visualization. *Patterns*. [DOI](https://doi.org/10.1016/j.patter.2020.100141)
- Jambor, H. K., et al. (2021). Creating clear and informative image-based figures for scientific publications. *PLOS Biology*. [DOI](https://doi.org/10.1371/journal.pbio.3001161)
- Crameri, F., Shephard, G. E., & Heron, P. J. (2020). The misuse of colour in science communication. *Nature Communications*. [DOI](https://doi.org/10.1038/s41467-020-19160-7)
- Wong, B. (2011). Points of view: Color blindness. *Nature Methods*. [DOI](https://doi.org/10.1038/nmeth.1618)

Color resource: [Okabe and Ito, Color Universal Design](https://jfly.uni-koeln.de/color/).
