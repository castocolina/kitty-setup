"""Unit tests for `kitty_setup.scenes.title` (set_window_title / set_tab_title).

Stubs `kitten_at` so the tests run without spawning kitty. The hypothesis
probe `tmp/h22-window-title/run.py` grounds the real behaviour; these stubs
are provisional per R7 until the integration tests under
`tests/integration/test_h22_window_title.py` (§7.2) are green.
"""

from __future__ import annotations

import subprocess

import pytest

from kitty_setup.scenes import _client, title


def _fake_run_returning(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr
    )


def test_set_window_title_passes_temporary_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert title.set_window_title("x", temporary=True) == 0
    assert captured["call"] == ("set-window-title", "--temporary", "x")


def test_set_window_title_omits_temporary_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert title.set_window_title("x", temporary=False) == 0
    assert "--temporary" not in captured["call"]
    assert captured["call"] == ("set-window-title", "x")


def test_set_tab_title_no_temporary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert title.set_tab_title("y") == 0
    assert "--temporary" not in captured["call"]
    assert captured["call"] == ("set-tab-title", "y")


def test_title_functions_propagate_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(returncode=1, stderr="kitten said no\n"),
    )
    assert title.set_window_title("x") == 1
    assert title.set_tab_title("x") == 1


def test_match_flag_passed_through_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    title.set_window_title("z", temporary=False, match="id:5")
    assert captured["call"] == ("set-window-title", "--match", "id:5", "z")


def test_match_flag_passed_through_tab(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    title.set_tab_title("z", match="recent:0")
    assert captured["call"] == ("set-tab-title", "--match", "recent:0", "z")


def test_cli_handler_translates_scene_client_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Provisional per R7; grounded by tmp/h22-window-title/run.py."""
    import argparse

    def raising(*a: object, **k: object) -> subprocess.CompletedProcess[str]:
        raise _client.SceneClientError("no kitty process found")

    monkeypatch.setattr(_client, "kitten_at", raising)
    ns = argparse.Namespace(text="x", temporary=True, match=None, to=None)
    assert title.cli_set_window_title(ns) == 1
    assert "no kitty process found" in capsys.readouterr().err
