"""Unit tests for `kitty_setup.scenes.font` (set_os_window_font_size).

Stubs `kitten_at` so the tests run without spawning kitty. The hypothesis
probe `tmp/h23-styling/run.py` grounds the real behaviour; these stubs
are provisional per R7 until the integration tests under
`tests/integration/test_h23_styling.py` are green.
"""

from __future__ import annotations

import subprocess

import pytest

from kitty_setup.scenes import _client, font


def _fake_run_returning(
    returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr
    )


@pytest.mark.parametrize("value", ["14", "+2", "-2", "*1.1", "/2", "0"])
def test_set_os_window_font_size_passes_value_verbatim(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    assert font.set_os_window_font_size(value) == 0
    assert captured["call"] == ("set-font-size", value)


def test_set_os_window_font_size_all_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    captured: dict[str, tuple[str, ...]] = {}

    def fake(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        captured["call"] = (verb, *args)
        return _fake_run_returning()

    monkeypatch.setattr(_client, "kitten_at", fake)
    font.set_os_window_font_size("14", all_=True)
    assert "--all" in captured["call"]
    assert captured["call"] == ("set-font-size", "--all", "14")


def test_set_os_window_font_size_propagates_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provisional per R7; grounded by tmp/h23-styling/run.py."""
    monkeypatch.setattr(
        _client,
        "kitten_at",
        lambda *a, **k: _fake_run_returning(returncode=1, stderr="bad size\n"),
    )
    assert font.set_os_window_font_size("notanumber") == 1
