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
        'exit 0\n',
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


def test_run_checks_reports_each_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(doctor.installer, "SYMLINK_PATH", tmp_path / "missing-link")
    monkeypatch.setattr(doctor.installer, "DESKTOP_PATH", tmp_path / "missing.desktop")
    monkeypatch.setattr(
        doctor.installer, "_kitty_bin", lambda _: tmp_path / "missing-kitty"
    )

    results = doctor.run_checks(home=home)
    names = [r.name for r in results]
    assert names == [
        "kitty binary",
        "symlink",
        "desktop entry",
        "config payload",
        "sentinel block",
        "parse check",
    ]
    assert all(not r.passed for r in results)


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
    code = doctor.main()
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
    code = doctor.main()
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out == ["PASS alpha: ok"]


def test_check_kitty_binary_handles_subprocess_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    failing = tmp_path / "broken-kitty"
    failing.write_text(
        "#!/usr/bin/env bash\nexit 5\n", encoding="utf-8"
    )
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
