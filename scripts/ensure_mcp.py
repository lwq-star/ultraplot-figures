#!/usr/bin/env python
"""Check and optionally configure the UltraPlot MCP for the active Python."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


SERVER_NAME = "ultraplot"
DEFAULT_STARTUP_TIMEOUT = 20
DEFAULT_TOOL_TIMEOUT = 60
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[.-][0-9A-Za-z.-]+)?$")
_HEADER_RE = re.compile(r"^\s*(\[\[?)([^\]]+)(\]\]?)\s*(?:#.*)?$")
_ASSIGN_RE = re.compile(
    r"^(\s*)([A-Za-z0-9_-]+)(\s*=\s*)(.*)$"
)
_TARGET_SECTION = "mcp_servers.ultraplot"
_ENV_SECTION = "mcp_servers.ultraplot.env"
_PROBE_CODE = r'''
import importlib.util
import inspect
import json
import sys

def has_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False

result = {
    "python": sys.executable,
    "ultraplot_available": False,
    "mcp_dependency_available": has_module("mcp"),
    "ultraplot_mcp_available": has_module("ultraplot.mcp"),
    "ultraplot_version": None,
    "source_file": None,
}
try:
    import ultraplot
except Exception as exc:
    result["import_error"] = f"{type(exc).__name__}: {exc}"
else:
    result["ultraplot_available"] = True
    result["ultraplot_version"] = str(getattr(ultraplot, "__version__", "unknown"))
    try:
        result["source_file"] = inspect.getsourcefile(ultraplot.subplots)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
print(json.dumps(result, ensure_ascii=False))
'''


class BootstrapError(RuntimeError):
    """Raised when a safe check or configuration update cannot complete."""


def _codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _config_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else _codex_home() / "config.toml"


def _canonical_path(value: str | Path) -> str:
    path = Path(value).expanduser()
    try:
        path = path.resolve(strict=False)
    except OSError:
        path = Path(os.path.abspath(path))
    value = str(path)
    if os.name == "nt" and value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(value)


def _resolve_python(value: str | None) -> Path:
    """Resolve an explicit interpreter without invoking a shell."""
    candidate = Path(value).expanduser() if value else Path(sys.executable)
    if not candidate.is_absolute():
        found = shutil.which(str(candidate))
        if found:
            candidate = Path(found)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BootstrapError(f"Python interpreter does not exist: {candidate}") from exc
    if not resolved.is_file():
        raise BootstrapError(f"Python interpreter is not a file: {resolved}")
    return resolved


def _runtime_info(executable: Path | None = None) -> dict[str, Any]:
    """Probe the selected interpreter in a child process."""
    selected = _resolve_python(str(executable) if executable else None)
    info: dict[str, Any] = {
        "python": str(selected),
        "ultraplot_available": False,
        "mcp_dependency_available": False,
        "ultraplot_mcp_available": False,
        "ultraplot_version": None,
        "source_file": None,
    }
    try:
        completed = subprocess.run(
            [str(selected), "-c", _PROBE_CODE],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        info["probe_error"] = f"{type(exc).__name__}: {exc}"
        return info
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        info["probe_error"] = detail[-1] if detail else f"exit {completed.returncode}"
        return info
    try:
        probed = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        info["probe_error"] = f"Invalid interpreter probe output: {exc}"
        return info
    if not isinstance(probed, dict):
        info["probe_error"] = "Invalid interpreter probe output."
        return info
    info.update(probed)
    info["python"] = str(selected)
    return info


def _read_config(path: Path) -> tuple[dict[str, Any], str | None]:
    if path.exists() and not path.is_file():
        return {}, f"Config path is not a regular file: {path}"
    if not path.exists():
        return {}, None
    if tomllib is None:  # pragma: no cover - Python 3.10 fallback
        return {}, "Python 3.11 or the 'tomli' package is required to parse config.toml."
    try:
        text = path.read_text(encoding="utf-8-sig")
        return tomllib.loads(text), None
    except (OSError, UnicodeError, ValueError) as exc:
        return {}, f"Could not parse {path}: {exc}"


def _entry_info(config: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    servers = config.get("mcp_servers")
    entry = servers.get(SERVER_NAME) if isinstance(servers, dict) else None
    if not isinstance(entry, dict):
        return {
            "present": False,
            "aligned": False,
            "enabled": False,
            "docs_path": None,
        }

    args = entry.get("args", [])
    command = entry.get("command")
    expected_python = _canonical_path(runtime["python"])
    command_path = (
        _canonical_path(command)
        if isinstance(command, str) and Path(command).is_absolute()
        else None
    )
    server_type = entry.get("type")
    aligned = (
        command_path == expected_python
        and isinstance(args, list)
        and args[:2] == ["-m", "ultraplot.mcp"]
        and server_type in (None, "stdio")
    )
    env = entry.get("env")
    docs_path = env.get("ULTRAPLOT_MCP_DOCS") if isinstance(env, dict) else None
    return {
        "present": True,
        "aligned": aligned,
        "enabled": entry.get("enabled", True) is True,
        "docs_path": docs_path if isinstance(docs_path, str) else None,
        "command": command,
        "args": args,
        "type": server_type,
        "env_is_table": isinstance(env, dict),
    }


def _docs_available(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() or not candidate.is_dir():
        return False
    # A checkout normally contains conf.py and reStructuredText sources.  This
    # deliberately stays permissive because repository layouts can evolve.
    return (candidate / "conf.py").is_file() or any(candidate.glob("*.rst"))


def inspect_state(path: Path, executable: Path | None = None) -> dict[str, Any]:
    """Return a JSON-safe, read-only snapshot of MCP readiness."""
    runtime = _runtime_info(executable)
    config, parse_error = _read_config(path)
    entry = _entry_info(config, runtime) if not parse_error else {
        "present": False,
        "aligned": False,
        "enabled": False,
        "docs_path": None,
    }

    if runtime.get("probe_error"):
        status = "interpreter_error"
    elif parse_error:
        status = "config_invalid"
    elif not runtime["ultraplot_available"]:
        status = "missing_ultraplot"
    elif not runtime["mcp_dependency_available"] or not runtime["ultraplot_mcp_available"]:
        status = "missing_mcp_dependency"
    elif not entry["present"] or not entry["aligned"] or not entry["enabled"]:
        status = "needs_configuration"
    elif not _docs_available(entry.get("docs_path")):
        status = "configured_without_docs"
    else:
        status = "configured"

    return {
        "status": status,
        "config_path": str(path.resolve(strict=False)),
        "runtime": runtime,
        "server": entry,
        "restart_required": False,
    }


def _header_name(line: str) -> tuple[str, bool] | None:
    match = _HEADER_RE.match(line.rstrip("\r\n"))
    if not match or match.group(1) != "[" or match.group(3) != "]":
        return None
    raw = match.group(2).strip()
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for character in raw:
        if quote == '"' and escaped:
            current.append(character)
            escaped = False
            continue
        if quote == '"' and character == "\\":
            current.append(character)
            escaped = True
            continue
        if quote and character == quote:
            current.append(character)
            quote = None
            continue
        if not quote and character in "\"'":
            quote = character
            current.append(character)
            continue
        if not quote and character == ".":
            part = "".join(current).strip()
            if not part:
                return None
            parts.append(_unquote_key(part))
            current = []
            continue
        current.append(character)
    if quote:
        return None
    part = "".join(current).strip()
    if not part:
        return None
    parts.append(_unquote_key(part))
    return ".".join(parts), True


def _unquote_key(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _section_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    headers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        parsed = _header_name(line)
        if parsed:
            headers.append((index, parsed[0]))
    ranges: dict[str, tuple[int, int]] = {}
    for position, (start, name) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        if name not in ranges:
            ranges[name] = (start, end)
    return ranges


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _comment_index(value: str) -> int | None:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if quote == '"' and escaped:
            escaped = False
            continue
        if quote == '"' and character == "\\":
            escaped = True
            continue
        if quote and character == quote:
            quote = None
        elif not quote and character in "\"'":
            quote = character
        elif not quote and character == "#":
            return index
    return None


def _editable_section(lines: list[str], section: str) -> tuple[int, int]:
    ranges = _section_ranges(lines)
    if section not in ranges:
        raise BootstrapError(
            f"Cannot safely edit [{section}]: section is not a simple TOML table."
        )
    start, end = ranges[section]
    for line in lines[start + 1 : end]:
        body = line.rstrip("\r\n")
        stripped = body.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not _ASSIGN_RE.match(body):
            raise BootstrapError(
                f"Cannot safely edit [{section}]: found a complex or multiline value."
            )
        if "'''" in body or '"""' in body:
            raise BootstrapError(
                f"Cannot safely edit [{section}]: found a multiline string."
            )
    return start, end


def _replace_assignment(line: str, value: str, newline: str) -> str:
    body = line.rstrip("\r\n")
    match = _ASSIGN_RE.match(body)
    if not match:
        raise BootstrapError("Cannot safely replace a non-simple TOML assignment.")
    value_and_comment = match.group(4)
    comment = _comment_index(value_and_comment)
    if comment is None:
        suffix = ""
    else:
        before_comment = value_and_comment[:comment]
        spacing = before_comment[len(before_comment.rstrip(" \t")) :]
        suffix = spacing + value_and_comment[comment:]
    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else newline
    return body[: match.start(4)] + value + suffix + ending


def _upsert_section(
    text: str,
    section: str,
    values: dict[str, str],
) -> tuple[str, bool]:
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    if not lines and text:
        lines = [text]
    ranges = _section_ranges(lines)
    if section not in ranges:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines.append(newline)
        if lines and not "".join(lines).endswith(newline + newline):
            lines.append(newline)
        lines.append(f"[{section}]{newline}")
        lines.extend(f"{key} = {value}{newline}" for key, value in values.items())
        return "".join(lines), True

    start, end = _editable_section(lines, section)
    existing: dict[str, int] = {}
    for index in range(start + 1, end):
        match = _ASSIGN_RE.match(lines[index].rstrip("\r\n"))
        if match and match.group(2) in values and match.group(2) not in existing:
            existing[match.group(2)] = index
        elif match and match.group(2) in values:
            raise BootstrapError(
                f"Cannot safely edit [{section}]: duplicate key {match.group(2)!r}."
            )
    changed = False
    for key, value in values.items():
        if key in existing:
            line = lines[existing[key]]
            updated = _replace_assignment(line, value, newline)
            if updated != line:
                lines[existing[key]] = updated
                changed = True
        else:
            insertion = end
            lines.insert(insertion, f"{key} = {value}{newline}")
            end += 1
            changed = True
    return "".join(lines), changed


def _section_keys(lines: list[str], section: str) -> set[str]:
    ranges = _section_ranges(lines)
    if section not in ranges:
        return set()
    start, end = _editable_section(lines, section)
    keys: set[str] = set()
    for line in lines[start + 1 : end]:
        match = _ASSIGN_RE.match(line.rstrip("\r\n"))
        if match:
            if match.group(2) in keys:
                raise BootstrapError(
                    f"Cannot safely edit [{section}]: duplicate key {match.group(2)!r}."
                )
            keys.add(match.group(2))
    return keys


def _entry_conflict(
    text: str,
    config: dict[str, Any],
    runtime: dict[str, Any],
    *,
    docs_path: str | None,
    force: bool,
) -> None:
    """Reject structures that a line-preserving patch cannot safely merge."""
    lines = text.splitlines(keepends=True)
    ranges = _section_ranges(lines)
    servers = config.get("mcp_servers")
    entry = servers.get(SERVER_NAME) if isinstance(servers, dict) else None
    if entry is not None and not isinstance(entry, dict):
        raise BootstrapError("mcp_servers.ultraplot is not a TOML table.")
    if entry is not None and _TARGET_SECTION not in ranges:
        raise BootstrapError(
            "mcp_servers.ultraplot is an inline or dotted table; refusing to "
            "append a duplicate table."
        )
    if _TARGET_SECTION in ranges:
        _editable_section(lines, _TARGET_SECTION)
    if docs_path and _ENV_SECTION in ranges:
        _editable_section(lines, _ENV_SECTION)
    if not isinstance(entry, dict):
        return

    entry_type = entry.get("type")
    if entry_type not in (None, "stdio"):
        raise BootstrapError(
            "Existing ultraplot MCP entry is not a stdio server; refusing to replace it."
        )
    expected = _canonical_path(runtime["python"])
    command = entry.get("command")
    command_matches = (
        isinstance(command, str)
        and Path(command).is_absolute()
        and _canonical_path(command) == expected
    )
    args = entry.get("args")
    args_match = isinstance(args, list) and args[:2] == ["-m", "ultraplot.mcp"]
    enabled = entry.get("enabled", True)
    enabled_match = enabled is True
    if not force and command is not None and not command_matches:
        raise BootstrapError(
            "Existing ultraplot MCP command uses a different or non-absolute "
            "interpreter; use --force only after reviewing it."
        )
    if not force and args is not None and not args_match:
        raise BootstrapError(
            "Existing ultraplot MCP args differ; use --force only after reviewing them."
        )
    if not force and enabled is not None and not enabled_match:
        raise BootstrapError(
            "Existing ultraplot MCP entry is disabled; use --force to enable it."
        )
    env = entry.get("env")
    if docs_path and env is not None and not isinstance(env, dict):
        raise BootstrapError(
            "Existing ultraplot MCP env is not a table; refusing to add documentation settings."
        )
    if docs_path and isinstance(env, dict) and _ENV_SECTION not in ranges:
        raise BootstrapError(
            "Existing ultraplot MCP env is inline or dotted; refusing to append a duplicate env table."
        )


def _atomic_replace(path: Path, original: bytes, updated: bytes) -> None:
    if original == updated:
        return
    try:
        if path.exists():
            if not path.is_file():
                raise BootstrapError(f"Config path is not a regular file: {path}")
            if path.read_bytes() != original:
                raise BootstrapError(
                    "config.toml changed while it was being prepared; no changes made."
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f"{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
    except BootstrapError:
        raise
    except OSError as exc:
        raise BootstrapError(f"Could not prepare atomic config write: {exc}") from exc

    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        current = path.read_bytes() if path.exists() else b""
        if current != original:
            raise BootstrapError(
                "config.toml changed while it was being written; no changes made."
            )
        if path.exists():
            os.chmod(temporary_name, path.stat().st_mode & 0o777)
        os.replace(temporary_name, path)
    except BootstrapError:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise BootstrapError(f"Could not replace {path}: {exc}") from exc


def _write_config(
    path: Path,
    runtime: dict[str, Any],
    docs_path: str | None,
    *,
    force: bool = False,
) -> bool:
    if path.is_symlink():
        raise BootstrapError(f"Refusing to replace symlinked config: {path}")
    if path.exists() and not path.is_file():
        raise BootstrapError(f"Config path is not a regular file: {path}")
    try:
        original = path.read_bytes() if path.exists() else b""
        text = original.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise BootstrapError(f"Could not read {path}: {exc}") from exc
    if tomllib is None:  # pragma: no cover - Python 3.10 without tomli
        raise BootstrapError(
            "Cannot validate config.toml: install 'tomli' in the selected Python "
            "environment (Python 3.11+ includes tomllib)."
        )
    try:
        config = tomllib.loads(text) if text else {}
    except (ValueError, TypeError) as exc:
        raise BootstrapError(f"Refusing to edit invalid TOML: {exc}") from exc

    _entry_conflict(text, config, runtime, docs_path=docs_path, force=force)
    lines = text.splitlines(keepends=True)
    main_keys = _section_keys(lines, _TARGET_SECTION) if _TARGET_SECTION in _section_ranges(lines) else set()
    servers = config.get("mcp_servers")
    entry = servers.get(SERVER_NAME) if isinstance(servers, dict) and isinstance(servers.get(SERVER_NAME), dict) else {}
    expected_command = _canonical_path(runtime["python"])
    command = entry.get("command")
    args = entry.get("args")
    enabled = entry.get("enabled", True)
    main_values: dict[str, str] = {}
    if "command" not in main_keys or force or not (
        isinstance(command, str)
        and Path(command).is_absolute()
        and _canonical_path(command) == expected_command
    ):
        main_values["command"] = _toml_string(str(Path(runtime["python"]).resolve()))
    if "args" not in main_keys or force or not (
        isinstance(args, list) and args[:2] == ["-m", "ultraplot.mcp"]
    ):
        main_values["args"] = '["-m", "ultraplot.mcp"]'
    if "enabled" not in main_keys or force or enabled is not True:
        main_values["enabled"] = "true"
    if "startup_timeout_sec" not in main_keys:
        main_values["startup_timeout_sec"] = str(DEFAULT_STARTUP_TIMEOUT)
    if "tool_timeout_sec" not in main_keys:
        main_values["tool_timeout_sec"] = str(DEFAULT_TOOL_TIMEOUT)

    updated, changed = _upsert_section(text, _TARGET_SECTION, main_values)
    if docs_path:
        docs_value = str(Path(docs_path).expanduser().resolve())
        env = entry.get("env") if isinstance(entry, dict) else None
        current_docs = env.get("ULTRAPLOT_MCP_DOCS") if isinstance(env, dict) else None
        if not isinstance(current_docs, str) or _canonical_path(current_docs) != _canonical_path(docs_value):
            updated, env_changed = _upsert_section(
                updated,
                _ENV_SECTION,
                {"ULTRAPLOT_MCP_DOCS": _toml_string(docs_value)},
            )
            changed = changed or env_changed

    try:
        tomllib.loads(updated)
    except (ValueError, TypeError) as exc:
        raise BootstrapError(f"Refusing to write invalid TOML: {exc}") from exc
    bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
    updated_bytes = bom + updated.encode("utf-8")
    if not changed or updated_bytes == original:
        return False
    _atomic_replace(path, original, updated_bytes)
    return True


def _candidate_docs(runtime: dict[str, Any]) -> str | None:
    configured = os.environ.get("ULTRAPLOT_MCP_DOCS")
    if _docs_available(configured):
        return str(Path(configured).expanduser().resolve())
    version = runtime.get("ultraplot_version")
    if version:
        candidate = _codex_home() / "mcp-sources" / f"ultraplot-{version}" / "docs"
        if candidate.is_dir():
            return str(candidate.resolve())
    return None


def _install_dependency(runtime: dict[str, Any]) -> None:
    version = runtime.get("ultraplot_version")
    executable = runtime.get("python")
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise BootstrapError(
            "Cannot install the MCP extra because the selected UltraPlot version "
            "is unknown or not safely pinnable."
        )
    if not isinstance(executable, str):
        raise BootstrapError("Cannot install the MCP extra without a selected Python.")
    requirement = f"ultraplot[mcp]=={version}"
    try:
        result = subprocess.run(
            [
                executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                requirement,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootstrapError(f"Could not install {requirement}: {exc}") from exc
    if result.returncode:
        raise BootstrapError(f"Could not install {requirement} (exit {result.returncode}).")


def configure(
    path: Path,
    *,
    confirm: bool,
    install_dependencies: bool,
    docs_path: str | None,
    executable: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if not confirm:
        raise BootstrapError(
            "Configuration changes require --yes after the user authorizes MCP setup."
        )

    state = inspect_state(path, executable)
    if state["status"] == "config_invalid":
        raise BootstrapError(state["config_path"] + " is not valid TOML; no changes made.")
    runtime = state["runtime"]
    if state["status"] == "interpreter_error":
        detail = runtime.get("probe_error", "interpreter probe failed")
        raise BootstrapError(f"Selected Python could not be probed: {detail}")
    if not runtime["ultraplot_available"]:
        raise BootstrapError(
            "UltraPlot is not installed in the selected Python environment; install it first."
        )
    if state["status"] == "missing_mcp_dependency":
        if not install_dependencies:
            raise BootstrapError(
                "The selected environment lacks UltraPlot MCP dependencies; "
                "rerun with --install-dependencies after authorization."
            )
        _install_dependency(runtime)
        state = inspect_state(path, executable)
        runtime = state["runtime"]
        if state["status"] == "missing_mcp_dependency":
            raise BootstrapError("MCP dependencies are still unavailable after installation.")

    current_docs = state["server"].get("docs_path")
    if docs_path:
        if not _docs_available(docs_path):
            raise BootstrapError(f"Documentation path is not a valid checkout: {docs_path}")
        selected_docs = docs_path
    elif current_docs and _docs_available(current_docs):
        selected_docs = current_docs
    else:
        # A stale or relative path already in Codex configuration should not
        # prevent the API-capable server from being configured.
        selected_docs = _candidate_docs(runtime)
        if selected_docs and not _docs_available(selected_docs):
            selected_docs = None
    if selected_docs:
        selected_docs = str(Path(selected_docs).expanduser().resolve())

    docs_changed = bool(
        selected_docs
        and (
            not current_docs
            or _canonical_path(selected_docs) != _canonical_path(current_docs)
        )
    )
    if (
        state["status"] in {"configured", "configured_without_docs"}
        and state["server"].get("aligned")
        and not docs_changed
    ):
        return {
            **state,
            "action": "unchanged",
            "restart_required": False,
        }

    changed = _write_config(
        path,
        runtime,
        selected_docs if docs_changed or not current_docs else None,
        force=force,
    )
    result = inspect_state(path, executable)
    result["action"] = "configured" if changed else "unchanged"
    result["restart_required"] = changed
    result["message"] = "Restart Codex or start a new task before relying on the new MCP entry."
    return result


def _self_test() -> dict[str, Any]:
    if tomllib is None:  # pragma: no cover - Python 3.10 without tomli
        raise BootstrapError(
            "self-test requires Python 3.11+ or the 'tomli' package."
        )
    tests: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ultraplot-mcp-test-") as directory:
        root = Path(directory)
        path = root / "config.toml"
        path.write_text(
            '# keep this comment\n[model]\nname = "keep"\n\n'
            '[mcp_servers.other]\ncommand = "other"\n\n'
            '[mcp_servers.ultraplot]\ncommand = "old" # preserve\nargs = []\n'
            'startup_timeout_sec = 99\n\n'
            '[mcp_servers.ultraplot.env]\nKEEP = "yes"\n',
            encoding="utf-8",
        )
        fake_runtime = {"python": sys.executable}
        docs = root / "docs"
        docs.mkdir()
        (docs / "conf.py").write_text("# test\n", encoding="utf-8")
        _write_config(path, fake_runtime, str(docs), force=True)
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        assert parsed["model"]["name"] == "keep"
        assert parsed["mcp_servers"]["other"]["command"] == "other"
        assert parsed["mcp_servers"]["ultraplot"]["args"] == ["-m", "ultraplot.mcp"]
        assert parsed["mcp_servers"]["ultraplot"]["startup_timeout_sec"] == 99
        assert parsed["mcp_servers"]["ultraplot"]["env"]["KEEP"] == "yes"
        assert "# preserve" in path.read_text(encoding="utf-8")
        tests.extend(["preserve_unrelated_tables", "preserve_timeout_and_comments"])
        first = path.read_bytes()
        assert _write_config(path, fake_runtime, str(docs), force=True) is False
        assert path.read_bytes() == first
        tests.append("idempotent_upsert")

        crlf = root / "crlf.toml"
        crlf.write_bytes(b"[model]\r\nname = 'keep'\r\n")
        _write_config(crlf, fake_runtime, None)
        crlf_bytes = crlf.read_bytes()
        assert b"\r\n[mcp_servers.ultraplot]\r\n" in crlf_bytes
        tomllib.loads(crlf_bytes.decode("utf-8"))
        tests.append("crlf_and_windows_paths")

        missing = root / "missing.toml"
        _write_config(missing, fake_runtime, None)
        assert tomllib.loads(missing.read_text(encoding="utf-8"))["mcp_servers"]["ultraplot"]
        tests.append("append_missing_section")

        conflict = root / "conflict.toml"
        conflict.write_text(
            '[mcp_servers.ultraplot]\ncommand = "uvx"\nargs = ["ultraplot-mcp"]\n',
            encoding="utf-8",
        )
        try:
            _write_config(conflict, fake_runtime, None)
        except BootstrapError:
            pass
        else:
            raise AssertionError("conflicting server was silently overwritten")
        tests.append("reject_conflicting_server")

        inline = root / "inline.toml"
        inline.write_text(
            'mcp_servers = { ultraplot = { command = "uvx" } }\n',
            encoding="utf-8",
        )
        try:
            _write_config(inline, fake_runtime, None)
        except BootstrapError:
            pass
        else:
            raise AssertionError("inline table was silently duplicated")
        tests.append("reject_inline_table")

        try:
            _install_dependency({"python": sys.executable, "ultraplot_version": "unknown"})
        except BootstrapError:
            pass
        else:
            raise AssertionError("unknown version was allowed for installation")
        tests.append("pin_dependency_version")
    return {"ok": True, "tests": tests}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Read-only readiness check (default).")
    modes.add_argument("--configure", action="store_true", help="Write the UltraPlot MCP entry.")
    modes.add_argument("--self-test", action="store_true", help="Run offline updater tests.")
    parser.add_argument("--config", help="Override the Codex config.toml path.")
    parser.add_argument("--python", dest="python_executable", help="Selected plotting Python executable.")
    parser.add_argument("--docs", help="Existing matching UltraPlot docs directory.")
    parser.add_argument("--install-dependencies", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace a reviewed conflicting MCP command.")
    parser.add_argument("--yes", action="store_true", help="Confirm the requested config mutation.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if args.self_test:
        try:
            result = _self_test()
        except (AssertionError, BootstrapError) as exc:
            result = {"ok": False, "error": str(exc)}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 5
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    path = _config_path(args.config)
    try:
        executable = _resolve_python(args.python_executable)
        result = (
            configure(
                path,
                confirm=args.yes,
                install_dependencies=args.install_dependencies,
                docs_path=args.docs,
                executable=executable,
                force=args.force,
            )
            if args.configure
            else inspect_state(path, executable)
        )
    except (BootstrapError, OSError, subprocess.SubprocessError) as exc:
        result = {"status": "error", "error": str(exc), "config_path": str(path)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["status"])
    if args.configure:
        return 0 if result["status"] in {"configured", "configured_without_docs"} else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
