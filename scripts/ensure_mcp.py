#!/usr/bin/env python
"""Check and optionally configure the UltraPlot MCP for the active Python."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
CONFIG_LOCK_TIMEOUT = 30.0
MAX_PIP_DIAGNOSTIC = 2000
AUTO_SETUP_ENV = "ULTRAPLOT_FIGURES_MCP_AUTO_SETUP"
AUTO_SETUP_DISABLED_VALUES = {"0", "false", "no", "off"}
PACKAGE_POLICY_ENV = "ULTRAPLOT_FIGURES_PACKAGE_POLICY"
AUTO_INSTALL_ULTRAPLOT_ENV = "ULTRAPLOT_FIGURES_AUTO_INSTALL_ULTRAPLOT"
AUTO_UPGRADE_ULTRAPLOT_ENV = "ULTRAPLOT_FIGURES_AUTO_UPGRADE"
ULTRAPLOT_VERSION_ENV = "ULTRAPLOT_FIGURES_ULTRAPLOT_VERSION"
ALLOW_PIP_IN_CONDA_ENV = "ULTRAPLOT_FIGURES_ALLOW_PIP_IN_CONDA"
PACKAGE_POLICIES = {"manual", "install", "upgrade", "install-and-upgrade"}
AUTO_SETUP_ENABLED_VALUES = {"1", "true", "yes", "on"}
DEFAULT_ULTRAPLOT_VERSION = "2.7.0"
SUPPORTED_ULTRAPLOT_MIN = (2, 7, 0)
SUPPORTED_ULTRAPLOT_MAX = (2, 8, 0)
# Automatic setup is intentionally limited to published stable versions.  A
# prerelease or local build may expose a different MCP contract and cannot be
# safely converted into a PyPI exact requirement by this helper.  PEP 440 post
# releases remain stable and are accepted for exact pinning.
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.post\d+)?$")
_VERSION_BASE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")
_HEADER_RE = re.compile(r"^\s*(\[\[?)([^\]]+)(\]\]?)\s*(?:#.*)?$")
_ASSIGN_RE = re.compile(
    r"^(\s*)([A-Za-z0-9_-]+)(\s*=\s*)(.*)$"
)
_TARGET_SECTION = "mcp_servers.ultraplot"
_ENV_SECTION = "mcp_servers.ultraplot.env"
_DOCS_VERSION_MARKER_RE = re.compile(
    r"^ultraplot[-_]?v?(\d+\.\d+\.\d+(?:\.post\d+)?)"
    r"(?:[-_].*)?$",
    re.IGNORECASE,
)
# These fields describe HTTP/auth transports and are mutually exclusive with
# the stdio command that this helper manages.  Keep them explicit so a
# pre-existing URL server is never silently converted into a mixed entry.
_STDIO_CONFLICT_KEYS = {
    "url",
    "bearer_token_env_var",
    "headers",
    "http_headers",
    "env_http_headers",
    "oauth",
    "oauth_resource",
    "mcp_oauth_callback_port",
}
_STRING_ARRAY_KEYS = {"env_vars", "enabled_tools", "disabled_tools"}
_SECRET_VALUE_RE = re.compile(
    r"(?i)(\b(?:password|passwd|token|secret|api[_-]?key|authorization)\b"
    r"\s*(?:(?:[:=])|(?:bearer|basic)\s+|\s+))([^\s,;]+)"
)
_AUTH_BEARER_RE = re.compile(
    r"(?i)(\bauthorization\b\s*:\s*bearer\s+)([^\s,;]+)"
)
_AUTH_BASIC_RE = re.compile(
    r"(?i)(\bauthorization\b\s*:\s*basic\s+)([^\s,;]+)"
)
_URL_CREDENTIAL_RE = re.compile(r"(?i)(https?://)([^/\s:@]+):([^/\s]+)@")
_URL_USERINFO_RE = re.compile(r"(?i)(https?://)([^/\s:@]+)@([^\s/]+)")
_PROBE_CODE = r'''
import importlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import re
import sys

def can_import(name):
    try:
        importlib.import_module(name)
    except Exception:
        return False
    return True

def compatible_mcp_version(value):
    if not isinstance(value, str):
        return False
    try:
        from packaging.version import Version
    except Exception:
        match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", value)
        if not match:
            return False
        major, minor = int(match.group(1)), int(match.group(2))
        return major == 2 and minor >= 1
    try:
        parsed = Version(value)
        if parsed.is_prerelease or parsed.is_devrelease or parsed.local is not None:
            return False
        return Version("2.1") <= parsed < Version("3")
    except Exception:
        return False

def path_under(child, root):
    if not isinstance(child, str) or not isinstance(root, str):
        return False
    try:
        child_path = os.path.realpath(child)
        root_path = os.path.realpath(root)
        return os.path.commonpath([child_path, root_path]) == root_path
    except (OSError, ValueError):
        return False

mcp_version = None
try:
    mcp_version = importlib.metadata.version("mcp")
except importlib.metadata.PackageNotFoundError:
    pass
except Exception:
    pass

result = {
    "python": sys.executable,
    "ultraplot_available": False,
    "mcp_dependency_available": can_import("mcp"),
    "ultraplot_mcp_available": can_import("ultraplot.mcp"),
    "mcp_version": mcp_version,
    "mcp_version_compatible": compatible_mcp_version(mcp_version),
    "ultraplot_version": None,
    "ultraplot_distribution_version": None,
    "ultraplot_distribution_root": None,
    "ultraplot_provenance": "unknown",
    "ultraplot_direct_url_present": False,
    "ultraplot_direct_url_valid": False,
    "source_file": None,
    "ultraplot_editable": False,
    "package_manager": "unknown",
    "conda_metadata_present": False,
    "conda_metadata_version": None,
    "conda_metadata_versions": [],
}
try:
    # A conda-managed prefix must not be silently replaced with a PyPI wheel.
    # This is deliberately conservative for missing packages as well as for
    # upgrades; users can use the environment's documented conda flow.
    prefix = Path(sys.prefix)
    conda_records = list((prefix / "conda-meta").glob("ultraplot-*.json"))
    result["conda_metadata_present"] = bool(conda_records)
    conda_versions = []
    for record in conda_records:
        try:
            record_info = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, TypeError):
            continue
        if isinstance(record_info, dict) and isinstance(record_info.get("version"), str):
            conda_versions.append(record_info["version"])
    result["conda_metadata_versions"] = conda_versions
    if conda_versions:
        result["conda_metadata_version"] = conda_versions[0]
    result["package_manager"] = (
        "conda" if (prefix / "conda-meta").is_dir() else "pip"
    )
except Exception:
    pass
try:
    import ultraplot
except Exception as exc:
    result["import_error"] = f"{type(exc).__name__}: {exc}"
else:
    result["ultraplot_available"] = True
    module_version = str(getattr(ultraplot, "__version__", "unknown"))
    result["ultraplot_version"] = module_version
    source_file = None
    try:
        source_file = inspect.getsourcefile(ultraplot.subplots)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    result["source_file"] = source_file
    try:
        distribution = importlib.metadata.distribution("ultraplot")
        distribution_version = str(distribution.version)
        distribution_root = str(distribution.locate_file(""))
        result["ultraplot_distribution_version"] = distribution_version
        result["ultraplot_distribution_root"] = distribution_root
        if result["conda_metadata_present"]:
            metadata_versions = result.get("conda_metadata_versions") or []
            result["package_manager"] = (
                "mixed"
                if not metadata_versions or any(
                    version != distribution_version for version in metadata_versions
                )
                else "conda"
            )
        direct_url = distribution.read_text("direct_url.json")
        if direct_url:
            result["ultraplot_direct_url_present"] = True
            try:
                direct_info = json.loads(direct_url)
            except (TypeError, ValueError, json.JSONDecodeError):
                direct_info = None
            if isinstance(direct_info, dict):
                result["ultraplot_direct_url_valid"] = True
                result["ultraplot_editable"] = bool(
                    direct_info.get("dir_info", {}).get("editable", False)
                )
            else:
                direct_info = None
        else:
            direct_info = None

        if module_version != distribution_version:
            result["ultraplot_provenance"] = "version_mismatch"
        elif not source_file or not distribution_root:
            result["ultraplot_provenance"] = "unknown"
        elif result["ultraplot_editable"]:
            result["ultraplot_provenance"] = "editable"
        elif result["ultraplot_direct_url_present"]:
            # A non-editable direct_url can point to a private/local wheel or
            # checkout.  Do not silently replace it with a PyPI wheel.
            direct_url_value = (
                direct_info.get("url") if isinstance(direct_info, dict) else None
            )
            if not result["ultraplot_direct_url_valid"]:
                result["ultraplot_provenance"] = "nonstandard"
            elif isinstance(direct_url_value, str) and direct_url_value.startswith(
                ("http://", "https://")
            ):
                result["ultraplot_provenance"] = "remote"
            else:
                result["ultraplot_provenance"] = "nonstandard"
        elif path_under(source_file, distribution_root):
            result["ultraplot_provenance"] = "installed"
        else:
            result["ultraplot_provenance"] = "unknown"
    except Exception:
        result["ultraplot_provenance"] = "unknown"
print(json.dumps(result, ensure_ascii=True))
'''


class BootstrapError(RuntimeError):
    """Raised when a safe check or configuration update cannot complete."""


def _codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _config_path(value: str | None) -> Path:
    return Path(value).expanduser() if value else _codex_home() / "config.toml"


def _safe_resolve(value: str | Path, *, strict: bool = False) -> Path:
    """Resolve a user path without letting platform/symlink errors escape."""
    path = Path(value).expanduser()
    try:
        return path.resolve(strict=strict)
    except Exception:
        # ``Path.resolve`` can raise RuntimeError for symlink loops and may
        # raise platform-specific exceptions for inaccessible parents.  A
        # normalized absolute fallback is sufficient for comparisons and
        # diagnostics; callers that require an existing file validate it
        # separately.
        try:
            return Path(os.path.abspath(str(path)))
        except Exception:
            return path


def _canonical_path(value: str | Path) -> str:
    path = _safe_resolve(value)
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
    except Exception as exc:
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
        "mcp_version": None,
        "mcp_version_compatible": False,
        "ultraplot_version": None,
        "ultraplot_distribution_version": None,
        "ultraplot_distribution_root": None,
        "ultraplot_provenance": "unknown",
        "ultraplot_direct_url_present": False,
        "ultraplot_direct_url_valid": False,
        "source_file": None,
        "ultraplot_editable": False,
    }
    try:
        # ``python -c`` places the current working directory at the front of
        # ``sys.path``.  Probe from an empty temporary directory and remove
        # PYTHONPATH so a project-local ``ultraplot``/``mcp`` module cannot
        # masquerade as the selected environment's packages.
        probe_env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() != "PYTHONPATH"
        }
        # User-site packages and PYTHONUSERBASE can shadow the selected
        # environment even when the working directory is isolated.
        probe_env["PYTHONNOUSERSITE"] = "1"
        probe_env.pop("PYTHONUSERBASE", None)
        probe_env.pop("PYTHONHOME", None)
        with tempfile.TemporaryDirectory(prefix="ultraplot-mcp-probe-") as probe_dir:
            completed = subprocess.run(
                [str(selected), "-c", _PROBE_CODE],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=probe_dir,
                env=probe_env,
                timeout=20,
                check=False,
            )
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError) as exc:
        info["probe_error"] = _redacted_diagnostic(
            f"{type(exc).__name__}: {exc}", limit=MAX_PIP_DIAGNOSTIC
        )
        return info
    if completed.returncode:
        detail = (getattr(completed, "stderr", None) or "").strip().splitlines()
        info["probe_error"] = _redacted_diagnostic(
            detail[-1] if detail else f"exit {completed.returncode}"
        )
        return info
    try:
        probed = json.loads(getattr(completed, "stdout", ""))
    except (json.JSONDecodeError, TypeError) as exc:
        info["probe_error"] = _redacted_diagnostic(
            f"Invalid interpreter probe output: {exc}"
        )
        return info
    if not isinstance(probed, dict):
        info["probe_error"] = "Invalid interpreter probe output."
        return info
    info.update(probed)
    info["python"] = str(selected)
    return info


def _read_config(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        if path.exists() and not path.is_file():
            return {}, f"Config path is not a regular file: {path}"
        if not path.exists():
            return {}, None
    except (OSError, RuntimeError, ValueError) as exc:
        return {}, f"Could not inspect {path}: {exc}"
    if tomllib is None:  # pragma: no cover - Python 3.10 fallback
        return {}, "Python 3.11 or the 'tomli' package is required to parse config.toml."
    try:
        text = path.read_text(encoding="utf-8-sig")
        return tomllib.loads(text), None
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
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
            "timeout_status": "verified",
            "timeout_reasons": [],
            "transport_conflicts": [],
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
        and args == ["-m", "ultraplot.mcp"]
        and server_type in (None, "stdio")
    )
    env = entry.get("env")
    docs_path = env.get("ULTRAPLOT_MCP_DOCS") if isinstance(env, dict) else None
    environment_status, environment_reasons = _entry_environment_status(entry, runtime)
    timeout_status, timeout_reasons = _entry_timeout_status(entry)
    return {
        "present": True,
        "aligned": aligned,
        "enabled": entry.get("enabled", True) is True,
        "docs_path": docs_path if isinstance(docs_path, str) else None,
        "command": command,
        "args": args,
        "type": server_type,
        "env_is_table": isinstance(env, dict),
        "environment_status": environment_status,
        "environment_reasons": environment_reasons,
        "timeout_status": timeout_status,
        "timeout_reasons": timeout_reasons,
        "transport_conflicts": _entry_transport_conflicts(entry),
    }


def _positive_finite_number(value: object) -> bool:
    """Return whether a TOML numeric timeout is strictly positive and finite."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return value > 0 and math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _entry_timeout_status(entry: dict[str, Any]) -> tuple[str, list[str]]:
    """Validate optional Codex timeout fields without changing user values."""
    reasons: list[str] = []
    for key in ("startup_timeout_sec", "tool_timeout_sec"):
        if key in entry and not _positive_finite_number(entry[key]):
            reasons.append(f"{key} must be a positive finite number")
    return ("conflict" if reasons else "verified"), reasons


def _entry_transport_conflicts(entry: dict[str, Any]) -> list[str]:
    """List HTTP/auth fields that cannot be combined with the managed stdio server."""
    return sorted(key for key in _STDIO_CONFLICT_KEYS if key in entry)


def _entry_environment_status(
    entry: dict[str, Any], runtime: dict[str, Any] | None = None
) -> tuple[str, list[str]]:
    """Classify startup-environment fields without exposing their values."""
    status = "verified"
    reasons: list[str] = []

    def mark(kind: str, reason: str) -> None:
        nonlocal status
        if kind == "conflict" or status == "verified":
            status = kind
        if reason not in reasons:
            reasons.append(reason)

    env = entry.get("env")
    if env is not None:
        if not isinstance(env, dict):
            mark("conflict", "env is not a TOML table")
        else:
            for key, value in env.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    mark("conflict", "env contains a non-string key or value")
                    continue
                # The documentation pointer is consumed by the official
                # server and does not alter Python import resolution.  Any
                # other environment override remains unverified because it
                # can change the server's executable behavior.
                upper_key = key.upper()
                if upper_key == "ULTRAPLOT_MCP_DOCS":
                    continue
                if upper_key in {"GDAL_DATA", "PROJ_LIB"} and _trusted_runtime_path(
                    value, runtime
                ):
                    continue
                if upper_key == "PYTHONPATH":
                    mark("unverified", "env.PYTHONPATH may alter imports")
                else:
                    mark("unverified", f"env.{key} may alter server startup")

    cwd = entry.get("cwd")
    if cwd is not None:
        if not isinstance(cwd, str) or not cwd.strip():
            mark("conflict", "cwd is not a non-empty string")
        else:
            mark("unverified", "cwd changes the server working directory")

    env_vars = entry.get("env_vars")
    if env_vars is not None:
        if isinstance(env_vars, list):
            if any(not isinstance(value, str) or not value.strip() for value in env_vars):
                mark("conflict", "env_vars is not a string array")
            else:
                mark("unverified", "env_vars may alter server startup")
        elif isinstance(env_vars, dict):
            if any(
                not isinstance(key, str)
                or not key.strip()
                or not isinstance(value, str)
                for key, value in env_vars.items()
            ):
                mark("conflict", "env_vars is not a string-valued table")
            else:
                mark("unverified", "env_vars may alter server startup")
        else:
            mark("conflict", "env_vars is not a string array or table")

    # A few clients use a top-level spelling instead of an env table.  Treat
    # those values as unverified rather than silently claiming alignment.
    for key in ("PYTHONPATH", "pythonpath", "working_dir"):
        if key in entry:
            value = entry[key]
            if not isinstance(value, str) or not value.strip():
                mark("conflict", f"{key} is not a non-empty string")
            else:
                mark("unverified", f"{key} may alter server startup")

    return status, reasons


def _trusted_runtime_path(value: str, runtime: dict[str, Any] | None) -> bool:
    """Accept known geospatial data roots only when they belong to Python."""
    if runtime is None or not isinstance(runtime.get("python"), str):
        return False
    try:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute() or not candidate.is_dir():
            return False
        executable = Path(runtime["python"])
        roots = {executable.parent}
        if executable.parent.name.lower() in {"scripts", "bin"}:
            roots.add(executable.parent.parent)
        candidate_key = _canonical_path(candidate)
        for root in roots:
            root_key = _canonical_path(root)
            try:
                if os.path.commonpath([candidate_key, root_key]) == root_key:
                    return True
            except ValueError:
                continue
    except (OSError, RuntimeError, ValueError):
        return False
    return False


def _docs_marker_version(path: str | Path) -> str | None:
    """Read a version marker from a conventional UltraPlot checkout name."""
    candidate = Path(path)
    for part in (candidate.name, candidate.parent.name, candidate.parent.parent.name):
        match = _DOCS_VERSION_MARKER_RE.fullmatch(part)
        if match:
            return match.group(1)
    return None


def _docs_available(
    path: str | None,
    *,
    expected_version: str | None = None,
    require_version_marker: bool = False,
) -> bool:
    if not path:
        return False
    try:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute() or not candidate.is_dir():
            return False
        # A checkout normally contains conf.py and reStructuredText sources.
        # This deliberately stays permissive because repository layouts can
        # evolve.
        if not ((candidate / "conf.py").is_file() or any(candidate.glob("*.rst"))):
            return False
        if require_version_marker:
            if not (candidate / "conf.py").is_file() or not (candidate / "index.rst").is_file():
                return False
            marker = _docs_marker_version(candidate)
            if not marker or not expected_version:
                return False
            if marker != expected_version:
                return False
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _docs_match_runtime(path: str | None, runtime: dict[str, Any]) -> bool:
    version = runtime.get("ultraplot_version")
    return isinstance(version, str) and _docs_available(
        path,
        expected_version=version,
        require_version_marker=True,
    )


def _supported_ultraplot_version(value: object) -> bool:
    """Return whether the installed version has the official MCP contract."""
    version = _version_key(value)
    # The helper is validated against the published UltraPlot 2.7.x MCP
    # contract. Do not assume a future minor/major version keeps the same
    # optional extra or protocol dependency range without an explicit update.
    return bool(version and SUPPORTED_ULTRAPLOT_MIN <= version < SUPPORTED_ULTRAPLOT_MAX)


def _version_key(value: object) -> tuple[int, int, int, int] | None:
    """Convert a stable UltraPlot version into a comparable tuple."""
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        return None
    match = _VERSION_BASE_RE.match(value)
    if not match:
        return None
    post_match = re.search(r"\.post(\d+)$", value)
    post = int(post_match.group(1)) if post_match else 0
    return (*tuple(int(part) for part in match.groups()), post)


def _target_ultraplot_version(
    value: str | None = None, *, required: bool = False
) -> str:
    """Resolve an exact, stable, supported version for package mutation."""
    raw = value or os.environ.get(ULTRAPLOT_VERSION_ENV)
    if not raw:
        if required:
            raise BootstrapError(
                "An exact target version is required for an UltraPlot upgrade; "
                f"set --ultraplot-version or {ULTRAPLOT_VERSION_ENV}."
            )
        raw = DEFAULT_ULTRAPLOT_VERSION
    raw = raw.strip()
    if not _supported_ultraplot_version(raw):
        raise BootstrapError(
            "Automatic UltraPlot installation and upgrades require a stable "
            "2.7.x target version (for example, 2.7.0)."
        )
    return raw


def _safe_ultraplot_provenance(runtime: dict[str, Any]) -> bool:
    """Allow only package sources that will not be silently replaced by pip."""
    # Missing provenance is retained as safe for synthetic callers and older
    # serialized test fixtures.  The real probe always supplies the field.
    return runtime.get("ultraplot_provenance", "installed") in {
        "installed",
        "editable",
    }


def inspect_state(path: Path, executable: Path | None = None) -> dict[str, Any]:
    """Return a JSON-safe, read-only snapshot of MCP readiness."""
    runtime = _runtime_info(executable)
    config, parse_error = _read_config(path)
    entry = _entry_info(config, runtime) if not parse_error else {
        "present": False,
        "aligned": False,
        "enabled": False,
        "docs_path": None,
        "timeout_status": "verified",
        "timeout_reasons": [],
        "transport_conflicts": [],
    }

    if runtime.get("probe_error"):
        status = "interpreter_error"
    elif parse_error:
        status = "config_invalid"
    elif not runtime["ultraplot_available"]:
        status = "missing_ultraplot"
    elif not _supported_ultraplot_version(runtime.get("ultraplot_version")):
        status = "unsupported_ultraplot_version"
    elif not _safe_ultraplot_provenance(runtime):
        status = "ultraplot_provenance_unverified"
    elif (
        not runtime["mcp_dependency_available"]
        or not runtime["ultraplot_mcp_available"]
        or not runtime.get("mcp_version_compatible", False)
    ):
        status = "missing_mcp_dependency"
    elif entry.get("transport_conflicts"):
        status = "configuration_conflict"
    elif entry.get("timeout_status") == "conflict":
        status = "configuration_conflict"
    elif not entry["present"] or not entry["aligned"] or not entry["enabled"]:
        status = "needs_configuration"
    elif entry.get("environment_status") == "conflict":
        status = "configuration_conflict"
    elif entry.get("environment_status") == "unverified":
        status = "configuration_unverified"
    elif not _docs_match_runtime(entry.get("docs_path"), runtime):
        status = "configured_without_docs"
    else:
        status = "configured"

    return {
        "status": status,
        "config_path": str(_safe_resolve(path)),
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


def _reject_unsupported_toml(text: str) -> None:
    """Reject constructs the line-preserving editor cannot reason about.

    A triple-quoted TOML string may contain lines that look like table headers
    or assignments.  A line scanner cannot distinguish those lines from real
    syntax without implementing a TOML lexer, so refusing the whole edit is
    safer than risking a write inside the string.  The check is intentionally
    conservative and also rejects a delimiter appearing in a comment.
    """
    if "'''" in text or '"""' in text:
        raise BootstrapError(
            "Cannot safely edit config.toml containing a multiline TOML string."
        )


def _line_value_is_editable(key: str, value: str) -> bool:
    """Return whether a single assignment can be safely replaced/extended."""
    comment = _comment_index(value)
    if comment is not None:
        value = value[:comment]
    stripped = value.strip()
    if not stripped:
        return False
    if stripped.startswith("{"):
        # ``env_vars`` is a supported Codex compatibility spelling.  Permit a
        # one-line string-valued inline table while continuing to reject all
        # other inline tables that may hide nested structure.
        if key != "env_vars" or "\n" in stripped or not stripped.endswith("}"):
            return False
        if tomllib is None:
            return False
        try:
            parsed = tomllib.loads(f"value = {stripped}")
        except (TypeError, ValueError):
            return False
        table = parsed.get("value")
        return isinstance(table, dict) and all(
            isinstance(name, str)
            and name.strip()
            and isinstance(value, str)
            for name, value in table.items()
        )
    if stripped.startswith("["):
        # One-line arrays are safe only for complete values whose shape is
        # known to this editor.  Multiline arrays (or malformed syntax) stay
        # rejected so a line-preserving edit cannot enter their body.
        if key not in {"args", *_STRING_ARRAY_KEYS} or "\n" in stripped or not stripped.endswith("]"):
            return False
        if tomllib is None:
            return False
        try:
            parsed = tomllib.loads(f"value = {stripped}")
        except (TypeError, ValueError):
            return False
        values = parsed.get("value")
        if not isinstance(values, list):
            return False
        if key == "args":
            return True
        return all(isinstance(value, str) and value.strip() for value in values)
    return True


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
        match = _ASSIGN_RE.match(body)
        if not match:
            raise BootstrapError(
                f"Cannot safely edit [{section}]: found a complex or multiline value."
            )
        if "'''" in body or '"""' in body:
            raise BootstrapError(
                f"Cannot safely edit [{section}]: found a multiline string."
            )
        if not _line_value_is_editable(match.group(2), match.group(4)):
            raise BootstrapError(
                f"Cannot safely edit [{section}]: found a complex or multiline value."
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
    changed = False
    if lines[end - 1] and not lines[end - 1].endswith(("\n", "\r")):
        lines[end - 1] += newline
        changed = True
    for index in range(start + 1, end):
        match = _ASSIGN_RE.match(lines[index].rstrip("\r\n"))
        if match and match.group(2) in values and match.group(2) not in existing:
            existing[match.group(2)] = index
        elif match and match.group(2) in values:
            raise BootstrapError(
                f"Cannot safely edit [{section}]: duplicate key {match.group(2)!r}."
            )
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
    _reject_unsupported_toml(text)
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

    transport_conflicts = _entry_transport_conflicts(entry)
    if transport_conflicts:
        fields = ", ".join(transport_conflicts)
        raise BootstrapError(
            "Existing ultraplot MCP entry contains transport/auth fields that "
            f"conflict with stdio: {fields}."
        )
    timeout_status, timeout_reasons = _entry_timeout_status(entry)
    if timeout_status == "conflict":
        raise BootstrapError(
            "Existing ultraplot MCP entry has invalid timeout settings: "
            + "; ".join(timeout_reasons)
            + "."
        )

    environment_status, environment_reasons = _entry_environment_status(entry, runtime)
    if environment_status == "conflict" or (
        environment_status == "unverified" and not force
    ):
        detail = "; ".join(environment_reasons) or "startup environment is not verifiable"
        raise BootstrapError(
            "Existing ultraplot MCP startup environment requires manual review: "
            f"{detail}."
        )

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
    args_match = isinstance(args, list) and args == ["-m", "ultraplot.mcp"]
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


@contextmanager
def _config_lock(path: Path):
    """Serialize config writes across concurrent first-use invocations."""
    lock_path = path.parent / f".{path.name}.ultraplot.lock"
    stream = None
    file_descriptor = None
    locked = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if lock_path.is_symlink():
            raise BootstrapError(f"Refusing symlinked config lock: {lock_path}")
        flags = os.O_RDWR | os.O_CREAT | os.O_APPEND
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if nofollow:
            flags |= nofollow
        try:
            file_descriptor = os.open(str(lock_path), flags, 0o600)
            stream = os.fdopen(file_descriptor, "a+b")
            file_descriptor = None
        except OSError as exc:
            if getattr(exc, "errno", None) == getattr(errno, "ELOOP", 40):
                raise BootstrapError(
                    f"Refusing symlinked config lock: {lock_path}"
                ) from exc
            raise
        # Recheck after opening to catch a link swap between the preflight and
        # open calls.  POSIX callers additionally benefit from the explicit
        # check below even when the platform lacks O_NOFOLLOW.
        if lock_path.is_symlink():
            stream.close()
            stream = None
            raise BootstrapError(f"Refusing symlinked config lock: {lock_path}")
        # Windows locking requires a byte to exist at the requested offset.
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + CONFIG_LOCK_TIMEOUT
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    try:
                        import fcntl
                    except ImportError:  # pragma: no cover - unusual platforms
                        break
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except (OSError, RuntimeError, ValueError) as exc:
                if time.monotonic() >= deadline:
                    raise BootstrapError(
                        f"Timed out waiting for the config lock: {lock_path}"
                    ) from exc
                time.sleep(0.05)
        yield
    except BootstrapError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise BootstrapError(f"Could not lock config.toml: {exc}") from exc
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        if stream is not None:
            if locked:
                try:
                    if os.name == "nt":
                        import msvcrt

                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        try:
                            import fcntl
                        except ImportError:  # pragma: no cover - unusual platforms
                            pass
                        else:
                            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                except (OSError, RuntimeError, ValueError):
                    pass
            try:
                stream.close()
            except OSError:
                pass


def _atomic_replace(path: Path, original: bytes, updated: bytes) -> None:
    if original == updated:
        return
    with _config_lock(path):
        _atomic_replace_unlocked(path, original, updated)


def _preflight_config_write(path: Path) -> None:
    """Check lock/parent access before an optional package mutation."""
    with _config_lock(path):
        if path.is_symlink():
            raise BootstrapError(f"Refusing to replace symlinked config: {path}")
        if path.exists() and not path.is_file():
            raise BootstrapError(f"Config path is not a regular file: {path}")


def _atomic_replace_unlocked(path: Path, original: bytes, updated: bytes) -> None:
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
    except (OSError, RuntimeError) as exc:
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
    except (OSError, RuntimeError) as exc:
        try:
            os.unlink(temporary_name)
        except (OSError, RuntimeError):
            pass
        raise BootstrapError(f"Could not replace {path}: {exc}") from exc


def _write_config(
    path: Path,
    runtime: dict[str, Any],
    docs_path: str | None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    try:
        if path.is_symlink():
            raise BootstrapError(f"Refusing to replace symlinked config: {path}")
        if path.exists() and not path.is_file():
            raise BootstrapError(f"Config path is not a regular file: {path}")
        original = path.read_bytes() if path.exists() else b""
        text = original.decode("utf-8-sig")
    except BootstrapError:
        raise
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
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
        main_values["command"] = _toml_string(str(_safe_resolve(runtime["python"])))
    if "args" not in main_keys or force or not (
        isinstance(args, list) and args == ["-m", "ultraplot.mcp"]
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
        docs_value = str(_safe_resolve(docs_path))
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
    if dry_run:
        return True
    _atomic_replace(path, original, updated_bytes)
    return True


def _candidate_docs(runtime: dict[str, Any]) -> str | None:
    version = runtime.get("ultraplot_version")
    if not isinstance(version, str):
        return None
    sources_root = _safe_resolve(_codex_home() / "mcp-sources")

    def is_canonical_candidate(value: str | None) -> bool:
        if not value:
            return False
        try:
            resolved_value = _safe_resolve(value)
            return os.path.commonpath(
                [_canonical_path(resolved_value), _canonical_path(sources_root)]
            ) == _canonical_path(sources_root)
        except (OSError, RuntimeError, ValueError):
            return False

    configured = os.environ.get("ULTRAPLOT_MCP_DOCS")
    if _docs_available(
        configured,
        expected_version=version,
        require_version_marker=True,
    ) and is_canonical_candidate(configured):
        return str(_safe_resolve(configured))
    if version:
        candidate = sources_root / f"ultraplot-{version}" / "docs"
        try:
            resolved = _safe_resolve(candidate)
            if (
                os.path.commonpath([_canonical_path(resolved), _canonical_path(sources_root)])
                == _canonical_path(sources_root)
                and _docs_available(
                    str(resolved),
                    expected_version=version,
                    require_version_marker=True,
                )
            ):
                return str(resolved)
        except (OSError, RuntimeError, ValueError):
            return None
    return None


def _dependency_requirement(runtime: dict[str, Any]) -> str:
    version = runtime.get("ultraplot_version")
    if not _supported_ultraplot_version(version):
        raise BootstrapError(
            "Cannot install the MCP extra because the selected UltraPlot version "
            "is unknown or outside the supported stable 2.7.x range."
        )
    return f"ultraplot[mcp]=={version}"


def _redacted_diagnostic(value: object, *, limit: int = MAX_PIP_DIAGNOSTIC) -> str:
    """Keep installer diagnostics useful without echoing common credentials."""
    if value is None:
        return ""
    # Bound the input before applying regexes so an unexpectedly large build
    # log cannot consume unbounded memory in the diagnostic path.
    text = str(value).strip()
    if len(text) > limit * 4:
        text = text[: limit * 4] + "...[truncated]"
    if not text:
        return ""
    text = _URL_CREDENTIAL_RE.sub(r"\1<redacted>:<redacted>@", text)
    text = _URL_USERINFO_RE.sub(r"\1<redacted>@\3", text)
    text = _AUTH_BEARER_RE.sub(r"\1<redacted>", text)
    text = _AUTH_BASIC_RE.sub(r"\1<redacted>", text)
    text = _SECRET_VALUE_RE.sub(r"\1<redacted>", text)
    if len(text) > limit:
        return text[: max(0, limit - 14)] + "...[truncated]"
    return text


def _pip_environment() -> dict[str, str]:
    """Keep package operations isolated from local import/user-site shadowing."""
    environment = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE"):
        environment.pop(key, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _run_pip_requirement(
    executable: str | None, requirement: str, *, upgrade: bool = False
) -> None:
    if not isinstance(executable, str):
        raise BootstrapError("Cannot install UltraPlot packages without a selected Python.")
    command = [
        executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
    ]
    if upgrade:
        command.append("--upgrade")
    command.append(requirement)
    try:
        # Run pip outside the task/project directory so a local ``pip.py`` or
        # ``pip`` package cannot shadow the selected interpreter's installer.
        with tempfile.TemporaryDirectory(prefix="ultraplot-pip-") as pip_cwd:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=pip_cwd,
                env=_pip_environment(),
                encoding="utf-8",
                errors="replace",
                check=False,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootstrapError(f"Could not install {requirement}: {exc}") from exc
    if result.returncode:
        detail = _redacted_diagnostic(getattr(result, "stderr", None))
        suffix = f": {detail}" if detail else "."
        raise BootstrapError(
            f"Could not install {requirement} (exit {result.returncode}){suffix}"
        )


def _install_dependency(runtime: dict[str, Any]) -> None:
    requirement = _dependency_requirement(runtime)
    _run_pip_requirement(runtime.get("python"), requirement)


def _install_ultraplot(
    executable: str, target_version: str, *, upgrade: bool = False
) -> str:
    """Install the base package and MCP extra in one exact-version operation."""
    if not _supported_ultraplot_version(target_version):
        raise BootstrapError(
            "The requested UltraPlot target is outside the supported stable 2.7.x range."
        )
    requirement = f"ultraplot[mcp]=={target_version}"
    _run_pip_requirement(executable, requirement, upgrade=upgrade)
    return requirement


def _configuration_plan(
    state: dict[str, Any],
    runtime: dict[str, Any],
    docs_path: str | None,
) -> tuple[str | None, str | None, bool]:
    """Resolve documentation input and the value that should be written."""
    current_docs = state["server"].get("docs_path")
    if docs_path:
        if not _docs_available(docs_path):
            raise BootstrapError(f"Documentation path is not a valid checkout: {docs_path}")
        selected_docs = docs_path
    elif current_docs and _docs_match_runtime(current_docs, runtime):
        selected_docs = current_docs
    else:
        # A stale, relative, or version-unverified path should not prevent
        # API-capable setup.  Only use a canonical, version-marked tree that is
        # already present on this machine.
        selected_docs = _candidate_docs(runtime)
        if selected_docs and not _docs_match_runtime(selected_docs, runtime):
            selected_docs = None
    if selected_docs:
        selected_docs = str(_safe_resolve(selected_docs))

    docs_changed = bool(
        selected_docs
        and (
            not current_docs
            or _canonical_path(selected_docs) != _canonical_path(current_docs)
        )
    )
    docs_value = selected_docs if docs_changed or not current_docs else None
    return selected_docs, docs_value, docs_changed


def _auto_setup_disabled() -> bool:
    value = os.environ.get(AUTO_SETUP_ENV)
    return value is not None and value.strip().lower() in AUTO_SETUP_DISABLED_VALUES


def _env_enabled(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in AUTO_SETUP_ENABLED_VALUES:
        return True
    if normalized in AUTO_SETUP_DISABLED_VALUES:
        return False
    raise BootstrapError(
        f"{name} must be one of: {', '.join(sorted(AUTO_SETUP_ENABLED_VALUES | AUTO_SETUP_DISABLED_VALUES))}."
    )


def _package_policy(value: str | None = None) -> str:
    """Resolve the explicit or environment-controlled base-package policy."""
    raw = value
    if raw is None:
        raw = os.environ.get(PACKAGE_POLICY_ENV)
    if raw is not None and raw.strip():
        normalized = raw.strip().lower().replace("_", "-")
        if normalized not in PACKAGE_POLICIES:
            raise BootstrapError(
                f"{PACKAGE_POLICY_ENV} must be one of: "
                f"{', '.join(sorted(PACKAGE_POLICIES))}."
            )
        return normalized
    install = _env_enabled(AUTO_INSTALL_ULTRAPLOT_ENV)
    upgrade = _env_enabled(AUTO_UPGRADE_ULTRAPLOT_ENV)
    if install and upgrade:
        return "install-and-upgrade"
    if install:
        return "install"
    if upgrade:
        return "upgrade"
    return "manual"


def _policy_allows(policy: str, operation: str) -> bool:
    return policy in {operation, "install-and-upgrade"}


def _runtime_package_manager(runtime: dict[str, Any]) -> str:
    value = runtime.get("package_manager")
    return value.strip().lower() if isinstance(value, str) and value.strip() else "unknown"


def _package_manager_allowed(
    runtime: dict[str, Any], *, allow_pip_in_conda: bool = False
) -> bool:
    manager = _runtime_package_manager(runtime)
    return manager == "pip" or (
        allow_pip_in_conda and manager in {"conda", "mixed"}
    )


def _upgrade_provenance_is_safe(
    runtime: dict[str, Any], *, allow_pip_in_conda: bool = False
) -> bool:
    """Allow normal pip upgrades; conda/mixed needs an explicit review flag."""
    manager_allowed = _package_manager_allowed(
        runtime, allow_pip_in_conda=allow_pip_in_conda
    )
    return (
        runtime.get("ultraplot_provenance") == "installed"
        and not runtime.get("ultraplot_editable", False)
        and manager_allowed
    )


def _allow_pip_in_conda(value: bool = False) -> bool:
    return bool(value or _env_enabled(ALLOW_PIP_IN_CONDA_ENV))


def _preflight_package_mutation(
    path: Path, executable: Path, runtime: dict[str, Any] | None = None
) -> None:
    """Reject config hazards before changing the selected Python environment."""
    _preflight_config_write(path)
    config, parse_error = _read_config(path)
    if parse_error:
        raise BootstrapError(f"{path} is not safe to edit: {parse_error}")
    try:
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        raise BootstrapError(f"Could not read {path}: {exc}") from exc
    _entry_conflict(
        text,
        config,
        runtime or {"python": str(executable)},
        docs_path=None,
        force=False,
    )


def _is_configured_state(state: dict[str, Any]) -> bool:
    """Require an aligned, enabled entry before reporting setup success."""
    if state.get("status") not in {"configured", "configured_without_docs"}:
        return False
    server = state.get("server")
    return isinstance(server, dict) and server.get("aligned") is True and server.get("enabled") is True


def configure(
    path: Path,
    *,
    confirm: bool,
    install_dependencies: bool,
    docs_path: str | None,
    executable: Path | None = None,
    force: bool = False,
    allow_pip_in_conda: bool = False,
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
    if state["status"] == "unsupported_ultraplot_version":
        raise BootstrapError(
            "The installed UltraPlot version does not provide the official MCP "
            "server; configuration supports the stable UltraPlot 2.7.x series."
        )
    if state["status"] == "ultraplot_provenance_unverified":
        raise BootstrapError(
            "The selected UltraPlot source/version cannot be safely identified; "
            "install the matching MCP extra manually instead of replacing it from PyPI."
        )
    if state["status"] in {"configuration_conflict", "configuration_unverified"}:
        reasons = state.get("server", {}).get("environment_reasons", [])
        detail = "; ".join(reasons) if isinstance(reasons, list) else ""
        raise BootstrapError(
            "The existing MCP startup environment requires manual review"
            f"{': ' + detail if detail else '.'}"
        )

    # Validate the complete line-preserving edit before any optional package
    # installation.  This keeps a conflicting or malformed config from
    # causing an otherwise unnecessary environment mutation.
    _, planned_docs, docs_changed = _configuration_plan(state, runtime, docs_path)
    dependency_installed = False
    if state["status"] == "missing_mcp_dependency":
        if not install_dependencies:
            raise BootstrapError(
                "The selected environment lacks UltraPlot MCP dependencies; "
                "rerun with --install-dependencies after authorization."
            )
        allow_pip_in_conda = _allow_pip_in_conda(allow_pip_in_conda)
        if not _package_manager_allowed(
            runtime, allow_pip_in_conda=allow_pip_in_conda
        ):
            manager = _runtime_package_manager(runtime)
            if manager in {"conda", "mixed"}:
                reason = (
                    "The selected environment is conda-managed or mixed; automatic "
                    "pip installation of UltraPlot MCP dependencies is disabled."
                )
                raise BootstrapError(
                    f"{reason} Review the environment and pass --allow-pip-in-conda "
                    f"or set {ALLOW_PIP_IN_CONDA_ENV}=1 to authorize it."
                )
            else:
                raise BootstrapError(
                    "The selected package manager could not be verified; automatic "
                    "pip installation of UltraPlot MCP dependencies is disabled. "
                    "Install the matching extra with the environment's package "
                    "manager after verifying its provenance."
                )
        _write_config(path, runtime, planned_docs, force=force, dry_run=True)
        _preflight_config_write(path)
        _install_dependency(runtime)
        state = inspect_state(path, executable)
        runtime = state["runtime"]
        if state["status"] in {
            "missing_mcp_dependency",
            "unsupported_ultraplot_version",
        }:
            raise BootstrapError("MCP dependencies are still unavailable after installation.")
        dependency_installed = True

    selected_docs, planned_docs, docs_changed = _configuration_plan(
        state, runtime, docs_path
    )
    if (
        state["status"] in {"configured", "configured_without_docs"}
        and state["server"].get("aligned")
        and not docs_changed
    ):
        return {
            **state,
            "action": "dependencies_installed" if dependency_installed else "unchanged",
            "dependency_installed": dependency_installed,
            "restart_required": dependency_installed,
            **(
                {
                    "message": (
                        "Restart Codex or start a new task before relying on the "
                        "updated MCP dependency."
                    )
                }
                if dependency_installed
                else {}
            ),
        }

    _write_config(path, runtime, planned_docs, force=force, dry_run=True)
    changed = _write_config(
        path,
        runtime,
        planned_docs,
        force=force,
    )
    result = inspect_state(path, executable)
    if not _is_configured_state(result):
        raise BootstrapError(
            "MCP configuration could not be verified after writing config.toml "
            f"(observed status: {result.get('status')})."
        )
    result["action"] = (
        "dependencies_installed_and_configured"
        if dependency_installed and changed
        else "dependencies_installed"
        if dependency_installed
        else "configured"
        if changed
        else "unchanged"
    )
    result["dependency_installed"] = dependency_installed
    result["restart_required"] = changed or dependency_installed
    result["message"] = "Restart Codex or start a new task before relying on the new MCP entry."
    return result


def _bootstrap_result(
    state: dict[str, Any],
    *,
    bootstrap_status: str,
    action: str = "unchanged",
    dependency_requirement: str | None = None,
    dependency_installed: bool = False,
    dependency_install_attempted: bool = False,
    package_policy: str = "manual",
    package_action: str = "none",
    package_requirement: str | None = None,
    base_install_attempted: bool = False,
    base_installed: bool = False,
    upgrade_attempted: bool = False,
    upgraded: bool = False,
    previous_version: str | None = None,
    target_version: str | None = None,
    package_manager: str | None = None,
    mutation_attempted: bool = False,
    config_changed: bool = False,
    partial: bool = False,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    result = {
        **state,
        "bootstrap_status": bootstrap_status,
        "action": action,
        "dependency_requirement": dependency_requirement,
        "dependency_installed": dependency_installed,
        "dependency_install_attempted": dependency_install_attempted,
        "package_policy": package_policy,
        "package_action": package_action,
        "package_requirement": package_requirement,
        "base_install_attempted": base_install_attempted,
        "base_installed": base_installed,
        "upgrade_attempted": upgrade_attempted,
        "upgraded": upgraded,
        "previous_version": previous_version,
        "target_version": target_version,
        "package_manager": package_manager,
        "mutation_attempted": mutation_attempted,
        "config_changed": config_changed,
        "partial": partial,
        "restart_required": bool(
            dependency_installed
            or base_installed
            or upgraded
            or config_changed
            or partial
        ),
    }
    if result["restart_required"]:
        result["message"] = (
            "Restart Codex or start a new task before relying on the new MCP entry."
        )
    if fallback_reason:
        result["fallback_reason"] = fallback_reason
    return result


def _bootstrap_error_status(error: BootstrapError) -> str:
    message = str(error).lower()
    if "already at or newer" in message:
        return "upgrade_not_needed"
    if "exact target version is required" in message:
        return "upgrade_target_required"
    if "installation completed but" in message or "upgrade completed but" in message:
        return "package_verification_failed"
    if "target version" in message or "target is outside" in message:
        return "package_target_invalid"
    if "not a normal pip installation" in message or "require manual upgrade" in message:
        return "upgrade_requires_manual"
    if (
        "conda environment" in message
        or "conda-managed" in message
        or "not a verified pip environment" in message
        or "package manager could not be verified" in message
    ):
        return "package_manager_requires_manual"
    if (
        "does not provide the official mcp" in message
        or "requires ultraplot 2.7.0" in message
        or "stable ultraplot 2.7.x" in message
        or "supports the stable ultraplot 2.7.x" in message
    ):
        return "unsupported_ultraplot_version"
    if "source/version cannot be safely identified" in message:
        return "ultraplot_provenance_unverified"
    if "could not be verified after writing" in message or "verification" in message:
        return "configuration_verification_failed"
    if "changed while" in message:
        return "configuration_changed"
    if "could not lock config.toml" in message or "waiting for the config lock" in message:
        return "configuration_lock_failed"
    if "multiline" in message or "complex" in message:
        return "configuration_conflict"
    if "install" in message or "mcp extra" in message:
        return "install_failed"
    if (
        "existing ultraplot" in message
        or "inline" in message
        or "dotted table" in message
        or "not a toml table" in message
        or "conflicting" in message
        or "startup environment" in message
        or "manual review" in message
        or "symlinked config" in message
    ):
        return "configuration_conflict"
    if "invalid toml" in message or "config.toml" in message:
        return "config_invalid"
    return "configuration_failed"


def _package_metadata() -> dict[str, Any]:
    return {
        "package_action": "none",
        "package_requirement": None,
        "base_install_attempted": False,
        "base_installed": False,
        "upgrade_attempted": False,
        "upgraded": False,
        "previous_version": None,
        "target_version": None,
        "package_manager": None,
        "mutation_attempted": False,
    }


def _package_result_kwargs(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: metadata.get(key)
        for key in (
            "package_action",
            "package_requirement",
            "base_install_attempted",
            "base_installed",
            "upgrade_attempted",
            "upgraded",
            "previous_version",
            "target_version",
            "package_manager",
        )
    }


def _perform_base_package_action(
    path: Path,
    state: dict[str, Any],
    executable: Path,
    *,
    policy: str,
    requested_version: str | None,
    metadata: dict[str, Any] | None = None,
    allow_pip_in_conda: bool = False,
    docs_path: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Optionally install/upgrade UltraPlot before MCP configuration."""
    metadata = metadata if metadata is not None else _package_metadata()
    runtime = state["runtime"]
    metadata["package_manager"] = _runtime_package_manager(runtime)
    status = state["status"]
    if docs_path and not _docs_available(docs_path):
        raise BootstrapError(f"Documentation path is not a valid checkout: {docs_path}")

    if status == "missing_ultraplot":
        if not _policy_allows(policy, "install"):
            return state, metadata, "UltraPlot is not installed; enable the install policy or install it manually."
        target = _target_ultraplot_version(requested_version)
        metadata["target_version"] = target
        metadata["package_requirement"] = f"ultraplot[mcp]=={target}"
        if not _package_manager_allowed(
            runtime, allow_pip_in_conda=allow_pip_in_conda
        ):
            manager = _runtime_package_manager(runtime)
            if manager in {"conda", "mixed"}:
                reason = (
                    "The selected interpreter is conda-managed or mixed; automatic "
                    "base-package installation with pip is disabled. Review the "
                    f"environment before enabling {ALLOW_PIP_IN_CONDA_ENV}."
                )
            else:
                reason = (
                    "The selected package manager could not be verified; automatic "
                    "base-package installation is disabled. Install UltraPlot with "
                    "the environment's package manager or use a verified pip "
                    "environment."
                )
            raise BootstrapError(reason)
        _preflight_package_mutation(path, executable, runtime)
        metadata["package_action"] = "install_base"
        metadata["base_install_attempted"] = True
        metadata["mutation_attempted"] = True
        with _config_lock(path):
            _install_ultraplot(str(executable), target)
        refreshed = inspect_state(path, executable)
        refreshed_runtime = refreshed["runtime"]
        metadata["package_manager"] = _runtime_package_manager(refreshed_runtime)
        if (
            refreshed_runtime.get("ultraplot_version") != target
            or not refreshed_runtime.get("ultraplot_available")
            or not _supported_ultraplot_version(refreshed_runtime.get("ultraplot_version"))
            or refreshed_runtime.get("ultraplot_provenance") != "installed"
            or not _package_manager_allowed(
                refreshed_runtime, allow_pip_in_conda=allow_pip_in_conda
            )
        ):
            raise BootstrapError(
                "UltraPlot installation completed but the selected interpreter did not "
                f"expose the verified target version {target}."
            )
        metadata["base_installed"] = True
        return refreshed, metadata, None

    if not _policy_allows(policy, "upgrade"):
        return state, metadata, None

    current = runtime.get("ultraplot_version")
    current_key = _version_key(current)
    if not runtime.get("ultraplot_available") or current_key is None:
        raise BootstrapError(
            "The installed UltraPlot version cannot be safely compared for an upgrade."
        )
    target = _target_ultraplot_version(requested_version, required=True)
    target_key = _version_key(target)
    metadata["previous_version"] = current if isinstance(current, str) else None
    metadata["target_version"] = target
    metadata["package_requirement"] = f"ultraplot[mcp]=={target}"
    metadata["package_manager"] = _runtime_package_manager(runtime)
    if target_key is None or target_key <= current_key:
        return state, metadata, (
            f"UltraPlot {current} is already at or newer than the requested target {target}; "
            "no downgrade was attempted."
        )
    if not _supported_ultraplot_version(current) and status != "unsupported_ultraplot_version":
        raise BootstrapError("The installed UltraPlot version is not safely upgradeable.")
    if not _upgrade_provenance_is_safe(
        runtime, allow_pip_in_conda=allow_pip_in_conda
    ):
        raise BootstrapError(
            "The selected UltraPlot installation is not a normal pip installation; "
            "editable, remote, and unknown sources always require manual upgrade. "
            "A conda-managed or mixed environment additionally requires explicit "
            f"review and {ALLOW_PIP_IN_CONDA_ENV}=1."
        )
    _preflight_package_mutation(path, executable, runtime)
    metadata["package_action"] = "upgrade_base"
    metadata["upgrade_attempted"] = True
    metadata["mutation_attempted"] = True
    with _config_lock(path):
        _install_ultraplot(str(executable), target, upgrade=True)
    refreshed = inspect_state(path, executable)
    refreshed_runtime = refreshed["runtime"]
    metadata["package_manager"] = _runtime_package_manager(refreshed_runtime)
    if (
        refreshed_runtime.get("ultraplot_version") != target
        or not refreshed_runtime.get("ultraplot_available")
        or not _supported_ultraplot_version(refreshed_runtime.get("ultraplot_version"))
        or refreshed_runtime.get("ultraplot_provenance") != "installed"
        or not _package_manager_allowed(
            refreshed_runtime, allow_pip_in_conda=allow_pip_in_conda
        )
    ):
        raise BootstrapError(
            "UltraPlot upgrade completed but the selected interpreter did not expose "
            f"the verified target version {target}."
        )
    metadata["upgraded"] = True
    return refreshed, metadata, None


def bootstrap(
    path: Path,
    *,
    docs_path: str | None,
    executable: Path | None = None,
    force: bool = False,
    automatic: bool = True,
    package_policy: str | None = None,
    ultraplot_version: str | None = None,
    allow_pip_in_conda: bool = False,
) -> dict[str, Any]:
    """Check, optionally mutate the package, then configure MCP safely.

    Base-package installation and upgrades are opt-in through ``package_policy``
    or the documented environment variables. The ordinary first-use path still
    fails open and returns structured diagnostics instead of prompting.
    """
    if executable is not None:
        executable = _resolve_python(str(executable))
    state = inspect_state(path, executable)
    if executable is None:
        executable = Path(state["runtime"].get("python", sys.executable))
    force = False
    metadata = _package_metadata()
    try:
        policy = _package_policy(package_policy)
    except BootstrapError as exc:
        return _bootstrap_result(
            state,
            bootstrap_status="package_policy_invalid",
            action="fallback",
            package_policy="manual",
            fallback_reason=str(exc),
        )
    auto_disabled = not automatic or _auto_setup_disabled()
    if auto_disabled:
        policy = "manual"
    try:
        allow_pip_in_conda = _allow_pip_in_conda(allow_pip_in_conda)
    except BootstrapError as exc:
        return _bootstrap_result(
            state,
            bootstrap_status="package_policy_invalid",
            action="fallback",
            package_policy=policy,
            fallback_reason=str(exc),
        )

    if state["status"] in {"config_invalid", "interpreter_error"}:
        reason = (
            "Codex config.toml is invalid; no changes were made."
            if state["status"] == "config_invalid"
            else "The selected plotting interpreter could not be inspected."
        )
        return _bootstrap_result(
            state,
            bootstrap_status=state["status"],
            action="fallback",
            package_policy=policy,
            fallback_reason=reason,
        )

    package_note: str | None = None
    try:
        selected_executable = executable or Path(state["runtime"]["python"])
        state, metadata, package_note = _perform_base_package_action(
            path,
            state,
            selected_executable,
            policy=policy,
            requested_version=ultraplot_version,
            metadata=metadata,
            allow_pip_in_conda=allow_pip_in_conda,
            docs_path=docs_path,
        )
    except (BootstrapError, OSError, subprocess.SubprocessError) as raw_error:
        exc = raw_error if isinstance(raw_error, BootstrapError) else BootstrapError(str(raw_error))
        try:
            current = inspect_state(path, executable)
        except (BootstrapError, OSError, subprocess.SubprocessError):
            current = state
        return _bootstrap_result(
            current,
            bootstrap_status=_bootstrap_error_status(exc),
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            mutation_attempted=bool(metadata.get("mutation_attempted")),
            partial=bool(metadata.get("mutation_attempted")),
            fallback_reason=str(exc),
        )

    if state["status"] == "missing_ultraplot":
        status = "base_install_required" if policy == "manual" else "base_install_disabled"
        reason = package_note or (
            "UltraPlot is not installed; enable the install policy or install it manually."
        )
        if auto_disabled:
            status = "opted_out"
            reason = f"Automatic package and MCP setup is disabled by {AUTO_SETUP_ENV}."
        return _bootstrap_result(
            state,
            bootstrap_status=status,
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            fallback_reason=reason,
        )

    if state["status"] in {
        "unsupported_ultraplot_version",
        "ultraplot_provenance_unverified",
        "configuration_conflict",
        "configuration_unverified",
    }:
        reason = {
            "unsupported_ultraplot_version": (
                "The installed UltraPlot version is outside the supported stable 2.7.x range."
            ),
            "ultraplot_provenance_unverified": (
                "The selected UltraPlot source/version cannot be verified; no replacement was attempted."
            ),
            "configuration_conflict": (
                "The existing MCP startup environment is malformed; no changes were made."
            ),
            "configuration_unverified": (
                "The existing MCP startup environment cannot be verified; no changes were made."
            ),
        }[state["status"]]
        return _bootstrap_result(
            state,
            bootstrap_status=state["status"],
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            fallback_reason=package_note or reason,
        )

    if auto_disabled:
        return _bootstrap_result(
            state,
            bootstrap_status="opted_out",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            fallback_reason=f"Automatic MCP setup is disabled by {AUTO_SETUP_ENV}.",
        )

    # A configured server without docs is still useful for API/source calls.
    if (
        state["status"] == "configured"
        and not docs_path
        and not package_note
        and not metadata.get("base_installed")
        and not metadata.get("upgraded")
    ):
        return _bootstrap_result(
            state,
            bootstrap_status="ready",
            package_policy=policy,
            **_package_result_kwargs(metadata),
        )
    if state["status"] == "configured_without_docs":
        try:
            _, planned_docs, docs_changed = _configuration_plan(
                state, state["runtime"], docs_path
            )
        except BootstrapError as exc:
            return _bootstrap_result(
                state,
                bootstrap_status=_bootstrap_error_status(exc),
                action="fallback",
                package_policy=policy,
                **_package_result_kwargs(metadata),
                fallback_reason=str(exc),
            )
        if not docs_changed:
            package_changed = bool(
                metadata.get("base_installed") or metadata.get("upgraded")
            )
            return _bootstrap_result(
                state,
                bootstrap_status=(
                    "base_package_changed"
                    if package_changed
                    else "upgrade_not_needed"
                    if package_note
                    else "ready_without_docs"
                ),
                action="base_package_changed" if package_changed else "unchanged",
                package_policy=policy,
                **_package_result_kwargs(metadata),
                fallback_reason=package_note
                or "No matching UltraPlot documentation directory is configured.",
                mutation_attempted=bool(metadata.get("mutation_attempted")),
            )

    runtime = state["runtime"]
    needs_dependency = state["status"] == "missing_mcp_dependency"
    if needs_dependency and not _package_manager_allowed(
        runtime, allow_pip_in_conda=allow_pip_in_conda
    ):
        manager = _runtime_package_manager(runtime)
        if manager in {"conda", "mixed"}:
            reason = (
                "The selected environment is conda-managed or mixed; automatic pip "
                "installation of UltraPlot MCP dependencies is disabled."
            )
        else:
            reason = (
                "The selected package manager could not be verified; automatic pip "
                "installation of UltraPlot MCP dependencies is disabled."
            )
        return _bootstrap_result(
            state,
            bootstrap_status="package_manager_requires_manual",
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            fallback_reason=reason,
        )
    if needs_dependency and runtime.get("ultraplot_editable"):
        return _bootstrap_result(
            state,
            bootstrap_status="editable_ultraplot",
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            fallback_reason=(
                "The selected UltraPlot installation is editable; use an explicit "
                "development checkout MCP install instead of replacing it from PyPI."
            ),
        )
    requirement: str | None = None
    dependency_installed = False
    dependency_install_attempted = False
    mutation_attempted = bool(metadata.get("mutation_attempted"))
    config_changed = False

    try:
        validated_requirement = _dependency_requirement(runtime)
        if needs_dependency:
            requirement = validated_requirement

        _, planned_docs, docs_changed = _configuration_plan(
            state, runtime, docs_path
        )
        should_edit = state["status"] in {
            "needs_configuration",
            "missing_mcp_dependency",
            "configured_without_docs",
        } or docs_changed
        if should_edit:
            _write_config(path, runtime, planned_docs, force=force, dry_run=True)

        if needs_dependency:
            mutation_attempted = True
            dependency_install_attempted = True
            _preflight_config_write(path)
            with _config_lock(path):
                _install_dependency(runtime)
            state = inspect_state(path, executable)
            runtime = state["runtime"]
            if state["status"] == "missing_mcp_dependency":
                raise BootstrapError(
                    "MCP dependencies are still unavailable after installation."
                )
            if state["status"] in {
                "config_invalid",
                "interpreter_error",
                "missing_ultraplot",
                "unsupported_ultraplot_version",
            }:
                raise BootstrapError(
                    f"Readiness changed unexpectedly after installing {requirement}."
                )
            dependency_installed = True

        _, planned_docs, docs_changed = _configuration_plan(
            state, runtime, docs_path
        )
        if (
            state["status"] in {"configured", "configured_without_docs"}
            and state["server"].get("aligned")
            and not docs_changed
        ):
            package_changed = bool(metadata.get("base_installed") or metadata.get("upgraded"))
            action = (
                "dependencies_installed" if dependency_installed else
                "base_package_changed" if package_changed else "unchanged"
            )
            bootstrap_status = (
                "dependencies_installed" if dependency_installed else
                "base_package_changed" if package_changed else
                "upgrade_not_needed" if package_note else "ready"
            )
            return _bootstrap_result(
                state,
                bootstrap_status=bootstrap_status,
                action=action,
                package_policy=policy,
                **_package_result_kwargs(metadata),
                dependency_requirement=requirement,
                dependency_installed=dependency_installed,
                dependency_install_attempted=dependency_install_attempted,
                mutation_attempted=mutation_attempted,
            )

        _write_config(path, runtime, planned_docs, force=force, dry_run=True)
        mutation_attempted = True
        config_changed = _write_config(path, runtime, planned_docs, force=force)
        result = inspect_state(path, executable)
        if not _is_configured_state(result):
            raise BootstrapError(
                "MCP configuration could not be verified after writing config.toml "
                f"(observed status: {result.get('status')})."
            )
        package_changed = bool(metadata.get("base_installed") or metadata.get("upgraded"))
        both = dependency_installed and config_changed
        action = (
            "dependencies_installed_and_configured"
            if both
            else "dependencies_installed"
            if dependency_installed
            else "base_package_and_configured"
            if package_changed and config_changed
            else "base_package_changed"
            if package_changed
            else "configured"
            if config_changed
            else "unchanged"
        )
        return _bootstrap_result(
            result,
            bootstrap_status=(
                "dependencies_and_configured"
                if both
                else "dependencies_installed"
                if dependency_installed
                else "base_package_and_configured"
                if package_changed and config_changed
                else "base_package_changed"
                if package_changed
                else "configured"
                if config_changed
                else "upgrade_not_needed"
                if package_note
                else "ready"
            ),
            action=action,
            package_policy=policy,
            **_package_result_kwargs(metadata),
            dependency_requirement=requirement,
            dependency_installed=dependency_installed,
            dependency_install_attempted=dependency_install_attempted,
            mutation_attempted=mutation_attempted,
            config_changed=config_changed,
        )
    except (BootstrapError, OSError, subprocess.SubprocessError) as raw_error:
        exc = raw_error if isinstance(raw_error, BootstrapError) else BootstrapError(str(raw_error))
        try:
            current = inspect_state(path, executable)
        except (BootstrapError, OSError, subprocess.SubprocessError):
            current = state
        return _bootstrap_result(
            current,
            bootstrap_status=_bootstrap_error_status(exc),
            action="fallback",
            package_policy=policy,
            **_package_result_kwargs(metadata),
            dependency_requirement=requirement,
            dependency_installed=dependency_installed,
            dependency_install_attempted=dependency_install_attempted,
            mutation_attempted=mutation_attempted,
            config_changed=config_changed,
            partial=dependency_install_attempted
            or dependency_installed
            or bool(metadata.get("mutation_attempted"))
            or bool(metadata.get("base_installed"))
            or bool(metadata.get("upgraded"))
            or config_changed,
            fallback_reason=str(exc),
        )


def _self_test() -> dict[str, Any]:
    from unittest import mock

    if tomllib is None:  # pragma: no cover - Python 3.10 without tomli
        raise BootstrapError(
            "self-test requires Python 3.11+ or the 'tomli' package."
        )
    tests: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ultraplot-mcp-test-") as directory:
        root = Path(directory)

        # pathlib raises RuntimeError for some symlink loops.  Canonicalizing
        # a user-supplied command path must retain a usable fallback instead
        # of escaping the bootstrap's fail-open error handling.
        original_path_resolve = Path.resolve

        def raising_path_resolve(self: Path, strict: bool = False) -> Path:
            raise RuntimeError("symlink loop")

        Path.resolve = raising_path_resolve  # type: ignore[assignment]
        try:
            canonical_fallback = _canonical_path("relative-command")
        finally:
            Path.resolve = original_path_resolve  # type: ignore[assignment]
        assert canonical_fallback == os.path.normcase(
            os.path.abspath("relative-command")
        )
        tests.append("canonical_path_symlink_loop_fallback")

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
        versioned_docs = root / "mcp-sources" / "ultraplot-2.7.0" / "docs"
        versioned_docs.mkdir(parents=True)
        (versioned_docs / "conf.py").write_text("# test\n", encoding="utf-8")
        (versioned_docs / "index.rst").write_text("UltraPlot\n=========\n", encoding="utf-8")
        docs_runtime = {"ultraplot_version": "2.7.0"}
        assert _docs_match_runtime(str(versioned_docs), docs_runtime)
        wrong_docs = root / "mcp-sources" / "ultraplot-2.6.0" / "docs"
        wrong_docs.mkdir(parents=True)
        (wrong_docs / "conf.py").write_text("# test\n", encoding="utf-8")
        (wrong_docs / "index.rst").write_text("Old\n===\n", encoding="utf-8")
        assert not _docs_match_runtime(str(wrong_docs), docs_runtime)
        with mock.patch.dict(
            os.environ,
            {"CODEX_HOME": str(root), "ULTRAPLOT_MCP_DOCS": ""},
            clear=False,
        ):
            assert _candidate_docs(docs_runtime) == str(versioned_docs.resolve())
            random_docs = root / "mcp-sources" / "random" / "docs"
            random_docs.mkdir(parents=True)
            (random_docs / "conf.py").write_text("# fake\n", encoding="utf-8")
            (random_docs / "index.rst").write_text("Fake\n====\n", encoding="utf-8")
            assert _candidate_docs({"ultraplot_version": "2.7.0"}) == str(
                versioned_docs.resolve()
            )
        tests.append("versioned_docs_candidate_provenance")
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

        no_newline = root / "no-newline.toml"
        no_newline.write_text(
            f"[mcp_servers.ultraplot]\ncommand = {_toml_string(sys.executable)}",
            encoding="utf-8",
        )
        _write_config(no_newline, fake_runtime, None)
        no_newline_config = tomllib.loads(no_newline.read_text(encoding="utf-8"))
        assert no_newline_config["mcp_servers"]["ultraplot"]["args"] == [
            "-m",
            "ultraplot.mcp",
        ]
        tests.append("append_to_unterminated_section")

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

        multiline = root / "multiline.toml"
        multiline_text = (
            'description = """\n'
            "[mcp_servers.ultraplot]\n"
            'command = "do-not-touch"\n'
            '"""\n'
            "[model]\nname = \"keep\"\n"
        )
        multiline.write_text(multiline_text, encoding="utf-8")
        try:
            _write_config(multiline, fake_runtime, None)
        except BootstrapError as exc:
            assert "multiline" in str(exc).lower()
        else:
            raise AssertionError("multiline TOML string was scanned as table syntax")
        assert multiline.read_text(encoding="utf-8") == multiline_text
        tests.append("reject_multiline_string_headers")

        complex_target = root / "complex-target.toml"
        complex_target_text = (
            "[mcp_servers.ultraplot]\n"
            'env = { KEEP = "yes" }\n'
            'command = "old"\n'
        )
        complex_target.write_text(complex_target_text, encoding="utf-8")
        try:
            _write_config(complex_target, fake_runtime, None)
        except BootstrapError:
            pass
        else:
            raise AssertionError("inline target value was silently patched")
        assert complex_target.read_text(encoding="utf-8") == complex_target_text
        tests.append("reject_complex_target_value")

        environment_target = root / "environment-target.toml"
        environment_target_text = (
            "[mcp_servers.ultraplot]\n"
            'command = "old"\n'
            'args = ["-m", "ultraplot.mcp"]\n'
            "\n[mcp_servers.ultraplot.env]\n"
            'PYTHONPATH = "C:/untrusted"\n'
        )
        environment_target.write_text(environment_target_text, encoding="utf-8")
        parsed_environment = tomllib.loads(environment_target_text)
        environment_info = _entry_info(parsed_environment, fake_runtime)
        assert environment_info["environment_status"] == "unverified"
        try:
            _write_config(environment_target, fake_runtime, None)
        except BootstrapError as exc:
            assert "startup environment" in str(exc)
        else:
            raise AssertionError("PYTHONPATH override was reported as aligned")
        assert environment_target.read_text(encoding="utf-8") == environment_target_text
        tests.append("mark_startup_environment_unverified")

        env_vars_list = root / "env-vars-list.toml"
        env_vars_list_text = (
            "[mcp_servers.ultraplot]\n"
            'command = "old"\n'
            'args = ["-m", "ultraplot.mcp"]\n'
            'env_vars = ["CODEX_WINDOWS_REGISTERED_CORE"]\n'
        )
        env_vars_list.write_text(env_vars_list_text, encoding="utf-8")
        parsed_env_vars_list = tomllib.loads(env_vars_list_text)
        env_vars_list_info = _entry_info(parsed_env_vars_list, fake_runtime)
        assert env_vars_list_info["environment_status"] == "unverified"
        assert _line_value_is_editable(
            "env_vars", '["CODEX_WINDOWS_REGISTERED_CORE"]'
        )
        try:
            _write_config(env_vars_list, fake_runtime, None)
        except BootstrapError as exc:
            assert "startup environment" in str(exc)
        else:
            raise AssertionError("unverified env_vars array was silently edited")
        _write_config(env_vars_list, fake_runtime, None, force=True)
        assert tomllib.loads(env_vars_list.read_text(encoding="utf-8"))[
            "mcp_servers"
        ]["ultraplot"]["env_vars"] == ["CODEX_WINDOWS_REGISTERED_CORE"]

        env_vars_table = root / "env-vars-table.toml"
        env_vars_table_text = (
            "[mcp_servers.ultraplot]\n"
            'command = "old"\n'
            'args = ["-m", "ultraplot.mcp"]\n'
            'env_vars = { CODEX_WINDOWS_REGISTERED_CORE = "1" }\n'
        )
        env_vars_table.write_text(env_vars_table_text, encoding="utf-8")
        parsed_env_vars_table = tomllib.loads(env_vars_table_text)
        env_vars_table_info = _entry_info(parsed_env_vars_table, fake_runtime)
        assert env_vars_table_info["environment_status"] == "unverified"
        assert _line_value_is_editable(
            "env_vars", '{ CODEX_WINDOWS_REGISTERED_CORE = "1" }'
        )
        _write_config(env_vars_table, fake_runtime, None, force=True)
        assert tomllib.loads(env_vars_table.read_text(encoding="utf-8"))[
            "mcp_servers"
        ]["ultraplot"]["env_vars"] == {"CODEX_WINDOWS_REGISTERED_CORE": "1"}
        tests.append("support_env_vars_array_and_table")

        optional_tools = root / "optional-tools.toml"
        optional_tools.write_text(
            "[mcp_servers.ultraplot]\n"
            'command = "old"\n'
            'args = ["-m", "ultraplot.mcp"]\n'
            'enabled_tools = ["ping"]\n'
            'disabled_tools = ["get_source"]\n',
            encoding="utf-8",
        )
        _write_config(optional_tools, fake_runtime, None, force=True)
        optional_config = tomllib.loads(optional_tools.read_text(encoding="utf-8"))
        assert optional_config["mcp_servers"]["ultraplot"]["enabled_tools"] == ["ping"]
        assert optional_config["mcp_servers"]["ultraplot"]["disabled_tools"] == [
            "get_source"
        ]
        tests.append("preserve_optional_tool_filters")

        timeout_runtime = {
            "python": sys.executable,
            "ultraplot_available": True,
            "mcp_dependency_available": True,
            "ultraplot_mcp_available": True,
            "mcp_version": "2.1.0",
            "mcp_version_compatible": True,
            "ultraplot_version": "2.7.0",
            "source_file": None,
            "ultraplot_editable": False,
        }
        original_runtime_info = _runtime_info
        globals()["_runtime_info"] = lambda executable=None: dict(timeout_runtime)
        try:
            for invalid_timeout in ('"bad"', "[]", "0", "-1", "true", "nan", "inf"):
                timeout_path = root / "invalid-timeout.toml"
                timeout_text = (
                    "[mcp_servers.ultraplot]\n"
                    f'command = {_toml_string(sys.executable)}\n'
                    'args = ["-m", "ultraplot.mcp"]\n'
                    "enabled = true\n"
                    f"startup_timeout_sec = {invalid_timeout}\n"
                    "tool_timeout_sec = 60\n"
                )
                timeout_path.write_text(timeout_text, encoding="utf-8")
                timeout_state = inspect_state(timeout_path, Path(sys.executable))
                assert timeout_state["status"] == "configuration_conflict"
                assert timeout_state["server"]["timeout_status"] == "conflict"
                try:
                    _write_config(timeout_path, timeout_runtime, None)
                except BootstrapError:
                    pass
                else:
                    raise AssertionError(
                        f"invalid timeout {invalid_timeout!r} was silently edited"
                    )
                assert timeout_path.read_text(encoding="utf-8") == timeout_text

            valid_timeout = root / "valid-timeout.toml"
            valid_timeout.write_text(
                "[mcp_servers.ultraplot]\n"
                f'command = {_toml_string(sys.executable)}\n'
                'args = ["-m", "ultraplot.mcp"]\n'
                "enabled = true\n"
                "startup_timeout_sec = 60.0\n"
                "tool_timeout_sec = 1\n",
                encoding="utf-8",
            )
            assert inspect_state(valid_timeout, Path(sys.executable))["status"] == (
                "configured_without_docs"
            )
        finally:
            globals()["_runtime_info"] = original_runtime_info
        tests.append("reject_invalid_timeout_values")

        for transport_key, transport_value in (
            ("url", '"https://example.invalid/mcp"'),
            ("bearer_token_env_var", '"TOKEN"'),
            ("http_headers", '{ X = "Y" }'),
            ("env_http_headers", '{ X = "Y" }'),
        ):
            transport_path = root / f"transport-{transport_key}.toml"
            transport_text = (
                "[mcp_servers.ultraplot]\n"
                f"{transport_key} = {transport_value}\n"
            )
            transport_path.write_text(transport_text, encoding="utf-8")
            parsed_transport = tomllib.loads(transport_text)
            transport_info = _entry_info(parsed_transport, fake_runtime)
            assert transport_key in transport_info["transport_conflicts"]
            try:
                _write_config(transport_path, fake_runtime, None)
            except BootstrapError:
                pass
            else:
                raise AssertionError(
                    f"stdio transport conflict {transport_key!r} was silently edited"
                )
            assert transport_path.read_text(encoding="utf-8") == transport_text
        tests.append("reject_stdio_transport_conflicts")

        try:
            _install_dependency({"python": sys.executable, "ultraplot_version": "unknown"})
        except BootstrapError:
            pass
        else:
            raise AssertionError("unknown version was allowed for installation")
        tests.append("pin_dependency_version")

        for unstable_version in ("2.7.0rc1", "2.7.0.dev1", "2.7.0+local", "3.0.0"):
            try:
                _install_dependency(
                    {"python": sys.executable, "ultraplot_version": unstable_version}
                )
            except BootstrapError:
                pass
            else:
                raise AssertionError(
                    f"non-stable version {unstable_version!r} was allowed for installation"
                )
        tests.append("reject_nonstable_or_future_versions")
        assert _dependency_requirement(
            {"python": sys.executable, "ultraplot_version": "2.7.0.post1"}
        ) == "ultraplot[mcp]==2.7.0.post1"
        tests.append("allow_stable_post_release")

        assert _package_policy("manual") == "manual"
        assert _package_policy("install-and-upgrade") == "install-and-upgrade"
        original_policy_env = os.environ.get(PACKAGE_POLICY_ENV)
        original_auto_install_env = os.environ.get(AUTO_INSTALL_ULTRAPLOT_ENV)
        original_auto_upgrade_env = os.environ.get(AUTO_UPGRADE_ULTRAPLOT_ENV)
        original_target_env = os.environ.get(ULTRAPLOT_VERSION_ENV)
        original_conda_allow_env = os.environ.get(ALLOW_PIP_IN_CONDA_ENV)
        try:
            os.environ.pop(PACKAGE_POLICY_ENV, None)
            os.environ[AUTO_INSTALL_ULTRAPLOT_ENV] = "1"
            os.environ[AUTO_UPGRADE_ULTRAPLOT_ENV] = "true"
            os.environ.pop(ULTRAPLOT_VERSION_ENV, None)
            os.environ[ALLOW_PIP_IN_CONDA_ENV] = "1"
            assert _allow_pip_in_conda() is True
            assert _package_policy() == "install-and-upgrade"
            os.environ[PACKAGE_POLICY_ENV] = "bad-policy"
            try:
                _package_policy()
            except BootstrapError:
                pass
            else:
                raise AssertionError("invalid package policy was accepted")
        finally:
            for name, value in (
                (PACKAGE_POLICY_ENV, original_policy_env),
                (AUTO_INSTALL_ULTRAPLOT_ENV, original_auto_install_env),
                (AUTO_UPGRADE_ULTRAPLOT_ENV, original_auto_upgrade_env),
                (ULTRAPLOT_VERSION_ENV, original_target_env),
                (ALLOW_PIP_IN_CONDA_ENV, original_conda_allow_env),
            ):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        assert _target_ultraplot_version("2.7.1") == "2.7.1"
        try:
            _target_ultraplot_version("3.0.0")
        except BootstrapError:
            pass
        else:
            raise AssertionError("unsupported target version was accepted")
        try:
            _target_ultraplot_version(required=True)
        except BootstrapError as exc:
            assert "exact target version" in str(exc)
        else:
            raise AssertionError("missing upgrade target was accepted")
        tests.append("package_policy_and_target_validation")

        with mock.patch.object(
            Path,
            "is_symlink",
            autospec=True,
            side_effect=lambda candidate: candidate.name == "symlink-config.toml",
        ):
            try:
                _preflight_config_write(root / "symlink-config.toml")
            except BootstrapError as exc:
                assert "symlinked config" in str(exc)
            else:
                raise AssertionError("symlinked config was allowed during preflight")
        assert _bootstrap_error_status(
            BootstrapError("Refusing to replace symlinked config: config.toml")
        ) == "configuration_conflict"
        tests.append("reject_symlinked_config_preflight")

        with mock.patch.object(
            Path,
            "is_symlink",
            autospec=True,
            side_effect=lambda candidate: candidate.name
            == ".symlink-lock.toml.ultraplot.lock",
        ):
            try:
                with _config_lock(root / "symlink-lock.toml"):
                    pass
            except BootstrapError as exc:
                assert "symlinked config lock" in str(exc)
            else:
                raise AssertionError("symlinked config lock was allowed")
        tests.append("reject_symlinked_config_lock")

        original_probe_subprocess_run = subprocess.run
        probe_call: dict[str, Any] = {}

        def fake_probe_subprocess_run(
            command: list[str], **kwargs: Any
        ) -> Any:
            probe_call.update(kwargs)
            probe_call["cwd_exists"] = Path(kwargs["cwd"]).is_dir()
            return type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "python": sys.executable,
                            "ultraplot_available": True,
                            "mcp_dependency_available": True,
                            "ultraplot_mcp_available": True,
                            "mcp_version": "2.1.0",
                            "mcp_version_compatible": True,
                            "ultraplot_version": "2.7.0",
                            "source_file": None,
                            "ultraplot_editable": False,
                        }
                    ),
                    "stderr": "",
                },
            )()

        original_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = "should-not-reach-probe"
        subprocess.run = fake_probe_subprocess_run  # type: ignore[assignment]
        try:
            _runtime_info(Path(sys.executable))
        finally:
            subprocess.run = original_probe_subprocess_run  # type: ignore[assignment]
            if original_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = original_pythonpath
        assert probe_call["cwd_exists"] is True
        assert probe_call["cwd"] != os.getcwd()
        assert "PYTHONPATH" not in probe_call["env"]
        assert probe_call["env"]["PYTHONNOUSERSITE"] == "1"
        assert "PYTHONUSERBASE" not in probe_call["env"]
        assert "PYTHONHOME" not in probe_call["env"]
        assert probe_call["encoding"] == "utf-8"
        assert probe_call["errors"] == "replace"
        tests.append("isolate_runtime_probe")

        original_subprocess_run = subprocess.run
        pip_calls: list[tuple[list[str], dict[str, Any]]] = []

        def fake_subprocess_run(command: list[str], **kwargs: Any) -> Any:
            kwargs["cwd_exists_during_call"] = Path(kwargs["cwd"]).is_dir()
            kwargs["cwd_is_task_dir"] = kwargs["cwd"] == os.getcwd()
            pip_calls.append((command, kwargs))
            return type("Completed", (), {"returncode": 0})()

        subprocess.run = fake_subprocess_run  # type: ignore[assignment]
        try:
            _install_dependency(
                {"python": sys.executable, "ultraplot_version": "2.7.0"}
            )
        finally:
            subprocess.run = original_subprocess_run  # type: ignore[assignment]
        assert pip_calls and pip_calls[0][0] == [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "ultraplot[mcp]==2.7.0",
        ]
        assert pip_calls[0][1]["timeout"] == 300
        assert pip_calls[0][1]["cwd_exists_during_call"] is True
        assert pip_calls[0][1]["cwd_is_task_dir"] is False
        tests.append("pin_dependency_command")

        pip_calls.clear()
        subprocess.run = fake_subprocess_run  # type: ignore[assignment]
        try:
            _install_ultraplot(sys.executable, "2.7.1", upgrade=True)
        finally:
            subprocess.run = original_subprocess_run  # type: ignore[assignment]
        assert pip_calls and pip_calls[0][0] == [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--upgrade",
            "ultraplot[mcp]==2.7.1",
        ]
        assert pip_calls[0][1]["encoding"] == "utf-8"
        assert pip_calls[0][1]["errors"] == "replace"
        assert pip_calls[0][1]["env"]["PYTHONNOUSERSITE"] == "1"
        tests.append("pin_base_upgrade_command")

        original_subprocess_run = subprocess.run

        def failing_subprocess_run(command: list[str], **kwargs: Any) -> Any:
            return type(
                "Completed",
                (),
                {
                    "returncode": 1,
                    "stderr": "token=super-secret " + ("x" * 2500),
                },
            )()

        subprocess.run = failing_subprocess_run  # type: ignore[assignment]
        try:
            try:
                _install_dependency(
                    {"python": sys.executable, "ultraplot_version": "2.7.0"}
                )
            except BootstrapError as exc:
                diagnostic = str(exc)
                assert "super-secret" not in diagnostic
                assert "[truncated]" in diagnostic
            else:
                raise AssertionError("pip failure did not propagate a diagnostic")
        finally:
            subprocess.run = original_subprocess_run  # type: ignore[assignment]
        tests.append("redact_and_truncate_pip_diagnostic")
        scrubbed = _redacted_diagnostic(
            "https://user:p@ss@example.invalid/x Authorization: Basic dG9rZW4= "
            "secret super-secret token super-token"
        )
        assert "p@ss" not in scrubbed
        assert "dG9rZW4=" not in scrubbed
        assert "super-secret" not in scrubbed
        assert "super-token" not in scrubbed
        tests.append("redact_url_and_auth_variants")

        # Exercise the automatic state machine without touching the user's
        # interpreter or Codex config.  The fake probe flips to ready only
        # after the mocked, version-pinned installer is called.
        original_probe = _runtime_info
        original_install = _install_dependency
        original_install_ultraplot = _install_ultraplot
        original_codex_home = os.environ.get("CODEX_HOME")
        ready = False
        fake_mcp_compatible = True
        fake_version = "2.7.0"
        fake_editable = False
        fake_provenance = "installed"
        install_calls: list[str] = []

        def fake_probe(executable: Path | None = None) -> dict[str, Any]:
            selected = str(executable or sys.executable)
            return {
                "python": selected,
                "ultraplot_available": True,
                "mcp_dependency_available": ready,
                "ultraplot_mcp_available": ready,
                "mcp_version": "2.1.0",
                "mcp_version_compatible": fake_mcp_compatible,
                "ultraplot_version": fake_version,
                "ultraplot_provenance": fake_provenance,
                "source_file": None,
                "ultraplot_editable": fake_editable,
                "package_manager": "pip",
            }

        def fake_install(runtime: dict[str, Any]) -> None:
            nonlocal ready, fake_mcp_compatible
            install_calls.append(_dependency_requirement(runtime))
            ready = True
            fake_mcp_compatible = True

        globals()["_runtime_info"] = fake_probe
        globals()["_install_dependency"] = fake_install
        os.environ["CODEX_HOME"] = str(root / "isolated-codex")
        try:
            auto_path = root / "auto.toml"
            first = bootstrap(auto_path, docs_path=None, executable=Path(sys.executable))
            assert first["status"] == "configured_without_docs"
            assert first["action"] == "dependencies_installed_and_configured"
            assert first["dependency_requirement"] == "ultraplot[mcp]==2.7.0"
            assert first["restart_required"] is True
            assert install_calls == ["ultraplot[mcp]==2.7.0"]
            first_bytes = auto_path.read_bytes()

            second = bootstrap(auto_path, docs_path=None, executable=Path(sys.executable))
            assert second["bootstrap_status"] == "ready_without_docs"
            assert second["action"] == "unchanged"
            assert install_calls == ["ultraplot[mcp]==2.7.0"]
            assert auto_path.read_bytes() == first_bytes
            tests.append("automatic_install_configure_and_idempotence")

            # Explicit configure mode must apply the same conda/mixed pip
            # safety gate as bootstrap mode.  The environment flag is tested
            # through the public function parameter below; the CLI forwards
            # that parameter in ``main``.
            configure_probe = globals()["_runtime_info"]
            configure_install = globals()["_install_dependency"]
            configure_calls: list[str] = []
            configure_ready = False

            def conda_configure_probe(executable: Path | None = None) -> dict[str, Any]:
                selected = str(executable or sys.executable)
                return {
                    "python": selected,
                    "ultraplot_available": True,
                    "mcp_dependency_available": configure_ready,
                    "ultraplot_mcp_available": configure_ready,
                    "mcp_version": "2.1.0" if configure_ready else None,
                    "mcp_version_compatible": configure_ready,
                    "ultraplot_version": "2.7.0",
                    "ultraplot_provenance": "installed",
                    "source_file": None,
                    "ultraplot_editable": False,
                    "package_manager": "conda",
                }

            def configure_install_dependency(runtime: dict[str, Any]) -> None:
                nonlocal configure_ready
                configure_calls.append(_dependency_requirement(runtime))
                configure_ready = True

            globals()["_runtime_info"] = conda_configure_probe
            globals()["_install_dependency"] = configure_install_dependency
            try:
                denied_configure = root / "configure-conda-denied.toml"
                try:
                    configure(
                        denied_configure,
                        confirm=True,
                        install_dependencies=True,
                        docs_path=None,
                        executable=Path(sys.executable),
                    )
                except BootstrapError as exc:
                    assert "--allow-pip-in-conda" in str(exc)
                else:
                    raise AssertionError("configure allowed unauthorized conda pip mutation")
                assert configure_calls == []

                def unknown_manager_probe(
                    executable: Path | None = None,
                ) -> dict[str, Any]:
                    observed = conda_configure_probe(executable)
                    observed["package_manager"] = "unknown"
                    return observed

                globals()["_runtime_info"] = unknown_manager_probe
                unknown_manager = bootstrap(
                    root / "unknown-manager.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                )
                assert unknown_manager["bootstrap_status"] == (
                    "package_manager_requires_manual"
                )
                assert configure_calls == []

                denied_unknown_configure = root / "configure-unknown-denied.toml"
                try:
                    configure(
                        denied_unknown_configure,
                        confirm=True,
                        install_dependencies=True,
                        docs_path=None,
                        executable=Path(sys.executable),
                    )
                except BootstrapError as exc:
                    assert "package manager could not be verified" in str(exc)
                else:
                    raise AssertionError(
                        "configure allowed an unknown package manager to install MCP"
                    )
                assert configure_calls == []
                globals()["_runtime_info"] = conda_configure_probe

                allowed_configure = root / "configure-conda-allowed.toml"
                configured = configure(
                    allowed_configure,
                    confirm=True,
                    install_dependencies=True,
                    docs_path=None,
                    executable=Path(sys.executable),
                    allow_pip_in_conda=True,
                )
                assert configured["status"] in {"configured", "configured_without_docs"}
                assert configure_calls == ["ultraplot[mcp]==2.7.0"]

                configure_ready = False
                aligned_configure = root / "configure-aligned.toml"
                aligned_configure.write_text(
                    "[mcp_servers.ultraplot]\n"
                    f"command = {_toml_string(str(Path(sys.executable)))}\n"
                    'args = ["-m", "ultraplot.mcp"]\n'
                    "enabled = true\n",
                    encoding="utf-8",
                )
                configure_calls.clear()
                aligned_result = configure(
                    aligned_configure,
                    confirm=True,
                    install_dependencies=True,
                    docs_path=None,
                    executable=Path(sys.executable),
                    allow_pip_in_conda=True,
                )
                assert aligned_result["action"] == "dependencies_installed"
                assert aligned_result["dependency_installed"] is True
                assert aligned_result["restart_required"] is True
                assert configure_calls == ["ultraplot[mcp]==2.7.0"]
            finally:
                globals()["_runtime_info"] = configure_probe
                globals()["_install_dependency"] = configure_install
                configure_ready = False
            tests.append("configure_conda_pip_authorization")

            # Base-package installation and upgrades are separately opt-in and
            # use the same exact target plus MCP extra.  The fake probe keeps
            # all package and config mutations inside this temporary directory.
            active_probe = globals()["_runtime_info"]
            base_available = False
            base_version = "2.7.0"
            base_calls: list[tuple[str, str, bool]] = []

            def base_probe(executable: Path | None = None) -> dict[str, Any]:
                selected = str(executable or sys.executable)
                return {
                    "python": selected,
                    "ultraplot_available": base_available,
                    "mcp_dependency_available": base_available,
                    "ultraplot_mcp_available": base_available,
                    "mcp_version": "2.1.0" if base_available else None,
                    "mcp_version_compatible": base_available,
                    "ultraplot_version": base_version if base_available else None,
                    "ultraplot_provenance": "installed" if base_available else "unknown",
                    "source_file": None,
                    "ultraplot_editable": False,
                    "package_manager": "pip",
                }

            def fake_base_install(
                executable: str, target_version: str, *, upgrade: bool = False
            ) -> str:
                nonlocal base_available, base_version
                base_calls.append((executable, target_version, upgrade))
                base_available = True
                base_version = target_version
                return f"ultraplot[mcp]=={target_version}"

            globals()["_runtime_info"] = base_probe
            globals()["_install_ultraplot"] = fake_base_install
            try:
                default_base = bootstrap(
                    root / "base-default.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                )
                assert default_base["bootstrap_status"] == "base_install_required"
                assert base_calls == []

                installed_base = bootstrap(
                    root / "base-installed.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="install",
                    ultraplot_version="2.7.0",
                )
                assert installed_base["base_installed"] is True
                assert installed_base["package_action"] == "install_base"
                assert installed_base["package_requirement"] == "ultraplot[mcp]==2.7.0"
                assert installed_base["restart_required"] is True
                assert base_calls[-1] == (sys.executable, "2.7.0", False)

                upgraded_base = bootstrap(
                    root / "base-installed.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="upgrade",
                    ultraplot_version="2.7.1",
                )
                assert upgraded_base["upgraded"] is True
                assert upgraded_base["package_action"] == "upgrade_base"
                assert upgraded_base["previous_version"] == "2.7.0"
                assert upgraded_base["target_version"] == "2.7.1"
                assert upgraded_base["mutation_attempted"] is True
                assert base_calls[-1] == (sys.executable, "2.7.1", True)

                no_downgrade = bootstrap(
                    root / "base-installed.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="upgrade",
                    ultraplot_version="2.7.0",
                )
                assert no_downgrade["bootstrap_status"] == "upgrade_not_needed"
                assert base_calls[-1] == (sys.executable, "2.7.1", True)
                tests.append("opt_in_base_install_and_upgrade")

                base_available = False
                conda_probe = dict(base_probe(Path(sys.executable)))
                conda_probe["package_manager"] = "conda"
                globals()["_runtime_info"] = lambda executable=None: dict(conda_probe)
                conda_result = bootstrap(
                    root / "conda-base.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="install",
                )
                assert conda_result["bootstrap_status"] == "package_manager_requires_manual"
                assert base_calls[-1] == (sys.executable, "2.7.1", True)

                unknown_base_probe = dict(conda_probe)
                unknown_base_probe["package_manager"] = "unknown"
                globals()["_runtime_info"] = lambda executable=None: dict(
                    unknown_base_probe
                )
                unknown_base = bootstrap(
                    root / "unknown-base.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="install",
                )
                assert unknown_base["bootstrap_status"] == (
                    "package_manager_requires_manual"
                )
                assert base_calls[-1] == (sys.executable, "2.7.1", True)

                def conda_base_probe(executable: Path | None = None) -> dict[str, Any]:
                    observed = base_probe(executable)
                    observed["package_manager"] = "conda"
                    return observed

                base_available = False
                globals()["_runtime_info"] = conda_base_probe
                allowed_conda = bootstrap(
                    root / "conda-allowed.toml",
                    docs_path=None,
                    executable=Path(sys.executable),
                    package_policy="install",
                    allow_pip_in_conda=True,
                )
                assert allowed_conda["base_installed"] is True
                assert base_calls[-1] == (sys.executable, "2.7.0", False)
                tests.append("reject_and_explicitly_allow_conda_base_mutation")
            finally:
                globals()["_runtime_info"] = active_probe
                globals()["_install_ultraplot"] = original_install_ultraplot
                fake_version = "2.7.0"
                ready = True

            fake_provenance = "nonstandard"
            provenance_path = root / "provenance-unknown.toml"
            provenance_result = bootstrap(
                provenance_path, docs_path=None, executable=Path(sys.executable)
            )
            assert provenance_result["bootstrap_status"] == (
                "ultraplot_provenance_unverified"
            )
            assert provenance_result["action"] == "fallback"
            assert install_calls == ["ultraplot[mcp]==2.7.0"]
            assert not provenance_path.exists()
            fake_provenance = "installed"
            tests.append("reject_unverified_ultraplot_provenance")

            verify_path = root / "verification-failure.toml"
            original_inspect_state = inspect_state
            verification_calls = 0

            def stale_inspect(
                inspect_path: Path,
                inspect_executable: Path | None = None,
            ) -> dict[str, Any]:
                nonlocal verification_calls
                observed = original_inspect_state(inspect_path, inspect_executable)
                if inspect_path == verify_path and verification_calls >= 1:
                    observed["status"] = "needs_configuration"
                    observed["server"]["aligned"] = False
                verification_calls += 1
                return observed

            globals()["inspect_state"] = stale_inspect
            try:
                verification_result = bootstrap(
                    verify_path,
                    docs_path=None,
                    executable=Path(sys.executable),
                )
            finally:
                globals()["inspect_state"] = original_inspect_state
            assert verification_result["bootstrap_status"] == (
                "configuration_verification_failed"
            )
            assert verification_result["config_changed"] is True
            assert verification_result["partial"] is True
            tests.append("verify_state_after_config_write")

            ready = False
            install_calls.clear()
            conflict_auto = root / "conflict-auto.toml"
            conflict_auto.write_text(
                '[mcp_servers.ultraplot]\ncommand = "uvx"\nargs = ["ultraplot-mcp"]\n',
                encoding="utf-8",
            )
            conflict_bytes = conflict_auto.read_bytes()
            conflict_result = bootstrap(
                conflict_auto, docs_path=None, executable=Path(sys.executable)
            )
            assert conflict_result["bootstrap_status"] == "configuration_conflict"
            assert install_calls == []
            assert conflict_auto.read_bytes() == conflict_bytes
            tests.append("conflict_preflight_before_install")

            extra_args = root / "extra-args.toml"
            extra_args.write_text(
                "[mcp_servers.ultraplot]\n"
                f"command = {_toml_string(sys.executable)}\n"
                'args = ["-m", "ultraplot.mcp", "--bad"]\n',
                encoding="utf-8",
            )
            extra_args_bytes = extra_args.read_bytes()
            extra_args_result = bootstrap(
                extra_args, docs_path=None, executable=Path(sys.executable)
            )
            assert extra_args_result["bootstrap_status"] == "configuration_conflict"
            assert install_calls == []
            assert extra_args.read_bytes() == extra_args_bytes
            tests.append("reject_extra_mcp_arguments")

            def failing_install(runtime: dict[str, Any]) -> None:
                install_calls.append(_dependency_requirement(runtime))
                raise BootstrapError("Could not install the MCP extra (test failure).")

            globals()["_install_dependency"] = failing_install
            failed_auto = root / "failed-auto.toml"
            failed_result = bootstrap(
                failed_auto, docs_path=None, executable=Path(sys.executable)
            )
            assert failed_result["bootstrap_status"] == "install_failed"
            assert failed_result["dependency_installed"] is False
            assert failed_result["dependency_install_attempted"] is True
            assert failed_result["partial"] is True
            assert not failed_auto.exists()
            tests.append("install_failure_fails_open")

            globals()["_install_dependency"] = fake_install
            ready = True
            fake_mcp_compatible = False
            incompatible_result = bootstrap(
                root / "incompatible-mcp.toml",
                docs_path=None,
                executable=Path(sys.executable),
            )
            assert incompatible_result["action"] == "dependencies_installed_and_configured"
            assert incompatible_result["dependency_install_attempted"] is True
            assert install_calls[-1] == "ultraplot[mcp]==2.7.0"
            tests.append("repair_incompatible_mcp_version")

            fake_version = "2.6.0"
            old_result = bootstrap(
                root / "old-version.toml",
                docs_path=None,
                executable=Path(sys.executable),
            )
            assert old_result["bootstrap_status"] == "unsupported_ultraplot_version"
            assert install_calls[-1] == "ultraplot[mcp]==2.7.0"
            tests.append("reject_unsupported_ultraplot_version")

            # An older installation may already expose both importable MCP
            # modules.  It still must not receive an automatic config entry,
            # because the official UltraPlot MCP contract starts at 2.7.0.
            ready = True
            install_calls.clear()
            fake_version = "2.6.0"
            old_ready_path = root / "old-ready.toml"
            old_ready_result = bootstrap(
                old_ready_path,
                docs_path=None,
                executable=Path(sys.executable),
            )
            assert old_ready_result["bootstrap_status"] == "unsupported_ultraplot_version"
            assert old_ready_result["action"] == "fallback"
            assert install_calls == []
            assert not old_ready_path.exists()

            # The same guard applies when the old server is already aligned
            # but a first-use docs update would otherwise mutate its table.
            old_docs_path = root / "old-docs"
            old_docs_path.mkdir()
            (old_docs_path / "conf.py").write_text("# test\n", encoding="utf-8")
            old_configured_path = root / "old-configured.toml"
            old_configured_path.write_text(
                "[mcp_servers.ultraplot]\n"
                f"command = {_toml_string(sys.executable)}\n"
                'args = ["-m", "ultraplot.mcp"]\n'
                "enabled = true\n",
                encoding="utf-8",
            )
            old_configured_bytes = old_configured_path.read_bytes()
            old_configured_result = bootstrap(
                old_configured_path,
                docs_path=str(old_docs_path),
                executable=Path(sys.executable),
            )
            assert old_configured_result["bootstrap_status"] == "unsupported_ultraplot_version"
            assert old_configured_path.read_bytes() == old_configured_bytes
            tests.append("reject_old_mcp_configuration_write")

            # ``--bootstrap --force`` must not turn first-use setup into an
            # implicit replacement of a user-managed server entry.
            fake_version = "2.7.0"
            ready = False
            force_path = root / "force-auto.toml"
            force_path.write_text(
                '[mcp_servers.ultraplot]\ncommand = "uvx"\n'
                'args = ["ultraplot-mcp"]\n',
                encoding="utf-8",
            )
            force_bytes = force_path.read_bytes()
            force_result = bootstrap(
                force_path,
                docs_path=None,
                executable=Path(sys.executable),
                force=True,
            )
            assert force_result["bootstrap_status"] == "configuration_conflict"
            assert force_result["action"] == "fallback"
            assert install_calls == []
            assert force_path.read_bytes() == force_bytes
            tests.append("automatic_bootstrap_never_forces_conflicts")

            fake_version = "2.7.0"
            fake_editable = True
            editable_result = bootstrap(
                root / "editable.toml",
                docs_path=None,
                executable=Path(sys.executable),
            )
            assert editable_result["bootstrap_status"] == "editable_ultraplot"
            assert editable_result["dependency_install_attempted"] is False
            tests.append("skip_editable_installation")
            fake_editable = False

            os.environ[AUTO_SETUP_ENV] = "0"
            opted_out = bootstrap(auto_path, docs_path=None, executable=Path(sys.executable))
            assert opted_out["bootstrap_status"] == "opted_out"
            assert opted_out["mutation_attempted"] is False
            tests.append("automatic_setup_opt_out")
            os.environ.pop(AUTO_SETUP_ENV, None)
        finally:
            globals()["_runtime_info"] = original_probe
            globals()["_install_dependency"] = original_install
            if original_codex_home is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = original_codex_home
            os.environ.pop(AUTO_SETUP_ENV, None)
    return {"ok": True, "tests": tests}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Read-only readiness check (default).")
    modes.add_argument("--configure", action="store_true", help="Write the UltraPlot MCP entry.")
    modes.add_argument(
        "--bootstrap",
        action="store_true",
        help="Automatically install the matching extra and configure MCP when safe.",
    )
    modes.add_argument("--self-test", action="store_true", help="Run offline updater tests.")
    parser.add_argument("--config", help="Override the Codex config.toml path.")
    parser.add_argument("--python", dest="python_executable", help="Selected plotting Python executable.")
    parser.add_argument("--docs", help="Existing matching UltraPlot docs directory.")
    package_modes = parser.add_mutually_exclusive_group()
    package_modes.add_argument(
        "--package-policy",
        choices=sorted(PACKAGE_POLICIES),
        help=(
            "For --bootstrap, opt in to base-package mutation: manual (default), "
            "install, upgrade, or install-and-upgrade."
        ),
    )
    package_modes.add_argument(
        "--install-ultraplot",
        action="store_true",
        help="For --bootstrap, authorize installation of a missing UltraPlot base package.",
    )
    package_modes.add_argument(
        "--upgrade-ultraplot",
        action="store_true",
        help="For --bootstrap, authorize an exact-target UltraPlot upgrade.",
    )
    parser.add_argument(
        "--ultraplot-version",
        help=(
            "For --bootstrap, exact stable UltraPlot 2.7.x target for base "
            "installation/upgrade (upgrade requires an explicit target)."
        ),
    )
    parser.add_argument(
        "--allow-pip-in-conda",
        action="store_true",
        help=(
            "Explicitly authorize pip base/MCP package changes in a conda or mixed "
            "environment for --bootstrap or --configure; use only after reviewing it."
        ),
    )
    parser.add_argument(
        "--install-dependencies",
        action="store_true",
        help="Allow the explicit --configure mode to install the matching extra; implied by --bootstrap.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "For explicit --configure repair only, replace a reviewed conflicting "
            "MCP command; automatic --bootstrap never forces conflicts."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm --configure; --bootstrap is already non-interactive.",
    )
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
    selected_package_policy = args.package_policy
    if args.install_ultraplot:
        selected_package_policy = "install"
    elif args.upgrade_ultraplot:
        selected_package_policy = "upgrade"
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
                allow_pip_in_conda=args.allow_pip_in_conda,
            )
            if args.configure
            else bootstrap(
                path,
                docs_path=args.docs,
                executable=executable,
                force=args.force,
                package_policy=selected_package_policy,
                ultraplot_version=args.ultraplot_version,
                allow_pip_in_conda=args.allow_pip_in_conda,
            )
            if args.bootstrap
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
    if args.bootstrap:
        # Bootstrap is deliberately fail-open.  Expected setup failures are
        # represented in JSON and the figure task can continue with fallback.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
