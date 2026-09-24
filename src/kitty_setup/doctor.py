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
from kitty_setup.scenes._client import _parse_listen_on_base, _pgrep_kitty_pids

# ``_check_completion`` is shared with the integration test that proves its verdict equals what
# real zsh registers (tests/integration/test_completion_e2e.py), so it is declared here.
__all__ = ["CheckResult", "_check_completion", "cli_doctor", "run_checks"]


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


def _one_line(text: str) -> str:
    """Join a multi-line diagnostic onto one line, so each check keeps one output line."""
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _check_parse(paths: config_updater.ConfigPaths, kitty_bin: Path | None) -> CheckResult:
    if kitty_bin is None:
        return CheckResult("parse check", False, "kitty binary not available", skipped=True)
    if not paths.conf_file.exists():
        return CheckResult("parse check", False, f"missing: {paths.conf_file}")
    try:
        result = config_updater._parse_check(paths.conf_file, kitty_bin)
    except config_updater.ConfigUpdaterError as exc:
        return CheckResult("parse check", False, str(exc))
    diagnostics = _one_line(result.stderr)
    if result.ok:
        warnings = f"; parser warnings: {diagnostics}" if diagnostics else ""
        return CheckResult("parse check", True, f"{result.command} exit=0{warnings}")
    return CheckResult(
        "parse check", False, f"{result.command} exit=non-0: {diagnostics or '(no stderr)'}"
    )


def _check_bindings(paths: config_updater.ConfigPaths, kitty_bin: Path | None) -> CheckResult:
    if kitty_bin is None:
        return CheckResult("bindings", False, "kitty binary not available", skipped=True)
    if not paths.conf_file.exists():
        return CheckResult("bindings", False, f"missing: {paths.conf_file}")
    try:
        report = binding_introspection.enumerate_bindings(
            paths.conf_file, kitty_bin=kitty_bin, payload_dir=paths.payload_dir
        )
    except binding_introspection.BindingIntrospectionError as exc:
        return CheckResult("bindings", False, str(exc), skipped=True)
    summary = (
        f"{report.ours_count} ours, {report.defaults_count} defaults, "
        f"{report.conflicts_count} conflict{'s' if report.conflicts_count != 1 else ''}"
    )
    if report.conflicts_count == 0:
        return CheckResult("bindings", True, summary)
    return CheckResult("bindings", False, f"{summary} (run `my-kitty keys` for details)")


def _kitten_ls_succeeds(kitten_bin: Path, socket: Path) -> tuple[bool, str]:
    """Return ``(ok, stderr_or_empty)`` for ``kitten @ --to unix:<socket> ls``.

    ``KITTY_LISTEN_ON`` is unset in the child's environment.
    """
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
    respond. Verified by probe 04
    (`tmp/probes/phase2-remote-control-foundation/04-out-of-process-ls.md`).
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
            return CheckResult(
                "remote-control", False, "no kitten binary on PATH or under ~/.local"
            )
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
    """Verify what can be proven about shell completion without starting the user's shell.

    In order, reporting the first failure: the completion script we own exists; our rc block's
    body is exactly the current template for the shell; for zsh, nothing executable follows the
    block; and the script's bytes equal freshly generated shellcode (the staleness check, U-3).
    The block is judged with the same two predicates install uses to decide whether to rewrite
    or move it, so doctor FAILs exactly the blocks the next ``my-kitty install`` fixes.
    """
    home_dir = home or Path.home()
    shell_name = Path(os.environ.get("SHELL", "")).name
    rc_basename = _RC_BY_SHELL.get(shell_name)
    if rc_basename is None:
        return CheckResult(
            "completion",
            False,
            f"shell {shell_name or '<unknown>'} is not supported; "
            "completion is set up for bash and zsh only",
            skipped=True,
        )
    script = installer.completion_script_path(shell_name, home=home)
    if not script.is_file():
        return CheckResult(
            "completion", False, f"{script} is missing; run `my-kitty install` to generate it"
        )

    rc_file = home_dir / rc_basename
    rc_text = rc_file.read_text(encoding="utf-8") if rc_file.is_file() else ""
    bounds = path_integration._find_block(
        rc_text, path_integration.MARKER_BEGIN, path_integration.MARKER_END
    )
    if bounds is None or not path_integration._block_body_matches_template(
        rc_text, bounds, shell_name
    ):
        return CheckResult(
            "completion",
            False,
            f"the my-kitty block in {rc_file} does not match the current template that "
            f"sources {script}; run `my-kitty install` to rewrite it",
        )
    is_zsh = shell_name == installer.CompletionShell.ZSH
    if is_zsh and not path_integration._block_followed_only_by_comments(rc_text, bounds):
        return CheckResult(
            "completion",
            False,
            f"the my-kitty block in {rc_file} is not the last command in it, so a later "
            "compinit undoes its registration; run `my-kitty install` to move it to the end",
        )

    try:
        current = script.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return CheckResult("completion", False, f"cannot read {script}: {exc}")
    if current != installer.generate_completion_script(shell_name):
        return CheckResult(
            "completion",
            False,
            f"{script} is stale: it differs from freshly generated shellcode; "
            "run `my-kitty install` to regenerate it",
        )

    if is_zsh:
        return CheckResult(
            "completion",
            True,
            f"{script} is current and sourced by the my-kitty block in {rc_file}, which starts "
            "zsh's completion system itself when needed and is the last command in the file "
            "(both checked). Doctor did not observe a live registration, and ~/.zlogin or a "
            "ZDOTDIR elsewhere is outside what it reads; to confirm, run "
            "`echo ${_comps[my-kitty]}` in a new shell",
        )
    return CheckResult(
        "completion", True, f"{script} is current and sourced by the my-kitty block in {rc_file}"
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
