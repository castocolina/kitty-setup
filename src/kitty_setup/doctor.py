"""Diagnostic that reports the install footprint and config-include health.

Implements the ``doctor`` requirement from the kitty-install capability. Prints
one line per check in ``PASS|FAIL <check>: <detail>`` form and exits non-zero
on any FAIL.
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kitty_setup import binding_introspection, config_updater, installer, path_integration


@dataclasses.dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"{status} {self.name}: {self.detail}"


def _check_kitty_binary() -> tuple[CheckResult, Path | None]:
    candidates: list[Path] = [installer.SYMLINK_PATH, installer._kitty_bin(installer.DEFAULT_DEST)]
    on_path = shutil.which("kitty")
    if on_path is not None:
        candidates.insert(0, Path(on_path))
    for candidate in candidates:
        if candidate.is_file() or candidate.is_symlink():
            try:
                version = subprocess.run(  # noqa: S603 — trusted path
                    [str(candidate), "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                ).stdout.strip()
            except (subprocess.SubprocessError, OSError) as exc:
                return (
                    CheckResult("kitty binary", False, f"{candidate} present but failed: {exc}"),
                    None,
                )
            return CheckResult("kitty binary", True, f"{candidate} -> {version}"), candidate
    return CheckResult("kitty binary", False, "no kitty on PATH or under ~/.local"), None


def _check_symlink() -> CheckResult:
    link = installer.SYMLINK_PATH
    if link.is_symlink():
        return CheckResult("symlink", True, f"{link} -> {link.resolve()}")
    if link.exists():
        return CheckResult("symlink", False, f"{link} exists but is not a symlink")
    return CheckResult("symlink", False, f"missing: {link}")


def _check_desktop_entry() -> CheckResult:
    entry = installer.DESKTOP_PATH
    if entry.is_file():
        return CheckResult("desktop entry", True, str(entry))
    return CheckResult("desktop entry", False, f"missing: {entry}")


def _check_payload(paths: config_updater.ConfigPaths) -> CheckResult:
    if paths.payload_entry.is_file():
        return CheckResult("config payload", True, str(paths.payload_entry))
    return CheckResult("config payload", False, f"missing: {paths.payload_entry}")


def _check_sentinel_block(paths: config_updater.ConfigPaths) -> CheckResult:
    if not paths.conf_file.exists():
        return CheckResult("sentinel block", False, f"missing: {paths.conf_file}")
    if config_updater.is_block_present(paths):
        return CheckResult("sentinel block", True, f"present in {paths.conf_file}")
    return CheckResult("sentinel block", False, f"absent from {paths.conf_file}")


def _check_parse(paths: config_updater.ConfigPaths, kitty_bin: Path | None) -> CheckResult:
    if kitty_bin is None:
        return CheckResult("parse check", False, "skipped — kitty binary not available")
    if not paths.conf_file.exists():
        return CheckResult("parse check", False, f"missing: {paths.conf_file}")
    try:
        ok = config_updater._parse_check(paths.conf_file, kitty_bin)
    except config_updater.ConfigUpdaterError as exc:
        return CheckResult("parse check", False, str(exc))
    return CheckResult("parse check", ok, f"kitty --debug-config exit={'0' if ok else 'non-0'}")


def _check_bindings(paths: config_updater.ConfigPaths, kitty_bin: Path | None) -> CheckResult:
    if kitty_bin is None:
        return CheckResult("bindings", False, "skipped — kitty binary not available")
    if not paths.conf_file.exists():
        return CheckResult("bindings", False, f"missing: {paths.conf_file}")
    try:
        report = binding_introspection.enumerate_bindings(
            paths.conf_file, kitty_bin=kitty_bin, payload_dir=paths.payload_dir
        )
    except binding_introspection.BindingIntrospectionError as exc:
        return CheckResult("bindings", False, f"skipped — {exc}")
    summary = (
        f"{report.ours_count} ours, {report.defaults_count} defaults, "
        f"{report.conflicts_count} conflict{'s' if report.conflicts_count != 1 else ''}"
    )
    if report.conflicts_count == 0:
        return CheckResult("bindings", True, summary)
    return CheckResult("bindings", False, f"{summary} (run `my-kitty keys` for details)")


_RC_BY_SHELL: dict[str, str] = {"zsh": ".zshrc", "bash": ".bashrc"}


def _check_completion(home: Path | None = None) -> CheckResult:
    """Verify the argcomplete helper + the completion eval line in rc."""
    helper = shutil.which("register-python-argcomplete")
    home_dir = home or Path.home()
    shell_name = Path(os.environ.get("SHELL", "")).name
    rc_basename = _RC_BY_SHELL.get(shell_name)
    if rc_basename is None:
        rc_basename = ".zshrc"  # default when shell is unknown
    rc_file = home_dir / rc_basename
    rc_text = rc_file.read_text(encoding="utf-8") if rc_file.is_file() else ""
    bounds = path_integration._find_block(
        rc_text, path_integration.MARKER_BEGIN, path_integration.MARKER_END
    )
    body = ""
    if bounds is not None:
        body_lines = rc_text.splitlines(keepends=False)[bounds[0] + 1 : bounds[1] - 1]
        body = "\n".join(body_lines)
    rc_has_eval = path_integration.COMPLETION_LINE in body

    if helper is not None and rc_has_eval:
        return CheckResult("completion", True, f"helper {helper}; eval line present in {rc_file}")
    if helper is None and not rc_has_eval:
        return CheckResult(
            "completion",
            False,
            f"register-python-argcomplete not on PATH AND eval line missing from {rc_file}",
        )
    if helper is None:
        return CheckResult("completion", False, "register-python-argcomplete not on PATH")
    return CheckResult(
        "completion",
        False,
        f"register-python-argcomplete present at {helper}; eval line missing from {rc_file}",
    )


def run_checks(home: Path | None = None) -> list[CheckResult]:
    paths = config_updater.ConfigPaths.for_user(home=home)
    binary_check, kitty_bin = _check_kitty_binary()
    return [
        binary_check,
        _check_symlink(),
        _check_desktop_entry(),
        _check_payload(paths),
        _check_sentinel_block(paths),
        _check_parse(paths, kitty_bin),
        _check_bindings(paths, kitty_bin),
        _check_completion(home=home),
    ]


def cli_doctor(args: object | None = None) -> int:
    """Handler for ``my-kitty-setup doctor``. Accepts (and ignores) parsed args."""
    del args  # no flags yet (JSON output deferred)
    results = run_checks()
    for result in results:
        print(result.render())
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(cli_doctor())
