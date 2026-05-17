"""Unit tests for `kitty_setup.scenes.background` (set_window_background).

Stubs `kitten_at` so the tests run without spawning kitty. The hypothesis
probe `tmp/h23-styling/run.py` grounds the real behaviour; these stubs
are provisional per R7 until the integration tests under
`tests/integration/test_h23_styling.py` are green.
"""

from __future__ import annotations

import subprocess

import pytest

from kitty_setup.scenes import _client, background


def _fake_run_returning(
    returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr
    )


def test_set_window_background_hex_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert background.set_window_background("#001a33") == 0
    assert captured["call"] == ("set-colors", "background=#001a33")


def test_set_window_background_named_with_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    background.set_window_background("red", match="id:5")
    assert captured["call"] == ("set-colors", "--match", "id:5", "background=red")


def test_set_window_background_propagates_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(returncode=1, stderr="bad color\n"),
    )
    assert background.set_window_background("notacolor") == 1
