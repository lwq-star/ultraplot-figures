#!/usr/bin/env python
"""Report UltraPlot capabilities used by the publication-figure workflow.

Do not use a method-existence check as a compatibility test. UltraPlot releases can
expose the same helper name with different keyword support and scaling behavior. This
module combines a version report with small runtime smoke checks.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


CACHE_SCHEMA_VERSION = 1


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _default_cache_path() -> Path:
    if os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "Codex" / "Cache"
    elif os.environ.get("XDG_CACHE_HOME"):
        root = Path(os.environ["XDG_CACHE_HOME"]) / "codex"
    else:
        root = Path.home() / ".cache" / "codex"
    return root / "ultraplot-figures" / "capabilities.json"


def _cache_identity() -> dict[str, Any]:
    helper_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    identity = {
        "schema": CACHE_SCHEMA_VERSION,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "ultraplot": _distribution_version("ultraplot"),
        "matplotlib": _distribution_version("matplotlib"),
        "helper_sha256": helper_hash,
    }
    serialized = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    identity["key"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return identity


def _load_cached_report(path: Path, identity: dict[str, Any]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if payload.get("identity", {}).get("key") != identity["key"]:
        return None
    report = payload.get("report")
    if not isinstance(report, dict) or not report.get("ok"):
        return None
    report = dict(report)
    report["cache"] = {"hit": True, "path": str(path), "key": identity["key"]}
    return report


def _write_cached_report(
    path: Path,
    identity: dict[str, Any],
    report: dict[str, Any],
) -> str | None:
    payload = {"identity": identity, "report": {**report, "cache": None}}
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return str(exc)
    return None


def _prepare_headless_environment() -> None:
    """Set safe headless defaults before importing UltraPlot."""
    gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
    if "GDAL_DATA" not in os.environ and gdal_data.exists():
        os.environ["GDAL_DATA"] = str(gdal_data)

    import matplotlib

    matplotlib.use("Agg", force=True)


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in version.replace("-", ".").split("."):
        digits = "".join(char for char in token if char.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def inspect_capabilities(
    *,
    use_cache: bool = True,
    refresh_cache: bool = False,
    cache_path: Path | None = None,
) -> dict[str, Any]:
    """Run or reuse checks for the APIs this skill relies on.

    Only successful environment-level reports are cached. Per-figure render,
    semantic, and artifact QA must still run for every delivered figure.
    """
    identity = _cache_identity()
    resolved_cache = cache_path or _default_cache_path()
    if use_cache and not refresh_cache:
        cached = _load_cached_report(resolved_cache, identity)
        if cached is not None:
            return cached

    _prepare_headless_environment()

    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
    import ultraplot as uplt
    from matplotlib.legend import Legend

    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "matplotlib": matplotlib.__version__,
        "ultraplot": uplt.__version__,
        "checks": {},
        "warnings": [],
        "errors": [],
    }

    version_ok = _version_tuple(uplt.__version__) >= (2, 4)
    report["checks"]["ultraplot_2_4_or_newer"] = version_ok
    if not version_ok:
        report["warnings"].append(
            "UltraPlot 2.4.x is the primary path; older releases require a verified fallback."
        )

    values = np.array([5.0, 6.0, 7.0])
    expected_areas = np.array([8.0, 44.0, 80.0])

    fig = None
    try:
        fig, axs = uplt.subplots(refwidth=1.8)
        ax = axs[0]
        scatter = ax.scatter(
            np.arange(values.size),
            np.arange(values.size),
            s=values,
            smin=8,
            smax=80,
        )
        scatter_areas = np.asarray(scatter.get_sizes(), dtype=float)
        scatter_ok = np.allclose(scatter_areas, expected_areas, rtol=1e-9, atol=1e-9)
        report["checks"]["scatter_semantic_size_mapping"] = bool(scatter_ok)
        report["scatter_areas_pt2"] = scatter_areas.tolist()

        handles, labels = ax.sizelegend(
            values,
            values=values,
            smin=8,
            smax=80,
            add=False,
        )
        legend_areas = np.asarray(
            [float(handle.get_markersize()) ** 2 for handle in handles], dtype=float
        )
        legend_ok = np.allclose(legend_areas, expected_areas, rtol=1e-9, atol=1e-9)
        report["checks"]["sizelegend_scatter_mapping"] = bool(legend_ok)
        report["sizelegend_areas_pt2"] = legend_areas.tolist()
        report["sizelegend_labels"] = [str(label) for label in labels]

        ax.plot([0, 1], [0, 1], label="unit spec")
        ax.legend(
            loc="r",
            frame=False,
            handletextpad="6pt",
            labelspacing="4pt",
            columnspacing="8pt",
        )
        fig.canvas.draw()
        legends = fig.findobj(match=Legend)
        unit_ok = bool(legends)
        report["checks"]["legend_physical_unit_specs"] = unit_ok
        report["checks"]["legend_discovery_via_findobj"] = bool(legends)
    except Exception as exc:  # noqa: BLE001 - capability report must remain printable.
        report["errors"].append(f"UltraPlot capability smoke test failed: {exc}")
        report["checks"].setdefault("scatter_semantic_size_mapping", False)
        report["checks"].setdefault("sizelegend_scatter_mapping", False)
        report["checks"].setdefault("legend_physical_unit_specs", False)
        report["checks"].setdefault("legend_discovery_via_findobj", False)
    finally:
        if fig is not None:
            plt.close(fig)

    journal_fig = None
    try:
        journal_fig, journal_axes = uplt.subplots(journal="nat2")
        journal_axes[0].plot([0, 1], [0, 1], label="series")
        journal_axes[0].legend(loc="r")
        before = np.asarray(journal_fig.get_size_inches(), dtype=float)
        journal_fig.canvas.draw()
        after = np.asarray(journal_fig.get_size_inches(), dtype=float)
        report["nat2_size_before_draw_in"] = before.tolist()
        report["nat2_size_after_draw_in"] = after.tolist()
        report["nat2_size_after_draw_mm"] = (after * 25.4).tolist()
        report["checks"]["journal_size_available_after_draw"] = bool(
            np.all(np.isfinite(after)) and np.all(after > 0)
        )
        report["journal_size_changed_on_draw"] = bool(
            not np.allclose(before, after, rtol=0, atol=1e-9)
        )
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"Journal-size smoke test failed: {exc}")
        report["checks"]["journal_size_available_after_draw"] = False
    finally:
        if journal_fig is not None:
            plt.close(journal_fig)

    required = (
        "scatter_semantic_size_mapping",
        "sizelegend_scatter_mapping",
        "legend_physical_unit_specs",
        "legend_discovery_via_findobj",
        "journal_size_available_after_draw",
    )
    report["required_checks"] = list(required)
    report["ok"] = not report["errors"] and all(
        bool(report["checks"].get(name)) for name in required
    )
    report["cache"] = {
        "hit": False,
        "path": str(resolved_cache) if use_cache else None,
        "key": identity["key"],
    }
    if use_cache and report["ok"]:
        write_error = _write_cached_report(resolved_cache, identity, report)
        if write_error:
            report["cache"]["write_error"] = write_error
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero unless all publication-workflow capability checks pass",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Rerun checks and replace any matching cached success",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Run checks without reading or writing the capability cache",
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        help="Override the default user cache path (mainly for isolated validation)",
    )
    args = parser.parse_args()

    report = inspect_capabilities(
        use_cache=not args.no_cache,
        refresh_cache=args.refresh_cache,
        cache_path=args.cache_path,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
        print(f"wrote {args.json}")
    print(text)

    if args.strict and not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
