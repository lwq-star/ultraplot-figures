# Configure the official UltraPlot MCP server

Read this reference when the first-use bootstrap reports a missing or
misaligned server, or when the user explicitly asks to configure, troubleshoot,
or repair the UltraPlot MCP server. The normal figure-task path performs a
read-only diagnostic first and is idempotent on later calls. Automatic mutation
is allowed only when that diagnostic reports a missing base package with an
explicit package policy, a missing/incompatible MCP extra, or a missing matching
entry; a `configured_without_docs` result is a docs-only enrichment exception
when a matching, version-marked tree is explicitly supplied or already present
at the standard candidate path. `unverified` discovery, review-only work,
status checks, and unverifiable package provenance remain read-only unless the
user explicitly requests repair.

The bootstrap may install the exact MCP extra matching an already installed
UltraPlot and modify one `mcp_servers.ultraplot` table. Base-package install and
upgrade are opt-in through `--package-policy install|upgrade|install-and-upgrade`
or the documented environment variables; upgrades require an exact stable
target version. It never downgrades, clones documentation, overwrites a
conflict, or changes unrelated settings. A package install can succeed while a
later configuration write fails; in that case the result carries `partial: true`
and the package change is not automatically rolled back. A configuration change
can require a new Codex task or restart. `restart_required` is a JSON boolean
field, not a status value.

By default the script reads/writes `$CODEX_HOME/config.toml`, or
`~/.codex/config.toml` when `CODEX_HOME` is unset. It does not discover a
project-level `.codex/config.toml`; pass `--config <path>` for an explicit
project or alternate configuration. The selected plotting interpreter and the
configured server command must point to the same environment.

Use the official UltraPlot and OpenAI documentation as the authority:

- <https://github.com/ultraplot/ultraplot/blob/v2.7.0/README.rst#mcp-server>
- <https://learn.chatgpt.com/docs/extend/mcp>

## 0. First-use bootstrap

Resolve `<skill-root>` from `SKILL.md`, select the plotting interpreter using
the active environment rules, then run the following with that exact
interpreter:

```powershell
& '<python.exe>' '<skill-root>\scripts\ensure_mcp.py' --bootstrap --python '<python.exe>' --json
```

From a POSIX shell, use the equivalent command:

```bash
<python> <skill-root>/scripts/ensure_mcp.py --bootstrap --python <python> --json
```

The default bootstrap policy is `manual` for the base package. To authorize a
missing-package install, add `--package-policy install --ultraplot-version 2.7.0`;
to authorize an upgrade, add `--package-policy upgrade
--ultraplot-version <newer-2.7.x>`. `install-and-upgrade` enables both. The same
policies can be selected with `ULTRAPLOT_FIGURES_PACKAGE_POLICY`, or with the
`ULTRAPLOT_FIGURES_AUTO_INSTALL_ULTRAPLOT` and
`ULTRAPLOT_FIGURES_AUTO_UPGRADE` environment flags. When both forms are set,
the package-policy variable takes precedence. In a conda or mixed
environment, pip mutation additionally requires `--allow-pip-in-conda` or
`ULTRAPLOT_FIGURES_ALLOW_PIP_IN_CONDA=1` after reviewing the environment.

For a strictly read-only preflight, replace `--bootstrap` with `--check` (or
omit the mode flag). Do this before deciding whether installation or
configuration mutation is justified.

The helper uses the selected interpreter's TOML parser. Python 3.11 and newer
include `tomllib`; on Python 3.10, install the small `tomli` dependency in that
interpreter first or use an interpreter that provides it. The helper does not
silently install a parser just to inspect Codex configuration.

The command checks the environment first. If UltraPlot is present but
`mcp`/`ultraplot.mcp` is missing or the MCP SDK is outside `mcp>=2.1,<3`, it
installs the exact matching `ultraplot[mcp]==<installed-version>` requirement,
rechecks the import and version, and then writes a matching configuration entry
when the active TOML is safe to edit. Repeated calls normally become no-ops
once the local dependency and entry are aligned; the client still has to be
reloaded before a newly written entry is callable.

If UltraPlot itself is missing, the status is `missing_ultraplot`. The default
`manual` policy returns `base_install_required`; with `--package-policy install`
or `ULTRAPLOT_FIGURES_AUTO_INSTALL_ULTRAPLOT=1`, the helper installs the exact
stable target (default `2.7.0`) as `ultraplot[mcp]`, re-probes it, and then
continues to MCP configuration. `install-and-upgrade` enables both operations.
An upgrade requires `--ultraplot-version <2.7.x>` or
`ULTRAPLOT_FIGURES_ULTRAPLOT_VERSION`, must be newer than the current version,
and never downgrades. `configured_without_docs` is a usable API/source-only
state, not full documentation readiness. When no matching documentation tree is
available, do not run the documentation verification steps below.

Editable or development UltraPlot installations with a missing or incompatible
MCP extra are reported for manual repair rather than replaced by a PyPI wheel.
Use the development checkout's documented `.[mcp]` installation flow when that
is intentional. If the editable environment already provides the MCP modules,
a safe matching configuration can still be reused or added.
Automatic setup supports the published stable UltraPlot 2.7.x series starting at
2.7.0. Older, future-major, prerelease, local-build, or unverifiable-source
versions are reported for manual repair by default. An explicit `upgrade` or
`install-and-upgrade` policy may migrate an older normal pip installation to an
exact supported 2.7.x target after the provenance checks pass.

The helper refuses to replace editable, remote, unknown, conda-managed, or
mixed package sources from PyPI by default. A reviewed conda/mixed environment
may explicitly authorize pip changes with `--allow-pip-in-conda` or
`ULTRAPLOT_FIGURES_ALLOW_PIP_IN_CONDA=1`. The JSON result exposes
`package_action`, `package_requirement`, `previous_version`, `target_version`,
`package_manager`, `partial`, and `restart_required` for auditing.

The explicit `--configure --yes` mode remains available for a requested manual repair.
When `--install-dependencies` is used there, the same package-manager guard applies:
conda/mixed environments require an explicit `--allow-pip-in-conda` review, while an
unknown package manager must be verified and repaired with its own package-manager
workflow before installing the extra; the flag does not authorize remote or editable
sources to be replaced from PyPI.

For explicit manual repair, add `--install-dependencies` only when the repair
is intended to install the matching extra. Use `--docs '<existing matching
docs>'` only for an existing directory; the bootstrap never clones a
repository. A successful configuration reports `restart_required`; start a new
Codex task or restart the client, then rerun the normal `ping` and
source-alignment checks. The statuses `configured` and
`configured_without_docs` describe local configuration, not a live server
connection. Set `ULTRAPLOT_FIGURES_MCP_AUTO_SETUP=0` to skip automatic mutation
and use the selected-runtime path when the plotting package is already
available.

If configuration reports a conflict with an existing command, table shape,
timeout, HTTP/auth transport, or environment, stop for manual review. Automatic
mode never uses `--force`; use it only after explicitly reviewing and authorizing
replacement of the command, arguments, or enabled flag. A non-standard startup
environment still requires manual review and is not repaired by `--force`.
`ultraplot_provenance_unverified` means the imported package cannot be matched
safely to its distribution source; install its MCP extra from that source
manually rather than allowing a PyPI replacement. `config_invalid`,
`interpreter_error`, `missing_ultraplot`, `base_install_required`, package
failures, and permission errors report the exact reason. A package-install
failure may have changed some packages before pip returned an error; inspect the
environment and the `partial: true` flag because changes are not automatically
rolled back. A failure after a successful install may likewise report
`partial: true`. A missing UltraPlot package is a prerequisite failure for
execution, not a successful runtime fallback.

## 1. Reuse an existing server first

Absence from an initially expanded tool list does not establish that the server
is unavailable. First perform the complete deferred-tool discovery defined in
`SKILL.md`.

If complete discovery finds `mcp__ultraplot__*` tools, call `ping`. During an
explicit setup or troubleshooting request, directly exposed matching tools may
also be used when the host has no complete registry; classify discovery as
`unverified` for the ordinary figure-task preflight in that case. An
`unverified` result is read-only and must not by itself trigger pip or a config
write. When `ping` returns `pong`, do not reinstall or register another server. Call
`get_api("ultraplot.subplots")` and compare its `source_file` with
`inspect.getsourcefile(ultraplot.subplots)` from the Python interpreter selected
for the plotting task. Canonicalize both paths as defined in `SKILL.md`; if they
belong to different environments or alignment remains unverified, keep the
plotting interpreter as the task authority and repair the MCP configuration only
when the user requested that repair.

If `ping` is absent, fails, or returns anything other than `pong`, or if
`get_api` is absent or fails, report that exact state and stop the reuse test.
For an ordinary first-use task, run the safe `--bootstrap` path only after the
read-only check identifies a missing dependency or missing matching entry; it
never overwrites a conflicting command or environment. Use the explicit repair
flow for a deliberate replacement of an existing nonstandard or mismatched
server.

When the Codex CLI is functional, `codex mcp list` can also reveal an existing
registration. Do not print unrelated configuration entries or secret values.
Do not overwrite, remove, or duplicate an existing `ultraplot` table without
first understanding its command, environment, and documentation path.

## 2. Select and inspect the plotting environment

Apply the user's active environment-selection rules before choosing Python. Use
that exact interpreter for all checks and commands. A reusable skill must not
hard-code one user's environment path.

Run a read-only inspection with the selected interpreter:

```powershell
& '<python.exe>' -c "import importlib.util, sys, ultraplot; print(sys.executable); print(ultraplot.__version__); print(ultraplot.__file__); print(importlib.util.find_spec('ultraplot.mcp')); print(importlib.util.find_spec('mcp'))"
```

UltraPlot 2.7.0 in the supported 2.x series provides the `ultraplot-mcp` entry point and declares
`mcp>=2.1,<3` in the `mcp` extra. A normal `ultraplot` installation, including
the `all` extra, does not necessarily install that optional SDK.

If UltraPlot is already installed but the MCP dependency is missing or
incompatible, the automatic bootstrap preserves the requested UltraPlot
version and uses the selected interpreter:

```powershell
& '<python.exe>' -m pip install 'ultraplot[mcp]==<installed-version>'
```

The POSIX form is:

```bash
<python> -m pip install 'ultraplot[mcp]==<installed-version>'
```

This may cause pip to reinstall the same distribution or resolve related
dependencies. It does not automatically roll back a successful package change
if a later configuration write fails; inspect a `partial` result before retrying.
Do not use a bare `pip`, and do not silently replace a non-PyPI/editable source.

Do not upgrade UltraPlot merely to configure MCP. An upgrade is allowed only
when the user explicitly selects the `upgrade` or `install-and-upgrade` policy
and supplies an exact newer 2.7.x target. For a development checkout, follow
the official `pip install -e '.[mcp]'` workflow from that checkout instead.

## 3. Configure Codex with the same environment

Codex desktop, CLI, and IDE clients on the same host share MCP configuration.
The automatic path uses the active user configuration `$CODEX_HOME/config.toml`,
or `~/.codex/config.toml` when `CODEX_HOME` is unset. A project-level
`.codex/config.toml` is not selected automatically; pass its absolute path with
`--config` during an explicit setup or repair. Preserve every unrelated setting.
One user-level entry cannot safely represent several different plotting
interpreters, so repeat setup with an explicit configuration path when projects
need different environments.

The most deterministic configuration launches the selected interpreter as a
module and does not depend on `PATH`:

```toml
[mcp_servers.ultraplot]
command = 'D:\path\to\selected\python.exe'
args = ["-m", "ultraplot.mcp"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Existing optional Codex fields are preserved. In particular, `env_vars` may be
a string array such as `env_vars = ["CODEX_WINDOWS_REGISTERED_CORE"]`; any
inherited environment, custom `cwd`, or non-documentation `env` override is
reported as unverified and is not silently rewritten. Timeout values must be
positive finite numbers. URL/auth transport fields such as `url`,
`bearer_token_env_var`, `http_headers`, `env_http_headers`, and
`mcp_oauth_callback_port` cannot be mixed with this managed stdio entry and
require manual review.

TOML single-quoted strings are convenient for Windows paths because backslashes
remain literal. With double-quoted strings, escape each backslash; forward
slashes are also valid in Windows Python paths.

Codex desktop can configure the same STDIO server through **Settings -> MCP
servers -> Add server**. Save it and select **Restart**. If the Codex CLI and
the selected environment are both correctly resolved, either of these official
registration paths is also valid:

```powershell
Get-Command codex -All
& '<python.exe>' -c "import shutil; print(shutil.which('codex')); print(shutil.which('ultraplot-mcp'))"
codex mcp add ultraplot -- '<python.exe>' -m ultraplot.mcp
& '<environment>\Scripts\ultraplot-mcp.exe' install codex
```

For the manual `codex mcp add` command, `Get-Command codex -All` shows
PowerShell's resolution order. The convenience installer instead uses Python's
`shutil.which()`: it requires `codex` on `PATH`, prefers an `ultraplot-mcp`
entry on `PATH`, and falls back to the current Python interpreter with
`-m ultraplot.mcp` when that entry is absent. Use the selected interpreter's
read-only check above to predict its choices. Bare `where` is a PowerShell
`Where-Object` alias, while `where.exe` omits PowerShell scripts and is not
equivalent to either resolution mechanism. If a wrong or broken Codex shim is
selected, use desktop settings or edit `config.toml` directly rather than
blocking setup.

## 4. Provide the official documentation tree

The UltraPlot wheel currently does not bundle its documentation. Without a
separate, version-matching documentation tree, `ping`, `get_api`, and
`get_source` may still work, but `search_docs`, `search_release_notes`, and
`read_doc` cannot provide their full results. This is reported as
`configured_without_docs`; do not treat it as a failed API/source setup, and do
not run documentation checks until a version-matched tree is configured.

Use an official checkout matching the installed version. Creating it is an
external write, so do this only within an explicit setup or repair request. The
automatic candidate path is deliberately conservative: it accepts a directory
under `$CODEX_HOME/mcp-sources/ultraplot-<version>/docs` only when both
`conf.py` and `index.rst` are present and the directory marker matches the
selected runtime version. An arbitrary directory containing one `.rst` file is
not treated as official documentation. `ULTRAPLOT_MCP_DOCS` is considered an
automatic candidate only when it resolves under that same `mcp-sources` root;
use explicit `--docs` for a deliberately different checkout.

```powershell
git clone --depth 1 --branch 'v<installed-version>' https://github.com/ultraplot/ultraplot.git '<checkout-directory>'
```

Confirm that `<checkout-directory>/docs` exists and corresponds to the installed
UltraPlot version, then add its absolute path. For an explicitly supplied path,
the helper preserves the user's choice; the caller must confirm its checkout
and version before using version-sensitive documentation or release-note calls:

```toml
[mcp_servers.ultraplot.env]
ULTRAPLOT_MCP_DOCS = 'D:\path\to\matching-ultraplot-checkout\docs'
```

Do not point this variable at a directory that merely contains plotting outputs
or an installed wheel. Installing the `docs` extra supplies documentation-build
dependencies, not the missing source documentation tree.

## 5. Use `uvx` only when isolation is intentional

The official portable launch command is:

```powershell
uvx --from 'ultraplot[mcp]' ultraplot-mcp
```

`uvx` creates an isolated environment, so its live API may differ from the
environment running the plotting script. For reproducible use, pin the intended
version and still configure `ULTRAPLOT_MCP_DOCS`:

```toml
[mcp_servers.ultraplot]
command = 'D:\path\to\uvx.exe'
args = ["--from", "ultraplot[mcp]==<version>", "ultraplot-mcp"]
startup_timeout_sec = 60

[mcp_servers.ultraplot.env]
ULTRAPLOT_MCP_DOCS = 'D:\path\to\matching-ultraplot-checkout\docs'
```

Prefer the selected-interpreter configuration for this skill because it keeps
API inspection aligned with the actual plotting runtime.

## 6. Restart and verify

After changing configuration, restart Codex (or start a new task) and inspect
`/mcp`. Then verify in this order:

1. `ping` returns `pong`.
2. `get_api("ultraplot.subplots")` succeeds and its `source_file` belongs to the
   selected plotting environment.
3. If a matching docs tree is configured, `search_docs("shared colorbars")`
   returns an official documentation path.
4. If step 3 succeeds, `read_doc` can open one path returned by `search_docs`.
5. If documentation is configured, `search_release_notes("MCP server")`
   returns release notes whose version matches the selected UltraPlot runtime.

Do not treat successful connection as figure validation. Still run the plotting
script with the selected interpreter and inspect every requested final export.

## 7. Troubleshoot narrowly

- `No module named mcp`: install the version-matched `ultraplot[mcp]` extra in
  the selected environment; do not use a bare `pip`.
- `missing_ultraplot` / `base_install_required`: the base package is absent and
  the default `manual` policy did not authorize installation. Use
  `--package-policy install --ultraplot-version 2.7.0` (or the documented
  environment flag) when a pip installation is intended.
- `unsupported_ultraplot_version`: automatic setup supports the published stable
  UltraPlot 2.7.x series; future-major, prerelease/local builds and older
  versions require manual repair or an explicitly authorized upgrade to a stable
  target.
- `upgrade_target_required` / `package_target_invalid`: supply an exact stable
  2.7.x target with `--ultraplot-version`; the helper never guesses a moving
  latest version or downgrades.
- `package_manager_requires_manual` / `upgrade_requires_manual`: the selected
  package is conda-managed, mixed, editable, remote, or otherwise not a normal
  pip installation. Use the environment's package manager, or explicitly review
  and enable `--allow-pip-in-conda` for a conda/mixed pip operation.
- `ultraplot_provenance_unverified`: the imported module and installed
  distribution metadata do not identify the same trusted source. Do not let the
  helper install a PyPI extra over it; use the source checkout or package
  manager's documented MCP installation flow.
- `missing_mcp_dependency`: the base package is present, but the matching MCP
  extra or SDK version is absent; install the exact extra shown by the check.
- `needs_configuration`: the MCP modules are available, but the selected
  configuration has no aligned enabled entry. Automatic mode may add one only
  when the existing TOML is safe to edit.
- `configuration_verification_failed`: a write was attempted, but a fresh
  read-back did not establish the expected entry. Inspect the file and current
  `--check` result before retrying; do not assume the write was rolled back.
- `configuration_conflict`: the existing entry or TOML structure (including an
  inline, dotted, multiline, or otherwise complex table/value, invalid timeout,
  or mixed HTTP/auth transport) is not safe for the conservative editor.
  Preserve it and review it manually; do not force an automatic replacement.
- `partial: true`: the package step or another mutation may already have changed the
  environment or configuration (including `config_changed: true`). Inspect the
  reported reason and current `--check` state before retrying; there is no
  automatic pip rollback.
- `base_install_disabled`: an install policy was requested but the selected
  environment was not eligible for an automatic pip mutation. Review
  `package_manager` and the provenance fields before choosing a package-manager
  specific repair.
- `package_verification_failed`: pip returned, but the selected interpreter did
  not expose the exact requested version or trusted provenance. Treat the
  environment as potentially changed and inspect it before retrying.
- `configured_without_docs`: API/source calls can be tested, but configure a
  matching docs tree before testing documentation or release-note tools.
- `restart_required: true`: restart Codex or start a new task before concluding
  that the newly written entry is unavailable. This is a JSON boolean field,
  not a status value.
- `ultraplot-mcp` is not on `PATH`: use the absolute executable or the preferred
  `<python.exe> -m ultraplot.mcp` configuration.
- Documentation reports that it is not installed: correct
  `ULTRAPLOT_MCP_DOCS` and restart Codex.
- `get_api` reports a different environment: replace the server command with
  the intended absolute interpreter path.
- Initial `uvx` startup times out: confirm network/package resolution and use a
  longer `startup_timeout_sec`; do not hide a persistent startup failure.
- Windows TOML parsing fails: use literal single-quoted paths or escaped
  backslashes.
- The CLI cannot list or add servers: use desktop settings or edit the shared
  `config.toml` directly.

The current UltraPlot MCP tools are operationally read-only but may not publish
read-only protocol annotations. Do not weaken approval settings for the entire
server merely to suppress prompts; keep normal Codex approval behavior unless
the user deliberately chooses another policy.
