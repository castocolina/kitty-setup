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


def _fake_run_returning(returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


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
    # red normalizes to its X11 hex #ff0000 before the kitten call.
    assert captured["call"] == ("set-colors", "--match", "id:5", "background=#ff0000")


def test_set_window_background_propagates_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(returncode=1, stderr="no kitty found\n"),
    )
    # A valid (normalized) color still reaches kitten, whose nonzero propagates.
    assert background.set_window_background("#abcdef") == 1


def _recording_kitten(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, ...]]:
    """Replace `kitten_at` with a stub that records every call; return the record."""
    calls: list[tuple[str, ...]] = []

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        calls.append((verb, *args))
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    return calls


# D-12 (02-06): an empty, whitespace-only or None colour is ABSENT — no kitten call at
# all. Before 02-06 the truthiness fallback sent `background=` (and, for None, the
# literal `background=None`) to the kitten, which exits 1 "is not a valid color"
# (tmp/h32-color-forms/). Asserted on the recorded calls, not on the return value alone.
@pytest.mark.parametrize("color", ["", "   ", None], ids=["empty", "whitespace", "none-object"])
def test_set_window_background_absent_no_call(
    monkeypatch: pytest.MonkeyPatch, color: str | None
) -> None:
    calls = _recording_kitten(monkeypatch)
    assert background.set_window_background(color) == 0
    assert calls == []


def test_guard_hex_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _recording_kitten(monkeypatch)
    assert background.set_window_background("#0a7") == 0
    assert calls == [("set-colors", "background=#0a7")]


# Today's reset-sentinel path, PINNED, not changed. Measured on kitty 0.49.0:
# `set-colors background=NONE` exits 1 "The color background cannot be set to none".
# That is a Phase 6 blocker recorded in .planning/STATE.md, not 02-06's to fix; this
# test states the starting point Phase 6 inherits.
@pytest.mark.parametrize("color", ["none", "NONE"])
def test_guard_none_sentinel(monkeypatch: pytest.MonkeyPatch, color: str) -> None:
    calls = _recording_kitten(monkeypatch)
    assert background.set_window_background(color) == 0
    assert calls == [("set-colors", "background=NONE")]
