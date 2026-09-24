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
    monkeypatch.setattr(doctor.installer, "_kitty_bin", lambda _: tmp_path / "missing-kitty")

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
