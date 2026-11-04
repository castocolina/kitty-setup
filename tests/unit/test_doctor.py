"""Unit tests for ``kitty_setup.doctor``.

The kitty binary check is exercised against a fake shell script that prints a
canned ``--version`` string. No real Kitty install is required.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from kitty_setup import doctor


def _fake_kitty(tmp_path: Path, version: str = "kitty 0.46.2 (fake)") -> Path:
    script = tmp_path / "fake-kitty"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'if [[ "$1" == "--version" ]]; then echo "{version}"; exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_check_result_render() -> None:
    pass_line = doctor.CheckResult("foo", True, "bar").render()
    fail_line = doctor.CheckResult("foo", False, "bar").render()
    assert pass_line == "PASS foo: bar"
    assert fail_line == "FAIL foo: bar"


def test_check_kitty_binary_finds_fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = _fake_kitty(tmp_path)
    monkeypatch.setattr(doctor.shutil, "which", lambda _: str(fake))
    result, resolved = doctor._check_kitty_binary()
    assert result.passed
    assert resolved == fake
    assert "0.46.2" in result.detail


def test_check_kitty_binary_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(doctor.installer, "DEFAULT_DEST", tmp_path / "nope")
    monkeypatch.setattr(doctor.installer, "SYMLINK_PATH", tmp_path / "no-link")
    result, resolved = doctor._check_kitty_binary()
    assert not result.passed
    assert resolved is None


def test_run_checks_reports_each_check(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(doctor.installer, "SYMLINK_PATH", tmp_path / "missing-link")
    monkeypatch.setattr(doctor.installer, "DESKTOP_PATH", tmp_path / "missing.desktop")
    monkeypatch.setattr(doctor.installer, "kitty_bin_path", lambda _: tmp_path / "missing-kitty")

    results = doctor.run_checks(home=home)
    names = [r.name for r in results]
    assert names == [
        "kitty binary",
        "symlink",
        "desktop entry",
        "config payload",
        "sentinel block",
        "parse check",
        "bindings",
        "completion",
        "remote-control",
    ]
    # All non-skipped checks must FAIL given the synthetic empty home. The
    # remote-control check SKIPs when `remote-control.conf` is absent — that
    # branch is correct here and is the expected behaviour after the
    # phase2-remote-control-foundation change.
    for r in results:
        assert not r.passed or r.skipped, f"{r.name} unexpectedly passed: {r.detail!r}"


def test_main_exits_non_zero_on_any_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        doctor,
        "run_checks",
        lambda home=None: [
            doctor.CheckResult("alpha", True, "ok"),
            doctor.CheckResult("beta", False, "broken"),
        ],
    )
    code = doctor.cli_doctor()
    out = capsys.readouterr().out.splitlines()
    assert code == 1
    assert out == ["PASS alpha: ok", "FAIL beta: broken"]


def test_main_exits_zero_on_all_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        doctor,
        "run_checks",
        lambda home=None: [doctor.CheckResult("alpha", True, "ok")],
    )
    code = doctor.cli_doctor()
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out == ["PASS alpha: ok"]


def test_check_kitty_binary_handles_subprocess_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    failing = tmp_path / "broken-kitty"
    failing.write_text("#!/usr/bin/env bash\nexit 5\n", encoding="utf-8")
    failing.chmod(failing.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(doctor.shutil, "which", lambda _: str(failing))

    result, resolved = doctor._check_kitty_binary()
    assert not result.passed
    assert resolved is None


def test_run_checks_uses_supplied_home_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    real_for_user = doctor.config_updater.ConfigPaths.for_user

    def spy(*, home: Path | None = None) -> Any:
        captured["home"] = home
        return real_for_user(home=home)

    monkeypatch.setattr(doctor.config_updater.ConfigPaths, "for_user", spy)
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(doctor.installer, "SYMLINK_PATH", tmp_path / "missing-link")
    monkeypatch.setattr(doctor.installer, "DESKTOP_PATH", tmp_path / "missing.desktop")

    def missing_kitty(dest: Path) -> Path:
        del dest
        return tmp_path / "missing-kitty"

    monkeypatch.setattr(doctor.installer, "kitty_bin_path", missing_kitty)

    doctor.run_checks(home=tmp_path)
    assert captured["home"] == tmp_path


def test_check_kitty_binary_subprocess_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = _fake_kitty(tmp_path)
    monkeypatch.setattr(doctor.shutil, "which", lambda _: str(fake))

    def boom(*_a: object, **_k: object) -> None:
        raise subprocess.TimeoutExpired(cmd="kitty", timeout=1)

    monkeypatch.setattr(doctor.subprocess, "run", boom)
    result, resolved = doctor._check_kitty_binary()
    assert not result.passed
    assert resolved is None


# --- completion (R1.1, D-01..D-03, U-3) -------------------------------------
# Built from the producers the runtime uses: ``installer.write_completion_script`` and
# ``path_integration.ensure_local_bin_in_path`` against a ``tmp_path`` home, with ``SHELL`` set.
# Each case asserts text no pre-D-01 detail can contain: under ``uv run`` the venv's ``bin/`` is
# on PATH, so the old helper lookup PASSes on the eval line alone.


def _completion_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shell: str) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("SHELL", f"/usr/bin/{shell}")
    doctor.installer.write_completion_script(shell, home=home)
    doctor.path_integration.ensure_local_bin_in_path(home=home, shell=shell)
    return home


def test_completion_check_passes_bash_naming_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _completion_home(tmp_path, monkeypatch, "bash")
    result = doctor._check_completion(home=home)
    assert result.name == "completion"
    assert result.passed is True
    assert result.skipped is False
    assert str(doctor.installer.completion_script_path("bash", home=home)) in result.detail


def test_completion_check_fails_when_file_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _completion_home(tmp_path, monkeypatch, "bash")
    script = doctor.installer.completion_script_path("bash", home=home)
    script.unlink()
    result = doctor._check_completion(home=home)
    assert result.passed is False
    assert result.skipped is False
    assert str(script) in result.detail


def test_completion_check_fails_when_file_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _completion_home(tmp_path, monkeypatch, "bash")
    script = doctor.installer.completion_script_path("bash", home=home)
    script.write_text("# shellcode from an older argcomplete\n", encoding="utf-8")
    result = doctor._check_completion(home=home)
    assert result.passed is False
    assert str(script) in result.detail
    assert "stale" in result.detail
    assert "my-kitty install" in result.detail


def test_completion_check_fails_when_block_lacks_source_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _completion_home(tmp_path, monkeypatch, "bash")
    rc = home / ".bashrc"
    rc.write_text(
        f"{doctor.path_integration.MARKER_BEGIN}\n"
        f"{doctor.path_integration.EXPORT_LINE}\n"
        f"{doctor.path_integration.MARKER_END}\n",
        encoding="utf-8",
    )
    result = doctor._check_completion(home=home)
    assert result.passed is False
    assert str(rc) in result.detail
    assert str(doctor.installer.completion_script_path("bash", home=home)) in result.detail


def test_completion_check_skips_unsupported_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    result = doctor._check_completion(home=home)
    assert result.skipped is True
    assert "fish" in result.detail
    assert result.render().startswith("SKIP completion: ")


def test_completion_check_passes_zsh_and_says_what_it_did_not_observe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = _completion_home(tmp_path, monkeypatch, "zsh")
    result = doctor._check_completion(home=home)
    assert result.passed is True
    assert str(doctor.installer.completion_script_path("zsh", home=home)) in result.detail
    assert "not observe" in result.detail
    assert "_comps" in result.detail


def test_completion_check_fails_zsh_block_followed_by_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Measured: a ``compinit`` after our block resets ``_comps``, so a structural PASS lies."""
    home = _completion_home(tmp_path, monkeypatch, "zsh")
    rc = home / ".zshrc"
    rc.write_text(rc.read_text(encoding="utf-8") + "autoload -Uz compinit && compinit\n")
    result = doctor._check_completion(home=home)
    assert result.passed is False
    assert result.skipped is False
    assert str(rc) in result.detail
    assert "my-kitty install" in result.detail


def test_completion_check_fails_zsh_body_without_self_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The pre-revision guard-only body, last, with no ``compinit`` anywhere: registers nothing.

    Hand-built, because no producer emits this body any more.
    """
    home = _completion_home(tmp_path, monkeypatch, "zsh")
    rc = home / ".zshrc"
    rc.write_text(
        f"{doctor.path_integration.MARKER_BEGIN}\n"
        f"{doctor.path_integration.EXPORT_LINE}\n"
        f"{doctor.path_integration.completion_source_line('zsh')}\n"
        f"{doctor.path_integration.MARKER_END}\n",
        encoding="utf-8",
    )
    result = doctor._check_completion(home=home)
    assert result.passed is False
    assert result.skipped is False
    assert str(rc) in result.detail
    assert "my-kitty install" in result.detail


# --- parse check and bindings: real SKIPs, and a label taken from the result (R1.5, R1.7) --------
# Driven through the public ``run_checks`` with ``_check_kitty_binary`` replaced by name, so these
# cases add no pyright ``reportPrivateUsage`` finding. New names (``ParseCheckResult``) are reached
# as module attributes inside each body, so a missing one fails its own case at RED.

BAD_LINE_DIAG = (
    "BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: "
    "banana allowed values are block, beam, underline'), file='kitty-setup/kitty-setup.conf')\n"
)
MISSING_INCLUDE_WARNING = (
    "[0.009] Could not find included config file: /x/kitty-setup/kitty-setup.conf, ignoring\n"
)


def _doctor_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    paths = doctor.config_updater.ConfigPaths.for_user(home=home)
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    return home


def _fake_parser_kitty(tmp_path: Path, *, exit_code: int, stderr: str = "") -> Path:
    """A fake kitty that writes ``stderr`` verbatim and exits ``exit_code`` for any argv."""
    script = tmp_path / f"fake-parser-kitty-{exit_code}"
    sidecar = tmp_path / f"fake-parser-kitty-{exit_code}.stderr"
    sidecar.write_text(stderr, encoding="utf-8")
    script.write_text(
        f"#!/usr/bin/env bash\ncat '{sidecar}' >&2\nexit {exit_code}\n", encoding="utf-8"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _checks_by_name(
    monkeypatch: pytest.MonkeyPatch,
    home: Path,
    kitty: Path | None,
    *,
    bindings_error: str = "introspection is not exercised by this case",
) -> dict[str, doctor.CheckResult]:
    def fake_kitty_binary() -> tuple[doctor.CheckResult, Path | None]:
        return doctor.CheckResult("kitty binary", kitty is not None, str(kitty)), kitty

    def failing_introspection(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise doctor.binding_introspection.BindingIntrospectionError(bindings_error)

    monkeypatch.setattr(doctor, "_check_kitty_binary", fake_kitty_binary)
    monkeypatch.setattr(doctor.binding_introspection, "enumerate_bindings", failing_introspection)
    return {r.name: r for r in doctor.run_checks(home=home)}


def _assert_one_skip(result: doctor.CheckResult, name: str) -> None:
    line = result.render()
    assert result.skipped is True
    assert result.passed is False
    assert line == f"SKIP {name}: {result.detail}"
    assert line.count("SKIP") == 1
    assert "skipped" not in line[len("SKIP ") :].lower()


def test_skip_state_parse_check_without_kitty_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result = _checks_by_name(monkeypatch, _doctor_home(tmp_path), None)["parse check"]
    _assert_one_skip(result, "parse check")
    assert "kitty binary not available" in result.detail


def test_skip_state_bindings_without_kitty_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result = _checks_by_name(monkeypatch, _doctor_home(tmp_path), None)["bindings"]
    _assert_one_skip(result, "bindings")
    assert "kitty binary not available" in result.detail


def test_skip_state_bindings_when_introspection_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kitty = _fake_parser_kitty(tmp_path, exit_code=0)
    checks = _checks_by_name(
        monkeypatch, _doctor_home(tmp_path), kitty, bindings_error="probe failure"
    )
    result = checks["bindings"]
    _assert_one_skip(result, "bindings")
    assert result.detail == "probe failure"


def test_parse_detail_names_the_command_from_the_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sentinel = "/sentinel/kitty +runpy 'import sys' /sentinel/kitty.conf"

    def fake_parse_check(
        conf_file: Path, kitty_bin: str | Path
    ) -> doctor.config_updater.ParseCheckResult:
        del conf_file, kitty_bin
        return doctor.config_updater.ParseCheckResult(ok=True, command=sentinel, stderr="")

    monkeypatch.setattr(doctor.config_updater, "parse_check", fake_parse_check)
    kitty = _fake_parser_kitty(tmp_path, exit_code=0)
    result = _checks_by_name(monkeypatch, _doctor_home(tmp_path), kitty)["parse check"]
    assert result.passed is True
    assert result.skipped is False
    assert sentinel in result.detail
    assert "--debug-config" not in result.detail


def test_parse_detail_surfaces_parser_stderr_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kitty = _fake_parser_kitty(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG)
    result = _checks_by_name(monkeypatch, _doctor_home(tmp_path), kitty)["parse check"]
    assert result.passed is False
    assert result.skipped is False
    assert BAD_LINE_DIAG.strip() in result.detail
    assert "+runpy" in result.detail
    assert "--debug-config" not in result.detail
    assert "\n" not in result.render()


def test_parse_detail_pass_carries_parser_warnings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing include does not fail the check (T-2-19), so the PASS line must show it."""
    kitty = _fake_parser_kitty(tmp_path, exit_code=0, stderr=MISSING_INCLUDE_WARNING)
    result = _checks_by_name(monkeypatch, _doctor_home(tmp_path), kitty)["parse check"]
    assert result.passed is True
    assert MISSING_INCLUDE_WARNING.strip() in result.detail
    assert "+runpy" in result.detail
    assert "\n" not in result.render()


def test_guard_kitty_less_host_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Over the real ``run_checks``: two checks turning into SKIPs must not let this host pass."""
    home = _doctor_home(tmp_path)
    missing_kitty = tmp_path / "missing-kitty"

    def no_which(name: str) -> None:
        del name

    def kitty_bin_under(dest: Path) -> Path:
        del dest
        return missing_kitty

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(doctor.shutil, "which", no_which)
    monkeypatch.setattr(doctor.installer, "SYMLINK_PATH", tmp_path / "missing-link")
    monkeypatch.setattr(doctor.installer, "DESKTOP_PATH", tmp_path / "missing.desktop")
    monkeypatch.setattr(doctor.installer, "kitty_bin_path", kitty_bin_under)

    code = doctor.cli_doctor()

    lines = capsys.readouterr().out.splitlines()
    assert code == 1
    assert len(lines) == 9
    assert lines[0].startswith("FAIL kitty binary: ")


def test_guard_all_pass_or_skip_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def all_pass_or_skip(home: Path | None = None) -> list[doctor.CheckResult]:
        del home
        return [
            doctor.CheckResult("alpha", True, "ok"),
            doctor.CheckResult("beta", False, "not applicable on this host", skipped=True),
        ]

    monkeypatch.setattr(doctor, "run_checks", all_pass_or_skip)

    code = doctor.cli_doctor()

    assert code == 0
    assert capsys.readouterr().out.splitlines() == [
        "PASS alpha: ok",
        "SKIP beta: not applicable on this host",
    ]


_OUR_BLOCK = (
    f"{doctor.config_updater.MARKER_BEGIN}\n{doctor.config_updater.INCLUDE_LINE}\n"
    f"{doctor.config_updater.MARKER_END}\n"
).encode()


def test_parse_cannot_run_is_a_fail_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A parse check that times out is a FAIL line naming the timeout, not a traceback (WR-01)."""
    paths = doctor.config_updater.ConfigPaths.for_user(home=_doctor_home(tmp_path))

    def timed_out(*args: Any, **kwargs: Any) -> None:
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=15)

    monkeypatch.setattr(doctor.config_updater.subprocess, "run", timed_out)
    check_parse = vars(doctor)["_check_parse"]
    result = check_parse(paths, Path("/nonexistent/kitty"))
    assert not result.passed
    assert not result.skipped
    assert "did not finish within" in result.detail


def test_sentinel_non_utf8(tmp_path: Path) -> None:
    """A Latin-1 byte outside our block does not break doctor's sentinel check (WR-06)."""
    home = tmp_path / "home"
    conf = home / ".config" / "kitty" / "kitty.conf"
    conf.parent.mkdir(parents=True)
    conf.write_bytes(b"# caf\xe9 comment\nfont_size 13\n" + _OUR_BLOCK)
    paths = doctor.config_updater.ConfigPaths.for_user(home=home)
    check_sentinel = vars(doctor)["_check_sentinel_block"]
    assert check_sentinel(paths).passed
