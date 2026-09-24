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


# D-12 (02-06): an empty or whitespace-only colour is ABSENT. With nothing else to set
# there is no kitten call at all. Before 02-06 the truthiness fallback sent
# `active_bg= inactive_bg=` to the kitten, which exits 1 "is not a valid color"
# (tmp/h32-color-forms/). Asserted on the recorded calls, not on the return value alone.
@pytest.mark.parametrize("color", ["", "   "], ids=["empty", "whitespace"])
def test_set_tab_accent_absent_no_call(monkeypatch: pytest.MonkeyPatch, color: str) -> None:
    calls = _recording_kitten(monkeypatch)
    assert accent.set_tab_accent(color) == 0
    assert calls == []


def test_set_tab_accent_absent_no_call_with_match_only(monkeypatch: pytest.MonkeyPatch) -> None:
    # A --match selector alone is not something to set: still no kitten call.
    calls = _recording_kitten(monkeypatch)
    assert accent.set_tab_accent("", match="id:1") == 0
    assert calls == []


def test_set_tab_accent_absent_keeps_fg(monkeypatch: pytest.MonkeyPatch) -> None:
    # The colour is absent but both fg overrides are present: the bg arguments are
    # omitted and the fg arguments still reach the kitten in one call.
    calls = _recording_kitten(monkeypatch)
    assert accent.set_tab_accent("", active_fg="white", inactive_fg="gray") == 0
    assert calls == [("set-tab-color", "active_fg=#ffffff", "inactive_fg=#bebebe")]


def test_guard_hex_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _recording_kitten(monkeypatch)
    assert accent.set_tab_accent("#0a7") == 0
    assert calls == [("set-tab-color", "active_bg=#0a7", "inactive_bg=#0a7")]


# Today's reset-sentinel path, PINNED, not changed. Measured on kitty 0.49.0:
# `set-tab-color active_bg=NONE` exits 0, while `set-colors background=NONE` exits 1 —
# the Phase 6 blocker recorded in .planning/STATE.md, not 02-06's to fix.
@pytest.mark.parametrize("color", ["none", "NONE"])
def test_guard_none_sentinel(monkeypatch: pytest.MonkeyPatch, color: str) -> None:
    calls = _recording_kitten(monkeypatch)
    assert accent.set_tab_accent(color) == 0
    assert calls == [("set-tab-color", "active_bg=NONE", "inactive_bg=NONE")]
