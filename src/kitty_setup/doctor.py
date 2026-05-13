"""Diagnostic that reports the install footprint and config-include health.

Implements the ``doctor`` requirement from the kitty-install capability. Prints
one line per check in ``PASS|FAIL <check>: <detail>`` form and exits non-zero
on any FAIL.
"""

from __future__ import annotations

import dataclasses
import os
import re
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
    skipped: bool = False

    def render(self) -> str:
        if self.skipped:
            return f"SKIP {self.name}: {self.detail}"
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


_LISTEN_ON_RE = re.compile(r"^\s*listen_on\s+unix:(?P<path>\S+)", re.MULTILINE)


def _parse_listen_on_base(remote_control_conf: Path) -> str | None:
    """Return the `listen_on unix:<path>` base path from the managed `remote-control.conf`.

    The resolved per-instance socket appends `-<PID>` to this base (kitty's documented
    behaviour, verified by probe 01 of phase2-remote-control-foundation). Returns
    ``None`` when the file is absent or contains no ``listen_on`` directive.
    """
    if not remote_control_conf.is_file():
        return None
    match = _LISTEN_ON_RE.search(remote_control_conf.read_text(encoding="utf-8"))
    return match.group("path") if match else None


def _pgrep_kitty_pids() -> list[int]:
    """Return the PIDs of running kitty processes (`pgrep -x kitty`)."""
    try:
        result = subprocess.run(  # noqa: S603 — fixed argv, trusted binary
            ["pgrep", "-x", "kitty"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode not in (0, 1):  # 1 = no matches; that is not an error
        return []
    return [int(line) for line in result.stdout.split() if line.isdigit()]


def _kitten_ls_succeeds(kitten_bin: Path, socket: Path) -> tuple[bool, str]:
    """Return ``(ok, stderr_or_empty)`` for ``kitten @ --to unix:<socket> ls`` with KITTY_LISTEN_ON unset."""
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    try:
        result = subprocess.run(  # noqa: S603 — trusted paths
            [str(kitten_bin), "@", f"--to=unix:{socket}", "ls"],
            capture_output=True,
            check=False,
            timeout=2,
            env=env,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, ""
    return False, result.stderr.decode("utf-8", errors="replace").strip()


def _check_remote_control_per_probe_04(paths: config_updater.ConfigPaths) -> CheckResult:
    """Per-instance remote-control reachability — best-effort, never fails on "no kitty running".

    Resolves the socket base from `remote-control.conf`, enumerates running kitty
    PIDs via `pgrep -x kitty`, and for every PID where the resolved socket
    `<base>-<PID>` exists on disk, calls `kitten @ ls` against it. SKIPs when no
    kitty is running OR no managed socket exists (e.g. a pre-`make setup` kitty
    is still running). FAILs only when at least one managed socket fails to
    respond. Verified by probe 04 (`tmp/probes/phase2-remote-control-foundation/04-out-of-process-ls.md`).
    """
    rc_conf = paths.payload_dir / "remote-control.conf"
    if not rc_conf.is_file():
        return CheckResult(
            "remote-control",
            True,
            "managed remote-control.conf not installed (run `make install`)",
            skipped=True,
        )
    base = _parse_listen_on_base(rc_conf)
    if base is None:
        return CheckResult(
            "remote-control", False, f"{rc_conf} has no `listen_on unix:<path>` directive"
        )

    kitten_bin = installer.DEFAULT_DEST / "kitty.app" / "bin" / "kitten"
    if not kitten_bin.is_file():
        on_path = shutil.which("kitten")
        if on_path is None:
            return CheckResult("remote-control", False, "no kitten binary on PATH or under ~/.local")
        kitten_bin = Path(on_path)

    pids = _pgrep_kitty_pids()
    reachable: list[int] = []
    failures: list[str] = []
    for pid in pids:
        socket = Path(f"{base}-{pid}")
        if not socket.exists():
            continue  # not a managed kitty; skip silently
        ok, stderr = _kitten_ls_succeeds(kitten_bin, socket)
        if ok:
            reachable.append(pid)
        else:
            failures.append(f"{socket} ({stderr or 'unknown error'})")

    if not pids:
        return CheckResult("remote-control", True, "no running kitty", skipped=True)
    if not reachable and not failures:
        return CheckResult(
            "remote-control",
            True,
            "no managed kitty socket found (running kitty pre-dates `make setup`?)",
            skipped=True,
        )
    if failures:
        return CheckResult("remote-control", False, "; ".join(failures))
    return CheckResult(
        "remote-control",
        True,
        f"reachable on {len(reachable)} kitty instance{'s' if len(reachable) != 1 else ''}",
    )


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
        _check_remote_control_per_probe_04(paths),
    ]


def cli_doctor(args: object | None = None) -> int:
    """Handler for ``my-kitty-setup doctor``. Accepts (and ignores) parsed args."""
    del args  # no flags yet (JSON output deferred)
    results = run_checks()
    for result in results:
        print(result.render())
    return 0 if all(r.passed or r.skipped for r in results) else 1


if __name__ == "__main__":
    sys.exit(cli_doctor())
