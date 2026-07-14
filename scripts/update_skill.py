#!/usr/bin/env python
"""Check for stable ultraplot-figures releases without installing them."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.error
import urllib.request


REPOSITORY = "lwq-star/ultraplot-figures"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
SKILL_NAME = "ultraplot-figures"
SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = "VERSION"
STATE_SCHEMA_VERSION = 2
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_HTTP_RETRIES = 4
CHECK_ENV_VAR = "ULTRAPLOT_FIGURES_UPDATE_CHECK"
DISABLED_VALUES = {"0", "false", "no", "off"}
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class UpdateCheckError(RuntimeError):
    """Raised when release metadata cannot be checked safely."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise UpdateCheckError(
            f"Invalid version {value!r}; expected MAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH."
        )
    return tuple(int(part) for part in match.groups())


def _normalized_version(value: str) -> str:
    return ".".join(str(part) for part in _version_tuple(value))


def _read_local_version(root: Path = SKILL_ROOT) -> str:
    path = root / VERSION_FILE
    try:
        return _normalized_version(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise UpdateCheckError(f"Could not read {path}: {exc}") from exc


def _cache_root() -> Path:
    if os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "Codex" / "Cache"
    elif os.environ.get("XDG_CACHE_HOME"):
        root = Path(os.environ["XDG_CACHE_HOME"]) / "codex"
    else:
        root = Path.home() / ".cache" / "codex"
    return root / SKILL_NAME


def _state_path() -> Path:
    return _cache_root() / "release-check-state.json"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise UpdateCheckError(
            f"Could not remove incomplete state file {temporary}: {exc}"
        ) from exc
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _retry_delay(exc: urllib.error.HTTPError, attempt: int) -> float | None:
    if exc.code == 429:
        raw = exc.headers.get("Retry-After")
        if raw:
            try:
                return max(0.0, float(raw))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(raw)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(
                        0.0,
                        (retry_at - datetime.now(timezone.utc)).total_seconds(),
                    )
                except (TypeError, ValueError, OverflowError):
                    pass
        return 60.0
    if 500 <= exc.code < 600:
        return float(2**attempt)
    return None


def _request_bytes(url: str, *, accept: str, max_bytes: int) -> bytes:
    headers = {
        "Accept": accept,
        "User-Agent": f"{SKILL_NAME}-release-checker",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    last_error: Exception | None = None
    for attempt in range(MAX_HTTP_RETRIES + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise UpdateCheckError(
                            f"Invalid Content-Length header: {content_length!r}."
                        ) from exc
                    if declared_size > max_bytes:
                        raise UpdateCheckError(
                            f"Response is too large: {declared_size} bytes exceeds {max_bytes}."
                        )
                payload = response.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    raise UpdateCheckError(f"Response exceeds {max_bytes} bytes.")
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            delay = _retry_delay(exc, attempt)
            if delay is None or attempt >= MAX_HTTP_RETRIES:
                raise
            time.sleep(delay)
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            if attempt >= MAX_HTTP_RETRIES:
                raise
            time.sleep(float(2**attempt))
    raise UpdateCheckError(f"Request failed: {last_error}")


def _latest_release() -> dict[str, Any] | None:
    try:
        payload = _request_bytes(
            LATEST_RELEASE_API,
            accept="application/vnd.github+json",
            max_bytes=MAX_METADATA_BYTES,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise UpdateCheckError(
            f"GitHub release check failed with HTTP {exc.code}."
        ) from exc
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise UpdateCheckError(f"GitHub release check failed: {reason}") from exc

    try:
        release = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateCheckError("GitHub returned invalid release metadata.") from exc
    if not isinstance(release, dict):
        raise UpdateCheckError("GitHub returned invalid release metadata.")
    if release.get("draft") or release.get("prerelease"):
        raise UpdateCheckError(
            "GitHub latest release unexpectedly points to a draft or prerelease."
        )
    for key in ("tag_name", "html_url"):
        if not isinstance(release.get(key), str) or not release[key]:
            raise UpdateCheckError(f"GitHub release metadata is missing {key}.")
    release["version"] = _normalized_version(release["tag_name"])
    return release


def _local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def _write_state(status: str, current: str, latest: str | None) -> None:
    _write_json_atomic(
        _state_path(),
        {
            "schema": STATE_SCHEMA_VERSION,
            "last_checked_date": _local_date(),
            "last_checked_epoch": time.time(),
            "status": status,
            "current_version": current,
            "latest_version": latest,
        },
    )


def _record_state(status: str, current: str, latest: str | None) -> None:
    try:
        _write_state(status, current, latest)
    except (OSError, UpdateCheckError):
        pass


def _state_checked_today() -> dict[str, Any] | None:
    state = _read_json(_state_path(), {})
    if not isinstance(state, dict):
        return None
    if state.get("schema") != STATE_SCHEMA_VERSION:
        return None
    if state.get("last_checked_date") != _local_date():
        return None
    return state


def _automatic_check_enabled() -> bool:
    value = os.environ.get(CHECK_ENV_VAR, "1")
    return value.strip().lower() not in DISABLED_VALUES


def _update_notification(
    current: str,
    latest: str,
    release_url: str,
) -> dict[str, str]:
    return {
        "message": (
            f"A new stable `{SKILL_NAME}` release is available: {latest} "
            f"(installed: {current}). Updating is recommended."
        ),
        "message_zh": (
            f"`{SKILL_NAME}` 已发布新的稳定版本 {latest}（当前安装版本：{current}），"
            "建议更新。"
        ),
        "update_request": (
            "Please update my installed `ultraplot-figures` skill to the latest "
            f"stable release: {release_url}"
        ),
        "update_request_zh": (
            "请将我已安装的 `ultraplot-figures` skill 更新到最新稳定版本："
            f"{release_url}"
        ),
    }


def _result(status: str, current: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": status,
        "repository": REPOSITORY,
        "current_version": current,
        **extra,
    }


def _run_check(*, automatic: bool) -> tuple[dict[str, Any], int]:
    current = _read_local_version()
    if automatic:
        if not _automatic_check_enabled():
            return _result("disabled", current), 0
        state = _state_checked_today()
        if state is not None:
            return _result(
                "skipped_checked_today",
                current,
                previous_status=state.get("status"),
                latest_version=state.get("latest_version"),
            ), 0

    try:
        release = _latest_release()
    except UpdateCheckError as exc:
        _record_state("check_failed", current, None)
        result = _result("check_failed", current, error=str(exc))
        return result, 0 if automatic else 1

    if release is None:
        _record_state("no_release", current, None)
        return _result("no_release", current), 0

    latest = release["version"]
    release_url = release["html_url"]
    if _version_tuple(latest) <= _version_tuple(current):
        _record_state("up_to_date", current, latest)
        return _result(
            "up_to_date",
            current,
            latest_version=latest,
            release_url=release_url,
        ), 0

    _record_state("update_available", current, latest)
    return _result(
        "update_available",
        current,
        latest_version=latest,
        release_url=release_url,
        **_update_notification(current, latest, release_url),
    ), 0


def _self_test() -> dict[str, Any]:
    from datetime import timedelta
    from email.utils import format_datetime
    import tempfile
    from unittest import mock

    tests: list[str] = []
    assert _version_tuple("v1.2.3") == (1, 2, 3)
    assert _normalized_version("1.2.3") == "1.2.3"
    tests.append("version_parsing")

    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    retry_error = urllib.error.HTTPError(
        LATEST_RELEASE_API,
        429,
        "rate limited",
        {"Retry-After": format_datetime(retry_at, usegmt=True)},
        None,
    )
    retry_delay = _retry_delay(retry_error, 0)
    assert retry_delay is not None and 0 <= retry_delay <= 30
    tests.append("retry_after_http_date")

    with tempfile.TemporaryDirectory(prefix=f"{SKILL_NAME}-self-test-") as directory:
        state_path = Path(directory) / "state.json"
        with mock.patch(f"{__name__}._state_path", return_value=state_path):
            assert _state_checked_today() is None
            _write_state("up_to_date", "0.1.0", "0.1.0")
            assert _state_checked_today() is not None
            tests.append("calendar_day_cache")

            with (
                mock.patch(f"{__name__}._read_local_version", return_value="0.1.0"),
                mock.patch(
                    f"{__name__}._latest_release",
                    side_effect=AssertionError("daily cache did not skip the network"),
                ),
                mock.patch.dict(os.environ, {CHECK_ENV_VAR: "1"}, clear=False),
            ):
                cached_result, cached_code = _run_check(automatic=True)
            assert cached_code == 0
            assert cached_result["status"] == "skipped_checked_today"
            tests.append("same_day_network_skip")

    fake_release = {
        "version": "0.2.0",
        "html_url": f"https://github.com/{REPOSITORY}/releases/tag/v0.2.0",
    }
    with (
        mock.patch(f"{__name__}._read_local_version", return_value="0.1.0"),
        mock.patch(f"{__name__}._latest_release", return_value=fake_release),
        mock.patch(f"{__name__}._record_state"),
    ):
        available_result, available_code = _run_check(automatic=False)
    assert available_code == 0
    assert available_result["status"] == "update_available"
    assert "Updating is recommended" in available_result["message"]
    assert "建议更新" in available_result["message_zh"]
    assert "update_request" in available_result
    assert "Git worktree" not in available_result["update_request"]
    assert "Git 工作区" not in available_result["update_request_zh"]
    assert "installed_files" not in available_result
    tests.append("notification_only")

    with (
        mock.patch(f"{__name__}._read_local_version", return_value="0.1.0"),
        mock.patch(f"{__name__}._state_checked_today", return_value=None),
        mock.patch(
            f"{__name__}._latest_release",
            side_effect=UpdateCheckError("offline"),
        ),
        mock.patch(f"{__name__}._record_state") as record_failed,
        mock.patch.dict(os.environ, {CHECK_ENV_VAR: "1"}, clear=False),
    ):
        failed_result, failed_code = _run_check(automatic=True)
    assert failed_code == 0
    assert failed_result["status"] == "check_failed"
    record_failed.assert_called_once_with("check_failed", "0.1.0", None)
    tests.append("failed_check_cached_for_day")

    with (
        mock.patch(f"{__name__}._read_local_version", return_value="0.1.0"),
        mock.patch.dict(os.environ, {CHECK_ENV_VAR: "0"}, clear=False),
    ):
        disabled_result, disabled_code = _run_check(automatic=True)
    assert disabled_code == 0
    assert disabled_result["status"] == "disabled"
    tests.append("automatic_check_opt_out")

    return {"ok": True, "tests": tests}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check the latest stable ultraplot-figures release without installing it."
        )
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--check",
        action="store_true",
        help="Check now even if a check already ran today.",
    )
    actions.add_argument(
        "--auto",
        action="store_true",
        help="Check at most once per local calendar day.",
    )
    actions.add_argument("--self-test", action="store_true", help="Run offline tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if args.self_test:
        print(json.dumps(_self_test(), ensure_ascii=False, indent=2))
        return 0
    result, exit_code = _run_check(automatic=args.auto)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
