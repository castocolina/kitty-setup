"""Unit tests for `kitty_setup.scenes.opacity` (set_os_window_opacity).

The load-bearing test is `test_toggle_argv_ordering` — kitten requires
`--toggle` BEFORE the positional value, and that ordering is enforced by
the implementation. A future refactor that flips the order would silently
break runtime usage; this test catches it.

Stubs `kitten_at` so the tests run without spawning kitty. The hypothesis
probe `tmp/h23-styling/run.py` grounds the real behaviour; these stubs
are provisional per R7 until the integration tests under
`tests/integration/test_h23_styling.py` are green.
"""

from __future__ import annotations

import argparse
import subprocess

import pytest

from kitty_setup.scenes import _client, opacity


def _fake_run_returning(
    returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr
    )


def test_set_os_window_opacity_no_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert opacity.set_os_window_opacity(0.7) == 0
    assert captured["call"] == ("set-background-opacity", "0.7")


def test_set_os_window_opacity_toggle_argv_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load-bearing per D3: --toggle MUST precede positional value.

    Provisional per R7; grounded by tmp/h23-styling/run.py.
    """
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert opacity.set_os_window_opacity(0.7, toggle=True) == 0
    call = captured["call"]
    assert call == ("set-background-opacity", "--toggle", "0.7")
    # Index-level guard: catches refactors that flip the order.
    assert call.index("--toggle") < call.index("0.7")


def test_set_os_window_opacity_all_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    opacity.set_os_window_opacity(0.5, all_=True)
    assert captured["call"] == ("set-background-opacity", "--all", "0.5")


def test_set_os_window_opacity_propagates_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(
            returncode=1,
            stderr=(
                "Error: You must turn on the dynamic_background_opacity option "
                "in kitty.conf to be able to set background opacity\n"
            ),
        ),
    )
    assert opacity.set_os_window_opacity(0.5) == 1


def test_cli_handler_translates_scene_client_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Representative for all four new cli_* wrappers per tasks §5.4.1.

    Provisional per R7; grounded by tmp/h23-styling/run.py.
    """

    def raising(*a: object, **k: object) -> subprocess.CompletedProcess[str]:
        raise _client.SceneClientError("no kitty process found")

    monkeypatch.setattr(_client, "kitten_at", raising)
    ns = argparse.Namespace(value=0.7, toggle=False, all=False, to=None)
    assert opacity.cli_set_os_window_opacity(ns) == 1
    assert "no kitty process found" in capsys.readouterr().err
