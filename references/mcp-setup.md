# Configure the official UltraPlot MCP server

Read this reference when the first-use bootstrap reports a missing or
misaligned server, or when the user explicitly asks to configure, troubleshoot,
or repair the UltraPlot MCP server. Begin with read-only diagnostics. A
configuration repair can install packages, modify persistent Codex settings,
and require a Codex restart; perform only the changes the user authorized. Do
not clone documentation or change unrelated settings as part of an ordinary
figure task.

Use the official UltraPlot and OpenAI documentation as the authority:

- <https://github.com/ultraplot/ultraplot/blob/v2.7.0/README.rst#mcp-server>
- <https://learn.chatgpt.com/docs/extend/mcp>

## 0. First-use bootstrap

Resolve `<skill-root>` from `SKILL.md`, then run the bundled check with the
interpreter selected for plotting:

```powershell
& '<python.exe>' '<skill-root>\scripts\ensure_mcp.py' --check --json
```

The check does not install packages or write configuration. If it reports
`needs_configuration` or `missing_mcp_dependency` and the user has authorized
the first-use mutation, run:

```powershell
& '<python.exe>' '<skill-root>\scripts\ensure_mcp.py' --configure --yes --json
```

Use `--install-dependencies` only with separate authorization to install the
matching `ultraplot[mcp]` extra. Use `--docs '<existing matching docs>'` only for
an existing directory; the bootstrap never clones a repository. A successful
configuration reports `restart_required`; start a new Codex task or restart the
client, then rerun the normal `ping` and source-alignment checks.

If configuration reports a conflict with an existing command, table shape, or
environment, stop for manual review. Use `--force` only after the user
explicitly authorizes replacing the reviewed command. `config_invalid` and
`interpreter_error` are read-only failures: preserve the file and continue with
the selected-runtime fallback after reporting the exact reason.

## 1. Reuse an existing server first

Absence from an initially expanded tool list does not establish that the server
is unavailable. First perform the complete deferred-tool discovery defined in
`SKILL.md`.

If complete discovery finds `mcp__ultraplot__*` tools, call `ping`. During an
explicit setup or troubleshooting request, directly exposed matching tools may
also be used when the host has no complete registry; classify discovery as
unverified for the ordinary figure-task preflight in that case. When `ping`
returns `pong`, do not reinstall or register another server. Call
`get_api("ultraplot.subplots")` and compare its `source_file` with
`inspect.getsourcefile(ultraplot.subplots)` from the Python interpreter selected
for the plotting task. Canonicalize both paths as defined in `SKILL.md`; if they
belong to different environments or alignment remains unverified, keep the
plotting interpreter as the task authority and repair the MCP configuration only
when the user requested that repair.

If `ping` is absent, fails, or returns anything other than `pong`, or if
`get_api` is absent or fails, report that exact state and stop the reuse test. Do
not infer that the server is unconfigured. Continue into configuration changes
only when the user requested the corresponding setup or repair.

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

UltraPlot 2.7.0 provides the `ultraplot-mcp` entry point and declares
`mcp>=2.1,<3` in the `mcp` extra. A normal `ultraplot` installation, including
the `all` extra, does not necessarily install that optional SDK.

If UltraPlot is already installed but the MCP dependency is missing, and the
user authorized installation, preserve the installed UltraPlot version:

```powershell
& '<python.exe>' -m pip install 'ultraplot[mcp]==<installed-version>'
```

Do not upgrade UltraPlot merely to configure MCP unless the user explicitly
requested an upgrade. For a development checkout, follow the official
`pip install -e '.[mcp]'` workflow from that checkout instead.

## 3. Configure Codex with the same environment

Codex desktop, CLI, and IDE clients on the same host share MCP configuration.
User-level configuration is normally `~/.codex/config.toml`; a trusted project
may instead use `.codex/config.toml`. Preserve every unrelated setting.

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
separate documentation tree, `ping`, `get_api`, and `get_source` still work,
but `search_docs`, `search_release_notes`, and `read_doc` cannot provide their
full results.

Use an official checkout matching the installed version. Creating it is an
external write, so do this only within an explicit setup or repair request:

```powershell
git clone --depth 1 --branch 'v<installed-version>' https://github.com/ultraplot/ultraplot.git '<checkout-directory>'
```

Confirm that `<checkout-directory>/docs` exists, then add its absolute path:

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

After changing configuration, restart Codex and inspect `/mcp`. Then verify in
this order:

1. `ping` returns `pong`.
2. `get_api("ultraplot.subplots")` succeeds and its `source_file` belongs to the
   selected plotting environment.
3. `search_docs("shared colorbars")` returns an official documentation path.
4. `read_doc` can open one path returned by `search_docs`.
5. `search_release_notes("MCP server")` returns release notes whose version
   matches the selected UltraPlot runtime.

Do not treat successful connection as figure validation. Still run the plotting
script with the selected interpreter and inspect every requested final export.

## 7. Troubleshoot narrowly

- `No module named mcp`: install the version-matched `ultraplot[mcp]` extra in
  the selected environment.
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
