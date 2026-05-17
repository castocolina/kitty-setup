"""Unit tests for `kitty_setup.scenes._client` socket discovery + kitten_at.

Each test stub carries the provisional-per-R7 docstring per the spec: the
unit stubs of `subprocess.run` and the filesystem are valid because (a) the
hypothesis probe `tmp/h22-window-title/run.py` grounded the real shape, and
(b) `tests/integration/test_client_socket_discovery.py` (§7.1) exercises the
live pgrep path. Until §7.1 is green, treat these stubs as provisional.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from kitty_setup import config_updater
from kitty_setup.scenes import _client


def _fake_paths(tmp_path: Path) -> config_updater.ConfigPaths:
    """Return a ConfigPaths whose payload_dir lives under tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True)
    return paths


def test_resolve_socket_returns_to_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)

    def boom() -> list[int]:
        raise AssertionError("pgrep must not run when --to is passed")

    monkeypatch.setattr(_client, "_pgrep_kitty_pids", boom)
    assert _client._resolve_socket("unix:/tmp/kitty-3333") == "unix:/tmp/kitty-3333"


def test_resolve_socket_returns_env_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.setenv("KITTY_LISTEN_ON", "unix:/tmp/kitty-1111")

    def boom() -> list[int]:
        raise AssertionError("pgrep must not run when $KITTY_LISTEN_ON is set")

    monkeypatch.setattr(_client, "_pgrep_kitty_pids", boom)
    assert _client._resolve_socket(None) == "unix:/tmp/kitty-1111"


def test_resolve_socket_pgrep_single_pid_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    paths = _fake_paths(tmp_path)
    (paths.payload_dir / "remote-control.conf").write_text(
        "listen_on unix:/tmp/kitty\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [4242])
    assert _client._resolve_socket(None) == "unix:/tmp/kitty-4242"


def test_resolve_socket_config_absent_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    paths = _fake_paths(tmp_path)
    # File does NOT exist on disk
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )

    def boom() -> list[int]:
        raise AssertionError("pgrep must not run when config is absent")

    monkeypatch.setattr(_client, "_pgrep_kitty_pids", boom)
    with pytest.raises(_client.SceneClientError, match="remote-control.conf missing"):
        _client._resolve_socket(None)


def test_resolve_socket_config_present_no_directive_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    paths = _fake_paths(tmp_path)
    # File exists but has no listen_on directive
    (paths.payload_dir / "remote-control.conf").write_text(
        "allow_remote_control yes\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )

    def boom() -> list[int]:
        raise AssertionError("pgrep must not run when listen_on directive is missing")

    monkeypatch.setattr(_client, "_pgrep_kitty_pids", boom)
    with pytest.raises(_client.SceneClientError, match="remote-control.conf missing"):
        _client._resolve_socket(None)


def test_resolve_socket_zero_pids_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    paths = _fake_paths(tmp_path)
    (paths.payload_dir / "remote-control.conf").write_text(
        "listen_on unix:/tmp/kitty\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [])
    with pytest.raises(_client.SceneClientError, match="no kitty process found"):
        _client._resolve_socket(None)


def test_resolve_socket_multi_pids_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    paths = _fake_paths(tmp_path)
    (paths.payload_dir / "remote-control.conf").write_text(
        "listen_on unix:/tmp/kitty\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [101, 202])
    with pytest.raises(_client.SceneClientError, match=r"multiple kitty processes.*101.*202"):
        _client._resolve_socket(None)


def test_kitten_at_constructs_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    fake_bin = tmp_path / "kitten"
    fake_bin.touch()
    monkeypatch.setattr(_client, "_resolve_kitten_binary", lambda: fake_bin)
    monkeypatch.setattr(_client, "_resolve_socket", lambda to: "unix:/tmp/kitty-4242")

    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(_client.subprocess, "run", fake_run)
    _client.kitten_at("set-window-title", "--temporary", "deploy logs")
    assert captured["argv"] == [
        str(fake_bin),
        "@",
        "--to=unix:/tmp/kitty-4242",
        "set-window-title",
        "--temporary",
        "deploy logs",
    ]
