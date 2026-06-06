"""Unit tests for `kitty_setup.scenes.accent` (set_tab_accent).

Stubs `kitten_at` so the tests run without spawning kitty. The hypothesis
probe `tmp/h23-styling/run.py` grounds the real behaviour; these stubs
are provisional per R7 until the integration tests under
`tests/integration/test_h23_styling.py` are green.
"""

from __future__ import annotations

import subprocess

import pytest

from kitty_setup.scenes import _client, accent


def _fake_run_returning(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


def test_set_tab_accent_hex_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert accent.set_tab_accent("#0066cc") == 0
    assert captured["call"] == (
        "set-tab-color",
        "active_bg=#0066cc",
        "inactive_bg=#0066cc",
    )
    assert "--match" not in captured["call"]


def test_set_tab_accent_named_with_active_fg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    accent.set_tab_accent("blue", active_fg="white")
    # Colors are normalized to hex client-side: blue->#0000ff, white->#ffffff.
    assert "active_bg=#0000ff" in captured["call"]
    assert "active_fg=#ffffff" in captured["call"]
    assert "inactive_fg=" not in " ".join(captured["call"])


def test_set_tab_accent_propagates_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(returncode=1, stderr="Error: no kitty process found\n"),
    )
    # A valid (normalized) color still reaches kitten, whose nonzero propagates.
    assert accent.set_tab_accent("#abcdef") == 1


def test_set_tab_accent_match_passed_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    accent.set_tab_accent("red", match="recent:0")
    # red normalizes to its X11 hex #ff0000 before the kitten call.
    assert captured["call"] == (
        "set-tab-color",
        "--match",
        "recent:0",
        "active_bg=#ff0000",
        "inactive_bg=#ff0000",
    )
