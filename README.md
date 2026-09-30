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

For a new publication figure with no width guidance, the skill may use
UltraPlot's `nat2` preset (183 mm wide). It produces publication-oriented PDF
and PNG exports when no format is requested; honor the user's, journal's, or
existing project's dimensions and formats when they are specified.

Preserve the effective UltraPlot font configuration by default. When no font
guidance exists, use an installed, reproducible font appropriate to the project
or journal rather than imposing a new global font. Many journals prefer a
clear sans-serif style; for example,
[Nature requires sans-serif figure lettering and prefers Helvetica or Arial](https://www.nature.com/nature/for-authors/final-submission).

For Chinese text, choose an installed local CJK fallback that matches the user,
journal, or project. `Microsoft YaHei` (`微软雅黑`) is one possible example
when it is already installed; the skill does not download or globally install
fonts. Use a requested or established raster DPI, and do not force DPI settings
on vector-only output.

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

Install UltraPlot into the interpreter that will run the plotting script. Use
that same interpreter for the MCP server; do not rely on a bare `pip` from an
unrelated environment:

```bash
<python> -m pip install "ultraplot[mcp]==2.7.0"
```

Use another exact stable 2.7.x target only when the project requires it; avoid
an unbounded install that could select an unsupported future release.

Or install it with conda:

```bash
conda install -n <environment> -c conda-forge ultraplot
```

Replace `<python>` and `<environment>` with the interpreter/environment selected
by the active host and project rules. On Windows PowerShell, an explicit
interpreter is commonly invoked as `& 'D:\path\to\python.exe' -m pip ...`;
on POSIX shells use `/path/to/python -m pip ...`.

Install Cartopy separately for geographic projections. Other data-reading and
processing libraries depend on the task. See the official
[installation guide](https://ultraplot.readthedocs.io/en/stable/install.html) for
details.

Installing or updating this skill does not execute package setup. The first
invocation after an install or update performs a read-only preflight in the
selected plotting environment, then may run the safe, idempotent MCP bootstrap
when its conditions are met. Normal figure tasks repeat the same preflight on
later invocations; a persistent first-use marker is not assumed. Review-only,
status, and troubleshooting tasks keep the whole flow read-only unless repair
is explicitly requested.

The base-package policy defaults to `manual`. To authorize a missing-package
installation, use `--package-policy install` (or
`ULTRAPLOT_FIGURES_AUTO_INSTALL_ULTRAPLOT=1`). To authorize an exact-target
upgrade, use `--package-policy upgrade --ultraplot-version 2.7.1` (or set
`ULTRAPLOT_FIGURES_AUTO_UPGRADE=1` together with
`ULTRAPLOT_FIGURES_ULTRAPLOT_VERSION`). `install-and-upgrade` enables both.
When both forms are set, `ULTRAPLOT_FIGURES_PACKAGE_POLICY` takes precedence
over the boolean aliases.
The helper installs `ultraplot[mcp]` at the requested stable 2.7.x version in
the selected interpreter and never downgrades. If UltraPlot is missing and the
policy remains `manual`, the result is `base_install_required` and a plotting
task must stop until the package is installed or the policy is explicitly
enabled.

### 3. UltraPlot MCP

The supported automatic setup contract is the stable UltraPlot 2.7.x series
starting at 2.7.0; it provides an official MCP server for API, documentation,
example, release-note, and source inspection. Codex checks MCP availability as
part of the figure workflow; a configured entry is not considered callable
until the client has reloaded it.

When an explicit check says repair is needed, the bootstrap can install
`ultraplot[mcp]==<installed-version>` and, when the active TOML is safe to edit,
write a matching `mcp_servers.ultraplot` entry. Base installation and upgrades
are separately policy-controlled and use an exact stable target. Editable,
remote, unknown, conda-managed, or mixed installations are not replaced from
PyPI by default; a reviewed conda/mixed environment can be explicitly allowed
with `--allow-pip-in-conda` or `ULTRAPLOT_FIGURES_ALLOW_PIP_IN_CONDA=1`. The
bootstrap never downgrades, clones documentation, overwrites a conflicting
entry, modifies unrelated settings, or restarts Codex. Automatic MCP setup
applies only to the published stable UltraPlot 2.7.x series; older,
future-major, prerelease, local-build, or unverifiable-source versions are
reported for manual repair by default. An explicitly authorized exact-target
upgrade may migrate an older verified pip installation to supported 2.7.x.

The default automatic target is the active user configuration
`$CODEX_HOME/config.toml`, or `~/.codex/config.toml` when `CODEX_HOME` is not
set. A project-level `.codex/config.toml` is not discovered automatically;
select it explicitly during a manual repair with `--config`. The selected
interpreter and the server command must refer to the same environment.

The result distinguishes local readiness from live availability. `configured`
means the dependency and entry are locally aligned; `configured_without_docs`
means API/source calls may work but documentation and release-note searches are
not available. `restart_required` is a JSON boolean field; when it is `true`,
the client must be restarted or a new task started before the entry can be used.
When a matching documentation tree is already available, bootstrap may add
only its documentation path to a `configured_without_docs` entry. Automatic
documentation enrichment accepts only a version-marked checkout (for example,
`ultraplot-2.7.0/docs` with both `conf.py` and `index.rst`); an explicitly
supplied path still needs manual version confirmation. If the dependency install succeeds
but a later mutation fails, the result may carry `partial: true`: pip can have
changed packages before returning an error, and no package change is
automatically rolled back. Review the reported reason and current environment.
Conflicts, invalid configuration, permissions, package failures, and a failed
post-write verification never use `--force` automatically. Set
`ULTRAPLOT_FIGURES_MCP_AUTO_SETUP=0` to opt out;
opted-out or `unverified` discovery is read-only and does not trigger pip or
configuration writes.

The standalone skill installer copies skill files and cannot run a process-level
startup hook; therefore the check runs when the installed or updated skill is
first invoked, not when the install command returns. The separate release
check usually runs at most once per local calendar day for the same installed
skill version. Network errors, missing metadata, and non-stable release
metadata fail open; the check never downloads, installs, or replaces skill
files. Set `ULTRAPLOT_FIGURES_UPDATE_CHECK=0` to disable it.

## Deliverables and limits

When data or plotting source is available, Codex retains only, as needed:

- concise, independently runnable, editable plotting code;
- preprocessing code and only the final processed data used by the figure when
  substantive preprocessing is required;
- the requested final figure files; for publication-oriented static figures,
  PDF and PNG are the usual defaults when no format is specified.

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

Complete examples are maintained in the separate
[`ultraplot-figures-examples`](https://github.com/lwq-star/ultraplot-figures-examples)
repository, so installing this skill does not download example data or rendered
outputs.

- [2025 global M5+ earthquake skill comparison](https://github.com/lwq-star/ultraplot-figures-examples/blob/v1.0.0/examples/earthquake/README.md):
  uses the same data and prompt to generate figures with and without
  `$ultraplot-figures`. The case includes input data, necessary editable scripts,
  and final PDF and PNG outputs.
- [Observed-versus-predicted model comparison](https://github.com/lwq-star/ultraplot-figures-examples/blob/v1.0.0/examples/correlation-scatter-plot/README.md):
  uses the same Excel data and prompt to compare LR, SVR, GBRT, and DNN across
  four land types. The case includes input data, necessary editable scripts, and
  final PDF and PNG outputs.

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
