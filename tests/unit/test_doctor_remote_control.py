"""Unit tests for the remote-control reachability check in ``kitty_setup.doctor``.

The check has three branches: SKIP (no kitty running OR managed conf absent),
PASS (every managed socket reachable), FAIL (at least one managed socket
unreachable). These tests stub ``pgrep_kitty_pids`` and ``_kitten_ls_succeeds``
to drive each branch without spawning real kitty processes.

The ``_per_probe_04`` suffix on the SUT function name carries the link to
``tmp/probes/phase2-remote-control-foundation/04-out-of-process-ls.md``,
which captured the real-system shape these stubs mock (R7 of agent-iteration).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kitty_setup import config_updater, doctor


@pytest.fixture()
def paths_with_rc(tmp_path: Path) -> config_updater.ConfigPaths:
    """Materialise a ``ConfigPaths`` rooted at ``tmp_path`` with a valid `remote-control.conf`."""
    home = tmp_path / "home"
    home.mkdir()
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        "allow_remote_control yes\nlisten_on unix:/tmp/kitty\n", encoding="utf-8"
    )
    return paths


@pytest.fixture()
def paths_without_rc(tmp_path: Path) -> config_updater.ConfigPaths:
    home = tmp_path / "home"
    home.mkdir()
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True)
    return paths


def test_parse_listen_on_base_returns_path(paths_with_rc: config_updater.ConfigPaths) -> None:
    base = doctor.parse_listen_on_base(paths_with_rc.payload_dir / "remote-control.conf")
    assert base == "/tmp/kitty"


def test_parse_listen_on_base_missing_returns_none(tmp_path: Path) -> None:
    assert doctor.parse_listen_on_base(tmp_path / "nope.conf") is None


def test_parse_listen_on_base_no_directive_returns_none(tmp_path: Path) -> None:
    conf = tmp_path / "rc.conf"
    conf.write_text("allow_remote_control yes\n", encoding="utf-8")
    assert doctor.parse_listen_on_base(conf) is None


def test_remote_control_skips_when_rc_conf_missing(
    paths_without_rc: config_updater.ConfigPaths,
) -> None:
    result = doctor._check_remote_control_per_probe_04(paths_without_rc)
    assert result.skipped is True
    assert "not installed" in result.detail


def test_remote_control_skips_when_no_kitty_running(
    paths_with_rc: config_updater.ConfigPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "pgrep_kitty_pids", lambda: [])
    result = doctor._check_remote_control_per_probe_04(paths_with_rc)
    assert result.skipped is True
    assert "no running kitty" in result.detail


def test_remote_control_skips_when_no_managed_socket_found(
    paths_with_rc: config_updater.ConfigPaths,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Kitty running but no socket at /tmp/kitty-<PID> — e.g. a pre-`make setup` kitty
    # the user hasn't restarted yet. The check must SKIP, not FAIL.
    monkeypatch.setattr(doctor, "pgrep_kitty_pids", lambda: [99999])
    monkeypatch.setattr(
        doctor, "_kitten_ls_succeeds", lambda *args, **kwargs: (False, "should not be called")
    )
    # The resolved socket path /tmp/kitty-99999 doesn't exist (huge PID never used).
    result = doctor._check_remote_control_per_probe_04(paths_with_rc)
    assert result.skipped is True
    assert "no managed kitty socket" in result.detail


def test_remote_control_passes_when_managed_socket_reachable(
    paths_with_rc: config_updater.ConfigPaths,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Materialise a fake socket file so the path-existence guard passes, then
    # stub the kitten @ ls subprocess to "succeed". The base path resolution is
    # exercised end-to-end (parser + concatenation), the kernel-level subprocess
    # call is the only stubbed step.
    fake_socket_base = tmp_path / "kitty"
    (paths_with_rc.payload_dir / "remote-control.conf").write_text(
        f"allow_remote_control yes\nlisten_on unix:{fake_socket_base}\n", encoding="utf-8"
    )
    fake_pid = 12345
    fake_socket = tmp_path / f"kitty-{fake_pid}"
    fake_socket.touch()

    monkeypatch.setattr(doctor, "pgrep_kitty_pids", lambda: [fake_pid])
    monkeypatch.setattr(doctor, "_kitten_ls_succeeds", lambda *args, **kwargs: (True, ""))

    result = doctor._check_remote_control_per_probe_04(paths_with_rc)
    assert result.passed is True
    assert result.skipped is False
    assert "reachable on 1 kitty instance" in result.detail


def test_remote_control_fails_when_managed_socket_unreachable(
    paths_with_rc: config_updater.ConfigPaths,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_socket_base = tmp_path / "kitty"
    (paths_with_rc.payload_dir / "remote-control.conf").write_text(
        f"allow_remote_control yes\nlisten_on unix:{fake_socket_base}\n", encoding="utf-8"
    )
    fake_pid = 12345
    (tmp_path / f"kitty-{fake_pid}").touch()

    monkeypatch.setattr(doctor, "pgrep_kitty_pids", lambda: [fake_pid])
    monkeypatch.setattr(
        doctor, "_kitten_ls_succeeds", lambda *args, **kwargs: (False, "connection refused")
    )

    result = doctor._check_remote_control_per_probe_04(paths_with_rc)
    assert result.passed is False
    assert result.skipped is False
    assert "connection refused" in result.detail


def test_skip_does_not_contribute_to_failure_in_cli(
    paths_without_rc: config_updater.ConfigPaths,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A SKIP in the remote-control check must not flip ``cli_doctor`` to non-zero."""
    monkeypatch.setattr(doctor, "run_checks", lambda home=None: [
        doctor.CheckResult("foo", True, "ok"),
        doctor.CheckResult("remote-control", True, "no running kitty", skipped=True),
    ])
    exit_code = doctor.cli_doctor()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SKIP remote-control: no running kitty" in captured.out
